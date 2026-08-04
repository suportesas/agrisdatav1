import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from .forms import EmpresaLogoForm
from django.utils import timezone
from django.db.models import Count, Q
from django.db.models.deletion import ProtectedError
from django.core.paginator import Paginator
from core.pagination import paginate
from django.http import JsonResponse
from django.template.loader import render_to_string

from .models import APIKey, ConfiguracaoPlataforma, Empresa, Plano, Programa, Role, PermissionTemplate, RoleAudit
from .forms import APIKeyForm, ConfiguracaoPlataformaForm, EmpresaForm, EmpresaPreferenciasForm, PlanoForm

# Nomes amigáveis dos apps do ERP (usados na matriz de permissões)
APP_LABELS_PT = {
    'cadastros': 'Cadastros',
    'rh': 'Recursos Humanos',
    'operacoes_campo': 'Operações de Campo',
    'estufas': 'Estufas',
    'mip': 'MIP / Pragas',
    'emprestimos': 'Empréstimos',
    'frota': 'Frota',
    'produtos': 'Produtos',
    'estoque': 'Estoque',
    'compras': 'Compras',
    'financeiro': 'Financeiro',
    'plano_contas': 'Plano de Contas',
    'bancario': 'Bancário',
    'adiantamentos': 'Adiantamentos',
    'faturamento': 'Faturamento',
    'vendas': 'Vendas',
    'exportacao': 'Exportação',
    'embalagem': 'Embalagem',
    'patrimonio': 'Patrimônio',
    'energia': 'Energia',
    'empresas': 'Empresas',
    'usuarios': 'Usuários',
    'dashboard': 'Dashboard',
    'metricas': 'Métricas',
    'portal': 'Portal do Cliente',
    'auth': 'Autenticação (sistema)',
}


def is_owner(user):
    """Somente superusuário tem acesso"""
    return user.is_superuser


def _erro_formulario(form):
    """Monta mensagem detalhada com todos os erros do form, campo a campo.

    Necessário porque nem todo campo de empresa_form.html tem um bloco
    {% if form.X.errors %} dedicado (ex: telefone, uf) — sem isso, um erro
    nesses campos ficava completamente invisível para o usuário.
    """
    campos_com_erro = []
    for field_name, errors in form.errors.items():
        if field_name == '__all__':
            campo_label = 'Geral'
        else:
            campo_label = form.fields[field_name].label if field_name in form.fields else field_name
        campos_com_erro.append(f"{campo_label}: {', '.join(errors)}")
    return '❌ Corrija os erros no formulário:<br>' + '<br>'.join(f'• {erro}' for erro in campos_com_erro)


# ==================== VIEWS DE EMPRESAS ====================

@login_required
@user_passes_test(is_owner)
def painel_admin(request):
    """Painel administrativo para proprietário do sistema"""
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')
    seven_days_ago = timezone.now() - timezone.timedelta(days=7)

    empresas = Empresa.objects.all().annotate(
        total_usuarios=Count('usuarios'),
        logins_recentes=Count('usuarios', filter=Q(usuarios__last_login__gte=seven_days_ago))
    )



    if q:
        empresas = empresas.filter(Q(nome__icontains=q) | Q(cnpj__icontains=q))

    if status == "ativas":
        empresas = empresas.filter(ativa=True, bloqueada=False)
    elif status == "bloqueadas":
        empresas = empresas.filter(bloqueada=True)
    elif status == "expiradas":
        empresas = empresas.filter(data_expiracao__lt=timezone.now().date(), data_expiracao__isnull=False)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        html = render_to_string('empresas/_empresa_table.html', {'empresas': empresas}, request=request)
        return JsonResponse({'html': html})

    return render(request, 'empresas/painel_admin.html', {'empresas': empresas})


@login_required
def empresa_list(request):
    """Lista empresas"""
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', 'ativas').strip()
    empresas = Empresa.objects.select_related('plano', 'configuracao_fiscal').all()

    if not request.user.is_superuser:
        if request.user.empresa:
            empresas = empresas.filter(id=request.user.empresa.id)
        else:
            empresas = Empresa.objects.none()

    if q:
        empresas = empresas.filter(Q(nome__icontains=q) | Q(cnpj__icontains=q))

    if status == 'ativas':
        empresas = empresas.filter(ativa=True, bloqueada=False)
    elif status == 'inativas':
        empresas = empresas.filter(Q(ativa=False) | Q(bloqueada=True))
    # status == 'todas': sem filtro adicional

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        html = render_to_string('empresas/_empresa_table.html', {'empresas': empresas}, request=request)
        return JsonResponse({'html': html})

    page_obj, per_page, per_page_options = paginate(request, empresas.order_by('nome'))

    return render(request, 'empresas/empresa_list.html', {
        'empresas': page_obj,
        'status': status,
        'q': q,
        'per_page': per_page,
        'per_page_options': per_page_options,
    })


