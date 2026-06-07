from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required

@login_required
def cotacao_item_comparativo(request, pk):
    """Exibe o comparativo de propostas para cada item da cotação"""
    cotacao = get_object_or_404(Cotacao, pk=pk, empresa=request.user.empresa)
    if request.method == 'POST':
        from decimal import Decimal, InvalidOperation
        
        # Validação: verificar se há propostas com valor zero
        todas_propostas = FornecedorCotacao.objects.filter(
            item_cotacao__cotacao=cotacao
        )
        propostas_zeradas = todas_propostas.filter(preco_unitario=0)
        
        if propostas_zeradas.exists():
            from django.contrib import messages
            messages.error(
                request, 
                f'❌ Não é permitido salvar o comparativo com propostas de valor R$ 0,00. '
                f'Encontradas {propostas_zeradas.count()} proposta(s) com valor zerado. '
                f'Edite as propostas e informe valores válidos.'
            )
            from django.urls import reverse
            return redirect(reverse('compras:cotacao_item_comparativo', args=[pk]))
        
        for item in cotacao.itens.select_related('produto', 'unidade_medida').all():
            propostas = list(item.propostas.select_related('fornecedor').all())
            selecionada_pk = request.POST.get(f'selecionada_{item.pk}')
            # Primeiro, desmarcar todas
            for proposta in propostas:
                proposta.selecionado = False
                motivo = request.POST.get(f'motivo_{proposta.pk}', proposta.motivo_escolha)
                proposta.motivo_escolha = motivo
                proposta.save()
            # Depois, marcar a selecionada
            if selecionada_pk:
                for proposta in propostas:
                    if str(proposta.pk) == str(selecionada_pk):
                        proposta.selecionado = True
                        proposta.save()
            # Atualiza status do item após salvar propostas
            if hasattr(item, 'atualizar_status'):
                item.atualizar_status()
        # Atualiza status da cotação e da solicitação
        cotacao.save()

        # Garante conclusão quando todos os itens possuem proposta vencedora.
        itens_total = cotacao.itens.count()
        itens_com_vencedor = ItemCotacao.objects.filter(
            cotacao=cotacao,
            propostas__selecionado=True,
        ).distinct().count()

        if itens_total > 0 and itens_com_vencedor == itens_total:
            if hasattr(cotacao, 'concluir'):
                try:
                    cotacao.concluir()
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error('Erro ao concluir cotação %s: %s', cotacao.pk, e)
        else:
            if hasattr(cotacao, 'atualizar_status_cotacao'):
                cotacao.atualizar_status_cotacao()
        if hasattr(cotacao, 'solicitacao') and hasattr(cotacao.solicitacao, 'atualizar_status_cotacao'):
            cotacao.solicitacao.atualizar_status_cotacao()
        from django.contrib import messages
        if itens_total > 0 and itens_com_vencedor == itens_total:
            messages.success(request, 'Seleção salva com sucesso! Cotação concluída e pronta para gerar pedido.')
        else:
            faltantes = max(itens_total - itens_com_vencedor, 0)
            messages.success(request, 'Seleção e justificativas salvas com sucesso!')
            messages.warning(
                request,
                f'Faltam selecionar fornecedores vencedores em {faltantes} item(ns) para liberar a geração do pedido.'
            )
        from django.urls import reverse
        # Mantém no comparativo para exibir o botão de gerar pedido quando liberado
        return redirect(reverse('compras:cotacao_item_comparativo', args=[pk]))
    itens_data = []
    for item in cotacao.itens.select_related('produto', 'unidade_medida').all():
        # Recarrega propostas do banco para garantir status atualizado
        propostas = list(item.propostas.select_related('fornecedor').all())
        menor_preco = min([p.preco_unitario for p in propostas], default=None)
        for p in propostas:
            p.melhor_preco = (p.preco_unitario == menor_preco) if menor_preco is not None else False
        itens_data.append({
            'item': item,
            'propostas': propostas,
        })
    context = {
        'cotacao': cotacao,
        'itens_data': itens_data,
        'has_pedidos': cotacao.pedidos.exists(),
    }
    return render(request, 'compras/cotacao_item_comparativo.html', context)
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.core.paginator import Paginator
from django.utils import timezone
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.core.files.base import ContentFile
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage
from reportlab.lib.units import cm
from django.conf import settings
import os
import io
from .models import (
    SolicitacaoCompra,
    ItemSolicitacaoCompra,
    Cotacao,
    ItemCotacao,
    FornecedorCotacao,
    PedidoCompra,
    ItemPedidoCompra,
    SolicitacaoMensagem
)
from .forms import (
    SolicitacaoCompraForm,
    ItemSolicitacaoFormSet,
    CotacaoForm,
    FornecedorCotacaoFormSet,
    SolicitacaoMensagemForm
)
from .forms_xml_nf import XMLNFeUploadForm
from .nfe_parser import NFEImportError, parse_nfe_xml
from produtos.models import Produto
from estoque.models import LocalEstocagem
from cadastros.models import Fornecedor
from django.db.models import Q
from core.feature_flags import is_feature_enabled

@login_required
def solicitacao_list(request):
    """Lista todas as solicitações de compra"""
    solicitacoes = SolicitacaoCompra.objects.filter(
        empresa=request.user.empresa
    ).select_related('solicitante', 'aprovador')
    
    # Filtros
    status = request.GET.get('status')
    if status:
        solicitacoes = solicitacoes.filter(status=status)
    

    # Atualiza status dos itens e da solicitação para garantir dados atualizados
    updated_solicitacoes = []
    for s in solicitacoes:
        # Atualiza status de cada item
        for item in s.itens.all():
            if hasattr(item, 'atualizar_status'):
                item.atualizar_status()
        s.atualizar_status_cotacao()
        # Recarrega do banco para garantir dados atualizados
        updated_solicitacoes.append(type(s).objects.get(pk=s.pk))
    solicitacoes = updated_solicitacoes

    # Paginação
    paginator = Paginator(solicitacoes, 20)
    page_number = request.GET.get('page')
    solicitacoes_page = paginator.get_page(page_number)

    # Adiciona flag de nova mensagem para cada solicitação
    user = request.user
    for s in solicitacoes_page:
        s.nova_msg = s.tem_nova_mensagem_para(user)

    context = {
        'solicitacoes': solicitacoes_page,
        'status_choices': SolicitacaoCompra.STATUS_CHOICES,
    }
    return render(request, 'compras/solicitacao_list.html', context)


@login_required
@transaction.atomic
def solicitacao_create(request):
    """Cria nova solicitação de compra"""
    if request.method == 'POST':
        form = SolicitacaoCompraForm(request.POST)
        formset = ItemSolicitacaoFormSet(
            request.POST,
            empresa=request.user.empresa
        )
        
        if form.is_valid() and formset.is_valid():
            solicitacao = form.save(commit=False)
            solicitacao.empresa = request.user.empresa
            solicitacao.solicitante = request.user
            
            # Define status inicial baseado em emergencial
            if solicitacao.emergencial:
                solicitacao.status = 'APROVADA'
                solicitacao.aprovador = request.user
                solicitacao.data_aprovacao = timezone.now()
            else:
                solicitacao.status = 'PENDENTE'
            
            solicitacao.save()
            
            # Salva os itens
            formset.instance = solicitacao
            formset.save()
            
            if solicitacao.emergencial:
                messages.success(
                    request,
                    f'Solicitação EMERGENCIAL {solicitacao.numero} criada e aprovada automaticamente!'
                )
            else:
                messages.success(
                    request,
                    f'Solicitação {solicitacao.numero} criada com sucesso!'
                )
            return redirect('compras:solicitacao_detail', pk=solicitacao.pk)
        else:
            messages.error(
                request,
                'Não foi possível salvar a solicitação. Verifique os campos obrigatórios e os itens informados.'
            )

            if form.errors:
                for field, errors in form.errors.items():
                    label = form.fields[field].label if field in form.fields else field
                    for error in errors:
                        messages.warning(request, f'{label}: {error}')

            non_form_errors = formset.non_form_errors()
            if non_form_errors:
                for error in non_form_errors:
                    messages.warning(request, f'Itens: {error}')

            for index, item_form in enumerate(formset.forms, start=1):
                if not item_form.errors:
                    continue

                if item_form.cleaned_data.get('DELETE', False) if hasattr(item_form, 'cleaned_data') else False:
                    continue

                for field, errors in item_form.errors.items():
                    field_label = item_form.fields[field].label if field in item_form.fields else field
                    for error in errors:
                        messages.warning(request, f'Item {index} - {field_label}: {error}')
    else:
        form = SolicitacaoCompraForm()
        formset = ItemSolicitacaoFormSet(empresa=request.user.empresa)
    
    from produtos.models import Produto
    produtos = Produto.objects.filter(
        categoria__empresa=request.user.empresa,
        ativo=True
    ).order_by('nome')
    context = {
        'form': form,
        'formset': formset,
        'title': 'Nova Solicitação de Compra',
        'produtos': produtos,
    }
    return render(request, 'compras/solicitacao_form.html', context)


@login_required
def solicitacao_detail(request, pk):
    """Exibe detalhes da solicitação"""
    solicitacao = get_object_or_404(
        SolicitacaoCompra,
        pk=pk,
        empresa=request.user.empresa
    )
    
    itens = solicitacao.itens.select_related(
        'produto',
        'unidade_medida',
        'cotacao_vinculada'
    )
    # IDs dos itens da solicitação que possuem ItemPedidoCompra relacionado
    from compras.models import ItemPedidoCompra
    itens_pedido_ids = set(
        ItemPedidoCompra.objects.filter(
            pedido__cotacao__solicitacao=solicitacao
        ).values_list('produto_id', flat=True)
    )
    
    solicitacao.atualizar_status_cotacao()
    mensagens = solicitacao.mensagens.select_related('autor').all()
    if request.method == 'POST':
        if 'enviar_mensagem' in request.POST:
            msg_form = SolicitacaoMensagemForm(request.POST)
            if msg_form.is_valid():
                mensagem = msg_form.save(commit=False)
                mensagem.solicitacao = solicitacao
                mensagem.autor = request.user
                mensagem.save()
                return redirect('compras:solicitacao_detail', pk=pk)
        elif 'salvar_aprovacao' in request.POST and request.user == solicitacao.aprovador and solicitacao.status == 'PENDENTE':
            # Aprovação/reprovação dos itens
            itens_aprovados = request.POST.getlist('itens_aprovados')
            for item in itens:
                if str(item.id) in itens_aprovados:
                    item.status_item = 'APROVADO'
                    item.motivo_recusa = ''
                    item.aprovador_recusa = None
                else:
                    item.status_item = 'RECUSADO'
                    item.aprovador_recusa = request.user
                    item.motivo_recusa = request.POST.get(f'motivo_recusa_{item.id}', '')
                item.save()
            messages.success(request, 'Aprovação dos itens registrada com sucesso.')
            return redirect('compras:solicitacao_detail', pk=pk)
        else:
            msg_form = SolicitacaoMensagemForm()
    else:
        msg_form = SolicitacaoMensagemForm()
    context = {
        'solicitacao': solicitacao,
        'itens': itens,
        'percentual_cotado': solicitacao.calcular_percentual_cotado(),
        'mensagens': mensagens,
        'msg_form': msg_form,
        'itens_pedido_ids': itens_pedido_ids,
    }
    return render(request, 'compras/solicitacao_detail.html', context)


@login_required
def solicitacao_aprovar(request, pk):
    """Aprova a solicitação"""
    solicitacao = get_object_or_404(
        SolicitacaoCompra,
        pk=pk,
        empresa=request.user.empresa
    )
    
    try:
        solicitacao.aprovar(request.user)
        messages.success(
            request,
            f'Solicitação {solicitacao.numero} aprovada com sucesso!'
        )
    except Exception as e:
        messages.error(request, str(e))
    
    return redirect('compras:solicitacao_detail', pk=pk)


@login_required
def solicitacao_cancelar(request, pk):
    """Cancela a solicitação"""
    solicitacao = get_object_or_404(
        SolicitacaoCompra,
        pk=pk,
        empresa=request.user.empresa
    )
    
    try:
        solicitacao.cancelar(usuario=request.user)
        messages.success(
            request,
            f'Solicitação {solicitacao.numero} cancelada.'
        )
    except Exception as e:
        messages.error(request, str(e))
    
    return redirect('compras:solicitacao_list')


@login_required
def selecionar_itens_cotar(request, pk):
    """Marca itens como selecionados para cotação"""
    if request.method == 'POST':
        solicitacao = get_object_or_404(
            SolicitacaoCompra,
            pk=pk,
            empresa=request.user.empresa
        )
        
        # Lista de IDs dos itens selecionados
        itens_ids = request.POST.getlist('itens_selecionados')
        
        if not itens_ids:
            messages.warning(request, 'Nenhum item foi selecionado.')
            return redirect('compras:solicitacao_detail', pk=pk)
        
        # Atualiza status dos itens
        solicitacao.itens.filter(id__in=itens_ids).update(
            selecionado_para_cotar=True,
            status_item='SELECIONADO'
        )
        
        messages.success(
            request,
            f'{len(itens_ids)} item(ns) selecionado(s) para cotação.'
        )
        
        # Redireciona para criar cotação
        return redirect('compras:cotacao_create', solicitacao_pk=pk)
    
    return redirect('compras:solicitacao_detail', pk=pk)


@login_required
@transaction.atomic
def cotacao_create(request, solicitacao_pk):
    """Cria nova cotação a partir dos itens selecionados"""
    solicitacao = get_object_or_404(
        SolicitacaoCompra,
        pk=solicitacao_pk,
        empresa=request.user.empresa
    )
    
    # Busca itens selecionados
    itens_selecionados = solicitacao.itens.filter(
        selecionado_para_cotar=True,
        status_item='SELECIONADO'
    )
    
    if not itens_selecionados.exists():
        messages.warning(
            request,
            'Não há itens selecionados para cotação. '
            'Selecione os itens na solicitação primeiro.'
        )
        return redirect('compras:solicitacao_detail', pk=solicitacao_pk)
    
    if request.method == 'POST':
        form = CotacaoForm(request.POST)
        
        if form.is_valid():
            cotacao = form.save(commit=False)
            cotacao.empresa = request.user.empresa
            cotacao.solicitacao = solicitacao
            cotacao.comprador = request.user
            cotacao.status = 'EM_ANDAMENTO'
            cotacao.save()
            
            # Cria itens da cotação
            from produtos.models import ProdutoFornecedor
            fornecedores_map = {}
            for item_sol in itens_selecionados:
                item_cot = ItemCotacao.objects.create(
                    cotacao=cotacao,
                    item_solicitacao=item_sol,
                    produto=item_sol.produto,
                    quantidade=item_sol.quantidade,
                    unidade_medida=item_sol.unidade_medida,
                    especificacao=item_sol.especificacao
                )
                # Atualiza status do item
                item_sol.status_item = 'EM_COTACAO'
                item_sol.cotacao_vinculada = cotacao
                item_sol.selecionado_para_cotar = False
                item_sol.save()
                # Agrupa fornecedores para cada produto
                fornecedores_produto = ProdutoFornecedor.objects.filter(
                    produto=item_sol.produto,
                    fornecedor__ativa=True,
                    fornecedor__empresa=request.user.empresa
                ).select_related('fornecedor')
                for pf in fornecedores_produto:
                    if pf.fornecedor.id not in fornecedores_map:
                        fornecedores_map[pf.fornecedor.id] = {
                            'fornecedor': pf.fornecedor,
                            'produtos': []
                        }
                    fornecedores_map[pf.fornecedor.id]['produtos'].append(item_cot)
            # Cria propostas agrupadas por fornecedor
            from .models import FornecedorCotacao
            for fornecedor_id, info in fornecedores_map.items():
                fornecedor = info['fornecedor']
                for item_cot in info['produtos']:
                    FornecedorCotacao.objects.create(
                        item_cotacao=item_cot,
                        fornecedor=fornecedor,
                        preco_unitario=0,
                        preco_total=0,
                        prazo_entrega=1
                    )
            # Atualiza status da solicitação
            solicitacao.atualizar_status_cotacao()
            messages.success(
                request,
                f'Cotação {cotacao.numero} criada agrupando fornecedores e produtos!'
            )
            return redirect('compras:cotacao_detail', pk=cotacao.pk)
    else:
        form = CotacaoForm()
    
    context = {
        'form': form,
        'solicitacao': solicitacao,
        'itens_selecionados': itens_selecionados,
        'title': f'Nova Cotação - {solicitacao.numero}',
    }
    return render(request, 'compras/cotacao/cotacao_form.html', context)


