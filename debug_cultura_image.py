#!/usr/bin/env python
"""
Debug para verificar por que imagem da Cultura não está sendo salva no Supabase
"""
import os
import sys
import django
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.insert(0, str(Path(__file__).parent))
django.setup()

import logging
from django.conf import settings
from django.db.models.signals import post_save
from cadastros.models import Cultura

# Ativar debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

print("\n" + "="*80)
print("DEBUG: UPLOAD DE IMAGEM DA CULTURA")
print("="*80)

# 1. Verificar settings
print("\n[1] VERIFICANDO SETTINGS:")
print(f"    SUPABASE_URL: {settings.SUPABASE_URL if hasattr(settings, 'SUPABASE_URL') else 'NÃO ENCONTRADO'}")
print(f"    SUPABASE_KEY: {settings.SUPABASE_KEY[:20] if hasattr(settings, 'SUPABASE_KEY') and settings.SUPABASE_KEY else 'NÃO ENCONTRADO'}...")
print(f"    SUPABASE_STORAGE_ENABLED: {settings.SUPABASE_STORAGE_ENABLED}")
print(f"    SUPABASE_STORAGE_BUCKETS: {list(settings.SUPABASE_STORAGE_BUCKETS.keys())}")

# 2. Verificar storage helper
print("\n[2] VERIFICANDO STORAGE HELPER:")
try:
    from core.storage import storage_helper
    print(f"    ✓ Storage helper inicializado")
    print(f"    ✓ Supabase client habilitado: {storage_helper.enabled}")
    print(f"    ✓ Client conectado: {storage_helper.client is not None}")
except Exception as e:
    print(f"    ✗ ERRO ao inicializar storage_helper: {e}")

# 3. Verificar signal registrado
print("\n[3] VERIFICANDO SIGNAL REGISTRADO:")
receivers = post_save._live_receivers(Cultura)
cultura_signals = [r.__name__ if hasattr(r, '__name__') else str(r) for r in receivers]
print(f"    Total de receivers: {len(receivers)}")
if any('cultura' in str(r).lower() and 'imagem' in str(r).lower() for r in receivers):
    print(f"    ✓ Signal 'cultura_post_save_upload_imagem' encontrado")
else:
    print(f"    ✗ Signal 'cultura_post_save_upload_imagem' NÃO ENCONTRADO")
    print(f"    Receivers registrados: {cultura_signals}")

# 4. Listar últimas culturas
print("\n[4] ÚLTIMAS CULTURAS CADASTRADAS:")
culturas = Cultura.objects.all().order_by('-pk')[:5]
for c in culturas:
    print(f"    ID: {c.pk}, Nome: {c.nome}, Tem imagem: {bool(c.imagem)}")
    if c.imagem:
        print(f"       Imagem: {c.imagem.name}")
        print(f"       URL: {c.imagem.url if c.imagem else 'N/A'}")

print("\n[5] PRÓXIMOS PASSOS:")
print("    1. Se signal não foi encontrado, reiniciar servidor")
print("    2. Se SUPABASE_STORAGE_ENABLED=False, verificar variáveis de ambiente")
print("    3. Criar nova Cultura com imagem e verificar logs")

print("\n" + "="*80)
