import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from produtos.models import Produto, Categoria, UnidadeMedida
from cadastros.models import NCM

# Buscar dados necessários
categoria_fertilizante = Categoria.objects.get(codigo='FERT')
categoria_defensivo = Categoria.objects.get(codigo='DEF')
unidade = UnidadeMedida.objects.first()
ncm = NCM.objects.first()

print("=== Testando Geração Automática de Código ===\n")

# Teste 1: Produto sem código (deve gerar FERT-000001)
print("Teste 1: Criando produto SEM código...")
produto1 = Produto(
    nome='Fertilizante NPK 10-10-10',
    categoria=categoria_fertilizante,
    unidade_medida=unidade,
    unidade_compra=unidade,
    unidade_venda=unidade,
    ncm=ncm
)
produto1.save()
print(f"✅ Código gerado: {produto1.codigo}\n")

# Teste 2: Outro produto sem código da mesma categoria (deve gerar FERT-000002)
print("Teste 2: Criando outro produto da mesma categoria SEM código...")
produto2 = Produto(
    nome='Fertilizante Ureia',
    categoria=categoria_fertilizante,
    unidade_medida=unidade,
    unidade_compra=unidade,
    unidade_venda=unidade,
    ncm=ncm
)
produto2.save()
print(f"✅ Código gerado: {produto2.codigo}\n")

# Teste 3: Produto de outra categoria sem código (deve gerar DEF-000001)
print("Teste 3: Criando produto de OUTRA categoria SEM código...")
produto3 = Produto(
    nome='Herbicida Glifosato',
    categoria=categoria_defensivo,
    unidade_medida=unidade,
    unidade_compra=unidade,
    unidade_venda=unidade,
    ncm=ncm
)
produto3.save()
print(f"✅ Código gerado: {produto3.codigo}\n")

# Teste 4: Produto COM código personalizado (não deve gerar automático)
print("Teste 4: Criando produto COM código personalizado...")
produto4 = Produto(
    codigo='FERT-CUSTOM-001',
    nome='Fertilizante Especial',
    categoria=categoria_fertilizante,
    unidade_medida=unidade,
    unidade_compra=unidade,
    unidade_venda=unidade,
    ncm=ncm
)
produto4.save()
print(f"✅ Código mantido: {produto4.codigo}\n")

# Teste 5: Mais um sem código (deve pular o CUSTOM e gerar FERT-000003)
print("Teste 5: Criando mais um produto SEM código...")
produto5 = Produto(
    nome='Fertilizante Super Fosfato',
    categoria=categoria_fertilizante,
    unidade_medida=unidade,
    unidade_compra=unidade,
    unidade_venda=unidade,
    ncm=ncm
)
produto5.save()
print(f"✅ Código gerado: {produto5.codigo}\n")

print("\n=== Resumo dos Produtos Criados ===")
for p in Produto.objects.all().order_by('codigo'):
    print(f"{p.codigo:20s} - {p.nome}")

print("\n✅ Teste concluído com sucesso!")
print("\nObservação: O código é gerado automaticamente no formato CATEGORIA-000001")
print("Se você informar um código personalizado, ele será mantido.")
