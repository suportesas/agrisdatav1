#!/usr/bin/env python
"""
Script para criar o Super Admin do SAAS (versão não-interativa)
Cria um Super Admin com dados padrão

Uso:
    cd c:\erp_agricola
    python criar_superadmin_rapido.py
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from django.contrib.auth import get_user_model

Usuario = get_user_model()


def main():
    print("\n" + "="*70)
    print("CRIAR SUPER ADMIN DO SAAS")
    print("="*70 + "\n")
    
    # Dados padrão
    username = 'admin'
    email = 'admin@erpseries.com.br'
    senha = 'AdminERP@2026'
    nome_completo = 'Proprietário Agrisdata'
    
    # Checagem
    if Usuario.objects.filter(username=username).exists():
        usuario_existente = Usuario.objects.get(username=username)
        print(f"⚠️  Usuário '{username}' já existe!")
        print(f"   Email: {usuario_existente.email}")
        print(f"   Superuser: {usuario_existente.is_superuser}")
        print("\nNenhuma alteração foi feita\n")
        return
    
    # Separar nome
    partes = nome_completo.split(" ", 1) if nome_completo else ["Admin"]
    first_name = partes[0]
    last_name = partes[1] if len(partes) > 1 else ""
    
    # Criar Super Admin
    usuario = Usuario.objects.create_superuser(
        username=username,
        email=email,
        password=senha,
        first_name=first_name,
        last_name=last_name
    )
    
    # Garantir que não tem empresa vinculada
    usuario.empresa = None
    usuario.tipo = 'SUPERADMIN'
    usuario.save()
    
    # Exibir resultado
    print("✅ SUPER ADMIN CRIADO COM SUCESSO!\n")
    print("="*70)
    print("DADOS DE ACESSO:")
    print("="*70)
    print(f"Username:    {usuario.username}")
    print(f"Email:       {usuario.email}")
    print(f"Senha:       {senha}")
    print(f"Nome:        {usuario.get_full_name()}")
    print(f"Tipo:        {usuario.tipo}")
    print(f"Acesso:      GLOBAL (Super Admin)")
    print("="*70)
    print("\n🔗 LINKS DE ACESSO:")
    print("   Admin: http://127.0.0.1:8000/admin/")
    print("   Login: http://127.0.0.1:8000/login/")
    print("\n💡 PRÓXIMAS AÇÕES:")
    print("   1. Fazer login com admin / AdminERP@2026")
    print("   2. Criar outras empresas via admin")
    print("   3. Criar usuários específicos por empresa")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()
