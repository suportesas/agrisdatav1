import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from compras.models import SolicitacaoCompra, ItemSolicitacaoCompra, Cotacao

# Buscar a solicitação SC-000003
try:
    sol = SolicitacaoCompra.objects.get(numero='SC-000003')
    
    print(f"\n{'='*60}")
    print(f"DIAGNÓSTICO DA SOLICITAÇÃO: {sol.numero}")
    print(f"{'='*60}")
    print(f"\nStatus atual: {sol.status} ({sol.get_status_display()})")
    print(f"Total de itens: {sol.itens.count()}")
    print(f"Percentual cotado: {sol.calcular_percentual_cotado()}%")
    
    print(f"\n{'='*60}")
    print("DETALHAMENTO DOS ITENS:")
    print(f"{'='*60}")
    
    for idx, item in enumerate(sol.itens.all(), 1):
        print(f"\n{idx}. Produto: {item.produto.nome}")
        print(f"   Status do item: {item.status_item} ({item.get_status_item_display()})")
        print(f"   Quantidade: {item.quantidade} {item.unidade_medida.sigla}")
    
    print(f"\n{'='*60}")
    print("COTAÇÕES RELACIONADAS:")
    print(f"{'='*60}")
    
    cotacoes = Cotacao.objects.filter(solicitacao=sol)
    if cotacoes.exists():
        for cot in cotacoes:
            print(f"\n- Cotação: {cot.numero}")
            print(f"  Status: {cot.status} ({cot.get_status_display()})")
            print(f"  Data: {cot.data_cotacao.strftime('%d/%m/%Y %H:%M')}")
            print(f"  Itens da cotação:")
            
            for item_cot in cot.itens.all():
                print(f"    * {item_cot.produto.nome}")
                propostas = item_cot.propostas.all()
                print(f"      Propostas: {propostas.count()}")
                for prop in propostas:
                    status_sel = "✓ SELECIONADA" if prop.selecionado else "  Não selecionada"
                    print(f"        - {prop.fornecedor.nome}: R$ {prop.preco_unitario} [{status_sel}]")
    else:
        print("\nNenhuma cotação encontrada para esta solicitação.")
    
    print(f"\n{'='*60}")
    print("ANÁLISE:")
    print(f"{'='*60}")
    
    itens_cotados = sol.itens.filter(status_item='COTADO').count()
    itens_pendentes = sol.itens.exclude(status_item='COTADO').count()
    
    print(f"\nItens COTADOS: {itens_cotados}")
    print(f"Itens PENDENTES: {itens_pendentes}")
    
    if sol.status == 'TOTALMENTE_COTADA' and sol.calcular_percentual_cotado() < 100:
        print(f"\n⚠️  PROBLEMA IDENTIFICADO!")
        print(f"   Status está como TOTALMENTE_COTADA mas percentual é {sol.calcular_percentual_cotado()}%")
        print(f"\n   CORREÇÃO NECESSÁRIA:")
        print(f"   - Reexecutar atualizar_status_cotacao()")
        
        # Aplicar correção
        sol.atualizar_status_cotacao()
        print(f"\n✓ Status atualizado para: {sol.status}")
    
    print(f"\n{'='*60}\n")

except SolicitacaoCompra.DoesNotExist:
    print("\n❌ Solicitação SC-000003 não encontrada no banco de dados.")
except Exception as e:
    print(f"\n❌ Erro ao diagnosticar: {e}")
    import traceback
    traceback.print_exc()
