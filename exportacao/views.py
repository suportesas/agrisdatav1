import io

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import get_template
from django.utils import timezone
from django.views.decorators.http import require_POST
from xhtml2pdf import pisa

from cadastros.models import Cultura, Transportadora
from frota.models import Motorista, MotoristaVinculoPlaca
from .forms import BookingContainerForm, BookingForm, ContainerTransferenciaForm, OrdemColetaForm, SolicitacaoBookingForm
from .models import Booking, BookingContainer, BookingContainerHistory, BookingHistory, OrdemColeta, SolicitacaoBooking


@login_required
def solicitacao_booking_list(request):
    if not request.user.empresa:
        messages.warning(request, '⚠️ Seu usuário não está vinculado a nenhuma empresa.')
        return redirect('dashboard:index')

    qs = SolicitacaoBooking.objects.filter(
        empresa=request.user.empresa
    ).select_related('cultura', 'armador', 'porto_origem', 'porto_destino', 'navio').order_by('-data_solicitacao')

    search = request.GET.get('search', '').strip()
    if search:
        qs = qs.filter(
            Q(nome__icontains=search) |
            Q(cultura__nome__icontains=search) |
            Q(armador__nome__icontains=search) |
            Q(navio__nome__icontains=search)
        )

    status_filter = request.GET.get('status', '')
    if status_filter:
        qs = qs.filter(status=status_filter)

    embarque_de = request.GET.get('embarque_de', '')
    if embarque_de:
        qs = qs.filter(data_prevista_embarque__gte=embarque_de)

    embarque_ate = request.GET.get('embarque_ate', '')
    if embarque_ate:
        qs = qs.filter(data_prevista_embarque__lte=embarque_ate)

    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'exportacao/solicitacao_booking_list.html', {
        'solicitacoes': page_obj,
        'page_obj': page_obj,
        'search': search,
        'status_filter': status_filter,
        'embarque_de': embarque_de,
        'embarque_ate': embarque_ate,
        'status_choices': SolicitacaoBooking.STATUS,
        'request': request,
    })


@login_required
def solicitacao_booking_detail(request, pk):
    solicitacao = get_object_or_404(SolicitacaoBooking, pk=pk, empresa=request.user.empresa)
    return render(request, 'exportacao/solicitacao_booking_detail.html', {
        'solicitacao': solicitacao,
        'request': request
    })


@login_required
def solicitacao_booking_create(request):
    if not request.user.empresa:
        messages.warning(request, '⚠️ Seu usuário não está vinculado a nenhuma empresa.')
        return redirect('dashboard:index')

    if request.method == 'POST':
        form = SolicitacaoBookingForm(request.POST, empresa=request.user.empresa)
        if form.is_valid():
            solicitacao = form.save(user=request.user)
            messages.success(request, f'✅ Solicitação "{solicitacao.nome}" criada com sucesso!')
            return redirect('exportacao:solicitacao_booking_detail', pk=solicitacao.pk)
        messages.error(request, '❌ Corrija os erros no formulário antes de salvar.')
    else:
        form = SolicitacaoBookingForm(empresa=request.user.empresa)

    return render(request, 'exportacao/solicitacao_booking_form.html', {
        'form': form,
        'action': 'Cadastrar Solicitação',
        'request': request
    })


@login_required
def solicitacao_booking_update(request, pk):
    solicitacao = get_object_or_404(SolicitacaoBooking, pk=pk, empresa=request.user.empresa)
    if request.method == 'POST':
        form = SolicitacaoBookingForm(request.POST, instance=solicitacao, empresa=request.user.empresa)
        if form.is_valid():
            solicitacao = form.save(user=request.user)
            messages.success(request, f'✅ Solicitação "{solicitacao.nome}" atualizada com sucesso!')
            return redirect('exportacao:solicitacao_booking_detail', pk=solicitacao.pk)
        messages.error(request, '❌ Corrija os erros no formulário antes de salvar.')
    else:
        form = SolicitacaoBookingForm(instance=solicitacao, empresa=request.user.empresa)

    return render(request, 'exportacao/solicitacao_booking_form.html', {
        'form': form,
        'action': 'Editar Solicitação',
        'request': request
    })


