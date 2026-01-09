import os, django, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE','core.settings')
django.setup()
from django.test import Client
from django.contrib.auth import get_user_model
from empresas.models import Empresa
from django.urls import reverse
User = get_user_model()
# create user and empresa
u, created = User.objects.get_or_create(username='autotest')
if created:
    u.set_password('pass')
    u.save()
empresa, _ = Empresa.objects.get_or_create(nome='Empresa Auto')
u.empresa = empresa
u.save()
print('User exists, empresa assigned')

c = Client()
if not c.login(username='autotest', password='pass'):
    print('LOGIN FAILED', file=sys.stderr); sys.exit(2)
print('Logged in')

url = reverse('cadastros:transportadora_create')
r = c.get(url)
print('GET create:', r.status_code)
content = r.content.decode('utf-8')
print('Contains id_cep:', 'id="id_cep"' in content)
print('Contains buscarCEPT:', 'buscarCEPT' in content)

cep_url = reverse('cadastros:buscar_cep')
print('buscar_cep URL:', cep_url)
r2 = c.get(cep_url, {'cep':'01001000'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
print('buscar_cep GET status:', r2.status_code)
print('buscar_cep content:', r2.content.decode('utf-8'))
