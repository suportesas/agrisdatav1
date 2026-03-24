"""
Script para testar renderização do template
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.template.loader import render_to_string
from django.contrib.auth import get_user_model
from cadastros.models import Funcionario
from cadastros.forms import FuncionarioForm

User = get_user_model()

# Pega funcionário 1 que tem dados
func = Funcionario.objects.get(pk=1)
user = User.objects.filter(empresa=func.empresa).first() or User.objects.first()

# Cria formulário
form = FuncionarioForm(instance=func, empresa=user.empresa, usuario=user)

print("🔍 HTML renderizado do formulário CPF:")
print(form['cpf'])
print()

print("🔍 HTML renderizado do formulário Telefone:")
print(form['telefone'])
print()

print("🔍 HTML renderizado do formulário Celular:")
print(form['celular'])
print()

print("🔍 HTML renderizado do formulário CEP:")
print(form['cep'])
