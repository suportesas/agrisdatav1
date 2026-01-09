from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from empresas.models import Empresa

User = get_user_model()

u, created = User.objects.get_or_create(username='autotest')
if created:
    u.set_password('pass')
    u.save()
empresa, _ = Empresa.objects.get_or_create(nome='Empresa Auto')
u.empresa = empresa
u.save()

c = Client()
c.login(username='autotest', password='pass')

r = c.get(reverse('cadastros:transportadora_create'))
s = r.content.decode('utf-8')
print('cidade count', s.count('id="id_cidade"'))
print('uf count', s.count('id="id_uf"'))
print('pais count', s.count('id="id_pais"'))
print('snippet around cidade:')
i = s.find('id="id_cidade"')
print(s[i-100:i+100])
