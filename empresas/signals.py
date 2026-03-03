@receiver(post_save, sender=Empresa)
def seed_tipos_produto_on_create(sender, instance, created, **kwargs):
    """Cria tipos de produto padrão quando uma Empresa é criada."""
    if not created:
        return

    try:
        from produtos.tipo_produto_seed import seed_tipos_produto_for_empresa
        criados, ignorados = seed_tipos_produto_for_empresa(instance)
        # Log silencioso
    except Exception as e:
        pass


# --- NOVO: Seed de categorias padrão ao criar empresa ---
@receiver(post_save, sender=Empresa)
def seed_categorias_on_create(sender, instance, created, **kwargs):
    """Cria categorias padrão quando uma Empresa é criada."""
    if not created:
        return
    try:
        from produtos.categoria_seed import seed_categorias_for_empresa
        criados, ignorados = seed_categorias_for_empresa(instance)
        # Log silencioso
    except Exception:
        pass

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Empresa, Role

# Reuse DEFAULT_ROLES from management command to keep a single source
try:
    from .management.commands.seed_roles import DEFAULT_ROLES
except Exception:
    DEFAULT_ROLES = [
        'Proprietário',
        'Almoxarife',
        'Operacional do Campo',
        'Financeiro',
        'Gerente',
        'Vendedor',
    ]


@receiver(post_save, sender=Empresa)
def create_default_roles(sender, instance, created, **kwargs):
    """Cria roles padrão quando uma Empresa é criada (idempotente)."""
    if not created:
        return

    for nome in DEFAULT_ROLES:
        Role.objects.get_or_create(empresa=instance, name=nome, defaults={'builtin': True})


@receiver(post_save, sender=Empresa)
def seed_ncms_on_create(sender, instance, created, **kwargs):
    """Seeds company NCMs when empresa is created and auto_seed_ncm is True."""
    if not created:
        return

    # Lazy import to avoid circular imports
    try:
        from cadastros.tasks import seed_ncms_for_company_async
        if getattr(instance, 'auto_seed_ncm', False):
            seed_ncms_for_company_async(instance.pk)
    except Exception:
        # Fail silently; admin can trigger via action
        pass


# --- NEW: Seed CFOPs for Empresa on creation ---
@receiver(post_save, sender=Empresa)
def seed_cfops_on_create(sender, instance, created, **kwargs):
    """Seeds company CFOPs when empresa is created."""
    if not created:
        return

    try:
        from cadastros.models import CFOP, EmpresaCFOP
        templates = CFOP.objects.filter(ativo=True).order_by('codigo')
        bulk = []
        for t in templates:
            bulk.append(EmpresaCFOP(empresa=instance, codigo=t.codigo, nome=t.nome, descricao=t.descricao, ativo=t.ativo, template=t))
        if bulk:
            EmpresaCFOP.objects.bulk_create(bulk)
    except Exception:
        # Fail silently; admin can trigger via action
        pass


@receiver(post_save, sender=Empresa)
def seed_pragas_on_create(sender, instance, created, **kwargs):
    """Cria pragas pré-definidas quando uma Empresa é criada."""
    if not created:
        return

    # Lazy import to avoid circular imports
    try:
        from cadastros.pragas_seed import seed_pragas_for_company
        criadas, ignoradas = seed_pragas_for_company(instance)
        # Log silencioso - pode adicionar logging se necessário
    except Exception as e:
        # Fail silently; não deve bloquear criação de empresa
        pass


@receiver(post_save, sender=Empresa)
def seed_defensivos_on_create(sender, instance, created, **kwargs):
    """Cria defensivos pré-definidos quando uma Empresa é criada."""
    if not created:
        return

    # Lazy import to avoid circular imports
    try:
        from produtos.defensivos_seed import seed_defensivos_for_empresa
        criados, ignorados = seed_defensivos_for_empresa(instance)
        # Log silencioso - pode adicionar logging se necessário
    except Exception as e:
        # Fail silently; não deve bloquear criação de empresa
        pass
