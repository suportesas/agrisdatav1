#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Teste Simplificado: Cria Recebimento Direto e Processa Entrada no Estoque
Simples: Recebimento -> Entrada no Estoque (sem exigencia de Pedido/Cotacao)
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
from compras.models import RecebimentoCompra, ItemRecebimento

Usuario = get_user_model()

print("\n" + "="*80)
print("  TESTE: Solicitacao -> Recebimento -> Entrada Estoque")
print("="*80)

# Buscar dados
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

print("\n[DADOS BASE]")
print(f"  Empresa: {empresa.nome}")
print(f"  Usuario: {usuario.username}")
print(f"  Prod 1: {produto1.nome}")
print(f"  Prod 2: {produto2.nome}")
print(f"  Fornecedor: {fornecedor.nome}")
print(f"  Armazem: {armazem.nome}")
print(f"  Local: {local_est.codigo}")

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
        
        print(f"\n[PASSO 1: CRIAR RECEBIMENTO]")
        
        recebimento = RecebimentoCompra.objects.create(
            empresa=empresa,
            numero=f'REC-{datetime.now().strftime("%Y%m%d%H%M%S")}',
            pedido=None,  # Sem pedido
            fornecedor=fornecedor,
            nota_fiscal=f'NF-E-{datetime.now().strftime("%Y%m%d%H%M%S")}',
            data_emissao_nf=timezone.now(),
            data_recebimento=timezone.now(),
            recebido_por=usuario,
            status='CRIADO',
            valor_total_nf=Decimal('0.00')
        )
        print(f"  Recebimento: {recebimento.numero}")
        
        print(f"\n[PASSO 2: ADICIONAR ITENS]")
        
        item_rec_1 = ItemRecebimento.objects.create(
            recebimento=recebimento,
            item_pedido=None,  # Sem item de pedido
            produto=produto1,
            quantidade_recebida=qty1,
            unidade_medida=produto1.unidade_medida,
            preco_unitario=Decimal('50.00'),
            local_estoque=local_est
        )
        print(f"  Item 1: {produto1.nome} x {qty1}")
        
        item_rec_2 = ItemRecebimento.objects.create(
            recebimento=recebimento,
            item_pedido=None,
            produto=produto2,
            quantidade_recebida=qty2,
            unidade_medida=produto2.unidade_medida,
            preco_unitario=Decimal('75.00'),
            local_estoque=local_est
        )
        print(f"  Item 2: {produto2.nome} x {qty2}")
        
        # Marcar como conferido
        recebimento.status = 'CONFERIDO'
        recebimento.save()
        print(f"  Status: CONFERIDO")
        
        print(f"\n[PASSO 3: PROCESSAR ENTRADA NO ESTOQUE]")
        
        for idx, item in enumerate([item_rec_1, item_rec_2], 1):
            print(f"\n  Item {idx}: {item.produto.nome}")
            try:
                item.registrar_movimento_estoque()
                print(f"    OK: Movimento registrado")
                
                if item.lote:
                    item.lote.refresh_from_db()
                    print(f"    OK: Lote {item.lote.numero_lote}")
                    print(f"    OK: Qtd {item.lote.quantidade_atual}")
            except Exception as e:
                print(f"    ERRO: {str(e)}")
                raise
        
        # Finalizar
        recebimento.status = 'FINALIZADO'
        recebimento.save()
        print(f"\n  OK: Recebimento FINALIZADO")
        
        print(f"\n[PASSO 4: VALIDACAO]")
        
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
            print(f"  OK: PASSOU")
        else:
            print(f"  ERRO: FALHOU")
            passou = False
        
        print(f"\nP2: {produto2.nome}")
        print(f"  Inicial:  {est_inicial_p2}")
        print(f"  Final:    {est_final_p2}")
        print(f"  Esperado: {esperado_p2}")
        if est_final_p2 == esperado_p2:
            print(f"  OK: PASSOU")
        else:
            print(f"  ERRO: FALHOU")
            passou = False
        
        print(f"\n" + "="*80)
        if passou:
            print("  OK OK OK TESTE PASSOU COM SUCESSO! OK OK OK")
        else:
            print("  ERRO: TESTE FALHOU")
        print("="*80 + "\n")

except Exception as e:
    print(f"\n[ERRO] {str(e)}")
    import traceback
    traceback.print_exc()
