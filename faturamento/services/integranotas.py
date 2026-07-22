"""
IntegraNota API client — NF-e emission and cancellation.

Docs: https://integranotas.com.br/doc/nfe
Auth: Bearer token (configured in ConfiguracaoFiscal.token_integranotas)
Async flow: POST /nfe → code 5023 (queued) or 100 (authorized)
            GET  /nfe/{chave} to poll
Webhook alternative: configure URL in IntegraNota panel → POST /faturamento/webhook/integranotas/
"""
import re
import logging
import requests
from datetime import date as _date

logger = logging.getLogger(__name__)

_ONLY_DIGITS = re.compile(r'\D')

# CST 40/41 (isenta/não tributada) usam o grupo ICMS40 da NF-e, que não tem
# modBC/vBC/pICMS/vICMS — nenhum item nessas CSTs declara vBC. O total do
# cabeçalho (vBC) deve somar só os itens que efetivamente declaram vBC, senão
# a SEFAZ rejeita com o erro 531 (total da BC ICMS difere do somatório dos itens).
CST_ICMS_SEM_TRIBUTACAO = {'40', '41'}

# PIS/COFINS — conforme o schema real do endpoint /nfe da IntegraNotas (bloco
# impostos.pis / impostos.cofins): valor_base_calculo/aliquota (grupo PISAliq/
# COFINSAliq) só são aceitos nos CST 01, 02 e 49-99; quantidade_vendida/
# aliquota_valor (grupo PISQtde/COFINSQtde) só nos CST 03 e 49-99. O campo
# "valor" é sempre obrigatório, independente do CST.
CST_PIS_COFINS_ALIQ = {'01', '02', '49', '98', '99'}
CST_PIS_COFINS_QTD = {'03'}


def _item_tem_vbc_icms(item) -> bool:
    cst_icms = item.cst_icms or '40'
    return cst_icms not in CST_ICMS_SEM_TRIBUTACAO and bool(item.aliquota_icms) and float(item.aliquota_icms) > 0


# ─── Certificate helpers ──────────────────────────────────────────────────────

def parse_pfx(pfx_bytes: bytes, password: str) -> dict:
    """Read a PKCS#12 (.pfx/.p12) file and return certificate metadata.

    Returns:
        dict with keys: validade (date), cnpj (str digits), nome_titular (str)

    Raises:
        ValueError: if file cannot be read or contains no certificate.
    """
    from cryptography.hazmat.primitives.serialization.pkcs12 import load_key_and_certificates
    from cryptography import x509 as _x509

    pwd = password.encode('utf-8') if password else b''
    try:
        _, cert, _ = load_key_and_certificates(pfx_bytes, pwd)
    except Exception as exc:
        raise ValueError(f'Não foi possível ler o arquivo PFX: {exc}') from exc

    if cert is None:
        raise ValueError('Nenhum certificado encontrado no arquivo PFX.')

    # CN in Brazilian A1 certs: "RAZAO SOCIAL:CNPJ" or "NOME PESSOA:CPF"
    cn_attrs = cert.subject.get_attributes_for_oid(_x509.oid.NameOID.COMMON_NAME)
    cn = cn_attrs[0].value if cn_attrs else ''
    cnpj = ''
    if ':' in cn:
        raw = cn.split(':')[-1].strip()
        cnpj = _ONLY_DIGITS.sub('', raw)

    # Expiry date — cryptography ≥42 provides timezone-aware not_valid_after_utc
    try:
        not_after: _date = cert.not_valid_after_utc.date()
    except AttributeError:
        not_after = cert.not_valid_after.date()  # type: ignore[attr-defined]

    return {
        'validade': not_after,
        'cnpj': cnpj,
        'nome_titular': cn,
    }


def _digits(value: str) -> str:
    return _ONLY_DIGITS.sub('', value or '')


def _ie(value: str) -> str:
    v = (value or '').strip().upper()
    return v if v == 'ISENTO' else _ONLY_DIGITS.sub('', v)


def _ie_info(obj) -> tuple:
    """Retorna (indicador_ie, inscricao_estadual) normalizados para SEFAZ CT-e.

    Derivado do valor da IE (não do campo indicador_ie do cadastro, que é projetado para NF-e):
    - IE com dígitos reais → indicador '1' (Contribuinte ICMS)
    - IE = 'ISENTO' → indicador '9' (Não Contribuinte) — CT-e regra 617 rejeita '2' na maioria das UFs
    - Sem IE → indicador '9' (Não Contribuinte)
    """
    ie_raw = (getattr(obj, 'inscricao_estadual', '') or '').strip()
    if ie_raw.upper() == 'ISENTO':
        return '9', ''
    ie_clean = _ONLY_DIGITS.sub('', ie_raw)
    if ie_clean:
        return '1', ie_clean
    return '9', ''


def _is_exterior(cliente) -> bool:
    tipo = getattr(cliente, 'tipo_cliente', '') or ''
    pais = (getattr(cliente, 'pais', '') or 'Brasil').strip()
    return tipo == 'IMPORTADOR' or pais.lower() not in ('brasil', '')


CRT_MAP = {
    'SIMPLES_NACIONAL': '1',
    'LUCRO_PRESUMIDO': '2',
    'LUCRO_REAL': '3',
}

MODALIDADE_FRETE_MAP = {
    'SEM_FRETE': '9',
    'CIF':        '0',
    'FOB':        '1',
    'EMITENTE':   '0',
    'DESTINATARIO': '1',
}


PAIS_IBGE_MAP: dict[str, str] = {
    'argentina': '1068', 'bolívia': '1120', 'bolivia': '1120',
    'brasil': '1058', 'brazil': '1058',
    'chile': '1589', 'colômbia': '1635', 'colombia': '1635',
    'equador': '2143', 'ecuador': '2143',
    'paraguai': '4375', 'paraguay': '4375',
    'peru': '4391', 'uruguai': '5266', 'uruguay': '5266',
    'venezuela': '5290',
    'canadá': '1490', 'canada': '1490',
    'estados unidos': '4235', 'estados unidos da américa': '4235',
    'eua': '4235', 'usa': '4235', 'united states': '4235',
    'méxico': '3700', 'mexico': '3700',
    'alemanha': '3581', 'germany': '3581',
    'áustria': '1040', 'austria': '1040',
    'bélgica': '1074', 'belgium': '1074',
    'dinamarca': '2100', 'denmark': '2100',
    'espanha': '4170', 'spain': '4170',
    'finlândia': '1279', 'finland': '1279',
    'frança': '1155', 'france': '1155',
    'grécia': '3298', 'greece': '3298',
    'holanda': '4855', 'países baixos': '4855', 'netherlands': '4855',
    'hungria': '3344', 'hungary': '3344',
    'irlanda': '3514', 'ireland': '3514',
    'itália': '3735', 'italy': '3735',
    'noruega': '4839', 'norway': '4839',
    'polônia': '4422', 'poland': '4422',
    'portugal': '4731',
    'reino unido': '4766', 'uk': '4766', 'united kingdom': '4766',
    'república tcheca': '2437', 'czech republic': '2437',
    'rússia': '4502', 'russia': '4502',
    'suécia': '4936', 'sweden': '4936',
    'suíça': '4952', 'switzerland': '4952',
    'turquia': '5185', 'turkey': '5185',
    'arábia saudita': '4553', 'saudi arabia': '4553',
    'austrália': '1023', 'australia': '1023',
    'china': '1503',
    'coreia do sul': '1694', 'south korea': '1694',
    'emirados árabes': '2127', 'uae': '2127', 'united arab emirates': '2127',
    'índia': '3395', 'india': '3395',
    'israel': '3557',
    'japão': '3549', 'japan': '3549',
    'singapura': '4847', 'singapore': '4847',
    'taiwan': '4995',
    'egito': '2186', 'egypt': '2186',
    'marrocos': '3697', 'morocco': '3697',
    'nigéria': '4804', 'nigeria': '4804',
}


class IntegranNotasError(Exception):
    """Raised when IntegraNota returns a non-success response."""
    def __init__(self, message, codigo=None, erros=None):
        super().__init__(message)
        self.codigo = codigo
        if isinstance(erros, list):
            self.erros = erros
        elif erros:
            self.erros = [erros]
        else:
            self.erros = []


def build_emitente_softhouse_payload(empresa, config) -> dict:
    """Monta o payload de POST /v1/soft/emitente a partir de Empresa + ConfiguracaoFiscal.
    Docs: https://integranotas.com.br/doc/soft/emitente/cria

    Levanta IntegranNotasError se algum campo obrigatório da API não estiver
    preenchido no cadastro da empresa.
    """
    campos_obrigatorios = {
        'Nome Fantasia':            empresa.nome,
        'Razão Social':             empresa.razao_social or empresa.nome,
        'Telefone':                 empresa.telefone,
        'Endereço (rua)':           empresa.endereco,
        'Número do endereço':       empresa.numero_endereco,
        'Bairro':                   empresa.bairro,
        'Código IBGE do Município': empresa.codigo_municipio,
        'Cidade':                   empresa.cidade,
        'UF':                       empresa.uf,
        'CEP':                      empresa.cep,
    }
    faltando = [label for label, valor in campos_obrigatorios.items() if not (valor or '').strip()]
    if faltando:
        raise IntegranNotasError(
            'Preencha os campos obrigatórios antes de criar o emitente na IntegraNotas: '
            + ', '.join(faltando),
            codigo=None,
        )

    crt = CRT_MAP.get(getattr(config, 'regime_tributario', 'SIMPLES_NACIONAL'), '1')

    payload: dict = {
        'nome':      empresa.nome,
        'razao':     empresa.razao_social or empresa.nome,
        'crt':       crt,
        'telefone':  _digits(empresa.telefone or ''),
        'rua':       empresa.endereco,
        'numero':    empresa.numero_endereco,
        'bairro':    empresa.bairro,
        'cmun':      empresa.codigo_municipio,
        'municipio': empresa.cidade,
        'uf':        (empresa.uf or '').strip().upper(),
        'cep':       _digits(empresa.cep or ''),
        'documentos': {
            'nfe':  True,
            'cte':  True,
            'mdfe': True,
        },
    }

    if empresa.complemento_endereco:
        payload['complemento'] = empresa.complemento_endereco
    if empresa.email:
        payload['email'] = empresa.email

    cnpj = _digits(empresa.cnpj or '')
    if len(cnpj) == 14:
        payload['cnpj'] = cnpj

    ie = _ie(empresa.inscricao_estadual or '')
    if ie:
        payload['ie'] = ie

    return payload


