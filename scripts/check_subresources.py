import os
import sys
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
if BASE_DIR not in sys.path: sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

from django.test import Client
from usuarios.models import Usuario
from empresas.models import Empresa, Plano
from cadastros.models import Cliente
from django.core.files.uploadedfile import SimpleUploadedFile

c = Client()
plano = Plano.objects.create(codigo='PEQ', nome='P', valor_mensal=1)
emp = Empresa.objects.create(nome='Empresa Sub', plano=plano)
user = Usuario.objects.create_user(username='sub', password='pass')
user.empresa = emp
user.save()
logged = c.login(username='sub', password='pass')
print('logged in', logged)

# Create Cliente
resp = c.post('/cadastros/clientes/novo/', {'razao_social':'CliSub','cnpj_cpf':'99999999999999','tipo_pessoa':'PJ','tipo_cliente':'NACIONAL'})
print('create client status', resp.status_code)
client = Cliente.objects.get(razao_social='CliSub')
print('client pk', client.pk)

# Post contato
data_cont = {'nome':'Contato Teste', 'telefone':'7133334444', 'email':'contato@x.com', 'preferencial':'on'}
resp = c.post(f'/cadastros/clientes/{client.pk}/contatos/novo/', data_cont)
print('post contato', resp.status_code)
print('contatos count', client.contatos.count())

# Post conta
data_acc = {'banco':'Banco Teste', 'agencia':'0001', 'conta':'12345', 'conta_digito':'6', 'conta_principal':'on'}
resp = c.post(f'/cadastros/clientes/{client.pk}/contas/nova/', data_acc)
print('post conta', resp.status_code)
print('contas count', client.contas_bancarias.count())

# Post documento
content = b"PDFTEST"
f = SimpleUploadedFile('doc.pdf', content, content_type='application/pdf')
data_doc = {'tipo':'CONTRATO','titulo':'Contrato Teste','numero_documento':'ABC123','data_emissao':'2025-01-01','data_validade':'2030-01-01','gerar_alerta_vencimento':'on','dias_antecedencia_alerta':'30'}
resp = c.post(f'/cadastros/clientes/{client.pk}/documentos/novo/', data_doc, FILES={'arquivo': f})
print('post documento', resp.status_code)
print('docs count', client.documentos.count())
