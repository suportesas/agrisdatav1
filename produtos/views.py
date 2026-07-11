from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
import json
from decimal import Decimal
# ============== PRODUTO FORNECEDOR ==============
@login_required
def produto_fornecedor_json(request, pk):
    """Retorna dados do fornecedor relacionado ao produto em JSON"""
    try:
        pf = get_object_or_404(ProdutoFornecedor, pk=pk)
        if pf.produto.categoria.empresa != request.user.empresa:
            return JsonResponse({'success': False, 'error': 'Não autorizado'}, status=403)
        return JsonResponse({
            'success': True,
            'fornecedor_id': pf.fornecedor_id,
            'codigo_fornecedor': pf.codigo_fornecedor,
            'preco_compra': float(pf.preco_compra) if pf.preco_compra else 0,
            'prazo_entrega': pf.prazo_entrega,
            'quantidade_minima': float(pf.quantidade_minima) if pf.quantidade_minima else 0,
            'fornecedor_preferencial': pf.fornecedor_preferencial,
            'observacoes': pf.observacoes or ''
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
@require_POST
def produto_fornecedor_editar(request, pk):
    """Edita dados do fornecedor relacionado ao produto via AJAX"""
    try:
        pf = get_object_or_404(ProdutoFornecedor, pk=pk)
        if pf.produto.categoria.empresa != request.user.empresa:
            return JsonResponse({'success': False, 'error': 'Não autorizado'}, status=403)
        data = json.loads(request.body)
        pf.fornecedor_id = data.get('fornecedor_id')
        pf.codigo_fornecedor = data.get('codigo_fornecedor', '').strip()
        pf.preco_compra = Decimal(data.get('preco_compra', 0))
        pf.prazo_entrega = data.get('prazo_entrega') or None
        pf.quantidade_minima = Decimal(data.get('quantidade_minima', 0))
        pf.fornecedor_preferencial = data.get('fornecedor_preferencial', False)
        pf.observacoes = data.get('observacoes', '')
        pf.save()
        return JsonResponse({'success': True, 'message': 'Fornecedor editado com sucesso!'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

@login_required
def categoria_seed(request):
    empresa = request.user.empresa
    from produtos.categoria_seed import seed_categorias_for_empresa
    criados, ignorados = seed_categorias_for_empresa(empresa)
    messages.success(request, f'Categorias padrão populadas! Criadas: {criados}, já existentes: {ignorados}')
    return redirect('produtos:categoria_list')
from django.db.models import Q, Count, Sum, F
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.urls import reverse
import json
from decimal import Decimal
from .models import Marca, UnidadeMedida, Categoria, SubCategoria, Produto, ProdutoTributacao, NaturezaOperacao, ProdutoDefensivoCultura, ProdutoFornecedor, TipoProduto, DimensaoVariante, ProdutoAtributo
from .forms import MarcaForm, UnidadeMedidaForm, CategoriaForm, SubCategoriaForm, ProdutoForm, ProdutoTributacaoForm, NaturezaOperacaoForm, ProdutoDefensivoCulturaForm
from cadastros.models import NCM, CFOP, Fornecedor
from emprestimos.models import EmprestimoProdutor


# ============== MARCA ==============

@login_required
def marca_list(request):
    query = request.GET.get('q', '')
    marcas = Marca.objects.filter(empresa=request.user.empresa)
    if query:
        marcas = marcas.filter(nome__icontains=query)
    return render(request, 'produtos/marca/marca_list.html', {
        'marcas': marcas.order_by('nome'),
        'query': query
    })


@login_required
def marca_create(request):
    if request.method == 'POST':
        form = MarcaForm(request.POST)
        if form.is_valid():
            marca = form.save(commit=False)
            marca.empresa = request.user.empresa
            marca.save()
            messages.success(request, 'Marca cadastrada com sucesso!')
            return redirect('produtos:marca_list')
    else:
        form = MarcaForm()
    return render(request, 'produtos/marca/marca_form.html', {
        'form': form,
        'action': 'Cadastrar'
    })


@login_required
def marca_update(request, pk):
    marca = get_object_or_404(Marca.objects.filter(empresa=request.user.empresa), pk=pk)
    if request.method == 'POST':
        form = MarcaForm(request.POST, instance=marca)
        if form.is_valid():
            form.save()
            messages.success(request, 'Marca atualizada com sucesso!')
            return redirect('produtos:marca_list')
    else:
        form = MarcaForm(instance=marca)
    return render(request, 'produtos/marca/marca_form.html', {
        'form': form,
        'action': 'Editar'
    })


@login_required
@require_POST
def marca_toggle_ativo(request, pk):
    marca = get_object_or_404(Marca.objects.filter(empresa=request.user.empresa), pk=pk)
    marca.ativo = not marca.ativo
    marca.save(update_fields=['ativo'])
    messages.success(request, f'Marca {"ativada" if marca.ativo else "desativada"}.')
    return redirect('produtos:marca_list')


# ============== DASHBOARD ==============

@login_required
def dashboard(request):
    """Dashboard do módulo Produtos"""
    empresa = request.user.empresa
    
    # Estatísticas gerais - Filtrar por categoria__empresa
    total_produtos = Produto.objects.filter(categoria__empresa=empresa, ativo=True).count()
    total_categorias = Categoria.objects.filter(empresa=empresa).count()
    total_subcategorias = SubCategoria.objects.filter(categoria__empresa=empresa).count()
    produtos_sem_tributacao = Produto.objects.filter(
        categoria__empresa=empresa, 
        ativo=True
    ).exclude(
        tributacoes__isnull=False
    ).count()
    
    # Produtos por categoria (top 5)
    produtos_por_categoria = Categoria.objects.filter(
        empresa=empresa
    ).annotate(
        total_produtos=Count('produto')
    ).order_by('-total_produtos')[:5]
    
    # Últimos produtos cadastrados
    ultimos_produtos = Produto.objects.filter(
        categoria__empresa=empresa
    ).select_related('categoria', 'subcategoria').order_by('-created_at')[:5]
    
    # Produtos sem categoria
    produtos_sem_categoria = Produto.objects.filter(
        categoria__isnull=True,
        ativo=True
    ).count()
    
    # Produtos inativos
    produtos_inativos = Produto.objects.filter(categoria__empresa=empresa, ativo=False).count()
    
    context = {
        'total_produtos': total_produtos,
        'total_categorias': total_categorias,
        'total_subcategorias': total_subcategorias,
        'produtos_sem_tributacao': produtos_sem_tributacao,
        'produtos_por_categoria': produtos_por_categoria,
        'ultimos_produtos': ultimos_produtos,
        'produtos_sem_categoria': produtos_sem_categoria,
        'produtos_inativos': produtos_inativos,
    }
    return render(request, 'produtos/dashboard.html', context)


# ============== UNIDADE DE MEDIDA ==============

@login_required
def unidademedida_list(request):
    query = request.GET.get('q', '')
    unidades = UnidadeMedida.objects.filter(empresa=request.user.empresa)
    if query:
        unidades = unidades.filter(
            Q(sigla__icontains=query) |
            Q(nome__icontains=query)
        )
    return render(request, 'produtos/unidademedida/unidademedida_list.html', {
        'unidades': unidades,
        'query': query
    })


@login_required
def unidademedida_create(request):
    if request.method == 'POST':
        form = UnidadeMedidaForm(request.POST)
        if form.is_valid():
            unidade = form.save(commit=False)
            unidade.empresa = request.user.empresa
            unidade.save()
            messages.success(request, 'Unidade de medida cadastrada com sucesso!')
            return redirect('produtos:unidademedida_list')
    else:
        form = UnidadeMedidaForm()
    return render(request, 'produtos/unidademedida/unidademedida_form.html', {
        'form': form,
        'action': 'Cadastrar'
    })


@login_required
def unidademedida_update(request, pk):
    unidade = get_object_or_404(UnidadeMedida.objects.filter(empresa=request.user.empresa), pk=pk)
    if request.method == 'POST':
        form = UnidadeMedidaForm(request.POST, instance=unidade)
        if form.is_valid():
            form.save()
            messages.success(request, 'Unidade de medida atualizada com sucesso!')
            return redirect('produtos:unidademedida_list')
    else:
        form = UnidadeMedidaForm(instance=unidade)
    return render(request, 'produtos/unidademedida/unidademedida_form.html', {
        'form': form,
        'action': 'Editar'
    })


@login_required
def unidademedida_delete(request, pk):
    unidade = get_object_or_404(UnidadeMedida.objects.filter(empresa=request.user.empresa), pk=pk)
    if request.method == 'POST':
        unidade.delete()
        messages.success(request, 'Unidade de medida excluída com sucesso!')
        return redirect('produtos:unidademedida_list')
    return render(request, 'produtos/unidademedida/unidademedida_confirm_delete.html', {
        'object': unidade
    })


# ============== NATUREZA DA OPERAÇÃO ==============

@login_required
def naturezaoperacao_list(request):
    query = request.GET.get('q', '')
    naturezas = NaturezaOperacao.objects.filter(empresa=request.user.empresa)
    if query:
        naturezas = naturezas.filter(
            Q(codigo__icontains=query) |
            Q(descricao__icontains=query)
        )
    return render(request, 'produtos/naturezaoperacao/naturezaoperacao_list.html', {
        'naturezas': naturezas,
        'query': query
    })


@login_required
def naturezaoperacao_create(request):
    if request.method == 'POST':
        form = NaturezaOperacaoForm(request.POST)
        if form.is_valid():
            natureza = form.save(commit=False)
            natureza.empresa = request.user.empresa
            natureza.save()
            messages.success(request, 'Natureza da Operação cadastrada com sucesso!')
            return redirect('produtos:naturezaoperacao_list')
    else:
        form = NaturezaOperacaoForm()
    return render(request, 'produtos/naturezaoperacao/naturezaoperacao_form.html', {
        'form': form,
        'action': 'Cadastrar'
    })


@login_required
def naturezaoperacao_update(request, pk):
    natureza = get_object_or_404(NaturezaOperacao.objects.filter(empresa=request.user.empresa), pk=pk)
    if request.method == 'POST':
        form = NaturezaOperacaoForm(request.POST, instance=natureza)
        if form.is_valid():
            form.save()
            messages.success(request, 'Natureza da Operação atualizada com sucesso!')
            return redirect('produtos:naturezaoperacao_list')
    else:
        form = NaturezaOperacaoForm(instance=natureza)
    return render(request, 'produtos/naturezaoperacao/naturezaoperacao_form.html', {
        'form': form,
        'action': 'Editar'
    })


@login_required
def naturezaoperacao_delete(request, pk):
    natureza = get_object_or_404(NaturezaOperacao.objects.filter(empresa=request.user.empresa), pk=pk)
    if request.method == 'POST':
        natureza.delete()
        messages.success(request, 'Natureza da Operação excluída com sucesso!')
        return redirect('produtos:naturezaoperacao_list')
    return render(request, 'produtos/naturezaoperacao/naturezaoperacao_confirm_delete.html', {
        'object': natureza
    })


# ============== CATEGORIA ==============

@login_required
def categoria_list(request):
    query = request.GET.get('q', '')
    categorias = Categoria.objects.filter(empresa=request.user.empresa)
    if query:
        categorias = categorias.filter(
            Q(codigo__icontains=query) |
            Q(nome__icontains=query)
        )
    return render(request, 'produtos/categoria/categoria_list.html', {
        'categorias': categorias,
        'query': query
    })


@login_required
def categoria_create(request):
    if request.method == 'POST':
        form = CategoriaForm(request.POST)
        if form.is_valid():
            categoria = form.save(commit=False)
            categoria.empresa = request.user.empresa
            categoria.save()
            messages.success(request, 'Categoria cadastrada com sucesso!')
            return redirect('produtos:categoria_list')
    else:
        form = CategoriaForm()
    return render(request, 'produtos/categoria/categoria_form.html', {
        'form': form,
        'action': 'Cadastrar'
    })


@login_required
def categoria_update(request, pk):
    categoria = get_object_or_404(Categoria.objects.filter(empresa=request.user.empresa), pk=pk)
    if request.method == 'POST':
        form = CategoriaForm(request.POST, instance=categoria)
        if form.is_valid():
            form.save()
            messages.success(request, 'Categoria atualizada com sucesso!')
            return redirect('produtos:categoria_list')
    else:
        form = CategoriaForm(instance=categoria)
    return render(request, 'produtos/categoria/categoria_form.html', {
        'form': form,
        'action': 'Editar'
    })


@login_required
def categoria_delete(request, pk):
    categoria = get_object_or_404(Categoria.objects.filter(empresa=request.user.empresa), pk=pk)
    if request.method == 'POST':
        categoria.delete()
        messages.success(request, 'Categoria excluída com sucesso!')
        return redirect('produtos:categoria_list')
    return render(request, 'produtos/categoria/categoria_confirm_delete.html', {
        'object': categoria
    })


# ============== SUBCATEGORIA ==============

@login_required
def subcategoria_list(request):
    query = request.GET.get('q', '')
    subcategorias = SubCategoria.objects.select_related('categoria').filter(categoria__empresa=request.user.empresa)
    if query:
        subcategorias = subcategorias.filter(
            Q(codigo__icontains=query) |
            Q(nome__icontains=query) |
            Q(categoria__nome__icontains=query)
        )
    return render(request, 'produtos/subcategoria/subcategoria_list.html', {
        'subcategorias': subcategorias,
        'query': query
    })


@login_required
def subcategoria_create(request):
    if request.method == 'POST':
        form = SubCategoriaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Subcategoria cadastrada com sucesso!')
            return redirect('produtos:subcategoria_list')
    else:
        form = SubCategoriaForm()
    return render(request, 'produtos/subcategoria/subcategoria_form.html', {
        'form': form,
        'action': 'Cadastrar'
    })


@login_required
def subcategoria_update(request, pk):
    subcategoria = get_object_or_404(SubCategoria.objects.filter(categoria__empresa=request.user.empresa), pk=pk)
    if request.method == 'POST':
        form = SubCategoriaForm(request.POST, instance=subcategoria)
        if form.is_valid():
            form.save()
            messages.success(request, 'Subcategoria atualizada com sucesso!')
            return redirect('produtos:subcategoria_list')
    else:
        form = SubCategoriaForm(instance=subcategoria)
    return render(request, 'produtos/subcategoria/subcategoria_form.html', {
        'form': form,
        'action': 'Editar'
    })


@login_required
def subcategoria_delete(request, pk):
    subcategoria = get_object_or_404(SubCategoria.objects.filter(categoria__empresa=request.user.empresa), pk=pk)
    if request.method == 'POST':
        subcategoria.delete()
        messages.success(request, 'Subcategoria excluída com sucesso!')
        return redirect('produtos:subcategoria_list')
    return render(request, 'produtos/subcategoria/subcategoria_confirm_delete.html', {
        'object': subcategoria
    })


# ============== PRODUTO ==============

@login_required
def produto_list(request):
    query = request.GET.get('q', '')
    categoria_filter = request.GET.get('categoria', '')
    tipo_filter = request.GET.get('tipo', '')
    status_filter = request.GET.get('status', 'ativo')
    sort_by = request.GET.get('sort', 'nome')
    # Padrão: ocultar variantes (exibe apenas bases e produtos simples)
    mostrar_variantes = request.GET.get('variantes', '') == '1'

    empresa = request.user.empresa
    qs_base = Produto.objects.select_related(
        'categoria', 'unidade_medida', 'ncm', 'tipo_produto', 'produto_base'
    ).filter(categoria__empresa=empresa)

    # KPIs (calculados antes dos filtros)
    total_cadastros = qs_base.count()
    total_ativos = qs_base.filter(ativo=True).count()
    total_inativos = qs_base.filter(ativo=False).count()
    total_estoque_baixo = qs_base.filter(
        ativo=True, controla_estoque=True, estoque_atual__lte=F('estoque_minimo')
    ).exclude(estoque_minimo=0).count()

    produtos = qs_base

    if query:
        produtos = produtos.filter(
            Q(codigo__icontains=query) |
            Q(nome__icontains=query) |
            Q(codigo_barras__icontains=query) |
            Q(categoria__nome__icontains=query)
        )
    if categoria_filter:
        produtos = produtos.filter(categoria_id=categoria_filter)
    if tipo_filter:
        produtos = produtos.filter(tipo_produto_id=tipo_filter)
    if status_filter == 'ativo':
        produtos = produtos.filter(ativo=True)
    elif status_filter == 'inativo':
        produtos = produtos.filter(ativo=False)

    # Ocultar variantes por padrão (produtos com produto_base preenchido)
    if not mostrar_variantes:
        produtos = produtos.filter(produto_base__isnull=True)

    sort_map = {
        'nome': 'nome', '-nome': '-nome',
        'codigo': 'codigo', '-codigo': '-codigo',
        'preco': 'preco_venda', '-preco': '-preco_venda',
        'estoque': 'estoque_atual', '-estoque': '-estoque_atual',
    }
    produtos = produtos.order_by(sort_map.get(sort_by, 'nome'))

    categorias = Categoria.objects.filter(empresa=empresa).order_by('nome')
    tipos_produto = TipoProduto.objects.filter(empresa=empresa).order_by('nome')

    try:
        per_page = int(request.GET.get('per_page', 25))
    except (TypeError, ValueError):
        per_page = 25
    if per_page not in (10, 25, 50, 100):
        per_page = 25

    paginator = Paginator(produtos, per_page)
    page_obj = paginator.get_page(request.GET.get('page'))

    produto_ids = [p.id for p in page_obj.object_list]

    # Anotar contagem de variantes nos produtos da página atual
    from django.db.models import Count as DjangoCount
    variantes_qs = (
        Produto.objects.filter(produto_base_id__in=produto_ids)
        .values('produto_base_id')
        .annotate(total=DjangoCount('id'), estoque_soma=Sum('estoque_atual'))
    )
    variantes_counts = {}
    variantes_estoque = {}
    for row in variantes_qs:
        variantes_counts[row['produto_base_id']] = row['total']
        variantes_estoque[row['produto_base_id']] = row['estoque_soma'] or Decimal('0')

    exibir_estoque_base = getattr(empresa, 'exibir_estoque_base', 'OCULTAR')

    for p in page_obj.object_list:
        p.num_variantes = variantes_counts.get(p.id, 0)
        if p.num_variantes > 0 and exibir_estoque_base == 'SOMA':
            p.estoque_base_agregado = variantes_estoque.get(p.id, Decimal('0'))
        else:
            p.estoque_base_agregado = None  # None = mostrar "—" no template

    metricas_por_produto = {}
    total_entrada = Decimal('0')
    total_saida = Decimal('0')

    if produto_ids:
        for row in (
            EmprestimoProdutor.objects
            .filter(produto_id__in=produto_ids, empresa=empresa)
            .values('produto_id')
            .annotate(entrada=Sum('quantidade_emprestada'), saida=Sum('quantidade_devolvida'))
        ):
            entrada = row['entrada'] or Decimal('0')
            saida = row['saida'] or Decimal('0')
            metricas_por_produto[row['produto_id']] = {
                'entrada': entrada, 'saida': saida, 'saldo': entrada - saida,
            }
            total_entrada += entrada
            total_saida += saida

    for produto in page_obj.object_list:
        dados = metricas_por_produto.get(produto.id, {
            'entrada': Decimal('0'), 'saida': Decimal('0'), 'saldo': Decimal('0'),
        })
        produto.emprestimo_entrada = dados['entrada']
        produto.emprestimo_saida = dados['saida']
        produto.emprestimo_saldo = dados['saldo']

    return render(request, 'produtos/produto/produto_list.html', {
        'page_obj': page_obj,
        'categorias': categorias,
        'tipos_produto': tipos_produto,
        'query': query,
        'categoria_filter': categoria_filter,
        'tipo_filter': tipo_filter,
        'status_filter': status_filter,
        'sort_by': sort_by,
        'per_page': per_page,
        'per_page_options': [10, 25, 50, 100],
        'total_cadastros': total_cadastros,
        'total_ativos': total_ativos,
        'total_inativos': total_inativos,
        'total_estoque_baixo': total_estoque_baixo,
        'emprestimo_total_entrada': total_entrada,
        'emprestimo_total_saida': total_saida,
        'emprestimo_total_saldo': total_entrada - total_saida,
        'mostrar_variantes': mostrar_variantes,
        'exibir_estoque_base': exibir_estoque_base,
    })


@login_required
def produto_detail(request, pk):
    produto = get_object_or_404(
        Produto.objects.select_related(
            'categoria', 'subcategoria', 'unidade_medida',
            'unidade_compra', 'unidade_venda', 'ncm', 'fornecedor_padrao', 'produto_base'
        ).prefetch_related('tributacoes', 'documentos', 'atributos__dimensao')
        .filter(categoria__empresa=request.user.empresa),
        pk=pk
    )
    fornecedores_produto = ProdutoFornecedor.objects.filter(produto=produto).select_related('fornecedor')

    # Para produto base: buscar variantes com seus atributos ordenados
    variantes = []
    dimensoes_base = []
    if not produto.is_variante:
        variantes_qs = (
            produto.variantes
            .prefetch_related('atributos__dimensao')
            .order_by('nome')
        )
        variantes = list(variantes_qs)
        if variantes:
            # Coletar dimensões únicas em ordem para montar o cabeçalho da tabela
            dims_vistas = {}
            for v in variantes:
                for a in v.atributos.all():
                    key = (a.dimensao.ordem, a.dimensao.nome)
                    dims_vistas[key] = a.dimensao.nome
            dimensoes_base = [nome for _, nome in sorted(dims_vistas.keys())]

    return render(request, 'produtos/produto/produto_detail.html', {
        'produto': produto,
        'fornecedores_produto': fornecedores_produto,
        'variantes': variantes,
        'dimensoes_base': dimensoes_base,
    })


@login_required
def produto_create(request):
    if request.method == 'POST':
        form = ProdutoForm(request.POST, request.FILES, empresa=request.user.empresa)
        if form.is_valid():
            produto = form.save()
            messages.success(request, 'Produto cadastrado com sucesso!')

            continue_tab = request.POST.get('continue_tab')
            if continue_tab in {'defensivo', 'fertilizante', 'fornecedores'}:
                return redirect(f"{reverse('produtos:produto_update', args=[produto.pk])}#{continue_tab}")

            return redirect('produtos:produto_list')
    else:
        form = ProdutoForm(empresa=request.user.empresa)
    # Adiciona o dicionário de categorias condicionais
    categorias = Categoria.objects.filter(empresa=request.user.empresa)
    categorias_condicionais = json.dumps({str(cat.pk): cat.condiciona_campos for cat in categorias})
    return render(request, 'produtos/produto/produto_form.html', {
        'form': form,
        'action': 'Cadastrar',
        'categorias_condicionais': categorias_condicionais
    })


@login_required
def produto_update(request, pk):
    produto = get_object_or_404(Produto.objects.filter(categoria__empresa=request.user.empresa), pk=pk)
    if request.method == 'POST':
        form = ProdutoForm(request.POST, request.FILES, instance=produto, empresa=request.user.empresa)
        if form.is_valid():
            form.save()
            messages.success(request, 'Produto atualizado com sucesso!')
            return redirect('produtos:produto_list')
    else:
        form = ProdutoForm(instance=produto, empresa=request.user.empresa)
    # Buscar culturas, pragas e unidades para os modais
    from cadastros.models import Cultura, Praga
    culturas = Cultura.objects.filter(empresa=request.user.empresa).order_by('nome')
    pragas = Praga.objects.filter(empresa=request.user.empresa, ativa=True).order_by('nome_comum')
    unidades = UnidadeMedida.objects.filter(empresa=request.user.empresa).order_by('sigla')
    # Buscar fornecedores e fornecedores relacionados ao produto
    fornecedores = Fornecedor.objects.filter(empresa=request.user.empresa, ativa=True).order_by('nome')
    fornecedores_produto = ProdutoFornecedor.objects.filter(produto=produto).select_related('fornecedor')
    # Adiciona o dicionário de categorias condicionais
    categorias = Categoria.objects.filter(empresa=request.user.empresa)
    categorias_condicionais = json.dumps({str(cat.pk): cat.condiciona_campos for cat in categorias})
    return render(request, 'produtos/produto/produto_form.html', {
        'form': form,
        'action': 'Editar',
        'object': produto,
        'culturas': culturas,
        'pragas': pragas,
        'unidades_dosagem': unidades,
        'fornecedores': fornecedores,
        'fornecedores_produto': fornecedores_produto,
        'categorias_condicionais': categorias_condicionais
    })


@login_required
@login_required
def produto_delete(request, pk):
    produto = get_object_or_404(Produto.objects.filter(categoria__empresa=request.user.empresa), pk=pk)
    
    if request.method == 'POST':
        try:
            # Em vez de deletar fisicamente, apenas desativar
            # (protege integridade de lotes, compras, recebimentos vinculados)
            produto.ativo = False
            produto.save(update_fields=['ativo'])
            messages.success(request, f'Produto "{produto.nome}" desativado com sucesso!')
            return redirect('produtos:produto_list')
        except Exception as e:
            messages.error(request, f'Erro ao desativar produto: {str(e)}')
            return redirect('produtos:produto_detail', pk=pk)
    
    # Verificar se tem dependências (apenas para avisar na tela)
    has_lotes = produto.lotes.exists()
    has_pedidos = produto.itens_pedido_compra.exists()
    has_recebimentos = produto.recebimentos_diretos.exists()
    
    return render(request, 'produtos/produto/produto_confirm_delete.html', {
        'object': produto,
        'has_dependencias': has_lotes or has_pedidos or has_recebimentos,
        'has_lotes': has_lotes,
        'has_pedidos': has_pedidos,
        'has_recebimentos': has_recebimentos,
    })



@login_required
def produto_clone(request, pk):
    """Clona um produto com todos os seus dados relacionados"""
    produto_original = get_object_or_404(Produto.objects.filter(categoria__empresa=request.user.empresa), pk=pk)
    
    # Criar cópia do produto
    produto_clone = Produto.objects.filter(categoria__empresa=request.user.empresa).get(pk=pk)
    produto_clone.pk = None  # Remove o ID para criar novo registro
    produto_clone.codigo = f"{produto_original.codigo}-COPIA"
    produto_clone.nome = f"{produto_original.nome} (CÓPIA)"
    produto_clone.codigo_barras = ""  # Limpar código de barras para evitar duplicidade
    produto_clone.save()
    
    # Clonar tributações
    tributacoes = ProdutoTributacao.objects.filter(produto=produto_original)
    for trib in tributacoes:
        trib.pk = None
        trib.produto = produto_clone
        trib.save()
    
    # Clonar defensivos/culturas se existirem
    defensivos = ProdutoDefensivoCultura.objects.filter(produto=produto_original)
    for def_cult in defensivos:
        def_cult.pk = None
        def_cult.produto = produto_clone
        def_cult.save()
    
    messages.success(request, f'Produto clonado com sucesso! Edite o código e nome conforme necessário.')
    return redirect('produtos:produto_update', pk=produto_clone.pk)


# ============== TRIBUTAÇÃO ==============

def _get_regime_tributario(empresa):
    """Return (codigo, display) for the company's fiscal regime."""
    try:
        from faturamento.models import ConfiguracaoFiscal
        cfg = ConfiguracaoFiscal.objects.get(empresa=empresa)
        return cfg.regime_tributario, cfg.get_regime_tributario_display()
    except Exception:
        return 'SIMPLES_NACIONAL', 'Simples Nacional'


@login_required
def produtotributacao_create(request, produto_id):
    empresa = request.user.empresa
    produto = get_object_or_404(Produto.objects.filter(categoria__empresa=empresa), pk=produto_id)
    if request.method == 'POST':
        form = ProdutoTributacaoForm(request.POST, empresa=empresa)
        if form.is_valid():
            tributacao = form.save(commit=False)
            tributacao.produto = produto
            tributacao.save()
            messages.success(request, 'Tributação cadastrada com sucesso!')
            return redirect('produtos:produto_detail', pk=produto.pk)
    else:
        form = ProdutoTributacaoForm(initial={'produto': produto, 'origem_mercadoria': produto.origem_mercadoria}, empresa=empresa)
    regime, regime_display = _get_regime_tributario(empresa)
    return render(request, 'produtos/tributacao/tributacao_form.html', {
        'form': form,
        'produto': produto,
        'action': 'Cadastrar',
        'regime_tributario': regime,
        'regime_tributario_display': regime_display,
    })


@login_required
def produtotributacao_update(request, pk):
    tributacao = get_object_or_404(ProdutoTributacao.objects.filter(produto__categoria__empresa=request.user.empresa), pk=pk)
    if request.method == 'POST':
        form = ProdutoTributacaoForm(request.POST, instance=tributacao, empresa=request.user.empresa)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tributação atualizada com sucesso!')
            return redirect('produtos:produto_detail', pk=tributacao.produto.pk)
    else:
        form = ProdutoTributacaoForm(instance=tributacao, empresa=request.user.empresa)
    # Buscar o código CFOP salvo
    cfop_codigo = ''
    natureza_descricao = ''
    if form.instance.cfop_id:
        try:
            cfop_codigo = form.fields['cfop'].queryset.get(pk=form.instance.cfop_id).codigo
        except Exception:
            cfop_codigo = ''
    if form.instance.natureza_operacao_id:
        try:
            natureza_descricao = form.fields['natureza_operacao'].queryset.get(pk=form.instance.natureza_operacao_id).descricao
        except Exception:
            natureza_descricao = ''
    regime, regime_display = _get_regime_tributario(request.user.empresa)
    return render(request, 'produtos/tributacao/tributacao_form.html', {
        'form': form,
        'produto': tributacao.produto,
        'action': 'Editar',
        'cfop_codigo': cfop_codigo,
        'natureza_descricao': natureza_descricao,
        'regime_tributario': regime,
        'regime_tributario_display': regime_display,
    })


@login_required
def produtotributacao_delete(request, pk):
    tributacao = get_object_or_404(ProdutoTributacao.objects.filter(produto__categoria__empresa=request.user.empresa), pk=pk)
    produto_id = tributacao.produto.pk
    if request.method == 'POST':
        tributacao.delete()
        messages.success(request, 'Tributação excluída com sucesso!')
        
        # Se for AJAX, retornar JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        
        return redirect('produtos:produto_update', pk=produto_id)
    return render(request, 'produtos/tributacao/tributacao_confirm_delete.html', {
        'object': tributacao
    })


@login_required
def ajax_buscar_produtos(request):
    """Autocomplete: busca produtos por nome ou código (max 15 resultados).
    Parâmetros opcionais:
    - apenas_base=1: retorna somente produtos base (produto_base__isnull=True)
    - excluir_variantes=1: sinônimo de apenas_base=1
    """
    q = request.GET.get('q', '').strip()
    empresa = request.user.empresa
    if not q or len(q) < 2:
        return JsonResponse({'results': []})
    qs = Produto.objects.filter(
        categoria__empresa=empresa, ativo=True
    ).filter(
        Q(nome__icontains=q) | Q(codigo__icontains=q)
    ).select_related('ncm', 'categoria')
    apenas_base = request.GET.get('apenas_base') == '1' or request.GET.get('excluir_variantes') == '1'
    if apenas_base:
        qs = qs.filter(produto_base__isnull=True)
    qs = qs[:15]
    results = [
        {
            'id': p.pk,
            'text': f'{p.codigo} — {p.nome}',
            'tem_variantes': p.variantes.exists() if not apenas_base else False,
            'categoria_nome': p.categoria.nome,
        }
        for p in qs
    ]
    return JsonResponse({'results': results})


@login_required
def ajax_variante_dimensoes(request):
    """Retorna dimensões e valores disponíveis para um produto base.
    GET ?produto_base_id=X
    Resposta: {dimensoes: [{id, nome, valores: [str]}]}
    """
    empresa = request.user.empresa
    produto_base_id = request.GET.get('produto_base_id')
    if not produto_base_id:
        return JsonResponse({'dimensoes': []})
    try:
        base = Produto.objects.get(pk=produto_base_id, categoria__empresa=empresa, produto_base__isnull=True)
    except Produto.DoesNotExist:
        return JsonResponse({'error': 'Produto base não encontrado.'}, status=404)

    # Coletar dimensões e valores a partir das variantes existentes
    from collections import defaultdict
    dim_valores = defaultdict(set)
    dim_meta = {}
    for atributo in (
        ProdutoAtributo.objects
        .filter(produto__produto_base=base, produto__ativo=True)
        .select_related('dimensao')
        .order_by('dimensao__ordem', 'dimensao__nome')
    ):
        d = atributo.dimensao
        dim_meta[d.pk] = {'id': d.pk, 'nome': d.nome, 'ordem': d.ordem}
        dim_valores[d.pk].add(atributo.valor)

    dimensoes = [
        {**dim_meta[pk], 'valores': sorted(dim_valores[pk])}
        for pk in sorted(dim_meta, key=lambda k: dim_meta[k]['ordem'])
    ]
    return JsonResponse({'produto_base': {'id': base.pk, 'nome': base.nome}, 'dimensoes': dimensoes})


@login_required
@require_POST
def ajax_variante_resolver(request):
    """Resolve a variante exata dado o produto base e os atributos selecionados.
    POST JSON: {produto_base_id: X, atributos: {dimensao_id: valor, ...}}
    Resposta: {produto_id, nome_completo, codigo} ou {erro}
    """
    empresa = request.user.empresa
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'erro': 'JSON inválido.'}, status=400)

    produto_base_id = data.get('produto_base_id')
    atributos_selecionados = data.get('atributos', {})  # {str(dimensao_id): valor}

    if not produto_base_id or not atributos_selecionados:
        return JsonResponse({'erro': 'produto_base_id e atributos são obrigatórios.'}, status=400)

    try:
        base = Produto.objects.get(pk=produto_base_id, categoria__empresa=empresa)
    except Produto.DoesNotExist:
        return JsonResponse({'erro': 'Produto base não encontrado.'}, status=404)

    # Buscar todas as variantes do base e filtrar pelos atributos
    variantes = Produto.objects.filter(produto_base=base, ativo=True).prefetch_related('atributos__dimensao')
    for variante in variantes:
        attrs = {str(a.dimensao_id): a.valor for a in variante.atributos.all()}
        if all(attrs.get(str(dim_id)) == valor for dim_id, valor in atributos_selecionados.items()):
            return JsonResponse({
                'produto_id': variante.pk,
                'nome_completo': variante.nome_completo,
                'codigo': variante.codigo,
                'preco_venda': str(variante.preco_venda),
                'unidade_sigla': variante.unidade_venda.sigla if variante.unidade_venda else '',
            })

    return JsonResponse({'erro': 'Nenhuma variante encontrada para esta combinação de atributos.'})


@login_required
def relatorio_por_atributo(request):
    """Relatório de faturamento/compras filtrado por dimensão de variante (Variedade, Marca, Calibre)."""
    empresa = request.user.empresa
    dimensoes = DimensaoVariante.objects.filter(empresa=empresa, ativo=True).order_by('ordem', 'nome')

    dimensao_id = request.GET.get('dimensao')
    valor_filtro = request.GET.get('valor', '').strip()
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')

    resultados = None
    dimensao_selecionada = None
    valores_disponiveis = []

    if dimensao_id:
        try:
            dimensao_selecionada = DimensaoVariante.objects.get(pk=dimensao_id, empresa=empresa)
            valores_disponiveis = (
                ProdutoAtributo.objects
                .filter(dimensao=dimensao_selecionada)
                .values_list('valor', flat=True)
                .distinct()
                .order_by('valor')
            )
        except DimensaoVariante.DoesNotExist:
            pass

    if dimensao_selecionada and valor_filtro:
        # Produtos com esse atributo
        produto_ids = ProdutoAtributo.objects.filter(
            dimensao=dimensao_selecionada, valor=valor_filtro
        ).values_list('produto_id', flat=True)

        # Faturamento (ItemNotaFiscal)
        try:
            from faturamento.models import ItemNotaFiscal
            qs_nfe = ItemNotaFiscal.objects.filter(
                produto_id__in=produto_ids,
                nota__empresa=empresa,
            ).select_related('produto', 'nota')
            if data_inicio:
                qs_nfe = qs_nfe.filter(nota__data_emissao__gte=data_inicio)
            if data_fim:
                qs_nfe = qs_nfe.filter(nota__data_emissao__lte=data_fim)
            fat_total = qs_nfe.aggregate(
                qtd=Sum('quantidade'), valor=Sum('valor_total')
            )
            faturamento_itens = qs_nfe.order_by('-nota__data_emissao')[:50]
        except Exception:
            fat_total = {'qtd': None, 'valor': None}
            faturamento_itens = []

        # Compras (ItemRecebimento)
        try:
            from compras.models import ItemRecebimento
            qs_compra = ItemRecebimento.objects.filter(
                produto_id__in=produto_ids,
                recebimento__empresa=empresa,
            ).select_related('produto', 'recebimento')
            if data_inicio:
                qs_compra = qs_compra.filter(recebimento__data_recebimento__gte=data_inicio)
            if data_fim:
                qs_compra = qs_compra.filter(recebimento__data_recebimento__lte=data_fim)
            compra_total = qs_compra.aggregate(
                qtd=Sum('quantidade'), valor=Sum('valor_total')
            )
            compra_itens = qs_compra.order_by('-recebimento__data_recebimento')[:50]
        except Exception:
            compra_total = {'qtd': None, 'valor': None}
            compra_itens = []

        resultados = {
            'dimensao': dimensao_selecionada,
            'valor': valor_filtro,
            'fat_total': fat_total,
            'faturamento_itens': faturamento_itens,
            'compra_total': compra_total,
            'compra_itens': compra_itens,
        }

    return render(request, 'produtos/relatorio_atributo.html', {
        'dimensoes': dimensoes,
        'dimensao_selecionada': dimensao_selecionada,
        'valores_disponiveis': valores_disponiveis,
        'valor_filtro': valor_filtro,
        'data_inicio': data_inicio or '',
        'data_fim': data_fim or '',
        'resultados': resultados,
        'dimensao_id': dimensao_id or '',
    })


@login_required
def ajax_produto_tributacoes(request, produto_id):
    """Retorna tributações de um produto para o recurso 'copiar de outro produto'."""
    empresa = request.user.empresa
    try:
        produto = Produto.objects.get(pk=produto_id, categoria__empresa=empresa)
    except Produto.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Produto não encontrado'}, status=404)

    tributacoes = []
    for t in produto.tributacoes.select_related('cfop', 'natureza_operacao').filter(ativo=True):
        tributacoes.append({
            'cfop_id':  t.cfop_id,
            'cfop_codigo': t.cfop.codigo,
            'cfop_nome': t.cfop.nome,
            'natureza_id': t.natureza_operacao_id or '',
            'natureza_descricao': t.natureza_operacao.descricao if t.natureza_operacao else '',
            'descricao': t.descricao or '',
            'origem_mercadoria': t.origem_mercadoria,
            'icms_situacao_tributaria': t.icms_situacao_tributaria,
            'icms_modalidade_base': t.icms_modalidade_base,
            'icms_aliquota': str(t.icms_aliquota),
            'icms_base_calculo': str(t.icms_base_calculo),
            'icms_reducao_base': str(t.icms_reducao_base),
            'icms_st_aliquota': str(t.icms_st_aliquota),
            'icms_st_mva': str(t.icms_st_mva),
            'icms_st_reducao_base': str(t.icms_st_reducao_base),
            'ipi_situacao_tributaria': t.ipi_situacao_tributaria,
            'ipi_aliquota': str(t.ipi_aliquota),
            'ipi_codigo_enquadramento': t.ipi_codigo_enquadramento,
            'pis_situacao_tributaria': t.pis_situacao_tributaria,
            'pis_aliquota': str(t.pis_aliquota),
            'pis_base_calculo': str(t.pis_base_calculo),
            'cofins_situacao_tributaria': t.cofins_situacao_tributaria,
            'cofins_aliquota': str(t.cofins_aliquota),
            'cofins_base_calculo': str(t.cofins_base_calculo),
        })
    return JsonResponse({'success': True, 'produto_nome': produto.nome, 'tributacoes': tributacoes})


# ============== CADASTRO RÁPIDO VIA AJAX ==============

@login_required
def categoria_create_ajax(request):
    """Cadastro rápido de categoria via AJAX"""
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            codigo = request.POST.get('codigo', '').strip()
            nome = request.POST.get('nome', '').strip()
            
            if not codigo or not nome:
                return JsonResponse({
                    'success': False,
                    'error': 'Código e nome são obrigatórios'
                }, status=400)
            
            # Verifica se já existe
            if Categoria.objects.filter(empresa=request.user.empresa, codigo=codigo).exists():
                return JsonResponse({
                    'success': False,
                    'error': f'Já existe uma categoria com o código {codigo}'
                }, status=400)
            
            # Cria a categoria
            categoria = Categoria.objects.create(
                empresa=request.user.empresa,
                codigo=codigo,
                nome=nome,
                descricao=request.POST.get('descricao', '').strip()
            )
            
            return JsonResponse({
                'success': True,
                'id': categoria.id,
                'nome': categoria.nome,
                'codigo': categoria.codigo
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'success': False, 'error': 'Método não permitido'}, status=405)


@login_required
def subcategoria_create_ajax(request):
    """Cadastro rápido de subcategoria via AJAX"""
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            categoria_id = request.POST.get('categoria_id', '').strip()
            codigo = request.POST.get('codigo', '').strip()
            nome = request.POST.get('nome', '').strip()
            
            if not categoria_id or not codigo or not nome:
                return JsonResponse({
                    'success': False,
                    'error': 'Categoria, código e nome são obrigatórios'
                }, status=400)
            
            # Busca a categoria
            try:
                categoria = Categoria.objects.get(
                    id=categoria_id,
                    empresa=request.user.empresa
                )
            except Categoria.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Categoria não encontrada'
                }, status=404)
            
            # Verifica se já existe
            if SubCategoria.objects.filter(categoria=categoria, codigo=codigo).exists():
                return JsonResponse({
                    'success': False,
                    'error': f'Já existe uma subcategoria com o código {codigo} nesta categoria'
                }, status=400)
            
            # Cria a subcategoria
            subcategoria = SubCategoria.objects.create(
                categoria=categoria,
                codigo=codigo,
                nome=nome,
                descricao=request.POST.get('descricao', '').strip()
            )
            
            return JsonResponse({
                'success': True,
                'id': subcategoria.id,
                'nome': subcategoria.nome,
                'codigo': subcategoria.codigo,
                'categoria_id': categoria.id
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'success': False, 'error': 'Método não permitido'}, status=405)


