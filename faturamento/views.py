import logging
import re

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from core.pagination import paginate
from django.db.models import Count, Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)


def _numero_from_cte_chave(chave: str) -> int | None:
    """Extrai o número do CT-e (9 dígitos) da chave de acesso de 44 dígitos."""
    import re as _re
    digits = _re.sub(r'\D', '', chave or '')
    if len(digits) != 44:
        return None
    try:
        # Posição do número (nCT) na chave: índices 25..33
        return int(digits[25:34])
    except Exception:
        return None


def _nf_log_validation(op, form, formset, pag_formset, dup_formset):
    """Loga erros de validação da NF-e no terminal do servidor (útil para diagnóstico)."""
    parts = []
    if not form.is_valid():
        parts.append(f'NF={form.errors.as_data()}')
    if not formset.is_valid():
        parts.append(f'ITENS={formset.errors}')
    if not pag_formset.is_valid():
        parts.append(f'PAG={pag_formset.errors}')
    if not dup_formset.is_valid():
        parts.append(f'DUP={dup_formset.errors}')
    if parts:
        logger.warning('[NF %s] Validação falhou: %s', op, ' | '.join(str(p) for p in parts))
    else:
        logger.debug('[NF %s] Validação OK — salvando', op)


from .forms import (
    CancelarCTeForm,
    CancelarMDFeForm,
    CartaCorrecaoNFeForm,
    CertificadoDigitalForm,
    CiotMDFeFormSet,
    ConfiguracaoFiscalForm,
    ComponenteValorCTeFormSet,
    CondutorMDFeFormSet,
    ContratanteMDFeFormSet,
    ConhecimentoTransporteForm,
    DevolucaoVendaForm,
    DocumentoVinculadoCTeFormSet,
    DocumentoVinculadoMDFeFormSet,
    DuplicataNFFormSet,
    NFeReferenciadaFormSet,
    EncerrarMDFeForm,
    InstrucaoEmbarqueForm,
    InvoiceExportacaoForm,
    InutilizacaoNFeForm,
    ItemInvoiceFormSet,
    ItemNotaFiscalFormSet,
    ItemPackingListFormSet,
    ManifestoDocumentoFiscalForm,
    MinutaForm,
    NotaFiscalCancelarForm,
    NotaFiscalForm,
    PackingListForm,
    PagamentoFreteMDFeFormSet,
    PagamentoNFFormSet,
    PercursoMDFeFormSet,
    ProdutoPredominanteMDFeForm,
    ReboqueMDFeFormSet,
    SeguroMDFeFormSet,
    ValePedagioMDFeFormSet,
)
from .models import (
    CartaCorrecaoCTe,
    CartaCorrecaoNFe,
    CondutorAdicionalMDFe,
    ConfiguracaoFiscal,
    ConhecimentoTransporte,
    DfeRecebido,
    DocumentoVinculadoCTe,
    DocumentoVinculadoMDFe,
    InstrucaoEmbarque,
    InutilizacaoNFe,
    InvoiceExportacao,
    ItemNotaFiscal,
    ItemPackingList,
    ManifestoDocumentoFiscal,
    Minuta,
    NotaFiscal,
    PackingList,
    PercursoMDFe,
    ProdutoPredominanteMDFe,
)


from .fiscal_storage import upload_xml as _fs_xml, upload_pdf as _fs_pdf


def _registrar_baixa_devolucao(nf):
    """Cria MovimentacaoEstoque de saída para NF-e de devolução de compra (finalidade_nfe='4').

    Chamado após SEFAZ autorizar — usa item_recebimento_origem para obter lote e local de estocagem.
    """
    if nf.finalidade_nfe != '4':
        return
    from estoque.services import criar_movimentacao
    for item_nf in nf.itens.select_related(
        'item_recebimento_origem__lote',
        'item_recebimento_origem__local_estoque',
        'produto',
    ):
        item_rec = item_nf.item_recebimento_origem
        if not item_rec or not item_nf.produto:
            continue
        lote = item_rec.lote
        criar_movimentacao(
            empresa=nf.empresa,
            tipo='SAIDA',
            origem='DEVOLUCAO_FORNECEDOR',
            quantidade=item_nf.quantidade,
            usuario=nf.atualizado_por or nf.criado_por,
            lote=lote,
            produto=item_nf.produto,
            documento=str(nf.numero or ''),
            observacao=f'Devolução NF-e {nf.numero}/{nf.serie} — chave {nf.chave_acesso}',
        )


def _registrar_entrada_devolucao_venda(nf):
    """Cria MovimentacaoEstoque de entrada para NF-e de devolução de venda.

    A NF de devolução de venda é criada por `nota_fiscal_devolucao` (clona a NF de
    saída original com finalidade_nfe='4' e tipo_operacao='DEVOLUCAO'). Diferente de
    `_registrar_baixa_devolucao` (devolução de COMPRA — saída de estoque via
    item_recebimento_origem), aqui a mercadoria volta ao nosso estoque: usa o
    produto (e o lote, quando o item carregar essa rastreabilidade) do próprio item
    clonado da nota original.
    """
    if nf.finalidade_nfe != '4' or nf.tipo_operacao != 'DEVOLUCAO':
        return
    from estoque.services import criar_movimentacao
    for item_nf in nf.itens.select_related('produto', 'lote'):
        if not item_nf.produto:
            continue
        criar_movimentacao(
            empresa=nf.empresa,
            tipo='ENTRADA',
            origem='DEVOLUCAO_VENDA',
            quantidade=item_nf.quantidade,
            usuario=nf.atualizado_por or nf.criado_por,
            lote=item_nf.lote,
            produto=item_nf.produto,
            documento=str(nf.numero or ''),
            observacao=f'Devolução de venda — NF-e {nf.numero}/{nf.serie} — chave {nf.chave_acesso}',
        )


def _processar_autorizacao_agrupamento(nf):
    """Dispara lógica de faturamento agrupado após SEFAZ autorizar a NF-e."""
    from .services.agrupamento import processar_autorizacao_remessa, processar_autorizacao_faturamento
    try:
        if nf.tipo_operacao == 'REMESSA':
            processar_autorizacao_remessa(nf)
        elif nf.tipo_operacao == 'FATURAMENTO':
            processar_autorizacao_faturamento(nf)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).error(
            'Erro ao processar agrupamento pós-autorização NF %s: %s', nf.pk, exc
        )


def _sync_pedido_de_documento(nf=None, invoice=None):
    """Sincroniza o status do PedidoVenda vinculado após NF-e/Invoice mudar de status.

    A FK é de PedidoVenda para o documento (não o inverso), então é preciso buscar
    o pedido pelo documento antes de sincronizar.
    """
    from vendas.models import PedidoVenda
    from vendas.services import sincronizar_status_pedido
    pedido = None
    if nf is not None:
        pedido = PedidoVenda.objects.filter(nota_fiscal=nf).first()
    elif invoice is not None:
        pedido = PedidoVenda.objects.filter(invoice=invoice).first()
    if pedido:
        sincronizar_status_pedido(pedido)


def _validar_itens_complementar(nf_cleaned_data, formset):
    """Garante a regra de negócio da NF-e Complementar (finalidade_nfe='2'):

    - Complemento de VALOR: mercadoria já saiu na nota original — todos os
      itens devem ter quantidade 0 (senão duplicaria o estoque fiscal).
    - Complemento de QUANTIDADE (típico de exportação): valor já foi acertado
      comercialmente — todos os itens devem ter valor unitário 0 (senão
      duplicaria a cobrança/faturamento).

    Retorna uma mensagem de erro (str) se a regra for violada, ou None se OK.
    """
    from decimal import Decimal

    if nf_cleaned_data.get('tipo_operacao') != 'COMPLEMENTAR':
        return None
    tipo_complemento = nf_cleaned_data.get('tipo_complemento')
    if not tipo_complemento:
        return None  # já reportado pelo NotaFiscalForm.clean()

    zero = Decimal('0')
    for item_data in formset.cleaned_data:
        if not item_data or item_data.get('DELETE'):
            continue
        quantidade = item_data.get('quantidade') or zero
        valor_unitario = item_data.get('valor_unitario') or zero
        if tipo_complemento == 'VALOR' and quantidade != zero:
            return (
                'Nota Complementar de Valor: a quantidade de todos os itens deve ser 0 '
                '(a mercadoria já saiu na nota original — aqui complementa-se apenas o valor).'
            )
        if tipo_complemento == 'QUANTIDADE' and valor_unitario != zero:
            return (
                'Nota Complementar de Quantidade: o valor unitário de todos os itens deve ser 0 '
                '(o valor já foi acertado comercialmente — aqui regulariza-se apenas o estoque físico).'
            )
    return None


def _get_empresa(request):
    return request.user.empresa


def _upload_fiscal_docs(obj, empresa_id, tipo, numero, serie, xml_b64=None, pdf_b64=None, cancel=False):
    """Faz upload de XML/PDF para Supabase Storage e atualiza os campos do objeto.

    Limpa o campo base64 somente se o upload foi bem-sucedido (URL retornada).
    Retorna lista de campos adicionados para incluir em update_fields.
    """
    extra_fields = []
    if xml_b64:
        prefix = 'CANCEL_' if cancel else 'XML_'
        fname = f'{prefix}{tipo.upper()}_{numero}_{serie}.xml'
        url = _fs_xml(xml_b64, empresa_id, tipo, fname)
        if url:
            if cancel:
                obj.xml_cancelamento_url = url
                obj.xml_cancelamento = ''
                extra_fields += ['xml_cancelamento_url', 'xml_cancelamento']
            else:
                obj.xml_autorizacao_url = url
                obj.xml_autorizacao = ''
                extra_fields += ['xml_autorizacao_url', 'xml_autorizacao']
    if pdf_b64:
        pdf_field = 'pdf_danfe' if tipo == 'nfe' else ('pdf_dacte' if tipo == 'cte' else 'pdf_damdfe')
        fname = f'PDF_{tipo.upper()}_{numero}_{serie}.pdf'
        url = _fs_pdf(pdf_b64, empresa_id, tipo, fname)
        if url:
            setattr(obj, f'{pdf_field}_url', url)
            setattr(obj, pdf_field, '')
            extra_fields += [f'{pdf_field}_url', pdf_field]
    return extra_fields


# ─────────────────────────── Dashboard ───────────────────────────

@login_required
def faturamento_dashboard(request):
    empresa = _get_empresa(request)
    if not empresa:
        messages.error(request, 'Empresa não encontrada.')
        return redirect('dashboard:index')

    hoje = timezone.now().date()
    inicio_mes = hoje.replace(day=1)

    nf_stats = NotaFiscal.objects.filter(empresa=empresa).aggregate(
        total=Count('id'),
        emitidas=Count('id', filter=Q(status='EMITIDA')),
        canceladas=Count('id', filter=Q(status='CANCELADA')),
        valor_mes=Sum('valor_total', filter=Q(status='EMITIDA', data_emissao__gte=inicio_mes)),
    )

    invoice_stats = InvoiceExportacao.objects.filter(empresa=empresa).aggregate(
        total=Count('id'),
        emitidas=Count('id', filter=Q(status='EMITIDA')),
        valor_fob=Sum('valor_mercadoria', filter=Q(status='EMITIDA')),
    )

    pl_stats = PackingList.objects.filter(empresa=empresa).aggregate(
        total=Count('id'),
        emitidos=Count('id', filter=Q(status='EMITIDO')),
    )

    ultimas_nf = NotaFiscal.objects.filter(empresa=empresa).select_related('cliente').order_by('-criado_em')[:5]
    ultimas_invoice = InvoiceExportacao.objects.filter(empresa=empresa).select_related('cliente', 'booking').order_by('-criado_em')[:5]

    return render(request, 'faturamento/dashboard.html', {
        'nf_stats': nf_stats,
        'invoice_stats': invoice_stats,
        'pl_stats': pl_stats,
        'ultimas_nf': ultimas_nf,
        'ultimas_invoice': ultimas_invoice,
    })


# ─────────────────────────── Nota Fiscal ───────────────────────────

def _auto_fill_transp(nf):
    """Copia dados da transportadora FK para os campos transp_* quando estão em branco."""
    if nf.transportadora and not (nf.transp_nome or '').strip():
        t = nf.transportadora
        nf.transp_nome = t.razao_social or ''
        nf.transp_cnpj = t.cnpj or ''
        nf.transp_ie = t.inscricao_estadual or ''
        nf.transp_endereco = ', '.join(p for p in [t.logradouro, t.numero, t.complemento] if p).strip()
        nf.transp_municipio = t.cidade or ''
        nf.transp_uf = t.uf or ''
        nf.transp_rntc = t.rntc or ''
        nf.save(update_fields=[
            'transp_nome', 'transp_cnpj', 'transp_ie',
            'transp_endereco', 'transp_municipio', 'transp_uf', 'transp_rntc',
        ])


@login_required
def nota_fiscal_list(request):
    empresa = _get_empresa(request)
    if not empresa:
        return redirect('dashboard:index')

    qs = NotaFiscal.objects.filter(empresa=empresa).select_related('cliente', 'transportadora')

    status_filter = request.GET.get('status', '')
    q = request.GET.get('q', '')
    data_ini = request.GET.get('data_ini', '')
    data_fim = request.GET.get('data_fim', '')

    if status_filter:
        qs = qs.filter(status=status_filter)
    if q:
        qs = qs.filter(Q(cliente__razao_social__icontains=q) | Q(numero__icontains=q))
    if data_ini:
        qs = qs.filter(data_emissao__gte=data_ini)
    if data_fim:
        qs = qs.filter(data_emissao__lte=data_fim)

    qs = qs.order_by('-data_emissao', '-numero')
    page_obj, per_page, per_page_options = paginate(request, qs)

    return render(request, 'faturamento/nota_fiscal/list.html', {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'q': q,
        'data_ini': data_ini,
        'data_fim': data_fim,
        'status_choices': NotaFiscal.STATUS,
        'per_page': per_page,
        'per_page_options': per_page_options,
    })


@login_required
def nota_fiscal_create(request):
    empresa = _get_empresa(request)
    if not empresa:
        return redirect('dashboard:index')

    if request.method == 'POST':
        form = NotaFiscalForm(request.POST, empresa=empresa)
        formset = ItemNotaFiscalFormSet(request.POST, prefix='itens',
                                        form_kwargs={'empresa': empresa})
        pag_formset = PagamentoNFFormSet(request.POST, prefix='pagamentos')
        dup_formset = DuplicataNFFormSet(request.POST, prefix='duplicatas')
        ref_formset = NFeReferenciadaFormSet(request.POST, prefix='referencias')
        _nf_log_validation('CREATE', form, formset, pag_formset, dup_formset)
        erro_complemento = None
        if form.is_valid() and formset.is_valid() and pag_formset.is_valid() and dup_formset.is_valid() and ref_formset.is_valid():
            erro_complemento = _validar_itens_complementar(form.cleaned_data, formset)
            if erro_complemento:
                form.add_error(None, erro_complemento)
        if form.is_valid() and formset.is_valid() and pag_formset.is_valid() and dup_formset.is_valid() and ref_formset.is_valid() and not erro_complemento:
            nf = form.save(user=request.user)
            if not nf.numero:
                ultimo = NotaFiscal.objects.filter(empresa=empresa).exclude(numero__isnull=True).order_by('-numero').first()
                if ultimo:
                    nf.numero = ultimo.numero + 1
                else:
                    cfg = ConfiguracaoFiscal.objects.filter(empresa=empresa).first()
                    nf.numero = cfg.numero_nfe_inicial if cfg else 1
            formset.instance = nf
            items = formset.save(commit=False)
            for idx, item in enumerate(items, start=1):
                item.numero_item = idx
                item.save()
            for obj in formset.deleted_objects:
                obj.delete()
            pag_formset.instance = nf
            pag_formset.save()
            dup_formset.instance = nf
            dup_formset.save()
            ref_formset.instance = nf
            ref_formset.save()
            # Preenche campos tributáveis (conversão CX→KG) ao salvar
            from decimal import Decimal as _Dec, ROUND_HALF_UP
            _ft = ['quantidade_tributavel', 'unidade_tributavel', 'valor_unitario_tributavel']
            for _item in nf.itens.select_related('produto__unidade_medida', 'produto__unidade_venda').all():
                _prod = _item.produto
                if not _prod:
                    continue
                _fator   = float(_prod.fator_conversao or 1)
                _un_med  = (_prod.unidade_medida.sigla if _prod.unidade_medida_id else '').strip()
                _un_vnd  = (_prod.unidade_venda.sigla  if _prod.unidade_venda_id  else '').strip()
                if _fator > 1 and _un_med and _un_med != _un_vnd and not float(_item.quantidade_tributavel or 0):
                    _item.quantidade_tributavel     = (_item.quantidade * _Dec(str(_fator))).quantize(_Dec('0.0001'), rounding=ROUND_HALF_UP)
                    _item.unidade_tributavel        = _un_med
                    _item.valor_unitario_tributavel = (_item.valor_unitario / _Dec(str(_fator))).quantize(_Dec('0.0001'), rounding=ROUND_HALF_UP)
                    _item.save(update_fields=_ft)
            # Auto-calcula volumes a partir dos itens se campos não foram preenchidos manualmente
            _itens_db = list(nf.itens.select_related('produto').all())
            if not nf.quantidade_volumes:
                _qtd_vol = sum(int(_i.quantidade) for _i in _itens_db if _i.quantidade)
                if _qtd_vol:
                    NotaFiscal.objects.filter(pk=nf.pk).update(quantidade_volumes=_qtd_vol)
            if not nf.peso_bruto_kg:
                _pb = sum(
                    (_i.produto.peso_bruto_unitario or _Dec(0)) * _i.quantidade
                    for _i in _itens_db if _i.produto and _i.produto.peso_bruto_unitario
                )
                if _pb:
                    NotaFiscal.objects.filter(pk=nf.pk).update(peso_bruto_kg=_pb)
            if not nf.peso_liquido_kg:
                _pl = sum(
                    (_i.produto.peso_liquido_unitario or _Dec(0)) * _i.quantidade
                    for _i in _itens_db if _i.produto and _i.produto.peso_liquido_unitario
                )
                if _pl:
                    NotaFiscal.objects.filter(pk=nf.pk).update(peso_liquido_kg=_pl)
            nf.calcular_totais()
            _auto_fill_transp(nf)
            messages.success(request, f'NF {nf.numero}/{nf.serie} criada com sucesso.')
            return redirect('faturamento:nota_fiscal_detail', pk=nf.pk)
    else:
        config = ConfiguracaoFiscal.objects.filter(empresa=empresa).first()
        initial = {}
        if config:
            initial['natureza_operacao'] = config.natureza_operacao_padrao
            initial['informacoes_complementares'] = config.observacoes_padrao_nfe
        form = NotaFiscalForm(empresa=empresa, initial=initial)
        formset = ItemNotaFiscalFormSet(prefix='itens',
                                        form_kwargs={'empresa': empresa})
        pag_formset = PagamentoNFFormSet(prefix='pagamentos')
        dup_formset = DuplicataNFFormSet(prefix='duplicatas')
        ref_formset = NFeReferenciadaFormSet(prefix='referencias')

    return render(request, 'faturamento/nota_fiscal/form.html', {
        'form': form,
        'formset': formset,
        'pag_formset': pag_formset,
        'dup_formset': dup_formset,
        'ref_formset': ref_formset,
        'title': 'Nova Nota Fiscal',
    })


@login_required
def nota_fiscal_danfe_preview(request, pk):
    from decimal import Decimal as _Dec, ROUND_HALF_UP
    empresa = _get_empresa(request)
    nf = get_object_or_404(
        NotaFiscal.objects.select_related('transportadora'),
        pk=pk, empresa=empresa,
    )
    cli = nf.cliente
    endereco_cli = cli.enderecos.order_by('-padrao').first() if cli else None

    # Transportadora: injeta em memória se transp_nome vazio mas FK setado
    if nf.transportadora and not (nf.transp_nome or '').strip():
        t = nf.transportadora
        nf.transp_nome = t.razao_social or ''
        nf.transp_cnpj = t.cnpj or ''
        nf.transp_ie = t.inscricao_estadual or ''
        nf.transp_endereco = ', '.join(p for p in [t.logradouro, t.numero, t.complemento] if p).strip()
        nf.transp_municipio = t.cidade or ''
        nf.transp_uf = t.uf or ''
        nf.transp_rntc = t.rntc or ''

    # Conversão de unidade: calcula em memória para itens sem qty_tributavel
    itens = list(
        nf.itens.select_related('produto__unidade_medida', 'produto__unidade_venda')
        .order_by('numero_item')
    )
    for _item in itens:
        if float(_item.quantidade_tributavel or 0) == 0 and _item.produto:
            _prod = _item.produto
            _fator = float(_prod.fator_conversao or 1)
            _un_med = (_prod.unidade_medida.sigla if _prod.unidade_medida_id else '').strip()
            _un_vnd = (_prod.unidade_venda.sigla if _prod.unidade_venda_id else '').strip()
            if _fator > 1 and _un_med and _un_med != _un_vnd:
                _item.quantidade_tributavel = (_item.quantidade * _Dec(str(_fator))).quantize(_Dec('0.0001'), rounding=ROUND_HALF_UP)
                _item.unidade_tributavel = _un_med
                _item.valor_unitario_tributavel = (_item.valor_unitario / _Dec(str(_fator))).quantize(_Dec('0.0001'), rounding=ROUND_HALF_UP)

    # Generate Code128 barcode SVG for chave de acesso
    barcode_svg = ''
    if nf.chave_acesso:
        try:
            import io as _io
            import re as _re
            from barcode import Code128
            from barcode.writer import SVGWriter
            _buf = _io.BytesIO()
            Code128(nf.chave_acesso, writer=SVGWriter()).write(_buf, options={
                'write_text': False,
                'module_height': 16.0,
                'quiet_zone': 2.0,
                'font_size': 0,
                'text_distance': 0,
                'module_width': 0.29,
            })
            _svg = _buf.getvalue().decode('utf-8')
            _svg = _re.sub(r'<[?]xml[^?]*[?]>', '', _svg)
            _svg = _re.sub(r'<!DOCTYPE[^>]*>', '', _svg)
            _wm = _re.search(r'width="([\d.]+)mm"', _svg)
            _hm = _re.search(r'height="([\d.]+)mm"', _svg)
            if _wm and _hm:
                _w, _h = _wm.group(1), _hm.group(1)
                _svg = _svg.replace(
                    'width="' + _w + 'mm" height="' + _h + 'mm"',
                    'viewBox="0 0 ' + _w + ' ' + _h + '" preserveAspectRatio="none" style="width:100%;height:17mm;display:block"',
                )
            barcode_svg = _svg.strip()
        except Exception:
            pass

    return render(request, 'faturamento/nota_fiscal/danfe_preview.html', {
        'nf': nf,
        'empresa': empresa,
        'cli': cli,
        'endereco_cli': endereco_cli,
        'itens': itens,
        'duplicatas': nf.duplicatas.order_by('vencimento'),
        'barcode_svg': barcode_svg,
    })


@login_required
def nota_fiscal_detail(request, pk):
    from drawback import services as drawback_services

    empresa = _get_empresa(request)
    nf = get_object_or_404(NotaFiscal, pk=pk, empresa=empresa)

    sugestoes_drawback = {}
    if nf.status == 'EMITIDA':
        for item in nf.itens.all():
            if not item.produto_id or not (item.cfop or '').startswith('7'):
                continue
            if hasattr(item, 'drawback_saida'):
                continue
            sugestao = drawback_services.sugerir_vinculo_saida(item, empresa)
            if sugestao:
                sugestoes_drawback[item.pk] = sugestao

    return render(request, 'faturamento/nota_fiscal/detail.html', {
        'nf': nf,
        'sugestoes_drawback': sugestoes_drawback,
    })


@login_required
def nota_fiscal_update(request, pk):
    empresa = _get_empresa(request)
    nf = get_object_or_404(NotaFiscal, pk=pk, empresa=empresa)

    if nf.status != 'RASCUNHO':
        messages.error(request, 'Apenas NF-e em RASCUNHO podem ser editadas.')
        return redirect('faturamento:nota_fiscal_detail', pk=pk)

    if nf.chave_acesso:
        messages.warning(request,
            'Esta NF-e foi enviada à SEFAZ e está aguardando resposta. '
            'Use "Verificar na SEFAZ" para obter o resultado antes de editar.')
        return redirect('faturamento:nota_fiscal_detail', pk=pk)

    if request.method == 'POST':
        form = NotaFiscalForm(request.POST, instance=nf, empresa=empresa)
        formset = ItemNotaFiscalFormSet(request.POST, instance=nf, prefix='itens',
                                        form_kwargs={'empresa': empresa})
        pag_formset = PagamentoNFFormSet(request.POST, instance=nf, prefix='pagamentos')
        dup_formset = DuplicataNFFormSet(request.POST, instance=nf, prefix='duplicatas')
        ref_formset = NFeReferenciadaFormSet(request.POST, instance=nf, prefix='referencias')
        _nf_log_validation('UPDATE', form, formset, pag_formset, dup_formset)
        erro_complemento = None
        if form.is_valid() and formset.is_valid() and pag_formset.is_valid() and dup_formset.is_valid() and ref_formset.is_valid():
            erro_complemento = _validar_itens_complementar(form.cleaned_data, formset)
            if erro_complemento:
                form.add_error(None, erro_complemento)
        if form.is_valid() and formset.is_valid() and pag_formset.is_valid() and dup_formset.is_valid() and ref_formset.is_valid() and not erro_complemento:
            form.save(user=request.user)
            # Atribuir numero_item sequencial antes de salvar para evitar conflito
            # de unique_together quando o JS submete valores incorretos.
            _n = 1
            for _f in formset.forms:
                if formset.can_delete and formset._should_delete_form(_f):
                    continue
                _f.instance.numero_item = _n
                _n += 1
            formset.save()
            # Renumerar todos os itens em dois passos para corrigir itens não alterados
            # que possam ter ficado com numero_item errado após adição/remoção.
            _INF = nf.itens.model
            _all_it = list(nf.itens.order_by('pk'))
            if _all_it:
                _off = max(i.numero_item for i in _all_it) + len(_all_it) + 1
                for _i2, _it2 in enumerate(_all_it):
                    _it2.numero_item = _off + _i2
                _INF.objects.bulk_update(_all_it, ['numero_item'])
                for _i2, _it2 in enumerate(_all_it, start=1):
                    _it2.numero_item = _i2
                _INF.objects.bulk_update(_all_it, ['numero_item'])
            pag_formset.save()
            dup_formset.save()
            ref_formset.save()
            # Se todas as referências foram removidas, limpa também o campo legado
            # de chave singular — senão a migração automática (linha ~628) a recria
            # sozinha na próxima vez que a página de edição for aberta.
            if nf.chave_nfe_referenciada and not nf.nfes_referenciadas.exists():
                NotaFiscal.objects.filter(pk=nf.pk).update(chave_nfe_referenciada='')
                nf.chave_nfe_referenciada = ''
            # Preenche campos tributáveis (conversão CX→KG) ao salvar
            from decimal import Decimal as _Dec, ROUND_HALF_UP
            _ft = ['quantidade_tributavel', 'unidade_tributavel', 'valor_unitario_tributavel']
            for _item in nf.itens.select_related('produto__unidade_medida', 'produto__unidade_venda').all():
                _prod = _item.produto
                if not _prod:
                    continue
                _fator  = float(_prod.fator_conversao or 1)
                _un_med = (_prod.unidade_medida.sigla if _prod.unidade_medida_id else '').strip()
                _un_vnd = (_prod.unidade_venda.sigla  if _prod.unidade_venda_id  else '').strip()
                if _fator > 1 and _un_med and _un_med != _un_vnd and not float(_item.quantidade_tributavel or 0):
                    _item.quantidade_tributavel     = (_item.quantidade * _Dec(str(_fator))).quantize(_Dec('0.0001'), rounding=ROUND_HALF_UP)
                    _item.unidade_tributavel        = _un_med
                    _item.valor_unitario_tributavel = (_item.valor_unitario / _Dec(str(_fator))).quantize(_Dec('0.0001'), rounding=ROUND_HALF_UP)
                    _item.save(update_fields=_ft)
            # Auto-calcula volumes a partir dos itens se campos não foram preenchidos manualmente
            _itens_db = list(nf.itens.select_related('produto').all())
            if not nf.quantidade_volumes:
                _qtd_vol = sum(int(_i.quantidade) for _i in _itens_db if _i.quantidade)
                if _qtd_vol:
                    NotaFiscal.objects.filter(pk=nf.pk).update(quantidade_volumes=_qtd_vol)
            if not nf.peso_bruto_kg:
                _pb = sum(
                    (_i.produto.peso_bruto_unitario or _Dec(0)) * _i.quantidade
                    for _i in _itens_db if _i.produto and _i.produto.peso_bruto_unitario
                )
                if _pb:
                    NotaFiscal.objects.filter(pk=nf.pk).update(peso_bruto_kg=_pb)
            if not nf.peso_liquido_kg:
                _pl = sum(
                    (_i.produto.peso_liquido_unitario or _Dec(0)) * _i.quantidade
                    for _i in _itens_db if _i.produto and _i.produto.peso_liquido_unitario
                )
                if _pl:
                    NotaFiscal.objects.filter(pk=nf.pk).update(peso_liquido_kg=_pl)
            nf.calcular_totais()
            _auto_fill_transp(nf)
            messages.success(request, 'NF-e atualizada com sucesso.')
            return redirect('faturamento:nota_fiscal_detail', pk=pk)
    else:
        form = NotaFiscalForm(instance=nf, empresa=empresa)
        formset = ItemNotaFiscalFormSet(instance=nf, prefix='itens',
                                        form_kwargs={'empresa': empresa})
        pag_formset = PagamentoNFFormSet(instance=nf, prefix='pagamentos')
        dup_formset = DuplicataNFFormSet(instance=nf, prefix='duplicatas')
        # Se a NF tem chave singular (devolução simples) mas ainda sem registro
        # NFeReferenciada, migra automaticamente para a tabela many-to-many.
        chave_singular = (nf.chave_nfe_referenciada or '').strip()
        if chave_singular and len(chave_singular) == 44 and not nf.nfes_referenciadas.exists():
            from .models import NFeReferenciada
            NFeReferenciada.objects.create(
                nota_fiscal=nf,
                chave_acesso_referenciada=chave_singular,
            )
        ref_formset = NFeReferenciadaFormSet(instance=nf, prefix='referencias')

    return render(request, 'faturamento/nota_fiscal/form.html', {
        'form': form,
        'formset': formset,
        'pag_formset': pag_formset,
        'dup_formset': dup_formset,
        'ref_formset': ref_formset,
        'nf': nf,
        'title': f'Editar NF {nf.numero}/{nf.serie}',
    })


@login_required
def nota_fiscal_debug_payload(request, pk):
    """Debug: retorna o payload JSON que seria enviado ao IntegraNotas (apenas superuser)."""
    import json as _json
    from .services.integranotas import IntegranNotasClient

    if not request.user.is_superuser:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('Apenas superuser pode acessar este recurso.')

    empresa = _get_empresa(request)
    nf = get_object_or_404(NotaFiscal, pk=pk, empresa=empresa)
    from django.conf import settings as _s
    client = IntegranNotasClient(
        getattr(_s, 'INTEGRANOTAS_TOKEN', ''),
        str(getattr(_s, 'INTEGRANOTAS_CNPJ', '') or (nf.empresa.cnpj or ''))
    )
    try:
        payload = client._build_payload(nf)
    except Exception as e:
        payload = {'erro': str(e)}

    return JsonResponse(payload, json_dumps_params={'ensure_ascii': False, 'indent': 2})


