#!/usr/bin/env python
"""Verificar alternativamente as tabelas criadas"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.conf import settings
from supabase import create_client

supabase = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_SERVICE_ROLE_KEY
)

print("=" * 70)
print("🔍 TESTER DE TABELAS - Supabase")
print("=" * 70)

# Testar cada tabela
tabelas_para_testar = [
    'usuarios_loginsupabase',
    'usuarios_supabaseusuariosync',
    'usuarios_usuario',
    'cadastros_fazenda'
]

print("\nTestando acesso às tabelas:\n")

for tabela in tabelas_para_testar:
    try:
        # Tenta listar 1 linha (ou ver que tabela existe)
        response = supabase.table(tabela).select('*', count='exact').limit(1).execute()
        
        # Se conseguir chegar aqui, tabela existe
        print(f"✅ {tabela}")
        print(f"   └─ Acessível (total: {response.count} registros)")
        
    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower() or "does not exist" in error_msg.lower():
            print(f"❌ {tabela}")
            print(f"   └─ NÃO ENCONTRADA")
        else:
            print(f"❓ {tabela}")
            print(f"   └─ Erro: {error_msg[:60]}...")

print("\n" + "=" * 70)
print("💡 VERIFICAÇÃO MANUAL")
print("=" * 70)
print("Se as tabelas não aparecerem acima, verifique em:")
print("https://supabase.com/dashboard/project/aycjmeeteinbjvqnrycj/editor")
print("\n1. Clique em 'SQL Editor' (aba superior)")
print("2. Execute este comando:")
print("   SELECT tablename FROM pg_tables WHERE schemaname='public';")
print("=" * 70)
