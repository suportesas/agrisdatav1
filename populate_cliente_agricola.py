import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.insert(0, '.')
django.setup()

from cadastros.models import Cliente, PrazoPagamentoPadrao
from empresas.models import Empresa

# Encontrar a empresa Agricola Salutaris
empresa = Empresa.objects.filter(nome='Agricola Salutaris S.A').first()
if not empresa:
    print("❌ Empresa 'Agricola Salutaris S.A' não encontrada")
    exit(1)

print(f"✓ Empresa: {empresa}")

# Pegar o cliente 1
cliente = Cliente.objects.filter(pk=1, empresa=empresa).first()
if not cliente:
    print("❌ Cliente 1 não encontrado")
    exit(1)

print(f"✓ Cliente: {cliente.razao_social}")

# Pegar um preset
preset = PrazoPagamentoPadrao.objects.filter(empresa=empresa, ativo=True).first()
if not preset:
    print("❌ Nenhum preset disponível")
    exit(1)

print(f"✓ Preset: {preset.nome} (ID: {preset.id})")

# Salvar dados no cliente
cliente.prazo_pagamento = 30
cliente.prazo_pagamento_padrao = preset
cliente.save()

print(f"\n✅ Cliente atualizado!")
print(f"  prazo_pagamento: {cliente.prazo_pagamento}")
print(f"  prazo_pagamento_padrao: {cliente.prazo_pagamento_padrao.nome} (ID: {cliente.prazo_pagamento_padrao_id})")

print(f"\n💡 Agora acesse a página com um usuário de Agricola Salutaris:")
print(f"  URL: http://127.0.0.1:8000/cadastros/clientes/{cliente.id}/editar/")
print(f"  Usuários: AS_Daniel, AS_Edson, AS_Junior, test_user, pw_test_admin")
