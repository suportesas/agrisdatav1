"""
Views para o módulo de Colheita Agrícola
Fluxo: EtapaColheita → FrotaColheita → CarrocaoFrota → ViagemColheita
"""

from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import (
    CarrocaoFrotaForm,
    EtapaColheitaForm,
    FrotaColheitaForm,
    ViagemColheitaForm,
)
from .models import (
    CarrocaoFrota, EtapaColheita, FrotaColheita, OrdemServico, ViagemColheita,
)
from cadastros.models import Talhao


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tipo_legado_os(os_obj):
    if os_obj.tipo_servico_id:
        return os_obj.tipo_servico.tipo_legado or ''
    return os_obj.tipo or ''


def _get_os_colheita(pk, empresa):
    """Retorna a OS garantindo que pertence à empresa e é do tipo COLHEITA."""
    os_obj = get_object_or_404(OrdemServico, pk=pk, empresa=empresa)
    if _tipo_legado_os(os_obj) != 'COLHEITA':
        return None
    return os_obj


# ---------------------------------------------------------------------------
# Etapas de Colheita
# ---------------------------------------------------------------------------

@login_required
def etapa_nova(request, os_pk):
    """Cria uma nova etapa de colheita para a OS."""
    empresa = request.user.empresa
    os_obj = get_object_or_404(OrdemServico, pk=os_pk, empresa=empresa)

    if _tipo_legado_os(os_obj) != 'COLHEITA':
        messages.error(request, 'Esta OS não é do tipo Colheita.')
        return redirect('operacoes_campo:os_detail', pk=os_pk)

    if os_obj.status not in ('APROVADA', 'EM_ANDAMENTO'):
        messages.error(request, 'A OS precisa estar aprovada ou em andamento para iniciar colheita.')
        return redirect('operacoes_campo:os_detail', pk=os_pk)

    # Verifica limite de etapas da cultura
    cultura = os_obj.safra.cultura if os_obj.safra_id else None
    max_etapas = cultura.max_etapas_colheita if cultura else 1
    num_existentes = EtapaColheita.objects.filter(os=os_obj).count()
    if num_existentes >= max_etapas:
        messages.error(
            request,
            f'Limite de {max_etapas} etapa(s) de colheita atingido para esta cultura.'
        )
        return redirect('operacoes_campo:os_detail', pk=os_pk)

    # Garante que a etapa anterior está concluída
    ultima = EtapaColheita.objects.filter(os=os_obj).order_by('-numero_etapa').first()
    if ultima and ultima.status != 'CONCLUIDA':
        messages.error(
            request,
            f'A {ultima.numero_etapa}ª etapa ainda está aberta. Conclua-a antes de iniciar a próxima.'
        )
        return redirect('cadastros:colheita_detalhe', os_pk=os_pk, etapa_pk=ultima.pk)

    if request.method == 'POST':
        form = EtapaColheitaForm(request.POST, empresa=empresa)
        if form.is_valid():
            etapa = form.save(commit=False)
            etapa.os = os_obj
            etapa.empresa = empresa
            etapa.talhao = os_obj.talhao
            etapa.safra = os_obj.safra
            etapa.numero_etapa = EtapaColheita.proximo_numero(os_obj)
            if not etapa.data_inicio:
                etapa.data_inicio = timezone.now()
            etapa.save()

            # Garante que a OS está em andamento
            if os_obj.status == 'APROVADA':
                os_obj.status = 'EM_ANDAMENTO'
                os_obj.data_inicio = os_obj.data_inicio or timezone.now()
                os_obj.save(update_fields=['status', 'data_inicio'])

            # Marca talhão em colheita
            talhao = os_obj.talhao
            if talhao.status == 'PLANTADO':
                talhao.status = 'COLHEITA'
                talhao.save(update_fields=['status'])

            messages.success(
                request,
                f'{etapa.numero_etapa}ª Etapa de Colheita iniciada para {os_obj.talhao.nome}!'
            )
            return redirect('cadastros:colheita_detalhe', os_pk=os_pk, etapa_pk=etapa.pk)
    else:
        form = EtapaColheitaForm(empresa=empresa)

    context = {
        'form': form,
        'os': os_obj,
        'titulo': f'Nova Etapa de Colheita — {os_obj.numero}',
        'num_existentes': num_existentes,
        'max_etapas': max_etapas,
    }
    return render(request, 'cadastros/colheita/etapa_form.html', context)


