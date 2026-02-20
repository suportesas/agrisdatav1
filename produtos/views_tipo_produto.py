"""
Views para CRUD de Tipos de Produto
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .models import TipoProduto
from .forms import TipoProdutoForm


@login_required
def tipo_produto_list(request):
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        messages.error(request, 'Usuario sem empresa vinculada.')
        return redirect('dashboard:index')
    
    qs = TipoProduto.objects.filter(empresa=empresa)
    search = request.GET.get('search', '').strip()
    
    if search:
        qs = qs.filter(
            Q(nome__icontains=search) |
            Q(codigo__icontains=search)
        )
    
    qs = qs.order_by('nome')
    
    paginator = Paginator(qs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'produtos/tipo_produto/list.html', {
        'tipos': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'search': search,
    })


@login_required
def tipo_produto_create(request):
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        messages.error(request, 'Usuario sem empresa vinculada.')
        return redirect('dashboard:index')
    
    if request.method == 'POST':
        form = TipoProdutoForm(request.POST, empresa=empresa)
        if form.is_valid():
            tipo = form.save(commit=False)
            tipo.empresa = empresa
            tipo.save()
            messages.success(request, 'Tipo de produto criado com sucesso.')
            return redirect('produtos:tipo_produto_list')
    else:
        form = TipoProdutoForm(empresa=empresa)
    
    return render(request, 'produtos/tipo_produto/form.html', {
        'form': form,
        'titulo': 'Novo Tipo de Produto',
    })


@login_required
def tipo_produto_update(request, pk):
    empresa = getattr(request.user, 'empresa', None)
    tipo = get_object_or_404(TipoProduto, pk=pk, empresa=empresa)
    
    if request.method == 'POST':
        form = TipoProdutoForm(request.POST, instance=tipo, empresa=empresa)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tipo de produto atualizado com sucesso.')
            return redirect('produtos:tipo_produto_list')
    else:
        form = TipoProdutoForm(instance=tipo, empresa=empresa)
    
    return render(request, 'produtos/tipo_produto/form.html', {
        'form': form,
        'titulo': f'Editar Tipo: {tipo.nome}',
        'tipo': tipo,
    })


@login_required
def tipo_produto_delete(request, pk):
    empresa = getattr(request.user, 'empresa', None)
    tipo = get_object_or_404(TipoProduto, pk=pk, empresa=empresa)
    
    if request.method == 'POST':
        try:
            nome = tipo.nome
            tipo.delete()
            messages.success(request, f'Tipo "{nome}" excluido com sucesso.')
        except Exception as e:
            messages.error(request, f'Erro ao excluir: {str(e)}')
        return redirect('produtos:tipo_produto_list')
    
    return render(request, 'produtos/tipo_produto/confirm_delete.html', {
        'tipo': tipo,
    })


@login_required
def tipo_produto_listar_ajax(request):
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'success': False, 'tipos': []})

    tipos = TipoProduto.objects.filter(empresa=empresa, ativo=True).order_by('nome')
    return JsonResponse({
        'success': True,
        'tipos': [
            {
                'id': tipo.id,
                'nome': tipo.nome,
                'codigo': tipo.codigo,
                'label': f'{tipo.nome} ({tipo.codigo})',
            }
            for tipo in tipos
        ]
    })
