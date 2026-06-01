from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import ContaBancariaForm, ConciliacaoManualForm, ImportarExtratoForm
from .matching import sugerir_matches
from .models import (
    ConciliacaoLancamento,
    ContaBancaria,
    ExtratoLancamento,
    ImportacaoExtrato,
)


# ---------------------------------------------------------------------------
# ContaBancaria — CRUD
# ---------------------------------------------------------------------------

@login_required
def conta_bancaria_list(request):
    empresa = request.user.empresa
    contas = ContaBancaria.objects.filter(empresa=empresa).order_by('-conta_principal', 'banco')

    # Anota última importação de cada conta
    for conta in contas:
        ultima = conta.importacoes.order_by('-importado_em').first()
        conta.ultima_importacao = ultima

    return render(request, 'bancario/conta_list.html', {'contas': contas})


@login_required
def conta_bancaria_create(request):
    empresa = request.user.empresa
    if request.method == 'POST':
        form = ContaBancariaForm(request.POST)
        if form.is_valid():
            conta = form.save(commit=False)
            conta.empresa = empresa
            conta.save()
            messages.success(request, f'Conta {conta.banco} criada com sucesso.')
            return redirect('bancario:conta_bancaria_detail', pk=conta.pk)
    else:
        form = ContaBancariaForm()

    return render(request, 'bancario/conta_form.html', {
        'form': form,
        'titulo': 'Nova Conta Bancária',
    })


@login_required
def conta_bancaria_detail(request, pk):
    empresa = request.user.empresa
    conta = get_object_or_404(ContaBancaria, pk=pk, empresa=empresa)
    importacoes = conta.importacoes.order_by('-importado_em')[:10]

    # Totais de lançamentos
    total_lancamentos = conta.lancamentos.count()
    pendentes = conta.lancamentos.filter(status_conciliacao='PENDENTE').count()
    conciliados = conta.lancamentos.filter(status_conciliacao='CONCILIADO').count()

    return render(request, 'bancario/conta_detail.html', {
        'conta': conta,
        'importacoes': importacoes,
        'total_lancamentos': total_lancamentos,
        'pendentes': pendentes,
        'conciliados': conciliados,
    })


@login_required
def conta_bancaria_edit(request, pk):
    empresa = request.user.empresa
    conta = get_object_or_404(ContaBancaria, pk=pk, empresa=empresa)

    if request.method == 'POST':
        form = ContaBancariaForm(request.POST, instance=conta)
        if form.is_valid():
            form.save()
            messages.success(request, 'Conta atualizada com sucesso.')
            return redirect('bancario:conta_bancaria_detail', pk=conta.pk)
    else:
        form = ContaBancariaForm(instance=conta)

    return render(request, 'bancario/conta_form.html', {
        'form': form,
        'conta': conta,
        'titulo': f'Editar Conta: {conta.banco}',
    })


@login_required
def conta_bancaria_toggle(request, pk):
    empresa = request.user.empresa
    conta = get_object_or_404(ContaBancaria, pk=pk, empresa=empresa)

    if request.method == 'POST':
        conta.ativa = not conta.ativa
        conta.save(update_fields=['ativa', 'atualizado_em'])
        acao = 'ativada' if conta.ativa else 'desativada'
        messages.success(request, f'Conta {acao} com sucesso.')
        return redirect('bancario:conta_bancaria_detail', pk=conta.pk)

    return render(request, 'bancario/conta_confirm_toggle.html', {'conta': conta})


# ---------------------------------------------------------------------------
# Importação de Extrato
# ---------------------------------------------------------------------------