@login_required
def cultura_create_ajax(request):
    """Cadastro rápido de cultura via AJAX"""
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            import json
            from cadastros.models import Cultura
            
            data = json.loads(request.body)
            nome = data.get('nome', '').strip()
            tipo = data.get('tipo', 'FRUTA')
            
            if not nome:
                return JsonResponse({
                    'success': False,
                    'error': 'Nome é obrigatório'
                }, status=400)
            
            # Verifica se já existe
            if Cultura.objects.filter(empresa=request.user.empresa, nome__iexact=nome).exists():
                return JsonResponse({
                    'success': False,
                    'error': f'Já existe uma cultura com o nome {nome}'
                }, status=400)
            
            # Cria a cultura
            cultura = Cultura.objects.create(
                empresa=request.user.empresa,
                nome=nome,
                tipo=tipo
            )
            
            return JsonResponse({
                'success': True,
                'id': cultura.id,
                'nome': cultura.nome
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'success': False, 'error': 'Método não permitido'}, status=405)



@login_required
def unidademedida_create_ajax(request):
    """Cadastro rápido de unidade de medida via AJAX"""
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            import json
            data = json.loads(request.body)
            
            sigla = data.get('sigla', '').strip()
            nome = data.get('nome', '').strip()
            tipo = data.get('tipo', '').strip()
            
            if not sigla or not nome or not tipo:
                return JsonResponse({
                    'success': False,
                    'error': 'Sigla, nome e tipo são obrigatórios'
                }, status=400)
            
            # Verifica se já existe
            if UnidadeMedida.objects.filter(empresa=request.user.empresa, sigla__iexact=sigla).exists():
                return JsonResponse({
                    'success': False,
                    'error': f'Já existe uma unidade de medida com a sigla {sigla}'
                }, status=400)
            
            # Cria a unidade de medida
            unidade = UnidadeMedida.objects.create(
                empresa=request.user.empresa,
                sigla=sigla,
                nome=nome,
                tipo=tipo
            )
            
            return JsonResponse({
                'success': True,
                'id': unidade.id,
                'sigla': unidade.sigla,
                'nome': unidade.nome
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'success': False, 'error': 'Método não permitido'}, status=405)