@login_required
@require_POST
def nota_fiscal_emitir_ajax(request, pk):
    """AJAX: valida, emite e retorna progresso passo a passo em JSON."""
    import re as _re
    from .services.integranotas import IntegranNotasClient, IntegranNotasError

    empresa = _get_empresa(request)
    nf = get_object_or_404(NotaFiscal, pk=pk, empresa=empresa)
    steps = []

    def ok(label, msg=None):
        steps.append({'status': 'ok', 'label': label, 'message': msg or ''})

    def erro(label, msg, fix_url=None, fix_label=None, errors=None):
        steps.append({'status': 'error', 'label': label, 'message': msg,
                      'fix_url': fix_url, 'fix_label': fix_label, 'errors': errors or []})
        return JsonResponse({'steps': steps, 'success': False})

    # ── 1. Status ────────────────────────────────────────────────────
    if nf.status != 'RASCUNHO':
        return erro('Status da NF-e',
                    f'NF-e já está como "{nf.status}" e não pode ser emitida.')
    if nf.chave_acesso:
        return erro('Status da NF-e',
                    'NF-e já foi enviada à SEFAZ e está aguardando resposta. '
                    'Use "Verificar na SEFAZ" para obter o resultado antes de reemitir.')

    # ── 2. Configuração / Token ───────────────────────────────────────
    config = ConfiguracaoFiscal.objects.filter(empresa=empresa).first()
    cfg_url = reverse('faturamento:configuracao')
    if not config:
        return erro('Token IntegraNOtas', 'Configuração fiscal não encontrada.',
                    fix_url=cfg_url, fix_label='Configurar')
    raw_token = config.get_token()
    if not raw_token:
        return erro('Token IntegraNOtas',
                    'Token não configurado ou não foi possível decriptografar. '
                    'Verifique se FIELD_ENCRYPTION_KEY está correta no servidor.',
                    fix_url=cfg_url, fix_label='Configurar token')
    ambiente_label = 'Produção' if config.ambiente_nfe == '1' else 'Homologação'
    api_url = IntegranNotasClient.PROD_URL if config.ambiente_nfe == '1' else IntegranNotasClient.HOM_URL
    token_prefix = raw_token[:12] + '...' if len(raw_token) > 12 else '(token curto)'
    ok('Token IntegraNOtas',
       f'Ambiente: {ambiente_label} · URL: {api_url} · Token: {token_prefix}')

    # ── 3. Dados do emitente ──────────────────────────────────────────
    cnpj_digits = _re.sub(r'\D', '', empresa.cnpj or '')
    emitente_erros = []
    if len(cnpj_digits) != 14:
        emitente_erros.append('CNPJ inválido ou não informado')
    if not (empresa.nome or '').strip():
        emitente_erros.append('Razão Social não informada')
    ie_emitente = (empresa.inscricao_estadual or '').strip()
    if not ie_emitente:
        emitente_erros.append(
            'Inscrição Estadual (IE) não informada — '
            'preencha a IE ou "ISENTO" se for não contribuinte'
        )
    if emitente_erros:
        return erro('Dados do emitente', ' | '.join(emitente_erros),
                    fix_url=cfg_url, fix_label='Corrigir dados do emitente')
    ok('Dados do emitente', f'{empresa.nome}  ·  CNPJ {empresa.cnpj}  ·  IE {ie_emitente}')

    # ── 4. Dados do destinatário ──────────────────────────────────────
    cli = nf.cliente
    forn = nf.fornecedor
    if not cli and not forn:
        return erro('Dados do destinatário',
                    'Nenhum destinatário informado. Preencha o campo Cliente ou Fornecedor.',
                    fix_url=reverse('faturamento:nota_fiscal_update', args=[pk]),
                    fix_label='Editar NF-e')
    dest_erros = []
    if forn and not cli:
        # NF-e de devolução de compra: destinatário é o fornecedor
        doc_dest = _re.sub(r'\D', '', forn.cnpj_cpf or '')
        dest_nome = forn.nome
        fix_url = reverse('cadastros:fornecedor_detail', args=[forn.pk])
        fix_label = 'Corrigir cadastro do fornecedor'
        if not doc_dest:
            dest_erros.append('CNPJ/CPF não informado')
        elif len(doc_dest) not in (11, 14):
            dest_erros.append(f'CNPJ/CPF inválido ({len(doc_dest)} dígitos — esperado 11 ou 14)')
        if not dest_nome.strip():
            dest_erros.append('Nome não informado')
        end_forn = forn.enderecos.filter(padrao=True).first()
        cidade = (end_forn.cidade if end_forn else forn.cidade) or ''
        uf = (end_forn.uf if end_forn else forn.uf) or ''
        cep = (end_forn.cep if end_forn else forn.cep) or ''
        logradouro = (end_forn.logradouro if end_forn else forn.endereco) or ''
        codigo_mun = (end_forn.codigo_municipio if end_forn else '') or ''
        end_faltam = []
        if not logradouro.strip(): end_faltam.append('Logradouro')
        if not cidade.strip():     end_faltam.append('Cidade')
        if not uf.strip():         end_faltam.append('UF')
        if not cep.strip():        end_faltam.append('CEP')
        if not codigo_mun.strip(): end_faltam.append('Código IBGE')
        if end_faltam:
            dest_erros.append(f'Endereço incompleto: faltam {", ".join(end_faltam)}')
    else:
        doc_dest = _re.sub(r'\D', '', cli.cnpj_cpf or '')
        dest_nome = cli.razao_social or ''
        fix_url = reverse('cadastros:cliente_update', args=[cli.pk])
        fix_label = 'Corrigir cadastro do cliente'
        if not doc_dest:
            dest_erros.append('CNPJ/CPF não informado')
        elif len(doc_dest) not in (11, 14):
            dest_erros.append(f'CNPJ/CPF inválido ({len(doc_dest)} dígitos — esperado 11 ou 14)')
        if not dest_nome.strip():
            dest_erros.append('Razão Social não informada')
        pais_cli = (cli.pais or '').strip().lower()
        is_exterior = pais_cli not in ('brasil', 'brazil', '')
        end_cli = cli.enderecos.order_by('-padrao').first()
        if not is_exterior:
            if not end_cli:
                dest_erros.append('Endereço não cadastrado')
            else:
                end_faltam = []
                if not (end_cli.logradouro or '').strip(): end_faltam.append('Logradouro')
                if not (end_cli.cidade or '').strip():     end_faltam.append('Cidade')
                if not (end_cli.uf or '').strip():         end_faltam.append('UF')
                if not (end_cli.cep or '').strip():        end_faltam.append('CEP')
                if end_faltam:
                    dest_erros.append(f'Endereço incompleto: faltam {", ".join(end_faltam)}')
    if dest_erros:
        return erro('Dados do destinatário',
                    f'{dest_nome or "?"}: {"; ".join(dest_erros)}',
                    fix_url=fix_url, fix_label=fix_label,
                    errors=dest_erros)
    ok('Dados do destinatário', f'{dest_nome}  ·  {doc_dest}')

    # ── 5. Itens e dados fiscais ──────────────────────────────────────
    itens = list(nf.itens.all())
    if not itens:
        edit_url = reverse('faturamento:nota_fiscal_update', args=[pk])
        return erro('Itens da NF-e', 'Nenhum item cadastrado.',
                    fix_url=edit_url, fix_label='Adicionar itens')

    edit_url = reverse('faturamento:nota_fiscal_update', args=[pk])
    item_erros = []
    for item in itens:
        faltam = []
        desc = (item.descricao or '')[:35]
        # NCM: 8 dígitos exatos
        ncm_digits = _re.sub(r'\D', '', item.ncm or '')
        if not ncm_digits:
            faltam.append('NCM ausente')
        elif len(ncm_digits) != 8:
            faltam.append(f'NCM "{ncm_digits}" inválido (deve ter 8 dígitos)')
        # CFOP: 4 dígitos
        cfop_digits = _re.sub(r'\D', '', item.cfop or '')
        if not cfop_digits:
            faltam.append('CFOP ausente')
        elif len(cfop_digits) != 4:
            faltam.append(f'CFOP "{cfop_digits}" inválido (deve ter 4 dígitos)')
        # CST obrigatórios
        if not item.cst_icms:  faltam.append('CST ICMS')
        if not item.cst_pis:   faltam.append('CST PIS')
        if not item.cst_cofins: faltam.append('CST COFINS')
        # Quantidade e valor
        if (item.quantidade or 0) <= 0:
            faltam.append('Quantidade deve ser maior que zero')
        if (item.valor_unitario or 0) <= 0:
            faltam.append('Valor Unitário deve ser maior que zero')
        # DI obrigatória para CFOP 3xxx — valida campos críticos
        if cfop_digits.startswith('3') and (item.di_numero or '').strip():
            di_num_digits = _re.sub(r'\D', '', item.di_numero or '')
            if len(di_num_digits) > 10:
                faltam.append(
                    f'Nº DI "{item.di_numero}" tem {len(di_num_digits)} dígitos '
                    f'(máx 10 — SEFAZ). Use "0000000000" para drawback sem DI real.'
                )
            di_campos = {
                'Data registro DI': item.di_data_registro,
                'Local do desembaraço': item.di_local_desembaraco,
                'UF desembaraço': item.di_uf_desembaraco,
                'Data desembaraço': item.di_data_desembaraco,
                'Via de transporte': item.di_via_transporte,
                'Código do exportador': item.di_codigo_exportador,
                'Cód. fabricante DI': item.di_codigo_fabricante,
            }
            di_faltam = [k for k, v in di_campos.items() if not v]
            if di_faltam:
                faltam.append(f'DI incompleta — preencha: {", ".join(di_faltam)}')
            dw = _re.sub(r'\D', '', item.di_numero_drawback or '')
            if dw and len(dw) != 11:
                faltam.append(f'Nº Drawback "{item.di_numero_drawback}" deve ter exatamente 11 dígitos (tem {len(dw)})')
        elif cfop_digits.startswith('3') and not (item.di_numero or '').strip():
            faltam.append('CFOP 3xxx exige Declaração de Importação (aba DI no item)')
        # IPI: fora do escopo desta fazenda (commodities agrícolas não são
        # produtos industrializados). CST 53/55 (únicos no escopo) são sempre
        # não-tributada/suspensão — nunca com alíquota.
        aliq_ipi = item.aliquota_ipi or 0
        if aliq_ipi > 0:
            cst_ipi = (item.cst_ipi or '').strip()
            faltam.append(
                f'IPI: CST "{cst_ipi}" não deveria ter alíquota preenchida '
                f'({aliq_ipi}%) — CST 53/55 são sempre não-tributada/suspensão (0%)'
            )
        # IBS/CBS — Reforma Tributária: CST + cClassTrib devem formar um par válido
        cst_reforma = (item.ibs_cbs_situacao_tributaria or '').strip()
        cclasstrib = (item.ibs_cbs_classificacao_tributaria or '').strip()
        if cst_reforma:
            codigos_validos = {c for c, _ in ItemNotaFiscal.IBS_CBS_CST_CCLASSTRIB_MAP.get(cst_reforma, [])}
            if not cclasstrib:
                faltam.append('cClassTrib obrigatório quando CST IBS/CBS informado')
            elif cclasstrib not in codigos_validos:
                faltam.append(f'cClassTrib "{cclasstrib}" inválido para CST IBS/CBS {cst_reforma}')
            # Campos obrigatórios por CST IBS/CBS (redução/diferimento são
            # independentes para IBS e CBS — exige os dois lados preenchidos)
            if cst_reforma == '200' and (
                (item.ibs_percentual_reducao or 0) <= 0
                or (item.cbs_percentual_reducao or 0) <= 0
            ):
                faltam.append('CST IBS/CBS 200 exige "% Redução IBS" e "% Redução CBS" preenchidos')
            if cst_reforma == '515' and (
                (item.ibs_percentual_diferimento or 0) <= 0
                or (item.ibs_percentual_reducao or 0) <= 0
                or (item.cbs_percentual_diferimento or 0) <= 0
                or (item.cbs_percentual_reducao or 0) <= 0
            ):
                faltam.append(
                    'CST IBS/CBS 515 exige "% Diferimento" e "% Redução" preenchidos '
                    'tanto para IBS quanto para CBS'
                )
        elif cclasstrib:
            faltam.append('cClassTrib informado sem CST IBS/CBS')
        if faltam:
            item_erros.append(f'Item {item.numero_item} — {desc}: {"; ".join(faltam)}')

    if item_erros:
        return erro('Dados fiscais dos itens',
                    f'{len(item_erros)} item(ns) com problemas fiscais.',
                    fix_url=edit_url, fix_label='Corrigir itens', errors=item_erros)
    ok('Dados fiscais dos itens',
       f'{len(itens)} item{"ns" if len(itens) > 1 else ""} — NCM, CFOP, CST e valores OK')

    # ── 5b. Preencher campos tributáveis server-side (fallback quando JS não preencheu) ──
    from decimal import Decimal as _Dec, ROUND_HALF_UP
    _fields_trib = ['quantidade_tributavel', 'unidade_tributavel', 'valor_unitario_tributavel']
    for _item in nf.itens.select_related('produto__unidade_medida', 'produto__unidade_venda').all():
        _prod = _item.produto
        if not _prod:
            continue
        _fator = float(_prod.fator_conversao or 1)
        _un_med   = (_prod.unidade_medida.sigla if _prod.unidade_medida_id else '').strip()
        _un_venda = (_prod.unidade_venda.sigla  if _prod.unidade_venda_id  else '').strip()
        if _fator > 1 and _un_med and _un_med != _un_venda and not float(_item.quantidade_tributavel or 0):
            _item.quantidade_tributavel     = (_item.quantidade * _Dec(str(_fator))).quantize(_Dec('0.0001'), rounding=ROUND_HALF_UP)
            _item.unidade_tributavel        = _un_med
            _item.valor_unitario_tributavel = (_item.valor_unitario / _Dec(str(_fator))).quantize(_Dec('0.0001'), rounding=ROUND_HALF_UP)
            _item.save(update_fields=_fields_trib)

    # ── 6. Transmissão ────────────────────────────────────────────────
    import requests as _requests
    try:
        client = IntegranNotasClient(raw_token, config.ambiente_nfe)
        data = client.emitir_nfe(nf)
    except IntegranNotasError as exc:
        def _fmt_api_erro(e):
            if isinstance(e, dict):
                campo = e.get('campo') or ''
                msg   = e.get('erro') or e.get('message') or str(e)
                detalhe = e.get('detalhes') or e.get('descricao') or ''
                partes = []
                if campo:
                    partes.append(f'Campo: {campo}')
                partes.append(msg)
                if detalhe:
                    partes.append(f'Detalhe: {detalhe}')
                return ' — '.join(partes)
            return str(e)

        # ── Error 5008: NF já existe no IntegraNotas ─────────────────────
        # Mensagem contém o path: /nfe/{44-digit-chave}
        if exc.codigo == 5008:
            import re as _re
            _m = _re.search(r'/nfe/(\d{44})', str(exc))
            if _m:
                chave_5008 = _m.group(1)
                nf.chave_acesso = chave_5008
                nf.save(update_fields=['chave_acesso'])
                try:
                    data2 = client.consultar_nfe(chave_5008)
                    codigo2 = data2.get('codigo')
                    if codigo2 == 100:
                        protocolo2 = data2.get('protocolo', '')
                        xml2 = data2.get('xml', '')
                        pdf2 = data2.get('pdf', '')
                        nf.protocolo_autorizacao = protocolo2
                        nf.xml_autorizacao       = xml2
                        nf.pdf_danfe             = pdf2
                        nf.status                = 'EMITIDA'
                        nf.data_hora_emissao     = timezone.now()
                        nf.atualizado_por        = request.user
                        _base_f = ['chave_acesso', 'protocolo_autorizacao', 'xml_autorizacao',
                                   'pdf_danfe', 'status', 'data_hora_emissao', 'atualizado_por']
                        _extra2 = _upload_fiscal_docs(nf, nf.empresa_id, 'nfe', nf.numero, nf.serie, xml2, pdf2)
                        nf.save(update_fields=list(dict.fromkeys(_base_f + _extra2)))
                        _registrar_baixa_devolucao(nf)
                        _registrar_entrada_devolucao_venda(nf)
                        _processar_autorizacao_agrupamento(nf)
                        _sync_pedido_de_documento(nf=nf)
                        steps.append({'status': 'authorized', 'label': 'NF-e Autorizada (recuperada) ✓',
                                      'protocolo': protocolo2, 'chave': chave_5008})
                        return JsonResponse({
                            'steps': steps, 'success': True, 'authorized': True,
                            'chave': chave_5008, 'protocolo': protocolo2,
                            'has_danfe': bool(pdf2),
                            'danfe_url': reverse('faturamento:nota_fiscal_danfe', args=[pk]),
                            'detail_url': reverse('faturamento:nota_fiscal_detail', args=[pk]),
                        })
                    elif codigo2 == 5023:
                        nf.data_hora_emissao = timezone.now()
                        nf.atualizado_por    = request.user
                        nf.save(update_fields=['data_hora_emissao', 'atualizado_por'])
                        steps.append({'status': 'pending', 'label': 'Aguardando autorização da SEFAZ',
                                      'message': 'NF em fila (5008→5023). Verificando…', 'chave': chave_5008})
                        return JsonResponse({'steps': steps, 'success': True, 'pending': True, 'chave': chave_5008})
                except Exception:
                    pass
                steps.append({'status': 'pending', 'label': 'NF já enviada — verifique na SEFAZ',
                              'message': f'IntegraNotas indica NF já existente. Chave armazenada: {chave_5008}',
                              'chave': chave_5008})
                return JsonResponse({'steps': steps, 'success': True, 'pending': True, 'chave': chave_5008})

        erros_api = [_fmt_api_erro(e) for e in (exc.erros or [])]
        return erro('Transmissão à SEFAZ', str(exc), errors=erros_api)
    except _requests.exceptions.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else '?'
        try:
            api_msg = exc.response.json().get('mensagem') or exc.response.json().get('message') or ''
        except Exception:
            api_msg = (exc.response.text[:200] if exc.response is not None else '') or str(exc)
        if status_code in (401, 403):
            dicas = [
                f'Token usado (prefixo): {token_prefix}',
                f'URL chamada: {api_url}/nfe',
                f'Ambiente configurado: {ambiente_label}',
                'Verifique se o token no painel IntegraNotas é para Homologação ou Produção.',
                'Tokens de Produção NÃO funcionam na URL de Homologação e vice-versa.',
            ]
            return erro('Transmissão à SEFAZ',
                        f'Token rejeitado pelo IntegraNOtas (erro {status_code}).',
                        fix_url=reverse('faturamento:configuracao'),
                        fix_label='Atualizar token / ambiente',
                        errors=dicas)
        return erro('Transmissão à SEFAZ',
                    f'Erro HTTP {status_code} ao comunicar com IntegraNOtas: {api_msg}')
    except Exception as exc:
        return erro('Transmissão à SEFAZ', f'Falha de comunicação: {exc}')

    ok('Transmissão à SEFAZ', 'Dados enviados ao IntegraNOtas')

    # ── 7. Resultado ──────────────────────────────────────────────────
    chave     = data.get('chave', '')
    protocolo = data.get('protocolo', '')
    xml_b64   = data.get('xml', '')
    pdf_b64   = data.get('pdf', '')
    codigo    = data.get('codigo')

    if codigo == 5023:
        # Mantém RASCUNHO — só muda para EMITIDA quando a SEFAZ confirmar (código 100)
        nf.chave_acesso      = chave
        nf.data_hora_emissao = timezone.now()
        nf.atualizado_por    = request.user
        nf.save(update_fields=['chave_acesso', 'data_hora_emissao', 'atualizado_por'])
        steps.append({'status': 'pending', 'label': 'Aguardando autorização da SEFAZ',
                      'message': 'NF em fila de processamento (código 5023). '
                                 'Verificando resposta automaticamente…',
                      'chave': chave})
        return JsonResponse({'steps': steps, 'success': True, 'pending': True, 'chave': chave})

    # código 100 — autorizada imediatamente
    nf.chave_acesso          = chave
    nf.protocolo_autorizacao = protocolo
    nf.xml_autorizacao       = xml_b64
    nf.pdf_danfe             = pdf_b64
    nf.status                = 'EMITIDA'
    nf.data_hora_emissao     = timezone.now()
    nf.atualizado_por        = request.user
    _base_fields = ['chave_acesso', 'protocolo_autorizacao', 'xml_autorizacao',
                    'pdf_danfe', 'status', 'data_hora_emissao', 'atualizado_por']
    _extra = _upload_fiscal_docs(nf, nf.empresa_id, 'nfe', nf.numero, nf.serie, xml_b64, pdf_b64)
    nf.save(update_fields=list(dict.fromkeys(_base_fields + _extra)))
    _registrar_baixa_devolucao(nf)
    _registrar_entrada_devolucao_venda(nf)
    _processar_autorizacao_agrupamento(nf)
    _sync_pedido_de_documento(nf=nf)
    steps.append({'status': 'authorized', 'label': 'NF-e Autorizada pela SEFAZ ✓',
                  'protocolo': protocolo, 'chave': chave})
    return JsonResponse({
        'steps': steps, 'success': True, 'authorized': True,
        'chave': chave, 'protocolo': protocolo,
        'has_danfe': bool(pdf_b64),
        'danfe_url': reverse('faturamento:nota_fiscal_danfe', args=[pk]),
        'detail_url': reverse('faturamento:nota_fiscal_detail', args=[pk]),
    })


@login_required
@require_POST
def nota_fiscal_emitir(request, pk):
    from .services.integranotas import IntegranNotasClient, IntegranNotasError

    empresa = _get_empresa(request)
    nf = get_object_or_404(NotaFiscal, pk=pk, empresa=empresa)

    if nf.status != 'RASCUNHO':
        messages.error(request, 'Apenas NF-e em RASCUNHO podem ser emitidas.')
        return redirect('faturamento:nota_fiscal_detail', pk=pk)

    if not nf.itens.exists():
        messages.error(request, 'Adicione pelo menos um item antes de emitir.')
        return redirect('faturamento:nota_fiscal_detail', pk=pk)

    config = ConfiguracaoFiscal.objects.filter(empresa=empresa).first()
    if not config or not config.has_token:
        messages.error(request, 'Emitente IntegraNotas não configurado. Peça ao administrador da plataforma para criá-lo (Empresas → Listar).')
        return redirect('faturamento:nota_fiscal_detail', pk=pk)

    # Validação prévia: CNPJ e Razão Social do emitente são obrigatórios
    import re as _re
    cnpj_digits = _re.sub(r'\D', '', empresa.cnpj or '')
    if len(cnpj_digits) != 14:
        messages.error(request,
            'CNPJ do emitente inválido ou não informado. '
            'Preencha em Faturamento → Configuração Fiscal → Dados do Emitente.')
        return redirect('faturamento:nota_fiscal_detail', pk=pk)
    if not empresa.nome or not empresa.nome.strip():
        messages.error(request,
            'Razão Social do emitente não informada. '
            'Preencha em Faturamento → Configuração Fiscal → Dados do Emitente.')
        return redirect('faturamento:nota_fiscal_detail', pk=pk)

    # Atribui número sequencial se a NF ainda não tiver um
    if not nf.numero:
        ultimo = NotaFiscal.objects.filter(empresa=empresa).exclude(numero__isnull=True).order_by('-numero').first()
        nf.numero = (ultimo.numero + 1) if ultimo else (config.numero_nfe_inicial or 1)
        NotaFiscal.objects.filter(pk=nf.pk).update(numero=nf.numero)

    try:
        client = IntegranNotasClient(config.get_token(), config.ambiente_nfe)
        data = client.emitir_nfe(nf)

        chave = data.get('chave', '')
        protocolo = data.get('protocolo', '')
        xml_b64 = data.get('xml', '')
        pdf_b64 = data.get('pdf', '')
        codigo = data.get('codigo')

        if codigo == 5023:
            # Queued — salva chave e aguarda webhook / polling
            nf.chave_acesso = chave
            nf.status = 'EMITIDA'
            nf.data_hora_emissao = timezone.now()
            nf.atualizado_por = request.user
            nf.save(update_fields=['chave_acesso', 'status', 'data_hora_emissao', 'atualizado_por'])
            _sync_pedido_de_documento(nf=nf)
            messages.info(request, f'NF {nf.numero}/{nf.serie} enviada à SEFAZ — aguardando autorização. Chave: {chave}')
        else:
            # Authorized immediately (codigo == 100)
            nf.chave_acesso = chave
            nf.protocolo_autorizacao = protocolo
            nf.xml_autorizacao = xml_b64
            nf.pdf_danfe = pdf_b64
            nf.status = 'EMITIDA'
            nf.data_hora_emissao = timezone.now()
            nf.atualizado_por = request.user
            _base = ['chave_acesso', 'protocolo_autorizacao', 'xml_autorizacao',
                     'pdf_danfe', 'status', 'data_hora_emissao', 'atualizado_por']
            _extra = _upload_fiscal_docs(nf, nf.empresa_id, 'nfe', nf.numero, nf.serie, xml_b64, pdf_b64)
            nf.save(update_fields=list(dict.fromkeys(_base + _extra)))
            _registrar_baixa_devolucao(nf)
            _registrar_entrada_devolucao_venda(nf)
            _processar_autorizacao_agrupamento(nf)
            _sync_pedido_de_documento(nf=nf)
            messages.success(request, f'NF {nf.numero}/{nf.serie} autorizada! Chave: {chave}')

    except IntegranNotasError as exc:
        # ── Error 5008: NF já existe no IntegraNotas ─────────────────────
        if exc.codigo == 5008:
            import re as _re
            _m = _re.search(r'/nfe/(\d{44})', str(exc))
            if _m:
                chave_5008 = _m.group(1)
                nf.chave_acesso = chave_5008
                nf.save(update_fields=['chave_acesso'])
                try:
                    data2 = client.consultar_nfe(chave_5008)
                    if data2.get('codigo') == 100:
                        xml2 = data2.get('xml', '')
                        pdf2 = data2.get('pdf', '')
                        nf.protocolo_autorizacao = data2.get('protocolo', '')
                        nf.xml_autorizacao       = xml2
                        nf.pdf_danfe             = pdf2
                        nf.status                = 'EMITIDA'
                        nf.data_hora_emissao     = timezone.now()
                        nf.atualizado_por        = request.user
                        _base = ['chave_acesso', 'protocolo_autorizacao', 'xml_autorizacao',
                                 'pdf_danfe', 'status', 'data_hora_emissao', 'atualizado_por']
                        _extra = _upload_fiscal_docs(nf, nf.empresa_id, 'nfe', nf.numero, nf.serie, xml2, pdf2)
                        nf.save(update_fields=list(dict.fromkeys(_base + _extra)))
                        _registrar_baixa_devolucao(nf)
                        _registrar_entrada_devolucao_venda(nf)
                        _sync_pedido_de_documento(nf=nf)
                        messages.success(request, f'NF {nf.numero}/{nf.serie} autorizada (recuperada)! Chave: {chave_5008}')
                        return redirect('faturamento:nota_fiscal_detail', pk=pk)
                    elif data2.get('codigo') == 5023:
                        nf.data_hora_emissao = timezone.now()
                        nf.atualizado_por    = request.user
                        nf.save(update_fields=['data_hora_emissao', 'atualizado_por'])
                        messages.info(request, f'NF {nf.numero}/{nf.serie} enviada — aguardando autorização SEFAZ. Chave: {chave_5008}')
                        return redirect('faturamento:nota_fiscal_detail', pk=pk)
                except Exception:
                    pass
                messages.warning(request, f'NF já enviada ao IntegraNotas. Chave armazenada: {chave_5008}. Use "Verificar na SEFAZ".')
                return redirect('faturamento:nota_fiscal_detail', pk=pk)
        erros = '; '.join(str(e) for e in exc.erros) if exc.erros else ''
        msg = f'Erro IntegraNota [{exc.codigo}]: {exc} {erros}'.strip()
        messages.error(request, msg)
    except Exception as exc:
        import requests as _req
        if isinstance(exc, _req.exceptions.HTTPError):
            status_code = exc.response.status_code if exc.response is not None else '?'
            try:
                body = exc.response.json()
                api_msg = body.get('mensagem') or body.get('message') or str(body)
            except Exception:
                api_msg = exc.response.text[:300] if exc.response is not None else str(exc)
            if status_code == 403:
                messages.error(request,
                    f'IntegraNotas recusou o acesso (403). '
                    f'Verifique o Token em Faturamento → Configuração Fiscal. '
                    f'Detalhe da API: {api_msg}')
            elif status_code == 401:
                messages.error(request, f'Token inválido ou não informado (401). Configure o Token em Faturamento → Configuração Fiscal.')
            else:
                messages.error(request, f'Falha na comunicação com IntegraNotas [{status_code}]: {api_msg}')
        else:
            messages.error(request, f'Falha na comunicação com IntegraNotas: {exc}')

    return redirect('faturamento:nota_fiscal_detail', pk=pk)


@login_required
def nota_fiscal_cancelar(request, pk):
    from .services.integranotas import IntegranNotasClient, IntegranNotasError

    empresa = _get_empresa(request)
    nf = get_object_or_404(NotaFiscal, pk=pk, empresa=empresa)

    if nf.status == 'CANCELADA':
        messages.warning(request, 'NF-e já está cancelada.')
        return redirect('faturamento:nota_fiscal_detail', pk=pk)

    # Bloqueia cancelamento de NF filha já faturada
    if nf.status_faturamento == 'FATURADA':
        messages.error(
            request,
            'Esta NF-e de remessa já foi faturada (vinculada à Nota Mãe). '
            'Para cancelá-la é necessário cancelar a Nota Mãe primeiro.'
        )
        return redirect('faturamento:nota_fiscal_detail', pk=pk)

    if request.method == 'POST':
        form = NotaFiscalCancelarForm(request.POST)
        if form.is_valid():
            justificativa = form.cleaned_data['justificativa']

            # Se NF tem chave, tenta cancelar na SEFAZ via IntegraNota
            if nf.chave_acesso:
                config = ConfiguracaoFiscal.objects.filter(empresa=empresa).first()
                if not config or not config.has_token:
                    messages.error(request, 'Emitente IntegraNotas não configurado. Peça ao administrador da plataforma para criá-lo (Empresas → Listar).')
                    return render(request, 'faturamento/nota_fiscal/cancelar_form.html', {'form': form, 'nf': nf})
                try:
                    client = IntegranNotasClient(config.get_token(), config.ambiente_nfe)
                    client.cancelar_nfe(nf.chave_acesso, justificativa)
                except IntegranNotasError as exc:
                    messages.error(request, f'Erro ao cancelar na SEFAZ [{exc.codigo}]: {exc}')
                    return render(request, 'faturamento/nota_fiscal/cancelar_form.html', {'form': form, 'nf': nf})
                except Exception as exc:
                    messages.error(request, f'Falha na comunicação com IntegraNota: {exc}')
                    return render(request, 'faturamento/nota_fiscal/cancelar_form.html', {'form': form, 'nf': nf})

            # Estorno de estoque para remessa pendente
            if nf.status_faturamento == 'PENDENTE':
                from .services.agrupamento import registrar_estorno_remessa
                registrar_estorno_remessa(nf)

            nf.status = 'CANCELADA'
            nf.motivo_cancelamento = justificativa
            nf.data_cancelamento = timezone.now()
            nf.atualizado_por = request.user
            nf.save(update_fields=['status', 'motivo_cancelamento', 'data_cancelamento', 'atualizado_por'])
            _sync_pedido_de_documento(nf=nf)
            messages.success(request, f'NF {nf.numero}/{nf.serie} cancelada.')
            return redirect('faturamento:nota_fiscal_detail', pk=pk)
    else:
        form = NotaFiscalCancelarForm()

    return render(request, 'faturamento/nota_fiscal/cancelar_form.html', {'form': form, 'nf': nf})


@login_required
@require_POST
def nota_fiscal_consultar(request, pk):
    """Consulta manual do status da NF-e na SEFAZ via IntegraNota.
    Útil quando o webhook não foi recebido e a NF está EMITIDA sem protocolo."""
    from .services.integranotas import IntegranNotasClient, IntegranNotasError

    empresa = _get_empresa(request)
    nf = get_object_or_404(NotaFiscal, pk=pk, empresa=empresa)

    if not nf.chave_acesso:
        messages.error(request, 'NF-e não possui chave de acesso — emita antes de consultar.')
        return redirect('faturamento:nota_fiscal_detail', pk=pk)

    config = ConfiguracaoFiscal.objects.filter(empresa=empresa).first()
    if not config or not config.has_token:
        messages.error(request, 'Emitente IntegraNotas não configurado. Peça ao administrador da plataforma para criá-lo (Empresas → Listar).')
        return redirect('faturamento:nota_fiscal_detail', pk=pk)

    try:
        client = IntegranNotasClient(config.get_token(), config.ambiente_nfe)
        data = client.consultar_nfe(nf.chave_acesso)
        codigo = data.get('codigo')

        if codigo == 100:
            # Autorizada — atualiza protocolo, XML e DANFE
            fields = []
            if data.get('protocolo') and not nf.protocolo_autorizacao:
                nf.protocolo_autorizacao = data['protocolo']
                fields.append('protocolo_autorizacao')
            if data.get('xml'):
                nf.xml_autorizacao = data['xml']
                fields.append('xml_autorizacao')
            if data.get('pdf'):
                nf.pdf_danfe = data['pdf']
                fields.append('pdf_danfe')
            if nf.status != 'EMITIDA':
                nf.status = 'EMITIDA'
                fields.append('status')
            if not nf.data_hora_emissao:
                nf.data_hora_emissao = timezone.now()
                fields.append('data_hora_emissao')
            if fields:
                _extra = _upload_fiscal_docs(nf, nf.empresa_id, 'nfe', nf.numero, nf.serie,
                                             data.get('xml'), data.get('pdf'))
                nf.save(update_fields=list(dict.fromkeys(fields + _extra)))
            messages.success(request,
                f'NF-e autorizada pela SEFAZ. Protocolo: {nf.protocolo_autorizacao}')

        elif codigo == 101:
            # Cancelada na SEFAZ
            nf.status = 'CANCELADA'
            nf.data_cancelamento = timezone.now()
            nf.save(update_fields=['status', 'data_cancelamento'])
            messages.warning(request, 'SEFAZ informou que esta NF-e está CANCELADA.')

        elif codigo == 5023:
            messages.info(request,
                'NF-e ainda em processamento na SEFAZ (código 5023). Tente novamente em alguns instantes.')

        else:
            mensagem = data.get('mensagem') or data.get('message') or f'Código {codigo}'

            # ── Rejeição 539: SEFAZ já tem esse número com chave diferente ──
            if codigo == 539:
                import re as _re539
                _m = _re539.search(r'chNFe[:\s]*(\d{44})', mensagem or '')
                if _m:
                    chave_sefaz = _m.group(1)
                    nf.chave_acesso = chave_sefaz
                    nf.save(update_fields=['chave_acesso'])
                    try:
                        data2 = client.consultar_nfe(chave_sefaz)
                        if data2.get('codigo') == 100:
                            _fields = ['chave_acesso', 'status']
                            nf.status = 'EMITIDA'
                            if data2.get('protocolo'):
                                nf.protocolo_autorizacao = data2['protocolo']
                                _fields.append('protocolo_autorizacao')
                            if data2.get('xml'):
                                nf.xml_autorizacao = data2['xml']
                                _fields.append('xml_autorizacao')
                            if data2.get('pdf'):
                                nf.pdf_danfe = data2['pdf']
                                _fields.append('pdf_danfe')
                            if not nf.data_hora_emissao:
                                nf.data_hora_emissao = timezone.now()
                                _fields.append('data_hora_emissao')
                            _extra = _upload_fiscal_docs(nf, nf.empresa_id, 'nfe',
                                                         nf.numero, nf.serie,
                                                         data2.get('xml'), data2.get('pdf'))
                            nf.save(update_fields=list(dict.fromkeys(_fields + _extra)))
                            messages.success(request,
                                f'NF-e recuperada e autorizada pela SEFAZ. Protocolo: {nf.protocolo_autorizacao}')
                            return redirect('faturamento:nota_fiscal_detail', pk=pk)
                    except Exception:
                        pass
                    messages.warning(request,
                        'NF-e já registrada na SEFAZ com chave diferente. '
                        'A chave foi salva — use "Verificar na SEFAZ" para confirmar a autorização.')
                    return redirect('faturamento:nota_fiscal_detail', pk=pk)

            # Rejeição — reverte para RASCUNHO limpo independente do status atual
            if not nf.protocolo_autorizacao:
                nf.status = 'RASCUNHO'
                nf.chave_acesso = ''
                nf.save(update_fields=['status', 'chave_acesso'])
                logger.warning('[NF %s] Rejeitada pela SEFAZ (código %s): %s — revertida para RASCUNHO',
                               nf.numero or 'S/N', codigo, mensagem)
            messages.error(request, f'NF-e REJEITADA pela SEFAZ (código {codigo}): {mensagem}')

    except IntegranNotasError as exc:
        erros = '; '.join(str(e) for e in exc.erros) if exc.erros else ''
        messages.error(request, f'Erro IntegraNota [{exc.codigo}]: {exc} {erros}'.strip())
    except Exception as exc:
        messages.error(request, f'Falha na comunicação com IntegraNota: {exc}')

    return redirect('faturamento:nota_fiscal_detail', pk=pk)