@login_required
def importar_extrato(request, pk):
    empresa = request.user.empresa
    conta = get_object_or_404(ContaBancaria, pk=pk, empresa=empresa, ativa=True)

    if request.method == 'GET':
        form = ImportarExtratoForm()
        return render(request, 'bancario/importar_extrato.html', {'form': form, 'conta': conta})

    form = ImportarExtratoForm(request.POST, request.FILES)
    if not form.is_valid():
        return render(request, 'bancario/importar_extrato.html', {'form': form, 'conta': conta})

    tipo = form.cleaned_data['tipo_arquivo']
    arquivo = form.cleaned_data['arquivo']

    importacao = ImportacaoExtrato.objects.create(
        conta_bancaria=conta,
        empresa=empresa,
        tipo_arquivo=tipo,
        arquivo=arquivo,
        status='PROCESSANDO',
        importado_por=request.user,
    )

    try:
        with transaction.atomic():
            if tipo == 'OFX':
                from .parsers.ofx_parser import parse_ofx
                arquivo.seek(0)
                dados = parse_ofx(arquivo)
            else:
                from .parsers.cnab240_parser import parse_cnab240
                arquivo.seek(0)
                dados = parse_cnab240(arquivo)

            if not dados.get('lancamentos'):
                raise ValueError('Nenhum lançamento encontrado no arquivo. Verifique o formato e o tipo selecionado.')

            total_debitos = Decimal('0.00')
            total_creditos = Decimal('0.00')
            criados = 0
            duplicados = 0

            for item in dados['lancamentos']:
                # Deduplicação por fit_id + conta_bancaria
                if item.get('fit_id') and ExtratoLancamento.objects.filter(
                    conta_bancaria=conta, fit_id=item['fit_id']
                ).exists():
                    duplicados += 1
                    continue

                ExtratoLancamento.objects.create(
                    importacao=importacao,
                    conta_bancaria=conta,
                    data_lancamento=item['data'],
                    tipo=item['tipo'],
                    valor=item['valor'],
                    descricao=item.get('descricao', '') or '',
                    numero_documento=item.get('numero_documento', '') or '',
                    fit_id=item.get('fit_id', '') or '',
                    status_conciliacao='PENDENTE',
                )
                criados += 1

                if item['tipo'] == 'DEBITO':
                    total_debitos += item['valor']
                else:
                    total_creditos += item['valor']

            importacao.status = 'CONCLUIDA'
            importacao.data_inicio_extrato = dados.get('data_inicio')
            importacao.data_fim_extrato = dados.get('data_fim')
            importacao.total_lancamentos = criados
            importacao.total_debitos = total_debitos
            importacao.total_creditos = total_creditos
            importacao.save()

    except Exception as exc:
        importacao.status = 'ERRO'
        importacao.erro_mensagem = str(exc)
        importacao.save(update_fields=['status', 'erro_mensagem'])
        messages.error(request, f'Erro ao processar o arquivo: {exc}')
        return redirect('bancario:conta_bancaria_detail', pk=conta.pk)

    aviso_dup = f' ({duplicados} duplicatas ignoradas)' if duplicados else ''
    messages.success(request, f'{criados} lançamentos importados com sucesso{aviso_dup}.')
    return redirect('bancario:conciliacao_workspace', importacao_pk=importacao.pk)


@login_required
def importacao_detail(request, pk):
    empresa = request.user.empresa
    importacao = get_object_or_404(ImportacaoExtrato, pk=pk, empresa=empresa)
    lancamentos = importacao.lancamentos.order_by('data_lancamento', 'tipo')

    paginator = Paginator(lancamentos, 50)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'bancario/importacao_detail.html', {
        'importacao': importacao,
        'conta': importacao.conta_bancaria,
        'page_obj': page_obj,
        'total_pendentes': lancamentos.filter(status_conciliacao='PENDENTE').count(),
        'total_conciliados': lancamentos.filter(status_conciliacao='CONCILIADO').count(),
        'total_ignorados': lancamentos.filter(status_conciliacao='IGNORADO').count(),
    })


@login_required
def importacao_deletar(request, pk):
    empresa = request.user.empresa
    importacao = get_object_or_404(ImportacaoExtrato, pk=pk, empresa=empresa)

    if request.method == 'POST':
        tem_conciliados = importacao.lancamentos.filter(status_conciliacao='CONCILIADO').exists()
        if tem_conciliados:
            messages.error(request, 'Não é possível excluir uma importação com lançamentos conciliados.')
            return redirect('bancario:importacao_detail', pk=pk)

        conta_pk = importacao.conta_bancaria_id
        importacao.delete()
        messages.success(request, 'Importação excluída com sucesso.')
        return redirect('bancario:conta_bancaria_detail', pk=conta_pk)

    return render(request, 'bancario/importacao_confirm_deletar.html', {'importacao': importacao})


# ---------------------------------------------------------------------------
# Conciliação Bancária
# ---------------------------------------------------------------------------

