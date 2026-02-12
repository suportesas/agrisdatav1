#!/usr/bin/env python
"""
Script para criar usuário administrador para uma empresa
Uso: python manage.py shell < criar_admin_empresa.py
Ou com Django: python criar_admin_empresa.py
"""

import os
import sys
import django
import logging

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from django.contrib.auth import get_user_model
from empresas.models import Empresa, GrupoCorporativo

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Usuario = get_user_model()


def criar_admin_empresa(
    username,
    email,
    senha,
    empresa_id,
    nome_completo="Admin",
    telefone="",
    grupo_corporativo_id=None
):
    """
    Cria um usuário administrador para uma empresa

    Args:
        username (str): Nome de usuário (ex: admin_empresa1)
        email (str): Email do administrador
        senha (str): Senha do usuário
        empresa_id (int): ID da empresa
        nome_completo (str): Nome completo (ex: "João Silva")
        telefone (str): Telefone (ex: "+55 84 99999-9999")
        grupo_corporativo_id (int): ID do grupo corporativo (opcional)

    Returns:
        Usuario: Objeto do usuário criado
    """

    try:
        # Validar empresa
        try:
            empresa = Empresa.objects.get(id=empresa_id)
            logger.info(f"✅ Empresa encontrada: {empresa.nome}")
        except Empresa.DoesNotExist:
            logger.error(f"❌ Empresa com ID {empresa_id} não encontrada")
            return None

        # Validar se username já existe
        if Usuario.objects.filter(username=username).exists():
            logger.error(f"❌ Usuário '{username}' já existe")
            return None

        # Separar nome e sobrenome
        partes = nome_completo.split(" ", 1) if nome_completo else ["Admin"]
        first_name = partes[0]
        last_name = partes[1] if len(partes) > 1 else ""

        # Criar usuário
        usuario = Usuario.objects.create_user(
            username=username,
            email=email,
            password=senha,
            first_name=first_name,
            last_name=last_name,
            empresa=empresa,
            tipo='ADMIN',
            is_staff=True,  # Permite acessar admin
            is_superuser=False,  # Sem permissões globais
            is_active=True
        )

        if telefone:
            usuario.telefone = telefone
            usuario.save()

        logger.info(f"✅ Usuário criado com sucesso!")
        logger.info(f"   Username: {usuario.username}")
        logger.info(f"   Email: {usuario.email}")
        logger.info(f"   Empresa: {usuario.empresa.nome}")
        logger.info(f"   Tipo: {usuario.tipo}")
        logger.info(f"   Staff: {usuario.is_staff}")

        # Se informou grupo corporativo, vinculá-lo
        if grupo_corporativo_id:
            try:
                grupo = GrupoCorporativo.objects.get(id=grupo_corporativo_id)
                # Atualizar empresa para estar no grupo
                empresa.grupo_corporativo = grupo
                empresa.save()
                logger.info(f"✅ Empresa vinculada ao grupo: {grupo.nome}")
            except GrupoCorporativo.DoesNotExist:
                logger.warning(f"⚠️ Grupo corporativo com ID {grupo_corporativo_id} não encontrado")

        return usuario

    except Exception as e:
        logger.error(f"❌ Erro ao criar usuário: {str(e)}")
        return None


def listar_empresas():
    """Lista todas as empresas disponíveis"""
    empresas = Empresa.objects.all()
    if not empresas:
        logger.info("Nenhuma empresa encontrada")
        return

    logger.info("\n📋 EMPRESAS DISPONÍVEIS:")
    logger.info("-" * 60)
    for empresa in empresas:
        grupo_info = f" | Grupo: {empresa.grupo_corporativo.nome}" if empresa.grupo_corporativo else ""
        logger.info(f"ID: {empresa.id} | Nome: {empresa.nome}{grupo_info}")
    logger.info("-" * 60 + "\n")


def listar_grupos():
    """Lista todos os grupos corporativos disponíveis"""
    grupos = GrupoCorporativo.objects.all()
    if not grupos:
        logger.info("Nenhum grupo corporativo encontrado")
        return

    logger.info("\n📋 GRUPOS CORPORATIVOS DISPONÍVEIS:")
    logger.info("-" * 60)
    for grupo in grupos:
        empresas_count = grupo.empresas.count()
        logger.info(f"ID: {grupo.id} | Nome: {grupo.nome} ({empresas_count} empresa(s))")
    logger.info("-" * 60 + "\n")


def main():
    """Função principal - exemplo de uso"""
    
    print("\n" + "=" * 70)
    print("🔐 CRIAR USUÁRIO ADMINISTRADOR PARA EMPRESA")
    print("=" * 70 + "\n")

    # Listar opções disponíveis
    listar_empresas()
    listar_grupos()

    # Exemplo de criação
    print("\n📝 EXEMPLO DE CRIAÇÃO:\n")
    
    usuario = criar_admin_empresa(
        username="admin_empresa1",
        email="admin@empresa1.com.br",
        senha="SenhaForte123!@#",
        empresa_id=1,  # 👈 Substitua pelo ID da empresa
        nome_completo="João Silva",
        telefone="+55 84 99999-9999",
        grupo_corporativo_id=None  # 👈 Opcional: ID do grupo corporativo
    )

    if usuario:
        print("\n" + "=" * 70)
        print("✅ USUÁRIO CRIADO COM SUCESSO!")
        print("=" * 70)
        print(f"\n📌 Informações de Acesso:")
        print(f"   URL: http://127.0.0.1:8000/admin/")
        print(f"   Username: {usuario.username}")
        print(f"   Senha: [Aquela que você definiu]")
        print(f"   Email: {usuario.email}")
        print(f"   Empresa: {usuario.empresa.nome}")
        print("\n")
    else:
        print("\n❌ Falha ao criar usuário. Verifique os logs acima.\n")


if __name__ == "__main__":
    main()
