"""
Telas de gestão de Programa (tela do sistema) — estilo MadBuilder:
lista de Programas + tela de detalhe onde se gerencia as Ações
(Detalhe/Excluir) de uma tela de Listagem e quais Funções (Roles) têm
acesso a cada uma.

Ver `empresas/acesso.py` (docstring "Herança Listagem → Detalhe/Excluir")
para a regra de negócio que essas telas configuram.
"""

import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .models import Programa, Role
from .views import APP_LABELS_PT


def _pode_gerenciar(user):
    """Ver a tela e mexer nos 'Grupos' (Funções da própria empresa) — Programa
    em si é compartilhado por todo o SaaS, mas quais Funções DA MINHA empresa
    o acessam é um dado por empresa, então o admin de empresa mexe nisso."""
    return user.is_superuser or (hasattr(user, 'is_admin_empresa') and user.is_admin_empresa())


def _pode_editar_global(user):
    """Editar nome/caminho do Programa e criar Ações manuais — afeta a
    exibição em TODAS as empresas do SaaS, então é restrito ao superusuário."""
    return user.is_superuser


@login_required
def programa_list(request):
    if not request.user.empresa and not request.user.is_superuser:
        messages.warning(request, 'Nenhuma empresa vinculada à sua conta.')
        return redirect('dashboard:index')
    if not _pode_gerenciar(request.user):
        messages.error(request, '⛔ Você não tem permissão para acessar esta área.')
        return redirect('dashboard:index')

    q = request.GET.get('q', '').strip()
    app_filtro = request.GET.get('app', '').strip()

    programas = Programa.objects.filter(ativo=True).order_by('app_label', 'grupo_tela', 'tipo_acao')
    if q:
        programas = programas.filter(nome__icontains=q)
    if app_filtro:
        programas = programas.filter(app_label=app_filtro)

    paginator = Paginator(programas, 50)
    page_obj = paginator.get_page(request.GET.get('page'))

    apps_disponiveis = sorted(
        Programa.objects.filter(ativo=True).values_list('app_label', flat=True).distinct()
    )

    context = {
        'page_obj': page_obj,
        'q': q,
        'app_filtro': app_filtro,
        'apps_disponiveis': [(a, APP_LABELS_PT.get(a, a.replace('_', ' ').title())) for a in apps_disponiveis],
        'app_labels_pt': APP_LABELS_PT,
    }
    return render(request, 'empresas/programa_list.html', context)


@login_required
def programa_detail(request, pk):
    programa = get_object_or_404(Programa, pk=pk)
    if not _pode_gerenciar(request.user):
        messages.error(request, '⛔ Você não tem permissão para acessar esta área.')
        return redirect('dashboard:index')

    empresa = request.user.empresa
    roles = Role.objects.filter(empresa=empresa).order_by('name') if empresa else Role.objects.none()

    acoes = []
    if programa.tipo_acao == 'listagem':
        acoes = list(
            Programa.objects.filter(
                app_label=programa.app_label, grupo_tela=programa.grupo_tela,
                tipo_acao__in=['detalhe', 'excluir', 'outro'], ativo=True,
            ).exclude(pk=programa.pk).order_by('tipo_acao', 'nome')
        )

    context = {
        'programa': programa,
        'acoes': acoes,
        'roles': roles,
        'roles_com_acesso': set(programa.roles.filter(empresa=empresa).values_list('id', flat=True)) if empresa else set(),
        'app_labels_pt': APP_LABELS_PT,
        'pode_editar_global': _pode_editar_global(request.user),
    }
    return render(request, 'empresas/programa_detail.html', context)


@login_required
def programa_update(request, pk):
    """POST: atualiza nome/caminho_menu do Programa (afeta todas as empresas — só superuser)."""
    programa = get_object_or_404(Programa, pk=pk)
    if not _pode_editar_global(request.user):
        messages.error(request, '⛔ Só o administrador do SaaS pode editar dados do Programa.')
        return redirect('empresas:programa_detail', pk=pk)

    nome = request.POST.get('nome', '').strip()
    caminho_menu = request.POST.get('caminho_menu', '').strip()
    if nome:
        programa.nome = nome
        programa.nome_customizado = True
    programa.caminho_menu = caminho_menu
    programa.save()
    messages.success(request, '✅ Programa atualizado.')
    return redirect('empresas:programa_detail', pk=programa.pk)


@login_required
def programa_set_roles(request, pk):
    """POST (AJAX): define quais Funções (da empresa do usuário) têm acesso a este Programa."""
    programa = get_object_or_404(Programa, pk=pk)
    if not _pode_gerenciar(request.user):
        return JsonResponse({'error': 'Permissão negada'}, status=403)

    empresa = request.user.empresa
    if not empresa:
        return JsonResponse({'error': 'Usuário sem empresa vinculada'}, status=400)

    try:
        payload = json.loads(request.body.decode('utf-8'))
        role_ids = payload.get('role_ids', [])
    except Exception:
        return JsonResponse({'error': 'Payload inválido'}, status=400)

    roles_da_empresa = Role.objects.filter(empresa=empresa)
    # Mantém intocadas as concessões de Funções de OUTRAS empresas (Programa é global)
    outras_empresas = set(programa.roles.exclude(empresa=empresa).values_list('id', flat=True))
    novas = set(roles_da_empresa.filter(id__in=role_ids).values_list('id', flat=True))
    programa.roles.set(outras_empresas | novas)

    return JsonResponse({'ok': True, 'total': len(novas)})


@login_required
def programa_acao_create(request, pk):
    """Cria uma Ação manual (sem URL própria) vinculada ao mesmo grupo_tela
    do Programa de Listagem informado — ver Programa.descoberta_automatica.
    Afeta todas as empresas do SaaS — só superuser."""
    programa = get_object_or_404(Programa, pk=pk)
    if not _pode_editar_global(request.user):
        messages.error(request, '⛔ Só o administrador do SaaS pode criar Ações.')
        return redirect('empresas:programa_detail', pk=pk)

    nome = request.POST.get('nome', '').strip()
    if not nome:
        messages.error(request, 'Informe um nome para a ação.')
        return redirect('empresas:programa_detail', pk=pk)

    from django.utils.text import slugify
    sufixo = slugify(nome).replace('-', '_')
    url_name = f'{programa.app_label}:{programa.grupo_tela}_{sufixo}'

    if Programa.objects.filter(url_name=url_name).exists():
        messages.error(request, 'Já existe uma ação com esse nome pra essa tela.')
        return redirect('empresas:programa_detail', pk=pk)

    Programa.objects.create(
        url_name=url_name,
        app_label=programa.app_label,
        grupo_tela=programa.grupo_tela,
        nome=nome,
        nome_customizado=True,
        tipo_acao='outro',
        ativo=True,
        descoberta_automatica=False,
    )
    messages.success(request, f'✅ Ação "{nome}" criada.')
    return redirect('empresas:programa_detail', pk=pk)
