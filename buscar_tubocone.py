import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from cadastros.models import Fornecedor

print(f"\n{'='*60}")
print("BUSCA DO FORNECEDOR 'TUBOCONE'")
print(f"{'='*60}\n")

# Buscar qualquer fornecedor com "TUBOCONE" no nome
fornecedores = Fornecedor.objects.filter(nome__icontains='TUBOCONE')

if fornecedores.exists():
    for forn in fornecedores:
        print(f"Encontrado: {forn.nome}")
        print(f"  ID: {forn.id}")
        print(f"  Nome fantasia: {forn.nome_fantasia or 'N/A'}")
        print(f"  CNPJ/CPF: {forn.cnpj_cpf}")
        print(f"  Empresa: {forn.empresa.nome_fantasia}")
        print(f"  Ativa: {forn.ativa} ({'ATIVO' if forn.ativa else 'INATIVO'})")
        print(f"  Data cadastro: {forn.data_cadastro.strftime('%d/%m/%Y %H:%M')}")
        print()
else:
    print("❌ Nenhum fornecedor com 'TUBOCONE' no nome foi encontrado.")
    print("\nBuscando fornecedores com nomes similares...")
    
    # Buscar com partes do nome
    similares = Fornecedor.objects.filter(nome__icontains='TUBO')
    if similares.exists():
        print(f"\nFornecedores com 'TUBO' no nome:")
        for forn in similares:
            print(f"  - {forn.nome} (ID: {forn.id}, Ativa: {forn.ativa})")
    
    similares = Fornecedor.objects.filter(nome__icontains='CONE')
    if similares.exists():
        print(f"\nFornecedores com 'CONE' no nome:")
        for forn in similares:
            print(f"  - {forn.nome} (ID: {forn.id}, Ativa: {forn.ativa})")

print(f"\n{'='*60}")
print(f"TOTAL DE FORNECEDORES NO SISTEMA: {Fornecedor.objects.count()}")
print(f"{'='*60}\n")