@login_required
def booking_list(request):
    if not request.user.empresa:
        messages.warning(request, '⚠️ Seu usuário não está vinculado a nenhuma empresa.')
        return redirect('dashboard:index')

    bookings_qs = (
        Booking.objects
        .filter(empresa=request.user.empresa)
        .select_related('solicitacao')
        .annotate(
            n_containers=Count('containers'),
            saldo=ExpressionWrapper(
                F('solicitacao__quantidade') - Count('containers'),
                output_field=DecimalField(max_digits=14, decimal_places=0),
            ),
        )
        .order_by('-data_embarque_previsto')
    )
    paginator = Paginator(bookings_qs, 25)
    bookings = paginator.get_page(request.GET.get('page'))

    return render(request, 'exportacao/booking_list.html', {
        'bookings': bookings,
        'request': request
    })


@login_required
def booking_detail(request, pk):
    booking = get_object_or_404(Booking, pk=pk, empresa=request.user.empresa)
    containers = booking.containers.order_by('numero_container')
    ordens = booking.ordens_coleta.order_by('-data_prevista')
    qtd_solicitada = int(booking.solicitacao.quantidade or 0) if booking.solicitacao else 0
    n_containers = containers.count()
    saldo = qtd_solicitada - n_containers
    return render(request, 'exportacao/booking_detail.html', {
        'booking': booking,
        'containers': containers,
        'ordens': ordens,
        'saldo': saldo,
        'qtd_solicitada': qtd_solicitada,
        'n_containers': n_containers,
        'request': request,
    })


@login_required
def booking_create(request):
    if not request.user.empresa:
        messages.warning(request, '⚠️ Seu usuário não está vinculado a nenhuma empresa.')
        return redirect('dashboard:index')

    if request.method == 'POST':
        form = BookingForm(request.POST, empresa=request.user.empresa)
        if form.is_valid():
            booking = form.save(user=request.user)
            messages.success(request, f'✅ Booking "{booking.codigo or booking.pk}" criado com sucesso!')
            return redirect('exportacao:booking_detail', pk=booking.pk)
        messages.error(request, '❌ Corrija os erros no formulário antes de salvar.')
    else:
        form = BookingForm(empresa=request.user.empresa)

    return render(request, 'exportacao/booking_form.html', {
        'form': form,
        'action': 'Cadastrar Booking',
        'request': request
    })


@login_required
def booking_update(request, pk):
    booking = get_object_or_404(Booking, pk=pk, empresa=request.user.empresa)
    if request.method == 'POST':
        form = BookingForm(request.POST, instance=booking, empresa=request.user.empresa)
        if form.is_valid():
            booking = form.save(user=request.user)
            messages.success(request, f'✅ Booking "{booking.codigo or booking.pk}" atualizado com sucesso!')
            return redirect('exportacao:booking_detail', pk=booking.pk)
        messages.error(request, '❌ Corrija os erros no formulário antes de salvar.')
    else:
        form = BookingForm(instance=booking, empresa=request.user.empresa)

    return render(request, 'exportacao/booking_form.html', {
        'form': form,
        'action': 'Editar Booking',
        'request': request
    })


@login_required
@require_POST
def booking_confirmar(request, pk):
    booking = get_object_or_404(Booking, pk=pk, empresa=request.user.empresa)
    if booking.status != 'ABERTO':
        messages.error(request, 'Só é possível confirmar bookings com status ABERTO.')
        return redirect('exportacao:booking_detail', pk=pk)

    with transaction.atomic():
        status_anterior = booking.status
        booking.status = 'CONFIRMADO'
        booking.atualizado_por = request.user
        booking.save(update_fields=['status', 'atualizado_por', 'atualizado_em'])
        BookingHistory.objects.create(
            empresa=booking.empresa,
            booking=booking,
            usuario=request.user,
            status_from=status_anterior,
            status_to='CONFIRMADO',
        )
    messages.success(request, f'✅ Booking "{booking.codigo or booking.pk}" confirmado.')
    return redirect('exportacao:booking_detail', pk=pk)


