#!/usr/bin/env python
"""
Script para inicializar buckets do Supabase Storage
Cria os buckets configurados em SUPABASE_STORAGE_BUCKETS se não existirem
"""

import os
import sys
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

import logging

logger = logging.getLogger(__name__)


def initialize_supabase_buckets():
    """Inicializa todos os buckets do Supabase Storage"""
    try:
        from core.supabase_config import supabase_auth
        
        if not settings.SUPABASE_STORAGE_ENABLED:
            print("⚠️  Supabase Storage não habilitado (SUPABASE_URL não configurado)")
            return False
        
        client = supabase_auth.client
        buckets_config = settings.SUPABASE_STORAGE_BUCKETS
        
        print(f"\n📦 Inicializando {len(buckets_config)} buckets no Supabase Storage...\n")
        
        # Listar buckets existentes
        existing_buckets = set()
        try:
            buckets = client.storage.list_buckets()
            existing_buckets = {b.name for b in buckets}
        except Exception as e:
            logger.warning(f"Erro ao listar buckets existentes: {e}")
        
        created = []
        already_exist = []
        
        # Criar/verificar cada bucket
        for bucket_name, description in buckets_config.items():
            if bucket_name in existing_buckets:
                already_exist.append(bucket_name)
                print(f"✅ {bucket_name:25} → Já existe ({description})")
            else:
                try:
                    client.storage.create_bucket(
                        bucket_name,
                        options={
                            "public": True,  # Acessível publicamente
                            "allowed_mime_types": ["image/*", "application/pdf", "text/xml", "application/json"],
                        }
                    )
                    created.append(bucket_name)
                    print(f"✨ {bucket_name:25} → Criado ({description})")
                except Exception as e:
                    print(f"❌ {bucket_name:25} → Erro: {str(e)}")
        
        print(f"\n📊 Resumo:")
        print(f"   ✨ Criados: {len(created)}")
        print(f"   ✅ Já existentes: {len(already_exist)}")
        print(f"   📦 Total: {len(buckets_config)}")
        
        if created:
            print(f"\n   Buckets criados: {', '.join(created)}")
        
        print(f"\n✓ Supabase Storage inicializado com sucesso!\n")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao inicializar buckets: {e}")
        print(f"\n❌ Erro ao inicializar buckets: {e}\n")
        return False


if __name__ == '__main__':
    success = initialize_supabase_buckets()
    sys.exit(0 if success else 1)
