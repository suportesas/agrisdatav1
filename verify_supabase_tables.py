#!/usr/bin/env python
"""Verificar tabelas criadas no Supabase"""

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
print("🔍 VERIFICAÇÃO DE TABELAS NO SUPABASE")
print("=" * 70)

try:
    # Listar todas as tabelas no schema public
    response = supabase.table('information_schema.tables').select('table_name').eq('table_schema', 'public').execute()
    
    if response.data:
        print("✅ Tabelas encontradas no Supabase:\n")
        tabelas = [t['table_name'] for t in response.data]
        
        for tabela in sorted(tabelas):
            status = "✓" if any(x in tabela for x in ['loginsupabase', 'supabaseusuariosync']) else " "
            print(f"  {status} {tabela}")
        
        # Verificar nossas tabelas específicas
        print("\n" + "=" * 70)
        print("TABELAS CRIADAS NESTA MIGRATION:")
        print("=" * 70)
        
        if 'usuarios_loginsupabase' in tabelas:
            print("✅ usuarios_loginsupabase - CRIADA")
        else:
            print("❌ usuarios_loginsupabase - NÃO ENCONTRADA")
            
        if 'usuarios_supabaseusuariosync' in tabelas:
            print("✅ usuarios_supabaseusuariosync - CRIADA")
        else:
            print("❌ usuarios_supabaseusuariosync - NÃO ENCONTRADA")
    else:
        print("❌ Nenhuma tabela encontrada")
        
except Exception as e:
    print(f"⚠️  Erro ao consultardirectly: {str(e)[:100]}")
    print("\n💡 Verifique manualmente em:")
    print("   https://supabase.com/dashboard/project/aycjmeeteinbjvqnrycj/editor")
    print("   → Table Editor → Schema public")
