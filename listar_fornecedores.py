import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from cadastros.models import Fornecedor
from empresas.models import Empresa

print(f"\n{'='*60}")
print("LISTA DE TODOS OS FORNECEDORES")
print(f"{'='*60}\n")

empresas = Empresa.objects.all()

for empresa in empresas:
    fornecedores = Fornecedor.objects.filter(empresa=empresa).order_by('nome')
    
    if fornecedores.exists():
        print(f"\n{'='*60}")
        print(f"EMPRESA: {empresa.nome_fantasia}")
        print(f"{'='*60}")
        
        ativos = fornecedores.filter(ativa=True).count()
        inativos = fornecedores.filter(ativa=False).count()
        
        print(f"\nTotal: {fornecedores.count()} | Ativos: {ativos} | Inativos: {inativos}\n")
        
        for forn in fornecedores:
            status = "✓ ATIVO" if forn.ativa else "✗ INATIVO"
            print(f"[{status}] {forn.nome}")
            if forn.nome_fantasia:
                print(f"           Fantasia: {forn.nome_fantasia}")
            print(f"           CNPJ/CPF: {forn.cnpj_cpf}")
            print()

print(f"\n{'='*60}\n")
