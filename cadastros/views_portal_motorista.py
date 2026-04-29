"""Portal do Motorista — autenticação por matrícula+PIN, registro de abastecimentos com foto."""
from functools import wraps
from datetime import date

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import AbastecimentoPortalForm, MotoristaLoginForm, SolicitacaoManutencaoForm
from .models import (
    AbastecimentoVeiculo, FotoAbastecimento, ManutencaoVeiculo,
    Motorista, MotoristaVinculoPlaca, Vehicle,
)

LOGIN_URL = 'portal_motorista:login'
HOME_URL  = 'portal_motorista:home'


def _get_vehicles_for_motorista(motorista):
    """
    Retorna queryset de veículos vinculados ao motorista (vínculos ativos no período).
    Se não houver vínculo ativo, retorna todos os veículos da empresa como fallback.
    """
    hoje = date.today()
    vinculos = MotoristaVinculoPlaca.objects.filter(
        motorista=motorista,
        ativo=True,
    ).filter(
        Q(data_fim__isnull=True) | Q(data_fim__gte=hoje)
    ).prefetch_related('reboques__vehicle').select_related('placa_principal__vehicle')

    vehicle_ids = set()
    for v in vinculos:
        if v.placa_principal and v.placa_principal.vehicle_id:
            vehicle_ids.add(v.placa_principal.vehicle_id)
        for reboque in v.reboques.all():
            if reboque.vehicle_id:
                vehicle_ids.add(reboque.vehicle_id)

    if vehicle_ids:
        return Vehicle.objects.filter(pk__in=vehicle_ids, ativo=True).order_by('descricao', 'modelo'), True
    # Fallback: sem vínculo configurado — mostra todos da empresa
    return Vehicle.objects.filter(empresa=motorista.empresa, ativo=True).order_by('descricao', 'modelo'), False


# ──────────────────────────────────────────────────────────────────────────────
# AUTENTICAÇÃO
# ──────────────────────────────────────────────────────────────────────────────

def motorista_login_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if 'motorista_id' not in request.session:
            return redirect(LOGIN_URL)
        return view_func(request, *args, **kwargs)
    return wrapper


def _get_motorista(request):
    motorista_id = request.session.get('motorista_id')
    if not motorista_id:
        return None
    try:
        return Motorista.objects.get(pk=motorista_id, ativo=True)
    except Motorista.DoesNotExist:
        return None


def motorista_login(request):
    if request.session.get('motorista_id'):
        return redirect(HOME_URL)

    if request.method == 'POST':
        form = MotoristaLoginForm(request.POST)
        if form.is_valid():
            matricula = form.cleaned_data['matricula'].strip()
            pin = form.cleaned_data['pin'].strip()
            try:
                motorista = Motorista.objects.get(matricula=matricula, ativo=True)
                if motorista.check_pin(pin):
                    request.session['motorista_id'] = motorista.pk
                    request.session['motorista_nome'] = motorista.nome
                    messages.success(request, f'Bem-vindo, {motorista.nome}!')
                    return redirect(HOME_URL)
                else:
                    messages.error(request, 'Matrícula ou PIN incorretos.')
            except Motorista.DoesNotExist:
                messages.error(request, 'Matrícula ou PIN incorretos.')
    else:
        form = MotoristaLoginForm()

    return render(request, 'cadastros/portal_motorista/login.html', {
        'form': form,
        'title': 'Portal do Motorista',
    })


def motorista_logout(request):
    request.session.flush()
    return redirect(LOGIN_URL)


# ──────────────────────────────────────────────────────────────────────────────
# HOME / DASHBOARD
# ──────────────────────────────────────────────────────────────────────────────

@motorista_login_required
def motorista_home(request):
    motorista = _get_motorista(request)
    if not motorista:
        request.session.flush()
        return redirect(LOGIN_URL)

    ultimos_abastecimentos = AbastecimentoVeiculo.objects.filter(
        motorista=motorista
    ).select_related('vehicle').order_by('-data', '-criado_em')[:5]

    manutencoes_pendentes = ManutencaoVeiculo.objects.filter(
        motorista_solicitante=motorista,
        status__in=['ABERTA', 'EM_ANDAMENTO'],
    ).select_related('vehicle').order_by('-data_abertura')[:5]

    return render(request, 'cadastros/portal_motorista/home.html', {
        'motorista': motorista,
        'ultimos_abastecimentos': ultimos_abastecimentos,
        'manutencoes_pendentes': manutencoes_pendentes,
        'hoje': date.today(),
    })


# ──────────────────────────────────────────────────────────────────────────────
# ABASTECIMENTO
# ──────────────────────────────────────────────────────────────────────────────