@login_required
def ncm_buscar_ajax(request):
    """Busca NCM por código e retorna os dados incluindo CEST"""
    if request.method == 'GET' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        from cadastros.models import NCM
        
        codigo = request.GET.get('codigo', '').strip()
        
        if not codigo:
            return JsonResponse({
                'success': False,
                'error': 'Código não fornecido'
            }, status=400)
        
        try:
            # Buscar NCM
            ncm = NCM.objects.filter(codigo=codigo, ativo=True).first()
            
            if ncm:
                return JsonResponse({
                    'success': True,
                    'id': ncm.id,
                    'codigo': ncm.codigo,
                    'nome': ncm.nome,
                    'descricao': ncm.descricao,
                    'cest': ncm.cest or ''
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'NCM não encontrado'
                }, status=404)
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'success': False, 'error': 'Método não permitido'}, status=405)


@login_required
def cfop_buscar_ajax(request):
    """View AJAX para buscar CFOP por código"""
    if request.method == 'GET':
        codigo = request.GET.get('codigo', '').strip()
        if not codigo:
            return JsonResponse({'success': False, 'error': 'Codigo nao fornecido'}, status=400)
        try:
            empresa = getattr(request.user, 'empresa', None)
            if not empresa:
                return JsonResponse({'success': False, 'error': 'Empresa não encontrada para o usuário.'}, status=400)
            from cadastros.models import EmpresaCFOP
            empresa_cfop = EmpresaCFOP.objects.filter(empresa=empresa, codigo=codigo, ativo=True).first()
            if not empresa_cfop:
                return JsonResponse({'success': False, 'error': 'CFOP não permitido para esta empresa.'}, status=404)
            cfop = empresa_cfop.template
            natureza_global = cfop.natureza_operacao if cfop else None
            natureza_dict = {'id': None, 'descricao': ''}

            if natureza_global:
                # Tentar encontrar NaturezaOperacao desta empresa pelo mesmo código
                from produtos.models import NaturezaOperacao
                natureza_empresa = NaturezaOperacao.objects.filter(
                    empresa=empresa, codigo=natureza_global.codigo, ativo=True
                ).first()
                if not natureza_empresa:
                    # Busca por descrição similar como fallback
                    natureza_empresa = NaturezaOperacao.objects.filter(
                        empresa=empresa, ativo=True
                    ).filter(descricao__icontains=natureza_global.descricao[:30]).first()

                if natureza_empresa:
                    natureza_dict = {'id': natureza_empresa.id, 'descricao': natureza_empresa.descricao}
                else:
                    # Natureza da empresa não encontrada — retorna só descrição para exibição
                    natureza_dict = {'id': None, 'descricao': natureza_global.descricao}
            elif cfop:
                natureza_dict = {'id': None, 'descricao': cfop.nome}
            return JsonResponse({
                'success': True,
                'id': cfop.id if cfop else empresa_cfop.id,
                'codigo': cfop.codigo if cfop else empresa_cfop.codigo,
                'nome': cfop.nome if cfop else empresa_cfop.nome,
                'descricao': cfop.nome if cfop else empresa_cfop.nome,
                'observacao': cfop.descricao if cfop else empresa_cfop.descricao or '',
                'natureza_operacao': natureza_dict
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'Metodo nao permitido'}, status=405)


