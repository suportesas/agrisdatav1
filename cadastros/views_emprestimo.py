
from datetime import date
import base64
from uuid import uuid4

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.core.paginator import Paginator
from django.db.models import Count, Sum, Q
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from estoque.models import MovimentacaoEstoque

from .emprestimo_utils import (
    criar_mensagem_emprestimo,
    enviar_whatsapp_emprestimo,
    marcar_mensagens_emprestimo_como_lidas,
    registrar_interacao_emprestimo,
    usuario_pode_interagir_emprestimo,
)
from .forms_emprestimo import EmprestimoExtratoFiltroForm, EmprestimoDevolucaoForm
from .models import EmprestimoMensagemAnexo, EmprestimoProdutor, EmprestimoMovimento
from .relatorio_utils_emprestimo import gerar_extrato_emprestimo_excel, gerar_extrato_emprestimo_pdf


def _recalcular_estoque_produto(produto, empresa):
    """Recalcula estoque_atual do produto somando todas as MovimentacaoEstoque da empresa."""
    from django.db.models import Sum, Q
    from decimal import Decimal
    movs = MovimentacaoEstoque.objects.filter(
        Q(produto=produto) | Q(lote__produto=produto),
        empresa=empresa,
    )
    entrada = movs.filter(tipo='ENTRADA').aggregate(total=Sum('quantidade'))['total'] or Decimal('0')
    saida = movs.filter(tipo='SAIDA').aggregate(total=Sum('quantidade'))['total'] or Decimal('0')
    produto.estoque_atual = Decimal(entrada) - Decimal(saida)
    produto.save(update_fields=['estoque_atual'])


# --- AJAX endpoint para registrar alerta visual exibido ---
@login_required
@require_POST
def registrar_alerta_visual_exibido(request):
    """Endpoint AJAX para registrar exibição do alerta visual de mensagens não lidas do produtor."""
    emprestimo_id = request.POST.get('emprestimo_id')
    if not emprestimo_id:
        return HttpResponse('ID do empréstimo não informado.', status=400)
    try:
        emprestimo = EmprestimoProdutor.objects.get(pk=emprestimo_id, empresa=request.user.empresa)
    except EmprestimoProdutor.DoesNotExist:
        return HttpResponse('Empréstimo não encontrado.', status=404)
    registrar_interacao_emprestimo(
        emprestimo,
        'ALERTA_VISUAL_EXIBIDO',
        'Alerta visual de mensagens do produtor exibido para o usuário.',
        usuario=request.user,
        sucesso=True,
    )
    return HttpResponse('OK')

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.core.paginator import Paginator
from django.db.models import Count, Sum, Q
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from estoque.models import MovimentacaoEstoque

from .emprestimo_utils import (
    criar_mensagem_emprestimo,
    enviar_whatsapp_emprestimo,
    marcar_mensagens_emprestimo_como_lidas,
    registrar_interacao_emprestimo,
    usuario_pode_interagir_emprestimo,
)
from .forms_emprestimo import EmprestimoExtratoFiltroForm, EmprestimoDevolucaoForm
from .models import EmprestimoMensagemAnexo, EmprestimoProdutor, EmprestimoMovimento
from .relatorio_utils_emprestimo import gerar_extrato_emprestimo_excel, gerar_extrato_emprestimo_pdf


def atualizar_promessas_vencidas(empresa):
    hoje = date.today()
    pendentes = EmprestimoProdutor.objects.filter(
        empresa=empresa,
        status='PROMESSA',
        data_promessa_devolucao__lt=hoje,
    ).exclude(saldo_pendente__lte=0)

    total = 0
    for emprestimo in pendentes:
        emprestimo.status = 'NORMAL'
        emprestimo.save(update_fields=['status', 'saldo_pendente', 'atualizado_em'])
        total += 1
    return total


