from django import setup
setup()
from django.test.client import RequestFactory
from django.http import QueryDict
from unittest.mock import Mock
from cadastros.forms import EnderecoClienteForm

# Mock requests.get to return a ViaCEP-like response
mock_resp = Mock()
mock_resp.status_code = 200
mock_resp.json.return_value = {
    'cep': '01001-000',
    'logradouro': 'Praça da Sé',
    'complemento': 'lado ímpar',
    'bairro': 'Sé',
    'localidade': 'São Paulo',
    'uf': 'SP'
}

class DummyRequests:
    def get(self, url, timeout=5):
        print('Mock requests.get called with', url)
        return mock_resp

import sys
sys.modules['requests'] = DummyRequests()

# Prepare POST data with empty UF
post = QueryDict('', mutable=True)
post.update({
    'tipo': 'PRINCIPAL',
    'cep': '01001-000',
    'logradouro': '',
    'numero': '',
    'complemento': '',
    'bairro': '',
    'cidade': '',
    'uf': '',
    'pais': 'Brasil',
    'padrao': 'on'
})

form = EnderecoClienteForm(post)
print('Initial data uf:', form.data.get('uf'))
print('is_bound:', form.is_bound)
print('running is_valid...')
valid = form.is_valid()
print('is_valid:', valid)
print('errors:', form.errors)
print('cleaned_data:', getattr(form, 'cleaned_data', None))

# Also inspect at different points by calling clean_cep directly
form2 = EnderecoClienteForm(post)
cep_clean = form2.clean_cep()
print('after clean_cep, data uf:', form2.data.get('uf'))
print('clean_cep returned:', cep_clean)