@login_required
def cotacao_list(request):
    """Lista todas as cotações"""
    cotacoes = Cotacao.objects.filter(
        empresa=request.user.empresa
    ).select_related('solicitacao', 'comprador')
    
    # Filtros
    status = request.GET.get('status')
    if status:
        cotacoes = cotacoes.filter(status=status)
    
    # Paginação
    paginator = Paginator(cotacoes, 20)
    page_number = request.GET.get('page')
    cotacoes_page = paginator.get_page(page_number)
    
    # Card de cotações pendentes
    cotacoes_pendentes = Cotacao.objects.filter(empresa=request.user.empresa, status='EM_ANDAMENTO').count()
    
    # Card de solicitações pendentes de cotação
    total_solicitacoes = SolicitacaoCompra.objects.filter(empresa=request.user.empresa).count()
    solicitacoes_pendentes = SolicitacaoCompra.objects.filter(empresa=request.user.empresa, status='PENDENTE').count()
    percentual_pendentes = 0
    if total_solicitacoes > 0:
        percentual_pendentes = int((solicitacoes_pendentes / total_solicitacoes) * 100)
    
    # Card de solicitações PARCIALMENTE_COTADA
    solicitacoes_parcial = SolicitacaoCompra.objects.filter(empresa=request.user.empresa, status='PARCIALMENTE_COTADA').count()

    context = {
        'cotacoes': cotacoes_page,
        'status_choices': Cotacao.STATUS_CHOICES,
        'cotacoes_pendentes': cotacoes_pendentes,
        'solicitacoes_pendentes': solicitacoes_pendentes,
        'percentual_pendentes': percentual_pendentes,
        'solicitacoes_parcial': solicitacoes_parcial
    }
    return render(request, 'compras/cotacao/cotacao_list_tradicional.html', context)


@login_required
def cotacao_detail(request, pk):
    # Redireciona para o comparativo de propostas
    from django.urls import reverse
    return redirect(reverse('compras:cotacao_item_comparativo', args=[pk]))


@login_required
@transaction.atomic

def adicionar_proposta(request, cotacao_pk, item_pk):
    """Fluxo novo: Cotação de fornecedores vinculados ao produto"""
    cotacao = get_object_or_404(Cotacao, pk=cotacao_pk, empresa=request.user.empresa)
    item = get_object_or_404(ItemCotacao, pk=item_pk, cotacao=cotacao)
    propostas = list(item.propostas.select_related('fornecedor').all())
    menor_preco = min([p.preco_unitario for p in propostas], default=None)
    for p in propostas:
        p.melhor_preco = (p.preco_unitario == menor_preco) if menor_preco is not None else False

    # Verificar se o produto tem fornecedores cadastrados
    from produtos.models import ProdutoFornecedor
    fornecedores_produto = ProdutoFornecedor.objects.filter(
        produto=item.produto,
        fornecedor__ativa=True,
        fornecedor__empresa=request.user.empresa
    ).count()
    
    # Listar fornecedores disponíveis para seleção manual
    from cadastros.models import Fornecedor
    if fornecedores_produto == 0:
        # Se não tem fornecedores no produto, listar todos
        fornecedores_disponiveis = Fornecedor.objects.filter(
            empresa=request.user.empresa,
            ativa=True
        ).exclude(
            id__in=[p.fornecedor.id for p in propostas]
        ).order_by('nome')
    else:
        fornecedores_disponiveis = []

    if request.method == 'POST':
        # Adicionar novo fornecedor manualmente
        fornecedor_id = request.POST.get('adicionar_fornecedor')
        if fornecedor_id:
            fornecedor = get_object_or_404(Fornecedor, pk=fornecedor_id, empresa=request.user.empresa)
            FornecedorCotacao.objects.create(
                item_cotacao=item,
                fornecedor=fornecedor,
                preco_unitario=0,
                preco_total=0,
                prazo_entrega=1
            )
            messages.success(request, f'Fornecedor {fornecedor.nome} adicionado!')
            return redirect('compras:adicionar_proposta', cotacao_pk=cotacao_pk, item_pk=item_pk)
        from decimal import Decimal, InvalidOperation
        # Atualiza valores das propostas
        for proposta in propostas:
            preco_unitario_str = request.POST.get(f'preco_unitario_{proposta.pk}', str(proposta.preco_unitario))
            # Remove máscara e converte para Decimal
            if isinstance(preco_unitario_str, str):
                # Remove caracteres de moeda e espaços
                preco_unitario_str = preco_unitario_str.replace('R$', '').strip()
                # Detecta formato brasileiro (1.000,00) vs inglês (1000.00)
                if ',' in preco_unitario_str and '.' in preco_unitario_str:
                    # Formato brasileiro: 1.000,00
                    preco_unitario_str = preco_unitario_str.replace('.', '').replace(',', '.')
                elif ',' in preco_unitario_str:
                    # Somente vírgula: 1000,00 (assumir brasileiro)
                    preco_unitario_str = preco_unitario_str.replace(',', '.')
                elif '.' in preco_unitario_str:
                    # Somente ponto: 1000.00 (já em formato correto) ou 1.000 (brasileiro sem decimal)
                    # Verificar se há números depois do ponto
                    partes = preco_unitario_str.split('.')
                    if len(partes[1]) == 2:
                        # Formato correto: 1000.00
                        pass
                    else:
                        # Formato brasileiro: 1.000
                        preco_unitario_str = preco_unitario_str.replace('.', '')
            try:
                proposta.preco_unitario = Decimal(preco_unitario_str)
            except (InvalidOperation, TypeError, ValueError) as e:
                import logging
                logging.error(f"Erro ao converter preço '{preco_unitario_str}': {e}")
                proposta.preco_unitario = Decimal('0.00')
            
            # Processa preco_total também (leitura apenas, mas com conversão segura)
            preco_total_str = request.POST.get(f'preco_total_{proposta.pk}', str(proposta.preco_total))
            if isinstance(preco_total_str, str):
                preco_total_str = preco_total_str.replace('R$', '').strip()
                if ',' in preco_total_str and '.' in preco_total_str:
                    preco_total_str = preco_total_str.replace('.', '').replace(',', '.')
                elif ',' in preco_total_str:
                    preco_total_str = preco_total_str.replace(',', '.')
                elif '.' in preco_total_str:
                    partes = preco_total_str.split('.')
                    if len(partes) > 1 and len(partes[1]) != 2:
                        preco_total_str = preco_total_str.replace('.', '')
            try:
                proposta.preco_total = Decimal(preco_total_str)
            except (InvalidOperation, TypeError, ValueError):
                # Se falhar, calcula automaticamente
                proposta.preco_total = proposta.preco_unitario * Decimal(str(item.quantidade))
            
            proposta.prazo_entrega = request.POST.get(f'prazo_entrega_{proposta.pk}', proposta.prazo_entrega)
            proposta.condicao_pagamento = request.POST.get(f'condicao_pagamento_{proposta.pk}', proposta.condicao_pagamento)
            proposta.marca = request.POST.get(f'marca_{proposta.pk}', proposta.marca)
            proposta.observacoes = request.POST.get(f'observacoes_{proposta.pk}', proposta.observacoes)
            proposta.motivo_escolha = request.POST.get(f'motivo_{proposta.pk}', proposta.motivo_escolha)
            proposta.selecionado = False
        # Seleção manual
        selecionada_pk = request.POST.get('selecionada')
        if selecionada_pk:
            for proposta in propostas:
                if str(proposta.pk) == str(selecionada_pk):
                    proposta.selecionado = True
        for proposta in propostas:
            proposta.save()
        messages.success(request, 'Propostas e seleção salvas com sucesso!')
        return redirect('compras:cotacao_item_comparativo', pk=cotacao_pk)

    context = {
        'cotacao': cotacao,
        'item': item,
        'propostas': propostas,
        'fornecedores_disponiveis': fornecedores_disponiveis,
        'produto_tem_fornecedores': fornecedores_produto > 0,
    }
    return render(request, 'compras/proposta_form.html', context)


@login_required
def selecionar_fornecedor(request, proposta_pk):
    """Marca um fornecedor como selecionado"""
    proposta = get_object_or_404(FornecedorCotacao, pk=proposta_pk)
    
    # Desmarca outras propostas do mesmo item
    proposta.item_cotacao.propostas.update(selecionado=False)
    
    # Marca esta proposta
    proposta.selecionado = True
    proposta.save()
    
    # Atualiza status do item APENAS se a cotação estiver CONCLUIDA
    if proposta.item_cotacao.cotacao.status == 'CONCLUIDA':
        proposta.item_cotacao.item_solicitacao.status_item = 'COTADO'
        proposta.item_cotacao.item_solicitacao.save()
        
        # Atualiza status da solicitação
        proposta.item_cotacao.cotacao.solicitacao.atualizar_status_cotacao()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    
    messages.success(
        request,
        f'Fornecedor {proposta.fornecedor.nome_fantasia} selecionado!'
    )
    return redirect('compras:cotacao_detail', pk=proposta.item_cotacao.cotacao.pk)


@login_required
def remover_proposta(request, proposta_pk):
    """Remove uma proposta de fornecedor"""
    proposta = get_object_or_404(FornecedorCotacao, pk=proposta_pk)
    cotacao_pk = proposta.item_cotacao.cotacao.pk
    item_pk = proposta.item_cotacao.pk
    fornecedor_nome = proposta.fornecedor.nome
    
    # Verifica se pode remover (não permitir se o produto tem fornecedores cadastrados)
    from produtos.models import ProdutoFornecedor
    tem_fornecedores = ProdutoFornecedor.objects.filter(
        produto=proposta.item_cotacao.produto,
        fornecedor__ativa=True,
        fornecedor__empresa=request.user.empresa
    ).exists()
    
    if tem_fornecedores:
        messages.error(request, 'Não é possível remover fornecedores cadastrados no produto!')
        return redirect('compras:adicionar_proposta', cotacao_pk=cotacao_pk, item_pk=item_pk)
    
    proposta.delete()
    messages.success(request, f'Fornecedor {fornecedor_nome} removido!')
    return redirect('compras:adicionar_proposta', cotacao_pk=cotacao_pk, item_pk=item_pk)


@login_required
def cotacao_concluir(request, pk):
    """Conclui a cotação"""
    cotacao = get_object_or_404(
        Cotacao,
        pk=pk,
        empresa=request.user.empresa
    )
    
    cotacao.concluir()
    messages.success(request, f'Cotação {cotacao.numero} concluída!')
    
    return redirect('compras:cotacao_list')


@login_required
def get_produto_estoque(request, produto_id):
    """API: Retorna o estoque atual do produto em todas as fazendas"""
    from produtos.models import Produto
    from empresas.models import Empresa
    
    try:
        # Busca o produto na empresa atual
        produto = Produto.objects.get(
            id=produto_id,
            categoria__empresa=request.user.empresa
        )
        
        # Estoque da empresa atual
        estoque_atual = {
            'success': True,
            'estoque_atual': float(produto.estoque_atual),
            'unidade': produto.unidade_medida.sigla,
            'unidade_id': produto.unidade_medida.id,
            'estoque_minimo': float(produto.estoque_minimo),
            'controla_estoque': produto.controla_estoque,
            'produto_nome': produto.nome,
            'produto_codigo': produto.codigo
        }
        
        # Busca o mesmo produto (por código) em outras empresas
        outras_fazendas = []
        produtos_outras_empresas = Produto.objects.filter(
            codigo=produto.codigo
        ).exclude(
            categoria__empresa=request.user.empresa
        ).select_related('categoria__empresa', 'unidade_medida')
        
        for prod in produtos_outras_empresas:
            outras_fazendas.append({
                'empresa_nome': prod.categoria.empresa.nome_fantasia,
                'estoque_atual': float(prod.estoque_atual),
                'estoque_minimo': float(prod.estoque_minimo),
                'unidade': prod.unidade_medida.sigla,
                'controla_estoque': prod.controla_estoque
            })
        
        estoque_atual['outras_fazendas'] = outras_fazendas
        
        return JsonResponse(estoque_atual)
        
    except Produto.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Produto não encontrado'
        }, status=404)


@login_required
def get_produto_unidades(request, produto_id):
    """API: Retorna as unidades de medida disponíveis para um produto"""
    from produtos.models import Produto, UnidadeMedida
    
    try:
        # Busca o produto na empresa atual
        produto = Produto.objects.get(
            id=produto_id,
            categoria__empresa=request.user.empresa
        )
        
        # Busca todas as unidades de medida da empresa
        unidades = UnidadeMedida.objects.filter(
            empresa=request.user.empresa
        ).values('id', 'nome', 'sigla').order_by('nome')
        
        return JsonResponse({
            'success': True,
            'unidades': list(unidades),
            'unidade_padrao_id': produto.unidade_medida.id,
            'unidade_padrao_nome': produto.unidade_medida.nome,
        })
        
    except Produto.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Produto não encontrado'
        }, status=404)