@login_required
def etapa_detalhe(request, os_pk, etapa_pk):
    """Tela principal de execução da etapa: tratores, carroções, viagens."""
    empresa = request.user.empresa
    os_obj = get_object_or_404(OrdemServico, pk=os_pk, empresa=empresa)
    etapa = get_object_or_404(EtapaColheita, pk=etapa_pk, os=os_obj)

    frotas = etapa.frotas.prefetch_related('carrocoes__viagens', 'trator', 'operador').all()

    # Totais por frota para exibir no template
    for frota in frotas:
        for carrocao in frota.carrocoes.all():
            carrocao._total_viagens = carrocao.viagens.aggregate(
                t=Sum('peso_final_kg')
            )['t'] or Decimal('0')

    # Lista de todos os carroções já selecionados (para o JS de disponibilidade)
    carrocoes_em_uso = list(
        CarrocaoFrota.objects.filter(frota__etapa=etapa).values_list('veiculo_id', flat=True)
    )

    context = {
        'os': os_obj,
        'etapa': etapa,
        'frotas': frotas,
        'carrocoes_em_uso_ids': carrocoes_em_uso,
        'frota_form': FrotaColheitaForm(empresa=empresa),
        'carrocao_form': CarrocaoFrotaForm(empresa=empresa),
        'viagem_form': ViagemColheitaForm(),
        'pode_concluir': etapa.status == 'ABERTA',
    }
    return render(request, 'cadastros/colheita/etapa_detalhe.html', context)


@login_required
def etapa_concluir(request, os_pk, etapa_pk):
    """Conclui uma etapa de colheita e, se for a última, finaliza o cultivo do talhão."""
    empresa = request.user.empresa
    os_obj = get_object_or_404(OrdemServico, pk=os_pk, empresa=empresa)
    etapa = get_object_or_404(EtapaColheita, pk=etapa_pk, os=os_obj)

    if request.method != 'POST':
        return redirect('cadastros:colheita_detalhe', os_pk=os_pk, etapa_pk=etapa_pk)

    if etapa.status == 'CONCLUIDA':
        messages.warning(request, 'Esta etapa já está concluída.')
        return redirect('cadastros:colheita_detalhe', os_pk=os_pk, etapa_pk=etapa_pk)

    # Exige pelo menos 1 viagem com peso > 0
    total = ViagemColheita.objects.filter(
        carrocao__frota__etapa=etapa, peso_final_kg__gt=0
    ).count()
    if total == 0:
        messages.error(request, 'Não é possível concluir sem registrar ao menos uma pesagem.')
        return redirect('cadastros:colheita_detalhe', os_pk=os_pk, etapa_pk=etapa_pk)

    etapa.recalcular_total()
    etapa.status = 'CONCLUIDA'
    etapa.data_fim = timezone.now()
    etapa.save()

    # Gera LoteProducao automaticamente (RF-109)
    if os_obj.safra_id and os_obj.talhao_id:
        try:
            from operacoes_campo.models import LoteProducao
            cultura = os_obj.safra.cultura if os_obj.safra_id else None
            if not LoteProducao.objects.filter(etapa_colheita=etapa).exists():
                lote = LoteProducao(
                    empresa=empresa,
                    talhao=os_obj.talhao,
                    safra=os_obj.safra,
                    cultura=cultura,
                    etapa_colheita=etapa,
                    criado_por=request.user,
                )
                lote.save()
                lote.calcular_totais()
        except Exception:
            pass  # Não bloqueia conclusão da etapa por falha no lote

    # Verifica se é a última etapa prevista
    cultura = os_obj.safra.cultura if os_obj.safra_id else None
    max_etapas = cultura.max_etapas_colheita if cultura else 1
    num_concluidas = EtapaColheita.objects.filter(os=os_obj, status='CONCLUIDA').count()

    if num_concluidas >= max_etapas:
        # Calcula produção total de todas as etapas
        producao_total = EtapaColheita.objects.filter(os=os_obj).aggregate(
            t=Sum('total_liquido_kg')
        )['t'] or Decimal('0')

        # Atualiza HistoricoTalhao se existir
        from cadastros.models import HistoricoTalhao
        historico = HistoricoTalhao.objects.filter(
            talhao=os_obj.talhao,
            safra=os_obj.safra if hasattr(HistoricoTalhao, 'safra') else None,
        ).first()
        if not historico:
            historico = HistoricoTalhao.objects.filter(
                talhao=os_obj.talhao,
            ).order_by('-data_plantio').first()

        if historico:
            historico.producao_real = producao_total
            historico.data_colheita = timezone.localdate()
            historico.save()

        # Finaliza cultivo no talhão
        os_obj.talhao.finalizar_cultivo()

        messages.success(
            request,
            f'Colheita finalizada! Total colhido: {producao_total:,.0f} kg. '
            'Talhão liberado para próximo ciclo.'
        )
    else:
        messages.success(
            request,
            f'{etapa.numero_etapa}ª etapa concluída — {etapa.total_liquido_kg:,.0f} kg. '
            f'Restam {max_etapas - num_concluidas} etapa(s).'
        )

    return redirect('operacoes_campo:os_detail', pk=os_pk)


