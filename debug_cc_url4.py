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

# Teste 9: manifesta endpoint com código 6 (carta de correção)
print("=== TESTE 9: POST /cte/manifesta com código 6 (CC-e) ===")
url9 = f'{BASE_URL}/cte/manifesta'
payload9 = {
    'chave': ct.chave_acesso,
    'codigo': '6',  # Código para carta de correção
    'descricao': 'Teste de CC-e via manifesta'
}
try:
    resp = requests.post(url9, json=payload9, headers=headers, timeout=10)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.json()}")
except Exception as e:
    print(f"Erro: {e}")
print()

# Teste 10: manifesta endpoint com código 7 (desacordo, para comparação)
print("=== TESTE 10: POST /cte/manifesta com código 7 (DESACORDO) ===")
url10 = f'{BASE_URL}/cte/manifesta'
payload10 = {
    'chave': ct.chave_acesso,
    'codigo': '7',
    'descricao': 'Teste'
}
try:
    resp = requests.post(url10, json=payload10, headers=headers, timeout=10)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.json()}")
except Exception as e:
    print(f"Erro: {e}")
print()

# Teste 11: /cte/carta (sem correcao)
print("=== TESTE 11: POST /cte/carta ===")
url11 = f'{BASE_URL}/cte/carta'
payload11 = {
    'chave': ct.chave_acesso,
    'correcoes': [
        {
            'grupo_corrigido': 'infadic',
            'campo_corrigido': 'obs',
            'valor_corrigido': 'Teste'
        }
    ]
}
try:
    resp = requests.post(url11, json=payload11, headers=headers, timeout=10)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.json()}")
except Exception as e:
    print(f"Erro: {e}")
