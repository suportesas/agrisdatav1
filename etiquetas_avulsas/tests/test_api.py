import json

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from empresas.models import APIKey, Empresa, Plano
from etiquetas_avulsas.models import LoteEtiquetaAvulsa

FLAGS_ON = {'ETIQUETA_AVULSA_API': True}


class EtiquetaAvulsaAPITests(TestCase):
    def setUp(self):
        plano = Plano.objects.create(codigo='PEQUENO', nome='Pequeno', valor_mensal=1)
        self.empresa = Empresa.objects.create(nome='Empresa Teste', plano=plano)
        self.outra_empresa = Empresa.objects.create(nome='Outra Empresa', plano=plano)
        self.api_key, self.raw_key = APIKey.gerar(self.empresa, 'Integração Teste')
        self.outra_api_key, self.outra_raw_key = APIKey.gerar(self.outra_empresa, 'Outra Integração')
        self.client = Client()
        self.list_url = reverse('etiquetas_avulsas_api:lote-list')

    def _payload(self, total_pallets=4):
        return {
            'fazenda_texto': 'Agricola Salutaris',
            'cliente_texto': '4 Fruit Company BV',
            'produto_texto': 'Melon',
            'variedade': 'Goldex',
            'caixas_por_pallet': 98,
            'total_pallets': total_pallets,
        }

    @override_settings(FEATURE_FLAGS=FLAGS_ON)
    def test_create_lote_com_chave_valida_retorna_etiquetas(self):
        resp = self.client.post(
            self.list_url, data=json.dumps(self._payload(total_pallets=5)),
            content_type='application/json', HTTP_X_API_KEY=self.raw_key,
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        data = resp.json()
        self.assertEqual(len(data['etiquetas']), 5)
        self.assertIn('numero_lote', data)
        self.assertIn('pdf_url', data)

        self.api_key.refresh_from_db()
        self.assertEqual(self.api_key.usage_count, 1)

    @override_settings(FEATURE_FLAGS=FLAGS_ON)
    def test_create_sem_chave_retorna_401_ou_403(self):
        resp = self.client.post(
            self.list_url, data=json.dumps(self._payload()), content_type='application/json',
        )
        self.assertIn(resp.status_code, (401, 403))

    @override_settings(FEATURE_FLAGS=FLAGS_ON)
    def test_create_com_chave_invalida_retorna_401(self):
        resp = self.client.post(
            self.list_url, data=json.dumps(self._payload()), content_type='application/json',
            HTTP_X_API_KEY='chave-invalida-qualquer',
        )
        self.assertEqual(resp.status_code, 401)

    @override_settings(FEATURE_FLAGS=FLAGS_ON)
    def test_isolamento_entre_empresas(self):
        self.client.post(
            self.list_url, data=json.dumps(self._payload()), content_type='application/json',
            HTTP_X_API_KEY=self.raw_key,
        )
        resp = self.client.get(self.list_url, HTTP_X_API_KEY=self.outra_raw_key)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()['results']), 0)

    @override_settings(FEATURE_FLAGS=FLAGS_ON)
    def test_pdf_endpoint_retorna_pdf(self):
        create_resp = self.client.post(
            self.list_url, data=json.dumps(self._payload(total_pallets=2)),
            content_type='application/json', HTTP_X_API_KEY=self.raw_key,
        )
        lote_id = create_resp.json()['id']
        pdf_url = reverse('etiquetas_avulsas_api:lote-pdf', args=[lote_id])
        resp = self.client.get(pdf_url, HTTP_X_API_KEY=self.raw_key)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')

    def test_feature_flag_desligada_bloqueia_api(self):
        # FEATURE_FLAGS padrão (sem override) mantém ETIQUETA_AVULSA_API desligada.
        resp = self.client.post(
            self.list_url, data=json.dumps(self._payload()), content_type='application/json',
            HTTP_X_API_KEY=self.raw_key,
        )
        self.assertEqual(resp.status_code, 403)