@login_required
@user_passes_test(is_owner)
def empresa_create(request):
    """Cria nova empresa"""
    if request.method == 'POST':
        form = EmpresaForm(request.POST, request.FILES)
        if form.is_valid():
            empresa = form.save()
            messages.success(request, f"✅ Empresa '{empresa.nome}' criada com sucesso.")
            return redirect('empresas:empresa_list')
        else:
            messages.error(request, _erro_formulario(form))
    else:
        form = EmpresaForm()
    
    return render(request, 'empresas/empresa_form.html', {
        'form': form,
        'action': 'Criar'
    })


@login_required
@user_passes_test(is_owner)
def empresa_update(request, pk):
    """Edita empresa"""
    empresa = get_object_or_404(Empresa, pk=pk)
    
    if request.method == 'POST':
        form = EmpresaForm(request.POST, request.FILES, instance=empresa)
        if form.is_valid():
            empresa = form.save()
            messages.success(request, f"✅ Empresa '{empresa.nome}' atualizada com sucesso.")
            return redirect('empresas:empresa_list')
        else:
            messages.error(request, _erro_formulario(form))
    else:
        form = EmpresaForm(instance=empresa)
    
    return render(request, 'empresas/empresa_form.html', {
        'form': form,
        'empresa': empresa,
        'action': 'Editar'
    })


@login_required
def empresa_preferencias(request):
    """Preferências operacionais da empresa do usuário logado."""
    empresa = request.user.empresa
    if empresa is None:
        messages.error(request, "Nenhuma empresa vinculada ao seu usuário.")
        return redirect('/')

    if request.method == 'POST':
        form = EmpresaPreferenciasForm(request.POST, instance=empresa)
        if form.is_valid():
            form.save()
            messages.success(request, "Preferências salvas com sucesso.")
            next_url = request.POST.get('next') or request.GET.get('next') or 'produtos:produto_list'
            return redirect(next_url)
    else:
        form = EmpresaPreferenciasForm(instance=empresa)

    return render(request, 'empresas/empresa_preferencias.html', {
        'form': form,
        'empresa': empresa,
    })


@login_required
@user_passes_test(is_owner)
def empresa_delete(request, pk):
    """Exclui empresa"""
    empresa = get_object_or_404(Empresa, pk=pk)
    
    # Verifica se tem usuários vinculados
    total_usuarios = empresa.usuarios.count()
    
    if total_usuarios > 0:
        messages.error(
            request,
            f"❌ Não é possível excluir! A empresa possui {total_usuarios} usuário(s) vinculado(s). "
            f"Remova os usuários primeiro."
        )
        return redirect('empresas:empresa_list')
    
    # Verifica vínculos que impedem exclusão (PROTECT)
    total_funcionarios = empresa.funcionarios.count()
    total_funcoes = empresa.funcoes_funcionarios.count()

    if total_funcionarios > 0 or total_funcoes > 0:
        detalhes = []
        if total_funcionarios > 0:
            detalhes.append(f"{total_funcionarios} funcionário(s)")
        if total_funcoes > 0:
            detalhes.append(f"{total_funcoes} função(ões)")
        detalhes_str = " e ".join(detalhes)
        messages.error(
            request,
            f"❌ Não é possível excluir! A empresa possui {detalhes_str} vinculados. "
            f"Remova esses registros primeiro."
        )
        return redirect('empresas:empresa_list')

    if request.method == 'POST':
        nome = empresa.nome
        try:
            empresa.delete()
            messages.success(request, f"🗑️ Empresa '{nome}' excluída com sucesso.")
        except ProtectedError:
            messages.error(
                request,
                "❌ Não é possível excluir! Existem registros vinculados que impedem a exclusão. "
                "Remova-os primeiro."
            )
        return redirect('empresas:empresa_list')
    
    return render(request, 'empresas/empresa_confirm_delete.html', {'empresa': empresa})


@login_required
def minha_empresa(request):
    """Exibe dados da empresa do usuário logado"""
    if not request.user.empresa:
        messages.warning(request, "Nenhuma empresa vinculada à sua conta.")
        return redirect('dashboard:index')
    
    empresa = request.user.empresa
    
    # Dados adicionais para exibir
    context = {
        'empresa': empresa,
        'total_usuarios': empresa.get_total_usuarios(),
        'dias_vencimento': empresa.get_dias_para_vencimento(),
        'proximo_vencimento': empresa.esta_proximo_vencimento(),
        'plano_consumo': empresa.plan_consumption_summary(),
    }
    
    return render(request, 'empresas/minha_empresa.html', context)


@login_required
def empresa_logo_update(request):
    """Atualiza apenas a logo da empresa do usuario logado"""
    if not request.user.empresa:
        messages.warning(request, 'Nenhuma empresa vinculada a sua conta.')
        return redirect('dashboard:index')

    empresa = request.user.empresa

    if request.method == 'POST':
        form = EmpresaLogoForm(request.POST, request.FILES, instance=empresa)
        if form.is_valid():
            form.save()
            messages.success(request, 'Logo atualizada com sucesso.')
            return redirect('empresas:minha_empresa')
        messages.error(request, 'Corrija os erros do formulario.')
    else:
        form = EmpresaLogoForm(instance=empresa)

    return render(request, 'empresas/empresa_logo_form.html', {
        'form': form,
        'empresa': empresa,
    })


