#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Teste via Shell Django - Fluxo Completo Solicitacao -> Cotacao -> Pedido -> Recebimento
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from decimal import Decimal
from datetime import datetime, timedelta
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model

from empresas.models import Empresa
from cadastros.models import Fornecedor
from produtos.models import Produto
from estoque.models import Armazem, LocalEstocagem
from compras.models import (
    SolicitacaoCompra, ItemSolicitacaoCompra,
    Cotacao, ItemCotacao,
    PedidoCompra, ItemPedidoCompra,
    RecebimentoCompra, ItemRecebimento
)

Usuario = get_user_model()

print("\n[LOG] Iniciando teste...")

# Buscar dados base
empresa = Empresa.objects.first()
usuario = Usuario.objects.filter(empresa=empresa).first()
produto1 = Produto.objects.filter(ativo=True).first()
produto2 = Produto.objects.filter(ativo=True).exclude(pk=produto1.pk).first()
if not produto2:
    produto2 = produto1
fornecedor = Fornecedor.objects.filter(empresa=empresa, ativa=True).first()

print(f"[OK] Empresa: {empresa.nome}")
print(f"[OK] Usuario: {usuario.username}")
print(f"[OK] Produtos: {produto1.nome}, {produto2.nome}")
print(f"[OK] Fornecedor: {fornecedor.nome}")

# Estoque inicial
produto1.refresh_from_db()
produto2.refresh_from_db()
est_inicial_p1 = produto1.estoque_atual
est_inicial_p2 = produto2.estoque_atual

print(f"\n[ESTOQUE INICIAL]")
print(f"  P1: {est_inicial_p1}")
print(f"  P2: {est_inicial_p2}")

