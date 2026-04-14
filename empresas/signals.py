from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.core.management import call_command
from django.utils import timezone
import os
import logging

from .models import Empresa, Role
from core.storage import storage_helper

logger = logging.getLogger(__name__)

# Reuse DEFAULT_ROLES from management command to keep a single source
try:
    from .management.commands.seed_roles import DEFAULT_ROLES
except Exception:
    DEFAULT_ROLES = [
        'Proprietario',
        'Almoxarife',
        'Operacional do Campo',
        'Financeiro',
        'Gerente',
        'Vendedor',
    ]


@receiver(post_save, sender=Empresa)
def create_default_roles(sender, instance, created, **kwargs):
    """Cria roles padrao quando uma Empresa e criada (idempotente)."""
    if kwargs.get('raw'):
        return
    if not created:
        return

    for nome in DEFAULT_ROLES:
        Role.objects.get_or_create(empresa=instance, name=nome, defaults={'builtin': True})


@receiver(post_save, sender=Empresa)
def seed_ncms_on_create(sender, instance, created, **kwargs):
    """Seed de NCMs da empresa ao criar empresa."""
    if kwargs.get('raw'):
        return
    if not created:
        return
    if getattr(instance, 'is_interna_saas', False):
        return

    try:
        from cadastros.models import NCM
        # Síncrono para garantir que os NCMs já existam após o cadastro da empresa.
        from cadastros.tasks import seed_ncms_for_company

        # Se templates globais estiverem vazios, tenta bootstrap via CSV local.
        if NCM.objects.filter(ativo=True).count() == 0:
            csv_path = os.path.join(settings.BASE_DIR, 'NCM_import.csv')
            if os.path.exists(csv_path):
                call_command('import_ncm', path=csv_path)

        if getattr(instance, 'auto_seed_ncm', False):
            seed_ncms_for_company(instance.pk)
    except Exception:
        # Nao deve bloquear criacao de empresa
        logger.exception('Falha ao seedar NCMs para empresa %s', instance.pk)


@receiver(post_save, sender=Empresa)
def seed_cfops_on_create(sender, instance, created, **kwargs):
    """Seed de CFOPs da empresa ao criar empresa."""
    if kwargs.get('raw'):
        return
    if not created:
        return
    if getattr(instance, 'is_interna_saas', False):
        return

    try:
        from cadastros.models import CFOP, EmpresaCFOP

        # Se templates globais estiverem vazios, tenta bootstrap via CSV local.
        if CFOP.objects.filter(ativo=True).count() == 0:
            csv_path = os.path.join(settings.BASE_DIR, 'CFOP_import.csv')
            if os.path.exists(csv_path):
                call_command('importa_cfop', file=csv_path)

        templates = CFOP.objects.filter(ativo=True).order_by('codigo')
        bulk = []
        existing_codes = set(EmpresaCFOP.objects.filter(empresa=instance).values_list('codigo', flat=True))

        for t in templates:
            if t.codigo in existing_codes:
                continue
            bulk.append(
                EmpresaCFOP(
                    empresa=instance,
                    codigo=t.codigo,
                    nome=t.nome,
                    descricao=t.descricao,
                    ativo=t.ativo,
                    template=t,
                )
            )

        if bulk:
            EmpresaCFOP.objects.bulk_create(bulk)
    except Exception:
        # Nao deve bloquear criacao de empresa
        logger.exception('Falha ao seedar CFOPs para empresa %s', instance.pk)


@receiver(post_save, sender=Empresa)
def seed_pragas_on_create(sender, instance, created, **kwargs):
    """Cria pragas pre-definidas quando uma Empresa e criada."""
    if kwargs.get('raw'):
        return
    if not created:
        return
    if getattr(instance, 'is_interna_saas', False):
        return

    try:
        from cadastros.pragas_seed import seed_pragas_for_company
        seed_pragas_for_company(instance)
    except Exception:
        # Nao deve bloquear criacao de empresa
        pass


@receiver(post_save, sender=Empresa)
def seed_defensivos_on_create(sender, instance, created, **kwargs):
    """Cria defensivos pre-definidos quando uma Empresa e criada."""
    if kwargs.get('raw'):
        return
    if not created:
        return
    if getattr(instance, 'is_interna_saas', False):
        return

    try:
        from produtos.defensivos_seed import seed_defensivos_for_empresa
        seed_defensivos_for_empresa(instance)
    except Exception:
        # Nao deve bloquear criacao de empresa
        pass