@motorista_login_required
def motorista_abastecimento_novo(request):
    motorista = _get_motorista(request)
    if not motorista:
        return redirect(LOGIN_URL)

    vehicles_qs, tem_vinculo = _get_vehicles_for_motorista(motorista)

    if request.method == 'POST':
        form = AbastecimentoPortalForm(request.POST, request.FILES, empresa=motorista.empresa, vehicles_qs=vehicles_qs)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.empresa = motorista.empresa
            obj.motorista = motorista
            obj.valor_total = obj.litros * obj.preco_por_litro
            obj.save()

            foto_bomba = form.cleaned_data.get('foto_bomba')
            foto_odometro = form.cleaned_data.get('foto_odometro')
            if foto_bomba:
                FotoAbastecimento.objects.create(
                    abastecimento=obj,
                    foto_bomba=foto_bomba,
                    foto_odometro=foto_odometro or '',
                    enviada_por=motorista,
                )
            messages.success(request, 'Abastecimento registrado com sucesso!')
            return redirect(HOME_URL)
    else:
        form = AbastecimentoPortalForm(
            empresa=motorista.empresa,
            vehicles_qs=vehicles_qs,
            initial={'data': date.today()},
        )

    return render(request, 'cadastros/portal_motorista/abastecimento_novo.html', {
        'form': form,
        'motorista': motorista,
        'title': 'Registrar Abastecimento',
        'tem_vinculo': tem_vinculo,
        'total_veiculos': vehicles_qs.count(),
    })


# ──────────────────────────────────────────────────────────────────────────────
# HISTÓRICO
# ──────────────────────────────────────────────────────────────────────────────

@motorista_login_required
def motorista_historico(request):
    motorista = _get_motorista(request)
    if not motorista:
        return redirect(LOGIN_URL)

    abastecimentos = AbastecimentoVeiculo.objects.filter(
        motorista=motorista
    ).select_related('vehicle').order_by('-data', '-criado_em')[:50]

    manutencoes = ManutencaoVeiculo.objects.filter(
        motorista_solicitante=motorista
    ).select_related('vehicle').order_by('-data_abertura')[:50]

    return render(request, 'cadastros/portal_motorista/historico.html', {
        'motorista': motorista,
        'abastecimentos': abastecimentos,
        'manutencoes': manutencoes,
        'title': 'Meu Histórico',
    })


# ──────────────────────────────────────────────────────────────────────────────
# MANUTENÇÕES
# ──────────────────────────────────────────────────────────────────────────────

@motorista_login_required
def motorista_manutencao_list(request):
    motorista = _get_motorista(request)
    if not motorista:
        return redirect(LOGIN_URL)

    manutencoes = ManutencaoVeiculo.objects.filter(
        motorista_solicitante=motorista
    ).select_related('vehicle').order_by('-data_abertura')

    return render(request, 'cadastros/portal_motorista/manutencao_list.html', {
        'motorista': motorista,
        'manutencoes': manutencoes,
        'title': 'Minhas Manutenções',
    })


@motorista_login_required
def motorista_solicitar_manutencao(request):
    motorista = _get_motorista(request)
    if not motorista:
        return redirect(LOGIN_URL)

    vehicles_qs, tem_vinculo = _get_vehicles_for_motorista(motorista)

    if request.method == 'POST':
        form = SolicitacaoManutencaoForm(request.POST, empresa=motorista.empresa, vehicles_qs=vehicles_qs)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.empresa = motorista.empresa
            obj.motorista_solicitante = motorista
            obj.status = 'ABERTA'
            obj.data_abertura = date.today()
            obj.save()
            messages.success(request, 'Solicitação enviada para aprovação.')
            return redirect('portal_motorista:manutencao_list')
    else:
        form = SolicitacaoManutencaoForm(empresa=motorista.empresa, vehicles_qs=vehicles_qs)

    return render(request, 'cadastros/portal_motorista/solicitar_manutencao.html', {
        'form': form,
        'motorista': motorista,
        'title': 'Solicitar Manutenção',
        'tem_vinculo': tem_vinculo,
    })


@motorista_login_required
def motorista_manutencao_concluir(request, pk):
    motorista = _get_motorista(request)
    if not motorista:
        return redirect(LOGIN_URL)

    manutencao = get_object_or_404(ManutencaoVeiculo, pk=pk, motorista_solicitante=motorista)

    if manutencao.status == 'CONCLUIDA':
        messages.info(request, 'Esta manutenção já está concluída.')
        return redirect('portal_motorista:manutencao_list')

    if request.method == 'POST':
        manutencao.status = 'CONCLUIDA'
        manutencao.data_conclusao = date.today()
        obs_extra = request.POST.get('observacoes', '').strip()
        if obs_extra:
            manutencao.observacoes = (manutencao.observacoes + '\n' + obs_extra).strip()
        manutencao.save()
        messages.success(request, 'Manutenção marcada como concluída.')
        return redirect('portal_motorista:manutencao_list')

    return render(request, 'cadastros/portal_motorista/manutencao_concluir.html', {
        'manutencao': manutencao,
        'motorista': motorista,
        'title': 'Confirmar Conclusão',
    })