try:
    with transaction.atomic():
        qty1 = Decimal('100.00')
        qty2 = Decimal('50.00')
        
        # PASSO 1: Criar Solicitacao
        print(f"\n[SOLICITACAO]")
        solicitacao = SolicitacaoCompra.objects.create(
            empresa=empresa,
            solicitante=usuario,
            numero=f'SC-{datetime.now().strftime("%Y%m%d%H%M%S")}',
            status='APROVADA',
            aprovador=usuario,
            data_aprovacao=timezone.now(),
            data_necessidade=timezone.now().date() + timedelta(days=5)
        )
        print(f"  Criada: {solicitacao.numero}")
        
        item_sol_1 = ItemSolicitacaoCompra.objects.create(
            solicitacao=solicitacao,
            produto=produto1,
            quantidade=qty1,
            unidade_medida=produto1.unidade_medida,
            selecionado_para_cotar=True,
            status_item='SELECIONADO'
        )
        
        item_sol_2 = ItemSolicitacaoCompra.objects.create(
            solicitacao=solicitacao,
            produto=produto2,
            quantidade=qty2,
            unidade_medida=produto2.unidade_medida,
            selecionado_para_cotar=True,
            status_item='SELECIONADO'
        )
        print(f"  Items: 2")
        
        # PASSO 2: Criar Cotacao
        print(f"\n[COTACAO]")
        cotacao = Cotacao.objects.create(
            empresa=empresa,
            solicitacao=solicitacao,
            comprador=usuario,
            numero=f'COT-{datetime.now().strftime("%Y%m%d%H%M%S")}',
            status='FINALIZADA'
        )
        print(f"  Criada: {cotacao.numero}")
        
        # Criar items de cotação e propostas
        item_cot_1 = ItemCotacao.objects.create(
            cotacao=cotacao,
            item_solicitacao=item_sol_1,
            fornecedor=fornecedor,
            preco_unitario=Decimal('50.00'),
            preco_total=qty1 * Decimal('50.00'),
            prazo_entrega=5,
            observacao='Propo ta para item 1'
        )
        
        item_cot_2 = ItemCotacao.objects.create(
            cotacao=cotacao,
            item_solicitacao=item_sol_2,
            fornecedor=fornecedor,
            preco_unitario=Decimal('75.00'),
            preco_total=qty2 * Decimal('75.00'),
            prazo_entrega=5,
            observacao='Proposta para item 2'
        )
        print(f"  Items: 2")
        
        # PASSO 3: Criar PedidoCompra
        print(f"\n[PEDIDO]")
        pedido = PedidoCompra.objects.create(
            empresa=empresa,
            numero=f'PED-{datetime.now().strftime("%Y%m%d%H%M%S")}',
            cotacao=cotacao,
            fornecedor=fornecedor,
            comprador=usuario,
            data_pedido=timezone.now(),
            data_entrega_prevista=timezone.now().date() + timedelta(days=5),
            status='PENDENTE_RECEBIMENTO'
        )
        print(f"  Criado: {pedido.numero}")
        
        item_ped_1 = ItemPedidoCompra.objects.create(
            pedido=pedido,
            proposta_fornecedor=item_cot_1,
            produto=produto1,
            quantidade_pedida=qty1,
            unidade_medida=produto1.unidade_medida,
            preco_unitario=Decimal('50.00'),
            preco_total=qty1 * Decimal('50.00')
        )
        
        item_ped_2 = ItemPedidoCompra.objects.create(
            pedido=pedido,
            proposta_fornecedor=item_cot_2,
            produto=produto2,
            quantidade_pedida=qty2,
            unidade_medida=produto2.unidade_medida,
            preco_unitario=Decimal('75.00'),
            preco_total=qty2 * Decimal('75.00')
        )
        print(f"  Items: 2")
        
        # PASSO 4: Criar Recebimento
        print(f"\n[RECEBIMENTO]")
        
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
        
        recebimento = RecebimentoCompra.objects.create(
            empresa=empresa,
            numero=f'REC-{datetime.now().strftime("%Y%m%d%H%M%S")}',
            pedido=pedido,
            fornecedor=fornecedor,
            nota_fiscal=f'NF-{datetime.now().strftime("%Y%m%d%H%M%S")}',
            serie_nf='1',
            data_emissao_nf=timezone.now(),
            data_recebimento=timezone.now(),
            recebido_por=usuario,
            status='CRIADO'
        )
        print(f"  Criado: {recebimento.numero}")
        
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
        print(f"  Items: 2")
        
        # Marcar como conferido
        recebimento.status = 'CONFERIDO'
        recebimento.save()
        print(f"  Status: CONFERIDO")
        
        # PASSO 5: Entrada no Estoque
        print(f"\n[ENTRADA ESTOQUE]")
        
        for idx, item in enumerate([item_rec_1, item_rec_2], 1):
            print(f"\n  Item {idx}: {item.produto.nome}")
            item.registrar_movimento_estoque()
            print(f"    [OK] Movimento registrado")
            
            if item.lote:
                item.lote.refresh_from_db()
                print(f"    [OK] Lote: {item.lote.numero_lote}")
                print(f"    [OK] Qtd: {item.lote.quantidade_atual}")
        
        # Finalizar
        recebimento.status = 'FINALIZADO'
        recebimento.save()
        print(f"\n  [OK] Recebimento FINALIZADO")
        
        # VALIDACAO
        print(f"\n[VALIDACAO]")
        
        produto1.refresh_from_db()
        produto2.refresh_from_db()
        
        est_final_p1 = produto1.estoque_atual
        est_final_p2 = produto2.estoque_atual
        
        esperado_p1 = est_inicial_p1 + qty1
        esperado_p2 = est_inicial_p2 + qty2
        
        passou = True
        
        print(f"\nP1: {produto1.nome}")
        print(f"  Inicial:  {est_inicial_p1}")
        print(f"  Final:    {est_final_p1}")
        print(f"  Esperado: {esperado_p1}")
        
        if est_final_p1 == esperado_p1:
            print(f"  [OK] PASSOU")
        else:
            print(f"  [ERRO] FALHOU")
            passou = False
        
        print(f"\nP2: {produto2.nome}")
        print(f"  Inicial:  {est_inicial_p2}")
        print(f"  Final:    {est_final_p2}")
        print(f"  Esperado: {esperado_p2}")
        
        if est_final_p2 == esperado_p2:
            print(f"  [OK] PASSOU")
        else:
            print(f"  [ERRO] FALHOU")
            passou = False
        
        print(f"\n{'='*80}")
        if passou:
            print("[OK] TESTE COMPLETO PASSOU COM SUCESSO!")
        else:
            print("[ERRO] TESTE FALHOU")
        print(f"{'='*80}\n")

except Exception as e:
    print(f"\n[ERRO] {str(e)}")
    import traceback
    traceback.print_exc()
