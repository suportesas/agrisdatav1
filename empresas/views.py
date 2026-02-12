import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import EmpresaLogoForm
from django.utils import timezone
from django.db.models import Count, Q
from django.db.models.deletion import ProtectedError
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.contrib.auth.models import Permission

from .models import Empresa, Plano, Role, PermissionTemplate
from .forms import EmpresaForm, PlanoForm


def is_owner(user):
    """Somente superusuário tem acesso"""
    return user.is_superuser


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
    empresas = Empresa.objects.select_related('plano').all()

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

    return render(request, 'empresas/empresa_list.html', {
        'empresas': empresas,
        'status': status,
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
            messages.error(request, "❌ Corrija os erros no formulário.")
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
            messages.error(request, "❌ Corrija os erros no formulário.")
    else:
        form = EmpresaForm(instance=empresa)
    
    return render(request, 'empresas/empresa_form.html', {
        'form': form,
        'empresa': empresa,
        'action': 'Editar'
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
    """Lista funções (roles) da empresa do usuário logado"""
    if not request.user.empresa:
        messages.warning(request, "Nenhuma empresa vinculada à sua conta.")
        return redirect('dashboard:index')

    roles = Role.objects.filter(empresa=request.user.empresa)
    
    # Estatísticas
    total_roles = roles.count()
    builtin_roles = roles.filter(builtin=True).count()
    custom_roles = roles.filter(builtin=False).count()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        html = render_to_string('empresas/_roles_table.html', {'roles': roles}, request=request)
        return JsonResponse({'html': html})

    context = {
        'roles': roles,
        'total_roles': total_roles,
        'builtin_roles': builtin_roles,
        'custom_roles': custom_roles,
    }
    return render(request, 'empresas/roles_list.html', context)


@login_required
def role_create(request):
    """Cria nova função (Role) para a empresa do usuário"""
    if not request.user.empresa or not request.user.is_admin_empresa():
        messages.error(request, '❌ Você não tem permissão para criar funções.')
        return redirect('empresas:roles_list')

    from .forms import RoleForm

    if request.method == 'POST':
        form = RoleForm(request.POST)
        if form.is_valid():
            role = form.save(commit=False)
            role.empresa = request.user.empresa
            role.builtin = False
            role.save()
            messages.success(request, f'✅ Função "{role.name}" criada com sucesso!')
            return redirect('empresas:roles_list')
    else:
        form = RoleForm()

    return render(request, 'empresas/role_form.html', {'form': form, 'action': 'Criar'})


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


from django.views.decorators.csrf import ensure_csrf_cookie

@login_required
@ensure_csrf_cookie
def role_permissions(request, role_id):
    """GET: retorna permissões (codename, name, app, model, has)
       POST: atualiza permissões da role (espera JSON {'permissions': [codename,...]})
    """
    role = get_object_or_404(Role, pk=role_id)

    # Verifica permissão: somente admin da empresa ou superuser
    if not request.user.is_superuser:
        if not request.user.empresa or role.empresa != request.user.empresa or not request.user.is_admin_empresa():
            return JsonResponse({'error': 'Permissão negada'}, status=403)

    if request.method == 'GET':
        # If request is AJAX or client expects JSON, return JSON payload
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
            # Lista todas as permissões do sistema agrupadas por app/model
            perms = Permission.objects.all().select_related('content_type')
            role_perms = set(p.codename for p in role.get_permissions())

            grouped = {}
            # Optional mapping to show friendly module names
            APP_LABELS = {
                'cadastros': 'Cadastros',
                'empresas': 'Empresa',
                'usuarios': 'Usuários',
                'auth': 'Autenticação',
                'produtos': 'Produtos',
                'estoque': 'Estoque',
                'compras': 'Compras',
            }

            for p in perms:
                app = p.content_type.app_label
                model = p.content_type.model
                key = f"{app}:{model}"
                if key not in grouped:
                    grouped[key] = {
                        'app_label': app,
                        'model': model,
                        'display': APP_LABELS.get(app, app.title()) + ' • ' + model.title(),
                        'perms': {'add': False, 'change': False, 'delete': False, 'view': False}
                    }
                if p.codename.startswith('add_'):
                    grouped[key]['perms']['add'] = p.codename in role_perms
                elif p.codename.startswith('change_'):
                    grouped[key]['perms']['change'] = p.codename in role_perms
                elif p.codename.startswith('delete_'):
                    grouped[key]['perms']['delete'] = p.codename in role_perms
                elif p.codename.startswith('view_'):
                    grouped[key]['perms']['view'] = p.codename in role_perms

            # Convert grouped to a sorted list for deterministic output
            items = []
            for k in sorted(grouped.keys()):
                item = grouped[k]
                item['key'] = k
                items.append(item)

            return JsonResponse({'permissions': items})
        # Otherwise render an HTML page that will load the permissions via JS
        return render(request, 'empresas/role_permissions_page.html', {'role': role})

    if request.method == 'POST':
        try:
            payload = json.loads(request.body.decode('utf-8'))
            codenames = payload.get('permissions', [])
        except Exception:
            return JsonResponse({'error': 'Payload inválido'}, status=400)

        role.set_permissions(codenames, actor=request.user if request.user.is_authenticated else None)
        return JsonResponse({'ok': True, 'updated': len(codenames)})


@login_required
def save_permission_template(request, role_id):
    """Salva um template a partir das permissões atuais exibidas para a role"""
    role = get_object_or_404(Role, pk=role_id)
    if not request.user.is_superuser and role.empresa != request.user.empresa:
        return JsonResponse({'error': 'Permissão negada'}, status=403)

    # Debugging aid: log CSRF presence for E2E diagnostics
    try:
        print('DEBUG save_permission_template: csrftoken cookie=', request.COOKIES.get('csrftoken'))
        print('DEBUG save_permission_template: X-CSRFToken header=', request.headers.get('X-CSRFToken'))
        # Also log body for debugging
        try:
            print('DEBUG save_permission_template: body=', request.body[:1000])
        except Exception:
            pass
    except Exception:
        pass

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

    try:
        print('DEBUG save_permission_template: created=', created, 'tpl_id=', tpl.id, 'tpl_nome=', tpl.nome)
    except Exception:
        pass

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

    # 'dados' tem o formato {"model": {"add": true, ...}}
    codenames = []
    for model, perms in tpl.dados.items():
        if perms.get('add'):
            codenames.append('add_' + model)
        if perms.get('change'):
            codenames.append('change_' + model)
        if perms.get('delete'):
            codenames.append('delete_' + model)
        if perms.get('view'):
            codenames.append('view_' + model)

    role.set_permissions(codenames, actor=request.user if request.user.is_authenticated else None)
    return JsonResponse({'ok': True, 'applied': len(codenames)})


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
        # Constrói codename list
        codenames = []
        for model, perms in tpl.dados.items():
            if perms.get('add'):
                codenames.append('add_' + model)
            if perms.get('change'):
                codenames.append('change_' + model)
            if perms.get('delete'):
                codenames.append('delete_' + model)
            if perms.get('view'):
                codenames.append('view_' + model)
        r.set_permissions(codenames, actor=request.user if request.user.is_authenticated else None)
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
# ==================== VIEWS DE PLANOS ====================

@login_required
@user_passes_test(is_owner)
def plano_list(request):
    """Lista todos os planos"""
    planos = Plano.objects.filter(ativo=True).order_by('ordem')
    
    # Adiciona informação de quantas empresas usam cada plano
    for plano in planos:
        plano.total_empresas_ativas = plano.empresas.filter(ativa=True).count()
    
    return render(request, 'empresas/plano_list.html', {'planos': planos})


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