# ============== DEFENSIVO CULTURA ==============

@login_required
def defensivo_cultura_create(request, produto_pk):
    """Criar novo registro de cultura/praga para defensivo"""
    produto = get_object_or_404(Produto.objects.filter(categoria__empresa=request.user.empresa), pk=produto_pk)
    
    # Verificar se o produto pertence à empresa do usuário
    if produto.categoria.empresa != request.user.empresa:
        messages.error(request, 'Produto não encontrado.')
        return redirect('produtos:produto_list')
    
    if request.method == 'POST':
        form = ProdutoDefensivoCulturaForm(request.POST, empresa=request.user.empresa)
        if form.is_valid():
            defensivo_cultura = form.save(commit=False)
            defensivo_cultura.produto = produto
            defensivo_cultura.save()
            messages.success(request, 'Cultura/Praga cadastrada com sucesso!')
            return redirect('produtos:produto_update', pk=produto.pk)
        else:
            # Se houver erros, exibir mensagem de erro
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
            return redirect('produtos:produto_update', pk=produto.pk)
    
    # Se não for POST, redirecionar de volta
    return redirect('produtos:produto_update', pk=produto.pk)


@login_required
def defensivo_cultura_delete(request, pk):
    """Excluir registro de cultura/praga"""
    defensivo_cultura = get_object_or_404(ProdutoDefensivoCultura, pk=pk)
    
    # Verificar se o produto pertence à empresa do usuário
    if defensivo_cultura.produto.categoria.empresa != request.user.empresa:
        return JsonResponse({'success': False, 'error': 'Não autorizado'}, status=403)
    
    if request.method == 'POST':
        try:
            produto_pk = defensivo_cultura.produto.pk
            defensivo_cultura.delete()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'error': 'Método não permitido'}, status=405)