@login_required
@require_POST
def nota_fiscal_consultar_ajax(request, pk):
    """AJAX: consulta status na SEFAZ e retorna JSON (usado para polling após código 5023)."""
    from .services.integranotas import IntegranNotasClient, IntegranNotasError

    empresa = _get_empresa(request)
    nf = get_object_or_404(NotaFiscal, pk=pk, empresa=empresa)

    if not nf.chave_acesso:
        return JsonResponse({'status': 'error', 'mensagem': 'NF sem chave de acesso.'})

    config = ConfiguracaoFiscal.objects.filter(empresa=empresa).first()
    if not config or not config.has_token:
        return JsonResponse({'status': 'error', 'mensagem': 'Token não configurado.'})

    try:
        client = IntegranNotasClient(config.get_token(), config.ambiente_nfe)
        data = client.consultar_nfe(nf.chave_acesso)
        codigo = data.get('codigo')

        if codigo == 100:
            fields = []
            if data.get('protocolo'):
                nf.protocolo_autorizacao = data['protocolo']
                fields.append('protocolo_autorizacao')
            if data.get('xml'):
                nf.xml_autorizacao = data['xml']
                fields.append('xml_autorizacao')
            if data.get('pdf'):
                nf.pdf_danfe = data['pdf']
                fields.append('pdf_danfe')
            if nf.status != 'EMITIDA':
                nf.status = 'EMITIDA'
                fields.append('status')
            if not nf.data_hora_emissao:
                nf.data_hora_emissao = timezone.now()
                fields.append('data_hora_emissao')
            if fields:
                _extra = _upload_fiscal_docs(nf, nf.empresa_id, 'nfe', nf.numero, nf.serie,
                                             data.get('xml'), data.get('pdf'))
                nf.save(update_fields=list(dict.fromkeys(fields + _extra)))
            return JsonResponse({
                'status': 'authorized',
                'protocolo': nf.protocolo_autorizacao,
                'has_danfe': bool(nf.pdf_danfe or nf.pdf_danfe_url),
                'danfe_url': nf.pdf_danfe_url or '',
                'detail_url': reverse('faturamento:nota_fiscal_detail', args=[pk]),
            })

        elif codigo == 5023:
            return JsonResponse({'status': 'pending'})

        elif codigo == 101:
            nf.status = 'CANCELADA'
            nf.save(update_fields=['status'])
            return JsonResponse({'status': 'cancelled', 'mensagem': 'NF-e cancelada na SEFAZ.'})

        else:
            mensagem = data.get('mensagem') or data.get('message') or f'Código {codigo}'

            # ── Rejeição 539: SEFAZ já tem esse número com chave diferente ──
            if codigo == 539:
                import re as _re539
                _m = _re539.search(r'chNFe[:\s]*(\d{44})', mensagem or '')
                if _m:
                    chave_sefaz = _m.group(1)
                    nf.chave_acesso = chave_sefaz
                    nf.save(update_fields=['chave_acesso'])
                    try:
                        data2 = client.consultar_nfe(chave_sefaz)
                        if data2.get('codigo') == 100:
                            _fields = ['chave_acesso', 'status']
                            nf.status = 'EMITIDA'
                            if data2.get('protocolo'):
                                nf.protocolo_autorizacao = data2['protocolo']
                                _fields.append('protocolo_autorizacao')
                            if data2.get('xml'):
                                nf.xml_autorizacao = data2['xml']
                                _fields.append('xml_autorizacao')
                            if data2.get('pdf'):
                                nf.pdf_danfe = data2['pdf']
                                _fields.append('pdf_danfe')
                            if not nf.data_hora_emissao:
                                nf.data_hora_emissao = timezone.now()
                                _fields.append('data_hora_emissao')
                            _extra = _upload_fiscal_docs(nf, nf.empresa_id, 'nfe',
                                                         nf.numero, nf.serie,
                                                         data2.get('xml'), data2.get('pdf'))
                            nf.save(update_fields=list(dict.fromkeys(_fields + _extra)))
                            return JsonResponse({
                                'status': 'authorized',
                                'protocolo': nf.protocolo_autorizacao,
                                'has_danfe': bool(nf.pdf_danfe or nf.pdf_danfe_url),
                                'danfe_url': nf.pdf_danfe_url or '',
                                'detail_url': reverse('faturamento:nota_fiscal_detail', args=[pk]),
                            })
                        if data2.get('codigo') == 5023:
                            return JsonResponse({'status': 'pending'})
                    except Exception:
                        pass
                    return JsonResponse({
                        'status': 'rejected', 'codigo': 539,
                        'mensagem': 'NF-e já registrada na SEFAZ com chave diferente. '
                                    'A chave foi salva — use "Verificar na SEFAZ" para confirmar.',
                    })

            if not nf.protocolo_autorizacao:
                nf.status = 'RASCUNHO'
                nf.chave_acesso = ''
                nf.save(update_fields=['status', 'chave_acesso'])
                logger.warning('[NF %s] Rejeitada (ajax) pelo SEFAZ código %s: %s — revertida para RASCUNHO',
                               nf.numero or 'S/N', codigo, mensagem)
            return JsonResponse({'status': 'rejected', 'codigo': codigo, 'mensagem': mensagem})

    except IntegranNotasError as exc:
        erros = '; '.join(str(e) for e in exc.erros) if exc.erros else ''
        return JsonResponse({'status': 'error', 'mensagem': f'{exc} {erros}'.strip()})
    except Exception as exc:
        return JsonResponse({'status': 'error', 'mensagem': str(exc)})


@login_required
@require_POST
def nota_fiscal_recuperar(request, pk):
    """Recupera NF-e cujo número já existe na SEFAZ com chave diferente.
    Útil quando a NF foi transmitida mas a resposta se perdeu (timeout, falha de rede).
    O usuário informa a chave correta (obtida no painel IntegraNotas) e o sistema a consulta."""
    from .services.integranotas import IntegranNotasClient, IntegranNotasError

    empresa = _get_empresa(request)
    nf = get_object_or_404(NotaFiscal, pk=pk, empresa=empresa)

    chave = (request.POST.get('chave_acesso') or '').strip().replace(' ', '')

    if len(chave) != 44 or not chave.isdigit():
        messages.error(request, 'Chave de acesso inválida — deve ter exatamente 44 dígitos numéricos.')
        return redirect('faturamento:nota_fiscal_detail', pk=pk)

    config = ConfiguracaoFiscal.objects.filter(empresa=empresa).first()
    if not config or not config.has_token:
        messages.error(request, 'Emitente IntegraNotas não configurado. Peça ao administrador da plataforma para criá-lo (Empresas → Listar).')
        return redirect('faturamento:nota_fiscal_detail', pk=pk)

    try:
        client = IntegranNotasClient(config.get_token(), config.ambiente_nfe)
        data = client.consultar_nfe(chave)
        codigo = data.get('codigo')

        if codigo == 100:
            fields = ['chave_acesso', 'status']
            nf.chave_acesso = chave
            nf.status = 'EMITIDA'
            if data.get('protocolo'):
                nf.protocolo_autorizacao = data['protocolo']
                fields.append('protocolo_autorizacao')
            if data.get('xml'):
                nf.xml_autorizacao = data['xml']
                fields.append('xml_autorizacao')
            if data.get('pdf'):
                nf.pdf_danfe = data['pdf']
                fields.append('pdf_danfe')
            if not nf.data_hora_emissao:
                nf.data_hora_emissao = timezone.now()
                fields.append('data_hora_emissao')
            _extra = _upload_fiscal_docs(nf, nf.empresa_id, 'nfe', nf.numero, nf.serie,
                                         data.get('xml'), data.get('pdf'))
            nf.save(update_fields=list(dict.fromkeys(fields + _extra)))
            messages.success(request,
                f'NF-e recuperada com sucesso! Protocolo SEFAZ: {nf.protocolo_autorizacao}')

        elif codigo == 5023:
            nf.chave_acesso = chave
            nf.status = 'EMITIDA'
            if not nf.data_hora_emissao:
                nf.data_hora_emissao = timezone.now()
            nf.save(update_fields=['chave_acesso', 'status', 'data_hora_emissao'])
            messages.info(request,
                'NF-e em fila na SEFAZ (código 5023). Chave registrada. '
                'Use "Verificar na SEFAZ" para atualizar o protocolo.')

        else:
            mensagem = data.get('mensagem') or f'Código {codigo}'
            messages.warning(request,
                f'Resposta da SEFAZ: {mensagem}. '
                'Verifique a chave informada ou consulte o painel IntegraNotas.')

    except IntegranNotasError as exc:
        erros = '; '.join(str(e) for e in exc.erros) if exc.erros else ''
        messages.error(request, f'Erro ao consultar [{exc.codigo}]: {exc} {erros}'.strip())
    except Exception as exc:
        messages.error(request, f'Falha na comunicação: {exc}')

    return redirect('faturamento:nota_fiscal_detail', pk=pk)


@csrf_exempt
def integranotas_webhook(request):
    """Receives async status notifications from IntegraNota."""
    import json
    if request.method != 'POST':
        return HttpResponse(status=405)

    try:
        payload = json.loads(request.body)
    except Exception:
        return HttpResponse(status=400)

    chave = payload.get('chave') or payload.get('chave_acesso', '')
    if not chave:
        return HttpResponse(status=200)

    try:
        nf = NotaFiscal.objects.get(chave_acesso=chave)
    except NotaFiscal.DoesNotExist:
        return HttpResponse(status=200)

    codigo = payload.get('codigo')
    if codigo == 100:
        nf.protocolo_autorizacao = payload.get('protocolo', nf.protocolo_autorizacao)
        nf.xml_autorizacao = payload.get('xml', nf.xml_autorizacao)
        nf.pdf_danfe = payload.get('pdf', nf.pdf_danfe)
        if not nf.data_hora_emissao:
            nf.data_hora_emissao = timezone.now()
        nf.status = 'EMITIDA'
        _base = ['protocolo_autorizacao', 'xml_autorizacao', 'pdf_danfe', 'data_hora_emissao', 'status']
        _extra = _upload_fiscal_docs(nf, nf.empresa_id, 'nfe', nf.numero, nf.serie,
                                     payload.get('xml'), payload.get('pdf'))
        nf.save(update_fields=list(dict.fromkeys(_base + _extra)))
    elif codigo == 101:
        nf.status = 'CANCELADA'
        if not nf.data_cancelamento:
            nf.data_cancelamento = timezone.now()
        nf.save(update_fields=['status', 'data_cancelamento'])
    elif codigo and not nf.protocolo_autorizacao:
        # Rejeição SEFAZ (ex.: 525, 539…) — reverte para RASCUNHO editável
        nf.status = 'RASCUNHO'
        nf.chave_acesso = ''
        nf.save(update_fields=['status', 'chave_acesso'])
        import logging as _log
        _log.getLogger(__name__).warning(
            '[Webhook NF %s] Rejeição SEFAZ código %s: %s — revertida para RASCUNHO',
            nf.numero or 'S/N', codigo, payload.get('mensagem', ''))

    return HttpResponse(status=200)


@login_required
def nota_fiscal_danfe(request, pk):
    """Download do DANFE PDF da NF-e (IntegraNotas)."""
    import base64
    from django.shortcuts import redirect as _redirect
    empresa = _get_empresa(request)
    nf = get_object_or_404(NotaFiscal, pk=pk, empresa=empresa)
    if nf.pdf_danfe_url:
        return _redirect(nf.pdf_danfe_url)
    if not nf.pdf_danfe:
        messages.error(request, 'DANFE não disponível — a NF-e ainda não foi autorizada pela SEFAZ.')
        return redirect('faturamento:nota_fiscal_detail', pk=pk)
    pdf_bytes = base64.b64decode(nf.pdf_danfe)
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="DANFE_{nf.numero}_{nf.serie}.pdf"'
    return response


@login_required
def nota_fiscal_xml(request, pk):
    """Download do XML autorizado da NF-e (Supabase URL ou base64)."""
    import base64
    import urllib.request as _ur
    empresa = _get_empresa(request)
    nf = get_object_or_404(NotaFiscal, pk=pk, empresa=empresa)

    xml_bytes = None
    chave = nf.chave_acesso or f'NF{nf.numero}_{nf.serie}'

    if nf.xml_autorizacao_url:
        try:
            with _ur.urlopen(nf.xml_autorizacao_url) as r:
                xml_bytes = r.read()
        except Exception:
            pass

    if xml_bytes is None and nf.xml_autorizacao:
        xml_bytes = base64.b64decode(nf.xml_autorizacao)

    if not xml_bytes:
        messages.error(request, 'XML não disponível — a NF-e ainda não foi autorizada pela SEFAZ.')
        return redirect('faturamento:nota_fiscal_detail', pk=pk)

    response = HttpResponse(xml_bytes, content_type='application/xml; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{chave}-nfe.xml"'
    return response


@login_required
def nota_fiscal_clone(request, pk):
    """Clona uma NF-e como novo rascunho (sem número, sem chave fiscal)."""
    empresa = _get_empresa(request)
    nf = get_object_or_404(NotaFiscal, pk=pk, empresa=empresa)

    itens      = list(nf.itens.all())
    pagamentos = list(nf.pagamentos.all())
    duplicatas = list(nf.duplicatas.all())

    nf.pk = None
    nf.numero                 = None
    nf.chave_acesso           = ''
    nf.protocolo_autorizacao  = ''
    nf.xml_autorizacao        = ''
    nf.xml_autorizacao_url    = ''
    nf.pdf_danfe              = ''
    nf.pdf_danfe_url          = ''
    nf.status                 = 'RASCUNHO'
    nf.data_hora_emissao      = None
    nf.motivo_cancelamento    = ''
    nf.data_cancelamento      = None
    nf.manifestacao_tipo      = ''
    nf.manifestacao_protocolo = ''
    nf.manifestacao_data      = None
    nf.save()

    for item in itens:
        item.pk = None
        item.nota_fiscal = nf
        item.save()
    for pag in pagamentos:
        pag.pk = None
        pag.nota_fiscal = nf
        pag.save()
    for dup in duplicatas:
        dup.pk = None
        dup.nota_fiscal = nf
        dup.save()

    messages.success(request, f'NF-e clonada como rascunho #{nf.pk}. Revise os dados antes de emitir.')
    return redirect('faturamento:nota_fiscal_update', pk=nf.pk)


# Mapeamento SEFAZ: CFOP de saída → CFOP de devolução (entrada)
_CFOP_DEV = {
    # Vendas internas (5xxx) → devoluções internas (1xxx)
    '5101': '1201', '5102': '1202', '5103': '1202', '5104': '1202',
    '5105': '1202', '5106': '1202', '5109': '1202', '5110': '1202',
    '5111': '1201', '5112': '1201', '5113': '1202', '5114': '1202',
    '5115': '1202', '5116': '1202', '5117': '1202', '5118': '1201',
    '5120': '1202', '5122': '1202', '5123': '1202',
    '5401': '1401', '5403': '1403', '5405': '1405', '5410': '1410',
    # Vendas interestaduais (6xxx) → devoluções interestaduais (2xxx)
    '6101': '2201', '6102': '2202', '6103': '2202', '6104': '2202',
    '6105': '2202', '6106': '2202', '6109': '2202', '6110': '2202',
    '6111': '2201', '6112': '2201', '6113': '2202', '6114': '2202',
    '6115': '2202', '6116': '2202', '6117': '2202', '6118': '2201',
    '6120': '2202', '6122': '2202', '6123': '2202',
    '6401': '2401', '6403': '2403', '6405': '2405', '6410': '2410',
    # Exportações (7xxx) → retorno do exterior sem DI (3949 evita rejeição 525)
    '7101': '3949', '7102': '3949', '7105': '3949', '7106': '3949',
    '7127': '3949', '7129': '3949',
    '7501': '3949', '7504': '3949',
}


def _cfop_devolucao(cfop):
    d = (cfop or '').replace('.', '').strip()
    if len(d) != 4:
        return cfop
    mapped = _CFOP_DEV.get(d)
    if mapped:
        return mapped
    # Fallback: troca primeiro dígito (5→1, 6→2, 7→3)
    novo = {'5': '1', '6': '2', '7': '3'}.get(d[0], d[0])
    return novo + d[1:]


@login_required
def nota_fiscal_devolucao(request, pk):
    """Cria rascunho de NF-e de devolução a partir de uma NF de saída autorizada."""
    import re as _re
    from datetime import date
    from django.db import transaction

    empresa = _get_empresa(request)
    nf_orig = get_object_or_404(NotaFiscal, pk=pk, empresa=empresa)

    if nf_orig.status != 'EMITIDA' or not nf_orig.chave_acesso:
        messages.error(request, 'Devolução só pode ser criada a partir de uma NF-e autorizada pela SEFAZ.')
        return redirect('faturamento:nota_fiscal_detail', pk=pk)

    if nf_orig.finalidade_nfe == '4':
        messages.error(request, 'Não é possível criar devolução de uma NF-e que já é de devolução.')
        return redirect('faturamento:nota_fiscal_detail', pk=pk)

    itens = list(nf_orig.itens.all())

    with transaction.atomic():
        nf_dev = NotaFiscal.objects.get(pk=pk)
        nf_dev.pk                  = None
        nf_dev.numero              = None
        nf_dev.chave_acesso        = ''
        nf_dev.protocolo_autorizacao = ''
        nf_dev.xml_autorizacao     = ''
        nf_dev.xml_autorizacao_url = ''
        nf_dev.pdf_danfe           = ''
        nf_dev.pdf_danfe_url       = ''
        nf_dev.status              = 'RASCUNHO'
        nf_dev.data_hora_emissao   = None
        nf_dev.motivo_cancelamento = ''
        nf_dev.data_cancelamento   = None
        nf_dev.manifestacao_tipo      = ''
        nf_dev.manifestacao_protocolo = ''
        nf_dev.manifestacao_data      = None
        nf_dev.data_emissao        = date.today()
        nf_dev.data_saida          = None
        # Campos de devolução
        nf_dev.finalidade_nfe          = '4'
        nf_dev.tipo_operacao           = 'DEVOLUCAO'
        nf_dev.natureza_operacao       = 'DEVOLUÇÃO DE VENDA'
        nf_dev.nota_mae                = None
        nf_dev.status_faturamento      = 'NAO_APLICA'
        # Não preenche chave_nfe_referenciada nem NFeReferenciada (NFref de
        # cabeçalho): a regra VC02-14 (NT 2025.002-RTC v1.50) proíbe o NFref
        # de cabeçalho em devolução de mercadoria — o referenciamento é feito
        # exclusivamente por item (dfe_ref_chave_acesso/dfe_ref_nitem abaixo).
        nf_dev.save()

        cnpj_empresa = _re.sub(r'\D', '', nf_orig.empresa.cnpj or '')
        for item in itens:
            item.pk          = None
            item.nota_fiscal = nf_dev
            item.cfop        = _cfop_devolucao(item.cfop)
            # Referenciamento por item (NT 2025.002-RTC v1.50, regra VC02-14): em
            # devolução, o DFeReferenciado por item substitui o NFref de cabeçalho.
            # numero_item ainda não foi alterado neste ponto — reflete o item da
            # NF-e original.
            item.dfe_ref_chave_acesso = nf_orig.chave_acesso
            item.dfe_ref_nitem        = item.numero_item
            # Auto-preenche DI para itens com CFOP 3xxx (retorno de exportação/drawback).
            # Convenção SEFAZ: nDI = zeros quando não há DI real de importação.
            if item.cfop.startswith('3') and not (item.di_numero or '').strip():
                item.di_numero            = '0000000000'
                item.di_data_registro     = date.today()
                item.di_data_desembaraco  = date.today()
                item.di_via_transporte    = '1'   # marítima
                item.di_tipo_intermediario = '1'  # conta própria
                item.di_numero_adicao     = '1'
                item.di_codigo_fabricante = '1'
                item.di_codigo_exportador = cnpj_empresa
                # Local/UF do porto de embarque da NF original
                if nf_orig.embarque_local:
                    item.di_local_desembaraco = nf_orig.embarque_local
                if nf_orig.embarque_uf:
                    item.di_uf_desembaraco = nf_orig.embarque_uf
                # di_numero_drawback deixado em branco — usuário preenche com o ato concessório real
            item.save()

        # nf_dev foi clonada de nf_orig (que é uma saída autorizada) — sem isso,
        # entrada_saida ficaria herdado como Saída mesmo sendo devolução (Entrada).
        nf_dev.calcular_totais()

    messages.info(
        request,
        f'Rascunho de devolução criado (NF #{nf_dev.pk}). '
        f'Preencha o Nº do Drawback na aba DI de cada item com CFOP 3xxx antes de emitir.'
    )
    return redirect('faturamento:nota_fiscal_update', pk=nf_dev.pk)


@login_required
def nota_fiscal_complementar(request, pk, tipo):
    """Cria rascunho de NF-e Complementar (finalidade_nfe='2') a partir de uma
    NF-e de saída autorizada.

    `tipo` define a regra de negócio aplicada aos itens copiados:
    - 'valor': complementa apenas o valor — zera a quantidade de todos os
      itens (a mercadoria já saiu/entrou pela nota original).
    - 'quantidade': complementa apenas a quantidade física (uso típico em
      exportação) — zera o valor unitário de todos os itens (o valor
      comercial já foi acertado/fechado no contrato original).
    """
    from datetime import date
    from django.db import transaction

    from .models import NFeReferenciada

    if tipo not in ('valor', 'quantidade'):
        messages.error(request, 'Tipo de complemento inválido.')
        return redirect('faturamento:nota_fiscal_detail', pk=pk)

    empresa = _get_empresa(request)
    nf_orig = get_object_or_404(NotaFiscal, pk=pk, empresa=empresa)

    if nf_orig.status != 'EMITIDA' or not nf_orig.chave_acesso:
        messages.error(request, 'Nota Complementar só pode ser criada a partir de uma NF-e autorizada pela SEFAZ.')
        return redirect('faturamento:nota_fiscal_detail', pk=pk)

    if nf_orig.finalidade_nfe == '4':
        messages.error(request, 'Não é possível criar nota complementar a partir de uma NF-e de devolução.')
        return redirect('faturamento:nota_fiscal_detail', pk=pk)

    tipo_complemento = 'VALOR' if tipo == 'valor' else 'QUANTIDADE'
    itens = list(nf_orig.itens.all())
    chave_orig = nf_orig.chave_acesso
    numero_orig = nf_orig.numero
    data_orig = nf_orig.data_emissao

    with transaction.atomic():
        nf_comp = NotaFiscal.objects.get(pk=pk)
        nf_comp.pk                  = None
        nf_comp.numero              = None
        nf_comp.chave_acesso        = ''
        nf_comp.protocolo_autorizacao = ''
        nf_comp.xml_autorizacao     = ''
        nf_comp.xml_autorizacao_url = ''
        nf_comp.pdf_danfe           = ''
        nf_comp.pdf_danfe_url       = ''
        nf_comp.status              = 'RASCUNHO'
        nf_comp.data_hora_emissao   = None
        nf_comp.motivo_cancelamento = ''
        nf_comp.data_cancelamento   = None
        nf_comp.manifestacao_tipo      = ''
        nf_comp.manifestacao_protocolo = ''
        nf_comp.manifestacao_data      = None
        nf_comp.data_emissao        = date.today()
        nf_comp.data_saida          = None
        nf_comp.chave_nfe_referenciada = ''
        # Campos de nota complementar
        nf_comp.finalidade_nfe    = '2'
        nf_comp.tipo_operacao     = 'COMPLEMENTAR'
        nf_comp.tipo_complemento  = tipo_complemento
        nf_comp.nota_complementada = nf_orig
        nf_comp.nota_mae           = None
        nf_comp.status_faturamento = 'NAO_APLICA'
        if tipo_complemento == 'VALOR':
            nf_comp.natureza_operacao = 'COMPLEMENTAÇÃO DE VALOR'
        else:
            nf_comp.natureza_operacao = 'COMPLEMENTAÇÃO DE QUANTIDADE'
        nf_comp.save()

        # Grupo NFref de cabeçalho — permitido para finNFe=2 (só é proibido em
        # devolução, finNFe=4, pela regra VC02-14).
        NFeReferenciada.objects.create(
            nota_fiscal=nf_comp,
            chave_acesso_referenciada=chave_orig,
            numero_referenciado=numero_orig,
            data_emissao_referenciada=data_orig,
        )

        for item in itens:
            item.pk          = None
            item.nota_fiscal = nf_comp
            if tipo_complemento == 'VALOR':
                # A mercadoria já saiu/entrou pela nota original — quantidade
                # zero evita duplicar o estoque fiscal. valor_unitario é
                # mantido como referência para o usuário ajustar ao valor a
                # complementar (ItemNotaFiscal.save() trata qtd=0 como vProd
                # = valor_unitario - desconto).
                item.quantidade = 0
            else:
                # Valor já foi acertado comercialmente — valor zero evita
                # duplicar o faturamento/receita. Quantidade é mantida como
                # referência para o usuário ajustar à quantidade física a
                # regularizar no estoque/Siscomex.
                item.valor_unitario = 0
            item.valor_desconto = 0
            item.save()

    if tipo_complemento == 'VALOR':
        msg = (
            f'Rascunho de nota complementar de VALOR criado (NF #{nf_comp.pk}). '
            'Quantidade dos itens zerada automaticamente — ajuste o valor unitário '
            'de cada item para o valor a complementar antes de emitir.'
        )
    else:
        msg = (
            f'Rascunho de nota complementar de QUANTIDADE criado (NF #{nf_comp.pk}). '
            'Valor unitário dos itens zerado automaticamente — ajuste a quantidade '
            'de cada item para a quantidade física a regularizar antes de emitir.'
        )
    messages.info(request, msg)
    return redirect('faturamento:nota_fiscal_update', pk=nf_comp.pk)


@login_required
def nota_fiscal_carta_correcao(request, pk):
    from .services.integranotas import IntegranNotasClient, IntegranNotasError

    empresa = _get_empresa(request)
    nf = get_object_or_404(NotaFiscal, pk=pk, empresa=empresa)

    if nf.status != 'EMITIDA' or not nf.chave_acesso:
        messages.error(request, 'Carta de Correção só pode ser enviada para NF-e autorizada.')
        return redirect('faturamento:nota_fiscal_detail', pk=pk)

    cartas_anteriores = nf.cartas_correcao.all()
    proxima_sequencia = (cartas_anteriores.count() + 1) if cartas_anteriores.exists() else 1

    if request.method == 'POST':
        form = CartaCorrecaoNFeForm(request.POST)
        if form.is_valid():
            config = ConfiguracaoFiscal.objects.filter(empresa=empresa).first()
            if not config or not config.has_token:
                messages.error(request, 'Emitente IntegraNotas não configurado. Peça ao administrador da plataforma para criá-lo (Empresas → Listar).')
                return render(request, 'faturamento/nota_fiscal/carta_correcao_form.html',
                              {'form': form, 'nf': nf, 'cartas': cartas_anteriores, 'proxima_sequencia': proxima_sequencia})
            try:
                client = IntegranNotasClient(config.get_token(), config.ambiente_nfe)
                resultado = client.carta_correcao_nfe(
                    nf.chave_acesso,
                    form.cleaned_data['correcao'],
                    proxima_sequencia,
                )
            except IntegranNotasError as exc:
                messages.error(request, f'Erro ao enviar CC-e [{exc.codigo}]: {exc}')
                return render(request, 'faturamento/nota_fiscal/carta_correcao_form.html',
                              {'form': form, 'nf': nf, 'cartas': cartas_anteriores, 'proxima_sequencia': proxima_sequencia})
            except Exception as exc:
                messages.error(request, f'Falha na comunicação com IntegraNota: {exc}')
                return render(request, 'faturamento/nota_fiscal/carta_correcao_form.html',
                              {'form': form, 'nf': nf, 'cartas': cartas_anteriores, 'proxima_sequencia': proxima_sequencia})

            CartaCorrecaoNFe.objects.create(
                nota_fiscal=nf,
                sequencia=proxima_sequencia,
                correcao=form.cleaned_data['correcao'],
                protocolo=resultado.get('protocolo', '') or resultado.get('numero_protocolo', ''),
                xml_retorno=(
                    resultado.get('xml_carta_correcao', '')
                    or resultado.get('xml_cce', '')
                    or resultado.get('xml', '')
                    or resultado.get('xmlRetorno', '')
                ),
                criado_por=request.user,
            )
            messages.success(request, f'Carta de Correção nº {proxima_sequencia} enviada com sucesso.')
            return redirect('faturamento:nota_fiscal_detail', pk=pk)
    else:
        form = CartaCorrecaoNFeForm()

    return render(request, 'faturamento/nota_fiscal/carta_correcao_form.html', {
        'form': form,
        'nf': nf,
        'cartas': cartas_anteriores,
        'proxima_sequencia': proxima_sequencia,
    })


@login_required
def nfe_cce_print(request, nf_pk, cc_pk):
    """Página de impressão da Carta de Correção (CC-e) da NF-e."""
    empresa = _get_empresa(request)
    nf = get_object_or_404(NotaFiscal, pk=nf_pk, empresa=empresa)
    cc = get_object_or_404(CartaCorrecaoNFe, pk=cc_pk, nota_fiscal=nf)
    return render(request, 'faturamento/nota_fiscal/cce_print.html', {
        'nf': nf,
        'cc': cc,
        'empresa': empresa,
    })


@login_required
def nfe_cce_xml(request, nf_pk, cc_pk):
    """Download do XML da Carta de Correção (CC-e) da NF-e.
    Se xml_retorno estiver vazio, busca na API e cacheia no banco."""
    import base64
    from .services.integranotas import IntegranNotasClient
    empresa = _get_empresa(request)
    nf = get_object_or_404(NotaFiscal, pk=nf_pk, empresa=empresa)
    cc = get_object_or_404(CartaCorrecaoNFe, pk=cc_pk, nota_fiscal=nf)

    xml_b64 = cc.xml_retorno

    # Se não tiver XML salvo, tenta buscar na API
    if not xml_b64 and nf.chave_acesso:
        try:
            config = ConfiguracaoFiscal.objects.filter(empresa=empresa).first()
            if config and config.has_token:
                client = IntegranNotasClient(config.get_token(), config.ambiente_nfe)
                xml_b64 = client.buscar_xml_cce_nfe(nf.chave_acesso, cc.sequencia)
                if xml_b64:
                    cc.xml_retorno = xml_b64
                    cc.save(update_fields=['xml_retorno'])
        except Exception:
            pass

    if not xml_b64:
        messages.error(request, 'XML da CC-e não disponível. A API não retornou o XML para esta correção.')
        return redirect('faturamento:nota_fiscal_detail', pk=nf_pk)

    try:
        xml_bytes = base64.b64decode(xml_b64)
    except Exception:
        xml_bytes = xml_b64.encode('utf-8')

    chave = nf.chave_acesso or f'NF{nf.numero}_{nf.serie}'
    response = HttpResponse(xml_bytes, content_type='application/xml; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="CCe_{chave}_seq{cc.sequencia}.xml"'
    return response


@login_required
def nota_fiscal_inutilizar(request):
    from .services.integranotas import IntegranNotasClient, IntegranNotasError
    from datetime import date

    empresa = _get_empresa(request)
    config = ConfiguracaoFiscal.objects.filter(empresa=empresa).first()

    if request.method == 'POST':
        form = InutilizacaoNFeForm(request.POST)
        if form.is_valid():
            if not config or not config.has_token:
                messages.error(request, 'Emitente IntegraNotas não configurado. Peça ao administrador da plataforma para criá-lo (Empresas → Listar).')
                return render(request, 'faturamento/nota_fiscal/inutilizacao_form.html', {'form': form})
            cnpj_emitente = ''
            if config.certificado_cnpj:
                cnpj_emitente = config.certificado_cnpj.replace('.', '').replace('/', '').replace('-', '')
            if not cnpj_emitente:
                messages.error(request, 'CNPJ da empresa não encontrado na configuração fiscal.')
                return render(request, 'faturamento/nota_fiscal/inutilizacao_form.html', {'form': form})
            try:
                client = IntegranNotasClient(config.get_token(), config.ambiente_nfe)
                resultado = client.inutilizar_nfe(
                    cnpj=cnpj_emitente,
                    serie=form.cleaned_data['serie'],
                    numero_ini=form.cleaned_data['numero_ini'],
                    numero_fim=form.cleaned_data['numero_fim'],
                    justificativa=form.cleaned_data['justificativa'],
                    ano=form.cleaned_data['ano'],
                )
            except IntegranNotasError as exc:
                messages.error(request, f'Erro ao inutilizar [{exc.codigo}]: {exc}')
                return render(request, 'faturamento/nota_fiscal/inutilizacao_form.html', {'form': form})
            except Exception as exc:
                messages.error(request, f'Falha na comunicação com IntegraNota: {exc}')
                return render(request, 'faturamento/nota_fiscal/inutilizacao_form.html', {'form': form})

            InutilizacaoNFe.objects.create(
                empresa=empresa,
                serie=form.cleaned_data['serie'],
                numero_ini=form.cleaned_data['numero_ini'],
                numero_fim=form.cleaned_data['numero_fim'],
                ano=form.cleaned_data['ano'],
                justificativa=form.cleaned_data['justificativa'],
                protocolo=resultado.get('protocolo', '') or resultado.get('numero_protocolo', ''),
                criado_por=request.user,
            )
            messages.success(
                request,
                f'Numeração {form.cleaned_data["numero_ini"]}–{form.cleaned_data["numero_fim"]} '
                f'da série {form.cleaned_data["serie"]} inutilizada com sucesso.'
            )
            return redirect('faturamento:nota_fiscal_list')
    else:
        initial = {'ano': date.today().year}
        if request.GET.get('numero'):
            initial['numero_ini'] = initial['numero_fim'] = request.GET['numero']
        if request.GET.get('serie'):
            initial['serie'] = request.GET['serie']
        form = InutilizacaoNFeForm(initial=initial)

    historico = InutilizacaoNFe.objects.filter(empresa=empresa).order_by('-criado_em')[:20]
    return render(request, 'faturamento/nota_fiscal/inutilizacao_form.html', {
        'form': form,
        'historico': historico,
    })


@login_required
def nota_fiscal_pdf(request, pk):
    from decimal import Decimal as _Dec, ROUND_HALF_UP
    from django.template.loader import get_template
    from xhtml2pdf import pisa
    from django.http import HttpResponse
    import io

    empresa = _get_empresa(request)
    nf = get_object_or_404(
        NotaFiscal.objects.select_related('transportadora'),
        pk=pk, empresa=empresa,
    )

    # Transportadora: injeta em memória se transp_nome vazio mas FK setado
    if nf.transportadora and not (nf.transp_nome or '').strip():
        t = nf.transportadora
        nf.transp_nome = t.razao_social or ''
        nf.transp_cnpj = t.cnpj or ''
        nf.transp_ie = t.inscricao_estadual or ''
        nf.transp_endereco = ', '.join(p for p in [t.logradouro, t.numero, t.complemento] if p).strip()
        nf.transp_municipio = t.cidade or ''
        nf.transp_uf = t.uf or ''
        nf.transp_rntc = t.rntc or ''

    # Conversão de unidade: calcula em memória para itens sem qty_tributavel
    itens = list(
        nf.itens.select_related('produto__unidade_medida', 'produto__unidade_venda')
        .order_by('numero_item')
    )
    for _item in itens:
        if float(_item.quantidade_tributavel or 0) == 0 and _item.produto:
            _prod = _item.produto
            _fator = float(_prod.fator_conversao or 1)
            _un_med = (_prod.unidade_medida.sigla if _prod.unidade_medida_id else '').strip()
            _un_vnd = (_prod.unidade_venda.sigla if _prod.unidade_venda_id else '').strip()
            if _fator > 1 and _un_med and _un_med != _un_vnd:
                _item.quantidade_tributavel = (_item.quantidade * _Dec(str(_fator))).quantize(_Dec('0.0001'), rounding=ROUND_HALF_UP)
                _item.unidade_tributavel = _un_med
                _item.valor_unitario_tributavel = (_item.valor_unitario / _Dec(str(_fator))).quantize(_Dec('0.0001'), rounding=ROUND_HALF_UP)

    template = get_template('faturamento/nota_fiscal/pdf.html')
    html = template.render({'nf': nf, 'empresa': empresa, 'itens': itens})
    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(html.encode('utf-8')), result)
    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="NF_{nf.numero}_{nf.serie}.pdf"'
        return response
    return HttpResponse('Erro ao gerar PDF', status=500)


# ─────────────────────────── Invoice de Exportação ───────────────────────────

@login_required
def invoice_list(request):
    empresa = _get_empresa(request)
    if not empresa:
        return redirect('dashboard:index')

    qs = InvoiceExportacao.objects.filter(empresa=empresa).select_related('cliente', 'booking')

    status_filter = request.GET.get('status', '')
    q = request.GET.get('q', '')
    data_ini = request.GET.get('data_ini', '')
    data_fim = request.GET.get('data_fim', '')

    if status_filter:
        qs = qs.filter(status=status_filter)
    if q:
        qs = qs.filter(Q(cliente__razao_social__icontains=q) | Q(numero__icontains=q))
    if data_ini:
        qs = qs.filter(data_emissao__gte=data_ini)
    if data_fim:
        qs = qs.filter(data_emissao__lte=data_fim)

    qs = qs.order_by('-data_emissao')
    page_obj, per_page, per_page_options = paginate(request, qs)

    return render(request, 'faturamento/invoice/list.html', {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'q': q,
        'data_ini': data_ini,
        'data_fim': data_fim,
        'status_choices': InvoiceExportacao.STATUS,
        'per_page': per_page,
        'per_page_options': per_page_options,
    })


@login_required
def invoice_create(request):
    empresa = _get_empresa(request)
    if not empresa:
        return redirect('dashboard:index')

    booking_id = request.GET.get('booking')
    pedido_id = request.GET.get('pedido')
    initial = {}
    pedido_origem = None
    pedido_items_json = '[]'

    if booking_id:
        from exportacao.models import Booking
        try:
            b = Booking.objects.get(pk=booking_id, empresa=empresa)
            initial['booking'] = b
            if b.porto_origem:
                initial['porto_embarque'] = str(b.porto_origem)
            if b.porto_destino:
                initial['porto_destino'] = str(b.porto_destino)
            if b.data_embarque_previsto:
                initial['data_embarque_previsto'] = b.data_embarque_previsto
            if b.solicitacao and b.solicitacao.cliente:
                initial['cliente'] = b.solicitacao.cliente
        except Exception:
            pass

    if pedido_id:
        from vendas.models import PedidoVenda
        import json as _json
        try:
            pedido_origem = PedidoVenda.objects.get(pk=pedido_id, empresa=empresa)
            initial['cliente'] = pedido_origem.cliente
            initial['moeda'] = pedido_origem.moeda
            if pedido_origem.taxa_cambio:
                initial['taxa_cambio'] = pedido_origem.taxa_cambio
            if pedido_origem.condicao_pagamento:
                initial['condicao_pagamento'] = pedido_origem.condicao_pagamento
            if pedido_origem.valor_frete:
                initial['valor_frete'] = pedido_origem.valor_frete
            if pedido_origem.observacoes:
                initial['observacoes'] = pedido_origem.observacoes
            pedido_items_json = _json.dumps([
                {
                    'descricao': item.descricao,
                    'quantidade': str(item.quantidade),
                    'unidade': item.unidade,
                    'valor_unitario_fob': str(item.preco_unitario),
                    'peso_bruto_kg': '0.000',
                    'peso_liquido_kg': '0.000',
                }
                for item in pedido_origem.itens.all()
            ])
        except Exception:
            pass

    if request.method == 'POST':
        form = InvoiceExportacaoForm(request.POST, empresa=empresa)
        formset = ItemInvoiceFormSet(request.POST, prefix='itens')
        if form.is_valid() and formset.is_valid():
            invoice = form.save(user=request.user)
            invoice.numero = _gerar_numero_invoice(empresa)
            invoice.save(update_fields=['numero'])
            formset.instance = invoice
            formset.save()
            invoice.calcular_totais()
            # Vincula pedido à invoice se veio de um pedido
            if pedido_id:
                from vendas.models import PedidoVenda
                try:
                    ped = PedidoVenda.objects.get(pk=pedido_id, empresa=empresa)
                    if not ped.invoice_id:
                        ped.invoice = invoice
                        ped.save(update_fields=['invoice'])
                except Exception:
                    pass
            messages.success(request, f'Invoice {invoice.numero} criada com sucesso.')
            return redirect('faturamento:invoice_detail', pk=invoice.pk)
    else:
        config = ConfiguracaoFiscal.objects.filter(empresa=empresa).first()
        if config and config.observacoes_padrao_invoice:
            initial.setdefault('observacoes', config.observacoes_padrao_invoice)
        form = InvoiceExportacaoForm(empresa=empresa, initial=initial)
        formset = ItemInvoiceFormSet(prefix='itens')

    return render(request, 'faturamento/invoice/form.html', {
        'form': form,
        'formset': formset,
        'title': 'Nova Invoice de Exportação',
        'pedido_origem': pedido_origem,
        'pedido_items_json': pedido_items_json,
    })


def _gerar_numero_invoice(empresa):
    ano = timezone.now().year
    ultimo = InvoiceExportacao.objects.filter(
        empresa=empresa,
        numero__startswith=f'INV-{ano}-',
    ).order_by('-numero').first()
    if ultimo and ultimo.numero:
        try:
            seq = int(ultimo.numero.split('-')[-1]) + 1
        except ValueError:
            seq = 1
    else:
        seq = 1
    return f'INV-{ano}-{seq:04d}'


@login_required
def invoice_detail(request, pk):
    empresa = _get_empresa(request)
    invoice = get_object_or_404(InvoiceExportacao, pk=pk, empresa=empresa)

    from adiantamentos.models import AdiantamentoInternacional, DescontoAdiantamento
    adiantamentos_ativos = AdiantamentoInternacional.objects.filter(
        empresa=empresa,
        cliente=invoice.cliente,
        status__in=['PENDENTE_EMBARQUE', 'EM_ANDAMENTO', 'PARCIALMENTE_QUITADO'],
    )
    desconto_adiantamento = DescontoAdiantamento.objects.filter(invoice=invoice, status='APLICADO').select_related('adiantamento').first()

    return render(request, 'faturamento/invoice/detail.html', {
        'invoice': invoice,
        'adiantamentos_ativos': adiantamentos_ativos,
        'desconto_adiantamento': desconto_adiantamento,
    })


@login_required
def invoice_update(request, pk):
    empresa = _get_empresa(request)
    invoice = get_object_or_404(InvoiceExportacao, pk=pk, empresa=empresa)

    if invoice.status == 'CANCELADA':
        messages.error(request, 'Invoices canceladas não podem ser editadas.')
        return redirect('faturamento:invoice_detail', pk=pk)

    editing_emitida = invoice.status == 'EMITIDA'

    if request.method == 'POST':
        form = InvoiceExportacaoForm(request.POST, instance=invoice, empresa=empresa)
        formset = ItemInvoiceFormSet(request.POST, instance=invoice, prefix='itens')
        if form.is_valid() and formset.is_valid():
            form.save(user=request.user)
            formset.save()
            invoice.calcular_totais()
            messages.success(request, 'Invoice atualizada com sucesso.')
            return redirect('faturamento:invoice_detail', pk=pk)
    else:
        form = InvoiceExportacaoForm(instance=invoice, empresa=empresa)
        formset = ItemInvoiceFormSet(instance=invoice, prefix='itens')

    return render(request, 'faturamento/invoice/form.html', {
        'form': form,
        'formset': formset,
        'invoice': invoice,
        'title': f'Editar {invoice.numero}',
        'editing_emitida': editing_emitida,
        'pedido_items_json': '[]',
    })


@login_required
@require_POST
def invoice_emitir(request, pk):
    empresa = _get_empresa(request)
    invoice = get_object_or_404(InvoiceExportacao, pk=pk, empresa=empresa)

    if invoice.status != 'RASCUNHO':
        messages.error(request, 'Apenas invoices em RASCUNHO podem ser emitidas.')
        return redirect('faturamento:invoice_detail', pk=pk)

    if invoice.booking and invoice.booking.status != 'CONFIRMADO':
        messages.error(request, 'O booking vinculado precisa estar CONFIRMADO (RN-07).')
        return redirect('faturamento:invoice_detail', pk=pk)

    if not invoice.itens.exists():
        messages.error(request, 'Adicione pelo menos um item antes de emitir.')
        return redirect('faturamento:invoice_detail', pk=pk)

    invoice.status = 'EMITIDA'
    invoice.atualizado_por = request.user
    invoice.save(update_fields=['status', 'atualizado_por'])
    _sync_pedido_de_documento(invoice=invoice)
    messages.success(request, f'{invoice.numero} emitida com sucesso.')
    return redirect('faturamento:invoice_detail', pk=pk)


@login_required
@require_POST
def invoice_cancelar(request, pk):
    empresa = _get_empresa(request)
    invoice = get_object_or_404(InvoiceExportacao, pk=pk, empresa=empresa)

    if invoice.status == 'CANCELADA':
        messages.warning(request, 'Invoice já está cancelada.')
        return redirect('faturamento:invoice_detail', pk=pk)

    invoice.status = 'CANCELADA'
    invoice.atualizado_por = request.user
    invoice.save(update_fields=['status', 'atualizado_por'])
    _sync_pedido_de_documento(invoice=invoice)
    messages.success(request, f'{invoice.numero} cancelada.')
    return redirect('faturamento:invoice_detail', pk=pk)


@login_required
def invoice_devolucao_registrar(request, pk):
    """Registra devolução de venda (entrada de estoque) para uma Invoice de exportação emitida.

    Para NF-e de mercado interno já existe um fluxo fiscal completo de devolução
    (`nota_fiscal_devolucao`, que gera uma NF-e reversa de verdade — ver
    `_registrar_entrada_devolucao_venda` para a baixa de estoque correspondente).
    Para Invoice de exportação não existe documento fiscal equivalente, então esta
    view registra só a entrada de estoque. `ItemInvoice` não referencia
    `produtos.Produto` diretamente, então a devolução fica aberta a qualquer
    produto da empresa (não há como restringir pelos itens da invoice).
    """
    empresa = _get_empresa(request)
    invoice = get_object_or_404(InvoiceExportacao, pk=pk, empresa=empresa)

    if invoice.status != 'EMITIDA':
        messages.error(request, 'Só é possível registrar devolução de invoices EMITIDAS.')
        return redirect('faturamento:invoice_detail', pk=pk)

    if request.method == 'POST':
        form = DevolucaoVendaForm(request.POST, empresa=empresa)
        if form.is_valid():
            from estoque.services import criar_movimentacao
            criar_movimentacao(
                empresa=empresa,
                tipo='ENTRADA',
                origem='DEVOLUCAO_VENDA',
                quantidade=form.cleaned_data['quantidade'],
                usuario=request.user,
                lote=form.cleaned_data.get('lote'),
                produto=form.cleaned_data['produto'],
                documento=str(invoice.numero or ''),
                observacao=form.cleaned_data['justificativa'],
            )
            messages.success(request, 'Devolução registrada e estoque atualizado.')
            return redirect('faturamento:invoice_detail', pk=pk)
    else:
        form = DevolucaoVendaForm(empresa=empresa)

    return render(request, 'faturamento/devolucao_venda/form.html', {
        'form': form, 'documento': invoice,
    })


@login_required
def invoice_pdf(request, pk):
    empresa = _get_empresa(request)
    invoice = get_object_or_404(InvoiceExportacao, pk=pk, empresa=empresa)

    from django.template.loader import get_template
    from django.http import HttpResponse
    from playwright.sync_api import sync_playwright

    from adiantamentos.models import DescontoAdiantamento
    desconto_adiantamento = DescontoAdiantamento.objects.filter(invoice=invoice, status='APLICADO').select_related('adiantamento').first()

    logo_url = request.build_absolute_uri(empresa.logo.url) if empresa.logo else None
    empresa_nome = empresa.razao_social or empresa.nome or ''
    empresa_inicial = empresa_nome[:1].upper() or 'E'

    template = get_template('faturamento/invoice/pdf.html')
    html = template.render({
        'invoice': invoice,
        'empresa': empresa,
        'desconto_adiantamento': desconto_adiantamento,
        'logo_url': logo_url,
        'empresa_inicial': empresa_inicial,
    })

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html, wait_until='networkidle')
        pdf_bytes = page.pdf(format='A4', print_background=True, prefer_css_page_size=True)
        browser.close()

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{invoice.numero}.pdf"'
    return response


