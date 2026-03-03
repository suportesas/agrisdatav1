import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from usuarios.models import Usuario
from django.test import Client
import json

user = Usuario.objects.filter(empresa__isnull=False).first()
if user:
    print(f"User: {user}")
    print(f"Company: {user.empresa}")
    
    client = Client()
    client.force_login(user)
    response = client.get('/compras/api/empresa/unidades/')
    print(f"Status: {response.status_code}")
    
    data = response.json()
    print(json.dumps(data, indent=2, ensure_ascii=False))
