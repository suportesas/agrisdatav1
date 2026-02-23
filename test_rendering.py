#!/usr/bin/env python
import os
import django
from django.test import Client

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from usuarios.models import Usuario

# Get admin user
admin_user = Usuario.objects.get(username='admin')

# Create test client and login
client = Client()
client.force_login(admin_user)

# Request dashboard page
response = client.get('/dashboard/')

# Check if rendered HTML contains Dashboard Executivo
if 'Dashboard Executivo' in response.content.decode():
    print("✅ 'Dashboard Executivo' ENCONTRADO no HTML renderizado!")
    print("\nContexto (50 caracteres ao redor):")
    content = response.content.decode()
    idx = content.find('Dashboard Executivo')
    print(content[max(0, idx-100):idx+150])
else:
    print("❌ 'Dashboard Executivo' NÃO encontrado no HTML!")
    print("\nVerificando condição {% if user.is_superuser %}:")
    print(f"   - user.is_superuser = {admin_user.is_superuser}")
    
    # Look for GESTÃO DO SISTEMA instead
    if 'GESTÃO DO SISTEMA' in response.content.decode():
        print("✅ 'GESTÃO DO SISTEMA' encontrado")
    else:
        print("❌ 'GESTÃO DO SISTEMA' NÃO encontrado")
