from django.test import Client
from empresas.models import Plano, Empresa
from django.contrib.auth import get_user_model
User = get_user_model()
plano = Plano.objects.create(codigo='PEQ', nome='P', valor_mensal=1)
empresa = Empresa.objects.create(nome='E', plano=plano)
user = User.objects.create_user(username='u', password='pass')
user.empresa = empresa
user.save()
c = Client()
logged = c.login(username='u', password='pass')
print('logged', logged)
resp = c.post('/cadastros/fornecedores/novo/', {'nome':'Novo Fornecedor','cnpj_cpf':'22.222.222/2222-22','telefone':'111'}, follow=True)
print('status', resp.status_code)
print('redirected to', resp.redirect_chain)
print('contains novo fornecedor?', b'Novo Fornecedor' in resp.content)
if resp.status_code == 200:
    s = resp.content.decode('utf-8')
    # crude error detection
    print('errorlist present?', 'errorlist' in s)
    print('is-invalid present?', 'is-invalid' in s)
    print('alert present?', 'alert' in s)
