import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model
from empresas.models import Empresa, GrupoCorporativo

Usuario = get_user_model()

# Listar empresas
print("\n" + "="*70)
print("EMPRESAS DISPONÍVEIS:")
print("="*70)
empresas = Empresa.objects.all()
if empresas.exists():
    for empresa in empresas:
        grupo_info = f" | Grupo: {empresa.grupo_corporativo.nome}" if empresa.grupo_corporativo else ""
        print(f"ID: {empresa.id} | Nome: {empresa.nome}{grupo_info}")
else:
    print("Nenhuma empresa encontrada")
print("="*70)

# Listar grupos
print("\n" + "="*70)
print("GRUPOS CORPORATIVOS DISPONÍVEIS:")
print("="*70)
grupos = GrupoCorporativo.objects.all()
if grupos.exists():
    for grupo in grupos:
        empresas_count = grupo.empresas.count()
        print(f"ID: {grupo.id} | Nome: {grupo.nome} ({empresas_count} empresa(s))")
else:
    print("Nenhum grupo corporativo encontrado")
print("="*70)

# Criar usuário
print("\nDigite 'S' para criar um novo usuário administrador ou 'N' para sair: ", end='')
opcao = input().strip().upper()

if opcao == 'S':
    print("\n--- CRIAR NOVO USUARIO ADMINISTRADOR ---")
    username = input("Username (ex: admin_empresa1): ").strip()
    email = input("Email (ex: admin@empresa1.com.br): ").strip()
    senha = input("Senha: ").strip()
    empresa_id = input("ID da Empresa: ").strip()
    nome_completo = input("Nome Completo (ex: Joao Silva): ").strip()
    telefone = input("Telefone (opcional, ex: +55 84 99999-9999): ").strip()
    
    try:
        empresa = Empresa.objects.get(id=empresa_id)
        
        if Usuario.objects.filter(username=username).exists():
            print(f"ERRO: Usuario '{username}' ja existe")
        else:
            partes = nome_completo.split(" ", 1) if nome_completo else ["Admin"]
            first_name = partes[0]
            last_name = partes[1] if len(partes) > 1 else ""
            
            usuario = Usuario.objects.create_user(
                username=username,
                email=email,
                password=senha,
                first_name=first_name,
                last_name=last_name,
                empresa=empresa,
                tipo='ADMIN',
                is_staff=True,
                is_superuser=False,
                is_active=True
            )
            
            if telefone:
                usuario.telefone = telefone
                usuario.save()
            
            print("\n" + "="*70)
            print("USUARIO CRIADO COM SUCESSO!")
            print("="*70)
            print(f"Username: {usuario.username}")
            print(f"Email: {usuario.email}")
            print(f"Empresa: {usuario.empresa.nome}")
            print(f"Tipo: {usuario.tipo}")
            print(f"Staff: {usuario.is_staff}")
            print("\nAcesso: http://127.0.0.1:8000/admin/")
            print("="*70 + "\n")
    
    except Empresa.DoesNotExist:
        print(f"ERRO: Empresa com ID {empresa_id} não encontrada")
    except Exception as e:
        print(f"ERRO: {str(e)}")
else:
    print("Operacao cancelada")