@login_required
def conciliacao_workspace(request, importacao_pk):
    empresa = request.user.empresa
    importacao = get_object_or_404(ImportacaoExtrato, pk=importacao_pk, empresa=empresa)

    pendentes = importacao.lancamentos.filter(
        status_conciliacao='PENDENTE'
    ).order_by('data_lancamento')

    conciliados = importacao.lancamentos.filter(
        status_conciliacao='CONCILIADO'
    ).select_related('conciliacao').order_by('data_lancamento')

    ignorados = importacao.lancamentos.filter(
        status_conciliacao='IGNORADO'
    ).order_by('data_lancamento')

    # Totais financeiros
    total_debito_pendente = pendentes.filter(tipo='DEBITO').aggregate(s=Sum('valor'))['s'] or Decimal('0')
    total_credito_pendente = pendentes.filter(tipo='CREDITO').aggregate(s=Sum('valor'))['s'] or Decimal('0')

    manual_form = ConciliacaoManualForm()

    return render(request, 'bancario/conciliacao_workspace.html', {
        'importacao': importacao,
        'conta': importacao.conta_bancaria,
        'pendentes': pendentes,
        'conciliados': conciliados,
        'ignorados': ignorados,
        'manual_form': manual_form,
        'stats': {
            'pendentes': pendentes.count(),
            'conciliados': conciliados.count(),
            'ignorados': ignorados.count(),
            'total_debito_pendente': total_debito_pendente,
            'total_credito_pendente': total_credito_pendente,
        },
    })


@login_required
def conciliacao_confirmar(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método não permitido'}, status=405)

    empresa = request.user.empresa
    lancamento_id = request.POST.get('lancamento_id')
    tipo_operacao = request.POST.get('tipo_operacao')
    operacao_id = request.POST.get('operacao_id')
    score = int(request.POST.get('score', 0))
    manual = request.POST.get('manual', 'false').lower() == 'true'

    lancamento = get_object_or_404(
        ExtratoLancamento,
        pk=lancamento_id,
        conta_bancaria__empresa=empresa,
        status_conciliacao='PENDENTE',
    )

    with transaction.atomic():
        kwargs = {
            'lancamento_extrato': lancamento,
            'tipo_operacao': tipo_operacao,
            'score_matching': score,
            'conciliado_manualmente': manual or score < 80,
            'conciliado_por': request.user,
            'conciliado_em': timezone.now(),
        }

        if tipo_operacao == 'CONTA_PAGAR' and operacao_id:
            kwargs['pagamento_conta_pagar_id'] = int(operacao_id)
        elif tipo_operacao == 'CONTA_RECEBER' and operacao_id:
            kwargs['recebimento_conta_receber_id'] = int(operacao_id)

        ConciliacaoLancamento.objects.create(**kwargs)
        lancamento.status_conciliacao = 'CONCILIADO'
        lancamento.save(update_fields=['status_conciliacao'])

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'lancamento_id': lancamento_id})

    messages.success(request, 'Lançamento conciliado com sucesso.')
    return redirect('bancario:conciliacao_workspace', importacao_pk=lancamento.importacao_id)


@login_required
def conciliacao_ignorar(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método não permitido'}, status=405)

    empresa = request.user.empresa
    lancamento_id = request.POST.get('lancamento_id')
    lancamento = get_object_or_404(
        ExtratoLancamento,
        pk=lancamento_id,
        conta_bancaria__empresa=empresa,
    )

    lancamento.status_conciliacao = 'IGNORADO'
    lancamento.save(update_fields=['status_conciliacao'])

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})

    messages.info(request, 'Lançamento marcado como ignorado.')
    return redirect('bancario:conciliacao_workspace', importacao_pk=lancamento.importacao_id)


@login_required
def conciliacao_desfazer(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método não permitido'}, status=405)

    empresa = request.user.empresa
    lancamento_id = request.POST.get('lancamento_id')
    lancamento = get_object_or_404(
        ExtratoLancamento,
        pk=lancamento_id,
        conta_bancaria__empresa=empresa,
    )

    with transaction.atomic():
        ConciliacaoLancamento.objects.filter(lancamento_extrato=lancamento).delete()
        lancamento.status_conciliacao = 'PENDENTE'
        lancamento.save(update_fields=['status_conciliacao'])

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})

    messages.success(request, 'Conciliação desfeita.')
    return redirect('bancario:conciliacao_workspace', importacao_pk=lancamento.importacao_id)


