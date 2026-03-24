"""
Script para corrigir dados corrompidos e garantir formato correto
"""

import os
import django
import re

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from cadastros.models import Funcionario

def limpar_valor(valor):
    """Remove todos os caracteres não-dígitos"""
    if not valor:
        return ''
    return re.sub(r'\D', '', valor)

def corrigir_dados_corrompidos():
    """Corrige dados corrompidos (como '(' no telefone)"""
    funcionarios = Funcionario.objects.all()
    corrigidos = 0
    
    print("🔧 Corrigindo dados corrompidos...\n")
    
    for func in funcionarios:
        changes = False
        
        # Se telefone é apenas '(' ou corrupto
        if func.telefone and len(func.telefone) <= 2:
            func.telefone = ''
            changes = True
            print(f"  🗑️ Limpou Telefone corrompido")
        
        # Se celular é apenas '(' ou corrupto
        if func.celular and len(func.celular) <= 2:
            func.celular = ''
            changes = True
            print(f"  🗑️ Limpou Celular corrompido")
        
        if changes:
            func.save()
            corrigidos += 1
            print(f"  ✅ Corrigido: {func.nome_completo}\n")
    
    print(f"\n✨ Total corrigido: {corrigidos} funcionários")

if __name__ == '__main__':
    corrigir_dados_corrompidos()
