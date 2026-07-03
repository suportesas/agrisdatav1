import io
import json
import math
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Case, Count, Q, Value, When
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.barcode_utils import barcode_b64 as _barcode_b64
from estoque.models import Armazem

from .forms import ItemPalletForm, OrdemEmbalagemForm, RomaneioVendaForm, TipoEmbalagemForm, TrocarClienteRomaneioForm
from .models import (
    ItemPallet, ItemRomaneioVenda, OrdemEmbalagem, PalletEmbalado, RomaneioVenda, TipoEmbalagem,
)


def _get_empresa(request):
    return request.user.empresa


# ─────────────────────────── Dashboard ──────────────────────────────────────

@login_required
def embalagem_dashboard(request):
    empresa = _get_empresa(request)
    tem_tipo = TipoEmbalagem.objects.filter(empresa=empresa, ativo=True).exists()
    pallets_disponiveis = PalletEmbalado.objects.filter(empresa=empresa, status='DISPONIVEL').count()
    pallets_reservados = PalletEmbalado.objects.filter(empresa=empresa, status='RESERVADO').count()
    ordens_abertas = OrdemEmbalagem.objects.filter(empresa=empresa, status__in=['ABERTA', 'EM_ANDAMENTO']).count()
    romaneios_rascunho = RomaneioVenda.objects.filter(empresa=empresa, status='RASCUNHO').count()
    romaneios_confirmados = RomaneioVenda.objects.filter(empresa=empresa, status__in=['CONFIRMADO', 'CARREGANDO']).count()
    ultimas_ordens = OrdemEmbalagem.objects.filter(empresa=empresa).select_related('tipo_embalagem').order_by('-criado_em')[:4]
    ultimos_romaneios = RomaneioVenda.objects.filter(empresa=empresa).select_related('cliente').order_by('-criado_em')[:4]
    return render(request, 'embalagem/dashboard.html', {
        'fluxo': {
            'tem_tipo': tem_tipo,
            'pallets_disponiveis': pallets_disponiveis,
            'pallets_reservados': pallets_reservados,
            'ordens_abertas': ordens_abertas,
            'romaneios_rascunho': romaneios_rascunho,
            'romaneios_confirmados': romaneios_confirmados,
        },
        'ultimas_ordens': ultimas_ordens,
        'ultimos_romaneios': ultimos_romaneios,
    })


# ─────────────────────────── TipoEmbalagem ──────────────────────────────────

@login_required
def tipo_embalagem_list(request):
    empresa = _get_empresa(request)
    qs = TipoEmbalagem.objects.filter(empresa=empresa).select_related('produto', 'cultura', 'subcategoria')
    q = request.GET.get('q', '')
    if q:
        qs = qs.filter(nome__icontains=q)
    return render(request, 'embalagem/tipo_embalagem/list.html', {
        'tipos': qs.order_by('nome'),
        'q': q,
    })


@login_required
def tipo_embalagem_create(request):
    empresa = _get_empresa(request)
    if request.method == 'POST':
        form = TipoEmbalagemForm(request.POST, empresa=empresa)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.empresa = empresa
            obj.save()
            messages.success(request, 'Tipo de embalagem criado com sucesso.')
            return redirect('embalagem:tipo_embalagem_list')
    else:
        form = TipoEmbalagemForm(empresa=empresa)
    return render(request, 'embalagem/tipo_embalagem/form.html', {
        'form': form, 'title': 'Novo Tipo de Embalagem',
    })


@login_required
def tipo_embalagem_update(request, pk):
    empresa = _get_empresa(request)
    obj = get_object_or_404(TipoEmbalagem, pk=pk, empresa=empresa)
    if request.method == 'POST':
        form = TipoEmbalagemForm(request.POST, instance=obj, empresa=empresa)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tipo de embalagem atualizado.')
            return redirect('embalagem:tipo_embalagem_list')
    else:
        form = TipoEmbalagemForm(instance=obj, empresa=empresa)
    return render(request, 'embalagem/tipo_embalagem/form.html', {
        'form': form, 'title': 'Editar Tipo de Embalagem', 'obj': obj,
    })


# ─────────────────────────── OrdemEmbalagem ─────────────────────────────────

@login_required
def ordem_list(request):
    empresa = _get_empresa(request)
    qs = OrdemEmbalagem.objects.filter(empresa=empresa).select_related('tipo_embalagem', 'lote_origem__produto')
    q = request.GET.get('q', '')
    status_f = request.GET.get('status', '')
    data_ini = request.GET.get('data_ini', '')
    data_fim = request.GET.get('data_fim', '')
    if q:
        qs = qs.filter(numero__icontains=q)
    if status_f:
        qs = qs.filter(status=status_f)
    if data_ini:
        qs = qs.filter(data__gte=data_ini)
    if data_fim:
        qs = qs.filter(data__lte=data_fim)
    paginator = Paginator(qs.order_by('-criado_em'), 25)
    return render(request, 'embalagem/ordem/list.html', {
        'page_obj': paginator.get_page(request.GET.get('page')),
        'filtros': {'q': q, 'status': status_f, 'data_ini': data_ini, 'data_fim': data_fim},
        'status_choices': OrdemEmbalagem.STATUS,
    })


