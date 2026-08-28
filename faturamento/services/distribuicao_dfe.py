"""
Protótipo — NFe Distribuição de DF-e (distDFeInt).

Consulta, por CNPJ ou CPF do destinatário, os documentos fiscais eletrônicos
(NF-e e eventos) emitidos contra ele, usando o serviço nacional (Ambiente
Nacional / SVRS), independente da UF do destinatário.

Docs oficiais: Nota Técnica 2014.002 (portal nacional da NF-e).

Como o serviço IntegraNotas (usado hoje para EMITIR notas — ver
`faturamento/services/integranotas.py`) não expõe esse serviço, aqui a
comunicação é feita diretamente com a SEFAZ/Ambiente Nacional via TLS mútuo
com o certificado A1, sem depender de bibliotecas externas (só lxml,
cryptography e requests, que já são dependências do projeto).

IMPORTANTE — autenticação: o certificado usado precisa pertencer ao MESMO
CNPJ/CPF que está sendo consultado (ou a alguém com procuração eletrônica
para consulta em nome dele — outorga cadastrada em
https://www.nfe.fazenda.gov.br). Hoje o certificado fica em
`ConfiguracaoFiscal` (por empresa), então se o CNPJ/CPF da fazenda for
diferente do CNPJ do certificado, a SEFAZ vai rejeitar a consulta.

Sincronização automática: `sincronizar_dfe_empresa()` / `sincronizar_todas_empresas()`
fazem a varredura incremental por NSU, gravam `faturamento.models.DfeRecebido` e buscam
o XML completo de cada NF-e nova (throttled — ver docstring de `sincronizar_dfe_empresa`).
São chamadas pelo management command `sincronizar_dfe` e pelo webhook
`faturamento:dfe_sync_webhook` (para o cron do Supabase). Para uma consulta pontual
manual, use o management command `consultar_dfe`.
"""
from __future__ import annotations

import base64
import gzip
import logging
import os
import re
import ssl
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation

import requests
import truststore
from django.db.models import Q
from django.utils import timezone
from lxml import etree
from requests.adapters import HTTPAdapter

logger = logging.getLogger(__name__)

NFE_NS = 'http://www.portalfiscal.inf.br/nfe'
SOAP_NS = 'http://www.w3.org/2003/05/soap-envelope'
WSDL_NS = 'http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe'

URL_PRODUCAO = 'https://www1.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx'
URL_HOMOLOGACAO = 'https://hom1.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx'
SOAP_ACTION = 'http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe/nfeDistDFeInteresse'

# Código IBGE da UF — exigido em cUFAutor mesmo sendo um serviço nacional.
UF_IBGE = {
    'RO': '11', 'AC': '12', 'AM': '13', 'RR': '14', 'PA': '15', 'AP': '16', 'TO': '17',
    'MA': '21', 'PI': '22', 'CE': '23', 'RN': '24', 'PB': '25', 'PE': '26', 'AL': '27',
    'SE': '28', 'BA': '29', 'MG': '31', 'ES': '32', 'RJ': '33', 'SP': '35', 'PR': '41',
    'SC': '42', 'RS': '43', 'MS': '50', 'MT': '51', 'GO': '52', 'DF': '53',
}

_ONLY_DIGITS = re.compile(r'\D')


class DistribuicaoDFeError(Exception):
    """Erro de transporte/parsing ao consultar o serviço de Distribuição de DF-e."""


@dataclass
class DocumentoDistribuido:
    nsu: str
    schema: str
    chave_acesso: str = ''
    xml: str = ''


@dataclass
class ResultadoDistribuicao:
    c_stat: str
    x_motivo: str
    ult_nsu: str = ''
    max_nsu: str = ''
    documentos: list[DocumentoDistribuido] = field(default_factory=list)

    @property
    def sucesso(self) -> bool:
        """cStat 137 = nenhum documento localizado (não é erro); 138 = localizado."""
        return self.c_stat in ('137', '138')


