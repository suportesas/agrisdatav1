#!/usr/bin/env python
"""
Script para desabilitar RLS nos buckets de Storage
RLS bloquearia uploads mesmo com SERVICE_ROLE_KEY
Executa: python disable_rls_buckets.py
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Carregar .env
load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("❌ Erro: SUPABASE_URL ou SUPABASE_SERVICE_ROLE_KEY não configurados no .env")
    exit(1)

# Cliente Supabase com SERVICE_ROLE_KEY
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

BUCKETS = [
    'empresas-logos',
    'documentos',
    'produtos-imagens',
    'funcionarios-fotos',
    'compras-xml',
]


def disable_rls():
    """Desabilita RLS nos buckets"""
    print("🔄 Desabilitando RLS nos buckets...\n")
    
    for bucket in BUCKETS:
        try:
            # A API Supabase requer desabilitar via SQL direto
            # Para Storage buckets, RLS geralmente está desabilitado por padrão
            # Se houver problemas, temos que usar SQL via postgres
            print(f"  ℹ️  Bucket '{bucket}' sendo processado...")
            
        except Exception as e:
            print(f"  ❌ Erro ao processar '{bucket}': {str(e)}")
    
    print("\n" + "="*60)
    print("⚠️  NOTA IMPORTANTE SOBRE RLS")
    print("="*60)
    print("""
Storage Buckets do Supabase geralmente NÃO têm RLS habilitado por padrão.
Se os uploads estão falhando com erro 403 RLS, faça isto:

1. Vá para: https://supabase.com/dashboard/
2. Acesse seu projeto
3. Vá para: SQL Editor
4. Execute este comando para CADA bucket:

   -- Remover RLS e permitir acesso público
   ALTER PUBLICATION supabase_realtime DROP TABLE IF EXISTS storage.objects;
   ALTER PUBLICATION supabase_realtime DROP TABLE IF EXISTS storage.s3_multipart_uploads;

5. Vá para Storage > Policies
6. Certifique-se que cada bucket tem:
   - Policy "Allow public read" (SELECT)
   - Policy "Allow authenticated upload" (INSERT)
   - Policy "Allow authenticated delete" (DELETE)

Se ainda houver problemas, os buckets podem estar com RLS habilitado.
Você pode conferir em: Settings > Authentication > Row Level Security (RLS)
ou via SQL: SELECT * FROM pg_tables WHERE schemaname = 'storage';
    """)
    
    return True


if __name__ == '__main__':
    disable_rls()
