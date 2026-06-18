import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)


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
    DocumentoVinculadoCTeFormSet,
    DocumentoVinculadoMDFeFormSet,
    DuplicataNFFormSet,
    EncerrarMDFeForm,
    InvoiceExportacaoForm,
    InutilizacaoNFeForm,
    ItemInvoiceFormSet,
    ItemNotaFiscalFormSet,
    ItemPackingListFormSet,
    ManifestoDocumentoFiscalForm,
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
    DocumentoVinculadoCTe,
    DocumentoVinculadoMDFe,
    InutilizacaoNFe,
    InvoiceExportacao,
    ItemPackingList,
    ManifestoDocumentoFiscal,
    NotaFiscal,
    PackingList,
    PercursoMDFe,
    ProdutoPredominanteMDFe,
)


from .fiscal_storage import upload_xml as _fs_xml, upload_pdf as _fs_pdf


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

@login_required
def nota_fiscal_list(request):
    empresa = _get_empresa(request)
    if not empresa:
        return redirect('dashboard:index')

    qs = NotaFiscal.objects.filter(empresa=empresa).select_related('cliente')

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
    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'faturamento/nota_fiscal/list.html', {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'q': q,
        'data_ini': data_ini,
        'data_fim': data_fim,
        'status_choices': NotaFiscal.STATUS,
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
        _nf_log_validation('CREATE', form, formset, pag_formset, dup_formset)
        if form.is_valid() and formset.is_valid() and pag_formset.is_valid() and dup_formset.is_valid():
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
            nf.calcular_totais()
            messages.success(request, f'NF {nf.numero}/{nf.serie} criada com sucesso.')
            return redirect('faturamento:nota_fiscal_detail', pk=nf.pk)
    else:
        config = ConfiguracaoFiscal.objects.filter(empresa=empresa).first()
        initial = {}
        if config:
            initial['natureza_operacao'] = config.natureza_operacao_padrao
            initial['cfop'] = config.cfop_venda_interna
            initial['informacoes_complementares'] = config.observacoes_padrao_nfe
        form = NotaFiscalForm(empresa=empresa, initial=initial)
        formset = ItemNotaFiscalFormSet(prefix='itens',
                                        form_kwargs={'empresa': empresa})
        pag_formset = PagamentoNFFormSet(prefix='pagamentos')
        dup_formset = DuplicataNFFormSet(prefix='duplicatas')

    return render(request, 'faturamento/nota_fiscal/form.html', {
        'form': form,
        'formset': formset,
        'pag_formset': pag_formset,
        'dup_formset': dup_formset,
        'title': 'Nova Nota Fiscal',
    })


@login_required
def nota_fiscal_danfe_preview(request, pk):
    empresa = _get_empresa(request)
    nf = get_object_or_404(NotaFiscal, pk=pk, empresa=empresa)
    cli = nf.cliente
    endereco_cli = cli.enderecos.order_by('-padrao').first()
    return render(request, 'faturamento/nota_fiscal/danfe_preview.html', {
        'nf': nf,
        'empresa': empresa,
        'cli': cli,
        'endereco_cli': endereco_cli,
        'itens': nf.itens.order_by('numero_item'),
        'duplicatas': nf.duplicatas.order_by('vencimento'),
    })


@login_required
def nota_fiscal_detail(request, pk):
    empresa = _get_empresa(request)
    nf = get_object_or_404(NotaFiscal, pk=pk, empresa=empresa)
    return render(request, 'faturamento/nota_fiscal/detail.html', {'nf': nf})


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
        _nf_log_validation('UPDATE', form, formset, pag_formset, dup_formset)
        if form.is_valid() and formset.is_valid() and pag_formset.is_valid() and dup_formset.is_valid():
            form.save(user=request.user)
            items = formset.save(commit=False)
            for idx, item in enumerate(items, start=1):
                item.numero_item = idx
                item.save()
            for obj in formset.deleted_objects:
                obj.delete()
            pag_formset.save()
            dup_formset.save()
            nf.calcular_totais()
            messages.success(request, 'NF-e atualizada com sucesso.')
            return redirect('faturamento:nota_fiscal_detail', pk=pk)
    else:
        form = NotaFiscalForm(instance=nf, empresa=empresa)
        formset = ItemNotaFiscalFormSet(instance=nf, prefix='itens',
                                        form_kwargs={'empresa': empresa})
        pag_formset = PagamentoNFFormSet(instance=nf, prefix='pagamentos')
        dup_formset = DuplicataNFFormSet(instance=nf, prefix='duplicatas')

    return render(request, 'faturamento/nota_fiscal/form.html', {
        'form': form,
        'formset': formset,
        'pag_formset': pag_formset,
        'dup_formset': dup_formset,
        'nf': nf,
        'title': f'Editar NF {nf.numero}/{nf.serie}',
    })


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
    cli_url = reverse('cadastros:cliente_update', args=[cli.pk])
    dest_erros = []
    doc_dest = _re.sub(r'\D', '', cli.cnpj_cpf or '')
    if not doc_dest:
        dest_erros.append('CNPJ/CPF não informado')
    elif len(doc_dest) not in (11, 14):
        dest_erros.append(f'CNPJ/CPF inválido ({len(doc_dest)} dígitos — esperado 11 ou 14)')
    if not (cli.razao_social or '').strip():
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
                    f'{cli.razao_social or "?"}: {"; ".join(dest_erros)}',
                    fix_url=cli_url, fix_label='Corrigir cadastro do cliente',
                    errors=dest_erros)
    ok('Dados do destinatário', f'{cli.razao_social}  ·  {cli.cnpj_cpf}')

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
        # IPI: se alíquota > 0, CST deve corresponder a saída tributada (50)
        aliq_ipi = item.aliquota_ipi or 0
        if aliq_ipi > 0:
            cst_ipi = (item.cst_ipi or '').strip()
            if cst_ipi not in ('50',):
                faltam.append(
                    f'IPI: CST "{cst_ipi}" incompatível com alíquota {aliq_ipi}% '
                    f'(use CST 50 — Saída Tributada)'
                )
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
        messages.error(request, 'Configure o token IntegraNota em Faturamento → Configuração Fiscal antes de emitir.')
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
            messages.success(request, f'NF {nf.numero}/{nf.serie} autorizada! Chave: {chave}')

    except IntegranNotasError as exc:
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

    if request.method == 'POST':
        form = NotaFiscalCancelarForm(request.POST)
        if form.is_valid():
            justificativa = form.cleaned_data['justificativa']

            # Se NF tem chave, tenta cancelar na SEFAZ via IntegraNota
            if nf.chave_acesso:
                config = ConfiguracaoFiscal.objects.filter(empresa=empresa).first()
                if not config or not config.has_token:
                    messages.error(request, 'Configure o token IntegraNota para cancelar via SEFAZ.')
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

            nf.status = 'CANCELADA'
            nf.motivo_cancelamento = justificativa
            nf.data_cancelamento = timezone.now()
            nf.atualizado_por = request.user
            nf.save(update_fields=['status', 'motivo_cancelamento', 'data_cancelamento', 'atualizado_por'])
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
        messages.error(request, 'Configure o token IntegraNota em Faturamento → Configuração Fiscal.')
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
        messages.error(request, 'Configure o token IntegraNota em Faturamento → Configuração Fiscal.')
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

    return HttpResponse(status=200)


