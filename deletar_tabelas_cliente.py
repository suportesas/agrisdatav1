import sqlite3
import os

# Caminho do banco
db_path = 'db.sqlite3'

if not os.path.exists(db_path):
    print(f"❌ Banco de dados não encontrado: {db_path}")
    exit()

# Conectar
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Tabelas para deletar
tabelas = [
    'cadastros_categoriadocumentocliente',
    
]

print("🗑️ Deletando tabelas...\n")

for tabela in tabelas:
    try:
        cursor.execute(f"DROP TABLE IF EXISTS {tabela}")
        print(f"✅ Deletada: {tabela}")
    except Exception as e:
        print(f"❌ Erro ao deletar {tabela}: {e}")

# Salvar e fechar
conn.commit()
conn.close()

print("\n✅ Processo concluído!")
print("\nAgora rode:")
print("  python manage.py makemigrations")
print("  python manage.py migrate")