@login_required
def role_list(request):
    """Lista funções (roles).

    - Empresa comum: suas próprias Funções + Funções Globais que ela ainda
      não personalizou (ver Role.origem_global).
    - Superuser sem empresa vinculada (SaaS Owner): gerencia as Funções
      Globais diretamente — essa é a tela de "Funções Globais" do painel SaaS.
    """
    modo_global = False

    if request.user.empresa:
        from .acesso import roles_visiveis_para_empresa
        roles = roles_visiveis_para_empresa(request.user.empresa).annotate(
            num_usuarios=Count('usuarios', distinct=True)
        ).order_by('builtin', 'name')
    elif request.user.is_superuser:
        modo_global = True
        roles = Role.objects.filter(empresa__isnull=True).annotate(
            num_usuarios=Count('usuarios', distinct=True)
        ).order_by('name')
    else:
        messages.warning(request, "Nenhuma empresa vinculada à sua conta.")
        return redirect('dashboard:index')

    # Estatísticas
    total_roles = roles.count()
    builtin_roles = roles.filter(builtin=True).count()
    custom_roles = roles.filter(builtin=False).count()

    context = {
        'roles': roles,
        'total_roles': total_roles,
        'builtin_roles': builtin_roles,
        'custom_roles': custom_roles,
        'modo_global': modo_global,
        'empresa_atual_id': request.user.empresa_id,
    }
    return render(request, 'empresas/roles_list.html', context)


@login_required
def role_create(request):
    """Cria nova função (Role) para a empresa do usuário, ou uma Função
    Global se quem cria é superuser sem empresa vinculada (painel SaaS)."""
    criar_global = request.user.is_superuser and not request.user.empresa
    if not criar_global and (not request.user.empresa or not request.user.is_admin_empresa()):
        messages.error(request, '❌ Você não tem permissão para criar funções.')
        return redirect('empresas:roles_list')

    from .forms import RoleForm

    if request.method == 'POST':
        form = RoleForm(request.POST)
        if form.is_valid():
            role = form.save(commit=False)
            role.empresa = None if criar_global else request.user.empresa
            role.builtin = False
            role.save()
            messages.success(request, f'✅ Função "{role.name}" criada com sucesso!')
            return redirect('empresas:roles_list')
    else:
        form = RoleForm()

    return render(request, 'empresas/role_form.html', {'form': form, 'action': 'Criar', 'criar_global': criar_global})


@login_required
def role_update(request, role_id):
    """Edita uma função existente (apenas para admin da empresa ou superuser)"""
    role = get_object_or_404(Role, pk=role_id)

    # Apenas superuser ou admin da mesma empresa podem editar
    if not request.user.is_superuser:
        if not request.user.empresa or role.empresa != request.user.empresa or not request.user.is_admin_empresa():
            messages.error(request, '❌ Você não tem permissão para editar esta função.')
            return redirect('empresas:roles_list')

    # Não permitir edição de funções built-in por usuários comuns
    if role.builtin and not request.user.is_superuser:
        messages.error(request, '⚠️ Funções padrão não podem ser editadas.')
        return redirect('empresas:roles_list')

    from .forms import RoleForm
    if request.method == 'POST':
        form = RoleForm(request.POST, instance=role)
        if form.is_valid():
            role = form.save()
            messages.success(request, f'✅ Função "{role.name}" atualizada com sucesso!')
            return redirect('empresas:roles_list')
    else:
        form = RoleForm(instance=role)

    return render(request, 'empresas/role_form.html', {'form': form, 'action': 'Editar', 'role': role})


@login_required
@require_POST
def role_fork(request, role_id):
    """Cria uma cópia própria da empresa a partir de uma Função Global
    ("Personalizar"). A cópia começa com os mesmos Programas da Global no
    momento do fork, e os usuários dessa empresa que já usavam a Global são
    reapontados pra cópia — dali em diante é uma Função comum, independente."""
    role = get_object_or_404(Role, pk=role_id, empresa__isnull=True)

    if not request.user.empresa or not request.user.is_admin_empresa():
        messages.error(request, '❌ Você não tem permissão pra personalizar Funções.')
        return redirect('empresas:roles_list')

    empresa = request.user.empresa
    if Role.objects.filter(empresa=empresa, name=role.name).exists():
        messages.error(
            request,
            f'❌ Você já tem uma Função chamada "{role.name}" — renomeie uma delas antes de personalizar.'
        )
        return redirect('empresas:roles_list')

    fork = role.criar_fork(empresa, actor=request.user)

    from usuarios.models import Usuario
    for usuario in Usuario.objects.filter(empresa=empresa, roles=role):
        usuario.roles.remove(role)
        usuario.roles.add(fork)

    messages.success(request, f'✅ "{role.name}" personalizada — agora você tem sua própria cópia.')
    return redirect('empresas:role_permissions', role_id=fork.id)


from django.views.decorators.csrf import ensure_csrf_cookie