@login_required
def defensivo_cultura_edit(request, pk):
    """Editar registro de cultura/praga"""
    defensivo_cultura = get_object_or_404(ProdutoDefensivoCultura, pk=pk)
    produto = defensivo_cultura.produto
    
    # Verificar se o produto pertence à empresa do usuário
    if produto.categoria.empresa != request.user.empresa:
        messages.error(request, 'Não autorizado.')
        return redirect('produtos:produto_list')
    
    if request.method == 'POST':
        form = ProdutoDefensivoCulturaForm(request.POST, instance=defensivo_cultura, empresa=request.user.empresa)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cultura/Praga atualizada com sucesso!')
            return redirect('produtos:produto_update', pk=produto.pk)
        else:
            # Se houver erros, exibir mensagem de erro
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
            return redirect('produtos:produto_update', pk=produto.pk)
    else:
        form = ProdutoDefensivoCulturaForm(instance=defensivo_cultura, empresa=request.user.empresa)
    
    # Buscar listas para o contexto
    from cadastros.models import Cultura, Praga
    culturas = Cultura.objects.filter(empresa=request.user.empresa).order_by('nome')
    pragas = Praga.objects.filter(empresa=request.user.empresa, ativa=True).order_by('nome_comum')
    unidades_dosagem = UnidadeMedida.objects.filter(empresa=request.user.empresa)
    
    return render(request, 'produtos/defensivo_cultura/defensivo_cultura_form.html', {
        'form': form,
        'produto': produto,
        'defensivo_cultura': defensivo_cultura,
        'action': 'Editar',
        'culturas': culturas,
        'pragas': pragas,
        'unidades_dosagem': unidades_dosagem
    })


