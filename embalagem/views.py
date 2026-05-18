import io
import math
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import OrdemEmbalagemForm, RomaneioVendaForm, TipoEmbalagemForm
from .models import (
    ItemRomaneioVenda, OrdemEmbalagem, PalletEmbalado, RomaneioVenda, TipoEmbalagem,
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
    qs = TipoEmbalagem.objects.filter(empresa=empresa).select_related('produto', 'cultura')
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
            codigo = PalletEmbalado._gerar_codigo(empresa, hoje)
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

    from estoque.models import Armazem
    armazens = Armazem.objects.filter(empresa=empresa).order_by('nome')

    data_ini = request.GET.get('data_ini', '')
    data_fim = request.GET.get('data_fim', '')
    if data_ini:
        qs = qs.filter(data_embalagem__gte=data_ini)
    if data_fim:
        qs = qs.filter(data_embalagem__lte=data_fim)
    stats = {
        'disponiveis': PalletEmbalado.objects.filter(empresa=empresa, status='DISPONIVEL').count(),
        'reservados': PalletEmbalado.objects.filter(empresa=empresa, status='RESERVADO').count(),
        'carregados': PalletEmbalado.objects.filter(empresa=empresa, status='CARREGADO').count(),
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

def _barcode_b64(codigo):
    """Gera um Code128 em base64 para embutir no PDF."""
    try:
        import barcode as pybarcode
        import base64
        cls = pybarcode.get_barcode_class('code128')
        buf = io.BytesIO()
        cls(codigo, writer=pybarcode.writer.ImageWriter()).write(buf, options={
            'module_height': 10, 'module_width': 0.4, 'quiet_zone': 2,
            'text_distance': 1, 'font_size': 7, 'write_text': False,
        })
        buf.seek(0)
        return base64.b64encode(buf.read()).decode()
    except Exception:
        return None


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
    pallet = get_object_or_404(PalletEmbalado, pk=pk, empresa=empresa)
    # Tenta obter romaneio vinculado
    item_rom = pallet.itens_romaneio.select_related('romaneio__cliente', 'romaneio__booking__transportadora').first()
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
    pallets = list(ordem.pallets.order_by('numero_sequencial'))
    pdf = _render_etiqueta_pdf(pallets)
    PalletEmbalado.objects.filter(ordem_embalagem=ordem).update(etiqueta_gerada=True)
    resp = HttpResponse(pdf, content_type='application/pdf')
    resp['Content-Disposition'] = f'inline; filename="etiquetas-{ordem.numero}.pdf"'
    return resp


@login_required
def romaneio_etiquetas_pdf(request, pk):
    empresa = _get_empresa(request)
    romaneio = get_object_or_404(RomaneioVenda, pk=pk, empresa=empresa)
    pallets = [item.pallet for item in romaneio.itens.select_related('pallet').order_by('pallet__codigo_pallet')]
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
    from estoque.models import Armazem
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
    from django.db.models import Max as _Max

    with transaction.atomic():
        # Gerar número do pedido
        ano = timezone.now().year
        ultimo = PedidoVenda.objects.filter(
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

        for item in rom.itens.select_related('pallet__tipo_embalagem__produto'):
            te = item.pallet.tipo_embalagem
            produto = te.produto
            ItemPedidoVenda.objects.create(
                pedido=pedido,
                produto=produto,
                descricao=te.nome,
                unidade='CX',
                quantidade=item.quantidade_caixas,
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


# ─────────────────────────── Conferência ────────────────────────────────────

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
        'tipo_embalagem': p.tipo_embalagem.nome,
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
    import json
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
        'tipo_embalagem': pallet.tipo_embalagem.nome,
        'quantidade_caixas': pallet.quantidade_caixas,
        'peso_bruto_kg': float(pallet.peso_bruto_kg),
        'peso_liquido_kg': float(pallet.peso_liquido_kg),
    })


@login_required
@require_POST
def ajax_conferir_pallet(request):
    import json
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
