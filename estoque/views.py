"""
Views do módulo Estoque
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.db import models
from django.db.models import Sum
from datetime import timedelta
from .models import Armazem, LocalEstocagem, Lote, MovimentacaoEstoque
from .forms import (
    ArmazemForm, LocalEstocagemForm, LoteForm, MovimentacaoEstoqueForm,
    EntradaEstoqueForm, SaidaEstoqueForm, TransferenciaEstoqueForm
)
from produtos.models import Produto
from django.template.loader import get_template
import io
from xhtml2pdf import pisa


@login_required
def dashboard(request):
    """Dashboard do estoque"""
    empresa = request.user.empresa
    
    # Estatísticas
    total_armazens = Armazem.objects.filter(empresa=empresa, ativo=True).count()
    total_locais = LocalEstocagem.objects.filter(armazem__empresa=empresa, ativo=True).count()
    total_lotes = Lote.objects.filter(empresa=empresa).exclude(status='ESGOTADO').count()
    
    # Lotes vencendo nos próximos 30 dias
    data_limite = timezone.now().date() + timedelta(days=30)
    lotes_proximos_vencimento = Lote.objects.filter(
        empresa=empresa,
        data_validade__lte=data_limite,
        data_validade__gte=timezone.now().date(),
        status='DISPONIVEL'
    ).select_related('produto', 'armazem', 'unidade_medida')[:10]
    
    # Lotes vencidos
    lotes_vencidos = Lote.objects.filter(
        empresa=empresa,
        status='VENCIDO'
    ).select_related('produto')[:5]
    
    context = {
        'total_armazens': total_armazens,
        'total_locais': total_locais,
        'total_lotes': total_lotes,
        'lotes_vencendo': lotes_proximos_vencimento.count(),
        'lotes_proximos_vencimento': lotes_proximos_vencimento,
        'lotes_vencidos': lotes_vencidos,
    }
    return render(request, 'estoque/dashboard.html', context)


@login_required
def armazem_list(request):
    """Lista de armazéns"""
    armazens = Armazem.objects.filter(empresa=request.user.empresa).order_by('nome')
    return render(request, 'estoque/armazem_list.html', {'armazens': armazens})


@login_required
def armazem_create(request):
    """Criar armazém"""
    if request.method == 'POST':
        form = ArmazemForm(request.POST, empresa=request.user.empresa, usuario=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Armazém cadastrado com sucesso!')
            return redirect('estoque:armazem_list')
    else:
        form = ArmazemForm(empresa=request.user.empresa, usuario=request.user)
    
    return render(request, 'estoque/armazem_form.html', {'form': form})


@login_required
def armazem_detail(request, pk):
    """Detalhes do armazém"""
    armazem = get_object_or_404(Armazem, pk=pk, empresa=request.user.empresa)
    locais = LocalEstocagem.objects.filter(armazem=armazem).order_by('codigo')
    total_lotes = Lote.objects.filter(armazem=armazem).exclude(status='ESGOTADO').count()
    
    context = {
        'armazem': armazem,
        'locais': locais,
        'total_lotes': total_lotes,
    }
    return render(request, 'estoque/armazem_detail.html', context)


@login_required
def armazem_edit(request, pk):
    """Editar armazém"""
    armazem = get_object_or_404(Armazem, pk=pk, empresa=request.user.empresa)
    
    if request.method == 'POST':
        form = ArmazemForm(request.POST, instance=armazem, empresa=request.user.empresa, usuario=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Armazém atualizado com sucesso!')
            return redirect('estoque:armazem_detail', pk=pk)
    else:
        form = ArmazemForm(instance=armazem, empresa=request.user.empresa, usuario=request.user)
    
    return render(request, 'estoque/armazem_form.html', {'form': form})


@login_required
def armazem_delete(request, pk):
    """Deletar armazém"""
    armazem = get_object_or_404(Armazem, pk=pk, empresa=request.user.empresa)
    
    if request.method == 'POST':
        armazem.delete()
        messages.success(request, 'Armazém excluído com sucesso!')
        return redirect('estoque:armazem_list')
    
    # Se GET, redireciona para a lista
    return redirect('estoque:armazem_list')


@login_required
def local_list(request):
    """Lista de locais"""
    locais = LocalEstocagem.objects.filter(armazem__empresa=request.user.empresa).select_related('armazem').order_by('armazem__nome', 'codigo')
    return render(request, 'estoque/local_list.html', {'locais': locais})


@login_required
def local_create(request):
    """Criar local"""
    if request.method == 'POST':
        form = LocalEstocagemForm(request.POST, empresa=request.user.empresa, usuario=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Local de estocagem cadastrado com sucesso!')
            return redirect('estoque:local_list')
    else:
        form = LocalEstocagemForm(empresa=request.user.empresa, usuario=request.user)
        
        # Se vier armazem na querystring, pré-seleciona
        armazem_id = request.GET.get('armazem')
        if armazem_id:
            form.fields['armazem'].initial = armazem_id
    
    return render(request, 'estoque/local_form.html', {'form': form})


@login_required
def local_edit(request, pk):
    """Editar local"""
    local = get_object_or_404(LocalEstocagem, pk=pk, armazem__empresa=request.user.empresa)
    
    if request.method == 'POST':
        form = LocalEstocagemForm(request.POST, instance=local, empresa=request.user.empresa, usuario=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Local de estocagem atualizado com sucesso!')
            return redirect('estoque:local_list')
    else:
        form = LocalEstocagemForm(instance=local, empresa=request.user.empresa, usuario=request.user)
    
    return render(request, 'estoque/local_form.html', {'form': form})


@login_required
def local_delete(request, pk):
    """Deletar local"""
    local = get_object_or_404(LocalEstocagem, pk=pk, armazem__empresa=request.user.empresa)
    
    if request.method == 'POST':
        local.delete()
        messages.success(request, 'Local de estocagem excluído com sucesso!')
        return redirect('estoque:local_list')
    
    return redirect('estoque:local_list')


@login_required
def local_bloquear(request, pk):
    """Bloquear local"""
    local = get_object_or_404(LocalEstocagem, pk=pk, armazem__empresa=request.user.empresa)
    
    if request.method == 'POST':
        motivo = request.POST.get('motivo', 'Bloqueio manual')
        local.bloquear(request.user, motivo)
        messages.warning(request, f'Local {local.codigo} bloqueado com sucesso!')
        return redirect('estoque:local_list')
    
    return redirect('estoque:local_list')


@login_required
def local_desbloquear(request, pk):
    """Desbloquear local"""
    local = get_object_or_404(LocalEstocagem, pk=pk, armazem__empresa=request.user.empresa)
    
    if request.method == 'POST' or request.method == 'GET':
        local.desbloquear()
        messages.success(request, f'Local {local.codigo} desbloqueado com sucesso!')
        return redirect('estoque:local_list')
    
    return redirect('estoque:local_list')


@login_required
def lote_list(request):
    """Lista de lotes"""
    lotes = Lote.objects.filter(empresa=request.user.empresa).select_related(
        'produto', 'armazem', 'local_estocagem', 'unidade_medida'
    ).order_by('-data_entrada')
    return render(request, 'estoque/lote_list.html', {'lotes': lotes})


@login_required
def lote_create(request):
    """Criar lote"""
    if request.method == 'POST':
        form = LoteForm(request.POST, empresa=request.user.empresa, usuario=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Lote cadastrado com sucesso!')
            return redirect('estoque:lote_list')
    else:
        form = LoteForm(empresa=request.user.empresa, usuario=request.user)
    
    return render(request, 'estoque/lote_form.html', {'form': form})


@login_required
def lote_detail(request, pk):
    """Detalhes do lote"""
    lote = get_object_or_404(Lote, pk=pk, empresa=request.user.empresa)
    return render(request, 'estoque/lote_detail.html', {'lote': lote})


@login_required
def lote_edit(request, pk):
    """Editar lote"""
    lote = get_object_or_404(Lote, pk=pk, empresa=request.user.empresa)
    
    if request.method == 'POST':
        form = LoteForm(request.POST, instance=lote, empresa=request.user.empresa, usuario=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Lote atualizado com sucesso!')
            return redirect('estoque:lote_detail', pk=pk)
    else:
        form = LoteForm(instance=lote, empresa=request.user.empresa, usuario=request.user)
    
    return render(request, 'estoque/lote_form.html', {'form': form})


@login_required
def lote_bloquear(request, pk):
    """Bloquear lote"""
    lote = get_object_or_404(Lote, pk=pk, empresa=request.user.empresa)
    
    if request.method == 'POST':
        motivo = request.POST.get('motivo', 'Bloqueio manual')
        lote.bloquear(motivo)
        messages.warning(request, f'Lote {lote.numero_lote} bloqueado com sucesso!')
        return redirect('estoque:lote_detail', pk=pk)
    
    return redirect('estoque:lote_detail', pk=pk)


@login_required
def lote_desbloquear(request, pk):
    """Desbloquear lote"""
    lote = get_object_or_404(Lote, pk=pk, empresa=request.user.empresa)
    
    if request.method == 'POST' or request.method == 'GET':
        lote.desbloquear()
        messages.success(request, f'Lote {lote.numero_lote} desbloqueado com sucesso!')
        return redirect('estoque:lote_detail', pk=pk)
    
    return redirect('estoque:lote_detail', pk=pk)


# ============================================
# MOVIMENTAÇÕES DE ESTOQUE (FASE 2)
# ============================================

@login_required
def movimentacao_list(request):
    """Lista todas as movimentações"""
    movimentacoes = MovimentacaoEstoque.objects.filter(
        empresa=request.user.empresa
    ).select_related(
        'lote__produto', 'armazem_origem', 'armazem_destino',
        'cadastrado_por', 'aprovador', 'executado_por'
    ).order_by('-data_movimentacao')
    
    # Filtros
    tipo = request.GET.get('tipo')
    status = request.GET.get('status')
    
    if tipo:
        movimentacoes = movimentacoes.filter(tipo=tipo)
    if status:
        movimentacoes = movimentacoes.filter(status=status)
    
    context = {
        'movimentacoes': movimentacoes,
        'tipos': MovimentacaoEstoque.TIPO_CHOICES,
        'status_choices': MovimentacaoEstoque.STATUS_CHOICES,
        'tipo_filtro': tipo,
        'status_filtro': status,
    }
    return render(request, 'estoque/movimentacao_list.html', context)


@login_required
def movimentacao_create(request):
    """Criar movimentação genérica"""
    if request.method == 'POST':
        form = MovimentacaoEstoqueForm(
            request.POST,
            empresa=request.user.empresa,
            usuario=request.user
        )
        if form.is_valid():
            movimentacao = form.save()
            messages.success(request, f'Movimentação {movimentacao.numero} criada com sucesso!')
            return redirect('estoque:movimentacao_detail', pk=movimentacao.pk)
    else:
        form = MovimentacaoEstoqueForm(empresa=request.user.empresa, usuario=request.user)
    
    return render(request, 'estoque/movimentacao_form.html', {
        'form': form,
        'titulo': 'Nova Movimentação'
    })


@login_required
def movimentacao_detail(request, pk):
    """Detalhes da movimentação"""
    movimentacao = get_object_or_404(
        MovimentacaoEstoque,
        pk=pk,
        empresa=request.user.empresa
    )
    return render(request, 'estoque/movimentacao_detail.html', {'movimentacao': movimentacao})


@login_required
def movimentacao_aprovar(request, pk):
    """Aprovar movimentação"""
    movimentacao = get_object_or_404(
        MovimentacaoEstoque,
        pk=pk,
        empresa=request.user.empresa
    )
    
    if request.method == 'POST':
        try:
            movimentacao.aprovar(request.user)
            messages.success(request, f'Movimentação {movimentacao.numero} aprovada!')
        except Exception as e:
            messages.error(request, f'Erro ao aprovar: {str(e)}')
        return redirect('estoque:movimentacao_detail', pk=pk)
    
    return redirect('estoque:movimentacao_detail', pk=pk)


@login_required
def movimentacao_executar(request, pk):
    """Executar movimentação e atualizar estoque"""
    movimentacao = get_object_or_404(
        MovimentacaoEstoque,
        pk=pk,
        empresa=request.user.empresa
    )
    
    if request.method == 'POST':
        try:
            movimentacao.executar(request.user)
            messages.success(request, f'Movimentação {movimentacao.numero} executada! Estoque atualizado.')
        except Exception as e:
            messages.error(request, f'Erro ao executar: {str(e)}')
        return redirect('estoque:movimentacao_detail', pk=pk)
    
    return redirect('estoque:movimentacao_detail', pk=pk)


@login_required
def movimentacao_cancelar(request, pk):
    """Cancelar movimentação"""
    movimentacao = get_object_or_404(
        MovimentacaoEstoque,
        pk=pk,
        empresa=request.user.empresa
    )
    
    if request.method == 'POST':
        try:
            movimentacao.cancelar()
            messages.warning(request, f'Movimentação {movimentacao.numero} cancelada.')
        except Exception as e:
            messages.error(request, f'Erro ao cancelar: {str(e)}')
        return redirect('estoque:movimentacao_detail', pk=pk)
    
    return redirect('estoque:movimentacao_detail', pk=pk)


@login_required
def entrada_create(request):
    """Entrada de estoque"""
    if request.method == 'POST':
        form = EntradaEstoqueForm(
            request.POST,
            empresa=request.user.empresa,
            usuario=request.user
        )
        if form.is_valid():
            movimentacao = form.save()
            messages.success(request, f'Entrada {movimentacao.numero} registrada!')
            return redirect('estoque:movimentacao_detail', pk=movimentacao.pk)
    else:
        form = EntradaEstoqueForm(empresa=request.user.empresa, usuario=request.user)
    
    return render(request, 'estoque/movimentacao_form.html', {
        'form': form,
        'titulo': 'Entrada de Estoque',
        'tipo': 'ENTRADA'
    })


@login_required
def saida_create(request):
    """Saída de estoque"""
    if request.method == 'POST':
        form = SaidaEstoqueForm(
            request.POST,
            empresa=request.user.empresa,
            usuario=request.user
        )
        if form.is_valid():
            movimentacao = form.save()
            messages.success(request, f'Saída {movimentacao.numero} registrada!')
            return redirect('estoque:movimentacao_detail', pk=movimentacao.pk)
    else:
        form = SaidaEstoqueForm(empresa=request.user.empresa, usuario=request.user)
    
    return render(request, 'estoque/movimentacao_form.html', {
        'form': form,
        'titulo': 'Saída de Estoque',
        'tipo': 'SAIDA'
    })


@login_required
def transferencia_create(request):
    """Transferência entre armazéns"""
    if request.method == 'POST':
        form = TransferenciaEstoqueForm(
            request.POST,
            empresa=request.user.empresa,
            usuario=request.user
        )
        if form.is_valid():
            movimentacao = form.save()
            messages.success(request, f'Transferência {movimentacao.numero} registrada!')
            return redirect('estoque:movimentacao_detail', pk=movimentacao.pk)
    else:
        form = TransferenciaEstoqueForm(empresa=request.user.empresa, usuario=request.user)
    
    return render(request, 'estoque/movimentacao_form.html', {
        'form': form,
        'titulo': 'Transferência entre Armazéns',
        'tipo': 'TRANSFERENCIA'
    })


@login_required
def get_lotes_disponiveis(request):
    """API para buscar lotes disponíveis de um produto (para JavaScript)"""
    produto_id = request.GET.get('produto_id')
    armazem_id = request.GET.get('armazem_id')
    
    lotes = Lote.objects.filter(
        empresa=request.user.empresa,
        produto_id=produto_id,
        status='DISPONIVEL',
        quantidade_atual__gt=0
    )
    
    if armazem_id:
        lotes = lotes.filter(armazem_id=armazem_id)
    
    lotes_data = [{
        'id': lote.id,
        'numero_lote': lote.numero_lote,
        'quantidade_disponivel': float(lote.quantidade_atual),
        'unidade': lote.unidade_medida.sigla,
        'data_validade': lote.data_validade.strftime('%d/%m/%Y') if lote.data_validade else None,
        'armazem': lote.armazem.nome,
    } for lote in lotes]
    
    return JsonResponse({'lotes': lotes_data})


@login_required
def estoque_produtos_list(request):
    """Listagem de produtos do estoque"""
    empresa = request.user.empresa
    busca = request.GET.get('busca', '')
    produtos = Produto.objects.filter(ativo=True, categoria__empresa=empresa)
    if busca:
        produtos = produtos.filter(nome__icontains=busca)
    # Recalcula estoque a partir dos lotes disponíveis
    for produto in produtos:
        total_estoque = produto.lotes.filter(status='DISPONIVEL').aggregate(
            total=Sum('quantidade_atual')
        )['total'] or 0
        produto.estoque_total = total_estoque
        if produto.estoque_atual != total_estoque:
            produto.estoque_atual = total_estoque
            produto.save(update_fields=['estoque_atual'])
    context = {
        'produtos': produtos,
        'busca': busca,
    }
    return render(request, 'estoque/estoque_produtos_list.html', context)


@login_required
def produto_historico(request, pk):
    """Histórico do produto"""
    produto = get_object_or_404(Produto, pk=pk)
    empresa = request.user.empresa

    # Filtros
    tipo_filtro = request.GET.get('tipo')
    origem_filtro = request.GET.get('origem')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')

    movimentacoes = MovimentacaoEstoque.objects.filter(
        empresa=empresa,
        lote__produto=produto
    ).select_related('lote', 'armazem_origem', 'armazem_destino', 'executado_por').order_by('-data_cadastro')

    if tipo_filtro:
        movimentacoes = movimentacoes.filter(tipo=tipo_filtro)
    if origem_filtro:
        movimentacoes = movimentacoes.filter(origem=origem_filtro)
    if data_inicio:
        movimentacoes = movimentacoes.filter(data_cadastro__date__gte=data_inicio)
    if data_fim:
        movimentacoes = movimentacoes.filter(data_cadastro__date__lte=data_fim)

    # Estatísticas
    stats = {
        'total_entradas': movimentacoes.filter(tipo='ENTRADA').aggregate(total=models.Sum('quantidade'))['total'] or 0,
        'total_saidas': movimentacoes.filter(tipo='SAIDA').aggregate(total=models.Sum('quantidade'))['total'] or 0,
        'total_transferencias': movimentacoes.filter(tipo='TRANSFERENCIA').count(),
        'total_compras': movimentacoes.filter(origem='COMPRA').count(),
        'total_solicitacoes': movimentacoes.filter(origem='REQUISICAO').count(),
    }

    # Compras relacionadas (se houver app de compras)
    try:
        from compras.models import ItemPedidoCompra
        compras = ItemPedidoCompra.objects.filter(
            produto=produto,
            pedido__empresa=empresa
        ).select_related('pedido').order_by('-pedido__data_pedido')
    except Exception as e:
        import logging
        logging.exception(f"Erro ao buscar compras para produto {produto.id}: {str(e)}")
        compras = []

    # Solicitações relacionadas (se houver app de compras)
    try:
        from compras.models import ItemSolicitacaoCompra
        solicitacoes = ItemSolicitacaoCompra.objects.filter(produto=produto, solicitacao__empresa=empresa).select_related('solicitacao')
    except Exception:
        solicitacoes = []

    # Empréstimos relacionados (se houver app de empréstimos)
    try:
        from emprestimos.models import ItemEmprestimo
        emprestimos = ItemEmprestimo.objects.filter(produto=produto, emprestimo__empresa=empresa).select_related('emprestimo')
    except Exception:
        emprestimos = []

    context = {
        'produto': produto,
        'movimentacoes': movimentacoes,
        'stats': stats,
        'compras': compras,
        'solicitacoes': solicitacoes,
        'emprestimos': emprestimos,
        'tipo_filtro': tipo_filtro,
        'origem_filtro': origem_filtro,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
    }
    return render(request, 'estoque/produto_historico.html', context)


@login_required
def produto_historico_pdf(request, pk):
    """Gera PDF do histórico do produto"""
    produto = get_object_or_404(Produto, pk=pk)
    # Aqui você pode adicionar lógica para buscar o histórico real do produto, se necessário
    context = {
        'produto': produto,
        # Adicione outros dados do histórico conforme necessário
    }
    template = get_template('estoque/produto_historico_pdf.html')
    html = template.render(context)
    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(html.encode('UTF-8')), result)
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return HttpResponse('Erro ao gerar PDF', status=500)


@login_required
def relatorio_estoque(request):
    """Exibir formulário de filtros para relatório de estoque"""
    from .forms_relatorio import FiltroRelatorioEstoqueForm
    
    if request.method == 'POST':
        form = FiltroRelatorioEstoqueForm(request.POST, empresa=request.user.empresa)
        
        if form.is_valid():
            return processar_relatorio(request, form)
    else:
        form = FiltroRelatorioEstoqueForm(empresa=request.user.empresa)
    
    context = {
        'form': form,
        'title': 'Relatório de Estoque',
    }
    return render(request, 'estoque/relatorio_estoque.html', context)


def processar_relatorio(request, form):
    """Processar e gerar o relatório"""
    from .relatorio_utils import RelatorioEstoquePDF, RelatorioEstoqueExcel
    from .enviador import EnviadorRelatorio
    from datetime import datetime
    
    empresa = request.user.empresa
    
    # Iniciar query de lotes
    lotes = Lote.objects.filter(empresa=empresa).select_related(
        'produto', 'armazem', 'unidade_medida'
    )
    
    # Aplicar filtros
    armazens = form.cleaned_data.get('armazem')
    if armazens:
        lotes = lotes.filter(armazem__in=armazens)
    
    categorias = form.cleaned_data.get('categoria')
    if categorias:
        lotes = lotes.filter(produto__categoria__in=categorias)
    
    status_lote = form.cleaned_data.get('status_lote')
    if status_lote:
        lotes = lotes.filter(status__in=status_lote)
    
    if form.cleaned_data.get('apenas_baixo_estoque'):
        lotes = lotes.filter(
            produto__estoque_atual__lt=models.F('produto__estoque_minimo')
        )
    
    if form.cleaned_data.get('apenas_vencidos'):
        lotes = lotes.filter(status='VENCIDO')
    
    # Construir descrição dos filtros
    filtros_desc = []
    if armazens:
        filtros_desc.append(f"Armazéns: {', '.join([a.nome for a in armazens])}")
    if categorias:
        filtros_desc.append(f"Categorias: {', '.join([c.nome for c in categorias])}")
    if status_lote:
        filtros_desc.append(f"Status: {', '.join([dict(Lote.STATUS_CHOICES).get(s) for s in status_lote])}")
    if form.cleaned_data.get('apenas_baixo_estoque'):
        filtros_desc.append("Apenas baixo estoque")
    if form.cleaned_data.get('apenas_vencidos'):
        filtros_desc.append("Apenas lotes vencidos")
    
    filtros_str = ' | '.join(filtros_desc) if filtros_desc else 'Nenhum filtro aplicado'
    
    # Gerar relatório
    enviar_para = form.cleaned_data.get('enviar_para')
    formato = form.cleaned_data.get('formato')
    nome_arquivo = f"relatorio_estoque_{datetime.now().strftime('%d%m%Y_%H%M%S')}"

    if enviar_para == 'tela':
        # Visualizar na tela (HTML)
        context = {
            'form': form,
            'title': 'Relatório de Estoque',
            'lotes': lotes,
            'filtros_str': filtros_str,
        }
        return render(request, 'estoque/relatorio_estoque_tela.html', context)

    if formato == 'pdf':
        relatorio = RelatorioEstoquePDF(empresa, titulo='Relatório de Estoque')
        relatorio.adicionar_cabecalho(filtros_str)
        relatorio.adicionar_tabela_lotes(lotes)
        relatorio.adicionar_resumo_produtos(lotes)
        arquivo_bytes = relatorio.gerar()
        nome_arquivo += '.pdf'
        tipo_mime = 'application/pdf'
    else:  # excel
        relatorio = RelatorioEstoqueExcel(empresa)
        relatorio.adicionar_cabecalho(filtros_str)
        linha = relatorio.adicionar_tabela_lotes(lotes)
        relatorio.adicionar_resumo_produtos(lotes, linha_inicio=linha + 2)
        arquivo_bytes = relatorio.gerar()
        nome_arquivo += '.xlsx'
        tipo_mime = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

    # Verificar se será enviado ou apenas baixado
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

    return redirect('estoque:relatorio_estoque')


@login_required
def relatorio_produto(request):
    """Exibir formulário de filtros para relatório de estoque por produto"""
    from .forms_relatorio_produto import FiltroRelatorioProdutoForm
    
    if request.method == 'POST':
        form = FiltroRelatorioProdutoForm(request.POST, empresa=request.user.empresa)
        
        if form.is_valid():
            return processar_relatorio_produto(request, form)
    else:
        form = FiltroRelatorioProdutoForm(empresa=request.user.empresa)
    
    context = {
        'form': form,
        'title': 'Relatório de Estoque por Produto',
    }
    return render(request, 'estoque/relatorio_produto.html', context)


def processar_relatorio_produto(request, form):
    """Processar e gerar o relatório por produto"""
    from .relatorio_produto_utils import RelatorioProdutoPDF, RelatorioProdutoExcel, gerar_dados_relatorio_produto
    from .enviador import EnviadorRelatorio
    from datetime import datetime
    
    empresa = request.user.empresa
    
    # Iniciar query de lotes
    lotes = Lote.objects.filter(empresa=empresa).select_related(
        'produto', 'armazem', 'unidade_medida', 'produto__categoria'
    )
    
    # Aplicar filtros
    armazens = form.cleaned_data.get('armazem')
    if armazens:
        lotes = lotes.filter(armazem__in=armazens)
    
    categorias = form.cleaned_data.get('categoria')
    if categorias:
        lotes = lotes.filter(produto__categoria__in=categorias)
    
    if form.cleaned_data.get('apenas_baixo_estoque'):
        lotes = lotes.filter(
            produto__estoque_atual__lt=models.F('produto__estoque_minimo')
        )
    
    incluir_zerados = form.cleaned_data.get('incluir_zerados', False)
    
    # Construir descrição dos filtros
    filtros_desc = []
    if armazens:
        filtros_desc.append(f"Armazéns: {', '.join([a.nome for a in armazens])}")
    if categorias:
        filtros_desc.append(f"Categorias: {', '.join([c.nome for c in categorias])}")
    if form.cleaned_data.get('apenas_baixo_estoque'):
        filtros_desc.append("Apenas baixo estoque")
    if incluir_zerados:
        filtros_desc.append("Incluindo produtos zerados")
    
    filtros_str = ' | '.join(filtros_desc) if filtros_desc else 'Nenhum filtro aplicado'
    
    # Gerar dados agregados por produto
    ordenacao = form.cleaned_data.get('ordenacao', 'produto')
    produtos_data = gerar_dados_relatorio_produto(lotes, empresa, incluir_zerados, ordenacao)
    
    # Gerar relatório
    formato = form.cleaned_data.get('formato')
    nome_arquivo = f"relatorio_produto_{datetime.now().strftime('%d%m%Y_%H%M%S')}"
    
    if formato == 'pdf':
        relatorio = RelatorioProdutoPDF(empresa)
        relatorio.adicionar_cabecalho(filtros_str)
        relatorio.adicionar_tabela_produtos(produtos_data)
        arquivo_bytes = relatorio.gerar()
        nome_arquivo += '.pdf'
        tipo_mime = 'application/pdf'
    else:  # excel
        relatorio = RelatorioProdutoExcel(empresa)
        relatorio.adicionar_cabecalho(filtros_str)
        relatorio.adicionar_tabela_produtos(produtos_data)
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
    
    return redirect('estoque:relatorio_produto')


