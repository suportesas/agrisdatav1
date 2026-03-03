"""
Setup rápido de tipos de divergência
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from compras.models import TipoDivergencia
from empresas.models import Empresa

# Tipos padrão
TIPOS = [
    ('DANO_EXT', 'Danos Externos', 'LEVE'),
    ('LACRE_ROMPIDO', 'Lacre Rompido', 'GRAVE'),
    ('SUJEIRA', 'Sujeira / Contaminação', 'MEDIO'),
    ('VENCIDO', 'Produto Vencido', 'GRAVE'),
    ('QTD_DIFERENTE', 'Quantidade Diferente', 'MEDIO'),
    ('PRODUTO_ERRADO', 'Produto Errado', 'GRAVE'),
]

# Para cada empresa
for empresa in Empresa.objects.filter(ativa=True):
    print(f"\n📦 {empresa.nome}:")
    
    for codigo, nome, severidade in TIPOS:
        tipo, criado = TipoDivergencia.objects.get_or_create(
            empresa=empresa,
            codigo=codigo,
            defaults={
                'nome': nome,
                'severidade': severidade,
                'ativo': True,
            }
        )
        
        if criado:
            print(f"  ✅ {nome}")
        else:
            print(f"  ℹ️ {nome} (já existe)")

print("\n✨ Concluído!")
