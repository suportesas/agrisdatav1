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
    OSRegistroExecucao, PushSubscriptionCampo, PortalCampoConfig,
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

    ctx = _base_ctx(request)
    ctx.update({
        'func': func,
        'os': os_obj,
        'alocacoes': alocacoes,
        'maquinas_detail': maquinas_detail,
        'insumos': insumos,
        'registro': registro,
    })
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
        os_obj.status = 'EM_ANDAMENTO'
        os_obj.data_inicio = timezone.now()
        os_obj.save(update_fields=['status', 'data_inicio'])
        messages.success(request, f'OS {os_obj.numero} iniciada.')
    else:
        messages.warning(request, 'Não é possível iniciar esta OS no status atual.')

    return redirect('portal_campo:os_detail', pk=pk)


# ──────────────────────────────────────────────────────────────────────────────
# REGISTRAR EXECUÇÃO (horas + dados por tipo de serviço)
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
        data_exec = request.POST.get('data_execucao') or str(date.today())
        hora_ini = request.POST.get('hora_inicio', '').strip()
        hora_fim = request.POST.get('hora_fim', '').strip()
        obs = request.POST.get('observacoes', '').strip()

        if hora_ini and hora_fim:
            OSFuncionario.objects.create(
                os=os_obj,
                funcionario=func,
                data_execucao=data_exec,
                hora_inicio=hora_ini,
                hora_fim=hora_fim,
                observacoes=obs,
            )
            if os_obj.status == 'APROVADA':
                os_obj.status = 'EM_ANDAMENTO'
                os_obj.data_inicio = timezone.now()
                os_obj.save(update_fields=['status', 'data_inicio'])

            foto = request.FILES.get('foto_evidencia')
            if foto:
                os_obj.foto_evidencia = foto
                os_obj.save(update_fields=['foto_evidencia'])

            _salvar_registro_execucao(request, os_obj, func, obs)

            messages.success(request, 'Horas e dados da operação registrados.')
            return redirect('portal_campo:os_detail', pk=pk)
        else:
            messages.error(request, 'Informe horário de início e fim.')

    veiculos = Vehicle.objects.filter(empresa=func.empresa, ativo=True).order_by('marca', 'modelo', 'descricao')
    funcionarios_empresa = Funcionario.objects.filter(empresa=func.empresa, ativo=True).order_by('nome_completo')
    produtos_insumo = Produto.objects.filter(ativo=True).select_related('unidade_medida').order_by('nome')
    portal_config, _ = PortalCampoConfig.objects.get_or_create(empresa=func.empresa)

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


def _worker_html(f):
    return (
        f'<div class="ajax-item d-flex justify-content-between align-items-center py-2 border-bottom" data-id="{f.pk}">'
        f'<div>'
        f'<div class="fw-semibold small">{f.funcionario.nome_completo}</div>'
        f'<div class="text-muted" style="font-size:.78rem;">'
        f'{f.data_execucao.strftime("%d/%m")} · {f.hora_inicio.strftime("%H:%M")}–{f.hora_fim.strftime("%H:%M")}'
        f'</div></div>'
        f'<button type="button" class="btn btn-sm btn-outline-danger rounded-circle p-0 ajax-del-worker" '
        f'data-id="{f.pk}" style="width:30px;height:30px;">'
        f'<i class="bi bi-trash"></i></button></div>'
    )


def _maquina_html(m):
    horas = f'{m.horas_trabalhadas:.1f}h' if m.horas_trabalhadas else ''
    hori = ''
    if m.horimetro_inicial is not None:
        hori = f' · H {m.horimetro_inicial}→{m.horimetro_final or "?"}'
    return (
        f'<div class="ajax-item d-flex justify-content-between align-items-center py-2 border-bottom" data-id="{m.pk}">'
        f'<div>'
        f'<div class="fw-semibold small">{m.veiculo}</div>'
        f'<div class="text-muted" style="font-size:.78rem;">'
        f'{m.data_execucao.strftime("%d/%m")}{hori} {horas}'
        f'</div></div>'
        f'<button type="button" class="btn btn-sm btn-outline-danger rounded-circle p-0 ajax-del-maquina" '
        f'data-id="{m.pk}" style="width:30px;height:30px;">'
        f'<i class="bi bi-trash"></i></button></div>'
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
        data_exec = body.get('data') or str(date.today())
        hora_ini = body.get('hora_inicio') or None
        hora_fim = body.get('hora_fim') or None

        # Se a config for OMITIR, usa horário do registro do operador como fallback
        if not hora_ini or not hora_fim:
            portal_config, _ = PortalCampoConfig.objects.get_or_create(empresa=func.empresa)
            if portal_config.horario_trabalhadores == PortalCampoConfig.HORARIO_TRABALHADORES_OMITIR:
                ultimo_reg = os_obj.funcionarios_os.filter(funcionario=func).order_by('-data_execucao', '-hora_inicio').first()
                if ultimo_reg:
                    hora_ini = hora_ini or str(ultimo_reg.hora_inicio)
                    hora_fim = hora_fim or str(ultimo_reg.hora_fim)
                    data_exec = data_exec or str(ultimo_reg.data_execucao)

        if not hora_ini or not hora_fim:
            return JsonResponse({'success': False, 'error': 'Informe início e término.'}, status=400)

        trab = Funcionario.objects.get(pk=fid, empresa=func.empresa)
        f_rec = OSFuncionario.objects.create(
            os=os_obj, funcionario=trab,
            data_execucao=data_exec, hora_inicio=hora_ini, hora_fim=hora_fim,
        )
        if os_obj.status == 'APROVADA':
            os_obj.status = 'EM_ANDAMENTO'
            os_obj.data_inicio = timezone.now()
            os_obj.save(update_fields=['status', 'data_inicio'])
        return JsonResponse({'success': True, 'id': f_rec.pk, 'html': _worker_html(f_rec)})
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
        veiculo = Vehicle.objects.get(pk=vid, empresa=func.empresa)
        m_rec = OSMaquina.objects.create(
            os=os_obj, veiculo=veiculo, data_execucao=data_exec,
            horimetro_inicial=h_ini, horimetro_final=h_fim,
        )
        if os_obj.status == 'APROVADA':
            os_obj.status = 'EM_ANDAMENTO'
            os_obj.data_inicio = timezone.now()
            os_obj.save(update_fields=['status', 'data_inicio'])
        return JsonResponse({'success': True, 'id': m_rec.pk, 'html': _maquina_html(m_rec)})
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

        from django.db import transaction
        with transaction.atomic():
            if foto:
                os_obj.foto_evidencia = foto
            os_obj.status = 'CONCLUIDA'
            os_obj.data_fim = timezone.now()
            os_obj.save(update_fields=['status', 'data_fim', 'foto_evidencia'])

            try:
                custo_obj = os_obj.custo
                custo_obj.recalcular()
            except Exception:
                pass

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
