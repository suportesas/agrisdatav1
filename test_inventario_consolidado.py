#!/usr/bin/env python
"""
Script para testar consolidação de estoque no inventário cíclico
Verifica: Lotes + Movimentações Diretas = Total esperado
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from estoque.models import Lote, MovimentacaoEstoque, InventarioCiclico, InventarioCiclicoItem, Armazem
from produtos.models import Produto
from empresas.models import Empresa
from decimal import Decimal

# Get FERT-000002
try:
    fert = Produto.objects.get(codigo='FERT-000002')
    print(f"✓ Produto encontrado: {fert.descricao}")
    
    # Get empresa
    empresa = Empresa.objects.first()
    armazem = Armazem.objects.filter(empresa=empresa).first()
    
    print(f"✓ Empresa: {empresa.nome}, Armazém: {armazem.nome}")
    
    # Verifica lotes
    lotes = Lote.objects.filter(
        empresa=empresa,
        armazem=armazem,
        produto=fert,
        status__in=['DISPONIVEL', 'BLOQUEADO']
    )
    qtd_lotes = sum(l.quantidade_atual for l in lotes)
    print(f"\n📦 LOTES:")
    for lote in lotes:
        print(f"  - {lote.numero}: {lote.quantidade_atual} {fert.unidade_medida.sigla} (status: {lote.status})")
    print(f"  TOTAL: {qtd_lotes} {fert.unidade_medida.sigla}")
    
    # Verifica movimentações diretas
    print(f"\n📤 MOVIMENTAÇÕES ENTRADA (sem lote, status EXECUTADO):")
    entradas = MovimentacaoEstoque.objects.filter(
        empresa=empresa,
        armazem_destino=armazem,
        produto=fert,
        lote__isnull=True,
        tipo='ENTRADA',
        status='EXECUTADO'
    )
    qtd_entrada = sum(e.quantidade for e in entradas)
    for mov in entradas:
        print(f"  - {mov.id}: {mov.quantidade} {fert.unidade_medida.sigla} ({mov.origem})")
    print(f"  TOTAL: {qtd_entrada} {fert.unidade_medida.sigla}")
    
    print(f"\n📥 MOVIMENTAÇÕES SAÍDA (sem lote, status EXECUTADO):")
    saidas = MovimentacaoEstoque.objects.filter(
        empresa=empresa,
        armazem_origem=armazem,
        produto=fert,
        lote__isnull=True,
        tipo='SAIDA',
        status='EXECUTADO'
    )
    qtd_saida = sum(s.quantidade for s in saidas)
    for mov in saidas:
        print(f"  - {mov.id}: {mov.quantidade} {fert.unidade_medida.sigla} ({mov.origem})")
    print(f"  TOTAL: {qtd_saida} {fert.unidade_medida.sigla}")
    
    # Cálculo consolidado
    total_consolidado = qtd_lotes + qtd_entrada - qtd_saida
    print(f"\n✓ TOTAL CONSOLIDADO = {qtd_lotes} + {qtd_entrada} - {qtd_saida} = {total_consolidado} {fert.unidade_medida.sigla}")
    
    # Verifica produto
    print(f"\n🔍 Campo estoque_atual do Produto: {fert.estoque_atual} {fert.unidade_medida.sigla}")
    
    if fert.estoque_atual == total_consolidado:
        print("✓ MATCH! Produto está correto")
    else:
        print(f"✗ DISCREPÂNCIA: esperado {total_consolidado}, encontrado {fert.estoque_atual}")
    
    # Verifica inventários existentes
    invs = InventarioCiclico.objects.filter(empresa=empresa, armazem=armazem).order_by('-data_contagem')
    if invs.exists():
        print(f"\n📊 ÚLTIMOS INVENTÁRIOS CRIADOS:")
        for inv in invs[:3]:
            print(f"  - {inv.numero}: {inv.tipo_inventario}, {inv.total_items_sistema} itens")
            
            # Procura por items relacionados a FERT-000002
            items = inv.itens.filter(produto=fert)
            if items.exists():
                for item in items:
                    lote_str = f"(Lote: {item.lote.numero})" if item.lote else "(Sem lote)"
                    print(f"    - {item.produto.descricao} {lote_str}: {item.quantidade_sistema} {fert.unidade_medida.sigla}")
            else:
                print(f"    (nenhum item de FERT-000002)")
    else:
        print(f"\n📊 Nenhum inventário criado ainda")
    
except Exception as e:
    print(f"✗ Erro: {e}")
    import traceback
    traceback.print_exc()
