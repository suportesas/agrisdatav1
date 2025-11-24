from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from django.db.models import Count, Q
from django.http import JsonResponse
from django.template.loader import render_to_string

from .models import Empresa, Plano
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
    empresas = Empresa.objects.select_related('plano').all()

    if not request.user.is_superuser:
        if request.user.empresa:
            empresas = empresas.filter(id=request.user.empresa.id)
        else:
            empresas = Empresa.objects.none()

    if q:
        empresas = empresas.filter(Q(nome__icontains=q) | Q(cnpj__icontains=q))

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        html = render_to_string('empresas/_empresa_table.html', {'empresas': empresas}, request=request)
        return JsonResponse({'html': html})

    return render(request, 'empresas/empresa_list.html', {'empresas': empresas})


@login_required
@user_passes_test(is_owner)
def empresa_create(request):
    """Cria nova empresa"""
    if request.method == 'POST':
        form = EmpresaForm(request.POST)
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
        form = EmpresaForm(request.POST, instance=empresa)
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
    
    if request.method == 'POST':
        nome = empresa.nome
        empresa.delete()
        messages.success(request, f"🗑️ Empresa '{nome}' excluída com sucesso.")
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
    }
    
    return render(request, 'empresas/minha_empresa.html', context)


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