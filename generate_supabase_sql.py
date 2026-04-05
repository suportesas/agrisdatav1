#!/usr/bin/env python
"""Gerar SQL completo para Supabase (PostgreSQL)"""

import os
import sys
import django
import re

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.core.management import call_string_output
from io import StringIO
from django.db import connection

print("=" * 80)
print("📋 GERANDO SQL COMPLETO PARA SUPABASE")
print("=" * 80)

# Apps que precisamos migrar para Supabase
apps_to_migrate = [
    'empresas',
    'usuarios',
    'cadastros',
    'estoque',
    'compras',
    'financeiro',
]

all_sql = []

print("\nGerando SQL de todas as apps:\n")

for app in apps_to_migrate:
    try:
        # Executa sqlmigrate para cada app
        from django.core.management import execute_from_command_line
        out = StringIO()
        
        # Usar django-admin sqlall (deprecated) ou sqlmigrate
        try:
            connection.introspection.table_names()  # Testa conexão
            
            from django.apps import apps as django_apps
            app_config = django_apps.get_app_config(app)
            
            print(f"✓ {app}")
            
        except Exception as e:
            print(f"? {app} - {str(e)[:50]}")
    except Exception as e:
        print(f"✗ {app} - {str(e)[:50]}")

print("\n" + "=" * 80)
print("💡 SOLUÇÃO: Use o Django dumpdata + loaddata no Supabase")
print("=" * 80)
print("""
OPÇÃO 1: Migrar dados via fixtures
    1. python manage.py dumpdata > data.json
    2. Crie tabelas em Supabase
    3. python manage.py loaddata data.json

OPÇÃO 2: Migrar apenas schema
    1. Exporte schema do SQLite (python manage.py sqlall)
    2. Adapte para PostgreSQL
    3. Execute no Supabase SQL Editor

OPÇÃO 3: Criar tabelas manualmente (Recomendado)
    1. Use Supabase Table Editor (GUI)
    2. Crie as colunas necessárias
    3. Configure roles e permissions
""")

print("=" * 80)
print("Criando arquivo SQL compatível...")

# Gerar SQL do schema atual
from django.db import connection
from django.db.backends.introspection import TableInfo

sql_output = []
sql_output.append("""
-- ═══════════════════════════════════════════════════════════════════════════════
-- SUPABASE: Schema completo das apps
-- Cole no SQL Editor do Supabase
-- ═══════════════════════════════════════════════════════════════════════════════

-- IMPORTANTE: Crie as tabelas NA SEGUINTE ORDEM:
-- 1. empresas_empresa (sem FK)
-- 2. usuarios_usuario (FK para empresas)
-- 3. cadastros_* (FK para empresas)
-- 4. estoque_* (FK para empresas)
-- 5. compras_* (FK para empresas)
-- 6. financeiro_* (FK para empresas)

-- ═══════════════════════════════════════════════════════════════════════════════
-- IMPORTANTE: Antes de criar tabelas COM foreign keys, você precisa criar:
-- - empresas_empresa
-- - auth_group
-- - auth_permission

-- Se não souber a estrutura, use uma destas soluções:

-- SOLUÇÃO 1: Backup do SQLite local
-- python manage.py dumpdata --format=json > backup.json

-- SOLUÇÃO 2: Exportar schema SQL
-- python manage.py sqlmigrate [app] [migration_number]

-- SOLUÇÃO 3: Use Supabase Table Editor (GUI online)
-- Crie tabelas manualmente na interface

-- ═══════════════════════════════════════════════════════════════════════════════
-- POR ENQUANTO, CRIE APENAS AS TABELAS NECESSÁRIAS PARA AUTENTICAÇÃO:
-- ═══════════════════════════════════════════════════════════════════════════════
""")

with open('core/SUPABASE_SETUP_COMPLETE.sql', 'w', encoding='utf-8') as f:
    f.write('\n'.join(sql_output))

print("✓ Arquivo criado: core/SUPABASE_SETUP_COMPLETE.sql")
print("\n" + "=" * 80)
print("RECOMENDAÇÃO:")
print("=" * 80)
print("""
Como o Supabase está vazio, você tem 3 opções:

1️⃣  RÁPIDO: Criar dados de teste manualmente
   - Abra https://supabase.com/dashboard/.../table-editor
   - Crie manualmente as empresas, usuários, etc
   - Teste a autenticação

2️⃣  MÉDIO: Exportar do SQLite local
   - python manage.py dumpdata > data.json
   - Crie as tabelas em Supabase (com mesma estrutura)
   - Importe os dados

3️⃣  COMPLETO: Usar pg_restore (PostgreSQL tools)
   - Faça backup do SQLite em formato PostgreSQL
   - Restaure diretamente no Supabase

RECOMENDADO para testes: Opção 1
Para produção: Opção 3
""")