def consultar_distribuicao_dfe(
    *,
    cnpj_cpf: str,
    cert_pfx: bytes,
    senha_cert: str,
    uf: str,
    ambiente: str = '2',
    ult_nsu: str | None = None,
    nsu: str | None = None,
    chave: str | None = None,
    timeout: int = 30,
) -> ResultadoDistribuicao:
    """Consulta o serviço de Distribuição de DF-e para um CNPJ/CPF.

    Uma das três formas de consulta deve ser escolhida (nesta ordem de
    prioridade se mais de uma for passada): `chave` (consChNFe — um
    documento específico), `nsu` (consNSU — um NSU específico), ou
    `ult_nsu` (distNSU — a forma normal de sincronização incremental;
    padrão '0' na primeira consulta).
    """
    if not cert_pfx:
        raise DistribuicaoDFeError('Certificado digital A1 não configurado.')

    uf_ibge = UF_IBGE.get((uf or '').upper())
    if not uf_ibge:
        raise DistribuicaoDFeError(f'UF inválida ou não informada: {uf!r}')

    xml_dist = _montar_dist_dfe_int(
        cnpj_cpf, uf_ibge, ambiente, ult_nsu=ult_nsu, nsu=nsu, chave=chave,
    )
    envelope = _montar_envelope_soap(xml_dist)
    url = URL_PRODUCAO if ambiente == '1' else URL_HOMOLOGACAO
    headers = {'Content-Type': f'application/soap+xml; charset=utf-8; action="{SOAP_ACTION}"'}

    with _pfx_para_pem(cert_pfx, senha_cert) as (cert_path, key_path):
        try:
            session = _session_com_certificado(cert_path, key_path)
            resp = session.post(url, data=envelope, headers=headers, timeout=timeout)
        except requests.RequestException as exc:
            raise DistribuicaoDFeError(f'Falha de comunicação com a SEFAZ: {exc}') from exc

    if resp.status_code != 200:
        raise DistribuicaoDFeError(f'SEFAZ retornou HTTP {resp.status_code}: {resp.text[:500]}')

    return _parsear_resposta(resp.content)


class _SSLContextAdapter(HTTPAdapter):
    """HTTPAdapter que usa um ssl.SSLContext já pronto em vez do bundle certifi padrão do requests."""

    def __init__(self, ssl_context: ssl.SSLContext, **kwargs):
        self._ssl_context = ssl_context
        super().__init__(**kwargs)

    def init_poolmanager(self, *args, **kwargs):
        kwargs['ssl_context'] = self._ssl_context
        return super().init_poolmanager(*args, **kwargs)


def _session_com_certificado(cert_path: str, key_path: str) -> requests.Session:
    """Monta uma sessão com TLS mútuo (certificado A1) que valida o servidor pela
    store de certificados do Windows/SO (via `truststore`) em vez do bundle certifi.

    Necessário porque o certificado TLS dos webservices da Receita/SEFAZ é emitido
    pela cadeia ICP-Brasil/SERPRO, que não está no bundle certifi padrão do
    `requests` — só na store do sistema operacional (por isso funciona no
    navegador, mas falha com `SSLCertVerificationError: unable to get local
    issuer certificate` usando `requests` puro).
    """
    ctx = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.load_cert_chain(certfile=cert_path, keyfile=key_path)
    session = requests.Session()
    session.mount('https://', _SSLContextAdapter(ctx))
    return session


# ─── Certificado: .pfx em memória → arquivos PEM temporários ──────────────────
# `requests` exige caminhos de arquivo para TLS mútuo (não aceita bytes em
# memória), então extraímos chave+certificado do .pfx e gravamos em arquivos
# temporários apagados assim que a requisição termina.

@contextmanager
def _pfx_para_pem(pfx_bytes: bytes, senha: str):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.serialization.pkcs12 import load_key_and_certificates

    pwd = senha.encode('utf-8') if senha else b''
    try:
        key, cert, _ = load_key_and_certificates(pfx_bytes, pwd)
    except Exception as exc:
        raise DistribuicaoDFeError(f'Não foi possível ler o certificado .pfx: {exc}') from exc
    if key is None or cert is None:
        raise DistribuicaoDFeError('Certificado .pfx não contém chave privada e certificado válidos.')

    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    key_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )

    cert_fd, cert_path = tempfile.mkstemp(suffix='.pem')
    key_fd, key_path = tempfile.mkstemp(suffix='.pem')
    try:
        with os.fdopen(cert_fd, 'wb') as f:
            f.write(cert_pem)
        with os.fdopen(key_fd, 'wb') as f:
            f.write(key_pem)
        yield cert_path, key_path
    finally:
        for path in (cert_path, key_path):
            try:
                os.unlink(path)
            except OSError:
                pass


# ─── Montagem do XML ───────────────────────────────────────────────────────────

