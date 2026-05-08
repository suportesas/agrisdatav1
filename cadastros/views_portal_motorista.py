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

    _vehicles, _ = _get_vehicles_for_motorista(motorista)
    _vehicle_ids = list(_vehicles.values_list('pk', flat=True))
    manutencoes_pendentes = ManutencaoVeiculo.objects.filter(
        Q(motorista_solicitante=motorista) | Q(vehicle_id__in=_vehicle_ids),
        status__in=['ABERTA', 'EM_ANDAMENTO'],
    ).select_related('vehicle').prefetch_related('itens', 'documentos').distinct().order_by('-data_abertura')[:5]

    from exportacao.models import OrdemColeta
    ordens_pendentes_count = OrdemColeta.objects.filter(
        motorista=motorista, status='PENDENTE'
    ).count()

    return render(request, 'cadastros/portal_motorista/home.html', {
        'motorista': motorista,
        'ultimos_abastecimentos': ultimos_abastecimentos,
        'manutencoes_pendentes': manutencoes_pendentes,
        'ordens_pendentes_count': ordens_pendentes_count,
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

    _vehicles_h, _ = _get_vehicles_for_motorista(motorista)
    _vehicle_ids_h = list(_vehicles_h.values_list('pk', flat=True))
    manutencoes = ManutencaoVeiculo.objects.filter(
        Q(motorista_solicitante=motorista) | Q(vehicle_id__in=_vehicle_ids_h)
    ).select_related('vehicle').prefetch_related('itens', 'documentos').distinct().order_by('-data_abertura')[:50]

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

    _vehicles_m, _ = _get_vehicles_for_motorista(motorista)
    _vehicle_ids_m = list(_vehicles_m.values_list('pk', flat=True))
    manutencoes = ManutencaoVeiculo.objects.filter(
        Q(motorista_solicitante=motorista) | Q(vehicle_id__in=_vehicle_ids_m)
    ).select_related('vehicle').prefetch_related('itens', 'documentos').distinct().order_by('-data_abertura')

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


# ──────────────────────────────────────────────────────────────────────────────
# ORDENS DE COLETA
# ──────────────────────────────────────────────────────────────────────────────

def motorista_ordens_coleta(request):
    motorista_id = request.session.get('motorista_id')
    if not motorista_id:
        return redirect(LOGIN_URL)
    motorista = get_object_or_404(Motorista, pk=motorista_id)
    from exportacao.models import OrdemColeta
    from datetime import date as _date, timedelta

    status_filtro = request.GET.get('status', '')
    periodo_filtro = request.GET.get('periodo', '')

    ordens = OrdemColeta.objects.filter(
        motorista_id=motorista_id,
    ).select_related('booking', 'container').order_by('-data_prevista')

    if status_filtro:
        ordens = ordens.filter(status=status_filtro)

    hoje = _date.today()
    if periodo_filtro == '7d':
        ordens = ordens.filter(data_prevista__gte=hoje - timedelta(days=7))
    elif periodo_filtro == '30d':
        ordens = ordens.filter(data_prevista__gte=hoje - timedelta(days=30))
    elif periodo_filtro == 'mes':
        ordens = ordens.filter(data_prevista__year=hoje.year, data_prevista__month=hoje.month)
    elif periodo_filtro == 'proximas':
        ordens = ordens.filter(data_prevista__gte=hoje)

    contagens = {
        'PENDENTE':    OrdemColeta.objects.filter(motorista_id=motorista_id, status='PENDENTE').count(),
        'EM_ANDAMENTO': OrdemColeta.objects.filter(motorista_id=motorista_id, status='EM_ANDAMENTO').count(),
        'CONCLUIDA':   OrdemColeta.objects.filter(motorista_id=motorista_id, status='CONCLUIDA').count(),
        'total':       OrdemColeta.objects.filter(motorista_id=motorista_id).count(),
    }

    return render(request, 'cadastros/portal_motorista/ordens_coleta_list.html', {
        'ordens': ordens,
        'motorista': motorista,
        'status_filtro': status_filtro,
        'periodo_filtro': periodo_filtro,
        'contagens': contagens,
        'title': 'Minhas Ordens de Coleta',
    })


def motorista_ordem_coleta_detail(request, pk):
    motorista_id = request.session.get('motorista_id')
    if not motorista_id:
        return redirect(LOGIN_URL)
    motorista = get_object_or_404(Motorista, pk=motorista_id)
    from exportacao.models import OrdemColeta
    ordem = get_object_or_404(OrdemColeta, pk=pk, motorista_id=motorista_id)
    fotos_count = ordem.fotos.count()
    return render(request, 'cadastros/portal_motorista/ordem_coleta_detail.html', {
        'ordem': ordem,
        'motorista': motorista,
        'fotos_count': fotos_count,
        'title': f'Ordem {ordem.numero}',
    })


def motorista_ordem_coleta_print(request, pk):
    """PDF da Ordem de Coleta — autenticação via session do portal."""
    from datetime import date as _date
    from django.db.models import Q as _Q
    motorista_id = request.session.get('motorista_id')
    if not motorista_id:
        return redirect(LOGIN_URL)
    motorista = get_object_or_404(Motorista, pk=motorista_id)
    from exportacao.models import OrdemColeta
    ordem = get_object_or_404(
        OrdemColeta.objects.select_related(
            'booking', 'container', 'transportadora', 'motorista', 'empresa'
        ),
        pk=pk, motorista_id=motorista_id,
    )
    placa_principal = ''
    veiculo_principal = ''
    reboques = []
    hoje = _date.today()
    vinculo = (
        MotoristaVinculoPlaca.objects
        .filter(motorista_id=motorista_id, ativo=True)
        .filter(_Q(data_fim__isnull=True) | _Q(data_fim__gte=hoje))
        .select_related('placa_principal__vehicle')
        .prefetch_related('reboques__vehicle')
        .order_by('-data_inicio')
        .first()
    )
    if vinculo and vinculo.placa_principal:
        placa_principal = vinculo.placa_principal.placa
        v = getattr(vinculo.placa_principal, 'vehicle', None)
        if v:
            veiculo_principal = f'{v.marca} {v.modelo}'.strip()
        for rp in vinculo.reboques.select_related('vehicle').all():
            rv = rp.vehicle
            reboques.append({
                'placa': rp.placa,
                'veiculo': f'{rv.marca} {rv.modelo}'.strip() if rv else '',
            })
    return render(request, 'exportacao/ordem_coleta_print.html', {
        'ordem': ordem,
        'empresa': motorista.empresa,
        'placa_principal': placa_principal,
        'veiculo_principal': veiculo_principal,
        'reboques': reboques,
    })


def motorista_carta_temperatura(request, pk):
    """Carta de Temperatura — autenticação via session do portal."""
    motorista_id = request.session.get('motorista_id')
    if not motorista_id:
        return redirect(LOGIN_URL)
    motorista = get_object_or_404(Motorista, pk=motorista_id)
    from exportacao.models import OrdemColeta
    ordem = get_object_or_404(
        OrdemColeta.objects.select_related(
            'booking__solicitacao__cultura',
            'booking__solicitacao__navio',
            'booking__porto_origem',
            'booking__porto_destino',
            'container',
        ),
        pk=pk, motorista_id=motorista_id,
    )
    MESES = [
        'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
        'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
    ]
    from datetime import date as _date
    booking = ordem.booking
    solicitacao = getattr(booking, 'solicitacao', None)
    cultura = getattr(solicitacao, 'cultura', None) if solicitacao else None
    navio = getattr(solicitacao, 'navio', None) if solicitacao else None
    navio_nome = str(navio) if navio else ''
    rota = booking.rota_navio or ''
    to_master = ' '.join(filter(None, [navio_nome, rota])) or '—'
    commodity = str(cultura) if cultura else '—'
    porto_loading = str(booking.porto_origem) if booking.porto_origem else '—'
    porto_discharge = str(booking.porto_destino) if booking.porto_destino else '—'
    temperatura = getattr(cultura, 'exportacao_temperatura', None)
    ventilacao_raw = getattr(cultura, 'exportacao_ventilacao', None)
    humidade_raw = getattr(cultura, 'exportacao_humidade', None)
    temperatura_display = f'{temperatura}°C' if temperatura is not None else '—'
    ventilacao_display = 'OFF' if (ventilacao_raw is None or ventilacao_raw == 0) else f'{ventilacao_raw} cbm/h'
    humidade_display = 'OFF' if (humidade_raw is None or humidade_raw == 0) else f'{humidade_raw}%'
    hoje = _date.today()
    empresa = motorista.empresa
    cidade_uf = f'{empresa.cidade}/{empresa.uf}' if (empresa.cidade and empresa.uf) else (empresa.cidade or '')
    mes_nome = MESES[hoje.month - 1].upper()
    data_local = f'{cidade_uf}, {mes_nome}, {hoje.day} de {hoje.year}.'
    return render(request, 'exportacao/ordem_coleta_carta_temperatura.html', {
        'ordem': ordem,
        'empresa': empresa,
        'to_master': to_master,
        'commodity': commodity,
        'porto_loading': porto_loading,
        'porto_discharge': porto_discharge,
        'place_delivery': porto_discharge,
        'temperatura_display': temperatura_display,
        'ventilacao_display': ventilacao_display,
        'humidade_display': humidade_display,
        'data_local': data_local,
    })


def motorista_confirmar_coleta(request, pk):
    """POST: muda status PENDENTE → EM_ANDAMENTO."""
    motorista_id = request.session.get('motorista_id')
    if not motorista_id:
        return redirect(LOGIN_URL)
    from exportacao.models import OrdemColeta
    ordem = get_object_or_404(OrdemColeta, pk=pk, motorista_id=motorista_id)
    if request.method == 'POST' and ordem.status == 'PENDENTE':
        ordem.status = 'EM_ANDAMENTO'
        ordem.save(update_fields=['status'])
    return redirect('portal_motorista:ordem_coleta_detail', pk=pk)


def motorista_finalizar_coleta(request, pk):
    """POST: muda status EM_ANDAMENTO → CONCLUIDA."""
    motorista_id = request.session.get('motorista_id')
    if not motorista_id:
        return redirect(LOGIN_URL)
    from exportacao.models import OrdemColeta
    ordem = get_object_or_404(OrdemColeta, pk=pk, motorista_id=motorista_id)
    if request.method == 'POST' and ordem.status == 'EM_ANDAMENTO':
        from datetime import date as _date
        ordem.status = 'CONCLUIDA'
        ordem.data_realizada = _date.today()
        ordem.save(update_fields=['status', 'data_realizada'])
    return redirect('portal_motorista:ordem_coleta_fotos', pk=pk)


def motorista_ordem_coleta_fotos(request, pk):
    """GET: galeria de fotos + formulário de upload. POST: salva nova foto."""
    from django import forms as _forms
    motorista_id = request.session.get('motorista_id')
    if not motorista_id:
        return redirect(LOGIN_URL)
    motorista = get_object_or_404(Motorista, pk=motorista_id)
    from exportacao.models import FotoOrdemColeta, OrdemColeta
    ordem = get_object_or_404(OrdemColeta, pk=pk, motorista_id=motorista_id)

    if request.method == 'POST':
        tipo = request.POST.get('tipo', 'OUTROS')
        observacao = request.POST.get('observacao', '').strip()
        foto_file = request.FILES.get('foto')
        if foto_file:
            FotoOrdemColeta.objects.create(
                ordem=ordem,
                tipo=tipo,
                foto=foto_file,
                observacao=observacao,
                enviada_por=motorista,
            )
        return redirect('portal_motorista:ordem_coleta_fotos', pk=pk)

    fotos = ordem.fotos.select_related('enviada_por').all()
    return render(request, 'cadastros/portal_motorista/ordem_coleta_fotos.html', {
        'ordem': ordem,
        'motorista': motorista,
        'fotos': fotos,
        'tipo_choices': FotoOrdemColeta.TIPO_CHOICES,
        'title': f'Fotos — {ordem.numero}',
    })
