"""
Views do módulo Fazendas
CRUD completo + integração com APIs externas
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q, Count, Sum, Avg
from django.core.paginator import Paginator
from django.utils import timezone
import requests
from .models import Funcionario, FuncaoFuncionario
from .forms import FuncionarioForm, FuncaoFuncionarioForm

from .models import (
    Fazenda, EnderecoFazenda, ContatoFazenda,
    ContaBancariaFazenda, DocumentoFazenda
)
from .forms import (
    FazendaForm, EnderecoFazendaForm, ContatoFazendaForm,
    ContaBancariaFazendaForm, DocumentoFazendaForm,
)

from .models import Area, Talhao, Cultura, HistoricoTalhao, Safra
from .forms import AreaForm, TalhaoForm, CulturaForm, HistoricoTalhaoForm, SafraForm




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
                
        except requests.exceptions.Timeout:
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
                
        except requests.exceptions.Timeout:
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



"""
ADICIONE ESTE CÓDIGO NO FINAL DO ARQUIVO cadastros/views.py
"""




# ==================== CULTURAS ====================

@login_required
def cultura_list(request):
    """Lista todas as culturas da empresa"""
    culturas = Cultura.objects.filter(
        empresa=request.user.empresa
    ).select_related('empresa', 'cadastrado_por')
    
    # Busca
    q = request.GET.get('q', '').strip()
    if q:
        culturas = culturas.filter(
            Q(nome__icontains=q) |
            Q(variedade__icontains=q) |
            Q(nome_cientifico__icontains=q) |
            Q(codigo_interno__icontains=q)
        )
    
    # Filtro por tipo
    tipo = request.GET.get('tipo', '')
    if tipo:
        culturas = culturas.filter(tipo=tipo)
    
    # Filtro por status
    status = request.GET.get('status', '')
    if status == 'ativas':
        culturas = culturas.filter(ativa=True)
    elif status == 'inativas':
        culturas = culturas.filter(ativa=False)
    
    # Paginação
    paginator = Paginator(culturas, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Informações adicionais
    context = {
        'page_obj': page_obj,
        'total_culturas': culturas.count(),
        'limite_plano': request.user.empresa.limite_produtos,
        'pode_adicionar': culturas.filter(ativa=True).count() < request.user.empresa.limite_produtos,
        'tipos_cultura': Cultura.TIPO_CULTURA,
    }
    
    return render(request, 'cadastros/cultura_list.html', context)


@login_required
def cultura_detail(request, pk):
    """Detalhes completos da cultura"""
    cultura = get_object_or_404(
        Cultura,
        pk=pk,
        empresa=request.user.empresa
    )
    
    context = {
        'cultura': cultura,
        # 'total_plantios': cultura.get_total_plantios(),  # Implementar depois
    }
    
    return render(request, 'cadastros/cultura_detail.html', context)


@login_required
def cultura_create(request):
    """Cria nova cultura"""
    # Verifica limite do plano
    total_culturas_ativas = Cultura.objects.filter(
        empresa=request.user.empresa,
        ativa=True
    ).count()
    
    if total_culturas_ativas >= request.user.empresa.limite_produtos:
        messages.error(
            request,
            f'❌ Limite de culturas atingido! Seu plano permite apenas '
            f'{request.user.empresa.limite_produtos} cultura(s) ativa(s). '
            f'Faça upgrade do plano para cadastrar mais.'
        )
        return redirect('cadastros:cultura_list')
    
    if request.method == 'POST':
        form = CulturaForm(
            request.POST,
            request.FILES,
            empresa=request.user.empresa,
            usuario=request.user
        )
        if form.is_valid():
            cultura = form.save()
            messages.success(request, f'✅ Cultura "{cultura.nome}" cadastrada com sucesso!')
            return redirect('cadastros:cultura_detail', pk=cultura.pk)
    else:
        form = CulturaForm(
            empresa=request.user.empresa,
            usuario=request.user
        )
    
    return render(request, 'cadastros/cultura_form.html', {
        'form': form,
        'action': 'Cadastrar'
    })


@login_required
def cultura_update(request, pk):
    """Edita cultura"""
    cultura = get_object_or_404(Cultura, pk=pk, empresa=request.user.empresa)
    
    if request.method == 'POST':
        form = CulturaForm(
            request.POST,
            request.FILES,
            instance=cultura,
            empresa=request.user.empresa,
            usuario=request.user
        )
        if form.is_valid():
            cultura = form.save()
            messages.success(request, f'✅ Cultura "{cultura.nome}" atualizada!')
            return redirect('cadastros:cultura_detail', pk=cultura.pk)
    else:
        form = CulturaForm(
            instance=cultura,
            empresa=request.user.empresa,
            usuario=request.user
        )
    
    return render(request, 'cadastros/cultura_form.html', {
        'form': form,
        'cultura': cultura,
        'action': 'Editar'
    })


@login_required
def cultura_delete(request, pk):
    """Deleta cultura"""
    cultura = get_object_or_404(Cultura, pk=pk, empresa=request.user.empresa)
    
    # Verifica se tem plantios associados (implementar depois)
    # total_plantios = cultura.get_total_plantios()
    # if total_plantios > 0:
    #     messages.error(request, f'❌ Não é possível excluir! A cultura possui {total_plantios} plantio(s).')
    #     return redirect('cadastros:cultura_detail', pk=cultura.pk)
    
    if request.method == 'POST':
        nome = cultura.nome
        
        # Remove imagem se existir
        if cultura.imagem:
            cultura.imagem.delete()
        
        cultura.delete()
        messages.success(request, f'🗑️ Cultura "{nome}" excluída com sucesso!')
        return redirect('cadastros:cultura_list')
    
    return render(request, 'cadastros/cultura_confirm_delete.html', {'cultura': cultura})



@login_required
def safra_list(request):
    """Lista safras da empresa do usuário"""
    empresa = request.user.empresa
    if not empresa:
        messages.warning(request, 'Você não está vinculado a nenhuma empresa.')
        # Em vez de redirecionar, renderiza a lista com aviso e sem safras
        context = {'safras': [], 'empresa_missing': True}
        return render(request, 'cadastros/safra_list.html', context)

    safras = Safra.objects.filter(fazenda__empresa=empresa).select_related('fazenda', 'cultura')

    # Filtros
    q = request.GET.get('q', '').strip()
    fazenda_id = request.GET.get('fazenda')
    cultura_id = request.GET.get('cultura')
    ano = request.GET.get('ano')
    status = request.GET.get('status')

    if q:
        safras = safras.filter(Q(nome__icontains=q) | Q(ano__icontains=q) | Q(fazenda__nome__icontains=q))
    if fazenda_id:
        safras = safras.filter(fazenda_id=fazenda_id)
    if cultura_id:
        safras = safras.filter(cultura_id=cultura_id)
    if ano:
        safras = safras.filter(ano=ano)
    if status:
        safras = safras.filter(status=status)

    # Paginação
    paginator = Paginator(safras.order_by('-ano', 'nome'), 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'safras': page_obj.object_list,
        'page_obj': page_obj,
        'fazendas': Fazenda.objects.filter(empresa=empresa, ativa=True).order_by('nome'),
        'culturas': Cultura.objects.filter(empresa=empresa, ativa=True).order_by('nome'),
    }
    return render(request, 'cadastros/safra_list.html', context)

#=====================================
#                SAFRAS
# ===================================+

@login_required
def safra_create(request):
    empresa = request.user.empresa
    if not empresa:
        messages.warning(request, 'Você não está vinculado a nenhuma empresa.')
        return render(request, 'cadastros/safra_form.html', {'empresa_missing': True, 'action': 'Cadastrar'})

    if request.method == 'POST':
        print(f"🔍 POST Data: {request.POST}")  # DEBUG
        
        # ✅ PEGA IDs DOS TALHÕES DO CAMPO HIDDEN
        talhoes_ids = request.POST.get('talhoes', '').strip()
        print(f"🔍 Talhões IDs recebidos: '{talhoes_ids}'")  # DEBUG
        
        form = SafraForm(request.POST, user=request.user)
        
        if form.is_valid():
            print("✅ Form válido!")  # DEBUG
            
            safra = form.save(commit=False)
            safra.cadastrado_por = request.user
            safra.save()
            
            print(f"✅ Safra salva! ID: {safra.pk}")  # DEBUG
            
            # ✅ LIMPA O RELACIONAMENTO ANTES DE ADICIONAR NOVOS
            safra.talhoes.clear()
            
            # ✅ ASSOCIA TALHÕES SE HOUVER
            if talhoes_ids:
                try:
                    # Converte string "1,2,3" em lista [1,2,3]
                    talhao_ids_list = [int(tid.strip()) for tid in talhoes_ids.split(',') if tid.strip()]
                    print(f"🔍 IDs processados: {talhao_ids_list}")  # DEBUG
                    
                    # Busca talhões da empresa
                    talhoes = Talhao.objects.filter(
                        id__in=talhao_ids_list,
                        empresa=empresa,
                        ativo=True
                    )
                    
                    print(f"🔍 Talhões encontrados: {talhoes.count()}")  # DEBUG
                    
                    # Valida se talhões pertencem à fazenda
                    for talhao in talhoes:
                        if talhao.fazenda != safra.fazenda:
                            messages.error(request, f'❌ Talhão {talhao.codigo} não pertence à fazenda selecionada')
                            safra.delete()
                            return render(request, 'cadastros/safra_form.html', {'form': form, 'action': 'Cadastrar'})
                    
                    # Adiciona talhões um por um
                    for talhao in talhoes:
                        safra.talhoes.add(talhao)
                    
                    print(f"✅ Talhões associados: {safra.talhoes.count()}")  # DEBUG
                    
                except Exception as e:
                    print(f"❌ Erro ao processar talhões: {e}")  # DEBUG
                    import traceback
                    traceback.print_exc()
                    messages.error(request, f'❌ Erro ao processar talhões: {e}')
                    safra.delete()
                    return render(request, 'cadastros/safra_form.html', {'form': form, 'action': 'Cadastrar'})
            
            messages.success(request, f'✅ Safra "{safra}" cadastrada com {safra.talhoes.count()} talhão(ões)!')
            return redirect('cadastros:safra_detail', pk=safra.pk)
        else:
            print(f"❌ Form inválido: {form.errors}")  # DEBUG
            messages.error(request, '❌ Corrija os erros no formulário')
    else:
        form = SafraForm(user=request.user)

    return render(request, 'cadastros/safra_form.html', {'form': form, 'action': 'Cadastrar'})


@login_required
def safra_update(request, pk):
    safra = get_object_or_404(Safra, pk=pk, fazenda__empresa=request.user.empresa)
    empresa = request.user.empresa
    
    if request.method == 'POST':
        print(f"🔍 POST Data: {request.POST}")  # DEBUG
        
        # ✅ PEGA IDs DOS TALHÕES
        talhoes_ids = request.POST.get('talhoes', '').strip()
        print(f"🔍 Talhões IDs recebidos: '{talhoes_ids}'")  # DEBUG
        
        form = SafraForm(request.POST, instance=safra, user=request.user)
        
        if form.is_valid():
            print("✅ Form válido!")  # DEBUG
            
            safra = form.save()
            
            # ✅ LIMPA RELACIONAMENTO EXISTENTE
            safra.talhoes.clear()
            
            # ✅ ATUALIZA TALHÕES
            if talhoes_ids:
                try:
                    talhao_ids_list = [int(tid.strip()) for tid in talhoes_ids.split(',') if tid.strip()]
                    print(f"🔍 IDs processados: {talhao_ids_list}")  # DEBUG
                    
                    talhoes = Talhao.objects.filter(
                        id__in=talhao_ids_list,
                        empresa=empresa,
                        ativo=True
                    )
                    
                    print(f"🔍 Talhões encontrados: {talhoes.count()}")  # DEBUG
                    
                    # Valida fazenda
                    for talhao in talhoes:
                        if talhao.fazenda != safra.fazenda:
                            messages.error(request, f'❌ Talhão {talhao.codigo} não pertence à fazenda selecionada')
                            return render(request, 'cadastros/safra_form.html', {
                                'form': form, 
                                'safra': safra, 
                                'action': 'Editar'
                            })
                    
                    # Adiciona talhões
                    for talhao in talhoes:
                        safra.talhoes.add(talhao)
                    
                    print(f"✅ Talhões associados: {safra.talhoes.count()}")  # DEBUG
                    
                except Exception as e:
                    print(f"❌ Erro ao processar talhões: {e}")  # DEBUG
                    import traceback
                    traceback.print_exc()
                    messages.error(request, f'❌ Erro ao processar talhões: {e}')
            
            messages.success(request, f'✅ Safra "{safra}" atualizada com {safra.talhoes.count()} talhão(ões)!')
            return redirect('cadastros:safra_detail', pk=safra.pk)
        else:
            print(f"❌ Form inválido: {form.errors}")  # DEBUG
            messages.error(request, '❌ Corrija os erros no formulário')
    else:
        form = SafraForm(instance=safra, user=request.user)

    return render(request, 'cadastros/safra_form.html', {
        'form': form, 
        'safra': safra, 
        'action': 'Editar'
    })

@login_required
def safra_detail(request, pk):
    safra = get_object_or_404(Safra, pk=pk, fazenda__empresa=request.user.empresa)
    # Prepare comparativo
    context = {'safra': safra}
    return render(request, 'cadastros/safra_detail.html', context)


@login_required
def safra_delete(request, pk):
    safra = get_object_or_404(Safra, pk=pk, fazenda__empresa=request.user.empresa)
    if request.method == 'POST':
        nome = str(safra)
        safra.delete()
        messages.success(request, f'🗑️ Safra "{nome}" excluída com sucesso!')
        return redirect('cadastros:safra_list')
    return render(request, 'cadastros/safra_confirm_delete.html', {'safra': safra})





    """
