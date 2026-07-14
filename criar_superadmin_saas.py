#!/usr/bin/env python
"""
Script para criar o Super Admin do SAAS
Este usuário é o proprietário/administrador global do sistema

Uso:
    cd c:\erp_agricola
    python criar_superadmin_saas.py
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from django.contrib.auth import get_user_model

Usuario = get_user_model()


def criar_superadmin(username, email, senha, nome_completo="Proprietário"):
    """
    Cria um Super Admin (proprietário do SAAS)
    
    Args:
        username (str): Nome de usuário (ex: admin)
        email (str): Email
        senha (str): Senha
        nome_completo (str): Nome completo
    
    Returns:
        Usuario: Objeto do usuário criado
    """
    
    # Validar se username já existe
    if Usuario.objects.filter(username=username).exists():
        print(f"❌ Erro: Usuário '{username}' já existe")
        return None
    
    # Separar nome e sobrenome
    partes = nome_completo.split(" ", 1) if nome_completo else ["Admin"]
    first_name = partes[0]
    last_name = partes[1] if len(partes) > 1 else ""
    
    # Criar Super Admin
    usuario = Usuario.objects.create_superuser(
        username=username,
        email=email,
        password=senha,
        first_name=first_name,
        last_name=last_name
    )
    
    # Remover vinculação com empresa (Super Admin não tem empresa específica)
    usuario.empresa = None
    usuario.tipo = 'SUPERADMIN'
    usuario.save()
    
    return usuario


def main():
    print("\n" + "="*70)
    print("CRIAR SUPER ADMIN DO SAAS")
    print("="*70)
    print("Este usuário terá acesso total ao sistema e painel administrativo\n")
    
    # Checagem rápida
    if Usuario.objects.filter(username='admin').exists():
        print("⚠️  Aviso: Já existe um usuário com username 'admin'")
        mudar = input("Deseja usar um username diferente? (S/N): ").strip().upper()
        if mudar == 'S':
            username = input("Username desejado: ").strip()
        else:
            print("Operação cancelada")
            return
    else:
        username = 'admin'
    
    # Coletar dados
    email = input("Email (ex: admin@erpseries.com.br): ").strip()
    
    if not email:
        print("❌ Email é obrigatório")
        return
    
    senha = input("Senha (mínimo 6 caracteres): ").strip()
    
    if len(senha) < 6:
        print("❌ Senha deve ter mínimo 6 caracteres")
        return
    
    nome_completo = input("Nome Completo (ex: Proprietário Agrisdata): ").strip()
    
    if not nome_completo:
        nome_completo = "Proprietário SAAS"
    
    # Confirmar
    print("\n" + "="*70)
    print("DADOS PARA CRIAR:")
    print("="*70)
    print(f"Username:      {username}")
    print(f"Email:         {email}")
    print(f"Nome Completo: {nome_completo}")
    print(f"Tipo:          SUPERADMIN")
    print(f"Empresa:       Nenhuma (Acesso Global)")
    print("="*70)
    
    confirmar = input("\nDeseja criar este Super Admin? (S/N): ").strip().upper()
    
    if confirmar != 'S':
        print("Operação cancelada")
        return
    
    # Criar
    usuario = criar_superadmin(username, email, senha, nome_completo)
    
    if usuario:
        print("\n" + "="*70)
        print("✅ SUPER ADMIN CRIADO COM SUCESSO!")
        print("="*70)
        print(f"Username: {usuario.username}")
        print(f"Email:    {usuario.email}")
        print(f"Nome:     {usuario.get_full_name()}")
        print(f"Tipo:     {usuario.tipo}")
        print(f"Empresa:  {usuario.empresa or 'Nenhuma (Acesso Global)'}")
        print(f"Staff:    {usuario.is_staff}")
        print(f"Superuser: {usuario.is_superuser}")
        print("\n🔗 Acesso:")
        print("   - Painel Admin: http://127.0.0.1:8000/admin/")
        print("   - Login: http://127.0.0.1:8000/login/")
        print("\n💡 Dica: Você pode criar outros usuários via admin ou scripts")
        print("="*70 + "\n")


if __name__ == '__main__':
    main()