@login_required
def ordem_create(request):
    empresa = _get_empresa(request)
    if request.method == 'POST':
        form = OrdemEmbalagemForm(request.POST, empresa=empresa)
        if form.is_valid():
            with transaction.atomic():
                ordem = form.save(commit=False)
                ordem.empresa = empresa
                ordem.numero = OrdemEmbalagem._gerar_numero(empresa)
                ordem.criado_por = request.user
                ordem.save()
            messages.success(request, f'Ordem {ordem.numero} criada.')
            return redirect('embalagem:ordem_detail', pk=ordem.pk)
    else:
        form = OrdemEmbalagemForm(empresa=empresa)
    return render(request, 'embalagem/ordem/form.html', {
        'form': form, 'title': 'Nova Ordem de Embalagem',
    })


@login_required
def ordem_detail(request, pk):
    empresa = _get_empresa(request)
    ordem = get_object_or_404(OrdemEmbalagem, pk=pk, empresa=empresa)
    pallets = ordem.pallets.select_related('armazem').order_by('numero_sequencial')
    return render(request, 'embalagem/ordem/detail.html', {
        'ordem': ordem,
        'pallets': pallets,
    })


@login_required
@require_POST
def ordem_gerar_pallets(request, pk):
    empresa = _get_empresa(request)
    ordem = get_object_or_404(OrdemEmbalagem, pk=pk, empresa=empresa)

    if ordem.status == 'CANCELADA':
        messages.error(request, 'Ordem cancelada não pode gerar pallets.')
        return redirect('embalagem:ordem_detail', pk=pk)

    if ordem.pallets.exists():
        messages.warning(request, 'Esta ordem já possui pallets gerados.')
        return redirect('embalagem:ordem_detail', pk=pk)

    te = ordem.tipo_embalagem
    peso_liq_pallet = te.peso_liquido_pallet
    if not peso_liq_pallet:
        messages.error(request, 'Tipo de embalagem inválido (peso zero).')
        return redirect('embalagem:ordem_detail', pk=pk)

    n_pallets = int(math.floor(float(ordem.quantidade_entrada_kg) / float(peso_liq_pallet)))
    if n_pallets < 1:
        messages.error(request, 'Quantidade insuficiente para gerar pelo menos 1 pallet.')
        return redirect('embalagem:ordem_detail', pk=pk)

    hoje = timezone.now().date()
    with transaction.atomic():
        for seq in range(1, n_pallets + 1):
            codigo = PalletEmbalado._gerar_codigo(empresa, hoje, safra=ordem.safra)
            PalletEmbalado.objects.create(
                empresa=empresa,
                codigo_pallet=codigo,
                ordem_embalagem=ordem,
                tipo_embalagem=te,
                numero_sequencial=seq,
                quantidade_caixas=te.caixas_por_pallet,
                peso_bruto_kg=te.peso_bruto_pallet,
                peso_liquido_kg=te.peso_liquido_pallet,
                data_embalagem=hoje,
                armazem=ordem.armazem_destino,
                local_estocagem=ordem.local_destino,
                status='DISPONIVEL',
            )
        ordem.status = 'CONCLUIDA'
        ordem.save(update_fields=['status'])

    messages.success(request, f'{n_pallets} pallets gerados com sucesso.')
    return redirect('embalagem:ordem_detail', pk=pk)


# ─────────────────────────── PalletEmbalado ─────────────────────────────────

@login_required
def pallet_list(request):
    empresa = _get_empresa(request)
    qs = PalletEmbalado.objects.filter(empresa=empresa).select_related(
        'tipo_embalagem', 'armazem', 'ordem_embalagem')

    status_f = request.GET.get('status', '')
    armazem_f = request.GET.get('armazem', '')
    q = request.GET.get('q', '')

    if status_f:
        qs = qs.filter(status=status_f)
    if armazem_f:
        qs = qs.filter(armazem_id=armazem_f)
    if q:
        qs = qs.filter(codigo_pallet__icontains=q)

    armazens = Armazem.objects.filter(empresa=empresa).order_by('nome')

    data_ini = request.GET.get('data_ini', '')
    data_fim = request.GET.get('data_fim', '')
    if data_ini:
        qs = qs.filter(data_embalagem__gte=data_ini)
    if data_fim:
        qs = qs.filter(data_embalagem__lte=data_fim)

    _stats = PalletEmbalado.objects.filter(empresa=empresa).aggregate(
        disponiveis=Count('id', filter=Q(status='DISPONIVEL')),
        reservados=Count('id', filter=Q(status='RESERVADO')),
        carregados=Count('id', filter=Q(status='CARREGADO')),
    )
    stats = {
        'disponiveis': _stats['disponiveis'] or 0,
        'reservados': _stats['reservados'] or 0,
        'carregados': _stats['carregados'] or 0,
    }
    paginator = Paginator(qs.order_by('-criado_em'), 50)
    return render(request, 'embalagem/pallet/list.html', {
        'page_obj': paginator.get_page(request.GET.get('page')),
        'status_choices': PalletEmbalado.STATUS,
        'filtros': {'q': q, 'status': status_f, 'armazem': armazem_f, 'data_ini': data_ini, 'data_fim': data_fim},
        'armazens': armazens,
        'stats': stats,
    })


# ─────────────────────────── Etiqueta PDF ───────────────────────────────────