@login_required
def conciliacao_manual(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método não permitido'}, status=405)

    empresa = request.user.empresa
    lancamento_id = request.POST.get('lancamento_id')
    lancamento = get_object_or_404(
        ExtratoLancamento,
        pk=lancamento_id,
        conta_bancaria__empresa=empresa,
        status_conciliacao='PENDENTE',
    )

    form = ConciliacaoManualForm(request.POST)
    if form.is_valid():
        with transaction.atomic():
            obs = form.cleaned_data.get('observacoes', '')
            ConciliacaoLancamento.objects.create(
                lancamento_extrato=lancamento,
                tipo_operacao='LANCAMENTO_MANUAL',
                descricao_manual=form.cleaned_data['descricao_manual'],
                score_matching=0,
                conciliado_manualmente=True,
                conciliado_por=request.user,
                conciliado_em=timezone.now(),
            )
            lancamento.status_conciliacao = 'CONCILIADO'
            if obs:
                lancamento.observacoes = obs
            lancamento.save(update_fields=['status_conciliacao', 'observacoes'])

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})

        messages.success(request, 'Lançamento manual registrado.')
    else:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)
        messages.error(request, 'Preencha a descrição do lançamento.')

    return redirect('bancario:conciliacao_workspace', importacao_pk=lancamento.importacao_id)


# ---------------------------------------------------------------------------
# Relatório de Conciliação
# ---------------------------------------------------------------------------

@login_required
def relatorio_conciliacao(request):
    empresa = request.user.empresa
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')
    conta_id = request.GET.get('conta', '')

    qs = ExtratoLancamento.objects.filter(conta_bancaria__empresa=empresa)

    if data_inicio:
        qs = qs.filter(data_lancamento__gte=data_inicio)
    if data_fim:
        qs = qs.filter(data_lancamento__lte=data_fim)
    if conta_id:
        qs = qs.filter(conta_bancaria_id=conta_id)

    conciliados = qs.filter(status_conciliacao='CONCILIADO').select_related(
        'conta_bancaria', 'conciliacao'
    ).order_by('-data_lancamento')

    pendentes = qs.filter(status_conciliacao='PENDENTE').select_related(
        'conta_bancaria'
    ).order_by('-data_lancamento')

    ignorados = qs.filter(status_conciliacao='IGNORADO').select_related(
        'conta_bancaria'
    ).order_by('-data_lancamento')

    agg_conc = conciliados.aggregate(
        deb=Sum('valor', filter=Q(tipo='DEBITO')),
        cred=Sum('valor', filter=Q(tipo='CREDITO')),
    )
    agg_pend = pendentes.aggregate(
        deb=Sum('valor', filter=Q(tipo='DEBITO')),
        cred=Sum('valor', filter=Q(tipo='CREDITO')),
    )

    contas = ContaBancaria.objects.filter(empresa=empresa, ativa=True)

    return render(request, 'bancario/relatorio_conciliacao.html', {
        'conciliados': conciliados,
        'pendentes': pendentes,
        'ignorados': ignorados,
        'contas': contas,
        'filtros': {'data_inicio': data_inicio, 'data_fim': data_fim, 'conta_id': conta_id},
        'stats': {
            'qtd_conciliados': conciliados.count(),
            'qtd_pendentes': pendentes.count(),
            'qtd_ignorados': ignorados.count(),
            'debito_conciliado': agg_conc['deb'] or Decimal('0'),
            'credito_conciliado': agg_conc['cred'] or Decimal('0'),
            'debito_pendente': agg_pend['deb'] or Decimal('0'),
            'credito_pendente': agg_pend['cred'] or Decimal('0'),
        },
    })


# ---------------------------------------------------------------------------
# AJAX
# ---------------------------------------------------------------------------

@login_required
def ajax_sugestoes(request, lancamento_pk):
    empresa = request.user.empresa
    lancamento = get_object_or_404(
        ExtratoLancamento,
        pk=lancamento_pk,
        conta_bancaria__empresa=empresa,
    )

    matches = sugerir_matches(lancamento, empresa)
    resultado = []
    for m in matches:
        resultado.append({
            'operacao_id': m['operacao_id'],
            'tipo_operacao': m['tipo_operacao'],
            'descricao': m['descricao'],
            'score': m['score'],
            'score_label': m['score_label'],
            'score_class': m['score_class'],
        })

    return JsonResponse({
        'sugestoes': resultado,
        'lancamento_id': lancamento_pk,
        'lancamento_valor': str(lancamento.valor),
        'lancamento_tipo': lancamento.tipo,
        'lancamento_data': lancamento.data_lancamento.strftime('%d/%m/%Y'),
        'lancamento_descricao': lancamento.descricao,
    })
