"""
Views do módulo Motorista
CRUD completo para motoristas próprios e terceirizados
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from .models import Motorista, MotoristadoDocumento
from .forms_motorista import MotoristadoForm, MotoristadoDocumentoForm
import requests
from django.core.cache import cache


@login_required
def motorista_list(request):
    """Lista de motoristas com filtros"""
    empresa = request.user.empresa
    motoristas = Motorista.objects.filter(empresa=empresa)
    
    # Filtros
    search = request.GET.get('search', '')
    tipo = request.GET.get('tipo', '')
    ativo = request.GET.get('ativo', '')
    transportadora = request.GET.get('transportadora', '')
    
    if search:
        motoristas = motoristas.filter(
            models.Q(nome__icontains=search) | 
            models.Q(cpf__icontains=search) | 
            models.Q(cnh__icontains=search)
        )
    
    if tipo:
        motoristas = motoristas.filter(tipo=tipo)
    
    if ativo:
        motoristas = motoristas.filter(ativo=ativo == '1')
    
    if transportadora:
        motoristas = motoristas.filter(transportadora_id=transportadora)
    
    # Paginação
    paginator = Paginator(motoristas, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'motoristas': page_obj.object_list,
        'search': search,
        'tipo': tipo,
        'is_paginated': page_obj.has_other_pages(),
    }
    
    return render(request, 'cadastros/motorista/list.html', context)


@login_required
def motorista_create(request):
    """Criar novo motorista"""
    empresa = request.user.empresa
    
    if request.method == 'POST':
        form = MotoristadoForm(request.POST, request.FILES, empresa=empresa)
        if form.is_valid():
            motorista = form.save()
            messages.success(request, f'Motorista {motorista.nome} criado com sucesso!')
            return redirect('cadastros:motorista_detail', pk=motorista.pk)
    else:
        form = MotoristadoForm(empresa=empresa)
    
    context = {
        'form': form,
        'title': 'Novo Motorista',
        'action': 'Criar'
    }
    return render(request, 'cadastros/motorista/form.html', context)


@login_required
def motorista_detail(request, pk):
    """Detalhe do motorista"""
    empresa = request.user.empresa
    motorista = get_object_or_404(Motorista, pk=pk, empresa=empresa)
    
    context = {
        'motorista': motorista,
        'documentos': motorista.documentos.all(),
    }
    return render(request, 'cadastros/motorista/detail.html', context)


@login_required
def motorista_update(request, pk):
    """Editar motorista"""
    empresa = request.user.empresa
    motorista = get_object_or_404(Motorista, pk=pk, empresa=empresa)
    
    if request.method == 'POST':
        form = MotoristadoForm(request.POST, request.FILES, instance=motorista, empresa=empresa)
        if form.is_valid():
            motorista = form.save()
            messages.success(request, f'Motorista {motorista.nome} atualizado com sucesso!')
            return redirect('cadastros:motorista_detail', pk=motorista.pk)
    else:
        form = MotoristadoForm(instance=motorista, empresa=empresa)
    
    context = {
        'form': form,
        'motorista': motorista,
        'title': f'Editar: {motorista.nome}',
        'action': 'Editar'
    }
    return render(request, 'cadastros/motorista/form.html', context)


@login_required
def motorista_delete(request, pk):
    """Deletar motorista"""
    empresa = request.user.empresa
    motorista = get_object_or_404(Motorista, pk=pk, empresa=empresa)
    
    if request.method == 'POST':
        nome = motorista.nome
        motorista.delete()
        messages.success(request, f'Motorista {nome} deletado com sucesso!')
        return redirect('cadastros:motorista_list')
    
    context = {
        'motorista': motorista,
        'title': 'Deletar Motorista',
    }
    return render(request, 'cadastros/motorista/confirm_delete.html', context)


# ========== DOCUMENTOS DO MOTORISTA ==========

@login_required
def motorista_documento_create(request, motorista_pk):
    """Adicionar documento ao motorista"""
    empresa = request.user.empresa
    motorista = get_object_or_404(Motorista, pk=motorista_pk, empresa=empresa)
    
    if request.method == 'POST':
        form = MotoristadoDocumentoForm(request.POST, request.FILES)
        if form.is_valid():
            documento = form.save(commit=False)
            documento.motorista = motorista
            documento.save()
            messages.success(request, 'Documento adicionado com sucesso!')
            return redirect('cadastros:motorista_detail', pk=motorista.pk)
    else:
        form = MotoristadoDocumentoForm()
    
    context = {
        'form': form,
        'motorista': motorista,
        'title': 'Adicionar Documento',
    }
    return render(request, 'cadastros/motorista/documento_form.html', context)


@login_required
def motorista_documento_delete(request, motorista_pk, documento_pk):
    """Deletar documento do motorista"""
    empresa = request.user.empresa
    motorista = get_object_or_404(Motorista, pk=motorista_pk, empresa=empresa)
    documento = get_object_or_404(MotoristadoDocumento, pk=documento_pk, motorista=motorista)
    
    if request.method == 'POST':
        documento.delete()
        messages.success(request, 'Documento deletado com sucesso!')
        return redirect('cadastros:motorista_detail', pk=motorista.pk)
    
    context = {
        'documento': documento,
        'motorista': motorista,
        'title': 'Deletar Documento',
    }
    return render(request, 'cadastros/motorista/documento_confirm_delete.html', context)


# ========== API DE CEP ==========

@login_required
@require_http_methods(["GET"])
def buscar_cep_motorista(request):
    """API para buscar endereço via CEP"""
    cep = request.GET.get('cep', '').strip()
    
    if not cep or len(cep) < 8:
        return JsonResponse({'erro': 'CEP inválido'}, status=400)
    
    try:
        # Verificar cache
        cache_key = f'cep_{cep}'
        resultado = cache.get(cache_key)
        
        if not resultado:
            # Tentar ViaCEP primeiro
            try:
                response = requests.get(
                    f'https://viacep.com.br/ws/{cep}/json/',
                    timeout=5
                )
                response.raise_for_status()
                data = response.json()
                
                if 'erro' not in data:
                    resultado = {
                        'logradouro': data.get('logradouro', ''),
                        'bairro': data.get('bairro', ''),
                        'cidade': data.get('localidade', ''),
                        'uf': data.get('uf', ''),
                    }
            except (requests.RequestException, ValueError):
                # Fallback para Brasil API
                try:
                    response = requests.get(
                        f'https://brasilapi.com.br/api/address/v2/{cep}',
                        timeout=5
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    resultado = {
                        'logradouro': data.get('street', ''),
                        'bairro': data.get('neighborhood', ''),
                        'cidade': data.get('city', ''),
                        'uf': data.get('state', ''),
                    }
                except (requests.RequestException, ValueError):
                    return JsonResponse(
                        {'erro': 'CEP não encontrado em nenhuma base de dados'},
                        status=404
                    )
        
        if resultado:
            cache.set(cache_key, resultado, 86400)  # 24 horas
            return JsonResponse(resultado)
        else:
            return JsonResponse({'erro': 'CEP não encontrado'}, status=404)
    
    except Exception as e:
        return JsonResponse({'erro': str(e)}, status=500)


from django.db import models
