#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Teste Completo e Simplificado: Solicitude -> Pedido -> Recebimento -> Entrada Estoque
"""
import os
import sys
import io
import django
from decimal import Decimal
from datetime import datetime, timedelta

# Fix encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

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
    SolicitacaoCompra, ItemSolicitacaoCompra,
    PedidoCompra, ItemPedidoCompra,
    RecebimentoCompra, ItemRecebimento
)

Usuario = get_user_model()

def print_section(title):
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

def print_ok(msg):
    print(f"[OK] {msg}")

def print_error(msg):
    print(f"[ERRO] {msg}")

def testar_fluxo():
    """Teste completo do fluxo"""
    
    try:
        with transaction.atomic():
            # 1. SETUP
            print_section("1. SETUP DADOS BASE")
            
            empresa = Empresa.objects.first()
            if not empresa:
                print_error("Nenhuma empresa encontrada!")
                return False
            print_ok(f"Empresa: {empresa.nome}")
            
            usuario = Usuario.objects.filter(empresa=empresa).first()
            if not usuario:
                print_error("Nenhum usuario encontrado!")
                return False
            print_ok(f"Usuario: {usuario.username}")
            
            produto1 = Produto.objects.filter(ativo=True).first()
            if not produto1:
                print_error("Nenhum produto encontrado!")
                return False
            print_ok(f"Produto 1: {produto1.nome}")
            
            produto2 = Produto.objects.filter(ativo=True).exclude(pk=produto1.pk).first()
            if not produto2:
                produto2 = produto1
            print_ok(f"Produto 2: {produto2.nome}")
            
            fornecedor = Fornecedor.objects.filter(empresa=empresa, ativa=True).first()
            if not fornecedor:
                print_error("Nenhum fornecedor encontrado!")
                return False
            print_ok(f"Fornecedor: {fornecedor.nome}")
            
            armazem = Armazem.objects.filter(empresa=empresa).first()
            if not armazem:
                armazem = Armazem.objects.create(
                    empresa=empresa,
                    codigo='ARM-001',
                    nome='Armazem Principal',
                    ativo=True
                )
            print_ok(f"Armazem: {armazem.nome}")
            
            local_est = LocalEstocagem.objects.filter(armazem=armazem).first()
            if not local_est:
                local_est = LocalEstocagem.objects.create(
                    armazem=armazem,
                    codigo='LOC-001',
                    descricao='Seccao Principal',
                    tipo='SALA',
                    ativo=True
                )
            print_ok(f"Local: {local_est.codigo}")
            
            # Estoque inicial
            produto1.refresh_from_db()
            produto2.refresh_from_db()
            est_inicial_p1 = produto1.estoque_atual
            est_inicial_p2 = produto2.estoque_atual
            print_ok(f"Estoque Inicial P1: {est_inicial_p1}")
            print_ok(f"Estoque Inicial P2: {est_inicial_p2}")
            
            # 2. CRIAR SOLICITACAO
            print_section("2. CRIAR SOLICITACAO DE COMPRA")
            
            solicitacao = SolicitacaoCompra.objects.create(
                empresa=empresa,
                solicitante=usuario,
                numero=f'SC-{datetime.now().strftime("%Y%m%d%H%M%S")}',
                status='APROVADA',
                aprovador=usuario,
                data_aprovacao=timezone.now(),
                data_necessidade=timezone.now().date() + timedelta(days=5)
            )
            print_ok(f"Solicitacao: {solicitacao.numero}")
            
            qty1 = Decimal('100.00')
            qty2 = Decimal('50.00')
            
            item_sol_1 = ItemSolicitacaoCompra.objects.create(
                solicitacao=solicitacao,
                produto=produto1,
                quantidade=qty1,
                unidade_medida=produto1.unidade_medida,
                selecionado_para_cotar=True,
                status_item='SELECIONADO'
            )
            print_ok(f"Item 1: {produto1.nome} x {qty1}")
            
            item_sol_2 = ItemSolicitacaoCompra.objects.create(
                solicitacao=solicitacao,
                produto=produto2,
                quantidade=qty2,
                unidade_medida=produto2.unidade_medida,
                selecionado_para_cotar=True,
                status_item='SELECIONADO'
            )
            print_ok(f"Item 2: {produto2.nome} x {qty2}")
            
            # 3. CRIAR PEDIDO
            print_section("3. CRIAR PEDIDO DE COMPRA")
            
            pedido = PedidoCompra.objects.create(
                empresa=empresa,
                numero=f'PED-{datetime.now().strftime("%Y%m%d%H%M%S")}',
                fornecedor=fornecedor,
                comprador=usuario,
                data_pedido=timezone.now(),
                data_entrega_prevista=timezone.now().date() + timedelta(days=5),
                status='PENDENTE_RECEBIMENTO'
            )
            print_ok(f"Pedido: {pedido.numero}")
            
            item_ped_1 = ItemPedidoCompra.objects.create(
                pedido=pedido,
                item_solicitacao=item_sol_1,
                produto=produto1,
                quantidade=qty1,
                unidade_medida=produto1.unidade_medida,
                preco_unitario=Decimal('50.00'),
                quantidade_recebida=Decimal('0'),
                status='PENDENTE'
            )
            print_ok(f"Item Pedido 1: {qty1}")
            
            item_ped_2 = ItemPedidoCompra.objects.create(
                pedido=pedido,
                item_solicitacao=item_sol_2,
                produto=produto2,
                quantidade=qty2,
                unidade_medida=produto2.unidade_medida,
                preco_unitario=Decimal('75.00'),
                quantidade_recebida=Decimal('0'),
                status='PENDENTE'
            )
            print_ok(f"Item Pedido 2: {qty2}")
            
            # 4. CRIAR RECEBIMENTO
            print_section("4. CRIAR RECEBIMENTO")
            
            recebimento = RecebimentoCompra.objects.create(
                empresa=empresa,
                numero=f'REC-{datetime.now().strftime("%Y%m%d%H%M%S")}',
                pedido=pedido,
                fornecedor=fornecedor,
                nota_fiscal='NF-TEST-001',
                serie_nf='1',
                data_emissao_nf=timezone.now(),
                data_recebimento=timezone.now(),
                recebido_por=usuario,
                status='CRIADO'
            )
            print_ok(f"Recebimento: {recebimento.numero}")
            
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
            print_ok(f"Item Recebimento 1: {qty1}")
            
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
            print_ok(f"Item Recebimento 2: {qty2}")
            
            # Marcar recebimento como conferido
            recebimento.status = 'CONFERIDO'
            recebimento.save()
            print_ok("Recebimento marcado como CONFERIDO")
            
            # 5. ENTRADA NO ESTOQUE
            print_section("5. DAR ENTRADA NO ESTOQUE")
            
            try:
                for idx, item in enumerate([item_rec_1, item_rec_2], 1):
                    print(f"\n  Processando Item {idx}...")
                    item.registrar_movimento_estoque()
                    print(f"  [OK] Movimento registrado para {item.produto.nome}")
                    
                    if item.lote:
                        item.lote.refresh_from_db()
                        print(f"  [OK] Lote criado: {item.lote.numero_lote}")
                        print(f"       Quantidade: {item.lote.quantidade_atual}")
            except Exception as e:
                print_error(f"Erro ao registrar movimento: {str(e)}")
                raise
            
            # Finalizar recebimento
            recebimento.status = 'FINALIZADO'
            recebimento.save()
            print_ok("Recebimento FINALIZADO")
            
            # 6. VALIDACAO
            print_section("6. VALIDACAO FINAL")
            
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
                print(f"  [ERRO] FALHOU")
                passou = False
            
            print(f"\nProduto 2: {produto2.nome}")
            print(f"  Inicial:  {est_inicial_p2}")
            print(f"  Final:    {est_final_p2}")
            print(f"  Esperado: {esperado_p2}")
            if est_final_p2 == esperado_p2:
                print(f"  [OK] PASSOU")
            else:
                print(f"  [ERRO] FALHOU")
                passou = False
            
            print_section("RESULTADO FINAL")
            if passou:
                print("[OK] [OK] [OK] TESTE COMPLETO PASSOU COM SUCESSO! [OK] [OK] [OK]")
                return True
            else:
                print("[ERRO] [ERRO] TESTE FALHOU NA VALIDACAO [ERRO] [ERRO]")
                return False
            
    except Exception as e:
        print_section("ERRO DURANTE EXECUCAO")
        print_error(str(e))
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    sucesso = testar_fluxo()
    sys.exit(0 if sucesso else 1)
