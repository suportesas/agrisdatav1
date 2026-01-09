from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from empresas.models import Empresa, Plano

User = get_user_model()

# Setup
u, _ = User.objects.get_or_create(username='autotest')
if not u.password:
    u.set_password('pass')
    u.save()
pl, _ = Plano.objects.get_or_create(codigo='PEQUENO', nome='Pequeno', valor_mensal=1)
emp, _ = Empresa.objects.get_or_create(nome='Empresa Auto', plano=pl)

u.empresa = emp
u.save()

c = Client()
c.login(username='autotest', password='pass')

r = c.get(reverse('empresas:minha_empresa'))
print('status', r.status_code)
print('contains plano nome', 'Pequeno' in r.content.decode('utf-8'))
print('contains consumo table', 'Consumo do Plano' in r.content.decode('utf-8'))
print('snippet:', r.content.decode('utf-8')[:800])