def _filtrar_emprestimos(empresa, cleaned_data):
    qs = EmprestimoProdutor.objects.filter(empresa=empresa).select_related('produtor', 'produto', 'requisicao')

    produtor = cleaned_data.get('produtor')
    produto = cleaned_data.get('produto')
    status = cleaned_data.get('status')
    data_inicio = cleaned_data.get('data_inicio')
    data_fim = cleaned_data.get('data_fim')
    apenas_vencidos = cleaned_data.get('apenas_vencidos')
    apenas_mensagens_nao_lidas = cleaned_data.get('apenas_mensagens_nao_lidas')

    if produtor:
        qs = qs.filter(produtor=produtor)
    if produto:
        qs = qs.filter(produto=produto)
    if status:
        qs = qs.filter(status=status)
    if data_inicio:
        qs = qs.filter(data_emprestimo__date__gte=data_inicio)
    if data_fim:
        qs = qs.filter(data_emprestimo__date__lte=data_fim)
    if apenas_vencidos:
        qs = qs.filter(data_promessa_devolucao__lt=date.today()).exclude(saldo_pendente__lte=0)
    if apenas_mensagens_nao_lidas:
        qs = qs.filter(mensagens__perfil_autor='PRODUTOR', mensagens__lido_interno_em__isnull=True)

    return qs.annotate(
        unread_mensagens_interno_count=Count(
            'mensagens',
            filter=Q(mensagens__perfil_autor='PRODUTOR', mensagens__lido_interno_em__isnull=True),
        )
    ).distinct().order_by('-data_emprestimo', '-id')


@login_required
def emprestimo_extrato(request):
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        messages.error(request, 'Usuário sem empresa vinculada.')
        return redirect('dashboard:index')

    total_atualizados = atualizar_promessas_vencidas(empresa)
    if total_atualizados:
        messages.warning(request, f'{total_atualizados} empréstimo(s) com promessa vencida foram convertidos para normal.')

    form = EmprestimoExtratoFiltroForm(request.GET or None, empresa=empresa)
    # PLANO: Garante que o queryset do extrato pega todos os EmprestimoProdutor da empresa, sem filtros extras, inclusive registros novos ou sem movimentação
    if not request.GET:
        emprestimos_qs = EmprestimoProdutor.objects.filter(empresa=empresa).select_related('produtor', 'produto', 'requisicao').annotate(
            unread_mensagens_interno_count=Count(
                'mensagens',
                filter=Q(mensagens__perfil_autor='PRODUTOR', mensagens__lido_interno_em__isnull=True),
            )
        ).order_by('-data_emprestimo', '-id')
    else:
        # Se houver filtros, aplica normalmente
        if form.is_valid():
            emprestimos_qs = _filtrar_emprestimos(empresa, form.cleaned_data)
        else:
            emprestimos_qs = EmprestimoProdutor.objects.filter(empresa=empresa).select_related('produtor', 'produto', 'requisicao').annotate(
                unread_mensagens_interno_count=Count(
                    'mensagens',
                    filter=Q(mensagens__perfil_autor='PRODUTOR', mensagens__lido_interno_em__isnull=True),
                )
            ).order_by('-data_emprestimo', '-id')

    # Agrupar por requisição

    from decimal import Decimal
    agrupados = {}
    for emp in emprestimos_qs.select_related('produto', 'requisicao'):
        req_id = emp.requisicao_id or f"emp-{emp.pk}"
        if req_id not in agrupados:
            agrupados[req_id] = {
                'data_emprestimo': emp.data_emprestimo,
                'numero_requisicao': emp.requisicao.numero if emp.requisicao else '-',
                'produtor': emp.produtor,
                'status': emp.status,
                'data_promessa_devolucao': emp.data_promessa_devolucao,
                'emprestimos': [],
                'total_emprestado': Decimal('0.00'),
                'total_devolvido': Decimal('0.00'),
                'saldo_pendente': Decimal('0.00'),
                'total_emprestado_valor': Decimal('0.00'),
                'total_devolvido_valor': Decimal('0.00'),
                'saldo_pendente_valor': Decimal('0.00'),
                'unread_mensagens_interno': 0,
                # Adiciona referência direta aos campos de assinatura da requisição
                'requisicao': emp.requisicao,
            }
        agrupados[req_id]['emprestimos'].append(emp)
        preco = getattr(emp.produto, 'preco_venda', Decimal('0.00'))
        # Quantidade
        agrupados[req_id]['total_emprestado'] += Decimal(emp.quantidade_emprestada or 0)
        agrupados[req_id]['total_devolvido'] += Decimal(emp.quantidade_devolvida or 0)
        agrupados[req_id]['saldo_pendente'] += Decimal(emp.saldo_pendente or 0)
        # Valor financeiro
        agrupados[req_id]['total_emprestado_valor'] += Decimal(emp.quantidade_emprestada or 0) * preco
        agrupados[req_id]['total_devolvido_valor'] += Decimal(emp.quantidade_devolvida or 0) * preco
        agrupados[req_id]['saldo_pendente_valor'] += Decimal(emp.saldo_pendente or 0) * preco
        agrupados[req_id]['unread_mensagens_interno'] += emp.unread_mensagens_interno if hasattr(emp, 'unread_mensagens_interno') else 0

    agrupados_lista = sorted(agrupados.values(), key=lambda x: (x['data_emprestimo'], x['numero_requisicao']), reverse=True)

    # Paginação manual
    paginator = Paginator(agrupados_lista, 25)
    pagina_obj = paginator.get_page(request.GET.get('page'))

    query_params = request.GET.copy()
    if 'page' in query_params:
        query_params.pop('page')
    query_string = query_params.urlencode()


    # Totais financeiros globais
    total_emprestado_valor = Decimal('0.00')
    total_devolvido_valor = Decimal('0.00')
    total_saldo_valor = Decimal('0.00')
    for grupo in agrupados.values():
        total_emprestado_valor += grupo['total_emprestado_valor']
        total_devolvido_valor += grupo['total_devolvido_valor']
        total_saldo_valor += grupo['saldo_pendente_valor']

    totais = emprestimos_qs.aggregate(
        total_emprestado=Sum('quantidade_emprestada'),
        total_devolvido=Sum('quantidade_devolvida'),
        total_saldo=Sum('saldo_pendente'),
    )
    totais['total_emprestado_valor'] = total_emprestado_valor
    totais['total_devolvido_valor'] = total_devolvido_valor
    totais['total_saldo_valor'] = total_saldo_valor

    from datetime import date
    today = date.today()

    return render(request, 'cadastros/emprestimo/extrato_list.html', {
        'form': form,
        'emprestimos_agrupados': pagina_obj,
        'pagina_obj': pagina_obj,
        'query_string': query_string,
        'totais': totais,
        'today': today,
    })


