#!/usr/bin/env python
"""
Testa a validação de roles - impede que admin de uma empresa
selecione funções de outra empresa
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from usuarios.models import Usuario
from empresas.models import Empresa, Role
from usuarios.forms import UsuarioCreateForm
from django.core.exceptions import ValidationError
from django.test.client import RequestFactory

print("=" * 70)
print("TESTE: Validação de Funções - Impedindo Cross-Company")
print("=" * 70)

# Empresas
emp1, _ = Empresa.objects.get_or_create(
    cnpj='22345678000001',
    defaults={'nome': 'Empresa Teste 1', 'ativa': True}
)

emp2, _ = Empresa.objects.get_or_create(
    cnpj='22345678000002',
    defaults={'nome': 'Empresa Teste 2', 'ativa': True}
)

print(f"\n✅ Empresa 1: {emp1.nome}")
print(f"✅ Empresa 2: {emp2.nome}")

# Roles
role_emp1, _ = Role.objects.get_or_create(
    name='Admin Tester 1',
    empresa=emp1,
    defaults={'description': 'Admin de Teste Empresa 1'}
)

role_emp2, _ = Role.objects.get_or_create(
    name='Admin Tester 2',
    empresa=emp2,
    defaults={'description': 'Admin de Teste Empresa 2'}
)

print(f"\n✅ Função Empresa 1: {role_emp1.name}")
print(f"✅ Função Empresa 2: {role_emp2.name}")

# Users
try:
    admin_emp1 = Usuario.objects.get(username='admin_test_emp1')
except:
    admin_emp1 = Usuario.objects.create_user(
        username='admin_test_emp1',
        email='admin_test1@emp1.com',
        password='123456',
        empresa=emp1,
        tipo='ADMIN',
        is_staff=True
    )

print(f"\n✅ Admin Empresa 1: {admin_emp1.username}")

# TESTE: Admin da Empresa 1 tentando selecionar role de Empresa 2
print("\n" + "=" * 70)
print("TESTE CRÍTICO: Admin Empresa 1 tentando usar Função de Empresa 2")
print("=" * 70)

# Simula POST data com role de OUTRA empresa
post_data = {
    'username': 'novo_usuario',
    'email': 'novo@teste.com',
    'first_name': 'Novo',
    'last_name': 'Usuario',
    'password1': 'Senha@12345',
    'password2': 'Senha@12345',
    'tipo': 'OPERADOR',
    'telefone': '(84) 99999-9999',
    'cpf': '',
    'empresa': str(emp1.id),
    'roles': [str(role_emp2.id)],  # ❌ TENTANDO USAR ROLE DE EMPRESA 2!
    'is_active': 'on',
    'is_staff': '',
}

form = UsuarioCreateForm(post_data, user=admin_emp1)

print(f"\n👤 Usuário criando: admin_test_emp1 (Empresa: {admin_emp1.empresa.nome})")
print(f"📝 Dados enviados:")
print(f"   - Username: novo_usuario")
print(f"   - Empresa: {emp1.nome} (ID: {emp1.id})")
print(f"   - Funções selecionadas: {role_emp2.name} (ID: {role_emp2.id}) ⚠️ DE OUTRA EMPRESA!")

if form.is_valid():
    print("\n❌ ERRO! Formulário foi validado, mas deveria rejeitar!")
    usuario = form.save()
    print(f"   Usuário criado: {usuario.username}")
    print(f"   Roles atribuídas: {list(usuario.roles.values_list('name', flat=True))}")
    if role_emp2 in usuario.roles.all():
        print("\n🚨 FALHA DE SEGURANÇA: Role de Empresa 2 foi atribuído a usuário de Empresa 1!")
    else:
        print("\n✅ Pelo menos o roles não foi salvo (salvo incorretamente)")
else:
    print(f"\n✅ VALIDAÇÃO FUNCIONOU! Formulário rejeitou com erro:")
    if 'roles' in form.errors:
        print(f"   {form.errors['roles']}")
    else:
        print(f"   Erros: {form.errors}")

print("\n" + "=" * 70)
print("FIM DO TESTE DE SEGURANÇA")
print("=" * 70)