def _render_etiqueta_pdf(pallets, romaneio=None):
    """Gera PDF com etiquetas dos pallets usando xhtml2pdf."""
    from django.template.loader import render_to_string
    from xhtml2pdf import pisa

    # Enriquecer pallets com dados do romaneio via related manager
    pallets_ctx = []
    for p in pallets:
        # Romaneio prioritário: passado explicitamente ou buscado via itens
        rom = romaneio
        if not rom:
            item = p.itens_romaneio.select_related(
                'romaneio__cliente', 'romaneio__booking__armador',
                'romaneio__booking__navio', 'romaneio__booking__porto_destino',
                'romaneio__container',
            ).first()
            rom = item.romaneio if item else None

        ctx_pallet = {
            'pallet': p,
            'barcode_b64': _barcode_b64(p.codigo_pallet),
            'romaneio': rom,
        }
        pallets_ctx.append(ctx_pallet)

    html = render_to_string('embalagem/pallet/etiqueta_pdf.html', {
        'pallets_ctx': pallets_ctx,
    })
    buffer = io.BytesIO()
    pisa.CreatePDF(html, dest=buffer)
    buffer.seek(0)
    return buffer.read()


@login_required
def pallet_etiqueta_pdf(request, pk):
    empresa = _get_empresa(request)
    pallet = get_object_or_404(
        PalletEmbalado.objects.select_related(
            'tipo_embalagem__cultura', 'tipo_embalagem__produto', 'empresa',
            'ordem_embalagem__safra',
        ).prefetch_related('composicao__tipo_embalagem__cultura'),
        pk=pk, empresa=empresa,
    )
    item_rom = pallet.itens_romaneio.select_related(
        'romaneio__cliente', 'romaneio__booking__armador',
        'romaneio__booking__navio', 'romaneio__booking__porto_destino',
        'romaneio__container',
    ).first()
    romaneio = item_rom.romaneio if item_rom else None
    pdf = _render_etiqueta_pdf([pallet], romaneio=romaneio)
    pallet.etiqueta_gerada = True
    pallet.save(update_fields=['etiqueta_gerada'])
    resp = HttpResponse(pdf, content_type='application/pdf')
    resp['Content-Disposition'] = f'inline; filename="etiqueta-{pallet.codigo_pallet}.pdf"'
    return resp


@login_required
def ordem_etiquetas_pdf(request, pk):
    empresa = _get_empresa(request)
    ordem = get_object_or_404(OrdemEmbalagem, pk=pk, empresa=empresa)
    pallets = list(
        ordem.pallets
        .select_related('tipo_embalagem__cultura', 'tipo_embalagem__produto', 'empresa', 'ordem_embalagem__safra')
        .prefetch_related('composicao__tipo_embalagem__cultura')
        .order_by('numero_sequencial')
    )
    pdf = _render_etiqueta_pdf(pallets)
    PalletEmbalado.objects.filter(ordem_embalagem=ordem).update(etiqueta_gerada=True)
    resp = HttpResponse(pdf, content_type='application/pdf')
    resp['Content-Disposition'] = f'inline; filename="etiquetas-{ordem.numero}.pdf"'
    return resp


@login_required
def romaneio_etiquetas_pdf(request, pk):
    empresa = _get_empresa(request)
    romaneio = get_object_or_404(
        RomaneioVenda.objects.select_related(
            'cliente', 'booking__armador', 'booking__navio', 'booking__porto_destino', 'container',
        ),
        pk=pk, empresa=empresa,
    )
    pallets = [
        item.pallet for item in romaneio.itens
        .select_related(
            'pallet__tipo_embalagem__cultura', 'pallet__tipo_embalagem__produto',
            'pallet__empresa', 'pallet__ordem_embalagem__safra',
        )
        .prefetch_related('pallet__composicao__tipo_embalagem__cultura')
        .order_by('pallet__codigo_pallet')
    ]
    pdf = _render_etiqueta_pdf(pallets, romaneio=romaneio)
    resp = HttpResponse(pdf, content_type='application/pdf')
    resp['Content-Disposition'] = f'inline; filename="etiquetas-romaneio-{romaneio.numero}.pdf"'
    return resp


# ─────────────────────────── RomaneioVenda ──────────────────────────────────

@login_required
def romaneio_list(request):
    empresa = _get_empresa(request)
    qs = RomaneioVenda.objects.filter(empresa=empresa).select_related('cliente', 'booking', 'pedido_venda')
    q = request.GET.get('q', '')
    status_f = request.GET.get('status', '')
    tipo_f = request.GET.get('tipo', '')
    data_ini = request.GET.get('data_ini', '')
    data_fim = request.GET.get('data_fim', '')
    if q:
        qs = qs.filter(numero__icontains=q)
    if status_f:
        qs = qs.filter(status=status_f)
    if tipo_f:
        qs = qs.filter(tipo=tipo_f)
    if data_ini:
        qs = qs.filter(data__gte=data_ini)
    if data_fim:
        qs = qs.filter(data__lte=data_fim)
    paginator = Paginator(qs.order_by('-criado_em'), 25)
    return render(request, 'embalagem/romaneio/list.html', {
        'page_obj': paginator.get_page(request.GET.get('page')),
        'status_choices': RomaneioVenda.STATUS,
        'tipo_choices': RomaneioVenda.TIPO,
        'filtros': {'q': q, 'status': status_f, 'tipo': tipo_f, 'data_ini': data_ini, 'data_fim': data_fim},
    })


