import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import connection

# Verificar se as tabelas existem
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name LIKE 'compras_%' 
        ORDER BY name
    """)
    tables = cursor.fetchall()
    
print("Tabelas do módulo compras:")
for table in tables:
    print(f"  - {table[0]}")

# Verificar modelos
print("\nVerificando modelos...")

from compras.models import TipoDivergencia, DivergenciaRecebimento, AvaliacaoFornecedor

print("✅ TipoDivergencia importado")
print("✅ DivergenciaRecebimento importado")
print("✅ AvaliacaoFornecedor importado")

# Contar registros
from empresas.models import Empresa

for empresa in Empresa.objects.filter(ativo=True)[:1]:
    count_tipos = TipoDivergencia.objects.filter(empresa=empresa).count()
    count_div = DivergenciaRecebimento.objects.count()
    count_aval = AvaliacaoFornecedor.objects.count()
    
    print(f"\n{empresa.nome}:")
    print(f"  - Tipos de Divergência: {count_tipos}")
    print(f"  - Divergências Registradas: {count_div}")
    print(f"  - Avaliações: {count_aval}")
