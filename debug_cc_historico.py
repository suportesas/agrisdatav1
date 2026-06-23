#!/usr/bin/env python
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from faturamento.models import CartaCorrecaoCTe
import json

cartas = CartaCorrecaoCTe.objects.all()
print(f"Total de CC-e no banco: {cartas.count()}")
print()

for carta in cartas:
    print(f"CC-e #{carta.sequencia} - CT-e {carta.cte.numero}/{carta.cte.serie}")
    print(f"  Protocolo: {carta.protocolo}")
    print(f"  Criado: {carta.criado_em}")
    print(f"  Correção (raw): {carta.correcao[:100] if carta.correcao else 'VAZIO'}")
    if carta.correcao:
        try:
            corr_obj = json.loads(carta.correcao)
            print(f"  Correção (parsed): {json.dumps(corr_obj, indent=4)}")
        except:
            print(f"  Não é JSON válido")
    print()
