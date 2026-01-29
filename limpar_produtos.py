import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from produtos.models import Produto

# Limpar todos os produtos
Produto.objects.all().delete()
print("✅ Produtos apagados com sucesso!")