@login_required
def nota_fiscal_danfe(request, pk):
    """Download do DANFE PDF da NF-e (Supabase URL ou base64)."""
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
                messages.error(request, 'Configure o token IntegraNota para enviar CC-e.')
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
                xml_retorno=resultado.get('xml', ''),
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
def nota_fiscal_inutilizar(request):
    from .services.integranotas import IntegranNotasClient, IntegranNotasError
    from datetime import date

    empresa = _get_empresa(request)
    config = ConfiguracaoFiscal.objects.filter(empresa=empresa).first()

    if request.method == 'POST':
        form = InutilizacaoNFeForm(request.POST)
        if form.is_valid():
            if not config or not config.has_token:
                messages.error(request, 'Configure o token IntegraNota para inutilizar numeração.')
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
    empresa = _get_empresa(request)
    nf = get_object_or_404(NotaFiscal, pk=pk, empresa=empresa)

    from django.template.loader import get_template
    from xhtml2pdf import pisa
    from django.http import HttpResponse
    import io

    template = get_template('faturamento/nota_fiscal/pdf.html')
    html = template.render({'nf': nf, 'empresa': empresa})
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
    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'faturamento/invoice/list.html', {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'q': q,
        'data_ini': data_ini,
        'data_fim': data_fim,
        'status_choices': InvoiceExportacao.STATUS,
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
    messages.success(request, f'{invoice.numero} cancelada.')
    return redirect('faturamento:invoice_detail', pk=pk)


@login_required
def invoice_pdf(request, pk):
    empresa = _get_empresa(request)
    invoice = get_object_or_404(InvoiceExportacao, pk=pk, empresa=empresa)

    from django.template.loader import get_template
    from xhtml2pdf import pisa
    from django.http import HttpResponse
    import io

    from adiantamentos.models import DescontoAdiantamento
    desconto_adiantamento = DescontoAdiantamento.objects.filter(invoice=invoice, status='APLICADO').select_related('adiantamento').first()

    template = get_template('faturamento/invoice/pdf.html')
    html = template.render({'invoice': invoice, 'empresa': empresa, 'desconto_adiantamento': desconto_adiantamento})
    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(html.encode('utf-8')), result)
    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{invoice.numero}.pdf"'
        return response
    return HttpResponse('Erro ao gerar PDF', status=500)


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
    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'faturamento/packing_list/list.html', {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'q': q,
        'status_choices': PackingList.STATUS,
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
    })


