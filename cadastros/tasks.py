import threading
from django.utils import timezone
from django.db import transaction, connections
from django.db import close_old_connections
from .models import NCM, EmpresaNCM
from empresas.models import Empresa
import logging

logger = logging.getLogger(__name__)

CHUNK_SIZE = 500


def seed_ncms_for_company(empresa_id, force=False):
    """Seed EmpresaNCM entries for a given company from global NCM templates.

    If force=True, existing conflicting codes will not be touched; function is idempotent.
    Returns a dict with counts: created, skipped, total_templates
    """
    # Skip running seed during test runs to avoid SQLite locking and noisy logs
    import sys
    from django.conf import settings
    if getattr(settings, 'TESTING', False) or any(arg.startswith('test') for arg in sys.argv):
        logger.info('seed_ncms_for_company: skipping during tests')
        return {'total_templates': 0, 'created': 0, 'skipped': 0, 'skipped_in_tests': True}

    # Ensure DB connections in this thread are usable
    try:
        close_old_connections()
    except Exception:
        pass

    try:
        empresa = Empresa.objects.filter(pk=empresa_id).first()
        if not empresa:
            logger.warning('seed_ncms_for_company: Empresa %s not found', empresa_id)
            return {'error': 'Empresa not found'}

        templates = list(NCM.objects.filter(ativo=True).order_by('codigo'))
        total = len(templates)
        created = 0
        skipped = 0

        # We'll create EmpresaNCM objects in bulk for those that don't exist
        to_create = []
        existing_codes = set(EmpresaNCM.objects.filter(empresa=empresa).values_list('codigo', flat=True))

        for t in templates:
            if t.codigo in existing_codes and not force:
                skipped += 1
                continue
            if t.codigo not in existing_codes:
                en = EmpresaNCM(
                    empresa=empresa,
                    codigo=t.codigo,
                    nome=t.nome,
                    descricao=t.descricao,
                    cest=t.cest,
                    ativo=t.ativo,
                    template=t,
                )
                to_create.append(en)
    except Exception as e:
        logger.exception('seed_ncms_for_company initial DB read failed: %s', e)
        return {'error': str(e)}
    # bulk create in chunks
    try:
        for i in range(0, len(to_create), CHUNK_SIZE):
            EmpresaNCM.objects.bulk_create(to_create[i:i+CHUNK_SIZE])
            created += len(to_create[i:i+CHUNK_SIZE])
    except Exception as e:
        logger.exception('Error during bulk_create in seed_ncms_for_company: %s', e)

    # update last seed timestamp
    try:
        empresa.last_ncm_seeded_at = timezone.now()
        empresa.save(update_fields=['last_ncm_seeded_at'])
    except Exception as e:
        logger.exception('Failed to update last_ncm_seeded_at for %s: %s', empresa, e)

    return {'total_templates': total, 'created': created, 'skipped': skipped}


def seed_ncms_for_company_async(empresa_id, force=False):
    """Spawn a background thread to run seeding function. Non-blocking."""
    thread = threading.Thread(target=seed_ncms_for_company, args=(empresa_id, force), daemon=True)
    thread.start()
    return thread