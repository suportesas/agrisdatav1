"""
Script para popular tipos padrão de produtos para todas as empresas
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from produtos.models import TipoProduto
from empresas.models import Empresa

tipos_padrao = [
    {'codigo': 'REVENDA', 'nome': 'Revenda'},
    {'codigo': 'CONSUMO', 'nome': 'Consumo'},
    {'codigo': 'MATERIA_PRIMA', 'nome': 'Matéria Prima'},
    {'codigo': 'PRODUTO_ACABADO', 'nome': 'Produto Acabado'},
]

empresas = Empresa.objects.all()
print(f"Populando tipos para {empresas.count()} empresa(s)...")

for empresa in empresas:
    print(f"\n- Empresa: {empresa.nome}")
    for tipo_data in tipos_padrao:
        tipo, created = TipoProduto.objects.get_or_create(
            empresa=empresa,
            codigo=tipo_data['codigo'],
            defaults={'nome': tipo_data['nome'], 'ativo': True}
        )
        status = "criado" if created else "já existe"
        print(f"  * {tipo.nome} ({tipo.codigo}): {status}")

print("\n✅ Tipos padrão populados com sucesso!")
