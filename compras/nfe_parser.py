from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import xmltodict


class NFEImportError(Exception):
    """Raised when the XML content cannot be parsed into NF-e data."""


@dataclass(frozen=True)
class ParsedNFEItem:
    codigo_fornecedor: str
    codigo_barras: str
    nome: str
    quantidade: Decimal
    preco_unitario: Decimal
    unidade: str
    ncm: str
    cfop: str


def _ensure_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _to_decimal(value: Any, default: str = '0') -> Decimal:
    raw_value = value if value not in (None, '') else default
    try:
        return Decimal(str(raw_value).strip())
    except (InvalidOperation, ValueError) as exc:
        raise NFEImportError(f'Valor decimal invalido no XML: {raw_value}') from exc


def _extract_date(raw_value: str) -> str:
    if not raw_value:
        raise NFEImportError('Data de emissao nao encontrada no XML.')

    raw_value = str(raw_value).strip()
    if 'T' in raw_value:
        return datetime.fromisoformat(raw_value.replace('Z', '+00:00')).date().isoformat()
    return datetime.strptime(raw_value[:10], '%Y-%m-%d').date().isoformat()


def _normalize_document(value: str) -> str:
    return ''.join(char for char in str(value or '') if char.isdigit())


def _normalize_barcode(value: str) -> str:
    normalized = str(value or '').strip()
    if not normalized:
        return ''
    if normalized.upper().startswith('SEM GTIN'):
        return ''
    return ''.join(char for char in normalized if char.isdigit())


def parse_nfe_xml(xml_content: str) -> dict[str, Any]:
    try:
        document = xmltodict.parse(xml_content)
    except Exception as exc:
        raise NFEImportError(f'XML invalido: {exc}') from exc

    root = document.get('nfeProc') or document.get('NFe')
    if not root:
        raise NFEImportError('Estrutura NF-e nao reconhecida.')

    nfe_root = root.get('NFe', root)
    inf_nfe = nfe_root.get('infNFe')
    if not inf_nfe:
        raise NFEImportError('Bloco infNFe nao encontrado no XML.')

    ide = inf_nfe.get('ide') or {}
    emit = inf_nfe.get('emit') or {}
    total = ((inf_nfe.get('total') or {}).get('ICMSTot') or (inf_nfe.get('total') or {}).get('ICMStot') or {})
    detalhes = _ensure_list(inf_nfe.get('det'))

    if not detalhes:
        raise NFEImportError('Nenhum item de produto encontrado no XML.')

    prot_nfe = root.get('protNFe') or {}
    inf_prot = prot_nfe.get('infProt') or {}

    chave_nfe = inf_prot.get('chNFe', '')
    if not chave_nfe:
        inf_nfe_id = inf_nfe.get('@Id') or inf_nfe.get('Id') or ''
        if str(inf_nfe_id).startswith('NFe'):
            chave_nfe = str(inf_nfe_id)[3:]

    produtos: list[dict[str, Any]] = []
    for item in detalhes:
        prod = item.get('prod') or {}
        parsed_item = ParsedNFEItem(
            codigo_fornecedor=str(prod.get('cProd') or '').strip(),
            codigo_barras=_normalize_barcode(prod.get('cEAN') or prod.get('cEANTrib') or ''),
            nome=str(prod.get('xProd') or '').strip(),
            quantidade=_to_decimal(prod.get('qCom') or prod.get('qTrib')),
            preco_unitario=_to_decimal(prod.get('vUnCom') or prod.get('vUnTrib')),
            unidade=str(prod.get('uCom') or prod.get('uTrib') or '').strip(),
            ncm=str(prod.get('NCM') or '').strip(),
            cfop=str(prod.get('CFOP') or '').strip(),
        )
        if not parsed_item.nome:
            raise NFEImportError('Item do XML sem descricao de produto.')
        produtos.append(
            {
                'codigo_fornecedor': parsed_item.codigo_fornecedor,
                'codigo_barras': parsed_item.codigo_barras,
                'nome': parsed_item.nome,
                'quantidade': str(parsed_item.quantidade),
                'preco_unitario': str(parsed_item.preco_unitario),
                'unidade': parsed_item.unidade,
                'ncm': parsed_item.ncm,
                'cfop': parsed_item.cfop,
            }
        )

    fornecedor_nome = str(emit.get('xNome') or '').strip()
    fornecedor_documento = _normalize_document(emit.get('CNPJ') or emit.get('CPF') or '')
    valor_total_nf = _to_decimal(total.get('vNF'))

    return {
        'fornecedor_nome': fornecedor_nome,
        'fornecedor_documento': fornecedor_documento,
        'nota_fiscal': str(ide.get('nNF') or '').strip(),
        'serie_nota': str(ide.get('serie') or '1').strip() or '1',
        'chave_nfe': _normalize_document(chave_nfe),
        'data_emissao_nf': _extract_date(ide.get('dhEmi') or ide.get('dEmi') or ''),
        'valor_total_nf': f"{valor_total_nf:.2f}",
        'valor_frete': f"{_to_decimal(total.get('vFrete')):.2f}",
        'valor_desconto': f"{_to_decimal(total.get('vDesc')):.2f}",
        'produtos': produtos,
        'xml_resumo': {
            'fornecedor': fornecedor_nome or 'Nao identificado',
            'documento': fornecedor_documento or 'Nao informado',
            'itens': len(produtos),
            'valor_total_nf': f"{valor_total_nf:.2f}",
        },
    }