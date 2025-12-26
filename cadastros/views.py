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
from .forms import ComissaoVendedorForm, FuncionarioForm, FuncaoFuncionarioForm, VendedorFiltroForm

from .models import (
    Fazenda, EnderecoFazenda, ContatoFazenda,
    ContaBancariaFazenda, DocumentoFazenda
)
from .forms import (
    FazendaForm, EnderecoFazendaForm, ContatoFazendaForm,
    ContaBancariaFazendaForm, DocumentoFazendaForm,
)

from .models import Area, Talhao, Cultura, HistoricoTalhao, Safra, Vendedor, ComissaoVendedor
from .forms import AreaForm, TalhaoForm, CulturaForm, HistoricoTalhaoForm, SafraForm,VendedorForm




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

# cadastros/views.py

@login_required
def safra_create(request):
    empresa = request.user.empresa
    if not empresa:
        messages.warning(request, 'Você não está vinculado a nenhuma empresa.')
        return render(request, 'cadastros/safra_form.html', {'empresa_missing': True, 'action': 'Cadastrar'})

    if request.method == 'POST':
        # 🔥 DEBUG
        print("=" * 80)
        print("📋 CRIAÇÃO DE SAFRA - DEBUG")
        print("=" * 80)
        print(f"POST completo: {request.POST}")
        print(f"Talhões raw: '{request.POST.get('talhoes', '')}'")
        print("=" * 80)
        
        form = SafraForm(request.POST, user=request.user)
        
        if form.is_valid():
            print("✅ Form é VÁLIDO")
            
            try:
                # Salva a safra
                safra = form.save(commit=False)
                safra.cadastrado_por = request.user
                safra.save()
                
                print(f"✅ Safra {safra.pk} salva no banco")
                
                # Processa talhões
                talhoes_ids = request.POST.get('talhoes', '').strip()
                print(f"📋 Talhões IDs do POST: '{talhoes_ids}'")
                
                if talhoes_ids:
                    try:
                        # Converte string para lista de IDs
                        talhao_ids_list = [int(tid.strip()) for tid in talhoes_ids.split(',') if tid.strip()]
                        print(f"📋 IDs parseados: {talhao_ids_list}")
                        
                        if not talhao_ids_list:
                            print("⚠️ Lista de IDs vazia após parse")
                        
                        # Busca talhões
                        talhoes = Talhao.objects.filter(
                            id__in=talhao_ids_list,
                            empresa=empresa,
                            ativo=True
                        )
                        
                        print(f"📋 Talhões encontrados no banco: {talhoes.count()}")
                        for t in talhoes:
                            print(f"  - {t.id}: {t.codigo} ({t.fazenda.nome})")
                        
                        # Valida fazenda
                        invalidos = []
                        for talhao in talhoes:
                            if talhao.fazenda != safra.fazenda:
                                invalidos.append(f"{talhao.codigo} (fazenda diferente)")
                        
                        if invalidos:
                            print(f"❌ Talhões inválidos: {invalidos}")
                            messages.error(request, f'❌ Talhões não pertencem à fazenda: {", ".join(invalidos)}')
                            safra.delete()
                            return render(request, 'cadastros/safra_form.html', {'form': form, 'action': 'Cadastrar'})
                        
                        # Valida conflitos
                        conflitos = []
                        for talhao in talhoes:
                            safras_conflito = Safra.objects.filter(
                                talhoes=talhao
                            ).exclude(
                                status='FINALIZADA'
                            ).exclude(
                                pk=safra.pk
                            )
                            
                            if safras_conflito.exists():
                                conflitos.append(f"{talhao.codigo} (em {safras_conflito.first()})")
                        
                        if conflitos:
                            print(f"❌ Conflitos encontrados: {conflitos}")
                            messages.error(request, f'❌ Talhões já estão em uso: {", ".join(conflitos)}')
                            safra.delete()
                            return render(request, 'cadastros/safra_form.html', {'form': form, 'action': 'Cadastrar'})
                        
                        # Limpa e associa
                        safra.talhoes.clear()
                        safra.talhoes.set(talhoes)
                        
                        print(f"✅ {talhoes.count()} talhões associados com sucesso")
                        print(f"   Talhões na safra: {[t.codigo for t in safra.talhoes.all()]}")
                        
                    except ValueError as e:
                        print(f"❌ Erro ao parsear IDs: {e}")
                        messages.error(request, f'❌ IDs de talhões inválidos: {e}')
                        safra.delete()
                        return render(request, 'cadastros/safra_form.html', {'form': form, 'action': 'Cadastrar'})
                    
                    except Exception as e:
                        print(f"❌ Erro inesperado: {e}")
                        import traceback
                        traceback.print_exc()
                        messages.error(request, f'❌ Erro ao processar talhões: {e}')
                        safra.delete()
                        return render(request, 'cadastros/safra_form.html', {'form': form, 'action': 'Cadastrar'})
                else:
                    print("⚠️ Nenhum talhão selecionado")
                
                total_talhoes = safra.talhoes.count()
                messages.success(request, f'✅ Safra "{safra}" cadastrada com {total_talhoes} talhão(ões)!')
                return redirect('cadastros:safra_detail', pk=safra.pk)
                
            except Exception as e:
                print(f"❌ Erro ao salvar safra: {e}")
                import traceback
                traceback.print_exc()
                messages.error(request, f'❌ Erro ao salvar: {e}')
                
        else:
            print("❌ Form INVÁLIDO")
            print(f"Erros: {form.errors}")
            print(f"Non-field errors: {form.non_field_errors()}")
            for field, errors in form.errors.items():
                print(f"  {field}: {errors}")
            
            messages.error(request, f'❌ Corrija os erros no formulário: {form.errors}')
    else:
        form = SafraForm(user=request.user)

    return render(request, 'cadastros/safra_form.html', {'form': form, 'action': 'Cadastrar'})


