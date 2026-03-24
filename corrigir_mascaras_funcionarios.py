"""
Script para corrigir valores de CPF, Telefone, Celular e CEP salvos com máscara
Converte valores como "123.456.789-01" para "12345678901"
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
        return valor
    return re.sub(r'\D', '', valor)

def corrigir_funcionarios():
    """Corrige todos os funcionários com valores mascarados"""
    funcionarios = Funcionario.objects.all()
    corrigidos = 0
    
    print(f"📋 Total de funcionários: {funcionarios.count()}")
    
    for func in funcionarios:
        changes = False
        
        # Corrigir CPF
        if func.cpf and '.' in func.cpf or '-' in func.cpf:
            cpf_limpo = limpar_valor(func.cpf)
            if cpf_limpo and len(cpf_limpo) == 11:
                func.cpf = cpf_limpo
                changes = True
                print(f"  ✅ CPF: {func.cpf} → {cpf_limpo}")
        
        # Corrigir Telefone
        if func.telefone and ('(' in func.telefone or ')' in func.telefone or '-' in func.telefone):
            telefone_limpo = limpar_valor(func.telefone)
            if telefone_limpo:
                func.telefone = telefone_limpo
                changes = True
                print(f"  ✅ Telefone: {func.telefone} → {telefone_limpo}")
        
        # Corrigir Celular
        if func.celular and ('(' in func.celular or ')' in func.celular or '-' in func.celular):
            celular_limpo = limpar_valor(func.celular)
            if celular_limpo:
                func.celular = celular_limpo
                changes = True
                print(f"  ✅ Celular: {func.celular} → {celular_limpo}")
        
        # Corrigir CEP
        if func.cep and '-' in func.cep:
            cep_limpo = limpar_valor(func.cep)
            if cep_limpo and len(cep_limpo) == 8:
                func.cep = cep_limpo
                changes = True
                print(f"  ✅ CEP: {func.cep} → {cep_limpo}")
        
        # Salvar se houve mudanças
        if changes:
            func.save()
            corrigidos += 1
    
    print(f"\n✨ Total corrigido: {corrigidos} funcionários")

if __name__ == '__main__':
    print("🔧 Corrigindo máscaras dos funcionários...\n")
    corrigir_funcionarios()
    print("\n✅ Concluído!")
