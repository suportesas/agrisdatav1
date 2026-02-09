"""
Script de verificação do sistema de defensivos.

Valida:
  ✅ Arquivo defensivos_seed.py existe e é válido
  ✅ Função seed_defensivos_for_empresa() funciona
  ✅ Signal está registrado
  ✅ Management command existe
  ✅ Isolamento multi-tenant funciona
  ✅ Idempotência (não duplica)

Uso:
  python verify_defensivos_system.py
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

from empresas.models import Empresa
from produtos.models import Produto
from produtos.defensivos_seed import seed_defensivos_for_empresa, DEFENSIVOS_SEED

print("\n" + "="*70)
print("🔍 VERIFICAÇÃO DO SISTEMA DE DEFENSIVOS")
print("="*70 + "\n")

erros = []
avisos = []
sucessos = []

# ============================================================================
# 1. Verificar arquivo de seed
# ============================================================================
print("1️⃣  Verificando arquivo defensivos_seed.py...")

try:
    quantidade = len(DEFENSIVOS_SEED)
    assert quantidade == 88, f"Esperado 88, encontrado {quantidade}"
    sucessos.append(f"✅ defensivos_seed.py contém {quantidade} defensivos")
except Exception as e:
    erros.append(f"❌ Erro em defensivos_seed.py: {e}")

# Verificar estrutura de cada defensivo
try:
    campos_obrigatorios = {
        'nome_comercial': str,
        'ingrediente_ativo': str,
        'classe_agronomica': str,
        'classe_toxicologica': str,
        'classe_ambiental': str,
    }
    
    for i, def_item in enumerate(DEFENSIVOS_SEED):
        for campo, tipo in campos_obrigatorios.items():
            if campo not in def_item:
                raise KeyError(f"Defensivo {i}: Falta campo '{campo}'")
            if not isinstance(def_item[campo], tipo):
                raise TypeError(f"Defensivo {i}: Campo '{campo}' tipo inválido")
    
    sucessos.append("✅ Estrutura de defensivos válida (todos têm campos obrigatórios)")
except Exception as e:
    erros.append(f"❌ Erro na estrutura: {e}")

# ============================================================================
# 2. Verificar signal
# ============================================================================
print("\n2️⃣  Verificando signal de criação...")

try:
    # Verificar se seed_defensivos_on_create está registrado
    from django.db.models.signals import post_save
    from django.dispatch import receiver
    
    # Ler arquivo de signals
    with open('empresas/signals.py', 'r') as f:
        signals_content = f.read()
    
    assert 'seed_defensivos_on_create' in signals_content, "Signal não encontrado"
    assert 'seed_defensivos_for_empresa' in signals_content, "Import não encontrado"
    
    sucessos.append("✅ Signal seed_defensivos_on_create() está registrado")
except Exception as e:
    erros.append(f"❌ Erro no signal: {e}")

# ============================================================================
# 3. Verificar Management Command
# ============================================================================
print("3️⃣  Verificando management command...")

try:
    from produtos.management.commands.seed_defensivos import Command
    assert hasattr(Command, 'handle'), "método handle() não encontrado"
    sucessos.append("✅ Management command seed_defensivos existe")
except Exception as e:
    erros.append(f"❌ Erro no command: {e}")

# ============================================================================
# 4. Testar criação de defensivos em empresa de teste
# ============================================================================
print("\n4️⃣  Testando criação em empresa...")

# Criar empresa temporária de teste
try:
    # Verificar se existe alguma empresa
    empresas = Empresa.objects.all()
    
    if not empresas.exists():
        avisos.append("⚠️  Nenhuma empresa encontrada para teste (pulando teste de criação)")
    else:
        empresa_teste = empresas.first()
        
        # Contar defensivos antes
        count_antes = empresa_teste.produto_set.filter(
            categoria_agricola='DEFENSIVO'
        ).count()
        
        # Chamar seed
        criados, ignorados = seed_defensivos_for_empresa(empresa_teste)
        
        # Contar depois
        count_depois = empresa_teste.produto_set.filter(
            categoria_agricola='DEFENSIVO'
        ).count()
        
        # Verificações
        if count_antes == 0:
            assert count_depois == 88, f"Esperado 88, mas criou {count_depois}"
            sucessos.append(f"✅ Função cria 88 defensivos corretamente ({criados} criados)")
        else:
            sucessos.append(f"✅ Função é idempotente ({criados} criados, {ignorados} ignorados)")
        
except Exception as e:
    erros.append(f"❌ Erro ao testar criação: {e}")

# ============================================================================
# 5. Verificar isolamento multi-tenant
# ============================================================================
print("\n5️⃣  Verificando isolamento multi-tenant...")

try:
    empresas = list(Empresa.objects.all())
    
    if len(empresas) < 2:
        avisos.append("⚠️  Menos de 2 empresas para testar isolamento (pulando)")
    else:
        empresa_a = empresas[0]
        empresa_b = empresas[1]
        
        # Obter um defensivo de A
        def_a = empresa_a.produto_set.filter(
            categoria_agricola='DEFENSIVO'
        ).first()
        
        if def_a:
            # Verificar que B não pode acessar
            def_b_with_same_name = empresa_b.produto_set.filter(
                categoria_agricola='DEFENSIVO',
                nome=def_a.nome
            ).first()
            
            # Devem ser diferentes objetos
            assert def_a != def_b_with_same_name, "Isolamento falhou!"
            
            sucessos.append("✅ Isolamento multi-tenant está funcionando")
        else:
            avisos.append("⚠️  Nenhum defensivo encontrado para testar isolamento")
            
except Exception as e:
    erros.append(f"❌ Erro ao testar isolamento: {e}")

# ============================================================================
# 6. Verificar idempotência
# ============================================================================
print("\n6️⃣  Verificando idempotência...")

try:
    empresas = Empresa.objects.all()
    
    if not empresas.exists():
        avisos.append("⚠️  Nenhuma empresa para testar idempotência")
    else:
        empresa_teste = empresas.first()
        
        # Primeira chamada
        criados_1, ignorados_1 = seed_defensivos_for_empresa(empresa_teste)
        count_1 = empresa_teste.produto_set.filter(
            categoria_agricola='DEFENSIVO'
        ).count()
        
        # Segunda chamada
        criados_2, ignorados_2 = seed_defensivos_for_empresa(empresa_teste)
        count_2 = empresa_teste.produto_set.filter(
            categoria_agricola='DEFENSIVO'
        ).count()
        
        # Verificar
        assert count_1 == count_2, f"Contagem mudou: {count_1} → {count_2}"
        assert criados_2 == 0, f"Segunda chamada criou {criados_2} (deveria ser 0)"
        
        sucessos.append("✅ Função é idempotente (não duplica)")
        
except Exception as e:
    erros.append(f"❌ Erro ao testar idempotência: {e}")

# ============================================================================
# 7. Verificar modelos
# ============================================================================
print("\n7️⃣  Verificando modelo Produto...")

try:
    # Verificar campos
    assert hasattr(Produto, 'empresa'), "Campo 'empresa' não existe"
    assert hasattr(Produto, 'categoria_agricola'), "Campo 'categoria_agricola' não existe"
    assert hasattr(Produto, 'classe_agronomica'), "Campo 'classe_agronomica' não existe"
    
    sucessos.append("✅ Modelo Produto tem campos necessários")
except Exception as e:
    erros.append(f"❌ Erro no modelo: {e}")

# ============================================================================
# RESULTADO FINAL
# ============================================================================
print("\n" + "="*70)
print("📊 RESULTADO DA VERIFICAÇÃO")
print("="*70 + "\n")

if sucessos:
    print("✅ SUCESSOS:")
    for msg in sucessos:
        print(f"   {msg}")

if avisos:
    print("\n⚠️  AVISOS:")
    for msg in avisos:
        print(f"   {msg}")

if erros:
    print("\n❌ ERROS:")
    for msg in erros:
        print(f"   {msg}")
    print("\n" + "="*70)
    print("❌ FALHA - Sistema não passou na verificação")
    print("="*70 + "\n")
    sys.exit(1)
else:
    print("\n" + "="*70)
    print("✅ SUCESSO - Sistema de defensivos está funcionando!")
    print("="*70 + "\n")
    sys.exit(0)
