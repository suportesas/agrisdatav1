import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from produtos.models import Categoria, SubCategoria

# Criar categorias
categorias_data = [
    {'codigo': 'FERT', 'nome': 'Fertilizante', 'descricao': 'Produtos para nutrição de plantas'},
    {'codigo': 'DEF', 'nome': 'Defensivo', 'descricao': 'Produtos para controle de pragas e doenças'},
    {'codigo': 'SEM', 'nome': 'Sementes', 'descricao': 'Sementes certificadas'},
]

categorias = {}
for cat_data in categorias_data:
    categoria, created = Categoria.objects.get_or_create(
        codigo=cat_data['codigo'],
        defaults={
            'nome': cat_data['nome'],
            'descricao': cat_data['descricao']
        }
    )
    categorias[cat_data['codigo']] = categoria
    print(f"{'Criada' if created else 'Já existe'}: Categoria {categoria.nome}")

# Criar subcategorias
subcategorias_data = [
    # Fertilizantes
    {'categoria': 'FERT', 'codigo': 'FERT-QUIM', 'nome': 'Químico', 'descricao': 'Fertilizantes químicos'},
    {'categoria': 'FERT', 'codigo': 'FERT-ORG', 'nome': 'Orgânico', 'descricao': 'Fertilizantes orgânicos'},
    {'categoria': 'FERT', 'codigo': 'FERT-FOL', 'nome': 'Foliar', 'descricao': 'Fertilizantes foliares'},
    {'categoria': 'FERT', 'codigo': 'FERT-MIN', 'nome': 'Mineral', 'descricao': 'Fertilizantes minerais'},
    
    # Defensivos
    {'categoria': 'DEF', 'codigo': 'DEF-HERB', 'nome': 'Herbicida', 'descricao': 'Controle de plantas daninhas'},
    {'categoria': 'DEF', 'codigo': 'DEF-INSET', 'nome': 'Inseticida', 'descricao': 'Controle de insetos'},
    {'categoria': 'DEF', 'codigo': 'DEF-FUNG', 'nome': 'Fungicida', 'descricao': 'Controle de fungos'},
    {'categoria': 'DEF', 'codigo': 'DEF-ACAR', 'nome': 'Acaricida', 'descricao': 'Controle de ácaros'},
    
    # Sementes
    {'categoria': 'SEM', 'codigo': 'SEM-SOJA', 'nome': 'Soja', 'descricao': 'Sementes de soja'},
    {'categoria': 'SEM', 'codigo': 'SEM-MILHO', 'nome': 'Milho', 'descricao': 'Sementes de milho'},
    {'categoria': 'SEM', 'codigo': 'SEM-TRIG', 'nome': 'Trigo', 'descricao': 'Sementes de trigo'},
]

for sub_data in subcategorias_data:
    subcategoria, created = SubCategoria.objects.get_or_create(
        codigo=sub_data['codigo'],
        defaults={
            'categoria': categorias[sub_data['categoria']],
            'nome': sub_data['nome'],
            'descricao': sub_data['descricao']
        }
    )
    print(f"{'Criada' if created else 'Já existe'}: Subcategoria {subcategoria.nome} ({subcategoria.categoria.nome})")

print("\n✅ Exemplos criados com sucesso!")
print("\nEstrutura:")
for cat in Categoria.objects.all():
    print(f"\n📂 {cat.nome}")
    for sub in cat.subcategorias.all():
        print(f"   └─ {sub.nome}")