@login_required
def emprestimo_detalhe(request, pk):
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        messages.error(request, 'Usuário sem empresa vinculada.')
        return redirect('dashboard:index')


    emprestimo = get_object_or_404(
        EmprestimoProdutor.objects.select_related('produtor', 'produto', 'requisicao', 'unidade_medida'),
        pk=pk,
        empresa=empresa,
    )


    # Buscar todos os produtos da mesma requisição e remover duplicidade manualmente
    if emprestimo.requisicao_id:
        emprestimos_lote_qs = EmprestimoProdutor.objects.filter(
            empresa=empresa,
            requisicao_id=emprestimo.requisicao_id
        ).select_related('produtor', 'produto', 'unidade_medida', 'requisicao')
        # Deduplicação manual por produto e unidade_medida
        seen = set()
        emprestimos_lote = []
        for emp in emprestimos_lote_qs:
            key = (emp.produto_id, emp.unidade_medida_id)
            if key not in seen:
                seen.add(key)
                emprestimos_lote.append(emp)
    else:
        emprestimos_lote = list(EmprestimoProdutor.objects.filter(pk=emprestimo.pk, empresa=empresa))

    # Movimentações agrupadas por produto
    movimentos_lote = {}
    for emp in emprestimos_lote:
        movimentos_lote[emp.pk] = list(
            EmprestimoMovimento.objects
            .filter(empresa=empresa, emprestimo=emp)
            .select_related('criado_por')
            .order_by('-data_movimento', '-id')
        )

    # Mensagens e interações do empréstimo selecionado
    marcar_mensagens_emprestimo_como_lidas(emprestimo, 'INTERNO')
    mensagens = emprestimo.mensagens.select_related('autor').prefetch_related('anexos').all()
    interacoes = emprestimo.interacoes.select_related('usuario').all()[:20]

    ultima_interacao_whatsapp = emprestimo.interacoes.filter(
        tipo_interacao__in=['WHATSAPP_SUCESSO', 'WHATSAPP_FALHA']
    ).order_by('-criado_em').first()

    return render(request, 'cadastros/emprestimo/emprestimo_detail.html', {
        'emprestimo': emprestimo,
        'emprestimos_lote': emprestimos_lote,
        'movimentos_lote': movimentos_lote,
        'mensagens_emprestimo': mensagens,
        'interacoes_emprestimo': interacoes,
        'ultima_interacao_whatsapp': ultima_interacao_whatsapp,
    })