class IntegranNotasClient:
    PROD_URL = 'https://api.integranotas.com.br/v1'
    HOM_URL  = 'https://hom-api.integranotas.com.br/v1'
    TIMEOUT  = 60  # seconds — IntegraNota recommends minimum 60s

    def __init__(self, token: str, ambiente: str = '2'):
        self.token = token
        self.base_url = self.PROD_URL if ambiente == '1' else self.HOM_URL

    # ─── Public methods ───────────────────────────────────────────────

    def test_connection(self) -> dict:
        """Testa a conexão e valida o token contra IntegraNotas.
        Retorna dict: {sucesso, codigo_http, mensagem, tempo_ms, ambiente_api}
        """
        import time
        endpoints = ['/nfe/status-sefaz', '/status', '/nfe']
        inicio = time.monotonic()
        last_code = None
        last_body = ''
        for endpoint in endpoints:
            try:
                resp = requests.get(
                    f'{self.base_url}{endpoint}',
                    headers=self._headers(),
                    timeout=10,
                )
                last_code = resp.status_code
                try:
                    last_body = resp.json()
                except Exception:
                    last_body = resp.text[:200]
                tempo_ms = int((time.monotonic() - inicio) * 1000)
                if resp.status_code in (401, 403):
                    return {
                        'sucesso': False,
                        'codigo_http': resp.status_code,
                        'mensagem': f'Token rejeitado pela API (HTTP {resp.status_code}). '
                                    'Verifique se o token corresponde ao ambiente selecionado.',
                        'tempo_ms': tempo_ms,
                        'detalhe': last_body,
                        'ambiente_api': self.base_url,
                    }
                # 200, 404, 405, etc. → auth OK
                return {
                    'sucesso': True,
                    'codigo_http': resp.status_code,
                    'mensagem': f'Token aceito pela API IntegraNotas (HTTP {resp.status_code}).',
                    'tempo_ms': tempo_ms,
                    'detalhe': last_body,
                    'ambiente_api': self.base_url,
                }
            except requests.exceptions.ConnectionError:
                tempo_ms = int((time.monotonic() - inicio) * 1000)
                return {
                    'sucesso': False,
                    'codigo_http': None,
                    'mensagem': f'Sem conexão com {self.base_url}. Verifique a internet ou firewall.',
                    'tempo_ms': tempo_ms,
                    'detalhe': '',
                    'ambiente_api': self.base_url,
                }
            except requests.exceptions.Timeout:
                tempo_ms = int((time.monotonic() - inicio) * 1000)
                return {
                    'sucesso': False,
                    'codigo_http': None,
                    'mensagem': 'Timeout — IntegraNotas não respondeu em 10s.',
                    'tempo_ms': tempo_ms,
                    'detalhe': '',
                    'ambiente_api': self.base_url,
                }
            except Exception as exc:
                continue
        tempo_ms = int((time.monotonic() - inicio) * 1000)
        return {
            'sucesso': False,
            'codigo_http': last_code,
            'mensagem': 'Não foi possível verificar a conexão.',
            'tempo_ms': tempo_ms,
            'detalhe': str(last_body),
            'ambiente_api': self.base_url,
        }

    def emitir_nfe(self, nf) -> dict:
        """Submit NF-e to IntegraNota. Returns API response dict."""
        if not nf.numero:
            self._atribuir_numero(nf)
        payload = self._build_payload(nf)
        import json as _json
        logger.info('IntegraNota: emitindo NF %s/%s — tipo_op=%s finalidade=%s cfop_nf=%s',
                    nf.numero, nf.serie,
                    payload.get('tipo_operacao'), payload.get('finalidade_emissao'),
                    nf.cfop)
        logger.info('IntegraNota payload frete.transportadora: %s', payload.get('frete', {}).get('transportadora'))
        for _it in payload.get('itens', []):
            if _it.get('unidade_tributavel'):
                logger.info('IntegraNota item %s: uTrib=%s qTrib=%s', _it.get('numero_item'), _it.get('unidade_tributavel'), _it.get('quantidade_tributavel'))
            if _it.get('declaracao_importacao'):
                logger.info(
                    'IntegraNota item %s: DI PRESENTE cfop=%s origem=%s '
                    'declaracao_importacao=%s declaracoes_importacao=%s di=%s',
                    _it.get('numero_item'), _it.get('cfop'), _it.get('origem'),
                    _json.dumps(_it.get('declaracao_importacao'), ensure_ascii=False),
                    _json.dumps(_it.get('declaracoes_importacao'), ensure_ascii=False),
                    _json.dumps(_it.get('di'), ensure_ascii=False),
                )
        resp = requests.post(
            f'{self.base_url}/nfe',
            json=payload,
            headers=self._headers(),
            timeout=self.TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        logger.info('IntegraNota resposta NF %s/%s: codigo=%s sucesso=%s mensagem=%s erros=%s',
                    nf.numero, nf.serie,
                    data.get('codigo'), data.get('sucesso'),
                    data.get('mensagem', ''),
                    data.get('erros', []))
        if not data.get('sucesso') and data.get('codigo') not in (100, 5023):
            raise IntegranNotasError(
                data.get('mensagem', 'Erro desconhecido na emissão'),
                codigo=data.get('codigo'),
                erros=data.get('erros', []),
            )
        return data

    def consultar_nfe(self, chave: str) -> dict:
        """Query NF-e status by chave de acesso (44 chars)."""
        resp = requests.get(
            f'{self.base_url}/nfe/{chave}',
            headers=self._headers(),
            timeout=self.TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()

    def cancelar_nfe(self, chave: str, justificativa: str) -> dict:
        """Cancel an authorized NF-e. justificativa: 15–255 chars."""
        resp = requests.post(
            f'{self.base_url}/nfe/{chave}/cancela',
            json={'justificativa': justificativa},
            headers=self._headers(),
            timeout=self.TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get('sucesso') and data.get('codigo') != 101:
            raise IntegranNotasError(
                data.get('mensagem', 'Erro ao cancelar NF-e'),
                codigo=data.get('codigo'),
                erros=data.get('erros', []),
            )
        return data

    def carta_correcao_nfe(self, chave: str, correcao: str, sequencia: int = 1) -> dict:
        """Envia Carta de Correção (CC-e) para NF-e autorizada."""
        resp = requests.post(
            f'{self.base_url}/nfe/correcao',
            json={'chave': chave, 'justificativa': correcao},
            headers=self._headers(),
            timeout=self.TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get('sucesso'):
            raise IntegranNotasError(
                data.get('mensagem', 'Erro ao enviar carta de correção'),
                codigo=data.get('codigo'),
                erros=data.get('erros', []),
            )
        return data

    def buscar_xml_cce_nfe(self, chave: str, sequencia: int) -> str | None:
        """Busca o XML base64 de uma CC-e já emitida consultando a NF-e na API.
        Retorna a string base64 ou None se não encontrado."""
        resp = requests.get(
            f'{self.base_url}/nfe/{chave}',
            headers=self._headers(),
            timeout=self.TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        # Procura em listas de eventos/cartas de correção na resposta
        for key in ('cartas_correcao', 'eventos', 'cce', 'correcoes'):
            lista = data.get(key) or []
            for item in lista:
                seq = item.get('sequencia') or item.get('seq')
                if str(seq) == str(sequencia):
                    for xml_key in ('xml', 'xml_cce', 'xml_carta_correcao', 'xmlRetorno'):
                        xml_b64 = item.get(xml_key)
                        if xml_b64:
                            return xml_b64
        # Fallback: XML direto da CC-e se houver somente uma
        for xml_key in ('xml_carta_correcao', 'xml_cce'):
            xml_b64 = data.get(xml_key)
            if xml_b64:
                return xml_b64
        return None

    def inutilizar_nfe(self, cnpj: str, serie: int, numero_ini: int, numero_fim: int,
                       justificativa: str, ano: int) -> dict:
        """Inutiliza intervalo de numeração de NF-e."""
        resp = requests.post(
            f'{self.base_url}/nfe/inutiliza',
            json={
                'cnpj': cnpj,
                'serie': serie,
                'numero_ini': numero_ini,
                'numero_fim': numero_fim,
                'justificativa': justificativa,
                'ano': ano,
            },
            headers=self._headers(),
            timeout=self.TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get('sucesso'):
            raise IntegranNotasError(
                data.get('mensagem', 'Erro ao inutilizar numeração'),
                codigo=data.get('codigo'),
                erros=data.get('erros', []),
            )
        return data

    def manifestar_nfe(self, chave: str, tipo: str, justificativa: str = '') -> dict:
        """Registra Manifestação do Destinatário (MD-e) na SEFAZ."""
        payload: dict = {'chave': chave, 'tipo': tipo}
        if justificativa:
            payload['justificativa'] = justificativa
        resp = requests.post(
            f'{self.base_url}/nfe/manifesta',
            json=payload,
            headers=self._headers(),
            timeout=self.TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get('sucesso'):
            raise IntegranNotasError(
                data.get('mensagem', 'Erro ao registrar manifestação'),
                codigo=data.get('codigo'),
                erros=data.get('erros', []),
            )
        return data

    def enviar_certificado(self, certificado_b64: str, senha: str) -> dict:
        """Envia o certificado digital A1 (base64) para ser configurado no emitente.
        Docs: POST /v1/certificado — requer token do emitente."""
        resp = requests.post(
            f'{self.base_url}/certificado',
            json={'certificado': certificado_b64, 'senha': senha},
            headers=self._headers(),
            timeout=self.TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get('sucesso'):
            raise IntegranNotasError(
                data.get('mensagem', 'Erro ao enviar certificado'),
                codigo=data.get('codigo'),
                erros=data.get('erros', []),
            )
        return data

    def consultar_certificado(self) -> dict:
        """Busca os dados do certificado digital configurado no emitente.
        Docs: GET /v1/certificado — requer token do emitente."""
        resp = requests.get(
            f'{self.base_url}/certificado',
            headers=self._headers(),
            timeout=self.TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()

    def criar_emitente_softhouse(self, dados: dict) -> dict:
        """Cria um novo emitente (empresa) via API de Softhouse. A resposta
        traz o token individual do emitente recém-criado — instanciar este
        client com o token da softhouse (ConfiguracaoPlataforma), não o de
        um emitente específico.
        Docs: POST /v1/soft/emitente"""
        resp = requests.post(
            f'{self.base_url}/soft/emitente',
            json=dados,
            headers=self._headers(),
            timeout=self.TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get('sucesso'):
            raise IntegranNotasError(
                data.get('mensagem', 'Erro ao criar emitente'),
                codigo=data.get('codigo'),
                erros=data.get('erros', []),
            )
        return data

    # ─── Private helpers ──────────────────────────────────────────────

    def _atribuir_numero(self, nf) -> None:
        """Atribui o próximo número sequencial à NF quando ela ainda não tem um."""
        from faturamento.models import NotaFiscal as _NF
        ultimo = (
            _NF.objects.filter(empresa=nf.empresa)
            .exclude(numero__isnull=True)
            .order_by('-numero')
            .values_list('numero', flat=True)
            .first()
        )
        try:
            inicial = int(nf.empresa.configuracao_fiscal.numero_nfe_inicial or 1)
        except Exception:
            inicial = 1
        nf.numero = (ultimo + 1) if ultimo else inicial
        _NF.objects.filter(pk=nf.pk).update(numero=nf.numero)
        logger.info('IntegraNota: número atribuído automaticamente → NF %s', nf.numero)

    def _format_datetime(self, dt) -> str:
        """Formata data/datetime no padrão exigido pela IntegraNotas: 2020-05-16T12:33:20-03:00"""
        from datetime import datetime
        if hasattr(dt, 'hour'):
            # já é datetime
            return dt.strftime('%Y-%m-%dT%H:%M:%S') + '-03:00'
        else:
            # é date — usa hora atual
            now = datetime.now()
            return f"{dt.strftime('%Y-%m-%d')}T{now.strftime('%H:%M:%S')}-03:00"

    def _headers(self):
        return {
            'authorization': self.token,
            'Content-Type': 'application/json',
        }

    def _build_payload(self, nf) -> dict:
        empresa = nf.empresa
        try:
            config = empresa.configuracao_fiscal
        except Exception:
            config = None

        # tipo_operacao: 0=entrada (CFOP 1xxx/2xxx/3xxx), 1=saída
        cfop_str = str(nf.cfop or '5102')
        tipo_operacao = '0' if cfop_str.startswith(('1', '2', '3')) else '1'

        payload: dict = {
            'natureza_operacao': nf.natureza_operacao,
            'serie': str(nf.serie),
            'numero': str(nf.numero),
            'data_emissao': self._format_datetime(nf.data_emissao),
            'tipo_operacao': tipo_operacao,
            'finalidade_emissao': getattr(nf, 'finalidade_nfe', '1') or '1',
            'consumidor_final': '0',
            'presenca_comprador': nf.presenca_comprador or '9',
            'tipo_emissao': str(nf.tipo_emissao or 1),
            'emitente': self._build_emitente(empresa, config),
            'destinatario': (
                self._build_destinatario_fornecedor(nf.fornecedor)
                if nf.fornecedor_id
                else self._build_destinatario(nf.cliente)
            ),
            'itens': [self._build_item(item) for item in nf.itens.all()],
            'totais': self._build_totais(nf),
            'frete': self._build_frete(nf),
            'pagamento': self._build_pagamento(nf),
            'informacoes_adicionais': {
                'informacoes_complementares': nf.informacoes_complementares or '',
                'informacoes_fisco': getattr(nf, 'informacoes_fisco', '') or '',
            },
        }

        # Intermediador (indIntermed / infIntermed) — obrigatório para indPres 2/3/4/9
        ind_intermed = getattr(nf, 'ind_intermediador', '').strip()
        if ind_intermed in ('0', '1'):
            payload['ind_intermediador'] = ind_intermed
            if ind_intermed == '1':
                cnpj_int = _digits(getattr(nf, 'intermediador_cnpj', '') or '')
                id_cad   = (getattr(nf, 'intermediador_id_cadastro', '') or '').strip()
                payload['intermediador'] = {
                    'cnpj':       cnpj_int,
                    'id_cadastro': id_cad,
                }

        # Exportação — grupo ZA da NF-e (<exporta>) — obrigatório para CFOP 7xxx.
        # NÃO incluir para CFOP 3xxx (devolução/entrada do exterior): SEFAZ rejeita
        # <exporta> em NF-e de entrada (tipo_operacao=0).
        uf_embarque    = getattr(nf, 'embarque_uf', '').strip().upper()
        local_embarque = getattr(nf, 'embarque_local', '').strip()
        local_despacho = getattr(nf, 'embarque_local_despacho', '').strip()
        if (uf_embarque or local_embarque) and cfop_str.startswith('7'):
            exporta: dict = {}
            if uf_embarque:
                exporta['uf_local_embarque'] = uf_embarque
            if local_embarque:
                exporta['local_embarque'] = local_embarque
            if local_despacho:
                exporta['local_despacho'] = local_despacho
            payload['exportacao'] = exporta

        # Local de Entrega — grupo G da NF-e (endereço diferente do destinatário)
        if getattr(nf, 'entrega_ativo', False):
            doc_entrega = _digits(nf.entrega_cnpj_cpf or '')
            entrega_block: dict = {
                'logradouro':       nf.entrega_logradouro or '',
                'numero':           nf.entrega_numero or 'S/N',
                'complemento':      nf.entrega_complemento or '',
                'bairro':           nf.entrega_bairro or '',
                'codigo_municipio': nf.entrega_codigo_municipio or '',
                'nome_municipio':   nf.entrega_nome_municipio or '',
                'uf':               nf.entrega_uf or '',
            }
            if len(doc_entrega) == 14:
                entrega_block['cnpj'] = doc_entrega
            elif len(doc_entrega) == 11:
                entrega_block['cpf'] = doc_entrega
            payload['local_entrega'] = entrega_block

        # Local de Retirada — grupo F da NF-e (endereço diferente do destinatário)
        if getattr(nf, 'retirada_ativo', False):
            doc_retirada = _digits(nf.retirada_cnpj_cpf or '')
            retirada_block: dict = {
                'logradouro':       nf.retirada_logradouro or '',
                'numero':           nf.retirada_numero or 'S/N',
                'complemento':      nf.retirada_complemento or '',
                'bairro':           nf.retirada_bairro or '',
                'codigo_municipio': nf.retirada_codigo_municipio or '',
                'nome_municipio':   nf.retirada_nome_municipio or '',
                'uf':               nf.retirada_uf or '',
            }
            if len(doc_retirada) == 14:
                retirada_block['cnpj'] = doc_retirada
            elif len(doc_retirada) == 11:
                retirada_block['cpf'] = doc_retirada
            payload['local_retirada'] = retirada_block

        # Nota de Produtor Rural — documento de origem referenciado
        pr_uf = (getattr(nf, 'produtor_rural_uf', '') or '').strip().upper()
        pr_numero = (getattr(nf, 'produtor_rural_numero', '') or '').strip()
        if pr_uf and pr_numero:
            pr_cnpj = _digits(getattr(nf, 'produtor_rural_cnpj', '') or '')
            pr_cpf = _digits(getattr(nf, 'produtor_rural_cpf', '') or '')
            pr_block: dict = {
                'uf':     pr_uf,
                'anomes': (getattr(nf, 'produtor_rural_anomes', '') or '').strip(),
                'inscricao_estadual': (getattr(nf, 'produtor_rural_ie', '') or '').strip(),
                'modelo': (getattr(nf, 'produtor_rural_modelo', '') or '').strip(),
                'serie':  (getattr(nf, 'produtor_rural_serie', '') or '').strip(),
                'numero': pr_numero,
            }
            if pr_cnpj:
                pr_block['cnpj'] = pr_cnpj
            elif pr_cpf:
                pr_block['cpf'] = pr_cpf
            payload['nota_produtor_rural'] = pr_block

        # Agropecuário — Guia de Trânsito Animal e Defensivo Agrícola
        agro_block: dict = {}
        gta_tipo = (getattr(nf, 'gta_tipo', '') or '').strip()
        gta_uf = (getattr(nf, 'gta_uf', '') or '').strip().upper()
        gta_numero = (getattr(nf, 'gta_numero', '') or '').strip()
        if gta_tipo and gta_uf and gta_numero:
            agro_block['guia_transito_animal'] = {
                'tipo':   gta_tipo,
                'uf':     gta_uf,
                'serie':  (getattr(nf, 'gta_serie', '') or '').strip(),
                'numero': gta_numero,
            }
        defensivo_receituario = (getattr(nf, 'defensivo_numero_receituario', '') or '').strip()
        defensivo_cpf = _digits(getattr(nf, 'defensivo_cpf_responsavel', '') or '')
        if defensivo_receituario and defensivo_cpf:
            agro_block['defensivo'] = [{
                'numero_receituario': defensivo_receituario,
                'cpf_responsavel':    defensivo_cpf,
            }]
        if agro_block:
            payload['agropecuario'] = agro_block

        # NF-e Referenciada — obrigatória para devolução e para Nota Mãe de agrupamento
        refs = []
        # Prioridade 1: modelo NFeReferenciada (Nota Mãe com N filhas referenciadas)
        for ref in nf.nfes_referenciadas.all():
            chave = (ref.chave_acesso_referenciada or '').strip()
            if len(chave) == 44:
                refs.append({'nfe': {'chave': chave}})
        # Prioridade 2: campo singular (devolução simples ou recebimento de origem)
        if not refs:
            chave_ref = (getattr(nf, 'chave_nfe_referenciada', '') or '').strip()
            if not chave_ref and getattr(nf, 'recebimento_origem_id', None):
                chave_ref = (getattr(nf.recebimento_origem, 'chave_nfe', '') or '').strip()
            if chave_ref and len(chave_ref) == 44:
                refs.append({'nfe': {'chave': chave_ref}})
        if refs:
            payload['notas_referenciadas'] = refs

        # Cobrança (duplicatas)
        duplicatas = list(nf.duplicatas.all()) if hasattr(nf, 'duplicatas') else []
        if duplicatas:
            payload['cobranca'] = {
                'fatura': {
                    'numero': duplicatas[0].numero or str(nf.numero),
                    'valor_original': str(nf.valor_total),
                    'valor_liquido': str(nf.valor_total),
                },
                'duplicatas': [
                    {
                        'numero': d.numero or str(i + 1).zfill(3),
                        'data_vencimento': d.vencimento.strftime('%Y-%m-%d'),
                        'valor': str(d.valor),
                    }
                    for i, d in enumerate(duplicatas)
                ],
            }

        return payload

    def _build_emitente(self, empresa, config) -> dict:
        crt = CRT_MAP.get(getattr(config, 'regime_tributario', 'SIMPLES_NACIONAL'), '1')
        return {
            'cnpj': _digits(empresa.cnpj or ''),
            'nome': empresa.nome,
            'inscricao_estadual': _ie(empresa.inscricao_estadual),
            'crt': crt,
            'endereco': {
                'logradouro': empresa.endereco or '',
                'numero': empresa.numero_endereco or 'S/N',
                'complemento': empresa.complemento_endereco or '',
                'bairro': empresa.bairro or '',
                'codigo_municipio': empresa.codigo_municipio or '',
                'nome_municipio': empresa.cidade or '',
                'uf': empresa.uf or '',
                'cep': _digits(empresa.cep or ''),
                'codigo_pais': '1058',
                'nome_pais': 'Brasil',
                'telefone': _digits(empresa.telefone or ''),
            },
        }

    def _build_destinatario(self, cliente) -> dict:
        doc = _digits(cliente.cnpj_cpf or '')
        pais_cli = (getattr(cliente, 'pais', '') or 'Brasil').strip()
        tipo_cliente = getattr(cliente, 'tipo_cliente', '') or ''
        is_exterior_cliente = (
            tipo_cliente == 'IMPORTADOR'
            or pais_cli.lower() not in ('brasil', '')
        )

        dest: dict = {'nome': cliente.razao_social}

        if is_exterior_cliente:
            # Exterior: usa id_estrangeiro (VAT, EORI ou qualquer ID fiscal do país)
            dest['indicador_inscricao_estadual'] = '9'
            id_ext = (
                getattr(cliente, 'vat', '') or
                getattr(cliente, 'eori', '') or
                doc or
                ''
            ).strip()
            if id_ext:
                dest['id_estrangeiro'] = id_ext
        else:
            dest['indicador_inscricao_estadual'] = cliente.indicador_ie or '9'
            dest['inscricao_estadual'] = cliente.inscricao_estadual or ''
            if len(doc) == 14:
                dest['cnpj'] = doc
            elif len(doc) == 11:
                dest['cpf'] = doc
            else:
                raise IntegranNotasError(
                    f'Destinatário "{cliente.razao_social}" sem CNPJ/CPF válido (14 ou 11 dígitos). '
                    'Corrija o documento no cadastro do cliente.',
                    codigo=None,
                )

        # Address from default EnderecoCliente
        endereco_obj = cliente.enderecos.filter(padrao=True).first()
        if endereco_obj:
            pais_end = (endereco_obj.pais or pais_cli or 'Brasil').strip()
            is_exterior = is_exterior_cliente or pais_end.lower() not in ('brasil', '')

            if is_exterior:
                # Endereço exterior: municipio = 9999999, UF = EX, sem IBGE obrigatório
                codigo_mun = '9999999'
                uf_dest = 'EX'
                nome_pais = pais_end
                # Prioridade: campo codigo_pais do cadastro → mapeamento por nome → erro
                codigo_pais = (getattr(cliente, 'codigo_pais', '') or '').strip()
                if not codigo_pais:
                    codigo_pais = PAIS_IBGE_MAP.get(pais_end.lower().strip(), '')
                if not codigo_pais:
                    raise IntegranNotasError(
                        f'País "{pais_end}" sem código IBGE válido. '
                        'Preencha o campo "Cód. IBGE País" no cadastro do cliente '
                        'ou use um nome reconhecido (ex: "Estados Unidos", "Argentina").',
                        codigo=None,
                    )
            else:
                codigo_mun = (endereco_obj.codigo_municipio or '').strip()
                if not codigo_mun:
                    raise IntegranNotasError(
                        f'Destinatário "{cliente.razao_social}" sem Código IBGE do município. '
                        'Preencha o campo Código IBGE no endereço padrão do cliente antes de emitir.',
                        codigo=None,
                    )
                uf_dest = endereco_obj.uf or ''
                codigo_pais = '1058'
                nome_pais = 'Brasil'

            dest['endereco'] = {
                'logradouro': endereco_obj.logradouro or '',
                'numero': endereco_obj.numero or 'S/N',
                'complemento': endereco_obj.complemento or '',
                'bairro': endereco_obj.bairro or '',
                'codigo_municipio': codigo_mun,
                'nome_municipio': endereco_obj.cidade or '',
                'uf': uf_dest,
                'cep': _digits(endereco_obj.cep or ''),
                'codigo_pais': codigo_pais,
                'nome_pais': nome_pais,
                'telefone': _digits(cliente.contato_principal_telefone or ''),
            }
        return dest

    def _build_destinatario_fornecedor(self, fornecedor) -> dict:
        doc = _digits(fornecedor.cnpj_cpf or '')
        dest: dict = {'nome': fornecedor.nome}

        ie = (fornecedor.inscricao_estadual or '').strip()
        if ie and ie.upper() not in ('ISENTO', 'ISENto', ''):
            dest['indicador_inscricao_estadual'] = '1'
            dest['inscricao_estadual'] = ie
        else:
            dest['indicador_inscricao_estadual'] = '9'
            dest['inscricao_estadual'] = ''

        if len(doc) == 14:
            dest['cnpj'] = doc
        elif len(doc) == 11:
            dest['cpf'] = doc
        else:
            raise IntegranNotasError(
                f'Fornecedor "{fornecedor.nome}" sem CNPJ/CPF válido (14 ou 11 dígitos). '
                'Corrija o documento no cadastro do fornecedor antes de emitir.',
                codigo=None,
            )

        # Tenta endereço padrão de FornecedorEndereco; usa campos diretos como fallback
        end = fornecedor.enderecos.filter(padrao=True).first()
        if end:
            logradouro = end.logradouro or ''
            numero = end.numero or 'S/N'
            complemento = end.complemento or ''
            bairro = end.bairro or ''
            cidade = end.cidade or ''
            uf = end.uf or ''
            cep = _digits(end.cep or '')
            codigo_mun = (end.codigo_municipio or '').strip()
        else:
            logradouro = fornecedor.endereco or ''
            numero = fornecedor.numero or 'S/N'
            complemento = fornecedor.complemento or ''
            bairro = fornecedor.bairro or ''
            cidade = fornecedor.cidade or ''
            uf = fornecedor.uf or ''
            cep = _digits(fornecedor.cep or '')
            codigo_mun = ''

        if not codigo_mun:
            raise IntegranNotasError(
                f'Fornecedor "{fornecedor.nome}" sem Código IBGE do município. '
                'Preencha o campo "Código IBGE" no endereço padrão do fornecedor antes de emitir.',
                codigo=None,
            )

        dest['endereco'] = {
            'logradouro': logradouro,
            'numero': numero,
            'complemento': complemento,
            'bairro': bairro,
            'codigo_municipio': codigo_mun,
            'nome_municipio': cidade,
            'uf': uf,
            'cep': cep,
            'codigo_pais': '1058',
            'nome_pais': 'Brasil',
            'telefone': _digits(fornecedor.telefone or ''),
        }
        return dest

    def _build_item(self, item) -> dict:
        produto_codigo = ''
        if item.produto_id:
            produto_codigo = item.produto.codigo or ''

        item_dict = {
            'numero_item': str(item.numero_item),
            'codigo_produto': produto_codigo or 'SEM CODIGO',
            'codigo_barras_comercial': item.ean or 'SEM GTIN',
            'descricao': item.descricao,
            'codigo_ncm': item.ncm or '',
            'cest': item.cest or '',
            'cfop': item.cfop or '',
            'unidade_comercial': item.unidade or 'UN',
            'quantidade_comercial': str(item.quantidade),
            'valor_unitario_comercial': str(item.valor_unitario),
            'valor_bruto': str(item.valor_total),
            'valor_desconto': str(item.valor_desconto),
            'inclui_no_total': '1',
            'origem': item.origem_mercadoria or '0',
            'imposto': self._build_impostos(item),
        }

        # Benefício Fiscal (cBenef) — campo do item, não de imposto.icms
        cbenefit = (getattr(item, 'beneficio_fiscal', '') or '').strip()
        if cbenefit:
            item_dict['codigo_beneficio_fiscal'] = cbenefit

        # Crédito Presumido de ICMS (item) — benefício estadual comum em commodities agrícolas
        cred_pres_cod = (getattr(item, 'credito_presumido_codigo_beneficio', '') or '').strip()
        cred_pres_pct = float(getattr(item, 'credito_presumido_percentual', 0) or 0)
        if cred_pres_cod and cred_pres_pct > 0:
            item_dict['creditos_presumido'] = [{
                'codigo_beneficio_fiscal': cred_pres_cod,
                'percentual': str(item.credito_presumido_percentual),
                'valor': str(item.credito_presumido_valor),
            }]

        # Rateio por item
        if float(getattr(item, 'valor_frete_item', 0) or 0) > 0:
            item_dict['valor_frete'] = str(item.valor_frete_item)
        if float(getattr(item, 'valor_seguro_item', 0) or 0) > 0:
            item_dict['valor_seguro'] = str(item.valor_seguro_item)
        if float(getattr(item, 'valor_outras_despesas', 0) or 0) > 0:
            item_dict['valor_outras_despesas'] = str(item.valor_outras_despesas)

        # Pedido de Compra
        ped = (getattr(item, 'pedido_compra', '') or '').strip()
        if ped:
            item_dict['pedido_compra'] = ped
            item_ped = (getattr(item, 'item_pedido_compra', '') or '').strip()
            if item_ped:
                item_dict['item_pedido_compra'] = item_ped

        # Informações adicionais do produto (DANFE / infAdProd)
        comp = (getattr(item, 'complemento_descricao', '') or '').strip()
        if comp:
            item_dict['informacoes_adicionais'] = comp[:500]

        # Unidade Tributável — exportação (CFOP 7xxx): qTrib / uTrib / vUnTrib
        # vUnTrib exige até 10 casas decimais no leiaute NF-e (NT 2012/003)
        qtrib = float(getattr(item, 'quantidade_tributavel', 0) or 0)
        if qtrib > 0:
            item_dict['unidade_tributavel']        = getattr(item, 'unidade_tributavel', '') or 'KG'
            item_dict['quantidade_tributavel']     = str(item.quantidade_tributavel)
            item_dict['valor_unitario_tributavel'] = f"{float(item.valor_unitario_tributavel or 0):.10f}"

        # DI — Declaração de Importação (origens 1, 2, 6, 7 ou CFOP 3xxx)
        di = self._build_di(item)
        if di:
            item_dict['documentos_importacao'] = [di]
            # IntegraNotas só gera <DI> no XML quando origem indica produto estrangeiro.
            # Para CFOP 3xxx com DI obrigatória (ex.: devolução drawback), forçamos
            # origem='1' no payload — apenas para a API, sem alterar o banco de dados.
            if item_dict.get('origem') == '0':
                item_dict['origem'] = '1'

        # Documentos de Exportação — drawback / exportação indireta (separado da DI)
        doc_exp = self._build_documento_exportacao(item)
        if doc_exp:
            item_dict['documentos_exportacao'] = [doc_exp]

        # Rastros — rastreabilidade de lote (numero_lote/quantidade/validade)
        rastro = self._build_rastro(item)
        if rastro:
            item_dict['rastros'] = [rastro]

        # DFeReferenciado — referenciamento por item, obrigatório em devolução
        # de mercadoria (finNFe=4) a partir de 01/09/2026 (NT 2025.002-RTC
        # v1.50, regra VC02-14), em substituição ao NFref de cabeçalho.
        chave_ref_item = (getattr(item, 'dfe_ref_chave_acesso', '') or '').strip()
        if chave_ref_item:
            dfe_ref = {'chave': chave_ref_item}
            nitem_ref = getattr(item, 'dfe_ref_nitem', None)
            if nitem_ref:
                dfe_ref['numero_item'] = str(nitem_ref)
            item_dict['dfe_referenciado'] = dfe_ref

        return item_dict

    def _build_di(self, item) -> dict | None:
        """Constrói o bloco DI (documentos_importacao) para item importado ou CFOP 3xxx."""
        cfop = str(getattr(item, 'cfop', '') or '').strip()
        origem = item.origem_mercadoria
        precisa_di = (origem in ('1', '2', '6', '7')) or cfop.startswith('3')
        if not precisa_di:
            return None
        numero = (getattr(item, 'di_numero', '') or '').strip()
        if not numero:
            return None  # DI não informada — campos obrigatórios não preenchidos

        # SEFAZ schema nDI: máximo 10 dígitos.
        # Para retorno de exportação/drawback sem DI real, convenção SEFAZ é '0000000000'.
        # Se o número informado ultrapassar 10 chars, truncamos com aviso.
        numero_digits = re.sub(r'\D', '', numero)
        if len(numero_digits) > 10:
            logger.warning('DI nDI "%s" tem %d dígitos (max 10) — truncando para 10', numero, len(numero_digits))
            numero_digits = numero_digits[:10]
        numero = numero_digits or numero[:10]

        di: dict = {
            'numero':                       numero,
            'data_registro':                item.di_data_registro.strftime('%Y-%m-%d') if item.di_data_registro else '',
            'local_desembaraco_aduaneiro':  (item.di_local_desembaraco or '').strip(),
            'uf_desembaraco_aduaneiro':     (item.di_uf_desembaraco or '').strip().upper(),
            'data_desembaraco_aduaneiro':   item.di_data_desembaraco.strftime('%Y-%m-%d') if item.di_data_desembaraco else '',
            'via_transporte':               (item.di_via_transporte or '').strip(),
            'forma_intermedio':             (item.di_tipo_intermediario or '1').strip(),
            'codigo_exportador':            (item.di_codigo_exportador or '').strip(),
        }

        # AFRMM só para via marítima (via = 1)
        if item.di_via_transporte == '1':
            di['valor_afrmm'] = str(item.di_valor_afrmm or '0.00')

        # CNPJ/CPF do adquirente/encomendante quando forma_intermedio = 2 ou 3
        doc_adq = _digits(item.di_cnpj_adquirente or '')
        if item.di_tipo_intermediario in ('2', '3') and doc_adq:
            di['cnpj' if len(doc_adq) == 14 else 'cpf'] = doc_adq

        # Adição da DI
        num_adicao = (item.di_numero_adicao or '1').strip() or '1'
        adicao: dict = {
            'numero_adicao':    num_adicao,
            'sequencia_item':   '1',
            'codigo_fabricante': (item.di_codigo_fabricante or '').strip(),
        }
        desconto_adi = float(item.di_desconto_adicao or 0)
        if desconto_adi > 0:
            adicao['valor_desconto'] = str(item.di_desconto_adicao)

        di['adicoes'] = [adicao]

        # Garante que todos os campos obrigatórios da DI estão preenchidos.
        # Campos vazios causam rejeição silenciosa no IntegraNotas.
        campos_obrig = ['data_registro', 'local_desembaraco_aduaneiro', 'uf_desembaraco_aduaneiro',
                        'data_desembaraco_aduaneiro', 'via_transporte']
        if any(not di.get(c) for c in campos_obrig):
            return None

        return di

    def _build_documento_exportacao(self, item) -> dict | None:
        """Constrói documentos_exportacao (drawback / exportação indireta) — bloco
        independente da DI, conforme schema da IntegraNotas."""
        drawback = (getattr(item, 'di_numero_drawback', '') or '').strip()
        numero_re = (getattr(item, 'exportacao_indireta_numero_re', '') or '').strip()
        chave_nfe_exp = (getattr(item, 'exportacao_indireta_chave_nfe', '') or '').strip()
        if not drawback and not (numero_re and chave_nfe_exp):
            return None

        doc: dict = {}
        if drawback:
            # SEFAZ schema nDraw: [0-9]{11} — exatamente 11 dígitos
            digs_dw = re.sub(r'\D', '', drawback)
            if len(digs_dw) == 11:
                doc['numero_drawback'] = digs_dw
            else:
                logger.warning('Drawback "%s" ignorado — deve ter 11 dígitos (tem %d)', drawback, len(digs_dw))

        if numero_re and chave_nfe_exp and len(chave_nfe_exp) == 44:
            quantidade_exp = getattr(item, 'exportacao_indireta_quantidade', 0) or item.quantidade
            doc['exportacao_indireta'] = {
                'numero_re': numero_re,
                'chave_nfe': chave_nfe_exp,
                'quantidade': str(quantidade_exp),
            }

        return doc or None

    def _build_rastro(self, item) -> dict | None:
        """Constrói rastros[] (rastreabilidade de lote) a partir de ItemNotaFiscal.lote."""
        lote = getattr(item, 'lote', None)
        if not lote or not lote.data_fabricacao or not lote.data_validade:
            return None
        return {
            'numero_lote':      lote.numero_lote,
            'quantidade_lote':  str(item.quantidade),
            'data_fabricacao':  lote.data_fabricacao.strftime('%Y-%m-%d'),
            'data_validade':    lote.data_validade.strftime('%Y-%m-%d'),
        }

    def _build_impostos(self, item) -> dict:
        impostos: dict = {}

        # ICMS
        cst_icms = item.cst_icms or '40'
        modalidade_bc = getattr(item, 'icms_modalidade_base', '3') or '3'
        reducao_bc = float(getattr(item, 'icms_reducao_base', 0) or 0)

        icms_block: dict = {'situacao_tributaria': cst_icms}

        # CST 40/41 (isenta/não tributada) usam o grupo ICMS40 da NF-e, que não
        # tem modBC/vBC/pICMS/vICMS — só CST + desoneração opcional. Gate por
        # CST (não só por alíquota>0) para nunca enviar esse grupo nesses CSTs,
        # mesmo que aliquota_icms guarde um valor residual/hipotético.
        if _item_tem_vbc_icms(item):
            icms_block.update({
                'modalidade_base_calculo': modalidade_bc,
                'valor_base_calculo': str(item.icms_base_calculo),
                'aliquota': str(item.aliquota_icms),
                'valor': str(item.valor_icms),
            })
            if reducao_bc > 0:
                icms_block['aliquota_reducao_base_calculo'] = str(reducao_bc)

        # Diferimento ICMS (CST 51) — nomes de campo a confirmar contra o
        # schema real da IntegraNotas antes de emitir em produção.
        pdif_icms = float(getattr(item, 'icms_percentual_diferimento', 0) or 0)
        if cst_icms == '51' and pdif_icms > 0:
            icms_block['percentual_diferimento'] = str(pdif_icms)
            icms_block['valor_icms_diferido'] = str(getattr(item, 'icms_valor_diferido', 0) or 0)

        # Desoneração ICMS
        motivo_deson = (getattr(item, 'icms_motivo_desoneracao', '') or '').strip()
        valor_deson  = float(getattr(item, 'icms_valor_desoneracao', 0) or 0)
        if motivo_deson and valor_deson > 0:
            icms_block['motivo_desoneracao'] = motivo_deson
            icms_block['valor_desonerado']   = str(item.icms_valor_desoneracao)

        # ICMS ST (CST 10, 30, 70, 90 etc.)
        valor_st = float(getattr(item, 'valor_icms_st', 0) or 0)
        if valor_st > 0:
            mva    = float(getattr(item, 'icms_st_mva', 0) or 0)
            red_st = float(getattr(item, 'icms_st_reducao_base', 0) or 0)
            aliq_st = float(getattr(item, 'icms_st_aliquota', 0) or 0)
            bc_st  = float(getattr(item, 'icms_st_base_calculo', 0) or 0)
            icms_block.update({
                'modalidade_base_calculo_st': '4',
                'aliquota_margem_valor_adicionado_st': str(mva),
                'aliquota_reducao_base_calculo_st': str(red_st),
                'valor_base_calculo_st': str(bc_st),
                'aliquota_st': str(aliq_st),
                'valor_st': str(valor_st),
            })

        impostos['icms'] = icms_block

        # FCP normal e FCP-ST — mesmo objeto imposto.fcp, campos independentes
        # (FCP-ST pode existir sem FCP normal e vice-versa)
        fcp_aliq    = float(getattr(item, 'fcp_aliquota', 0) or 0)
        fcp_st_aliq = float(getattr(item, 'fcp_st_aliquota', 0) or 0)
        if fcp_aliq > 0 or fcp_st_aliq > 0:
            fcp_block: dict = {}
            if fcp_aliq > 0:
                fcp_block.update({
                    'valor_base_calculo': str(item.fcp_base_calculo),
                    'aliquota':           str(item.fcp_aliquota),
                    'valor':              str(item.fcp_valor),
                })
            if fcp_st_aliq > 0:
                fcp_block.update({
                    'valor_base_calculo_st': str(item.fcp_st_base_calculo),
                    'aliquota_st':           str(item.fcp_st_aliquota),
                    'valor_st':              str(item.fcp_st_valor),
                })
            impostos['fcp'] = fcp_block

        # IPI
        # Omite bloco IPI quando alíquota = 0 — o grupo é opcional na NF-e.
        # Enviar IPI com apenas 'valor: 0.00' causa erro na API IntegraNotas;
        # enviar CST 52-55 + enquadramento 999 causa rejeição SEFAZ 388.
        _ipi_aliq = item.aliquota_ipi and float(item.aliquota_ipi) > 0
        if _ipi_aliq:
            cst_ipi = getattr(item, 'cst_ipi', '') or '50'
            impostos['ipi'] = {
                'situacao_tributaria': cst_ipi,
                'codigo_enquadramento_legal': item.ipi_codigo_enquadramento or '999',
                'valor_base_calculo': str(item.valor_total),
                'aliquota': str(item.aliquota_ipi),
                'valor': str(item.valor_ipi),
            }
            # CNPJProd — CNPJ do produtor, quando diferente do emitente
            # (exportação direta/indireta). Bloco inteiro segue omitido para
            # CST 53/55 (alíquota=0), então isto só entra em vigor se o grupo
            # IPI voltar a ser enviado com alíquota diferente de zero.
            cnpj_produtor = (getattr(item, 'ipi_cnpj_produtor', '') or '').strip()
            if cnpj_produtor:
                impostos['ipi']['cnpj_produtor'] = cnpj_produtor

        # PIS — "valor" é sempre obrigatório no schema da IntegraNotas; os
        # demais campos dependem do grupo (Aliq x Qtde) conforme o CST.
        cst_pis = item.cst_pis or '07'
        pis_block: dict = {
            'situacao_tributaria': cst_pis,
            'valor': str(item.valor_pis),
        }
        if cst_pis in CST_PIS_COFINS_ALIQ and item.aliquota_pis and float(item.aliquota_pis) > 0:
            # IntegraNotas aceita no máximo 4 casas decimais para aliquota
            _aliq_pis = f"{float(item.aliquota_pis):.4f}".rstrip('0').rstrip('.')
            pis_block['valor_base_calculo'] = str(item.pis_base_calculo)
            pis_block['aliquota'] = _aliq_pis
        if cst_pis in CST_PIS_COFINS_QTD and item.pis_aliquota_valor and float(item.pis_aliquota_valor) > 0:
            _aliqv_pis = f"{float(item.pis_aliquota_valor):.4f}".rstrip('0').rstrip('.')
            pis_block['quantidade_vendida'] = str(item.quantidade)
            pis_block['aliquota_valor'] = _aliqv_pis
        impostos['pis'] = pis_block

        # COFINS — mesmo critério do PIS.
        cst_cofins = item.cst_cofins or '07'
        cofins_block: dict = {
            'situacao_tributaria': cst_cofins,
            'valor': str(item.valor_cofins),
        }
        if cst_cofins in CST_PIS_COFINS_ALIQ and item.aliquota_cofins and float(item.aliquota_cofins) > 0:
            # IntegraNotas aceita no máximo 4 casas decimais para aliquota
            _aliq_cofins = f"{float(item.aliquota_cofins):.4f}".rstrip('0').rstrip('.')
            cofins_block['valor_base_calculo'] = str(item.cofins_base_calculo)
            cofins_block['aliquota'] = _aliq_cofins
        if cst_cofins in CST_PIS_COFINS_QTD and item.cofins_aliquota_valor and float(item.cofins_aliquota_valor) > 0:
            _aliqv_cofins = f"{float(item.cofins_aliquota_valor):.4f}".rstrip('0').rstrip('.')
            cofins_block['quantidade_vendida'] = str(item.quantidade)
            cofins_block['aliquota_valor'] = _aliqv_cofins
        impostos['cofins'] = cofins_block

        # IBS/CBS — Reforma Tributária (NT 2024/2025, grupo_ibs_cbs). Estrutura
        # conforme o schema real do endpoint /nfe da IntegraNotas: percentual_reducao,
        # aliquota_reducao_base_calculo_efetiva, percentual_diferimento e
        # valor_diferimento ficam DENTRO de cada bloco (ibs_estadual/ibs_municipal/
        # cbs) — não em grupos "reducao_ibs"/"reducao_cbs"/"diferimento_ibs"/
        # "diferimento_cbs" à parte. Não existe grupo de crédito presumido dentro
        # de ibs_cbs no schema real (removido pela própria NT) — não enviar.
        cst_reforma = (getattr(item, 'ibs_cbs_situacao_tributaria', '') or '').strip()
        if cst_reforma:
            cclasstrib = (getattr(item, 'ibs_cbs_classificacao_tributaria', '') or '').strip()

            def _bloco_tributo(aliquota, percentual_reducao, valor, percentual_diferimento=0, valor_diferimento=0):
                bloco = {'aliquota': str(aliquota), 'valor': str(valor)}
                pred = float(percentual_reducao or 0)
                if pred > 0:
                    aliq_efet = float(aliquota or 0) * (1 - pred / 100)
                    bloco['percentual_reducao'] = str(percentual_reducao)
                    bloco['aliquota_reducao_base_calculo_efetiva'] = f'{aliq_efet:.4f}'
                pdif = float(percentual_diferimento or 0)
                if pdif > 0:
                    bloco['percentual_diferimento'] = str(percentual_diferimento)
                    bloco['valor_diferimento'] = str(valor_diferimento or 0)
                return bloco

            # O model só guarda UM percentual/valor de diferimento combinado para
            # IBS (UF + Município juntos) — rateado aqui proporcionalmente ao
            # valor de cada competência, já que o schema exige os dois separados.
            pdif_ibs = float(getattr(item, 'ibs_percentual_diferimento', 0) or 0)
            valor_dif_uf = valor_dif_mun = 0
            if pdif_ibs > 0:
                valor_dif_uf = float(item.ibs_cbs_valor_uf or 0) * pdif_ibs / 100
                valor_dif_mun = float(item.ibs_cbs_valor_municipal or 0) * pdif_ibs / 100

            valor_total_ibs = float(item.ibs_cbs_valor_uf or 0) + float(item.ibs_cbs_valor_municipal or 0)

            impostos['ibs_cbs'] = {
                'situacao_tributaria': cst_reforma,
                'classificacao_tributaria': cclasstrib,
                'grupo_ibs_cbs': {
                    'valor_base_calculo': str(item.ibs_cbs_base_calculo),
                    'valor_total_ibs': str(valor_total_ibs),
                    'ibs_estadual': _bloco_tributo(
                        item.ibs_cbs_aliquota_uf, item.ibs_percentual_reducao, item.ibs_cbs_valor_uf,
                        pdif_ibs, valor_dif_uf),
                    'ibs_municipal': _bloco_tributo(
                        item.ibs_cbs_aliquota_municipal, item.ibs_percentual_reducao, item.ibs_cbs_valor_municipal,
                        pdif_ibs, valor_dif_mun),
                    'cbs': _bloco_tributo(
                        item.ibs_cbs_aliquota_cbs, item.cbs_percentual_reducao, item.ibs_cbs_valor_cbs,
                        item.cbs_percentual_diferimento, item.cbs_valor_diferido),
                },
            }

        return impostos

    def _build_totais(self, nf) -> dict:
        itens = list(nf.itens.all())
        return {
            # Soma só os itens que efetivamente declaram vBC no XML (mesmo gate
            # de _build_impostos) — itens CST 40/41 ou sem alíquota não entram,
            # senão o total diverge do somatório real e a SEFAZ rejeita (erro 531).
            'icms_base_calculo': str(sum(
                i.icms_base_calculo for i in itens if _item_tem_vbc_icms(i)
            )),
            'icms_valor_total': str(nf.valor_icms),
            'icms_st_valor_total': str(getattr(nf, 'valor_icms_st', 0) or 0),
            'icms_st_base_calculo': str(sum(getattr(i, 'icms_st_base_calculo', 0) or 0 for i in itens)),
            'ipi_valor_total': str(nf.valor_ipi),
            'pis_valor_total': str(nf.valor_pis),
            'cofins_valor_total': str(nf.valor_cofins),
            'valor_produtos_total': str(nf.valor_produtos),
            'valor_frete_total': str(nf.valor_frete),
            'valor_seguro_total': str(nf.valor_seguro),
            'valor_desconto_total': str(nf.valor_desconto),
            'valor_total': str(nf.valor_total),
        }

    def _build_frete(self, nf) -> dict:
        mod = MODALIDADE_FRETE_MAP.get(nf.modalidade_frete, '9')
        frete: dict = {'modalidade_frete': mod}

        # Lê campos transp_* da NF; fallback campo-a-campo do FK de transportadora
        t = nf.transportadora if nf.transportadora_id else None
        cnpj      = _digits(nf.transp_cnpj or '') or (t and _digits(t.cnpj or '') or '')
        nome      = (nf.transp_nome or '').strip() or (t.razao_social if t else '')
        ie        = (nf.transp_ie or '').strip() or (t.inscricao_estadual if t else '')
        endereco  = (nf.transp_endereco or '').strip() or (
            ' '.join(filter(None, [t.logradouro, t.numero, t.complemento])).strip() if t else '')
        municipio = (nf.transp_municipio or '').strip() or (t.cidade if t else '')
        uf        = (nf.transp_uf or '').strip().upper() or ((t.uf or '').upper() if t else '')
        rntc      = (nf.transp_rntc or '').strip() or (t.rntc if t else '')

        if cnpj or nome:
            transp_data = {}
            # IntegraNotas strips <transporta> when carrier CNPJ root matches emitter root.
            # Omit CNPJ in that case so IntegraNotas includes <xNome> without triggering the check.
            emit_cnpj = _digits(getattr(nf.empresa, 'cnpj', '') or '')
            cnpj_raiz_igual = bool(cnpj and emit_cnpj and cnpj[:8] == emit_cnpj[:8])
            if cnpj and not cnpj_raiz_igual:
                transp_data['cnpj' if len(cnpj) == 14 else 'cpf'] = cnpj
            if nome:       transp_data['nome']             = nome[:60]
            if ie:         transp_data['inscricao_estadual'] = ie
            if endereco:   transp_data['endereco']         = endereco[:60]
            if municipio:  transp_data['nome_municipio']   = municipio[:60]
            if uf:         transp_data['uf']               = uf
            if transp_data:
                frete['transportador'] = transp_data

        if nf.veic_placa:
            frete['veiculo'] = {
                'placa': nf.veic_placa.upper(),
                'uf':    (nf.veic_uf or '').upper(),
            }
            if rntc:
                frete['veiculo']['rntc'] = rntc

        if any([nf.quantidade_volumes, nf.especie_volumes, nf.marca_volumes,
                nf.numeracao_volumes, nf.peso_bruto_kg, nf.peso_liquido_kg]):
            vol: dict = {}
            if nf.quantidade_volumes: vol['quantidade']   = nf.quantidade_volumes
            if nf.especie_volumes:    vol['especie']      = nf.especie_volumes
            if nf.marca_volumes:      vol['marca']        = nf.marca_volumes
            if nf.numeracao_volumes:  vol['numero']       = nf.numeracao_volumes
            if nf.peso_liquido_kg:    vol['peso_liquido'] = str(nf.peso_liquido_kg)
            if nf.peso_bruto_kg:      vol['peso_bruto']   = str(nf.peso_bruto_kg)
            frete['volumes'] = [vol]

        return frete

    def _build_pagamento(self, nf) -> dict:
        pagamentos = list(nf.pagamentos.all())
        if pagamentos:
            return {
                'formas_pagamento': [
                    {'meio_pagamento': p.meio_pagamento, 'valor': str(p.valor)}
                    for p in pagamentos
                ]
            }
        return {
            'formas_pagamento': [{'meio_pagamento': '90', 'valor': str(nf.valor_total)}]
        }

    # ─── CT-e ─────────────────────────────────────────────────────

    def emitir_cte(self, ct) -> dict:
        """Submit CT-e to IntegraNotas. Returns API response dict."""
        payload = self._build_cte_payload(ct)
        logger.info('IntegraNotas: emitindo CT-e %s/%s', ct.numero, ct.serie)
        resp = requests.post(
            f'{self.base_url}/cte',
            json=payload,
            headers=self._headers(),
            timeout=self.TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get('sucesso') and data.get('codigo') not in (100, 5023):
            raise IntegranNotasError(
                data.get('mensagem', 'Erro desconhecido na emissão do CT-e'),
                codigo=data.get('codigo'),
                erros=data.get('erros', []),
            )
        return data

    def consultar_cte(self, chave: str) -> dict:
        resp = requests.get(f'{self.base_url}/cte/{chave}', headers=self._headers(), timeout=self.TIMEOUT)
        resp.raise_for_status()
        return resp.json()

    def cancelar_cte(self, chave: str, justificativa: str) -> dict:
        resp = requests.post(
            f'{self.base_url}/cte/cancela',
            json={'chave': chave, 'justificativa': justificativa},
            headers=self._headers(),
            timeout=self.TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get('sucesso') and data.get('codigo') != 101:
            raise IntegranNotasError(
                data.get('mensagem', 'Erro ao cancelar CT-e'),
                codigo=data.get('codigo'),
                erros=data.get('erros', []),
            )
        return data

    def dacte(self, chave: str) -> dict:
        resp = requests.get(f'{self.base_url}/cte/pdf', params={'chave': chave}, headers=self._headers(), timeout=self.TIMEOUT)
        resp.raise_for_status()
        return resp.json()

    def correcao_cte(self, chave: str, correcoes: list, sequencia: int | None = None) -> dict:
        """Envia Carta de Correção (CC-e) para CT-e autorizado com estrutura de múltiplas correções.

        Args:
            chave: Chave de acesso do CT-e
            correcoes: Lista de dicts com: grupo_corrigido, campo_corrigido, valor_corrigido, indice_item (opcional)
            sequencia: Sequencial opcional (gerenciado automaticamente pela API se não informado)

        Exemplo:
            correcoes = [
                {
                    'grupo_corrigido': 'ide',
                    'campo_corrigido': 'natOp',
                    'valor_corrigido': 'PRESTACAO DE SERVIÇO'
                }
            ]
        """
        payload = {'chave': chave, 'correcoes': correcoes}
        if sequencia is not None:
            payload['sequencia'] = sequencia

        resp = requests.post(
            f'{self.base_url}/cte/correcao',
            json=payload,
            headers=self._headers(),
            timeout=self.TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get('sucesso'):
            raise IntegranNotasError(
                data.get('mensagem', 'Erro ao enviar carta de correção'),
                codigo=data.get('codigo'),
                erros=data.get('erros', []),
            )
        return data

    def carta_correcao_cte(self, chave: str, correcao: str, sequencia: int | None = None) -> dict:
        """DEPRECATED: Use correcao_cte com estrutura de múltiplas correções.
        Mantido para compatibilidade com código legado.
        """
        correcoes = [{'campo_corrigido': 'observacao', 'valor_corrigido': correcao}]
        return self.correcao_cte(chave, correcoes, sequencia)

    def manifesta_desacordo_cte(self, chave: str, descricao: str) -> dict:
        """Registra Manifestação de Desacordo no CT-e (código 7 = desacordo)."""
        resp = requests.post(
            f'{self.base_url}/cte/manifesta',
            json={'chave': chave, 'codigo': '7', 'descricao': descricao},
            headers=self._headers(),
            timeout=self.TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get('sucesso'):
            raise IntegranNotasError(
                data.get('mensagem', 'Erro ao registrar desacordo'),
                codigo=data.get('codigo'),
                erros=data.get('erros', []),
            )
        return data

    def insucesso_entrega_cte(self, chave: str, payload: dict) -> dict:
        """Registra Insucesso na Entrega da Carga no CT-e (evento SEFAZ 610410)."""
        resp = requests.post(
            f'{self.base_url}/cte/insucesso-entrega',
            json={'chave': chave, **payload},
            headers=self._headers(),
            timeout=self.TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get('sucesso'):
            raise IntegranNotasError(
                data.get('mensagem', 'Erro ao registrar insucesso na entrega'),
                codigo=data.get('codigo'),
                erros=data.get('erros', []),
            )
        return data

    def preview_cte(self, chave: str) -> dict:
        """Retorna o PDF preview do CT-e (antes ou depois da emissão)."""
        resp = requests.post(
            f'{self.base_url}/cte/preview',
            json={'chave': chave},
            headers=self._headers(),
            timeout=self.TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()

    # Mapeamento tipo_servico (string model → código IntegraNotas)
    _TIPO_SERVICO_MAP = {
        'NORMAL': '0', 'SUBCONTRATADO': '1', 'REDESPACHO': '2',
        'INTERMEDIARIO': '3', 'VINCULADO_MULTIMODAL': '4',
    }

    def _build_cte_payload(self, ct) -> dict:
        from datetime import datetime as _dt
        empresa = ct.empresa
        try:
            config = empresa.configuracao_fiscal
        except Exception:
            config = None

        # data_emissao: obrigatório no formato 2020-05-16T12:33:20-03:00
        dt = ct.data_emissao
        if hasattr(dt, 'hour'):
            data_emissao_str = dt.strftime('%Y-%m-%dT%H:%M:%S') + '-03:00'
        else:
            now = _dt.now()
            data_emissao_str = f"{dt.strftime('%Y-%m-%d')}T{now.strftime('%H:%M:%S')}-03:00"

        tipo_servico = self._TIPO_SERVICO_MAP.get(ct.tipo_servico or 'NORMAL', '0')

        docs = [{'chave': d.chave_nfe} for d in ct.documentos_vinculados.all()]

        # Campos de percurso — validação antecipada dos códigos IBGE
        cod_ini = (ct.codigo_municipio_inicio or '').strip()
        cod_fim = (ct.codigo_municipio_fim or '').strip()
        if not cod_ini:
            raise IntegranNotasError(
                'Código IBGE do município de início (Percurso) não preenchido. '
                'Preencha o campo "Cód. IBGE Início" no CT-e antes de emitir.',
                codigo=None,
            )
        if not cod_fim:
            raise IntegranNotasError(
                'Código IBGE do município de fim (Percurso) não preenchido. '
                'Preencha o campo "Cód. IBGE Fim" no CT-e antes de emitir.',
                codigo=None,
            )

        payload: dict = {
            'serie': str(ct.serie),
            'numero': str(ct.numero),
            'data_emissao': data_emissao_str,
            'tipo_operacao': ct.tipo_cte,              # bloqueado em '0'-Normal por _validar_cte
            'cfop': ct.cfop,
            'natureza_operacao': ct.natureza_operacao,
            'tipo_servico': tipo_servico,
            # Município de envio (emissão) = mesma origem da prestação
            'codigo_municipio_envio': cod_ini,
            'nome_municipio_envio': ct.municipio_inicio or '',
            'uf_envio': ct.uf_inicio or '',
            # Início da prestação
            'codigo_municipio_inicio': cod_ini,
            'nome_municipio_inicio': ct.municipio_inicio or '',
            'uf_inicio': ct.uf_inicio or '',
            # Fim da prestação
            'codigo_municipio_fim': cod_fim,
            'nome_municipio_fim': ct.municipio_fim or '',
            'uf_fim': ct.uf_fim or '',
            # Retirada / programação entrega
            'retirar_mercadoria': '1',                # 1 = Não retira
            'tipo_programacao_entrega': '0',
            'sem_hora_tipo_hora_programada': '0',
            'emitente': self._build_emitente(empresa, config),
            'remetente':    self._build_parte_cte(ct.remetente),
            'destinatario': self._build_parte_cte(ct.destinatario),
            'tomador': self._build_tomador_cte(ct),
            'valores': self._build_valores_cte(ct),
            'imposto': self._build_imposto_cte(ct),
            'modal_rodoviario': self._build_modal_rodoviario_cte(ct),
            'nfes': docs,
            'informacoes_adicionais': {'informacoes_contribuinte': self._build_obs_cte(ct)},
        }

        # Fatura (cobrança) — só inclui se número ou valor original informado
        fat_num = (getattr(ct, 'fatura_numero', '') or '').strip()
        fat_orig = float(getattr(ct, 'fatura_valor_original', 0) or 0)
        if fat_num or fat_orig > 0:
            payload['cobranca'] = {
                'fatura': {
                    'numero': fat_num or str(ct.numero or ''),
                    'valor_original': str(ct.fatura_valor_original),
                    'valor_desconto': str(ct.fatura_valor_desconto),
                    'valor_liquido': str(
                        (ct.fatura_valor_original or 0) - (ct.fatura_valor_desconto or 0)
                    ),
                }
            }

        return payload

    def _build_obs_cte(self, ct) -> str:
        partes = []
        if getattr(ct, 'globalizado', False):
            ref = (getattr(ct, 'referencia_despacho', '') or '').strip()
            partes.append('CT-e GLOBALIZADO')
            if ref:
                partes.append(f'DESPACHO: {ref}')
        obs = (ct.observacoes or '').strip()
        if obs:
            partes.append(obs)
        return ' | '.join(partes)

    def _build_valores_cte(self, ct) -> dict:
        valores: dict = {
            'valor_total': str(ct.valor_servico),
            'valor_receber': str(ct.valor_receber or ct.valor_servico),
            'valor_total_carga': str(ct.valor_carga),
        }
        produto = (getattr(ct, 'produto_predominante', '') or '').strip()
        if produto:
            valores['produto_predominante'] = produto
        tributos = float(getattr(ct, 'valor_aproximado_tributos', 0) or 0)
        if tributos > 0:
            valores['valor_aproximado_tributos'] = str(ct.valor_aproximado_tributos)
        # quantidades — obrigatório quando tipo_operacao='0' ou '3'
        peso = float(ct.peso_bruto_kg or 0)
        valores['quantidades'] = [
            {
                'codigo_unidade_medida': '01',   # 01 = KG
                'tipo_medida': 'PESO BRUTO',
                'quantidade': f'{peso:.3f}',
            }
        ]

        # Componentes do valor da prestação (Prestações)
        comps = list(ct.componentes_valor.all())
        if comps:
            valores['componentes_valor'] = [
                {'nome': c.nome, 'valor': str(c.valor)} for c in comps
            ]
        return valores

    def _build_imposto_cte(self, ct) -> dict:
        cst = getattr(ct, 'cst_icms', '40') or '40'
        bc  = float(getattr(ct, 'base_calculo_icms', 0) or 0)
        alq = float(getattr(ct, 'aliquota_icms', 0) or 0)
        val = float(getattr(ct, 'valor_icms', 0) or 0)
        red = float(getattr(ct, 'reducao_base_icms', 0) or 0)

        icms: dict = {'situacao_tributaria': cst}
        if bc > 0:
            icms['valor_base_calculo'] = str(ct.base_calculo_icms)
        if alq > 0:
            icms['aliquota'] = str(ct.aliquota_icms)
        if val > 0:
            icms['valor'] = str(ct.valor_icms)
        if red > 0:
            icms['aliquota_reducao_base_calculo'] = str(ct.reducao_base_icms)

        # Crédito Outorgado/Presumido (vCred) — Convênio ICMS 106/96. Só existe
        # nos grupos ICMS60 e ICMS90 do schema do CT-e (MOC Anexo I).
        vcred = float(getattr(ct, 'valor_credito_outorgado_icms', 0) or 0)
        if cst in ('60', '90') and vcred > 0:
            icms['valor_credito_outorgado'] = str(ct.valor_credito_outorgado_icms)

        # Partilha ICMS (interestadual) — só inclui se houver valor preenchido
        pb = float(getattr(ct, 'partilha_bc_icms', 0) or 0)
        if pb > 0:
            icms['partilha'] = {
                'valor_base_calculo': str(ct.partilha_bc_icms),
                'aliquota_interna_uf_fim': str(ct.partilha_aliq_interna_uf_fim),
                'aliquota_interestadual': str(ct.partilha_aliq_interestadual),
                'percentual_uf_fim': str(ct.partilha_percentual_uf_fim),
                'valor_icms_uf_inicio': str(ct.partilha_valor_icms_uf_inicio),
                'valor_icms_uf_fim': str(ct.partilha_valor_icms_uf_fim),
                'percentual_fcp_uf_fim': str(ct.partilha_percentual_fcp_uf_fim),
                'valor_fcp_uf_fim': str(ct.partilha_valor_fcp_uf_fim),
            }

        impostos: dict = {'icms': icms}

        # IBS/CBS — Reforma Tributária (NT 2025.001, grupo_ibs_cbs). BC = valor
        # da prestação de serviço (o CT-e não tem itens, ao contrário da NF-e).
        # Estrutura conforme o schema real do endpoint /cte da IntegraNotas:
        # percentual_reducao e aliquota_reducao_base_calculo_efetiva (pAliqEfet)
        # ficam DENTRO de cada bloco (ibs_estadual/ibs_municipal/cbs), não como
        # um grupo "reducao_ibs"/"reducao_cbs" à parte.
        cst_reforma = (getattr(ct, 'ibs_cbs_situacao_tributaria', '') or '').strip()
        if cst_reforma:
            cclasstrib = (getattr(ct, 'ibs_cbs_classificacao_tributaria', '') or '').strip()

            def _bloco_tributo(aliquota, percentual_reducao, valor):
                bloco = {'aliquota': str(aliquota), 'valor': str(valor)}
                pred = float(percentual_reducao or 0)
                if pred > 0:
                    aliq_efet = float(aliquota or 0) * (1 - pred / 100)
                    bloco['percentual_reducao'] = str(percentual_reducao)
                    bloco['aliquota_reducao_base_calculo_efetiva'] = f'{aliq_efet:.4f}'
                return bloco

            impostos['ibs_cbs'] = {
                'situacao_tributaria': cst_reforma,
                'classificacao_tributaria': cclasstrib,
                'grupo_ibs_cbs': {
                    'valor_base_calculo': str(ct.ibs_cbs_base_calculo),
                    'valor_total_ibs': str(ct.valor_ibs),
                    'ibs_estadual': _bloco_tributo(ct.ibs_cbs_aliquota_uf, ct.ibs_percentual_reducao, ct.ibs_cbs_valor_uf),
                    'ibs_municipal': _bloco_tributo(ct.ibs_cbs_aliquota_municipal, ct.ibs_percentual_reducao, ct.ibs_cbs_valor_municipal),
                    'cbs': _bloco_tributo(ct.ibs_cbs_aliquota_cbs, ct.cbs_percentual_reducao, ct.ibs_cbs_valor_cbs),
                },
            }

        return impostos

    def _build_parte_cte(self, cliente) -> dict:
        parte: dict = {'razao_social': cliente.razao_social, 'nome': cliente.razao_social}
        exterior = _is_exterior(cliente)

        if exterior:
            parte['indicador_inscricao_estadual'] = '9'
            parte['cnpj'] = '00000000000000'
        else:
            doc = _digits(cliente.cnpj_cpf or '')
            if len(doc) == 14:
                parte['cnpj'] = doc
            elif len(doc) == 11:
                parte['cpf'] = doc
            ind, ie_str = _ie_info(cliente)
            parte['indicador_inscricao_estadual'] = ind
            if ie_str:
                parte['inscricao_estadual'] = ie_str

        endereco = (
            cliente.enderecos.filter(padrao=True).first()
            or cliente.enderecos.first()
        )
        if not endereco:
            raise IntegranNotasError(
                f'"{cliente.razao_social}" não possui endereço cadastrado. '
                'Cadastre um endereço antes de emitir o CT-e.',
                codigo=None,
            )

        pais_cli = (getattr(cliente, 'pais', '') or 'Brasil').strip()
        pais_end = (getattr(endereco, 'pais', '') or pais_cli or 'Brasil').strip()
        is_ext_end = exterior or pais_end.lower() not in ('brasil', '')

        if is_ext_end:
            codigo_pais = (getattr(cliente, 'codigo_pais', '') or '').strip()
            if not codigo_pais:
                codigo_pais = PAIS_IBGE_MAP.get(pais_end.lower().strip(), '')
            if not codigo_pais:
                raise IntegranNotasError(
                    f'País "{pais_end}" sem código IBGE válido. '
                    'Preencha o campo "Cód. IBGE País" no cadastro do cliente.',
                    codigo=None,
                )
            parte['endereco'] = {
                'logradouro': endereco.logradouro or '',
                'numero': endereco.numero or 'S/N',
                'bairro': endereco.bairro or '',
                'codigo_municipio': '9999999',
                'nome_municipio': 'Exterior',
                'uf': 'EX',
                'cep': '00000000',
                'codigo_pais': codigo_pais,
                'nome_pais': pais_end,
            }
        else:
            parte['endereco'] = {
                'logradouro': endereco.logradouro or '',
                'numero': endereco.numero or 'S/N',
                'bairro': endereco.bairro or '',
                'codigo_municipio': (getattr(endereco, 'codigo_municipio', '') or '9999999'),
                'nome_municipio': endereco.cidade or '',
                'uf': endereco.uf or '',
                'cep': _digits(endereco.cep or ''),
            }
        return parte

    def _build_tomador_cte(self, ct) -> dict:
        """Monta o bloco tomador a partir de ct.tipo_tomador.

        Tipos 0-3: tomador é uma das partes já declaradas; bloco precisa de 'tipo'
        e 'indicador_inscricao_estadual' (obrigatório pela IntegraNotas).
        Tipo 4: tomador externo — exige dados completos via ct.tomador FK.
        """
        tipo = ct.tipo_tomador or '0'
        result: dict = {'tipo': tipo}

        # indicador_inscricao_estadual: obrigatório para todos os tipos
        parte_map = {
            '0': ct.remetente,
            '1': getattr(ct, 'expedidor', None),
            '2': getattr(ct, 'recebedor', None),
            '3': ct.destinatario,
        }
        parte_ref = parte_map.get(tipo)
        ind_ie, ie_str = _ie_info(parte_ref) if parte_ref else ('9', '')
        result['indicador_inscricao_estadual'] = ind_ie
        if ie_str:
            result['inscricao_estadual'] = ie_str

        if tipo == '4':
            tomador = ct.tomador
            if not tomador:
                return result
            exterior_tom = _is_exterior(tomador)
            if exterior_tom:
                result['indicador_inscricao_estadual'] = '9'
                result['cnpj'] = '00000000000000'
            else:
                ind_tom, ie_tom = _ie_info(tomador)
                result['indicador_inscricao_estadual'] = ind_tom
                if ie_tom:
                    result['inscricao_estadual'] = ie_tom
                doc = _digits(tomador.cnpj_cpf or '')
                if len(doc) == 14:
                    result['cnpj'] = doc
                elif len(doc) == 11:
                    result['cpf'] = doc
            result['razao_social'] = tomador.razao_social
            result['nome'] = tomador.razao_social
            endereco = (
                tomador.enderecos.filter(padrao=True).first()
                or tomador.enderecos.first()
            )
            if endereco:
                pais_cli = (getattr(tomador, 'pais', '') or 'Brasil').strip()
                pais_end = (getattr(endereco, 'pais', '') or pais_cli or 'Brasil').strip()
                is_ext_end = exterior_tom or pais_end.lower() not in ('brasil', '')
                if is_ext_end:
                    codigo_pais = (getattr(tomador, 'codigo_pais', '') or '').strip()
                    if not codigo_pais:
                        codigo_pais = PAIS_IBGE_MAP.get(pais_end.lower().strip(), '')
                    if not codigo_pais:
                        raise IntegranNotasError(
                            f'País "{pais_end}" sem código IBGE válido. '
                            'Preencha o campo "Cód. IBGE País" no cadastro do tomador.',
                            codigo=None,
                        )
                    result['endereco'] = {
                        'logradouro': endereco.logradouro or '',
                        'numero': endereco.numero or 'S/N',
                        'bairro': endereco.bairro or '',
                        'codigo_municipio': '9999999',
                        'nome_municipio': 'Exterior',
                        'uf': 'EX',
                        'cep': '00000000',
                        'codigo_pais': codigo_pais,
                        'nome_pais': pais_end,
                    }
                else:
                    result['endereco'] = {
                        'logradouro': endereco.logradouro or '',
                        'numero': endereco.numero or 'S/N',
                        'bairro': endereco.bairro or '',
                        'codigo_municipio': (getattr(endereco, 'codigo_municipio', '') or '9999999'),
                        'nome_municipio': endereco.cidade or '',
                        'uf': endereco.uf or '',
                        'cep': _digits(endereco.cep or ''),
                    }
        return result

    def _build_modal_rodoviario_cte(self, ct) -> dict:
        rntrc = (getattr(ct, 'rntrc_override', '') or '').strip()
        if not rntrc:
            rntrc = getattr(ct.transportadora, 'rntc', '') or ''
        modal: dict = {'rntrc': rntrc}
        placa = (getattr(ct, 'placa_veiculo_override', '') or '').strip()
        if not placa and ct.veiculo:
            placa = ct.veiculo.get_current_plate() or ''
            if not placa:
                first = ct.veiculo.plates.order_by('-vigencia_inicio').first()
                placa = first.placa if first else ''
        if placa:
            modal['veiculo'] = {'placa': placa, 'uf': ct.uf_inicio}
        if ct.motorista:
            modal['condutor'] = {
                'nome': ct.motorista.nome,
                'cpf':  _digits(getattr(ct.motorista, 'cpf', '') or ''),
            }
        return modal

    # ─── MDF-e ────────────────────────────────────────────────────

    def emitir_mdfe(self, mdfe) -> dict:
        """Submit MDF-e to IntegraNotas. Returns API response dict."""
        payload = self._build_mdfe_payload(mdfe)
        logger.info('IntegraNotas: emitindo MDF-e %s/%s', mdfe.numero, mdfe.serie)
        resp = requests.post(
            f'{self.base_url}/mdfe',
            json=payload,
            headers=self._headers(),
            timeout=self.TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        # 5008 = MDF-e já registrado na IntegraNotas (tentativa anterior); consulta o existente
        if data.get('codigo') == 5008 and data.get('chave'):
            import time; time.sleep(2)
            data = self.consultar_mdfe(data['chave'])
        if not data.get('sucesso') and data.get('codigo') not in (100, 2, 5023):
            raise IntegranNotasError(
                data.get('mensagem', 'Erro desconhecido na emissão do MDF-e'),
                codigo=data.get('codigo'),
                erros=data.get('erros', []),
            )
        return data

    def consultar_mdfe(self, chave: str) -> dict:
        resp = requests.get(f'{self.base_url}/mdfe/mostra', params={'chave': chave}, headers=self._headers(), timeout=self.TIMEOUT)
        resp.raise_for_status()
        return resp.json()

    def cancelar_mdfe(self, chave: str, justificativa: str) -> dict:
        resp = requests.post(
            f'{self.base_url}/mdfe/cancela',
            json={'chave': chave, 'justificativa': justificativa},
            headers=self._headers(),
            timeout=self.TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get('sucesso') and data.get('codigo') != 101:
            raise IntegranNotasError(
                data.get('mensagem', 'Erro ao cancelar MDF-e'),
                codigo=data.get('codigo'),
                erros=data.get('erros', []),
            )
        return data

    def encerrar_mdfe(self, chave: str, municipio: str, data_enc) -> dict:
        data_str = data_enc.strftime('%Y-%m-%dT%H:%M:%S') + '-03:00' if hasattr(data_enc, 'strftime') else str(data_enc)
        payload = {'chave': chave, 'municipio_encerramento': municipio, 'data_encerramento': data_str}
        logger.info('IntegraNotas: encerrando MDF-e chave=%s payload=%s', chave, payload)
        resp = requests.post(
            f'{self.base_url}/mdfe/encerra',
            json=payload,
            headers=self._headers(),
            timeout=self.TIMEOUT,
        )
        logger.info('IntegraNotas: encerrar_mdfe HTTP %s body=%s', resp.status_code, resp.text[:500])
        if resp.status_code in (401, 403):
            try:
                body = resp.json()
                msg = body.get('mensagem') or body.get('message') or resp.text[:200]
            except Exception:
                msg = resp.text[:200]
            raise IntegranNotasError(
                f'Token rejeitado pelo IntegraNotas (HTTP {resp.status_code}): {msg}. '
                'Verifique se o token configurado corresponde ao ambiente de homologação.',
                codigo=resp.status_code,
            )
        resp.raise_for_status()
        data = resp.json()
        if not data.get('sucesso') and data.get('codigo') != 103:
            erros = data.get('erros') or []
            detail = '; '.join(str(e) for e in erros) if erros else ''
            msg = data.get('mensagem', 'Erro ao encerrar MDF-e')
            raise IntegranNotasError(
                f'{msg}{(" — " + detail) if detail else ""}',
                codigo=data.get('codigo'),
                erros=erros,
            )
        return data

    def damdfe(self, chave: str) -> dict:
        resp = requests.get(f'{self.base_url}/mdfe/pdf', params={'chave': chave}, headers=self._headers(), timeout=self.TIMEOUT)
        resp.raise_for_status()
        return resp.json()

    def mdfe_abertos(self) -> dict:
        resp = requests.get(f'{self.base_url}/mdfe/abertos', headers=self._headers(), timeout=self.TIMEOUT)
        resp.raise_for_status()
        return resp.json()

    def preview_mdfe(self, chave: str) -> dict:
        resp = requests.post(
            f'{self.base_url}/mdfe/preview',
            json={'chave': chave},
            headers=self._headers(),
            timeout=self.TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()

    def inclui_condutor_mdfe(self, chave: str, cpf: str, nome: str) -> dict:
        resp = requests.post(
            f'{self.base_url}/mdfe/inclui-condutor',
            json={'chave': chave, 'cpf': cpf, 'nome': nome},
            headers=self._headers(),
            timeout=self.TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get('sucesso') and data.get('codigo') not in (100,):
            raise IntegranNotasError(
                data.get('mensagem', 'Erro ao incluir condutor no MDF-e'),
                codigo=data.get('codigo'),
                erros=data.get('erros', []),
            )
        return data

    def inclui_nfe_mdfe(self, chave: str, chave_nfe: str, municipio_descarregamento: str) -> dict:
        resp = requests.post(
            f'{self.base_url}/mdfe/inclui-nfe',
            json={'chave': chave, 'chave_nfe': chave_nfe, 'municipio_descarregamento': municipio_descarregamento},
            headers=self._headers(),
            timeout=self.TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get('sucesso') and data.get('codigo') not in (100,):
            raise IntegranNotasError(
                data.get('mensagem', 'Erro ao incluir NF-e no MDF-e'),
                codigo=data.get('codigo'),
                erros=data.get('erros', []),
            )
        return data

    def _build_mdfe_payload(self, mdfe) -> dict:
        empresa = mdfe.empresa
        try:
            config = empresa.configuracao_fiscal
        except Exception:
            config = None

        # Agrupar documentos por município de descarregamento (código + nome)
        municipios: dict = {}
        ceps_por_municipio: dict = {}
        docs_sem_ibge = []
        docs_sem_municipio = []
        for doc in mdfe.documentos_vinculados.all():
            codigo = doc.codigo_municipio_descarregamento or ''
            nome   = doc.municipio_descarregamento or ''
            cep    = (doc.cep_descarregamento or '').replace('-', '').replace('.', '').zfill(8) if (doc.cep_descarregamento or '').strip() else ''
            chave_id = doc.chave[:10] + '…' if doc.chave else '(sem chave)'
            if not codigo:
                docs_sem_ibge.append(chave_id)
            if not nome:
                docs_sem_municipio.append(chave_id)
            key = (codigo, nome)
            if key not in municipios:
                municipios[key] = []
                ceps_por_municipio[key] = cep
            municipios[key].append({'chave': doc.chave, 'tipo': doc.tipo})

        if docs_sem_ibge:
            raise ValueError(
                f"Código IBGE de descarregamento ausente nos documentos: {', '.join(docs_sem_ibge)}. "
                "Edite o MDF-e e preencha o 'Cód. IBGE' na seção 'Municípios de Entrega' (aba Geral)."
            )
        if docs_sem_municipio:
            raise ValueError(
                f"Município de Entrega ausente nos documentos: {', '.join(docs_sem_municipio)}. "
                "Edite o MDF-e e preencha o 'Município de Entrega' na seção 'Municípios de Entrega' (aba Geral)."
            )
        if not mdfe.municipio_carregamento:
            raise ValueError(
                "Município de Carregamento é obrigatório. "
                "Preencha o campo 'Município de Carregamento' no card Percurso (aba Geral)."
            )

        municipios_list = []
        for (codigo, nome), docs in municipios.items():
            entry: dict = {'codigo_municipio': codigo, 'nome_municipio': nome}
            cep_desc = ceps_por_municipio.get((codigo, nome), '')
            if cep_desc:
                entry['cep'] = cep_desc
            nfes  = [{'chave': d['chave']} for d in docs if d['tipo'] == 'nfe']
            ctes  = [{'chave': d['chave']} for d in docs if d['tipo'] == 'cte']
            mdfes = [{'chave': d['chave']} for d in docs if d['tipo'] == 'mdfe']
            if nfes:  entry['nfes']  = nfes
            if ctes:  entry['ctes']  = ctes
            if mdfes: entry['mdfes'] = mdfes
            municipios_list.append(entry)

        percursos = [{'uf': p.uf} for p in mdfe.percursos.order_by('ordem')]

        plates = mdfe.veiculo.plates.order_by('-id').first()
        placa = (mdfe.placa_tracao or (plates.placa if plates else '')).upper()
        uf_tracao = (mdfe.uf_tracao or mdfe.veiculo.uf_licenciamento or mdfe.uf_inicio or '').upper()
        tara_tracao = mdfe.tara_tracao_kg if mdfe.tara_tracao_kg is not None else mdfe.veiculo.tara_kg

        # ── Condutores (motorista principal + CondutorMDFe pré-emissão) ────────
        condutores_list = [{
            'nome': mdfe.motorista.nome,
            'cpf': _digits(getattr(mdfe.motorista, 'cpf', '') or ''),
        }]
        for c in mdfe.condutores.order_by('ordem'):
            condutores_list.append({'nome': c.nome, 'cpf': _digits(c.cpf)})

        # ── Veículo de tração ────────────────────────────────────────────────────
        veiculo_payload: dict = {
            'placa': placa,
            'uf': uf_tracao,
            'condutores': condutores_list,
        }
        if tara_tracao:
            veiculo_payload['tara'] = tara_tracao
        if mdfe.veiculo.renavam:
            veiculo_payload['renavam'] = mdfe.veiculo.renavam
        tipo_rodado = mdfe.tipo_rodado or mdfe.veiculo.tipo_rodado
        if tipo_rodado:
            veiculo_payload['tipo_rodado'] = tipo_rodado
        tipo_carroceria = mdfe.tipo_carroceria or mdfe.veiculo.tipo_carroceria
        if tipo_carroceria:
            veiculo_payload['tipo_carroceria'] = tipo_carroceria

        # Proprietário/possuidor diferente do emitente
        if mdfe.proprietario_diferente and mdfe.prop_cpf_cnpj:
            digits_prop = _digits(mdfe.prop_cpf_cnpj)
            prop: dict = {'cnpj': digits_prop} if len(digits_prop) == 14 else {'cpf': digits_prop}
            if mdfe.prop_rntrc:
                prop['rntrc'] = mdfe.prop_rntrc
            if mdfe.prop_nome:
                prop['nome'] = mdfe.prop_nome
            if mdfe.prop_ie:
                prop['inscricao_estadual'] = mdfe.prop_ie
            if mdfe.prop_uf:
                prop['uf'] = mdfe.prop_uf
            if mdfe.prop_tipo:
                prop['tipo'] = mdfe.prop_tipo
            veiculo_payload['proprietario'] = prop

        # ── Modal rodoviário ─────────────────────────────────────────────────────
        modal: dict = {
            'veiculo': veiculo_payload,
        }

        # RNTRC (infANTT)
        rntrc = mdfe.rntrc_veiculo or getattr(mdfe.veiculo, 'rntrc', '') or ''
        if not rntrc:
            # fallback: transportadora do veículo
            transp = getattr(mdfe.veiculo, 'transportadora', None)
            if transp:
                rntrc = getattr(transp, 'rntc', '') or ''
        if rntrc:
            modal['rntrc'] = rntrc

        if mdfe.cod_ag_porto:
            modal['cod_ag_porto'] = mdfe.cod_ag_porto

        # CIOTs — infANTT/infCIOT: CNPJ ou CPF separados (não cpf_cnpj unificado)
        ciots = []
        for c in mdfe.ciots.all():
            digits_ciot = _digits(c.cpf_cnpj)
            entry: dict = {'ciot': c.ciot}
            if len(digits_ciot) == 14:
                entry['cnpj'] = digits_ciot
            else:
                entry['cpf'] = digits_ciot
            ciots.append(entry)
        if ciots:
            modal['ciot'] = ciots

        # Vales Pedágio
        vales = []
        for v in mdfe.vales_pedagio.all():
            vd: dict = {'cnpj_fornecedor': _digits(v.cnpj_fornecedor), 'n_compra': v.n_compra, 'valor': str(v.valor)}
            if v.tp_vale:
                vd['tp_vale'] = v.tp_vale
            vales.append(vd)
        if vales:
            modal['vale_pedagio'] = vales

        # Contratantes
        contratantes = []
        for ct in mdfe.contratantes.all():
            digits = _digits(ct.cpf_cnpj)
            if len(digits) == 11:
                cd: dict = {'cpf': digits}
            elif len(digits) == 14:
                cd = {'cnpj': digits}
            else:
                cd = {'cpf': digits}  # melhor esforço
            if ct.ie:
                cd['ie'] = ct.ie
            if ct.n_contrato:
                cd['n_contrato'] = ct.n_contrato
            if ct.v_contrato is not None:
                cd['v_contrato'] = str(ct.v_contrato)
            contratantes.append(cd)
        if contratantes:
            modal['contratante'] = contratantes

        if not ciots and not contratantes:
            raise ValueError(
                "É obrigatório informar ao menos um CIOT ou Contratante no modal rodoviário. "
                "Preencha a sub-aba 'CIOT' ou 'Contratantes' antes de emitir."
            )

        # Pagamentos do frete
        pags = []
        for pf in mdfe.pagamentos_frete.all():
            pf_digits = _digits(pf.cpf_cnpj)
            pd: dict = {'responsavel': pf.responsavel}
            if len(pf_digits) == 11:
                pd['cpf'] = pf_digits
            elif len(pf_digits) == 14:
                pd['cnpj'] = pf_digits
            else:
                pd['cpf'] = pf_digits
            if pf.x_nome:
                pd['x_nome'] = pf.x_nome
            if pf.ind_pag:
                pd['ind_pag'] = pf.ind_pag
            if pf.vr_total is not None:
                pd['vr_total'] = str(pf.vr_total)
            if pf.tp_antecip:
                pd['tp_antecip'] = pf.tp_antecip
            pags.append(pd)
        if pags:
            modal['inf_pag'] = pags

        # Reboques
        reboques = []
        for rb in mdfe.reboques.all():
            rd: dict = {'placa': (rb.placa or '').upper(), 'uf': (rb.uf or '').upper()}
            if rb.rntrc:
                rd['rntrc'] = rb.rntrc
            if rb.tipo_carroceria:
                rd['tipo_carroceria'] = rb.tipo_carroceria
            if rb.tara_kg:
                rd['tara'] = rb.tara_kg
            if rb.renavam:
                rd['renavam'] = rb.renavam
            if rb.capacidade_kg:
                rd['capacidade_kg'] = rb.capacidade_kg
            if rb.capacidade_m3:
                rd['capacidade_m3'] = rb.capacidade_m3
            if rb.prop_cpf_cnpj:
                digits_rb = _digits(rb.prop_cpf_cnpj)
                prop_rb: dict = {'cnpj': digits_rb} if len(digits_rb) == 14 else {'cpf': digits_rb}
                if rb.prop_nome:
                    prop_rb['nome'] = rb.prop_nome
                if rb.prop_tipo:
                    prop_rb['tipo'] = rb.prop_tipo
                if rb.prop_uf:
                    prop_rb['uf'] = rb.prop_uf
                if rb.prop_rntrc:
                    prop_rb['rntrc'] = rb.prop_rntrc
                if rb.prop_ie:
                    prop_rb['inscricao_estadual'] = rb.prop_ie
                rd['proprietario'] = prop_rb
            reboques.append(rd)
        if reboques:
            modal['reboque'] = reboques

        # ── Seguros ──────────────────────────────────────────────────────────────
        seguros = []
        for sg in mdfe.seguros.all():
            sd: dict = {'n_apolice': sg.n_apolice, 'responsavel': sg.responsavel}
            # CNPJ/CPF do responsável: só enviar quando responsavel ≠ "1" (Emitente)
            # Quando responsavel="1" o emitente já consta no bloco raiz — enviar aqui gera rejeição
            if sg.responsavel != '1' and sg.cpf_cnpj:
                digits_sg = _digits(sg.cpf_cnpj)
                if len(digits_sg) == 14:
                    sd['cnpj'] = digits_sg
                else:
                    sd['cpf'] = digits_sg
            if sg.seguradora:
                sd['nome_seguradora'] = sg.seguradora
            if sg.cnpj_seguradora:
                sd['cnpj_seguradora'] = _digits(sg.cnpj_seguradora)
            # nAverb tem cardinalidade 0..999 no XML — IntegraNotas espera array
            if sg.n_averbacao:
                sd['numero_averbacao'] = [sg.n_averbacao]
            seguros.append(sd)

        # ── Produto Predominante — na raiz do payload (prodPred no XML MDF-e) ──
        try:
            pp = mdfe.produto_predominante
            if not pp.x_prod:
                raise ValueError("descricao (x_prod) vazio")
            if not pp.tipo_carga:
                raise ValueError("tipo_carga vazio")
            prod_pred: dict = {}
            if pp.c_prod:
                prod_pred['c_prod'] = pp.c_prod
            prod_pred['descricao'] = pp.x_prod  # API usa 'descricao', não 'x_prod'
            prod_pred['tipo_carga'] = pp.tipo_carga
            if pp.tipo_medida:
                prod_pred['tipo_medida'] = pp.tipo_medida
            if pp.q_carga is not None:
                prod_pred['q_carga'] = str(pp.q_carga)
            # infLotacao: obrigatório quando há apenas 1 município de descarregamento
            # e o modal é rodoviário (tipo_operacao=1)
            if len(municipios_list) == 1:
                cod_ibge_carga = mdfe.codigo_municipio_carregamento or ''
                nom_carga = mdfe.municipio_carregamento or ''
                mun_desc = municipios_list[0]
                if not cod_ibge_carga:
                    raise ValueError(
                        "Código IBGE do município de carregamento é obrigatório quando há apenas "
                        "1 município de descarregamento (lotação). "
                        "Preencha o campo 'Município de Carregamento' do MDF-e."
                    )
                cep_carga = (empresa.cep or '').replace('-', '').replace('.', '').zfill(8) if (empresa.cep or '').strip() else ''
                cep_desc  = mun_desc.get('cep', '')
                mun_carg_obj: dict = {'codigo_municipio': cod_ibge_carga, 'nome_municipio': nom_carga}
                if cep_carga:
                    mun_carg_obj['cep'] = cep_carga
                mun_desc_obj: dict = {'codigo_municipio': mun_desc['codigo_municipio'], 'nome_municipio': mun_desc['nome_municipio']}
                if cep_desc:
                    mun_desc_obj['cep'] = cep_desc
                prod_pred['lotacao'] = {
                    'municipio_carregamento': mun_carg_obj,
                    'municipio_descarregamento': mun_desc_obj,
                }
                logger.debug('MDF-e lotacao payload: %s', prod_pred['lotacao'])
        except ValueError:
            raise
        except Exception:
            raise ValueError(
                "Produto Predominante é obrigatório (tipo_operacao=1). "
                "Preencha a aba 'Produto Predominante' do MDF-e antes de emitir."
            )

        payload: dict = {
            'tipo_operacao': mdfe.tipo_emitente,  # '1'=PST (serviço), '2'=TCP (carga própria)
            'serie': str(mdfe.serie),
            'numero': str(mdfe.numero),
            'data_emissao': mdfe.data_emissao.strftime('%Y-%m-%dT00:00:00-03:00') if hasattr(mdfe.data_emissao, 'strftime') else str(mdfe.data_emissao),
            'emitente': self._build_emitente(empresa, config),
            'uf_inicio': mdfe.uf_inicio,
            'uf_fim': mdfe.uf_fim,
            'municipios_carregamento': [{
                'codigo_municipio': mdfe.codigo_municipio_carregamento or '',
                'nome_municipio': mdfe.municipio_carregamento or '',
            }],
            'municipios_descarregamento': municipios_list,
            'valores': {
                'valor_total_carga': str(mdfe.valor_carga),
                'codigo_unidade_medida_peso_bruto': '01',
                'peso_bruto': str(mdfe.peso_bruto_kg),
            },
            'modal_rodoviario': modal,
            'produto': prod_pred,
        }
        # Campos opcionais: só incluir quando preenchidos (schema SEFAZ exige minLength=1)
        if percursos:
            payload['percursos'] = percursos
        # tipo_transporte só pode ser enviado se proprietario estiver presente no veiculo (Rej. 745)
        if mdfe.tipo_transporte and 'proprietario' in veiculo_payload:
            payload['tipo_transporte'] = mdfe.tipo_transporte
        if mdfe.informacoes_fisco:
            payload['informacoes_adicionais_fisco'] = mdfe.informacoes_fisco
        if mdfe.informacoes_contribuinte:
            payload['informacoes_adicionais_contribuinte'] = mdfe.informacoes_contribuinte
        if seguros:
            modal['seguro'] = seguros
        logger.debug('MDF-e payload: %s', payload)
        return payload