@login_required
def safra_update(request, pk):
    safra = get_object_or_404(Safra, pk=pk, fazenda__empresa=request.user.empresa)
    empresa = request.user.empresa
    
    if request.method == 'POST':
        # 🔥 DEBUG
        print("=" * 80)
        print("📋 EDIÇÃO DE SAFRA - DEBUG")
        print("=" * 80)
        print(f"Safra ID: {safra.pk}")
        print(f"POST completo: {request.POST}")
        print(f"Talhões raw: '{request.POST.get('talhoes', '')}'")
        print("=" * 80)
        
        form = SafraForm(request.POST, instance=safra, user=request.user)
        
        if form.is_valid():
            print("✅ Form é VÁLIDO")
            
            try:
                safra = form.save()
                print(f"✅ Safra {safra.pk} atualizada")
                
                # Processa talhões
                talhoes_ids = request.POST.get('talhoes', '').strip()
                print(f"📋 Talhões IDs: '{talhoes_ids}'")
                
                # Limpa relacionamento
                safra.talhoes.clear()
                
                if talhoes_ids:
                    try:
                        talhao_ids_list = [int(tid.strip()) for tid in talhoes_ids.split(',') if tid.strip()]
                        print(f"📋 IDs parseados: {talhao_ids_list}")
                        
                        talhoes = Talhao.objects.filter(
                            id__in=talhao_ids_list,
                            empresa=empresa,
                            ativo=True
                        )
                        
                        print(f"📋 Talhões encontrados: {talhoes.count()}")
                        
                        # Valida fazenda
                        invalidos = []
                        for talhao in talhoes:
                            if talhao.fazenda != safra.fazenda:
                                invalidos.append(f"{talhao.codigo}")
                        
                        if invalidos:
                            messages.error(request, f'❌ Talhões não pertencem à fazenda: {", ".join(invalidos)}')
                            return render(request, 'cadastros/safra_form.html', {
                                'form': form, 
                                'safra': safra, 
                                'action': 'Editar'
                            })
                        
                        # Valida conflitos
                        conflitos = []
                        for talhao in talhoes:
                            safras_conflito = Safra.objects.filter(
                                talhoes=talhao
                            ).exclude(
                                status='FINALIZADA'
                            ).exclude(
                                pk=safra.pk
                            )
                            
                            if safras_conflito.exists():
                                conflitos.append(f"{talhao.codigo}")
                        
                        if conflitos:
                            messages.error(request, f'❌ Talhões já estão em uso: {", ".join(conflitos)}')
                            return render(request, 'cadastros/safra_form.html', {
                                'form': form,
                                'safra': safra,
                                'action': 'Editar'
                            })
                        
                        safra.talhoes.set(talhoes)
                        print(f"✅ {talhoes.count()} talhões associados")
                        
                    except Exception as e:
                        print(f"❌ Erro ao processar: {e}")
                        import traceback
                        traceback.print_exc()
                        messages.error(request, f'❌ Erro: {e}')
                
                total = safra.talhoes.count()
                messages.success(request, f'✅ Safra atualizada com {total} talhão(ões)!')
                return redirect('cadastros:safra_detail', pk=safra.pk)
                
            except Exception as e:
                print(f"❌ Erro: {e}")
                import traceback
                traceback.print_exc()
                messages.error(request, f'❌ Erro: {e}')
        else:
            print("❌ Form INVÁLIDO")
            print(f"Erros: {form.errors}")
            messages.error(request, f'❌ Corrija os erros: {form.errors}')
    else:
        form = SafraForm(instance=safra, user=request.user)

    return render(request, 'cadastros/safra_form.html', {
        'form': form, 
        'safra': safra, 'action': 'Editar'
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

# cadastros/views.py - Localize e SUBSTITUA a função talhao_list

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
        ).prefetch_related('safras')
    else:
        talhoes = Talhao.objects.filter(empresa=empresa).select_related(
            'fazenda', 'area', 'cultura_atual'
        ).prefetch_related('safras')
    
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
    
    # 🔥 NOVO: Adiciona informação da safra ativa para cada talhão
    talhoes_list = list(talhoes)  # Converte para lista para poder modificar
    for talhao in talhoes_list:
        # Busca safra ativa (não finalizada) associada ao talhão
        safra_ativa = talhao.safras.filter(
            status__in=['PLANEJADA', 'EM_ANDAMENTO']
        ).select_related('cultura').first()
        
        # Anexa a safra e cultura ao objeto talhão
        talhao.safra_ativa = safra_ativa
        if safra_ativa:
            talhao.cultura_safra = safra_ativa.cultura
            talhao.safra_nome = str(safra_ativa)
        else:
            talhao.cultura_safra = None
            talhao.safra_nome = None
    
    # 🔒 Dados para filtros (apenas da empresa)
    fazendas = Fazenda.objects.filter(empresa=empresa, ativa=True).order_by('nome')
    if hasattr(Area.objects, 'da_empresa'):
        areas = Area.objects.da_empresa(empresa).filter(ativa=True).order_by('nome')
    else:
        areas = Area.objects.filter(empresa=empresa, ativa=True).order_by('nome')
    
    context = {
        'talhoes': talhoes_list,
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
            try:
                talhao = form.save(commit=False)
                talhao.empresa = empresa  # 🔒 Vincula à empresa
                talhao.cadastrado_por = request.user
                
                # 🔥 GARANTIA: area_hac já foi setado pelo form.save(), mas vamos garantir
                area_tamanho = form.cleaned_data.get('area_tamanho')
                if area_tamanho and not talhao.area_hac:
                    talhao.area_hac = area_tamanho
                
                talhao.save()
                
                messages.success(
                    request,
                    f'✅ Talhão "{talhao.codigo} - {talhao.nome}" cadastrado com {talhao.area_hac} ha!'
                )
                return redirect('cadastros:talhao_list')
            except Exception as e:
                messages.error(request, f'❌ Erro ao salvar talhão: {e}')
                print(f"❌ Erro detalhado: {e}")
                import traceback
                traceback.print_exc()
        else:
            messages.error(request, '❌ Corrija os erros no formulário')
            print(f"❌ Erros do form: {form.errors}")
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
            messages.success(request, '✅ Histórico atualizado!')
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



"""
ADICIONAR ESTE CÓDIGO AO FINAL DO ARQUIVO: cadastros/views.py

Certifique-se de ter os imports corretos no topo do arquivo
"""

# ========================================================================
# VIEWS DE VENDEDORES
# ========================================================================

@login_required
def vendedor_list(request):
    """Lista vendedores da empresa com filtros"""
    empresa = request.user.empresa
    
    if not empresa:
        messages.error(request, '❌ Você não está vinculado a nenhuma empresa.')
        return redirect('dashboard:index')
    
    filtro_form = VendedorFiltroForm(request.GET or None)
    vendedores = Vendedor.objects.filter(empresa=empresa).select_related('supervisor', 'empresa')
    
    if filtro_form.is_valid():
        busca = filtro_form.cleaned_data.get('busca')
        status = filtro_form.cleaned_data.get('status')
        tipo_mercado = filtro_form.cleaned_data.get('tipo_mercado')
        
        if busca:
            vendedores = vendedores.filter(
                Q(nome_completo__icontains=busca) |
                Q(cpf__icontains=busca) |
                Q(email_corporativo__icontains=busca)
            )
        
        if status:
            vendedores = vendedores.filter(status=status)
        
        if tipo_mercado:
            vendedores = vendedores.filter(tipo_mercado=tipo_mercado)
    
    total_vendedores = vendedores.count()
    total_ativos = vendedores.filter(status='ATIVO').count()
    total_mercado_interno = vendedores.filter(tipo_mercado__in=['INTERNO', 'AMBOS']).count()
    total_exportacao = vendedores.filter(tipo_mercado__in=['EXTERNO', 'AMBOS']).count()
    
    context = {
        'vendedores': vendedores,
        'filtro_form': filtro_form,
        'total_vendedores': total_vendedores,
        'total_ativos': total_ativos,
        'total_mercado_interno': total_mercado_interno,
        'total_exportacao': total_exportacao,
    }
    
    return render(request, 'cadastros/vendedor_list.html', context)


@login_required
def vendedor_create(request):
    """Cria novo vendedor"""
    empresa = request.user.empresa
    
    if not empresa:
        messages.error(request, '❌ Você não está vinculado a nenhuma empresa.')
        return redirect('dashboard:index')
    
    if request.method == 'POST':
        form = VendedorForm(request.POST, request.FILES, user=request.user, empresa=empresa)
        if form.is_valid():
            vendedor = form.save()
            messages.success(request, f"✅ Vendedor '{vendedor.nome_completo}' cadastrado com sucesso!")
            return redirect('cadastros:vendedor_list')
        else:
            messages.error(request, '❌ Corrija os erros no formulário.')
    else:
        form = VendedorForm(user=request.user, empresa=empresa)
    
    context = {
        'form': form,
        'action': 'Criar',
        'title': 'Novo Vendedor'
    }
    
    return render(request, 'cadastros/vendedor_form.html', context)


@login_required
def vendedor_update(request, pk):
    """Edita vendedor existente"""
    empresa = request.user.empresa
    
    if not empresa:
        messages.error(request, '❌ Você não está vinculado a nenhuma empresa.')
        return redirect('dashboard:index')
    
    vendedor = get_object_or_404(Vendedor, pk=pk, empresa=empresa)
    
    if request.method == 'POST':
        form = VendedorForm(request.POST, request.FILES, instance=vendedor, user=request.user, empresa=empresa)
        if form.is_valid():
            vendedor = form.save()
            messages.success(request, f"✅ Vendedor '{vendedor.nome_completo}' atualizado com sucesso!")
            return redirect('cadastros:vendedor_list')
        else:
            messages.error(request, '❌ Corrija os erros no formulário.')
    else:
        form = VendedorForm(instance=vendedor, user=request.user, empresa=empresa)
    
    context = {
        'form': form,
        'vendedor': vendedor,
        'action': 'Editar',
        'title': f'Editar: {vendedor.get_nome_curto()}'
    }
    
    return render(request, 'cadastros/vendedor_form.html', context)


@login_required
def vendedor_detail(request, pk):
    """Exibe detalhes do vendedor"""
    empresa = request.user.empresa
    
    if not empresa:
        messages.error(request, '❌ Você não está vinculado a nenhuma empresa.')
        return redirect('dashboard:index')
    
    vendedor = get_object_or_404(Vendedor.objects.select_related('supervisor', 'empresa'), pk=pk, empresa=empresa)
    
    subordinados = vendedor.subordinados.filter(status='ATIVO')
    
    comissoes_pendentes = vendedor.comissoes.filter(status='PENDENTE').aggregate(
        total=Sum('valor_comissao')
    )['total'] or 0
    
    comissoes_pagas = vendedor.comissoes.filter(status='PAGA').aggregate(
        total=Sum('valor_comissao')
    )['total'] or 0
    
    ultimas_comissoes = vendedor.comissoes.all().order_by('-referencia_mes')[:5]
    
    context = {
        'vendedor': vendedor,
        'subordinados': subordinados,
        'comissoes_pendentes': comissoes_pendentes,
        'comissoes_pagas': comissoes_pagas,
        'ultimas_comissoes': ultimas_comissoes,
    }
    
    return render(request, 'cadastros/vendedor_detail.html', context)


@login_required
def vendedor_delete(request, pk):
    """Exclui vendedor (com confirmação)"""
    empresa = request.user.empresa
    
    if not empresa:
        messages.error(request, '❌ Você não está vinculado a nenhuma empresa.')
        return redirect('dashboard:index')
    
    vendedor = get_object_or_404(Vendedor, pk=pk, empresa=empresa)
    
    if vendedor.subordinados.exists():
        messages.error(
            request,
            f"❌ Não é possível excluir! O vendedor '{vendedor.nome_completo}' possui "
            f"{vendedor.get_total_subordinados()} subordinado(s). Reatribua-os primeiro."
        )
        return redirect('cadastros:vendedor_list')
    
    comissoes_pendentes = vendedor.comissoes.filter(status='PENDENTE').count()
    if comissoes_pendentes > 0:
        messages.error(
            request,
            f"❌ Não é possível excluir! O vendedor possui {comissoes_pendentes} "
            f"comissão(ões) pendente(s). Resolva-as primeiro."
        )
        return redirect('cadastros:vendedor_list')
    
    if request.method == 'POST':
        nome = vendedor.nome_completo
        vendedor.delete()
        messages.success(request, f"🗑️ Vendedor '{nome}' excluído com sucesso!")
        return redirect('cadastros:vendedor_list')
    
    context = {'vendedor': vendedor}
    return render(request, 'cadastros/vendedor_confirm_delete.html', context)


@login_required
def vendedor_inativar(request, pk):
    """Inativa vendedor (sem excluir)"""
    empresa = request.user.empresa
    
    if not empresa:
        messages.error(request, '❌ Você não está vinculado a nenhuma empresa.')
        return redirect('dashboard:index')
    
    vendedor = get_object_or_404(Vendedor, pk=pk, empresa=empresa)
    
    if vendedor.status == 'ATIVO':
        vendedor.status = 'INATIVO'
        vendedor.data_desligamento = timezone.now().date()
        vendedor.save()
        messages.success(request, f"✅ Vendedor '{vendedor.nome_completo}' inativado com sucesso!")
    else:
        messages.warning(request, f"⚠️ Vendedor '{vendedor.nome_completo}' já está inativo.")
    
    return redirect('cadastros:vendedor_list')


@login_required
def vendedor_reativar(request, pk):
    """Reativa vendedor"""
    empresa = request.user.empresa
    
    if not empresa:
        messages.error(request, '❌ Você não está vinculado a nenhuma empresa.')
        return redirect('dashboard:index')
    
    vendedor = get_object_or_404(Vendedor, pk=pk, empresa=empresa)
    
    if vendedor.status == 'INATIVO':
        vendedor.status = 'ATIVO'
        vendedor.data_desligamento = None
        vendedor.save()
        messages.success(request, f"✅ Vendedor '{vendedor.nome_completo}' reativado com sucesso!")
    else:
        messages.warning(request, f"⚠️ Vendedor '{vendedor.nome_completo}' já está ativo.")
    
    return redirect('cadastros:vendedor_list')


# ========== COMISSÕES (PREPARADO PARA MÓDULO FINANCEIRO) ==========

@login_required
def comissao_list(request):
    """Lista comissões de vendedores"""
    empresa = request.user.empresa
    
    if not empresa:
        messages.error(request, '❌ Você não está vinculado a nenhuma empresa.')
        return redirect('dashboard:index')
    
    comissoes = ComissaoVendedor.objects.filter(empresa=empresa).select_related('vendedor')
    
    status = request.GET.get('status')
    vendedor_id = request.GET.get('vendedor')
    
    if status:
        comissoes = comissoes.filter(status=status)
    
    if vendedor_id:
        comissoes = comissoes.filter(vendedor_id=vendedor_id)
    
    total_pendente = comissoes.filter(status='PENDENTE').aggregate(
        total=Sum('valor_comissao')
    )['total'] or 0
    
    total_pago = comissoes.filter(status='PAGA').aggregate(
        total=Sum('valor_comissao')
    )['total'] or 0
    
    context = {
        'comissoes': comissoes.order_by('-referencia_mes'),
        'total_pendente': total_pendente,
        'total_pago': total_pago,
        'vendedores': Vendedor.objects.filter(empresa=empresa, status='ATIVO'),
    }
    
    return render(request, 'cadastros/comissao_list.html', context)


@login_required
def comissao_create(request):
    """Registra nova comissão"""
    empresa = request.user.empresa
    
    if not empresa:
        messages.error(request, '❌ Você não está vinculado a nenhuma empresa.')
        return redirect('dashboard:index')
    
    if request.method == 'POST':
        form = ComissaoVendedorForm(request.POST, empresa=empresa)
        if form.is_valid():
            comissao = form.save(commit=False)
            comissao.empresa = empresa
            comissao.save()
            messages.success(request, '✅ Comissão registrada com sucesso!')
            return redirect('cadastros:comissao_list')
    else:
        form = ComissaoVendedorForm(empresa=empresa)
    
    context = {
        'form': form,
        'title': 'Registrar Comissão'
    }
    
    return render(request, 'cadastros/comissao_form.html', context)


@login_required
def comissao_pagar(request, pk):
    """Marca comissão como paga"""
    empresa = request.user.empresa
    
    if not empresa:
        messages.error(request, '❌ Você não está vinculado a nenhuma empresa.')
        return redirect('dashboard:index')
    
    comissao = get_object_or_404(ComissaoVendedor, pk=pk, empresa=empresa)
    
    if comissao.status == 'PENDENTE':
        comissao.status = 'PAGA'
        comissao.data_pagamento = timezone.now().date()
        comissao.save()
        messages.success(request, f"✅ Comissão de R$ {comissao.valor_comissao:.2f} paga com sucesso!")
    else:
        messages.warning(request, '⚠️ Esta comissão já foi paga.')
    
    return redirect('cadastros:comissao_list')


# ========== APIS/AJAX ==========

@login_required
def vendedor_json(request):
    """Retorna vendedores em JSON para uso em formulários"""
    empresa = request.user.empresa
    
    if not empresa:
        return JsonResponse({'error': 'Empresa não encontrada'}, status=400)
    
    vendedores = Vendedor.objects.filter(
        empresa=empresa,
        status='ATIVO'
    ).values('id', 'nome_completo', 'email_corporativo', 'tipo_mercado')
    
    return JsonResponse(list(vendedores), safe=False)


"""
========================================
CÓDIGO PARA ADICIONAR AO cadastros/views.py
========================================

INSTRUÇÕES:
1. Abra o arquivo cadastros/views.py
2. Vá até o FINAL do arquivo
3. Cole este código completo
4. Salve o arquivo

Este código adiciona:
- CRUD completo de Fornecedores
- Busca CNPJ (ReceitaWS API)
- Busca CEP (ViaCEP API)
- Filtros e pesquisa
- AJAX para tabelas dinâmicas
"""

import requests
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.template.loader import render_to_string

from .models import (
    Fornecedor, FornecedorEndereco, FornecedorContato,
    FornecedorDadoBancario, FornecedorDocumento, FornecedorAvaliacao,
    CategoriaFornecedor, SubcategoriaFornecedor
)
from .forms import (
    FornecedorForm, FornecedorEnderecoForm, FornecedorContatoForm,
    FornecedorDadoBancarioForm, FornecedorDocumentoForm, FornecedorAvaliacaoForm,
    CategoriaFornecedorForm, SubcategoriaFornecedorForm
)


# ============================================
# FORNECEDORES - CRUD PRINCIPAL
# ============================================

@login_required
def fornecedor_list(request):
    """Lista fornecedores da empresa com filtros e pesquisa"""
    
    empresa = request.user.empresa
    if not empresa:
        messages.warning(request, "Você precisa estar vinculado a uma empresa.")
        return redirect('dashboard:index')
    
    # Busca e filtros
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')
    categoria = request.GET.get('categoria', '')
    tipo = request.GET.get('tipo', '')
    
    # QuerySet base
    fornecedores = Fornecedor.objects.filter(empresa=empresa).select_related('empresa').prefetch_related('categorias')
    
    # Aplicar filtros
    if q:
        fornecedores = fornecedores.filter(
            Q(razao_social__icontains=q) |
            Q(nome_fantasia__icontains=q) |
            Q(cnpj_cpf__icontains=q)
        )
    
    if status:
        fornecedores = fornecedores.filter(status=status)
    
    if categoria:
        fornecedores = fornecedores.filter(categorias__id=categoria)
    
    if tipo:
        fornecedores = fornecedores.filter(tipo_fornecedor=tipo)
    
    # Ordenação
    fornecedores = fornecedores.order_by('-data_cadastro')
    
    # AJAX para tabela dinâmica
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        html = render_to_string('cadastros/fornecedor/_fornecedor_table.html', {
            'fornecedores': fornecedores
        }, request=request)
        return JsonResponse({'html': html})
    
    # Dados para filtros
    categorias = CategoriaFornecedor.objects.filter(
        Q(empresa=empresa) | Q(empresa__isnull=True),
        ativa=True
    )
    
    context = {
        'fornecedores': fornecedores,
        'categorias': categorias,
        'q': q,
        'status_atual': status,
        'categoria_atual': categoria,
        'tipo_atual': tipo,
    }
    
    return render(request, 'cadastros/fornecedor/fornecedor_list.html', context)


@login_required
def fornecedor_create(request):
    """Criar novo fornecedor"""
    
    if request.method == 'POST':
        form = FornecedorForm(request.POST, user=request.user)
        if form.is_valid():
            fornecedor = form.save()
            messages.success(request, f"✅ Fornecedor '{fornecedor.razao_social}' cadastrado com sucesso!")
            return redirect('cadastros:fornecedor_detail', pk=fornecedor.pk)
        else:
            messages.error(request, "❌ Corrija os erros no formulário.")
    else:
        form = FornecedorForm(user=request.user)
    
    return render(request, 'cadastros/fornecedor/fornecedor_form.html', {
        'form': form,
        'action': 'Novo',
        'title': 'Novo Fornecedor'
    })


@login_required
def fornecedor_update(request, pk):
    """Editar fornecedor existente"""
    
    fornecedor = get_object_or_404(Fornecedor, pk=pk, empresa=request.user.empresa)
    
    if request.method == 'POST':
        form = FornecedorForm(request.POST, instance=fornecedor, user=request.user)
        if form.is_valid():
            fornecedor = form.save()
            messages.success(request, f"✅ Fornecedor '{fornecedor.razao_social}' atualizado com sucesso!")
            return redirect('cadastros:fornecedor_detail', pk=fornecedor.pk)
        else:
            messages.error(request, "❌ Corrija os erros no formulário.")
    else:
        form = FornecedorForm(instance=fornecedor, user=request.user)
    
    return render(request, 'cadastros/fornecedor/fornecedor_form.html', {
        'form': form,
        'fornecedor': fornecedor,
        'action': 'Editar',
        'title': f'Editar: {fornecedor.razao_social}'
    })


@login_required
def fornecedor_detail(request, pk):
    """Visualizar detalhes do fornecedor"""
    
    fornecedor = get_object_or_404(
        Fornecedor.objects.select_related('empresa', 'cadastrado_por')
                          .prefetch_related('categorias', 'subcategorias', 'enderecos', 
                                          'contatos', 'dados_bancarios', 'documentos', 'avaliacoes'),
        pk=pk,
        empresa=request.user.empresa
    )
    
    # Estatísticas
    total_avaliacoes = fornecedor.avaliacoes.count()
    avaliacoes_recentes = fornecedor.avaliacoes.order_by('-data_avaliacao')[:5]
    
    # Status de documentação
    status_docs = fornecedor.get_status_documentacao()
    docs_obrigatorios = fornecedor.documentos.filter(obrigatorio=True)
    docs_vencidos = docs_obrigatorios.filter(status='VENCIDO').count()
    
    context = {
        'fornecedor': fornecedor,
        'total_avaliacoes': total_avaliacoes,
        'avaliacoes_recentes': avaliacoes_recentes,
        'status_docs': status_docs,
        'docs_vencidos': docs_vencidos,
    }
    
    return render(request, 'cadastros/fornecedor/fornecedor_detail.html', context)


@login_required
def fornecedor_delete(request, pk):
    """Excluir fornecedor"""
    
    fornecedor = get_object_or_404(Fornecedor, pk=pk, empresa=request.user.empresa)
    
    # Verifica se tem pedidos vinculados (futuro)
    # if fornecedor.pedidos.exists():
    #     messages.error(request, "❌ Não é possível excluir! Existem pedidos vinculados a este fornecedor.")
    #     return redirect('cadastros:fornecedor_detail', pk=pk)
    
    if request.method == 'POST':
        razao_social = fornecedor.razao_social
        fornecedor.delete()
        messages.success(request, f"🗑️ Fornecedor '{razao_social}' excluído com sucesso!")
        return redirect('cadastros:fornecedor_list')
    
    return render(request, 'cadastros/fornecedor/fornecedor_confirm_delete.html', {
        'fornecedor': fornecedor
    })


# ============================================
# APIs AUXILIARES - BUSCA CNPJ E CEP
# ============================================

@login_required
def buscar_cnpj(request):
    """
    API para buscar dados do CNPJ na ReceitaWS
    Retorna dados para preenchimento automático do formulário
    """
    
    if request.method != 'POST':
        return JsonResponse({'sucesso': False, 'erro': 'Método não permitido'}, status=405)
    
    cnpj = request.POST.get('cnpj', '').strip()
    
    # Remove formatação
    cnpj_limpo = cnpj.replace('.', '').replace('/', '').replace('-', '')
    
    if len(cnpj_limpo) != 14:
        return JsonResponse({
            'sucesso': False,
            'erro': 'CNPJ deve ter 14 dígitos'
        })
    
    try:
        # Chamada à API ReceitaWS
        url = f'https://receitaws.com.br/v1/cnpj/{cnpj_limpo}'
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            return JsonResponse({
                'sucesso': False,
                'erro': 'Erro ao consultar CNPJ. Tente novamente.'
            })
        
        data = response.json()
        
        # Verifica se retornou erro
        if data.get('status') == 'ERROR':
            return JsonResponse({
                'sucesso': False,
                'erro': data.get('message', 'CNPJ não encontrado')
            })
        
        # Extrai dados
        dados_fornecedor = {
            'razao_social': data.get('nome', ''),
            'nome_fantasia': data.get('fantasia', ''),
            'telefone': data.get('telefone', '').replace('/', '').strip(),
            'email': data.get('email', ''),
            'situacao': data.get('situacao', ''),
            
            # Dados de endereço
            'logradouro': data.get('logradouro', ''),
            'numero': data.get('numero', ''),
            'complemento': data.get('complemento', ''),
            'bairro': data.get('bairro', ''),
            'cidade': data.get('municipio', ''),
            'uf': data.get('uf', ''),
            'cep': data.get('cep', '').replace('.', '').replace('-', ''),
        }
        
        return JsonResponse({
            'sucesso': True,
            'dados': dados_fornecedor
        })
    
    except requests.Timeout:
        return JsonResponse({
            'sucesso': False,
            'erro': 'Tempo de consulta excedido. Tente novamente.'
        })
    except Exception as e:
        return JsonResponse({
            'sucesso': False,
            'erro': f'Erro ao buscar CNPJ: {str(e)}'
        })


@login_required
def buscar_cep(request):
    """
    API para buscar endereço pelo CEP usando ViaCEP
    Retorna dados para preenchimento automático do formulário de endereço
    """
    
    if request.method != 'GET':
        return JsonResponse({'sucesso': False, 'erro': 'Método não permitido'}, status=405)
    
    cep = request.GET.get('cep', '').strip()
    
    # Remove formatação
    cep_limpo = cep.replace('-', '').replace('.', '')
    
    if len(cep_limpo) != 8:
        return JsonResponse({
            'sucesso': False,
            'erro': 'CEP deve ter 8 dígitos'
        })
    
    try:
        # Chamada à API ViaCEP
        url = f'https://viacep.com.br/ws/{cep_limpo}/json/'
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            return JsonResponse({
                'sucesso': False,
                'erro': 'Erro ao consultar CEP. Tente novamente.'
            })
        
        data = response.json()
        
        # Verifica se retornou erro
        if data.get('erro'):
            return JsonResponse({
                'sucesso': False,
                'erro': 'CEP não encontrado'
            })
        
        # Extrai dados
        dados_endereco = {
            'logradouro': data.get('logradouro', ''),
            'bairro': data.get('bairro', ''),
            'cidade': data.get('localidade', ''),
            'uf': data.get('uf', ''),
            'complemento': data.get('complemento', ''),
        }
        
        return JsonResponse({
            'sucesso': True,
            'dados': dados_endereco
        })
    
    except requests.Timeout:
        return JsonResponse({
            'sucesso': False,
            'erro': 'Tempo de consulta excedido. Tente novamente.'
        })
    except Exception as e:
        return JsonResponse({
            'sucesso': False,
            'erro': f'Erro ao buscar CEP: {str(e)}'
        })


# ============================================
# AJAX - SUBCATEGORIAS DINÂMICAS
# ============================================

@login_required
def ajax_subcategorias_por_categoria(request):
    """
    Retorna subcategorias filtradas por categoria
    Usado em formulários com seleção dinâmica
    """
    
    categoria_id = request.GET.get('categoria_id')
    
    if not categoria_id:
        return JsonResponse({'subcategorias': []})
    
    try:
        subcategorias = SubcategoriaFornecedor.objects.filter(
            categoria_id=categoria_id,
            ativa=True
        ).values('id', 'nome')
        
        return JsonResponse({
            'subcategorias': list(subcategorias)
        })
    except Exception as e:
        return JsonResponse({
            'erro': str(e)
        }, status=400)


# ============================================
# FORNECEDOR - ENDEREÇOS
# ============================================

@login_required
def fornecedor_endereco_create(request, fornecedor_pk):
    """Adicionar novo endereço ao fornecedor"""
    
    fornecedor = get_object_or_404(Fornecedor, pk=fornecedor_pk, empresa=request.user.empresa)
    
    if request.method == 'POST':
        form = FornecedorEnderecoForm(request.POST)
        if form.is_valid():
            endereco = form.save(commit=False)
            endereco.fornecedor = fornecedor
            endereco.save()
            messages.success(request, "✅ Endereço adicionado com sucesso!")
            return redirect('cadastros:fornecedor_detail', pk=fornecedor.pk)
        else:
            messages.error(request, "❌ Corrija os erros no formulário.")
    else:
        form = FornecedorEnderecoForm()
    
    return render(request, 'cadastros/fornecedor/fornecedor_endereco_form.html', {
        'form': form,
        'fornecedor': fornecedor,
        'action': 'Adicionar'
    })


@login_required
def fornecedor_endereco_update(request, pk):
    """Editar endereço do fornecedor"""
    
    endereco = get_object_or_404(FornecedorEndereco, pk=pk, fornecedor__empresa=request.user.empresa)
    
    if request.method == 'POST':
        form = FornecedorEnderecoForm(request.POST, instance=endereco)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Endereço atualizado com sucesso!")
            return redirect('cadastros:fornecedor_detail', pk=endereco.fornecedor.pk)
        else:
            messages.error(request, "❌ Corrija os erros no formulário.")
    else:
        form = FornecedorEnderecoForm(instance=endereco)
    
    return render(request, 'cadastros/fornecedor/fornecedor_endereco_form.html', {
        'form': form,
        'endereco': endereco,
        'fornecedor': endereco.fornecedor,
        'action': 'Editar'
    })


@login_required
def fornecedor_endereco_delete(request, pk):
    """Excluir endereço do fornecedor"""
    
    endereco = get_object_or_404(FornecedorEndereco, pk=pk, fornecedor__empresa=request.user.empresa)
    fornecedor = endereco.fornecedor
    
    if request.method == 'POST':
        endereco.delete()
        messages.success(request, "🗑️ Endereço excluído com sucesso!")
        return redirect('cadastros:fornecedor_detail', pk=fornecedor.pk)
    
    return render(request, 'cadastros/fornecedor/fornecedor_endereco_confirm_delete.html', {
        'endereco': endereco,
        'fornecedor': fornecedor
    })


# ============================================
# FORNECEDOR - CONTATOS
# ============================================

@login_required
def fornecedor_contato_create(request, fornecedor_pk):
    """Adicionar novo contato ao fornecedor"""
    
    fornecedor = get_object_or_404(Fornecedor, pk=fornecedor_pk, empresa=request.user.empresa)
    
    if request.method == 'POST':
        form = FornecedorContatoForm(request.POST)
        if form.is_valid():
            contato = form.save(commit=False)
            contato.fornecedor = fornecedor
            contato.save()
            messages.success(request, "✅ Contato adicionado com sucesso!")
            return redirect('cadastros:fornecedor_detail', pk=fornecedor.pk)
        else:
            messages.error(request, "❌ Corrija os erros no formulário.")
    else:
        form = FornecedorContatoForm()
    
    return render(request, 'cadastros/fornecedor/fornecedor_contato_form.html', {
        'form': form,
        'fornecedor': fornecedor,
        'action': 'Adicionar'
    })


@login_required
def fornecedor_contato_update(request, pk):
    """Editar contato do fornecedor"""
    
    contato = get_object_or_404(FornecedorContato, pk=pk, fornecedor__empresa=request.user.empresa)
    
    if request.method == 'POST':
        form = FornecedorContatoForm(request.POST, instance=contato)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Contato atualizado com sucesso!")
            return redirect('cadastros:fornecedor_detail', pk=contato.fornecedor.pk)
        else:
            messages.error(request, "❌ Corrija os erros no formulário.")
    else:
        form = FornecedorContatoForm(instance=contato)
    
    return render(request, 'cadastros/fornecedor/fornecedor_contato_form.html', {
        'form': form,
        'contato': contato,
        'fornecedor': contato.fornecedor,
        'action': 'Editar'
    })


@login_required
def fornecedor_contato_delete(request, pk):
    """Excluir contato do fornecedor"""
    
    contato = get_object_or_404(FornecedorContato, pk=pk, fornecedor__empresa=request.user.empresa)
    fornecedor = contato.fornecedor
    
    if request.method == 'POST':
        contato.delete()
        messages.success(request, "🗑️ Contato excluído com sucesso!")
        return redirect('cadastros:fornecedor_detail', pk=fornecedor.pk)
    
    return render(request, 'cadastros/fornecedor/fornecedor_contato_confirm_delete.html', {
        'contato': contato,
        'fornecedor': fornecedor
    })


# ============================================
# FORNECEDOR - DOCUMENTOS
# ============================================

@login_required
def fornecedor_documento_create(request, fornecedor_pk):
    """Adicionar novo documento ao fornecedor"""
    
    fornecedor = get_object_or_404(Fornecedor, pk=fornecedor_pk, empresa=request.user.empresa)
    
    if request.method == 'POST':
        form = FornecedorDocumentoForm(request.POST, request.FILES)
        if form.is_valid():
            documento = form.save(commit=False)
            documento.fornecedor = fornecedor
            documento.enviado_por = request.user
            documento.save()
            messages.success(request, "✅ Documento adicionado com sucesso!")
            return redirect('cadastros:fornecedor_detail', pk=fornecedor.pk)
        else:
            messages.error(request, "❌ Corrija os erros no formulário.")
    else:
        form = FornecedorDocumentoForm()
    
    return render(request, 'cadastros/fornecedor/fornecedor_documento_form.html', {
        'form': form,
        'fornecedor': fornecedor,
        'action': 'Adicionar'
    })


@login_required
def fornecedor_documento_delete(request, pk):
    """Excluir documento do fornecedor"""
    
    documento = get_object_or_404(FornecedorDocumento, pk=pk, fornecedor__empresa=request.user.empresa)
    fornecedor = documento.fornecedor
    
    if request.method == 'POST':
        # Remove arquivo físico
        if documento.arquivo:
            documento.arquivo.delete()
        documento.delete()
        messages.success(request, "🗑️ Documento excluído com sucesso!")
        return redirect('cadastros:fornecedor_detail', pk=fornecedor.pk)
    
    return render(request, 'cadastros/fornecedor/fornecedor_documento_confirm_delete.html', {
        'documento': documento,
        'fornecedor': fornecedor
    })


# ============================================
# FORNECEDOR - AVALIAÇÕES
# ============================================

@login_required
def fornecedor_avaliacao_create(request, fornecedor_pk):
    """Criar nova avaliação do fornecedor"""
    
    fornecedor = get_object_or_404(Fornecedor, pk=fornecedor_pk, empresa=request.user.empresa)
    
    if request.method == 'POST':
        form = FornecedorAvaliacaoForm(request.POST)
        if form.is_valid():
            avaliacao = form.save(commit=False)
            avaliacao.fornecedor = fornecedor
            avaliacao.avaliado_por = request.user
            avaliacao.save()
            messages.success(request, f"✅ Avaliação registrada! Score do fornecedor: {fornecedor.score_avaliacao}/10")
            return redirect('cadastros:fornecedor_detail', pk=fornecedor.pk)
        else:
            messages.error(request, "❌ Corrija os erros no formulário.")
    else:
        form = FornecedorAvaliacaoForm()
    
    return render(request, 'cadastros/fornecedor/fornecedor_avaliacao_form.html', {
        'form': form,
        'fornecedor': fornecedor,
        'action': 'Criar'
    })


"""
========================================
FIM DO CÓDIGO PARA ADICIONAR
========================================

PRÓXIMO PASSO:
Adicionar URLs ao cadastros/urls.py
"""