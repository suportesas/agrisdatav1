import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from compras.models import TipoDivergencia
from empresas.models import Empresa

# Verificar se já existem tipos de divergência
for empresa in Empresa.objects.filter(ativo=True):
    count = TipoDivergencia.objects.filter(empresa=empresa).count()
    print(f"Empresa: {empresa.nome} - Tipos de Divergência: {count}")
    
    # Listar os tipos
    for tipo in TipoDivergencia.objects.filter(empresa=empresa):
        print(f"  - {tipo.codigo}: {tipo.nome}")