# ─────────────────────────── Packing List ───────────────────────────

@login_required
def packing_list_list(request):
    empresa = _get_empresa(request)
    if not empresa:
        return redirect('dashboard:index')

    qs = PackingList.objects.filter(empresa=empresa).select_related('invoice', 'invoice__cliente')

    status_filter = request.GET.get('status', '')
    q = request.GET.get('q', '')

    if status_filter:
        qs = qs.filter(status=status_filter)
    if q:
        qs = qs.filter(Q(numero__icontains=q) | Q(invoice__numero__icontains=q))

    qs = qs.order_by('-data_emissao')
    page_obj, per_page, per_page_options = paginate(request, qs)

    return render(request, 'faturamento/packing_list/list.html', {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'q': q,
        'status_choices': PackingList.STATUS,
        'per_page': per_page,
        'per_page_options': per_page_options,
    })


@login_required
def packing_list_create(request):
    empresa = _get_empresa(request)
    if not empresa:
        return redirect('dashboard:index')

    invoice_id = request.GET.get('invoice')
    initial = {}
    if invoice_id:
        try:
            inv = InvoiceExportacao.objects.get(pk=invoice_id, empresa=empresa)
            initial['invoice'] = inv
        except InvoiceExportacao.DoesNotExist:
            pass

    if request.method == 'POST':
        form = PackingListForm(request.POST, empresa=empresa)
        formset = ItemPackingListFormSet(request.POST, prefix='itens')
        if form.is_valid() and formset.is_valid():
            pl = form.save(user=request.user)
            pl.numero = _gerar_numero_pl(empresa)
            pl.save(update_fields=['numero'])
            formset.instance = pl
            items = formset.save(commit=False)
            for idx, item in enumerate(items, start=1):
                item.ordem = idx
                item.save()
            for obj in formset.deleted_objects:
                obj.delete()
            messages.success(request, f'Packing List {pl.numero} criado com sucesso.')
            return redirect('faturamento:packing_list_detail', pk=pl.pk)
    else:
        form = PackingListForm(empresa=empresa, initial=initial)
        formset = ItemPackingListFormSet(prefix='itens')

    return render(request, 'faturamento/packing_list/form.html', {
        'form': form,
        'formset': formset,
        'title': 'Novo Packing List',
    })


def _gerar_numero_pl(empresa):
    ano = timezone.now().year
    ultimo = PackingList.objects.filter(
        empresa=empresa,
        numero__startswith=f'PL-{ano}-',
    ).order_by('-numero').first()
    if ultimo and ultimo.numero:
        try:
            seq = int(ultimo.numero.split('-')[-1]) + 1
        except ValueError:
            seq = 1
    else:
        seq = 1
    return f'PL-{ano}-{seq:04d}'


@login_required
def packing_list_detail(request, pk):
    empresa = _get_empresa(request)
    pl = get_object_or_404(PackingList, pk=pk, empresa=empresa)
    return render(request, 'faturamento/packing_list/detail.html', {'pl': pl})


@login_required
def packing_list_update(request, pk):
    empresa = _get_empresa(request)
    pl = get_object_or_404(PackingList, pk=pk, empresa=empresa)

    if pl.status != 'RASCUNHO':
        messages.error(request, 'Apenas Packing Lists em RASCUNHO podem ser editados.')
        return redirect('faturamento:packing_list_detail', pk=pk)

    if request.method == 'POST':
        form = PackingListForm(request.POST, instance=pl, empresa=empresa)
        formset = ItemPackingListFormSet(request.POST, instance=pl, prefix='itens')
        if form.is_valid() and formset.is_valid():
            form.save(user=request.user)
            items = formset.save(commit=False)
            for idx, item in enumerate(items, start=1):
                item.ordem = idx
                item.save()
            for obj in formset.deleted_objects:
                obj.delete()
            messages.success(request, 'Packing List atualizado.')
            return redirect('faturamento:packing_list_detail', pk=pk)
    else:
        form = PackingListForm(instance=pl, empresa=empresa)
        formset = ItemPackingListFormSet(instance=pl, prefix='itens')

    return render(request, 'faturamento/packing_list/form.html', {
        'form': form,
        'formset': formset,
        'pl': pl,
        'title': f'Editar {pl.numero}',
    })


@login_required
@require_POST
def packing_list_emitir(request, pk):
    empresa = _get_empresa(request)
    pl = get_object_or_404(PackingList, pk=pk, empresa=empresa)

    if pl.status != 'RASCUNHO':
        messages.error(request, 'Apenas Packing Lists em RASCUNHO podem ser emitidos.')
        return redirect('faturamento:packing_list_detail', pk=pk)

    pl.status = 'EMITIDO'
    pl.atualizado_por = request.user
    pl.save(update_fields=['status', 'atualizado_por'])
    messages.success(request, f'{pl.numero} emitido com sucesso.')
    return redirect('faturamento:packing_list_detail', pk=pk)


@login_required
def packing_list_pdf(request, pk):
    empresa = _get_empresa(request)
    pl = get_object_or_404(PackingList, pk=pk, empresa=empresa)

    from django.template.loader import get_template
    from xhtml2pdf import pisa
    from django.http import HttpResponse
    import io

    template = get_template('faturamento/packing_list/pdf.html')
    html = template.render({'pl': pl, 'empresa': empresa})
    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(html.encode('utf-8')), result)
    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{pl.numero}.pdf"'
        return response
    return HttpResponse('Erro ao gerar PDF', status=500)


# ─────────────────────────── Instrução de Embarque ───────────────────────────

@login_required
def instrucao_embarque_list(request):
    empresa = _get_empresa(request)
    if not empresa:
        return redirect('dashboard:index')

    qs = InstrucaoEmbarque.objects.filter(empresa=empresa).select_related('invoice', 'invoice__cliente')

    status_filter = request.GET.get('status', '')
    q = request.GET.get('q', '')

    if status_filter:
        qs = qs.filter(status=status_filter)
    if q:
        qs = qs.filter(Q(numero__icontains=q) | Q(invoice__numero__icontains=q))

    qs = qs.order_by('-data_emissao')
    page_obj, per_page, per_page_options = paginate(request, qs)

    return render(request, 'faturamento/instrucao_embarque/list.html', {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'q': q,
        'status_choices': InstrucaoEmbarque.STATUS,
        'per_page': per_page,
        'per_page_options': per_page_options,
    })


@login_required
def instrucao_embarque_create(request):
    empresa = _get_empresa(request)
    if not empresa:
        return redirect('dashboard:index')

    invoice_id = request.GET.get('invoice')
    initial = {}
    if invoice_id:
        try:
            inv = InvoiceExportacao.objects.select_related('cliente').get(pk=invoice_id, empresa=empresa)
            initial['invoice'] = inv
            endereco_linha = ', '.join(filter(None, [empresa.endereco, empresa.cidade and f'{empresa.cidade} - {empresa.uf}']))
            initial['shipper'] = '\n'.join(filter(None, [
                empresa.razao_social or empresa.nome,
                endereco_linha,
                f'CNPJ: {empresa.cnpj}' if empresa.cnpj else '',
            ]))
            if inv.cliente:
                initial['consignee'] = inv.cliente.razao_social
        except InvoiceExportacao.DoesNotExist:
            pass

    if request.method == 'POST':
        form = InstrucaoEmbarqueForm(request.POST, empresa=empresa)
        if form.is_valid():
            ie = form.save(user=request.user)
            ie.numero = _gerar_numero_ie(empresa)
            ie.save(update_fields=['numero'])
            messages.success(request, f'Instrução de Embarque {ie.numero} criada com sucesso.')
            return redirect('faturamento:instrucao_embarque_detail', pk=ie.pk)
    else:
        form = InstrucaoEmbarqueForm(empresa=empresa, initial=initial)

    return render(request, 'faturamento/instrucao_embarque/form.html', {
        'form': form,
        'title': 'Nova Instrução de Embarque',
    })


def _gerar_numero_ie(empresa):
    ano = timezone.now().year
    ultimo = InstrucaoEmbarque.objects.filter(
        empresa=empresa,
        numero__startswith=f'SI-{ano}-',
    ).order_by('-numero').first()
    if ultimo and ultimo.numero:
        try:
            seq = int(ultimo.numero.split('-')[-1]) + 1
        except ValueError:
            seq = 1
    else:
        seq = 1
    return f'SI-{ano}-{seq:04d}'


@login_required
def instrucao_embarque_detail(request, pk):
    empresa = _get_empresa(request)
    ie = get_object_or_404(InstrucaoEmbarque, pk=pk, empresa=empresa)
    return render(request, 'faturamento/instrucao_embarque/detail.html', {'ie': ie})


@login_required
def instrucao_embarque_update(request, pk):
    empresa = _get_empresa(request)
    ie = get_object_or_404(InstrucaoEmbarque, pk=pk, empresa=empresa)

    if ie.status != 'RASCUNHO':
        messages.error(request, 'Apenas Instruções de Embarque em RASCUNHO podem ser editadas.')
        return redirect('faturamento:instrucao_embarque_detail', pk=pk)

    if request.method == 'POST':
        form = InstrucaoEmbarqueForm(request.POST, instance=ie, empresa=empresa)
        if form.is_valid():
            form.save(user=request.user)
            messages.success(request, 'Instrução de Embarque atualizada.')
            return redirect('faturamento:instrucao_embarque_detail', pk=pk)
    else:
        form = InstrucaoEmbarqueForm(instance=ie, empresa=empresa)

    return render(request, 'faturamento/instrucao_embarque/form.html', {
        'form': form,
        'ie': ie,
        'title': f'Editar {ie.numero}',
    })


@login_required
@require_POST
def instrucao_embarque_emitir(request, pk):
    empresa = _get_empresa(request)
    ie = get_object_or_404(InstrucaoEmbarque, pk=pk, empresa=empresa)

    if ie.status != 'RASCUNHO':
        messages.error(request, 'Apenas Instruções de Embarque em RASCUNHO podem ser emitidas.')
        return redirect('faturamento:instrucao_embarque_detail', pk=pk)

    ie.status = 'EMITIDA'
    ie.atualizado_por = request.user
    ie.save(update_fields=['status', 'atualizado_por'])
    messages.success(request, f'{ie.numero} emitida com sucesso.')
    return redirect('faturamento:instrucao_embarque_detail', pk=pk)


@login_required
def instrucao_embarque_pdf(request, pk):
    empresa = _get_empresa(request)
    ie = get_object_or_404(InstrucaoEmbarque, pk=pk, empresa=empresa)

    from django.template.loader import get_template
    from xhtml2pdf import pisa
    from django.http import HttpResponse
    import io

    template = get_template('faturamento/instrucao_embarque/pdf.html')
    html = template.render({'ie': ie, 'empresa': empresa})
    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(html.encode('utf-8')), result)
    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{ie.numero}.pdf"'
        return response
    return HttpResponse('Erro ao gerar PDF', status=500)


# ─────────────────────────── Minuta de Conhecimento ───────────────────────────

@login_required
def minuta_list(request):
    empresa = _get_empresa(request)
    if not empresa:
        return redirect('dashboard:index')

    qs = Minuta.objects.filter(empresa=empresa).select_related('invoice', 'invoice__cliente')

    status_filter = request.GET.get('status', '')
    q = request.GET.get('q', '')

    if status_filter:
        qs = qs.filter(status=status_filter)
    if q:
        qs = qs.filter(Q(numero__icontains=q) | Q(invoice__numero__icontains=q))

    qs = qs.order_by('-data_emissao')
    page_obj, per_page, per_page_options = paginate(request, qs)

    return render(request, 'faturamento/minuta/list.html', {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'q': q,
        'status_choices': Minuta.STATUS,
        'per_page': per_page,
        'per_page_options': per_page_options,
    })


@login_required
def minuta_create(request):
    empresa = _get_empresa(request)
    if not empresa:
        return redirect('dashboard:index')

    invoice_id = request.GET.get('invoice')
    initial = {}
    if invoice_id:
        try:
            inv = InvoiceExportacao.objects.select_related('cliente').get(pk=invoice_id, empresa=empresa)
            initial['invoice'] = inv
            endereco_linha = ', '.join(filter(None, [empresa.endereco, empresa.cidade and f'{empresa.cidade} - {empresa.uf}']))
            initial['shipper'] = '\n'.join(filter(None, [
                empresa.razao_social or empresa.nome,
                endereco_linha,
                f'CNPJ: {empresa.cnpj}' if empresa.cnpj else '',
            ]))
            if inv.cliente:
                initial['consignee'] = inv.cliente.razao_social
            cidade_uf = f'{empresa.cidade}/{empresa.uf}' if (empresa.cidade and empresa.uf) else (empresa.cidade or '')
            if cidade_uf:
                initial['local_emissao'] = cidade_uf
        except InvoiceExportacao.DoesNotExist:
            pass

    if request.method == 'POST':
        form = MinutaForm(request.POST, empresa=empresa)
        if form.is_valid():
            mn = form.save(user=request.user)
            mn.numero = _gerar_numero_mn(empresa)
            mn.save(update_fields=['numero'])
            messages.success(request, f'Minuta {mn.numero} criada com sucesso.')
            return redirect('faturamento:minuta_detail', pk=mn.pk)
    else:
        form = MinutaForm(empresa=empresa, initial=initial)

    return render(request, 'faturamento/minuta/form.html', {
        'form': form,
        'title': 'Nova Minuta de Conhecimento',
    })


def _gerar_numero_mn(empresa):
    ano = timezone.now().year
    ultimo = Minuta.objects.filter(
        empresa=empresa,
        numero__startswith=f'MN-{ano}-',
    ).order_by('-numero').first()
    if ultimo and ultimo.numero:
        try:
            seq = int(ultimo.numero.split('-')[-1]) + 1
        except ValueError:
            seq = 1
    else:
        seq = 1
    return f'MN-{ano}-{seq:04d}'


@login_required
def minuta_detail(request, pk):
    empresa = _get_empresa(request)
    mn = get_object_or_404(Minuta, pk=pk, empresa=empresa)
    return render(request, 'faturamento/minuta/detail.html', {'mn': mn})


@login_required
def minuta_update(request, pk):
    empresa = _get_empresa(request)
    mn = get_object_or_404(Minuta, pk=pk, empresa=empresa)

    if mn.status != 'RASCUNHO':
        messages.error(request, 'Apenas Minutas em RASCUNHO podem ser editadas.')
        return redirect('faturamento:minuta_detail', pk=pk)

    if request.method == 'POST':
        form = MinutaForm(request.POST, instance=mn, empresa=empresa)
        if form.is_valid():
            form.save(user=request.user)
            messages.success(request, 'Minuta atualizada.')
            return redirect('faturamento:minuta_detail', pk=pk)
    else:
        form = MinutaForm(instance=mn, empresa=empresa)

    return render(request, 'faturamento/minuta/form.html', {
        'form': form,
        'mn': mn,
        'title': f'Editar {mn.numero}',
    })


@login_required
@require_POST
def minuta_emitir(request, pk):
    empresa = _get_empresa(request)
    mn = get_object_or_404(Minuta, pk=pk, empresa=empresa)

    if mn.status != 'RASCUNHO':
        messages.error(request, 'Apenas Minutas em RASCUNHO podem ser emitidas.')
        return redirect('faturamento:minuta_detail', pk=pk)

    mn.status = 'EMITIDA'
    mn.atualizado_por = request.user
    mn.save(update_fields=['status', 'atualizado_por'])
    messages.success(request, f'{mn.numero} emitida com sucesso.')
    return redirect('faturamento:minuta_detail', pk=pk)


@login_required
def minuta_pdf(request, pk):
    empresa = _get_empresa(request)
    mn = get_object_or_404(Minuta, pk=pk, empresa=empresa)

    from django.template.loader import get_template
    from xhtml2pdf import pisa
    from django.http import HttpResponse
    import io

    template = get_template('faturamento/minuta/pdf.html')
    html = template.render({'mn': mn, 'empresa': empresa})
    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(html.encode('utf-8')), result)
    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{mn.numero}.pdf"'
        return response
    return HttpResponse('Erro ao gerar PDF', status=500)


# ─────────────────────────── Configuração Fiscal ───────────────────────────

@login_required
def configuracao_fiscal(request):
    from datetime import timedelta
    from empresas.forms import EmpresaFiscalForm

    empresa = _get_empresa(request)
    if not empresa:
        return redirect('dashboard:index')

    config, _ = ConfiguracaoFiscal.objects.get_or_create(empresa=empresa)

    if request.method == 'POST':
        form = ConfiguracaoFiscalForm(request.POST, instance=config)
        empresa_form = EmpresaFiscalForm(request.POST, instance=empresa)
        if form.is_valid() and empresa_form.is_valid():
            form.save()
            empresa_form.save()
            messages.success(request, 'Configuração fiscal salva com sucesso.')
            return redirect('faturamento:configuracao')
    else:
        form = ConfiguracaoFiscalForm(instance=config)
        empresa_form = EmpresaFiscalForm(instance=empresa)

    today = timezone.now().date()
    cert_expirado = config.certificado_validade and config.certificado_validade < today
    cert_expira_breve = (
        config.certificado_validade
        and not cert_expirado
        and config.certificado_validade <= today + timedelta(days=30)
    )

    return render(request, 'faturamento/configuracao.html', {
        'form': form,
        'config': config,
        'empresa_form': empresa_form,
        'cert_form': CertificadoDigitalForm(),
        'cert_expirado': cert_expirado,
        'cert_expira_breve': cert_expira_breve,
        'emitente_configurado': bool(config.get_token()),
    })


@login_required
@require_POST
def certificado_upload(request):
    import base64
    from .services.integranotas import parse_pfx, IntegranNotasClient, IntegranNotasError

    empresa = _get_empresa(request)
    if not empresa:
        return redirect('dashboard:index')

    config, _ = ConfiguracaoFiscal.objects.get_or_create(empresa=empresa)
    form = CertificadoDigitalForm(request.POST, request.FILES)

    if form.is_valid():
        arquivo = form.cleaned_data['arquivo_pfx']
        senha = form.cleaned_data['senha_certificado']
        pfx_bytes = arquivo.read()
        try:
            info = parse_pfx(pfx_bytes, senha)
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect('faturamento:configuracao')
        except Exception as exc:
            messages.error(request, f'Erro inesperado ao processar certificado: {exc}')
            return redirect('faturamento:configuracao')

        if not config.get_token():
            messages.error(request, 'Emitente IntegraNotas não configurado. Peça ao administrador da plataforma para criá-lo (Empresas → Listar) antes de importar o certificado.')
            return redirect('faturamento:configuracao')

        try:
            client = IntegranNotasClient(token=config.get_token(), ambiente=config.ambiente_nfe)
            certificado_b64 = base64.b64encode(pfx_bytes).decode('ascii')
            client.enviar_certificado(certificado_b64, senha)
        except IntegranNotasError as exc:
            messages.error(request, f'IntegraNotas recusou o certificado [{exc.codigo}]: {exc}')
            return redirect('faturamento:configuracao')
        except Exception as exc:
            messages.error(request, f'Erro de comunicação com a IntegraNotas: {exc}')
            return redirect('faturamento:configuracao')

        config.certificado_pfx = pfx_bytes
        config.senha_certificado = senha
        config.certificado_validade = info['validade']
        config.certificado_cnpj = info['cnpj']
        config.certificado_arquivo_nome = arquivo.name
        config.save()
        messages.success(
            request,
            f'Certificado "{arquivo.name}" importado e enviado à IntegraNotas. '
            f'Válido até {info["validade"].strftime("%d/%m/%Y")}.'
        )
    else:
        for field_errors in form.errors.values():
            for error in field_errors:
                messages.error(request, error)

    return redirect('faturamento:configuracao')


@login_required
@require_POST
def certificado_consultar(request):
    """Consulta na IntegraNotas os dados do certificado configurado no emitente."""
    from .services.integranotas import IntegranNotasClient, IntegranNotasError

    empresa = _get_empresa(request)
    if not empresa:
        return redirect('dashboard:index')

    config, _ = ConfiguracaoFiscal.objects.get_or_create(empresa=empresa)
    if not config.get_token():
        messages.error(request, 'Emitente IntegraNotas não configurado. Peça ao administrador da plataforma para criá-lo (Empresas → Listar) antes de consultar o certificado.')
        return redirect('faturamento:configuracao')

    try:
        client = IntegranNotasClient(token=config.get_token(), ambiente=config.ambiente_nfe)
        data = client.consultar_certificado()
        if data.get('sucesso'):
            messages.success(
                request,
                f"IntegraNotas: {data.get('mensagem', 'Certificado localizado.')} "
                f"Válido até {data.get('validade', '—')}."
            )
        else:
            messages.warning(request, f"IntegraNotas: {data.get('mensagem', 'Certificado não localizado no emitente.')}")
    except IntegranNotasError as exc:
        messages.error(request, f'Erro ao consultar certificado [{exc.codigo}]: {exc}')
    except Exception as exc:
        messages.error(request, f'Erro de comunicação com a IntegraNotas: {exc}')

    return redirect('faturamento:configuracao')


@login_required
@require_POST
def certificado_delete(request):
    """Remove o certificado digital da configuração fiscal da empresa."""
    empresa = _get_empresa(request)
    if not empresa:
        return redirect('dashboard:index')
    try:
        config = empresa.configuracao_fiscal
        config.certificado_pfx = b''
        config.senha_certificado = ''
        config.certificado_validade = None
        config.certificado_cnpj = ''
        config.certificado_arquivo_nome = ''
        config.save()
        messages.success(request, 'Certificado digital removido com sucesso.')
    except Exception:
        messages.info(request, 'Nenhum certificado configurado para remover.')
    return redirect('faturamento:configuracao')


# ─────────────────────────── Distribuição de DF-e ───────────────────────────

_SOMENTE_DIGITOS_RE = re.compile(r'\D')


@login_required
def dfe_list(request):
    """Lista os documentos descobertos via Distribuição de DF-e, com filtros."""
    empresa = _get_empresa(request)
    if not empresa:
        return redirect('dashboard:index')

    config, _ = ConfiguracaoFiscal.objects.get_or_create(empresa=empresa)

    cnpj_emitente = request.GET.get('cnpj_emitente', '').strip()
    chave_acesso = request.GET.get('chave_acesso', '').strip()
    if 'tipo' in request.GET:
        tipo = request.GET.get('tipo', '').strip()
    else:
        # Sem filtro explícito na URL: entra mostrando só NF-e (resNFe), não os resEvento.
        tipo = 'resNFe'
    situacao = request.GET.get('situacao', '').strip()
    data_ini = request.GET.get('data_ini', '').strip()
    data_fim = request.GET.get('data_fim', '').strip()

    qs = DfeRecebido.objects.filter(empresa=empresa)
    if cnpj_emitente:
        digitos = _SOMENTE_DIGITOS_RE.sub('', cnpj_emitente)
        if digitos:
            qs = qs.filter(Q(cnpj_emitente__icontains=digitos) | Q(nome_emitente__icontains=cnpj_emitente))
        else:
            qs = qs.filter(nome_emitente__icontains=cnpj_emitente)
    if chave_acesso:
        qs = qs.filter(chave_acesso__icontains=_SOMENTE_DIGITOS_RE.sub('', chave_acesso))
    if tipo:
        qs = qs.filter(schema=tipo)
    if situacao:
        qs = qs.filter(situacao=situacao)
    if data_ini:
        qs = qs.filter(data_emissao__gte=data_ini)
    if data_fim:
        qs = qs.filter(data_emissao__lte=data_fim)

    total = qs.count()
    total_autorizadas = qs.filter(situacao='1').count()
    total_canceladas = qs.filter(situacao='2').count()
    total_pendente_manifestacao = qs.filter(
        schema='resNFe', situacao='1', manifestacao_tipo='',
    ).exclude(cnpj_emitente=_SOMENTE_DIGITOS_RE.sub('', empresa.cnpj or '')).count()

    page_obj, per_page, per_page_options = paginate(request, qs)

    return render(request, 'faturamento/dfe_list.html', {
        'config': config,
        'page_obj': page_obj,
        'cnpj_emitente': cnpj_emitente,
        'chave_acesso': chave_acesso,
        'tipo': tipo,
        'situacao': situacao,
        'data_ini': data_ini,
        'data_fim': data_fim,
        'tipo_choices': DfeRecebido.SCHEMA_CHOICES,
        'situacao_choices': DfeRecebido.SITUACAO_CHOICES,
        'manifestacao_tipos': DfeRecebido.MANIFESTACAO_TIPO_CHOICES,
        'total': total,
        'total_autorizadas': total_autorizadas,
        'total_canceladas': total_canceladas,
        'total_pendente_manifestacao': total_pendente_manifestacao,
        'cnpj_empresa': _SOMENTE_DIGITOS_RE.sub('', empresa.cnpj or ''),
        'per_page': per_page,
        'per_page_options': per_page_options,
    })


