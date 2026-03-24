"""
Script para testar renderização HTML completa da página de edição
"""

import os
import django
from django.test import RequestFactory
from django.contrib.auth import get_user_model

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from cadastros.models import Funcionario
from cadastros.forms import FuncionarioForm

User = get_user_model()

# Pega funcionário 3
func = Funcionario.objects.get(pk=3)
user = User.objects.filter(empresa=func.empresa).first() or User.objects.first()

# Cria formulário
form = FuncionarioForm(instance=func, empresa=user.empresa, usuario=user)

print("📋 Verificando rendering dos campos:\n")

for field_name in ['cpf', 'telefone', 'celular', 'cep']:
    field = form[field_name]
    value = field.value()
    html = str(field)
    
    print(f"{'='*60}")
    print(f"Campo: {field_name}")
    print(f"{'='*60}")
    print(f"Valor: {value}")
    print(f"\nHTML:\n{html}\n")
