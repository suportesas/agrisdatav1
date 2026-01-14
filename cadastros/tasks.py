import threading
from django.utils import timezone
from django.db import transaction
from .models import NCM, EmpresaNCM
from empresas.models import Empresa

CHUNK_SIZE = 500


def seed_ncms_for_company(empresa_id, force=False):
    """Seed EmpresaNCM entries for a given company from global NCM templates.

    If force=True, existing conflicting codes will not be touched; function is idempotent.
    Returns a dict with counts: created, skipped, total_templates
    """
    empresa = Empresa.objects.filter(pk=empresa_id).first()
    if not empresa:
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

    # bulk create in chunks
    for i in range(0, len(to_create), CHUNK_SIZE):
        EmpresaNCM.objects.bulk_create(to_create[i:i+CHUNK_SIZE])
        created += len(to_create[i:i+CHUNK_SIZE])

    # update last seed timestamp
    empresa.last_ncm_seeded_at = timezone.now()
    empresa.save(update_fields=['last_ncm_seeded_at'])

    return {'total_templates': total, 'created': created, 'skipped': skipped}


def seed_ncms_for_company_async(empresa_id, force=False):
    """Spawn a background thread to run seeding function. Non-blocking."""
    thread = threading.Thread(target=seed_ncms_for_company, args=(empresa_id, force), daemon=True)
    thread.start()
    return thread