@login_required
@require_POST
def dfe_manifestar(request, pk):
    """Registra Manifestação do Destinatário (MD-e) para um resNFe recebido via distribuição.

    Chamado pelo modal em dfe_list.html — sempre redireciona de volta pra lá (sucesso ou erro).
    """
    documento = get_object_or_404(DfeRecebido, pk=pk, empresa=_get_empresa(request))

    if documento.schema != 'resNFe' or not documento.chave_acesso:
        messages.error(request, 'Este documento não é uma NF-e manifestável.')
        return redirect('faturamento:dfe_list')

    cnpj_empresa = _SOMENTE_DIGITOS_RE.sub('', documento.empresa.cnpj or '')
    if documento.cnpj_emitente == cnpj_empresa:
        messages.error(request, 'Não é possível manifestar sobre uma nota emitida pela própria empresa.')
        return redirect('faturamento:dfe_list')

    if documento.manifestacao_tipo in DfeRecebido.MANIFESTACAO_TIPOS_TERMINAIS:
        messages.info(request, f'Manifestação já registrada: {documento.get_manifestacao_tipo_display()}.')
        return redirect('faturamento:dfe_list')

    from .services.integranotas import IntegranNotasClient, IntegranNotasError

    TIPOS = DfeRecebido.MANIFESTACAO_TIPO_CHOICES
    tipos_validos = [t[0] for t in TIPOS]
    tipo = request.POST.get('tipo', '').strip()
    justificativa = request.POST.get('justificativa', '').strip()

    if tipo not in tipos_validos:
        messages.error(request, 'Tipo de manifestação inválido.')
        return redirect('faturamento:dfe_list')

    if tipo == 'operacao_nao_realizada' and not justificativa:
        messages.error(request, 'Justificativa obrigatória para "Operação Não Realizada".')
        return redirect('faturamento:dfe_list')

    config = ConfiguracaoFiscal.objects.filter(empresa=documento.empresa).first()
    if not config or not config.has_token:
        messages.error(request, 'Configure o token IntegraNota em Configuração Fiscal para registrar manifestação.')
        return redirect('faturamento:dfe_list')

    try:
        client = IntegranNotasClient(config.get_token(), config.ambiente_nfe)
        resultado = client.manifestar_nfe(documento.chave_acesso, tipo, justificativa)
    except IntegranNotasError as exc:
        if str(exc.codigo) == '573':
            # SEFAZ já tinha esse evento registrado pra essa chave (nosso registro local
            # estava desatualizado, ex.: manifestado por fora do sistema). Sincroniza em
            # vez de tratar como falha — não há novo protocolo pra guardar nesse caso.
            documento.manifestacao_tipo = tipo
            documento.manifestacao_data = timezone.now()
            documento.save(update_fields=['manifestacao_tipo', 'manifestacao_data'])
            messages.info(request, 'Esta manifestação já estava registrada na SEFAZ — status sincronizado.')
            return redirect('faturamento:dfe_list')
        detalhe = '; '.join(str(e) for e in exc.erros) if exc.erros else ''
        msg = f'Erro ao registrar manifestação [{exc.codigo}]: {exc}'
        if detalhe:
            msg += f' — {detalhe}'
        messages.error(request, msg)
        return redirect('faturamento:dfe_list')
    except Exception as exc:
        messages.error(request, f'Falha na comunicação com IntegraNota: {exc}')
        return redirect('faturamento:dfe_list')

    documento.manifestacao_tipo = tipo
    documento.manifestacao_protocolo = resultado.get('protocolo', '') or resultado.get('numero_protocolo', '')
    documento.manifestacao_data = timezone.now()
    documento.save(update_fields=['manifestacao_tipo', 'manifestacao_protocolo', 'manifestacao_data'])

    from .services.distribuicao_dfe import baixar_xml_completo_dfe

    try:
        xml_pronto = baixar_xml_completo_dfe(documento, config=config)
    except Exception as exc:
        logger.warning('Falha ao buscar XML completo após manifestação da chave %s: %s', documento.chave_acesso, exc)
        xml_pronto = False

    msg = f'Manifestação "{dict(TIPOS)[tipo]}" registrada com sucesso na SEFAZ.'
    msg += ' XML completo já disponível para download.' if xml_pronto else \
        ' O XML completo ainda não está disponível — aguarde a próxima sincronização.'
    messages.success(request, msg)
    return redirect('faturamento:dfe_list')


@login_required
@require_POST
def dfe_manifestar_lote(request):
    """Registra Manifestação do Destinatário em lote para os documentos selecionados na listagem.

    O tipo de manifestação e a justificativa (quando aplicável) são escolhidos
    individualmente por nota no modal de lote — chegam como campos `tipo_<pk>` e
    `justificativa_<pk>` no POST. Documentos não elegíveis (evento, nota própria, já
    manifestada) ou sem tipo válido informado são simplesmente ignorados.
    """
    empresa = _get_empresa(request)
    if not empresa:
        return redirect('dashboard:index')

    ids = request.POST.getlist('ids')
    if not ids:
        messages.warning(request, 'Nenhum documento selecionado.')
        return redirect('faturamento:dfe_list')

    config = ConfiguracaoFiscal.objects.filter(empresa=empresa).first()
    if not config or not config.has_token:
        messages.error(request, 'Configure o token IntegraNota em Configuração Fiscal para registrar manifestação.')
        return redirect('faturamento:dfe_list')

    from .services.integranotas import IntegranNotasClient, IntegranNotasError
    from .services.distribuicao_dfe import baixar_xml_completo_dfe

    tipos_validos = [t[0] for t in DfeRecebido.MANIFESTACAO_TIPO_CHOICES]
    cnpj_empresa = _SOMENTE_DIGITOS_RE.sub('', empresa.cnpj or '')
    documentos = DfeRecebido.objects.filter(
        empresa=empresa, pk__in=ids, schema='resNFe',
    ).exclude(chave_acesso='').exclude(cnpj_emitente=cnpj_empresa).exclude(
        manifestacao_tipo__in=DfeRecebido.MANIFESTACAO_TIPOS_TERMINAIS,
    )

    client = IntegranNotasClient(config.get_token(), config.ambiente_nfe)
    sucesso = 0
    falhas = 0
    invalidos = 0
    xml_baixados = 0
    for doc in documentos:
        tipo = request.POST.get(f'tipo_{doc.pk}', '').strip()
        justificativa = request.POST.get(f'justificativa_{doc.pk}', '').strip()

        if tipo not in tipos_validos or (tipo == 'operacao_nao_realizada' and not justificativa):
            invalidos += 1
            continue

        try:
            resultado = client.manifestar_nfe(doc.chave_acesso, tipo, justificativa)
        except IntegranNotasError as exc:
            if str(exc.codigo) == '573':
                # SEFAZ já tinha esse evento registrado — sincroniza em vez de contar como falha.
                doc.manifestacao_tipo = tipo
                doc.manifestacao_data = timezone.now()
                doc.save(update_fields=['manifestacao_tipo', 'manifestacao_data'])
                sucesso += 1
                continue
            logger.warning('Falha ao manifestar em lote a chave %s: %s', doc.chave_acesso, exc)
            falhas += 1
            continue
        except Exception as exc:
            logger.warning('Falha ao manifestar em lote a chave %s: %s', doc.chave_acesso, exc)
            falhas += 1
            continue
        doc.manifestacao_tipo = tipo
        doc.manifestacao_protocolo = resultado.get('protocolo', '') or resultado.get('numero_protocolo', '')
        doc.manifestacao_data = timezone.now()
        doc.save(update_fields=['manifestacao_tipo', 'manifestacao_protocolo', 'manifestacao_data'])
        sucesso += 1
        try:
            if baixar_xml_completo_dfe(doc, config=config):
                xml_baixados += 1
        except Exception as exc:
            logger.warning('Falha ao buscar XML completo em lote da chave %s: %s', doc.chave_acesso, exc)

    if sucesso:
        messages.success(request, f'{sucesso} manifestação(ões) registrada(s) com sucesso '
                                   f'({xml_baixados} com XML completo já disponível para download).')
    if falhas:
        messages.warning(request, f'{falhas} documento(s) falharam ao manifestar (veja o log do servidor).')
    if invalidos:
        messages.warning(request, f'{invalidos} documento(s) ignorados por tipo/justificativa não informados.')
    if not sucesso and not falhas and not invalidos:
        messages.info(request, 'Nenhum dos documentos selecionados era elegível para manifestação (evento, nota própria ou já manifestada).')
    return redirect('faturamento:dfe_list')


@login_required
def dfe_baixar_xml(request, pk):
    """Baixa o XML completo de um resNFe — se ainda não tiver sido buscado, tenta na
    hora na SEFAZ (mesma lógica best-effort usada logo após a manifestação e pela
    cron), em vez de depender só da próxima sincronização.

    Chamado pelo ícone de download individual em dfe_list.html.
    """
    documento = get_object_or_404(DfeRecebido, pk=pk, empresa=_get_empresa(request))

    if not documento.xml_url:
        from .services.distribuicao_dfe import baixar_xml_completo_dfe

        config = ConfiguracaoFiscal.objects.filter(empresa=documento.empresa).first()
        try:
            baixar_xml_completo_dfe(documento, config=config)
        except Exception as exc:
            logger.warning('Falha ao buscar XML completo sob demanda da chave %s: %s', documento.chave_acesso, exc)

    if not documento.xml_url:
        messages.warning(request, 'XML completo ainda não disponível na SEFAZ. Tente novamente em alguns minutos.')
        return redirect('faturamento:dfe_list')

    import requests

    try:
        resp = requests.get(documento.xml_url, timeout=30)
        resp.raise_for_status()
    except Exception as exc:
        logger.warning('Falha ao baixar XML do storage para a chave %s: %s', documento.chave_acesso, exc)
        messages.error(request, 'Falha ao baixar o arquivo. Tente novamente.')
        return redirect('faturamento:dfe_list')

    response = HttpResponse(resp.content, content_type='application/xml')
    filename = f'{documento.chave_acesso or documento.pk}.xml'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
def dfe_baixar_danfe(request, pk):
    """Baixa o DANFE (PDF) de um resNFe — rota oficial da IntegraNotas com fallback
    pro gerador local a partir do XML completo (ver dfe_danfe.obter_pdf_base64).

    O PDF já é gerado automaticamente logo após o download do XML completo (ver
    `baixar_xml_completo_dfe`); se por algum motivo ainda não existir mas o XML já
    estiver disponível, tenta gerar na hora em vez de só reportar indisponível.
    """
    documento = get_object_or_404(DfeRecebido, pk=pk, empresa=_get_empresa(request))

    if not documento.pdf_danfe_url and documento.xml_url:
        import requests as _requests

        from .fiscal_storage import upload_pdf
        from .services.dfe_danfe import obter_pdf_base64, versionar_url

        try:
            resp_xml = _requests.get(documento.xml_url, timeout=30)
            resp_xml.raise_for_status()
            config = ConfiguracaoFiscal.objects.filter(empresa=documento.empresa).first()
            # .content.decode('utf-8') explícito — .text deixa o requests "adivinhar" a
            # codificação e, sem charset no header do Storage, ele erra pra Latin-1 às
            # vezes, corrompendo acentos (raiz do bug "SERVIÇOS" -> "SERVIÃ■OS").
            pdf_b64 = obter_pdf_base64(resp_xml.content.decode('utf-8'), documento, config=config)
            if pdf_b64:
                pdf_url = upload_pdf(pdf_b64, documento.empresa_id, 'dfe', f'{documento.chave_acesso}.pdf')
                if pdf_url:
                    documento.pdf_danfe_url = versionar_url(pdf_url)
                    documento.save(update_fields=['pdf_danfe_url'])
        except Exception as exc:
            logger.warning('Falha ao gerar DANFE sob demanda da chave %s: %s', documento.chave_acesso, exc)

    if not documento.pdf_danfe_url:
        messages.warning(request, 'DANFE ainda não disponível — baixe o XML completo primeiro.')
        return redirect('faturamento:dfe_list')

    import requests

    try:
        resp = requests.get(documento.pdf_danfe_url, timeout=30)
        resp.raise_for_status()
    except Exception as exc:
        logger.warning('Falha ao baixar DANFE do storage para a chave %s: %s', documento.chave_acesso, exc)
        messages.error(request, 'Falha ao baixar o arquivo. Tente novamente.')
        return redirect('faturamento:dfe_list')

    response = HttpResponse(resp.content, content_type='application/pdf')
    filename = f'DANFE_{documento.chave_acesso or documento.pk}.pdf'
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    # A URL desta view não muda entre regenerações do DANFE — sem isso o navegador
    # (o visualizador de PDF do Chrome em especial) guarda a resposta em cache e não
    # busca o PDF atualizado mesmo depois de regenerado no servidor.
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response


@login_required
@require_POST
def dfe_baixar_xml_lote(request):
    """Baixa em um único .zip os XMLs completos já disponíveis dos documentos selecionados.

    Só inclui documentos com `xml_url` preenchido — os ainda pendentes (sem manifestação
    ou aguardando a próxima sincronização) são ignorados e reportados à parte.
    """
    import zipfile
    from io import BytesIO

    import requests

    empresa = _get_empresa(request)
    if not empresa:
        return redirect('dashboard:index')

    ids = request.POST.getlist('ids')
    if not ids:
        messages.warning(request, 'Nenhum documento selecionado.')
        return redirect('faturamento:dfe_list')

    documentos = list(DfeRecebido.objects.filter(empresa=empresa, pk__in=ids).exclude(xml_url=''))
    ignorados = len(ids) - len(documentos)

    if not documentos:
        messages.warning(
            request,
            'Nenhum dos documentos selecionados tem XML completo disponível. '
            'Registre a manifestação e aguarde a próxima sincronização antes de baixar.',
        )
        return redirect('faturamento:dfe_list')

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for doc in documentos:
            try:
                resp = requests.get(doc.xml_url, timeout=30)
                resp.raise_for_status()
            except Exception as exc:
                logger.warning('Falha ao baixar XML %s para o zip em lote: %s', doc.chave_acesso, exc)
                continue
            zf.writestr(f'{doc.chave_acesso or doc.pk}.xml', resp.content)

    if ignorados:
        messages.info(request, f'{ignorados} documento(s) selecionado(s) ainda sem XML completo foram ignorados.')

    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/zip')
    filename = f'dfe_xmls_{timezone.now():%Y%m%d_%H%M%S}.zip'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
@require_POST
def dfe_baixar_danfe_lote(request):
    """Baixa em um único .zip os DANFEs (PDF) já gerados dos documentos selecionados.

    Só inclui documentos com `pdf_danfe_url` preenchido — os ainda sem XML completo
    (ou cujo DANFE não pôde ser gerado) são ignorados e reportados à parte.
    """
    import zipfile
    from io import BytesIO

    import requests

    empresa = _get_empresa(request)
    if not empresa:
        return redirect('dashboard:index')

    ids = request.POST.getlist('ids')
    if not ids:
        messages.warning(request, 'Nenhum documento selecionado.')
        return redirect('faturamento:dfe_list')

    documentos = list(DfeRecebido.objects.filter(empresa=empresa, pk__in=ids).exclude(pdf_danfe_url=''))
    ignorados = len(ids) - len(documentos)

    if not documentos:
        messages.warning(
            request,
            'Nenhum dos documentos selecionados tem DANFE disponível. '
            'Registre a manifestação e aguarde a próxima sincronização antes de baixar.',
        )
        return redirect('faturamento:dfe_list')

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for doc in documentos:
            try:
                resp = requests.get(doc.pdf_danfe_url, timeout=30)
                resp.raise_for_status()
            except Exception as exc:
                logger.warning('Falha ao baixar DANFE %s para o zip em lote: %s', doc.chave_acesso, exc)
                continue
            zf.writestr(f'DANFE_{doc.chave_acesso or doc.pk}.pdf', resp.content)

    if ignorados:
        messages.info(request, f'{ignorados} documento(s) selecionado(s) ainda sem DANFE disponível foram ignorados.')

    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/zip')
    filename = f'dfe_danfes_{timezone.now():%Y%m%d_%H%M%S}.zip'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@csrf_exempt
def dfe_sync_webhook(request):
    """Webhook para o cron do Supabase (pg_cron + pg_net) disparar a sincronização
    periódica de todas as empresas. Protegido por segredo compartilhado — diferente
    de `integranotas_webhook`, que não tem autenticação porque só recebe notificações;
    este endpoint executa consultas reais à SEFAZ e uploads, então precisa de segredo.
    """
    if request.method != 'POST':
        return HttpResponse(status=405)

    secret = request.headers.get('X-Sync-Secret', '')
    if not settings.DFE_SYNC_SECRET or secret != settings.DFE_SYNC_SECRET:
        return HttpResponse(status=403)

    from .services.distribuicao_dfe import sincronizar_todas_empresas

    resultados = sincronizar_todas_empresas()
    return JsonResponse({'resultados': resultados})


# ─────────────────────────── AJAX ───────────────────────────

@login_required
def ajax_produto_detail(request, pk):
    empresa = _get_empresa(request)
    from produtos.models import Produto
    try:
        produto = Produto.objects.select_related('ncm', 'unidade_venda', 'unidade_medida').get(pk=pk, categoria__empresa=empresa)
    except Produto.DoesNotExist:
        return JsonResponse({'erro': 'Produto não encontrado'}, status=404)

    tributacoes = []
    for t in produto.tributacoes.select_related('cfop').filter(ativo=True):
        tributacoes.append({
            'cfop': t.cfop.codigo if t.cfop_id else '',
            'padrao': bool(t.padrao),
            'origem_mercadoria': t.origem_mercadoria or '0',
            'cst_icms': t.icms_situacao_tributaria,
            'icms_modalidade_base': t.icms_modalidade_base or '3',
            'icms_reducao_base': float(t.icms_reducao_base or 0),
            'aliquota_icms': float(t.icms_aliquota),
            'icms_st_aliquota': float(t.icms_st_aliquota or 0),
            'icms_st_mva': float(t.icms_st_mva or 0),
            'icms_st_reducao_base': float(t.icms_st_reducao_base or 0),
            'cst_ipi': t.ipi_situacao_tributaria or '99',
            'aliquota_ipi': float(t.ipi_aliquota or 0),
            'ipi_codigo_enquadramento': t.ipi_codigo_enquadramento or '999',
            'cst_pis': t.pis_situacao_tributaria,
            'aliquota_pis': float(t.pis_aliquota),
            'natureza_receita_pis': t.natureza_receita_pis or '',
            'cst_cofins': t.cofins_situacao_tributaria,
            'aliquota_cofins': float(t.cofins_aliquota),
            'natureza_receita_cofins': t.natureza_receita_cofins or '',
            'beneficio_fiscal': t.beneficio_fiscal or '',
            'icms_percentual_diferimento': float(t.icms_percentual_diferimento or 0),
            'ibs_cbs_situacao_tributaria': t.ibs_cbs_situacao_tributaria or '',
            'ibs_cbs_classificacao_tributaria': t.ibs_cbs_classificacao_tributaria or '',
            'ibs_cbs_aliquota_uf': float(t.ibs_cbs_aliquota_uf or 0),
            'ibs_cbs_aliquota_municipal': float(t.ibs_cbs_aliquota_municipal or 0),
            'ibs_cbs_aliquota_cbs': float(t.ibs_cbs_aliquota_cbs or 0),
            'ibs_percentual_reducao': float(t.ibs_percentual_reducao or 0),
            'ibs_percentual_diferimento': float(t.ibs_percentual_diferimento or 0),
            'cbs_percentual_reducao': float(t.cbs_percentual_reducao or 0),
            'cbs_percentual_diferimento': float(t.cbs_percentual_diferimento or 0),
            'ibs_cbs_credito_presumido_codigo': t.ibs_cbs_credito_presumido_codigo or '',
            'ibs_cbs_credito_presumido_percentual': float(t.ibs_cbs_credito_presumido_percentual or 0),
        })

    fator = float(produto.fator_conversao or 1)
    un_med_sigla = produto.unidade_medida.sigla if produto.unidade_medida_id else ''
    un_venda_sigla = produto.unidade_venda.sigla if produto.unidade_venda_id else ''
    # Unidade tributável = unidade_medida quando difere da unidade_venda; caso contrário KG (fallback peso)
    un_trib = un_med_sigla if (un_med_sigla and un_med_sigla != un_venda_sigla) else ''

    # Resolve a tributação correta a partir do cadastro do cliente — mesma
    # regra do Pedido de Venda (produtos.tributacao.resolver_tributacao_venda):
    # dentro do estado / fora do estado (interestadual) / exportação. O tipo
    # de venda não é escolhido manualmente nem depende do CFOP digitado no
    # cabeçalho — vem direto do cadastro do cliente (uf_fiscal() retorna 'EX'
    # para cliente do exterior). Só se aplica a NF-e de saída (com cliente);
    # NF-e de entrada (fornecedor) mantém a seleção manual/por CFOP.
    tributacao_sugerida_cfop = None
    tributacao_sugerida_erro = None
    cliente_id = request.GET.get('cliente_id')
    if cliente_id:
        from cadastros.models import Cliente
        from produtos.tributacao import resolver_tributacao_venda
        cliente = Cliente.objects.filter(pk=cliente_id, empresa=empresa).first()
        tipo_venda = 'EXPORTACAO' if (cliente and cliente.uf_fiscal() == 'EX') else 'MERCADO_INTERNO'
        resultado = resolver_tributacao_venda(produto, empresa, cliente, tipo_venda)
        if resultado.ok:
            tributacao_sugerida_cfop = resultado.cfop_codigo
        else:
            tributacao_sugerida_erro = resultado.mensagem

    return JsonResponse({
        'nome': produto.nome,
        'ncm': produto.ncm.codigo if produto.ncm_id else '',
        'cest': produto.cest or '',
        'origem_mercadoria': produto.origem_mercadoria or '0',
        'unidade': un_venda_sigla,
        'preco_venda': float(produto.preco_venda),
        'peso_liquido_unitario': float(produto.peso_liquido_unitario or 0),
        'peso_bruto_unitario':   float(produto.peso_bruto_unitario or 0),
        'fator_conversao': fator,
        'unidade_tributavel': un_trib,
        'tributacoes': tributacoes,
        'tributacao_sugerida_cfop': tributacao_sugerida_cfop,
        'tributacao_sugerida_erro': tributacao_sugerida_erro,
    })


@login_required
def ajax_nfe_para_mdfe(request):
    empresa = _get_empresa(request)
    q = request.GET.get('q', '').strip()
    notas = NotaFiscal.objects.filter(empresa=empresa, status='EMITIDA').select_related('cliente')
    if q:
        notas = notas.filter(Q(cliente__razao_social__icontains=q) | Q(numero__icontains=q))
    notas = notas.order_by('-data_emissao')[:50]
    results = [{
        'id':               n.pk,
        'numero':           n.numero,
        'serie':            n.serie,
        'cliente_nome':     n.cliente.razao_social,
        'valor_total':      str(n.valor_total),
        'peso_bruto_kg':    str(n.peso_bruto_kg or '0'),
        'chave_acesso':     n.chave_acesso or '',
        'municipio':        (n.entrega_nome_municipio if n.entrega_ativo else '') or '',
        'codigo_municipio': (n.entrega_codigo_municipio if n.entrega_ativo else '') or '',
        'data_emissao':     n.data_emissao.strftime('%d/%m/%Y'),
    } for n in notas]
    return JsonResponse({'results': results})


@login_required
def ajax_cte_para_mdfe(request):
    empresa = _get_empresa(request)
    q = request.GET.get('q', '').strip()
    ctes = ConhecimentoTransporte.objects.filter(empresa=empresa, status='EMITIDO').select_related('destinatario')
    if q:
        ctes = ctes.filter(Q(destinatario__razao_social__icontains=q) | Q(numero__icontains=q))
    ctes = ctes.order_by('-data_emissao')[:50]
    results = [{
        'id':               c.pk,
        'numero':           c.numero,
        'serie':            c.serie,
        'destinatario_nome': c.destinatario.razao_social,
        'valor_carga':      str(c.valor_carga),
        'peso_bruto_kg':    str(c.peso_bruto_kg),
        'chave_acesso':     c.chave_acesso or '',
        'municipio':        c.municipio_fim,
        'codigo_municipio': c.codigo_municipio_fim or '',
        'uf_fim':           c.uf_fim,
        'data_emissao':     c.data_emissao.strftime('%d/%m/%Y'),
    } for c in ctes]
    return JsonResponse({'results': results})


@login_required
def ajax_nfe_para_cte(request):
    empresa = _get_empresa(request)
    q    = request.GET.get('q', '').strip()
    tipo = request.GET.get('tipo', 'nfe')   # 'nfe' | 'cte'

    results = []

    if tipo == 'cte':
        ctes = (
            ConhecimentoTransporte.objects
            .filter(empresa=empresa, status='EMITIDO')
            .select_related('remetente', 'destinatario', 'transportadora')
        )
        if q:
            ctes = ctes.filter(
                Q(remetente__razao_social__icontains=q) |
                Q(destinatario__razao_social__icontains=q) |
                Q(numero__icontains=q)
            )
        ctes = ctes.order_by('-data_emissao')[:50]
        for c in ctes:
            results.append({
                'id':                  c.pk,
                'tipo_doc':            'cte',
                'numero':              c.numero or 0,
                'serie':               c.serie,
                'cliente_id':          c.remetente_id,
                'cliente_nome':        c.remetente.razao_social,
                'destinatario_id':     c.destinatario_id,
                'destinatario_nome':   c.destinatario.razao_social,
                'valor_total':         str(c.valor_servico),
                'chave_acesso':        c.chave_acesso or '',
                'data_emissao':        c.data_emissao.strftime('%d/%m/%Y'),
                'transportadora_id':   c.transportadora_id,
                'transportadora_nome': c.transportadora.nome,
                'modalidade_frete':    c.modalidade_frete or '',
                'peso_bruto_kg':       str(c.peso_bruto_kg or '0'),
                'natureza_operacao':   c.natureza_operacao or '',
                'valor_frete':         str(c.valor_servico),
                'produto_predominante': c.produto_predominante or '',
                'cliente_uf':          c.uf_fim,
                'cliente_municipio':   c.municipio_fim,
                'empresa_uf':          c.uf_inicio,
                'empresa_municipio':   c.municipio_inicio,
            })
    else:
        notas = (
            NotaFiscal.objects
            .filter(
                empresa=empresa,
                status='EMITIDA',
                cliente__isnull=False,
                chave_acesso__gt='',
            )
            .select_related('cliente', 'transportadora')
        )
        if q:
            notas = notas.filter(Q(cliente__razao_social__icontains=q) | Q(numero__icontains=q))
        notas = notas.order_by('-data_emissao')[:50]
        try:
            for n in notas:
                endereco = n.cliente.enderecos.filter(padrao=True).first()
                results.append({
                    'id':                  n.pk,
                    'tipo_doc':            'nfe',
                    'numero':              n.numero,
                    'serie':               n.serie,
                    'cliente_id':          n.cliente_id,
                    'cliente_nome':        n.cliente.razao_social,
                    'valor_total':         str(n.valor_total),
                    'chave_acesso':        n.chave_acesso or '',
                    'data_emissao':        n.data_emissao.strftime('%d/%m/%Y'),
                    'transportadora_id':   '',
                    'transportadora_nome': str(n.transportadora) if n.transportadora else '',
                    'modalidade_frete':    n.modalidade_frete or '',
                    'peso_bruto_kg':       str(n.peso_bruto_kg or '0'),
                    'natureza_operacao':   n.natureza_operacao or '',
                    'valor_frete':         str(n.valor_frete or '0'),
                    'produto_predominante': '',
                    'cliente_uf':          endereco.uf if endereco else '',
                    'cliente_municipio':   endereco.cidade if endereco else '',
                    'empresa_uf':          empresa.uf or '',
                    'empresa_municipio':   empresa.cidade or '',
                })
        except Exception as exc:
            import logging
            logging.getLogger(__name__).error('ajax_nfe_para_cte error: %s', exc)
            return JsonResponse({'results': [], 'error': str(exc)})

    return JsonResponse({'results': results})


@login_required
def ajax_booking_preview(request, pk):
    empresa = _get_empresa(request)
    from exportacao.models import Booking
    try:
        b = Booking.objects.get(pk=pk, empresa=empresa)
    except Booking.DoesNotExist:
        return JsonResponse({'error': 'Não encontrado'}, status=404)

    cliente_id = None
    cliente_nome = ''
    if b.solicitacao and b.solicitacao.cliente:
        cliente_id = b.solicitacao.cliente.pk
        cliente_nome = str(b.solicitacao.cliente)

    containers = list(b.containers.values('id', 'numero_container', 'tipo_container'))

    return JsonResponse({
        'porto_embarque': str(b.porto_origem) if b.porto_origem else '',
        'porto_destino': str(b.porto_destino) if b.porto_destino else '',
        'data_embarque_previsto': str(b.data_embarque_previsto) if b.data_embarque_previsto else '',
        'valor_fob': str(b.valor_fob) if b.valor_fob else '',
        'cliente_id': cliente_id,
        'cliente_nome': cliente_nome,
        'containers': containers,
    })


@login_required
def ajax_cotacao_bcb(request):
    """
    Retorna cotações PTAX do BCB para o último dia útil anterior.
    Usado nos formulários de Invoice, Pedido de Venda e Conta a Receber
    para pré-preencher a taxa de câmbio.

    Query params opcionais:
        moedas — lista separada por vírgula (ex: USD,EUR,GBP). Padrão: USD,EUR,GBP
        data   — data de referência ISO (ex: 2026-05-20). Padrão: hoje
    """
    from .bcb import buscar_cotacoes
    from datetime import date

    moedas_param = request.GET.get('moedas', 'USD,EUR,GBP')
    moedas = [m.strip().upper() for m in moedas_param.split(',') if m.strip()]

    data_ref = None
    data_param = request.GET.get('data', '')
    if data_param:
        try:
            data_ref = date.fromisoformat(data_param)
        except ValueError:
            pass

    try:
        resultado = buscar_cotacoes(moedas=moedas, referencia=data_ref)
    except RuntimeError as e:
        return JsonResponse({'erro': str(e)}, status=503)
    except Exception as e:
        return JsonResponse({'erro': f'Erro ao consultar o BCB: {e}'}, status=503)

    cotacoes_json = {}
    for moeda, dados in resultado['cotacoes'].items():
        cotacoes_json[moeda] = {
            'compra': float(dados['compra']),
            'venda': float(dados['venda']),
            'dataHora': dados.get('dataHora', ''),
        }

    # Persiste automaticamente as cotações consultadas
    data_ref_obj = date.fromisoformat(resultado['data_iso'])
    MOEDAS_SALVAR = {'USD', 'EUR', 'GBP'}
    from .models import CotacaoBCB
    for moeda, dados in resultado['cotacoes'].items():
        if moeda in MOEDAS_SALVAR:
            CotacaoBCB.objects.update_or_create(
                data=data_ref_obj,
                moeda=moeda,
                defaults={'compra': dados['compra'], 'venda': dados['venda']},
            )

    return JsonResponse({
        'data': resultado['data'],
        'data_iso': resultado['data_iso'],
        'cotacoes': cotacoes_json,
    })


@login_required
def ajax_gerar_infcpl(request):
    """
    Gera o texto de "Informações Complementares" da NF-e a partir do
    texto-base configurado em ConfiguracaoFiscal + dados de rastreabilidade
    (mercado interno) ou de embarque/drawback/PTAX (exportação).

    Query params:
        tipo               — 'interna' ou 'exportacao'
        rastreabilidade    — número de rastreabilidade digitado na NF
        data_emissao        — data ISO da NF (usada para buscar o PTAX do dia útil anterior)
        produtos            — nomes dos produtos dos itens da NF, já concatenados (só exportação)
        ordem_coleta_id     — pk de exportacao.OrdemColeta (só exportação)
        ato_id              — pk de drawback.AtoConcessorio (só exportação)
    """
    from datetime import date

    from drawback.models import AtoConcessorio
    from exportacao.models import OrdemColeta

    from .services.infcpl import montar_texto_infcpl_exportacao, montar_texto_infcpl_interna

    empresa = _get_empresa(request)

    try:
        config = ConfiguracaoFiscal.objects.filter(empresa=empresa).first()
        texto_base = config.texto_isencao_icms if config else ''

        tipo = request.GET.get('tipo', 'interna')
        rastreabilidade = request.GET.get('rastreabilidade', '').strip()

        if tipo != 'exportacao':
            texto = montar_texto_infcpl_interna(texto_base=texto_base, numero_rastreabilidade=rastreabilidade)
            return JsonResponse({'texto': texto})

        ordem_coleta_id = request.GET.get('ordem_coleta_id', '').strip()
        ato_id = request.GET.get('ato_id', '').strip()
        ordem_coleta = OrdemColeta.objects.filter(
            empresa=empresa, pk=ordem_coleta_id,
        ).select_related('booking', 'container').first() if ordem_coleta_id else None
        ato_concessorio = AtoConcessorio.objects.filter(
            empresa=empresa, pk=ato_id,
        ).first() if ato_id else None

        booking = navio = numero_container = lacre_fiscal = lacre_g7 = numero_tale = ''
        tara_container = None
        if ordem_coleta:
            if ordem_coleta.booking:
                booking = ordem_coleta.booking.codigo
                navio = ordem_coleta.booking.rota_navio
            lacre_fiscal = ordem_coleta.lacre_fiscal
            lacre_g7 = ordem_coleta.lacre_g7
            if ordem_coleta.container:
                numero_container = ordem_coleta.container.numero_container
                tara_container = ordem_coleta.container.tara_container
                numero_tale = ordem_coleta.container.numero_tale
                lacre_fiscal = lacre_fiscal or ordem_coleta.container.lacre_fiscal
                lacre_g7 = lacre_g7 or ordem_coleta.container.lacre_g7

        ptax_eur = ptax_data = None
        data_param = request.GET.get('data_emissao', '')
        try:
            data_emissao = date.fromisoformat(data_param) if data_param else date.today()
        except ValueError:
            data_emissao = date.today()
        try:
            from .bcb import buscar_cotacoes
            resultado = buscar_cotacoes(moedas=['EUR'], referencia=data_emissao)
            ptax_eur = resultado['cotacoes']['EUR']['venda']
            ptax_data = resultado['data']
        except Exception:
            pass

        texto = montar_texto_infcpl_exportacao(
            texto_base=texto_base,
            ato_concessorio=ato_concessorio,
            produtos_desc=request.GET.get('produtos', '').strip(),
            booking=booking,
            navio=navio,
            numero_container=numero_container,
            lacre_fiscal=lacre_fiscal,
            tara_container=tara_container,
            lacre_g7=lacre_g7,
            numero_tale=numero_tale,
            numero_rastreabilidade=rastreabilidade,
            ptax_eur=ptax_eur,
            ptax_data=ptax_data,
        )
        return JsonResponse({'texto': texto})
    except Exception as e:
        return JsonResponse({'erro': f'Erro ao gerar informações complementares: {e}'}, status=500)


# ───────────────────────── Histórico de Cotações BCB ─────────────────────

