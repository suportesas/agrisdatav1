#!/usr/bin/env python
"""
Resalva as culturas existentes para disparar o signal de upload
"""
import os
import sys
import django
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.insert(0, str(Path(__file__).parent))
django.setup()

import logging
from cadastros.models import Cultura

# Ativar debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

print("\n" + "="*80)
print("RESALVANDO CULTURAS PARA DISPARAR UPLOAD")
print("="*80)

# Buscar culturas com imagem
culturas_com_imagem = Cultura.objects.filter(imagem__isnull=False).exclude(imagem='')

print(f"\nCulturas com imagem: {culturas_com_imagem.count()}")

for cultura in culturas_com_imagem:
    print(f"\n[{cultura.pk}] {cultura.nome}")
    print(f"    Imagem atual: {cultura.imagem.name if cultura.imagem else 'Não tem'}")
    
    try:
        # Resalva para disparar o signal
        cultura.save()
        print(f"    ✓ Resalvo disparado - Signal será executado")
    except Exception as e:
        print(f"    ✗ ERRO ao resalvar: {e}")

print("\n" + "="*80)
print("Verifique os logs acima para ver se o upload foi bem-sucedido")
print("="*80 + "\n")
