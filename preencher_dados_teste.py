"""
Script para preencher dados de teste no funcionário 3
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from cadastros.models import Funcionario

# Atualiza funcionário 3
func = Funcionario.objects.get(pk=3)
print(f"Funcionário: {func.nome_completo}")

# Copia dados do funcionário 1
func1 = Funcionario.objects.get(pk=1)

func.telefone = func1.telefone
func.celular = func1.celular
func.cep = func1.cep
func.endereco = func1.endereco
func.numero = func1.numero
func.bairro = func1.bairro
func.cidade = func1.cidade
func.uf = func1.uf

func.save()

print(f"\n✅ Dados preenchidos:")
print(f"  CPF: {func.cpf}")
print(f"  Telefone: {func.telefone}")
print(f"  Celular: {func.celular}")
print(f"  CEP: {func.cep}")
print(f"  Endereço: {func.endereco}, {func.numero}")
