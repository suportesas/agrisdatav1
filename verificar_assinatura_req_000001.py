#!/usr/bin/env python
"""
Verifica o status da assinatura de liberação interna da requisição REQ-000001 e dos empréstimos relacionados.
"""
import os
import sys
import django
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.insert(0, str(Path(__file__).parent))
django.setup()

from cadastros.models import Requisicao

try:
    req = Requisicao.objects.get(numero='REQ-000001')
    print(f"Requisição: {req.numero} (ID: {req.pk})")
    print(f"  assinatura_liberacao_interna_imagem: {req.assinatura_liberacao_interna_imagem}")
    print(f"  assinatura_liberacao_interna_nome: {req.assinatura_liberacao_interna_nome}")
    print(f"  assinatura_liberacao_interna_datahora: {req.assinatura_liberacao_interna_datahora}")
    print(f"  assinatura_liberacao_interna_usuario: {req.assinatura_liberacao_interna_usuario}")
    print("\nEmpréstimos relacionados:")
    for emp in req.emprestimos_gerados.all():
        print(f"  EmprestimoProdutor ID: {emp.pk}")
        print(f"    assinatura_liberador_imagem: {emp.assinatura_liberador_imagem}")
        print(f"    assinatura_liberador_nome: {emp.assinatura_liberador_nome}")
        print(f"    assinatura_liberador_datahora: {emp.assinatura_liberador_datahora}")
        print(f"    liberado_por: {emp.liberado_por}")
        print()
except Requisicao.DoesNotExist:
    print("Requisição REQ-000001 não encontrada.")
