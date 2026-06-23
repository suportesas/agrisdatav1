#!/usr/bin/env python
"""Testa chamada correta para CC-e - verifica documentação SDK"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

import requests
import json
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

print("=== Testa POST /cte/atualizacte (método alternativo) ===")
payload_alt = {
    'chave': ct.chave_acesso,
    'correcoes': [
        {
            'grupo_corrigido': 'infadic',
            'campo_corrigido': 'obs',
            'valor_corrigido': 'Teste CC-e'
        }
    ]
}
try:
    resp = requests.post(f'{BASE_URL}/cte/atualizacte', json=payload_alt, headers=headers, timeout=10)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.json()}")
except Exception as e:
    print(f"Erro: {e}")
