"""
Migrar dados de tipo_produto antigo (CharField) para novo (ForeignKey)
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from produtos.models import TipoProduto, Produto
from empresas.models import Empresa

print("=== Migrando Dados de Tipo de Produto ===\n")

# 1. Popular tipos padrão
tipos_padrao = [
    {'codigo': 'REVENDA', 'nome': 'Revenda'},
    {'codigo': 'CONSUMO', 'nome': 'Consumo'},
    {'codigo': 'MATERIA_PRIMA', 'nome': 'Matéria Prima'},
    {'codigo': 'PRODUTO_ACABADO', 'nome': 'Produto Acabado'},
]

empresas = Empresa.objects.all()
print(f"1. Populando tipos para {empresas.count()} empresa(s)...\n")

for empresa in empresas:
    print(f"   Empresa: {empresa.nome}")
    for tipo_data in tipos_padrao:
        tipo, created = TipoProduto.objects.get_or_create(
            empresa=empresa,
            codigo=tipo_data['codigo'],
            defaults={'nome': tipo_data['nome'], 'ativo': True}
        )
        if created:
            print(f"   ✓ Criado: {tipo.nome}")

# 2. Copiar valores antigos para tipo_produto_antigo
print(f"\n2. Copiando valores antigos...")
from django.db import connection
with connection.cursor() as cursor:
    # Apenas se o campo antigo ainda não foi populado
    cursor.execute("SELECT COUNT(*) FROM produtos_produto WHERE tipo_produto_antigo IS NULL AND tipo_produto IS NOT NULL")
    count = cursor.fetchone()[0]
    if count > 0:
        cursor.execute("""
            UPDATE produtos_produto 
            SET tipo_produto_antigo = tipo_produto 
            WHERE tipo_produto_antigo IS NULL AND tipo_produto IS NOT NULL
        """)
        print(f"   ✓ Copiado {count} registros para campo temporário")

# 3. Limpar FK tipo_produto (será preenchido logo abaixo)
print(f"\n3. Limpando FKs...")
Produto.objects.update(tipo_produto=None)

# 4. Migrar dados
print(f"\n4. Migrando dados dos produtos...")
produtos = Produto.objects.exclude(tipo_produto_antigo__isnull=True).exclude(tipo_produto_antigo='')
total = produtos.count()
migrados = 0
erros = 0

for produto in produtos:
    try:
        tipo = TipoProduto.objects.filter(
            empresa=produto.empresa,
            codigo=produto.tipo_produto_antigo
        ).first()
        
        if tipo:
            produto.tipo_produto = tipo
            produto.save(update_fields=['tipo_produto'])
            migrados += 1
        else:
            print(f"   ⚠ Tipo '{produto.tipo_produto_antigo}' não encontrado para produto '{produto.nome}'")
            erros += 1
    except Exception as e:
        print(f"   ✗ Erro ao migrar produto {produto.id}: {e}")
        erros += 1

print(f"\n   ✓ Migrados: {migrados}/{total}")
if erros > 0:
    print(f"   ⚠ Erros: {erros}")

print("\n=== Concluído! ===")
