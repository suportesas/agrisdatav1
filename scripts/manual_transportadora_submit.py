from django.test import Client
from django.contrib.auth import get_user_model
from empresas.models import Empresa
from django.urls import reverse
from cadastros.models import Transportadora

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

url = reverse('cadastros:transportadora_create')
# Try submit without inscricao_estadual but with contribuinte_icms
data = {'razao_social':'T Manual','cnpj':'11.111.111/1111-44','contato_principal_email':'t@t.com','contribuinte_icms':'on'}
r = c.post(url, data, follow=True)
print('POST1 status:', r.status_code)
print('POST1 has errors:', 'errorlist' in r.content.decode('utf-8'))
print('POST1 snippet:', r.content.decode('utf-8')[:500])

# Validate form server-side to show errors
from cadastros.forms import TransportadoraForm
f = TransportadoraForm(data=data, empresa=empresa)
print('Form valid:', f.is_valid())
print('Form errors:', f.errors)

# Now submit with inscricao_estadual
data2 = {'razao_social':'T Manual 2','cnpj':'11.111.111/1111-45','contato_principal_email':'t2@t.com','contribuinte_icms':'on','inscricao_estadual':'12345'}
r2 = c.post(url, data2, follow=True)
print('POST2 status:', r2.status_code)
print('redirect chain:', r2.redirect_chain)

# Verify saved object and indicador_ie
t = Transportadora.objects.filter(razao_social='T Manual 2').first()
print('T exists:', bool(t))
if t:
    print('t.indicador_ie:', t.indicador_ie, 't.contribuinte_icms:', t.contribuinte_icms)

# Create with tipo_conta and tipo_pix and rntc
data3 = {'razao_social':'T Manual 3','cnpj':'11.111.111/1111-46','contato_principal_email':'t3@t.com','conta':'123456','tipo_conta':'CC','tipo_pix':'CPF','pix_key':'123','rntc':'RN-10'}
r3 = c.post(url, data3, follow=True)
print('POST3 status:', r3.status_code)
t3 = Transportadora.objects.filter(razao_social='T Manual 3').first()
print('T3 exists:', bool(t3))
if t3:
    print('t3.tipo_conta, tipo_pix, rntc:', t3.tipo_conta, t3.tipo_pix, t3.rntc)