ADICIONE ESTAS VIEWS AO ARQUIVO cadastros/views.py
Views para Áreas e Talhões com isolamento Multi-Tenant
"""




# ============================================
# VIEWS DE ÁREA
# ============================================

@login_required
def area_list(request):
    """
    Lista áreas da empresa do usuário logado
    🔒 FILTRO AUTOMÁTICO POR EMPRESA
    """
    empresa = request.user.empresa
    
    if not empresa:
        messages.warning(request, 'Você não está vinculado a nenhuma empresa.')
        return redirect('dashboard:index')
    
    # 🔒 Filtra apenas áreas da empresa do usuário
    # Nem sempre o manager customizado pode estar disponível (erro em alguns ambientes).
    # Usamos um fallback seguro para evitar AttributeError caso `da_empresa` não exista.
    if hasattr(Area.objects, 'da_empresa'):
        areas = Area.objects.da_empresa(empresa).select_related(
            'fazenda', 'cadastrado_por'
        ).prefetch_related('talhoes')
    else:
        areas = Area.objects.filter(empresa=empresa).select_related(
            'fazenda', 'cadastrado_por'
        ).prefetch_related('talhoes')
    
    # Busca
    q = request.GET.get('q', '').strip()
    if q:
        areas = areas.filter(
            Q(nome__icontains=q) |
            Q(codigo_interno__icontains=q) |
            Q(fazenda__nome__icontains=q)
        )
    
    # Filtro por fazenda
    fazenda_id = request.GET.get('fazenda')
    if fazenda_id:
        areas = areas.filter(fazenda_id=fazenda_id)
    
    # Filtro por tipo
    tipo = request.GET.get('tipo')
    if tipo:
        areas = areas.filter(tipo_area=tipo)
    
    # Filtro por status
    status = request.GET.get('status')
    if status:
        areas = areas.filter(status=status)
    
    # Adiciona estatísticas
    for area in areas:
        area.total_talhoes = area.talhoes.filter(ativo=True).count()
        area.area_disponivel = area.get_area_disponivel()
        area.percentual_uso = area.get_percentual_uso()
    
    # 🔒 Fazendas da empresa para filtro
    fazendas = Fazenda.objects.filter(
        empresa=empresa, 
        ativa=True
    ).order_by('nome')
    
    context = {
        'areas': areas,
        'fazendas': fazendas,
        'total_areas': areas.count(),
    }
    
    return render(request, 'cadastros/area_list.html', context)


@login_required
def area_create(request):
    """
    Cria nova área
    🔒 VINCULA AUTOMATICAMENTE À EMPRESA DO USUÁRIO
    """
    empresa = request.user.empresa
    
    if not empresa:
        messages.error(request, 'Você não está vinculado a nenhuma empresa.')
        return redirect('dashboard:index')
    
    if request.method == 'POST':
        form = AreaForm(request.POST, user=request.user)
        if form.is_valid():
            area = form.save(commit=False)
            area.empresa = empresa  # 🔒 Vincula à empresa
            area.cadastrado_por = request.user
            area.save()
            
            messages.success(
                request, 
                f'✅ Área "{area.nome}" cadastrada com sucesso!'
            )
            return redirect('cadastros:area_list')
    else:
        form = AreaForm(user=request.user)
    
    return render(request, 'cadastros/area_form.html', {
        'form': form,
        'title': 'Nova Área'
    })


@login_required
def area_update(request, pk):
    """
    Edita área existente
    🔒 VERIFICA SE PERTENCE À EMPRESA DO USUÁRIO
    """
    empresa = request.user.empresa
    
    # 🔒 Busca apenas se pertencer à empresa
    area = get_object_or_404(
        Area.objects.da_empresa(empresa),
        pk=pk
    )
    
    if request.method == 'POST':
        form = AreaForm(request.POST, instance=area, user=request.user)
        if form.is_valid():
            area = form.save()
            messages.success(request, f'✅ Área "{area.nome}" atualizada!')
            return redirect('cadastros:area_list')
    else:
        form = AreaForm(instance=area, user=request.user)
    
    return render(request, 'cadastros/area_form.html', {
        'form': form,
        'area': area,
        'title': f'Editar Área: {area.nome}'
    })


@login_required
def area_delete(request, pk):
    """
    Exclui área
    🔒 VERIFICA PERMISSÃO E VALIDA EXCLUSÃO
    """
    empresa = request.user.empresa
    
    # 🔒 Busca apenas se pertencer à empresa
    area = get_object_or_404(
        Area.objects.da_empresa(empresa),
        pk=pk
    )
    
    # Verifica se tem talhões vinculados
    total_talhoes = area.talhoes.filter(ativo=True).count()
    
    if total_talhoes > 0:
        messages.error(
            request,
            f'❌ Não é possível excluir! A área possui {total_talhoes} talhão(ões) ativo(s).'
        )
        return redirect('cadastros:area_list')
    
    if request.method == 'POST':
        nome = area.nome
        area.delete()
        messages.success(request, f'🗑️ Área "{nome}" excluída com sucesso!')
        return redirect('cadastros:area_list')
    
    return render(request, 'cadastros/area_confirm_delete.html', {
        'area': area
    })


@login_required
def area_detail(request, pk):
    """
    Detalhes da área com talhões
    🔒 ACESSO APENAS PARA EMPRESA DONA
    """
    empresa = request.user.empresa
    
    # 🔒 Busca apenas se pertencer à empresa
    area = get_object_or_404(
        Area.objects.da_empresa(empresa).select_related('fazenda'),
        pk=pk
    )
    
    # Talhões da área
    talhoes = area.talhoes.filter(ativo=True).select_related('cultura_atual')
    
    # Estatísticas
    stats = {
        'total_talhoes': talhoes.count(),
        'area_ocupada': talhoes.aggregate(Sum('area_hac'))['area_hac__sum'] or 0,
        'area_disponivel': area.get_area_disponivel(),
        'percentual_uso': area.get_percentual_uso(),
        'talhoes_plantados': talhoes.filter(status='PLANTADO').count(),
        'talhoes_disponiveis': talhoes.filter(status='DISPONIVEL').count(),
    }
    
    return render(request, 'cadastros/area_detail.html', {
        'area': area,
        'talhoes': talhoes,
        'stats': stats
    })


# ============================================
# VIEWS DE TALHÃO
# ============================================

@login_required
def talhao_list(request):
    """
    Lista talhões da empresa
    🔒 FILTRO AUTOMÁTICO POR EMPRESA
    """
    empresa = request.user.empresa
    
    if not empresa:
        messages.warning(request, 'Você não está vinculado a nenhuma empresa.')
        return redirect('dashboard:index')
    
    # 🔒 Filtra apenas talhões da empresa
    if hasattr(Talhao.objects, 'da_empresa'):
        talhoes = Talhao.objects.da_empresa(empresa).select_related(
            'fazenda', 'area', 'cultura_atual'
        )
    else:
        talhoes = Talhao.objects.filter(empresa=empresa).select_related(
            'fazenda', 'area', 'cultura_atual'
        )
    
    # Busca
    q = request.GET.get('q', '').strip()
    if q:
        talhoes = talhoes.filter(
            Q(nome__icontains=q) |
            Q(codigo__icontains=q) |
            Q(fazenda__nome__icontains=q)
        )
    
    # Filtros
    fazenda_id = request.GET.get('fazenda')
    if fazenda_id:
        talhoes = talhoes.filter(fazenda_id=fazenda_id)
    
    area_id = request.GET.get('area')
    if area_id:
        talhoes = talhoes.filter(area_id=area_id)
    
    status = request.GET.get('status')
    if status:
        talhoes = talhoes.filter(status=status)
    
    # Estatísticas
    stats = {
        'total': talhoes.count(),
        'plantados': talhoes.filter(status='PLANTADO').count(),
        'disponiveis': talhoes.filter(status='DISPONIVEL').count(),
        'area_total': talhoes.aggregate(Sum('area_hac'))['area_hac__sum'] or 0,
    }
    
    # 🔒 Dados para filtros (apenas da empresa)
    fazendas = Fazenda.objects.filter(empresa=empresa, ativa=True).order_by('nome')
    if hasattr(Area.objects, 'da_empresa'):
        areas = Area.objects.da_empresa(empresa).filter(ativa=True).order_by('nome')
    else:
        areas = Area.objects.filter(empresa=empresa, ativa=True).order_by('nome')
    
    context = {
        'talhoes': talhoes,
        'fazendas': fazendas,
        'areas': areas,
        'stats': stats,
    }
    
    return render(request, 'cadastros/talhao_list.html', context)


@login_required
def talhao_create(request):
    """
    Cria novo talhão
    🔒 VINCULA AUTOMATICAMENTE À EMPRESA
    """
    empresa = request.user.empresa
    
    if not empresa:
        messages.error(request, 'Você não está vinculado a nenhuma empresa.')
        return redirect('dashboard:index')
    
    if request.method == 'POST':
        form = TalhaoForm(request.POST, user=request.user)
        if form.is_valid():
            talhao = form.save(commit=False)
            talhao.empresa = empresa  # 🔒 Vincula à empresa
            talhao.cadastrado_por = request.user
            talhao.save()
            
            messages.success(
                request,
                f'✅ Talhão "{talhao.codigo} - {talhao.nome}" cadastrado!'
            )
            return redirect('cadastros:talhao_list')
    else:
        form = TalhaoForm(user=request.user)
    
    return render(request, 'cadastros/talhao_form.html', {
        'form': form,
        'title': 'Novo Talhão'
    })


@login_required
def talhao_update(request, pk):
    """
    Edita talhão
    🔒 VERIFICA PERMISSÃO
    """
    empresa = request.user.empresa
    
    # 🔒 Busca apenas se pertencer à empresa
    talhao = get_object_or_404(
        Talhao.objects.da_empresa(empresa),
        pk=pk
    )
    
    if request.method == 'POST':
        form = TalhaoForm(request.POST, instance=talhao, user=request.user)
        if form.is_valid():
            talhao = form.save()
            messages.success(request, f'✅ Talhão "{talhao.codigo}" atualizado!')
            return redirect('cadastros:talhao_list')
    else:
        form = TalhaoForm(instance=talhao, user=request.user)
    
    return render(request, 'cadastros/talhao_form.html', {
        'form': form,
        'talhao': talhao,
        'title': f'Editar Talhão: {talhao.codigo}'
    })


@login_required
def talhao_delete(request, pk):
    """
    Exclui talhão
    🔒 VERIFICA PERMISSÃO
    """
    empresa = request.user.empresa
    
    # 🔒 Busca apenas se pertencer à empresa
    talhao = get_object_or_404(
        Talhao.objects.da_empresa(empresa),
        pk=pk
    )
    
    # Verifica se está em uso
    if talhao.status == 'PLANTADO':
        messages.error(
            request,
            '❌ Não é possível excluir talhão com cultivo ativo!'
        )
        return redirect('cadastros:talhao_list')
    
    if request.method == 'POST':
        codigo = talhao.codigo
        talhao.delete()
        messages.success(request, f'🗑️ Talhão "{codigo}" excluído!')
        return redirect('cadastros:talhao_list')
    
    return render(request, 'cadastros/talhao_confirm_delete.html', {
        'talhao': talhao
    })


@login_required
def talhao_detail(request, pk):
    """
    Detalhes do talhão com histórico
    🔒 ACESSO APENAS PARA EMPRESA DONA
    """
    empresa = request.user.empresa
    
    # 🔒 Busca apenas se pertencer à empresa
    talhao = get_object_or_404(
        Talhao.objects.da_empresa(empresa).select_related(
            'fazenda', 'area', 'cultura_atual'
        ),
        pk=pk
    )
    
    # Histórico de cultivos
    historico = talhao.historico.all().order_by('-data_plantio')[:10]
    
    # Estatísticas do histórico
    historico_stats = talhao.historico.aggregate(
        total_safras=Count('id'),
        producao_total=Sum('producao_real'),
        media_produtividade=Avg('produtividade')
    )
    
    return render(request, 'cadastros/talhao_detail.html', {
        'talhao': talhao,
        'historico': historico,
        'historico_stats': historico_stats
    })


@login_required
def historico_create(request, talhao_pk):
    """Cria um registro de histórico para um talhão (usuário da empresa)."""
    empresa = request.user.empresa
    talhao = get_object_or_404(Talhao.objects.da_empresa(empresa), pk=talhao_pk)

    if request.method == 'POST':
        form = HistoricoTalhaoForm(request.POST, user=request.user)
        if form.is_valid():
            hist = form.save(commit=False)
            hist.talhao = talhao
            hist.empresa = empresa
            hist.registrado_por = request.user
            hist.save()
            messages.success(request, f'✅ Histórico registrado para {talhao.nome}!')
            return redirect('cadastros:talhao_detail', pk=talhao.pk)
    else:
        form = HistoricoTalhaoForm(initial={'talhao': talhao}, user=request.user)

    return render(request, 'cadastros/historico_form.html', {
        'form': form,
        'talhao': talhao,
        'action': 'Registrar'
    })


@login_required
def historico_update(request, pk):
    """Edita um registro de histórico (pertence à mesma empresa)."""
    empresa = request.user.empresa
    historico = get_object_or_404(HistoricoTalhao, pk=pk, empresa=empresa)

    if request.method == 'POST':
        form = HistoricoTalhaoForm(request.POST, instance=historico, user=request.user)
        if form.is_valid():
            hist = form.save()
            messages.success(request, f'✅ Histórico atualizado!')
            return redirect('cadastros:talhao_detail', pk=hist.talhao.pk)
    else:
        form = HistoricoTalhaoForm(instance=historico, user=request.user)

    return render(request, 'cadastros/historico_form.html', {
        'form': form,
        'historico': historico,
        'action': 'Editar'
    })


@login_required
def historico_delete(request, pk):
    """Exclui um registro de histórico."""
    empresa = request.user.empresa
    historico = get_object_or_404(HistoricoTalhao, pk=pk, empresa=empresa)

    if request.method == 'POST':
        talhao_pk = historico.talhao.pk
        historico.delete()
        messages.success(request, '🗑️ Histórico excluído!')
        return redirect('cadastros:talhao_detail', pk=talhao_pk)

    return render(request, 'cadastros/historico_confirm_delete.html', {
        'historico': historico
    })


@login_required
def historico_detail(request, pk):
    """Mostra detalhes de um registro de histórico."""
    empresa = request.user.empresa
    historico = get_object_or_404(HistoricoTalhao.objects.select_related('talhao', 'cultura', 'registrado_por'), pk=pk, empresa=empresa)

    return render(request, 'cadastros/historico_detail.html', {
        'historico': historico
    })


# ============================================
# AJAX: ÁREAS POR FAZENDA
# ============================================

@login_required
def ajax_areas_por_fazenda(request, fazenda_id):
    """
    Retorna áreas de uma fazenda (para select dinâmico)
    🔒 APENAS ÁREAS DA EMPRESA DO USUÁRIO
    """
    empresa = request.user.empresa
    
    # 🔒 Valida se fazenda pertence à empresa
    try:
        fazenda = Fazenda.objects.get(pk=fazenda_id, empresa=empresa)
    except Fazenda.DoesNotExist:
        return JsonResponse({'error': 'Fazenda não encontrada'}, status=404)
    
    # 🔒 Busca apenas áreas da empresa
    areas = Area.objects.filter(
        fazenda=fazenda,
        empresa=empresa,
        ativa=True
    ).values('id', 'nome', 'area_total')
    
    return JsonResponse(list(areas), safe=False)


# ============================================
# AJAX: TALHÕES POR FAZENDA
# ============================================


@login_required
def ajax_talhoes_por_fazenda(request, fazenda_id):
    """
    Retorna talhões de uma fazenda (para select dinâmico)
    🔒 APENAS TALHÕES DA EMPRESA DO USUÁRIO
    """
    empresa = request.user.empresa

    # 🔒 Valida se fazenda pertence à empresa
    try:
        fazenda = Fazenda.objects.get(pk=fazenda_id, empresa=empresa)
    except Fazenda.DoesNotExist:
        return JsonResponse({'error': 'Fazenda não encontrada'}, status=404)

    talhoes = Talhao.objects.filter(
        fazenda=fazenda,
        empresa=empresa,
        ativo=True
    ).values('id', 'nome', 'codigo', 'area_hac')
    # Para cada talhão, informa se já está associado a uma safra não finalizada
    talhao_ids = [t['id'] for t in talhoes]
    safra_map = {}
    if talhao_ids:
        safras = Safra.objects.filter(talhoes__in=talhao_ids).exclude(status='FINALIZADA').select_related('fazenda')
        for s in safras:
            for t in s.talhoes.all():
                if t.id in talhao_ids and t.id not in safra_map:
                    safra_map[t.id] = str(s)

    result = []
    for t in talhoes:
        tid = t['id']
        result.append({
            'id': tid,
            'nome': t['nome'],
            'codigo': t.get('codigo'),
            'area_hac': t.get('area_hac'),
            'in_use': tid in safra_map,
            'in_use_by': safra_map.get(tid)
        })

    return JsonResponse(result, safe=False)