# ============== VIEWS DE DOCUMENTOS DO PRODUTO ==============

@login_required
def documento_upload(request, produto_pk):
    """Upload de documento para produto"""
    from .models import ProdutoDocumento
    produto = get_object_or_404(Produto.objects.filter(categoria__empresa=request.user.empresa), pk=produto_pk)
    
    # Verificar se o produto pertence à empresa do usuário
    if produto.categoria.empresa != request.user.empresa:
        messages.error(request, 'Produto não encontrado.')
        return redirect('produtos:produto_list')
    
    if request.method == 'POST':
        tipo = request.POST.get('tipo')
        nome = request.POST.get('nome')
        arquivo = request.FILES.get('arquivo')
        observacoes = request.POST.get('observacoes', '')
        
        if not tipo or not nome or not arquivo:
            messages.error(request, 'Preencha todos os campos obrigatórios.')
            return redirect('produtos:produto_update', pk=produto.pk)
        
        try:
            documento = ProdutoDocumento(
                produto=produto,
                tipo=tipo,
                nome=nome,
                arquivo=arquivo,
                observacoes=observacoes,
                cadastrado_por=request.user
            )
            documento.save()
            messages.success(request, 'Documento enviado com sucesso!')
        except Exception as e:
            messages.error(request, f'Erro ao enviar documento: {str(e)}')
        
        return redirect('produtos:produto_update', pk=produto.pk)
    
    return redirect('produtos:produto_update', pk=produto.pk)


