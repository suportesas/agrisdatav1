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

Este módulo é um PROTÓTIPO: não está ligado a nenhuma view/URL. Para testar,
use o management command `consultar_dfe`.
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

import requests
import truststore
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
