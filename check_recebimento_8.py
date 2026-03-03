import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from compras.models import RecebimentoCompra, ItemRecebimento

try:
    recebimento = RecebimentoCompra.objects.get(pk=8)
    print(f"Recebimento: {recebimento.numero}")
    print(f"Status: {recebimento.status}")
    print(f"Divergências: {recebimento.divergencias if recebimento.divergencias else 'Nenhuma registrada'}")
    
    print(f"\nItens:")
    for item in recebimento.itens.all():
        print(f"  - {item.quantidade_recebida} {item.unidade_medida.sigla}")
        print(f"    Lote: {item.lote.numero_lote if item.lote else 'Não criado'}")
        
except RecebimentoCompra.DoesNotExist:
    print("Recebimento 8 não encontrado")
except Exception as e:
    print(f"Erro: {e}")
