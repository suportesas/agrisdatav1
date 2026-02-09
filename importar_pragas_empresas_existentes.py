"""
Script para importar 88 pragas em empresas já cadastradas.

Uso:
  python manage.py shell < importar_pragas_empresas_existentes.py
  
Ou no shell interativo:
  python manage.py shell
  >>> exec(open('importar_pragas_empresas_existentes.py').read())
"""

from empresas.models import Empresa
from cadastros.pragas_seed import seed_pragas_for_company
from django.db.models import Count

print("\n" + "="*60)
print("🌾 IMPORTADOR DE PRAGAS PARA EMPRESAS EXISTENTES")
print("="*60)

# 1. Listar empresas sem pragas
print("\n📊 Analisando empresas...")
empresas_sem_pragas = Empresa.objects.annotate(
    num_pragas=Count('pragas')
).filter(num_pragas=0)

print(f"\nEmpresas SEM pragas: {empresas_sem_pragas.count()}")
for empresa in empresas_sem_pragas:
    print(f"  • {empresa.nome_fantasia} (ID: {empresa.id})")

# 2. Importar pragas
if empresas_sem_pragas.exists():
    print("\n⏳ Importando pragas...")
    
    total_criadas = 0
    total_ignoradas = 0
    
    for empresa in empresas_sem_pragas:
        criadas, ignoradas = seed_pragas_for_company(empresa)
        total_criadas += criadas
        total_ignoradas += ignoradas
        
        print(f"  ✅ {empresa.nome_fantasia}: {criadas} pragas criadas")
    
    print(f"\n✅ SUCESSO!")
    print(f"  Total criado: {total_criadas} pragas")
    print(f"  Total ignorado: {total_ignoradas} pragas")
else:
    print("\n✅ Todas as empresas já têm pragas!")

# 3. Verificar resultado final
print("\n📈 Resultado final:")
for empresa in Empresa.objects.all():
    num_pragas = empresa.pragas.count()
    print(f"  • {empresa.nome_fantasia}: {num_pragas} pragas")

print("\n" + "="*60)
print("✨ Processo concluído!")
print("="*60 + "\n")
