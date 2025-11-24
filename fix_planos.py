"""
Script de migração para corrigir o problema de planos
Execute este comando no terminal Django:

python manage.py shell < fix_planos.py

OU copie e cole o código abaixo no shell:
python manage.py shell
"""

from empresas.models import Plano, Empresa
from django.db import transaction

print("=" * 60)
print("SCRIPT DE CORREÇÃO DE PLANOS")
print("=" * 60)

# Passo 1: Criar planos padrão se não existirem
print("\n[1/3] Verificando planos padrão...")

planos_padrao = [
    {
        'codigo': 'PEQUENO',
        'nome': 'Pequeno Produtor',
        'icone': '🌱',
        'valor_mensal': 99.00,
        'desconto_anual': 16.67,
        'limite_fazendas': 2,
        'limite_usuarios': 3,
        'limite_talhoes': 10,
        'limite_produtos': 50,
        'acesso_relatorios_avancados': False,
        'acesso_api': False,
        'acesso_app_mobile': False,
        'acesso_suporte_prioritario': False,
        'ordem': 1,
    },
    {
        'codigo': 'MEDIO',
        'nome': 'Médio Produtor',
        'icone': '🌾',
        'valor_mensal': 249.00,
        'desconto_anual': 16.67,
        'limite_fazendas': 5,
        'limite_usuarios': 10,
        'limite_talhoes': 30,
        'limite_produtos': 200,
        'acesso_relatorios_avancados': True,
        'acesso_api': False,
        'acesso_app_mobile': True,
        'acesso_suporte_prioritario': True,
        'ordem': 2,
    },
    {
        'codigo': 'GRANDE',
        'nome': 'Grande Produtor',
        'icone': '🚜',
        'valor_mensal': 499.00,
        'desconto_anual': 16.67,
        'limite_fazendas': 999,
        'limite_usuarios': 999,
        'limite_talhoes': 999,
        'limite_produtos': 999,
        'acesso_relatorios_avancados': True,
        'acesso_api': True,
        'acesso_app_mobile': True,
        'acesso_suporte_prioritario': True,
        'ordem': 3,
    },
]

criados = 0
for dados in planos_padrao:
    plano, created = Plano.objects.get_or_create(
        codigo=dados['codigo'],
        defaults=dados
    )
    if created:
        criados += 1
        print(f"   ✅ Plano criado: {plano.nome}")
    else:
        print(f"   ℹ️  Plano já existe: {plano.nome}")

print(f"\n   Total de planos criados: {criados}")

# Passo 2: Corrigir empresas que têm plano como string
print("\n[2/3] Corrigindo empresas com plano incorreto...")

# Busca empresas onde plano está null (erro de migração anterior)
empresas_sem_plano = Empresa.objects.filter(plano__isnull=True)

if empresas_sem_plano.exists():
    print(f"   Encontradas {empresas_sem_plano.count()} empresas sem plano associado")
    
    # Tenta recuperar o código do plano do campo antigo
    # IMPORTANTE: Se você tiver backup do banco, use isso
    # Por enquanto, vamos atribuir o plano MEDIO como padrão
    
    plano_medio = Plano.objects.get(codigo='MEDIO')
    
    with transaction.atomic():
        for empresa in empresas_sem_plano:
            print(f"   Corrigindo empresa: {empresa.nome}")
            empresa.plano = plano_medio
            empresa.aplicar_limites_plano()
            empresa.save()
            print(f"   ✅ {empresa.nome} → Plano {plano_medio.nome}")
else:
    print("   ✅ Todas as empresas já possuem plano associado!")

# Passo 3: Aplicar limites do plano em todas as empresas
print("\n[3/3] Aplicando limites dos planos em todas as empresas...")

todas_empresas = Empresa.objects.select_related('plano').all()

with transaction.atomic():
    for empresa in todas_empresas:
        if empresa.plano:
            print(f"   Atualizando limites: {empresa.nome}")
            empresa.aplicar_limites_plano()
            empresa.save()

print("\n" + "=" * 60)
print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
print("=" * 60)

# Resumo final
print("\n📊 RESUMO:")
print(f"   Total de planos: {Plano.objects.count()}")
print(f"   Total de empresas: {Empresa.objects.count()}")
print(f"   Empresas ativas: {Empresa.objects.filter(ativa=True).count()}")

print("\n📋 PLANOS CADASTRADOS:")
for plano in Plano.objects.all():
    total_empresas = plano.empresas.count()
    print(f"   {plano.icone} {plano.nome}: {total_empresas} empresa(s)")

print("\n" + "=" * 60)
print("Agora você pode usar o CRUD de planos normalmente!")
print("=" * 60)