@login_required
def romaneio_create(request):
    empresa = _get_empresa(request)
    if request.method == 'POST':
        form = RomaneioVendaForm(request.POST, empresa=empresa)
        if form.is_valid():
            with transaction.atomic():
                rom = form.save(commit=False)
                rom.empresa = empresa
                rom.numero = RomaneioVenda._gerar_numero(empresa)
                rom.criado_por = request.user
                rom.save()
            messages.success(request, f'Romaneio {rom.numero} criado.')
            return redirect('embalagem:romaneio_detail', pk=rom.pk)
    else:
        form = RomaneioVendaForm(empresa=empresa)
    return render(request, 'embalagem/romaneio/form.html', {
        'form': form, 'title': 'Novo Romaneio de Venda',
    })


@login_required
def romaneio_update(request, pk):
    empresa = _get_empresa(request)
    rom = get_object_or_404(RomaneioVenda, pk=pk, empresa=empresa)
    if rom.status != 'RASCUNHO':
        messages.error(request, 'Apenas romaneios em RASCUNHO podem ser editados.')
        return redirect('embalagem:romaneio_detail', pk=pk)
    if request.method == 'POST':
        form = RomaneioVendaForm(request.POST, instance=rom, empresa=empresa)
        if form.is_valid():
            form.save()
            messages.success(request, 'Romaneio atualizado.')
            return redirect('embalagem:romaneio_detail', pk=pk)
    else:
        form = RomaneioVendaForm(instance=rom, empresa=empresa)
    return render(request, 'embalagem/romaneio/form.html', {
        'form': form, 'title': 'Editar Romaneio', 'obj': rom,
    })


@login_required
def romaneio_detail(request, pk):
    empresa = _get_empresa(request)
    rom = get_object_or_404(RomaneioVenda, pk=pk, empresa=empresa)
    itens = rom.itens.select_related('pallet__tipo_embalagem', 'pallet__armazem').order_by('pallet__codigo_pallet')
    armazens = Armazem.objects.filter(empresa=empresa).order_by('nome')
    return render(request, 'embalagem/romaneio/detail.html', {
        'romaneio': rom,
        'itens': itens,
        'armazens': armazens,
    })


@login_required
@require_POST
def romaneio_confirmar(request, pk):
    empresa = _get_empresa(request)
    rom = get_object_or_404(RomaneioVenda, pk=pk, empresa=empresa)
    if rom.status != 'RASCUNHO':
        messages.error(request, 'Apenas romaneios em RASCUNHO podem ser confirmados.')
        return redirect('embalagem:romaneio_detail', pk=pk)
    if not rom.itens.exists():
        messages.error(request, 'Adicione pelo menos um pallet antes de confirmar.')
        return redirect('embalagem:romaneio_detail', pk=pk)
    with transaction.atomic():
        # Reservar pallets
        pallet_ids = rom.itens.values_list('pallet_id', flat=True)
        PalletEmbalado.objects.filter(pk__in=pallet_ids).update(status='RESERVADO')
        rom.status = 'CONFIRMADO'
        rom.save(update_fields=['status'])
    messages.success(request, f'Romaneio {rom.numero} confirmado. Pallets reservados.')
    return redirect('embalagem:romaneio_detail', pk=pk)


