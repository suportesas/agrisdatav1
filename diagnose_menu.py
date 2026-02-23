#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import django
from django.test import Client
import re

# Force UTF-8 output on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

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
content = response.content.decode()

# Extract sidebar
start_idx = content.find('<div class="sidebar-modern"')
nav_end = content.find('</nav>', start_idx)
sidebar_close = content.find('</div>\n  <!-- Overlay', nav_end)
if sidebar_close == -1:
    sidebar_close = content.find('</div>', nav_end) + len('</div>')

sidebar_html = content[start_idx:sidebar_close]

print("ANALISE DO SIDEBAR RENDERIZADO:\n")
print(f"Total de caracteres: {len(sidebar_html)}\n")

# Count nav-section elements
nav_sections = re.findall(r'<li class="nav-section">\s*<span>(.*?)</span>', sidebar_html)
print(f"Secoes de menu encontradas: {len(nav_sections)}")
for i, section in enumerate(nav_sections, 1):
    print(f"   {i}. {section.strip()}")

print("\n" + "="*80 + "\n")

# Check for specific menu items
menu_items = [
    ('Dashboard', 'Dashboard'),
    ('GESTAO DO SISTEMA', 'Superuser section'),
    ('Empresas', 'Empresas'),
    ('Grupos Corporativos', 'Grupos'),
    ('Dashboard Executivo', 'Dashboard Executivo'),
    ('KPIs Principais', 'KPIs'),
    ('Consumo de Recursos', 'Consumo'),
    ('GESTAO DA EMPRESA', 'Empresa section'),
    ('Configuracoes', 'Configuracoes'),
    ('Minha Empresa', 'Minha Empresa'),
]

print("ITENS DE MENU ENCONTRADOS:\n")
for item, label in menu_items:
    if item in sidebar_html:
        count = sidebar_html.count(item)
        print(f"OK {item:30} ({'x' + str(count) if count > 1 else ''})")
    else:
        print(f"NO {item:30} (nao encontrado)")

print("\n" + "="*80 + "\n")

# Check conditional sections
print("ANALISE DE CONDICIONAIS NO TEMPLATE:\n")

if 'GESTAO DO SISTEMA' in sidebar_html and 'GESTAO DA EMPRESA' in sidebar_html:
    print("ATENCAO: PROBLEMA DETECTADO!")
    print("   Ambas as secoes estao renderizadas:")
    print("   OK GESTAO DO SISTEMA (Superuser)")
    print("   OK GESTAO DA EMPRESA (Empresa)")
    print("\n   Isso significa que os condicionais nao estao funcionando corretamente.")
    print("   O usuario.empresa deveria ser None para um superuser!")
    
    idx_sistema = sidebar_html.find('GESTAO DO SISTEMA')
    idx_empresa = sidebar_html.find('GESTAO DA EMPRESA')
    
    if idx_sistema < idx_empresa:
        print("\n   Ordem: GESTAO DO SISTEMA aparece antes de GESTAO DA EMPRESA [OK]")
    
elif 'GESTAO DO SISTEMA' in sidebar_html:
    print("CORRETO!")
    print("   Apenas 'GESTAO DO SISTEMA' foi renderizada (Superuser)")
    print("   'GESTAO DA EMPRESA' nao aparece [OK]")
    
elif 'GESTAO DA EMPRESA' in sidebar_html:
    print("ATENCAO: Apenas 'GESTAO DA EMPRESA' renderizada")
    print("   'GESTAO DO SISTEMA' nao aparece")
    print("   Isso significa que user.is_superuser = False!")
    
else:
    print("ERRO: NENHUMA secao de gestao foi renderizada!")

# Final check
print("\n" + "="*80)
print("\nVERIFICACAO DO USUARIO:\n")
print(f"   username: {admin_user.username}")
print(f"   is_superuser: {admin_user.is_superuser}")
print(f"   is_staff: {admin_user.is_staff}")
print(f"   empresa: {admin_user.empresa}")
print(f"   tipo: {admin_user.tipo}")