@login_required
@ensure_csrf_cookie
def role_permissions(request, role_id):
    """GET: retorna permissões (codename, name, app, model, has)
       POST: atualiza permissões da role (espera JSON {'permissions': [codename,...]})
    """
    role = get_object_or_404(Role, pk=role_id)
    is_global = role.empresa_id is None

    def _pode_ver():
        if request.user.is_superuser:
            return True
        if not (hasattr(request.user, 'is_admin_empresa') and request.user.is_admin_empresa()):
            return False
        if is_global:
            return bool(request.user.empresa)  # qualquer admin de empresa pode VER uma Função Global
        return role.empresa_id == request.user.empresa_id

    def _pode_editar():
        if request.user.is_superuser:
            return True
        if is_global:
            return False  # Função Global só é editável pelo superuser — empresa usa "Personalizar"
        return (
            hasattr(request.user, 'is_admin_empresa') and request.user.is_admin_empresa()
            and role.empresa_id == request.user.empresa_id
        )

    if not _pode_ver():
        return JsonResponse({'error': 'Permissão negada'}, status=403)

    if request.method == 'GET':
        # If request is AJAX or client expects JSON, return JSON payload
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
            # Lista plana de Programas (uma linha + um checkbox por Programa).
            # 'detalhe'/'excluir' não aparecem aqui — são geridos na tela do
            # próprio Programa, com herança automática a partir da Listagem
            # (ver empresas/acesso.py).
            ACAO_LABEL = {'listagem': 'Listagem', 'criar': 'Criar', 'editar': 'Editar'}

            programas = list(
                Programa.objects.filter(ativo=True, tipo_acao__in=['listagem', 'criar', 'editar', 'outro'])
            )
            concedidos = set(role.programas.values_list('id', flat=True))
            nomes_tela = {
                (p.app_label, p.grupo_tela): p.nome
                for p in programas if p.tipo_acao == 'listagem'
            }
            ordem_acao = {'listagem': 0, 'criar': 1, 'editar': 2, 'outro': 3}

            apps = {}
            for p in programas:
                app = p.app_label
                app_nome = APP_LABELS_PT.get(app, app.replace('_', ' ').title())
                if app not in apps:
                    apps[app] = {'app_label': app, 'app_nome': app_nome, 'programas': []}

                if p.tipo_acao in ACAO_LABEL:
                    tela_nome = nomes_tela.get((p.app_label, p.grupo_tela), p.nome)
                    nome_exibicao = f'{tela_nome} — {ACAO_LABEL[p.tipo_acao]}'
                else:
                    nome_exibicao = p.nome

                apps[app]['programas'].append({
                    'id': p.id,
                    'nome': nome_exibicao,
                    'concedido': p.id in concedidos,
                    '_ordem': (p.grupo_tela, ordem_acao.get(p.tipo_acao, 9)),
                })

            # Ordena: apps do ERP primeiro (por APP_LABELS_PT order), system last
            erp_order = list(APP_LABELS_PT.keys())
            def sort_key(app_key):
                try:
                    return (0, erp_order.index(app_key))
                except ValueError:
                    return (1, 0)

            grupos = []
            for app_key in sorted(apps.keys(), key=sort_key):
                grupo = apps[app_key]
                itens = sorted(grupo['programas'], key=lambda x: x['_ordem'])
                for item in itens:
                    item.pop('_ordem')
                grupos.append({
                    'app_label': grupo['app_label'],
                    'app_nome': grupo['app_nome'],
                    'programas': itens,
                })

            return JsonResponse({'grupos': grupos, 'pode_editar': _pode_editar(), 'is_global': is_global})
        # Otherwise render an HTML page that will load the permissions via JS
        return render(request, 'empresas/role_permissions_page.html', {'role': role})

    if request.method == 'POST':
        if not _pode_editar():
            return JsonResponse({
                'error': 'Esta é uma Função Global — só o administrador do SaaS pode editá-la. '
                         'Use "Personalizar" pra criar sua própria cópia.'
            }, status=403)
        try:
            payload = json.loads(request.body.decode('utf-8'))
            programa_ids = payload.get('programa_ids', [])
        except Exception:
            return JsonResponse({'error': 'Payload inválido'}, status=400)

        role.set_programas(programa_ids, actor=request.user if request.user.is_authenticated else None)
        return JsonResponse({'ok': True, 'updated': len(programa_ids)})


@login_required
def save_permission_template(request, role_id):
    """Salva um template a partir das permissões atuais exibidas para a role"""
    role = get_object_or_404(Role, pk=role_id)
    if not request.user.is_superuser and role.empresa != request.user.empresa:
        return JsonResponse({'error': 'Permissão negada'}, status=403)

    try:
        payload = json.loads(request.body.decode('utf-8'))
        nome = payload.get('nome')
        dados = payload.get('dados')
    except Exception:
        return JsonResponse({'error': 'Payload inválido'}, status=400)

    if not nome or not isinstance(dados, dict):
        return JsonResponse({'error': 'Nome ou dados inválidos'}, status=400)

    tpl, created = PermissionTemplate.objects.get_or_create(
        empresa=role.empresa,
        nome=nome,
        defaults={'dados': dados, 'criado_por': request.user}
    )
    if not created:
        tpl.dados = dados
        tpl.criado_por = request.user
        tpl.save()

    return JsonResponse({'ok': True, 'template_id': tpl.id})