@login_required
@require_POST
def certificado_upload(request):
    from .services.integranotas import parse_pfx

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
            config.certificado_pfx = pfx_bytes
            config.senha_certificado = senha
            config.certificado_validade = info['validade']
            config.certificado_cnpj = info['cnpj']
            config.certificado_arquivo_nome = arquivo.name
            config.save()
            messages.success(
                request,
                f'Certificado "{arquivo.name}" importado. '
                f'Válido até {info["validade"].strftime("%d/%m/%Y")}.'
            )
        except ValueError as exc:
            messages.error(request, str(exc))
        except Exception as exc:
            messages.error(request, f'Erro inesperado ao processar certificado: {exc}')
    else:
        for field_errors in form.errors.values():
            for error in field_errors:
                messages.error(request, error)

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
            'cst_icms': t.icms_situacao_tributaria,
            'icms_modalidade_base': t.icms_modalidade_base or '3',
            'icms_reducao_base': float(t.icms_reducao_base or 0),
            'aliquota_icms': float(t.icms_aliquota),
            'icms_st_aliquota': float(t.icms_st_aliquota or 0),
            'icms_st_mva': float(t.icms_st_mva or 0),
            'icms_st_reducao_base': float(t.icms_st_reducao_base or 0),
            'cst_ipi': t.ipi_situacao_tributaria or '99',
            'aliquota_ipi': float(t.ipi_aliquota),
            'ipi_codigo_enquadramento': t.ipi_codigo_enquadramento or '999',
            'cst_pis': t.pis_situacao_tributaria,
            'aliquota_pis': float(t.pis_aliquota),
            'natureza_receita_pis': t.natureza_receita_pis or '',
            'cst_cofins': t.cofins_situacao_tributaria,
            'aliquota_cofins': float(t.cofins_aliquota),
            'natureza_receita_cofins': t.natureza_receita_cofins or '',
            'beneficio_fiscal': t.beneficio_fiscal or '',
        })

    fator = float(produto.fator_conversao or 1)
    un_med_sigla = produto.unidade_medida.sigla if produto.unidade_medida_id else ''
    un_venda_sigla = produto.unidade_venda.sigla if produto.unidade_venda_id else ''
    # Unidade tributável = unidade_medida quando difere da unidade_venda; caso contrário KG (fallback peso)
    un_trib = un_med_sigla if (un_med_sigla and un_med_sigla != un_venda_sigla) else ''

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
            .filter(empresa=empresa, status='EMITIDA')
            .select_related('cliente', 'transportadora')
        )
        if q:
            notas = notas.filter(Q(cliente__razao_social__icontains=q) | Q(numero__icontains=q))
        notas = notas.order_by('-data_emissao')[:50]
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
                'transportadora_nome': n.transportadora.nome if n.transportadora else '',
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

    return render(request, 'faturamento/cotacoes_bcb/list.html', {
        'linhas': linhas,
        'data_ini': data_ini_str,
        'data_fim': data_fim_str,
        'total': len(linhas),
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
@require_POST
def integranotas_test_token(request):
    """AJAX: testa um token IntegraNotas sem salvar. Aceita token e ambiente via POST."""
    from .services.integranotas import IntegranNotasClient

    empresa = _get_empresa(request)

    token_input  = request.POST.get('token', '').strip()
    ambiente_input = request.POST.get('ambiente', '2').strip()

    # Se não passou token no POST, usa o já salvo
    if not token_input:
        config = ConfiguracaoFiscal.objects.filter(empresa=empresa).first()
        if not config:
            return JsonResponse({'sucesso': False, 'mensagem': 'Configuração fiscal não encontrada.'})
        token_input = config.get_token()
        if not token_input:
            return JsonResponse({'sucesso': False, 'mensagem': 'Nenhum token configurado. Cole o token no campo acima para testar.'})
        ambiente_input = config.ambiente_nfe

    token_prefix = token_input[:16] + '...' if len(token_input) > 16 else token_input
    client = IntegranNotasClient(token=token_input, ambiente=ambiente_input)
    result = client.test_connection()
    result['token_prefix'] = token_prefix
    result['ambiente_label'] = 'Produção' if ambiente_input == '1' else 'Homologação'
    return JsonResponse(result)


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
    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'faturamento/cte/list.html', {
        'page_obj': page, 'status_filtro': status, 'q': q,
        'status_choices': ConhecimentoTransporte.STATUS,
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
        form = ConhecimentoTransporteForm(empresa=empresa)
        docs_formset = DocumentoVinculadoCTeFormSet(prefix='docs')
        comp_formset = ComponenteValorCTeFormSet(prefix='comp')
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


@login_required
def cte_emitir(request, pk):
    empresa = _get_empresa(request)
    ct = get_object_or_404(ConhecimentoTransporte, pk=pk, empresa=empresa)
    if ct.status != 'RASCUNHO':
        messages.error(request, 'CT-e ja foi emitido ou cancelado.')
        return redirect('faturamento:cte_detail', pk=pk)
    try:
        config = empresa.configuracao_fiscal
    except Exception:
        messages.error(request, 'Configure o token IntegraNotas em Faturamento > Configuracao Fiscal.')
        return redirect('faturamento:cte_detail', pk=pk)
    if not ct.numero:
        ultimo = ConhecimentoTransporte.objects.filter(empresa=empresa).exclude(pk=pk).order_by('-numero').values_list('numero', flat=True).first()
        ct.numero = (ultimo or 0) + 1
        ct.save(update_fields=['numero'])
    from .services.integranotas import IntegranNotasClient, IntegranNotasError
    client = IntegranNotasClient(token=config.get_token(), ambiente=config.ambiente_nfe)
    try:
        resp = client.emitir_cte(ct)
        if resp.get('codigo') == 5023:
            import time
            time.sleep(4)
            resp = client.consultar_cte(resp.get('chave', ''))
        if resp.get('sucesso') or resp.get('codigo') == 100:
            ct.status = 'EMITIDO'
            ct.chave_acesso = resp.get('chave', '')
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
    from .services.integranotas import IntegranNotasClient, IntegranNotasError
    empresa = _get_empresa(request)
    ct = get_object_or_404(ConhecimentoTransporte, pk=pk, empresa=empresa)
    if ct.status != 'EMITIDO' or not ct.chave_acesso:
        messages.error(request, 'CC-e só pode ser enviada para CT-e autorizado.')
        return redirect('faturamento:cte_detail', pk=pk)

    cartas = ct.cartas_correcao.all()
    proxima_sequencia = cartas.count() + 1

    if request.method == 'POST':
        correcao = request.POST.get('correcao', '').strip()
        if len(correcao) < 15:
            messages.error(request, 'O texto da correção deve ter pelo menos 15 caracteres.')
            return render(request, 'faturamento/cte/carta_correcao_form.html',
                          {'ct': ct, 'cartas': cartas, 'proxima_sequencia': proxima_sequencia, 'correcao': correcao})
        try:
            config = empresa.configuracao_fiscal
            client = IntegranNotasClient(token=config.get_token(), ambiente=config.ambiente_nfe)
            resultado = client.carta_correcao_cte(ct.chave_acesso, correcao, proxima_sequencia)
        except IntegranNotasError as exc:
            messages.error(request, f'Erro [{exc.codigo}]: {exc}')
            return render(request, 'faturamento/cte/carta_correcao_form.html',
                          {'ct': ct, 'cartas': cartas, 'proxima_sequencia': proxima_sequencia, 'correcao': correcao})
        except Exception as exc:
            messages.error(request, f'Falha na comunicação: {exc}')
            return render(request, 'faturamento/cte/carta_correcao_form.html',
                          {'ct': ct, 'cartas': cartas, 'proxima_sequencia': proxima_sequencia, 'correcao': correcao})

        CartaCorrecaoCTe.objects.create(
            cte=ct,
            sequencia=proxima_sequencia,
            correcao=correcao,
            protocolo=resultado.get('protocolo', '') or resultado.get('numero_protocolo', ''),
            xml_retorno=resultado.get('xml', ''),
            criado_por=request.user,
        )
        messages.success(request, f'Carta de Correção nº {proxima_sequencia} enviada com sucesso.')
        return redirect('faturamento:cte_detail', pk=pk)

    return render(request, 'faturamento/cte/carta_correcao_form.html', {
        'ct': ct, 'cartas': cartas, 'proxima_sequencia': proxima_sequencia,
    })


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
    from django.shortcuts import redirect as _redirect
    from .services.integranotas import IntegranNotasClient, IntegranNotasError
    empresa = _get_empresa(request)
    ct = get_object_or_404(ConhecimentoTransporte, pk=pk, empresa=empresa)
    if ct.xml_autorizacao_url:
        return _redirect(ct.xml_autorizacao_url)
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
    resp = HttpResponse(xml_bytes, content_type='application/xml')
    resp['Content-Disposition'] = f'attachment; filename="CTE_{ct.numero}_{ct.serie}.xml"'
    return resp


@login_required
def cte_xml_cancelamento(request, pk):
    """Download do XML de cancelamento do CT-e (Supabase URL ou base64)."""
    import base64
    from django.shortcuts import redirect as _redirect
    empresa = _get_empresa(request)
    ct = get_object_or_404(ConhecimentoTransporte, pk=pk, empresa=empresa)
    if ct.xml_cancelamento_url:
        return _redirect(ct.xml_cancelamento_url)
    if not ct.xml_cancelamento:
        messages.error(request, 'XML de cancelamento não disponível para este CT-e.')
        return redirect('faturamento:cte_detail', pk=pk)
    xml_bytes = base64.b64decode(ct.xml_cancelamento)
    resp = HttpResponse(xml_bytes, content_type='application/xml')
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
    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'faturamento/mdfe/list.html', {
        'page_obj': page, 'status_filtro': status, 'q': q,
        'status_choices': ManifestoDocumentoFiscal.STATUS,
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
        form = ManifestoDocumentoFiscalForm(empresa=empresa)
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
def mdfe_emitir(request, pk):
    empresa = _get_empresa(request)
    mdfe = get_object_or_404(ManifestoDocumentoFiscal, pk=pk, empresa=empresa)
    if mdfe.status != 'RASCUNHO':
        messages.error(request, 'MDF-e ja emitido ou encerrado.')
        return redirect('faturamento:mdfe_detail', pk=pk)
    try:
        config = empresa.configuracao_fiscal
    except Exception:
        messages.error(request, 'Configure o token IntegraNotas em Faturamento > Configuracao Fiscal.')
        return redirect('faturamento:mdfe_detail', pk=pk)
    if not mdfe.numero:
        ultimo = ManifestoDocumentoFiscal.objects.filter(empresa=empresa).exclude(pk=pk).order_by('-numero').values_list('numero', flat=True).first()
        mdfe.numero = (ultimo or 0) + 1
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
                client.cancelar_mdfe(mdfe.chave_acesso, form.cleaned_data['justificativa'])
                mdfe.status = 'CANCELADO'
                mdfe.motivo_cancelamento = form.cleaned_data['justificativa']
                mdfe.data_cancelamento = timezone.now()
                mdfe.save()
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

