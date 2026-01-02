import os
import sys
import django

# Ensure project root is on sys.path so Django settings can be imported
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.test import Client
from usuarios.models import Usuario
from empresas.models import Empresa
from cadastros.models import Fazenda, Cliente

c = Client()
# Create empresa and user
emp = Empresa.objects.create(nome='Empresa Script')
user = Usuario.objects.create_user(username='script', password='script')
user.empresa = emp
user.save()

# Login
logged_in = c.login(username='script', password='script')
print('Logged in:', logged_in)

# Create fazenda and cliente
faz = Fazenda.objects.create(empresa=emp, nome='Fazenda Script', cnpj_cpf='12345678000123', area_total=10)
cli = Cliente.objects.create(empresa=emp, razao_social='Cliente Script', cnpj_cpf='12345678901')

# Test fazenda detail
try:
    resp = c.get(f'/cadastros/fazendas/{faz.pk}/')
    print('Fazenda detail status:', resp.status_code)
except Exception as e:
    print('Fazenda detail error:', type(e).__name__, e)

# Test cliente detail
try:
    resp = c.get(f'/cadastros/clientes/{cli.pk}/')
    print('Cliente detail status:', resp.status_code)
except Exception as e:
    print('Cliente detail error:', type(e).__name__, e)
