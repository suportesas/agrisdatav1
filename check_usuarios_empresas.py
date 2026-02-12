import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.insert(0, '.')
django.setup()

from usuarios.models import Usuario
from cadastros.models import Cliente
from empresas.models import Empresa

print("📋 VERIFICAÇÃO DE USUÁRIOS E SUAS EMPRESAS\n")

usuarios = Usuario.objects.all()
for user in usuarios:
    print(f"\n{'='*60}")
    print(f"Usuário: {user.username}")
    print(f"Email: {user.email}")
    print(f"Empresa: {user.empresa}")
    
    if user.empresa:
        # Contar clientes desta empresa
        clientes = Cliente.objects.filter(empresa=user.empresa)
        print(f"Clientes na empresa: {clientes.count()}")
        
        # Mostrar clientes com prazos salvos
        clientes_com_prazo = clientes.filter(prazo_pagamento__isnull=False)
        if clientes_com_prazo.exists():
            print(f"  ✓ Clientes com prazos ({clientes_com_prazo.count()}):")
            for c in clientes_com_prazo[:3]:
                print(f"    - ID {c.id}: {c.razao_social} (Prazo: {c.prazo_pagamento} dias)")
        else:
            print(f"  ✗ Nenhum cliente com prazo salvo")

print(f"\n✅ Análise concluída")
