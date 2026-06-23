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

# Teste 6: GET /cte/carta-correcao
print("=== TESTE 6: GET /cte/carta-correcao ===")
url6 = f'{BASE_URL}/cte/carta-correcao'
try:
    resp = requests.get(url6, headers=headers, timeout=10)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.json()}")
except Exception as e:
    print(f"Erro: {e}")
print()

# Teste 7: POST with different payload structure (sem 'correcoes')
print("=== TESTE 7: POST /cte/carta-correcao com correcao simples ===")
url7 = f'{BASE_URL}/cte/carta-correcao'
payload7 = {
    'chave': ct.chave_acesso,
    'correcao': 'Teste simples'
}
try:
    resp = requests.post(url7, json=payload7, headers=headers, timeout=10)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.json()}")
except Exception as e:
    print(f"Erro: {e}")
print()

# Teste 8: Procurar por PATCH
print("=== TESTE 8: PATCH /cte/carta-correcao ===")
url8 = f'{BASE_URL}/cte/carta-correcao'
try:
    resp = requests.patch(url8, json={'chave': ct.chave_acesso, 'correcoes': []}, headers=headers, timeout=10)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.json()}")
except Exception as e:
    print(f"Erro: {e}")
