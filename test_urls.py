#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.urls import reverse
from django.template import Template, Context
from usuarios.models import Usuario

# Get admin user
admin_user = Usuario.objects.get(username='admin')

# Test URLs
urls_to_test = [
    ('metricas:dashboard_executivo', None),
    ('metricas:consumo_lista', None),
    ('metricas:alertas_lista', None),
]

print("\n🔍 Testando URLs da app metricas:\n")

for url_name, kwargs in urls_to_test:
    try:
        url = reverse(url_name, kwargs=kwargs or {})
        print(f"✅ {url_name:40} → {url}")
    except Exception as e:
        print(f"❌ {url_name:40} → ERRO: {e}")

# Test template rendering
print("\n\n🔍 Testando renderização do template:\n")

template_code = """
{% if user.is_superuser %}
  <li class="nav-item has-submenu">
    <a href="{{ dashboard_url }}" class="nav-link">
      <span>Dashboard Executivo</span>
    </a>
    <ul class="nav-submenu">
      <li><a href="{{ kpi_url }}">KPIs Principais</a></li>
      <li><a href="{{ consumo_url }}">Consumo de Recursos</a></li>
      <li><a href="{{ alertas_url }}">Alertas</a></li>
    </ul>
  </li>
{% else %}
  Não é superuser
{% endif %}
"""

context_data = {
    'user': admin_user,
    'dashboard_url': reverse('metricas:dashboard_executivo'),
    'kpi_url': reverse('metricas:dashboard_executivo'),
    'consumo_url': reverse('metricas:consumo_lista'),
    'alertas_url': reverse('metricas:alertas_lista'),
}

try:
    template = Template(template_code)
    rendered = template.render(Context(context_data))
    print("✅ Template renderizado com sucesso!")
    print("\nConteúdo:\n")
    print(rendered)
except Exception as e:
    print(f"❌ Erro ao renderizar template: {e}")
