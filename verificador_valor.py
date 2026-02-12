"""
VERIFICADOR: Confirma se o limite_credito mudou para 20000.00
Execute este script DEPOIS de alterar e salvar no navegador
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.insert(0, '.')
django.setup()

from cadastros.models import Cliente

cliente = Cliente.objects.get(pk=6)

print("="*80)
print("VERIFICACAO: Cliente ID 6 - Confirmando novo valor")
print("="*80)

print(f"\nCliente: {cliente.razao_social}")
print(f"Empresa: {cliente.empresa.nome}")

print(f"\nVALOR ATUAL NO BANCO:")
print(f"  limite_credito: {cliente.limite_credito}")
print(f"  forma_pagamento_padrao: {cliente.forma_pagamento_padrao}")
print(f"  desconto_padrao: {cliente.desconto_padrao}")
print(f"  prazo_pagamento: {cliente.prazo_pagamento}")
print(f"  observacoes_comerciais: {cliente.observacoes_comerciais}")

print(f"\nVERIFICACAO:")
if cliente.limite_credito == 20000.00:
    print("  SUCCESS! limite_credito = 20000.00")
    print("  O CAMPO FOI SALVO CORRETAMENTE!")
elif cliente.limite_credito == 30000.00:
    print("  FALHA! limite_credito ainda = 30000.00")
    print("  O VALOR NAO FOI ATUALIZADO!")
    print("\n  Possíveis causas:")
    print("    1. Voce nao clicou em 'Salvar Cliente'")
    print("    2. Houve erro silencioso no formulario")
    print("    3. Validacao rejeitou os dados")
    print("    4. Erro de conexao com servidor")
else:
    print(f"  INESPERADO! limite_credito = {cliente.limite_credito}")
    print(f"  Esperava 20000.00 ou 30000.00")

print("\n" + "="*80)
