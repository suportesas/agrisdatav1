"""Script para testar o salvamento de produto"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from produtos.models import Produto, Categoria, SubCategoria, UnidadeMedida
from produtos.forms import ProdutoForm
from cadastros.models import NCM, Fornecedor
from empresas.models import Empresa
from usuarios.models import Usuario

print("=" * 80)
print("TESTE DE SALVAMENTO DE PRODUTO")
print("=" * 80)

# Buscar empresa
empresa = Empresa.objects.first()
if not empresa:
    print("❌ ERRO: Nenhuma empresa encontrada")
    exit()

print(f"\n✓ Empresa: {empresa.nome}")

# Buscar ou criar categoria
categoria, created = Categoria.objects.get_or_create(
    empresa=empresa,
    codigo='TESTE',
    defaults={'nome': 'Categoria Teste'}
)
print(f"✓ Categoria: {categoria.nome} (ID: {categoria.id})")

# Buscar ou criar unidade
unidade, created = UnidadeMedida.objects.get_or_create(
    empresa=empresa,
    sigla='UN',
    defaults={'descricao': 'Unidade'}
)
print(f"✓ Unidade: {unidade.sigla} (ID: {unidade.id})")

# Buscar NCM
ncm = NCM.objects.first()
if not ncm:
    print("❌ ERRO: Nenhum NCM encontrado")
    exit()
print(f"✓ NCM: {ncm.codigo} - {ncm.nome} (ID: {ncm.id})")

# Dados do formulário simulando POST
form_data = {
    'codigo': '',  # Será gerado automaticamente
    'nome': 'Produto Teste',
    'categoria': categoria.id,
    'unidade_medida': unidade.id,
    'unidade_compra': unidade.id,
    'unidade_venda': unidade.id,
    'fator_conversao': 1,
    'ncm': ncm.id,
    'cest': '',
    'origem_mercadoria': '0',
    'tipo_item': '00',
    'preco_custo': 0,
    'preco_venda': 0,
    'margem_lucro': 0,
    'preco_minimo': 0,
    'controla_estoque': True,
    'estoque_minimo': 0,
    'estoque_maximo': 0,
    'estoque_atual': 0,
    'ativo': True,
    'tipo_produto': 'REVENDA',
    'categoria_agricola': '',  # Campo opcional
}

print("\n" + "=" * 80)
print("TESTANDO FORMULÁRIO")
print("=" * 80)

form = ProdutoForm(data=form_data, empresa=empresa)

print("\n📋 Campos do formulário:")
for field_name in form.fields:
    field = form.fields[field_name]
    required = "✓" if field.required else "○"
    print(f"  {required} {field_name}")

print("\n" + "=" * 80)
print("VALIDAÇÃO DO FORMULÁRIO")
print("=" * 80)

if form.is_valid():
    print("✅ Formulário VÁLIDO")
    
    try:
        produto = form.save(commit=False)
        print(f"\n✓ Produto criado em memória: {produto.nome}")
        print(f"  - Código: {produto.codigo}")
        print(f"  - Categoria: {produto.categoria}")
        print(f"  - NCM: {produto.ncm}")
        print(f"  - Unidade: {produto.unidade_medida}")
        
        # Tentar salvar no banco
        produto.save()
        print(f"\n✅ Produto salvo com sucesso! ID: {produto.id}")
        
        # Deletar produto de teste
        produto.delete()
        print("✓ Produto de teste deletado")
        
    except Exception as e:
        print(f"\n❌ ERRO ao salvar: {e}")
        import traceback
        traceback.print_exc()
else:
    print("❌ Formulário INVÁLIDO")
    print("\n🔍 Erros encontrados:")
    for field, errors in form.errors.items():
        print(f"\n  Campo: {field}")
        for error in errors:
            print(f"    ❌ {error}")
    
    print("\n🔍 Dados fornecidos:")
    for field, value in form_data.items():
        print(f"  {field}: {value}")

print("\n" + "=" * 80)
print("TESTE CONCLUÍDO")
print("=" * 80)
