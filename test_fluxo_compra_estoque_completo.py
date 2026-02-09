#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Teste Completo de Fluxo de Compra até Entrada no Estoque
Simula: Solicitacao -> Cotacao -> Pedido -> Recebimento -> Entrada no Estoque
"""
import os
import sys
import io
import django

# Fix encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
from decimal import Decimal
from datetime import datetime, timedelta
from django.db import transaction
from django.utils import timezone

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model
from empresas.models import Empresa
from cadastros.models import Fornecedor
from produtos.models import Produto, UnidadeMedida, Categoria, NCM
from estoque.models import Armazem, LocalEstocagem, Lote, MovimentacaoEstoque
from compras.models import (
    SolicitacaoCompra, ItemSolicitacaoCompra,
    Cotacao, ItemCotacao, FornecedorCotacao,
    PedidoCompra, ItemPedidoCompra,
    RecebimentoCompra, ItemRecebimento
)

Usuario = get_user_model()

class TestFluxoCompraEstoque:
    """Teste end-to-end do fluxo completo de compra"""
    
    def __init__(self):
        self.empresa = None
        self.usuario = None
        self.produto1 = None
        self.produto2 = None
        self.fornecedor1 = None
        self.armazem = None
        self.local_estoque = None
        self.unidade = None
        
    def setup_dados_base(self):
        """Cria os dados base para o teste"""
        print("\n" + "="*80)
        print("PASSO 1: SETUP DOS DADOS BASE")
        print("="*80)
        
        # Obter empresa (primeira ou criar)
        self.empresa = Empresa.objects.first()
        if not self.empresa:
            self.empresa = Empresa.objects.create(
                nome='Empresa Teste',
                cnpj='12345678000190',
                ativa=True
            )
            print(f"✓ Empresa criada: {self.empresa.nome}")
        else:
            print(f"✓ Empresa encontrada: {self.empresa.nome}")
        
        # Obter usuário (primeiro ou criar)
        self.usuario = Usuario.objects.filter(empresa=self.empresa).first()
        if not self.usuario:
            self.usuario = Usuario.objects.create_user(
                username='teste_compra',
                email='teste@example.com',
                password='senha123',
                empresa=self.empresa,
                is_staff=True
            )
            print(f"✓ Usuário criado: {self.usuario.username}")
        else:
            print(f"✓ Usuário encontrado: {self.usuario.username}")
        
        # Obter unidade de medida
        self.unidade = UnidadeMedida.objects.first()
        if not self.unidade:
            self.unidade = UnidadeMedida.objects.create(
                sigla='KG',
                nome='Quilograma',
                tipo='M'
            )
            print(f"✓ Unidade criada: {self.unidade.nome}")
        else:
            print(f"✓ Unidade encontrada: {self.unidade.nome}")
        
        # Obter NCM
        ncm = NCM.objects.first()
        if not ncm:
            raise Exception("Nenhum NCM cadastrado. Por favor, cadastre um NCM primeiro.")
        print(f"✓ NCM encontrado: {ncm.codigo}")
        
        # Obter/criar categoria
        categoria = Categoria.objects.filter(empresa=self.empresa).first()
        if not categoria:
            categoria = Categoria.objects.create(
                empresa=self.empresa,
                nome='Categoria Teste'
            )
            print(f"✓ Categoria criada: {categoria.nome}")
        else:
            print(f"✓ Categoria encontrada: {categoria.nome}")
        
        # Criar ou obter produtos - usar produtos existentes se disponíveis
        self.produto1 = Produto.objects.filter(ativo=True).first()
        if not self.produto1:
            raise Exception("Nenhum produto ativo encontrado. Por favor, cadastre produtos primeiro.")
        print(f"✓ Produto 1 encontrado: {self.produto1.nome}")
        
        # Tentar encontrar um segundo produto
        self.produto2 = Produto.objects.filter(ativo=True).exclude(pk=self.produto1.pk).first()
        if not self.produto2:
            # Se não houver segundo, usar o mesmo
            self.produto2 = self.produto1
            print(f"✓ Produto 2 (usando o mesmo): {self.produto2.nome}")
        else:
            print(f"✓ Produto 2 encontrado: {self.produto2.nome}")
        
        # Obter/criar fornecedor - usar fornecedor existente se disponível
        self.fornecedor1 = Fornecedor.objects.filter(empresa=self.empresa, ativa=True).first()
        if not self.fornecedor1:
            raise Exception("Nenhum fornecedor ativo encontrado. Por favor, cadastre fornecedores primeiro.")
        print(f"✓ Fornecedor encontrado: {self.fornecedor1.nome}")
        
        # Obter/criar armazém
        self.armazem, created = Armazem.objects.get_or_create(
            empresa=self.empresa,
            codigo='ARM-001',
            defaults={
                'nome': 'Armazém Principal',
                'ativo': True,
            }
        )
        print(f"{'✓ Armazém criado' if created else '✓ Armazém encontrado'}: {self.armazem.nome}")
        
        # Obter/criar local de estocagem
        self.local_estoque = LocalEstocagem.objects.filter(armazem=self.armazem).first()
        if not self.local_estoque:
            self.local_estoque = LocalEstocagem.objects.create(
                armazem=self.armazem,
                codigo='LOC-001',
                descricao='Seção de Fertilizantes',
                tipo='SALA',
                ativo=True,
            )
            print(f"✓ Local criado: {self.local_estoque.codigo}")
        else:
            print(f"✓ Local encontrado: {self.local_estoque.codigo}")
        
        print("\n✓ Setup Base Concluído!")
        return True
    
    def passo_2_criar_solicitacao(self):
        """Passo 2: Criar Solicitação de Compra"""
        print("\n" + "="*80)
        print("PASSO 2: CRIAR SOLICITAÇÃO DE COMPRA")
        print("="*80)
        
        solicitacao = SolicitacaoCompra.objects.create(
            empresa=self.empresa,
            solicitante=self.usuario,
            numero=f'SC-{datetime.now().strftime("%Y%m%d%H%M%S")}',
            status='APROVADA',  # Simular aprovação imediata
            aprovador=self.usuario,
            data_aprovacao=timezone.now(),
            data_necessidade=timezone.now().date() + timedelta(days=5)
        )
        print(f"✓ Solicitação criada: {solicitacao.numero}")
        print(f"  Status: {solicitacao.status}")
        print(f"  Solicitante: {solicitacao.solicitante.username}")
        
        # Adicionar itens
        item1 = ItemSolicitacaoCompra.objects.create(
            solicitacao=solicitacao,
            produto=self.produto1,
            quantidade=Decimal('100.00'),
            unidade_medida=self.unidade,
            selecionado_para_cotar=True,
            status_item='SELECIONADO'
        )
        print(f"\n  Item 1 adicionado:")
        print(f"    Produto: {item1.produto.nome}")
        print(f"    Quantidade: {item1.quantidade} {item1.unidade_medida.sigla}")
        
        item2 = ItemSolicitacaoCompra.objects.create(
            solicitacao=solicitacao,
            produto=self.produto2,
            quantidade=Decimal('50.00'),
            unidade_medida=self.unidade,
            selecionado_para_cotar=True,
            status_item='SELECIONADO'
        )
        print(f"  Item 2 adicionado:")
        print(f"    Produto: {item2.produto.nome}")
        print(f"    Quantidade: {item2.quantidade} {item2.unidade_medida.sigla}")
        
        print("\n✓ Solicitação Concluída!")
        return solicitacao
    
    def passo_3_criar_cotacao(self, solicitacao):
        """Passo 3: Criar Cotação"""
        print("\n" + "="*80)
        print("PASSO 3: CRIAR COTAÇÃO")
        print("="*80)
        
        cotacao = Cotacao.objects.create(
            empresa=self.empresa,
            solicitacao=solicitacao,
            comprador=self.usuario,
            status='EM_ANDAMENTO',
            numero=f'COT-{datetime.now().strftime("%Y%m%d%H%M%S")}'
        )
        print(f"✓ Cotação criada: {cotacao.numero}")
        
        # Adicionar fornecedor à cotação
        fornecedor_cotacao = FornecedorCotacao.objects.create(
            cotacao=cotacao,
            fornecedor=self.fornecedor1
        )
        print(f"  Fornecedor adicionado: {self.fornecedor1.nome}")
        
        # Adicionar itens de cotação com preços
        for idx, item_sol in enumerate(solicitacao.itens.all(), 1):
            preco_unitario = Decimal('50.00') if idx == 1 else Decimal('75.00')
            
            item_cotacao = ItemCotacao.objects.create(
                cotacao=cotacao,
                item_solicitacao=item_sol,
                fornecedor=self.fornecedor1,
                preco_unitario=preco_unitario,
                preco_total=item_sol.quantidade * preco_unitario,
                prazo_entrega=5,
                observacao=f'Cotação para {item_sol.produto.nome}'
            )
            print(f"\n  Item {idx} cotado:")
            print(f"    Produto: {item_sol.produto.nome}")
            print(f"    Preço Unit.: R$ {preco_unitario:.2f}")
            print(f"    Preço Total: R$ {item_cotacao.preco_total:.2f}")
            print(f"    Prazo: {item_cotacao.prazo_entrega} dias")
        
        # Finalizar cotação
        cotacao.status = 'FINALIZADA'
        cotacao.save(update_fields=['status'])
        print(f"\n✓ Cotação Finalizada!")
        
        return cotacao
    
    def passo_4_criar_pedido(self, solicitacao):
        """Passo 4: Criar Pedido de Compra"""
        print("\n" + "="*80)
        print("PASSO 4: CRIAR PEDIDO DE COMPRA")
        print("="*80)
        
        pedido = PedidoCompra.objects.create(
            empresa=self.empresa,
            numero=f'PED-{datetime.now().strftime("%Y%m%d%H%M%S")}',
            solicitacao=solicitacao,
            fornecedor=self.fornecedor1,
            comprador=self.usuario,
            data_pedido=timezone.now(),
            data_entrega_prevista=timezone.now().date() + timedelta(days=5),
            status='PENDENTE_RECEBIMENTO'
        )
        print(f"✓ Pedido criado: {pedido.numero}")
        print(f"  Fornecedor: {pedido.fornecedor.nome}")
        print(f"  Data Pedido: {pedido.data_pedido.strftime('%d/%m/%Y')}")
        print(f"  Entrega Prevista: {pedido.data_entrega_prevista.strftime('%d/%m/%Y')}")
        
        # Adicionar itens do pedido
        for idx, item_sol in enumerate(solicitacao.itens.all(), 1):
            item_ped = ItemPedidoCompra.objects.create(
                pedido=pedido,
                item_solicitacao=item_sol,
                produto=item_sol.produto,
                quantidade=item_sol.quantidade,
                unidade_medida=item_sol.unidade_medida,
                preco_unitario=Decimal('50.00') if idx == 1 else Decimal('75.00'),
                quantidade_recebida=Decimal('0'),
                status='PENDENTE'
            )
            print(f"\n  Item {idx}:")
            print(f"    Produto: {item_ped.produto.nome}")
            print(f"    Quantidade: {item_ped.quantidade} {item_ped.unidade_medida.sigla}")
            print(f"    Preço Unit.: R$ {item_ped.preco_unitario:.2f}")
        
        print(f"\n✓ Pedido Criado com Sucesso!")
        return pedido
    
    def passo_5_criar_recebimento(self, pedido):
        """Passo 5: Criar Recebimento"""
        print("\n" + "="*80)
        print("PASSO 5: CRIAR RECEBIMENTO")
        print("="*80)
        
        recebimento = RecebimentoCompra.objects.create(
            empresa=self.empresa,
            numero=f'REC-{datetime.now().strftime("%Y%m%d%H%M%S")}',
            pedido=pedido,
            fornecedor=pedido.fornecedor,
            nota_fiscal='NF-E-0000001',
            serie_nf='1',
            data_emissao_nf=timezone.now(),
            data_recebimento=timezone.now(),
            recebido_por=self.usuario,
            status='CRIADO',
            observacao='Teste automatizado'
        )
        print(f"✓ Recebimento criado: {recebimento.numero}")
        print(f"  NF-e: {recebimento.nota_fiscal}")
        print(f"  Fornecedor: {recebimento.fornecedor.nome}")
        
        # Adicionar itens ao recebimento
        for idx, item_ped in enumerate(pedido.itens.all(), 1):
            item_rec = ItemRecebimento.objects.create(
                recebimento=recebimento,
                item_pedido=item_ped,
                produto=item_ped.produto,
                quantidade_pedida=item_ped.quantidade,
                quantidade_recebida=item_ped.quantidade,  # Receber tudo
                unidade_medida=item_ped.unidade_medida,
                preco_unitario=item_ped.preco_unitario,
                local_estoque=self.local_estoque,
                status='CONFERIDO'  # Já conferido
            )
            print(f"\n  Item {idx}:")
            print(f"    Produto: {item_rec.produto.nome}")
            print(f"    Qtd Recebida: {item_rec.quantidade_recebida} {item_rec.unidade_medida.sigla}")
            print(f"    Status: {item_rec.status}")
        
        # Atualizar status do recebimento
        recebimento.status = 'CONFERIDO'
        recebimento.save(update_fields=['status'])
        print(f"\n✓ Recebimento Conferido!")
        
        return recebimento
    
    def passo_6_entrada_estoque(self, recebimento):
        """Passo 6: Dar Entrada no Estoque"""
        print("\n" + "="*80)
        print("PASSO 6: DAR ENTRADA NO ESTOQUE")
        print("="*80)
        
        # Verificar estoque inicial
        print("\n📊 ESTOQUE INICIAL:")
        for produto in [self.produto1, self.produto2]:
            produto.refresh_from_db()
            print(f"  {produto.nome}: {produto.estoque_atual} {produto.unidade_medida.sigla}")
        
        # Processar entrada
        print("\n🔄 Processando entrada nos itens...")
        for idx, item in enumerate(recebimento.itens.all(), 1):
            print(f"\n  Item {idx}: {item.produto.nome}")
            
            # Chamar método de registrar movimento
            try:
                item.registrar_movimento_estoque()
                print(f"    ✓ Movimento registrado")
                
                # Verificar lote criado
                if item.lote:
                    item.lote.refresh_from_db()
                    print(f"    ✓ Lote: {item.lote.numero_lote}")
                    print(f"    ✓ Quantidade no Lote: {item.lote.quantidade_atual} {item.lote.unidade_medida.sigla}")
            except Exception as e:
                print(f"    ✗ Erro: {str(e)}")
                raise
        
        # Finalizar recebimento
        recebimento.status = 'FINALIZADO'
        recebimento.save(update_fields=['status'])
        print(f"\n✓ Recebimento Finalizado!")
        
        # Verificar estoque final
        print("\n📊 ESTOQUE FINAL:")
        for produto in [self.produto1, self.produto2]:
            produto.refresh_from_db()
            print(f"  {produto.nome}: {produto.estoque_atual} {produto.unidade_medida.sigla}")
        
        return recebimento
    
    def validar_resultado(self):
        """Validação Final"""
        print("\n" + "="*80)
        print("VALIDAÇÃO FINAL")
        print("="*80)
        
        self.produto1.refresh_from_db()
        self.produto2.refresh_from_db()
        
        esperado_prod1 = Decimal('100.00')
        esperado_prod2 = Decimal('50.00')
        
        resultado = True
        
        print(f"\n✓ Produto 1: {self.produto1.nome}")
        print(f"  Estoque Final: {self.produto1.estoque_atual}")
        print(f"  Esperado: {esperado_prod1}")
        if self.produto1.estoque_atual == esperado_prod1:
            print(f"  ✓ PASSOU")
        else:
            print(f"  ✗ FALHOU")
            resultado = False
        
        print(f"\n✓ Produto 2: {self.produto2.nome}")
        print(f"  Estoque Final: {self.produto2.estoque_atual}")
        print(f"  Esperado: {esperado_prod2}")
        if self.produto2.estoque_atual == esperado_prod2:
            print(f"  ✓ PASSOU")
        else:
            print(f"  ✗ FALHOU")
            resultado = False
        
        # Validar movimentações criadas
        print(f"\n✓ Movimentações de Estoque Criadas:")
        movimentacoes = MovimentacaoEstoque.objects.all().order_by('-id')[:2]
        for mov in movimentacoes:
            print(f"  - {mov.tipo} ({mov.origem}): {mov.quantidade} unidades - {mov.lote.produto.nome}")
        
        return resultado
    
    def executar(self):
        """Executa todo o fluxo de teste"""
        try:
            with transaction.atomic():
                self.setup_dados_base()
                solicitacao = self.passo_2_criar_solicitacao()
                cotacao = self.passo_3_criar_cotacao(solicitacao)
                pedido = self.passo_4_criar_pedido(solicitacao)
                recebimento = self.passo_5_criar_recebimento(pedido)
                recebimento = self.passo_6_entrada_estoque(recebimento)
                
                passou = self.validar_resultado()
                
                print("\n" + "="*80)
                if passou:
                    print("✓✓✓ TESTE COMPLETO PASSOU COM SUCESSO! ✓✓✓")
                else:
                    print("✗✗✗ TESTE FALHOU EM VALIDAÇÕES ✗✗✗")
                print("="*80 + "\n")
                
                return 0 if passou else 1
                
        except Exception as e:
            print("\n" + "="*80)
            print(f"✗✗✗ ERRO DURANTE EXECUÇÃO ✗✗✗")
            print(f"Erro: {str(e)}")
            print("="*80 + "\n")
            import traceback
            traceback.print_exc()
            return 1


if __name__ == '__main__':
    teste = TestFluxoCompraEstoque()
    exit_code = teste.executar()
    sys.exit(exit_code)