@login_required
def get_empresa_unidades(request):
    """API: Retorna todas as unidades de medida da empresa"""
    from produtos.models import UnidadeMedida
    
    try:
        # Busca todas as unidades de medida da empresa
        unidades = UnidadeMedida.objects.filter(
            empresa=request.user.empresa
        ).values('id', 'nome', 'sigla').order_by('nome')
        
        return JsonResponse({
            'success': True,
            'unidades': list(unidades),
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# ========================================
# PEDIDOS DE COMPRA
# ========================================

@login_required
def pedido_list(request):
    """Lista todos os pedidos de compra"""
    from .models import PedidoCompra
    
    pedidos = PedidoCompra.objects.filter(
        empresa=request.user.empresa
    ).select_related('fornecedor', 'comprador', 'cotacao')
    
    # Filtros
    status = request.GET.get('status')
    if status:
        pedidos = pedidos.filter(status=status)
    
    fornecedor = request.GET.get('fornecedor')
    if fornecedor:
        pedidos = pedidos.filter(fornecedor_id=fornecedor)
    
    # Paginação
    paginator = Paginator(pedidos, 20)
    page_number = request.GET.get('page')
    pedidos_page = paginator.get_page(page_number)
    
    # Calcula status de recebimento para cada pedido na página
    pedidos_recebimento = []
    for pedido in pedidos_page:
        itens = pedido.itens.all()
        todos_recebidos = all(
            item.quantidade_recebida >= item.quantidade_pedida
            for item in itens
        )
        algum_recebido = any(
            item.quantidade_recebida > 0
            for item in itens
        )
        if todos_recebidos:
            status_recebimento = 'RECEBIDO_TOTAL'
        elif algum_recebido:
            status_recebimento = 'RECEBIDO_PARCIAL'
        else:
            status_recebimento = None
        pedidos_recebimento.append((pedido, status_recebimento))

    context = {
        'pedidos_recebimento': pedidos_recebimento,
        'status_choices': PedidoCompra.STATUS_CHOICES,
        'pedidos': pedidos_page,  # mantém para compatibilidade
    }
    return render(request, 'compras/pedido_list.html', context)


@login_required
def pedido_detail(request, pk):
    """Detalhes do pedido de compra"""
    from .models import PedidoCompra
    
    pedido = get_object_or_404(
        PedidoCompra,
        pk=pk,
        empresa=request.user.empresa
    )
    
    itens = pedido.itens.all().select_related(
        'produto',
        'unidade_medida',
        'proposta_fornecedor'
    )
    
    # Calcula status de recebimento para exibição
    todos_recebidos = all(
        item.quantidade_recebida >= item.quantidade_pedida
        for item in itens
    )
    algum_recebido = any(
        item.quantidade_recebida > 0
        for item in itens
    )
    if todos_recebidos:
        status_recebimento = 'RECEBIDO_TOTAL'
    elif algum_recebido:
        status_recebimento = 'RECEBIDO_PARCIAL'
    else:
        status_recebimento = None

    # Buscar recebimentos deste pedido
    recebimentos = pedido.recebimentos.all().order_by('-data_recebimento')

    limite_credito = pedido.fornecedor.limite_credito or 0
    valor_pedido = pedido.valor_final or pedido.valor_total or 0
    excede_limite_credito = bool(limite_credito and valor_pedido > limite_credito)
    valor_excedente_credito = (valor_pedido - limite_credito) if excede_limite_credito else 0

    context = {
        'pedido': pedido,
        'itens': itens,
        'status_recebimento': status_recebimento,
        'recebimentos': recebimentos,
        'limite_credito_fornecedor': limite_credito,
        'valor_pedido_atual': valor_pedido,
        'excede_limite_credito': excede_limite_credito,
        'valor_excedente_credito': valor_excedente_credito,
    }
    return render(request, 'compras/pedido_detail.html', context)


@login_required
@transaction.atomic
def pedido_gerar(request, cotacao_pk):
    """
    Gera Pedido de Compra a partir de uma cotação concluída
    Agrupa itens por fornecedor selecionado
    """
    from .models import PedidoCompra, ItemPedidoCompra
    from datetime import timedelta
    
    cotacao = get_object_or_404(
        Cotacao,
        pk=cotacao_pk,
        empresa=request.user.empresa,
    )

    if cotacao.status != 'CONCLUIDA':
        for item in cotacao.itens.all():
            if hasattr(item, 'atualizar_status'):
                item.atualizar_status()

        if hasattr(cotacao, 'pode_concluir') and cotacao.pode_concluir():
            cotacao.concluir()
            cotacao.refresh_from_db()

        if cotacao.status != 'CONCLUIDA':
            messages.warning(
                request,
                'A cotação ainda não está concluída. Salve a seleção dos fornecedores antes de gerar o pedido de compra.'
            )
            return redirect('compras:cotacao_item_comparativo', pk=cotacao_pk)

    # Evita gerar pedidos duplicados para a mesma cotação
    if PedidoCompra.objects.filter(cotacao=cotacao).exists():
        messages.warning(request, 'Pedidos já foram gerados para esta cotação.')
        return redirect('compras:cotacao_item_comparativo', pk=cotacao_pk)
    
    # Busca propostas vencedoras
    propostas_vencedoras = FornecedorCotacao.objects.filter(
        item_cotacao__cotacao=cotacao,
        selecionado=True
    ).select_related('fornecedor', 'item_cotacao__item_solicitacao')
    
    if not propostas_vencedoras.exists():
        messages.error(request, 'Nenhum fornecedor foi selecionado na cotação.')
        return redirect('compras:cotacao_detail', pk=cotacao_pk)
    
    # Agrupa por fornecedor
    pedidos_por_fornecedor = {}
    for proposta in propostas_vencedoras:
        fornecedor_id = proposta.fornecedor.id
        if fornecedor_id not in pedidos_por_fornecedor:
            pedidos_por_fornecedor[fornecedor_id] = {
                'fornecedor': proposta.fornecedor,
                'propostas': [],
                'prazo': proposta.prazo_entrega or 0,
                'forma_pagamento': proposta.forma_pagamento or '',
                'condicao_pagamento': proposta.condicao_pagamento or '',
            }
        pedidos_por_fornecedor[fornecedor_id]['propostas'].append(proposta)
    
    # Cria um pedido para cada fornecedor
    pedidos_criados = []
    for fornecedor_id, dados in pedidos_por_fornecedor.items():
        # Cria o pedido
        pedido = PedidoCompra.objects.create(
            empresa=request.user.empresa,
            cotacao=cotacao,
            fornecedor=dados['fornecedor'],
            comprador=request.user,
            status='PENDENTE',
            prazo_entrega_dias=dados['prazo'],
            forma_pagamento=dados['forma_pagamento'],
            condicao_pagamento=dados['condicao_pagamento'],
            data_entrega_prevista=timezone.now().date() + timedelta(days=dados['prazo'])
        )
        
        # Cria os itens do pedido
        for proposta in dados['propostas']:
            item_solicitacao = proposta.item_cotacao.item_solicitacao
            ItemPedidoCompra.objects.create(
                pedido=pedido,
                proposta_fornecedor=proposta,
                produto=item_solicitacao.produto,
                quantidade_pedida=proposta.item_cotacao.quantidade,
                unidade_medida=item_solicitacao.unidade_medida,
                preco_unitario=proposta.preco_unitario,
                preco_total=proposta.preco_unitario * proposta.item_cotacao.quantidade,
                especificacao=proposta.item_cotacao.especificacao or '',
                marca=proposta.marca or '',
            )
        
        # Calcula o total do pedido
        total_pedido = pedido.calcular_total()

        limite_credito = dados['fornecedor'].limite_credito or 0
        if limite_credito and total_pedido > limite_credito:
            messages.warning(
                request,
                (
                    f'⚠️ Alerta de crédito: o pedido {pedido.numero} para "{dados["fornecedor"].nome}" '
                    f'(R$ {total_pedido:,.2f}) ultrapassa o limite aprovado '
                    f'de R$ {limite_credito:,.2f}.'
                )
            )

        pedidos_criados.append(pedido)
    
    # Atualiza status dos itens da solicitação para APROVADO apenas se enviados no pedido
    itens_enviados_ids = set()
    for dados in pedidos_por_fornecedor.values():
        for proposta in dados['propostas']:
            if hasattr(proposta, 'item_cotacao') and hasattr(proposta.item_cotacao, 'item_solicitacao'):
                itens_enviados_ids.add(proposta.item_cotacao.item_solicitacao.id)
    for item in cotacao.solicitacao.itens.all():
        if item.id in itens_enviados_ids:
            item.status_item = 'APROVADO'
            item.save(update_fields=['status_item'])
    # Atualiza status da solicitação para EM_COMPRA
    cotacao.solicitacao.status = 'EM_COMPRA'
    cotacao.solicitacao.save()
    
    if len(pedidos_criados) == 1:
        messages.success(
            request,
            f'Pedido {pedidos_criados[0].numero} gerado com sucesso!'
        )
        return redirect('compras:pedido_detail', pk=pedidos_criados[0].pk)
    else:
        messages.success(
            request,
            f'{len(pedidos_criados)} pedidos gerados com sucesso!'
        )
        return redirect('compras:pedido_list')


@login_required
def pedido_pdf(request, pk):
    """Gera PDF do pedido de compra usando reportlab"""
    pedido = get_object_or_404(
        PedidoCompra.objects.select_related(
            'empresa', 'fornecedor', 'cotacao', 'comprador'
        ).prefetch_related('itens__produto', 'itens__unidade_medida'),
        pk=pk,
        empresa=request.user.empresa
    )
    
    # Cria o buffer
    buffer = io.BytesIO()
    
    # Cria o documento PDF
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1*cm, bottomMargin=2*cm)
    elements = []
    
    # Estilos
    styles = getSampleStyleSheet()
    
    # Estilo para o cabeçalho da empresa
    header_empresa_style = ParagraphStyle(
        'HeaderEmpresa',
        parent=styles['Normal'],
        fontSize=16,
        textColor=colors.HexColor('#0d6efd'),
        alignment=1,  # Center
        fontName='Helvetica-Bold',
        spaceAfter=5
    )
    
    header_info_style = ParagraphStyle(
        'HeaderInfo',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#666666'),
        alignment=1,  # Center
        spaceAfter=3
    )
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.white,
        spaceAfter=0,
        alignment=1,  # Center
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#0d6efd'),
        spaceAfter=12,
        spaceBefore=12
    )
    
    # ========== CABEÇALHO COM LOGO E DADOS DA EMPRESA ==========
    # Cria tabela com logo e dados da empresa lado a lado
    header_data = []
    
    # Verifica se há logo
    logo_cell = []
    if pedido.empresa.logo:
        try:
            logo_path = pedido.empresa.logo.path
            if os.path.exists(logo_path):
                logo = RLImage(logo_path, width=3*cm, height=3*cm, kind='proportional')
                logo_cell = [logo]
            else:
                logo_cell = [Paragraph('', header_empresa_style)]
        except NotImplementedError:
            # Storage remoto (ex: Supabase) — carrega via URL
            try:
                import urllib.request as _urllib_req
                logo_data = io.BytesIO(_urllib_req.urlopen(pedido.empresa.logo.url, timeout=5).read())
                logo = RLImage(logo_data, width=3*cm, height=3*cm, kind='proportional')
                logo_cell = [logo]
            except Exception:
                logo_cell = [Paragraph('', header_empresa_style)]
    else:
        logo_cell = [Paragraph('', header_empresa_style)]
    
    # Dados da empresa
    empresa_info = []
    empresa_info.append(Paragraph(f"<b>{pedido.empresa.nome}</b>", header_empresa_style))
    
    empresa_info_parts = []
    if pedido.empresa.cnpj:
        empresa_info_parts.append(f"CNPJ: {pedido.empresa.cnpj}")
    if pedido.empresa.endereco:
        endereco_completo = pedido.empresa.endereco
        if pedido.empresa.cidade and pedido.empresa.uf:
            endereco_completo += f" - {pedido.empresa.cidade}/{pedido.empresa.uf}"
        empresa_info_parts.append(endereco_completo)
    if pedido.empresa.telefone:
        empresa_info_parts.append(f"Tel: {pedido.empresa.telefone}")
    if pedido.empresa.email:
        empresa_info_parts.append(f"Email: {pedido.empresa.email}")
    
    if empresa_info_parts:
        for info_line in empresa_info_parts:
            empresa_info.append(Paragraph(info_line, header_info_style))
    
    # Cria a tabela do cabeçalho (logo à esquerda, dados à direita)
    if logo_cell and logo_cell[0]:
        header_table = Table([logo_cell + [empresa_info]], colWidths=[3.5*cm, 13.5*cm])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (0, 0), 'CENTER'),
            ('ALIGN', (1, 0), (1, 0), 'LEFT'),
        ]))
        elements.append(header_table)
    else:
        # Se não houver logo, centraliza os dados
        for item in empresa_info:
            elements.append(item)
    
    # Linha separadora
    line_table = Table([['']], colWidths=[17*cm])
    line_table.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (-1, 0), 2, colors.HexColor('#0d6efd')),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(line_table)
    elements.append(Spacer(1, 0.3*cm))
    
    # Título do Pedido com fundo azul
    pedido_table = Table([[Paragraph(f"PEDIDO DE COMPRA Nº {pedido.numero}", title_style)]], colWidths=[17*cm])
    pedido_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#0d6efd')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
    ]))
    elements.append(pedido_table)
    elements.append(Spacer(1, 0.5*cm))
    # ====================================================
    
    # Informações da Empresa (removido pois já está no cabeçalho)
    # Informações do Fornecedor
    elements.append(Paragraph("Informações do Fornecedor", heading_style))
    fornecedor_data = [
        ['Razão Social:', pedido.fornecedor.nome],
        ['CNPJ:', pedido.fornecedor.cnpj_cpf or '-'],
        ['Telefone:', pedido.fornecedor.telefone or '-'],
        ['Email:', pedido.fornecedor.email or '-'],
    ]
    fornecedor_table = Table(fornecedor_data, colWidths=[4*cm, 12*cm])
    fornecedor_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8f9fa')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(fornecedor_table)
    elements.append(Spacer(1, 0.5*cm))
    
    # Dados do Pedido
    elements.append(Paragraph("Dados do Pedido", heading_style))
    pedido_data = [
        ['Data do Pedido:', pedido.data_pedido.strftime('%d/%m/%Y'), 
         'Previsão de Entrega:', pedido.data_entrega_prevista.strftime('%d/%m/%Y') if pedido.data_entrega_prevista else '-'],
        ['Condição Pagamento:', pedido.condicao_pagamento, 
         'Status:', pedido.get_status_display()],
    ]
    pedido_table = Table(pedido_data, colWidths=[4*cm, 6*cm, 4*cm, 6*cm])
    pedido_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8f9fa')),
        ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#f8f9fa')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(pedido_table)
    elements.append(Spacer(1, 0.5*cm))
    
    # Itens do Pedido
    elements.append(Paragraph("Itens do Pedido", heading_style))
    cell_style = ParagraphStyle('cell', parent=styles['Normal'], fontSize=9, leading=12)
    itens_data = [['Código', 'Produto', 'Un.', 'Qtd', 'Preço Unit.', 'Subtotal']]

    for item in pedido.itens.all():
        subtotal = item.quantidade_pedida * item.preco_unitario
        itens_data.append([
            item.produto.codigo,
            Paragraph(item.produto.nome, cell_style),
            item.unidade_medida.sigla,
            f"{item.quantidade_pedida:.2f}",
            f"R$ {item.preco_unitario:.2f}",
            f"R$ {subtotal:.2f}"
        ])
    
    itens_table = Table(itens_data, colWidths=[3.2*cm, 6*cm, 1*cm, 1.8*cm, 2.5*cm, 2.5*cm])
    itens_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d6efd')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
    ]))
    elements.append(itens_table)
    elements.append(Spacer(1, 0.3*cm))
    
    # Total
    total_data = [
        ['', '', '', '', 'VALOR TOTAL:', f"R$ {pedido.valor_total:.2f}"]
    ]
    total_table = Table(total_data, colWidths=[2*cm, 6*cm, 1.5*cm, 2*cm, 3*cm, 3*cm])
    total_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (4, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('TEXTCOLOR', (4, 0), (-1, 0), colors.HexColor('#0d6efd')),
        ('LINEABOVE', (4, 0), (-1, 0), 2, colors.HexColor('#0d6efd')),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
    ]))
    elements.append(total_table)
    
    # Observações
    if pedido.observacoes:
        elements.append(Spacer(1, 0.5*cm))
        elements.append(Paragraph("Observações:", heading_style))
        obs_style = ParagraphStyle('obs', parent=styles['Normal'], fontSize=9)
        elements.append(Paragraph(pedido.observacoes, obs_style))
    
    # Rodapé
    elements.append(Spacer(1, 1*cm))
    footer_style = ParagraphStyle(
        'footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=1
    )
    elements.append(Paragraph(
        f"Documento gerado em {timezone.now().strftime('%d/%m/%Y às %H:%M')}",
        footer_style
    ))
    
    # Gera o PDF
    doc.build(elements)
    
    # Retorna o PDF
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="pedido_{pedido.numero}.pdf"'
    
    return response


