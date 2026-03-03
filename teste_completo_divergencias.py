"""
SCRIPT DE TESTE COMPLETO
Valida toda a funcionalidade de divergências e avaliação
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from compras.models import (
    RecebimentoCompra, TipoDivergencia, DivergenciaRecebimento, 
    AvaliacaoFornecedor, ItemRecebimento
)
from empresas.models import Empresa
from usuarios.models import Usuario
from django.utils import timezone
from decimal import Decimal

def testar_tipos_divergencia():
    """Testa se tipos de divergência foram criados"""
    print("\n" + "="*60)
    print("📋 TESTE 1: Tipos de Divergência")
    print("="*60)
    
    empresa = Empresa.objects.first()
    if not empresa:
        print("❌ Nenhuma empresa encontrada!")
        return False
    
    tipos = TipoDivergencia.objects.filter(empresa=empresa, ativo=True)
    print(f"✅ Empresa: {empresa.nome}")
    print(f"✅ Tipos ativos: {tipos.count()}")
    
    if tipos.exists():
        print("\nTipos cadastrados:")
        for tipo in tipos[:5]:  # Mostra os 5 primeiros
            print(f"  • {tipo.codigo}: {tipo.nome} [{tipo.severidade}]")
        if tipos.count() > 5:
            print(f"  ... e {tipos.count() - 5} mais")
        return True
    else:
        print("⚠️  Nenhum tipo de divergência encontrado.")
        print("    Execute: python criar_tipos_divergencia.py")
        return False

def testar_divergencia_recebimento():
    """Testa criação de divergência em recebimento"""
    print("\n" + "="*60)
    print("⚠️  TESTE 2: Divergência de Recebimento")
    print("="*60)
    
    # Procurar recebimento com status DIVERGENTE
    recebimento = RecebimentoCompra.objects.filter(
        status='DIVERGENTE'
    ).first()
    
    if recebimento:
        print(f"✅ Recebimento encontrado: {recebimento.numero}")
        print(f"   Status: {recebimento.status}")
        
        divergencias = recebimento.divergencias_detalhes.all()
        if divergencias.exists():
            print(f"✅ Divergências registradas: {divergencias.count()}")
            for div in divergencias:
                print(f"   • {div.tipo_divergencia.nome}")
                print(f"     Status: {div.status_divergencia}")
                print(f"     Descrição: {div.descricao_detalhes[:50]}...")
            return True
        else:
            print("⚠️  Recebimento DIVERGENTE mas sem divergências detalhadas")
            return False
    else:
        print("⚠️  Nenhum recebimento com status DIVERGENTE encontrado.")
        print("   Para testar, crie um recebimento e marque como DIVERGENTE")
        return False

def testar_avaliacao_fornecedor():
    """Testa avaliação de fornecedor"""
    print("\n" + "="*60)
    print("⭐ TESTE 3: Avaliação de Fornecedor")
    print("="*60)
    
    # Procurar avaliações
    avaliacoes = AvaliacaoFornecedor.objects.all()
    
    if avaliacoes.exists():
        print(f"✅ Avaliações encontradas: {avaliacoes.count()}")
        for av in avaliacoes[:3]:
            print(f"\n   Fornecedor: {av.fornecedor.nome}")
            print(f"   Recebimento: {av.recebimento.numero}")
            print(f"   Nota Média: {av.nota_media}/5.0")
            print(f"   Recomenda: {'Sim' if av.recomenda else 'Não'}")
            print(f"   Critérios:")
            print(f"      Qualidade: {av.qualidade_produto}/5")
            print(f"      Prazo: {av.prazo_entrega}/5")
            print(f"      Documentação: {av.documentacao}/5")
            print(f"      Atendimento: {av.atendimento}/5")
            print(f"      Preço: {av.preco}/5")
        return True
    else:
        print("⚠️  Nenhuma avaliação registrada ainda.")
        print("   Para testar, finalize um recebimento e avalie o fornecedor")
        return False

def testar_models():
    """Valida estrutura dos modelos"""
    print("\n" + "="*60)
    print("🔍 TESTE 4: Estrutura dos Modelos")
    print("="*60)
    
    # Verificar fields dos modelos
    from django.db import connection
    
    cursor = connection.cursor()
    
    # Verificar TipoDivergencia
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='compras_tipodivergencia'
    """)
    if cursor.fetchone():
        print("✅ Tabela TipoDivergencia criada")
    else:
        print("❌ Tabela TipoDivergencia NÃO encontrada")
        return False
    
    # Verificar DivergenciaRecebimento
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='compras_divergenciarecebimento'
    """)
    if cursor.fetchone():
        print("✅ Tabela DivergenciaRecebimento criada")
    else:
        print("❌ Tabela DivergenciaRecebimento NÃO encontrada")
        return False
    
    # Verificar AvaliacaoFornecedor
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='compras_avaliacaofornecedor'
    """)
    if cursor.fetchone():
        print("✅ Tabela AvaliacaoFornecedor criada")
    else:
        print("❌ Tabela AvaliacaoFornecedor NÃO encontrada")
        return False
    
    print("✅ Todas as tabelas foram criadas com sucesso")
    return True

