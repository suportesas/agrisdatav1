from django.core.management.base import BaseCommand
from django.test.client import RequestFactory
from django.http import QueryDict
from unittest.mock import Mock
from cadastros.forms import EnderecoClienteForm

class Command(BaseCommand):
    help = 'Debug EnderecoClienteForm CEP autofill behavior'

    def handle(self, *args, **options):
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
                self.stdout.write('Mock requests.get called with {}'.format(url))
                return mock_resp

        import sys
        sys.modules['requests'] = DummyRequests()

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
        self.stdout.write('Initial data uf: {}'.format(form.data.get('uf')))
        self.stdout.write('is_bound: {}'.format(form.is_bound))
        self.stdout.write('running is_valid...')
        valid = form.is_valid()
        self.stdout.write('is_valid: {}'.format(valid))
        self.stdout.write('errors: {}'.format(form.errors))
        self.stdout.write('cleaned_data: {}'.format(getattr(form, 'cleaned_data', None)))

        # Inspect clean_cep directly by setting cleaned_data to simulate field cleaning
        form2 = EnderecoClienteForm(post)
        form2.cleaned_data = {'cep': post.get('cep')}
        cep_clean = form2.clean_cep()
        self.stdout.write('after clean_cep, data uf: {}'.format(form2.data.get('uf')))
        self.stdout.write('clean_cep returned: {}'.format(cep_clean))
