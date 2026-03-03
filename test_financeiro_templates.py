#!/usr/bin/env python
"""
Script para testar se os templates financeiros estão funcionando corretamente
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser
from financeiro.views import conta_pagar_create
from financeiro.forms import ContaPageForm
from usuarios.models import Usuario
from empresas.models import Empresa

# Criar uma request fake
factory = RequestFactory()

# Testar se o formulário carrega sem erros
print("=" * 60)
print("TESTE 1: Verificar se ContaPageForm carrega")
print("=" * 60)

try:
    form = ContaPageForm()
    print("✅ ContaPageForm carregou com sucesso!")
    print(f"   Campos do formulário: {list(form.fields.keys())}")
except Exception as e:
    print(f"❌ Erro ao carregar ContaPageForm: {e}")

# Testar se a view renderiza o template corretamente
print("\n" + "=" * 60)
print("TESTE 2: Testar renderização de conta_pagar_create")
print("=" * 60)

try:
    # Buscar um usuário para fazer a requisição
    user = Usuario.objects.first()
    if not user:
        print("❌ Nenhum usuário encontrado no banco de dados")
    else:
        # Criar uma request GET
        request = factory.get('/financeiro/contas/criar/')
        request.user = user
        
        # Chamar a view
        response = conta_pagar_create(request)
        
        if response.status_code == 200:
            print("✅ View conta_pagar_create respondeu com status 200!")
            print("   (Página renderizou com sucesso)")
        else:
            print(f"❌ View retornou status {response.status_code}")
            
except Exception as e:
    print(f"❌ Erro ao testar view: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("RESUMO")
print("=" * 60)
print("Se todos os testes passaram, os templates estão funcionando!")
print("Acesse: http://127.0.0.1:8000/financeiro/contas/criar/")
