import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from cadastros.models import Fornecedor
from empresas.models import Empresa

print(f"\n{'='*70}")
print("DIAGNÓSTICO COMPLETO - FORNECEDORES NO SISTEMA")
print(f"{'='*70}\n")

# Listar todas as empresas
empresas = Empresa.objects.all()
print(f"Total de empresas no sistema: {empresas.count()}\n")

for empresa in empresas:
    print(f"\n{'='*70}")
    print(f"EMPRESA: {empresa.nome} (ID: {empresa.id})")
    print(f"{'='*70}")
    
    fornecedores = Fornecedor.objects.filter(empresa=empresa).order_by('nome')
    print(f"Total de fornecedores: {fornecedores.count()}")
    
    if fornecedores.exists():
        print("\nFornecedores:")
        for idx, forn in enumerate(fornecedores, 1):
            status = "[ATIVO]" if forn.ativa else "[INATIVO]"
            print(f"\n  {idx}. {status} {forn.nome}")
            if forn.nome_fantasia:
                print(f"      Nome fantasia: {forn.nome_fantasia}")
            print(f"      CNPJ/CPF: {forn.cnpj_cpf}")
            print(f"      ID: {forn.id}")
    else:
        print("  (Nenhum fornecedor cadastrado)")

# Buscar especificamente por TUBO ou CONE
print(f"\n{'='*70}")
print("BUSCA ESPECÍFICA POR 'TUBO' NO NOME")
print(f"{'='*70}\n")

tubo_fornecedores = Fornecedor.objects.filter(nome__icontains='TUBO')
if tubo_fornecedores.exists():
    for forn in tubo_fornecedores:
        print(f"Encontrado: {forn.nome}")
        print(f"  Empresa: {forn.empresa.nome}")
        print(f"  Ativa: {forn.ativa}")
        print(f"  ID: {forn.id}\n")
else:
    print("Nenhum fornecedor com 'TUBO' no nome encontrado.\n")

print(f"{'='*70}")
print("BUSCA ESPECÍFICA POR 'CONE' NO NOME")
print(f"{'='*70}\n")

cone_fornecedores = Fornecedor.objects.filter(nome__icontains='CONE')
if cone_fornecedores.exists():
    for forn in cone_fornecedores:
        print(f"Encontrado: {forn.nome}")
        print(f"  Empresa: {forn.empresa.nome}")
        print(f"  Ativa: {forn.ativa}")
        print(f"  ID: {forn.id}\n")
else:
    print("Nenhum fornecedor com 'CONE' no nome encontrado.\n")

print(f"{'='*70}")
print(f"TOTAL GERAL DE FORNECEDORES: {Fornecedor.objects.count()}")
print(f"{'='*70}\n")
