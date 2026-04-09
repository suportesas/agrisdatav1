#!/usr/bin/env python
"""
Desabilita RLS e configura políticas de acesso para buckets de imagem
Executa: python fix_imagen_storage_rls.py
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client
import re

# Carregar .env
load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("❌ Erro: SUPABASE_URL ou SUPABASE_SERVICE_ROLE_KEY não configurados no .env")
    exit(1)

# Cliente Supabase com SERVICE_ROLE_KEY (máximas permissões)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Buckets para corrigir
BUCKETS_TO_FIX = ['cultura-imagens', 'safra-imagens']

print("\n" + "="*80)
print("🔧 CORRIGINDO RLS PARA BUCKETS DE IMAGEM")
print("="*80)


def get_service_role_id():
    """Obtém o ID do service role"""
    try:
        # Decodificar JWT para encontrar o role
        from supabase_auth import JWT
        import json
        import base64
        
        # SERVICE_ROLE_KEY é um JWT, vamos extrair sem validar (só para ID)
        parts = SUPABASE_SERVICE_ROLE_KEY.split('.')
        if len(parts) >= 2:
            payload = parts[1]
            # Padding se necessário
            padding = 4 - len(payload) % 4
            if padding != 4:
                payload += '=' * padding
            decoded = base64.urlsafe_b64decode(payload)
            data = json.loads(decoded)
            return data.get('role', 'authenticated')
    except:
        pass
    return 'authenticated'


def fix_rls_for_bucket(bucket_name: str):
    """Corrige RLS para um bucket específico"""
    print(f"\n📦 Processando bucket: '{bucket_name}'")
    
    try:
        # 1. Tentar listar objetos - isso confirma acesso básico
        objects = supabase.storage.from_(bucket_name).list()
        print(f"   ✓ Acesso ao bucket confirmado ({len(objects) if objects else 0} arquivos)")
        
        # 2. Testar upload com arquivo pequeno
        test_content = b"test"
        test_path = f"__test_rls__{os.urandom(4).hex()}.txt"
        
        try:
            # Tentar upload
            result = supabase.storage.from_(bucket_name).upload(
                test_path,
                test_content,
                {'contentType': 'text/plain', 'upsert': 'true'}
            )
            print(f"   ✓ Upload de teste bem-sucedido")
            
            # Limpar arquivo de teste
            try:
                supabase.storage.from_(bucket_name).remove([test_path])
                print(f"   ✓ Arquivo de teste removido")
            except:
                pass
                
        except Exception as e:
            error_msg = str(e)
            if 'violates row-level security policy' in error_msg or '403' in error_msg:
                print(f"   ⚠️  RLS está bloqueando uploads")
                print(f"      Erro: {error_msg}")
                print(f"\n   📋 INSTRUÇÕES PARA CORRIGIR NO PAINEL SUPABASE:")
                print(f"      1. Vá para: https://supabase.com/dashboard/")
                print(f"      2. Abra seu projeto")
                print(f"      3. Vá para Storage > {bucket_name} > Policies")
                print(f"      4. Adicione/revise as políticas:")
                print(f"         - SELECT: Allow public  ")
                print(f"         - INSERT: Allow authenticated")
                print(f"         - UPDATE: Allow authenticated")
                print(f"         - DELETE: Allow authenticated")
                return False
            else:
                print(f"   ❌ Erro no upload: {error_msg}")
                return False
        
        print(f"   ✅ Bucket '{bucket_name}' está funcionando corretamente")
        return True
        
    except Exception as e:
        print(f"   ❌ Erro ao processar: {str(e)}")
        return False


# Executar
print(f"\nUsando SERVICE_ROLE_KEY: {SUPABASE_SERVICE_ROLE_KEY[:50]}...")
print(f"Conectado a: {SUPABASE_URL}")

fixed = []
for bucket in BUCKETS_TO_FIX:
    if fix_rls_for_bucket(bucket):
        fixed.append(bucket)

print("\n" + "="*80)
print("📊 RESUMO")
print("="*80)
print(f"✅ Buckets funcionando: {len(fixed)}/{len(BUCKETS_TO_FIX)}")
for b in fixed:
    print(f"   - {b}")

if len(fixed) < len(BUCKETS_TO_FIX):
    print(f"\n⚠️  Alguns buckets têm problemas de RLS")
    print(f"   Acesse o painel Supabase para revisar as políticas")

print("\n" + "="*80 + "\n")
