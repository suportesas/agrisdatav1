import io
import json
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from core.pagination import paginate
from django.db import transaction
from django.db.models import Case, Count, Q, Value, When
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from estoque.models import Armazem, Lote, MovimentacaoEstoque

from .forms import (
    CargaFreteForm, FaixaPesoCalibreForm, GerarPalletsForm, ItemPalletForm, MaterialEmbalagemForm,
    OrdemEmbalagemForm, OrdemParceiroForm, PalletParceiroForm, RomaneioVendaForm, TipoEmbalagemClienteForm,
    TipoEmbalagemForm, TrocarClienteRomaneioForm,
)
from .models import (
    CargaFrete, CargaFreteError, FaixaPesoCalibre, ItemPallet, ItemRomaneioVenda, MaterialEmbalagem,
    OrdemEmbalagem, PalletEmbalado, RomaneioMaterialEmbalagem, RomaneioVenda, TipoEmbalagem, TipoEmbalagemCliente,
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
    ultimas_ordens = OrdemEmbalagem.objects.filter(empresa=empresa).prefetch_related('tipos_embalagem').order_by('-criado_em')[:4]
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

    tipos, per_page, per_page_options = paginate(request, qs.order_by('nome'))

    return render(request, 'embalagem/tipo_embalagem/list.html', {
        'tipos': tipos,
        'q': q,
        'per_page': per_page,
        'per_page_options': per_page_options,
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


# ─────────────────────────── MaterialEmbalagem ───────────────────────────────

@login_required
def material_embalagem_list(request):
    empresa = _get_empresa(request)
    qs = MaterialEmbalagem.objects.filter(empresa=empresa).select_related('produto__fornecedor_padrao').prefetch_related(
        'produto__fornecedores_relacionados__fornecedor'
    )
    q = request.GET.get('q', '')
    tipo_f = request.GET.get('tipo', '')
    if q:
        qs = qs.filter(produto__nome__icontains=q)
    if tipo_f:
        qs = qs.filter(tipo=tipo_f)

    materiais, per_page, per_page_options = paginate(request, qs.order_by('tipo', 'produto__nome'))

    return render(request, 'embalagem/material_embalagem/list.html', {
        'materiais': materiais,
        'q': q,
        'tipo_f': tipo_f,
        'tipo_choices': MaterialEmbalagem.TIPO,
        'per_page': per_page,
        'per_page_options': per_page_options,
    })


@login_required
def material_embalagem_create(request):
    empresa = _get_empresa(request)
    if request.method == 'POST':
        form = MaterialEmbalagemForm(request.POST, empresa=empresa)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.empresa = empresa
            obj.save()
            messages.success(request, 'Material de embalagem criado com sucesso.')
            return redirect('embalagem:material_embalagem_list')
    else:
        form = MaterialEmbalagemForm(empresa=empresa)
    return render(request, 'embalagem/material_embalagem/form.html', {
        'form': form, 'title': 'Novo Material de Embalagem',
    })


@login_required
def material_embalagem_update(request, pk):
    empresa = _get_empresa(request)
    obj = get_object_or_404(MaterialEmbalagem, pk=pk, empresa=empresa)
    if request.method == 'POST':
        form = MaterialEmbalagemForm(request.POST, instance=obj, empresa=empresa)
        if form.is_valid():
            form.save()
            messages.success(request, 'Material de embalagem atualizado.')
            return redirect('embalagem:material_embalagem_list')
    else:
        form = MaterialEmbalagemForm(instance=obj, empresa=empresa)
    return render(request, 'embalagem/material_embalagem/form.html', {
        'form': form, 'title': 'Editar Material de Embalagem', 'obj': obj,
    })


# ─────────────────────────── TipoEmbalagemCliente (IAN) ─────────────────────

@login_required
def tipo_embalagem_cliente_list(request):
    empresa = _get_empresa(request)
    qs = TipoEmbalagemCliente.objects.filter(empresa=empresa).select_related('cultura', 'cliente')
    q = request.GET.get('q', '')
    if q:
        qs = qs.filter(
            Q(cultura__nome__icontains=q) | Q(variedade__icontains=q) | Q(marca__icontains=q)
            | Q(cliente__razao_social__icontains=q) | Q(codigo_ian__icontains=q)
        )

    codigos, per_page, per_page_options = paginate(request, qs.order_by('cliente__razao_social'))

    return render(request, 'embalagem/tipo_embalagem_cliente/list.html', {
        'codigos': codigos,
        'q': q,
        'per_page': per_page,
        'per_page_options': per_page_options,
    })


@login_required
def tipo_embalagem_cliente_create(request):
    empresa = _get_empresa(request)
    if request.method == 'POST':
        form = TipoEmbalagemClienteForm(request.POST, empresa=empresa)
        if form.is_valid():
            form.save()
            messages.success(request, 'Código IAN cadastrado com sucesso.')
            return redirect('embalagem:tipo_embalagem_cliente_list')
    else:
        form = TipoEmbalagemClienteForm(empresa=empresa)
    return render(request, 'embalagem/tipo_embalagem_cliente/form.html', {
        'form': form, 'title': 'Novo Código IAN por Cliente',
    })


@login_required
def tipo_embalagem_cliente_update(request, pk):
    empresa = _get_empresa(request)
    obj = get_object_or_404(TipoEmbalagemCliente, pk=pk, empresa=empresa)
    if request.method == 'POST':
        form = TipoEmbalagemClienteForm(request.POST, instance=obj, empresa=empresa)
        if form.is_valid():
            form.save()
            messages.success(request, 'Código IAN atualizado.')
            return redirect('embalagem:tipo_embalagem_cliente_list')
    else:
        form = TipoEmbalagemClienteForm(instance=obj, empresa=empresa)
    return render(request, 'embalagem/tipo_embalagem_cliente/form.html', {
        'form': form, 'title': 'Editar Código IAN por Cliente', 'obj': obj,
    })


# ──────────────────────── FaixaPesoCalibre (Size-span & count) ──────────────

@login_required
def faixa_peso_calibre_list(request):
    empresa = _get_empresa(request)
    qs = FaixaPesoCalibre.objects.filter(empresa=empresa).select_related('cultura')
    q = request.GET.get('q', '')
    if q:
        qs = qs.filter(Q(cultura__nome__icontains=q) | Q(calibre__icontains=q))

    faixas, per_page, per_page_options = paginate(request, qs.order_by('cultura__nome', 'peso_carton', 'calibre'))

    return render(request, 'embalagem/faixa_peso_calibre/list.html', {
        'faixas': faixas,
        'q': q,
        'per_page': per_page,
        'per_page_options': per_page_options,
    })


@login_required
def faixa_peso_calibre_create(request):
    empresa = _get_empresa(request)
    if request.method == 'POST':
        form = FaixaPesoCalibreForm(request.POST, empresa=empresa)
        if form.is_valid():
            form.save()
            messages.success(request, 'Faixa de peso por calibre cadastrada com sucesso.')
            return redirect('embalagem:faixa_peso_calibre_list')
    else:
        form = FaixaPesoCalibreForm(empresa=empresa)
    return render(request, 'embalagem/faixa_peso_calibre/form.html', {
        'form': form, 'title': 'Nova Faixa de Peso por Calibre',
    })


@login_required
def faixa_peso_calibre_update(request, pk):
    empresa = _get_empresa(request)
    obj = get_object_or_404(FaixaPesoCalibre, pk=pk, empresa=empresa)
    if request.method == 'POST':
        form = FaixaPesoCalibreForm(request.POST, instance=obj, empresa=empresa)
        if form.is_valid():
            form.save()
            messages.success(request, 'Faixa de peso por calibre atualizada.')
            return redirect('embalagem:faixa_peso_calibre_list')
    else:
        form = FaixaPesoCalibreForm(instance=obj, empresa=empresa)
    return render(request, 'embalagem/faixa_peso_calibre/form.html', {
        'form': form, 'title': 'Editar Faixa de Peso por Calibre', 'obj': obj,
    })


# ─────────────────────────── OrdemEmbalagem ─────────────────────────────────

@login_required
def ordem_list(request):
    empresa = _get_empresa(request)
    qs = OrdemEmbalagem.objects.filter(empresa=empresa).select_related('lote_origem__produto').prefetch_related('tipos_embalagem')
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
    page_obj, per_page, per_page_options = paginate(request, qs.order_by('-criado_em'))
    return render(request, 'embalagem/ordem/list.html', {
        'page_obj': page_obj,
        'filtros': {'q': q, 'status': status_f, 'data_ini': data_ini, 'data_fim': data_fim},
        'status_choices': OrdemEmbalagem.STATUS,
        'per_page': per_page,
        'per_page_options': per_page_options,
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
                form.save_m2m()
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
    tipos = list(ordem.tipos_embalagem.all().order_by('nome'))
    tipos_resumo = [
        {'tipo': te, 'sugestao': ordem.pallets_possiveis(te)}
        for te in tipos
    ]
    tipos_info = {
        te.pk: {
            'peso_liquido_pallet': float(te.peso_liquido_pallet),
            'sugestao': ordem.pallets_possiveis(te),
        }
        for te in tipos
    }
    return render(request, 'embalagem/ordem/detail.html', {
        'ordem': ordem,
        'pallets': pallets,
        'tipos_embalagem': tipos,
        'tipos_resumo': tipos_resumo,
        'gerar_pallets_form': GerarPalletsForm(ordem=ordem),
        'tipos_info_json': json.dumps(tipos_info),
        'item_pallet_form': ItemPalletForm(ordem=ordem, auto_id='id_misto_%s'),
    })


@login_required
@require_POST
def ordem_gerar_pallets(request, pk):
    empresa = _get_empresa(request)
    ordem = get_object_or_404(OrdemEmbalagem, pk=pk, empresa=empresa)

    if ordem.status == 'CANCELADA':
        messages.error(request, 'Ordem cancelada não pode gerar pallets.')
        return redirect('embalagem:ordem_detail', pk=pk)

    form = GerarPalletsForm(request.POST, ordem=ordem)
    if not form.is_valid():
        for erros in form.errors.values():
            for erro in erros:
                messages.error(request, erro)
        return redirect('embalagem:ordem_detail', pk=pk)

    te = form.cleaned_data['tipo_embalagem']
    n_pallets = form.cleaned_data['n_pallets']

    peso_liq_pallet = te.peso_liquido_pallet
    if not peso_liq_pallet:
        messages.error(request, 'Tipo de embalagem inválido (peso zero).')
        return redirect('embalagem:ordem_detail', pk=pk)

    if not te.produto_id:
        messages.error(request, f'Tipo de embalagem "{te.nome}" não tem produto configurado — associe um produto antes de gerar pallets.')
        return redirect('embalagem:ordem_detail', pk=pk)

    hoje = timezone.now().date()
    from django.core.exceptions import ValidationError
    from estoque.services import criar_movimentacao
    try:
        with transaction.atomic():
            seq_inicial = ordem.pallets.count() + 1
            for seq in range(seq_inicial, seq_inicial + n_pallets):
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
                    estoque_baixado=True,
                )

            # Baixa o lote de matéria-prima a granel na quantidade efetivamente
            # empacotada (n_pallets * peso líquido do pallet) deste tipo.
            quantidade_empacotada = Decimal(n_pallets) * Decimal(peso_liq_pallet)
            criar_movimentacao(
                empresa=empresa,
                tipo='SAIDA',
                origem='PEDIDO_VENDA',
                quantidade=quantidade_empacotada,
                usuario=request.user,
                lote=ordem.lote_origem,
                documento=ordem.numero,
                observacao=f'Baixa por embalagem — Ordem {ordem.numero} ({n_pallets} pallets de {te.nome}).',
            )

            # Entrada em estoque do produto acabado (pallets gerados)
            total_caixas = Decimal(n_pallets) * Decimal(te.caixas_por_pallet)
            lote_embalado = Lote.objects.create(
                empresa=empresa,
                produto=te.produto,
                armazem=ordem.armazem_destino,
                local_estocagem=ordem.local_destino,
                numero_lote=f"EMB-{ordem.numero}-{te.pk}-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                data_fabricacao=hoje,
                quantidade_inicial=total_caixas,
                quantidade_atual=total_caixas,
                unidade_medida=te.produto.unidade_venda,
                status='DISPONIVEL',
                observacoes=f'Produto acabado da Ordem de Embalagem {ordem.numero} ({n_pallets} pallets de {te.nome}).',
                cadastrado_por=request.user,
            )
            MovimentacaoEstoque.objects.create(
                empresa=empresa,
                produto=te.produto,
                lote=lote_embalado,
                tipo='ENTRADA',
                origem='PRODUCAO',
                quantidade=total_caixas,
                documento=ordem.numero,
                observacao=f'Embalagem — Ordem {ordem.numero}: {n_pallets} pallets de {te.nome}.',
                status='EXECUTADO',
                cadastrado_por=request.user,
                executado_por=request.user,
                data_execucao=timezone.now(),
            )

            if ordem.status == 'ABERTA':
                ordem.status = 'EM_ANDAMENTO'
                ordem.save(update_fields=['status'])
    except ValidationError as exc:
        messages.error(request, f'Saldo insuficiente no lote de origem: {"; ".join(exc.messages)}')
        return redirect('embalagem:ordem_detail', pk=pk)

    messages.success(request, f'{n_pallets} pallets de {te.nome} gerados com sucesso.')
    return redirect('embalagem:ordem_detail', pk=pk)


# ──────────────── OrdemEmbalagem — Produtor Parceiro ────────────────────────

@login_required
def ordem_parceiro_create(request):
    empresa = _get_empresa(request)
    if request.method == 'POST':
        form = OrdemParceiroForm(request.POST, empresa=empresa)
        if form.is_valid():
            with transaction.atomic():
                produto = form.cleaned_data['produto']
                produtor = form.cleaned_data['produtor_parceiro']
                data = form.cleaned_data['data']
                armazem_destino = form.cleaned_data['armazem_destino']
                lote = Lote.objects.create(
                    empresa=empresa,
                    produto=produto,
                    armazem=armazem_destino,
                    numero_lote=f"PARCEIRO-{produtor.pk}-{data.strftime('%Y%m%d')}",
                    data_entrada=timezone.now(),
                    quantidade_inicial=Decimal('0'),
                    quantidade_atual=Decimal('0'),
                    unidade_medida=produto.unidade_venda,
                    observacoes=f'Placeholder — pallets recebidos prontos do produtor parceiro {produtor.razao_social}.',
                    cadastrado_por=request.user,
                )
                ordem = form.save(commit=False)
                ordem.empresa = empresa
                ordem.numero = OrdemEmbalagem._gerar_numero(empresa)
                ordem.criado_por = request.user
                ordem.lote_origem = lote
                ordem.quantidade_entrada_kg = Decimal('0')
                ordem.save()
            messages.success(request, f'Ordem de parceiro {ordem.numero} criada.')
            return redirect('embalagem:ordem_parceiro_detail', pk=ordem.pk)
    else:
        form = OrdemParceiroForm(empresa=empresa)
    return render(request, 'embalagem/ordem_parceiro/create.html', {
        'form': form, 'title': 'Nova Ordem de Produtor Parceiro',
    })


@login_required
def ordem_parceiro_detail(request, pk):
    empresa = _get_empresa(request)
    ordem = get_object_or_404(OrdemEmbalagem, pk=pk, empresa=empresa, produtor_parceiro__isnull=False)
    pallets = ordem.pallets.select_related('tipo_embalagem', 'armazem').order_by('numero_sequencial')
    return render(request, 'embalagem/ordem_parceiro/detail.html', {
        'ordem': ordem,
        'pallets': pallets,
        'pallet_form': PalletParceiroForm(ordem=ordem),
    })


@login_required
@require_POST
def ordem_parceiro_adicionar_pallet(request, pk):
    empresa = _get_empresa(request)
    ordem = get_object_or_404(OrdemEmbalagem, pk=pk, empresa=empresa, produtor_parceiro__isnull=False)
    form = PalletParceiroForm(request.POST, ordem=ordem)
    if not form.is_valid():
        return JsonResponse({'erro': str(form.errors)}, status=400)

    with transaction.atomic():
        pallet = form.save(commit=False)
        pallet.empresa = empresa
        pallet.ordem_embalagem = ordem
        pallet.numero_sequencial = ordem.pallets.count() + 1
        pallet.codigo_pallet = PalletEmbalado._gerar_codigo(empresa, ordem.data, safra=ordem.safra)
        pallet.data_embalagem = ordem.data
        pallet.armazem = ordem.armazem_destino
        pallet.local_estocagem = ordem.local_destino
        pallet.status = 'DISPONIVEL'
        pallet.estoque_baixado = True
        pallet.save()

    return JsonResponse({
        'ok': True,
        'pallet_pk': pallet.pk,
        'codigo_pallet': pallet.codigo_pallet,
        'tipo_embalagem': pallet.tipo_embalagem.label_completo if pallet.tipo_embalagem_id else '',
        'codigo_producao_externo': pallet.codigo_producao_externo,
        'quantidade_caixas': pallet.quantidade_caixas,
        'peso_bruto_kg': float(pallet.peso_bruto_kg),
        'peso_liquido_kg': float(pallet.peso_liquido_kg),
    })


@login_required
@require_POST
def ordem_parceiro_importar_xlsx(request, pk):
    empresa = _get_empresa(request)
    ordem = get_object_or_404(OrdemEmbalagem, pk=pk, empresa=empresa, produtor_parceiro__isnull=False)

    arquivo = request.FILES.get('arquivo')
    if not arquivo:
        messages.error(request, 'Selecione um arquivo .xlsx para importar.')
        return redirect('embalagem:ordem_parceiro_detail', pk=pk)

    import openpyxl
    try:
        wb = openpyxl.load_workbook(arquivo, data_only=True)
        ws = wb.active
        linhas = list(ws.iter_rows(min_row=2, values_only=True))
    except Exception:
        messages.error(request, 'Não foi possível ler o arquivo. Confirme que é um .xlsx válido, com uma linha por '
                                 'pallet: tipo_embalagem, codigo_rastreabilidade, qtd_caixas, peso_bruto_kg, peso_liquido_kg.')
        return redirect('embalagem:ordem_parceiro_detail', pk=pk)

    tipos_por_nome = {
        t.nome.strip().lower(): t
        for t in TipoEmbalagem.objects.filter(empresa=empresa, ativo=True)
    }

    criados, erros = 0, []
    with transaction.atomic():
        seq = ordem.pallets.count()
        for i, row in enumerate(linhas, start=2):
            if not row or not any(row):
                continue
            valores = list(row) + [None] * 5
            tipo_nome, codigo_rastreio, qtd_caixas, peso_bruto, peso_liquido = valores[:5]

            tipo = tipos_por_nome.get(str(tipo_nome or '').strip().lower())
            if not tipo:
                erros.append(f'Linha {i}: tipo de embalagem "{tipo_nome}" não encontrado ou inativo.')
                continue
            if not codigo_rastreio:
                erros.append(f'Linha {i}: código de rastreabilidade em branco.')
                continue
            try:
                qtd_caixas = int(qtd_caixas)
                peso_bruto = Decimal(str(peso_bruto))
                peso_liquido = Decimal(str(peso_liquido))
            except (TypeError, ValueError, ArithmeticError):
                erros.append(f'Linha {i}: quantidade de caixas ou peso inválido.')
                continue

            seq += 1
            PalletEmbalado.objects.create(
                empresa=empresa,
                codigo_pallet=PalletEmbalado._gerar_codigo(empresa, ordem.data, safra=ordem.safra),
                ordem_embalagem=ordem,
                tipo_embalagem=tipo,
                numero_sequencial=seq,
                quantidade_caixas=qtd_caixas,
                peso_bruto_kg=peso_bruto,
                peso_liquido_kg=peso_liquido,
                codigo_producao_externo=str(codigo_rastreio).strip(),
                data_embalagem=ordem.data,
                armazem=ordem.armazem_destino,
                local_estocagem=ordem.local_destino,
                status='DISPONIVEL',
                estoque_baixado=True,
            )
            criados += 1

    if criados:
        messages.success(request, f'{criados} pallet(s) importado(s) com sucesso.')
    for erro in erros[:20]:
        messages.error(request, erro)
    if len(erros) > 20:
        messages.error(request, f'... e mais {len(erros) - 20} linha(s) com erro.')

    return redirect('embalagem:ordem_parceiro_detail', pk=pk)


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
    page_obj, per_page, per_page_options = paginate(request, qs.order_by('-criado_em'))
    return render(request, 'embalagem/pallet/list.html', {
        'page_obj': page_obj,
        'status_choices': PalletEmbalado.STATUS,
        'filtros': {'q': q, 'status': status_f, 'armazem': armazem_f, 'data_ini': data_ini, 'data_fim': data_fim},
        'armazens': armazens,
        'stats': stats,
        'per_page': per_page,
        'per_page_options': per_page_options,
    })


# ─────────────────────────── Etiqueta PDF ───────────────────────────────────

_SELECT_RELATED_ETIQUETA = (
    'tipo_embalagem__cultura', 'tipo_embalagem__produto', 'empresa',
    'ordem_embalagem__safra', 'ordem_embalagem__lote_producao__talhao__fazenda',
    'ordem_embalagem__lote_producao__cultura', 'armazem',
)
_PREFETCH_RELATED_ETIQUETA = ('composicao__tipo_embalagem__cultura',)
_SELECT_RELATED_ROMANEIO_ETIQUETA = (
    'romaneio__cliente', 'romaneio__booking__solicitacao__armador',
    'romaneio__booking__solicitacao__navio', 'romaneio__booking__porto_destino',
    'romaneio__booking__porto_origem', 'romaneio__container',
)


@login_required
def pallet_etiqueta_pdf(request, pk):
    empresa = _get_empresa(request)
    pallet = get_object_or_404(
        PalletEmbalado.objects.select_related(*_SELECT_RELATED_ETIQUETA)
        .prefetch_related(*_PREFETCH_RELATED_ETIQUETA),
        pk=pk, empresa=empresa,
    )
    romaneio = _romaneio_do_pallet(pallet)
    from .pdf_pallet import render_etiquetas_pallet_pdf
    pdf = render_etiquetas_pallet_pdf([{'pallet': pallet, 'romaneio': romaneio}])
    pallet.etiqueta_gerada = True
    pallet.save(update_fields=['etiqueta_gerada'])
    resp = HttpResponse(pdf, content_type='application/pdf')
    resp['Content-Disposition'] = f'inline; filename="etiqueta-{pallet.codigo_pallet}.pdf"'
    return resp


def _romaneio_do_pallet(pallet, romaneio=None):
    if romaneio:
        return romaneio
    item = pallet.itens_romaneio.select_related(*_SELECT_RELATED_ROMANEIO_ETIQUETA).first()
    return item.romaneio if item else None


@login_required
def pallet_etiqueta_caixa_pdf(request, pk):
    empresa = _get_empresa(request)
    pallet = get_object_or_404(
        PalletEmbalado.objects.select_related(*_SELECT_RELATED_ETIQUETA)
        .prefetch_related(*_PREFETCH_RELATED_ETIQUETA),
        pk=pk, empresa=empresa,
    )
    from .pdf_caixa import render_etiquetas_caixa_pdf
    pdf = render_etiquetas_caixa_pdf([{'pallet': pallet, 'romaneio': _romaneio_do_pallet(pallet)}])
    resp = HttpResponse(pdf, content_type='application/pdf')
    resp['Content-Disposition'] = f'inline; filename="etiqueta-caixa-{pallet.codigo_pallet}.pdf"'
    return resp


@login_required
def ordem_etiquetas_pdf(request, pk):
    empresa = _get_empresa(request)
    ordem = get_object_or_404(OrdemEmbalagem, pk=pk, empresa=empresa)
    pallets = list(
        ordem.pallets
        .select_related(*_SELECT_RELATED_ETIQUETA)
        .prefetch_related(*_PREFETCH_RELATED_ETIQUETA)
        .order_by('numero_sequencial')
    )
    from .pdf_pallet import render_etiquetas_pallet_pdf
    pallets_ctx = [{'pallet': p, 'romaneio': _romaneio_do_pallet(p)} for p in pallets]
    pdf = render_etiquetas_pallet_pdf(pallets_ctx)
    PalletEmbalado.objects.filter(ordem_embalagem=ordem).update(etiqueta_gerada=True)
    resp = HttpResponse(pdf, content_type='application/pdf')
    resp['Content-Disposition'] = f'inline; filename="etiquetas-{ordem.numero}.pdf"'
    return resp


@login_required
def ordem_etiquetas_caixa_pdf(request, pk):
    empresa = _get_empresa(request)
    ordem = get_object_or_404(OrdemEmbalagem, pk=pk, empresa=empresa)
    pallets = list(
        ordem.pallets
        .select_related(*_SELECT_RELATED_ETIQUETA)
        .prefetch_related(*_PREFETCH_RELATED_ETIQUETA)
        .order_by('numero_sequencial')
    )
    from .pdf_caixa import render_etiquetas_caixa_pdf
    pallets_ctx = [{'pallet': p, 'romaneio': _romaneio_do_pallet(p)} for p in pallets]
    pdf = render_etiquetas_caixa_pdf(pallets_ctx)
    resp = HttpResponse(pdf, content_type='application/pdf')
    resp['Content-Disposition'] = f'inline; filename="etiquetas-caixa-{ordem.numero}.pdf"'
    return resp


@login_required
def romaneio_etiquetas_pdf(request, pk):
    empresa = _get_empresa(request)
    romaneio = get_object_or_404(
        RomaneioVenda.objects.select_related(
            'cliente', 'booking__solicitacao__armador', 'booking__solicitacao__navio',
            'booking__porto_destino', 'booking__porto_origem', 'container',
        ),
        pk=pk, empresa=empresa,
    )
    pallets = [
        item.pallet for item in romaneio.itens
        .select_related(*[f'pallet__{f}' for f in _SELECT_RELATED_ETIQUETA])
        .prefetch_related(*[f'pallet__{f}' for f in _PREFETCH_RELATED_ETIQUETA])
        .order_by('pallet__codigo_pallet')
    ]
    from .pdf_pallet import render_etiquetas_pallet_pdf
    pallets_ctx = [{'pallet': p, 'romaneio': romaneio} for p in pallets]
    pdf = render_etiquetas_pallet_pdf(pallets_ctx)
    resp = HttpResponse(pdf, content_type='application/pdf')
    resp['Content-Disposition'] = f'inline; filename="etiquetas-romaneio-{romaneio.numero}.pdf"'
    return resp


@login_required
def romaneio_etiquetas_caixa_pdf(request, pk):
    empresa = _get_empresa(request)
    romaneio = get_object_or_404(
        RomaneioVenda.objects.select_related(
            'cliente', 'booking__solicitacao__armador', 'booking__solicitacao__navio',
            'booking__porto_destino', 'booking__porto_origem', 'container',
        ),
        pk=pk, empresa=empresa,
    )
    pallets = [
        item.pallet for item in romaneio.itens
        .select_related(*[f'pallet__{f}' for f in _SELECT_RELATED_ETIQUETA])
        .prefetch_related(*[f'pallet__{f}' for f in _PREFETCH_RELATED_ETIQUETA])
        .order_by('pallet__codigo_pallet')
    ]
    from .pdf_caixa import render_etiquetas_caixa_pdf
    pallets_ctx = [{'pallet': p, 'romaneio': romaneio} for p in pallets]
    pdf = render_etiquetas_caixa_pdf(pallets_ctx)
    resp = HttpResponse(pdf, content_type='application/pdf')
    resp['Content-Disposition'] = f'inline; filename="etiquetas-caixa-romaneio-{romaneio.numero}.pdf"'
    return resp


@login_required
def romaneio_rastreabilidade_pdf(request, pk):
    """Relatório PPWR de rastreabilidade de embalagens (TP/SP) do romaneio."""
    from django.template.loader import render_to_string
    from xhtml2pdf import pisa

    empresa = _get_empresa(request)
    romaneio = get_object_or_404(
        RomaneioVenda.objects.select_related(
            'cliente', 'empresa', 'booking__solicitacao__armador', 'booking__solicitacao__navio',
            'booking__porto_destino', 'container',
        ),
        pk=pk, empresa=empresa,
    )
    if not romaneio.rastreabilidade_transporte:
        messages.error(request, 'Confirme o romaneio para gerar os códigos de rastreabilidade antes de emitir o relatório.')
        return redirect('embalagem:romaneio_detail', pk=pk)

    materiais_tp = romaneio.materiais_embalagem.select_related('material__produto__fornecedor_padrao').prefetch_related(
        'material__produto__fornecedores_relacionados__fornecedor'
    ).filter(material__tipo='TRANSPORTE').order_by('material__produto__nome')
    materiais_sp = romaneio.materiais_embalagem.select_related('material__produto__fornecedor_padrao').prefetch_related(
        'material__produto__fornecedores_relacionados__fornecedor'
    ).filter(material__tipo='VENDA').order_by('material__produto__nome')

    fornecedores = {}
    for item in list(materiais_tp) + list(materiais_sp):
        f = item.material.fornecedor
        if not f:
            continue
        fornecedores.setdefault(f.pk, {'fornecedor': f, 'materiais': []})
        fornecedores[f.pk]['materiais'].append(item.material.nome)

    tipo_ids = set()
    for item in romaneio.itens.select_related('pallet').prefetch_related('pallet__composicao__tipo_embalagem'):
        p = item.pallet
        if p.tipo_embalagem_id:
            tipo_ids.add(p.tipo_embalagem_id)
        else:
            tipo_ids.update(c.tipo_embalagem_id for c in p.composicao.all())
    tipos_embalagem = TipoEmbalagem.objects.filter(pk__in=tipo_ids).select_related('cultura')
    commodities = ', '.join(sorted({t.cultura.nome for t in tipos_embalagem if t.cultura_id}))
    variedades = ', '.join(sorted({t.variedade for t in tipos_embalagem if t.variedade}))

    html = render_to_string('embalagem/romaneio/rastreabilidade_pdf.html', {
        'romaneio': romaneio,
        'empresa': empresa,
        'materiais_tp': materiais_tp,
        'materiais_sp': materiais_sp,
        'fornecedores': fornecedores.values(),
        'commodities': commodities,
        'variedades': variedades,
    })
    buffer = io.BytesIO()
    pisa.CreatePDF(html, dest=buffer)
    buffer.seek(0)
    resp = HttpResponse(buffer.read(), content_type='application/pdf')
    resp['Content-Disposition'] = f'inline; filename="rastreabilidade-{romaneio.numero}.pdf"'
    return resp


# ─────────────────────────── CargaFrete ─────────────────────────────────────

@login_required
def carga_frete_list(request):
    empresa = _get_empresa(request)
    qs = CargaFrete.objects.filter(empresa=empresa, ativo=True).select_related('transportadora')
    page_obj, per_page, per_page_options = paginate(request, qs.order_by('-data_embarque'))
    return render(request, 'embalagem/carga_frete/list.html', {
        'page_obj': page_obj,
        'per_page': per_page,
        'per_page_options': per_page_options,
    })


@login_required
def carga_frete_create(request):
    empresa = _get_empresa(request)
    if request.method == 'POST':
        form = CargaFreteForm(request.POST, empresa=empresa)
        if form.is_valid():
            carga = form.save(commit=False)
            carga.empresa = empresa
            carga.criado_por = request.user
            carga.save()
            messages.success(request, 'Carga de frete criada.')
            return redirect('embalagem:carga_frete_detail', pk=carga.pk)
    else:
        form = CargaFreteForm(empresa=empresa)
    return render(request, 'embalagem/carga_frete/form.html', {
        'form': form, 'title': 'Nova Carga de Frete',
    })


@login_required
def carga_frete_update(request, pk):
    empresa = _get_empresa(request)
    carga = get_object_or_404(CargaFrete, pk=pk, empresa=empresa)
    if request.method == 'POST':
        form = CargaFreteForm(request.POST, instance=carga, empresa=empresa)
        if form.is_valid():
            form.save()
            messages.success(request, 'Carga de frete atualizada.')
            return redirect('embalagem:carga_frete_detail', pk=pk)
    else:
        form = CargaFreteForm(instance=carga, empresa=empresa)
    return render(request, 'embalagem/carga_frete/form.html', {
        'form': form, 'title': 'Editar Carga de Frete', 'obj': carga,
    })


@login_required
def carga_frete_detail(request, pk):
    empresa = _get_empresa(request)
    carga = get_object_or_404(CargaFrete, pk=pk, empresa=empresa)
    romaneios = carga.romaneios.select_related('cliente', 'pedido_venda').order_by('numero')
    soma_caixas = sum(r.total_caixas for r in romaneios)
    return render(request, 'embalagem/carga_frete/detail.html', {
        'carga': carga,
        'romaneios': romaneios,
        'soma_caixas': soma_caixas,
    })


@login_required
@require_POST
def carga_frete_ratear(request, pk):
    empresa = _get_empresa(request)
    carga = get_object_or_404(CargaFrete, pk=pk, empresa=empresa)
    try:
        carga.ratear()
        messages.success(request, 'Frete e pedágio rateados entre os romaneios vinculados.')
    except CargaFreteError as e:
        messages.error(request, str(e))
    return redirect('embalagem:carga_frete_detail', pk=pk)


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
    page_obj, per_page, per_page_options = paginate(request, qs.order_by('-criado_em'))
    return render(request, 'embalagem/romaneio/list.html', {
        'page_obj': page_obj,
        'status_choices': RomaneioVenda.STATUS,
        'tipo_choices': RomaneioVenda.TIPO,
        'filtros': {'q': q, 'status': status_f, 'tipo': tipo_f, 'data_ini': data_ini, 'data_fim': data_fim},
        'per_page': per_page,
        'per_page_options': per_page_options,
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
    itens = rom.itens.select_related('pallet__tipo_embalagem', 'pallet__armazem').prefetch_related(
        'pallet__composicao__tipo_embalagem',
    ).order_by('pallet__codigo_pallet')
    armazens = Armazem.objects.filter(empresa=empresa).order_by('nome')
    materiais_vinculados = rom.materiais_embalagem.select_related('material__produto__fornecedor_padrao').prefetch_related(
        'material__produto__fornecedores_relacionados__fornecedor'
    ).all()
    materiais_disponiveis = MaterialEmbalagem.objects.filter(empresa=empresa, ativo=True).select_related(
        'produto'
    ).exclude(
        pk__in=materiais_vinculados.values_list('material_id', flat=True)
    ).order_by('tipo', 'produto__nome')
    return render(request, 'embalagem/romaneio/detail.html', {
        'romaneio': rom,
        'itens': itens,
        'armazens': armazens,
        'materiais_tp': materiais_vinculados.filter(material__tipo='TRANSPORTE'),
        'materiais_sp': materiais_vinculados.filter(material__tipo='VENDA'),
        'materiais_disponiveis': materiais_disponiveis,
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
        update_fields = ['status']
        if not rom.rastreabilidade_transporte:
            rom.rastreabilidade_transporte, rom.rastreabilidade_venda = RomaneioVenda._gerar_rastreabilidade(empresa)
            update_fields += ['rastreabilidade_transporte', 'rastreabilidade_venda']
        rom.save(update_fields=update_fields)
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

    from vendas.models import PedidoVenda, ItemPedidoVenda, TabelaPreco
    from produtos.tributacao import resolver_tributacao_venda

    avisos = []

    tipo_venda = 'EXPORTACAO' if rom.tipo == 'EXPORTACAO' else 'MERCADO_INTERNO'
    moeda_padrao_cliente = (rom.cliente.moeda_padrao or '').strip().upper()
    moedas_validas = dict(PedidoVenda.MOEDA_CHOICES)
    if moeda_padrao_cliente in moedas_validas:
        moeda = moeda_padrao_cliente
    else:
        moeda = 'USD' if rom.tipo == 'EXPORTACAO' else 'BRL'

    # Condição/forma de pagamento padrão do cliente — mesma regra usada em
    # cadastros.views.ajax_dados_cliente para pré-preencher o form manual.
    if rom.cliente.prazo_pagamento_padrao_id:
        condicao_pagamento = f"{rom.cliente.prazo_pagamento_padrao.termos} dias"
    elif rom.cliente.prazo_pagamento:
        condicao_pagamento = f"{rom.cliente.prazo_pagamento} dias"
    else:
        condicao_pagamento = ''
    forma_pagamento = (
        rom.cliente.get_forma_pagamento_padrao_display() if rom.cliente.forma_pagamento_padrao else ''
    )
    vendedor = rom.cliente.vendedor_responsavel

    # Cotação PTAX do BCB é buscada fora da transação (chamada de rede) —
    # mesma fonte usada pelo botão "Buscar Cotação BCB" do formulário manual.
    taxa_cambio = None
    if moeda != 'BRL':
        from faturamento.bcb import buscar_cotacoes
        try:
            resultado_bcb = buscar_cotacoes(moedas=[moeda])
            cotacao = resultado_bcb['cotacoes'].get(moeda)
            if cotacao:
                taxa_cambio = cotacao['venda']
        except Exception:
            pass
        if taxa_cambio is None:
            avisos.append(
                f'Não foi possível obter a cotação BCB para {moeda} automaticamente — '
                'informe a taxa de câmbio manualmente ao editar o pedido.'
            )

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

        pedido = PedidoVenda.objects.create(
            empresa=empresa,
            numero=numero_pv,
            cliente=rom.cliente,
            data_pedido=rom.data,
            status='RASCUNHO',
            tipo_venda=tipo_venda,
            moeda=moeda,
            taxa_cambio=taxa_cambio,
            condicao_pagamento=condicao_pagamento,
            forma_pagamento=forma_pagamento,
            vendedor=vendedor,
            criado_por=request.user,
        )

        hoje = timezone.now().date()
        for te, totais in _agrupar_itens_por_tipo(rom).items():
            resultado = resolver_tributacao_venda(te.produto, empresa, rom.cliente, tipo_venda)
            if resultado.ok:
                ncm, cfop, tributacao = resultado.ncm_codigo, resultado.cfop_codigo, resultado.tributacao
            else:
                ncm, cfop, tributacao = '', '', None
                avisos.append(resultado.mensagem)

            preco_unitario = Decimal('0')
            tabelas_vigentes = TabelaPreco.objects.filter(
                empresa=empresa, produto=te.produto, moeda=moeda, ativo=True,
                vigencia_inicio__lte=hoje,
            ).filter(Q(vigencia_fim__isnull=True) | Q(vigencia_fim__gte=hoje))
            tabela = (
                tabelas_vigentes.filter(cliente=rom.cliente).first()
                or tabelas_vigentes.filter(cliente__isnull=True).first()
            )
            if tabela:
                preco_unitario = tabela.preco_unitario
            else:
                avisos.append(
                    f'Sem tabela de preço vigente para "{te.produto.nome}" em {moeda} — preço zerado.'
                )

            ItemPedidoVenda.objects.create(
                pedido=pedido,
                produto=te.produto,
                descricao=te.nome,
                ncm=ncm,
                cfop=cfop,
                tributacao=tributacao,
                unidade='CX',
                quantidade=totais['caixas'],
                preco_unitario=preco_unitario,
            )

        pedido.calcular_total()
        pedido.save(update_fields=['valor_produtos', 'valor_total'])
        rom.pedido_venda = pedido
        rom.save(update_fields=['pedido_venda'])

    for aviso in avisos:
        messages.warning(request, aviso)
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


@login_required
@require_POST
def romaneio_adicionar_material(request, pk):
    empresa = _get_empresa(request)
    rom = get_object_or_404(RomaneioVenda, pk=pk, empresa=empresa)
    if rom.status in ('CONCLUIDO', 'CANCELADO'):
        messages.error(request, 'Romaneio concluído/cancelado não pode ter materiais alterados.')
        return redirect('embalagem:romaneio_detail', pk=pk)
    material = get_object_or_404(MaterialEmbalagem, pk=request.POST.get('material'), empresa=empresa, ativo=True)
    RomaneioMaterialEmbalagem.objects.get_or_create(romaneio=rom, material=material)
    messages.success(request, 'Material de embalagem adicionado ao romaneio.')
    return redirect('embalagem:romaneio_detail', pk=pk)


@login_required
@require_POST
def romaneio_remover_material(request, pk, item_pk):
    empresa = _get_empresa(request)
    rom = get_object_or_404(RomaneioVenda, pk=pk, empresa=empresa)
    if rom.status in ('CONCLUIDO', 'CANCELADO'):
        messages.error(request, 'Romaneio concluído/cancelado não pode ter materiais alterados.')
        return redirect('embalagem:romaneio_detail', pk=pk)
    item = get_object_or_404(RomaneioMaterialEmbalagem, pk=item_pk, romaneio=rom)
    item.delete()
    messages.success(request, 'Material de embalagem removido do romaneio.')
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


def _rastreabilidade_por_tipo(rom):
    """Para cada TipoEmbalagem do romaneio, retorna o LoteProducao mais antigo
    entre os pallets que o compõem — usado para popular fazenda/variedade/GGN/
    datas de colheita no Packing List (RF-110). Se um tipo agregar pallets de
    mais de um LoteProducao, usa o mais antigo e ignora os demais (não bloqueia
    a geração do documento).
    """
    from collections import defaultdict
    lotes_por_tipo = defaultdict(list)
    itens_qs = rom.itens.select_related(
        'pallet__tipo_embalagem',
        'pallet__ordem_embalagem__lote_producao__talhao__fazenda',
        'pallet__ordem_embalagem__lote_producao__cultura',
    ).prefetch_related('pallet__composicao__tipo_embalagem')
    for item in itens_qs:
        pallet = item.pallet
        lote_producao = pallet.ordem_embalagem.lote_producao
        if not lote_producao:
            continue
        if pallet.is_misto:
            for comp in pallet.composicao.all():
                lotes_por_tipo[comp.tipo_embalagem].append(lote_producao)
        else:
            lotes_por_tipo[pallet.tipo_embalagem].append(lote_producao)

    resultado = {}
    for te, lotes in lotes_por_tipo.items():
        lotes_ordenados = sorted(lotes, key=lambda l: l.data_colheita_inicio or timezone.now().date())
        resultado[te] = lotes_ordenados[0]
    return resultado


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
    if rom.pedido_venda_id and rom.pedido_venda.invoice_id:
        # O Pedido de Venda vinculado já foi faturado pelo fluxo vendas-primeiro —
        # reaproveita essa Invoice em vez de gerar uma segunda para a mesma carga.
        rom.invoice_exportacao = rom.pedido_venda.invoice
        rom.save(update_fields=['invoice_exportacao'])
        messages.info(request, f'Pedido {rom.pedido_venda.numero} já possui Invoice {rom.pedido_venda.invoice.numero} — reaproveitada.')
        return redirect('faturamento:invoice_detail', pk=rom.pedido_venda.invoice_id)
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
        conta_bancaria = empresa.contas_bancarias_empresa.filter(
            ativa=True, conta_principal=True,
        ).first()
        dados_bancarios = {}
        if conta_bancaria and (conta_bancaria.iban or conta_bancaria.swift_bic):
            dados_bancarios = {
                'banco_nome': conta_bancaria.banco,
                'banco_endereco': conta_bancaria.endereco_banco,
                'banco_swift': conta_bancaria.swift_bic,
                'banco_iban': conta_bancaria.iban,
                'banco_numero_conta': conta_bancaria.numero_formatado,
                'banco_beneficiario_nome': conta_bancaria.beneficiario_nome,
            }
            # moeda não é definida explicitamente abaixo, então a Invoice nasce
            # com o default do model (USD) — usamos a mesma moeda aqui.
            correspondente = conta_bancaria.correspondente_para_moeda('USD')
            if correspondente:
                dados_bancarios['banco_correspondente_nome'] = correspondente.nome
                dados_bancarios['banco_correspondente_swift'] = correspondente.swift_bic
        invoice = InvoiceExportacao.objects.create(
            empresa=empresa,
            booking=booking,
            cliente=rom.cliente,
            data_emissao=timezone.now().date(),
            data_embarque_previsto=data_embarque,
            porto_embarque=porto_embarque,
            porto_destino=porto_destino,
            **dados_bancarios,
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
        rastreabilidade = _rastreabilidade_por_tipo(rom)
        for i, (te, totais) in enumerate(grupos.items(), start=1):
            lote_producao = rastreabilidade.get(te)
            farm_nome = ''
            variedade = ''
            data_colheita_inicio = None
            data_colheita_fim = None
            ggn_numero = ''
            if lote_producao:
                if lote_producao.talhao and lote_producao.talhao.fazenda:
                    farm_nome = lote_producao.talhao.fazenda.nome
                    ggn_numero = lote_producao.talhao.fazenda.ggn_numero
                if lote_producao.cultura:
                    variedade = lote_producao.cultura.variedade or lote_producao.cultura.nome
                data_colheita_inicio = lote_producao.data_colheita_inicio
                data_colheita_fim = lote_producao.data_colheita_fim
            ItemPackingList.objects.create(
                packing_list=pl,
                container=rom.container,
                numero_container=nr_container,
                descricao_produto=te.descricao_completa,
                quantidade_caixas=totais['caixas'],
                quantidade_pallets=totais['pallets'] or None,
                peso_bruto_kg=totais['peso_bruto'],
                peso_liquido_kg=totais['peso_liquido'],
                farm_nome=farm_nome,
                variedade=variedade,
                data_colheita_inicio=data_colheita_inicio,
                data_colheita_fim=data_colheita_fim,
                ggn_numero=ggn_numero,
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
    if rom.pedido_venda_id and rom.pedido_venda.nota_fiscal_id:
        # O Pedido de Venda vinculado já foi faturado pelo fluxo vendas-primeiro —
        # reaproveita essa NF-e em vez de gerar uma segunda para a mesma carga.
        rom.nota_fiscal = rom.pedido_venda.nota_fiscal
        rom.save(update_fields=['nota_fiscal'])
        messages.info(request, f'Pedido {rom.pedido_venda.numero} já possui NF-e {rom.pedido_venda.nota_fiscal.numero} — reaproveitada.')
        return redirect('faturamento:nota_fiscal_detail', pk=rom.pedido_venda.nota_fiscal_id)
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


@login_required
def romaneio_gerar_cte(request, pk):
    empresa = _get_empresa(request)
    rom = get_object_or_404(RomaneioVenda, pk=pk, empresa=empresa)
    if rom.tipo != 'MERCADO_INTERNO':
        messages.error(request, 'Esta ação é apenas para romaneios de Mercado Interno.')
        return redirect('embalagem:romaneio_detail', pk=pk)
    if not rom.carga_frete_id or rom.valor_frete_rateado is None:
        messages.error(request, 'Rateie o frete da carga antes de gerar o CT-e.')
        return redirect('embalagem:romaneio_detail', pk=pk)
    return redirect(f"{reverse('faturamento:cte_create')}?romaneio_venda={rom.pk}")


# ─────────────────────────── Conferência ────────────────────────────────────

@login_required
def romaneio_conferencia_pdf(request, pk):
    """Relatório de carregamento (para assinatura na doca)."""
    empresa = _get_empresa(request)
    rom = get_object_or_404(
        RomaneioVenda.objects.select_related(
            'cliente', 'booking__solicitacao__armador', 'booking__solicitacao__navio',
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
    ).select_related('tipo_embalagem', 'armazem').order_by('codigo_pallet')

    tipo_id = request.GET.get('tipo_embalagem')
    armazem_id = request.GET.get('armazem')
    q = request.GET.get('q', '')

    if tipo_id:
        qs = qs.filter(tipo_embalagem_id=tipo_id)
    if armazem_id:
        qs = qs.filter(armazem_id=armazem_id)
    if q:
        qs = qs.filter(codigo_pallet__icontains=q)

    page = int(request.GET.get('page') or 1)
    page_size = 20
    start = (page - 1) * page_size
    pallets = list(qs[start:start + page_size + 1])
    has_more = len(pallets) > page_size
    pallets = pallets[:page_size]

    results = [{
        'id': p.pk,
        'text': (
            f"{p.codigo_pallet} — {p.tipo_embalagem.nome if p.tipo_embalagem else 'Misto'} — "
            f"{p.quantidade_caixas} cx — {p.peso_liquido_kg:.3f} kg — {p.armazem.nome}"
        ),
        'codigo_pallet': p.codigo_pallet,
        'tipo_embalagem': p.tipo_embalagem.nome if p.tipo_embalagem else 'Misto',
        'quantidade_caixas': p.quantidade_caixas,
        'peso_bruto_kg': float(p.peso_bruto_kg),
        'peso_liquido_kg': float(p.peso_liquido_kg),
        'armazem': p.armazem.nome,
        'data_embalagem': p.data_embalagem.strftime('%d/%m/%Y'),
    } for p in pallets]

    return JsonResponse({'results': results, 'pagination': {'more': has_more}})


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
    """Cria um pallet misto vazio. Chamado via AJAX pelo modal em ordem_detail —
    a composição é montada ali mesmo, sem navegar para outra página."""
    empresa = _get_empresa(request)
    ordem = get_object_or_404(OrdemEmbalagem, pk=ordem_pk, empresa=empresa)

    if ordem.status == 'CANCELADA':
        return JsonResponse({'erro': 'Ordem cancelada não pode receber pallets.'}, status=400)

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

    return JsonResponse({'ok': True, 'pallet_pk': pallet.pk, 'codigo_pallet': pallet.codigo_pallet})


@login_required
def pallet_misto_detail(request, pk):
    empresa = _get_empresa(request)
    pallet = get_object_or_404(PalletEmbalado, pk=pk, empresa=empresa, is_misto=True)
    itens = pallet.composicao.select_related('tipo_embalagem__cultura', 'tipo_embalagem__produto').all()
    capacidade = pallet.ordem_embalagem.capacidade_caixas_pallet
    return render(request, 'embalagem/pallet/detalhe_misto.html', {
        'pallet': pallet,
        'itens': itens,
        'form': ItemPalletForm(ordem=pallet.ordem_embalagem),
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
    if pallet.estoque_baixado:
        return JsonResponse({'erro': 'Pallet já finalizado — a composição não pode mais ser alterada.'}, status=400)

    form = ItemPalletForm(request.POST, ordem=pallet.ordem_embalagem)
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
    if pallet.estoque_baixado:
        return JsonResponse({'erro': 'Pallet já finalizado — a composição não pode mais ser alterada.'}, status=400)
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


@login_required
@require_POST
def pallet_misto_finalizar(request, pk):
    """Confirma a composição do pallet misto: baixa o granel de origem (proporcional
    ao peso de cada item) e dá entrada no estoque do produto acabado de cada tipo usado.
    Só é feita uma vez — depois disso a composição fica travada."""
    empresa = _get_empresa(request)
    pallet = get_object_or_404(PalletEmbalado, pk=pk, empresa=empresa, is_misto=True)
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

    if pallet.estoque_baixado:
        if is_ajax:
            return JsonResponse({'erro': 'Este pallet já foi finalizado.'}, status=400)
        messages.warning(request, 'Este pallet já foi finalizado.')
        return redirect('embalagem:pallet_misto_detail', pk=pk)

    itens = list(pallet.composicao.select_related('tipo_embalagem__produto').all())
    if not itens:
        if is_ajax:
            return JsonResponse({'erro': 'Adicione ao menos um item à composição antes de finalizar.'}, status=400)
        messages.error(request, 'Adicione ao menos um item à composição antes de finalizar.')
        return redirect('embalagem:pallet_misto_detail', pk=pk)

    ordem = pallet.ordem_embalagem
    from django.core.exceptions import ValidationError
    from estoque.services import criar_movimentacao
    try:
        with transaction.atomic():
            for item in itens:
                te = item.tipo_embalagem
                if not te.produto_id:
                    raise ValidationError(f'Tipo de embalagem "{te.nome}" não tem produto configurado.')

                criar_movimentacao(
                    empresa=empresa,
                    tipo='SAIDA',
                    origem='PEDIDO_VENDA',
                    quantidade=item.peso_liquido_kg,
                    usuario=request.user,
                    lote=ordem.lote_origem,
                    documento=pallet.codigo_pallet,
                    observacao=f'Baixa por pallet misto {pallet.codigo_pallet} — {item.quantidade_caixas}cx de {te.nome}.',
                )

                lote_embalado = Lote.objects.create(
                    empresa=empresa,
                    produto=te.produto,
                    armazem=pallet.armazem,
                    local_estocagem=pallet.local_estocagem,
                    numero_lote=f"EMB-{pallet.codigo_pallet}-{te.pk}-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                    data_fabricacao=pallet.data_embalagem,
                    quantidade_inicial=item.quantidade_caixas,
                    quantidade_atual=item.quantidade_caixas,
                    unidade_medida=te.produto.unidade_venda,
                    status='DISPONIVEL',
                    observacoes=f'Produto acabado — pallet misto {pallet.codigo_pallet}.',
                    cadastrado_por=request.user,
                )
                MovimentacaoEstoque.objects.create(
                    empresa=empresa,
                    produto=te.produto,
                    lote=lote_embalado,
                    tipo='ENTRADA',
                    origem='PRODUCAO',
                    quantidade=item.quantidade_caixas,
                    documento=pallet.codigo_pallet,
                    observacao=f'Embalagem — pallet misto {pallet.codigo_pallet}: {item.quantidade_caixas}cx de {te.nome}.',
                    status='EXECUTADO',
                    cadastrado_por=request.user,
                    executado_por=request.user,
                    data_execucao=timezone.now(),
                )

            pallet.estoque_baixado = True
            pallet.save(update_fields=['estoque_baixado'])
    except ValidationError as exc:
        erro_msg = f'Saldo insuficiente no lote de origem: {"; ".join(exc.messages)}'
        if is_ajax:
            return JsonResponse({'erro': erro_msg}, status=400)
        messages.error(request, erro_msg)
        return redirect('embalagem:pallet_misto_detail', pk=pk)

    if is_ajax:
        return JsonResponse({'ok': True, 'redirect_url': reverse('embalagem:ordem_detail', args=[ordem.pk])})
    messages.success(request, f'Pallet misto {pallet.codigo_pallet} finalizado — estoque atualizado.')
    return redirect('embalagem:ordem_detail', pk=ordem.pk)
