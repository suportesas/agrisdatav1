#!/usr/bin/env python
"""
Script para criar buckets no Supabase Storage
Executa: python generate_supabase_buckets.py
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

# Cliente Supabase com SERVICE_ROLE_KEY (permissões de admin)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Buckets a criar
BUCKETS = [
    {
        'name': 'empresas-logos',
        'description': 'Logos das empresas',
    },
    {
        'name': 'documentos',
        'description': 'Documentos gerais (PDFs, Word, Excel)',
    },
    {
        'name': 'produtos-imagens',
        'description': 'Imagens de produtos',
    },
    {
        'name': 'funcionarios-fotos',
        'description': 'Fotos de funcionários',
    },
    {
        'name': 'compras-xml',
        'description': 'Arquivos XML de notas fiscais',
    },
]


def criar_buckets():
    """Cria buckets no Supabase Storage"""
    print("🔄 Criando buckets no Supabase Storage...\n")
    
    sucesso = 0
    erro = 0
    
    for bucket in BUCKETS:
        try:
            # Tenta criar o bucket como público
            response = supabase.storage.create_bucket(bucket['name'])
            print(f"✅ Bucket '{bucket['name']}' criado com sucesso")
            print(f"   └─ {bucket['description']}")
            sucesso += 1
            
        except Exception as e:
            error_msg = str(e)
            
            # Se o bucket já existe, é apenas um aviso
            if 'already exists' in error_msg or 'duplicate' in error_msg.lower():
                print(f"⚠️  Bucket '{bucket['name']}' já existe")
                sucesso += 1
            else:
                print(f"❌ Erro ao criar '{bucket['name']}':")
                print(f"   └─ {error_msg}")
                erro += 1
    
    print(f"\n{'='*60}")
    print(f"📊 Resultado: {sucesso} OK, {erro} Erros")
    print(f"{'='*60}\n")
    
    if erro == 0:
        print("✅ Todos os buckets estão prontos!")
        print("\nBuckets criados:")
        for bucket in BUCKETS:
            print(f"  • {bucket['name']}")
    
    return erro == 0


if __name__ == '__main__':
    sucesso = criar_buckets()
    exit(0 if sucesso else 1)
