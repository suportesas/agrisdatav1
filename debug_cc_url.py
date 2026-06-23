#!/usr/bin/env python
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

import requests
from faturamento.models import ConhecimentoTransporte, ConfiguracaoFiscal

ct = ConhecimentoTransporte.objects.get(pk=12)
empresa = ct.empresa
config = empresa.configuracao_fiscal

token = config.get_token()
headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json',
}

BASE_URL = 'https://hom-api.integranotas.com.br/v1'

# Teste 1: URL atual (errando 404)
print("=== TESTE 1: URL atual (com chave na URL) ===")
url1 = f'{BASE_URL}/cte/{ct.chave_acesso}/carta-correcao'
print(f"URL: {url1}")
print()

# Teste 2: Alternativa - chave no payload
print("=== TESTE 2: URL alternativa (chave no payload) ===")
url2 = f'{BASE_URL}/cte/carta-correcao'
payload = {
    'chave': ct.chave_acesso,
    'correcoes': [
        {
            'grupo_corrigido': 'infadic',
            'campo_corrigido': 'obs',
            'valor_corrigido': 'Teste de CC-e'
        }
    ]
}
print(f"URL: {url2}")
print(f"Payload: {payload}")

try:
    resp = requests.post(url2, json=payload, headers=headers, timeout=10)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.json()}")
except Exception as e:
    print(f"Erro: {e}")
