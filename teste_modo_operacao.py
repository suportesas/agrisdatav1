#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Teste de Modo de Operação - Verifica se URLs estão funcionando
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from empresas.models import Empresa
from core.models_config import ConfiguracaoSistema

User = get_user_model()

print("\n" + "="*70)
print("🧪 TESTE DO SISTEMA DE MODOS DE OPERAÇÃO")
print("="*70)

# 1. Verificar ConfiguracaoSistema
print("\n✓ Testando ConfiguracaoSistema...")
try:
    # Obter primeira empresa
    empresa = Empresa.objects.first()
    if not empresa:
        print("   ❌ Nenhuma empresa encontrada!")
    else:
        config = ConfiguracaoSistema.get_config(empresa)
        print(f"   ✓ Empresa: {empresa.razao_social}")
        print(f"   ✓ Modo Compras: {config.modo_compras}")
        print(f"   ✓ Modo Estoque: {config.modo_estoque}")
except Exception as e:
    print(f"   ❌ Erro: {e}")

# 2. Testar URLs (simulação)
print("\n✓ Testando URLs disponíveis...")

urls_to_test = [
    ("GET", "/compras/compra-rapida/", "Compra Rápida"),
    ("GET", "/compras/recebimento-rapido/", "Recebimento Rápido"),
    ("GET", "/compras/escolher-modo/", "Escolher Modo - Compras"),
    ("GET", "/estoque/entrada-rapida/", "Entrada Rápida"),
    ("GET", "/estoque/saida-rapida/", "Saída Rápida"),
    ("GET", "/estoque/ajuste-rapido/", "Ajuste Rápido"),
    ("GET", "/estoque/escolher-modo-estoque/", "Escolher Modo - Estoque"),
    ("GET", "/configuracoes/sistema/", "Configuração do Sistema"),
]

client = Client()

for method, url, desc in urls_to_test:
    try:
        response = client.get(url)
        status = response.status_code
        
        if status == 200:
            print(f"   ✓ {desc:<30} [{status}] ✅")
        elif status == 302:
            print(f"   ⚠ {desc:<30} [{status}] (Redirect - Requer login)")
        elif status == 404:
            print(f"   ❌ {desc:<30} [{status}] (Não encontrado)")
        else:
            print(f"   ⚠ {desc:<30} [{status}]")
    except Exception as e:
        print(f"   ❌ {desc:<30} Error: {str(e)[:40]}")

# 3. Verificar Views
print("\n✓ Verificando Views...")

try:
    from compras.views_simples import (
        compra_rapida, 
        recebimento_rapido, 
        escolher_modo_compra
    )
    print("   ✓ compras.views_simples.compra_rapida")
    print("   ✓ compras.views_simples.recebimento_rapido")
    print("   ✓ compras.views_simples.escolher_modo_compra")
except Exception as e:
    print(f"   ❌ Erro ao importar compras.views_simples: {e}")

try:
    from estoque.views_simples import (
        entrada_rapida,
        saida_rapida,
        ajuste_rapido,
        escolher_modo_estoque
    )
    print("   ✓ estoque.views_simples.entrada_rapida")
    print("   ✓ estoque.views_simples.saida_rapida")
    print("   ✓ estoque.views_simples.ajuste_rapido")
    print("   ✓ estoque.views_simples.escolher_modo_estoque")
except Exception as e:
    print(f"   ❌ Erro ao importar estoque.views_simples: {e}")

# 4. Verificar Templates
print("\n✓ Verificando Templates...")

import os
templates_to_check = [
    "compras/templates/compras/compra_rapida.html",
    "compras/templates/compras/recebimento_rapido.html",
    "compras/templates/compras/escolher_modo.html",
    "estoque/templates/estoque/entrada_rapida.html",
    "estoque/templates/estoque/saida_rapida.html",
    "estoque/templates/estoque/escolher_modo.html",
    "core/templates/configuracao_sistema.html",
]

for template in templates_to_check:
    full_path = os.path.join('/erp_agricola', template)
    exists = os.path.exists(full_path)
    status = "✓" if exists else "❌"
    print(f"   {status} {template}")

# 5. Resumo
print("\n" + "="*70)
print("📊 RESUMO DO SISTEMA DE MODOS")
print("="*70)

print("\n⚡ MODO SIMPLES:")
print("  - Compra: /compras/compra-rapida/")
print("  - Estoque: /estoque/entrada-rapida/, /estoque/saida-rapida/")
print("  - Tempo: 30-60 segundos")

print("\n📋 MODO FORMAL:")
print("  - Compra: /compras/solicitacao/create/")
print("  - Estoque: /estoque/movimentacao/")
print("  - Tempo: 5-10 minutos")

print("\n🔀 MODO HIBRIDO:")
print("  - Compra: /compras/escolher-modo/")
print("  - Estoque: /estoque/escolher-modo-estoque/")
print("  - Permite escolha em cada operação")

print("\n⚙️ CONFIGURAÇÃO:")
print("  - URL: /configuracoes/sistema/")
print("  - Define modo padrão por empresa")

print("\n" + "="*70)
print("✅ TESTE CONCLUÍDO!")
print("="*70 + "\n")
