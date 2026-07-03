from django.db import transaction
from django.db.models import Max

from .models import EtiquetaAvulsa, LoteEtiquetaAvulsa

# Campos que passam direto (podem ser None): FKs e decimais.
CAMPOS_PRODUTO_DIRETOS = ('produto', 'cultura', 'marca', 'peso_liquido_cx', 'peso_bruto_cx')
# Campos de texto: viram '' quando ausentes.
CAMPOS_PRODUTO_TEXTO = (
    'produto_texto', 'variedade', 'embalagem', 'marca_texto', 'cultivares',
    'tipo_size', 'temperatura', 'carimbo',
)


class LoteConcluidoError(Exception):
    """Levantado ao tentar adicionar pallets a um lote já CONCLUIDA."""


def _base_existente_do_lote(lote):
    """Deriva o código-base já usado pelos pallets deste lote (esquema sem
    safra), a partir do codigo_pallet de um pallet já existente
    (ex: '100003-2' -> '100003'). Retorna None se o lote ainda não tem
    nenhum pallet."""
    ultima = lote.etiquetas.order_by('-numero_sequencial').first()
    if ultima and '-' in ultima.codigo_pallet:
        return ultima.codigo_pallet.rsplit('-', 1)[0]
    return None


def _criar_etiquetas_para_lote(lote, empresa, quantidade, seq_inicio, item_data):
    """Núcleo comum de geração: cria `quantidade` EtiquetaAvulsa a partir de
    numero_sequencial=seq_inicio, todas com a especificação de produto de
    `item_data` (uma leva = um produto), usando o esquema de código de
    barras correto (prefixo de safra contínuo entre lotes, ou base genérica
    reaproveitada/gerada por lote)."""
    campos_produto = {campo: item_data.get(campo) for campo in CAMPOS_PRODUTO_DIRETOS}
    campos_produto.update({campo: item_data.get(campo) or '' for campo in CAMPOS_PRODUTO_TEXTO})
    caixas = item_data['caixas_por_pallet']

    prefixo_safra = lote.safra_codigo
    if prefixo_safra:
        for i in range(quantidade):
            codigo = EtiquetaAvulsa._gerar_codigo_por_safra(empresa, prefixo_safra)
            EtiquetaAvulsa.objects.create(
                empresa=empresa, lote=lote, codigo_pallet=codigo,
                numero_sequencial=seq_inicio + i, caixas=caixas, **campos_produto,
            )
    else:
        base = _base_existente_do_lote(lote) or EtiquetaAvulsa._gerar_codigo_base(empresa)
        for i in range(quantidade):
            EtiquetaAvulsa.objects.create(
                empresa=empresa, lote=lote, codigo_pallet=f'{base}-{seq_inicio + i}',
                numero_sequencial=seq_inicio + i, caixas=caixas, **campos_produto,
            )


def criar_lote_com_etiquetas(lote, empresa, quantidade, item_data):
    """Salva o cabeçalho do lote (ainda não persistido) e gera a primeira
    leva de `quantidade` pallets com a especificação de produto de
    `item_data`. Mais levas (possivelmente de outro produto) podem ser
    adicionadas depois via `adicionar_pallets`."""
    with transaction.atomic():
        lote.empresa = empresa
        lote.numero_lote = LoteEtiquetaAvulsa._gerar_numero(empresa)
        lote.total_pallets = 0
        lote.save()
    return adicionar_pallets(lote, empresa, quantidade, item_data)


def adicionar_pallets(lote, empresa, quantidade, item_data):
    """Adiciona `quantidade` pallets com a especificação de produto de
    `item_data` a um lote ABERTA já existente, continuando a numeração
    própria do lote e o esquema de código de barras (base do lote sem
    safra / contador contínuo da safra). Levanta LoteConcluidoError se o
    lote já estiver CONCLUIDA. Retorna o lote atualizado — use-o em vez da
    referência original, já que o total_pallets/status pode ter mudado."""
    if quantidade < 1:
        raise ValueError('quantidade deve ser >= 1')
    with transaction.atomic():
        lote = LoteEtiquetaAvulsa.objects.select_for_update().get(pk=lote.pk)
        if lote.status == 'CONCLUIDA':
            raise LoteConcluidoError(f'Lote {lote.numero_lote} já concluído.')
        ultimo_seq = lote.etiquetas.aggregate(m=Max('numero_sequencial'))['m'] or 0
        _criar_etiquetas_para_lote(lote, empresa, quantidade, ultimo_seq + 1, item_data)
        lote.total_pallets += quantidade
        lote.save(update_fields=['total_pallets'])
    return lote


def concluir_lote(lote):
    """Marca o lote como CONCLUIDA. Idempotente."""
    with transaction.atomic():
        lote = LoteEtiquetaAvulsa.objects.select_for_update().get(pk=lote.pk)
        if lote.status != 'CONCLUIDA':
            lote.status = 'CONCLUIDA'
            lote.save(update_fields=['status'])
    return lote
