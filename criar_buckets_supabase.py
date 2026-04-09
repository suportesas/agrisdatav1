#!/usr/bin/env python
"""
Script para criar buckets no Supabase Storage via API
Executa: python criar_buckets_supabase.py
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.conf import settings


def criar_buckets():
    """Cria todos os buckets no Supabase via API"""
    try:
        from core.supabase_config import supabase_auth
        
        if not settings.SUPABASE_STORAGE_ENABLED:
            print("❌ Supabase Storage não habilitado")
            return False
        
        client = supabase_auth.client
        buckets_config = settings.SUPABASE_STORAGE_BUCKETS
        
        print(f"\n📦 Criando {len(buckets_config)} buckets no Supabase Storage...\n")
        
        # Listar buckets existentes
        buckets = client.storage.list_buckets()
        existing_buckets = {b.name for b in buckets}
        
        criados = []
        ja_existem = []
        erros = []
        
        for bucket_name, description in buckets_config.items():
            if bucket_name in existing_buckets:
                ja_existem.append(bucket_name)
                print(f"✅ {bucket_name:25} → Já existe ({description})")
            else:
                try:
                    # Criar bucket
                    client.storage.create_bucket(
                        bucket_name,
                        options={"public": True}
                    )
                    criados.append(bucket_name)
                    print(f"✨ {bucket_name:25} → Criado ({description})")
                except Exception as e:
                    erros.append((bucket_name, str(e)))
                    print(f"❌ {bucket_name:25} → Erro: {str(e)[:60]}")
        
        print(f"\n📊 Resumo:")
        print(f"   ✨ Criados: {len(criados)}")
        print(f"   ✅ Já existentes: {len(ja_existem)}")
        print(f"   ❌ Erros: {len(erros)}")
        print(f"   📦 Total: {len(buckets_config)}")
        
        if criados:
            print(f"\n✨ Buckets criados com sucesso:")
            for b in criados:
                print(f"   • {b}")
        
        if erros:
            print(f"\n❌ Erros ao criar buckets:")
            for b, err in erros:
                print(f"   • {b}: {err}")
        
        if len(criados) + len(ja_existem) == len(buckets_config):
            print(f"\n✓ Todos os buckets estão prontos!\n")
            return True
        else:
            print(f"\n⚠️  Alguns buckets ainda precisam ser criados manualmente\n")
            return False
        
    except Exception as e:
        print(f"\n❌ Erro ao conectar ao Supabase: {e}\n")
        return False


if __name__ == '__main__':
    success = criar_buckets()
    sys.exit(0 if success else 1)
