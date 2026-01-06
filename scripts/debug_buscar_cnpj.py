from django.test import Client
from unittest.mock import Mock
import django
django.setup()
from usuarios.models import Usuario
from empresas.models import Empresa
from unittest.mock import patch

# create user + empresa
emp = Empresa.objects.create(nome='Debug Emp')
user = Usuario.objects.create_user(username='debugu', password='pass')
user.empresa = emp
user.save()

client = Client()
client.force_login(user)

# Mock requests.get inside cadastros.views
with patch('cadastros.views.requests.get') as mock_get:
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        'status': 'OK',
        'nome': 'Empresa Debug LTDA',
        'fantasia': 'Debug Fantasia',
        'cnpj': '00000000000100',
        'telefone': '11223344',
        'email': 'contato@debug.com',
        'logradouro': 'Av Debug',
        'numero': '123',
        'complemento': '',
        'bairro': 'Centro',
        'municipio': 'Cidade Debug',
        'uf': 'SP',
        'cep': '01001-000'
    }
    mock_get.return_value = mock_resp

    resp = client.post('/cadastros/api/buscar-cnpj/', {'cnpj': '00.000.000/0001-00'})
    print('status', resp.status_code)
    print('json', resp.json())
