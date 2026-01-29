"""
Script para testar o salvamento de tributação com origem_mercadoria
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from produtos.models import Produto, ProdutoTributacao
from produtos.forms import ProdutoTributacaoForm
from cadastros.models import CFOP
from empresas.models import Empresa

def testar_form():
    print("=" * 80)
    print("TESTE DE SALVAMENTO - TRIBUTAÇÃO")
    print("=" * 80)
    
    # Buscar dados necessários
    produto = Produto.objects.get(pk=10)
    cfop = CFOP.objects.first()
    empresa = Empresa.objects.first()
    
    print(f"\n✓ Produto: {produto.nome}")
    print(f"✓ CFOP: {cfop.codigo}")
    print(f"✓ Empresa: {empresa.nome}")
    
    # Dados do formulário
    form_data = {
        'produto': produto.id,
        'cfop': cfop.id,
        'origem_mercadoria': '0',
        'descricao': 'Teste de tributação',
        
        # ICMS
        'icms_situacao_tributaria': '00',
        'icms_modalidade_base': '3',
        'icms_aliquota': '18.00',
        'icms_reducao_base': '0.00',
        'icms_base_calculo': '100.00',
        
        # ICMS ST
        'icms_st_aliquota': '0.00',
        'icms_st_mva': '0.00',
        'icms_st_reducao_base': '0.00',
        
        # IPI
        'ipi_situacao_tributaria': '53',
        'ipi_aliquota': '0.00',
        'ipi_codigo_enquadramento': '999',
        
        # PIS
        'pis_situacao_tributaria': '01',
        'pis_aliquota': '1.65',
        'pis_base_calculo': '100.00',
        
        # COFINS
        'cofins_situacao_tributaria': '01',
        'cofins_aliquota': '7.60',
        'cofins_base_calculo': '100.00',
        
        # Controle
        'padrao': True,
        'ativo': True,
        'observacoes': 'Teste'
    }
    
    print("\n" + "─" * 80)
    print("TESTANDO FORMULÁRIO")
    print("─" * 80)
    
    # Criar formulário
    form = ProdutoTributacaoForm(data=form_data, empresa=empresa)
    
    print(f"\nFormulário válido: {form.is_valid()}")
    
    if not form.is_valid():
        print("\n❌ ERROS NO FORMULÁRIO:")
        for field, errors in form.errors.items():
            print(f"  • {field}: {', '.join(errors)}")
    else:
        print("\n✅ Formulário válido!")
        
        # Tentar salvar
        try:
            tributacao = form.save(commit=False)
            tributacao.produto = produto
            tributacao.save()
            
            print(f"\n✅ TRIBUTAÇÃO SALVA COM SUCESSO!")
            print(f"ID: {tributacao.id}")
            print(f"Origem: {tributacao.get_origem_mercadoria_display()}")
            
            # Limpar teste
            tributacao.delete()
            print("\n✓ Registro de teste deletado")
            
        except Exception as e:
            print(f"\n❌ ERRO AO SALVAR: {e}")
    
    print("\n" + "=" * 80)

if __name__ == '__main__':
    testar_form()
