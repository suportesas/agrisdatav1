#!/usr/bin/env python
"""
Script para testar o seed de pragas
Verifica se o sistema está criando pragas automaticamente quando uma empresa é criada
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from empresas.models import Empresa, Plano
from cadastros.models import Praga
from cadastros.pragas_seed import PRAGAS_SEED, seed_pragas_for_company

print("=" * 80)
print("TESTE DO SISTEMA DE SEED DE PRAGAS")
print("=" * 80)

# Verificar quantidade de pragas no seed
print(f"\n📊 Total de pragas no seed: {len(PRAGAS_SEED)}")

# Listar todas as pragas por categoria
categorias = {}
for praga in PRAGAS_SEED:
    nome = praga['nome_comum']
    print(f"  - {nome}")

# Testar criação manual
print("\n" + "=" * 80)
print("TESTANDO CRIAÇÃO DE PRAGAS PARA UMA EMPRESA")
print("=" * 80)

# Criar empresa de teste
try:
    # Obter o primeiro plano disponível
    plano = Plano.objects.first()
    if not plano:
        print("❌ Nenhum plano encontrado! Execute as migrações primeiro.")
        exit(1)
    
    # Verificar se empresa de teste já existe
    empresa_teste = Empresa.objects.filter(nome='EMPRESA_TESTE_PRAGAS').first()
    if empresa_teste:
        print(f"✓ Empresa de teste já existe: {empresa_teste.nome}")
        empresa = empresa_teste
    else:
        empresa = Empresa.objects.create(
            nome='EMPRESA_TESTE_PRAGAS',
            plano=plano
        )
        print(f"✓ Empresa de teste criada: {empresa.nome}")
    
    # Contar pragas existentes
    pragas_antes = Praga.objects.filter(empresa=empresa).count()
    print(f"✓ Pragas já existentes nesta empresa: {pragas_antes}")
    
    # Deletar pragas da empresa para teste limpo
    if pragas_antes > 0:
        deletadas = Praga.objects.filter(empresa=empresa).delete()[0]
        print(f"✓ Pragas deletadas para teste limpo: {deletadas}")
    
    # Executar seed manualmente
    criadas, ignoradas = seed_pragas_for_company(empresa)
    print(f"\n✓ Pragas criadas: {criadas}")
    print(f"✓ Pragas ignoradas (já existiam): {ignoradas}")
    
    # Verificar resultado
    pragas_depois = Praga.objects.filter(empresa=empresa).count()
    print(f"\n✓ Total de pragas na empresa agora: {pragas_depois}")
    
    # Listar algumas pragas
    print(f"\n📋 Primeiras 10 pragas cadastradas:")
    for praga in Praga.objects.filter(empresa=empresa)[:10]:
        print(f"   - {praga.nome_comum} ({praga.nome_cientifico})")
    
    if pragas_depois == len(PRAGAS_SEED):
        print("\n✅ SUCESSO! Todas as pragas foram criadas corretamente!")
    else:
        print(f"\n⚠️  AVISO: Esperava {len(PRAGAS_SEED)} pragas, mas só tem {pragas_depois}")
    
    print("\n" + "=" * 80)
    print("VERIFICANDO ISOLAMENTO MULTI-TENANT")
    print("=" * 80)
    
    # Criar outra empresa
    empresa2 = Empresa.objects.filter(nome='EMPRESA_TESTE_PRAGAS_2').first()
    if not empresa2:
        empresa2 = Empresa.objects.create(
            nome='EMPRESA_TESTE_PRAGAS_2',
            plano=plano
        )
        print(f"✓ Segunda empresa criada: {empresa2.nome}")
    else:
        print(f"✓ Segunda empresa já existe: {empresa2.nome}")
    
    # Deletar pragas da segunda empresa
    deletadas2 = Praga.objects.filter(empresa=empresa2).delete()[0]
    if deletadas2 > 0:
        print(f"✓ Pragas deletadas da segunda empresa: {deletadas2}")
    
    # Criar pragas na segunda empresa com um nome diferente
    praga_unica = Praga.objects.create(
        empresa=empresa2,
        nome_comum='PRAGA_UNICA_EMPRESA2',
        nome_cientifico='Virus.uniquus'
    )
    print(f"✓ Praga única criada na empresa 2: {praga_unica.nome_comum}")
    
    # Verificar isolamento
    pragas_emp1 = Praga.objects.filter(empresa=empresa).count()
    pragas_emp2 = Praga.objects.filter(empresa=empresa2).count()
    
    print(f"\n✓ Pragas na empresa 1: {pragas_emp1}")
    print(f"✓ Pragas na empresa 2: {pragas_emp2}")
    
    if pragas_emp1 > pragas_emp2 and 'PRAGA_UNICA_EMPRESA2' not in [p.nome_comum for p in Praga.objects.filter(empresa=empresa)]:
        print("\n✅ SUCESSO! Isolamento multi-tenant funcionando corretamente!")
        print("   - Cada empresa tem seus próprios dados")
        print("   - Pragas de uma empresa não aparecem em outra")
    else:
        print("\n⚠️  Possível problema no isolamento multi-tenant")
    
except Exception as e:
    print(f"❌ Erro durante teste: {str(e)}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("FIM DO TESTE")
print("=" * 80)