@login_required
def apply_template_to_role(request, role_id):
    """Aplica um template a uma role específica (substitui permissões)."""
    role = get_object_or_404(Role, pk=role_id)
    if not request.user.is_superuser and role.empresa != request.user.empresa:
        return JsonResponse({'error': 'Permissão negada'}, status=403)

    try:
        payload = json.loads(request.body.decode('utf-8'))
        template_id = payload.get('template_id')
    except Exception:
        return JsonResponse({'error': 'Payload inválido'}, status=400)

    tpl = get_object_or_404(PermissionTemplate, pk=template_id)
    if tpl.empresa != role.empresa:
        return JsonResponse({'error': 'Template não pertence à mesma empresa'}, status=400)

    # 'dados' tem o formato {"programa_ids": [1, 2, ...]}
    programa_ids = tpl.dados.get('programa_ids', [])
    role.set_programas(programa_ids, actor=request.user if request.user.is_authenticated else None)
    return JsonResponse({'ok': True, 'applied': len(programa_ids)})


@login_required
def apply_template_bulk(request):
    """Aplica um template a várias roles (bulk apply). Espera {'template_id': int, 'role_ids': [int,...]}"""
    try:
        payload = json.loads(request.body.decode('utf-8'))
        template_id = payload.get('template_id')
        role_ids = payload.get('role_ids', [])
    except Exception:
        return JsonResponse({'error': 'Payload inválido'}, status=400)

    tpl = get_object_or_404(PermissionTemplate, pk=template_id)

    # Valida roles e aplica
    applied = 0
    for rid in role_ids:
        r = Role.objects.filter(pk=rid).first()
        if not r:
            continue
        if not request.user.is_superuser and r.empresa != request.user.empresa:
            continue
        programa_ids = tpl.dados.get('programa_ids', [])
        r.set_programas(programa_ids, actor=request.user if request.user.is_authenticated else None)
        applied += 1

    return JsonResponse({'ok': True, 'roles_updated': applied})


@login_required
def permission_templates_list(request):
    """Lista templates de permissões para a empresa do usuário (ou todos para superuser)"""
    if request.user.is_superuser:
        templates = PermissionTemplate.objects.all()
    else:
        if not request.user.empresa:
            return JsonResponse({'templates': []})
        templates = PermissionTemplate.objects.filter(empresa=request.user.empresa)

    data = []
    for t in templates:
        data.append({'id': t.id, 'nome': t.nome, 'criado_por': t.criado_por.username if t.criado_por else None, 'data_criacao': t.data_criacao.isoformat()})
    return JsonResponse({'templates': data})


@login_required
def permission_template_detail(request, pk):
    tpl = get_object_or_404(PermissionTemplate, pk=pk)
    if not request.user.is_superuser and tpl.empresa != request.user.empresa:
        return JsonResponse({'error': 'Permissão negada'}, status=403)

    return JsonResponse({'id': tpl.id, 'nome': tpl.nome, 'dados': tpl.dados, 'criado_por': tpl.criado_por.username if tpl.criado_por else None, 'data_criacao': tpl.data_criacao.isoformat()})


@login_required
@require_POST
def role_clone(request, role_id):
    """Clona uma função copiando todas as suas permissões para um novo nome.

    Diferente de "Personalizar" (`role_fork`): o clone é uma Função nova e
    independente, com nome escolhido pelo usuário — não fica vinculada via
    `origem_global`, e a Global de origem continua disponível pra ser
    personalizada normalmente depois.
    """
    role = get_object_or_404(Role, pk=role_id)

    if role.empresa_id:
        empresa_destino = role.empresa
        if not request.user.is_superuser and (
            not request.user.empresa or role.empresa != request.user.empresa
        ):
            return JsonResponse({'error': 'Permissão negada'}, status=403)
    else:
        # Clonando uma Função Global: superuser sem empresa (painel SaaS) gera
        # outra Global; admin de empresa gera uma cópia independente da empresa dele.
        if request.user.is_superuser and not request.user.empresa:
            empresa_destino = None
        elif request.user.empresa and request.user.is_admin_empresa():
            empresa_destino = request.user.empresa
        else:
            return JsonResponse({'error': 'Permissão negada'}, status=403)

    try:
        payload = json.loads(request.body.decode('utf-8'))
        new_name = (payload.get('name') or '').strip()
        new_desc = (payload.get('description') or '').strip()
    except Exception:
        return JsonResponse({'error': 'Payload inválido'}, status=400)

    if not new_name:
        return JsonResponse({'error': 'Informe o nome para a nova função.'}, status=400)

    if Role.objects.filter(empresa=empresa_destino, name=new_name).exists():
        return JsonResponse({'error': f'Já existe uma função com o nome "{new_name}".'}, status=400)

    new_role = Role.objects.create(
        empresa=empresa_destino,
        name=new_name,
        description=new_desc or f'Clonada de: {role.name}',
        builtin=False,
    )
    programa_ids = list(role.programas.values_list('id', flat=True))
    new_role.set_programas(programa_ids, actor=request.user)

    return JsonResponse({'ok': True, 'role_id': new_role.pk, 'role_name': new_role.name})