def _montar_dist_dfe_int(
    cnpj_cpf: str, uf_ibge: str, ambiente: str, *,
    ult_nsu: str | None, nsu: str | None, chave: str | None,
) -> bytes:
    digitos = _ONLY_DIGITS.sub('', cnpj_cpf or '')
    if len(digitos) == 14:
        tag_doc = 'CNPJ'
    elif len(digitos) == 11:
        tag_doc = 'CPF'
    else:
        raise DistribuicaoDFeError(f'CNPJ/CPF inválido: {cnpj_cpf!r}')

    raiz = etree.Element('distDFeInt', versao='1.01', nsmap={None: NFE_NS})
    etree.SubElement(raiz, 'tpAmb').text = str(ambiente)
    etree.SubElement(raiz, 'cUFAutor').text = uf_ibge
    etree.SubElement(raiz, tag_doc).text = digitos

    if chave:
        cons = etree.SubElement(raiz, 'consChNFe')
        etree.SubElement(cons, 'chNFe').text = chave
    elif nsu:
        cons = etree.SubElement(raiz, 'consNSU')
        etree.SubElement(cons, 'NSU').text = nsu.zfill(15)
    else:
        dist = etree.SubElement(raiz, 'distNSU')
        etree.SubElement(dist, 'ultNSU').text = (ult_nsu or '0').zfill(15)

    return etree.tostring(raiz, xml_declaration=False, encoding='utf-8')


def _montar_envelope_soap(xml_dist_dfe_int: bytes) -> bytes:
    envelope = (
        '<soap12:Envelope '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
        'xmlns:xsd="http://www.w3.org/2001/XMLSchema" '
        f'xmlns:soap12="{SOAP_NS}">'
        '<soap12:Body>'
        f'<nfeDistDFeInteresse xmlns="{WSDL_NS}">'
        f'<nfeDadosMsg>{xml_dist_dfe_int.decode("utf-8")}</nfeDadosMsg>'
        '</nfeDistDFeInteresse>'
        '</soap12:Body>'
        '</soap12:Envelope>'
    )
    return envelope.encode('utf-8')


# ─── Parsing da resposta ────────────────────────────────────────────────────────

def _parsear_resposta(soap_bytes: bytes) -> ResultadoDistribuicao:
    try:
        raiz = etree.fromstring(soap_bytes)
    except etree.XMLSyntaxError as exc:
        raise DistribuicaoDFeError(f'Resposta da SEFAZ não é XML válido: {exc}') from exc

    ns = {'nfe': NFE_NS}
    ret = raiz.find('.//nfe:retDistDFeInt', namespaces=ns)
    if ret is None:
        raise DistribuicaoDFeError(f'Resposta da SEFAZ em formato inesperado: {soap_bytes[:800]!r}')

    def _txt(tag: str) -> str:
        el = ret.find(f'nfe:{tag}', namespaces=ns)
        return el.text or '' if el is not None else ''

    resultado = ResultadoDistribuicao(
        c_stat=_txt('cStat'),
        x_motivo=_txt('xMotivo'),
        ult_nsu=_txt('ultNSU'),
        max_nsu=_txt('maxNSU'),
    )

    lote = ret.find('nfe:loteDistDFeInt', namespaces=ns)
    if lote is not None:
        for doc_zip in lote.findall('nfe:docZip', namespaces=ns):
            xml_descompactado = gzip.decompress(base64.b64decode(doc_zip.text)).decode('utf-8')
            resultado.documentos.append(DocumentoDistribuido(
                nsu=doc_zip.get('NSU', ''),
                schema=doc_zip.get('schema', ''),
                chave_acesso=_extrair_chave(xml_descompactado),
                xml=xml_descompactado,
            ))

    return resultado


def _extrair_chave(xml_str: str) -> str:
    try:
        doc = etree.fromstring(xml_str.encode('utf-8'))
    except etree.XMLSyntaxError:
        return ''
    ns = {'nfe': NFE_NS}
    for tag in ('chNFe', 'chNFePend'):
        el = doc.find(f'.//nfe:{tag}', namespaces=ns)
        if el is not None and el.text:
            return el.text
    return ''


