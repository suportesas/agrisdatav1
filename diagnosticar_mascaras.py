"""
Script para diagnosticar valores salvos de CPF, Telefone, Celular e CEP
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from cadastros.models import Funcionario

def diagnosticar():
    """Verifica valores salvos nos campos"""
    funcionarios = Funcionario.objects.all()
    
    print(f"📋 Diagnosticando {funcionarios.count()} funcionários:\n")
    
    for func in funcionarios:
        print(f"ID: {func.id} | {func.nome_completo}")
        print(f"  CPF: '{func.cpf}' (tipo: {type(func.cpf).__name__}, len: {len(func.cpf) if func.cpf else 0})")
        print(f"  Telefone: '{func.telefone}' (len: {len(func.telefone) if func.telefone else 0})")
        print(f"  Celular: '{func.celular}' (len: {len(func.celular) if func.celular else 0})")
        print(f"  CEP: '{func.cep}' (len: {len(func.cep) if func.cep else 0})")
        print()

if __name__ == '__main__':
    diagnosticar()
