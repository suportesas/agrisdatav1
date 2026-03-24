"""
Script para debugar o formulário de edição
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model
from cadastros.models import Funcionario
from cadastros.forms import FuncionarioForm

User = get_user_model()

# Testa todos os funcionários
for pk in [1, 2, 3]:
    try:
        func = Funcionario.objects.get(pk=pk)
        print(f"\n{'='*60}")
        print(f"ID: {pk} | Funcionário: {func.nome_completo}")
        print(f"{'='*60}")
        print(f"  CPF BD: '{func.cpf}'")
        print(f"  Telefone BD: '{func.telefone}'")
        print(f"  Celular BD: '{func.celular}'")
        print(f"  CEP BD: '{func.cep}'")
        
        # Pega primeiro usuário para empresa
        user = User.objects.filter(empresa=func.empresa).first()
        if not user:
            user = User.objects.first()
        
        # Cria formulário
        form = FuncionarioForm(instance=func, empresa=user.empresa, usuario=user)
        
        print(f"\n📋 Valores no formulário:")
        print(f"  form['cpf'].value(): {form['cpf'].value()}")
        print(f"  form['telefone'].value(): {form['telefone'].value()}")
        print(f"  form['celular'].value(): {form['celular'].value()}")
        print(f"  form['cep'].value(): {form['cep'].value()}")
        
    except Funcionario.DoesNotExist:
        print(f"Funcionário {pk} não existe")