@login_required
def documento_delete(request, pk):
    """Excluir documento"""
    from .models import ProdutoDocumento
    documento = get_object_or_404(ProdutoDocumento, pk=pk)
    
    # Verificar se o produto pertence à empresa do usuário
    if documento.produto.categoria.empresa != request.user.empresa:
        return JsonResponse({'success': False, 'error': 'Não autorizado'}, status=403)
    
    if request.method == 'POST':
        try:
            produto_pk = documento.produto.pk
            # Deletar o arquivo físico
            if documento.arquivo:
                documento.arquivo.delete()
            documento.delete()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'error': 'Método não permitido'}, status=405)


# ============== PRODUTO FORNECEDOR ==============

@login_required
def fornecedores_listar(request):
    """Lista fornecedores ativos da empresa via AJAX"""
    fornecedores = Fornecedor.objects.filter(
        empresa=request.user.empresa, 
        ativa=True
    ).order_by('nome').values('id', 'nome', 'cnpj_cpf')
    
    return JsonResponse({
        'success': True,
        'fornecedores': list(fornecedores)
    })


@login_required
@require_POST
def produto_fornecedor_create(request, produto_pk):
    """Adiciona um fornecedor a um produto via AJAX"""
    try:
        produto = get_object_or_404(Produto.objects.filter(categoria__empresa=request.user.empresa), pk=produto_pk)
        
        # Verificar se o produto pertence à empresa do usuário
        if produto.categoria.empresa != request.user.empresa:
            return JsonResponse({'success': False, 'error': 'Não autorizado'}, status=403)
        
        # Parse JSON data
        data = json.loads(request.body)
        
        fornecedor_id = data.get('fornecedor_id')
        codigo_fornecedor = data.get('codigo_fornecedor', '').strip()
        
        if not fornecedor_id or not codigo_fornecedor:
            return JsonResponse({'success': False, 'error': 'Fornecedor e código são obrigatórios'}, status=400)
        
        fornecedor = get_object_or_404(Fornecedor, pk=fornecedor_id, empresa=request.user.empresa)
        
        # Verificar se já existe essa combinação
        if ProdutoFornecedor.objects.filter(produto=produto, fornecedor=fornecedor).exists():
            return JsonResponse({'success': False, 'error': 'Este fornecedor já está vinculado ao produto'}, status=400)
        
        # Criar relacionamento
        produto_fornecedor = ProdutoFornecedor(
            produto=produto,
            fornecedor=fornecedor,
            codigo_fornecedor=codigo_fornecedor,
            preco_compra=Decimal(data.get('preco_compra', 0)),
            prazo_entrega=data.get('prazo_entrega') or None,
            quantidade_minima=Decimal(data.get('quantidade_minima', 0)),
            fornecedor_preferencial=data.get('fornecedor_preferencial', False),
            observacoes=data.get('observacoes', ''),
            cadastrado_por=request.user
        )
        produto_fornecedor.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Fornecedor adicionado com sucesso!',
            'id': produto_fornecedor.pk
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Dados JSON inválidos'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def produto_fornecedor_delete(request, pk):
    """Remove um fornecedor de um produto via AJAX"""
    try:
        produto_fornecedor = get_object_or_404(ProdutoFornecedor, pk=pk)
        
        # Verificar se o produto pertence à empresa do usuário
        if produto_fornecedor.produto.categoria.empresa != request.user.empresa:
            return JsonResponse({'success': False, 'error': 'Não autorizado'}, status=403)
        
        produto_fornecedor.delete()

        return JsonResponse({
            'success': True,
            'message': 'Fornecedor removido com sucesso!'
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ============== ATRIBUTOS DE VARIAÇÃO (CRUD inline) ==============

@login_required
@require_POST
def produto_atributo_salvar(request, produto_pk):
    empresa = request.user.empresa
    produto = get_object_or_404(Produto, pk=produto_pk, categoria__empresa=empresa)
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'success': False, 'error': 'JSON inválido.'}, status=400)

    dim_nome = (data.get('dimensao_nome') or '').strip()
    valor    = (data.get('valor') or '').strip()
    atrib_pk = data.get('atributo_id')

    if not dim_nome or not valor:
        return JsonResponse({'success': False, 'error': 'Dimensão e valor são obrigatórios.'}, status=400)

    dim, _ = DimensaoVariante.objects.get_or_create(
        empresa=empresa, nome=dim_nome, defaults={'ordem': 0}
    )

    if atrib_pk:
        atrib = get_object_or_404(ProdutoAtributo, pk=atrib_pk, produto=produto)
        # Se mudou a dimensão, verificar conflito
        if atrib.dimensao_id != dim.pk:
            if ProdutoAtributo.objects.filter(produto=produto, dimensao=dim).exclude(pk=atrib_pk).exists():
                return JsonResponse({'success': False, 'error': f'Já existe um atributo "{dim_nome}" neste produto.'}, status=400)
            atrib.dimensao = dim
        atrib.valor = valor
        atrib.save()
        msg = 'Atributo atualizado.'
    else:
        if ProdutoAtributo.objects.filter(produto=produto, dimensao=dim).exists():
            return JsonResponse({'success': False, 'error': f'Já existe um atributo "{dim_nome}" neste produto.'}, status=400)
        atrib = ProdutoAtributo.objects.create(produto=produto, dimensao=dim, valor=valor)
        msg = 'Atributo adicionado.'

    return JsonResponse({
        'success': True,
        'message': msg,
        'atributo': {'id': atrib.pk, 'dimensao': dim.nome, 'valor': atrib.valor},
    })


