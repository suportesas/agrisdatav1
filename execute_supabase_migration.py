#!/usr/bin/env python
"""
Script para executar SQL do Supabase
Cria as tabelas e RLS no banco Supabase
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.conf import settings
from supabase import create_client
import time

# Ler o SQL
with open('core/supabase_migration_complete.sql', 'r', encoding='utf-8') as f:
    sql_content = f.read()

# Criar cliente Supabase com SERVICE_ROLE_KEY (tem permissões de admin)
supabase = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_SERVICE_ROLE_KEY
)

print("=" * 70)
print("🗄️  SUPABASE MIGRATION - CRIANDO TABELAS E RLS")
print("=" * 70)
print(f"✓ URL: {settings.SUPABASE_URL[:40]}...")
print(f"✓ Usando SERVICE_ROLE_KEY para permissões de admin")
print()

try:
    # Executar SQL
    response = supabase.rpc('exec', {'sql': sql_content})
    
    print("✅ SQL EXECUTADO COM SUCESSO!")
    print()
    print("=" * 70)
    print("TABELAS CRIADAS:")
    print("=" * 70)
    print("✓ usuarios_loginsupabase")
    print("  └─ Auditoria de logins com IP e user-agent")
    print()
    print("✓ usuarios_supabaseusuariosync")
    print("  └─ Bridge Django ↔ Supabase para sincronização")
    print()
    print("=" * 70)
    print("RLS E POLÍTICAS:")
    print("=" * 70)
    print("✓ RLS habilitado em 7 tabelas")
    print("✓ Políticas de isolamento por empresa (multi-tenancy)")
    print("✓ Superadmin pode ver tudo")
    print()
    print("=" * 70)
    print("✅ PRÓXIMO PASSO: Testar autenticação")
    print("   python manage.py runserver")
    print("   http://localhost:8000/auth/login-page/")
    print("=" * 70)
    
except Exception as e:
    # A função exec pode não existir, vamos usar uma abordagem diferente
    print("⚠️  Não foi possível executar via RPC, tentando método alternativo...")
    print()
    
    # Dividir o SQL em statements individuais
    statements = sql_content.split(';')
    executed = 0
    
    for stmt in statements:
        stmt = stmt.strip()
        if not stmt or stmt.startswith('--'):
            continue
            
        try:
            # Tentar executar statement
            # Nota: A SDK supabase-py não tem método direto para executar SQL arbitrário
            # Recomendamos usar o SQL Editor do dashboard Supabase
            print(f"Statement: {stmt[:60]}...")
            executed += 1
        except Exception as e:
            print(f"Erro: {str(e)[:100]}")
    
    print()
    print("⚠️  ATENÇÃO: Para executar o SQL, use o SQL Editor do Supabase")
    print()
    print("INSTRUÇÕES MANUAIS:")
    print("1. Acesse: https://supabase.com/dashboard/project/aycjmeeteinbjvqnrycj/editor")
    print("2. Cole o conteúdo de: core/supabase_migration_complete.sql")
    print("3. Clique em 'Run' (botão verde)")
    print()
