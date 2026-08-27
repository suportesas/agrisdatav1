"""Serviços do módulo Frota: cálculo de margem, integração financeira."""
from datetime import date, timedelta
from decimal import Decimal


def calcular_margem_viagem(viagem):
    """Retorna dict com breakdown de custos e margem da viagem."""
    from frota.models import AbastecimentoVeiculo, PedagioVeiculo, ManutencaoVeiculo

    frete = viagem.valor_frete or Decimal('0')

    abastecimentos = AbastecimentoVeiculo.objects.filter(empresa=viagem.transportadora.empresa)
    # Tenta associar pelo vehicle e data da viagem (mesmo dia ou viagem FK futura)
    custo_combustivel = Decimal('0')
    custo_pedagio = Decimal('0')
    custo_manutencao = Decimal('0')

    pedagios = PedagioVeiculo.objects.filter(viagem=viagem)
    custo_pedagio = sum(p.valor for p in pedagios) or Decimal('0')

    manutencoes = ManutencaoVeiculo.objects.filter(
        vehicle=viagem.vehicle,
        data_abertura=viagem.data,
        status='CONCLUIDA',
    ) if viagem.vehicle else []
    custo_manutencao = sum(m.valor_total for m in manutencoes) if manutencoes else Decimal('0')

    if viagem.vehicle:
        abast = AbastecimentoVeiculo.objects.filter(vehicle=viagem.vehicle, data=viagem.data)
        custo_combustivel = sum(a.valor_total for a in abast) or Decimal('0')

    custo_total = custo_combustivel + custo_pedagio + custo_manutencao
    margem_bruta = frete - custo_total
    margem_pct = (margem_bruta / frete * 100).quantize(Decimal('0.01')) if frete else None

    km = viagem.km_percorrido
    custo_por_km = (custo_total / km).quantize(Decimal('0.01')) if km else None

    return {
        'frete': frete,
        'custo_combustivel': custo_combustivel,
        'custo_pedagio': custo_pedagio,
        'custo_manutencao': custo_manutencao,
        'custo_total': custo_total,
        'margem_bruta': margem_bruta,
        'margem_pct': margem_pct,
        'km_percorrido': km,
        'custo_por_km': custo_por_km,
    }


def gerar_alertas_manutencao(empresa):
    """Verifica manutenções com proxima_data/proximo_km próximos e cria AlertaManutencao."""
    from frota.models import ManutencaoVeiculo, AlertaManutencao

    hoje = date.today()
    limite_data = hoje + timedelta(days=7)

    criados = 0
    manutencoes_com_data = ManutencaoVeiculo.objects.filter(
        empresa=empresa,
        status='CONCLUIDA',
        proxima_data__isnull=False,
        proxima_data__lte=limite_data,
    )
    for m in manutencoes_com_data:
        existe = AlertaManutencao.objects.filter(
            manutencao_origem=m, tipo_gatilho__in=['DATA', 'AMBOS'], status='PENDENTE'
        ).exists()
        if not existe:
            AlertaManutencao.objects.create(
                empresa=empresa,
                vehicle=m.vehicle,
                manutencao_origem=m,
                tipo_gatilho='DATA',
                descricao=f"{m.descricao} — próxima em {m.proxima_data.strftime('%d/%m/%Y')}",
                data_alerta=hoje,
            )
            criados += 1
    return criados


def criar_conta_pagar_abastecimento(abastecimento, data_vencimento=None):
    """Cria ContaPagar a partir de um abastecimento. Retorna a instância criada."""
    from financeiro.models import ContaPagar
    import uuid

    if not abastecimento.fornecedor:
        raise ValueError('Fornecedor é obrigatório para gerar Conta a Pagar.')

    numero = f'COMB-{abastecimento.pk:06d}-{uuid.uuid4().hex[:6].upper()}'
    venc = data_vencimento or abastecimento.data

    cp = ContaPagar.objects.create(
        empresa=abastecimento.empresa,
        fornecedor=abastecimento.fornecedor,
        numero=numero,
        valor_total=abastecimento.valor_total,
        data_emissao=abastecimento.data,
        observacoes=f'Abastecimento — {abastecimento.vehicle} — {abastecimento.litros}L '
                    f'{abastecimento.get_tipo_combustivel_display()} em {abastecimento.local_abastecimento}',
        criado_por=abastecimento.criado_por,
    )
    abastecimento.conta_pagar = cp
    abastecimento.save(update_fields=['conta_pagar'])
    return cp


def criar_baixa_estoque_abastecimento(abastecimento, usuario):
    """Gera e executa a MovimentacaoEstoque (SAIDA) do combustível abastecido. Retorna a movimentação criada."""
    from estoque.services import criar_movimentacao

    if not abastecimento.lote_combustivel:
        raise ValueError('Selecione um lote de combustível para gerar a baixa de estoque.')

    mov = criar_movimentacao(
        empresa=abastecimento.empresa,
        tipo='SAIDA',
        origem='ABASTECIMENTO',
        quantidade=abastecimento.litros,
        usuario=usuario,
        lote=abastecimento.lote_combustivel,
        documento=f'ABAST-{abastecimento.pk}',
        observacao=(f'Abastecimento — {abastecimento.vehicle} — {abastecimento.litros}L '
                    f'{abastecimento.get_tipo_combustivel_display()} em {abastecimento.local_abastecimento}'),
    )
    abastecimento.movimentacao_estoque = mov
    abastecimento.save(update_fields=['movimentacao_estoque'])
    return mov


def criar_conta_pagar_manutencao(manutencao, data_vencimento=None):
    """Cria ContaPagar a partir de uma manutenção externa. Retorna a instância criada."""
    from financeiro.models import ContaPagar
    import uuid

    if not manutencao.fornecedor_externo:
        raise ValueError('Fornecedor externo é obrigatório para gerar Conta a Pagar.')

    numero = f'MAN-{manutencao.pk:06d}-{uuid.uuid4().hex[:6].upper()}'
    venc = data_vencimento or (manutencao.data_conclusao or manutencao.data_abertura)

    cp = ContaPagar.objects.create(
        empresa=manutencao.empresa,
        fornecedor=manutencao.fornecedor_externo,
        numero=numero,
        valor_total=manutencao.valor_total,
        data_emissao=manutencao.data_abertura,
        observacoes=f'Manutenção — {manutencao.vehicle} — {manutencao.descricao}',
        criado_por=manutencao.criado_por,
    )
    manutencao.conta_pagar = cp
    manutencao.save(update_fields=['conta_pagar'])
    return cp