@login_required
def emprestimo_reenviar_whatsapp(request, pk):
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        messages.error(request, 'Usuário sem empresa vinculada.')
        return redirect('dashboard:index')

    emprestimo = get_object_or_404(
        EmprestimoProdutor.objects.select_related('liberado_por', 'produtor'),
        pk=pk,
        empresa=empresa,
    )
    if not usuario_pode_interagir_emprestimo(request.user, emprestimo):
        messages.error(request, 'Você não tem permissão para reenviar o WhatsApp deste empréstimo.')
        return redirect('cadastros:emprestimo_detalhe', pk=emprestimo.pk)

    if request.method != 'POST':
        return redirect('cadastros:emprestimo_detalhe', pk=emprestimo.pk)

    sucesso, retorno = enviar_whatsapp_emprestimo(request, emprestimo)
    if sucesso:
        messages.success(request, retorno)
    else:
        messages.error(request, retorno)
    return redirect('cadastros:emprestimo_detalhe', pk=emprestimo.pk)


@login_required
def emprestimo_mensagem_create(request, pk):
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        messages.error(request, 'Usuário sem empresa vinculada.')
        return redirect('dashboard:index')

    emprestimo = get_object_or_404(EmprestimoProdutor.objects.select_related('liberado_por'), pk=pk, empresa=empresa)
    if not usuario_pode_interagir_emprestimo(request.user, emprestimo):
        messages.error(request, 'Você não tem permissão para interagir neste empréstimo.')
        return redirect('cadastros:emprestimo_detalhe', pk=emprestimo.pk)

    if request.method != 'POST':
        return redirect('cadastros:emprestimo_detalhe', pk=emprestimo.pk)

    texto_mensagem = (request.POST.get('mensagem') or '').strip()
    arquivos = request.FILES.getlist('anexos')
    if not texto_mensagem and not arquivos:
        messages.error(request, 'Informe uma mensagem ou anexe pelo menos um arquivo.')
        return redirect('cadastros:emprestimo_detalhe', pk=emprestimo.pk)

    criar_mensagem_emprestimo(emprestimo, request.user, 'INTERNO', texto_mensagem or 'Mensagem com anexo.', arquivos)
    messages.success(request, 'Mensagem registrada no histórico do empréstimo.')
    return redirect('cadastros:emprestimo_detalhe', pk=emprestimo.pk)


@login_required
def emprestimo_mensagem_anexo_download(request, anexo_id):
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        messages.error(request, 'Usuário sem empresa vinculada.')
        return redirect('dashboard:index')

    anexo = get_object_or_404(
        EmprestimoMensagemAnexo.objects.select_related('mensagem__emprestimo__liberado_por'),
        pk=anexo_id,
        mensagem__empresa=empresa,
    )
    emprestimo = anexo.mensagem.emprestimo
    if not usuario_pode_interagir_emprestimo(request.user, emprestimo):
        messages.error(request, 'Você não tem permissão para baixar este anexo.')
        return redirect('cadastros:emprestimo_detalhe', pk=emprestimo.pk)

    registrar_interacao_emprestimo(
        emprestimo,
        'DOWNLOAD_ANEXO',
        f'Anexo baixado: {anexo.nome_original or anexo.arquivo.name}',
        usuario=request.user,
        sucesso=True,
    )
    return FileResponse(anexo.arquivo.open('rb'), as_attachment=True, filename=anexo.nome_original or None)


