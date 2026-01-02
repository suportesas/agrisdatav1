import os
import sys
import django
# Ensure project root is on sys.path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.test import Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from empresas.models import Plano, Empresa
from usuarios.models import Usuario
from cadastros.models import Cliente

# Setup data
plano = Plano.objects.create(codigo='PEQ', nome='P', valor_mensal=1)
empresa = Empresa.objects.create(nome='E', plano=plano)
user = Usuario.objects.create_user(username='u', password='pass')
user.empresa = empresa
user.save()
client = Client()
client.login(username='u', password='pass')
c = Cliente.objects.create(empresa=empresa, razao_social='C', cnpj_cpf='12345678901')

url = reverse('cadastros:cliente_documento_create_ajax', args=[c.pk])
f = SimpleUploadedFile('doc.pdf', b'PDFDATA', content_type='application/pdf')
data = {'tipo':'CONTRATO','titulo':'T','data_emissao':'2025-01-01','data_validade':'2025-12-31','arquivo': f}
resp = client.post(url, data)
print('status:', resp.status_code)
try:
    print('json:', resp.json())
except Exception as e:
    print('content:', resp.content.decode('utf-8'))

