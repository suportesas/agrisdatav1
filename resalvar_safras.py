#!/usr/bin/env python
"""
Resalva as safras existentes para disparar o signal de upload
"""
import os
import sys
import django
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.insert(0, str(Path(__file__).parent))
django.setup()

import logging
from cadastros.models import Safra

# Ativar debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

print("\n" + "="*80)
print("RESALVANDO SAFRAS PARA DISPARAR UPLOAD")
print("="*80)

# Buscar safras com imagem
safras_com_imagem = Safra.objects.filter(imagem__isnull=False).exclude(imagem='')

print(f"\nSafras com imagem: {safras_com_imagem.count()}")

for safra in safras_com_imagem:
    print(f"\n[{safra.pk}] {safra.nome}")
    print(f"    Imagem atual: {safra.imagem.name if safra.imagem else 'Não tem'}")
    
    try:
        # Resalva para disparar o signal
        safra.save()
        print(f"    ✓ Resalvo disparado - Signal será executado")
    except Exception as e:
        print(f"    ✗ ERRO ao resalvar: {e}")

print("\n" + "="*80)
print("Verifique os logs acima para ver se o upload foi bem-sucedido")
print("="*80 + "\n")
