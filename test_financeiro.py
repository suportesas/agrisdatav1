#!/usr/bin/env python
"""
Script para testar o acesso ao módulo financeiro
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from usuarios.models import Usuario
from empresas.models import Empresa
from financeiro.models import ContaPagar

# Buscar um usuário
usuarios = Usuario.objects.filter(is_active=True).first()

if usuarios:
    print("=" * 70)
    print("TESTE DO MÓDULO FINANCEIRO")
    print("=" * 70)
    
    print(f"\n✅ Usuário encontrado: {usuarios.username}")
    print(f"   Email: {usuarios.email}")
    
    if usuarios.empresa:
        print(f"   Empresa (atributo correto): {usuarios.empresa.nome}")
        
        # Testar query de contas
        contas = ContaPagar.objects.filter(empresa=usuarios.empresa)
        print(f"\n   Contas a pagar nesta empresa: {contas.count()}")
        
        if contas.exists():
            for conta in contas[:3]:
                print(f"      - {conta.numero}: R$ {conta.valor_total}")
        else:
            print("      (Nenhuma conta registrada ainda)")
    else:
        print("   ⚠️  Usuário SEM empresa vinculada")
        print("       (Use um usuário com empresa para testar o financeiro)")
    
    print("\n" + "=" * 70)
    print("✅ Atributo 'empresa' funcionando corretamente!")
    print("=" * 70)
else:
    print("\n❌ Nenhum usuário ativo encontrado no sistema")
