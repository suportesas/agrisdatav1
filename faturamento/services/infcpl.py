"""Geração automática do texto de "Informações Complementares" (infCpl) da NF-e.

Monta o texto de isenção de ICMS + dados de rastreabilidade/drawback/embarque
a partir de um texto-base configurável por empresa (`ConfiguracaoFiscal.texto_isencao_icms`).
O mesmo texto-base é usado nos dois casos — mercado interno e exportação — o que muda
é o que é anexado depois dele.
"""


def montar_texto_infcpl_interna(*, texto_base, numero_rastreabilidade):
    """Mercado interno: texto-base + número de rastreabilidade."""
    partes = [texto_base.strip()] if texto_base and texto_base.strip() else []
    if numero_rastreabilidade:
        partes.append(f'RASTREABILIDADE: {numero_rastreabilidade}.')
    return ' '.join(partes)


def montar_texto_infcpl_exportacao(*, texto_base, ato_concessorio=None, produtos_desc='',
                                     booking='', navio='', numero_container='',
                                     lacre_fiscal='', tara_container=None, lacre_g7='',
                                     numero_tale='', numero_rastreabilidade='',
                                     ptax_eur=None, ptax_data=''):
    """Exportação: texto-base + DRAWBACK + bloco de embarque (booking/navio/container/
    lacres/tara/TALE/PTAX/rastreabilidade). Cada dado só entra no texto se estiver
    disponível — a ausência de um dado não impede a geração do restante.
    """
    partes = [texto_base.strip()] if texto_base and texto_base.strip() else []

    if ato_concessorio is not None:
        data_fim = ato_concessorio.data_fim_efetiva
        drawback = f'DRAWBACK INTEGRADO:{ato_concessorio.numero_ac} DE {ato_concessorio.data_inicio:%d/%m/%Y}'
        if data_fim:
            drawback += f' valido {data_fim:%d/%m/%Y}'
        partes.append(drawback + '.')

    bloco = []
    if produtos_desc:
        bloco.append(f'PRODUTO {produtos_desc}')
    bloco.append('CERTIFICADO')
    if booking:
        bloco.append(f'BOOKING: {booking}')
    if navio:
        bloco.append(f'NAVIO: {navio}')
    if numero_container:
        bloco.append(f'CONTAINER: {numero_container}')
    if lacre_fiscal:
        bloco.append(f'LACRE: {lacre_fiscal}')
    if tara_container:
        bloco.append(f'TARA: {tara_container}')
    if lacre_g7:
        bloco.append(f'G7: {lacre_g7}')
    if numero_tale:
        bloco.append(f'TEMP.TALE: {numero_tale}')
    if ptax_eur is not None and ptax_data:
        valor_fmt = f'{ptax_eur:.4f}'.replace('.', ',')
        bloco.append(f'VALOR DO PTAX DO EURO DIA {ptax_data} R$: {valor_fmt}')
    if numero_rastreabilidade:
        bloco.append(f'RASTREABILIDADE: {numero_rastreabilidade}')

    if bloco:
        partes.append(' - '.join(bloco) + '.')

    return ' '.join(partes)