@login_required
def cotacoes_bcb_list(request):
    from .models import CotacaoBCB
    from datetime import date

    # Filtro por período (padrão: últimos 90 dias)
    data_fim = date.today()
    data_ini_str = request.GET.get('data_ini', '')
    data_fim_str = request.GET.get('data_fim', '')
    try:
        data_ini = date.fromisoformat(data_ini_str) if data_ini_str else None
    except ValueError:
        data_ini = None
    try:
        data_fim = date.fromisoformat(data_fim_str) if data_fim_str else date.today()
    except ValueError:
        data_fim = date.today()

    qs = CotacaoBCB.objects.all()
    if data_ini:
        qs = qs.filter(data__gte=data_ini)
    qs = qs.filter(data__lte=data_fim)

    # Monta estrutura: {data: {moeda: {compra, venda}}}
    from collections import defaultdict
    por_data = defaultdict(dict)
    for c in qs:
        por_data[c.data][c.moeda] = {'compra': c.compra, 'venda': c.venda}

    linhas = [
        {'data': d, 'cotacoes': por_data[d]}
        for d in sorted(por_data.keys(), reverse=True)
    ]

    linhas_page, per_page, per_page_options = paginate(request, linhas)

    return render(request, 'faturamento/cotacoes_bcb/list.html', {
        'linhas': linhas_page,
        'data_ini': data_ini_str,
        'data_fim': data_fim_str,
        'total': len(linhas),
        'per_page': per_page,
        'per_page_options': per_page_options,
    })


@login_required
def cotacoes_bcb_buscar_hoje(request):
    """Busca manualmente as cotações do dia e redireciona para o histórico."""
    if request.method != 'POST':
        from django.shortcuts import redirect
        return redirect('faturamento:cotacoes_bcb_list')

    from .bcb import buscar_cotacoes
    from .models import CotacaoBCB
    from datetime import date

    try:
        resultado = buscar_cotacoes(moedas=['USD', 'EUR', 'GBP'])
        data_ref = date.fromisoformat(resultado['data_iso'])
        for moeda, dados in resultado['cotacoes'].items():
            CotacaoBCB.objects.update_or_create(
                data=data_ref,
                moeda=moeda,
                defaults={'compra': dados['compra'], 'venda': dados['venda']},
            )
        from django.contrib import messages
        messages.success(request, f"Cotações BCB salvas para {resultado['data']} — USD, EUR, GBP.")
    except Exception as e:
        from django.contrib import messages
        messages.error(request, f'Erro ao buscar cotações do BCB: {e}')

    from django.shortcuts import redirect
    return redirect('faturamento:cotacoes_bcb_list')


# ───────────────────────── Documentação IntegraNotas ──────────────────────