@login_required
def pedido_enviar_email(request, pk):
    """Envia pedido de compra por email para o fornecedor"""
    pedido = get_object_or_404(
        PedidoCompra.objects.select_related(
            'empresa', 'fornecedor', 'cotacao', 'comprador'
        ).prefetch_related('itens__produto', 'itens__unidade_medida'),
        pk=pk,
        empresa=request.user.empresa
    )
    
    if request.method == 'POST':
        email_destino = request.POST.get('email_destino', pedido.fornecedor.email)
        mensagem_adicional = request.POST.get('mensagem', '')
        
        if not email_destino:
            messages.error(request, 'Email do fornecedor não cadastrado!')
            return redirect('compras:pedido_detail', pk=pk)
        
        try:
            # Gera o PDF usando a mesma função
            # Cria o buffer
            buffer = io.BytesIO()
            
            # Cria o documento PDF (mesma lógica da função pedido_pdf)
            doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
            elements = []
            
            # Estilos
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                textColor=colors.HexColor('#0d6efd'),
                spaceAfter=30,
                alignment=1
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=12,
                textColor=colors.HexColor('#0d6efd'),
                spaceAfter=12,
                spaceBefore=12
            )
            
            # Título
            elements.append(Paragraph(f"PEDIDO DE COMPRA Nº {pedido.numero}", title_style))
            elements.append(Spacer(1, 0.5*cm))
            
            # Informações da Empresa
            elements.append(Paragraph("Informações da Empresa", heading_style))
            empresa_data = [
                ['Razão Social:', pedido.empresa.nome],
                ['CNPJ:', pedido.empresa.cnpj or '-'],
                ['Telefone:', pedido.empresa.telefone or '-'],
                ['Email:', pedido.empresa.email or '-'],
            ]
            empresa_table = Table(empresa_data, colWidths=[4*cm, 12*cm])
            empresa_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8f9fa')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            elements.append(empresa_table)
            elements.append(Spacer(1, 0.5*cm))
            
            # Informações do Fornecedor
            elements.append(Paragraph("Informações do Fornecedor", heading_style))
            fornecedor_data = [
                ['Razão Social:', pedido.fornecedor.nome],
                ['CNPJ:', pedido.fornecedor.cnpj_cpf or '-'],
                ['Telefone:', pedido.fornecedor.telefone or '-'],
                ['Email:', pedido.fornecedor.email or '-'],
            ]
            fornecedor_table = Table(fornecedor_data, colWidths=[4*cm, 12*cm])
            fornecedor_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8f9fa')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            elements.append(fornecedor_table)
            elements.append(Spacer(1, 0.5*cm))
            
            # Dados do Pedido
            elements.append(Paragraph("Dados do Pedido", heading_style))
            pedido_data = [
                ['Data do Pedido:', pedido.data_pedido.strftime('%d/%m/%Y'), 
                 'Previsão de Entrega:', pedido.data_entrega_prevista.strftime('%d/%m/%Y') if pedido.data_entrega_prevista else '-'],
                ['Condição Pagamento:', pedido.condicao_pagamento, 
                 'Status:', pedido.get_status_display()],
            ]
            pedido_info_table = Table(pedido_data, colWidths=[4*cm, 6*cm, 4*cm, 6*cm])
            pedido_info_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8f9fa')),
                ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#f8f9fa')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            elements.append(pedido_info_table)
            elements.append(Spacer(1, 0.5*cm))
            
            # Itens do Pedido
            elements.append(Paragraph("Itens do Pedido", heading_style))
            itens_data = [['Código', 'Produto', 'Un.', 'Qtd', 'Preço Unit.', 'Subtotal']]
            
            for item in pedido.itens.all():
                subtotal = item.quantidade_pedida * item.preco_unitario
                itens_data.append([
                    item.produto.codigo,
                    item.produto.nome[:40],
                    item.unidade_medida.sigla,
                    f"{item.quantidade_pedida:.2f}",
                    f"R$ {item.preco_unitario:.2f}",
                    f"R$ {subtotal:.2f}"
                ])
            
            itens_table = Table(itens_data, colWidths=[2*cm, 6*cm, 1.5*cm, 2*cm, 3*cm, 3*cm])
            itens_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d6efd')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ]))
            elements.append(itens_table)
            elements.append(Spacer(1, 0.3*cm))
            
            # Total
            total_data = [
                ['', '', '', '', 'VALOR TOTAL:', f"R$ {pedido.valor_total:.2f}"]
            ]
            total_table = Table(total_data, colWidths=[2*cm, 6*cm, 1.5*cm, 2*cm, 3*cm, 3*cm])
            total_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                ('FONTNAME', (4, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('TEXTCOLOR', (4, 0), (-1, 0), colors.HexColor('#0d6efd')),
                ('LINEABOVE', (4, 0), (-1, 0), 2, colors.HexColor('#0d6efd')),
                ('TOPPADDING', (0, 0), (-1, -1), 12),
            ]))
            elements.append(total_table)
            
            # Gera o PDF
            doc.build(elements)
            pdf_file = buffer.getvalue()
            buffer.close()
            
            # Prepara o email
            assunto = f'Pedido de Compra {pedido.numero} - {pedido.empresa.nome}'
            
            corpo_email = f"""
Prezado(a) {pedido.fornecedor.nome_fantasia or pedido.fornecedor.nome},

Segue em anexo o Pedido de Compra {pedido.numero}.

{mensagem_adicional}

Dados do Pedido:
- Número: {pedido.numero}
- Data: {pedido.data_pedido.strftime('%d/%m/%Y')}
- Previsão de Entrega: {pedido.data_entrega_prevista.strftime('%d/%m/%Y') if pedido.data_entrega_prevista else 'Não informada'}
- Valor Total: R$ {pedido.valor_total:,.2f}
- Condição de Pagamento: {pedido.condicao_pagamento}

Por favor, confirme o recebimento deste pedido.

Atenciosamente,
{pedido.empresa.nome}
            """
            
            email = EmailMessage(
                assunto,
                corpo_email,
                pedido.empresa.email or 'noreply@example.com',
                [email_destino],
            )
            
            # Anexa o PDF
            email.attach(
                f'pedido_{pedido.numero}.pdf',
                pdf_file,
                'application/pdf'
            )
            
            # Envia o email
            email.send()
            
            # Atualiza o status do pedido para ENVIADO
            pedido.enviar()
            
            messages.success(
                request,
                f'Pedido enviado com sucesso para {email_destino}!'
            )
            
        except Exception as e:
            messages.error(
                request,
                f'Erro ao enviar email: {str(e)}'
            )
        
        return redirect('compras:pedido_detail', pk=pk)
    
    # GET - Mostra o formulário
    return render(request, 'compras/pedido_enviar_email.html', {
        'pedido': pedido,
        'email_padrao': pedido.fornecedor.email
    })


@login_required
def pedido_whatsapp(request, pk):
    """Gera link do WhatsApp para enviar pedido ao fornecedor"""
    from urllib.parse import quote
    
    pedido = get_object_or_404(
        PedidoCompra.objects.select_related(
            'empresa', 'fornecedor', 'cotacao', 'comprador'
        ),
        pk=pk,
        empresa=request.user.empresa
    )
    
    # Verifica se o fornecedor tem celular cadastrado
    if not pedido.fornecedor.celular:
        messages.error(
            request, 
            'Fornecedor não possui número de celular/WhatsApp cadastrado! '
            'Por favor, edite o cadastro do fornecedor e adicione o número no formato (00) 00000-0000'
        )
        return redirect('compras:pedido_detail', pk=pk)
    
    # Tenta usar celular, se não existir ou for inválido, usa telefone
    numero_raw = pedido.fornecedor.celular.strip() if pedido.fornecedor.celular else ''
    telefone = ''.join(filter(str.isdigit, numero_raw))
    if len(telefone) < 11:
        # Tenta telefone
        numero_raw = pedido.fornecedor.telefone.strip() if pedido.fornecedor.telefone else ''
        telefone = ''.join(filter(str.isdigit, numero_raw))
        messages.info(request, f"Usando telefone do fornecedor: {numero_raw}")
    debug_info = (
        f"Celular cadastrado: {pedido.fornecedor.celular} | Telefone cadastrado: {pedido.fornecedor.telefone} | Número processado: {telefone}\n"
        f"Fornecedor pertence à empresa: {pedido.fornecedor.empresa} (ID: {pedido.fornecedor.empresa_id})\n"
        f"Pedido pertence à empresa: {pedido.empresa} (ID: {pedido.empresa_id})"
    )
    messages.info(request, debug_info)
    # Validação: número deve ter pelo menos 10 dígitos (2 DDD + 8/9 número)
    if len(telefone) < 10:
        messages.error(
            request,
            f'O fornecedor não possui número de celular/WhatsApp ou telefone válido!\nPreencha no formato (00) 00000-0000 ou (00) 0000-0000 com DDD e número válido.'
        )
        return redirect('compras:pedido_detail', pk=pk)

    # Adiciona código do país se não tiver (Brasil = 55)
    if not telefone.startswith('55'):
        telefone = '55' + telefone
    
    # Monta a mensagem
    mensagem = f"""Olá *{pedido.fornecedor.nome_fantasia or pedido.fornecedor.nome}*!

📋 *PEDIDO DE COMPRA* {pedido.numero}

*{pedido.empresa.nome}* gostaria de fazer o seguinte pedido:

📅 *Data:* {pedido.data_pedido.strftime('%d/%m/%Y')}
🚚 *Previsão de Entrega:* {pedido.data_entrega_prevista.strftime('%d/%m/%Y') if pedido.data_entrega_prevista else 'A combinar'}
💳 *Condição de Pagamento:* {pedido.condicao_pagamento}
💰 *Valor Total:* R$ {pedido.valor_total:,.2f}

*Itens do Pedido:*
"""
    
    # Adiciona os itens
    for i, item in enumerate(pedido.itens.all()[:5], 1):  # Limita a 5 itens para não ficar muito longo
        mensagem += f"\n{i}. {item.produto.nome} - {item.quantidade_pedida} {item.unidade_medida.sigla}"
    
    if pedido.itens.count() > 5:
        mensagem += f"\n_... e mais {pedido.itens.count() - 5} itens_"
    
    mensagem += f"""

📄 Para ver os detalhes completos, acesse:
{request.build_absolute_uri(f'/compras/pedidos/{pedido.pk}/pdf/')}

Por favor, confirme o recebimento deste pedido.

_Mensagem enviada via ERP Agrícola_"""
    
    # Gera o link do WhatsApp
    whatsapp_url = f"https://wa.me/{telefone}?text={quote(mensagem)}"
    
    # Marca como enviado ao gerar o link do WhatsApp
    if pedido.status != 'ENVIADO':
        pedido.enviar()
    
    return render(request, 'compras/pedido_whatsapp.html', {
        'pedido': pedido,
        'whatsapp_url': whatsapp_url,
        'telefone': pedido.fornecedor.celular
    })


@login_required
@transaction.atomic
def pedido_enviar(request, pk):
    """Envia o pedido ao fornecedor"""
    from .models import PedidoCompra
    
    pedido = get_object_or_404(
        PedidoCompra,
        pk=pk,
        empresa=request.user.empresa
    )
    
    pedido.enviar()
    messages.success(request, f'Pedido {pedido.numero} enviado ao fornecedor!')
    return redirect('compras:pedido_detail', pk=pk)


@login_required
@transaction.atomic
def pedido_cancelar(request, pk):
    """Cancela o pedido"""
    from .models import PedidoCompra
    
    pedido = get_object_or_404(
        PedidoCompra,
        pk=pk,
        empresa=request.user.empresa
    )
    
    if request.method == 'POST':
        motivo = request.POST.get('motivo', '')
        pedido.cancelar(motivo)
        messages.success(request, f'Pedido {pedido.numero} cancelado!')
        return redirect('compras:pedido_list')
    
    return render(request, 'compras/pedido_cancelar.html', {'pedido': pedido})


