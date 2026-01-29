"""
Script para criar tributação de teste
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from produtos.models import Produto, ProdutoTributacao, NaturezaOperacao
from cadastros.models import CFOP

def criar_tributacao_teste():
    print("=" * 60)
    print("CRIANDO TRIBUTAÇÃO DE TESTE")
    print("=" * 60)
    
    # Buscar produto
    try:
        produto = Produto.objects.get(pk=10)
        print(f"\n✓ Produto encontrado: {produto.nome} (ID: {produto.id})")
    except Produto.DoesNotExist:
        print("\n❌ Produto ID 10 não encontrado!")
        print("\nProdutos disponíveis:")
        for p in Produto.objects.all()[:5]:
            print(f"  - ID {p.id}: {p.nome}")
        return
    
    # Buscar CFOP
    cfop = CFOP.objects.filter(codigo__startswith='5').first()
    if not cfop:
        cfop = CFOP.objects.first()
    
    if cfop:
        print(f"✓ CFOP: {cfop.codigo} - {cfop.descricao}")
    else:
        print("❌ Nenhum CFOP encontrado no banco!")
        return
    
    # Buscar Natureza de Operação
    natureza = NaturezaOperacao.objects.first()
    if natureza:
        print(f"✓ Natureza: {natureza.codigo} - {natureza.descricao}")
    
    # Verificar se já existe tributação para este produto/cfop
    tributacao_existente = ProdutoTributacao.objects.filter(
        produto=produto,
        cfop=cfop
    ).first()
    
    if tributacao_existente:
        print(f"\n⚠️  Já existe tributação para {produto.nome} + {cfop.codigo}")
        print(f"   ID: {tributacao_existente.id}")
        resposta = input("\n   Deseja deletar e criar nova? (s/n): ")
        if resposta.lower() == 's':
            tributacao_existente.delete()
            print("   ✓ Tributação anterior deletada")
        else:
            print("   Operação cancelada")
            return
    
    # Criar tributação de teste
    print("\n" + "─" * 60)
    print("CRIANDO NOVA TRIBUTAÇÃO")
    print("─" * 60)
    
    tributacao = ProdutoTributacao.objects.create(
        produto=produto,
        cfop=cfop,
        natureza_operacao=natureza,
        descricao=natureza.descricao if natureza else "Venda de mercadoria",
        origem_mercadoria='0',  # Nacional
        
        # ICMS - Tributado normalmente
        icms_situacao_tributaria='00',  # Tributada integralmente
        icms_modalidade_base='3',  # Valor da operação
        icms_aliquota=18.00,
        icms_reducao_base=0.00,
        icms_base_calculo=100.00,
        
        # ICMS ST
        icms_st_aliquota=0.00,
        icms_st_mva=0.00,
        icms_st_reducao_base=0.00,
        
        # IPI - Não tributado para produtos agrícolas
        ipi_situacao_tributaria='53',  # Saída Não-Tributada
        ipi_aliquota=0.00,
        ipi_codigo_enquadramento='999',
        
        # PIS
        pis_situacao_tributaria='01',  # Operação Tributável com Alíquota Básica
        pis_aliquota=1.65,
        pis_base_calculo=100.00,
        
        # COFINS
        cofins_situacao_tributaria='01',  # Operação Tributável com Alíquota Básica
        cofins_aliquota=7.60,
        cofins_base_calculo=100.00,
        
        # Controles
        padrao=True,
        ativo=True,
        observacoes="Tributação padrão criada automaticamente para testes"
    )
    
    print("\n✅ TRIBUTAÇÃO CRIADA COM SUCESSO!")
    print(f"\nID: {tributacao.id}")
    print(f"Produto: {tributacao.produto.nome}")
    print(f"CFOP: {tributacao.cfop.codigo} - {tributacao.cfop.descricao}")
    print(f"Descrição: {tributacao.descricao}")
    print(f"Origem da Mercadoria: {tributacao.get_origem_mercadoria_display()}")
    print("\n📋 IMPOSTOS CONFIGURADOS:")
    print(f"  • ICMS: {tributacao.icms_aliquota}% (CST {tributacao.icms_situacao_tributaria})")
    print(f"  • IPI: {tributacao.ipi_aliquota}% (CST {tributacao.ipi_situacao_tributaria})")
    print(f"  • PIS: {tributacao.pis_aliquota}% (CST {tributacao.pis_situacao_tributaria})")
    print(f"  • COFINS: {tributacao.cofins_aliquota}% (CST {tributacao.cofins_situacao_tributaria})")
    print(f"\n🔗 URL: http://127.0.0.1:8000/produtos/{produto.id}/tributacao/{tributacao.id}/editar/")
    print("\n" + "=" * 60)

if __name__ == '__main__':
    criar_tributacao_teste()