@login_required
@require_POST
def booking_embarcar(request, pk):
    booking = get_object_or_404(Booking, pk=pk, empresa=request.user.empresa)
    if booking.status != 'CONFIRMADO':
        messages.error(request, 'Só é possível embarcar bookings com status CONFIRMADO.')
        return redirect('exportacao:booking_detail', pk=pk)

    with transaction.atomic():
        status_anterior = booking.status
        booking.status = 'EMBARCADO'
        if not booking.data_embarque_realizado:
            booking.data_embarque_realizado = timezone.now().date()
        booking.atualizado_por = request.user
        booking.save(update_fields=['status', 'data_embarque_realizado', 'atualizado_por', 'atualizado_em'])
        BookingHistory.objects.create(
            empresa=booking.empresa,
            booking=booking,
            usuario=request.user,
            status_from=status_anterior,
            status_to='EMBARCADO',
        )

        # Cascateia para os containers que ainda não foram explicitamente
        # embarcados/deslocados/devolvidos — um booking não fica "embarcado"
        # com containers ainda PENDENTE/CONFIRMADO.
        containers_pendentes = booking.containers.filter(status__in=['PENDENTE', 'CONFIRMADO'])
        n_containers = containers_pendentes.count()
        for container in containers_pendentes:
            status_from_ct = container.status
            container.status = 'EMBARCADO'
            container.atualizado_por = request.user
            container.save(update_fields=['status', 'atualizado_por', 'atualizado_em'])
            BookingContainerHistory.objects.create(
                empresa=container.empresa,
                container=container,
                usuario=request.user,
                status_from=status_from_ct,
                status_to='EMBARCADO',
                observacoes='Embarque cascateado a partir da confirmação de embarque do Booking.',
            )

    if n_containers:
        messages.success(
            request,
            f'✅ Booking "{booking.codigo or booking.pk}" embarcado — '
            f'{n_containers} contêiner(es) atualizado(s) para EMBARCADO.'
        )
    else:
        messages.success(request, f'✅ Booking "{booking.codigo or booking.pk}" embarcado.')
    return redirect('exportacao:booking_detail', pk=pk)


@login_required
def container_list(request, booking_pk=None):
    if not request.user.empresa:
        messages.warning(request, '⚠️ Seu usuário não está vinculado a nenhuma empresa.')
        return redirect('dashboard:index')

    containers_qs = BookingContainer.objects.filter(empresa=request.user.empresa).order_by('booking__codigo', 'numero_container')
    booking = None
    if booking_pk:
        booking = get_object_or_404(Booking, pk=booking_pk, empresa=request.user.empresa)
        containers_qs = containers_qs.filter(booking=booking)

    paginator = Paginator(containers_qs, 25)
    containers = paginator.get_page(request.GET.get('page'))

    return render(request, 'exportacao/container_list.html', {
        'containers': containers,
        'booking': booking,
        'request': request
    })


@login_required
def container_create(request, booking_pk):
    booking = get_object_or_404(Booking, pk=booking_pk, empresa=request.user.empresa)
    qtd_solicitada = int(booking.solicitacao.quantidade or 0) if booking.solicitacao else 0
    saldo = qtd_solicitada - booking.containers.count()
    if saldo <= 0:
        messages.error(
            request,
            f'❌ O booking {booking.codigo} já atingiu o limite de '
            f'{qtd_solicitada} contêiner(es). Saldo esgotado.',
        )
        return redirect('exportacao:booking_detail', pk=booking.pk)
    if request.method == 'POST':
        form = BookingContainerForm(request.POST, empresa=request.user.empresa)
        if form.is_valid():
            container = form.save(user=request.user)
            ordem_coleta_id = request.POST.get('ordem_coleta_id')
            if ordem_coleta_id:
                OrdemColeta.objects.filter(
                    pk=ordem_coleta_id,
                    booking__empresa=request.user.empresa,
                ).update(container=container)
            messages.success(request, f'✅ Contêiner "{container.numero_container}" criado com sucesso!')
            return redirect('exportacao:booking_detail', pk=booking.pk)
        messages.error(request, '❌ Corrija os erros no formulário antes de salvar.')
    else:
        form = BookingContainerForm(initial={'booking': booking}, empresa=request.user.empresa)

    return render(request, 'exportacao/container_form.html', {
        'form': form,
        'action': 'Cadastrar Contêiner',
        'booking': booking,
    })


@login_required
def container_update(request, pk):
    container = get_object_or_404(BookingContainer, pk=pk, empresa=request.user.empresa)
    if request.method == 'POST':
        form = BookingContainerForm(request.POST, instance=container, empresa=request.user.empresa)
        if form.is_valid():
            container = form.save(user=request.user)
            messages.success(request, f'✅ Contêiner "{container.numero_container}" atualizado com sucesso!')
            return redirect('exportacao:booking_detail', pk=container.booking.pk)
        messages.error(request, '❌ Corrija os erros no formulário antes de salvar.')
    else:
        form = BookingContainerForm(instance=container, empresa=request.user.empresa)

    return render(request, 'exportacao/container_form.html', {
        'form': form,
        'action': 'Editar Contêiner',
        'booking': container.booking,
        'request': request
    })


