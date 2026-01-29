import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from produtos.models import Produto, ProdutoDefensivoCultura

print("=" * 60)
print("VERIFICAÇÃO COMPLETA DO PRODUTO")
print("=" * 60)

try:
    p = Produto.objects.get(id=10)
    print(f"\n✅ Produto encontrado: ID {p.id}")
    print(f"   Nome: {p.nome}")
    print(f"   Código: {p.codigo}")
    print(f"   Categoria: {p.categoria.nome} (ID: {p.categoria.id})")
    print(f"   Categoria Agrícola: {p.categoria_agricola or 'Não definida'}")
    
    print(f"\n📋 CAMPOS NOVOS:")
    print(f"   Período Reentrada: {p.periodo_reentrada or 'Não definido'} horas")
    print(f"   Países Proibidos: {p.paises_proibidos or 'Nenhum'}")
    
    print(f"\n🌾 DEFENSIVO - CULTURAS/PRAGAS:")
    culturas = ProdutoDefensivoCultura.objects.filter(produto=p)
    if culturas.exists():
        for dc in culturas:
            print(f"   - {dc.cultura} / {dc.praga}")
            print(f"     Dosagem: {dc.dosagem_minima}-{dc.dosagem_maxima} {dc.unidade_dosagem.sigla}")
            print(f"     Carência: {dc.carencia} dias")
    else:
        print(f"   Nenhuma cultura/praga cadastrada")
    
    print(f"\n🔍 VERIFICAÇÃO DA CATEGORIA:")
    cat_nome_lower = p.categoria.nome.lower()
    tem_defensivo = 'defensivo' in cat_nome_lower
    print(f"   Nome da categoria (lowercase): '{cat_nome_lower}'")
    print(f"   Contém 'defensivo'? {tem_defensivo}")
    
    if tem_defensivo:
        print(f"   ✅ A aba DEVERIA aparecer!")
    else:
        print(f"   ❌ A aba NÃO vai aparecer (categoria não contém 'defensivo')")
        
except Produto.DoesNotExist:
    print("❌ Produto ID 10 não encontrado!")
except Exception as e:
    print(f"❌ Erro: {e}")

print("\n" + "=" * 60)