@login_required
@require_POST
def romaneio_gerar_pedido(request, pk):
    empresa = _get_empresa(request)
    rom = get_object_or_404(RomaneioVenda, pk=pk, empresa=empresa)
    if rom.pedido_venda_id:
        messages.warning(request, 'Romaneio já possui pedido de venda vinculado.')
        return redirect('embalagem:romaneio_detail', pk=pk)
    if rom.status not in ('CONFIRMADO', 'CARREGANDO'):
        messages.error(request, 'Confirme o romaneio antes de gerar o pedido.')
        return redirect('embalagem:romaneio_detail', pk=pk)

    from vendas.models import PedidoVenda, ItemPedidoVenda

    with transaction.atomic():
        ano = timezone.now().year
        # select_for_update evita race condition na geração do número do pedido
        ultimo = PedidoVenda.objects.select_for_update().filter(
            empresa=empresa, numero__startswith=f'PV-{ano}-'
        ).order_by('numero').last()
        if ultimo and ultimo.numero:
            try:
                seq = int(ultimo.numero.split('-')[-1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        numero_pv = f'PV-{ano}-{seq:04d}'

        tipo_venda = 'EXPORTACAO' if rom.tipo == 'EXPORTACAO' else 'MERCADO_INTERNO'
        moeda = 'USD' if rom.tipo == 'EXPORTACAO' else 'BRL'

        pedido = PedidoVenda.objects.create(
            empresa=empresa,
            numero=numero_pv,
            cliente=rom.cliente,
            data_pedido=rom.data,
            status='RASCUNHO',
            tipo_venda=tipo_venda,
            moeda=moeda,
            criado_por=request.user,
        )

        for te, totais in _agrupar_itens_por_tipo(rom).items():
            ItemPedidoVenda.objects.create(
                pedido=pedido,
                produto=te.produto,
                descricao=te.nome,
                unidade='CX',
                quantidade=totais['caixas'],
                preco_unitario=Decimal('0'),
                preco_total=Decimal('0'),
            )

        pedido.calcular_total()
        rom.pedido_venda = pedido
        rom.save(update_fields=['pedido_venda'])

    messages.success(request, f'Pedido {pedido.numero} criado a partir do romaneio.')
    return redirect('vendas:pedido_detail', pk=pedido.pk)


@login_required
@require_POST
def romaneio_remover_pallet(request, pk, item_pk):
    empresa = _get_empresa(request)
    rom = get_object_or_404(RomaneioVenda, pk=pk, empresa=empresa)
    if rom.status != 'RASCUNHO':
        return JsonResponse({'erro': 'Romaneio não está em RASCUNHO'}, status=400)
    item = get_object_or_404(ItemRomaneioVenda, pk=item_pk, romaneio=rom)
    item.pallet.status = 'DISPONIVEL'
    item.pallet.save(update_fields=['status'])
    item.delete()
    messages.success(request, 'Pallet removido do romaneio.')
    return redirect('embalagem:romaneio_detail', pk=pk)


# ─────────────────── Trocar Cliente / Booking ───────────────────────────────

@login_required
def romaneio_trocar_cliente(request, pk):
    empresa = _get_empresa(request)
    rom = get_object_or_404(RomaneioVenda, pk=pk, empresa=empresa)
    if rom.status not in ('CONFIRMADO', 'CARREGANDO'):
        messages.error(request, 'Só é possível trocar o cliente em romaneios Confirmados ou Carregando.')
        return redirect('embalagem:romaneio_detail', pk=pk)
    if request.method == 'POST':
        form = TrocarClienteRomaneioForm(request.POST, instance=rom, empresa=empresa)
        if form.is_valid():
            form.save(commit=False)
            rom.cliente = form.cleaned_data['cliente']
            rom.booking = form.cleaned_data.get('booking')
            rom.container = form.cleaned_data.get('container')
            rom.save(update_fields=['cliente', 'booking', 'container'])
            messages.success(request, 'Cliente/Booking atualizado sem alterar os pallets reservados.')
            return redirect('embalagem:romaneio_detail', pk=pk)
    else:
        form = TrocarClienteRomaneioForm(instance=rom, empresa=empresa)
    return render(request, 'embalagem/romaneio/trocar_cliente.html', {
        'form': form, 'romaneio': rom,
    })


# ─────────────────────── Gerar Documentos Fiscais ───────────────────────────

def _agrupar_itens_por_tipo(rom):
    """Agrupa itens do romaneio por TipoEmbalagem, somando caixas e pesos."""
    from collections import defaultdict
    grupos = defaultdict(lambda: {
        'caixas': 0, 'peso_bruto': Decimal('0'), 'peso_liquido': Decimal('0'), 'pallets': 0,
    })
    itens_qs = rom.itens.select_related(
        'pallet__tipo_embalagem'
    ).prefetch_related('pallet__composicao__tipo_embalagem')
    for item in itens_qs:
        pallet = item.pallet
        if pallet.is_misto:
            for comp in pallet.composicao.all():
                te = comp.tipo_embalagem
                grupos[te]['caixas'] += comp.quantidade_caixas
                grupos[te]['peso_bruto'] += comp.peso_bruto_kg
                grupos[te]['peso_liquido'] += comp.peso_liquido_kg
        else:
            te = pallet.tipo_embalagem
            grupos[te]['caixas'] += item.quantidade_caixas
            grupos[te]['peso_bruto'] += item.peso_bruto_kg
            grupos[te]['peso_liquido'] += item.peso_liquido_kg
            grupos[te]['pallets'] += 1
    return dict(grupos)


@login_required
@require_POST
def romaneio_gerar_invoice(request, pk):
    empresa = _get_empresa(request)
    rom = get_object_or_404(RomaneioVenda, pk=pk, empresa=empresa)
    if rom.tipo != 'EXPORTACAO':
        messages.error(request, 'Esta ação é apenas para romaneios de Exportação.')
        return redirect('embalagem:romaneio_detail', pk=pk)
    if not rom.booking:
        messages.error(request, 'Associe um Booking ao romaneio antes de gerar a Invoice.')
        return redirect('embalagem:romaneio_detail', pk=pk)
    if rom.invoice_exportacao_id:
        messages.warning(request, 'Romaneio já possui Invoice vinculada.')
        return redirect('embalagem:romaneio_detail', pk=pk)
    if rom.status not in ('CONFIRMADO', 'CARREGANDO', 'CONCLUIDO'):
        messages.error(request, 'Confirme o romaneio antes de gerar a Invoice.')
        return redirect('embalagem:romaneio_detail', pk=pk)

    from faturamento.models import InvoiceExportacao, ItemInvoice, PackingList, ItemPackingList

    grupos = _agrupar_itens_por_tipo(rom)
    booking = rom.booking

    porto_embarque = ''
    porto_destino = ''
    data_embarque = None
    if hasattr(booking, 'porto_embarque') and booking.porto_embarque:
        porto_embarque = getattr(booking.porto_embarque, 'nome', str(booking.porto_embarque))
    if booking.porto_destino:
        porto_destino = getattr(booking.porto_destino, 'nome', str(booking.porto_destino))
    if hasattr(booking, 'data_embarque_previsto'):
        data_embarque = booking.data_embarque_previsto

    with transaction.atomic():
        invoice = InvoiceExportacao.objects.create(
            empresa=empresa,
            booking=booking,
            cliente=rom.cliente,
            data_emissao=timezone.now().date(),
            data_embarque_previsto=data_embarque,
            porto_embarque=porto_embarque,
            porto_destino=porto_destino,
            criado_por=request.user,
        )

        for te, totais in grupos.items():
            ItemInvoice.objects.create(
                invoice=invoice,
                container=rom.container,
                descricao=te.descricao_completa,
                quantidade=totais['caixas'],
                unidade='CTN',
                peso_bruto_kg=totais['peso_bruto'],
                peso_liquido_kg=totais['peso_liquido'],
                valor_unitario_fob=Decimal('0'),
            )

        invoice.calcular_totais()

        pl = PackingList.objects.create(
            empresa=empresa,
            invoice=invoice,
            data_emissao=timezone.now().date(),
            criado_por=request.user,
        )
        nr_container = rom.container.numero_container if rom.container else ''
        for i, (te, totais) in enumerate(grupos.items(), start=1):
            ItemPackingList.objects.create(
                packing_list=pl,
                container=rom.container,
                numero_container=nr_container,
                descricao_produto=te.descricao_completa,
                quantidade_caixas=totais['caixas'],
                quantidade_pallets=totais['pallets'] or None,
                peso_bruto_kg=totais['peso_bruto'],
                peso_liquido_kg=totais['peso_liquido'],
                ordem=i,
            )

        rom.invoice_exportacao = invoice
        rom.save(update_fields=['invoice_exportacao'])

    messages.success(request, 'Invoice e Packing List gerados em Rascunho. Complete os preços antes de emitir.')
    return redirect('faturamento:invoice_detail', pk=invoice.pk)


@login_required
@require_POST
def romaneio_gerar_nota_fiscal(request, pk):
    empresa = _get_empresa(request)
    rom = get_object_or_404(RomaneioVenda, pk=pk, empresa=empresa)
    if rom.tipo != 'MERCADO_INTERNO':
        messages.error(request, 'Esta ação é apenas para romaneios de Mercado Interno.')
        return redirect('embalagem:romaneio_detail', pk=pk)
    if rom.nota_fiscal_id:
        messages.warning(request, 'Romaneio já possui Nota Fiscal vinculada.')
        return redirect('embalagem:romaneio_detail', pk=pk)
    if rom.status not in ('CONFIRMADO', 'CARREGANDO', 'CONCLUIDO'):
        messages.error(request, 'Confirme o romaneio antes de gerar a Nota Fiscal.')
        return redirect('embalagem:romaneio_detail', pk=pk)

    from faturamento.models import ConfiguracaoFiscal, ItemNotaFiscal, NotaFiscal

    grupos = _agrupar_itens_por_tipo(rom)

    with transaction.atomic():
        try:
            cfg = empresa.configuracao_fiscal
            cfop = cfg.cfop_venda_interna
            natureza = cfg.natureza_operacao_padrao
        except Exception:
            cfop = '5102'
            natureza = 'VENDA DE MERCADORIA'

        nf = NotaFiscal.objects.create(
            empresa=empresa,
            cliente=rom.cliente,
            data_emissao=timezone.now().date(),
            cfop=cfop,
            natureza_operacao=natureza,
            criado_por=request.user,
        )

        for i, (te, totais) in enumerate(grupos.items(), start=1):
            ItemNotaFiscal.objects.create(
                nota_fiscal=nf,
                numero_item=i,
                descricao=te.descricao_completa,
                produto=te.produto,
                cfop=cfop,
                unidade='CX',
                quantidade=totais['caixas'],
                valor_unitario=Decimal('0'),
            )

        nf.calcular_totais()
        rom.nota_fiscal = nf
        rom.save(update_fields=['nota_fiscal'])

    messages.success(request, 'Pré-Nota Fiscal gerada em Rascunho. Informe os preços e emita.')
    return redirect('faturamento:nota_fiscal_detail', pk=nf.pk)


# ─────────────────────────── Conferência ────────────────────────────────────

@login_required
def romaneio_conferencia_pdf(request, pk):
    """Relatório de carregamento (para assinatura na doca)."""
    empresa = _get_empresa(request)
    rom = get_object_or_404(
        RomaneioVenda.objects.select_related(
            'cliente', 'booking__armador', 'booking__navio',
            'booking__porto_destino', 'container', 'empresa',
        ),
        pk=pk, empresa=empresa,
    )
    itens = (
        rom.itens
        .select_related(
            'pallet__tipo_embalagem', 'pallet__armazem',
            'conferido_por',
        )
        .prefetch_related('pallet__composicao__tipo_embalagem')
        .order_by('pallet__codigo_pallet')
    )
    from django.template.loader import render_to_string
    from xhtml2pdf import pisa
    html = render_to_string('embalagem/romaneio/conferencia_pdf.html', {
        'romaneio': rom,
        'itens': itens,
        'empresa': empresa,
        'hoje': timezone.now(),
    })
    buf = io.BytesIO()
    pisa.CreatePDF(html, dest=buf)
    buf.seek(0)
    resp = HttpResponse(buf.read(), content_type='application/pdf')
    resp['Content-Disposition'] = f'inline; filename="conferencia-{rom.numero}.pdf"'
    return resp


@login_required
def romaneio_conferencia(request, pk):
    empresa = _get_empresa(request)
    rom = get_object_or_404(RomaneioVenda, pk=pk, empresa=empresa)
    itens = rom.itens.select_related('pallet__tipo_embalagem', 'conferido_por').order_by('pallet__codigo_pallet')
    pallets_conferidos = itens.filter(status_conferencia='CONFERIDO').count()
    total_pallets = itens.count()
    return render(request, 'embalagem/romaneio/conferencia.html', {
        'romaneio': rom,
        'itens': itens,
        'pallets_conferidos': pallets_conferidos,
        'total_pallets': total_pallets,
    })


# ─────────────────────────── AJAX ───────────────────────────────────────────

@login_required
def ajax_pallets_disponiveis(request):
    empresa = _get_empresa(request)
    qs = PalletEmbalado.objects.filter(
        empresa=empresa, status='DISPONIVEL'
    ).select_related('tipo_embalagem', 'armazem')

    tipo_id = request.GET.get('tipo_embalagem')
    armazem_id = request.GET.get('armazem')
    q = request.GET.get('q', '')

    if tipo_id:
        qs = qs.filter(tipo_embalagem_id=tipo_id)
    if armazem_id:
        qs = qs.filter(armazem_id=armazem_id)
    if q:
        qs = qs.filter(codigo_pallet__icontains=q)

    data = [{
        'pk': p.pk,
        'codigo_pallet': p.codigo_pallet,
        'tipo_embalagem': p.tipo_embalagem.nome if p.tipo_embalagem else 'Misto',
        'quantidade_caixas': p.quantidade_caixas,
        'peso_bruto_kg': float(p.peso_bruto_kg),
        'peso_liquido_kg': float(p.peso_liquido_kg),
        'armazem': p.armazem.nome,
        'data_embalagem': p.data_embalagem.strftime('%d/%m/%Y'),
    } for p in qs[:100]]

    return JsonResponse({'pallets': data})


@login_required
@require_POST
def ajax_adicionar_pallet(request):
    empresa = _get_empresa(request)
    try:
        body = json.loads(request.body)
        romaneio_pk = body.get('romaneio_pk')
        pallet_pk = body.get('pallet_pk')
        marks_numbers = body.get('marks_numbers', '')
    except (ValueError, KeyError):
        return JsonResponse({'erro': 'Dados inválidos'}, status=400)

    rom = get_object_or_404(RomaneioVenda, pk=romaneio_pk, empresa=empresa)
    if rom.status != 'RASCUNHO':
        return JsonResponse({'erro': 'Romaneio não está em RASCUNHO'}, status=400)

    pallet = get_object_or_404(PalletEmbalado, pk=pallet_pk, empresa=empresa, status='DISPONIVEL')

    if ItemRomaneioVenda.objects.filter(romaneio=rom, pallet=pallet).exists():
        return JsonResponse({'erro': 'Pallet já adicionado neste romaneio'}, status=400)

    with transaction.atomic():
        item = ItemRomaneioVenda.objects.create(
            romaneio=rom,
            pallet=pallet,
            quantidade_caixas=pallet.quantidade_caixas,
            peso_bruto_kg=pallet.peso_bruto_kg,
            peso_liquido_kg=pallet.peso_liquido_kg,
            marks_numbers=marks_numbers,
        )
        pallet.status = 'RESERVADO'
        pallet.save(update_fields=['status'])

    return JsonResponse({
        'ok': True,
        'item_pk': item.pk,
        'codigo_pallet': pallet.codigo_pallet,
        'tipo_embalagem': pallet.tipo_embalagem.nome if pallet.tipo_embalagem else 'Misto',
        'quantidade_caixas': pallet.quantidade_caixas,
        'peso_bruto_kg': float(pallet.peso_bruto_kg),
        'peso_liquido_kg': float(pallet.peso_liquido_kg),
    })


@login_required
@require_POST
def ajax_conferir_pallet(request):
    empresa = _get_empresa(request)
    try:
        body = json.loads(request.body)
        codigo = body.get('codigo_pallet', '').strip()
        romaneio_pk = body.get('romaneio_pk')
    except (ValueError, KeyError):
        return JsonResponse({'ok': False, 'status': 'erro', 'msg': 'Dados inválidos'}, status=400)

    rom = get_object_or_404(RomaneioVenda, pk=romaneio_pk, empresa=empresa)

    try:
        pallet = PalletEmbalado.objects.get(codigo_pallet=codigo, empresa=empresa)
    except PalletEmbalado.DoesNotExist:
        return JsonResponse({
            'ok': False,
            'status': 'nao_encontrado',
            'msg': f'Pallet "{codigo}" não encontrado no sistema.',
            'alerta': True,
        })

    try:
        item = ItemRomaneioVenda.objects.get(romaneio=rom, pallet=pallet)
    except ItemRomaneioVenda.DoesNotExist:
        return JsonResponse({
            'ok': False,
            'status': 'nao_pertence',
            'msg': f'Pallet {codigo} NÃO pertence a este romaneio!',
            'alerta': True,
        })

    if item.status_conferencia == 'CONFERIDO':
        return JsonResponse({
            'ok': False,
            'status': 'ja_conferido',
            'msg': f'Pallet {codigo} já foi conferido.',
            'pallet': {'codigo': codigo, 'caixas': item.quantidade_caixas},
        })

    with transaction.atomic():
        item.status_conferencia = 'CONFERIDO'
        item.data_conferencia = timezone.now()
        item.conferido_por = request.user
        item.save(update_fields=['status_conferencia', 'data_conferencia', 'conferido_por'])
        pallet.status = 'CARREGADO'
        pallet.save(update_fields=['status'])

        # Se todos conferidos → romaneio CONCLUIDO
        total = rom.itens.count()
        conferidos = rom.itens.filter(status_conferencia='CONFERIDO').count()
        if total == conferidos:
            rom.status = 'CONCLUIDO'
            rom.save(update_fields=['status'])

    return JsonResponse({
        'ok': True,
        'status': 'conferido',
        'msg': f'✅ Pallet {codigo} conferido!',
        'pallet': {
            'codigo': codigo,
            'caixas': item.quantidade_caixas,
            'peso_bruto': float(item.peso_bruto_kg),
        },
        'progresso': {'conferidos': conferidos, 'total': total},
    })


# ─────────────────────────── Pallet Misto ───────────────────────────────────

@login_required
@require_POST
def pallet_misto_create(request, ordem_pk):
    empresa = _get_empresa(request)
    ordem = get_object_or_404(OrdemEmbalagem, pk=ordem_pk, empresa=empresa)

    if ordem.status == 'CANCELADA':
        messages.error(request, 'Ordem cancelada não pode receber pallets.')
        return redirect('embalagem:ordem_detail', pk=ordem_pk)

    hoje = timezone.now().date()
    with transaction.atomic():
        seq = ordem.pallets.count() + 1
        codigo = PalletEmbalado._gerar_codigo(empresa, hoje, safra=ordem.safra)
        pallet = PalletEmbalado.objects.create(
            empresa=empresa,
            codigo_pallet=codigo,
            ordem_embalagem=ordem,
            tipo_embalagem=None,
            is_misto=True,
            numero_sequencial=seq,
            quantidade_caixas=0,
            peso_bruto_kg=0,
            peso_liquido_kg=0,
            data_embalagem=hoje,
            armazem=ordem.armazem_destino,
            local_estocagem=ordem.local_destino,
            status='DISPONIVEL',
        )
        if ordem.status == 'ABERTA':
            ordem.status = 'EM_ANDAMENTO'
            ordem.save(update_fields=['status'])

    return redirect('embalagem:pallet_misto_detail', pk=pallet.pk)


@login_required
def pallet_misto_detail(request, pk):
    empresa = _get_empresa(request)
    pallet = get_object_or_404(PalletEmbalado, pk=pk, empresa=empresa, is_misto=True)
    itens = pallet.composicao.select_related('tipo_embalagem__cultura', 'tipo_embalagem__produto').all()
    capacidade = pallet.ordem_embalagem.capacidade_caixas_pallet
    return render(request, 'embalagem/pallet/detalhe_misto.html', {
        'pallet': pallet,
        'itens': itens,
        'form': ItemPalletForm(empresa=empresa),
        'capacidade': capacidade,
        'alerta_capacidade': pallet.alerta_capacidade,
    })


@login_required
@require_POST
def pallet_misto_add_item(request, pk):
    empresa = _get_empresa(request)
    pallet = get_object_or_404(PalletEmbalado, pk=pk, empresa=empresa, is_misto=True)

    if pallet.status != 'DISPONIVEL':
        return JsonResponse({'erro': 'Pallet não pode ser editado neste status.'}, status=400)

    form = ItemPalletForm(request.POST, empresa=empresa)
    if not form.is_valid():
        return JsonResponse({'erro': str(form.errors)}, status=400)

    with transaction.atomic():
        item = form.save(commit=False)
        item.pallet = pallet
        item.save()  # save() do ItemPallet calcula pesos e chama recalcular_totais

    pallet.refresh_from_db()
    capacidade = pallet.ordem_embalagem.capacidade_caixas_pallet
    alerta = bool(capacidade and pallet.quantidade_caixas != capacidade)
    return JsonResponse({
        'ok': True,
        'item_pk': item.pk,
        'descricao': item.tipo_embalagem.descricao_completa,
        'quantidade_caixas': item.quantidade_caixas,
        'peso_liquido_kg': float(item.peso_liquido_kg),
        'peso_bruto_kg': float(item.peso_bruto_kg),
        'total_caixas': pallet.quantidade_caixas,
        'total_liquido': float(pallet.peso_liquido_kg),
        'total_bruto': float(pallet.peso_bruto_kg),
        'alerta': alerta,
        'alerta_msg': (
            f'⚠️ Total de caixas ({pallet.quantidade_caixas}) ≠ capacidade esperada ({capacidade})'
            if alerta else ''
        ),
    })


@login_required
@require_POST
def pallet_misto_remove_item(request, pk, item_pk):
    empresa = _get_empresa(request)
    pallet = get_object_or_404(PalletEmbalado, pk=pk, empresa=empresa, is_misto=True)
    item = get_object_or_404(ItemPallet, pk=item_pk, pallet=pallet)

    with transaction.atomic():
        item.delete()  # delete() do ItemPallet chama recalcular_totais

    pallet.refresh_from_db()
    capacidade = pallet.ordem_embalagem.capacidade_caixas_pallet
    alerta = bool(capacidade and pallet.quantidade_caixas != capacidade)
    return JsonResponse({
        'ok': True,
        'total_caixas': pallet.quantidade_caixas,
        'total_liquido': float(pallet.peso_liquido_kg),
        'total_bruto': float(pallet.peso_bruto_kg),
        'alerta': alerta,
        'alerta_msg': (
            f'⚠️ Total de caixas ({pallet.quantidade_caixas}) ≠ capacidade esperada ({capacidade})'
            if alerta else ''
        ),
    })