@login_required
def container_transferir(request, pk):
    """Transfere um container para outro booking, marcando o original como DESLOCADO."""
    container = get_object_or_404(BookingContainer, pk=pk, empresa=request.user.empresa)

    if request.method == 'POST':
        form = ContainerTransferenciaForm(
            request.POST, empresa=request.user.empresa, container=container,
        )
        if form.is_valid():
            booking_destino = form.cleaned_data['booking_destino']
            porto_destino   = form.cleaned_data['porto_destino'] or container.porto_destino
            cultura         = form.cleaned_data['cultura'] or container.cultura
            observacao      = form.cleaned_data['observacao'] or ''

            novo = BookingContainer.objects.create(
                booking=booking_destino,
                empresa=container.empresa,
                numero_container=container.numero_container,
                tipo_container=container.tipo_container,
                status='PENDENTE',
                cultura=cultura,
                porto_origem=container.porto_origem,
                porto_destino=porto_destino,
                armador=container.armador,
                transportadora=container.transportadora,
                motorista=container.motorista,
                placa_principal=container.placa_principal,
                placa_reboque=container.placa_reboque,
                tara_container=container.tara_container,
                numero_genset=container.numero_genset,
                peso_bruto_kg=container.peso_bruto_kg,
                data_coleta_prevista=container.data_coleta_prevista,
                data_coleta_realizada=container.data_coleta_realizada,
                hora_coleta_realizada=container.hora_coleta_realizada,
                criado_por=request.user,
                atualizado_por=request.user,
            )

            status_anterior = container.status
            container.status = 'DESLOCADO'
            container.atualizado_por = request.user
            container.save(update_fields=['status', 'atualizado_por', 'atualizado_em'])

            BookingContainerHistory.objects.create(
                container=container,
                empresa=container.empresa,
                usuario=request.user,
                status_from=status_anterior,
                status_to='DESLOCADO',
                observacoes=(
                    f'Transferido para booking {booking_destino.codigo} '
                    f'(novo container ID {novo.pk}). {observacao}'
                ).strip(),
            )

            messages.success(
                request,
                f'✅ Container {container.numero_container} transferido para o booking '
                f'"{booking_destino.codigo}" com sucesso. '
                f'O container original foi marcado como Deslocado.',
            )
            return redirect('exportacao:booking_detail', pk=booking_destino.pk)
        messages.error(request, '❌ Corrija os erros antes de prosseguir.')
    else:
        form = ContainerTransferenciaForm(empresa=request.user.empresa, container=container)

    campos_copiados = [
        'Número do contêiner', 'Tipo do contêiner', 'Armador', 'Transportadora',
        'Motorista', 'Placa principal', 'Placa reboque', 'Cultura', 'Porto origem',
        'Porto destino', 'Peso bruto', 'Tara', 'Nº Genset', 'Data coleta prevista',
    ]

    return render(request, 'exportacao/container_transferencia.html', {
        'form': form,
        'container': container,
        'booking': container.booking,
        'campos_copiados': campos_copiados,
    })


@login_required
def container_historico(request, pk):
    container = get_object_or_404(BookingContainer, pk=pk, empresa=request.user.empresa)
    historico = container.historico.select_related('usuario').order_by('-data')
    return render(request, 'exportacao/container_historico.html', {
        'container': container,
        'booking': container.booking,
        'historico': historico,
    })


@login_required
def ordem_coleta_list(request):
    if not request.user.empresa:
        messages.warning(request, '⚠️ Seu usuário não está vinculado a nenhuma empresa.')
        return redirect('dashboard:index')

    ordens_qs = (
        OrdemColeta.objects.filter(empresa=request.user.empresa)
        .select_related('booking', 'motorista', 'container')
        .prefetch_related('fotos')
        .order_by('-data_prevista')
    )
    paginator = Paginator(ordens_qs, 25)
    ordens = paginator.get_page(request.GET.get('page'))

    return render(request, 'exportacao/ordem_coleta_list.html', {
        'ordens': ordens,
        'request': request
    })


