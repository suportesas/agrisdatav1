import io

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import get_template
from django.utils import timezone
from xhtml2pdf import pisa

from cadastros.models import Cultura
from .forms import BookingContainerForm, BookingForm, OrdemColetaForm, SolicitacaoBookingForm
from .models import Booking, BookingContainer, OrdemColeta, SolicitacaoBooking


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

    bookings = Booking.objects.filter(empresa=request.user.empresa).order_by('-data_embarque_previsto')
    return render(request, 'exportacao/booking_list.html', {
        'bookings': bookings,
        'request': request
    })


@login_required
def booking_detail(request, pk):
    booking = get_object_or_404(Booking, pk=pk, empresa=request.user.empresa)
    containers = booking.containers.order_by('numero_container')
    ordens = booking.ordens_coleta.order_by('-data_prevista')
    return render(request, 'exportacao/booking_detail.html', {
        'booking': booking,
        'containers': containers,
        'ordens': ordens,
        'request': request
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
def container_list(request, booking_pk=None):
    if not request.user.empresa:
        messages.warning(request, '⚠️ Seu usuário não está vinculado a nenhuma empresa.')
        return redirect('dashboard:index')

    containers = BookingContainer.objects.filter(empresa=request.user.empresa).order_by('booking__codigo', 'numero_container')
    booking = None
    if booking_pk:
        booking = get_object_or_404(Booking, pk=booking_pk, empresa=request.user.empresa)
        containers = containers.filter(booking=booking)

    return render(request, 'exportacao/container_list.html', {
        'containers': containers,
        'booking': booking,
        'request': request
    })


@login_required
def container_create(request, booking_pk):
    booking = get_object_or_404(Booking, pk=booking_pk, empresa=request.user.empresa)
    if request.method == 'POST':
        form = BookingContainerForm(request.POST, empresa=request.user.empresa)
        if form.is_valid():
            container = form.save(user=request.user)
            messages.success(request, f'✅ Contêiner "{container.numero_container}" criado com sucesso!')
            return redirect('exportacao:booking_detail', pk=booking.pk)
        messages.error(request, '❌ Corrija os erros no formulário antes de salvar.')
    else:
        form = BookingContainerForm(initial={'booking': booking}, empresa=request.user.empresa)

    return render(request, 'exportacao/container_form.html', {
        'form': form,
        'action': 'Cadastrar Contêiner',
        'booking': booking,
        'request': request
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
def ordem_coleta_list(request):
    if not request.user.empresa:
        messages.warning(request, '⚠️ Seu usuário não está vinculado a nenhuma empresa.')
        return redirect('dashboard:index')

    ordens = OrdemColeta.objects.filter(empresa=request.user.empresa).order_by('-data_prevista')
    return render(request, 'exportacao/ordem_coleta_list.html', {
        'ordens': ordens,
        'request': request
    })


@login_required
def ordem_coleta_create(request):
    if not request.user.empresa:
        messages.warning(request, '⚠️ Seu usuário não está vinculado a nenhuma empresa.')
        return redirect('dashboard:index')

    if request.method == 'POST':
        form = OrdemColetaForm(request.POST, request.FILES, empresa=request.user.empresa)
        if form.is_valid():
            ordem = form.save(user=request.user)
            messages.success(request, f'✅ Ordem de coleta criada com sucesso!')
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
            messages.success(request, f'✅ Ordem de coleta atualizada com sucesso!')
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
