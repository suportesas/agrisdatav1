"""
Portal do Campo — autenticação por CPF+PIN, execução e conclusão de OS no campo.
Mobile-first / PWA: sem sidebar, navegação inferior fixa.
"""
import json
import os
from datetime import date, timedelta
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from rh.models import Funcionario
from operacoes_campo.models import (
    OrdemServico, OSFuncionario, OSMaquina, OrdemServicoInsumo,
    OSRegistroExecucao, OSIntervalo, PushSubscriptionCampo, PortalCampoConfig,
    CustoTalhao,
)
from frota.models import Vehicle
from produtos.models import Produto

LOGIN_URL = 'portal_campo:login'
HOME_URL  = 'portal_campo:home'

# Mapeamento tipo → template parcial de campos específicos
_TIPO_FORM_MAP = {
    'PULV_MECANICA': 'cadastros/portal_campo/execucao/_form_pulverizacao.html',
    'PULV_COSTAL':   'cadastros/portal_campo/execucao/_form_pulverizacao.html',
    'IRRIGACAO':     'cadastros/portal_campo/execucao/_form_irrigacao.html',
    'ADUBACAO':      'cadastros/portal_campo/execucao/_form_irrigacao.html',
    'PLANTIO':       'cadastros/portal_campo/execucao/_form_plantio.html',
    'PREPARO_SOLO':  'cadastros/portal_campo/execucao/_form_preparo_solo.html',
    'MANUTENCAO':    'cadastros/portal_campo/execucao/_form_tratos_culturais.html',
}


def _tipo_form_template(os_obj):
    return _TIPO_FORM_MAP.get(os_obj.tipo, 'cadastros/portal_campo/execucao/_form_generico.html')


# ──────────────────────────────────────────────────────────────────────────────
# AUTENTICAÇÃO
# ──────────────────────────────────────────────────────────────────────────────

def campo_login_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if 'campo_funcionario_id' not in request.session:
            return redirect(LOGIN_URL)
        return view_func(request, *args, **kwargs)
    return wrapper


def _get_funcionario(request):
    fid = request.session.get('campo_funcionario_id')
    if not fid:
        return None
    try:
        return Funcionario.objects.get(pk=fid, ativo=True, portal_ativo=True)
    except Funcionario.DoesNotExist:
        return None


def _base_ctx(request):
    """Contexto base injetado em todas as views do portal."""
    return {
        'vapid_public_key': getattr(settings, 'VAPID_PUBLIC_KEY', ''),
    }


def campo_login(request):
    if request.session.get('campo_funcionario_id'):
        return redirect(HOME_URL)

    error = None
    if request.method == 'POST':
        import re
        cpf_raw = request.POST.get('cpf', '').strip()
        pin = request.POST.get('pin', '').strip()
        cpf_digits = re.sub(r'\D', '', cpf_raw)

        func = None
        for f in Funcionario.objects.filter(ativo=True, portal_ativo=True):
            if re.sub(r'\D', '', f.cpf) == cpf_digits:
                func = f
                break

        if func and func.check_pin(pin):
            request.session['campo_funcionario_id'] = func.pk
            request.session['campo_funcionario_nome'] = func.nome_completo.split()[0]
            messages.success(request, f'Bem-vindo, {func.nome_completo.split()[0]}!')
            return redirect(HOME_URL)
        else:
            error = 'CPF ou PIN incorretos.'

    return render(request, 'cadastros/portal_campo/login.html', {'error': error})


def campo_logout(request):
    request.session.flush()
    return redirect(LOGIN_URL)