def _extrair_dados_resumo(xml_str: str) -> dict:
    """Extrai os campos do resumo (resNFe/resEvento) já presentes no próprio XML —
    não precisa do XML completo pra isso (CNPJ, nome, valor, data, situação/evento)."""
    try:
        doc = etree.fromstring(xml_str.encode('utf-8'))
    except etree.XMLSyntaxError:
        return {}
    ns = {'nfe': NFE_NS}

    def _t(tag: str) -> str:
        el = doc.find(f'.//nfe:{tag}', namespaces=ns)
        return (el.text or '').strip() if el is not None else ''

    valor_txt = _t('vNF')
    try:
        valor_total = Decimal(valor_txt) if valor_txt else None
    except InvalidOperation:
        valor_total = None

    data_txt = _t('dhEmi') or _t('dhEvento')
    data_emissao = None
    if data_txt:
        try:
            data_emissao = datetime.fromisoformat(data_txt.replace('Z', '+00:00')).date()
        except ValueError:
            data_emissao = None

    return {
        'chave_acesso': _t('chNFe') or _t('chNFePend'),
        'cnpj_emitente': _t('CNPJ'),
        'nome_emitente': _t('xNome'),
        'situacao': _t('cSitNFe'),
        'tipo_evento': _t('tpEvento'),
        'valor_total': valor_total,
        'data_emissao': data_emissao,
    }


# ─── Sincronização automática (usa as funções acima) ────────────────────────────

CANCELAMENTO_TPEVENTO = '110111'


def _normalizar_schema(schema_raw: str) -> str:
    """O atributo `schema` do docZip vem como nome de arquivo XSD (ex: 'resNFe_v1.01.xsd'),
    não o valor curto usado em DfeRecebido.SCHEMA_CHOICES — normaliza aqui."""
    if schema_raw.startswith('resNFe'):
        return 'resNFe'
    if schema_raw.startswith('resEvento'):
        return 'resEvento'
    return schema_raw[:20]


def baixar_xml_completo_dfe(doc, config=None) -> bool:
    """Busca o XML completo (`consChNFe`) de um `DfeRecebido` (schema resNFe) e salva em `xml_url`.

    Best-effort: usada tanto pelo passo 3 de `sincronizar_dfe_empresa` (cron) quanto
    logo após uma manifestação bem-sucedida (views `dfe_manifestar`/`dfe_manifestar_lote`),
    para não depender só do próximo ciclo da cron. Nunca levanta — qualquer falha de
    comunicação com a SEFAZ ou configuração ausente só retorna False, já que quem chama
    não deve deixar de completar seu fluxo principal (manifestação já registrada) por
    causa disso; a cron tenta de novo depois.
    """
    from faturamento.fiscal_storage import upload_xml_texto
    from faturamento.models import ConfiguracaoFiscal

    if doc.xml_url:
        return True

    if config is None:
        config = ConfiguracaoFiscal.objects.filter(empresa=doc.empresa).first()
    if not config or not config.certificado_pfx:
        return False

    cnpj_cpf = _ONLY_DIGITS.sub('', doc.empresa.cnpj or '')
    uf = (doc.empresa.uf or '').upper()
    if not cnpj_cpf or not uf or not doc.chave_acesso:
        return False

    try:
        resp_chave = consultar_distribuicao_dfe(
            cnpj_cpf=cnpj_cpf, cert_pfx=bytes(config.certificado_pfx),
            senha_cert=config.senha_certificado, uf=uf, ambiente='1',
            chave=doc.chave_acesso,
        )
    except DistribuicaoDFeError as exc:
        logger.warning('Falha ao baixar XML completo da chave %s: %s', doc.chave_acesso, exc)
        return False

    if not resp_chave.documentos:
        if resp_chave.c_stat not in ('137', '138'):
            logger.warning('SEFAZ recusou XML completo da chave %s: cStat %s — %s',
                            doc.chave_acesso, resp_chave.c_stat, resp_chave.x_motivo)
        return False

    xml_completo = resp_chave.documentos[0].xml
    url = upload_xml_texto(xml_completo, doc.empresa_id, doc.chave_acesso)
    if not url:
        return False

    doc.xml_url = url
    update_fields = ['xml_url']

    # DANFE (PDF): tenta a rota oficial da IntegraNotas primeiro, cai pro gerador local
    # se ela não tiver essa chave (nota de terceiro pode não estar na conta). Best-effort
    # — uma falha aqui não pode derrubar o download do XML, que é o que efetivamente
    # libera a manifestação/consulta da nota.
    try:
        from faturamento.fiscal_storage import upload_pdf
        from faturamento.services.dfe_danfe import obter_pdf_base64, versionar_url

        pdf_b64 = obter_pdf_base64(xml_completo, doc, config=config)
        if pdf_b64:
            pdf_url = upload_pdf(pdf_b64, doc.empresa_id, 'dfe', f'{doc.chave_acesso}.pdf')
            if pdf_url:
                doc.pdf_danfe_url = versionar_url(pdf_url)
                update_fields.append('pdf_danfe_url')
    except Exception as exc:
        logger.warning('Falha ao gerar DANFE (PDF) da chave %s: %s', doc.chave_acesso, exc)

    doc.save(update_fields=update_fields)
    return True


