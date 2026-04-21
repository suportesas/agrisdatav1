#!/usr/bin/env python
"""
Sincroniza retroativamente os campos de assinatura de liberação interna dos EmprestimoProdutor
com base nos dados da Requisicao relacionada.
"""
import os
import sys
import django
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.insert(0, str(Path(__file__).parent))
django.setup()

from cadastros.models import EmprestimoProdutor

count = 0
for emp in EmprestimoProdutor.objects.filter(requisicao__isnull=False):
    req = emp.requisicao
    if req and req.assinatura_liberacao_interna_imagem and req.assinatura_liberacao_interna_datahora:
        # Só sincroniza se o EmprestimoProdutor ainda não tem assinatura
        if not emp.assinatura_liberador_imagem and not emp.assinatura_liberador_datahora:
            emp.assinatura_liberador_imagem = req.assinatura_liberacao_interna_imagem
            emp.assinatura_liberador_nome = req.assinatura_liberacao_interna_nome
            emp.assinatura_liberador_datahora = req.assinatura_liberacao_interna_datahora
            emp.liberado_por = req.assinatura_liberacao_interna_usuario
            emp.save(update_fields=[
                'assinatura_liberador_imagem',
                'assinatura_liberador_nome',
                'assinatura_liberador_datahora',
                'liberado_por',
            ])
            print(f"EmprestimoProdutor {emp.pk} sincronizado com assinatura da Requisicao {req.pk}")
            count += 1

print(f"\nTotal de EmprestimoProdutor sincronizados: {count}\n")