# ---------------------------------------------------------------------------
# Frotas (AJAX — adicionar trator à etapa)
# ---------------------------------------------------------------------------

@login_required
def frota_adicionar(request, os_pk, etapa_pk):
    """Adiciona um trator à etapa via POST (pode ser AJAX)."""
    empresa = request.user.empresa
    os_obj = get_object_or_404(OrdemServico, pk=os_pk, empresa=empresa)
    etapa = get_object_or_404(EtapaColheita, pk=etapa_pk, os=os_obj)

    if etapa.status == 'CONCLUIDA':
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'erro': 'Etapa já concluída.'}, status=400)
        messages.error(request, 'Etapa já concluída.')
        return redirect('cadastros:colheita_detalhe', os_pk=os_pk, etapa_pk=etapa_pk)

    form = FrotaColheitaForm(request.POST, empresa=empresa)
    if form.is_valid():
        frota = form.save(commit=False)
        frota.etapa = etapa
        frota.save()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'ok': True,
                'frota_id': frota.pk,
                'trator_nome': str(frota.trator),
                'operador_nome': str(frota.operador) if frota.operador else '—',
            })
        messages.success(request, f'Trator {frota.trator} adicionado.')
    else:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'erros': form.errors}, status=400)
        messages.error(request, 'Erro ao adicionar trator. Verifique os dados.')

    return redirect('cadastros:colheita_detalhe', os_pk=os_pk, etapa_pk=etapa_pk)


@login_required
def frota_horimetro_final(request, os_pk, etapa_pk, frota_pk):
    """Atualiza o horímetro final do trator ao encerrar a etapa."""
    empresa = request.user.empresa
    os_obj = get_object_or_404(OrdemServico, pk=os_pk, empresa=empresa)
    etapa = get_object_or_404(EtapaColheita, pk=etapa_pk, os=os_obj)
    frota = get_object_or_404(FrotaColheita, pk=frota_pk, etapa=etapa)

    if request.method == 'POST':
        valor = request.POST.get('horimetro_final', '').strip()
        try:
            frota.horimetro_final = Decimal(valor)
            frota.full_clean()
            frota.save(update_fields=['horimetro_final'])
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'ok': True})
            messages.success(request, 'Horímetro final salvo.')
        except Exception as e:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'ok': False, 'erro': str(e)}, status=400)
            messages.error(request, f'Erro: {e}')

    return redirect('cadastros:colheita_detalhe', os_pk=os_pk, etapa_pk=etapa_pk)


# ---------------------------------------------------------------------------
# Carroções (AJAX — adicionar carroção a um trator)
# ---------------------------------------------------------------------------

