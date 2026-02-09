#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Teste Simplificado: Cria Recebimento e Processa Entrada no Estoque
"""
import os
import sys
import io
import django
from decimal import Decimal
from datetime import datetime, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model

from empresas.models import Empresa
from cadastros.models import Fornecedor
from produtos.models import Produto
from estoque.models import Armazem, LocalEstocagem
from compras.models import (
    PedidoCompra, ItemPedidoCompra,
    RecebimentoCompra, ItemRecebimento
)

Usuario = get_user_model()

def print_line():
    print("=" * 80)

def print_title(title):
    print("\n")
    print_line()
    print(f"  {title}")
    print_line()

try:
    with transaction.atomic():
        print_title("1. SETUP DADOS BASE")
        
        empresa = Empresa.objects.first()
        usuario = Usuario.objects.filter(empresa=empresa).first()
        produto1 = Produto.objects.filter(ativo=True).first()
        produto2 = Produto.objects.filter(ativo=True).exclude(pk=produto1.pk).first()
        if not produto2:
            produto2 = produto1
        fornecedor = Fornecedor.objects.filter(empresa=empresa, ativa=True).first()
        
        armazem = Armazem.objects.filter(empresa=empresa).first()
        if not armazem:
            armazem = Armazem.objects.create(
                empresa=empresa,
                codigo='ARM-001',
                nome='Armazem Principal',
                ativo=True
            )
        
        local_est = LocalEstocagem.objects.filter(armazem=armazem).first()
        if not local_est:
            local_est = LocalEstocagem.objects.create(
                armazem=armazem,
                codigo='LOC-001',
                descricao='Seccao Principal',
                tipo='SALA',
                ativo=True
            )
        
        print(f"[OK] Empresa: {empresa.nome}")
        print(f"[OK] Usuario: {usuario.username}")
        print(f"[OK] Produto 1: {produto1.nome}")
        print(f"[OK] Produto 2: {produto2.nome}")
        print(f"[OK] Fornecedor: {fornecedor.nome}")
        print(f"[OK] Armazem: {armazem.nome}")
        print(f"[OK] Local: {local_est.codigo}")
        
        # Estoque inicial
        produto1.refresh_from_db()
        produto2.refresh_from_db()
        est_inicial_p1 = produto1.estoque_atual
        est_inicial_p2 = produto2.estoque_atual
        
        print(f"[OK] Estoque Inicial P1: {est_inicial_p1}")
        print(f"[OK] Estoque Inicial P2: {est_inicial_p2}")
        
        # Quantidades para teste
        qty1 = Decimal('100.00')
        qty2 = Decimal('50.00')
        
        print_title("2. CRIAR PEDIDO DE COMPRA (minimo necessario)")
        
        # Criar pedido minimo
        pedido = PedidoCompra.objects.create(
            empresa=empresa,
            numero=f'PED-{datetime.now().strftime("%Y%m%d%H%M%S")}',
            fornecedor=fornecedor,
            comprador=usuario,
            data_pedido=timezone.now(),
            data_entrega_prevista=timezone.now().date() + timedelta(days=5),
            status='PENDENTE_RECEBIMENTO'
        )
        print(f"[OK] Pedido: {pedido.numero}")
        
        # Itens do pedido
        item_ped_1 = ItemPedidoCompra.objects.create(
            pedido=pedido,
            produto=produto1,
            quantidade=qty1,
            unidade_medida=produto1.unidade_medida,
            preco_unitario=Decimal('50.00'),
            quantidade_recebida=Decimal('0'),
            status='PENDENTE'
        )
        print(f"[OK] Item Pedido 1: {produto1.nome} x {qty1}")
        
        item_ped_2 = ItemPedidoCompra.objects.create(
            pedido=pedido,
            produto=produto2,
            quantidade=qty2,
            unidade_medida=produto2.unidade_medida,
            preco_unitario=Decimal('75.00'),
            quantidade_recebida=Decimal('0'),
            status='PENDENTE'
        )
        print(f"[OK] Item Pedido 2: {produto2.nome} x {qty2}")
        
        print_title("3. CRIAR RECEBIMENTO")
        
        recebimento = RecebimentoCompra.objects.create(
            empresa=empresa,
            numero=f'REC-{datetime.now().strftime("%Y%m%d%H%M%S")}',
            pedido=pedido,
            fornecedor=fornecedor,
            nota_fiscal='NF-E-0000001',
            serie_nf='1',
            data_emissao_nf=timezone.now(),
            data_recebimento=timezone.now(),
            recebido_por=usuario,
            status='CRIADO'
        )
        print(f"[OK] Recebimento: {recebimento.numero}")
        
        # Itens do recebimento
        item_rec_1 = ItemRecebimento.objects.create(
            recebimento=recebimento,
            item_pedido=item_ped_1,
            produto=produto1,
            quantidade_pedida=qty1,
            quantidade_recebida=qty1,
            unidade_medida=produto1.unidade_medida,
            preco_unitario=Decimal('50.00'),
            local_estoque=local_est,
            status='CONFERIDO'
        )
        print(f"[OK] Item Recebimento 1: {produto1.nome} x {qty1}")
        
        item_rec_2 = ItemRecebimento.objects.create(
            recebimento=recebimento,
            item_pedido=item_ped_2,
            produto=produto2,
            quantidade_pedida=qty2,
            quantidade_recebida=qty2,
            unidade_medida=produto2.unidade_medida,
            preco_unitario=Decimal('75.00'),
            local_estoque=local_est,
            status='CONFERIDO'
        )
        print(f"[OK] Item Recebimento 2: {produto2.nome} x {qty2}")
        
        # Marcar como conferido
        recebimento.status = 'CONFERIDO'
        recebimento.save()
        print(f"[OK] Recebimento marcado como CONFERIDO")
        
        print_title("4. PROCESSAR ENTRADA NO ESTOQUE")
        
        for idx, item in enumerate([item_rec_1, item_rec_2], 1):
            print(f"\n  Processando Item {idx}: {item.produto.nome}")
            try:
                item.registrar_movimento_estoque()
                print(f"  [OK] Movimento registrado")
                
                if item.lote:
                    item.lote.refresh_from_db()
                    print(f"  [OK] Lote: {item.lote.numero_lote}")
                    print(f"  [OK] Quantidade no Lote: {item.lote.quantidade_atual}")
            except Exception as e:
                print(f"  [ERRO] {str(e)}")
                raise
        
        # Finalizar
        recebimento.status = 'FINALIZADO'
        recebimento.save()
        print(f"\n[OK] Recebimento FINALIZADO")
        
        print_title("5. VALIDACAO FINAL")
        
        produto1.refresh_from_db()
        produto2.refresh_from_db()
        
        est_final_p1 = produto1.estoque_atual
        est_final_p2 = produto2.estoque_atual
        
        esperado_p1 = est_inicial_p1 + qty1
        esperado_p2 = est_inicial_p2 + qty2
        
        passou = True
        
        print(f"\nProduto 1: {produto1.nome}")
        print(f"  Inicial:  {est_inicial_p1}")
        print(f"  Final:    {est_final_p1}")
        print(f"  Esperado: {esperado_p1}")
        if est_final_p1 == esperado_p1:
            print(f"  [OK] PASSOU")
        else:
            print(f"  [ERRO] FALHOU!")
            passou = False
        
        print(f"\nProduto 2: {produto2.nome}")
        print(f"  Inicial:  {est_inicial_p2}")
        print(f"  Final:    {est_final_p2}")
        print(f"  Esperado: {esperado_p2}")
        if est_final_p2 == esperado_p2:
            print(f"  [OK] PASSOU")
        else:
            print(f"  [ERRO] FALHOU!")
            passou = False
        
        print_title("RESULTADO")
        if passou:
            print("[OK] [OK] [OK] TESTE PASSOU COM SUCESSO! [OK] [OK] [OK]")
            sys.exit(0)
        else:
            print("[ERRO] TESTE FALHOU NA VALIDACAO")
            sys.exit(1)

except Exception as e:
    print_title("ERRO DURANTE EXECUCAO")
    print(f"[ERRO] {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