def _sync_lacres_container(ordem):
    if ordem.segregado and ordem.container:
        ct = ordem.container
        changed = False
        for field in ('lacre_armador', 'lacre_fiscal', 'lacre_terminal', 'lacre_g7'):
            val = getattr(ordem, field)
            if val:
                setattr(ct, field, val)
                changed = True
        if changed:
            ct.save()


@login_required
def ordem_coleta_create(request):
    if not request.user.empresa:
        messages.warning(request, '⚠️ Seu usuário não está vinculado a nenhuma empresa.')
        return redirect('dashboard:index')

    if request.method == 'POST':
        form = OrdemColetaForm(request.POST, request.FILES, empresa=request.user.empresa)
        if form.is_valid():
            if not form.cleaned_data.get('numero'):
                form.instance.numero = OrdemColeta.generate_numero(request.user.empresa)
            ordem = form.save(user=request.user)
            _sync_lacres_container(ordem)
            messages.success(request, f'✅ Ordem de coleta {ordem.numero} criada com sucesso!')
            return redirect('exportacao:ordem_coleta_list')
        messages.error(request, '❌ Corrija os erros no formulário antes de salvar.')
    else:
        form = OrdemColetaForm(empresa=request.user.empresa)

    return render(request, 'exportacao/ordem_coleta_form.html', {
        'form': form,
        'action': 'Cadastrar Ordem de Coleta',
        'request': request
    })


@login_required
def ordem_coleta_update(request, pk):
    ordem = get_object_or_404(OrdemColeta, pk=pk, empresa=request.user.empresa)
    if request.method == 'POST':
        form = OrdemColetaForm(request.POST, request.FILES, instance=ordem, empresa=request.user.empresa)
        if form.is_valid():
            ordem = form.save(user=request.user)
            _sync_lacres_container(ordem)
            messages.success(request, f'✅ Ordem de coleta {ordem.numero} atualizada com sucesso!')
            return redirect('exportacao:ordem_coleta_list')
        messages.error(request, '❌ Corrija os erros no formulário antes de salvar.')
    else:
        form = OrdemColetaForm(instance=ordem, empresa=request.user.empresa)

    return render(request, 'exportacao/ordem_coleta_form.html', {
        'form': form,
        'action': 'Editar Ordem de Coleta',
        'request': request
    })


@login_required
def ordem_coleta_print(request, pk):
    from datetime import date as _date
    from django.db.models import Q as _Q

    ordem = get_object_or_404(
        OrdemColeta.objects.select_related(
            'booking', 'container', 'transportadora', 'motorista', 'empresa'
        ),
        pk=pk, empresa=request.user.empresa,
    )

    placa_principal = ''
    veiculo_principal = ''
    reboques = []
    if ordem.motorista_id:
        hoje = _date.today()
        vinculo = (
            MotoristaVinculoPlaca.objects
            .filter(
                motorista_id=ordem.motorista_id,
                ativo=True,
            )
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
        'empresa': request.user.empresa,
        'placa_principal': placa_principal,
        'veiculo_principal': veiculo_principal,
        'reboques': reboques,
    })


@login_required
def ordem_coleta_fotos_admin(request, pk):
    from .models import FotoOrdemColeta
    ordem = get_object_or_404(OrdemColeta, pk=pk, empresa=request.user.empresa)
    fotos = ordem.fotos.select_related('enviada_por').all()
    return render(request, 'exportacao/ordem_coleta_fotos.html', {
        'ordem': ordem,
        'fotos': fotos,
    })


