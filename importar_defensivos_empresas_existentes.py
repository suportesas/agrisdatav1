"""
Script para importar 88 defensivos em empresas já cadastradas.

Uso:
  python manage.py shell < importar_defensivos_empresas_existentes.py
  
Ou no shell interativo:
  python manage.py shell
  >>> exec(open('importar_defensivos_empresas_existentes.py').read())
"""

from empresas.models import Empresa
from produtos.defensivos_seed import seed_defensivos_for_empresa
from produtos.models import Produto
from django.db.models import Count

print("\n" + "="*60)
print("🌾 IMPORTADOR DE DEFENSIVOS PARA EMPRESAS EXISTENTES")
print("="*60)

# 1. Analisar situação
print("\n📊 Analisando empresas...")
total_defensivos_esperado = 88

for empresa in Empresa.objects.all():
    num_defensivos = empresa.produto_set.filter(categoria_agricola='DEFENSIVO').count()
    
    if num_defensivos == 0:
        print(f"\n📍 {empresa.nome_fantasia}")
        print(f"   Status: Sem defensivos (0/{total_defensivos_esperado})")
        print(f"   Ação: Será importado")
    else:
        print(f"\n📍 {empresa.nome_fantasia}")
        print(f"   Status: ✅ Já tem defensivos ({num_defensivos}/{total_defensivos_esperado})")

# 2. Importar em empresas sem defensivos
print("\n" + "-"*60)
print("⏳ Importando defensivos...")
print("-"*60 + "\n")

total_criados = 0
total_ignorados = 0

for empresa in Empresa.objects.all():
    num_existentes = empresa.produto_set.filter(categoria_agricola='DEFENSIVO').count()
    
    if num_existentes == 0:
        criados, ignorados = seed_defensivos_for_empresa(empresa)
        total_criados += criados
        total_ignorados += ignorados
        
        print(f"✅ {empresa.nome_fantasia}:")
        print(f"   • Criados: {criados}")
        if ignorados > 0:
            print(f"   • Ignorados: {ignorados}")
    else:
        print(f"⏭️  {empresa.nome_fantasia}: Pulado (já tem {num_existentes})")

# 3. Relatório final
print("\n" + "="*60)
print("📈 RELATÓRIO FINAL")
print("="*60 + "\n")

for empresa in Empresa.objects.all():
    num_defensivos = empresa.produto_set.filter(categoria_agricola='DEFENSIVO').count()
    status = "✅" if num_defensivos == total_defensivos_esperado else "⚠️"
    print(f"{status} {empresa.nome_fantasia}: {num_defensivos}/{total_defensivos_esperado}")

print(f"\n📊 Resumo:")
print(f"  • Total criado: {total_criados}")
print(f"  • Total ignorado: {total_ignorados}")

print("\n" + "="*60)
print("✨ Processo concluído!")
print("="*60 + "\n")
