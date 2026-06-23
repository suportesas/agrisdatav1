#!/usr/bin/env python
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

import requests
from faturamento.models import ConhecimentoTransporte

ct = ConhecimentoTransporte.objects.get(pk=12)
empresa = ct.empresa
config = empresa.configuracao_fiscal

token = config.get_token()
headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json',
}

BASE_URL = 'https://hom-api.integranotas.com.br/v1'

# Teste 3: /cte/{chave}/correcao
print("=== TESTE 3: /cte/{chave}/correcao ===")
url3 = f'{BASE_URL}/cte/{ct.chave_acesso}/correcao'
payload = {
    'correcoes': [
        {
            'grupo_corrigido': 'infadic',
            'campo_corrigido': 'obs',
            'valor_corrigido': 'Teste de CC-e'
        }
    ]
}
try:
    resp = requests.post(url3, json=payload, headers=headers, timeout=10)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.json()}")
except Exception as e:
    print(f"Erro: {e}")
print()

# Teste 4: /cte-carta-correcao
print("=== TESTE 4: /cte-carta-correcao (sem slash) ===")
url4 = f'{BASE_URL}/cte-carta-correcao'
payload2 = {
    'chave': ct.chave_acesso,
    'correcoes': [
        {
            'grupo_corrigido': 'infadic',
            'campo_corrigido': 'obs',
            'valor_corrigido': 'Teste de CC-e'
        }
    ]
}
try:
    resp = requests.post(url4, json=payload2, headers=headers, timeout=10)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.json()}")
except Exception as e:
    print(f"Erro: {e}")
print()

# Teste 5: Com PUT
print("=== TESTE 5: PUT /cte/carta-correcao ===")
url5 = f'{BASE_URL}/cte/carta-correcao'
try:
    resp = requests.put(url5, json=payload2, headers=headers, timeout=10)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.json()}")
except Exception as e:
    print(f"Erro: {e}")
