"""
Views do módulo Fazendas
CRUD completo + integração com APIs externas
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.utils import timezone
import requests
import json
from .models import Funcionario, FuncaoFuncionario
from .forms import FuncionarioForm, FuncaoFuncionarioForm

from .models import (
    Fazenda, EnderecoFazenda, ContatoFazenda,
    ContaBancariaFazenda, DocumentoFazenda
)
from .forms import (
    FazendaForm, EnderecoFazendaForm, ContatoFazendaForm,
    ContaBancariaFazendaForm, DocumentoFazendaForm,
    BuscarCNPJForm, BuscarCEPForm
)


# ==================== FAZENDAS ====================

@login_required
def fazenda_list(request):
    """Lista todas as fazendas da empresa"""
    # ✅ Verifica se usuário tem empresa
    if not request.user.empresa:
        messages.warning(
            request,
            '⚠️ Seu usuário não está vinculado a nenhuma empresa. '
            'Entre em contato com o administrador.'
        )
        return redirect('dashboard:index')
    
    fazendas = Fazenda.objects.filter(
        empresa=request.user.empresa
    ).select_related('empresa').prefetch_related(
        'enderecos', 'contatos', 'contas_bancarias', 'documentos'
    )
    
    # Busca
    q = request.GET.get('q', '').strip()
    if q:
        fazendas = fazendas.filter(
            Q(nome__icontains=q) |
            Q(nome_fantasia__icontains=q) |
            Q(cnpj_cpf__icontains=q)
        )
    
    # Filtro por status
    status = request.GET.get('status', '')
    if status == 'ativas':
        fazendas = fazendas.filter(ativa=True)
    elif status == 'inativas':
        fazendas = fazendas.filter(ativa=False)
    
    # Paginação
    paginator = Paginator(fazendas, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Informações adicionais
    context = {
        'page_obj': page_obj,
        'total_fazendas': fazendas.count(),
        'limite_plano': request.user.empresa.limite_fazendas,
        'pode_adicionar': fazendas.filter(ativa=True).count() < request.user.empresa.limite_fazendas,
    }
    
    return render(request, 'cadastros/fazenda_list.html', context)


@login_required
def fazenda_detail(request, pk):
    """Detalhes completos da fazenda"""
    fazenda = get_object_or_404(
        Fazenda.objects.prefetch_related(
            'enderecos', 'contatos', 'contas_bancarias', 'documentos'
        ),
        pk=pk,
        empresa=request.user.empresa
    )
    
    # Documentos que precisam de atenção
    docs_vencidos = fazenda.documentos.filter(
        data_validade__lt=timezone.now().date(),
        gerar_alerta_vencimento=True
    )
    
    docs_vencendo = []
    for doc in fazenda.documentos.filter(gerar_alerta_vencimento=True):
        if doc.precisa_alerta():
            docs_vencendo.append(doc)
    
    context = {
        'fazenda': fazenda,
        'docs_vencidos': docs_vencidos,
        'docs_vencendo': docs_vencendo,
    }
    
    return render(request, 'cadastros/fazenda_detail.html', context)


@login_required
def fazenda_create(request):
    """Cria nova fazenda"""
    # ✅ Verifica se usuário tem empresa
    if not request.user.empresa:
        messages.warning(
            request,
            '⚠️ Seu usuário não está vinculado a nenhuma empresa. '
            'Entre em contato com o administrador.'
        )
        return redirect('dashboard:index')
    
    # Verifica limite do plano
    total_fazendas_ativas = Fazenda.objects.filter(
        empresa=request.user.empresa,
        ativa=True
    ).count()
    
    if total_fazendas_ativas >= request.user.empresa.limite_fazendas:
        messages.error(
            request,
            f'❌ Limite de fazendas atingido! Seu plano permite apenas '
            f'{request.user.empresa.limite_fazendas} fazenda(s) ativa(s). '
            f'Faça upgrade do plano para cadastrar mais.'
        )
        return redirect('cadastros:fazenda_list')
    
    if request.method == 'POST':
        # ✅ DEBUG: Imprime dados recebidos
        print(f"🔍 POST data: {request.POST}")
        print(f"🔍 Usuário: {request.user.username}")
        print(f"🔍 Empresa: {request.user.empresa}")
        
        form = FazendaForm(
            request.POST,
            empresa=request.user.empresa,
            usuario=request.user
        )
        
        # ✅ DEBUG: Verifica se form é válido
        if form.is_valid():
            print("✅ Form é VÁLIDO")
            print(f"🔍 Cleaned data: {form.cleaned_data}")
            
            try:
                fazenda = form.save()
                print(f"✅ Fazenda salva! ID: {fazenda.pk}, Empresa: {fazenda.empresa}")
                messages.success(request, f'✅ Fazenda "{fazenda.nome}" cadastrada com sucesso!')
                return redirect('cadastros:fazenda_detail', pk=fazenda.pk)
            except Exception as e:
                print(f"❌ ERRO ao salvar: {e}")
                messages.error(request, f'❌ Erro ao salvar: {e}')
        else:
            print("❌ Form é INVÁLIDO")
            print(f"🔍 Erros: {form.errors}")
            messages.error(request, '❌ Corrija os erros no formulário abaixo.')
    else:
        form = FazendaForm(
            empresa=request.user.empresa,
            usuario=request.user
        )
    
    return render(request, 'cadastros/fazenda_form.html', {
        'form': form,
        'action': 'Cadastrar'
    })

@login_required
def fazenda_update(request, pk):
    """Edita fazenda"""
    fazenda = get_object_or_404(Fazenda, pk=pk, empresa=request.user.empresa)
    
    if request.method == 'POST':
        form = FazendaForm(
            request.POST,
            instance=fazenda,
            empresa=request.user.empresa,
            usuario=request.user
        )
        if form.is_valid():
            fazenda = form.save()
            messages.success(request, f'✅ Fazenda "{fazenda.nome}" atualizada!')
            return redirect('cadastros:fazenda_detail', pk=fazenda.pk)
    else:
        form = FazendaForm(
            instance=fazenda,
            empresa=request.user.empresa,
            usuario=request.user
        )
    
    return render(request, 'cadastros/fazenda_form.html', {
        'form': form,
        'fazenda': fazenda,
        'action': 'Editar'
    })


@login_required
def fazenda_delete(request, pk):
    """Deleta fazenda"""
    fazenda = get_object_or_404(Fazenda, pk=pk, empresa=request.user.empresa)
    
    # Verifica se tem talhões ou outras dependências
    # total_talhoes = fazenda.talhoes.count()
    # if total_talhoes > 0:
    #     messages.error(request, f'❌ Não é possível excluir! A fazenda possui {total_talhoes} talhão(ões) cadastrado(s).')
    #     return redirect('cadastros:fazenda_detail', pk=fazenda.pk)
    
    if request.method == 'POST':
        nome = fazenda.nome
        fazenda.delete()
        messages.success(request, f'🗑️ Fazenda "{nome}" excluída com sucesso!')
        return redirect('cadastros:fazenda_list')
    
    return render(request, 'cadastros/fazenda_confirm_delete.html', {'fazenda': fazenda})


# ==================== API EXTERNA - CNPJ ====================

@login_required
def buscar_cnpj(request):
    """Busca dados do CNPJ via API ReceitaWS"""
    if request.method == 'POST':
        cnpj = request.POST.get('cnpj', '').replace('.', '').replace('/', '').replace('-', '')
        
        if len(cnpj) != 14:
            return JsonResponse({'erro': 'CNPJ inválido'}, status=400)
        
        try:
            # API ReceitaWS (gratuita)
            url = f'https://www.receitaws.com.br/v1/cnpj/{cnpj}'
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                dados = response.json()
                
                if dados.get('status') == 'ERROR':
                    return JsonResponse({'erro': dados.get('message', 'CNPJ não encontrado')}, status=404)
                
                # Formata dados para retornar
                resultado = {
                    'nome': dados.get('nome', ''),
                    'nome_fantasia': dados.get('fantasia', ''),
                    'cnpj': dados.get('cnpj', ''),
                    'telefone': dados.get('telefone', ''),
                    'email': dados.get('email', ''),
                    'logradouro': dados.get('logradouro', ''),
                    'numero': dados.get('numero', ''),
                    'complemento': dados.get('complemento', ''),
                    'bairro': dados.get('bairro', ''),
                    'cidade': dados.get('municipio', ''),
                    'uf': dados.get('uf', ''),
                    'cep': dados.get('cep', '').replace('.', '').replace('-', ''),
                }
                
                return JsonResponse({'sucesso': True, 'dados': resultado})
            else:
                return JsonResponse({'erro': 'Erro ao consultar API'}, status=500)
                
        except requests.Timeout:
            return JsonResponse({'erro': 'Timeout na consulta'}, status=500)
        except Exception as e:
            return JsonResponse({'erro': str(e)}, status=500)
    
    return JsonResponse({'erro': 'Método não permitido'}, status=405)


# ==================== API EXTERNA - CEP ====================

@login_required
def buscar_cep(request):
    """Busca endereço via CEP usando ViaCEP"""
    if request.method == 'POST':
        cep = request.POST.get('cep', '').replace('-', '').replace('.', '')
        
        if len(cep) != 8:
            return JsonResponse({'erro': 'CEP inválido'}, status=400)
        
        try:
            # API ViaCEP (gratuita)
            url = f'https://viacep.com.br/ws/{cep}/json/'
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                dados = response.json()
                
                if dados.get('erro'):
                    return JsonResponse({'erro': 'CEP não encontrado'}, status=404)
                
                resultado = {
                    'cep': dados.get('cep', ''),
                    'logradouro': dados.get('logradouro', ''),
                    'complemento': dados.get('complemento', ''),
                    'bairro': dados.get('bairro', ''),
                    'cidade': dados.get('localidade', ''),
                    'uf': dados.get('uf', ''),
                }
                
                return JsonResponse({'sucesso': True, 'dados': resultado})
            else:
                return JsonResponse({'erro': 'Erro ao consultar API'}, status=500)
                
        except requests.Timeout:
            return JsonResponse({'erro': 'Timeout na consulta'}, status=500)
        except Exception as e:
            return JsonResponse({'erro': str(e)}, status=500)
    
    return JsonResponse({'erro': 'Método não permitido'}, status=405)


# ==================== ENDEREÇOS ====================

@login_required
def endereco_create(request, fazenda_pk):
    """Adiciona endereço à fazenda"""
    fazenda = get_object_or_404(Fazenda, pk=fazenda_pk, empresa=request.user.empresa)
    
    if request.method == 'POST':
        form = EnderecoFazendaForm(request.POST)
        if form.is_valid():
            endereco = form.save(commit=False)
            endereco.fazenda = fazenda
            endereco.save()
            messages.success(request, '✅ Endereço adicionado!')
            return redirect('cadastros:fazenda_detail', pk=fazenda.pk)
    else:
        form = EnderecoFazendaForm()
    
    return render(request, 'cadastros/endereco_form.html', {
        'form': form,
        'fazenda': fazenda,
        'action': 'Adicionar'
    })


@login_required
def endereco_update(request, fazenda_pk, endereco_pk):
    """Edita endereço"""
    fazenda = get_object_or_404(Fazenda, pk=fazenda_pk, empresa=request.user.empresa)
    endereco = get_object_or_404(EnderecoFazenda, pk=endereco_pk, fazenda=fazenda)
    
    if request.method == 'POST':
        form = EnderecoFazendaForm(request.POST, instance=endereco)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Endereço atualizado!')
            return redirect('cadastros:fazenda_detail', pk=fazenda.pk)
    else:
        form = EnderecoFazendaForm(instance=endereco)
    
    return render(request, 'cadastros/endereco_form.html', {
        'form': form,
        'fazenda': fazenda,
        'endereco': endereco,
        'action': 'Editar'
    })


@login_required
def endereco_delete(request, fazenda_pk, endereco_pk):
    """Remove endereço"""
    fazenda = get_object_or_404(Fazenda, pk=fazenda_pk, empresa=request.user.empresa)
    endereco = get_object_or_404(EnderecoFazenda, pk=endereco_pk, fazenda=fazenda)
    
    if request.method == 'POST':
        endereco.delete()
        messages.success(request, '🗑️ Endereço removido!')
        return redirect('cadastros:fazenda_detail', pk=fazenda.pk)
    
    return render(request, 'cadastros/endereco_confirm_delete.html', {
        'fazenda': fazenda,
        'endereco': endereco
    })


# ==================== CONTATOS ====================

@login_required
def contato_create(request, fazenda_pk):
    """Adiciona contato à fazenda"""
    fazenda = get_object_or_404(Fazenda, pk=fazenda_pk, empresa=request.user.empresa)
    
    if request.method == 'POST':
        form = ContatoFazendaForm(request.POST)
        if form.is_valid():
            contato = form.save(commit=False)
            contato.fazenda = fazenda
            contato.save()
            messages.success(request, '✅ Contato adicionado!')
            return redirect('cadastros:fazenda_detail', pk=fazenda.pk)
    else:
        form = ContatoFazendaForm()
    
    return render(request, 'cadastros/contato_form.html', {
        'form': form,
        'fazenda': fazenda,
        'action': 'Adicionar'
    })


@login_required
def contato_update(request, fazenda_pk, contato_pk):
    """Edita contato"""
    fazenda = get_object_or_404(Fazenda, pk=fazenda_pk, empresa=request.user.empresa)
    contato = get_object_or_404(ContatoFazenda, pk=contato_pk, fazenda=fazenda)
    
    if request.method == 'POST':
        form = ContatoFazendaForm(request.POST, instance=contato)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Contato atualizado!')
            return redirect('cadastros:fazenda_detail', pk=fazenda.pk)
    else:
        form = ContatoFazendaForm(instance=contato)
    
    return render(request, 'cadastros/contato_form.html', {
        'form': form,
        'fazenda': fazenda,
        'contato': contato,
        'action': 'Editar'
    })


@login_required
def contato_delete(request, fazenda_pk, contato_pk):
    """Remove contato"""
    fazenda = get_object_or_404(Fazenda, pk=fazenda_pk, empresa=request.user.empresa)
    contato = get_object_or_404(ContatoFazenda, pk=contato_pk, fazenda=fazenda)
    
    if request.method == 'POST':
        contato.delete()
        messages.success(request, '🗑️ Contato removido!')
        return redirect('cadastros:fazenda_detail', pk=fazenda.pk)
    
    return render(request, 'cadastros/contato_confirm_delete.html', {
        'fazenda': fazenda,
        'contato': contato
    })


# ==================== CONTAS BANCÁRIAS ====================

@login_required
def conta_bancaria_create(request, fazenda_pk):
    """Adiciona conta bancária"""
    fazenda = get_object_or_404(Fazenda, pk=fazenda_pk, empresa=request.user.empresa)
    
    if request.method == 'POST':
        form = ContaBancariaFazendaForm(request.POST)
        if form.is_valid():
            conta = form.save(commit=False)
            conta.fazenda = fazenda
            conta.save()
            messages.success(request, '✅ Conta bancária adicionada!')
            return redirect('cadastros:fazenda_detail', pk=fazenda.pk)
    else:
        form = ContaBancariaFazendaForm()
    
    return render(request, 'cadastros/conta_bancaria_form.html', {
        'form': form,
        'fazenda': fazenda,
        'action': 'Adicionar'
    })


@login_required
def conta_bancaria_update(request, fazenda_pk, conta_pk):
    """Edita conta bancária"""
    fazenda = get_object_or_404(Fazenda, pk=fazenda_pk, empresa=request.user.empresa)
    conta = get_object_or_404(ContaBancariaFazenda, pk=conta_pk, fazenda=fazenda)
    
    if request.method == 'POST':
        form = ContaBancariaFazendaForm(request.POST, instance=conta)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Conta bancária atualizada!')
            return redirect('cadastros:fazenda_detail', pk=fazenda.pk)
    else:
        form = ContaBancariaFazendaForm(instance=conta)
    
    return render(request, 'cadastros/conta_bancaria_form.html', {
        'form': form,
        'fazenda': fazenda,
        'conta': conta,
        'action': 'Editar'
    })


@login_required
def conta_bancaria_delete(request, fazenda_pk, conta_pk):
    """Remove conta bancária"""
    fazenda = get_object_or_404(Fazenda, pk=fazenda_pk, empresa=request.user.empresa)
    conta = get_object_or_404(ContaBancariaFazenda, pk=conta_pk, fazenda=fazenda)
    
    if request.method == 'POST':
        conta.delete()
        messages.success(request, '🗑️ Conta bancária removida!')
        return redirect('cadastros:fazenda_detail', pk=fazenda.pk)
    
    return render(request, 'cadastros/conta_bancaria_confirm_delete.html', {
        'fazenda': fazenda,
        'conta': conta
    })


# ==================== DOCUMENTOS ====================

@login_required
def documento_create(request, fazenda_pk):
    """Adiciona documento à fazenda"""
    fazenda = get_object_or_404(Fazenda, pk=fazenda_pk, empresa=request.user.empresa)
    
    if request.method == 'POST':
        form = DocumentoFazendaForm(request.POST, request.FILES)
        if form.is_valid():
            documento = form.save(commit=False)
            documento.fazenda = fazenda
            documento.enviado_por = request.user
            documento.save()
            messages.success(request, '✅ Documento anexado!')
            return redirect('cadastros:fazenda_detail', pk=fazenda.pk)
    else:
        form = DocumentoFazendaForm()
    
    return render(request, 'cadastros/documento_form.html', {
        'form': form,
        'fazenda': fazenda,
        'action': 'Adicionar'
    })


@login_required
def documento_delete(request, fazenda_pk, documento_pk):
    """Remove documento"""
    fazenda = get_object_or_404(Fazenda, pk=fazenda_pk, empresa=request.user.empresa)
    documento = get_object_or_404(DocumentoFazenda, pk=documento_pk, fazenda=fazenda)
    
    if request.method == 'POST':
        # Remove arquivo físico
        if documento.arquivo:
            documento.arquivo.delete()
        
        documento.delete()
        messages.success(request, '🗑️ Documento removido!')
        return redirect('cadastros:fazenda_detail', pk=fazenda.pk)
    
    return render(request, 'cadastros/documento_confirm_delete.html', {
        'fazenda': fazenda,
        'documento': documento
    })


# ==================== ALERTAS ====================

@login_required
def dashboard_alertas(request):
    """Dashboard com alertas de documentos vencidos/vencendo"""
    fazendas = Fazenda.objects.filter(
        empresa=request.user.empresa,
        ativa=True
    )
    
    docs_vencidos = []
    docs_vencendo = []
    
    for fazenda in fazendas:
        # Vencidos
        vencidos = DocumentoFazenda.objects.filter(
            fazenda=fazenda,
            data_validade__lt=timezone.now().date(),
            gerar_alerta_vencimento=True
        )
        docs_vencidos.extend(vencidos)
        
        # A vencer
        for doc in DocumentoFazenda.objects.filter(fazenda=fazenda, gerar_alerta_vencimento=True):
            if doc.precisa_alerta():
                docs_vencendo.append(doc)
    
    context = {
        'docs_vencidos': docs_vencidos,
        'docs_vencendo': docs_vencendo,
        'total_alertas': len(docs_vencidos) + len(docs_vencendo),
    }
    
    return render(request, 'cadastros/dashboard_alertas.html', context)




"""
ADICIONE ESTAS VIEWS AO FINAL DO ARQUIVO cadastros/views.py
"""




# ==================== FUNÇÕES ====================

@login_required
def funcao_list(request):
    """Lista funções de funcionários"""
    funcoes = FuncaoFuncionario.objects.filter(empresa=request.user.empresa)
    
    q = request.GET.get('q', '').strip()
    if q:
        funcoes = funcoes.filter(nome__icontains=q)
    
    return render(request, 'cadastros/funcao_list.html', {'funcoes': funcoes})


@login_required
def funcao_create_ajax(request):
    """Cria função via AJAX (para modal)"""
    if request.method == 'POST':
        form = FuncaoFuncionarioForm(request.POST)
        if form.is_valid():
            funcao = form.save(commit=False)
            funcao.empresa = request.user.empresa
            funcao.save()
            
            return JsonResponse({
                'sucesso': True,
                'id': funcao.id,
                'nome': funcao.nome,
                'mensagem': f'Função "{funcao.nome}" criada com sucesso!'
            })
        else:
            return JsonResponse({
                'sucesso': False,
                'erros': form.errors
            }, status=400)
    
    return JsonResponse({'erro': 'Método não permitido'}, status=405)


# ==================== FUNCIONÁRIOS ====================

@login_required
def funcionario_list(request):
    """Lista funcionários"""
    funcionarios = Funcionario.objects.filter(
        empresa=request.user.empresa
    ).select_related('funcao', 'fazenda')
    
    # Busca
    q = request.GET.get('q', '').strip()
    if q:
        funcionarios = funcionarios.filter(
            Q(nome_completo__icontains=q) |
            Q(cpf__icontains=q) |
            Q(funcao__nome__icontains=q)
        )
    
    # Filtros
    status = request.GET.get('status', '')
    if status == 'ativos':
        funcionarios = funcionarios.filter(ativo=True)
    elif status == 'inativos':
        funcionarios = funcionarios.filter(ativo=False)
    
    fazenda_id = request.GET.get('fazenda', '')
    if fazenda_id:
        funcionarios = funcionarios.filter(fazenda_id=fazenda_id)
    
    funcao_id = request.GET.get('funcao', '')
    if funcao_id:
        funcionarios = funcionarios.filter(funcao_id=funcao_id)
    
    # Paginação
    paginator = Paginator(funcionarios, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Para filtros
    fazendas = Fazenda.objects.filter(empresa=request.user.empresa, ativa=True)
    funcoes = FuncaoFuncionario.objects.filter(empresa=request.user.empresa, ativa=True)
    
    context = {
        'page_obj': page_obj,
        'fazendas': fazendas,
        'funcoes': funcoes,
        'total_funcionarios': funcionarios.count(),
    }
    
    return render(request, 'cadastros/funcionario_list.html', context)


@login_required
def funcionario_detail(request, pk):
    """Detalhes do funcionário"""
    funcionario = get_object_or_404(
        Funcionario,
        pk=pk,
        empresa=request.user.empresa
    )
    
    return render(request, 'cadastros/funcionario_detail.html', {
        'funcionario': funcionario
    })


@login_required
def funcionario_create(request):
    """Cria funcionário"""
    if request.method == 'POST':
        form = FuncionarioForm(
            request.POST,
            request.FILES,
            empresa=request.user.empresa,
            usuario=request.user
        )
        if form.is_valid():
            funcionario = form.save()
            messages.success(request, f'✅ Funcionário "{funcionario.nome_completo}" cadastrado!')
            return redirect('cadastros:funcionario_detail', pk=funcionario.pk)
    else:
        form = FuncionarioForm(
            empresa=request.user.empresa,
            usuario=request.user
        )
    
    # Para o modal de nova função
    form_funcao = FuncaoFuncionarioForm()
    
    return render(request, 'cadastros/funcionario_form.html', {
        'form': form,
        'form_funcao': form_funcao,
        'action': 'Cadastrar'
    })


@login_required
def funcionario_update(request, pk):
    """Edita funcionário"""
    funcionario = get_object_or_404(Funcionario, pk=pk, empresa=request.user.empresa)
    
    if request.method == 'POST':
        form = FuncionarioForm(
            request.POST,
            request.FILES,
            instance=funcionario,
            empresa=request.user.empresa,
            usuario=request.user
        )
        if form.is_valid():
            funcionario = form.save()
            messages.success(request, f'✅ Funcionário "{funcionario.nome_completo}" atualizado!')
            return redirect('cadastros:funcionario_detail', pk=funcionario.pk)
    else:
        form = FuncionarioForm(
            instance=funcionario,
            empresa=request.user.empresa,
            usuario=request.user
        )
    
    form_funcao = FuncaoFuncionarioForm()
    
    return render(request, 'cadastros/funcionario_form.html', {
        'form': form,
        'form_funcao': form_funcao,
        'funcionario': funcionario,
        'action': 'Editar'
    })


@login_required
def funcionario_delete(request, pk):
    """Deleta funcionário"""
    funcionario = get_object_or_404(Funcionario, pk=pk, empresa=request.user.empresa)
    
    if request.method == 'POST':
        nome = funcionario.nome_completo
        funcionario.delete()
        messages.success(request, f'🗑️ Funcionário "{nome}" excluído!')
        return redirect('cadastros:funcionario_list')
    
    return render(request, 'cadastros/funcionario_confirm_delete.html', {
        'funcionario': funcionario
    })