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

        payload: dict = {
            'natureza_operacao': nf.natureza_operacao,
            'serie': str(nf.serie),
            'numero': str(nf.numero),
            'data_emissao': nf.data_emissao.strftime('%Y-%m-%dT%H:%M:%S') if hasattr(nf.data_emissao, 'strftime') else str(nf.data_emissao),
            'tipo_documento': '1',
            'finalidade': getattr(nf, 'finalidade_nfe', '1') or '1',
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
                'informacoes_fisco': getattr(nf, 'informacoes_fisco', '') or '',
            },
        }

        # Exportação — grupo ZA da NF-e (<exporta>) — obrigatório para CFOP 7xxx
        uf_embarque    = getattr(nf, 'embarque_uf', '').strip().upper()
        local_embarque = getattr(nf, 'embarque_local', '').strip()
        local_despacho = getattr(nf, 'embarque_local_despacho', '').strip()
        if uf_embarque or local_embarque:
            exporta: dict = {}
            if uf_embarque:
                exporta['uf_saida_pais'] = uf_embarque
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
                        'vencimento': d.vencimento.strftime('%Y-%m-%d'),
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
        modalidade_bc = getattr(item, 'icms_modalidade_base', '3') or '3'
        reducao_bc = float(getattr(item, 'icms_reducao_base', 0) or 0)

        icms_block: dict = {'situacao_tributaria': cst_icms}
        if item.aliquota_icms and float(item.aliquota_icms) > 0:
            icms_block.update({
                'modalidade_base_calculo': modalidade_bc,
                'base_calculo': str(item.icms_base_calculo),
                'aliquota': str(item.aliquota_icms),
                'valor': str(item.valor_icms),
            })
            if reducao_bc > 0:
                icms_block['percentual_reducao_base'] = str(reducao_bc)

        # ICMS ST (CST 10, 30, 70, 90 etc.)
        valor_st = float(getattr(item, 'valor_icms_st', 0) or 0)
        if valor_st > 0:
            mva = float(getattr(item, 'icms_st_mva', 0) or 0)
            red_st = float(getattr(item, 'icms_st_reducao_base', 0) or 0)
            aliq_st = float(getattr(item, 'icms_st_aliquota', 0) or 0)
            bc_st = float(getattr(item, 'icms_st_base_calculo', 0) or 0)
            icms_block.update({
                'modalidade_base_calculo_st': '4',
                'percentual_mva_st': str(mva),
                'percentual_reducao_base_st': str(red_st),
                'base_calculo_st': str(bc_st),
                'aliquota_st': str(aliq_st),
                'valor_st': str(valor_st),
            })

        impostos['icms'] = icms_block

        # IPI
        cst_ipi = getattr(item, 'cst_ipi', '') or ('50' if item.aliquota_ipi and float(item.aliquota_ipi) > 0 else '99')
        if item.aliquota_ipi and float(item.aliquota_ipi) > 0:
            impostos['ipi'] = {
                'situacao_tributaria': cst_ipi,
                'codigo_enquadramento': item.ipi_codigo_enquadramento or '999',
                'base_calculo': str(item.valor_total),
                'aliquota': str(item.aliquota_ipi),
                'valor': str(item.valor_ipi),
            }
        else:
            impostos['ipi'] = {
                'situacao_tributaria': cst_ipi or '99',
                'codigo_enquadramento': item.ipi_codigo_enquadramento or '999',
                'valor': '0.00',
            }

        # PIS
        cst_pis = item.cst_pis or '07'
        pis_block: dict = {'situacao_tributaria': cst_pis}
        nat_pis = (getattr(item, 'natureza_receita_pis', '') or '').strip()
        if nat_pis:
            pis_block['natureza_receita'] = nat_pis
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
        nat_cofins = (getattr(item, 'natureza_receita_cofins', '') or '').strip()
        if nat_cofins:
            cofins_block['natureza_receita'] = nat_cofins
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
        itens = list(nf.itens.all())
        return {
            'base_calculo_icms': str(sum(i.icms_base_calculo for i in itens)),
            'valor_icms': str(nf.valor_icms),
            'valor_icms_st': str(getattr(nf, 'valor_icms_st', 0) or 0),
            'base_calculo_icms_st': str(sum(getattr(i, 'icms_st_base_calculo', 0) or 0 for i in itens)),
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

    def _build_cte_payload(self, ct) -> dict:
        empresa = ct.empresa
        try:
            config = empresa.configuracao_fiscal
        except Exception:
            config = None

        docs = [{'chave': d.chave_nfe} for d in ct.documentos_vinculados.all()]

        payload: dict = {
            'serie': str(ct.serie),
            'numero': str(ct.numero),
            'data_emissao': ct.data_emissao.strftime('%Y-%m-%dT%H:%M:%S') if hasattr(ct.data_emissao, 'strftime') else str(ct.data_emissao),
            'cfop': ct.cfop,
            'natureza_operacao': ct.natureza_operacao,
            'tipo_servico': ct.tipo_servico,
            'emitente': self._build_emitente(empresa, config),
            'remetente': self._build_parte_cte(ct.remetente),
            'destinatario': self._build_parte_cte(ct.destinatario),
            'tomador': {'indicador': '3', **self._build_parte_cte(ct.tomador)},
            'valores': {
                'valor_total_servico': str(ct.valor_servico),
                'valor_carga': str(ct.valor_carga),
            },
            'modal_rodoviario': self._build_modal_rodoviario_cte(ct),
            'percurso': {
                'uf_inicio': ct.uf_inicio,
                'municipio_inicio': ct.municipio_inicio,
                'uf_fim': ct.uf_fim,
                'municipio_fim': ct.municipio_fim,
            },
            'documentos_originarios': docs,
            'informacoes_adicionais': {'informacoes_contribuinte': ct.observacoes or ''},
        }
        return payload

    def _build_parte_cte(self, cliente) -> dict:
        doc = _digits(cliente.cnpj_cpf or '')
        parte: dict = {'nome': cliente.razao_social}
        if len(doc) == 14:
            parte['cnpj'] = doc
        else:
            parte['cpf'] = doc
        endereco = cliente.enderecos.filter(padrao=True).first()
        if endereco:
            parte['endereco'] = {
                'logradouro': endereco.logradouro or '',
                'numero': endereco.numero or 'S/N',
                'bairro': endereco.bairro or '',
                'municipio': endereco.cidade or '',
                'uf': endereco.uf or '',
                'cep': _digits(endereco.cep or ''),
                'pais': '1058',
            }
        return parte

    def _build_modal_rodoviario_cte(self, ct) -> dict:
        modal: dict = {
            'rntc': getattr(ct.transportadora, 'rntc', '') or '',
        }
        if ct.veiculo:
            plates = ct.veiculo.plates.order_by('-id').first()
            placa = plates.plate if plates else ''
            modal['veiculo'] = {'placa': placa, 'uf': ct.uf_inicio}
        if ct.motorista:
            modal['condutor'] = {
                'nome': ct.motorista.nome,
                'cpf': _digits(getattr(ct.motorista, 'cpf', '') or ''),
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
        from datetime import datetime
        data_str = data_enc.strftime('%Y-%m-%dT%H:%M:%S') if hasattr(data_enc, 'strftime') else str(data_enc)
        resp = requests.post(
            f'{self.base_url}/mdfe/encerra',
            json={'chave': chave, 'municipio_encerramento': municipio, 'data_encerramento': data_str},
            headers=self._headers(),
            timeout=self.TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get('sucesso') and data.get('codigo') != 103:
            raise IntegranNotasError(
                data.get('mensagem', 'Erro ao encerrar MDF-e'),
                codigo=data.get('codigo'),
                erros=data.get('erros', []),
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

    def _build_mdfe_payload(self, mdfe) -> dict:
        empresa = mdfe.empresa
        try:
            config = empresa.configuracao_fiscal
        except Exception:
            config = None

        # Agrupar documentos por município de descarregamento
        municipios: dict = {}
        for doc in mdfe.documentos_vinculados.all():
            mun = doc.municipio_descarregamento
            if mun not in municipios:
                municipios[mun] = []
            municipios[mun].append({'chave': doc.chave, 'tipo': doc.tipo})

        municipios_list = [
            {'municipio': mun, 'documentos': docs}
            for mun, docs in municipios.items()
        ]

        percursos = [{'uf': p.uf} for p in mdfe.percursos.order_by('ordem')]

        plates = mdfe.veiculo.plates.order_by('-id').first()
        placa = plates.plate if plates else ''

        payload: dict = {
            'tipo_operacao': '1',
            'serie': str(mdfe.serie),
            'numero': str(mdfe.numero),
            'data_emissao': mdfe.data_emissao.strftime('%Y-%m-%dT%H:%M:%S') if hasattr(mdfe.data_emissao, 'strftime') else str(mdfe.data_emissao),
            'emitente': self._build_emitente(empresa, config),
            'uf_inicio': mdfe.uf_inicio,
            'uf_fim': mdfe.uf_fim,
            'municipios_carregamento': [{'municipio': mdfe.municipio_carregamento}],
            'percursos': percursos,
            'municipios_descarregamento': municipios_list,
            'valores': {
                'valor_carga': str(mdfe.valor_carga),
                'unidade_medida': '01',
                'peso_bruto': str(mdfe.peso_bruto_kg),
            },
            'modal_rodoviario': {
                'veiculo': {'placa': placa, 'uf': mdfe.uf_inicio},
                'condutor': {
                    'nome': mdfe.motorista.nome,
                    'cpf': _digits(getattr(mdfe.motorista, 'cpf', '') or ''),
                },
            },
            'tipo_transporte': mdfe.tipo_transporte,
            'informacoes_adicionais_fisco': mdfe.informacoes_fisco or '',
            'informacoes_adicionais_contribuinte': mdfe.informacoes_contribuinte or '',
        }
        return payload