# ==================== CONFIGURAÇÃO DA PLATAFORMA (Softhouse) ====================

@login_required
@user_passes_test(is_owner)
def configuracao_softhouse(request):
    """Token mestre de revenda (softhouse) da IntegraNotas — usado para criar
    automaticamente o emitente de cada empresa na Configuração Fiscal."""
    config, _ = ConfiguracaoPlataforma.objects.get_or_create(pk=1)

    if request.method == 'POST':
        form = ConfiguracaoPlataformaForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, 'Configuração da plataforma salva com sucesso.')
            return redirect('empresas:configuracao_softhouse')
    else:
        form = ConfiguracaoPlataformaForm(instance=config)

    return render(request, 'empresas/configuracao_softhouse.html', {
        'form': form,
        'token_configurado': bool(config.get_token()),
    })


@login_required
@user_passes_test(is_owner)
def empresa_emitente_softhouse(request, pk):
    """Tela de configuração/criação do emitente de uma empresa na IntegraNotas.
    Ação exclusiva do admin da plataforma — quem tem a credencial da
    IntegraNotas é a softhouse, não a empresa cliente. Antes de criar, o
    admin escolhe o ambiente e quais tipos de documento (NF-e, CT-e, etc.)
    o emitente vai usar."""
    from faturamento.models import ConfiguracaoFiscal
    from faturamento.services.integranotas import (
        IntegranNotasClient, IntegranNotasError, build_emitente_softhouse_payload,
        SOFTHOUSE_DOCUMENTOS_CHOICES, SOFTHOUSE_DOCUMENTOS_PADRAO,
    )

    empresa = get_object_or_404(Empresa, pk=pk)
    config, _ = ConfiguracaoFiscal.objects.get_or_create(empresa=empresa)
    token_configurado = bool(config.get_token())

    documentos_selecionados = SOFTHOUSE_DOCUMENTOS_PADRAO

    if request.method == 'POST':
        if token_configurado:
            messages.info(request, 'Esta empresa já tem um emitente configurado na IntegraNotas.')
            return redirect('empresas:empresa_emitente_softhouse', pk=empresa.pk)

        ambiente = request.POST.get('ambiente', '2').strip()
        if ambiente not in ('1', '2'):
            ambiente = '2'
        documentos_marcados = set(request.POST.getlist('documentos'))
        documentos_selecionados = documentos_marcados
        documentos_payload = {chave: (chave in documentos_marcados) for chave, _ in SOFTHOUSE_DOCUMENTOS_CHOICES}

        if ambiente != config.ambiente_nfe:
            config.ambiente_nfe = ambiente
            config.save(update_fields=['ambiente_nfe'])

        plataforma = ConfiguracaoPlataforma.objects.first()
        token_softhouse = plataforma.get_token() if plataforma else ''
        if not token_softhouse:
            messages.error(request, 'Token da softhouse não configurado. Configure em "IntegraNotas (Softhouse)".')
        else:
            client = IntegranNotasClient(token=token_softhouse, ambiente=config.ambiente_nfe)
            try:
                payload = build_emitente_softhouse_payload(empresa, config, documentos=documentos_payload)
            except IntegranNotasError as exc:
                messages.error(request, f'Erro ao criar emitente de "{empresa.nome}" [{exc.codigo}]: {exc}')
            else:
                try:
                    data = client.criar_emitente_softhouse(payload)
                    novo_token = data.get('token', '')
                    if novo_token:
                        config.set_token(novo_token)
                        config.save()
                        messages.success(request, f'Emitente de "{empresa.nome}" criado na IntegraNotas com sucesso!')
                        return redirect('empresas:empresa_emitente_softhouse', pk=empresa.pk)
                    else:
                        messages.warning(request, f'Emitente de "{empresa.nome}" criado, mas a resposta não trouxe um token.')
                except IntegranNotasError as exc:
                    # O emitente pode já existir na IntegraNotas (criado a partir de outro
                    # ambiente/banco) — nesse caso a criação falha mas dá pra recuperar o
                    # token buscando pelo CNPJ/CPF em vez de mostrar só o erro.
                    novo_token = ''
                    try:
                        data_existente = client.buscar_emitente_softhouse(empresa.cnpj or '')
                        novo_token = (data_existente.get('emitente') or {}).get('token', '')
                    except IntegranNotasError:
                        pass
                    if novo_token:
                        config.set_token(novo_token)
                        config.save()
                        messages.success(
                            request,
                            f'Emitente de "{empresa.nome}" já existia na IntegraNotas — token recuperado com sucesso!',
                        )
                        return redirect('empresas:empresa_emitente_softhouse', pk=empresa.pk)
                    messages.error(request, f'Erro ao criar emitente de "{empresa.nome}" [{exc.codigo}]: {exc}')
                except Exception as exc:
                    messages.error(request, f'Erro de comunicação com a IntegraNotas: {exc}')

    campos_faltando_msg = ''
    if not token_configurado:
        try:
            build_emitente_softhouse_payload(empresa, config, documentos={})
        except IntegranNotasError as exc:
            campos_faltando_msg = str(exc)

    return render(request, 'empresas/empresa_emitente_softhouse.html', {
        'empresa': empresa,
        'config': config,
        'token_configurado': token_configurado,
        'documentos_choices': SOFTHOUSE_DOCUMENTOS_CHOICES,
        'documentos_selecionados': documentos_selecionados,
        'campos_faltando_msg': campos_faltando_msg,
    })


