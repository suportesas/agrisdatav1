import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.insert(0, '.')
django.setup()

from cadastros.models import Cliente, PrazoPagamentoPadrao
from empresas.models import Empresa

# Analisar todos os cliente
print("📊 ANÁLISE DO BANCO DE DADOS - Clientes e Prazos\n")

empresas = Empresa.objects.all()
for empresa in empresas:
    print(f"\n{'='*60}")
    print(f"Empresa: {empresa}")
    print(f"{'='*60}")
    
    # Presets disponíveis
    presets = PrazoPagamentoPadrao.objects.filter(empresa=empresa, ativo=True)
    print(f"\n📋 Presets disponíveis: {presets.count()}")
    for p in presets[:5]:
        print(f"   ID {p.id:3d}: {p.nome:20s} - Termos: {p.termos}")
    
    # Clientes
    clientes = Cliente.objects.filter(empresa=empresa)
    print(f"\n👥 Clientes: {clientes.count()}")
    print(f"\n{'ID':<5} {'Razão Social':<40} {'Prazo (dias)':<15} {'Preset (ID)':<15}")
    print("-" * 75)
    
    for cliente in clientes:
        prazo_val = cliente.prazo_pagamento if cliente.prazo_pagamento else "-"
        preset_val = cliente.prazo_pagamento_padrao_id if cliente.prazo_pagamento_padrao_id else "-"
        print(f"{cliente.id:<5} {cliente.razao_social[:40]:<40} {str(prazo_val):<15} {str(preset_val):<15}")

print(f"\n✅ Análise concluída")
