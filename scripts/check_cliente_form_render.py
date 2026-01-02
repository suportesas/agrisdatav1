import os
import sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
if BASE_DIR not in sys.path: sys.path.insert(0, BASE_DIR)
import django
django.setup()

from django.test import Client
from usuarios.models import Usuario
from empresas.models import Empresa, Plano

c = Client()
plano = Plano.objects.create(codigo='PEQ', nome='P', valor_mensal=1)
emp = Empresa.objects.create(nome='Empresa UI', plano=plano)
user = Usuario.objects.create_user(username='ui', password='ui')
user.empresa = emp
user.save()
logged_in = c.login(username='ui', password='ui')
print('logged in', logged_in)
resp = c.get('/cadastros/clientes/novo/')
print('status', resp.status_code)
content = resp.content.decode('utf-8')
checks = ['id="buscarCNPJ"', 'id="cnpjLoadingModal"', 'id="cnpjFeedback"', 'data-auto="true"', 'name="vendedor_responsavel"', 'class="section-header"']
for chk in checks:
    print(chk, 'in page:', chk in content)
