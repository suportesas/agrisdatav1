#!/usr/bin/env python
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from faturamento.models import ConhecimentoTransporte, ConfiguracaoFiscal
from faturamento.services.integranotas import IntegranNotasClient

ct = ConhecimentoTransporte.objects.get(pk=12)
empresa = ct.empresa

print(f"=== Consultando CT-e {ct.numero}/{ct.serie} ===")
print(f"Chave: {ct.chave_acesso}")
print(f"Status BD: {ct.status}")

try:
    config = empresa.configuracao_fiscal
    client = IntegranNotasClient(token=config.get_token(), ambiente=config.ambiente_nfe)
    
    print(f"\n[API] Consultando...")
    resultado = client.consultar_cte(ct.chave_acesso)
    
    print(f"Status API: {resultado.get('status')}")
    print(f"Protocolo: {resultado.get('protocolo')}")
    print(f"Motivo Rejeição: {resultado.get('motivo_rejeicao', 'N/A')}")
    print(f"Pode corrigir (CC-e)? {resultado.get('pode_fazer_cartacorrecao', 'N/A')}")
    
except Exception as e:
    print(f"ERRO: {e}")