def campo_sw_js(request):
    """Serve o Service Worker dentro do escopo /portal/campo/ com header correto."""
    sw_path = os.path.join(settings.BASE_DIR, 'static', 'campo_pwa', 'sw.js')
    try:
        with open(sw_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        return HttpResponse('// SW not found', content_type='application/javascript', status=404)

    response = HttpResponse(content, content_type='application/javascript; charset=utf-8')
    response['Service-Worker-Allowed'] = '/'
    response['Cache-Control'] = 'no-cache, no-store'
    return response


# ──────────────────────────────────────────────────────────────────────────────
# DASHBOARD
# ──────────────────────────────────────────────────────────────────────────────

@campo_login_required
def campo_home(request):
    func = _get_funcionario(request)
    if not func:
        request.session.flush()
        return redirect(LOGIN_URL)

    hoje = date.today()
    sete_dias = hoje - timedelta(days=7)

    from django.db.models import Q
    os_ids_alocado = list(OSFuncionario.objects.filter(
        funcionario=func
    ).values_list('os_id', flat=True).distinct())

    os_unicas = list(OrdemServico.objects.filter(
        empresa=func.empresa
    ).filter(
        Q(responsavel=func) | Q(pk__in=os_ids_alocado)
    ).select_related(
        'tipo_servico', 'subtipo_servico', 'modalidade_execucao', 'talhao', 'safra'
    ).order_by('-data_prevista').distinct())

    # Todas as OS aprovadas — sem filtro de data (datas nulas ou passadas também aparecem)
    para_fazer = [o for o in os_unicas if o.status == 'APROVADA']
    para_fazer.sort(key=lambda o: (o.data_prevista is None, o.data_prevista or date.min))

    em_andamento = [o for o in os_unicas if o.status == 'EM_ANDAMENTO']
    concluidas_recentes = [
        o for o in os_unicas
        if o.status == 'CONCLUIDA' and o.data_fim and o.data_fim.date() >= sete_dias
    ]

    ctx = _base_ctx(request)
    ctx.update({
        'func': func,
        'para_fazer': para_fazer,
        'em_andamento': em_andamento,
        'concluidas_recentes': concluidas_recentes[:5],
        'hoje': hoje,
    })
    return render(request, 'cadastros/portal_campo/home.html', ctx)


# ──────────────────────────────────────────────────────────────────────────────
# DETALHE DA OS
# ──────────────────────────────────────────────────────────────────────────────

@campo_login_required
def campo_os_detail(request, pk):
    func = _get_funcionario(request)
    if not func:
        request.session.flush()
        return redirect(LOGIN_URL)

    os_obj = get_object_or_404(OrdemServico, pk=pk, empresa=func.empresa)
    alocacoes = os_obj.funcionarios_os.select_related('funcionario').order_by('data_execucao', 'hora_inicio')
    maquinas_detail = os_obj.maquinas_os.select_related('veiculo').order_by('data_execucao')
    insumos = os_obj.insumos_os.select_related('produto', 'unidade_medida').all()

    try:
        registro = os_obj.registro_execucao
    except OSRegistroExecucao.DoesNotExist:
        registro = None

    intervalos = os_obj.intervalos.select_related('funcionario').order_by('inicio')
    intervalo_aberto = intervalos.filter(fim__isnull=True).first()

    ctx = _base_ctx(request)
    ctx.update({
        'func': func,
        'os': os_obj,
        'alocacoes': alocacoes,
        'maquinas_detail': maquinas_detail,
        'insumos': insumos,
        'registro': registro,
        'intervalos': intervalos,
        'intervalo_aberto': intervalo_aberto,
        'hoje': str(date.today()),
    })
    # Selects de pré-montagem de equipe só são necessários na fase APROVADA
    if os_obj.status == 'APROVADA':
        ctx['funcionarios_empresa'] = Funcionario.objects.filter(
            empresa=func.empresa, ativo=True).order_by('nome_completo')
        ctx['veiculos'] = Vehicle.objects.filter(
            empresa=func.empresa, ativo=True).order_by('marca', 'modelo', 'descricao')
    return render(request, 'cadastros/portal_campo/os_detail.html', ctx)


# ──────────────────────────────────────────────────────────────────────────────
# INICIAR OS
# ──────────────────────────────────────────────────────────────────────────────

@campo_login_required
@require_POST
def campo_os_iniciar(request, pk):
    func = _get_funcionario(request)
    if not func:
        request.session.flush()
        return redirect(LOGIN_URL)

    os_obj = get_object_or_404(OrdemServico, pk=pk, empresa=func.empresa)

    if os_obj.status == 'APROVADA':
        agora = timezone.now()
        agora_local = timezone.localtime(agora)
        os_obj.status = 'EM_ANDAMENTO'
        os_obj.data_inicio = agora
        os_obj.save(update_fields=['status', 'data_inicio'])
        lat = request.POST.get('latitude') or None
        lng = request.POST.get('longitude') or None
        OSIntervalo.objects.create(os=os_obj, funcionario=func, inicio=agora, latitude=lat, longitude=lng)
        # Trabalhadores pré-definidos (sem hora_inicio) recebem o horário de início da OS
        os_obj.funcionarios_os.filter(hora_inicio__isnull=True).update(
            hora_inicio=agora_local.time(),
            data_execucao=agora_local.date(),
        )
        messages.success(request, f'OS {os_obj.numero} iniciada.')
        # Aviso não-bloqueante: máquinas sem horímetro inicial
        maquinas_sem_hini = os_obj.maquinas_os.filter(horimetro_inicial__isnull=True)
        if maquinas_sem_hini.exists():
            nomes = ', '.join(str(m.veiculo) for m in maquinas_sem_hini)
            messages.warning(request, f'Registre o horímetro inicial: {nomes}')
    else:
        messages.warning(request, 'Não é possível iniciar esta OS no status atual.')

    return redirect('portal_campo:os_detail', pk=pk)


# ──────────────────────────────────────────────────────────────────────────────
# PAUSAR OS
# ──────────────────────────────────────────────────────────────────────────────

@campo_login_required
@require_POST
def campo_os_pausar(request, pk):
    func = _get_funcionario(request)
    if not func:
        request.session.flush()
        return redirect(LOGIN_URL)

    os_obj = get_object_or_404(OrdemServico, pk=pk, empresa=func.empresa)

    if os_obj.status != 'EM_ANDAMENTO':
        messages.warning(request, 'Não é possível pausar esta OS.')
        return redirect('portal_campo:os_detail', pk=pk)

    intervalo = os_obj.intervalos.filter(fim__isnull=True, funcionario=func).first()
    if not intervalo:
        messages.warning(request, 'Nenhum intervalo aberto encontrado.')
        return redirect('portal_campo:os_detail', pk=pk)

    intervalo.fim = timezone.now()
    intervalo.save(update_fields=['fim'])

    messages.info(request, 'OS pausada. Retome quando quiser continuar.')
    return redirect('portal_campo:os_detail', pk=pk)


# ──────────────────────────────────────────────────────────────────────────────
# RETOMAR OS
# ──────────────────────────────────────────────────────────────────────────────

@campo_login_required
@require_POST
def campo_os_retomar(request, pk):
    func = _get_funcionario(request)
    if not func:
        request.session.flush()
        return redirect(LOGIN_URL)

    os_obj = get_object_or_404(OrdemServico, pk=pk, empresa=func.empresa)

    if os_obj.status != 'EM_ANDAMENTO':
        messages.warning(request, 'Não é possível retomar esta OS.')
        return redirect('portal_campo:os_detail', pk=pk)

    if os_obj.intervalos.filter(fim__isnull=True, funcionario=func).exists():
        messages.warning(request, 'Esta OS já está em andamento.')
        return redirect('portal_campo:os_detail', pk=pk)

    lat = request.POST.get('latitude') or None
    lng = request.POST.get('longitude') or None
    OSIntervalo.objects.create(os=os_obj, funcionario=func, inicio=timezone.now(), latitude=lat, longitude=lng)

    messages.success(request, 'OS retomada. Bom trabalho!')
    return redirect('portal_campo:os_detail', pk=pk)


# ──────────────────────────────────────────────────────────────────────────────
# REGISTRAR EXECUÇÃO (dados por tipo de serviço, insumos, máquinas, foto)
# ──────────────────────────────────────────────────────────────────────────────

@campo_login_required
def campo_os_executar(request, pk):
    func = _get_funcionario(request)
    if not func:
        request.session.flush()
        return redirect(LOGIN_URL)

    os_obj = get_object_or_404(OrdemServico, pk=pk, empresa=func.empresa)

    if os_obj.status not in ('APROVADA', 'EM_ANDAMENTO'):
        messages.error(request, 'Esta OS não pode ser executada no status atual.')
        return redirect('portal_campo:os_detail', pk=pk)

    try:
        registro = os_obj.registro_execucao
    except OSRegistroExecucao.DoesNotExist:
        registro = None

    if request.method == 'POST':
        obs = request.POST.get('observacoes', '').strip()

        foto = request.FILES.get('foto_evidencia')
        if foto:
            os_obj.foto_evidencia = foto
            os_obj.save(update_fields=['foto_evidencia'])

        area = request.POST.get('area_executada_ha', '').strip()
        if area:
            os_obj.area_executada_ha = area
            os_obj.save(update_fields=['area_executada_ha'])

        _salvar_registro_execucao(request, os_obj, func, obs)

        messages.success(request, 'Dados da operação salvos.')
        return redirect('portal_campo:os_detail', pk=pk)

    veiculos = Vehicle.objects.filter(empresa=func.empresa, ativo=True).order_by('marca', 'modelo', 'descricao')
    funcionarios_empresa = Funcionario.objects.filter(empresa=func.empresa, ativo=True).order_by('nome_completo')
    produtos_insumo = Produto.objects.filter(ativo=True).select_related('unidade_medida').order_by('nome')
    portal_config, _ = PortalCampoConfig.objects.get_or_create(empresa=func.empresa)

    # Horário do operador nesta OS para pré-preencher os campos de trabalhadores adicionais.
    # Usa o intervalo aberto; se não houver, usa o intervalo mais recente encerrado.
    intervalo_op = (
        os_obj.intervalos.filter(funcionario=func, fim__isnull=True).first()
        or os_obj.intervalos.filter(funcionario=func).order_by('-inicio').first()
    )
    if intervalo_op:
        hora_ini_operador = timezone.localtime(intervalo_op.inicio).strftime('%H:%M')
        data_execucao_operador = str(timezone.localtime(intervalo_op.inicio).date())
    else:
        hora_ini_operador = ''
        data_execucao_operador = str(date.today())

    ctx = _base_ctx(request)
    ctx.update({
        'func': func,
        'os': os_obj,
        'registro': registro,
        'hoje': str(date.today()),
        'tipo_form': _tipo_form_template(os_obj),
        'veiculos': veiculos,
        'funcionarios_empresa': funcionarios_empresa,
        'produtos_insumo': produtos_insumo,
        'funcionarios_registrados': os_obj.funcionarios_os.select_related('funcionario').order_by('data_execucao', 'hora_inicio'),
        'maquinas_registradas': os_obj.maquinas_os.select_related('veiculo').order_by('data_execucao'),
        'insumos_os': os_obj.insumos_os.select_related('produto', 'unidade_medida').order_by('id'),
        'portal_config': portal_config,
        'hora_ini_operador': hora_ini_operador,
        'data_execucao_operador': data_execucao_operador,
    })
    return render(request, 'cadastros/portal_campo/os_executar_form.html', ctx)


# ──────────────────────────────────────────────────────────────────────────────
# AJAX CRUD — Trabalhadores / Máquinas / Insumos da OS
# ──────────────────────────────────────────────────────────────────────────────

def _os_ajax_guard(request, pk):
    """Retorna (func, os_obj) ou raise Http404 se inválido."""
    func = _get_funcionario(request)
    if not func:
        return None, None
    os_obj = get_object_or_404(OrdemServico, pk=pk, empresa=func.empresa)
    return func, os_obj


def _fmt_date(d):
    """Formata date ou string 'YYYY-MM-DD' como 'dd/mm'. Robusto contra strings retornadas pelo ORM."""
    if not d:
        return '–'
    if hasattr(d, 'strftime'):
        return d.strftime('%d/%m')
    try:
        from datetime import datetime as _dt
        return _dt.strptime(str(d)[:10], '%Y-%m-%d').strftime('%d/%m')
    except Exception:
        return str(d)


def _fmt_time(t):
    """Formata time ou string 'HH:MM[:SS]' como 'HH:MM'. Robusto contra strings."""
    if not t:
        return None
    if hasattr(t, 'strftime'):
        return t.strftime('%H:%M')
    return str(t)[:5]


def _worker_html(f):
    data_str = _fmt_date(f.data_execucao)
    ini_str  = _fmt_time(f.hora_inicio) or '--:--'
    fim_str  = _fmt_time(f.hora_fim) or '?'
    return (
        f'<div class="ajax-item d-flex justify-content-between align-items-center py-2 border-bottom" data-id="{f.pk}">'
        f'<div>'
        f'<div class="fw-semibold small">{f.funcionario.nome_completo}</div>'
        f'<div class="text-muted" style="font-size:.78rem;">'
        f'{data_str} · {ini_str}–{fim_str}'
        f'</div></div>'
        f'<button type="button" class="btn btn-sm btn-outline-danger rounded-circle p-0 ajax-del-worker" '
        f'data-id="{f.pk}" style="width:30px;height:30px;">'
        f'<i class="bi bi-trash"></i></button></div>'
    )


def _maquina_html(m):
    horas = f'{m.horas_trabalhadas:.1f}h' if m.horas_trabalhadas else ''
    hori = ''
    h_ini_val = str(m.horimetro_inicial) if m.horimetro_inicial is not None else ''
    h_fim_val = str(m.horimetro_final) if m.horimetro_final is not None else ''
    if m.horimetro_inicial is not None:
        hori = f' · H {m.horimetro_inicial}→{m.horimetro_final or "?"}'
    return (
        f'<div class="ajax-item border-bottom" data-id="{m.pk}">'
        f'<div class="d-flex justify-content-between align-items-center py-2">'
        f'<div>'
        f'<div class="fw-semibold small">{m.veiculo}</div>'
        f'<div class="text-muted" style="font-size:.78rem;">'
        f'{_fmt_date(m.data_execucao)}{hori} {horas}'
        f'</div></div>'
        f'<div class="d-flex gap-1">'
        f'<button type="button" class="btn btn-sm btn-outline-secondary rounded-circle p-0 ajax-edit-maquina" '
        f'data-id="{m.pk}" data-hini="{h_ini_val}" data-hfim="{h_fim_val}" style="width:30px;height:30px;" title="Editar horímetro">'
        f'<i class="bi bi-pencil" style="font-size:.7rem;"></i></button>'
        f'<button type="button" class="btn btn-sm btn-outline-danger rounded-circle p-0 ajax-del-maquina" '
        f'data-id="{m.pk}" style="width:30px;height:30px;">'
        f'<i class="bi bi-trash"></i></button>'
        f'</div></div>'
        f'<div class="maq-edit-form d-none px-1 pb-2" data-id="{m.pk}">'
        f'<div class="row g-2 align-items-end">'
        f'<div class="col-5"><label class="form-label small text-muted mb-1">H.Ini (h)</label>'
        f'<input type="number" class="form-control form-control-sm maq-hini" step="0.01" min="0" value="{h_ini_val}" placeholder="Opcional"></div>'
        f'<div class="col-5"><label class="form-label small text-muted mb-1">H.Fim (h)</label>'
        f'<input type="number" class="form-control form-control-sm maq-hfim" step="0.01" min="0" value="{h_fim_val}" placeholder="Opcional"></div>'
        f'<div class="col-2"><button type="button" class="btn btn-sm btn-success w-100 maq-save-edit" data-id="{m.pk}">'
        f'<i class="bi bi-check-lg"></i></button></div>'
        f'</div></div>'
        f'</div>'
    )


def _insumo_html(ins):
    un = str(ins.unidade_medida) if ins.unidade_medida_id else ''
    return (
        f'<div class="ajax-item d-flex justify-content-between align-items-center py-2 border-bottom" data-id="{ins.pk}">'
        f'<div>'
        f'<div class="fw-semibold small">{ins.produto.nome}</div>'
        f'<div class="text-muted" style="font-size:.78rem;">'
        f'{ins.quantidade_aplicada} {un}'
        f'</div></div>'
        f'<button type="button" class="btn btn-sm btn-outline-danger rounded-circle p-0 ajax-del-insumo" '
        f'data-id="{ins.pk}" style="width:30px;height:30px;">'
        f'<i class="bi bi-trash"></i></button></div>'
    )


@campo_login_required
@require_POST
def ajax_add_worker(request, pk):
    func, os_obj = _os_ajax_guard(request, pk)
    if not func:
        return JsonResponse({'success': False, 'error': 'Não autorizado'}, status=403)
    try:
        body = json.loads(request.body)
        fid = int(body['funcionario_id'])
        hora_ini = body.get('hora_inicio') or None
        hora_fim = body.get('hora_fim') or None
        data_exec = body.get('data') or None

        # Fallback: usa OSIntervalo do operador nesta OS como fonte do horário.
        # Funciona tanto no modo OMITIR quanto no AUTO (quando o operador não preencheu hora_ini).
        if not hora_ini or not data_exec:
            intervalo_op = (
                os_obj.intervalos.filter(funcionario=func, fim__isnull=True).first()
                or os_obj.intervalos.filter(funcionario=func).order_by('-inicio').first()
            )
            if intervalo_op:
                inicio_local = timezone.localtime(intervalo_op.inicio)
                hora_ini = hora_ini or inicio_local.strftime('%H:%M')
                data_exec = data_exec or str(inicio_local.date())
                # hora_fim: só copia se o intervalo já estiver encerrado e o campo estiver vazio
                if not hora_fim and intervalo_op.fim:
                    hora_fim = timezone.localtime(intervalo_op.fim).strftime('%H:%M')

        data_exec = data_exec or str(date.today())

        trab = Funcionario.objects.get(pk=fid, empresa=func.empresa)
        f_rec = OSFuncionario.objects.create(
            os=os_obj, funcionario=trab,
            data_execucao=data_exec, hora_inicio=hora_ini, hora_fim=hora_fim,
        )
        f_rec.refresh_from_db()  # garante tipos Python corretos (date/time) após create com strings
        # Nota: a transição APROVADA→EM_ANDAMENTO ocorre exclusivamente via campo_os_iniciar.
        # Adicionar equipe pré-start não muda o status da OS.
        return JsonResponse({
            'success': True,
            'id': f_rec.pk,
            'nome': trab.nome_completo,
            'html': _worker_html(f_rec),
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@campo_login_required
@require_POST
def ajax_del_worker(request, pk, item_pk):
    func, os_obj = _os_ajax_guard(request, pk)
    if not func:
        return JsonResponse({'success': False}, status=403)
    try:
        OSFuncionario.objects.get(pk=item_pk, os=os_obj).delete()
        return JsonResponse({'success': True})
    except OSFuncionario.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Não encontrado'}, status=404)


@campo_login_required
@require_POST
def ajax_add_maquina(request, pk):
    func, os_obj = _os_ajax_guard(request, pk)
    if not func:
        return JsonResponse({'success': False}, status=403)
    try:
        body = json.loads(request.body)
        vid = int(body['veiculo_id'])
        data_exec = body.get('data') or str(date.today())
        h_ini = body.get('horimetro_inicial') or None
        h_fim = body.get('horimetro_final') or None

        # EM_ANDAMENTO: horímetro inicial obrigatório
        if os_obj.status == 'EM_ANDAMENTO' and not h_ini:
            return JsonResponse({
                'success': False,
                'error': 'Informe o horímetro inicial para registrar o uso da máquina.'
            }, status=400)

        veiculo = Vehicle.objects.get(pk=vid, empresa=func.empresa)
        m_rec = OSMaquina.objects.create(
            os=os_obj, veiculo=veiculo, data_execucao=data_exec,
            horimetro_inicial=h_ini, horimetro_final=h_fim,
        )
        m_rec.refresh_from_db()  # garante tipos Python corretos (date/Decimal) após create com strings
        # Nota: a transição APROVADA→EM_ANDAMENTO ocorre exclusivamente via campo_os_iniciar.
        return JsonResponse({
            'success': True,
            'id': m_rec.pk,
            'veiculo': str(veiculo),
            'html': _maquina_html(m_rec),
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@campo_login_required
@require_POST
def ajax_edit_maquina(request, pk, item_pk):
    """Atualiza horímetro inicial/final de uma máquina já adicionada à OS."""
    func, os_obj = _os_ajax_guard(request, pk)
    if not func:
        return JsonResponse({'success': False}, status=403)
    try:
        body = json.loads(request.body)
        m_rec = OSMaquina.objects.get(pk=item_pk, os=os_obj)
        h_ini = body.get('horimetro_inicial') or None
        h_fim = body.get('horimetro_final') or None
        m_rec.horimetro_inicial = h_ini
        m_rec.horimetro_final = h_fim
        m_rec.save(update_fields=['horimetro_inicial', 'horimetro_final'])
        m_rec.refresh_from_db()
        return JsonResponse({'success': True, 'html': _maquina_html(m_rec)})
    except OSMaquina.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@campo_login_required
@require_POST
def ajax_del_maquina(request, pk, item_pk):
    func, os_obj = _os_ajax_guard(request, pk)
    if not func:
        return JsonResponse({'success': False}, status=403)
    try:
        OSMaquina.objects.get(pk=item_pk, os=os_obj).delete()
        return JsonResponse({'success': True})
    except OSMaquina.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Não encontrado'}, status=404)


@campo_login_required
@require_POST
def ajax_add_insumo(request, pk):
    func, os_obj = _os_ajax_guard(request, pk)
    if not func:
        return JsonResponse({'success': False}, status=403)
    try:
        body = json.loads(request.body)
        pid = int(body['produto_id'])
        qtd = body.get('quantidade') or None
        if not qtd:
            return JsonResponse({'success': False, 'error': 'Informe a quantidade'}, status=400)
        produto = Produto.objects.select_related('unidade_medida').get(pk=pid)
        ins = OrdemServicoInsumo.objects.create(
            os=os_obj, empresa=os_obj.empresa, produto=produto,
            unidade_medida=produto.unidade_medida,
            quantidade_aplicada=qtd,
            observacoes='Lançado pelo operador via portal do campo',
        )
        return JsonResponse({'success': True, 'id': ins.pk, 'html': _insumo_html(ins)})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@campo_login_required
@require_POST
def ajax_del_insumo(request, pk, item_pk):
    func, os_obj = _os_ajax_guard(request, pk)
    if not func:
        return JsonResponse({'success': False}, status=403)
    try:
        OrdemServicoInsumo.objects.get(pk=item_pk, os=os_obj).delete()
        return JsonResponse({'success': True})
    except OrdemServicoInsumo.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Não encontrado'}, status=404)


def _salvar_registro_execucao(request, os_obj, func, obs):
    """Cria ou atualiza OSRegistroExecucao com dados do POST."""
    p = request.POST

    defaults = {
        'empresa': os_obj.empresa,
        'registrado_por': func,
        'observacoes': obs,
        'area_executada_ha': p.get('area_executada_ha') or None,
        # Pulverização
        'volume_calda_litros': p.get('volume_calda_litros') or None,
        'vazao_bicos_lmin': p.get('vazao_bicos_lmin') or None,
        'velocidade_kmh': p.get('velocidade_kmh') or None,
        'condicao_vento': p.get('condicao_vento', ''),
        'temperatura_c': p.get('temperatura_c') or None,
        'umidade_relativa_pct': p.get('umidade_relativa_pct') or None,
        # Irrigação / Fertirrigação
        'horas_bomba': p.get('horas_bomba') or None,
        'volume_agua_m3': p.get('volume_agua_m3') or None,
        'setor_irrigado': p.get('setor_irrigado', ''),
        # Preparo de Solo
        'profundidade_cm': p.get('profundidade_cm') or None,
        'implemento_utilizado': p.get('implemento_utilizado', ''),
        # Plantio
        'quantidade_mudas': p.get('quantidade_mudas') or None,
        'espacamento_m': p.get('espacamento_m') or None,
        'plantio_em_estufa': 'plantio_em_estufa' in p,
        # Tratos Culturais
        'tipo_trato': p.get('tipo_trato', ''),
        'tipo_trato_outro': p.get('tipo_trato_outro', ''),
    }

    try:
        reg = os_obj.registro_execucao
        for k, v in defaults.items():
            setattr(reg, k, v)
        reg.save()
    except OSRegistroExecucao.DoesNotExist:
        OSRegistroExecucao.objects.create(ordem_servico=os_obj, **defaults)


# ──────────────────────────────────────────────────────────────────────────────
# CONCLUIR OS (foto obrigatória)
# ──────────────────────────────────────────────────────────────────────────────

@campo_login_required
def campo_os_concluir(request, pk):
    func = _get_funcionario(request)
    if not func:
        request.session.flush()
        return redirect(LOGIN_URL)

    os_obj = get_object_or_404(OrdemServico, pk=pk, empresa=func.empresa)

    if os_obj.status not in ('APROVADA', 'EM_ANDAMENTO'):
        messages.error(request, 'Esta OS não pode ser concluída no status atual.')
        return redirect('portal_campo:os_detail', pk=pk)

    if request.method == 'POST':
        foto = request.FILES.get('foto_evidencia')
        if not foto and not os_obj.foto_evidencia:
            messages.error(request, 'Uma foto de evidência é obrigatória (RN-03).')
            return redirect('portal_campo:os_concluir', pk=pk)

        # Bloqueia se alguma máquina tem horímetro inicial mas falta o final
        pendentes_hfim = os_obj.maquinas_os.filter(
            horimetro_inicial__isnull=False, horimetro_final__isnull=True
        )
        if pendentes_hfim.exists():
            nomes = ', '.join(str(m.veiculo) for m in pendentes_hfim)
            messages.error(request, f'Preencha o horímetro final antes de concluir: {nomes}')
            return redirect('portal_campo:os_concluir', pk=pk)

        from django.db import transaction
        with transaction.atomic():
            agora = timezone.now()
            agora_local = timezone.localtime(agora)
            # Fecha todos os intervalos abertos
            os_obj.intervalos.filter(fim__isnull=True).update(fim=agora)

            # Backfill hora_inicio para trabalhadores sem entrada
            data_inicio = os_obj.data_inicio or agora
            data_inicio_local = timezone.localtime(data_inicio)
            os_obj.funcionarios_os.filter(hora_inicio__isnull=True).update(
                hora_inicio=data_inicio_local.time(),
                data_execucao=data_inicio_local.date(),
            )
            # Preenche hora_fim de todos os trabalhadores sem saída
            os_obj.funcionarios_os.filter(hora_fim__isnull=True).update(
                hora_fim=agora_local.time(),
            )

            if foto:
                os_obj.foto_evidencia = foto
            os_obj.status = 'CONCLUIDA'
            os_obj.data_fim = agora
            os_obj.save(update_fields=['status', 'data_fim', 'foto_evidencia'])

            try:
                custo_obj, _ = CustoTalhao.objects.get_or_create(
                    os=os_obj,
                    defaults={
                        'empresa': os_obj.empresa,
                        'talhao': os_obj.talhao,
                        'safra': os_obj.safra,
                    },
                )
                custo_obj.recalcular()
            except Exception as e:
                import logging
                logging.getLogger(__name__).error('Erro ao gerar CustoTalhao para OS %s: %s', os_obj.pk, e)

        messages.success(request, f'OS {os_obj.numero} concluída com sucesso!')
        return redirect('portal_campo:home')

    ctx = _base_ctx(request)
    ctx.update({'func': func, 'os': os_obj})
    return render(request, 'cadastros/portal_campo/os_concluir.html', ctx)


# ──────────────────────────────────────────────────────────────────────────────
# PUSH SUBSCRIPTION (PWA)
# ──────────────────────────────────────────────────────────────────────────────

@campo_login_required
def campo_push_subscribe(request):
    """Recebe o JSON de subscription Web Push e salva no banco."""
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)

    func = _get_funcionario(request)
    if not func:
        return JsonResponse({'ok': False}, status=403)

    try:
        data = json.loads(request.body)
        endpoint = data['endpoint']
        p256dh = data['p256dh']
        auth = data['auth']
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({'ok': False, 'error': 'payload inválido'}, status=400)

    PushSubscriptionCampo.objects.update_or_create(
        funcionario=func,
        endpoint=endpoint,
        defaults={
            'empresa': func.empresa,
            'p256dh': p256dh,
            'auth': auth,
            'ativo': True,
        },
    )
    return JsonResponse({'ok': True})


# ──────────────────────────────────────────────────────────────────────────────
# SYNC OFFLINE → SERVIDOR
# ──────────────────────────────────────────────────────────────────────────────

@campo_login_required
def campo_sync_offline(request):
    """
    Endpoint chamado pelo pwa.js ao reconectar.
    Aceita JSON com lista de mutações enfileiradas offline e as processa.
    Retorna lista de resultados por id de fila.
    """
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)

    func = _get_funcionario(request)
    if not func:
        return JsonResponse({'ok': False}, status=403)

    try:
        body = json.loads(request.body)
        items = body.get('queue', [])
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({'ok': False, 'error': 'payload inválido'}, status=400)

    from django.test import RequestFactory
    results = []

    for item in items:
        queue_id = item.get('id')
        endpoint = item.get('endpoint', '')
        method = item.get('method', 'POST').upper()
        payload = item.get('payload', {})

        result = _process_offline_mutation(request, func, endpoint, method, payload)
        results.append({'id': queue_id, 'ok': result['ok'], 'detail': result.get('detail', '')})

    return JsonResponse({'ok': True, 'results': results})


def _process_offline_mutation(request, func, endpoint, method, payload):
    """Processa uma mutação offline mapeando endpoint → ação Django."""
    import re

    # OS iniciar: /portal/campo/os/<pk>/iniciar/
    m = re.match(r'.*/os/(\d+)/iniciar/?$', endpoint)
    if m:
        pk = int(m.group(1))
        try:
            os_obj = OrdemServico.objects.get(pk=pk, empresa=func.empresa)
            if os_obj.status == 'APROVADA':
                os_obj.status = 'EM_ANDAMENTO'
                os_obj.data_inicio = timezone.now()
                os_obj.save(update_fields=['status', 'data_inicio'])
            return {'ok': True}
        except OrdemServico.DoesNotExist:
            return {'ok': False, 'detail': 'OS não encontrada'}

    # OS executar: /portal/campo/os/<pk>/executar/
    m = re.match(r'.*/os/(\d+)/executar/?$', endpoint)
    if m:
        pk = int(m.group(1))
        try:
            os_obj = OrdemServico.objects.get(pk=pk, empresa=func.empresa)
            hora_ini = payload.get('hora_inicio', '').strip()
            hora_fim = payload.get('hora_fim', '').strip()
            if hora_ini and hora_fim:
                OSFuncionario.objects.create(
                    os=os_obj, funcionario=func,
                    data_execucao=payload.get('data_execucao', str(timezone.now().date())),
                    hora_inicio=hora_ini, hora_fim=hora_fim,
                    observacoes=payload.get('observacoes', ''),
                )
                if os_obj.status == 'APROVADA':
                    os_obj.status = 'EM_ANDAMENTO'
                    os_obj.data_inicio = timezone.now()
                    os_obj.save(update_fields=['status', 'data_inicio'])
                _salvar_registro_execucao_dict(payload, os_obj, func)
            return {'ok': True}
        except OrdemServico.DoesNotExist:
            return {'ok': False, 'detail': 'OS não encontrada'}

    return {'ok': False, 'detail': f'endpoint não mapeado: {endpoint}'}


def _salvar_registro_execucao_dict(payload, os_obj, func):
    """Igual a _salvar_registro_execucao mas aceita dict ao invés de request.POST."""
    p = payload
    defaults = {
        'empresa': os_obj.empresa,
        'registrado_por': func,
        'observacoes': p.get('observacoes', ''),
        'area_executada_ha': p.get('area_executada_ha') or None,
        'volume_calda_litros': p.get('volume_calda_litros') or None,
        'vazao_bicos_lmin': p.get('vazao_bicos_lmin') or None,
        'velocidade_kmh': p.get('velocidade_kmh') or None,
        'condicao_vento': p.get('condicao_vento', ''),
        'temperatura_c': p.get('temperatura_c') or None,
        'umidade_relativa_pct': p.get('umidade_relativa_pct') or None,
        'horas_bomba': p.get('horas_bomba') or None,
        'volume_agua_m3': p.get('volume_agua_m3') or None,
        'setor_irrigado': p.get('setor_irrigado', ''),
        'profundidade_cm': p.get('profundidade_cm') or None,
        'implemento_utilizado': p.get('implemento_utilizado', ''),
        'quantidade_mudas': p.get('quantidade_mudas') or None,
        'espacamento_m': p.get('espacamento_m') or None,
        'plantio_em_estufa': bool(p.get('plantio_em_estufa')),
        'tipo_trato': p.get('tipo_trato', ''),
        'tipo_trato_outro': p.get('tipo_trato_outro', ''),
    }
    try:
        reg = os_obj.registro_execucao
        for k, v in defaults.items():
            setattr(reg, k, v)
        reg.save()
    except OSRegistroExecucao.DoesNotExist:
        OSRegistroExecucao.objects.create(ordem_servico=os_obj, **defaults)
