"""
SCRIPT DE CORREÇÃO FINAL - GARANTIDO
Execute: python fix_final.py
"""

import os
import shutil
from pathlib import Path

def main():
    print("🔧 CORREÇÃO FINAL - GARANTIDA")
    print("=" * 80)
    
    # PASSO 1: Remove TODAS as migrações problemáticas
    print("\n📦 PASSO 1: Limpando migrações...")
    migrations_dir = Path("cadastros/migrations")
    
    removed = []
    for migration_file in migrations_dir.glob("0009_*.py"):
        print(f"  🗑️  Removendo: {migration_file.name}")
        migration_file.unlink()
        removed.append(migration_file.name)
    
    for migration_file in migrations_dir.glob("0010_*.py"):
        print(f"  🗑️  Removendo: {migration_file.name}")
        migration_file.unlink()
        removed.append(migration_file.name)
    
    if removed:
        print(f"  ✅ {len(removed)} arquivo(s) removido(s)")
    else:
        print("  ℹ️  Nenhuma migração problemática encontrada")
    
    # PASSO 2: Remove cache do Python
    print("\n🧹 PASSO 2: Limpando cache Python...")
    
    pycache_dirs = list(Path(".").rglob("__pycache__"))
    for cache_dir in pycache_dirs:
        if "cadastros" in str(cache_dir):
            print(f"  🗑️  Removendo: {cache_dir}")
            shutil.rmtree(cache_dir, ignore_errors=True)
    
    pyc_files = list(Path("cadastros").rglob("*.pyc"))
    for pyc_file in pyc_files:
        print(f"  🗑️  Removendo: {pyc_file}")
        pyc_file.unlink()
    
    print("  ✅ Cache limpo!")
    
    # PASSO 3: Remove banco de dados SQLite (SE QUISER RESETAR TUDO)
    print("\n⚠️  PASSO 3: Resetar banco de dados?")
    print("  ATENÇÃO: Isso vai APAGAR TODOS OS DADOS!")
    resposta = input("  Digite 'SIM' para confirmar ou ENTER para pular: ").strip().upper()
    
    if resposta == "SIM":
        db_file = Path("db.sqlite3")
        if db_file.exists():
            backup = Path("db.sqlite3.backup")
            print(f"  💾 Criando backup: {backup}")
            shutil.copy(db_file, backup)
            
            print(f"  🗑️  Removendo: {db_file}")
            db_file.unlink()
            
            print("  ✅ Banco resetado! Execute:")
            print("     python manage.py migrate")
    else:
        print("  ⏭️  Pulando reset do banco")
    
    # INSTRUÇÕES FINAIS
    print("\n" + "=" * 80)
    print("✅ LIMPEZA CONCLUÍDA!")
    print("=" * 80)
    print("\n📋 PRÓXIMOS PASSOS:")
    print("1. python manage.py makemigrations cadastros")
    print("2. python manage.py migrate")
    print("3. python manage.py runserver")
    print("=" * 80)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()