"""
Views do módulo Motorista
CRUD completo para motoristas próprios e terceirizados
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.template.loader import render_to_string
from .models import Motorista, MotoristadoDocumento, MotoristaVinculoPlaca
from .forms_motorista import MotoristadoForm, MotoristadoDocumentoForm, MotoristaVinculoPlacaForm, MotoristaVinculoConsultaForm
import requests
from django.core.cache import cache
from io import BytesIO


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
            return redirect('frota:motorista_detail', pk=motorista.pk)
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
            return redirect('frota:motorista_detail', pk=motorista.pk)
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
def motorista_vinculo_list(request):
    """Lista de vinculos motorista x placa"""
    empresa = request.user.empresa
    vinculos = MotoristaVinculoPlaca.objects.filter(empresa=empresa).select_related(
        'motorista', 'placa_principal', 'placa_principal__vehicle'
    ).prefetch_related('reboques')

    search = request.GET.get('search', '')
    status = request.GET.get('status', '')

    if search:
        vinculos = vinculos.filter(
            models.Q(motorista__nome__icontains=search) |
            models.Q(placa_principal__placa__icontains=search) |
            models.Q(reboques__placa__icontains=search)
        ).distinct()

    if status == 'ATIVO':
        vinculos = vinculos.filter(ativo=True)
    elif status == 'ENCERRADO':
        vinculos = vinculos.filter(ativo=False)

    paginator = Paginator(vinculos, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'vinculos': page_obj.object_list,
        'search': search,
        'status': status,
        'is_paginated': page_obj.has_other_pages(),
    }

    return render(request, 'cadastros/motorista_vinculo/list.html', context)


@login_required
def motorista_vinculo_create(request):
    """Criar vinculo motorista x placa"""
    empresa = request.user.empresa

    if request.method == 'POST':
        form = MotoristaVinculoPlacaForm(request.POST, empresa=empresa)
        if form.is_valid():
            vinculo = form.save()
            messages.success(request, 'Vinculo criado com sucesso!')
            return redirect('frota:motorista_vinculo_detail', pk=vinculo.pk)
    else:
        form = MotoristaVinculoPlacaForm(empresa=empresa)

    context = {
        'form': form,
        'title': 'Novo Vinculo',
        'action': 'Criar'
    }
    return render(request, 'cadastros/motorista_vinculo/form.html', context)


@login_required
def motorista_vinculo_detail(request, pk):
    """Detalhe do vinculo"""
    empresa = request.user.empresa
    vinculo = get_object_or_404(MotoristaVinculoPlaca, pk=pk, empresa=empresa)
    context = {
        'vinculo': vinculo,
        'reboques': vinculo.reboques.all(),
    }
    return render(request, 'cadastros/motorista_vinculo/detail.html', context)


@login_required
def motorista_vinculo_update(request, pk):
    """Editar vinculo motorista x placa"""
    empresa = request.user.empresa
    vinculo = get_object_or_404(MotoristaVinculoPlaca, pk=pk, empresa=empresa)

    if request.method == 'POST':
        form = MotoristaVinculoPlacaForm(request.POST, instance=vinculo, empresa=empresa)
        if form.is_valid():
            form.save()
            messages.success(request, 'Vinculo atualizado com sucesso!')
            return redirect('frota:motorista_vinculo_detail', pk=vinculo.pk)
    else:
        form = MotoristaVinculoPlacaForm(instance=vinculo, empresa=empresa)

    context = {
        'form': form,
        'vinculo': vinculo,
        'title': 'Editar Vinculo',
        'action': 'Salvar'
    }
    return render(request, 'cadastros/motorista_vinculo/form.html', context)


@login_required
def motorista_delete(request, pk):
    """Deletar motorista"""
    empresa = request.user.empresa
    motorista = get_object_or_404(Motorista, pk=pk, empresa=empresa)
    
    if request.method == 'POST':
        nome = motorista.nome
        motorista.delete()
        messages.success(request, f'Motorista {nome} deletado com sucesso!')
        return redirect('frota:motorista_list')
    
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
            return redirect('frota:motorista_detail', pk=motorista.pk)
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
        return redirect('frota:motorista_detail', pk=motorista.pk)
    
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


# ===========================
# CONSULTA DE VÍNCULOS HISTÓRICOS
# ===========================

@login_required
def motorista_vinculo_consulta(request):
    """
    Painel de consulta histórica de vínculos Motorista x Placa
    Permite buscar:
    1. Placa + Data: Quem estava com determinada placa em certa data (para multas)
    2. Motorista + Período: Quais placas um motorista operou em determinado período
    """
    empresa = request.user.empresa
    form = MotoristaVinculoConsultaForm(empresa=empresa)
    resultados = []
    consulta_realizada = False
    tipo_consulta = None
    parametros = {}
    
    if request.method == 'POST':
        form = MotoristaVinculoConsultaForm(request.POST, empresa=empresa)
        
        if form.is_valid():
            consulta_realizada = True
            tipo_consulta = form.cleaned_data['tipo_consulta']
            
            if tipo_consulta == 'placa_data':
                # Consulta: Quem estava com a placa na data?
                placa = form.cleaned_data['placa']
                data_ref = form.cleaned_data['data_referencia']
                
                parametros = {
                    'placa': placa,
                    'data_referencia': data_ref
                }
                
                # Buscar vínculos que cobrem esta data
                # Vínculo cobre se: data_inicio <= data_ref E (data_fim >= data_ref OU data_fim é NULL)
                resultados = MotoristaVinculoPlaca.objects.filter(
                    empresa=empresa,
                    ativo=True,
                    data_inicio__lte=data_ref
                ).filter(
                    Q(data_fim__gte=data_ref) | Q(data_fim__isnull=True)
                ).filter(
                    Q(placa_principal=placa) | Q(reboques=placa)
                ).select_related('motorista', 'placa_principal').prefetch_related('reboques').distinct()
                
            elif tipo_consulta == 'motorista_periodo':
                # Consulta: Quais placas o motorista operou no período?
                motorista = form.cleaned_data['motorista']
                data_inicio = form.cleaned_data['data_inicio']
                data_fim = form.cleaned_data.get('data_fim')
                
                parametros = {
                    'motorista': motorista,
                    'data_inicio': data_inicio,
                    'data_fim': data_fim
                }
                
                # Buscar vínculos que se sobrepõem ao período consultado
                vinculos_filter = MotoristaVinculoPlaca.objects.filter(
                    empresa=empresa,
                    ativo=True,
                    motorista=motorista,
                    data_inicio__lte=data_fim if data_fim else timezone.now().date()
                ).filter(
                    Q(data_fim__gte=data_inicio) | Q(data_fim__isnull=True)
                )
                
                resultados = vinculos_filter.select_related('motorista', 'placa_principal').prefetch_related('reboques').order_by('-data_inicio')
    
    context = {
        'form': form,
        'resultados': resultados,
        'consulta_realizada': consulta_realizada,
        'tipo_consulta': tipo_consulta,
        'parametros': parametros,
        'total_resultados': len(resultados) if resultados else 0,
    }
    
    return render(request, 'cadastros/motorista_vinculo/consulta.html', context)


@login_required
def motorista_vinculo_consulta_pdf(request):
    """
    Exporta resultado da consulta em PDF
    """
    empresa = request.user.empresa
    form = MotoristaVinculoConsultaForm(request.GET, empresa=empresa)
    
    if not form.is_valid():
        messages.error(request, 'Parâmetros de consulta inválidos.')
        return redirect('frota:motorista_vinculo_consulta')
    
    tipo_consulta = form.cleaned_data['tipo_consulta']
    resultados = []
    parametros = {}
    
    if tipo_consulta == 'placa_data':
        placa = form.cleaned_data['placa']
        data_ref = form.cleaned_data['data_referencia']
        
        parametros = {
            'placa': placa,
            'data_referencia': data_ref
        }
        
        resultados = MotoristaVinculoPlaca.objects.filter(
            empresa=empresa,
            ativo=True,
            data_inicio__lte=data_ref
        ).filter(
            Q(data_fim__gte=data_ref) | Q(data_fim__isnull=True)
        ).filter(
            Q(placa_principal=placa) | Q(reboques=placa)
        ).select_related('motorista', 'placa_principal').prefetch_related('reboques').distinct()
        
    elif tipo_consulta == 'motorista_periodo':
        motorista = form.cleaned_data['motorista']
        data_inicio = form.cleaned_data['data_inicio']
        data_fim = form.cleaned_data.get('data_fim')
        
        parametros = {
            'motorista': motorista,
            'data_inicio': data_inicio,
            'data_fim': data_fim
        }
        
        vinculos_filter = MotoristaVinculoPlaca.objects.filter(
            empresa=empresa,
            ativo=True,
            motorista=motorista,
            data_inicio__lte=data_fim if data_fim else timezone.now().date()
        ).filter(
            Q(data_fim__gte=data_inicio) | Q(data_fim__isnull=True)
        )
        
        resultados = vinculos_filter.select_related('motorista', 'placa_principal').prefetch_related('reboques').order_by('-data_inicio')
    
    # Renderizar HTML
    html_string = render_to_string('cadastros/motorista_vinculo/consulta_pdf.html', {
        'empresa': empresa,
        'tipo_consulta': tipo_consulta,
        'parametros': parametros,
        'resultados': resultados,
        'total_resultados': len(resultados),
        'data_geracao': timezone.now()
    })

    # Import tardio para evitar falha no carregamento global de URLs/check.
    try:
        from xhtml2pdf import pisa
    except Exception:
        messages.error(
            request,
            'Dependência de PDF indisponível no ambiente. Instale/atualize xhtml2pdf para exportar.',
        )
        return redirect('frota:motorista_vinculo_consulta')
    
    # Gerar PDF
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html_string.encode("UTF-8")), result)
    
    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        filename = f'consulta_vinculos_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    
    messages.error(request, 'Erro ao gerar PDF.')
    return redirect('frota:motorista_vinculo_consulta')


@login_required
def motorista_set_pin(request, pk):
    """Define matrícula e PIN de login (Usuario vinculado) para acesso ao Portal do Motorista."""
    from django.contrib.auth.models import Group
    from usuarios.models import Usuario
    from .services.motorista_portal import gerar_username_motorista

    empresa = request.user.empresa
    motorista = get_object_or_404(Motorista, pk=pk, empresa=empresa)

    if request.method == 'POST':
        matricula = request.POST.get('matricula', '').strip()
        pin = request.POST.get('pin', '').strip()
        pin2 = request.POST.get('pin2', '').strip()

        matricula_em_uso = Motorista.objects.filter(
            empresa=empresa, matricula=matricula
        ).exclude(pk=motorista.pk).exists() if matricula else False

        if not matricula:
            messages.error(request, 'A matrícula é obrigatória.')
        elif matricula_em_uso:
            messages.error(request, 'Essa matrícula já está em uso por outro motorista desta empresa.')
        elif not motorista.usuario_vinculado_id and not pin:
            messages.error(request, 'Defina um PIN para o primeiro acesso deste motorista.')
        elif pin and pin != pin2:
            messages.error(request, 'Os PINs não coincidem.')
        elif pin and not pin.isdigit():
            messages.error(request, 'O PIN deve conter apenas números.')
        elif pin and len(pin) < 4:
            messages.error(request, 'O PIN deve ter pelo menos 4 dígitos.')
        else:
            motorista.matricula = matricula
            usuario = motorista.usuario_vinculado

            if not usuario:
                username = gerar_username_motorista(empresa.pk, matricula)
                nome_partes = motorista.nome.strip().split(' ', 1)
                usuario = Usuario(
                    username=username,
                    first_name=nome_partes[0],
                    last_name=nome_partes[1] if len(nome_partes) > 1 else '',
                    empresa=empresa,
                    tipo='MOTORISTA',
                    is_active=motorista.ativo,
                )
                usuario.set_password(pin)
                usuario.save()

                grupo, _ = Group.objects.get_or_create(name='MOTORISTA')
                usuario.groups.add(grupo)

                motorista.usuario_vinculado = usuario
            else:
                if pin:
                    usuario.set_password(pin)
                usuario.is_active = motorista.ativo
                usuario.save()

            motorista.save(update_fields=['matricula', 'usuario_vinculado'])
            messages.success(
                request,
                f'Acesso ao portal configurado para {motorista.nome}. '
                f'Login: "{usuario.username}" (informe ao motorista junto com o PIN).'
            )
            return redirect('frota:motorista_detail', pk=motorista.pk)

    return render(request, 'cadastros/motorista/set_pin.html', {
        'motorista': motorista,
        'title': f'Configurar Acesso ao Portal — {motorista.nome}',
    })