@login_required
def ordem_coleta_carta_temperatura(request, pk):
    from datetime import date as _date
    MESES = [
        'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
        'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
    ]

    ordem = get_object_or_404(
        OrdemColeta.objects.select_related(
            'booking__solicitacao__cultura',
            'booking__solicitacao__navio',
            'booking__porto_origem',
            'booking__porto_destino',
            'container',
            'empresa',
        ),
        pk=pk, empresa=request.user.empresa,
    )

    booking = ordem.booking
    solicitacao = getattr(booking, 'solicitacao', None)
    cultura = getattr(solicitacao, 'cultura', None) if solicitacao else None
    navio = getattr(solicitacao, 'navio', None) if solicitacao else None

    # "To the master of": navio + rota_navio
    navio_nome = str(navio) if navio else ''
    rota = booking.rota_navio or ''
    to_master = ' '.join(filter(None, [navio_nome, rota])) or '—'

    # Commodity
    commodity = str(cultura) if cultura else '—'

    # Porto
    porto_loading = str(booking.porto_origem) if booking.porto_origem else '—'
    porto_discharge = str(booking.porto_destino) if booking.porto_destino else '—'
    place_delivery = porto_discharge  # mesmo porto de descarga

    # Temperatura / ventilação / humidade — valores raw (sem normalize para evitar notação científica)
    temperatura = getattr(cultura, 'exportacao_temperatura', None)
    ventilacao_raw = getattr(cultura, 'exportacao_ventilacao', None)
    humidade_raw = getattr(cultura, 'exportacao_humidade', None)

    temperatura_display = f'{temperatura}°C' if temperatura is not None else '—'
    ventilacao_display = 'OFF' if (ventilacao_raw is None or ventilacao_raw == 0) else f'{ventilacao_raw} cbm/h'
    humidade_display = 'OFF' if (humidade_raw is None or humidade_raw == 0) else f'{humidade_raw}%'

    # Data localizada
    hoje = _date.today()
    empresa = request.user.empresa
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
        'place_delivery': place_delivery,
        'temperatura_display': temperatura_display,
        'ventilacao_display': ventilacao_display,
        'humidade_display': humidade_display,
        'data_local': data_local,
    })


