#!/usr/bin/env python
import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.test import Client, override_settings

# Teste simples da página 404
print("Testando página 404...\n")

# Teste 1: URL que não existe
with override_settings(ALLOWED_HOSTS=['*']):
    c = Client()
    response = c.get('/pagina-inexistente/', HTTP_HOST='127.0.0.1:8000')
    print(f"✓ GET /pagina-inexistente/")
    print(f"  Status: {response.status_code}")
    print(f"  Tem '404' no conteúdo: {'404' in response.content.decode()}")
    print(f"  Tem 'Página não encontrada' no conteúdo: {'Página não encontrada' in response.content.decode() or 'pagina-nao-encontrada' in response.content.decode()}")
    print()

# Teste 2: URLs conhecidas devem funcionar
with override_settings(ALLOWED_HOSTS=['*']):
    c = Client()
    response = c.get('/recursos/', HTTP_HOST='127.0.0.1:8000')
    print(f"✓ GET /recursos/")
    print(f"  Status: {response.status_code}")
    print()

# Teste 3: URL raiz
with override_settings(ALLOWED_HOSTS=['*']):
    c = Client()
    response = c.get('/', HTTP_HOST='127.0.0.1:8000')
    print(f"✓ GET /")
    print(f"  Status: {response.status_code}")

print("\n✓ Testes completados!")