@receiver(post_save, sender=Empresa)
def seed_categorias_on_create(sender, instance, created, **kwargs):
    """Cria categorias padrao quando uma Empresa e criada."""
    if kwargs.get('raw'):
        return
    if not created:
        return
    if getattr(instance, 'is_interna_saas', False):
        return

    try:
        from produtos.categoria_seed import seed_categorias_for_empresa
        seed_categorias_for_empresa(instance)
    except Exception:
        # Nao deve bloquear criacao de empresa
        pass


@receiver(post_save, sender=Empresa)
def seed_tipos_produto_on_create(sender, instance, created, **kwargs):
    """Cria tipos de produto padrao quando uma Empresa e criada."""
    if kwargs.get('raw'):
        return
    if not created:
        return
    if getattr(instance, 'is_interna_saas', False):
        return

    try:
        from produtos.tipo_produto_seed import seed_tipos_produto_for_empresa
        seed_tipos_produto_for_empresa(instance)
    except Exception:
        # Nao deve bloquear criacao de empresa
        pass


@receiver(post_save, sender=Empresa)
def seed_tipos_exame_aso_on_create(sender, instance, created, **kwargs):
    """Cria tipos de exame ASO padrão quando uma Empresa é criada."""
    if kwargs.get('raw'):
        return
    if not created:
        return
    if getattr(instance, 'is_interna_saas', False):
        return

    try:
        from cadastros.models import TipoExameASO

        exames_padrao = [
            ('AUDIOMETRIA', 'Audiometria', 10),
            ('COLINESTERASE', 'Colinesterase', 20),
            ('ESPIROMETRIA', 'Espirometria', 30),
            ('ACUIDADE_VISUAL', 'Acuidade Visual', 40),
            ('HEMOGRAMA', 'Hemograma', 50),
            ('ECG', 'Eletrocardiograma (ECG)', 60),
            ('RX_TORAX', 'Raio-X de Tórax', 70),
            ('GLICEMIA', 'Glicemia', 80),
            ('URINA_TIPO_1', 'Urina Tipo I', 90),
        ]

        for codigo, nome, ordem in exames_padrao:
            TipoExameASO.objects.get_or_create(
                empresa=instance,
                codigo=codigo,
                defaults={
                    'nome': nome,
                    'ativo': True,
                    'ordem': ordem,
                    'eh_padrao_sistema': True,
                }
            )
    except Exception:
        # Nao deve bloquear criacao de empresa
        logger.exception('Falha ao seedar tipos de exame ASO para empresa %s', instance.pk)


@receiver(post_save, sender=Empresa)
def seed_categorias_risco_ambiental_on_create(sender, instance, created, **kwargs):
    """Cria categorias padrão de risco ambiental quando uma empresa é criada."""
    if kwargs.get('raw'):
        return
    if not created:
        return
    if getattr(instance, 'is_interna_saas', False):
        return

    try:
        from cadastros.models import CategoriaRiscoAmbiental
        CategoriaRiscoAmbiental.criar_categorias_padrao_empresa(instance)
    except Exception:
        # Nao deve bloquear criacao de empresa
        logger.exception('Falha ao seedar categorias de risco ambiental para empresa %s', instance.pk)


@receiver(post_save, sender=Empresa)
def upload_empresa_logo(sender, instance, created, **kwargs):
    """
    Faz upload da logo para Supabase Storage quando salvar empresa
    Organiza em: empresas-logos/empresa_ID/YYYY/MM/filename.ext
    """
    if getattr(settings, 'SUPABASE_STORAGE_USE_AS_DEFAULT', False):
        return
    
    if instance.logo and hasattr(instance.logo, 'file'):
        try:
            # Gerar path organizado
            now = timezone.now()
            file_name = os.path.basename(instance.logo.name)
            file_path = f"empresa{instance.id}/{now.year}/{now.month:02d}/{file_name}"
            
            # Upload para Supabase
            url = storage_helper.upload_file(
                instance.logo.file,
                'empresas-logos',
                file_path
            )
            
            if url:
                logger.info(f"Logo de '{instance.nome}' enviada para Supabase Storage")
        except Exception as e:
            logger.error(f"Erro ao fazer upload de logo para '{instance.nome}': {e}")
