"""
Portal do Campo — autenticação por CPF+PIN, execução e conclusão de OS no campo.
Mobile-first: sem sidebar, navegação inferior fixa.
"""
from datetime import date, timedelta
from functools import wraps

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Funcionario, OrdemServico, OSFuncionario, OrdemServicoInsumo

LOGIN_URL = 'portal_campo:login'
HOME_URL  = 'portal_campo:home'


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

    # OS em que o funcionário é responsável ou está alocado via OSFuncionario
    from django.db.models import Q
    os_ids_alocado = list(OSFuncionario.objects.filter(
        funcionario=func
    ).values_list('os_id', flat=True).distinct())

    os_unicas = list(OrdemServico.objects.filter(
        empresa=func.empresa
    ).filter(
        Q(responsavel=func) | Q(pk__in=os_ids_alocado)
    ).order_by('-data_prevista').distinct())

    # Reagrupa por grupo
    para_hoje = [o for o in os_unicas if o.status == 'APROVADA' and o.data_prevista == hoje]
    em_andamento = [o for o in os_unicas if o.status == 'EM_ANDAMENTO']
    concluidas_recentes = [o for o in os_unicas if o.status == 'CONCLUIDA' and o.data_fim and o.data_fim.date() >= sete_dias]

    return render(request, 'cadastros/portal_campo/home.html', {
        'func': func,
        'para_hoje': para_hoje,
        'em_andamento': em_andamento,
        'concluidas_recentes': concluidas_recentes[:5],
        'hoje': hoje,
    })


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

    alocacoes = os_obj.funcionarios_os.select_related('funcionario').all()
    insumos = os_obj.insumos.select_related('produto').all()

    return render(request, 'cadastros/portal_campo/os_detail.html', {
        'func': func,
        'os': os_obj,
        'alocacoes': alocacoes,
        'insumos': insumos,
    })


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
# REGISTRAR EXECUÇÃO (horas + foto parcial)
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
            # Avança para EM_ANDAMENTO se ainda APROVADA
            if os_obj.status == 'APROVADA':
                os_obj.status = 'EM_ANDAMENTO'
                os_obj.data_inicio = timezone.now()
                os_obj.save(update_fields=['status', 'data_inicio'])

            messages.success(request, 'Horas registradas com sucesso.')
            return redirect('portal_campo:os_detail', pk=pk)
        else:
            messages.error(request, 'Informe horário de início e fim.')

    return render(request, 'cadastros/portal_campo/os_executar_form.html', {
        'func': func,
        'os': os_obj,
        'hoje': str(date.today()),
    })


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

    return render(request, 'cadastros/portal_campo/os_concluir.html', {
        'func': func,
        'os': os_obj,
    })
