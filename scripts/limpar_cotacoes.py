
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from compras.models import SolicitacaoCompra, Cotacao, ItemCotacao, FornecedorCotacao

if __name__ == "__main__":
    FornecedorCotacao.objects.all().delete()
    ItemCotacao.objects.all().delete()
    Cotacao.objects.all().delete()
    SolicitacaoCompra.objects.all().delete()
    print("Solicitações e cotações removidas.")
