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


class IntegranNotasError(Exception):
    """Raised when IntegraNota returns a non-success response."""
    def __init__(self, message, codigo=None, erros=None):
        super().__init__(message)
        self.codigo = codigo
        self.erros = erros or []


class IntegranNotasClient:
    PROD_URL = 'https://api.integranotas.com.br/v1'
    HOM_URL  = 'https://hom-api.integranotas.com.br/v1'
    TIMEOUT  = 60  # seconds — IntegraNota recommends minimum 60s

    def __init__(self, token: str, ambiente: str = '2'):
        self.token = token
        self.base_url = self.PROD_URL if ambiente == '1' else self.HOM_URL

    # ─── Public methods ───────────────────────────────────────────────

    def emitir_nfe(self, nf) -> dict:
        """Submit NF-e to IntegraNota. Returns API response dict."""
        payload = self._build_payload(nf)
        logger.info('IntegraNota: emitindo NF %s/%s', nf.numero, nf.serie)
        resp = requests.post(
            f'{self.base_url}/nfe',
            json=payload,
            headers=self._headers(),
            timeout=self.TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
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

    # ─── Private helpers ──────────────────────────────────────────────

    def _headers(self):
        return {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json',
        }

    def _build_payload(self, nf) -> dict:
        empresa = nf.empresa
        try:
            config = empresa.configuracao_fiscal
        except Exception:
            config = None

        return {
            'natureza_operacao': nf.natureza_operacao,
            'serie': str(nf.serie),
            'numero': str(nf.numero),
            'data_emissao': nf.data_emissao.strftime('%Y-%m-%dT%H:%M:%S') if hasattr(nf.data_emissao, 'strftime') else str(nf.data_emissao),
            'tipo_documento': '1',  # 1=NF-e
            'presenca_comprador': nf.presenca_comprador or '9',
            'tipo_emissao': str(nf.tipo_emissao or 1),
            'emitente': self._build_emitente(empresa, config),
            'destinatario': self._build_destinatario(nf.cliente),
            'produtos': [self._build_item(item) for item in nf.itens.all()],
            'totais': self._build_totais(nf),
            'transporte': self._build_transporte(nf),
            'pagamento': self._build_pagamento(nf),
            'informacoes_adicionais': {
                'informacoes_complementares': nf.informacoes_complementares or '',
            },
        }

    def _build_emitente(self, empresa, config) -> dict:
        crt = CRT_MAP.get(getattr(config, 'regime_tributario', 'SIMPLES_NACIONAL'), '1')
        return {
            'cnpj': _digits(empresa.cnpj or ''),
            'nome': empresa.nome,
            'inscricao_estadual': empresa.inscricao_estadual or '',
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
        dest: dict = {
            'nome': cliente.razao_social,
            'indicador_inscricao_estadual': cliente.indicador_ie or '9',
            'inscricao_estadual': cliente.inscricao_estadual or '',
        }
        if len(doc) == 14:
            dest['cnpj'] = doc
        elif len(doc) == 11:
            dest['cpf'] = doc
        else:
            dest['cnpj'] = doc  # will fail validation, but keeps structure

        # Address from default EnderecoCliente
        endereco_obj = cliente.enderecos.filter(padrao=True).first()
        if endereco_obj:
            is_exterior = (cliente.pais or '').strip().lower() not in ('brasil', '')
            dest['endereco'] = {
                'logradouro': endereco_obj.logradouro or '',
                'numero': endereco_obj.numero or 'S/N',
                'complemento': endereco_obj.complemento or '',
                'bairro': endereco_obj.bairro or '',
                'codigo_municipio': endereco_obj.codigo_municipio or '',
                'nome_municipio': endereco_obj.cidade or '',
                'uf': 'EX' if is_exterior else (endereco_obj.uf or ''),
                'cep': _digits(endereco_obj.cep or ''),
                'codigo_pais': '1058' if not is_exterior else '9999',
                'nome_pais': 'Brasil' if not is_exterior else (cliente.pais or ''),
                'telefone': _digits(cliente.contato_principal_telefone or ''),
            }
        return dest

    def _build_item(self, item) -> dict:
        produto_codigo = ''
        if item.produto_id:
            produto_codigo = item.produto.codigo or ''

        return {
            'numero_item': str(item.numero_item),
            'codigo_produto': produto_codigo or 'SEM CODIGO',
            'ean': item.ean or 'SEM GTIN',
            'descricao': item.descricao,
            'ncm': item.ncm or '',
            'cest': item.cest or '',
            'cfop': item.cfop or '',
            'unidade_comercial': item.unidade or 'UN',
            'quantidade_comercial': str(item.quantidade),
            'valor_unitario_comercial': str(item.valor_unitario),
            'valor_bruto': str(item.valor_total),
            'valor_desconto': str(item.valor_desconto),
            'origem_mercadoria': item.origem_mercadoria or '0',
            'imposto': self._build_impostos(item),
        }

    def _build_impostos(self, item) -> dict:
        impostos: dict = {}

        # ICMS
        cst_icms = item.cst_icms or '40'
        icms_block: dict = {'situacao_tributaria': cst_icms}
        if item.aliquota_icms and float(item.aliquota_icms) > 0:
            icms_block.update({
                'modalidade_base_calculo': '3',
                'base_calculo': str(item.icms_base_calculo),
                'aliquota': str(item.aliquota_icms),
                'valor': str(item.valor_icms),
            })
        impostos['icms'] = icms_block

        # IPI (only when there's an aliquota or enquadramento)
        if item.aliquota_ipi and float(item.aliquota_ipi) > 0:
            impostos['ipi'] = {
                'situacao_tributaria': '50',
                'codigo_enquadramento': item.ipi_codigo_enquadramento or '999',
                'base_calculo': str(item.valor_total),
                'aliquota': str(item.aliquota_ipi),
                'valor': str(item.valor_ipi),
            }
        else:
            impostos['ipi'] = {
                'situacao_tributaria': '99',
                'codigo_enquadramento': item.ipi_codigo_enquadramento or '999',
                'valor': '0.00',
            }

        # PIS
        cst_pis = item.cst_pis or '07'
        pis_block: dict = {'situacao_tributaria': cst_pis}
        if item.aliquota_pis and float(item.aliquota_pis) > 0:
            pis_block.update({
                'base_calculo': str(item.pis_base_calculo),
                'aliquota_percentual': str(item.aliquota_pis),
                'valor': str(item.valor_pis),
            })
        else:
            pis_block['valor'] = '0.00'
        impostos['pis'] = pis_block

        # COFINS
        cst_cofins = item.cst_cofins or '07'
        cofins_block: dict = {'situacao_tributaria': cst_cofins}
        if item.aliquota_cofins and float(item.aliquota_cofins) > 0:
            cofins_block.update({
                'base_calculo': str(item.cofins_base_calculo),
                'aliquota_percentual': str(item.aliquota_cofins),
                'valor': str(item.valor_cofins),
            })
        else:
            cofins_block['valor'] = '0.00'
        impostos['cofins'] = cofins_block

        return impostos

    def _build_totais(self, nf) -> dict:
        return {
            'base_calculo_icms': str(sum(i.icms_base_calculo for i in nf.itens.all())),
            'valor_icms': str(nf.valor_icms),
            'valor_ipi': str(nf.valor_ipi),
            'valor_pis': str(nf.valor_pis),
            'valor_cofins': str(nf.valor_cofins),
            'valor_produtos': str(nf.valor_produtos),
            'valor_frete': str(nf.valor_frete),
            'valor_seguro': str(nf.valor_seguro),
            'valor_desconto': str(nf.valor_desconto),
            'valor_nota': str(nf.valor_total),
        }

    def _build_transporte(self, nf) -> dict:
        mod = MODALIDADE_FRETE_MAP.get(nf.modalidade_frete, '9')
        transporte: dict = {'modalidade_frete': mod}
        if nf.transportadora_id:
            t = nf.transportadora
            transporte['transportadora'] = {
                'cnpj': _digits(getattr(t, 'cnpj', '') or ''),
                'nome': getattr(t, 'nome', '') or '',
            }
        return transporte

    def _build_pagamento(self, nf) -> dict:
        # Default: À vista / outros (código 90)
        return {
            'formas_pagamento': [
                {
                    'meio_pagamento': '90',
                    'valor': str(nf.valor_total),
                }
            ]
        }
