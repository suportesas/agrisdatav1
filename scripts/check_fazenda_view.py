import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','core.settings')
import django
django.setup()
from django.test import Client
from empresas.models import Empresa
from cadastros.models import Fazenda

emp = Empresa.objects.create(nome='C1')
f = Fazenda.objects.create(empresa=emp, nome='F1', cnpj_cpf='11.111.111/0001-11', area_total=1)
client = Client()
resp = client.get(f'/cadastros/fazendas/{f.pk}/')
print('status_code', resp.status_code)
print('contains FieldError text?', 'FieldError' in resp.content.decode(errors='ignore'))
print('response length', len(resp.content))