@login_required
def carrocao_adicionar(request, os_pk, etapa_pk, frota_pk):
    """Adiciona um carroção a uma frota (trator) via POST."""
    empresa = request.user.empresa
    os_obj = get_object_or_404(OrdemServico, pk=os_pk, empresa=empresa)
    etapa = get_object_or_404(EtapaColheita, pk=etapa_pk, os=os_obj)
    frota = get_object_or_404(FrotaColheita, pk=frota_pk, etapa=etapa)

    if etapa.status == 'CONCLUIDA':
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'erro': 'Etapa já concluída.'}, status=400)
        messages.error(request, 'Etapa já concluída.')
        return redirect('cadastros:colheita_detalhe', os_pk=os_pk, etapa_pk=etapa_pk)

    form = CarrocaoFrotaForm(request.POST, empresa=empresa)
    if form.is_valid():
        carrocao = form.save(commit=False)
        carrocao.frota = frota
        # Auto-preenche identificação e medidas do cadastro do Vehicle se não informadas
        veiculo = carrocao.veiculo
        if not carrocao.numero_identificacao:
            carrocao.numero_identificacao = veiculo.descricao or str(veiculo)
        if not carrocao.capacidade_ton and veiculo.capacidade_ton:
            carrocao.capacidade_ton = veiculo.capacidade_ton
        if not carrocao.tara_kg and veiculo.tara_kg:
            carrocao.tara_kg = veiculo.tara_kg
        try:
            carrocao.full_clean()
            carrocao.save()
        except Exception as e:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'ok': False, 'erro': str(e)}, status=400)
            messages.error(request, str(e))
            return redirect('cadastros:colheita_detalhe', os_pk=os_pk, etapa_pk=etapa_pk)

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'ok': True,
                'carrocao_id': carrocao.pk,
                'frota_id': frota.pk,
                'veiculo_id': carrocao.veiculo_id,
                'identificacao': carrocao.numero_identificacao,
                'capacidade': str(carrocao.capacidade_ton or '—'),
                'tara': carrocao.tara_kg or 0,
            })
        messages.success(request, f'Carroção {carrocao.numero_identificacao} adicionado.')
    else:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'erros': form.errors}, status=400)
        messages.error(request, 'Erro ao adicionar carroção.')

    return redirect('cadastros:colheita_detalhe', os_pk=os_pk, etapa_pk=etapa_pk)


@login_required
def carrocao_remover(request, os_pk, etapa_pk, carrocao_pk):
    """Remove um carroção da frota (só se não tiver viagens registradas)."""
    empresa = request.user.empresa
    os_obj = get_object_or_404(OrdemServico, pk=os_pk, empresa=empresa)
    etapa = get_object_or_404(EtapaColheita, pk=etapa_pk, os=os_obj)
    carrocao = get_object_or_404(CarrocaoFrota, pk=carrocao_pk, frota__etapa=etapa)

    if request.method == 'POST':
        if carrocao.viagens.exists():
            messages.error(request, 'Não é possível remover um carroção que já possui viagens registradas.')
        else:
            carrocao.delete()
            messages.success(request, 'Carroção removido.')

    return redirect('cadastros:colheita_detalhe', os_pk=os_pk, etapa_pk=etapa_pk)


# ---------------------------------------------------------------------------
# Viagens / Pesagens
# ---------------------------------------------------------------------------

@login_required
def viagem_nova(request, os_pk, etapa_pk, carrocao_pk):
    """Registra uma nova viagem/pesagem para um carroção."""
    empresa = request.user.empresa
    os_obj = get_object_or_404(OrdemServico, pk=os_pk, empresa=empresa)
    etapa = get_object_or_404(EtapaColheita, pk=etapa_pk, os=os_obj)
    carrocao = get_object_or_404(CarrocaoFrota, pk=carrocao_pk, frota__etapa=etapa)

    if etapa.status == 'CONCLUIDA':
        messages.error(request, 'Etapa já concluída — não é possível adicionar viagens.')
        return redirect('cadastros:colheita_detalhe', os_pk=os_pk, etapa_pk=etapa_pk)

    if request.method == 'POST':
        form = ViagemColheitaForm(request.POST, request.FILES)
        if form.is_valid():
            viagem = form.save(commit=False)
            viagem.carrocao = carrocao
            viagem.numero_viagem = ViagemColheita.proximo_numero(carrocao)
            # Tara padrão do carroção se não informada
            if not viagem.tara_usada_kg:
                viagem.tara_usada_kg = Decimal(carrocao.tara_kg or 0)
            viagem.save()

            total_carrocao = carrocao.viagens.aggregate(t=Sum('peso_final_kg'))['t'] or Decimal('0')

            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'ok': True,
                    'viagem_id': viagem.pk,
                    'carrocao_id': carrocao.pk,
                    'numero': viagem.numero_viagem,
                    'peso_bruto': str(viagem.peso_bruto_kg),
                    'tara': str(viagem.tara_usada_kg),
                    'peso_liquido': str(viagem.peso_liquido_kg),
                    'desconto': str(viagem.desconto_kg),
                    'peso_final': str(viagem.peso_final_kg),
                    'total_carrocao': str(total_carrocao),
                    'total_etapa': str(etapa.total_liquido_kg),
                })
            messages.success(
                request,
                f'Viagem {viagem.numero_viagem} registrada — {viagem.peso_final_kg:,.0f} kg.'
            )
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'ok': False, 'erros': form.errors}, status=400)
            messages.error(request, 'Erro ao registrar viagem. Verifique os dados.')
    else:
        form = ViagemColheitaForm(initial={'tara_usada_kg': carrocao.tara_kg or 0})

    return redirect('cadastros:colheita_detalhe', os_pk=os_pk, etapa_pk=etapa_pk)