@login_required
def emprestimo_assinar_liberacao(request, pk):
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        messages.error(request, 'Usuário sem empresa vinculada.')
        return redirect('dashboard:index')


    emprestimo = get_object_or_404(
        EmprestimoProdutor.objects.select_related('produtor', 'produto', 'unidade_medida', 'requisicao'),
        pk=pk,
        empresa=empresa,
    )


    # Buscar todos os empréstimos da mesma requisição e deduplicar manualmente
    if emprestimo.requisicao_id:
        emprestimos_lote_qs = EmprestimoProdutor.objects.filter(
            empresa=empresa,
            requisicao_id=emprestimo.requisicao_id
        ).select_related('produtor', 'produto', 'unidade_medida', 'requisicao')
        seen = set()
        emprestimos_lote = []
        for emp in emprestimos_lote_qs:
            key = (emp.produto_id, emp.unidade_medida_id)
            if key not in seen:
                seen.add(key)
                emprestimos_lote.append(emp)
    else:
        emprestimos_lote = list(EmprestimoProdutor.objects.filter(pk=emprestimo.pk, empresa=empresa))

    if request.user.tipo not in ['ADMIN', 'GERENTE']:
        messages.error(request, 'Você não tem permissão para assinar a liberação deste empréstimo.')
        return redirect('cadastros:emprestimo_detalhe', pk=emprestimo.pk)


    # Se TODOS já possuem assinatura, não permitir nova assinatura
    if all(e.possui_assinatura_liberador for e in emprestimos_lote):
        messages.warning(request, 'Todos os produtos desta requisição já possuem assinatura de liberação registrada.')
        return redirect('cadastros:emprestimo_detalhe', pk=emprestimo.pk)



    if request.method == 'POST':
        assinatura_data = (request.POST.get('assinatura_data') or '').strip()
        assinatura_nome = (request.POST.get('assinatura_liberador_nome') or '').strip()
        assinatura_upload = request.FILES.get('assinatura_upload')
        modo = request.POST.get('modo_assinatura', 'desenho')

        if not assinatura_nome:
            assinatura_nome = request.user.get_full_name() or request.user.username

        if modo == 'upload' and not assinatura_upload:
            messages.error(request, 'Selecione um arquivo de imagem para a assinatura.')
            return render(request, 'cadastros/emprestimo/emprestimo_assinar_liberacao.html', {'emprestimos_lote': emprestimos_lote, 'emprestimo': emprestimo})

        if modo == 'desenho' and not assinatura_data:
            messages.error(request, 'Desenhe a assinatura antes de salvar.')
            return render(request, 'cadastros/emprestimo/emprestimo_assinar_liberacao.html', {'emprestimos_lote': emprestimos_lote, 'emprestimo': emprestimo})

        try:
            requisicao = emprestimo.requisicao
            if requisicao is None:
                messages.error(request, 'Requisição não encontrada para este empréstimo.')
                return redirect('cadastros:emprestimo_detalhe', pk=emprestimo.pk)

            if requisicao.assinatura_liberacao_interna_imagem:
                messages.warning(request, 'Esta requisição já possui assinatura de liberação registrada.')
                return redirect('cadastros:emprestimo_detalhe', pk=emprestimo.pk)

            if modo == 'upload':
                filename = f'assinatura_requisicao_{requisicao.pk}_{uuid4().hex[:8]}.png'
                requisicao.assinatura_liberacao_interna_imagem.save(filename, assinatura_upload, save=False)
            else:
                if ',' in assinatura_data:
                    _, assinatura_b64 = assinatura_data.split(',', 1)
                else:
                    assinatura_b64 = assinatura_data
                assinatura_bin = base64.b64decode(assinatura_b64)
                filename = f'assinatura_requisicao_{requisicao.pk}_{uuid4().hex[:8]}.png'
                requisicao.assinatura_liberacao_interna_imagem.save(filename, ContentFile(assinatura_bin), save=False)

            requisicao.assinatura_liberacao_interna_nome = assinatura_nome
            requisicao.assinatura_liberacao_interna_datahora = timezone.now()
            requisicao.assinatura_liberacao_interna_usuario = request.user
            requisicao.save(update_fields=[
                'assinatura_liberacao_interna_imagem',
                'assinatura_liberacao_interna_nome',
                'assinatura_liberacao_interna_datahora',
                'assinatura_liberacao_interna_usuario',
            ])

            messages.success(request, 'Liberação da requisição assinada.')
            return redirect('cadastros:emprestimo_detalhe', pk=emprestimo.pk)
        except Exception:
            messages.error(request, 'Não foi possível processar a assinatura eletrônica da liberação.')

    return render(request, 'cadastros/emprestimo/emprestimo_assinar_liberacao.html', {
        'emprestimos_lote': emprestimos_lote,
        'emprestimo': emprestimo,
    })


