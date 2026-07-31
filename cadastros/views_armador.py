"""
Views do módulo Armador e Navio
CRUD completo com integração a APIs (CNPJ, CEP)
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.core.paginator import Paginator
from django.db.models import Q
from core.pagination import paginate
import requests
import re

from .models import (
    Armador, ArmadorEndereco, ArmadorContato, ArmadorDadoBancario,
    Navio
)

from .forms_armador import (
    ArmadorForm, ArmadorEnderecoForm, ArmadorContatoForm, ArmadorDadoBancarioForm,
    NavioForm
)


# ============================================
# ARMADOR - VIEWS CRUD
# ============================================

@login_required
def armador_list(request):
    """Lista de Armadores com filtros"""
    empresa = request.user.empresa
    
    # Filtros
    queryset = Armador.objects.filter(empresa=empresa).select_related('empresa')
    
    search = request.GET.get('search', '')
    if search:
        queryset = queryset.filter(
            Q(nome__icontains=search) |
            Q(nome_fantasia__icontains=search) |
            Q(cnpj__icontains=search) |
            Q(codigo__icontains=search)
        )
    
    ativo_filter = request.GET.get('ativo', '')
    if ativo_filter == 'sim':
        queryset = queryset.filter(ativo=True)
    elif ativo_filter == 'nao':
        queryset = queryset.filter(ativo=False)
    
    # Paginação
    armadores, per_page, per_page_options = paginate(request, queryset)

    context = {
        'armadores': armadores,
        'search': search,
        'ativo_filter': ativo_filter,
        'title': 'Armadores',
        'per_page': per_page,
        'per_page_options': per_page_options,
    }
    return render(request, 'cadastros/armador/list.html', context)


@login_required
def armador_detail(request, pk):
    """Detalhes de um Armador com seus endereços, contatos e dados bancários"""
    empresa = request.user.empresa
    armador = get_object_or_404(Armador, pk=pk, empresa=empresa)
    
    context = {
        'armador': armador,
        'enderecos': armador.enderecos.all(),
        'contatos': armador.contatos.all(),
        'dados_bancarios': armador.dados_bancarios.all(),
        'navios': armador.navios.all(),
        'title': f'Armador: {armador.nome}'
    }
    return render(request, 'cadastros/armador/detail.html', context)


@login_required
def armador_create(request):
    """Criar novo Armador"""
    empresa = request.user.empresa
    
    if request.method == 'POST':
        form = ArmadorForm(request.POST, empresa=empresa, usuario=request.user)
        if form.is_valid():
            armador = form.save()
            messages.success(request, f'Armador {armador.nome} criado com sucesso!')
            return redirect('cadastros:armador_detail', pk=armador.pk)
    else:
        form = ArmadorForm(empresa=empresa, usuario=request.user)
    
    context = {
        'form': form,
        'title': 'Novo Armador',
        'action': 'Criar'
    }
    return render(request, 'cadastros/armador/form.html', context)


@login_required
def armador_update(request, pk):
    """Editar Armador"""
    empresa = request.user.empresa
    armador = get_object_or_404(Armador, pk=pk, empresa=empresa)
    
    if request.method == 'POST':
        form = ArmadorForm(request.POST, instance=armador, empresa=empresa, usuario=request.user)
        if form.is_valid():
            armador = form.save()
            messages.success(request, f'Armador {armador.nome} atualizado com sucesso!')
            return redirect('cadastros:armador_detail', pk=armador.pk)
    else:
        form = ArmadorForm(instance=armador, empresa=empresa, usuario=request.user)
    
    context = {
        'form': form,
        'armador': armador,
        'title': f'Editar: {armador.nome}',
        'action': 'Editar'
    }
    return render(request, 'cadastros/armador/form.html', context)


@login_required
def armador_delete(request, pk):
    """Deletar Armador"""
    empresa = request.user.empresa
    armador = get_object_or_404(Armador, pk=pk, empresa=empresa)
    
    if request.method == 'POST':
        nome = armador.nome
        armador.delete()
        messages.success(request, f'Armador {nome} deletado com sucesso!')
        return redirect('armador_list')
    
    context = {
        'object': armador,
        'title': f'Deletar Armador: {armador.nome}'
    }
    return render(request, 'cadastros/armador/confirm_delete.html', context)


# ============================================
# ARMADOR ENDEREÇO - INLINE VIEWS
# ============================================

@login_required
def armador_endereco_create(request, armador_pk):
    """Criar endereço para Armador"""
    empresa = request.user.empresa
    armador = get_object_or_404(Armador, pk=armador_pk, empresa=empresa)
    
    if request.method == 'POST':
        form = ArmadorEnderecoForm(request.POST)
        if form.is_valid():
            endereco = form.save(commit=False)
            endereco.armador = armador
            endereco.save()
            messages.success(request, 'Endereço adicionado com sucesso!')
            return redirect('cadastros:armador_detail', pk=armador.pk)
    else:
        form = ArmadorEnderecoForm()
    
    context = {
        'form': form,
        'armador': armador,
        'title': f'Novo Endereço - {armador.nome}'
    }
    return render(request, 'cadastros/armador/endereco_form.html', context)


@login_required
def armador_endereco_update(request, pk, armador_pk):
    """Editar endereço do Armador"""
    empresa = request.user.empresa
    armador = get_object_or_404(Armador, pk=armador_pk, empresa=empresa)
    endereco = get_object_or_404(ArmadorEndereco, pk=pk, armador=armador)
    
    if request.method == 'POST':
        form = ArmadorEnderecoForm(request.POST, instance=endereco)
        if form.is_valid():
            form.save()
            messages.success(request, 'Endereço atualizado com sucesso!')
            return redirect('cadastros:armador_detail', pk=armador.pk)
    else:
        form = ArmadorEnderecoForm(instance=endereco)
    
    context = {
        'form': form,
        'armador': armador,
        'endereco': endereco,
        'title': f'Editar Endereço - {armador.nome}'
    }
    return render(request, 'cadastros/armador/endereco_form.html', context)


@login_required
def armador_endereco_delete(request, pk, armador_pk):
    """Deletar endereço do Armador"""
    empresa = request.user.empresa
    armador = get_object_or_404(Armador, pk=armador_pk, empresa=empresa)
    endereco = get_object_or_404(ArmadorEndereco, pk=pk, armador=armador)
    
    if request.method == 'POST':
        endereco.delete()
        messages.success(request, 'Endereço deletado com sucesso!')
        return redirect('cadastros:armador_detail', pk=armador.pk)
    
    context = {
        'endereco': endereco,
        'armador': armador,
        'title': f'Deletar Endereço - {armador.nome}'
    }
    return render(request, 'cadastros/armador/endereco_confirm_delete.html', context)


# ============================================
# ARMADOR CONTATO - INLINE VIEWS
# ============================================

@login_required
def armador_contato_create(request, armador_pk):
    """Criar contato para Armador"""
    empresa = request.user.empresa
    armador = get_object_or_404(Armador, pk=armador_pk, empresa=empresa)
    
    if request.method == 'POST':
        form = ArmadorContatoForm(request.POST)
        if form.is_valid():
            contato = form.save(commit=False)
            contato.armador = armador
            contato.save()
            messages.success(request, 'Contato adicionado com sucesso!')
            return redirect('cadastros:armador_detail', pk=armador.pk)
    else:
        form = ArmadorContatoForm()
    
    context = {
        'form': form,
        'armador': armador,
        'title': f'Novo Contato - {armador.nome}'
    }
    return render(request, 'cadastros/armador/contato_form.html', context)


@login_required
def armador_contato_update(request, pk, armador_pk):
    """Editar contato do Armador"""
    empresa = request.user.empresa
    armador = get_object_or_404(Armador, pk=armador_pk, empresa=empresa)
    contato = get_object_or_404(ArmadorContato, pk=pk, armador=armador)
    
    if request.method == 'POST':
        form = ArmadorContatoForm(request.POST, instance=contato)
        if form.is_valid():
            form.save()
            messages.success(request, 'Contato atualizado com sucesso!')
            return redirect('cadastros:armador_detail', pk=armador.pk)
    else:
        form = ArmadorContatoForm(instance=contato)
    
    context = {
        'form': form,
        'armador': armador,
        'contato': contato,
        'title': f'Editar Contato - {armador.nome}'
    }
    return render(request, 'cadastros/armador/contato_form.html', context)


@login_required
def armador_contato_delete(request, pk, armador_pk):
    """Deletar contato do Armador"""
    empresa = request.user.empresa
    armador = get_object_or_404(Armador, pk=armador_pk, empresa=empresa)
    contato = get_object_or_404(ArmadorContato, pk=pk, armador=armador)
    
    if request.method == 'POST':
        contato.delete()
        messages.success(request, 'Contato deletado com sucesso!')
        return redirect('cadastros:armador_detail', pk=armador.pk)
    
    context = {
        'contato': contato,
        'armador': armador,
        'title': f'Deletar Contato - {armador.nome}'
    }
    return render(request, 'cadastros/armador/contato_confirm_delete.html', context)


# ============================================
# ARMADOR DADO BANCÁRIO - INLINE VIEWS
# ============================================

@login_required
def armador_banco_create(request, armador_pk):
    """Criar dado bancário para Armador"""
    empresa = request.user.empresa
    armador = get_object_or_404(Armador, pk=armador_pk, empresa=empresa)
    
    if request.method == 'POST':
        form = ArmadorDadoBancarioForm(request.POST)
        if form.is_valid():
            banco = form.save(commit=False)
            banco.armador = armador
            banco.save()
            messages.success(request, 'Dado bancário adicionado com sucesso!')
            return redirect('cadastros:armador_detail', pk=armador.pk)
    else:
        form = ArmadorDadoBancarioForm()
    
    context = {
        'form': form,
        'armador': armador,
        'title': f'Novo Dado Bancário - {armador.nome}'
    }
    return render(request, 'cadastros/armador/banco_form.html', context)


@login_required
def armador_banco_update(request, pk, armador_pk):
    """Editar dado bancário do Armador"""
    empresa = request.user.empresa
    armador = get_object_or_404(Armador, pk=armador_pk, empresa=empresa)
    banco = get_object_or_404(ArmadorDadoBancario, pk=pk, armador=armador)
    
    if request.method == 'POST':
        form = ArmadorDadoBancarioForm(request.POST, instance=banco)
        if form.is_valid():
            form.save()
            messages.success(request, 'Dado bancário atualizado com sucesso!')
            return redirect('cadastros:armador_detail', pk=armador.pk)
    else:
        form = ArmadorDadoBancarioForm(instance=banco)
    
    context = {
        'form': form,
        'armador': armador,
        'banco': banco,
        'title': f'Editar Dado Bancário - {armador.nome}'
    }
    return render(request, 'cadastros/armador/banco_form.html', context)


@login_required
def armador_banco_delete(request, pk, armador_pk):
    """Deletar dado bancário do Armador"""
    empresa = request.user.empresa
    armador = get_object_or_404(Armador, pk=armador_pk, empresa=empresa)
    banco = get_object_or_404(ArmadorDadoBancario, pk=pk, armador=armador)
    
    if request.method == 'POST':
        banco.delete()
        messages.success(request, 'Dado bancário deletado com sucesso!')
        return redirect('cadastros:armador_detail', pk=armador.pk)
    
    context = {
        'banco': banco,
        'armador': armador,
        'title': f'Deletar Dado Bancário - {armador.nome}'
    }
    return render(request, 'cadastros/armador/banco_confirm_delete.html', context)


# ============================================
# NAVIO - VIEWS CRUD
# ============================================

@login_required
def navio_list(request):
    """Lista de Navios com filtros"""
    empresa = request.user.empresa
    
    queryset = Navio.objects.filter(empresa=empresa).select_related('empresa', 'armador')
    
    search = request.GET.get('search', '')
    if search:
        queryset = queryset.filter(
            Q(nome__icontains=search) |
            Q(codigo__icontains=search) |
            Q(imo__icontains=search) |
            Q(armador__nome__icontains=search)
        )
    
    status_filter = request.GET.get('status', '')
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    ativo_filter = request.GET.get('ativo', '')
    if ativo_filter == 'sim':
        queryset = queryset.filter(ativo=True)
    elif ativo_filter == 'nao':
        queryset = queryset.filter(ativo=False)
    
    # Paginação
    navios, per_page, per_page_options = paginate(request, queryset)

    context = {
        'navios': navios,
        'search': search,
        'status_filter': status_filter,
        'ativo_filter': ativo_filter,
        'title': 'Navios',
        'per_page': per_page,
        'per_page_options': per_page_options,
    }
    return render(request, 'cadastros/navio/list.html', context)


@login_required
def navio_detail(request, pk):
    """Detalhes de um Navio"""
    empresa = request.user.empresa
    navio = get_object_or_404(Navio, pk=pk, empresa=empresa)
    
    context = {
        'navio': navio,
        'portos': navio.portos_operacao.all(),
        'title': f'Navio: {navio.nome}'
    }
    return render(request, 'cadastros/navio/detail.html', context)


@login_required
def navio_create(request):
    """Criar novo Navio"""
    empresa = request.user.empresa
    
    if request.method == 'POST':
        form = NavioForm(request.POST, empresa=empresa)
        if form.is_valid():
            navio = form.save()
            messages.success(request, f'Navio {navio.nome} criado com sucesso!')
            return redirect('cadastros:navio_detail', pk=navio.pk)
    else:
        form = NavioForm(empresa=empresa)
    
    context = {
        'form': form,
        'title': 'Novo Navio',
        'action': 'Criar'
    }
    return render(request, 'cadastros/navio/form.html', context)


@login_required
def navio_update(request, pk):
    """Editar Navio"""
    empresa = request.user.empresa
    navio = get_object_or_404(Navio, pk=pk, empresa=empresa)
    
    if request.method == 'POST':
        form = NavioForm(request.POST, instance=navio, empresa=empresa)
        if form.is_valid():
            navio = form.save()
            messages.success(request, f'Navio {navio.nome} atualizado com sucesso!')
            return redirect('cadastros:navio_detail', pk=navio.pk)
    else:
        form = NavioForm(instance=navio, empresa=empresa)
    
    context = {
        'form': form,
        'navio': navio,
        'title': f'Editar: {navio.nome}',
        'action': 'Editar'
    }
    return render(request, 'cadastros/navio/form.html', context)


@login_required
def navio_delete(request, pk):
    """Deletar Navio"""
    empresa = request.user.empresa
    navio = get_object_or_404(Navio, pk=pk, empresa=empresa)
    
    if request.method == 'POST':
        nome = navio.nome
        navio.delete()
        messages.success(request, f'Navio {nome} deletado com sucesso!')
        return redirect('navio_list')
    
    context = {
        'object': navio,
        'title': f'Deletar Navio: {navio.nome}'
    }
    return render(request, 'cadastros/navio/confirm_delete.html', context)