def testar_calculo_media():
    """Testa cálculo de nota média"""
    print("\n" + "="*60)
    print("📊 TESTE 5: Cálculo de Nota Média")
    print("="*60)
    
    # Procurar avaliação com notas
    av = AvaliacaoFornecedor.objects.filter(
        qualidade_produto__gt=0
    ).first()
    
    if av:
        media_esperada = (
            av.qualidade_produto +
            av.prazo_entrega +
            av.documentacao +
            av.atendimento +
            av.preco
        ) / 5
        
        print(f"✅ Avaliação encontrada: {av.fornecedor.nome}")
        print(f"   Notas: {av.qualidade_produto}, {av.prazo_entrega}, {av.documentacao}, {av.atendimento}, {av.preco}")
        print(f"   Nota armazenada: {av.nota_media}")
        print(f"   Cálculo esperado: {media_esperada:.2f}")
        
        if abs(float(av.nota_media) - media_esperada) < 0.01:
            print("✅ Cálculo correto!")
            return True
        else:
            print("❌ Cálculo incorreto!")
            return False
    else:
        print("⚠️  Nenhuma avaliação para testar cálculo")
        return False

def main():
    """Executa todos os testes"""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*15 + "🧪 TESTE COMPLETO DO SISTEMA" + " "*15 + "║")
    print("║" + " "*12 + "Divergências e Avaliação de Fornecedor" + " "*8 + "║")
    print("╚" + "="*58 + "╝")
    
    testes = [
        ("Modelos", testar_models),
        ("Tipos de Divergência", testar_tipos_divergencia),
        ("Divergência Recebimento", testar_divergencia_recebimento),
        ("Avaliação Fornecedor", testar_avaliacao_fornecedor),
        ("Cálculo de Média", testar_calculo_media),
    ]
    
    resultados = {}
    for nome, teste in testes:
        try:
            resultados[nome] = teste()
        except Exception as e:
            print(f"❌ Erro: {str(e)}")
            resultados[nome] = False
    
    # Sumário
    print("\n" + "="*60)
    print("📋 RESUMO DOS TESTES")
    print("="*60)
    
    passados = sum(1 for r in resultados.values() if r)
    total = len(resultados)
    
    for nome, resultado in resultados.items():
        status = "✅ PASSOU" if resultado else "⚠️  FALHOU"
        print(f"{nome:.<40} {status}")
    
    print("-"*60)
    print(f"Total: {passados}/{total} testes passaram")
    
    if passados == total:
        print("\n🎉 TUDO FUNCIONANDO CORRETAMENTE!")
        print("\n📝 PRÓXIMOS PASSOS:")
        print("   1. Acesse um recebimento pendente")
        print("   2. Clique 'Conferir Recebimento'")
        print("   3. Selecione 'Há Divergências'")
        print("   4. Teste o formulário de divergência")
        print("   5. Finalize a conferência")
        print("   6. Dê entrada no estoque")
        print("   7. Clique 'Avaliar Fornecedor'")
        print("   8. Preencha as 5 estrelas e salve")
    else:
        print("\n⚠️  Alguns testes falharam. Verifique os erros acima.")
    
    print("\n" + "="*60)

if __name__ == '__main__':
    main()