@login_required
def historico_completo(request, solicitacao_pk):
    """
    Exibe o histórico completo da solicitação até os pedidos de compra
    Timeline completa do processo de compras
    """
    from .models import PedidoCompra
    
    solicitacao = get_object_or_404(
        SolicitacaoCompra,
        pk=solicitacao_pk,
        empresa=request.user.empresa
    )
    
    # Busca todas as cotações relacionadas
    cotacoes = Cotacao.objects.filter(
        solicitacao=solicitacao
    ).select_related('comprador').order_by('data_cadastro')
    
    # Busca todos os pedidos relacionados às cotações
    pedidos = PedidoCompra.objects.filter(
        cotacao__solicitacao=solicitacao
    ).select_related('comprador', 'cotacao').order_by('data_pedido')
    
    # Monta eventos da timeline
    eventos = []
    
    # 1. Criação da Solicitação
    eventos.append({
        'tipo': 'solicitacao_criada',
        'icone': 'bi-file-text',
        'cor': 'primary',
        'titulo': 'Solicitação Criada',
        'descricao': f'Solicitação {solicitacao.numero} criada',
        'usuario': solicitacao.solicitante.get_full_name(),
        'data': solicitacao.data_solicitacao,
        'detalhes': f'{solicitacao.itens.count()} itens solicitados',
        'badge': 'Emergencial' if solicitacao.emergencial else None,
        'badge_cor': 'danger' if solicitacao.emergencial else None
    })
    # Evento de cancelamento da solicitação
    if solicitacao.status == 'CANCELADA':
        usuario_cancelou = solicitacao.cancelado_por.get_full_name() if solicitacao.cancelado_por else '-'
        eventos.append({
            'tipo': 'solicitacao_cancelada',
            'icone': 'bi-x-circle',
            'cor': 'danger',
            'titulo': 'Solicitação Cancelada',
            'descricao': f'Solicitação {solicitacao.numero} foi cancelada por {usuario_cancelou}',
            'usuario': usuario_cancelou,
            'data': solicitacao.data_atualizacao,
            'detalhes': '',
        })
    
    # 2. Aprovação
    if solicitacao.data_aprovacao:
        eventos.append({
            'tipo': 'solicitacao_aprovada',
            'icone': 'bi-check-circle',
            'cor': 'success',
            'titulo': 'Solicitação Aprovada',
            'descricao': f'Aprovada por {solicitacao.aprovador.get_full_name()}',
            'usuario': solicitacao.aprovador.get_full_name() if solicitacao.aprovador else '-',
            'data': solicitacao.data_aprovacao,
            'detalhes': solicitacao.justificativa[:100] if solicitacao.justificativa else ''
        })
    
    # 3. Cotações
    for cotacao in cotacoes:
        # Criação da cotação
        eventos.append({
            'tipo': 'cotacao_criada',
            'icone': 'bi-cart3',
            'cor': 'info',
            'titulo': 'Cotação Iniciada',
            'descricao': f'Cotação {cotacao.numero} criada',
            'usuario': cotacao.comprador.get_full_name(),
            'data': cotacao.data_cadastro,
            'detalhes': f'{cotacao.itens.count()} itens para cotar',
            'link': 'compras:cotacao_detail',
            'link_id': cotacao.pk
        })
        
        # Propostas recebidas
        propostas = FornecedorCotacao.objects.filter(
            item_cotacao__cotacao=cotacao
        ).select_related('fornecedor').order_by('data_cadastro')
        
        fornecedores_unicos = {}
        for proposta in propostas:
            forn_id = proposta.fornecedor.id
            if forn_id not in fornecedores_unicos:
                fornecedores_unicos[forn_id] = {
                    'fornecedor': proposta.fornecedor,
                    'data': proposta.data_cadastro,
                    'count': 0
                }
            fornecedores_unicos[forn_id]['count'] += 1
        
        for forn_data in fornecedores_unicos.values():
            eventos.append({
                'tipo': 'proposta_recebida',
                'icone': 'bi-envelope-check',
                'cor': 'warning',
                'titulo': 'Proposta Recebida',
                'descricao': f'Proposta de {forn_data["fornecedor"].nome_fantasia}',
                'usuario': forn_data['fornecedor'].nome_fantasia,
                'data': forn_data['data'],
                'detalhes': f'{forn_data["count"]} item(ns) cotado(s)'
            })
        
        # Fornecedores selecionados
        vencedores = FornecedorCotacao.objects.filter(
            item_cotacao__cotacao=cotacao,
            selecionado=True
        ).select_related('fornecedor', 'item_cotacao__item_solicitacao__produto')
        
        for vencedor in vencedores:
            eventos.append({
                'tipo': 'fornecedor_selecionado',
                'icone': 'bi-trophy',
                'cor': 'success',
                'titulo': 'Fornecedor Vencedor',
                'descricao': f'{vencedor.fornecedor.nome_fantasia} selecionado',
                'usuario': 'Sistema',
                'data': vencedor.data_cadastro,
                'detalhes': f'{vencedor.item_cotacao.item_solicitacao.produto.nome} - R$ {vencedor.preco_total}'
            })
        
        # Conclusão da cotação
        if cotacao.status == 'CONCLUIDA':
            eventos.append({
                'tipo': 'cotacao_concluida',
                'icone': 'bi-check-circle-fill',
                'cor': 'success',
                'titulo': 'Cotação Concluída',
                'descricao': f'Cotação {cotacao.numero} finalizada',
                'usuario': cotacao.comprador.get_full_name(),
                'data': cotacao.data_cadastro,
                'detalhes': 'Pronta para gerar pedido'
            })
    
    # 4. Pedidos de Compra
    for pedido in pedidos:
        # Criação do pedido
        eventos.append({
            'tipo': 'pedido_gerado',
            'icone': 'bi-file-earmark-check',
            'cor': 'primary',
            'titulo': 'Pedido de Compra Gerado',
            'descricao': f'Pedido {pedido.numero} para {pedido.fornecedor.nome_fantasia}',
            'usuario': pedido.comprador.get_full_name(),
            'data': pedido.data_pedido,
            'detalhes': f'Valor: R$ {pedido.valor_final} | {pedido.itens.count()} itens',
            'link': 'compras:pedido_detail',
            'link_id': pedido.pk
        })

        # Envio do pedido
        if pedido.data_envio:
            eventos.append({
                'tipo': 'pedido_enviado',
                'icone': 'bi-send-check',
                'cor': 'info',
                'titulo': 'Pedido Enviado',
                'descricao': f'Pedido {pedido.numero} enviado ao fornecedor',
                'usuario': 'Sistema',
                'data': pedido.data_envio,
                'detalhes': f'{pedido.fornecedor.nome_fantasia}'
            })

        # Confirmação
        if pedido.data_confirmacao:
            eventos.append({
                'tipo': 'pedido_confirmado',
                'icone': 'bi-check2-circle',
                'cor': 'success',
                'titulo': 'Pedido Confirmado',
                'descricao': f'Fornecedor confirmou o pedido {pedido.numero}',
                'usuario': pedido.fornecedor.nome_fantasia,
                'data': pedido.data_confirmacao,
                'detalhes': f'Entrega prevista: {pedido.data_entrega_prevista.strftime("%d/%m/%Y") if pedido.data_entrega_prevista else "-"}'
            })

        # RECEBIMENTOS (incluir todos os RecebimentoCompra do pedido)
        for recebimento in pedido.recebimentos.all().order_by('data_recebimento', 'hora_recebimento'):
            eventos.append({
                'tipo': 'pedido_recebido_parcial',
                'icone': 'bi-truck',
                'cor': 'secondary',
                'titulo': 'Recebimento de Mercadorias',
                'descricao': f'Recebimento {recebimento.numero} (NF {recebimento.nota_fiscal})',
                'usuario': recebimento.recebido_por.get_full_name() if recebimento.recebido_por else '-',
                'data': timezone.make_aware(timezone.datetime.combine(recebimento.data_recebimento, recebimento.hora_recebimento)),
                'detalhes': f'Valor NF: R$ {recebimento.valor_total_nf} | Status: {recebimento.get_status_display()}',
                'link': None,  # Pode ser adicionado um link para o detalhe do recebimento se existir
                'link_id': None,
            })

        # Entrega total
        if pedido.data_entrega_real:
            eventos.append({
                'tipo': 'pedido_recebido',
                'icone': 'bi-box-seam',
                'cor': 'success',
                'titulo': 'Pedido Recebido',
                'descricao': f'Pedido {pedido.numero} totalmente recebido',
                'usuario': 'Almoxarifado',
                'data': timezone.make_aware(timezone.datetime.combine(pedido.data_entrega_real, timezone.datetime.min.time())),
                'detalhes': f'R$ {pedido.valor_final}'
            })

        # Cancelamento
        if pedido.status == 'CANCELADO':
            eventos.append({
                'tipo': 'pedido_cancelado',
                'icone': 'bi-x-circle',
                'cor': 'danger',
                'titulo': 'Pedido Cancelado',
                'descricao': f'Pedido {pedido.numero} foi cancelado',
                'usuario': 'Sistema',
                'data': pedido.data_atualizacao,
                'detalhes': pedido.observacoes_internas[-100:] if pedido.observacoes_internas else ''
            })
    
    # Ordena eventos por data
    eventos.sort(key=lambda x: x['data'])
    
    # Mensagens (conversas)
    mensagens = solicitacao.mensagens.select_related('autor').all()
    context = {
        'solicitacao': solicitacao,
        'eventos': eventos,
        'cotacoes': cotacoes,
        'pedidos': pedidos,
        'mensagens': mensagens,
    }
    return render(request, 'compras/historico_completo.html', context)


# ==================== VIEWS DE RECEBIMENTO ====================

@login_required
def recebimento_create(request, pedido_id):
    """Cria novo recebimento para um pedido"""
    from .models import RecebimentoCompra, PedidoCompra
    from .forms_recebimento import RecebimentoCompraForm, ItemRecebimentoFormSet
    
    pedido = get_object_or_404(
        PedidoCompra,
        pk=pedido_id,
        empresa=request.user.empresa
    )
    
    # Verifica se o pedido pode ser recebido
    if pedido.status not in ['ENVIADO', 'PARCIALMENTE_RECEBIDO']:
        messages.error(request, 'Este pedido não pode receber mercadorias no status atual.')
        return redirect('compras:pedido_detail', pk=pedido.pk)
    
    # Verifica se há itens pendentes
    itens_pendentes = [item for item in pedido.itens.all() if item.quantidade_pendente > 0]
    if not itens_pendentes:
        messages.error(request, 'Todos os itens deste pedido já foram recebidos.')
        return redirect('compras:pedido_detail', pk=pedido.pk)
    
    if request.method == 'POST':
        # Always set pedido in form data to avoid validation error
        post_data = request.POST.copy()
        post_data['pedido'] = pedido.pk
        form = RecebimentoCompraForm(post_data, request.FILES)
        formset = ItemRecebimentoFormSet(post_data, empresa=request.user.empresa)
        
        if form.is_valid() and formset.is_valid():
            try:
                # Calcular valor total da NF com base nos itens
                total_nf = 0
                for item_form in formset:
                    if not item_form.cleaned_data.get('DELETE', False):
                        qtd = item_form.cleaned_data.get('quantidade_recebida') or 0
                        preco = item_form.cleaned_data.get('preco_unitario') or 0
                        desconto = item_form.cleaned_data.get('valor_desconto') or 0
                        total_nf += (qtd * preco) - desconto if (qtd and preco) else 0
                recebimento = form.save(commit=False)
                recebimento.empresa = request.user.empresa
                recebimento.pedido = pedido
                recebimento.recebido_por = request.user
                recebimento.status = 'PENDENTE'
                recebimento.valor_total_nf = total_nf
                recebimento.save()
                # Salva os itens
                formset.instance = recebimento
                itens = formset.save(commit=False)
                for item in itens:
                    item.save()  # chama o save do modelo, que atualiza estoque e quantidade recebida
                # Exclui itens marcados para exclusão
                for obj in formset.deleted_objects:
                    obj.delete()
                # Recarrega o pedido do banco para garantir atualização
                pedido.refresh_from_db()
                # Atualiza lista de itens pendentes após recebimento
                itens_pendentes_atual = [item for item in pedido.itens.all() if item.quantidade_pendente > 0]
                messages.success(
                    request,
                    f'Recebimento {recebimento.numero} criado com sucesso! Entrada registrada no estoque.'
                )
                # Redireciona para a própria página se ainda houver itens pendentes, senão para lista de pedidos
                if itens_pendentes_atual:
                    messages.info(request, 'Ainda há itens pendentes para receber neste pedido.')
                    return redirect('compras:recebimento_create', pedido_id=pedido.pk)
                else:
                    return redirect('compras:pedido_list')
            except Exception as e:
                import logging
                logging.exception('Erro ao criar recebimento')
                messages.error(request, f'Erro ao criar recebimento: {str(e)}')
        else:
            # Exibe erros do formset
            if not form.is_valid():
                messages.error(request, f'Erros no formulário principal: {form.errors}')
            if not formset.is_valid():
                messages.error(request, f'Erros nos itens: {formset.errors}')
    else:
        # Passa o pedido como initial para o form
        form = RecebimentoCompraForm(initial={'pedido': pedido.pk})
        # Inicializar o formset com os itens pendentes do pedido
        initial = [
            {
                'item_pedido': item.pk,
                'quantidade_recebida': item.quantidade_pendente,
                'preco_unitario': item.preco_unitario
            }
            for item in itens_pendentes
        ]
        formset = ItemRecebimentoFormSet(initial=initial, empresa=request.user.empresa)
    
    context = {
        'form': form,
        'formset': formset,
        'pedido': pedido,
        'itens_pendentes': itens_pendentes,
    }
    
    return render(request, 'compras/recebimento_form.html', context)


@login_required
def entrada_direta_nf(request):
    """Entrada direta de NF-e (sem pedido)"""
    from decimal import Decimal
    from django.db import transaction
    from cadastros.models import Fornecedor
    from produtos.models import Produto, ProdutoFornecedor, UnidadeMedida
    from estoque.models import LocalEstocagem
    from .models import RecebimentoCompra, ItemRecebimento

    empresa = request.user.empresa
    xml_import_enabled = is_feature_enabled('COMPRAS_XML_IMPORT')

    fornecedores = Fornecedor.objects.filter(empresa=empresa, ativa=True).order_by('nome')
    produtos = Produto.objects.filter(ativo=True, categoria__empresa=empresa).order_by('nome')
    unidades = UnidadeMedida.objects.all().order_by('sigla')
    locais_estoque = LocalEstocagem.objects.filter(armazem__empresa=empresa, ativo=True).order_by('armazem__nome')

    xml_data = {}
    xml_upload_form = XMLNFeUploadForm()

    def normalize_text(value):
        return ' '.join(str(value or '').strip().lower().split())

    def normalize_document(value):
        return ''.join(char for char in str(value or '') if char.isdigit())

    def normalize_code(value):
        return str(value or '').strip().lower()

    def enrich_xml_data(parsed_data):
        fornecedor_id = None
        fornecedor_documento = normalize_document(parsed_data.get('fornecedor_documento'))
        fornecedor_nome = normalize_text(parsed_data.get('fornecedor_nome'))

        for fornecedor in fornecedores:
            fornecedor_cnpj = normalize_document(getattr(fornecedor, 'cnpj_cpf', ''))
            if fornecedor_documento and fornecedor_cnpj == fornecedor_documento:
                fornecedor_id = fornecedor.pk
                break
            if fornecedor_nome and normalize_text(fornecedor.nome) == fornecedor_nome:
                fornecedor_id = fornecedor.pk
                break
            if fornecedor_nome and normalize_text(fornecedor.nome_fantasia) == fornecedor_nome:
                fornecedor_id = fornecedor.pk
                break

        parsed_data['fornecedor_id'] = fornecedor_id

        produto_fornecedor_by_code = {}
        if fornecedor_id:
            relacoes = ProdutoFornecedor.objects.filter(
                fornecedor_id=fornecedor_id,
                produto__categoria__empresa=empresa,
                produto__ativo=True,
                ativo=True,
            ).select_related('produto')
            produto_fornecedor_by_code = {
                normalize_code(relacao.codigo_fornecedor): relacao.produto
                for relacao in relacoes
                if normalize_code(relacao.codigo_fornecedor)
            }

        produtos_by_barcode = {
            normalize_document(getattr(produto, 'codigo_barras', '')): produto
            for produto in produtos
            if normalize_document(getattr(produto, 'codigo_barras', ''))
        }

        for item in parsed_data.get('produtos', []):
            item_nome = normalize_text(item.get('nome'))
            item_codigo_fornecedor = normalize_code(item.get('codigo_fornecedor'))
            item_codigo_barras = normalize_document(item.get('codigo_barras'))
            item['produto_id'] = None
            item['unidade_medida_id'] = None

            produto_match = None
            if item_codigo_fornecedor and item_codigo_fornecedor in produto_fornecedor_by_code:
                produto_match = produto_fornecedor_by_code[item_codigo_fornecedor]
            elif item_codigo_barras and item_codigo_barras in produtos_by_barcode:
                produto_match = produtos_by_barcode[item_codigo_barras]

            if produto_match:
                item['produto_id'] = produto_match.pk
                item['unidade_medida_id'] = getattr(produto_match, 'unidade_medida_id', None)

            for produto in produtos:
                if item['produto_id']:
                    break
                if normalize_text(produto.nome) == item_nome:
                    item['produto_id'] = produto.pk
                    item['unidade_medida_id'] = getattr(produto, 'unidade_medida_id', None)
                    break
            # Estratégia 4: correspondência parcial de nome (XML contém nome do produto ou vice-versa)
            if not item['produto_id']:
                for produto in produtos:
                    nome_produto = normalize_text(produto.nome)
                    if nome_produto and item_nome and (
                        nome_produto in item_nome or item_nome in nome_produto
                    ):
                        item['produto_id'] = produto.pk
                        item['unidade_medida_id'] = getattr(produto, 'unidade_medida_id', None)
                        break
            if not item['unidade_medida_id']:
                unidade_sigla = normalize_text(item.get('unidade'))
                for unidade in unidades:
                    if normalize_text(unidade.sigla) == unidade_sigla:
                        item['unidade_medida_id'] = unidade.pk
                        break

            item['pendente'] = item['produto_id'] is None

        parsed_data['itens_pendentes'] = sum(
            1 for item in parsed_data.get('produtos', []) if item.get('pendente')
        )
        return parsed_data

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'extract_xml' and xml_import_enabled:
            xml_upload_form = XMLNFeUploadForm(request.POST, request.FILES)
            if xml_upload_form.is_valid():
                xml_file = xml_upload_form.cleaned_data['xml_file']
                try:
                    xml_bytes = xml_file.read()
                    parsed_data = parse_nfe_xml(xml_bytes.decode('utf-8-sig'))
                    xml_data = enrich_xml_data(parsed_data)
                    request.session['entrada_direta_xml_cache'] = {
                        'filename': xml_file.name,
                        'content': xml_bytes.decode('utf-8-sig'),
                    }
                    messages.success(request, 'XML processado com sucesso. Revise os dados antes de registrar a entrada.')
                except (UnicodeDecodeError, NFEImportError) as exc:
                    messages.error(request, f'Nao foi possivel extrair os dados do XML: {exc}')
            else:
                for error in xml_upload_form.errors.get('xml_file', []):
                    messages.error(request, error)

            context = {
                'fornecedores': fornecedores,
                'produtos': produtos,
                'unidades': unidades,
                'locais_estoque': locais_estoque,
                'xml_data': xml_data,
                'xml_upload_form': xml_upload_form,
                'xml_import_enabled': xml_import_enabled,
            }
            return render(request, 'compras/entrada_direta_nf.html', context)

        try:
            with transaction.atomic():
                fornecedor_id = request.POST.get('fornecedor')
                nota_fiscal = request.POST.get('nota_fiscal')
                serie_nota = request.POST.get('serie_nota') or '1'
                chave_nfe = request.POST.get('chave_nfe')
                data_emissao_nf = request.POST.get('data_emissao_nf')
                data_recebimento = request.POST.get('data_recebimento')
                hora_recebimento = request.POST.get('hora_recebimento')
                valor_total_nf = request.POST.get('valor_total_nf') or '0'
                valor_frete = request.POST.get('valor_frete') or '0'
                valor_desconto = request.POST.get('valor_desconto') or '0'
                observacoes = request.POST.get('observacoes')
                arquivo_nfe = request.FILES.get('xml_file')
                xml_cache = request.session.get('entrada_direta_xml_cache')

                if chave_nfe and RecebimentoCompra.objects.filter(
                    empresa=empresa,
                    chave_nfe=chave_nfe,
                ).exists():
                    raise ValueError('Ja existe um recebimento registrado com esta chave NF-e.')

                recebimento = RecebimentoCompra.objects.create(
                    empresa=empresa,
                    fornecedor_id=fornecedor_id,
                    numero='',
                    nota_fiscal=nota_fiscal,
                    serie_nota=serie_nota,
                    chave_nfe=chave_nfe,
                    data_emissao_nf=data_emissao_nf,
                    data_recebimento=data_recebimento,
                    hora_recebimento=hora_recebimento,
                    recebido_por=request.user,
                    status='CONFERIDO',
                    valor_total_nf=Decimal(valor_total_nf),
                    valor_frete=Decimal(valor_frete),
                    valor_desconto=Decimal(valor_desconto),
                    observacoes=observacoes or '',
                    arquivo_nfe=arquivo_nfe,
                )

                if not arquivo_nfe and xml_cache:
                    recebimento.arquivo_nfe.save(
                        xml_cache.get('filename') or f'{recebimento.numero}.xml',
                        ContentFile((xml_cache.get('content') or '').encode('utf-8')),
                        save=True,
                    )

                itens_count = int(request.POST.get('itens_count', 1))
                itens = []
                for i in range(itens_count):
                    produto_id = request.POST.get(f'produto_{i}')
                    unidade_id = request.POST.get(f'unidade_medida_{i}')
                    quantidade = request.POST.get(f'quantidade_{i}')
                    preco_unitario = request.POST.get(f'preco_unitario_{i}')
                    valor_desc = request.POST.get(f'valor_desconto_{i}') or '0'
                    local_estoque_id = request.POST.get(f'local_estoque_{i}')
                    from datetime import date as _date
                    _df_str = request.POST.get(f'data_fabricacao_{i}') or None
                    _dv_str = request.POST.get(f'data_validade_{i}') or None
                    try:
                        data_fabricacao = _date.fromisoformat(_df_str) if _df_str else None
                    except (ValueError, AttributeError):
                        data_fabricacao = None
                    try:
                        data_validade = _date.fromisoformat(_dv_str) if _dv_str else None
                    except (ValueError, AttributeError):
                        data_validade = None
                    observacoes_item = request.POST.get(f'observacoes_{i}') or ''

                    if not produto_id or not quantidade or not local_estoque_id:
                        continue

                    item = ItemRecebimento.objects.create(
                        recebimento=recebimento,
                        produto_id=produto_id,
                        unidade_medida_id=unidade_id,
                        quantidade_recebida=Decimal(quantidade),
                        preco_unitario=Decimal(preco_unitario or '0'),
                        valor_desconto=Decimal(valor_desc),
                        local_estoque_id=local_estoque_id,
                        data_fabricacao=data_fabricacao,
                        data_validade=data_validade,
                        observacoes=observacoes_item,
                    )
                    itens.append(item)

                for item in itens:
                    item.registrar_movimento_estoque()

                recebimento.status = 'FINALIZADO'
                recebimento.save(update_fields=['status'])

                if 'entrada_direta_xml_cache' in request.session:
                    del request.session['entrada_direta_xml_cache']

            messages.success(request, 'Entrada direta registrada e estoque atualizado!')
            return redirect('compras:recebimento_detail', pk=recebimento.pk)
        except Exception as e:
            messages.error(request, f'Erro ao registrar entrada direta: {str(e)}')

    context = {
        'fornecedores': fornecedores,
        'produtos': produtos,
        'unidades': unidades,
        'locais_estoque': locais_estoque,
        'xml_data': xml_data,
        'xml_upload_form': xml_upload_form,
        'xml_import_enabled': xml_import_enabled,
    }
    return render(request, 'compras/entrada_direta_nf.html', context)