@login_required
@require_POST
def produto_atributo_excluir(request, pk):
    empresa = request.user.empresa
    atrib = get_object_or_404(ProdutoAtributo, pk=pk, produto__categoria__empresa=empresa)
    atrib.delete()
    return JsonResponse({'success': True, 'message': 'Atributo removido.'})


@login_required
def produto_atributo_listar(request, produto_pk):
    empresa = request.user.empresa
    produto = get_object_or_404(Produto, pk=produto_pk, categoria__empresa=empresa)
    atributos = list(
        produto.atributos.select_related('dimensao')
        .values('id', 'dimensao__nome', 'valor')
        .order_by('dimensao__ordem', 'dimensao__nome')
    )
    dimensoes = list(
        DimensaoVariante.objects.filter(empresa=empresa, ativo=True)
        .values_list('nome', flat=True)
        .order_by('ordem', 'nome')
    )
    return JsonResponse({'atributos': atributos, 'dimensoes': dimensoes})


# ============== GERADOR DE VARIAÇÕES ==============

@login_required
def produto_variacao_form(request):
    empresa = request.user.empresa
    categorias = Categoria.objects.filter(empresa=empresa, ativo=True).order_by('nome')
    unidades = UnidadeMedida.objects.filter(empresa=empresa, ativo=True).order_by('nome')
    dimensoes = list(
        DimensaoVariante.objects.filter(empresa=empresa, ativo=True)
        .values('id', 'nome', 'ordem')
        .order_by('ordem', 'nome')
    )

    produto_origem_json = 'null'
    origem_pk = request.GET.get('origem')
    if origem_pk:
        try:
            p = Produto.objects.select_related(
                'categoria', 'ncm', 'unidade_medida', 'unidade_compra', 'unidade_venda'
            ).get(pk=origem_pk, categoria__empresa=empresa)
            produto_origem_json = json.dumps({
                'id': p.pk,
                'nome': p.nome,
                'categoria_id': p.categoria_id,
                'ncm_id': p.ncm_id,
                'ncm_codigo': p.ncm.codigo if p.ncm else '',
                'ncm_descricao': p.ncm.descricao if p.ncm else '',
                'cest': p.cest,
                'unidade_medida_id': p.unidade_medida_id,
                'unidade_compra_id': p.unidade_compra_id,
                'unidade_venda_id': p.unidade_venda_id,
                'tipo_item': p.tipo_item,
                'origem_mercadoria': p.origem_mercadoria,
                'peso_liquido': float(p.peso_liquido_unitario),
                'peso_bruto': float(p.peso_bruto_unitario),
                'fator_conversao': float(p.fator_conversao),
            }, ensure_ascii=False)
        except Produto.DoesNotExist:
            pass

    return render(request, 'produtos/produto/variacao_gerar.html', {
        'categorias': categorias,
        'unidades': unidades,
        'dimensoes_json': json.dumps(dimensoes, ensure_ascii=False),
        'tipo_item_choices': Produto.TIPO_ITEM_CHOICES,
        'origem_choices': Produto.ORIGEM_MERCADORIA_CHOICES,
        'produto_origem_json': produto_origem_json,
    })


@login_required
@require_POST
def produto_variacao_gerar(request):
    empresa = request.user.empresa
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'success': False, 'error': 'JSON inválido.'}, status=400)

    combinacoes = data.get('combinacoes', [])
    if not combinacoes:
        return JsonResponse({'success': False, 'error': 'Nenhuma combinação selecionada.'}, status=400)

    # Validar campos base obrigatórios
    try:
        categoria = Categoria.objects.get(pk=data['categoria_id'], empresa=empresa)
        ncm = NCM.objects.get(pk=data['ncm_id'])
        um  = UnidadeMedida.objects.get(pk=data['unidade_medida_id'], empresa=empresa)
        uc  = UnidadeMedida.objects.get(pk=data['unidade_compra_id'], empresa=empresa)
        uv  = UnidadeMedida.objects.get(pk=data['unidade_venda_id'], empresa=empresa)
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Campos base inválidos: {e}'}, status=400)

    criados = []
    erros = []

    # Produto base opcional — agrupa as variantes criadas
    produto_base_obj = None
    produto_base_id = data.get('produto_base_id')
    if produto_base_id:
        try:
            produto_base_obj = Produto.objects.get(pk=produto_base_id, categoria__empresa=empresa)
        except Produto.DoesNotExist:
            pass

    tributacoes_base = (
        list(ProdutoTributacao.objects.filter(produto=produto_base_obj))
        if produto_base_obj else []
    )

    try:
        with transaction.atomic():
            for combo in combinacoes:
                nome = (combo.get('nome') or '').strip()
                atributos = combo.get('atributos', {})
                if not nome:
                    erros.append({'nome': '(sem nome)', 'erro': 'Nome vazio, combinação ignorada.'})
                    continue
                produto = Produto(
                    nome=nome,
                    categoria=categoria,
                    ncm=ncm,
                    cest=data.get('cest', '') or '',
                    unidade_medida=um,
                    unidade_compra=uc,
                    unidade_venda=uv,
                    tipo_item=data.get('tipo_item', '00'),
                    origem_mercadoria=data.get('origem_mercadoria', '0'),
                    peso_liquido_unitario=data.get('peso_liquido', 0) or 0,
                    peso_bruto_unitario=data.get('peso_bruto', 0) or 0,
                    fator_conversao=data.get('fator_conversao', 1) or 1,
                    produto_base=produto_base_obj,
                )
                produto.save()

                # Herdar as tributações (CST/alíquotas por CFOP) do produto base
                for trib in tributacoes_base:
                    trib.pk = None
                    trib.produto = produto
                    trib.save()

                for dim_nome, valor in atributos.items():
                    dim_nome = dim_nome.strip()
                    valor = valor.strip()
                    if not dim_nome or not valor:
                        continue
                    dim, _ = DimensaoVariante.objects.get_or_create(
                        empresa=empresa,
                        nome=dim_nome,
                        defaults={'ordem': 0},
                    )
                    ProdutoAtributo.objects.create(produto=produto, dimensao=dim, valor=valor)

                criados.append({'id': produto.pk, 'nome': produto.nome, 'codigo': produto.codigo})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

    return JsonResponse({
        'success': True,
        'criados': len(criados),
        'erros': erros,
        'produtos': criados,
    })