@login_required
@user_passes_test(is_owner)
@require_POST
def empresa_testar_conexao_integranotas(request, pk):
    """AJAX: testa a conexão/token IntegraNotas de uma empresa específica."""
    from faturamento.models import ConfiguracaoFiscal
    from faturamento.services.integranotas import IntegranNotasClient

    empresa = get_object_or_404(Empresa, pk=pk)
    config = ConfiguracaoFiscal.objects.filter(empresa=empresa).first()
    if not config or not config.get_token():
        return JsonResponse({'sucesso': False, 'mensagem': 'Nenhum token configurado para esta empresa.'})

    client = IntegranNotasClient(token=config.get_token(), ambiente=config.ambiente_nfe)
    result = client.test_connection()
    result['ambiente_label'] = 'Produção' if config.ambiente_nfe == '1' else 'Homologação'
    return JsonResponse(result)


# ==================== VIEWS DE PLANOS ====================

@login_required
@user_passes_test(is_owner)
def plano_list(request):
    """Lista todos os planos"""
    planos = Plano.objects.filter(ativo=True).order_by('ordem')

    # Adiciona informação de quantas empresas usam cada plano
    for plano in planos:
        plano.total_empresas_ativas = plano.empresas.filter(ativa=True).count()

    page_obj, per_page, per_page_options = paginate(request, planos)

    return render(request, 'empresas/plano_list.html', {
        'planos': page_obj,
        'per_page': per_page,
        'per_page_options': per_page_options,
    })


@login_required
@user_passes_test(is_owner)
def plano_create(request):
    """Cria novo plano"""
    if request.method == 'POST':
        form = PlanoForm(request.POST)
        if form.is_valid():
            plano = form.save()
            messages.success(request, f"✅ Plano '{plano.nome}' criado com sucesso!")
            return redirect('empresas:plano_list')
        else:
            messages.error(request, "❌ Corrija os erros no formulário.")
    else:
        form = PlanoForm()
    
    return render(request, 'empresas/plano_form.html', {
        'form': form,
        'action': 'Criar'
    })


@login_required
@user_passes_test(is_owner)
def plano_update(request, pk):
    """Edita plano existente"""
    plano = get_object_or_404(Plano, pk=pk)
    
    if request.method == 'POST':
        form = PlanoForm(request.POST, instance=plano)
        if form.is_valid():
            plano = form.save()
            
            # ✅ CORRIGIDO: Atualizar empresas que usam este plano (usando objeto, não código)
            empresas = Empresa.objects.filter(plano=plano)  # ← CORREÇÃO AQUI
            
            if empresas.exists():
                for empresa in empresas:
                    empresa.aplicar_limites_plano()
                    empresa.save()
                
                messages.success(
                    request,
                    f"✅ Plano '{plano.nome}' atualizado! {empresas.count()} empresa(s) afetada(s)."
                )
            else:
                messages.success(request, f"✅ Plano '{plano.nome}' atualizado com sucesso!")
            
            return redirect('empresas:plano_list')
        else:
            messages.error(request, "❌ Corrija os erros no formulário.")
    else:
        form = PlanoForm(instance=plano)
    
    # ✅ CORRIGIDO: Conta empresas usando objeto, não código
    total_empresas = Empresa.objects.filter(plano=plano).count()  # ← CORREÇÃO AQUI
    
    return render(request, 'empresas/plano_form.html', {
        'form': form,
        'plano': plano,
        'total_empresas': total_empresas,
        'action': 'Editar'
    })


@login_required
@user_passes_test(is_owner)
def plano_delete(request, pk):
    """Deleta plano (se não houver empresas vinculadas)"""
    plano = get_object_or_404(Plano, pk=pk)
    
    # ✅ CORRIGIDO: Verifica empresas usando objeto, não código
    empresas_vinculadas = Empresa.objects.filter(plano=plano).count()  # ← CORREÇÃO AQUI
    
    if empresas_vinculadas > 0:
        messages.error(
            request,
            f"❌ Não é possível excluir! {empresas_vinculadas} empresa(s) está(ão) usando este plano. "
            f"Altere o plano dessas empresas antes de excluir."
        )
        return redirect('empresas:plano_list')
    
    if request.method == 'POST':
        nome = plano.nome
        plano.delete()
        messages.success(request, f"🗑️ Plano '{nome}' excluído com sucesso!")
        return redirect('empresas:plano_list')
    
    return render(request, 'empresas/plano_confirm_delete.html', {'plano': plano})


