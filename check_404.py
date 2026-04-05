#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.test import Client, override_settings

with override_settings(ALLOWED_HOSTS=['*']):
    c = Client()
    r = c.get('/pagina-inexistente/', HTTP_HOST='127.0.0.1:8000')
    content = r.content.decode()
    
    # Verificar se contém elementos esperados
    checks = {
        'Contém "404"': '404' in content,
        'Contém "error-code"': 'error-code' in content,
        'Contém "Nexsafra"': 'Nexsafra' in content or 'NEXSAFRA' in content,
        'Contém "não encontrada"': 'não encontrada' in content,
        'Contém "btn-primary"': 'btn-primary' in content,
    }
    
    print("Verificações da página 404:")
    for check, result in checks.items():
        status = "✓" if result else "✗"
        print(f"  {status} {check}: {result}")
    
    print(f"\nStatus HTTP: {r.status_code}")
    print(f"Content-Type: {r.get('Content-Type')}")
    print(f"Tamanho: {len(content)} bytes")
    print(f"\nPrimeiros 300 caracteres:\n{content[:300]}")
