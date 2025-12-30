import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()
from django.test import Client
from django.contrib.auth import get_user_model
from empresas.models import Empresa, Plano
from cadastros.models import Fazenda

# Setup data
pl = Plano.objects.create(codigo='PEQ2', nome='P2', valor_mensal=1)
empresa = Empresa.objects.create(nome='CheckCo', plano=pl)
User = get_user_model()
user = User.objects.create_user(username='checku', password='pass')
user.empresa = empresa
user.save()

fazenda = Fazenda.objects.create(empresa=empresa, nome='FCheck', cnpj_cpf='11.111.111/0001-11', area_total=10)

client = Client()
client.login(username='checku', password='pass')
resp = client.get(f'/cadastros/fazendas/{fazenda.pk}/documentos/novo/')
print('status_code', resp.status_code)
content = resp.content.decode('utf-8')
print('has label:', 'Número do Documento' in content)
print('has input name:', 'name="numero_documento"' in content)
print('snippet around label:')
idx = content.find('Número do Documento')
print(content[idx-100:idx+200])