@login_required
def solicitacao_booking_pdf(request, pk):
    solicitacao = get_object_or_404(SolicitacaoBooking, pk=pk, empresa=request.user.empresa)
    empresa = request.user.empresa
    hoje = timezone.localdate().strftime('%d/%m/%Y')

    template = get_template('exportacao/solicitacao_booking_pdf.html')
    html = template.render({'solicitacao': solicitacao, 'empresa': empresa, 'hoje': hoje})

    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(html.encode('UTF-8')), result)
    if pdf.err:
        return HttpResponse('Erro ao gerar PDF', status=500)

    filename = f'solicitacao_booking_{pk:05d}.pdf'
    response = HttpResponse(result.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


@login_required
def ajax_cultura_exportacao(request, pk):
    cultura = get_object_or_404(Cultura, pk=pk, empresa=request.user.empresa)
    return JsonResponse({
        'temperatura': str(cultura.exportacao_temperatura) if cultura.exportacao_temperatura is not None else '',
        'humidade': str(cultura.exportacao_humidade) if cultura.exportacao_humidade is not None else '',
        'ventilacao': str(cultura.exportacao_ventilacao) if cultura.exportacao_ventilacao is not None else '',
    })


@login_required
def ajax_solicitacao_preview(request, pk):
    s = get_object_or_404(SolicitacaoBooking, pk=pk, empresa=request.user.empresa)
    return JsonResponse({
        'nome': s.nome,
        'cliente': str(s.cliente) if s.cliente else '',
        'cultura': str(s.cultura) if s.cultura else '',
        'porto_origem': str(s.porto_origem) if s.porto_origem else '',
        'porto_destino': str(s.porto_destino) if s.porto_destino else '',
        'armador': str(s.armador) if s.armador else '',
        'navio': str(s.navio) if s.navio else '',
        'frete': s.get_frete_display(),
        'genset': s.get_genset_display(),
        'tipo_exportacao': s.get_tipo_exportacao_display() if s.tipo_exportacao else '',
        'tipo_exportacao_outros': s.tipo_exportacao_outros,
        'data_prevista_embarque': s.data_prevista_embarque.strftime('%d/%m/%Y') if s.data_prevista_embarque else '',
        'quantidade': str(s.quantidade) if s.quantidade is not None else '',
        'status': s.get_status_display(),
    })


@login_required
def ajax_booking_coleta_preview(request, pk):
    b = get_object_or_404(Booking, pk=pk, empresa=request.user.empresa)
    s = b.solicitacao
    cultura = s.cultura if s else None
    return JsonResponse({
        'porto_origem': str(b.porto_origem) if b.porto_origem else '',
        'porto_destino': str(b.porto_destino) if b.porto_destino else '',
        'rota_navio': b.rota_navio,
        'armador': str(s.armador) if s and s.armador else '',
        'navio': str(s.navio) if s and s.navio else '',
        'cultura': str(cultura) if cultura else '',
        'genset': s.get_genset_display() if s and s.genset else '',
        'temperatura': str(cultura.exportacao_temperatura) if cultura and cultura.exportacao_temperatura is not None else '',
        'humidade': str(cultura.exportacao_humidade) if cultura and cultura.exportacao_humidade is not None else '',
        'ventilacao': str(cultura.exportacao_ventilacao) if cultura and cultura.exportacao_ventilacao is not None else '',
        'containers': [
            {'id': c.pk, 'label': f'{c.numero_container} ({c.get_tipo_container_display()})'}
            for c in b.containers.order_by('numero_container')
        ],
    })


@login_required
def ajax_booking_container_preview(request, pk):
    """Dados do Booking + OrdemColeta para pré-preencher o form de container."""
    from datetime import date as _date
    from django.db.models import Q as _Q
    b = get_object_or_404(
        Booking.objects.select_related(
            'solicitacao__cultura', 'solicitacao__armador',
            'porto_origem', 'porto_destino', 'transportadora',
        ),
        pk=pk, empresa=request.user.empresa,
    )
    s = b.solicitacao
    data = {
        'codigo':               b.codigo,
        'cultura_id':           s.cultura_id if s else None,
        'cultura':              str(s.cultura) if s and s.cultura else '',
        'porto_origem_id':      b.porto_origem_id,
        'porto_destino_id':     b.porto_destino_id,
        'porto_destino':        str(b.porto_destino) if b.porto_destino else '',
        'data_coleta_prevista': b.data_embarque_previsto.strftime('%Y-%m-%d') if b.data_embarque_previsto else '',
        'armador_id':           s.armador_id if s else None,
        'armador':              str(s.armador) if s and s.armador else '',
        'navio':                str(s.navio) if s and s.navio else '',
        'transportadora_id':    b.transportadora_id,
        'transportadora_nome':  str(b.transportadora) if b.transportadora else '',
        'motorista_id':         None,
        'motorista_nome':       '',
        'placa_principal':      '',
        'placa_reboque':        '',
        'veiculo':              '',
    }
    # Motorista e placas vêm da OrdemColeta vinculada (se existir)
    ordem = (
        OrdemColeta.objects
        .filter(booking=b)
        .select_related('transportadora', 'motorista')
        .order_by('-data_prevista')
        .first()
    )
    if ordem:
        # OrdemColeta pode ter transportadora diferente (sobrescreve a do Booking)
        if ordem.transportadora_id:
            data['transportadora_id'] = ordem.transportadora_id
            data['transportadora_nome'] = str(ordem.transportadora) if ordem.transportadora else ''
        data['motorista_id'] = ordem.motorista_id
        data['motorista_nome'] = str(ordem.motorista) if ordem.motorista else ''
        if ordem.motorista_id:
            hoje = _date.today()
            vinculo = (
                MotoristaVinculoPlaca.objects
                .filter(motorista_id=ordem.motorista_id, ativo=True)
                .filter(_Q(data_fim__isnull=True) | _Q(data_fim__gte=hoje))
                .select_related('placa_principal__vehicle')
                .prefetch_related('reboques')
                .order_by('-data_inicio')
                .first()
            )
            if vinculo and vinculo.placa_principal:
                data['placa_principal'] = vinculo.placa_principal.placa
                v = getattr(vinculo.placa_principal, 'vehicle', None)
                if v:
                    data['veiculo'] = f'{v.marca} {v.modelo}'.strip()
                data['placa_reboque'] = ', '.join(rp.placa for rp in vinculo.reboques.all())
    return JsonResponse(data)


@login_required
def ajax_transportadora_preview(request, pk):
    t = get_object_or_404(Transportadora, pk=pk, empresa=request.user.empresa)
    return JsonResponse({
        'razao_social': t.razao_social,
        'cnpj': t.cnpj or '',
        'contato': t.contato_principal_nome,
        'telefone': t.contato_principal_telefone,
        'cidade': f'{t.cidade}/{t.uf}' if t.cidade else '',
        'rntc': t.rntc,
    })


@login_required
def ajax_motorista_preview(request, pk):
    m = get_object_or_404(Motorista, pk=pk, empresa=request.user.empresa)
    vinculo = m.vinculos_placas.filter(ativo=True).order_by('-data_inicio').first()
    placa = ''
    veiculo = ''
    reboques = []
    if vinculo and hasattr(vinculo, 'placa_principal') and vinculo.placa_principal:
        placa = vinculo.placa_principal.placa
        v = getattr(vinculo.placa_principal, 'vehicle', None)
        if v:
            veiculo = f'{v.marca} {v.modelo}'.strip()
        for rp in vinculo.reboques.select_related('vehicle').all():
            rv = rp.vehicle
            reboques.append({
                'placa': rp.placa,
                'veiculo': f'{rv.marca} {rv.modelo}'.strip() if rv else '',
            })
    return JsonResponse({
        'nome': m.nome,
        'cpf': m.cpf,
        'celular': m.celular,
        'cnh': m.cnh,
        'categoria_cnh': m.categoria_cnh,
        'validade_cnh': m.data_validade_cnh.strftime('%d/%m/%Y') if m.data_validade_cnh else '',
        'placa': placa,
        'veiculo': veiculo,
        'reboques': reboques,
        'transportadora': str(m.transportadora) if m.transportadora else '',
    })


@login_required
def ajax_motoristas_por_transportadora(request, pk):
    motoristas = list(
        Motorista.objects.filter(
            empresa=request.user.empresa,
            transportadora_id=pk,
            ativo=True,
        ).values('id', 'nome').order_by('nome')
    )
    return JsonResponse({'motoristas': motoristas})


@login_required
def ajax_booking_ordens_coleta(request, pk):
    """Lista de Ordens de Coleta de um booking com status de vínculo a container."""
    b = get_object_or_404(Booking, pk=pk, empresa=request.user.empresa)
    ordens = (
        OrdemColeta.objects
        .filter(booking=b)
        .select_related('motorista', 'transportadora', 'container')
        .order_by('data_prevista', 'numero')
    )
    result = []
    for o in ordens:
        result.append({
            'id':                  o.pk,
            'numero':              o.numero or f'OC #{o.pk}',
            'status':              o.status,
            'status_display':      o.get_status_display(),
            'data_prevista':       o.data_prevista.strftime('%d/%m/%Y') if o.data_prevista else '—',
            'motorista_nome':      o.motorista.nome if o.motorista else '—',
            'transportadora_nome': o.transportadora.razao_social if o.transportadora else '—',
            'container_vinculado': o.container_id is not None,
            'container_numero':    o.container.numero_container if o.container else '',
        })
    return JsonResponse({'ordens': result})


@login_required
def ajax_ordem_coleta_container_dados(request, pk):
    """Dados completos de uma OC para pré-preencher o formulário de container."""
    from datetime import date as _date
    from django.db.models import Q as _Q
    ordem = get_object_or_404(
        OrdemColeta.objects.select_related(
            'booking__solicitacao__cultura',
            'booking__solicitacao__armador',
            'booking__porto_origem',
            'booking__porto_destino',
            'booking__transportadora',
            'motorista',
            'transportadora',
        ),
        pk=pk, booking__empresa=request.user.empresa,
    )
    b = ordem.booking
    s = b.solicitacao
    data = {
        'cultura_id':           s.cultura_id if s else None,
        'porto_origem_id':      b.porto_origem_id,
        'porto_destino_id':     b.porto_destino_id,
        'data_coleta_prevista': (
            ordem.data_prevista.strftime('%Y-%m-%d') if ordem.data_prevista else (
                b.data_embarque_previsto.strftime('%Y-%m-%d') if b.data_embarque_previsto else ''
            )
        ),
        'armador_id':         s.armador_id if s else None,
        'transportadora_id':  ordem.transportadora_id or b.transportadora_id,
        'transportadora_nome': str(ordem.transportadora) if ordem.transportadora else (str(b.transportadora) if b.transportadora else ''),
        'motorista_id':       ordem.motorista_id,
        'motorista_nome':     str(ordem.motorista) if ordem.motorista else '',
        'placa_principal':    '',
        'placa_reboque':      '',
        'veiculo':            '',
    }
    if ordem.motorista_id:
        hoje = _date.today()
        vinculo = (
            MotoristaVinculoPlaca.objects
            .filter(motorista_id=ordem.motorista_id, ativo=True)
            .filter(_Q(data_fim__isnull=True) | _Q(data_fim__gte=hoje))
            .select_related('placa_principal__vehicle')
            .prefetch_related('reboques')
            .order_by('-data_inicio')
            .first()
        )
        if vinculo and vinculo.placa_principal:
            data['placa_principal'] = vinculo.placa_principal.placa
            v = getattr(vinculo.placa_principal, 'vehicle', None)
            if v:
                data['veiculo'] = f'{v.marca} {v.modelo}'.strip()
            data['placa_reboque'] = ', '.join(rp.placa for rp in vinculo.reboques.all())
    return JsonResponse(data)
