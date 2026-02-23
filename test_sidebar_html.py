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

# Extract just the sidebar section
content = response.content.decode()

# Find sidebar - look for the opening div and keep going
start_idx = content.find('<div class="sidebar-modern"')

if start_idx != -1:
    # Find the closing </nav> inside the sidebar
    nav_end = content.find('</nav>', start_idx)
    sidebar_close = content.find('</div>\n  <!-- Overlay', nav_end)  # Find the sidebar closing div
    
    if sidebar_close == -1:
        sidebar_close = content.find('</div>', nav_end) + len('</div>')
    
    sidebar_html = content[start_idx:sidebar_close]
    
    # Save to file for inspection
    with open('sidebar_rendered.html', 'w', encoding='utf-8') as f:
        f.write(sidebar_html)
    
    print(f"✅ Sidebar HTML saved to sidebar_rendered.html ({len(sidebar_html)} characters)")
    print("\n🔍 Procurando por 'Dashboard Executivo':\n")
    
    if 'Dashboard Executivo' in sidebar_html:
        print("✅ ENCONTRADO no HTML renderizado!")
        idx = sidebar_html.find('Dashboard Executivo')
        context = sidebar_html[max(0, idx-300):idx+400]
        print("\nContexto:\n")
        print(context)
    else:
        print("❌ Dashboard Executivo NÃO encontrado")
        
        if 'GESTÃO DO SISTEMA' in sidebar_html:
            print("✅ Mas 'GESTÃO DO SISTEMA' foi encontrado")
            idx = sidebar_html.find('GESTÃO DO SISTEMA')
            print(f"\nPróximos 1000 caracteres:\n")
            print(sidebar_html[idx:idx+1000])
        else:
            print("❌ 'GESTÃO DO SISTEMA' também não encontrado")
            
            if 'is_superuser' in sidebar_html:
                print("⚠️  Mas encontrei 'is_superuser' no HTML")
            
            # Show the menu structure
            if 'nav-section' in sidebar_html:
                print("\n✅ Encontradas seções de menu:")
                parts = sidebar_html.split('nav-section')
                for i, part in enumerate(parts[1:], 1):
                    section = part[part.find('>')+1:part.find('</span>')]
                    if section.strip():
                        print(f"   {i}. {section.strip()}")
            else:
                print("\n❌ Nenhuma seção de menu encontrada")
                print("\nPrimeiros 3000 caracteres:\n")
                print(sidebar_html[:3000])
else:
    print("❌ Sidebar não encontrado no HTML")
