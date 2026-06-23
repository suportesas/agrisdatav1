#!/usr/bin/env python
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from faturamento.models import ConhecimentoTransporte

ct = ConhecimentoTransporte.objects.get(pk=12)
print(f"ID: {ct.pk}")
print(f"Número: {ct.numero}/{ct.serie}")
print(f"Status: {ct.status}")
print(f"Chave: {ct.chave_acesso}")
print(f"Protocolo: {ct.protocolo}")
print(f"XML Retorno: {'SIM' if ct.xml_autorizacao else 'NÃO'}")
