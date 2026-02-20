from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
import json
from decimal import Decimal
from .models import UnidadeMedida, Categoria, SubCategoria, Produto, ProdutoTributacao, NaturezaOperacao, ProdutoDefensivoCultura, ProdutoFornecedor
from .forms import UnidadeMedidaForm, CategoriaForm, SubCategoriaForm, ProdutoForm, ProdutoTributacaoForm, NaturezaOperacaoForm, ProdutoDefensivoCulturaForm
from cadastros.models import NCM, CFOP, Fornecedor


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
    status_filter = request.GET.get('status', '')
    
    produtos = Produto.objects.select_related('categoria', 'unidade_medida', 'ncm').filter(categoria__empresa=request.user.empresa)
    
    if query:
        produtos = produtos.filter(
            Q(codigo__icontains=query) |
            Q(nome__icontains=query) |
            Q(codigo_barras__icontains=query) |
            Q(categoria__nome__icontains=query)
        )
    
    if categoria_filter:
        produtos = produtos.filter(categoria_id=categoria_filter)
    
    if status_filter == 'ativo':
        produtos = produtos.filter(ativo=True)
    elif status_filter == 'inativo':
        produtos = produtos.filter(ativo=False)
    
    categorias = Categoria.objects.filter(empresa=request.user.empresa).order_by('nome')
    
    # Paginação
    try:
        per_page = int(request.GET.get('per_page', 25))
    except (TypeError, ValueError):
        per_page = 25
    if per_page not in (10, 25, 50, 100):
        per_page = 25
    
    paginator = Paginator(produtos.order_by('nome'), per_page)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    return render(request, 'produtos/produto/produto_list.html', {
        'page_obj': page_obj,
        'categorias': categorias,
        'query': query,
        'categoria_filter': categoria_filter,
        'status_filter': status_filter,
        'per_page': per_page,
    })


@login_required
def produto_detail(request, pk):
    produto = get_object_or_404(
        Produto.objects.select_related(
            'categoria', 'subcategoria', 'unidade_medida', 
            'unidade_compra', 'unidade_venda', 'ncm', 'fornecedor_padrao'
        ).prefetch_related('tributacoes').filter(categoria__empresa=request.user.empresa),
        pk=pk
    )
    return render(request, 'produtos/produto/produto_detail.html', {
        'produto': produto
    })


@login_required
def produto_create(request):
    if request.method == 'POST':
        form = ProdutoForm(request.POST, request.FILES, empresa=request.user.empresa)
        if form.is_valid():
            form.save()
            messages.success(request, 'Produto cadastrado com sucesso!')
            return redirect('produtos:produto_list')
    else:
        form = ProdutoForm(empresa=request.user.empresa)
    return render(request, 'produtos/produto/produto_form.html', {
        'form': form,
        'action': 'Cadastrar'
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
    
    return render(request, 'produtos/produto/produto_form.html', {
        'form': form,
        'action': 'Editar',
        'object': produto,
        'culturas': culturas,
        'pragas': pragas,
        'unidades_dosagem': unidades,
        'fornecedores': fornecedores,
        'fornecedores_produto': fornecedores_produto,
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
    has_recebimentos = produto.itemrecebimento_set.exists()
    
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

@login_required
def produtotributacao_create(request, produto_id):
    produto = get_object_or_404(Produto.objects.filter(categoria__empresa=request.user.empresa), pk=produto_id)
    if request.method == 'POST':
        form = ProdutoTributacaoForm(request.POST, empresa=request.user.empresa)
        if form.is_valid():
            tributacao = form.save(commit=False)
            tributacao.produto = produto
            tributacao.save()
            messages.success(request, 'Tributação cadastrada com sucesso!')
            return redirect('produtos:produto_detail', pk=produto.pk)
    else:
        form = ProdutoTributacaoForm(initial={'produto': produto}, empresa=request.user.empresa)
    return render(request, 'produtos/tributacao/tributacao_form.html', {
        'form': form,
        'produto': produto,
        'action': 'Cadastrar'
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
    return render(request, 'produtos/tributacao/tributacao_form.html', {
        'form': form,
        'produto': tributacao.produto,
        'action': 'Editar'
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
            
            if not sigla or not nome:
                return JsonResponse({
                    'success': False,
                    'error': 'Sigla e nome são obrigatórios'
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
                nome=nome
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
            cfop = CFOP.objects.filter(codigo=codigo, ativo=True).first()
            if cfop:
                return JsonResponse({
                    'success': True, 
                    'id': cfop.id, 
                    'codigo': cfop.codigo, 
                    'nome': cfop.nome,
                    'descricao': cfop.nome  # Retornar nome como descricao para compatibilidade
                })
            else:
                return JsonResponse({'success': False, 'error': 'CFOP nao encontrado'}, status=404)
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
