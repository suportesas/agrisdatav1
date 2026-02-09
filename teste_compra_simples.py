#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Teste do Fluxo Simples de Compras
Demonstra compra rápida sem cotação
"""
import os
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import transaction
from django.utils import timezone

from empresas.models import Empresa
from usuarios.models import Usuario
from cadastros.models import Fornecedor
from produtos.models import Produto
from compras.models import PedidoCompra, ItemPedidoCompra
from core.models import ConfiguracaoSistema


def teste_compra_simples():
    """
    Testa criação de pedido de compra SEM cotação (modo simples)
    """
    print("=" * 80)
    print("🧪 TESTE: Fluxo Simples de Compras (Sem Cotação)")
    print("=" * 80)
    
    try:
        # 1. Obter dados básicos
        empresa = Empresa.objects.first()
        usuario = Usuario.objects.filter(empresa=empresa, is_active=True).first()
        fornecedor = Fornecedor.objects.filter(empresa=empresa, ativa=True).first()
        produtos = Produto.objects.filter(
            categoria__empresa=empresa,
            ativo=True
        )[:3]  # Pegar 3 produtos
        
        print(f"\n📊 Dados de Teste:")
        print(f"  Empresa: {empresa.nome}")
        print(f"  Usuário: {usuario.first_name} {usuario.last_name}")
        print(f"  Fornecedor: {fornecedor.nome}")
        print(f"  Produtos selecionados: {produtos.count()}")
        
        # 2. Verificar configuração
        config = ConfiguracaoSistema.get_config(empresa)
        print(f"\n⚙️ Configuração Atual:")
        print(f"  Modo Compras: {config.modo_compras}")
        print(f"  Pode criar pedido sem cotação? {config.pode_criar_pedido_sem_cotacao()}")
        print(f"  Modo simples ativo? {config.modo_simples_ativo()}")
        
        if not config.modo_simples_ativo():
            print("\n❌ Modo simples não está ativo. Teste cancelado.")
            return
        
        # 3. Criar pedido SEM cotação
        with transaction.atomic():
            print("\n🛒 Criando Pedido de Compra Simples...")
            
            # Gerar número do pedido
            ultimo_pedido = PedidoCompra.objects.filter(
                empresa=empresa
            ).order_by('-id').first()
            
            numero = f"PC-{(ultimo_pedido.id + 1) if ultimo_pedido else 1:06d}"
            
            pedido = PedidoCompra.objects.create(
                empresa=empresa,
                numero=numero,
                cotacao=None,  # 🎯 SEM COTAÇÃO! (modo simples)
                fornecedor=fornecedor,
                comprador=usuario,
                status='PENDENTE',
                condicao_pagamento='30 dias',
                prazo_entrega_dias=7,
                observacoes='Pedido criado no modo simples - compra rápida'
            )
            
            print(f"  ✅ Pedido criado: {pedido.numero}")
            print(f"  📋 Status: {pedido.status}")
            print(f"  📝 Cotação: {pedido.cotacao or 'NENHUMA (modo simples)'}")
            
            # 4. Adicionar itens ao pedido
            print(f"\n📦 Adicionando Itens ao Pedido...")
            total_pedido = Decimal('0.00')
            
            for i, produto in enumerate(produtos, 1):
                quantidade = Decimal(f'{i * 10}.00')  # 10, 20, 30 litros
                preco_unitario = produto.preco_custo or Decimal('50.00')
                preco_total = quantidade * preco_unitario
                
                item = ItemPedidoCompra.objects.create(
                    pedido=pedido,
                    proposta_fornecedor=None,  # 🎯 SEM PROPOSTA! (modo simples)
                    produto=produto,
                    quantidade_pedida=quantidade,
                    quantidade_recebida=Decimal('0.00'),
                    unidade_medida=produto.unidade_compra,
                    preco_unitario=preco_unitario,
                    preco_total=preco_total,
                    especificacao=produto.descricao,
                )
                
                print(f"  Item {i}: {produto.descricao}")
                print(f"    Quantidade: {quantidade} {produto.unidade_compra.sigla}")
                print(f"    Preço Unit: R$ {preco_unitario}")
                print(f"    Total: R$ {preco_total}")
                
                total_pedido += preco_total
            
            # 5. Atualizar valor total do pedido
            pedido.valor_total = total_pedido
            pedido.save()
            
            print(f"\n💰 Valor Total do Pedido: R$ {total_pedido}")
            
        # 6. Verificar dados salvos
        print(f"\n✅ Verificando Dados Salvos...")
        pedido_salvo = PedidoCompra.objects.get(id=pedido.id)
        
        print(f"  Pedido #{pedido_salvo.numero}")
        print(f"  Cotação: {pedido_salvo.cotacao or '❌ SEM COTAÇÃO (modo simples)'}")
        print(f"  Fornecedor: {pedido_salvo.fornecedor.nome}")
        print(f"  Itens: {pedido_salvo.itens.count()}")
        print(f"  Valor Total: R$ {pedido_salvo.valor_total}")
        
        # Listar itens
        print(f"\n  📋 Itens do Pedido:")
        for item in pedido_salvo.itens.all():
            print(f"    - {item.produto.descricao}")
            print(f"      Proposta: {item.proposta_fornecedor or '❌ SEM PROPOSTA (modo simples)'}")
            print(f"      Qtd: {item.quantidade_pedida} {item.unidade_medida.sigla}")
            print(f"      Valor: R$ {item.preco_total}")
        
        print("\n" + "=" * 80)
        print("✅ TESTE CONCLUÍDO COM SUCESSO!")
        print("=" * 80)
        print(f"\n🎉 Pedido #{pedido_salvo.numero} criado sem cotação prévia!")
        print(f"⚡ Modo Simples: 3 produtos adicionados em segundos!")
        print(f"📊 Total: R$ {pedido_salvo.valor_total}")
        print(f"\n💡 Próximo passo: Criar recebimento rápido para este pedido")
        
        return pedido_salvo
        
    except Exception as e:
        print(f"\n❌ ERRO: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == '__main__':
    pedido = teste_compra_simples()
    
    if pedido:
        print(f"\n🔗 Pedido criado com ID: {pedido.id}")
        print(f"   Número: {pedido.numero}")