@login_required
@user_passes_test(is_owner)
def inicializar_planos_padrao(request):
    """Cria os 3 planos padrão do sistema"""
    planos_padrao = [
        {
            'codigo': 'PEQUENO',
            'nome': 'Pequeno Produtor',
            'icone': '🌱',
            'valor_mensal': 99.00,
            'desconto_anual': 16.67,
            'limite_fazendas': 2,
            'limite_usuarios': 3,
            'limite_talhoes': 10,
            'limite_produtos': 50,
            'acesso_relatorios_avancados': False,
            'acesso_api': False,
            'acesso_app_mobile': False,
            'acesso_suporte_prioritario': False,
            'ordem': 1,
        },
        {
            'codigo': 'MEDIO',
            'nome': 'Médio Produtor',
            'icone': '🌾',
            'valor_mensal': 249.00,
            'desconto_anual': 16.67,
            'limite_fazendas': 5,
            'limite_usuarios': 10,
            'limite_talhoes': 30,
            'limite_produtos': 200,
            'acesso_relatorios_avancados': True,
            'acesso_api': False,
            'acesso_app_mobile': True,
            'acesso_suporte_prioritario': True,
            'ordem': 2,
        },
        {
            'codigo': 'GRANDE',
            'nome': 'Grande Produtor',
            'icone': '🚜',
            'valor_mensal': 499.00,
            'desconto_anual': 16.67,
            'limite_fazendas': 999,
            'limite_usuarios': 999,
            'limite_talhoes': 999,
            'limite_produtos': 999,
            'acesso_relatorios_avancados': True,
            'acesso_api': True,
            'acesso_app_mobile': True,
            'acesso_suporte_prioritario': True,
            'ordem': 3,
        },
    ]
    
    criados = 0
    atualizados = 0
    
    for dados in planos_padrao:
        plano, created = Plano.objects.get_or_create(
            codigo=dados['codigo'],
            defaults=dados
        )
        
        if created:
            criados += 1
        else:
            # Atualiza plano existente
            for key, value in dados.items():
                if key != 'codigo':  # Não atualiza o código
                    setattr(plano, key, value)
            plano.save()
            atualizados += 1
    
    if criados > 0:
        messages.success(request, f"✅ {criados} plano(s) padrão criado(s)!")
    if atualizados > 0:
        messages.info(request, f"ℹ️ {atualizados} plano(s) atualizado(s).")
    if criados == 0 and atualizados == 0:
        messages.info(request, "ℹ️ Planos padrão já existem e estão atualizados.")
    
    return redirect('empresas:plano_list')


@login_required
def api_plano_dados(request, plano_id):
    """API para retornar dados do plano (AJAX)"""
    try:
        plano = Plano.objects.get(id=plano_id)
        dados = {
            'id': plano.id,
            'codigo': plano.codigo,
            'nome': plano.nome,
            'valor_mensal': str(plano.valor_mensal),
            'valor_anual': str(plano.valor_anual) if plano.valor_anual else None,
            'desconto_anual': str(plano.desconto_anual),
            'limite_fazendas': plano.limite_fazendas,
            'limite_usuarios': plano.limite_usuarios,
            'limite_talhoes': plano.limite_talhoes,
            'limite_produtos': plano.limite_produtos,
            'acesso_relatorios_avancados': plano.acesso_relatorios_avancados,
            'acesso_api': plano.acesso_api,
            'acesso_app_mobile': plano.acesso_app_mobile,
            'acesso_suporte_prioritario': plano.acesso_suporte_prioritario,
        }
        return JsonResponse(dados)
    except Plano.DoesNotExist:
        return JsonResponse({'erro': 'Plano não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'erro': str(e)}, status=500)


# ─────────────────────────── API Keys ────────────────────────────────────────

@login_required
def api_key_list(request):
    empresa = request.user.empresa
    keys = APIKey.objects.filter(empresa=empresa).order_by('-criado_em')
    return render(request, 'empresas/api_key_list.html', {'keys': keys})


@login_required
def api_key_create(request):
    empresa = request.user.empresa
    raw_key = None
    if request.method == 'POST':
        form = APIKeyForm(request.POST)
        if form.is_valid():
            instance, raw_key = APIKey.gerar(
                empresa=empresa,
                nome=form.cleaned_data['nome'],
                criado_por=request.user,
            )
            messages.success(request, 'Chave de API criada com sucesso. Copie-a agora — ela não será exibida novamente.')
            form = APIKeyForm()
    else:
        form = APIKeyForm()
    return render(request, 'empresas/api_key_form.html', {'form': form, 'raw_key': raw_key})


@login_required
@require_POST
def api_key_revoke(request, pk):
    empresa = request.user.empresa
    api_key = get_object_or_404(APIKey, pk=pk, empresa=empresa)
    api_key.ativo = False
    api_key.save(update_fields=['ativo'])
    messages.success(request, f'Chave "{api_key.nome}" revogada.')
    return redirect('empresas:api_key_list')