@login_required
def docs_integranotas(request):
    import os
    from django.conf import settings
    docs_path = os.path.join(settings.BASE_DIR, 'docs_integranotas.html')
    with open(docs_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return HttpResponse(content, content_type='text/html; charset=utf-8')

# CT-e and MDF-e views — appended to views.py


# ═══════════════════════════════════════════════════════════════════
#  CT-e — Views
# ═══════════════════════════════════════════════════════════════════

@login_required
def cte_list(request):
    empresa = _get_empresa(request)
    if not empresa:
        return redirect('dashboard:index')
    qs = ConhecimentoTransporte.objects.filter(empresa=empresa).select_related('remetente', 'destinatario')
    status = request.GET.get('status', '')
    if status:
        qs = qs.filter(status=status)
    q = request.GET.get('q', '')
    if q:
        qs = qs.filter(
            Q(remetente__razao_social__icontains=q) |
            Q(destinatario__razao_social__icontains=q) |
            Q(chave_acesso__icontains=q)
        )
    page, per_page, per_page_options = paginate(request, qs)
    return render(request, 'faturamento/cte/list.html', {
        'page_obj': page, 'status_filtro': status, 'q': q,
        'status_choices': ConhecimentoTransporte.STATUS,
        'per_page': per_page,
        'per_page_options': per_page_options,
    })


@login_required
def cte_create(request):
    empresa = _get_empresa(request)
    if not empresa:
        return redirect('dashboard:index')
    if request.method == 'POST':
        form = ConhecimentoTransporteForm(request.POST, empresa=empresa)
        docs_formset = DocumentoVinculadoCTeFormSet(request.POST, prefix='docs')
        comp_formset = ComponenteValorCTeFormSet(request.POST, prefix='comp')
        if form.is_valid() and docs_formset.is_valid() and comp_formset.is_valid():
            docs_validos = [
                f for f in docs_formset
                if f.cleaned_data
                and f.cleaned_data.get('chave_nfe')
                and not f.cleaned_data.get('DELETE', False)
            ]
            if not docs_validos:
                messages.error(request, 'Adicione pelo menos uma Chave NF-e antes de salvar.')
            else:
                ct = form.save(user=request.user)
                docs_formset.instance = ct
                docs_formset.save()
                comp_formset.instance = ct
                comp_formset.save()
                messages.success(request, 'CT-e criado com sucesso.')
                return redirect('faturamento:cte_detail', pk=ct.pk)
    else:
        _cfg_cte = ConfiguracaoFiscal.objects.filter(empresa=empresa).first()
        _serie_cte_ini = _cfg_cte.serie_cte if _cfg_cte else 1
        initial = {'serie': _serie_cte_ini}
        comp_initial = []

        rom_id = request.GET.get('romaneio_venda')
        if rom_id:
            from decimal import Decimal
            from embalagem.models import RomaneioVenda
            rom = (RomaneioVenda.objects
                   .filter(pk=rom_id, empresa=empresa)
                   .select_related('carga_frete', 'cliente')
                   .first())
            if rom and rom.valor_frete_rateado is not None:
                initial.update({
                    'romaneio_venda': rom.pk,
                    'destinatario': rom.cliente_id,
                    'peso_bruto_kg': rom.peso_bruto_total,
                    'valor_servico': rom.valor_frete_rateado,
                    'base_calculo_icms': rom.valor_bc_icms_frete,
                    'reducao_base_icms': (
                        rom.percentual_reducao_bc if rom.metodo_icms_frete == 'REDUCAO' else Decimal('0')
                    ),
                    'aliquota_icms': rom.aliquota_icms_frete,
                    'valor_icms': rom.valor_icms_frete,
                    'cst_icms': '20' if rom.metodo_icms_frete == 'REDUCAO' else '00',
                })
                if rom.carga_frete_id:
                    initial['transportadora'] = rom.carga_frete.transportadora_id
                comp_initial.append({'nome': 'FRETE VALOR', 'valor': rom.valor_frete_rateado, 'ordem': 1})
                if rom.valor_pedagio_rateado:
                    comp_initial.append({'nome': 'PEDÁGIO', 'valor': rom.valor_pedagio_rateado, 'ordem': 2})
            else:
                messages.warning(request, 'Rateie o frete do romaneio antes de gerar o CT-e — valores não pré-preenchidos.')

        form = ConhecimentoTransporteForm(empresa=empresa, initial=initial)
        docs_formset = DocumentoVinculadoCTeFormSet(prefix='docs')
        comp_formset = ComponenteValorCTeFormSet(prefix='comp', initial=comp_initial)
    return render(request, 'faturamento/cte/form.html', {
        'form': form, 'docs_formset': docs_formset, 'comp_formset': comp_formset, 'action': 'Novo',
    })


@login_required
def cte_update(request, pk):
    empresa = _get_empresa(request)
    ct = get_object_or_404(ConhecimentoTransporte, pk=pk, empresa=empresa)
    if ct.status != 'RASCUNHO':
        messages.error(request, 'Somente CT-e em Rascunho pode ser editado.')
        return redirect('faturamento:cte_detail', pk=pk)
    if request.method == 'POST':
        form = ConhecimentoTransporteForm(request.POST, instance=ct, empresa=empresa)
        docs_formset = DocumentoVinculadoCTeFormSet(request.POST, instance=ct, prefix='docs')
        comp_formset = ComponenteValorCTeFormSet(request.POST, instance=ct, prefix='comp')
        if form.is_valid() and docs_formset.is_valid() and comp_formset.is_valid():
            docs_validos = [
                f for f in docs_formset
                if f.cleaned_data
                and f.cleaned_data.get('chave_nfe')
                and not f.cleaned_data.get('DELETE', False)
            ]
            if not docs_validos:
                messages.error(request, 'Adicione pelo menos uma Chave NF-e antes de salvar.')
            else:
                form.save(user=request.user)
                docs_formset.save()
                comp_formset.save()
                messages.success(request, 'CT-e atualizado.')
                return redirect('faturamento:cte_detail', pk=pk)
    else:
        form = ConhecimentoTransporteForm(instance=ct, empresa=empresa)
        docs_formset = DocumentoVinculadoCTeFormSet(instance=ct, prefix='docs')
        comp_formset = ComponenteValorCTeFormSet(instance=ct, prefix='comp')
    return render(request, 'faturamento/cte/form.html', {
        'form': form, 'docs_formset': docs_formset, 'comp_formset': comp_formset, 'action': 'Editar', 'object': ct,
    })


@login_required
def cte_detail(request, pk):
    empresa = _get_empresa(request)
    ct = get_object_or_404(ConhecimentoTransporte, pk=pk, empresa=empresa)
    return render(request, 'faturamento/cte/detail.html', {'ct': ct})


def _validar_cte(ct):
    import re as _re
    erros = []

    # IE do emitente
    ie_emit = (getattr(ct.empresa, 'inscricao_estadual', '') or '').strip()
    if not ie_emit:
        erros.append({'aba': 'Configuração', 'campo': 'Inscrição Estadual do emitente',
                      'msg': 'Preencha a IE em Minha Empresa antes de emitir.'})

    # Aba Geral
    if not ct.cfop:
        erros.append({'aba': 'Geral', 'campo': 'CFOP', 'msg': 'Campo obrigatório.'})
    if not ct.natureza_operacao:
        erros.append({'aba': 'Geral', 'campo': 'Natureza da Operação', 'msg': 'Campo obrigatório.'})
    if not ct.remetente_id:
        erros.append({'aba': 'Geral', 'campo': 'Remetente', 'msg': 'Campo obrigatório.'})
    if not ct.destinatario_id:
        erros.append({'aba': 'Geral', 'campo': 'Destinatário', 'msg': 'Campo obrigatório.'})
    if ct.tipo_tomador == '4' and not ct.tomador_id:
        erros.append({'aba': 'Geral', 'campo': 'Tomador (Outros)', 'msg': 'Obrigatório quando Tomador = "4 - Outros".'})
    if not ct.transportadora_id:
        erros.append({'aba': 'Geral', 'campo': 'Transportadora', 'msg': 'Campo obrigatório.'})

    # Aba Percurso
    if not ct.uf_inicio:
        erros.append({'aba': 'Percurso', 'campo': 'UF de Início', 'msg': 'Campo obrigatório.'})
    if not ct.municipio_inicio:
        erros.append({'aba': 'Percurso', 'campo': 'Município de Início', 'msg': 'Campo obrigatório.'})
    if not ct.codigo_municipio_inicio or len(ct.codigo_municipio_inicio.strip()) != 7:
        erros.append({'aba': 'Percurso', 'campo': 'Cód. IBGE Início', 'msg': 'Obrigatório — deve ter exatamente 7 dígitos.'})
    if not ct.uf_fim:
        erros.append({'aba': 'Percurso', 'campo': 'UF de Fim', 'msg': 'Campo obrigatório.'})
    if not ct.municipio_fim:
        erros.append({'aba': 'Percurso', 'campo': 'Município de Fim', 'msg': 'Campo obrigatório.'})
    if not ct.codigo_municipio_fim or len(ct.codigo_municipio_fim.strip()) != 7:
        erros.append({'aba': 'Percurso', 'campo': 'Cód. IBGE Fim', 'msg': 'Obrigatório — deve ter exatamente 7 dígitos.'})

    # Aba Carga e Modal
    if not ct.valor_carga or ct.valor_carga <= 0:
        erros.append({'aba': 'Carga e Modal', 'campo': 'Valor da Carga', 'msg': 'Deve ser maior que zero.'})
    if not ct.peso_bruto_kg or ct.peso_bruto_kg <= 0:
        erros.append({'aba': 'Carga e Modal', 'campo': 'Peso Bruto (kg)', 'msg': 'Deve ser maior que zero.'})
    placa_ef = (ct.placa_veiculo_override or '').strip()
    if not placa_ef and ct.veiculo_id:
        placa_ef = ct.veiculo.get_current_plate() or ''
    if not placa_ef:
        erros.append({'aba': 'Carga e Modal', 'campo': 'Placa do Veículo', 'msg': 'Campo obrigatório.'})
    rntrc_ef = (ct.rntrc_override or '').strip() or (ct.transportadora.rntc if ct.transportadora_id else '')
    if not rntrc_ef:
        erros.append({'aba': 'Carga e Modal', 'campo': 'RNTRC', 'msg': 'Preencha o RNTRC na transportadora ou no campo RNTRC do CT-e.'})

    # Aba Valores e Cobranças
    if not ct.valor_servico or ct.valor_servico <= 0:
        erros.append({'aba': 'Valores e Cobranças', 'campo': 'Valor Total da Prestação', 'msg': 'Deve ser maior que zero.'})
    if not ct.componentes_valor.exists():
        erros.append({'aba': 'Valores e Cobranças', 'campo': 'Prestações', 'msg': 'Adicione ao menos uma prestação (componente do frete).'})

    # Aba Tributação
    cst = ct.cst_icms or ''
    if cst in ('00', '20') and (not ct.base_calculo_icms or ct.base_calculo_icms <= 0):
        erros.append({'aba': 'Tributação', 'campo': 'Base de Cálculo ICMS', 'msg': 'Deve ser maior que zero para o CST selecionado.'})
    if cst in ('00', '20') and (not ct.aliquota_icms or ct.aliquota_icms <= 0):
        erros.append({'aba': 'Tributação', 'campo': 'Alíquota ICMS (%)', 'msg': 'Deve ser maior que zero para o CST selecionado.'})

    # Reforma Tributária — IBS/CBS
    if ct.tipo_cte != '0':
        erros.append({'aba': 'Geral', 'campo': 'Tipo do CT-e',
                       'msg': 'CT-e Complementar/Anulação/Substituto não são suportados para emissão — selecione "0 - CT-e Normal".'})
    cst_reforma = (ct.ibs_cbs_situacao_tributaria or '').strip()
    cclasstrib_reforma = (ct.ibs_cbs_classificacao_tributaria or '').strip()
    if cst_reforma:
        codigos_validos = {c for c, _ in ConhecimentoTransporte.IBS_CBS_CST_CCLASSTRIB_MAP.get(cst_reforma, [])}
        if not cclasstrib_reforma:
            erros.append({'aba': 'Tributação', 'campo': 'cClassTrib',
                          'msg': 'cClassTrib obrigatório quando CST IBS/CBS informado.'})
        elif cclasstrib_reforma not in codigos_validos:
            erros.append({'aba': 'Tributação', 'campo': 'cClassTrib',
                          'msg': f'cClassTrib "{cclasstrib_reforma}" inválido para CST IBS/CBS {cst_reforma}.'})
        if cst_reforma == '200' and (
            (ct.ibs_percentual_reducao or 0) <= 0
            or (ct.cbs_percentual_reducao or 0) <= 0
        ):
            erros.append({'aba': 'Tributação', 'campo': '% Redução IBS/CBS',
                          'msg': 'CST IBS/CBS 200 exige "% Redução IBS" e "% Redução CBS" preenchidos.'})
    elif cclasstrib_reforma:
        erros.append({'aba': 'Tributação', 'campo': 'cClassTrib', 'msg': 'cClassTrib informado sem CST IBS/CBS.'})

    # Aba Documentos
    docs_validos = [d for d in ct.documentos_vinculados.all() if _re.fullmatch(r'\d{44}', d.chave_nfe or '')]
    if not docs_validos:
        erros.append({'aba': 'Documentos (NF-e)', 'campo': 'Chave NF-e', 'msg': 'Adicione ao menos uma NF-e com chave válida (44 dígitos).'})

    return erros


@login_required
def cte_validar(request, pk):
    empresa = _get_empresa(request)
    ct = get_object_or_404(ConhecimentoTransporte, pk=pk, empresa=empresa)
    erros = _validar_cte(ct)
    return JsonResponse({'valido': len(erros) == 0, 'erros': erros})


@login_required
@require_POST
def cte_emitir_ajax(request, pk):
    """AJAX: valida, emite e retorna progresso passo a passo em JSON."""
    import re as _re
    from .services.integranotas import IntegranNotasClient, IntegranNotasError

    empresa = _get_empresa(request)
    ct = get_object_or_404(ConhecimentoTransporte, pk=pk, empresa=empresa)
    steps = []

    def ok(label, msg=None):
        steps.append({'status': 'ok', 'label': label, 'message': msg or ''})

    def erro(label, msg, fix_url=None, fix_label=None, errors=None):
        steps.append({'status': 'error', 'label': label, 'message': msg,
                      'fix_url': fix_url, 'fix_label': fix_label, 'errors': errors or []})
        return JsonResponse({'steps': steps, 'success': False})

    # 1. Status
    if ct.status != 'RASCUNHO':
        return erro('Status do CT-e', f'CT-e já está como "{ct.status}" e não pode ser emitido.')

    # 2. Token / Configuração
    config = ConfiguracaoFiscal.objects.filter(empresa=empresa).first()
    cfg_url = reverse('faturamento:configuracao')
    if not config:
        return erro('Token IntegraNotas', 'Configuração fiscal não encontrada.',
                    fix_url=cfg_url, fix_label='Configurar')
    raw_token = config.get_token()
    if not raw_token:
        return erro('Token IntegraNotas', 'Token não configurado.',
                    fix_url=cfg_url, fix_label='Configurar token')
    ambiente_label = 'Produção' if config.ambiente_nfe == '1' else 'Homologação'
    ok('Token IntegraNotas', f'Ambiente: {ambiente_label}')

    # 3. Emitente
    ie_emit = (empresa.inscricao_estadual or '').strip()
    cnpj_emit = _re.sub(r'\D', '', empresa.cnpj or '')
    emit_erros = []
    if len(cnpj_emit) != 14:
        emit_erros.append('CNPJ inválido')
    if not (empresa.nome or '').strip():
        emit_erros.append('Razão Social não informada')
    if not ie_emit:
        emit_erros.append('IE não informada — preencha a IE ou "ISENTO"')
    if emit_erros:
        return erro('Dados do emitente', ' | '.join(emit_erros),
                    fix_url=cfg_url, fix_label='Corrigir dados do emitente')
    ok('Dados do emitente', f'{empresa.nome} · CNPJ {empresa.cnpj} · IE {ie_emit}')

    # 4. Validação pré-emissão
    erros_ct = _validar_cte(ct)
    if erros_ct:
        edit_url = reverse('faturamento:cte_update', args=[pk])
        err_list = [f"[{e['aba']}] {e['campo']}: {e['msg']}" for e in erros_ct]
        return erro('Validação do CT-e',
                    f'{len(erros_ct)} campo(s) obrigatório(s) não preenchido(s).',
                    fix_url=edit_url, fix_label='Corrigir CT-e', errors=err_list)
    ok('Validação do CT-e', 'Todos os campos obrigatórios preenchidos')

    # 5. Número
    if not ct.numero:
        ultimo = (
            ConhecimentoTransporte.objects
            .filter(empresa=empresa, serie=ct.serie)
            .exclude(pk=pk)
            .order_by('-numero')
            .values_list('numero', flat=True)
            .first()
        )
        ct.numero = (ultimo + 1) if ultimo else (config.numero_cte_inicial or 1)
        ct.save(update_fields=['numero'])

    # Se o número já estiver em uso na mesma série, reajusta automaticamente
    duplicado = (
        ConhecimentoTransporte.objects
        .filter(empresa=empresa, serie=ct.serie, numero=ct.numero)
        .exclude(pk=pk)
        .exists()
    )
    if duplicado:
        numero_anterior = ct.numero
        ultimo = (
            ConhecimentoTransporte.objects
            .filter(empresa=empresa, serie=ct.serie)
            .exclude(pk=pk)
            .order_by('-numero')
            .values_list('numero', flat=True)
            .first()
        )
        ct.numero = (ultimo or 0) + 1
        ct.save(update_fields=['numero'])
        ok('Numeração', f'CT-e {numero_anterior}/{ct.serie} já existia; ajustado para {ct.numero}/{ct.serie}')
    else:
        ok('Numeração', f'CT-e {ct.numero}/{ct.serie}')

    # 6. Transmissão
    try:
        client = IntegranNotasClient(raw_token, config.ambiente_nfe)
        resp = client.emitir_cte(ct)
    except IntegranNotasError as exc:
        def _fmt(e):
            if isinstance(e, dict):
                partes = []
                if e.get('campo'): partes.append(f"Campo: {e['campo']}")
                partes.append(e.get('erro') or e.get('message') or str(e))
                if e.get('detalhes'): partes.append(f"Detalhe: {e['detalhes']}")
                return ' — '.join(partes)
            return str(e)

        # 5008: CT-e já existe no IntegraNotas -> recuperar por chave
        if exc.codigo == 5008:
            _m = _re.search(r'/cte/(\d{44})', str(exc))
            if _m:
                chave_5008 = _m.group(1)
                numero_chave_5008 = _numero_from_cte_chave(chave_5008)
                ct.chave_acesso = chave_5008
                _f = ['chave_acesso']
                if numero_chave_5008 and ct.numero != numero_chave_5008:
                    ct.numero = numero_chave_5008
                    _f.append('numero')
                ct.save(update_fields=_f)

                try:
                    data2 = client.consultar_cte(chave_5008)
                    codigo2 = data2.get('codigo')

                    if codigo2 == 100 or data2.get('sucesso'):
                        protocolo2 = data2.get('protocolo', '')
                        xml2 = data2.get('xml', '')
                        pdf2 = data2.get('pdf', '')
                        ct.status = 'EMITIDO'
                        ct.chave_acesso = chave_5008
                        ct.protocolo = protocolo2
                        ct.xml_autorizacao = xml2
                        ct.pdf_dacte = pdf2
                        ct.data_hora_emissao = timezone.now()
                        _base = ['status', 'chave_acesso', 'protocolo', 'xml_autorizacao', 'pdf_dacte', 'data_hora_emissao']
                        if numero_chave_5008:
                            _base.append('numero')
                        _extra = _upload_fiscal_docs(ct, ct.empresa_id, 'cte', ct.numero, ct.serie, xml2, pdf2)
                        ct.save(update_fields=list(dict.fromkeys(_base + _extra)))

                        steps.append({
                            'status': 'authorized',
                            'label': 'CT-e Autorizado (recuperado) ✓',
                            'protocolo': protocolo2,
                            'chave': chave_5008,
                        })
                        return JsonResponse({
                            'steps': steps, 'success': True, 'authorized': True,
                            'chave': chave_5008, 'protocolo': protocolo2,
                            'has_dacte': bool(pdf2),
                            'dacte_url': reverse('faturamento:cte_dacte', args=[pk]),
                            'detail_url': reverse('faturamento:cte_detail', args=[pk]),
                        })

                    if codigo2 == 5023:
                        ct.chave_acesso = chave_5008
                        ct.data_hora_emissao = timezone.now()
                        _f = ['chave_acesso', 'data_hora_emissao']
                        if numero_chave_5008 and ct.numero != numero_chave_5008:
                            ct.numero = numero_chave_5008
                            _f.append('numero')
                        ct.save(update_fields=_f)
                        steps.append({
                            'status': 'pending',
                            'label': 'Aguardando autorização da SEFAZ',
                            'message': 'CT-e em fila (5008→5023). Verificando automaticamente…',
                            'chave': chave_5008,
                        })
                        return JsonResponse({'steps': steps, 'success': True, 'pending': True, 'chave': chave_5008})
                except Exception:
                    pass

                steps.append({
                    'status': 'pending',
                    'label': 'CT-e já enviado — verifique na SEFAZ',
                    'message': f'IntegraNotas indica CT-e já existente. Chave armazenada: {chave_5008}',
                    'chave': chave_5008,
                })
                return JsonResponse({'steps': steps, 'success': True, 'pending': True, 'chave': chave_5008})

        errs = [_fmt(e) for e in exc.erros] if exc.erros else [str(exc)]
        return erro('Transmissão à SEFAZ', f'Erro IntegraNotas [{exc.codigo}]', errors=errs)
    except Exception as exc:
        return erro('Transmissão à SEFAZ', f'Falha de comunicação: {exc}')

    ok('Transmissão à SEFAZ', 'Dados enviados ao IntegraNotas')

    # 7. Resultado
    chave     = resp.get('chave', '')
    protocolo = resp.get('protocolo', '')
    xml_b64   = resp.get('xml', '')
    pdf_b64   = resp.get('pdf', '')
    codigo    = resp.get('codigo')

    if codigo == 5023:
        numero_chave = _numero_from_cte_chave(chave)
        _f = ['chave_acesso', 'data_hora_emissao']
        if numero_chave and ct.numero != numero_chave:
            ct.numero = numero_chave
            _f.append('numero')
        ct.chave_acesso      = chave
        ct.data_hora_emissao = timezone.now()
        ct.save(update_fields=_f)
        steps.append({'status': 'pending', 'label': 'Aguardando autorização da SEFAZ',
                      'message': 'CT-e em fila (código 5023). Verificando automaticamente…',
                      'chave': chave})
        return JsonResponse({'steps': steps, 'success': True, 'pending': True, 'chave': chave})

    if resp.get('sucesso') or codigo == 100:
        numero_chave = _numero_from_cte_chave(chave)
        if numero_chave and ct.numero != numero_chave:
            ct.numero = numero_chave
        ct.status            = 'EMITIDO'
        ct.chave_acesso      = chave
        ct.protocolo         = protocolo
        ct.xml_autorizacao   = xml_b64
        ct.pdf_dacte         = pdf_b64
        ct.data_hora_emissao = timezone.now()
        _base = ['status', 'chave_acesso', 'protocolo', 'xml_autorizacao',
                 'pdf_dacte', 'data_hora_emissao']
        if numero_chave:
            _base.append('numero')
        _extra = _upload_fiscal_docs(ct, ct.empresa_id, 'cte', ct.numero, ct.serie, xml_b64, pdf_b64)
        ct.save(update_fields=list(dict.fromkeys(_base + _extra)))
        steps.append({'status': 'authorized', 'label': 'CT-e Autorizado pela SEFAZ ✓',
                      'protocolo': protocolo, 'chave': chave})
        return JsonResponse({
            'steps': steps, 'success': True, 'authorized': True,
            'chave': chave, 'protocolo': protocolo,
            'has_dacte': bool(pdf_b64),
            'dacte_url': reverse('faturamento:cte_dacte', args=[pk]),
            'detail_url': reverse('faturamento:cte_detail', args=[pk]),
        })

    return erro('SEFAZ', resp.get('mensagem', 'Resposta inesperada da SEFAZ.'))


@login_required
@require_POST
def cte_consultar_ajax(request, pk):
    """AJAX: consulta status do CT-e na SEFAZ para polling após código 5023."""
    from .services.integranotas import IntegranNotasClient, IntegranNotasError
    empresa = _get_empresa(request)
    ct = get_object_or_404(ConhecimentoTransporte, pk=pk, empresa=empresa)
    if not ct.chave_acesso:
        return JsonResponse({'status': 'error', 'mensagem': 'CT-e sem chave de acesso.'})
    config = ConfiguracaoFiscal.objects.filter(empresa=empresa).first()
    if not config or not config.get_token():
        return JsonResponse({'status': 'error', 'mensagem': 'Token não configurado.'})
    try:
        client = IntegranNotasClient(config.get_token(), config.ambiente_nfe)
        data = client.consultar_cte(ct.chave_acesso)
        codigo = data.get('codigo')
        if codigo == 100 or data.get('sucesso'):
            fields = []
            if data.get('protocolo') and not ct.protocolo:
                ct.protocolo = data['protocolo']; fields.append('protocolo')
            if data.get('xml') and not ct.xml_autorizacao:
                ct.xml_autorizacao = data['xml']; fields.append('xml_autorizacao')
            if data.get('pdf') and not ct.pdf_dacte:
                ct.pdf_dacte = data['pdf']; fields.append('pdf_dacte')
            if ct.status != 'EMITIDO':
                ct.status = 'EMITIDO'; fields.append('status')
            if fields:
                _extra = _upload_fiscal_docs(ct, ct.empresa_id, 'cte', ct.numero, ct.serie,
                                             data.get('xml'), data.get('pdf'))
                ct.save(update_fields=list(dict.fromkeys(fields + _extra)))
            return JsonResponse({
                'status': 'authorized',
                'protocolo': ct.protocolo or '',
                'has_dacte': bool(ct.pdf_dacte),
                'dacte_url': reverse('faturamento:cte_dacte', args=[pk]),
                'detail_url': reverse('faturamento:cte_detail', args=[pk]),
            })
        elif codigo == 5023:
            return JsonResponse({'status': 'pending'})
        else:
            return JsonResponse({'status': 'rejected',
                                 'codigo': codigo,
                                 'mensagem': data.get('mensagem', f'Código {codigo}')})
    except Exception as exc:
        return JsonResponse({'status': 'error', 'mensagem': str(exc)})


@login_required
def cte_emitir(request, pk):
    empresa = _get_empresa(request)
    ct = get_object_or_404(ConhecimentoTransporte, pk=pk, empresa=empresa)
    if ct.status != 'RASCUNHO':
        messages.error(request, 'CT-e ja foi emitido ou cancelado.')
        return redirect('faturamento:cte_detail', pk=pk)
    erros_pre = _validar_cte(ct)
    if erros_pre:
        for e in erros_pre:
            messages.error(request, f"[{e['aba']}] {e['campo']}: {e['msg']}")
        return redirect('faturamento:cte_update', pk=pk)
    try:
        config = empresa.configuracao_fiscal
    except Exception:
        messages.error(request, 'Emitente IntegraNotas não configurado. Peça ao administrador da plataforma para criá-lo (Empresas → Listar).')
        return redirect('faturamento:cte_detail', pk=pk)
    if not ct.numero:
        ultimo = (
            ConhecimentoTransporte.objects
            .filter(empresa=empresa, serie=ct.serie)
            .exclude(pk=pk)
            .order_by('-numero')
            .values_list('numero', flat=True)
            .first()
        )
        ct.numero = (ultimo or 0) + 1
        ct.save(update_fields=['numero'])

    duplicado = (
        ConhecimentoTransporte.objects
        .filter(empresa=empresa, serie=ct.serie, numero=ct.numero)
        .exclude(pk=pk)
        .exists()
    )
    if duplicado:
        numero_anterior = ct.numero
        ultimo = (
            ConhecimentoTransporte.objects
            .filter(empresa=empresa, serie=ct.serie)
            .exclude(pk=pk)
            .order_by('-numero')
            .values_list('numero', flat=True)
            .first()
        )
        ct.numero = (ultimo or 0) + 1
        ct.save(update_fields=['numero'])
        messages.warning(request, f'Número {numero_anterior}/{ct.serie} já estava em uso. Ajustado para {ct.numero}/{ct.serie}.')
    from .services.integranotas import IntegranNotasClient, IntegranNotasError
    client = IntegranNotasClient(token=config.get_token(), ambiente=config.ambiente_nfe)
    try:
        resp = client.emitir_cte(ct)
        if resp.get('codigo') == 5023:
            import time
            time.sleep(4)
            resp = client.consultar_cte(resp.get('chave', ''))
        if resp.get('sucesso') or resp.get('codigo') == 100:
            chave_resp = resp.get('chave', '')
            numero_chave = _numero_from_cte_chave(chave_resp)
            if numero_chave and ct.numero != numero_chave:
                ct.numero = numero_chave
            ct.status = 'EMITIDO'
            ct.chave_acesso = chave_resp
            ct.protocolo = resp.get('protocolo', '')
            ct.xml_autorizacao = resp.get('xml', '')
            ct.pdf_dacte = resp.get('pdf', '')
            ct.data_hora_emissao = timezone.now()
            _upload_fiscal_docs(ct, ct.empresa_id, 'cte', ct.numero, ct.serie,
                                resp.get('xml'), resp.get('pdf'))
            ct.save()
            messages.success(request, f'CT-e {ct.numero} emitido! Chave: {ct.chave_acesso}')
        else:
            messages.error(request, f'SEFAZ: {resp.get("mensagem", "Erro desconhecido")}')
    except IntegranNotasError as e:
        if e.codigo == 5008:
            import re as _re
            _m = _re.search(r'/cte/(\d{44})', str(e))
            if _m:
                chave_5008 = _m.group(1)
                numero_chave_5008 = _numero_from_cte_chave(chave_5008)
                ct.chave_acesso = chave_5008
                _f = ['chave_acesso']
                if numero_chave_5008 and ct.numero != numero_chave_5008:
                    ct.numero = numero_chave_5008
                    _f.append('numero')
                ct.save(update_fields=_f)
                try:
                    data2 = client.consultar_cte(chave_5008)
                    if data2.get('codigo') == 100 or data2.get('sucesso'):
                        xml2 = data2.get('xml', '')
                        pdf2 = data2.get('pdf', '')
                        ct.protocolo = data2.get('protocolo', '')
                        ct.xml_autorizacao = xml2
                        ct.pdf_dacte = pdf2
                        ct.status = 'EMITIDO'
                        ct.data_hora_emissao = timezone.now()
                        _upload_fiscal_docs(ct, ct.empresa_id, 'cte', ct.numero, ct.serie, xml2, pdf2)
                        ct.save()
                        messages.success(request, f'CT-e {ct.numero}/{ct.serie} autorizado (recuperado)! Chave: {chave_5008}')
                        return redirect('faturamento:cte_detail', pk=pk)
                    if data2.get('codigo') == 5023:
                        ct.data_hora_emissao = timezone.now()
                        ct.save(update_fields=['data_hora_emissao'])
                        messages.info(request, f'CT-e {ct.numero}/{ct.serie} em processamento SEFAZ. Chave: {chave_5008}')
                        return redirect('faturamento:cte_detail', pk=pk)
                except Exception:
                    pass
                messages.warning(request, f'CT-e já enviado ao IntegraNotas. Chave armazenada: {chave_5008}. Use "Verificar na SEFAZ".')
                return redirect('faturamento:cte_detail', pk=pk)

        erros = '; '.join(str(x) for x in e.erros) if e.erros else str(e)
        messages.error(request, f'Erro IntegraNotas [{e.codigo}]: {erros}')
    except Exception as e:
        messages.error(request, f'Erro inesperado: {e}')
    return redirect('faturamento:cte_detail', pk=pk)


@login_required
def cte_cancelar(request, pk):
    empresa = _get_empresa(request)
    ct = get_object_or_404(ConhecimentoTransporte, pk=pk, empresa=empresa)
    if ct.status != 'EMITIDO':
        messages.error(request, 'Apenas CT-e emitido pode ser cancelado.')
        return redirect('faturamento:cte_detail', pk=pk)
    if request.method == 'POST':
        form = CancelarCTeForm(request.POST)
        if form.is_valid():
            try:
                config = empresa.configuracao_fiscal
                from .services.integranotas import IntegranNotasClient, IntegranNotasError
                client = IntegranNotasClient(token=config.get_token(), ambiente=config.ambiente_nfe)
                resp_cancel = client.cancelar_cte(ct.chave_acesso, form.cleaned_data['justificativa'])
                ct.status = 'CANCELADO'
                ct.motivo_cancelamento = form.cleaned_data['justificativa']
                ct.data_cancelamento = timezone.now()
                if resp_cancel.get('xml'):
                    ct.xml_cancelamento = resp_cancel['xml']
                    _upload_fiscal_docs(ct, ct.empresa_id, 'cte', ct.numero, ct.serie,
                                        xml_b64=resp_cancel['xml'], cancel=True)
                ct.save()
                messages.success(request, 'CT-e cancelado com sucesso.')
                return redirect('faturamento:cte_detail', pk=pk)
            except Exception as e:
                messages.error(request, f'Erro ao cancelar: {e}')
    else:
        form = CancelarCTeForm()
    return render(request, 'faturamento/cte/cancelar.html', {'form': form, 'ct': ct})


@login_required
def cte_dacte(request, pk):
    import base64
    from django.shortcuts import redirect as _redirect
    empresa = _get_empresa(request)
    ct = get_object_or_404(ConhecimentoTransporte, pk=pk, empresa=empresa)
    if ct.pdf_dacte_url:
        return _redirect(ct.pdf_dacte_url)
    if ct.pdf_dacte:
        pdf_bytes = base64.b64decode(ct.pdf_dacte)
        r = HttpResponse(pdf_bytes, content_type='application/pdf')
        r['Content-Disposition'] = f'inline; filename="DACTE_{ct.numero}_{ct.serie}.pdf"'
        return r
    if not ct.chave_acesso:
        messages.error(request, 'DACTE não disponível — CT-e não possui chave de acesso.')
        return redirect('faturamento:cte_detail', pk=pk)
    try:
        config = empresa.configuracao_fiscal
        from .services.integranotas import IntegranNotasClient
        client = IntegranNotasClient(token=config.get_token(), ambiente=config.ambiente_nfe)
        data = client.consultar_cte(ct.chave_acesso)
        pdf_b64 = data.get('pdf', '')
        if pdf_b64:
            ct.pdf_dacte = pdf_b64
            _extra = _upload_fiscal_docs(ct, ct.empresa_id, 'cte', ct.numero, ct.serie, pdf_b64=pdf_b64)
            ct.save(update_fields=list(dict.fromkeys(['pdf_dacte'] + _extra)))
            if ct.pdf_dacte_url:
                return _redirect(ct.pdf_dacte_url)
            pdf_bytes = base64.b64decode(ct.pdf_dacte or pdf_b64)
            r = HttpResponse(pdf_bytes, content_type='application/pdf')
            r['Content-Disposition'] = f'inline; filename="DACTE_{ct.numero}_{ct.serie}.pdf"'
            return r
        messages.error(request, 'DACTE não disponível na IntegraNotas. O CT-e pode estar em processamento — tente novamente em instantes.')
    except Exception as e:
        messages.error(request, f'Erro ao obter DACTE: {e}')
    return redirect('faturamento:cte_detail', pk=pk)


@login_required
@require_POST
def cte_consultar(request, pk):
    """Consulta status do CT-e na SEFAZ e atualiza protocolo/DACTE se autorizado."""
    from .services.integranotas import IntegranNotasClient, IntegranNotasError
    empresa = _get_empresa(request)
    ct = get_object_or_404(ConhecimentoTransporte, pk=pk, empresa=empresa)
    if not ct.chave_acesso:
        messages.error(request, 'CT-e sem chave de acesso — não é possível consultar.')
        return redirect('faturamento:cte_detail', pk=pk)
    try:
        config = empresa.configuracao_fiscal
        client = IntegranNotasClient(token=config.get_token(), ambiente=config.ambiente_nfe)
        resp = client.consultar_cte(ct.chave_acesso)
        if resp.get('sucesso') or resp.get('codigo') == 100:
            fields = []
            if resp.get('protocolo') and not ct.protocolo:
                ct.protocolo = resp['protocolo']
                fields.append('protocolo')
            if resp.get('xml') and not ct.xml_autorizacao:
                ct.xml_autorizacao = resp['xml']
                fields.append('xml_autorizacao')
            if resp.get('pdf') and not ct.pdf_dacte:
                ct.pdf_dacte = resp['pdf']
                fields.append('pdf_dacte')
            if fields:
                _extra = _upload_fiscal_docs(ct, ct.empresa_id, 'cte', ct.numero, ct.serie,
                                             resp.get('xml'), resp.get('pdf'))
                ct.save(update_fields=list(dict.fromkeys(fields + _extra)))
            messages.success(request, f'CT-e autorizado. Protocolo: {ct.protocolo}')
        else:
            messages.warning(request, f'SEFAZ: {resp.get("mensagem", "Aguardando autorização.")}')
    except IntegranNotasError as exc:
        messages.error(request, f'Erro [{exc.codigo}]: {exc}')
    except Exception as exc:
        messages.error(request, f'Falha na comunicação: {exc}')
    return redirect('faturamento:cte_detail', pk=pk)


@login_required
def cte_carta_correcao(request, pk):
    import json
    from .services.integranotas import IntegranNotasClient, IntegranNotasError
    empresa = _get_empresa(request)
    ct = get_object_or_404(ConhecimentoTransporte, pk=pk, empresa=empresa)
    if ct.status != 'EMITIDO' or not ct.chave_acesso:
        messages.error(request, 'CC-e só pode ser enviada para CT-e autorizado.')
        return redirect('faturamento:cte_detail', pk=pk)

    cartas = ct.cartas_correcao.all()
    proxima_sequencia = cartas.count() + 1

    if request.method == 'POST':
        # Recupera JSON com múltiplas correções
        correcoes_json = request.POST.get('correcoes_json', '[]').strip()
        sequencia_manual_raw = request.POST.get('sequencia', '').strip()
        sequencia_manual = None

        # Valida sequência manual se informada
        if sequencia_manual_raw:
            try:
                sequencia_manual = int(sequencia_manual_raw)
                if sequencia_manual <= 0:
                    raise ValueError('Sequência deve ser maior que zero')
            except (ValueError, TypeError):
                messages.error(request, 'Sequência inválida. Informe um número inteiro positivo.')
                return render(request, 'faturamento/cte/carta_correcao_form.html', {
                    'ct': ct,
                    'cartas': cartas,
                    'proxima_sequencia': proxima_sequencia,
                    'sequencia': sequencia_manual_raw,
                })

        # Valida e carrega correções
        try:
            correcoes = json.loads(correcoes_json)
        except json.JSONDecodeError:
            messages.error(request, 'Erro ao processar correções. Formato inválido.')
            return render(request, 'faturamento/cte/carta_correcao_form.html', {
                'ct': ct,
                'cartas': cartas,
                'proxima_sequencia': proxima_sequencia,
                'sequencia': sequencia_manual_raw,
            })

        # Valida que há ao menos uma correção
        if not correcoes or len(correcoes) == 0:
            messages.error(request, 'Adicione pelo menos uma correção.')
            return render(request, 'faturamento/cte/carta_correcao_form.html', {
                'ct': ct,
                'cartas': cartas,
                'proxima_sequencia': proxima_sequencia,
                'sequencia': sequencia_manual_raw,
            })

        # Valida campos obrigatórios em cada correção
        for i, corr in enumerate(correcoes):
            if not corr.get('grupo_corrigido', '').strip():
                messages.error(request, f'Linha {i+1}: Grupo a ser alterado é obrigatório.')
                return render(request, 'faturamento/cte/carta_correcao_form.html', {
                    'ct': ct,
                    'cartas': cartas,
                    'proxima_sequencia': proxima_sequencia,
                    'sequencia': sequencia_manual_raw,
                })
            if not corr.get('campo_corrigido', '').strip():
                messages.error(request, f'Linha {i+1}: Campo a ser alterado é obrigatório.')
                return render(request, 'faturamento/cte/carta_correcao_form.html', {
                    'ct': ct,
                    'cartas': cartas,
                    'proxima_sequencia': proxima_sequencia,
                    'sequencia': sequencia_manual_raw,
                })
            if not corr.get('valor_corrigido', '').strip():
                messages.error(request, f'Linha {i+1}: Valor alterado é obrigatório.')
                return render(request, 'faturamento/cte/carta_correcao_form.html', {
                    'ct': ct,
                    'cartas': cartas,
                    'proxima_sequencia': proxima_sequencia,
                    'sequencia': sequencia_manual_raw,
                })
            # Limpa numero_item_grupo_corrigido se vazio
            if not str(corr.get('numero_item_grupo_corrigido', '')).strip():
                corr.pop('numero_item_grupo_corrigido', None)
                corr.pop('indice_item', None)  # compatibilidade com JSON antigo

        try:
            config = empresa.configuracao_fiscal
            client = IntegranNotasClient(token=config.get_token(), ambiente=config.ambiente_nfe)
            resultado = client.correcao_cte(ct.chave_acesso, correcoes, sequencia=sequencia_manual)
        except IntegranNotasError as exc:
            erros = '; '.join(str(e) for e in (exc.erros or []))
            msg = f'Erro [{exc.codigo}]: {exc}'
            if erros:
                msg = f'{msg} — {erros}'
            messages.error(request, msg)
            return render(request, 'faturamento/cte/carta_correcao_form.html', {
                'ct': ct,
                'cartas': cartas,
                'proxima_sequencia': proxima_sequencia,
                'sequencia': sequencia_manual_raw,
            })
        except Exception as exc:
            messages.error(request, f'Falha na comunicação: {exc}')
            return render(request, 'faturamento/cte/carta_correcao_form.html', {
                'ct': ct,
                'cartas': cartas,
                'proxima_sequencia': proxima_sequencia,
                'sequencia': sequencia_manual_raw,
            })

        sequencia_api = (
            resultado.get('numero_carta_correcao')
            or resultado.get('sequencial')
            or proxima_sequencia
        )
        try:
            sequencia_api = int(sequencia_api)
        except Exception:
            sequencia_api = proxima_sequencia

        protocolo = resultado.get('protocolo', '') or resultado.get('numero_protocolo', '')
        xml_retorno = (
            resultado.get('xml_carta_correcao', '')
            or resultado.get('xml', '')
        )

        CartaCorrecaoCTe.objects.update_or_create(
            cte=ct,
            sequencia=sequencia_api,
            defaults={
                'correcao': json.dumps(correcoes),
                'protocolo': protocolo,
                'xml_retorno': xml_retorno,
                'criado_por': request.user,
            },
        )

        if sequencia_api != proxima_sequencia:
            messages.success(
                request,
                f'Carta de Correção ({len(correcoes)} linha(s)) registrada com sucesso (sequência: {sequencia_api}).',
            )
        else:
            messages.success(request, f'Carta de Correção nº {sequencia_api} ({len(correcoes)} linha(s)) enviada com sucesso.')
        return redirect('faturamento:cte_detail', pk=pk)

    return render(request, 'faturamento/cte/carta_correcao_form.html', {
        'ct': ct,
        'cartas': cartas,
        'proxima_sequencia': proxima_sequencia,
        'sequencia': '',
    })


@login_required
def cte_cce_print(request, cte_pk, cc_pk):
    """Página de impressão da Carta de Correção (CC-e) do CT-e."""
    import json as _json
    empresa = _get_empresa(request)
    ct = get_object_or_404(ConhecimentoTransporte, pk=cte_pk, empresa=empresa)
    cc = get_object_or_404(CartaCorrecaoCTe, pk=cc_pk, cte=ct)
    try:
        correcoes = _json.loads(cc.correcao or '[]')
    except Exception:
        correcoes = []
    return render(request, 'faturamento/cte/cce_print.html', {
        'ct': ct,
        'cc': cc,
        'correcoes': correcoes,
        'empresa': empresa,
    })


@login_required
def cte_cce_xml(request, cte_pk, cc_pk):
    """Download do XML da Carta de Correção (CC-e) do CT-e."""
    import base64
    empresa = _get_empresa(request)
    ct = get_object_or_404(ConhecimentoTransporte, pk=cte_pk, empresa=empresa)
    cc = get_object_or_404(CartaCorrecaoCTe, pk=cc_pk, cte=ct)
    if not cc.xml_retorno:
        messages.error(request, 'XML da CC-e não disponível.')
        return redirect('faturamento:cte_detail', pk=cte_pk)
    try:
        xml_bytes = base64.b64decode(cc.xml_retorno)
    except Exception:
        xml_bytes = cc.xml_retorno.encode('utf-8')
    chave = ct.chave_acesso or f'CTE{ct.numero}_{ct.serie}'
    response = HttpResponse(xml_bytes, content_type='application/xml; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="CCe_{chave}_seq{cc.sequencia}.xml"'
    return response


@login_required
def cte_manifestar_desacordo(request, pk):
    from .services.integranotas import IntegranNotasClient, IntegranNotasError
    empresa = _get_empresa(request)
    ct = get_object_or_404(ConhecimentoTransporte, pk=pk, empresa=empresa)
    if ct.status != 'EMITIDO' or not ct.chave_acesso:
        messages.error(request, 'Desacordo só pode ser registrado para CT-e autorizado.')
        return redirect('faturamento:cte_detail', pk=pk)
    if ct.desacordo_protocolo:
        messages.info(request, 'Este CT-e já possui desacordo registrado.')
        return redirect('faturamento:cte_detail', pk=pk)

    if request.method == 'POST':
        descricao = request.POST.get('descricao', '').strip()
        if len(descricao) < 15:
            messages.error(request, 'A descrição do desacordo deve ter pelo menos 15 caracteres.')
            return render(request, 'faturamento/cte/manifestar_desacordo_form.html',
                          {'ct': ct, 'descricao': descricao})
        try:
            config = empresa.configuracao_fiscal
            client = IntegranNotasClient(token=config.get_token(), ambiente=config.ambiente_nfe)
            resultado = client.manifesta_desacordo_cte(ct.chave_acesso, descricao)
        except IntegranNotasError as exc:
            messages.error(request, f'Erro [{exc.codigo}]: {exc}')
            return render(request, 'faturamento/cte/manifestar_desacordo_form.html',
                          {'ct': ct, 'descricao': descricao})
        except Exception as exc:
            messages.error(request, f'Falha na comunicação: {exc}')
            return render(request, 'faturamento/cte/manifestar_desacordo_form.html',
                          {'ct': ct, 'descricao': descricao})

        ct.desacordo_descricao = descricao
        ct.desacordo_protocolo = resultado.get('protocolo', '') or resultado.get('numero_protocolo', '')
        ct.desacordo_data = timezone.now()
        ct.save(update_fields=['desacordo_descricao', 'desacordo_protocolo', 'desacordo_data'])
        messages.success(request, 'Manifesta Desacordo registrado com sucesso na SEFAZ.')
        return redirect('faturamento:cte_detail', pk=pk)

    return render(request, 'faturamento/cte/manifestar_desacordo_form.html', {'ct': ct})


@login_required
def cte_insucesso_entrega(request, pk):
    from .services.integranotas import IntegranNotasClient, IntegranNotasError
    import re as _re
    empresa = _get_empresa(request)
    ct = get_object_or_404(ConhecimentoTransporte, pk=pk, empresa=empresa)
    if ct.status != 'EMITIDO' or not ct.chave_acesso:
        messages.error(request, 'Insucesso só pode ser registrado para CT-e autorizado.')
        return redirect('faturamento:cte_detail', pk=pk)
    if ct.insucesso_protocolo:
        messages.info(request, 'Este CT-e já possui insucesso na entrega registrado.')
        return redirect('faturamento:cte_detail', pk=pk)

    MOTIVOS = [
        ('01', '01 — Destinatário não encontrado'),
        ('02', '02 — Recusa do destinatário'),
        ('03', '03 — Endereço errado'),
        ('04', '04 — Outros'),
    ]

    if request.method == 'POST':
        data_hora      = request.POST.get('data_hora_tentativa', '').strip()
        num_tentativas = request.POST.get('numero_tentativas', '1').strip()
        motivo         = request.POST.get('motivo', '').strip()
        justificativa  = request.POST.get('justificativa', '').strip()
        latitude       = request.POST.get('latitude', '').strip()
        longitude      = request.POST.get('longitude', '').strip()
        chave_nfe      = request.POST.get('chave_nfe', '').strip()

        erros = []
        if not data_hora:
            erros.append('Data e hora da tentativa são obrigatórios.')
        if motivo not in [m[0] for m in MOTIVOS]:
            erros.append('Selecione um motivo válido.')
        if len(justificativa) < 15:
            erros.append('A justificativa deve ter pelo menos 15 caracteres.')
        if not _re.fullmatch(r'\d{44}', chave_nfe):
            erros.append('Informe a chave da NF-e com exatamente 44 dígitos.')

        ctx = {'ct': ct, 'motivos': MOTIVOS,
               'data_hora_tentativa': data_hora, 'numero_tentativas': num_tentativas,
               'motivo': motivo, 'justificativa': justificativa,
               'latitude': latitude, 'longitude': longitude, 'chave_nfe': chave_nfe}
        if erros:
            for e in erros:
                messages.error(request, e)
            return render(request, 'faturamento/cte/insucesso_entrega_form.html', ctx)

        payload = {
            'data_hora_tentativa': data_hora,
            'numero_tentativas': num_tentativas,
            'motivo': motivo,
            'justificativa': justificativa,
            'chave_nfe': chave_nfe,
        }
        if latitude:
            payload['latitude'] = latitude
        if longitude:
            payload['longitude'] = longitude

        try:
            config = empresa.configuracao_fiscal
            client = IntegranNotasClient(token=config.get_token(), ambiente=config.ambiente_nfe)
            resultado = client.insucesso_entrega_cte(ct.chave_acesso, payload)
        except IntegranNotasError as exc:
            messages.error(request, f'Erro [{exc.codigo}]: {exc}')
            return render(request, 'faturamento/cte/insucesso_entrega_form.html', ctx)
        except Exception as exc:
            messages.error(request, f'Falha na comunicação: {exc}')
            return render(request, 'faturamento/cte/insucesso_entrega_form.html', ctx)

        ct.insucesso_protocolo     = resultado.get('protocolo', '') or resultado.get('numero_protocolo', '')
        ct.insucesso_data          = timezone.now()
        ct.insucesso_motivo        = motivo
        ct.insucesso_justificativa = justificativa
        ct.insucesso_chave_nfe     = chave_nfe
        ct.save(update_fields=[
            'insucesso_protocolo', 'insucesso_data',
            'insucesso_motivo', 'insucesso_justificativa', 'insucesso_chave_nfe',
        ])
        messages.success(request, 'Insucesso na Entrega registrado com sucesso na SEFAZ.')
        return redirect('faturamento:cte_detail', pk=pk)

    return render(request, 'faturamento/cte/insucesso_entrega_form.html',
                  {'ct': ct, 'motivos': MOTIVOS})


@login_required
def cte_preview(request, pk):
    """Abre o PDF preview do CT-e diretamente no browser."""
    from .services.integranotas import IntegranNotasClient, IntegranNotasError
    import base64
    empresa = _get_empresa(request)
    ct = get_object_or_404(ConhecimentoTransporte, pk=pk, empresa=empresa)
    if not ct.chave_acesso:
        messages.error(request, 'CT-e ainda não foi emitido — sem chave para gerar preview.')
        return redirect('faturamento:cte_detail', pk=pk)
    try:
        config = empresa.configuracao_fiscal
        client = IntegranNotasClient(token=config.get_token(), ambiente=config.ambiente_nfe)
        data = client.preview_cte(ct.chave_acesso)
        pdf_b64 = data.get('pdf', '')
        if not pdf_b64:
            messages.error(request, 'IntegraNota não retornou PDF de preview.')
            return redirect('faturamento:cte_detail', pk=pk)
        pdf_bytes = base64.b64decode(pdf_b64)
        r = HttpResponse(pdf_bytes, content_type='application/pdf')
        r['Content-Disposition'] = f'inline; filename="preview_CTE_{ct.numero}_{ct.serie}.pdf"'
        return r
    except IntegranNotasError as exc:
        messages.error(request, f'Erro [{exc.codigo}]: {exc}')
    except Exception as exc:
        messages.error(request, f'Falha na comunicação: {exc}')
    return redirect('faturamento:cte_detail', pk=pk)


@login_required
def cte_clone(request, pk):
    """Clona um CT-e como novo rascunho (sem número, sem chave)."""
    empresa = _get_empresa(request)
    ct = get_object_or_404(ConhecimentoTransporte, pk=pk, empresa=empresa)
    docs = list(ct.documentos_vinculados.all())
    comps = list(ct.componentes_valor.all())

    ct.pk = None
    ct.numero = None
    ct.chave_acesso = ''
    ct.protocolo = ''
    ct.xml_autorizacao = ''
    ct.xml_cancelamento = ''
    ct.pdf_dacte = ''
    ct.status = 'RASCUNHO'
    ct.motivo_cancelamento = ''
    ct.data_cancelamento = None
    ct.data_hora_emissao = None
    ct.desacordo_descricao = ''
    ct.desacordo_protocolo = ''
    ct.desacordo_data = None
    ct.save()

    for d in docs:
        d.pk = None
        d.cte = ct
        d.save()
    for c in comps:
        c.pk = None
        c.cte = ct
        c.save()

    messages.success(request, f'CT-e clonado como rascunho #{ct.pk}. Revise os dados antes de emitir.')
    return redirect('faturamento:cte_update', pk=ct.pk)


@login_required
def cte_xml(request, pk):
    """Download do XML autorizado do CT-e (Supabase URL ou base64)."""
    import base64
    import urllib.request as _ur
    from .services.integranotas import IntegranNotasClient
    empresa = _get_empresa(request)
    ct = get_object_or_404(ConhecimentoTransporte, pk=pk, empresa=empresa)
    if ct.xml_autorizacao_url:
        try:
            xml_bytes = _ur.urlopen(ct.xml_autorizacao_url, timeout=20).read()
            resp = HttpResponse(xml_bytes, content_type='application/xml; charset=utf-8')
            resp['Content-Disposition'] = f'attachment; filename="CTE_{ct.numero}_{ct.serie}.xml"'
            return resp
        except Exception:
            # Se a URL estiver indisponível, tenta as demais fontes abaixo.
            pass
    if not ct.xml_autorizacao and ct.chave_acesso:
        try:
            config = empresa.configuracao_fiscal
            client = IntegranNotasClient(token=config.get_token(), ambiente=config.ambiente_nfe)
            resp_api = client.consultar_cte(ct.chave_acesso)
            if resp_api.get('xml'):
                ct.xml_autorizacao = resp_api['xml']
                fields = ['xml_autorizacao']
                if resp_api.get('protocolo') and not ct.protocolo:
                    ct.protocolo = resp_api['protocolo']
                    fields.append('protocolo')
                _extra = _upload_fiscal_docs(ct, ct.empresa_id, 'cte', ct.numero, ct.serie,
                                             xml_b64=resp_api['xml'])
                ct.save(update_fields=list(dict.fromkeys(fields + _extra)))
                if ct.xml_autorizacao_url:
                    return _redirect(ct.xml_autorizacao_url)
        except Exception:
            pass
    if not ct.xml_autorizacao:
        messages.error(request, 'XML de autorização não disponível para este CT-e.')
        return redirect('faturamento:cte_detail', pk=pk)
    xml_bytes = base64.b64decode(ct.xml_autorizacao)
    resp = HttpResponse(xml_bytes, content_type='application/xml; charset=utf-8')
    resp['Content-Disposition'] = f'attachment; filename="CTE_{ct.numero}_{ct.serie}.xml"'
    return resp


@login_required
def cte_xml_cancelamento(request, pk):
    """Download do XML de cancelamento do CT-e (Supabase URL ou base64)."""
    import base64
    import urllib.request as _ur
    empresa = _get_empresa(request)
    ct = get_object_or_404(ConhecimentoTransporte, pk=pk, empresa=empresa)
    if ct.xml_cancelamento_url:
        try:
            xml_bytes = _ur.urlopen(ct.xml_cancelamento_url, timeout=20).read()
            resp = HttpResponse(xml_bytes, content_type='application/xml; charset=utf-8')
            resp['Content-Disposition'] = f'attachment; filename="CANCEL_CTE_{ct.numero}_{ct.serie}.xml"'
            return resp
        except Exception:
            pass
    if not ct.xml_cancelamento:
        messages.error(request, 'XML de cancelamento não disponível para este CT-e.')
        return redirect('faturamento:cte_detail', pk=pk)
    xml_bytes = base64.b64decode(ct.xml_cancelamento)
    resp = HttpResponse(xml_bytes, content_type='application/xml; charset=utf-8')
    resp['Content-Disposition'] = f'attachment; filename="CANCEL_CTE_{ct.numero}_{ct.serie}.xml"'
    return resp


@login_required
@require_POST
def cte_reenviar_email(request, pk):
    """Reenvia o DACTE e XML por e-mail para o destinatário e remetente do CT-e."""
    import base64
    from django.core.mail import EmailMessage
    from .services.integranotas import IntegranNotasClient, IntegranNotasError
    empresa = _get_empresa(request)
    ct = get_object_or_404(ConhecimentoTransporte, pk=pk, empresa=empresa)
    if ct.status != 'EMITIDO' or (not ct.pdf_dacte and not ct.pdf_dacte_url
                                   and not ct.xml_autorizacao and not ct.xml_autorizacao_url
                                   and not ct.chave_acesso):
        messages.error(request, 'CT-e não autorizado ou documentos não disponíveis.')
        return redirect('faturamento:cte_detail', pk=pk)

    # Busca lazy do XML se ainda não estiver salvo (nem em Storage nem em base64)
    if not ct.xml_autorizacao and not ct.xml_autorizacao_url and ct.chave_acesso:
        try:
            config = empresa.configuracao_fiscal
            client = IntegranNotasClient(token=config.get_token(), ambiente=config.ambiente_nfe)
            resp_api = client.consultar_cte(ct.chave_acesso)
            if resp_api.get('xml'):
                ct.xml_autorizacao = resp_api['xml']
                fields = ['xml_autorizacao']
                if resp_api.get('protocolo') and not ct.protocolo:
                    ct.protocolo = resp_api['protocolo']
                    fields.append('protocolo')
                _extra = _upload_fiscal_docs(ct, ct.empresa_id, 'cte', ct.numero, ct.serie,
                                             xml_b64=resp_api['xml'])
                ct.save(update_fields=list(dict.fromkeys(fields + _extra)))
        except Exception:
            pass

    destinatarios = []
    for parte in [ct.remetente, ct.destinatario, ct.tomador]:
        email = getattr(parte, 'email', '') or ''
        if email and email not in destinatarios:
            destinatarios.append(email)

    email_extra = request.POST.get('email_extra', '').strip()
    if email_extra and email_extra not in destinatarios:
        destinatarios.append(email_extra)

    if not destinatarios:
        messages.error(request, 'Nenhum e-mail cadastrado para remetente, destinatário ou tomador.')
        return redirect('faturamento:cte_detail', pk=pk)

    try:
        msg = EmailMessage(
            subject=f'CT-e {ct.numero}/{ct.serie} — DACTE e XML — {empresa.nome}',
            body=(
                f'Segue em anexo o DACTE e o XML do CT-e {ct.numero}/{ct.serie}.\n\n'
                f'Chave: {ct.chave_acesso}\n'
                f'Protocolo: {ct.protocolo}\n\n'
                f'{empresa.nome}'
            ),
            from_email=None,
            to=destinatarios,
        )
        if ct.pdf_dacte_url:
            import urllib.request as _ur
            try:
                pdf_bytes = _ur.urlopen(ct.pdf_dacte_url).read()
                msg.attach(f'DACTE_{ct.numero}_{ct.serie}.pdf', pdf_bytes, 'application/pdf')
            except Exception:
                pass
        elif ct.pdf_dacte:
            pdf_bytes = base64.b64decode(ct.pdf_dacte)
            msg.attach(f'DACTE_{ct.numero}_{ct.serie}.pdf', pdf_bytes, 'application/pdf')
        if ct.xml_autorizacao_url:
            import urllib.request as _ur
            try:
                xml_bytes = _ur.urlopen(ct.xml_autorizacao_url).read()
                msg.attach(f'CTE_{ct.numero}_{ct.serie}.xml', xml_bytes, 'application/xml')
            except Exception:
                pass
        elif ct.xml_autorizacao:
            xml_bytes = base64.b64decode(ct.xml_autorizacao)
            msg.attach(f'CTE_{ct.numero}_{ct.serie}.xml', xml_bytes, 'application/xml')
        msg.send()
        messages.success(request, f'CT-e enviado para: {", ".join(destinatarios)}')
    except Exception as exc:
        messages.error(request, f'Falha ao enviar e-mail: {exc}')
    return redirect('faturamento:cte_detail', pk=pk)


# ═══════════════════════════════════════════════════════════════════
#  MDF-e — Views
# ═══════════════════════════════════════════════════════════════════

@login_required
def mdfe_list(request):
    empresa = _get_empresa(request)
    if not empresa:
        return redirect('dashboard:index')
    qs = ManifestoDocumentoFiscal.objects.filter(empresa=empresa).select_related('motorista', 'veiculo')
    status = request.GET.get('status', '')
    if status:
        qs = qs.filter(status=status)
    q = request.GET.get('q', '')
    if q:
        qs = qs.filter(Q(motorista__nome__icontains=q) | Q(chave_acesso__icontains=q))
    page, per_page, per_page_options = paginate(request, qs)
    return render(request, 'faturamento/mdfe/list.html', {
        'page_obj': page, 'status_filtro': status, 'q': q,
        'status_choices': ManifestoDocumentoFiscal.STATUS,
        'per_page': per_page,
        'per_page_options': per_page_options,
    })


def _mdfe_formsets(request, instance=None):
    """Cria todos os formsets do MDF-e a partir de POST ou instância existente."""
    data = request.POST if request.method == 'POST' else None
    kw = {'instance': instance} if instance else {}
    # OneToOne: tenta buscar instância existente sem levantar exceção
    prod_instance = None
    if instance:
        try:
            prod_instance = instance.produto_predominante
        except ProdutoPredominanteMDFe.DoesNotExist:
            pass
    return {
        'docs_formset':        DocumentoVinculadoMDFeFormSet(data, prefix='docs', **kw),
        'perc_formset':        PercursoMDFeFormSet(data, prefix='perc', **kw),
        'condutor_formset':    CondutorMDFeFormSet(data, prefix='cond', **kw),
        'reboque_formset':     ReboqueMDFeFormSet(data, prefix='reb', **kw),
        'ciot_formset':        CiotMDFeFormSet(data, prefix='ciot', **kw),
        'contratante_formset': ContratanteMDFeFormSet(data, prefix='cont', **kw),
        'vale_formset':        ValePedagioMDFeFormSet(data, prefix='vale', **kw),
        'pagfrete_formset':    PagamentoFreteMDFeFormSet(data, prefix='pagfrete', **kw),
        'seguro_formset':      SeguroMDFeFormSet(data, prefix='seg', **kw),
        'prod_pred_form':      ProdutoPredominanteMDFeForm(data, instance=prod_instance),
    }


def _mdfe_all_valid(formsets_ctx):
    return all(
        f.is_valid() if hasattr(f, 'management_form') else f.is_valid()
        for f in formsets_ctx.values()
    )


def _mdfe_save_formsets(formsets_ctx, mdfe):
    for key, f in formsets_ctx.items():
        if key == 'prod_pred_form':
            if f.is_valid():
                c = f.cleaned_data
                if c.get('c_prod') or c.get('x_prod'):
                    prod = f.save(commit=False)
                    prod.mdfe = mdfe
                    prod.save()
        else:
            f.instance = mdfe
            f.save()


@login_required
def mdfe_create(request):
    empresa = _get_empresa(request)
    if not empresa:
        return redirect('dashboard:index')
    if request.method == 'POST':
        form = ManifestoDocumentoFiscalForm(request.POST, empresa=empresa)
        fs = _mdfe_formsets(request)
        if form.is_valid() and _mdfe_all_valid(fs):
            mdfe = form.save(user=request.user)
            _mdfe_save_formsets(fs, mdfe)
            messages.success(request, 'MDF-e criado com sucesso.')
            return redirect('faturamento:mdfe_detail', pk=mdfe.pk)
    else:
        _cfg_mdfe = ConfiguracaoFiscal.objects.filter(empresa=empresa).first()
        _serie_mdfe_ini = _cfg_mdfe.serie_mdfe if _cfg_mdfe else 1
        form = ManifestoDocumentoFiscalForm(empresa=empresa, initial={'serie': _serie_mdfe_ini})
        fs = _mdfe_formsets(request)
    ctx = {'form': form, 'action': 'Novo'}
    ctx.update(fs)
    return render(request, 'faturamento/mdfe/form.html', ctx)


@login_required
def mdfe_update(request, pk):
    empresa = _get_empresa(request)
    mdfe = get_object_or_404(ManifestoDocumentoFiscal, pk=pk, empresa=empresa)
    if mdfe.status != 'RASCUNHO':
        messages.error(request, 'Somente MDF-e em Rascunho pode ser editado.')
        return redirect('faturamento:mdfe_detail', pk=pk)
    if request.method == 'POST':
        form = ManifestoDocumentoFiscalForm(request.POST, instance=mdfe, empresa=empresa)
        fs = _mdfe_formsets(request, instance=mdfe)
        if form.is_valid() and _mdfe_all_valid(fs):
            form.save(user=request.user)
            _mdfe_save_formsets(fs, mdfe)
            messages.success(request, 'MDF-e atualizado.')
            return redirect('faturamento:mdfe_detail', pk=pk)
    else:
        form = ManifestoDocumentoFiscalForm(instance=mdfe, empresa=empresa)
        fs = _mdfe_formsets(request, instance=mdfe)
    ctx = {'form': form, 'action': 'Editar', 'object': mdfe}
    ctx.update(fs)
    return render(request, 'faturamento/mdfe/form.html', ctx)


@login_required
def mdfe_detail(request, pk):
    empresa = _get_empresa(request)
    mdfe = get_object_or_404(ManifestoDocumentoFiscal, pk=pk, empresa=empresa)
    return render(request, 'faturamento/mdfe/detail.html', {'mdfe': mdfe})


@login_required
@require_POST
def mdfe_emitir_ajax(request, pk):
    """AJAX: valida, emite e retorna progresso passo a passo em JSON."""
    from .services.integranotas import IntegranNotasClient, IntegranNotasError

    empresa = _get_empresa(request)
    mdfe = get_object_or_404(ManifestoDocumentoFiscal, pk=pk, empresa=empresa)
    steps = []

    def ok(label, msg=None):
        steps.append({'status': 'ok', 'label': label, 'message': msg or ''})

    def erro(label, msg, fix_url=None, fix_label=None, errors=None):
        steps.append({'status': 'error', 'label': label, 'message': msg,
                      'fix_url': fix_url, 'fix_label': fix_label, 'errors': errors or []})
        return JsonResponse({'steps': steps, 'success': False})

    # 1. Status
    if mdfe.status != 'RASCUNHO':
        return erro('Status do MDF-e', f'MDF-e já está como "{mdfe.status}" e não pode ser emitido.')

    # 2. Token / Configuração
    config = ConfiguracaoFiscal.objects.filter(empresa=empresa).first()
    cfg_url = reverse('faturamento:configuracao')
    if not config:
        return erro('Token IntegraNotas', 'Configuração fiscal não encontrada.',
                    fix_url=cfg_url, fix_label='Configurar')
    raw_token = config.get_token()
    if not raw_token:
        return erro('Token IntegraNotas', 'Token não configurado.',
                    fix_url=cfg_url, fix_label='Configurar token')
    ambiente_label = 'Produção' if config.ambiente_nfe == '1' else 'Homologação'
    ok('Token IntegraNotas', f'Ambiente: {ambiente_label}')

    # 3. Emitente
    import re as _re
    cnpj_emit = _re.sub(r'\D', '', empresa.cnpj or '')
    emit_erros = []
    if len(cnpj_emit) != 14:
        emit_erros.append('CNPJ inválido')
    if not (empresa.nome or '').strip():
        emit_erros.append('Razão Social não informada')
    if emit_erros:
        return erro('Dados do emitente', ' | '.join(emit_erros),
                    fix_url=cfg_url, fix_label='Corrigir dados do emitente')
    ok('Dados do emitente', f'{empresa.nome} · CNPJ {empresa.cnpj}')

    # 4. Validação básica do MDF-e
    mdfe_erros = []
    if not mdfe.motorista_id:
        mdfe_erros.append('Motorista não informado')
    if not mdfe.veiculo_id:
        mdfe_erros.append('Veículo não informado')
    if not mdfe.uf_inicio:
        mdfe_erros.append('UF de início não informada')
    if not mdfe.uf_fim:
        mdfe_erros.append('UF destino não informada')
    if not mdfe.municipio_carregamento:
        mdfe_erros.append('Município de carregamento não informado')
    if not mdfe.documentos_vinculados.exists():
        mdfe_erros.append('Nenhum documento vinculado (NF-e/CT-e)')
    if mdfe_erros:
        edit_url = reverse('faturamento:mdfe_update', args=[pk])
        return erro('Validação do MDF-e',
                    f'{len(mdfe_erros)} campo(s) obrigatório(s) não preenchido(s).',
                    fix_url=edit_url, fix_label='Corrigir MDF-e', errors=mdfe_erros)
    ok('Validação do MDF-e', 'Campos obrigatórios preenchidos')

    # 5. Número
    if not mdfe.numero:
        ultimo = (
            ManifestoDocumentoFiscal.objects
            .filter(empresa=empresa, serie=mdfe.serie)
            .exclude(pk=pk)
            .order_by('-numero')
            .values_list('numero', flat=True)
            .first()
        )
        mdfe.numero = (ultimo + 1) if ultimo else (config.numero_mdfe_inicial or 1)
        mdfe.save(update_fields=['numero'])
    ok('Numeração', f'MDF-e {mdfe.numero}/{mdfe.serie}')

    # 6. Transmissão
    try:
        client = IntegranNotasClient(raw_token, config.ambiente_nfe)
        resp = client.emitir_mdfe(mdfe)
    except IntegranNotasError as exc:
        def _fmt(e):
            if isinstance(e, dict):
                partes = []
                if e.get('campo'): partes.append(f"Campo: {e['campo']}")
                partes.append(e.get('erro') or e.get('message') or str(e))
                if e.get('detalhes'): partes.append(f"Detalhe: {e['detalhes']}")
                return ' — '.join(partes)
            return str(e)
        errs = [_fmt(e) for e in exc.erros] if exc.erros else [str(exc)]
        return erro('Transmissão à SEFAZ', f'Erro IntegraNotas [{exc.codigo}]', errors=errs)
    except Exception as exc:
        return erro('Transmissão à SEFAZ', f'Falha de comunicação: {exc}')

    ok('Transmissão à SEFAZ', 'Dados enviados ao IntegraNotas')

    # 7. Resultado
    chave     = resp.get('chave', '')
    protocolo = resp.get('protocolo', '')
    xml_b64   = resp.get('xml', '')
    pdf_b64   = resp.get('pdf', '')
    codigo    = resp.get('codigo')

    if codigo == 5023:
        mdfe.chave_acesso      = chave
        mdfe.data_hora_emissao = timezone.now()
        mdfe.save(update_fields=['chave_acesso', 'data_hora_emissao'])
        steps.append({'status': 'pending', 'label': 'Aguardando autorização da SEFAZ',
                      'message': 'MDF-e em fila (código 5023). Verificando automaticamente…',
                      'chave': chave})
        return JsonResponse({'steps': steps, 'success': True, 'pending': True, 'chave': chave})

    if resp.get('sucesso') or codigo in (100, 2):
        mdfe.status            = 'EMITIDO'
        mdfe.chave_acesso      = chave
        mdfe.protocolo         = protocolo
        mdfe.xml_autorizacao   = xml_b64
        mdfe.pdf_damdfe        = pdf_b64
        mdfe.data_hora_emissao = timezone.now()
        _extra = _upload_fiscal_docs(mdfe, mdfe.empresa_id, 'mdfe', mdfe.numero, mdfe.serie, xml_b64, pdf_b64)
        _base  = ['status', 'chave_acesso', 'protocolo', 'xml_autorizacao', 'pdf_damdfe', 'data_hora_emissao']
        mdfe.save(update_fields=list(dict.fromkeys(_base + _extra)))
        steps.append({'status': 'authorized', 'label': 'MDF-e Autorizado pela SEFAZ ✓',
                      'protocolo': protocolo, 'chave': chave})
        return JsonResponse({
            'steps': steps, 'success': True, 'authorized': True,
            'chave': chave, 'protocolo': protocolo,
            'has_damdfe': bool(pdf_b64),
            'damdfe_url': reverse('faturamento:mdfe_damdfe', args=[pk]),
            'detail_url': reverse('faturamento:mdfe_detail', args=[pk]),
        })

    return erro('SEFAZ', resp.get('mensagem', 'Resposta inesperada da SEFAZ.'))


@login_required
@require_POST
def mdfe_consultar_ajax(request, pk):
    """AJAX: consulta status do MDF-e na SEFAZ para polling após código 5023."""
    from .services.integranotas import IntegranNotasClient, IntegranNotasError
    empresa = _get_empresa(request)
    mdfe = get_object_or_404(ManifestoDocumentoFiscal, pk=pk, empresa=empresa)
    if not mdfe.chave_acesso:
        return JsonResponse({'status': 'error', 'mensagem': 'MDF-e sem chave de acesso.'})
    config = ConfiguracaoFiscal.objects.filter(empresa=empresa).first()
    if not config or not config.get_token():
        return JsonResponse({'status': 'error', 'mensagem': 'Token não configurado.'})
    try:
        client = IntegranNotasClient(config.get_token(), config.ambiente_nfe)
        data = client.consultar_mdfe(mdfe.chave_acesso)
        codigo = data.get('codigo')
        if codigo == 100 or data.get('sucesso') or codigo == 2:
            fields = []
            if data.get('protocolo') and not mdfe.protocolo:
                mdfe.protocolo = data['protocolo']; fields.append('protocolo')
            if data.get('xml') and not mdfe.xml_autorizacao:
                mdfe.xml_autorizacao = data['xml']; fields.append('xml_autorizacao')
            if data.get('pdf') and not mdfe.pdf_damdfe:
                mdfe.pdf_damdfe = data['pdf']; fields.append('pdf_damdfe')
            if mdfe.status != 'EMITIDO':
                mdfe.status = 'EMITIDO'; fields.append('status')
            if fields:
                _extra = _upload_fiscal_docs(mdfe, mdfe.empresa_id, 'mdfe', mdfe.numero, mdfe.serie,
                                             data.get('xml'), data.get('pdf'))
                mdfe.save(update_fields=list(dict.fromkeys(fields + _extra)))
            return JsonResponse({
                'status': 'authorized',
                'protocolo': mdfe.protocolo or '',
                'has_damdfe': bool(mdfe.pdf_damdfe),
                'damdfe_url': reverse('faturamento:mdfe_damdfe', args=[pk]),
                'detail_url': reverse('faturamento:mdfe_detail', args=[pk]),
            })
        elif codigo == 5023:
            return JsonResponse({'status': 'pending'})
        else:
            return JsonResponse({'status': 'rejected', 'codigo': codigo,
                                 'mensagem': data.get('mensagem', 'Rejeitado pela SEFAZ.')})
    except Exception as exc:
        return JsonResponse({'status': 'error', 'mensagem': str(exc)})


@login_required
def mdfe_emitir(request, pk):
    empresa = _get_empresa(request)
    mdfe = get_object_or_404(ManifestoDocumentoFiscal, pk=pk, empresa=empresa)
    if mdfe.status != 'RASCUNHO':
        messages.error(request, 'MDF-e ja emitido ou encerrado.')
        return redirect('faturamento:mdfe_detail', pk=pk)
    try:
        config = empresa.configuracao_fiscal
    except Exception:
        messages.error(request, 'Emitente IntegraNotas não configurado. Peça ao administrador da plataforma para criá-lo (Empresas → Listar).')
        return redirect('faturamento:mdfe_detail', pk=pk)
    if not mdfe.numero:
        ultimo = ManifestoDocumentoFiscal.objects.filter(empresa=empresa, serie=mdfe.serie).exclude(pk=pk).order_by('-numero').values_list('numero', flat=True).first()
        mdfe.numero = (ultimo + 1) if ultimo else (config.numero_mdfe_inicial or 1)
        mdfe.save(update_fields=['numero'])
    from .services.integranotas import IntegranNotasClient, IntegranNotasError
    client = IntegranNotasClient(token=config.get_token(), ambiente=config.ambiente_nfe)
    try:
        resp = client.emitir_mdfe(mdfe)
        if resp.get('codigo') == 5023:
            import time
            time.sleep(4)
            resp = client.consultar_mdfe(resp.get('chave', ''))
        if resp.get('sucesso') or resp.get('codigo') in (100, 2):
            mdfe.status = 'EMITIDO'
            mdfe.chave_acesso = resp.get('chave', '')
            mdfe.protocolo = resp.get('protocolo', '')
            mdfe.xml_autorizacao = resp.get('xml', '')
            mdfe.pdf_damdfe = resp.get('pdf', '')
            mdfe.data_hora_emissao = timezone.now()
            _upload_fiscal_docs(mdfe, mdfe.empresa_id, 'mdfe', mdfe.numero, mdfe.serie,
                                resp.get('xml'), resp.get('pdf'))
            mdfe.save()
            messages.success(request, f'MDF-e {mdfe.numero} emitido! Chave: {mdfe.chave_acesso}')
        else:
            messages.error(request, f'SEFAZ: {resp.get("mensagem", "Erro desconhecido")}')
    except ValueError as e:
        messages.error(request, str(e))
    except IntegranNotasError as e:
        erros = '; '.join(str(x) for x in e.erros) if e.erros else str(e)
        messages.error(request, f'Erro IntegraNotas [{e.codigo}]: {erros}')
    except Exception as e:
        messages.error(request, f'Erro inesperado: {e}')
    return redirect('faturamento:mdfe_detail', pk=pk)


@login_required
def mdfe_encerrar(request, pk):
    empresa = _get_empresa(request)
    mdfe = get_object_or_404(ManifestoDocumentoFiscal, pk=pk, empresa=empresa)
    if mdfe.status != 'EMITIDO':
        messages.error(request, 'MDF-e deve estar Emitido para ser encerrado.')
        return redirect('faturamento:mdfe_detail', pk=pk)
    if request.method == 'POST':
        form = EncerrarMDFeForm(request.POST)
        if form.is_valid():
            try:
                config = empresa.configuracao_fiscal
                from .services.integranotas import IntegranNotasClient, IntegranNotasError
                client = IntegranNotasClient(token=config.get_token(), ambiente=config.ambiente_nfe)
                client.encerrar_mdfe(mdfe.chave_acesso, form.cleaned_data['municipio_encerramento'], timezone.now())
                mdfe.status = 'ENCERRADO'
                mdfe.municipio_encerramento = form.cleaned_data['municipio_encerramento']
                mdfe.data_encerramento = timezone.now()
                mdfe.save()
                messages.success(request, 'MDF-e encerrado com sucesso.')
                return redirect('faturamento:mdfe_detail', pk=pk)
            except IntegranNotasError as e:
                detail = ('; '.join(str(x) for x in e.erros)) if e.erros else ''
                messages.error(request, f'Erro ao encerrar [{e.codigo}]: {e}' + (f' — {detail}' if detail else ''))
            except Exception as e:
                import logging as _log
                _log.getLogger(__name__).exception('Erro inesperado ao encerrar MDF-e pk=%s', pk)
                messages.error(request, f'Erro inesperado ao encerrar: {e}')
    else:
        form = EncerrarMDFeForm()
    return render(request, 'faturamento/mdfe/encerrar.html', {'form': form, 'mdfe': mdfe})


@login_required
def mdfe_cancelar(request, pk):
    empresa = _get_empresa(request)
    mdfe = get_object_or_404(ManifestoDocumentoFiscal, pk=pk, empresa=empresa)
    if mdfe.status != 'EMITIDO':
        messages.error(request, 'Apenas MDF-e emitido pode ser cancelado.')
        return redirect('faturamento:mdfe_detail', pk=pk)
    if request.method == 'POST':
        form = CancelarMDFeForm(request.POST)
        if form.is_valid():
            try:
                config = empresa.configuracao_fiscal
                from .services.integranotas import IntegranNotasClient, IntegranNotasError
                client = IntegranNotasClient(token=config.get_token(), ambiente=config.ambiente_nfe)
                data = client.cancelar_mdfe(mdfe.chave_acesso, form.cleaned_data['justificativa'])
                mdfe.status = 'CANCELADO'
                mdfe.motivo_cancelamento = form.cleaned_data['justificativa']
                mdfe.data_cancelamento = timezone.now()
                if data.get('xml'):
                    mdfe.xml_cancelamento = data['xml']
                    _extra = _upload_fiscal_docs(mdfe, mdfe.empresa_id, 'mdfe', mdfe.numero, mdfe.serie,
                                                 xml_cancel_b64=data['xml'])
                    mdfe.save(update_fields=list(dict.fromkeys(
                        ['status', 'motivo_cancelamento', 'data_cancelamento', 'xml_cancelamento'] + _extra
                    )))
                else:
                    mdfe.save(update_fields=['status', 'motivo_cancelamento', 'data_cancelamento'])
                messages.success(request, 'MDF-e cancelado com sucesso.')
                return redirect('faturamento:mdfe_detail', pk=pk)
            except Exception as e:
                messages.error(request, f'Erro ao cancelar: {e}')
    else:
        form = CancelarMDFeForm()
    return render(request, 'faturamento/mdfe/cancelar.html', {'form': form, 'mdfe': mdfe})


@login_required
def mdfe_damdfe(request, pk):
    import base64
    from django.shortcuts import redirect as _redirect
    empresa = _get_empresa(request)
    mdfe = get_object_or_404(ManifestoDocumentoFiscal, pk=pk, empresa=empresa)
    if mdfe.pdf_damdfe_url:
        return _redirect(mdfe.pdf_damdfe_url)
    if mdfe.pdf_damdfe:
        pdf_bytes = base64.b64decode(mdfe.pdf_damdfe)
        r = HttpResponse(pdf_bytes, content_type='application/pdf')
        r['Content-Disposition'] = f'inline; filename="DAMDFE_{mdfe.numero}_{mdfe.serie}.pdf"'
        return r
    try:
        config = empresa.configuracao_fiscal
        from .services.integranotas import IntegranNotasClient
        client = IntegranNotasClient(token=config.get_token(), ambiente=config.ambiente_nfe)
        data = client.damdfe(mdfe.chave_acesso)
        if data.get('pdf'):
            mdfe.pdf_damdfe = data['pdf']
            _extra = _upload_fiscal_docs(mdfe, mdfe.empresa_id, 'mdfe', mdfe.numero, mdfe.serie,
                                         pdf_b64=data['pdf'])
            mdfe.save(update_fields=list(dict.fromkeys(['pdf_damdfe'] + _extra)))
            if mdfe.pdf_damdfe_url:
                return _redirect(mdfe.pdf_damdfe_url)
            pdf_bytes = base64.b64decode(mdfe.pdf_damdfe or data['pdf'])
            r = HttpResponse(pdf_bytes, content_type='application/pdf')
            r['Content-Disposition'] = f'inline; filename="DAMDFE_{mdfe.numero}_{mdfe.serie}.pdf"'
            return r
    except Exception as e:
        messages.error(request, f'Erro ao obter DAMDFE: {e}')
    return redirect('faturamento:mdfe_detail', pk=pk)


@login_required
@require_POST
def mdfe_consultar(request, pk):
    empresa = _get_empresa(request)
    mdfe = get_object_or_404(ManifestoDocumentoFiscal, pk=pk, empresa=empresa)
    if not mdfe.chave_acesso:
        messages.error(request, 'MDF-e sem chave de acesso.')
        return redirect('faturamento:mdfe_detail', pk=pk)
    try:
        config = empresa.configuracao_fiscal
        from .services.integranotas import IntegranNotasClient
        client = IntegranNotasClient(token=config.get_token(), ambiente=config.ambiente_nfe)
        data = client.consultar_mdfe(mdfe.chave_acesso)
        if data.get('protocolo'):
            mdfe.protocolo = data['protocolo']
        if data.get('xml'):
            mdfe.xml_autorizacao = data['xml']
        if data.get('pdf'):
            mdfe.pdf_damdfe = data['pdf']
        mdfe.save()
        messages.success(request, f'MDF-e atualizado — protocolo: {mdfe.protocolo or "pendente"}')
    except Exception as e:
        messages.error(request, f'Erro ao consultar SEFAZ: {e}')
    return redirect('faturamento:mdfe_detail', pk=pk)


@login_required
def mdfe_xml(request, pk):
    """Download do XML autorizado do MDF-e."""
    import base64
    import urllib.request as _ur
    from .services.integranotas import IntegranNotasClient
    empresa = _get_empresa(request)
    mdfe = get_object_or_404(ManifestoDocumentoFiscal, pk=pk, empresa=empresa)
    if mdfe.xml_autorizacao_url:
        try:
            xml_bytes = _ur.urlopen(mdfe.xml_autorizacao_url, timeout=20).read()
            resp = HttpResponse(xml_bytes, content_type='application/xml; charset=utf-8')
            resp['Content-Disposition'] = f'attachment; filename="MDFE_{mdfe.numero}_{mdfe.serie}.xml"'
            return resp
        except Exception:
            pass
    if not mdfe.xml_autorizacao and mdfe.chave_acesso:
        try:
            config = empresa.configuracao_fiscal
            client = IntegranNotasClient(token=config.get_token(), ambiente=config.ambiente_nfe)
            data = client.consultar_mdfe(mdfe.chave_acesso)
            if data.get('xml'):
                mdfe.xml_autorizacao = data['xml']
                fields = ['xml_autorizacao']
                if data.get('protocolo') and not mdfe.protocolo:
                    mdfe.protocolo = data['protocolo']
                    fields.append('protocolo')
                _extra = _upload_fiscal_docs(mdfe, mdfe.empresa_id, 'mdfe', mdfe.numero, mdfe.serie,
                                             xml_b64=data['xml'])
                mdfe.save(update_fields=list(dict.fromkeys(fields + _extra)))
                if mdfe.xml_autorizacao_url:
                    from django.shortcuts import redirect as _redirect
                    return _redirect(mdfe.xml_autorizacao_url)
        except Exception:
            pass
    if not mdfe.xml_autorizacao:
        messages.error(request, 'XML de autorização não disponível para este MDF-e.')
        return redirect('faturamento:mdfe_detail', pk=pk)
    xml_bytes = base64.b64decode(mdfe.xml_autorizacao)
    resp = HttpResponse(xml_bytes, content_type='application/xml; charset=utf-8')
    resp['Content-Disposition'] = f'attachment; filename="MDFE_{mdfe.numero}_{mdfe.serie}.xml"'
    return resp


@login_required
def mdfe_xml_cancelamento(request, pk):
    """Download do XML de cancelamento do MDF-e."""
    import base64
    import urllib.request as _ur
    empresa = _get_empresa(request)
    mdfe = get_object_or_404(ManifestoDocumentoFiscal, pk=pk, empresa=empresa)
    if mdfe.xml_cancelamento_url:
        try:
            xml_bytes = _ur.urlopen(mdfe.xml_cancelamento_url, timeout=20).read()
            resp = HttpResponse(xml_bytes, content_type='application/xml; charset=utf-8')
            resp['Content-Disposition'] = f'attachment; filename="CANCEL_MDFE_{mdfe.numero}_{mdfe.serie}.xml"'
            return resp
        except Exception:
            pass
    if not mdfe.xml_cancelamento:
        messages.error(request, 'XML de cancelamento não disponível para este MDF-e.')
        return redirect('faturamento:mdfe_detail', pk=pk)
    xml_bytes = base64.b64decode(mdfe.xml_cancelamento)
    resp = HttpResponse(xml_bytes, content_type='application/xml; charset=utf-8')
    resp['Content-Disposition'] = f'attachment; filename="CANCEL_MDFE_{mdfe.numero}_{mdfe.serie}.xml"'
    return resp


@login_required
def mdfe_preview(request, pk):
    empresa = _get_empresa(request)
    mdfe = get_object_or_404(ManifestoDocumentoFiscal, pk=pk, empresa=empresa)
    if not mdfe.chave_acesso:
        messages.error(request, 'MDF-e sem chave de acesso — emita na SEFAZ primeiro.')
        return redirect('faturamento:mdfe_detail', pk=pk)
    try:
        config = empresa.configuracao_fiscal
        from .services.integranotas import IntegranNotasClient
        client = IntegranNotasClient(token=config.get_token(), ambiente=config.ambiente_nfe)
        data = client.preview_mdfe(mdfe.chave_acesso)
        if data.get('pdf'):
            import base64
            pdf_bytes = base64.b64decode(data['pdf'])
            r = HttpResponse(pdf_bytes, content_type='application/pdf')
            r['Content-Disposition'] = f'inline; filename="preview_DAMDFE_{mdfe.numero}.pdf"'
            return r
        messages.error(request, 'Preview não retornou PDF.')
    except Exception as e:
        messages.error(request, f'Erro ao gerar preview: {e}')
    return redirect('faturamento:mdfe_detail', pk=pk)


@login_required
def mdfe_inclui_condutor(request, pk):
    empresa = _get_empresa(request)
    mdfe = get_object_or_404(ManifestoDocumentoFiscal, pk=pk, empresa=empresa)
    if mdfe.status != 'EMITIDO':
        messages.error(request, 'Apenas MDF-e emitido pode ter condutor incluído.')
        return redirect('faturamento:mdfe_detail', pk=pk)
    if request.method == 'POST':
        cpf = request.POST.get('cpf', '').strip()
        nome = request.POST.get('nome', '').strip()
        if not cpf or not nome:
            messages.error(request, 'CPF e nome são obrigatórios.')
        else:
            try:
                config = empresa.configuracao_fiscal
                from .services.integranotas import IntegranNotasClient, IntegranNotasError
                client = IntegranNotasClient(token=config.get_token(), ambiente=config.ambiente_nfe)
                cpf_digits = ''.join(c for c in cpf if c.isdigit())
                data = client.inclui_condutor_mdfe(mdfe.chave_acesso, cpf_digits, nome)
                protocolo = data.get('protocolo', '')
                CondutorAdicionalMDFe.objects.create(
                    mdfe=mdfe, cpf=cpf, nome=nome,
                    protocolo=protocolo, adicionado_por=request.user,
                )
                messages.success(request, f'Condutor {nome} incluído no MDF-e. Protocolo: {protocolo or "—"}')
                return redirect('faturamento:mdfe_detail', pk=pk)
            except Exception as e:
                messages.error(request, f'Erro ao incluir condutor: {e}')
    condutores = mdfe.condutores_adicionais.all()
    return render(request, 'faturamento/mdfe/inclui_condutor_form.html', {
        'mdfe': mdfe, 'condutores': condutores,
    })


@login_required
def mdfe_inclui_nfe(request, pk):
    empresa = _get_empresa(request)
    mdfe = get_object_or_404(ManifestoDocumentoFiscal, pk=pk, empresa=empresa)
    if mdfe.status != 'EMITIDO':
        messages.error(request, 'Apenas MDF-e emitido pode ter NF-e incluída.')
        return redirect('faturamento:mdfe_detail', pk=pk)
    if request.method == 'POST':
        chave_nfe = request.POST.get('chave_nfe', '').strip()
        municipio = request.POST.get('municipio_descarregamento', '').strip()
        tipo = request.POST.get('tipo', 'nfe')
        if not chave_nfe or not municipio:
            messages.error(request, 'Chave e município de descarregamento são obrigatórios.')
        elif len(chave_nfe) != 44:
            messages.error(request, 'Chave de acesso deve ter exatamente 44 dígitos.')
        else:
            try:
                config = empresa.configuracao_fiscal
                from .services.integranotas import IntegranNotasClient, IntegranNotasError
                client = IntegranNotasClient(token=config.get_token(), ambiente=config.ambiente_nfe)
                client.inclui_nfe_mdfe(mdfe.chave_acesso, chave_nfe, municipio)
                DocumentoVinculadoMDFe.objects.create(
                    mdfe=mdfe, tipo=tipo, chave=chave_nfe,
                    municipio_descarregamento=municipio,
                )
                messages.success(request, f'Documento {chave_nfe[:10]}… incluído no MDF-e.')
                return redirect('faturamento:mdfe_detail', pk=pk)
            except Exception as e:
                messages.error(request, f'Erro ao incluir NF-e: {e}')
    return render(request, 'faturamento/mdfe/inclui_nfe_form.html', {'mdfe': mdfe})


@login_required
def mdfe_clonar(request, pk):
    empresa = _get_empresa(request)
    original = get_object_or_404(ManifestoDocumentoFiscal, pk=pk, empresa=empresa)
    if request.method != 'POST':
        return redirect('faturamento:mdfe_detail', pk=pk)

    from django.utils import timezone as _tz

    # Duplica o registro principal zerando campos SEFAZ e resetando para Rascunho
    novo = ManifestoDocumentoFiscal.objects.get(pk=original.pk)
    novo.pk = None
    novo.numero = None
    novo.status = 'RASCUNHO'
    novo.data_emissao = _tz.now().date()
    novo.chave_acesso = ''
    novo.protocolo = ''
    novo.xml_autorizacao = ''
    novo.xml_autorizacao_url = ''
    novo.pdf_damdfe = ''
    novo.pdf_damdfe_url = ''
    novo.motivo_cancelamento = ''
    novo.data_cancelamento = None
    novo.data_hora_emissao = None
    novo.data_encerramento = None
    novo.municipio_encerramento = ''
    novo.criado_por = request.user
    novo.atualizado_por = request.user
    novo.save()

    # Clona todos os relacionamentos relevantes
    for obj in original.percursos.all():
        obj.pk = None
        obj.mdfe = novo
        obj.save()

    for obj in original.documentos_vinculados.all():
        obj.pk = None
        obj.mdfe = novo
        obj.save()

    for obj in original.condutores.all():
        obj.pk = None
        obj.mdfe = novo
        obj.save()

    for obj in original.reboques.all():
        obj.pk = None
        obj.mdfe = novo
        obj.save()

    for obj in original.ciots.all():
        obj.pk = None
        obj.mdfe = novo
        obj.save()

    for obj in original.contratantes.all():
        obj.pk = None
        obj.mdfe = novo
        obj.save()

    for obj in original.vales_pedagio.all():
        obj.pk = None
        obj.mdfe = novo
        obj.save()

    for obj in original.pagamentos_frete.all():
        obj.pk = None
        obj.mdfe = novo
        obj.save()

    for obj in original.seguros.all():
        obj.pk = None
        obj.mdfe = novo
        obj.save()

    try:
        pp = original.produto_predominante
        pp.pk = None
        pp.mdfe = novo
        pp.save()
    except Exception:
        pass

    messages.success(request, f'MDF-e clonado com sucesso. Edite os dados antes de emitir.')
    return redirect('faturamento:mdfe_update', pk=novo.pk)


# ═══════════════════════════════════════════════════════════════════
#  FATURAMENTO AGRUPADO — Remessas Pendentes e Nota Mãe
# ═══════════════════════════════════════════════════════════════════

@login_required
def remessas_pendentes(request):
    """Tela A — Dashboard de NF-es de Remessa aguardando faturamento."""
    empresa = _get_empresa(request)

    qs = NotaFiscal.objects.filter(
        empresa=empresa,
        tipo_operacao='REMESSA',
        status='EMITIDA',
        status_faturamento='PENDENTE',
    ).select_related('cliente').order_by('cliente__razao_social', 'data_emissao')

    # Filtros opcionais
    cliente_id = request.GET.get('cliente_id', '').strip()
    data_de = request.GET.get('data_de', '').strip()
    data_ate = request.GET.get('data_ate', '').strip()

    if cliente_id:
        qs = qs.filter(cliente_id=cliente_id)
    if data_de:
        qs = qs.filter(data_emissao__gte=data_de)
    if data_ate:
        qs = qs.filter(data_emissao__lte=data_ate)

    from cadastros.models import Cliente
    clientes = Cliente.objects.filter(empresa=empresa, status='ATIVO').order_by('razao_social')

    return render(request, 'faturamento/remessas_pendentes.html', {
        'notas': qs,
        'clientes': clientes,
        'cliente_id_sel': cliente_id,
        'data_de': data_de,
        'data_ate': data_ate,
        'total_geral': qs.aggregate(t=Sum('valor_total'))['t'] or 0,
    })


@login_required
@require_POST
def fechar_lote(request):
    """Tela B — Prévia da Nota Mãe. Processa em memória, não persiste."""
    from django.core.exceptions import ValidationError as DjValidationError
    from .services.agrupamento import (
        validar_selecao_notas,
        consolidar_itens_para_nota_mae,
        gerar_infcpl_faturamento,
        inferir_cfop_faturamento,
    )

    empresa = _get_empresa(request)
    notas_ids = request.POST.getlist('notas_ids')

    try:
        notas = validar_selecao_notas(notas_ids, empresa)
    except DjValidationError as exc:
        messages.error(request, ' '.join(exc.messages))
        return redirect('faturamento:remessas_pendentes')

    notas_list = list(notas.order_by('data_emissao'))
    cliente = notas_list[0].cliente
    itens_consolidados = consolidar_itens_para_nota_mae(notas_list)
    infcpl = gerar_infcpl_faturamento(notas_list)
    cfop_sugerido = inferir_cfop_faturamento(empresa, cliente)

    # Período das remessas
    datas = [nf.data_emissao for nf in notas_list]
    periodo_de = min(datas)
    periodo_ate = max(datas)

    valor_total = sum(nf.valor_total for nf in notas_list)

    CFOPS_FATURAMENTO = [
        ('5116', '5.116 — Venda de produção própria (interno)'),
        ('5117', '5.117 — Venda de mercadoria adquirida (interno)'),
        ('6116', '6.116 — Venda de produção própria (interestadual)'),
        ('6117', '6.117 — Venda de mercadoria adquirida (interestadual)'),
    ]

    return render(request, 'faturamento/fechar_lote_preview.html', {
        'notas': notas_list,
        'notas_ids': notas_ids,
        'cliente': cliente,
        'periodo_de': periodo_de,
        'periodo_ate': periodo_ate,
        'itens_consolidados': itens_consolidados,
        'infcpl': infcpl,
        'cfop_sugerido': cfop_sugerido,
        'cfops_faturamento': CFOPS_FATURAMENTO,
        'valor_total': valor_total,
        'data_emissao_hoje': timezone.now().date(),
    })


@login_required
@require_POST
def gerar_nota_mae(request):
    """Cria a Nota Mãe e emite para a SEFAZ (síncrono)."""
    from django.core.exceptions import ValidationError as DjValidationError
    from .services.agrupamento import validar_selecao_notas, criar_nota_mae, inferir_cfop_faturamento, gerar_infcpl_faturamento, consolidar_itens_para_nota_mae
    from .services.integranotas import IntegranNotasClient, IntegranNotasError
    import datetime

    empresa = _get_empresa(request)
    notas_ids = request.POST.getlist('notas_ids')

    try:
        notas = validar_selecao_notas(notas_ids, empresa)
    except DjValidationError as exc:
        messages.error(request, ' '.join(exc.messages))
        return redirect('faturamento:remessas_pendentes')

    notas_list = list(notas.order_by('data_emissao'))
    cliente = notas_list[0].cliente

    # Campos editáveis da prévia
    data_emissao_str = request.POST.get('data_emissao', str(timezone.now().date()))
    try:
        data_emissao = datetime.date.fromisoformat(data_emissao_str)
    except ValueError:
        data_emissao = timezone.now().date()

    cfop = request.POST.get('cfop', inferir_cfop_faturamento(empresa, cliente))
    natureza_operacao = request.POST.get(
        'natureza_operacao', 'FATURAMENTO DE REMESSAS ANTERIORES'
    )
    informacoes_complementares = request.POST.get(
        'informacoes_complementares', gerar_infcpl_faturamento(notas_list)
    )

    try:
        nota_mae = criar_nota_mae(
            notas_filhas=notas_list,
            data_emissao=data_emissao,
            cfop=cfop,
            natureza_operacao=natureza_operacao,
            informacoes_complementares=informacoes_complementares,
            empresa=empresa,
            usuario=request.user,
        )
    except DjValidationError as exc:
        messages.error(request, 'Erro ao criar Nota Mãe: ' + ' '.join(exc.messages))
        return redirect('faturamento:remessas_pendentes')
    except Exception as exc:
        messages.error(request, f'Erro inesperado ao criar Nota Mãe: {exc}')
        return redirect('faturamento:remessas_pendentes')

    # Tenta emitir para SEFAZ
    config = ConfiguracaoFiscal.objects.filter(empresa=empresa).first()
    if config and config.has_token:
        try:
            from .services.integranotas import IntegranNotasClient
            client = IntegranNotasClient(config.get_token(), config.ambiente_nfe)
            resultado = client.emitir_nfe(nota_mae)
            codigo = resultado.get('codigo')
            if codigo == 100:
                chave = resultado.get('chave', '')
                protocolo = resultado.get('protocolo', '')
                xml_b64 = resultado.get('xml', '')
                pdf_b64 = resultado.get('pdf', '')
                nota_mae.chave_acesso = chave
                nota_mae.protocolo_autorizacao = protocolo
                nota_mae.xml_autorizacao = xml_b64
                nota_mae.pdf_danfe = pdf_b64
                nota_mae.status = 'EMITIDA'
                nota_mae.data_hora_emissao = timezone.now()
                nota_mae.atualizado_por = request.user
                _base = ['chave_acesso', 'protocolo_autorizacao', 'xml_autorizacao',
                         'pdf_danfe', 'status', 'data_hora_emissao', 'atualizado_por']
                _extra = _upload_fiscal_docs(
                    nota_mae, nota_mae.empresa_id, 'nfe',
                    nota_mae.numero, nota_mae.serie, xml_b64, pdf_b64
                )
                nota_mae.save(update_fields=list(dict.fromkeys(_base + _extra)))
                _processar_autorizacao_agrupamento(nota_mae)
                messages.success(
                    request,
                    f'Nota Mãe NF {nota_mae.numero}/{nota_mae.serie} gerada e autorizada! '
                    f'Chave: {chave}'
                )
            else:
                msg_sefaz = resultado.get('mensagem', f'Código {codigo}')
                messages.warning(
                    request,
                    f'Nota Mãe criada como Rascunho. SEFAZ retornou: {msg_sefaz}. '
                    'Emita manualmente pela tela de detalhes.'
                )
        except IntegranNotasError as exc:
            messages.error(
                request,
                f'Nota Mãe criada como Rascunho. Erro SEFAZ [{exc.codigo}]: {exc}. '
                'Emita manualmente pela tela de detalhes.'
            )
        except Exception as exc:
            messages.error(
                request,
                f'Nota Mãe criada como Rascunho. Falha na comunicação: {exc}. '
                'Emita manualmente pela tela de detalhes.'
            )
    else:
        messages.info(
            request,
            'Nota Mãe criada como Rascunho (token IntegraNota não configurado). '
            'Emita manualmente pela tela de detalhes.'
        )

    return redirect('faturamento:nota_fiscal_detail', pk=nota_mae.pk)