@login_required
def emprestimo_exportar_excel(request):
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        messages.error(request, 'Usuário sem empresa vinculada.')
        return redirect('dashboard:index')

    form = EmprestimoExtratoFiltroForm(request.GET or None, empresa=empresa)
    emprestimos = _filtrar_emprestimos(empresa, form.cleaned_data if form.is_valid() else {})

    content = gerar_extrato_emprestimo_excel(empresa, emprestimos)
    response = HttpResponse(content, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="extrato_emprestimos_{timezone.now().strftime("%Y%m%d_%H%M")}.xlsx"'
    return response


@login_required
def emprestimo_extrato_imprimir(request):
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return redirect('dashboard:index')

    form = EmprestimoExtratoFiltroForm(request.GET or None, empresa=empresa)
    if form.is_valid():
        emprestimos_qs = _filtrar_emprestimos(empresa, form.cleaned_data)
    else:
        emprestimos_qs = EmprestimoProdutor.objects.filter(empresa=empresa).select_related(
            'produtor', 'produto', 'requisicao'
        ).order_by('-data_emprestimo', '-id')

    from decimal import Decimal
    agrupados = {}
    for emp in emprestimos_qs.select_related('produto', 'requisicao', 'produtor'):
        req_id = emp.requisicao_id or f'emp-{emp.pk}'
        if req_id not in agrupados:
            agrupados[req_id] = {
                'data_emprestimo': emp.data_emprestimo,
                'numero_requisicao': emp.requisicao.numero if emp.requisicao else '-',
                'produtor': emp.produtor,
                'status': emp.status,
                'data_promessa_devolucao': emp.data_promessa_devolucao,
                'emprestimos': [],
                'total_emprestado_valor': Decimal('0.00'),
                'total_devolvido_valor': Decimal('0.00'),
                'saldo_pendente_valor': Decimal('0.00'),
                'requisicao': emp.requisicao,
            }
        agrupados[req_id]['emprestimos'].append(emp)
        preco = Decimal(getattr(emp.produto, 'preco_venda', 0) or 0)
        agrupados[req_id]['total_emprestado_valor'] += Decimal(emp.quantidade_emprestada or 0) * preco
        agrupados[req_id]['total_devolvido_valor'] += Decimal(emp.quantidade_devolvida or 0) * preco
        agrupados[req_id]['saldo_pendente_valor'] += Decimal(emp.saldo_pendente or 0) * preco

    grupos = sorted(agrupados.values(), key=lambda x: (x['data_emprestimo'], x['numero_requisicao']), reverse=True)
    total_emprestado = sum(g['total_emprestado_valor'] for g in grupos)
    total_devolvido = sum(g['total_devolvido_valor'] for g in grupos)
    total_saldo = sum(g['saldo_pendente_valor'] for g in grupos)

    filtros = form.cleaned_data if form.is_valid() else {}

    return render(request, 'cadastros/emprestimo/extrato_print.html', {
        'empresa': empresa,
        'grupos': grupos,
        'total_emprestado': total_emprestado,
        'total_devolvido': total_devolvido,
        'total_saldo': total_saldo,
        'filtros': filtros,
        'form': form,
    })


@login_required
def emprestimo_exportar_pdf(request):
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        messages.error(request, 'Usuário sem empresa vinculada.')
        return redirect('dashboard:index')

    form = EmprestimoExtratoFiltroForm(request.GET or None, empresa=empresa)
    emprestimos = _filtrar_emprestimos(empresa, form.cleaned_data if form.is_valid() else {})

    content = gerar_extrato_emprestimo_pdf(empresa, emprestimos)
    response = HttpResponse(content, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="extrato_emprestimos_{timezone.now().strftime("%Y%m%d_%H%M")}.pdf"'
    return response


@login_required
def emprestimo_imprimir(request, pk):
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return redirect('dashboard:index')

    emprestimo = get_object_or_404(
        EmprestimoProdutor.objects.select_related('produtor', 'produto', 'requisicao', 'unidade_medida'),
        pk=pk, empresa=empresa,
    )

    if emprestimo.requisicao_id:
        emprestimos_lote_qs = EmprestimoProdutor.objects.filter(
            empresa=empresa, requisicao_id=emprestimo.requisicao_id
        ).select_related('produto', 'unidade_medida', 'requisicao')
        seen = set()
        emprestimos_lote = []
        for emp in emprestimos_lote_qs:
            key = (emp.produto_id, emp.unidade_medida_id)
            if key not in seen:
                seen.add(key)
                emprestimos_lote.append(emp)
    else:
        emprestimos_lote = list(EmprestimoProdutor.objects.filter(pk=emprestimo.pk, empresa=empresa))

    movimentos_lote = {}
    for emp in emprestimos_lote:
        movimentos_lote[emp.pk] = list(
            EmprestimoMovimento.objects.filter(empresa=empresa, emprestimo=emp)
            .select_related('criado_por')
            .order_by('data_movimento', 'id')
        )

    mensagens = emprestimo.mensagens.select_related('autor').all()

    from decimal import Decimal
    total_valor = sum(
        Decimal(emp.quantidade_emprestada or 0) * Decimal(getattr(emp.produto, 'preco_venda', 0) or 0)
        for emp in emprestimos_lote
    )

    return render(request, 'cadastros/emprestimo/emprestimo_print.html', {
        'emprestimo': emprestimo,
        'emprestimos_lote': emprestimos_lote,
        'movimentos_lote': movimentos_lote,
        'mensagens_emprestimo': mensagens,
        'empresa': empresa,
        'total_valor': total_valor,
    })


@login_required
def emprestimo_devolucao_create(request):
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        messages.error(request, 'Usuário sem empresa vinculada.')
        return redirect('dashboard:index')

    if request.method == 'POST':
        form = EmprestimoDevolucaoForm(request.POST, request.FILES, empresa=empresa)
        if form.is_valid():
            emprestimo = form.cleaned_data['emprestimo']
            quantidade = form.cleaned_data['quantidade']
            data_movimento = form.cleaned_data.get('data_movimento') or timezone.now()
            comprovante = form.cleaned_data.get('comprovante')
            observacoes = form.cleaned_data.get('observacoes') or ''

            emprestimo.quantidade_devolvida = (emprestimo.quantidade_devolvida or 0) + quantidade
            emprestimo.save()

            EmprestimoMovimento.objects.create(
                empresa=empresa,
                emprestimo=emprestimo,
                tipo_movimento='DEVOLUCAO',
                quantidade=quantidade,
                saldo_resultante=emprestimo.saldo_pendente,
                data_movimento=data_movimento,
                documento_referencia=f'DEV-{emprestimo.id}',
                comprovante=comprovante,
                observacoes=observacoes,
                criado_por=request.user,
            )

            MovimentacaoEstoque.objects.create(
                tipo='ENTRADA',
                origem='REQUISICAO',
                status='EXECUTADO',
                empresa=empresa,
                produto=emprestimo.produto,
                unidade_medida=emprestimo.unidade_medida,
                quantidade=quantidade,
                documento=f'DEV-{emprestimo.id}',
                requisitante=request.user,
                executado_por=request.user,
                data_movimentacao=data_movimento,
                data_execucao=timezone.now(),
                observacao=f'Devolução de empréstimo - Produtor: {emprestimo.produtor.razao_social}',
            )
            _recalcular_estoque_produto(emprestimo.produto, empresa)

            messages.success(request, 'Devolução registrada com sucesso.')
            return redirect('cadastros:emprestimo_extrato')
    else:
        form = EmprestimoDevolucaoForm(empresa=empresa)

    return render(request, 'cadastros/emprestimo/devolucao_form.html', {
        'form': form,
        'titulo': 'Registrar Devolução de Empréstimo',
    })
