from django.db import transaction

from .models import EtiquetaAvulsa, LoteEtiquetaAvulsa


def criar_lote_com_etiquetas(lote, empresa):
    """Salva o lote (ainda não persistido) e gera as N EtiquetaAvulsa filhas
    atomicamente, uma por pallet, com códigos sequenciais únicos.

    Com safra informada (lote.safra_codigo), o código de cada pallet é
    contínuo dentro da safra (reinicia só quando a safra muda). Sem safra,
    mantém o esquema genérico anterior: um código-base por lote, sufixado
    -1, -2, ... para cada pallet.
    """
    with transaction.atomic():
        lote.empresa = empresa
        lote.numero_lote = LoteEtiquetaAvulsa._gerar_numero(empresa)
        lote.save()

        prefixo_safra = lote.safra_codigo
        if prefixo_safra:
            for seq in range(1, lote.total_pallets + 1):
                codigo = EtiquetaAvulsa._gerar_codigo_por_safra(empresa, prefixo_safra)
                EtiquetaAvulsa.objects.create(
                    empresa=empresa,
                    lote=lote,
                    codigo_pallet=codigo,
                    numero_sequencial=seq,
                    caixas=lote.caixas_por_pallet,
                )
        else:
            base = EtiquetaAvulsa._gerar_codigo_base(empresa)
            for seq in range(1, lote.total_pallets + 1):
                EtiquetaAvulsa.objects.create(
                    empresa=empresa,
                    lote=lote,
                    codigo_pallet=f'{base}-{seq}',
                    numero_sequencial=seq,
                    caixas=lote.caixas_por_pallet,
                )
    return lote
