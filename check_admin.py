#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from usuarios.models import Usuario

try:
    user = Usuario.objects.get(username='admin')
    print(f"\n✅ Username: {user.username}")
    print(f"✅ is_superuser: {user.is_superuser}")
    print(f"✅ is_staff: {user.is_staff}")
    print(f"✅ empresa: {user.empresa}")
    print(f"✅ tipo: {user.tipo}\n")
    
    if user.is_superuser and user.empresa is None:
        print("✅ SUPERUSER CONFIGURADO CORRETAMENTE!")
    else:
        print("❌ PROBLEMA: Superuser não está configurado corretamente!")
        print("   - Deve ter is_superuser=True")
        print("   - Deve ter empresa=None")
except Usuario.DoesNotExist:
    print("❌ Usuário 'admin' não encontrado!")
