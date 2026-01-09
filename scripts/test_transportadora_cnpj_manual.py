from django.test import Client
from django.contrib.auth import get_user_model
from empresas.models import Empresa
from django.urls import reverse
User = get_user_model()

u, created = User.objects.get_or_create(username='autotest')
if created:
    u.set_password('pass')
    u.save()
empresa, _ = Empresa.objects.get_or_create(nome='Empresa Auto')
u.empresa = empresa
u.save()

c = Client()
if not c.login(username='autotest', password='pass'):
    print('LOGIN FAILED')

url = reverse('cadastros:buscar_cnpj')
# Try GET
r_get = c.get(url + '?cnpj=00.000.000/0001-00', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
print('GET status:', r_get.status_code)
print('GET body:', r_get.content.decode('utf-8'))
# Try POST
r_post = c.post(url, {'cnpj': '00.000.000/0001-00'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
print('POST status:', r_post.status_code)
print('POST body:', r_post.content.decode('utf-8'))