@login_required
def produto_busca_ajax(request):
    """AJAX: busca produtos para vinculação manual na importação XML."""
    import json as _json
    from django.http import JsonResponse
    from django.db.models import Q
    from produtos.models import Produto

    q = request.GET.get('q', '').strip()
    empresa = request.user.empresa
    qs = Produto.objects.filter(ativo=True, categoria__empresa=empresa)
    if q:
        qs = qs.filter(
            Q(nome__icontains=q) |
            Q(codigo_barras__icontains=q) |
            Q(codigo__icontains=q)
        )
    qs = qs.order_by('nome')[:20]
    data = [
        {
            'id': p.pk,
            'nome': p.nome,
            'codigo_barras': p.codigo_barras or '',
            'codigo': p.codigo or '',
        }
        for p in qs
    ]
    return JsonResponse({'produtos': data})


@login_required
def salvar_vinculo_xml_ajax(request):
    """AJAX: persiste o vínculo produto-fornecedor para próximas importações XML."""
    import json as _json
    from django.http import JsonResponse
    from produtos.models import Produto, ProdutoFornecedor
    from cadastros.models import Fornecedor

    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método não permitido'}, status=405)

    try:
        payload = _json.loads(request.body)
        fornecedor_id = int(payload.get('fornecedor_id', 0))
        produto_id = int(payload.get('produto_id', 0))
        codigo_fornecedor = str(payload.get('codigo_fornecedor', '')).strip()
    except (ValueError, KeyError, _json.JSONDecodeError) as exc:
        return JsonResponse({'ok': False, 'error': str(exc)}, status=400)

    if not fornecedor_id or not produto_id or not codigo_fornecedor:
        return JsonResponse({'ok': False, 'error': 'Dados incompletos'}, status=400)

    empresa = request.user.empresa

    forn = Fornecedor.objects.filter(pk=fornecedor_id, empresa=empresa).first()
    if not forn:
        return JsonResponse({'ok': False, 'error': 'Fornecedor não encontrado'}, status=404)

    prod = Produto.objects.filter(pk=produto_id, categoria__empresa=empresa, ativo=True).first()
    if not prod:
        return JsonResponse({'ok': False, 'error': 'Produto não encontrado'}, status=404)

    pf, created = ProdutoFornecedor.objects.get_or_create(
        fornecedor=forn,
        produto=prod,
        defaults={'codigo_fornecedor': codigo_fornecedor, 'ativo': True},
    )
    if not created and pf.codigo_fornecedor != codigo_fornecedor:
        pf.codigo_fornecedor = codigo_fornecedor
        pf.save(update_fields=['codigo_fornecedor', 'updated_at'])

    return JsonResponse({'ok': True, 'created': created})


@login_required
def mde_list(request):
    """Lista de NF-e recebidas com gestão de Manifestação do Destinatário (MD-e)."""
    from .models import RecebimentoCompra
    from cadastros.models import Fornecedor
    from django.db.models import Q

    empresa = request.user.empresa
    qs = RecebimentoCompra.objects.filter(
        empresa=empresa,
        chave_nfe__gt='',
    ).select_related('fornecedor', 'pedido').order_by('-data_emissao_nf')

    # Filtros
    q = request.GET.get('q', '').strip()
    fornecedor_id = request.GET.get('fornecedor', '')
    mde_status = request.GET.get('mde', '')
    data_ini = request.GET.get('data_ini', '')
    data_fim = request.GET.get('data_fim', '')

    if q:
        qs = qs.filter(
            Q(nota_fiscal__icontains=q) |
            Q(chave_nfe__icontains=q) |
            Q(fornecedor__nome__icontains=q) |
            Q(fornecedor__nome_fantasia__icontains=q)
        )
    if fornecedor_id:
        qs = qs.filter(fornecedor_id=fornecedor_id)
    if mde_status == 'pendente':
        qs = qs.filter(manifestacao_tipo='')
    elif mde_status and mde_status != 'pendente':
        qs = qs.filter(manifestacao_tipo=mde_status)
    if data_ini:
        qs = qs.filter(data_emissao_nf__gte=data_ini)
    if data_fim:
        qs = qs.filter(data_emissao_nf__lte=data_fim)

    total = qs.count()
    total_pendente = qs.filter(manifestacao_tipo='').count()
    total_ciencia = qs.filter(manifestacao_tipo='ciencia_operacao').count()
    total_confirmado = qs.filter(manifestacao_tipo='confirmacao_operacao').count()
    total_outros = qs.filter(
        manifestacao_tipo__in=['desconhecimento_operacao', 'operacao_nao_realizada']
    ).count()

    from django.core.paginator import Paginator
    paginator = Paginator(qs, 30)
    page_obj = paginator.get_page(request.GET.get('page'))

    fornecedores = Fornecedor.objects.filter(empresa=empresa, ativa=True).order_by('nome')

    MDE_STATUS_CHOICES = [
        ('pendente', 'Pendente (sem manifestação)'),
        ('ciencia_operacao', 'Ciência da Operação'),
        ('confirmacao_operacao', 'Confirmação da Operação'),
        ('desconhecimento_operacao', 'Desconhecimento da Operação'),
        ('operacao_nao_realizada', 'Operação Não Realizada'),
    ]

    return render(request, 'compras/mde_list.html', {
        'page_obj': page_obj,
        'q': q,
        'fornecedor_id': fornecedor_id,
        'mde_status': mde_status,
        'data_ini': data_ini,
        'data_fim': data_fim,
        'total': total,
        'total_pendente': total_pendente,
        'total_ciencia': total_ciencia,
        'total_confirmado': total_confirmado,
        'total_outros': total_outros,
        'fornecedores': fornecedores,
        'mde_status_choices': MDE_STATUS_CHOICES,
    })


@login_required
def recebimento_list(request):
    """Lista todos os recebimentos"""
    from .models import RecebimentoCompra
    
    recebimentos = RecebimentoCompra.objects.filter(
        empresa=request.user.empresa
    ).select_related(
        'pedido',
        'pedido__fornecedor',
        'recebido_por'
    ).order_by('-data_recebimento')
    
    # Filtros
    nota_fiscal = request.GET.get('nota_fiscal')
    if nota_fiscal:
        recebimentos = recebimentos.filter(nota_fiscal__icontains=nota_fiscal)
    
    fornecedor = request.GET.get('fornecedor')
    if fornecedor:
        from django.db.models import Q
        recebimentos = recebimentos.filter(
            Q(pedido__fornecedor__id=fornecedor) | Q(fornecedor__id=fornecedor)
        )
    
    # Cards de status
    total_pendente = recebimentos.filter(status='PENDENTE').count()
    total_conferido = recebimentos.filter(status='CONFERIDO').count()
    total_divergente = recebimentos.filter(status='DIVERGENTE').count()
    total_cancelado = recebimentos.filter(status='CANCELADO').count()

    # Abas por status
    tabs = [
        ('pendente', 'Pendente de Conferência', 'PENDENTE'),
        ('conferido', 'Conferido', 'CONFERIDO'),
        ('divergente', 'Com Divergência', 'DIVERGENTE'),
        ('cancelado', 'Cancelado', 'CANCELADO'),
    ]
    tab_data = {}
    for tab_key, tab_label, tab_status in tabs:
        tab_qs = recebimentos.filter(status=tab_status)
        paginator = Paginator(tab_qs, 20)
        page_number = request.GET.get(f'{tab_key}_page', 1)
        page_obj = paginator.get_page(page_number)
        tab_data[tab_key] = {
            'label': tab_label,
            'page_obj': page_obj,
            'recebimentos': page_obj.object_list,
        }

    from cadastros.models import Fornecedor
    fornecedores = Fornecedor.objects.filter(empresa=request.user.empresa, ativa=True).order_by('nome')
    context = {
        'tab_data': tab_data,
        'tabs': tabs,
        'active_tab': request.GET.get('tab', 'pendente'),
        'total_pendente': total_pendente,
        'total_conferido': total_conferido,
        'total_divergente': total_divergente,
        'total_cancelado': total_cancelado,
        'fornecedores': fornecedores,
        'fornecedor_filtro': request.GET.get('fornecedor', ''),
        'xml_import_enabled': is_feature_enabled('COMPRAS_XML_IMPORT'),
    }

    return render(request, 'compras/recebimento_list.html', context)


@login_required
def recebimento_detail(request, pk):
    """Exibe detalhes do recebimento"""
    from .models import RecebimentoCompra
    
    recebimento = get_object_or_404(
        RecebimentoCompra,
        pk=pk,
        empresa=request.user.empresa
    )
    
    context = {
        'recebimento': recebimento,
    }
    
    return render(request, 'compras/recebimento_detail.html', context)


@login_required
def recebimento_manifestar(request, pk):
    """Registra Manifestação do Destinatário (MD-e) para NF-e recebida de fornecedor."""
    from .models import RecebimentoCompra
    from faturamento.services.integranotas import IntegranNotasClient, IntegranNotasError
    from faturamento.models import ConfiguracaoFiscal
    from django.utils import timezone

    recebimento = get_object_or_404(RecebimentoCompra, pk=pk, empresa=request.user.empresa)

    if not recebimento.chave_nfe:
        messages.error(request, 'Este recebimento não possui chave de acesso NF-e para manifestar.')
        return redirect('compras:recebimento_detail', pk=pk)

    if recebimento.manifestacao_tipo:
        messages.info(request, f'Manifestação já registrada: {recebimento.get_manifestacao_tipo_display()}.')
        return redirect('compras:recebimento_detail', pk=pk)

    TIPOS = [
        ('ciencia_operacao', 'Ciência da Operação'),
        ('confirmacao_operacao', 'Confirmação da Operação'),
        ('desconhecimento_operacao', 'Desconhecimento da Operação'),
        ('operacao_nao_realizada', 'Operação Não Realizada'),
    ]

    if request.method == 'POST':
        tipo = request.POST.get('tipo', '').strip()
        justificativa = request.POST.get('justificativa', '').strip()
        tipos_validos = [t[0] for t in TIPOS]

        if tipo not in tipos_validos:
            messages.error(request, 'Tipo de manifestação inválido.')
            return render(request, 'compras/recebimento_manifestar.html',
                          {'recebimento': recebimento, 'tipos': TIPOS})

        if tipo == 'operacao_nao_realizada' and not justificativa:
            messages.error(request, 'Justificativa obrigatória para "Operação Não Realizada".')
            return render(request, 'compras/recebimento_manifestar.html',
                          {'recebimento': recebimento, 'tipos': TIPOS})

        config = ConfiguracaoFiscal.objects.filter(empresa=request.user.empresa).first()
        if not config or not config.has_token:
            messages.error(request, 'Configure o token IntegraNota em Configuração Fiscal para registrar manifestação.')
            return redirect('compras:recebimento_detail', pk=pk)

        try:
            client = IntegranNotasClient(config.get_token(), config.ambiente_nfe)
            resultado = client.manifestar_nfe(recebimento.chave_nfe, tipo, justificativa)
        except IntegranNotasError as exc:
            messages.error(request, f'Erro ao registrar manifestação [{exc.codigo}]: {exc}')
            return render(request, 'compras/recebimento_manifestar.html',
                          {'recebimento': recebimento, 'tipos': TIPOS})
        except Exception as exc:
            messages.error(request, f'Falha na comunicação com IntegraNota: {exc}')
            return render(request, 'compras/recebimento_manifestar.html',
                          {'recebimento': recebimento, 'tipos': TIPOS})

        recebimento.manifestacao_tipo = tipo
        recebimento.manifestacao_protocolo = resultado.get('protocolo', '') or resultado.get('numero_protocolo', '')
        recebimento.manifestacao_data = timezone.now()
        recebimento.save(update_fields=['manifestacao_tipo', 'manifestacao_protocolo', 'manifestacao_data'])
        messages.success(request, f'Manifestação "{dict(TIPOS)[tipo]}" registrada com sucesso na SEFAZ.')
        return redirect('compras:recebimento_detail', pk=pk)

    return render(request, 'compras/recebimento_manifestar.html', {
        'recebimento': recebimento,
        'tipos': TIPOS,
    })


