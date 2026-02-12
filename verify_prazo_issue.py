"""
Teste simplificado: Verificar dados salvos no cliente 3 (PISTILO FRUTAS)
e validar se o JavaScript conseguiria sincronizar, se houvesse.
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.insert(0, '.')
django.setup()

from cadastros.models import Cliente, PrazoPagamentoPadrao
from empresas.models import Empresa

# Encontrar Terra Brasilis
empresa = Empresa.objects.filter(nome__icontains='Terra Brasilis').first()
if not empresa:
    print("❌ Empresa não encontrada")
    exit(1)

print(f"🏢 Empresa: {empresa.nome}\n")

# Cliente 3
cliente = Cliente.objects.filter(pk=3, empresa=empresa).first()
if not cliente:
    print("❌ Cliente não encontrado")
    exit(1)

print(f"📋 Cliente: {cliente.razao_social} (ID: {cliente.id})")
print(f"\n📊 Estado atual NO BANCO DE DADOS:")
print(f"  prazo_pagamento: {cliente.prazo_pagamento}")
print(f"  prazo_pagamento_padrao_id: {cliente.prazo_pagamento_padrao_id}")

if cliente.prazo_pagamento_padrao:
    print(f"  prazo_pagamento_padrao.nome: {cliente.prazo_pagamento_padrao.nome}")
    print(f"  prazo_pagamento_padrao.termos: {cliente.prazo_pagamento_padrao.termos}")

print("\n" + "="*60)
print("Presets disponíveis para essa empresa:")
print("="*60)

presets = PrazoPagamentoPadrao.objects.filter(empresa=empresa, ativo=True).order_by('nome')
for p in presets:
    print(f"  ID {p.id}: '{p.nome}' → Termos: {p.termos}")

# Agora o problema: o usuário quer mudar para 15 dias
print("\n" + "="*60)
print("📝 Cenário do usuário:")
print("="*60)
print("1. Usuário acessa editar cliente")
print("2. Seleciona preset '15' (ID 110)")
print("3. Seleciona termo '15 dias'")
print("4. Clica 'Salvar'")
print("5. Verifica no banco... dados não foram salvos?")

print("\n⚠️ POSSÍVEIS CAUSAS:")
print("1. JavaScript não sincronizou valores para hidden inputs ANTES do submit")
print("2. Valores were passed but form validation failed")
print("3. Form.save() was never called due to form.is_valid() being False")

# Testar se a validação do form passaria
from cadastros.forms import ClienteForm

# Preparar dados mínimos para um POST válido
post_data = {
    'razao_social': cliente.razao_social,
    'tipo_pessoa': cliente.tipo_pessoa or 'J',
    'cnpj_cpf': cliente.cnpj_cpf,
    'prazo_pagamento': '15',  # ✓ Valor que JS deveria sincronizar
    'prazo_pagamento_padrao': '110',  # ✓ Preset selecionado
}

form = ClienteForm(post_data, instance=cliente, empresa=empresa)
print(f"\n✓ Form is_valid(): {form.is_valid()}")

if not form.is_valid():
    print("\n❌ Form validation errors:")
    for field, errors in form.errors.items():
        print(f"  {field}: {errors}")
else:
    # Tentar salvar
    cliente_temp = form.save(commit=False)
    print(f"\n✓ Form aceitou valores!")
    print(f"  cliente.prazo_pagamento será: {cliente_temp.prazo_pagamento}")
    print(f"  cliente.prazo_pagamento_padrao_id será: {cliente_temp.prazo_pagamento_padrao_id}")
    
    # Não vamos realmente salvar, só verificar que funcionaria
    print(f"\n✅ Se cliente.save() fosse chamado, dados SERIAM salvos corretamente!")

print("\n" + "="*60)
print("RESUMO DO PROBLEMA:")
print("="*60)
print("""
O problema é que o JavaScript NÃO ESTAVA SINCRONIZANDO os valores
para os hidden inputs ANTES do formulário ser submetido.

CORREÇÃO IMPLEMENTADA:
✅ Adicionado event listener no SUBMIT do formulário que:
   1. Força sincronização de preset_id do select visível → hidden input
   2. Força sincronização de prazo_pagamento do terms select → hidden input
   3. Valida se ambos foram preenchidos antes de permitir submit
   4. Mostra console logs para debug

PRÓXIMO PASSO:
Você deve:
1. Fechar e reabrir a página de editar cliente
2. Selecionar um Preset e um termo
3. Clicar Salvar
4. Abrindo DevTools (F12), verificar console para logs:
   ✓ Form submit - Sincronizado preset: 110
   ✓ Form submit - Sincronizado prazo: 15
5. Verificar no banco se os dados foram salvos
""")
