#!/usr/bin/env python
"""
Solução: Copiar dados do SQLite local para Supabase
Exporte JSON e crie tabelas simples no Supabase
"""

import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.core.management import execute_from_command_line

print("=" * 80)
print("📊 EXPORTANDO DADOS DO SQLITE PARA JSON")
print("=" * 80)

# Exportar dados
print("\n1. Exportando usuarios...")
os.system("python manage.py dumpdata usuarios > usuarios_backup.json")
print("   ✓ usuarios_backup.json criado")

print("\n2. Exportando empresas...")
os.system("python manage.py dumpdata empresas > empresas_backup.json")
print("   ✓ empresas_backup.json criado")

print("\n3. Exportando todos os dados...")
os.system("python manage.py dumpdata > backup_completo.json")
print("   ✓ backup_completo.json criado")

print("\n" + "=" * 80)
print("✅ BACKUP CRIADO COM SUCESSO!")
print("=" * 80)

print("""
PRÓXIMOS PASSOS:

1️⃣  Criar tabelas simples no Supabase (SEM foreign keys):

    -- TABELA: empresas_empresa
    CREATE TABLE IF NOT EXISTS public.empresas_empresa (
        id BIGSERIAL PRIMARY KEY,
        nome VARCHAR(200) NOT NULL,
        cnpj VARCHAR(18) UNIQUE,
        data_criacao TIMESTAMP WITH TIME ZONE
    );

    -- TABELA: usuarios_usuario (versão simplificada)
    CREATE TABLE IF NOT EXISTS public.usuarios_usuario (
        id BIGSERIAL PRIMARY KEY,
        username VARCHAR(150) NOT NULL UNIQUE,
        email VARCHAR(254),
        password VARCHAR(128),
        first_name VARCHAR(150),
        last_name VARCHAR(150),
        is_active BOOLEAN DEFAULT true,
        is_staff BOOLEAN DEFAULT false,
        is_superuser BOOLEAN DEFAULT false,
        date_joined TIMESTAMP WITH TIME ZONE,
        tipo VARCHAR(15),
        empresa_id BIGINT,
        other fields...
    );

2️⃣  Depois, use Python para importar os dados:

    from supabase import create_client
    import json

    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

    # Ler dados
    with open('usuarios_backup.json') as f:
        data = json.load(f)

    # Inserir no Supabase
    for record in data:
        supabase.table('usuarios_usuario').insert(record['fields']).execute()

3️⃣  Ou use o Supabase CLI:

    supabase db push  # Sincronizar esquema
    supabase db remote commit  # Enviar dados

═══════════════════════════════════════════════════════════════════════════════

RECOMENDAÇÃO MAIS SIMPLES:

Para começar a testar a autenticação, você pode:
1. Criar 1 empresa teste no Supabase via Table Editor
2. Criar 1 usuário teste
3. Testar o login/registro
4. Depois importar todos os dados

Arquivos criados:
- usuarios_backup.json
- empresas_backup.json  
- backup_completo.json
""")