@login_required
def viagem_editar(request, os_pk, etapa_pk, viagem_pk):
    """Edita uma viagem já registrada (somente se etapa ainda ABERTA)."""
    empresa = request.user.empresa
    os_obj = get_object_or_404(OrdemServico, pk=os_pk, empresa=empresa)
    etapa = get_object_or_404(EtapaColheita, pk=etapa_pk, os=os_obj)
    viagem = get_object_or_404(ViagemColheita, pk=viagem_pk, carrocao__frota__etapa=etapa)

    if etapa.status == 'CONCLUIDA':
        messages.error(request, 'Etapa concluída — não é possível editar viagens.')
        return redirect('cadastros:colheita_detalhe', os_pk=os_pk, etapa_pk=etapa_pk)

    if request.method == 'POST':
        form = ViagemColheitaForm(request.POST, request.FILES, instance=viagem)
        if form.is_valid():
            form.save()
            messages.success(request, f'Viagem {viagem.numero_viagem} atualizada.')
            return redirect('cadastros:colheita_detalhe', os_pk=os_pk, etapa_pk=etapa_pk)
    else:
        form = ViagemColheitaForm(instance=viagem)

    context = {
        'form': form,
        'os': os_obj,
        'etapa': etapa,
        'viagem': viagem,
    }
    return render(request, 'cadastros/colheita/viagem_form.html', context)


@login_required
def viagem_excluir(request, os_pk, etapa_pk, viagem_pk):
    """Exclui uma viagem (somente se etapa ainda ABERTA)."""
    empresa = request.user.empresa
    os_obj = get_object_or_404(OrdemServico, pk=os_pk, empresa=empresa)
    etapa = get_object_or_404(EtapaColheita, pk=etapa_pk, os=os_obj)
    viagem = get_object_or_404(ViagemColheita, pk=viagem_pk, carrocao__frota__etapa=etapa)

    if request.method == 'POST':
        if etapa.status == 'CONCLUIDA':
            messages.error(request, 'Etapa concluída — operação não permitida.')
        else:
            viagem.delete()
            etapa.recalcular_total()
            messages.success(request, 'Viagem excluída.')

    return redirect('cadastros:colheita_detalhe', os_pk=os_pk, etapa_pk=etapa_pk)


# ---------------------------------------------------------------------------
# AJAX: Lista de carroções disponíveis (para feedback de disponibilidade)
# ---------------------------------------------------------------------------

@login_required
def ajax_carrocoes_disponiveis(request, os_pk, etapa_pk):
    """
    Retorna todos os veículos REBOQUE da empresa com status se já estão na etapa.
    Usado pelo JS para marcar [EM USO] nos selects.
    GET /colheita/<etapa_pk>/ajax/carrocoes/
    """
    empresa = request.user.empresa
    os_obj = get_object_or_404(OrdemServico, pk=os_pk, empresa=empresa)
    etapa = get_object_or_404(EtapaColheita, pk=etapa_pk, os=os_obj)

    from frota.models import Vehicle as Veh

    em_uso_ids = set(
        CarrocaoFrota.objects.filter(frota__etapa=etapa).values_list('veiculo_id', flat=True)
    )

    veiculos = Veh.objects.filter(empresa=empresa, ativo=True, tipo='REBOQUE').order_by('descricao')
    resultado = []
    for v in veiculos:
        resultado.append({
            'id': v.pk,
            'nome': v.descricao or str(v),
            'capacidade_ton': str(v.capacidade_ton or ''),
            'tara_kg': v.tara_kg or 0,
            'em_uso': v.pk in em_uso_ids,
        })

    return JsonResponse({'carrocoes': resultado})