def sincronizar_dfe_empresa(empresa, *, max_xml: int = 10, max_manifestacoes: int = 10) -> dict:
    """Sincroniza a Distribuição de DF-e de uma empresa a partir do último NSU salvo.

    1. Avança página a página em `distNSU` (usando `ConfiguracaoFiscal.dfe_ultimo_nsu`
       como cursor) até alcançar o `maxNSU` informado pela SEFAZ, gravando um
       `DfeRecebido` por documento novo (idempotente via unique_together empresa+nsu).
    2. Se `dfe_manifestar_ciencia_automatica` estiver ativo, registra "Ciência da
       Operação" (via IntegraNotas) para até `max_manifestacoes` `resNFe` de terceiros
       ainda sem manifestação — necessário porque a SEFAZ só libera o download do XML
       completo (`consChNFe`) ao destinatário depois de pelo menos essa manifestação.
    3. Busca o XML completo (`consChNFe`) de até `max_xml` `resNFe` pendentes
       (`xml_url=''`) e sobe pro Supabase — throttled porque cada busca é uma consulta
       extra à SEFAZ, sujeita ao mesmo rate limit (`cStat 656`) do distNSU.

    Sempre consulta ambiente PRODUÇÃO (documentos reais só existem lá) e usa o CNPJ/CPF
    cadastrado na própria Empresa (não o do certificado — só precisam ser compatíveis
    perante a SEFAZ, por outorga/procuração).

    Retorna um resumo: {'empresa_id', 'novos', 'ciencia_automatica', 'xml_baixados', 'erro'}.
    """
    from faturamento.models import ConfiguracaoFiscal, DfeRecebido
    from faturamento.services.integranotas import IntegranNotasClient, IntegranNotasError

    resultado = {'empresa_id': empresa.id, 'novos': 0, 'ciencia_automatica': 0, 'xml_baixados': 0, 'erro': None}

    try:
        config = ConfiguracaoFiscal.objects.get(empresa=empresa)
    except ConfiguracaoFiscal.DoesNotExist:
        resultado['erro'] = 'Empresa sem Configuração Fiscal.'
        return resultado

    if not config.certificado_pfx:
        resultado['erro'] = 'Empresa sem certificado digital A1 configurado.'
        return resultado

    cnpj_cpf = _ONLY_DIGITS.sub('', empresa.cnpj or '')
    if not cnpj_cpf:
        resultado['erro'] = 'Empresa sem CNPJ/CPF cadastrado.'
        return resultado

    uf = (empresa.uf or '').upper()
    if not uf:
        resultado['erro'] = 'Empresa sem UF cadastrada.'
        return resultado

    cert_pfx = bytes(config.certificado_pfx)
    senha_cert = config.senha_certificado
    ult_nsu = config.dfe_ultimo_nsu or '0'

    # Limite de páginas por execução — cada página já traz um lote de documentos;
    # isso é só uma trava de segurança contra loop infinito, não um limite operacional.
    for _ in range(50):
        try:
            resp = consultar_distribuicao_dfe(
                cnpj_cpf=cnpj_cpf, cert_pfx=cert_pfx, senha_cert=senha_cert,
                uf=uf, ambiente='1', ult_nsu=ult_nsu,
            )
        except DistribuicaoDFeError as exc:
            resultado['erro'] = str(exc)
            break

        if resp.c_stat not in ('137', '138'):
            resultado['erro'] = f'cStat {resp.c_stat}: {resp.x_motivo}'
            break

        for doc in resp.documentos:
            schema = _normalizar_schema(doc.schema)
            dados = _extrair_dados_resumo(doc.xml)

            if schema == 'resEvento' and dados.get('tipo_evento') == CANCELAMENTO_TPEVENTO and dados.get('chave_acesso'):
                DfeRecebido.objects.filter(
                    empresa=empresa, chave_acesso=dados['chave_acesso'],
                ).update(situacao='2')

            _, criado = DfeRecebido.objects.get_or_create(
                empresa=empresa, nsu=doc.nsu,
                defaults={
                    'schema': schema,
                    'chave_acesso': dados.get('chave_acesso', ''),
                    'cnpj_emitente': dados.get('cnpj_emitente', ''),
                    'nome_emitente': dados.get('nome_emitente', ''),
                    'valor_total': dados.get('valor_total'),
                    'data_emissao': dados.get('data_emissao'),
                    'situacao': dados.get('situacao', ''),
                },
            )
            if criado:
                resultado['novos'] += 1

        novo_ult_nsu = resp.ult_nsu or ult_nsu
        if novo_ult_nsu != config.dfe_ultimo_nsu:
            config.dfe_ultimo_nsu = novo_ult_nsu
            config.save(update_fields=['dfe_ultimo_nsu'])
        ult_nsu = novo_ult_nsu

        if not resp.documentos or not resp.max_nsu or resp.ult_nsu == resp.max_nsu:
            break

    if config.dfe_manifestar_ciencia_automatica and config.has_token:
        pendentes_manifestacao = DfeRecebido.objects.filter(
            empresa=empresa, schema='resNFe', manifestacao_tipo='',
        ).exclude(chave_acesso='').exclude(cnpj_emitente='').exclude(
            cnpj_emitente=cnpj_cpf,
        ).order_by('nsu')[:max_manifestacoes]

        client = IntegranNotasClient(config.get_token(), config.ambiente_nfe)
        for doc in pendentes_manifestacao:
            try:
                resp_manifesto = client.manifestar_nfe(doc.chave_acesso, 'ciencia_operacao')
            except IntegranNotasError as exc:
                if str(exc.codigo) == '573':
                    # SEFAZ já tinha esse evento registrado (fora deste sistema, ou
                    # dessincronizado) — sincroniza em vez de tratar como falha.
                    doc.manifestacao_tipo = 'ciencia_operacao'
                    doc.manifestacao_data = timezone.now()
                    doc.save(update_fields=['manifestacao_tipo', 'manifestacao_data'])
                    resultado['ciencia_automatica'] += 1
                    continue
                logger.warning('Falha ao manifestar Ciência automática da chave %s: %s', doc.chave_acesso, exc)
                continue
            except Exception as exc:
                logger.warning('Falha ao manifestar Ciência automática da chave %s: %s', doc.chave_acesso, exc)
                continue

            doc.manifestacao_tipo = 'ciencia_operacao'
            doc.manifestacao_protocolo = resp_manifesto.get('protocolo', '') or resp_manifesto.get('numero_protocolo', '')
            doc.manifestacao_data = timezone.now()
            doc.save(update_fields=['manifestacao_tipo', 'manifestacao_protocolo', 'manifestacao_data'])
            resultado['ciencia_automatica'] += 1

    # A SEFAZ só libera o XML completo (consChNFe) depois de pelo menos a
    # manifestação de Ciência — exceto para notas emitidas pela própria empresa
    # (não manifestáveis, mas liberadas de qualquer forma). Sem esse filtro, o
    # lote de max_xml pega sempre os NSU mais antigos independente de terem sido
    # manifestados, então um backlog de notas de terceiros nunca manifestadas
    # trava a fila pra sempre: a cron gasta as max_xml tentativas nelas (que
    # sempre falham) e nunca chega nas notas manifestadas mais recentes.
    pendentes = DfeRecebido.objects.filter(
        empresa=empresa, schema='resNFe', xml_url='',
    ).exclude(chave_acesso='').exclude(
        Q(manifestacao_tipo='') & ~Q(cnpj_emitente=cnpj_cpf),
    ).order_by('nsu')[:max_xml]

    for pendente in pendentes:
        if baixar_xml_completo_dfe(pendente, config=config):
            resultado['xml_baixados'] += 1

    return resultado


def sincronizar_todas_empresas(*, max_xml: int = 10) -> list[dict]:
    """Roda `sincronizar_dfe_empresa` para toda empresa com certificado configurado.

    Erros em uma empresa não interrompem as demais.
    """
    from faturamento.models import ConfiguracaoFiscal

    resultados = []
    for config in ConfiguracaoFiscal.objects.select_related('empresa'):
        if not config.certificado_pfx:
            continue
        try:
            resultados.append(sincronizar_dfe_empresa(config.empresa, max_xml=max_xml))
        except Exception as exc:
            logger.exception('Falha ao sincronizar DF-e da empresa %s', config.empresa_id)
            resultados.append({'empresa_id': config.empresa_id, 'erro': str(exc)})
    return resultados