@login_required
def recebimento_conferir(request, pk):
    """Marca recebimento como conferido com suporte a divergências estruturadas"""
    from .models import RecebimentoCompra, TipoDivergencia, DivergenciaRecebimento
    
    recebimento = get_object_or_404(
        RecebimentoCompra,
        pk=pk,
        empresa=request.user.empresa
    )
    
    if recebimento.status != 'PENDENTE':
        messages.error(request, 'Este recebimento já foi conferido.')
        return redirect('compras:recebimento_detail', pk=recebimento.pk)
    
    if request.method == 'POST':
        tem_divergencia = request.POST.get('tem_divergencia') == 'sim'
        
        if not tem_divergencia:
            # Sem divergência - marcar como CONFERIDO
            recebimento.status = 'CONFERIDO'
            recebimento.save()
            messages.success(request, f'✅ Recebimento {recebimento.numero} conferido com sucesso!')
            return redirect('compras:recebimento_detail', pk=recebimento.pk)
        
        else:
            # COM divergências - processa registros estruturados
            recebimento.status = 'DIVERGENTE'
            recebimento.divergencias = request.POST.get('divergencias_texto', '')
            recebimento.save()
            
            # Salva divergências estruturadas
            num_divergencias = int(request.POST.get('num_divergencias', 0))
            
            for i in range(num_divergencias):
                tipo_id = request.POST.get(f'divergencia_{i}_tipo')
                if not tipo_id:
                    continue
                
                try:
                    tipo_divergencia = TipoDivergencia.objects.get(
                        pk=tipo_id,
                        empresa=request.user.empresa
                    )
                except TipoDivergencia.DoesNotExist:
                    messages.warning(request, f'Tipo de divergência #{i+1} não encontrado')
                    continue
                
                # Criar registro de divergência
                divergencia = DivergenciaRecebimento(
                    recebimento=recebimento,
                    tipo_divergencia=tipo_divergencia,
                    descricao_detalhes=request.POST.get(f'divergencia_{i}_descricao', ''),
                    acao_proposta=request.POST.get(f'divergencia_{i}_acao', ''),
                    registrado_por=request.user,
                )
                
                # Item opcional
                item_id = request.POST.get(f'divergencia_{i}_item')
                if item_id:
                    try:
                        from .models import ItemRecebimento
                        divergencia.item_recebimento = ItemRecebimento.objects.get(pk=item_id)
                    except:
                        pass
                
                # Quantidade afetada opcional
                qtd = request.POST.get(f'divergencia_{i}_quantidade')
                if qtd:
                    try:
                        divergencia.quantidade_afetada = float(qtd)
                    except:
                        pass
                
                divergencia.save()
            
            messages.success(
                request,
                f'⚠️ Recebimento {recebimento.numero} registrado com {num_divergencias} divergência(s)!'
            )
            return redirect('compras:recebimento_detail', pk=recebimento.pk)
    
    # GET - mostrar formulário
    tipos_divergencia = TipoDivergencia.objects.filter(
        empresa=request.user.empresa,
        ativo=True
    ).order_by('severidade', 'nome')
    
    context = {
        'recebimento': recebimento,
        'tipos_divergencia': tipos_divergencia,
    }
    
    return render(request, 'compras/recebimento_conferir.html', context)


@login_required
def recebimento_entrada_estoque(request, pk):
    """Processa a entrada dos itens do recebimento no estoque"""
    from .models import RecebimentoCompra, ItemRecebimento
    from estoque.models import MovimentacaoEstoque
    recebimento = get_object_or_404(RecebimentoCompra, pk=pk, empresa=request.user.empresa)
    # Permite entrada para recebimentos CONFERIDO ou DIVERGENTE (já conferidos)
    if recebimento.status not in ['CONFERIDO', 'DIVERGENTE']:
        from django.contrib import messages
        alertas = {
            'PENDENTE': '⏳ Este recebimento ainda não foi conferido.',
            'FINALIZADO': '✅ Este recebimento já foi finalizado e entrado em estoque.',
            'CANCELADO': '❌ Este recebimento foi cancelado.',
        }
        msg = alertas.get(recebimento.status, f'Status inválido: {recebimento.status}')
        messages.error(request, msg)
        from django.urls import reverse
        return redirect(reverse('compras:recebimento_detail', args=[recebimento.pk]))
    if request.method == 'POST':
        # Garante registro de movimentação e atualização de estoque
        for item in recebimento.itens.all():
            item.registrar_movimento_estoque()

        recebimento.status = 'FINALIZADO'
        recebimento.save()
        from django.contrib import messages
        messages.success(request, 'Itens do recebimento lançados no estoque com sucesso!')
        from django.urls import reverse
        return redirect(reverse('compras:recebimento_detail', args=[recebimento.pk]))
    from django.urls import reverse
    return redirect(reverse('compras:recebimento_detail', args=[recebimento.pk]))


@login_required
def avaliar_fornecedor(request, pk):
    """Avalia o fornecedor após finalização do recebimento"""
    from .models import RecebimentoCompra, AvaliacaoFornecedor
    
    recebimento = get_object_or_404(RecebimentoCompra, pk=pk, empresa=request.user.empresa)
    
    # Só permite avaliar se recebimento foi finalizado
    if recebimento.status != 'FINALIZADO':
        messages.error(request, '❌ Só é possível avaliar após a entrada no estoque.')
        return redirect('compras:recebimento_detail', pk=recebimento.pk)
    
    # Tenta recuperar avaliação existente
    avaliacao, criada = AvaliacaoFornecedor.objects.get_or_create(
        recebimento=recebimento,
        defaults={
            'empresa': request.user.empresa,
            'fornecedor': recebimento.pedido.fornecedor if recebimento.pedido else recebimento.fornecedor,
            'avaliador': request.user,
            'qualidade_produto': 3,
            'prazo_entrega': 3,
            'documentacao': 3,
            'atendimento': 3,
            'preco': 3,
        }
    )
    
    if request.method == 'POST':
        # Atualizar avaliação
        avaliacao.qualidade_produto = int(request.POST.get('qualidade_produto', 3))
        avaliacao.prazo_entrega = int(request.POST.get('prazo_entrega', 3))
        avaliacao.documentacao = int(request.POST.get('documentacao', 3))
        avaliacao.atendimento = int(request.POST.get('atendimento', 3))
        avaliacao.preco = int(request.POST.get('preco', 3))
        
        avaliacao.pontos_positivos = request.POST.get('pontos_positivos', '')
        avaliacao.pontos_negativos = request.POST.get('pontos_negativos', '')
        avaliacao.recomendacao = request.POST.get('recomendacao', '')
        avaliacao.recomenda = request.POST.get('recomenda') == 'sim'
        
        avaliacao.save()
        
        messages.success(
            request,
            f'⭐ Obrigado! Fornecedor avaliado com nota {avaliacao.nota_media:.1f}/5.'
        )
        return redirect('compras:recebimento_detail', pk=recebimento.pk)
    
    context = {
        'recebimento': recebimento,
        'avaliacao': avaliacao,
        'fornecedor': recebimento.pedido.fornecedor if recebimento.pedido else recebimento.fornecedor,
        'estrelas_choices': range(1, 6),
    }
    
    return render(request, 'compras/avaliar_fornecedor.html', context)


@login_required
def relatorio_pedidos_pendentes(request):
    """Relatório de pedidos de compra pendentes"""
    from .forms_relatorio import FiltroPedidosPendentesForm
    
    if request.method == 'POST':
        form = FiltroPedidosPendentesForm(request.POST, empresa=request.user.empresa)
        
        if form.is_valid():
            return processar_relatorio_pedidos(request, form)
    else:
        form = FiltroPedidosPendentesForm(empresa=request.user.empresa)
    
    context = {
        'form': form,
        'title': 'Relatório de Pedidos Pendentes',
    }
    return render(request, 'compras/relatorio_pedidos_pendentes.html', context)


def processar_relatorio_pedidos(request, form):
    """Processar e gerar relatório de pedidos pendentes"""
    from .relatorio_utils import RelatorioPedidosPendentesPDF, RelatorioPedidosPendentesExcel, gerar_dados_pedidos_pendentes
    from estoque.enviador import EnviadorRelatorio
    from datetime import datetime
    from django.http import HttpResponse
    from django.shortcuts import redirect
    from django.contrib import messages
    
    empresa = request.user.empresa
    
    # Buscar pedidos com status que indique pendência
    from .models import PedidoCompra
    pedidos = PedidoCompra.objects.filter(
        empresa=empresa
    ).exclude(
        status__in=['CANCELADO', 'FINALIZADO']
    ).select_related('fornecedor').prefetch_related('itens', 'recebimentos__itens')
    
    # Aplicar filtros
    fornecedores = form.cleaned_data.get('fornecedor')
    if fornecedores:
        pedidos = pedidos.filter(fornecedor__in=fornecedores)
    
    data_inicio = form.cleaned_data.get('data_inicio')
    if data_inicio:
        pedidos = pedidos.filter(data_pedido__gte=data_inicio)
    
    data_fim = form.cleaned_data.get('data_fim')
    if data_fim:
        pedidos = pedidos.filter(data_pedido__lte=data_fim)
    
    apenas_parciais = form.cleaned_data.get('apenas_parciais', False)
    
    # Construir descrição dos filtros
    filtros_desc = []
    if fornecedores:
        filtros_desc.append(f"Fornecedores: {', '.join([f.nome_razao for f in fornecedores])}")
    if data_inicio:
        filtros_desc.append(f"Data início: {data_inicio.strftime('%d/%m/%Y')}")
    if data_fim:
        filtros_desc.append(f"Data fim: {data_fim.strftime('%d/%m/%Y')}")
    if apenas_parciais:
        filtros_desc.append("Apenas parcialmente recebidos")
    
    filtros_str = ' | '.join(filtros_desc) if filtros_desc else 'Todos os pedidos pendentes'
    
    # Gerar dados
    pedidos_data = gerar_dados_pedidos_pendentes(pedidos)
    
    # Filtrar apenas parciais se solicitado
    if apenas_parciais:
        pedidos_data = [p for p in pedidos_data if p['status'] == 'Parcial']
    
    # Gerar relatório
    formato = form.cleaned_data.get('formato')
    nome_arquivo = f"pedidos_pendentes_{datetime.now().strftime('%d%m%Y_%H%M%S')}"
    
    if formato == 'pdf':
        relatorio = RelatorioPedidosPendentesPDF(empresa)
        relatorio.adicionar_cabecalho(filtros_str)
        relatorio.adicionar_tabela_pedidos(pedidos_data)
        arquivo_bytes = relatorio.gerar()
        nome_arquivo += '.pdf'
        tipo_mime = 'application/pdf'
    else:  # excel
        relatorio = RelatorioPedidosPendentesExcel(empresa)
        relatorio.adicionar_cabecalho(filtros_str)
        relatorio.adicionar_tabela_pedidos(pedidos_data)
        arquivo_bytes = relatorio.gerar()
        nome_arquivo += '.xlsx'
        tipo_mime = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    
    # Verificar se será enviado ou apenas baixado
    enviar_para = form.cleaned_data.get('enviar_para')
    
    if enviar_para == 'visualizar':
        # Visualizar na tela
        response = HttpResponse(arquivo_bytes, content_type=tipo_mime)
        response['Content-Disposition'] = f'inline; filename="{nome_arquivo}"'
        return response
    
    if enviar_para == 'nenhum':
        # Apenas baixar
        response = HttpResponse(arquivo_bytes, content_type=tipo_mime)
        response['Content-Disposition'] = f'attachment; filename="{nome_arquivo}"'
        return response
    
    # Enviar por email e/ou WhatsApp
    resultados = []
    
    if enviar_para in ['email', 'ambos']:
        email = form.cleaned_data.get('email_destino')
        sucesso, msg = EnviadorRelatorio.enviar(
            'email', email, empresa.nome, arquivo_bytes, 
            nome_arquivo, formato
        )
        resultados.append(('Email', sucesso, msg))
    
    if enviar_para in ['whatsapp', 'ambos']:
        whatsapp = form.cleaned_data.get('whatsapp_destino')
        sucesso, msg = EnviadorRelatorio.enviar(
            'whatsapp', whatsapp, empresa.nome, arquivo_bytes, 
            nome_arquivo, formato
        )
        resultados.append(('WhatsApp', sucesso, msg))
    
    # Exibir resultados
    for tipo, sucesso, mensagem in resultados:
        if sucesso:
            messages.success(request, f'{tipo}: {mensagem}')
        else:
            messages.error(request, f'{tipo}: {mensagem}')
    
    return redirect('compras:relatorio_pedidos_pendentes')


@login_required
def relatorio_compras(request):
    """Relatório de compras por período com detalhes de notas fiscais"""
    from .forms_relatorio_compras import FiltroRelatorioComprasForm
    
    if request.method == 'POST':
        form = FiltroRelatorioComprasForm(request.POST, empresa=request.user.empresa)
        
        if form.is_valid():
            return processar_relatorio_compras(request, form)
    else:
        form = FiltroRelatorioComprasForm(empresa=request.user.empresa)
    
    context = {
        'form': form,
        'title': 'Relatório de Compras por Período',
    }
    return render(request, 'compras/relatorio_compras.html', context)


@login_required
def relatorio_compras_simples(request):
    """Relatório simples de compras: Data, NF, Fornecedor, Valor"""
    from datetime import datetime, timedelta
    from django.db.models import Sum
    from django.utils import timezone
    from .models import RecebimentoCompra
    from cadastros.models import Fornecedor

    empresa = request.user.empresa
    hoje = timezone.now().date()

    # Filtros
    data_fim_str = request.GET.get('data_fim')
    data_inicio_str = request.GET.get('data_inicio')

    data_fim = hoje
    data_inicio = hoje - timedelta(days=30)

    if data_inicio_str:
        try:
            data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    if data_fim_str:
        try:
            data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    fornecedor_ids = request.GET.getlist('fornecedor')

    recebimentos = RecebimentoCompra.objects.filter(
        empresa=empresa,
        data_emissao_nf__gte=data_inicio,
        data_emissao_nf__lte=data_fim
    ).exclude(status='CANCELADO').select_related('pedido__fornecedor', 'fornecedor').order_by('-data_emissao_nf')

    if fornecedor_ids:
        from django.db.models import Q
        recebimentos = recebimentos.filter(
            Q(pedido__fornecedor_id__in=fornecedor_ids) | Q(fornecedor_id__in=fornecedor_ids)
        )

    # Calcular total
    total_valor = recebimentos.aggregate(total=Sum('valor_total_nf'))['total'] or 0

    # Listas de filtros
    fornecedores = Fornecedor.objects.filter(empresa=empresa, ativa=True).order_by('nome')

    context = {
        'title': 'Relatório de Compras',
        'data_inicio': data_inicio.strftime('%Y-%m-%d'),
        'data_fim': data_fim.strftime('%Y-%m-%d'),
        'fornecedores': fornecedores,
        'filtros': {
            'fornecedor': list(map(int, fornecedor_ids)) if fornecedor_ids else [],
        },
        'recebimentos': recebimentos,
        'total_valor': total_valor,
        'total_compras': recebimentos.count(),
    }
    return render(request, 'compras/relatorio_compras_simples.html', context)


