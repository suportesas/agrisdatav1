#!/usr/bin/env python
"""
Sincroniza assinaturas de liberação interna retroativamente:
Para cada EmprestimoProdutor com assinatura de liberação preenchida e requisição relacionada,
copia os dados de assinatura para a Requisicao caso ainda estejam pendentes.
"""
import os
import sys
import django
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.insert(0, str(Path(__file__).parent))
django.setup()

from cadastros.models import EmprestimoProdutor

assinados = EmprestimoProdutor.objects.filter(
    assinatura_liberador_imagem__isnull=False,
    assinatura_liberador_datahora__isnull=False,
    requisicao__isnull=False
)

count = 0
for emp in assinados:
    req = emp.requisicao
    if req.assinatura_liberacao_interna_imagem and req.assinatura_liberacao_interna_datahora:
        continue  # já sincronizado
    req.assinatura_liberacao_interna_imagem = emp.assinatura_liberador_imagem
    req.assinatura_liberacao_interna_nome = emp.assinatura_liberador_nome
    req.assinatura_liberacao_interna_datahora = emp.assinatura_liberador_datahora
    req.assinatura_liberacao_interna_usuario = emp.liberado_por
    req.save(update_fields=[
        'assinatura_liberacao_interna_imagem',
        'assinatura_liberacao_interna_nome',
        'assinatura_liberacao_interna_datahora',
        'assinatura_liberacao_interna_usuario',
    ])
    print(f"Sincronizado requisição {req.pk} com assinatura do empréstimo {emp.pk}")
    count += 1

print(f"\nTotal de requisições sincronizadas: {count}\n")
