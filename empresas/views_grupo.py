"""
Views para Grupo Corporativo (Enterprise Plus)
CRUD completo de grupos corporativos, gerenciamento de empresas
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.db.models import Q, Count
from django.http import JsonResponse
from decimal import Decimal

from .models import GrupoCorporativo, Empresa, Plano
from .forms_grupo import GrupoCorporativoForm, EmpresaGrupoForm, AdicionarEmpresasAoGrupoForm


# ========== FUNÇÃO-BASED VIEWS ==========

@login_required
def grupo_list(request):
    """Lista de grupos corporativos"""
    if request.user.is_superuser or request.user.is_staff:
        grupos = GrupoCorporativo.objects.all()
    else:
        grupos = GrupoCorporativo.objects.filter(administrador=request.user)
    
    grupos = grupos.annotate(
        num_empresas=Count('empresas')
    )
    
    context = {
        'grupos': grupos,
        'titulo': 'Grupos Corporativos',
    }
    return render(request, 'empresas/grupo/grupo_list.html', context)


@login_required
def grupo_detail(request, pk):
    """Detalhes de um grupo corporativo"""
    grupo = get_object_or_404(GrupoCorporativo, pk=pk)
    
    # Verificar permissão
    if not (request.user.is_superuser or grupo.administrador == request.user):
        messages.error(request, '❌ Você não possui permissão para acessar este grupo')
        return redirect('empresas:grupo_list')
    
    empresas = grupo.empresas.all()
    
    # Calcular consolidados
    total_usuarios = 0
    total_fazendas = 0
    total_produtos = 0
    
    for empresa in empresas:
        total_usuarios += empresa.limite_usuarios
        total_fazendas += empresa.limite_fazendas
        total_produtos += empresa.limite_produtos
    
    context = {
        'grupo': grupo,
        'empresas': empresas,
        'total_usuarios': total_usuarios,
        'total_fazendas': total_fazendas,
        'total_produtos': total_produtos,
        'num_empresas': empresas.count(),
    }
    return render(request, 'empresas/grupo/grupo_detail.html', context)


@login_required
def grupo_create(request):
    """Criar novo grupo corporativo"""
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, '❌ Você não possui permissão para criar grupos')
        return redirect('empresas:grupo_list')
    
    if request.method == 'POST':
        form = GrupoCorporativoForm(request.POST, request.FILES)
        if form.is_valid():
            grupo = form.save()
            messages.success(request, f'✅ Grupo "{grupo.nome}" criado com sucesso!')
            return redirect('empresas:grupo_detail', pk=grupo.pk)
    else:
        form = GrupoCorporativoForm()
    
    context = {
        'form': form,
        'titulo': 'Novo Grupo Corporativo',
        'action': 'Criar',
    }
    return render(request, 'empresas/grupo/grupo_form.html', context)


@login_required
def grupo_update(request, pk):
    """Editar grupo corporativo"""
    grupo = get_object_or_404(GrupoCorporativo, pk=pk)
    
    # Verificar permissão
    if not (request.user.is_superuser or grupo.administrador == request.user):
        messages.error(request, '❌ Você não possui permissão para editar este grupo')
        return redirect('empresas:grupo_detail', pk=grupo.pk)
    
    if request.method == 'POST':
        form = GrupoCorporativoForm(request.POST, request.FILES, instance=grupo)
        if form.is_valid():
            grupo = form.save()
            messages.success(request, f'✅ Grupo "{grupo.nome}" atualizado!')
            return redirect('empresas:grupo_detail', pk=grupo.pk)
    else:
        form = GrupoCorporativoForm(instance=grupo)
    
    context = {
        'form': form,
        'grupo': grupo,
        'titulo': f'Editar {grupo.nome}',
        'action': 'Editar',
    }
    return render(request, 'empresas/grupo/grupo_form.html', context)


@login_required
def grupo_delete(request, pk):
    """Deletar grupo corporativo"""
    grupo = get_object_or_404(GrupoCorporativo, pk=pk)
    
    # Verificar permissão
    if not (request.user.is_superuser or grupo.administrador == request.user):
        messages.error(request, '❌ Você não possui permissão para deletar este grupo')
        return redirect('empresas:grupo_detail', pk=grupo.pk)
    
    # Não permitir deletar se houver empresas vinculadas
    if grupo.empresas.exists():
        messages.error(request, f'❌ Não é possível deletar "{grupo.nome}" pois possui empresas vinculadas')
        return redirect('empresas:grupo_detail', pk=grupo.pk)
    
    if request.method == 'POST':
        nome = grupo.nome
        grupo.delete()
        messages.success(request, f'🗑️ Grupo "{nome}" deletado com sucesso!')
        return redirect('empresas:grupo_list')
    
    context = {
        'grupo': grupo,
        'titulo': f'Deletar {grupo.nome}',
    }
    return render(request, 'empresas/grupo/grupo_confirm_delete.html', context)


@login_required
def grupo_adicionar_empresas(request, pk):
    """Adicionar empresas a um grupo"""
    grupo = get_object_or_404(GrupoCorporativo, pk=pk)
    
    # Verificar permissão
    if not (request.user.is_superuser or grupo.administrador == request.user):
        messages.error(request, '❌ Você não possui permissão para gerenciar este grupo')
        return redirect('empresas:grupo_detail', pk=grupo.pk)
    
    if request.method == 'POST':
        form = AdicionarEmpresasAoGrupoForm(request.POST, grupo_id=pk)
        if form.is_valid():
            empresas = form.cleaned_data['empresas']
            empresas.update(grupo_corporativo=grupo)
            messages.success(request, f'✅ {empresas.count()} empresa(s) adicionada(s) ao grupo!')
            return redirect('empresas:grupo_detail', pk=grupo.pk)
    else:
        form = AdicionarEmpresasAoGrupoForm(grupo_id=pk)
    
    context = {
        'form': form,
        'grupo': grupo,
        'titulo': f'Adicionar Empresas a {grupo.nome}',
    }
    return render(request, 'empresas/grupo/grupo_adicionar_empresas.html', context)


@login_required
def remover_empresa_do_grupo(request, grupo_id, empresa_id):
    """Remover empresa de um grupo"""
    grupo = get_object_or_404(GrupoCorporativo, pk=grupo_id)
    empresa = get_object_or_404(Empresa, pk=empresa_id)
    
    # Verificar permissão
    if not (request.user.is_superuser or grupo.administrador == request.user):
        return JsonResponse({'success': False, 'error': 'Sem permissão'}, status=403)
    
    # Verificar se empresa pertence ao grupo
    if empresa.grupo_corporativo != grupo:
        return JsonResponse({'success': False, 'error': 'Empresa não pertence a este grupo'}, status=400)
    
    if request.method == 'POST':
        empresa.grupo_corporativo = None
        empresa.save()
        messages.success(request, f'✅ Empresa "{empresa.nome}" removida do grupo')
        return redirect('empresas:grupo_detail', pk=grupo.pk)
    
    context = {
        'grupo': grupo,
        'empresa': empresa,
        'titulo': f'Remover {empresa.nome} do grupo',
    }
    return render(request, 'empresas/grupo/grupo_remover_empresa.html', context)


@login_required
def grupo_relatorio_consolidado(request, pk):
    """Relatório consolidado do grupo corporativo"""
    grupo = get_object_or_404(GrupoCorporativo, pk=pk)
    
    # Verificar permissão
    if not (request.user.is_superuser or grupo.administrador == request.user):
        messages.error(request, '❌ Você não possui permissão para acessar este relatório')
        return redirect('empresas:grupo_list')
    
    empresas = grupo.empresas.filter(ativa=True)
    
    # Agregações
    consolidado = {
        'num_empresas': empresas.count(),
        'num_usuarios': sum(e.limite_usuarios for e in empresas),
        'num_fazendas': sum(e.limite_fazendas for e in empresas),
        'num_produtos': sum(e.limite_produtos for e in empresas),
        'total_planos': Plano.objects.count(),
        'empresas': empresas.values('nome', 'cnpj', 'email', 'plano', 'ativa'),
    }
    
    from django.utils import timezone
    context = {
        'grupo': grupo,
        'consolidado': consolidado,
        'titulo': f'Relatório Consolidado - {grupo.nome}',
        'now': timezone.now(),
    }
    return render(request, 'empresas/grupo/grupo_relatorio.html', context)


def ajuda_grupos_corporativos(request):
    """Página de ajuda para Grupos Corporativos"""
    context = {
        'titulo': 'Ajuda - Grupos Corporativos',
    }
    return render(request, 'empresas/grupo/ajuda_grupos_corporativos.html', context)


def ajuda_usuarios_grupos(request):
    """Página de ajuda para Usuários e Grupos Corporativos"""
    context = {
        'titulo': 'Ajuda - Usuários e Grupos Corporativos',
    }
    return render(request, 'empresas/ajuda_usuarios_grupos.html', context)