@login_required
def relatorio_compras_simples_pdf(request):
    """Gera PDF do relatório simples de compras"""
    from datetime import datetime, timedelta
    from django.db.models import Sum
    from django.utils import timezone
    from .models import RecebimentoCompra
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.units import cm
    from reportlab.lib.enums import TA_CENTER
    import io

    empresa = request.user.empresa
    hoje = timezone.now().date()

    # Filtros (mesmos do relatório HTML)
    data_fim_str = request.GET.get('data_fim')
    data_inicio_str = request.GET.get('data_inicio')
    data_fim = hoje
    data_inicio = hoje - timedelta(days=30)

    if data_inicio_str:
        try:
            data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    if data_fim_str:
        try:
            data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    fornecedor_ids = request.GET.getlist('fornecedor')

    recebimentos = RecebimentoCompra.objects.filter(
        empresa=empresa,
        data_emissao_nf__gte=data_inicio,
        data_emissao_nf__lte=data_fim
    ).exclude(status='CANCELADO').select_related('pedido__fornecedor', 'fornecedor').order_by('-data_emissao_nf')

    if fornecedor_ids:
        from django.db.models import Q
        recebimentos = recebimentos.filter(
            Q(pedido__fornecedor_id__in=fornecedor_ids) | Q(fornecedor_id__in=fornecedor_ids)
        )

    # Calcular total
    total_valor = recebimentos.aggregate(total=Sum('valor_total_nf'))['total'] or 0

    # Criar PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=1*cm,
        leftMargin=1*cm,
        topMargin=1.5*cm,
        bottomMargin=1*cm,
    )

    elementos = []
    styles = getSampleStyleSheet()

    # Estilo customizado para título
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1f4788'),
        spaceAfter=10,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#666666'),
        spaceAfter=15,
        alignment=TA_CENTER,
    )

    # Cabeçalho
    elementos.append(Paragraph('Relatório de Compras', title_style))
    
    info_texto = f'<b>Empresa:</b> {empresa.nome}<br/>'
    info_texto += f'<b>Período:</b> {data_inicio.strftime("%d/%m/%Y")} a {data_fim.strftime("%d/%m/%Y")}<br/>'
    info_texto += f'<b>Gerado em:</b> {timezone.now().strftime("%d/%m/%Y às %H:%M")}'
    
    elementos.append(Paragraph(info_texto, subtitle_style))
    elementos.append(Spacer(1, 0.5*cm))

    # Tabela
    dados = [['Data Emissão', 'Nota Fiscal', 'Fornecedor', 'Valor da Compra']]

    for r in recebimentos:
        if r.pedido:
            fornecedor_nome = r.pedido.fornecedor.nome_fantasia or r.pedido.fornecedor.nome
        elif r.fornecedor:
            fornecedor_nome = r.fornecedor.nome_fantasia or r.fornecedor.nome
        else:
            fornecedor_nome = 'N/A'

        dados.append([
            r.data_emissao_nf.strftime('%d/%m/%Y'),
            f'{r.nota_fiscal} - {r.serie_nota}' if r.serie_nota else r.nota_fiscal,
            fornecedor_nome[:50],  # Limitar tamanho
            f'R$ {r.valor_total_nf:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.'),
        ])

    # Linha de total
    dados.append([
        '',
        '',
        'TOTAL GERAL',
        f'R$ {total_valor:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.'),
    ])

    # Criar tabela
    tabela = Table(dados, colWidths=[3*cm, 3.5*cm, 11*cm, 4*cm])

    # Estilo da tabela
    estilo = TableStyle([
        # Cabeçalho
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
        
        # Corpo
        ('GRID', (0, 0), (-1, -2), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f5f5f5')]),
        ('FONTSIZE', (0, 1), (-1, -2), 9),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 1), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
        ('ALIGN', (3, 1), (3, -1), 'RIGHT'),  # Valor alinhado à direita
        
        # Linha de total
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e9ecef')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 11),
        ('TOPPADDING', (0, -1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, -1), (-1, -1), 8),
        ('LINEABOVE', (0, -1), (-1, -1), 2, colors.HexColor('#1f4788')),
    ])

    tabela.setStyle(estilo)
    elementos.append(tabela)

    # Construir PDF
    doc.build(elementos)
    buffer.seek(0)

    # Retornar resposta
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    filename = f'relatorio_compras_{data_inicio.strftime("%Y%m%d")}_{data_fim.strftime("%Y%m%d")}.pdf'
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    
    return response


@login_required
def relatorio_compras_geral(request):
    """Relatório geral de compras com visão gerencial"""
    from datetime import datetime, timedelta
    from django.db.models import Sum, Count, Q
    from django.utils import timezone
    from django.contrib.auth import get_user_model
    from .models import PedidoCompra, ItemPedidoCompra, RecebimentoCompra
    from cadastros.models import Fornecedor

    empresa = request.user.empresa
    hoje = timezone.now().date()

    # Filtros
    data_fim_str = request.GET.get('data_fim')
    data_inicio_str = request.GET.get('data_inicio')

    data_fim = hoje
    data_inicio = hoje - timedelta(days=90)

    if data_inicio_str:
        try:
            data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    if data_fim_str:
        try:
            data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    fornecedor_ids = request.GET.getlist('fornecedor')
    comprador_ids = request.GET.getlist('comprador')
    status_list = request.GET.getlist('status')

    pedidos = PedidoCompra.objects.filter(
        empresa=empresa,
        data_pedido__date__gte=data_inicio,
        data_pedido__date__lte=data_fim
    ).select_related('fornecedor', 'comprador')

    if fornecedor_ids:
        pedidos = pedidos.filter(fornecedor_id__in=fornecedor_ids)
    if comprador_ids:
        pedidos = pedidos.filter(comprador_id__in=comprador_ids)
    if status_list:
        pedidos = pedidos.filter(status__in=status_list)

    # Totais
    total_pedidos = pedidos.count()
    total_valor = pedidos.aggregate(total=Sum('valor_final'))['total'] or 0
    ticket_medio = (total_valor / total_pedidos) if total_pedidos else 0

    # Itens
    itens = ItemPedidoCompra.objects.filter(pedido__in=pedidos)
    total_itens = itens.count()
    total_qtd = itens.aggregate(total=Sum('quantidade_pedida'))['total'] or 0

    # Atrasos
    pedidos_atrasados = pedidos.filter(
        data_entrega_prevista__lt=hoje
    ).exclude(status__in=['RECEBIDO', 'CANCELADO']).order_by('data_entrega_prevista')

    # Breakdown por status
    status_labels = dict(PedidoCompra.STATUS_CHOICES)
    por_status_raw = pedidos.values('status').annotate(
        total=Count('id'),
        valor=Sum('valor_final')
    ).order_by('-total')
    por_status = [
        {
            'status': s['status'],
            'label': status_labels.get(s['status'], s['status']),
            'total': s['total'],
            'valor': s['valor'] or 0,
        }
        for s in por_status_raw
    ]

    # Por fornecedor
    por_fornecedor = pedidos.values('fornecedor__nome_fantasia', 'fornecedor__nome').annotate(
        total=Count('id'),
        valor=Sum('valor_final')
    ).order_by('-valor')[:20]

    # Por comprador
    por_comprador = pedidos.values('comprador__username', 'comprador__first_name', 'comprador__last_name').annotate(
        total=Count('id'),
        valor=Sum('valor_final')
    ).order_by('-valor')[:20]

    # Top produtos
    top_produtos = itens.values('produto__nome', 'produto__unidade_medida__sigla').annotate(
        qtd=Sum('quantidade_pedida'),
        valor=Sum('preco_total')
    ).order_by('-valor')[:20]

    # Recebimentos
    recebimentos = RecebimentoCompra.objects.filter(
        empresa=empresa,
        data_recebimento__gte=data_inicio,
        data_recebimento__lte=data_fim
    ).select_related('pedido', 'fornecedor')

    if fornecedor_ids:
        recebimentos = recebimentos.filter(
            Q(pedido__fornecedor_id__in=fornecedor_ids) | Q(fornecedor_id__in=fornecedor_ids)
        )

    recebimentos_total = recebimentos.count()
    recebimentos_valor = recebimentos.aggregate(total=Sum('valor_total_nf'))['total'] or 0
    recebimento_status_labels = dict(RecebimentoCompra.STATUS_CHOICES)
    recebimentos_por_status_raw = recebimentos.values('status').annotate(
        total=Count('id'),
        valor=Sum('valor_total_nf')
    ).order_by('-total')
    recebimentos_por_status = [
        {
            'status': r['status'],
            'label': recebimento_status_labels.get(r['status'], r['status']),
            'total': r['total'],
            'valor': r['valor'] or 0,
        }
        for r in recebimentos_por_status_raw
    ]

    # Listas de filtros
    fornecedores = Fornecedor.objects.filter(empresa=empresa, ativa=True).order_by('nome')
    User = get_user_model()
    compradores = User.objects.filter(pedidos_realizados__empresa=empresa).distinct().order_by('username')

    context = {
        'title': 'Relatório Geral de Compras',
        'data_inicio': data_inicio.strftime('%Y-%m-%d'),
        'data_fim': data_fim.strftime('%Y-%m-%d'),
        'fornecedores': fornecedores,
        'compradores': compradores,
        'status_choices': PedidoCompra.STATUS_CHOICES,
        'status_labels': status_labels,
        'filtros': {
            'fornecedor': list(map(int, fornecedor_ids)) if fornecedor_ids else [],
            'comprador': list(map(int, comprador_ids)) if comprador_ids else [],
            'status': status_list,
        },
        'total_pedidos': total_pedidos,
        'total_valor': total_valor,
        'ticket_medio': ticket_medio,
        'total_itens': total_itens,
        'total_qtd': total_qtd,
        'pedidos_atrasados': pedidos_atrasados[:50],
        'por_status': por_status,
        'por_fornecedor': por_fornecedor,
        'por_comprador': por_comprador,
        'top_produtos': top_produtos,
        'recebimentos_total': recebimentos_total,
        'recebimentos_valor': recebimentos_valor,
        'recebimentos_por_status': recebimentos_por_status,
        'recebimentos_lista': recebimentos.order_by('-data_recebimento')[:50],
    }
    return render(request, 'compras/relatorio_compras_geral.html', context)


def processar_relatorio_compras(request, form):
    """Processar e gerar relatório de compras por período"""
    from .relatorio_compras_utils import RelatorioComprasPDF, RelatorioComprasExcel, gerar_dados_compras
    from estoque.enviador import EnviadorRelatorio
    from datetime import datetime
    from django.http import HttpResponse
    from django.shortcuts import redirect
    from django.contrib import messages
    
    empresa = request.user.empresa
    
    # Buscar pedidos
    from .models import PedidoCompra
    pedidos = PedidoCompra.objects.filter(
        empresa=empresa
    ).select_related('fornecedor').prefetch_related(
        'itens__produto',
        'recebimentos__itens__produto'
    )
    
    # Aplicar filtros
    fornecedores = form.cleaned_data.get('fornecedor')
    if fornecedores:
        pedidos = pedidos.filter(fornecedor__in=fornecedores)
    
    data_inicio = form.cleaned_data.get('data_inicio')
    if data_inicio:
        pedidos = pedidos.filter(data_pedido__gte=data_inicio)
    
    data_fim = form.cleaned_data.get('data_fim')
    if data_fim:
        pedidos = pedidos.filter(data_pedido__lte=data_fim)
    
    incluir_cancelados = form.cleaned_data.get('incluir_cancelados', False)
    if not incluir_cancelados:
        pedidos = pedidos.exclude(status='CANCELADO')
    
    agrupar_por_fornecedor = form.cleaned_data.get('agrupar_por_fornecedor', False)
    ordenacao = form.cleaned_data.get('ordenacao', 'fornecedor')
    
    # Construir descrição dos filtros
    filtros_desc = []
    if fornecedores:
        filtros_desc.append(f"Fornecedores: {', '.join([f.nome for f in fornecedores])}")
    if data_inicio:
        filtros_desc.append(f"Data início: {data_inicio.strftime('%d/%m/%Y')}")
    if data_fim:
        filtros_desc.append(f"Data fim: {data_fim.strftime('%d/%m/%Y')}")
    if incluir_cancelados:
        filtros_desc.append("Incluindo cancelados")
    if agrupar_por_fornecedor:
        filtros_desc.append("Agrupado por fornecedor")
    
    # Mapa de rótulos de ordenação
    ordenacao_labels = {
        'fornecedor': 'Fornecedor',
        'nota_fiscal': 'Número da Nota',
        'data_emissao': 'Data de Emissão',
    }
    filtros_desc.append(f"Ordenado por: {ordenacao_labels.get(ordenacao, ordenacao)}")
    
    filtros_str = ' | '.join(filtros_desc) if filtros_desc else 'Todas as compras'
    
    # Gerar dados
    compras_data = gerar_dados_compras(pedidos, ordenacao)
    
    # Gerar relatório
    formato = form.cleaned_data.get('formato')
    nome_arquivo = f"compras_{datetime.now().strftime('%d%m%Y_%H%M%S')}"
    
    if formato == 'pdf':
        relatorio = RelatorioComprasPDF(empresa)
        relatorio.adicionar_cabecalho(filtros_str)
        relatorio.adicionar_tabela_compras(compras_data, agrupar_por_fornecedor)
        arquivo_bytes = relatorio.gerar()
        nome_arquivo += '.pdf'
        tipo_mime = 'application/pdf'
    else:  # excel
        relatorio = RelatorioComprasExcel(empresa)
        linha_inicio = relatorio.adicionar_cabecalho(filtros_str)
        relatorio.adicionar_tabela_compras(compras_data, linha_inicio, agrupar_por_fornecedor)
        arquivo_bytes = relatorio.gerar()
        nome_arquivo += '.xlsx'
        tipo_mime = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    
    # Verificar se será enviado ou apenas baixado
    enviar_para = form.cleaned_data.get('enviar_para')
    
    if enviar_para == 'visualizar':
        # Visualizar na tela
        response = HttpResponse(arquivo_bytes, content_type=tipo_mime)
        response['Content-Disposition'] = f'inline; filename="{nome_arquivo}"'
        return response
    
    if enviar_para == 'nenhum':
        # Apenas baixar
        response = HttpResponse(arquivo_bytes, content_type=tipo_mime)
        response['Content-Disposition'] = f'attachment; filename="{nome_arquivo}"'
        return response
    
    # Enviar por email e/ou WhatsApp
    resultados = []
    
    if enviar_para in ['email', 'ambos']:
        email = form.cleaned_data.get('email_destino')
        sucesso, msg = EnviadorRelatorio.enviar(
            'email', email, empresa.nome, arquivo_bytes, 
            nome_arquivo, formato
        )
        resultados.append(('Email', sucesso, msg))
    
    if enviar_para in ['whatsapp', 'ambos']:
        whatsapp = form.cleaned_data.get('whatsapp_destino')
        sucesso, msg = EnviadorRelatorio.enviar(
            'whatsapp', whatsapp, empresa.nome, arquivo_bytes, 
            nome_arquivo, formato
        )
        resultados.append(('WhatsApp', sucesso, msg))
    
    # Exibir resultados
    for tipo, sucesso, mensagem in resultados:
        if sucesso:
            messages.success(request, f'{tipo}: {mensagem}')
        else:
            messages.error(request, f'{tipo}: {mensagem}')
    
    return redirect('compras:relatorio_compras')
