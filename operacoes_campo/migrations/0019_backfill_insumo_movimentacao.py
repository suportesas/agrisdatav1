from django.db import migrations


def backfill_movimentacao(apps, schema_editor):
    """
    Vincula os insumos de OS já concluídas (antes desta mudança) à
    MovimentacaoEstoque 'OS_DIRETA' correspondente, já executada na época.
    Sem esse vínculo, `estoque.disponibilidade.reservas_por_produto` passaria
    a considerar esses itens como reserva pendente para sempre, já que não
    tem como diferenciar "baixa já feita antes desta mudança" de "aguardando
    o almoxarifado" apenas pelo status da OS.
    """
    OrdemServicoInsumo = apps.get_model('operacoes_campo', 'OrdemServicoInsumo')
    MovimentacaoEstoque = apps.get_model('estoque', 'MovimentacaoEstoque')

    itens = OrdemServicoInsumo.objects.filter(
        os__status='CONCLUIDA',
        quantidade_aplicada__gt=0,
        movimentacao__isnull=True,
    ).select_related('os').order_by('os_id', 'produto_id', 'id')

    usados = set()
    for item in itens:
        candidata = MovimentacaoEstoque.objects.filter(
            empresa_id=item.empresa_id,
            produto_id=item.produto_id,
            documento=item.os.numero,
            origem='OS_DIRETA',
            tipo='SAIDA',
        ).exclude(id__in=usados).order_by('id').first()
        if candidata:
            item.movimentacao_id = candidata.id
            item.save(update_fields=['movimentacao'])
            usados.add(candidata.id)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('operacoes_campo', '0018_ordemservicoinsumo_movimentacao'),
    ]

    operations = [
        migrations.RunPython(backfill_movimentacao, noop_reverse),
    ]
