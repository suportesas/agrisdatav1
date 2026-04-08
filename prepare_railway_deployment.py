#!/usr/bin/env python
"""
Script interativo para preparar deploy em Railway
Ajuda a gerar SECRET_KEY, verificar settings, etc
"""

import os
import secrets
from dotenv import load_dotenv
from pathlib import Path

def load_env():
    """Carrega variáveis do .env"""
    load_dotenv()
    return os.environ


def generate_secret_key():
    """Gera uma SECRET_KEY segura para Django"""
    return secrets.token_urlsafe(50)


def check_procfile():
    """Verifica se Procfile existe"""
    if Path('Procfile').exists():
        print("✅ Procfile existe")
        return True
    else:
        print("❌ Procfile não existe - criando...")
        with open('Procfile', 'w') as f:
            f.write('web: gunicorn core.wsgi --log-file -\n')
        print("✅ Procfile criado")
        return True


def check_requirements():
    """Verifica se requirements.txt existe"""
    if Path('requirements.txt').exists():
        with open('requirements.txt', 'r') as f:
            lines = f.readlines()
        print(f"✅ requirements.txt existe ({len(lines)} pacotes)")
        return True
    else:
        print("❌ requirements.txt não existe - gere com: pip freeze > requirements.txt")
        return False


def check_git():
    """Verifica se está tudo no Git"""
    result = os.system('git status > nul 2>&1')
    if result == 0:
        print("✅ Repositório Git configurado")
        return True
    else:
        print("❌ Repositório Git não encontrado")
        return False


def show_environment_variables():
    """Mostra variáveis que precisa configurar no Railway"""
    env = load_env()
    
    print("\n" + "="*70)
    print("🔐 VARIÁVEIS DE AMBIENTE NECESSÁRIAS NO RAILWAY")
    print("="*70)
    print()
    
    print("📋 Copie e configure estas variáveis no Railway Dashboard:")
    print()
    
    # Gerar SECRET_KEY se não existir
    secret_key = env.get('SECRET_KEY')
    if not secret_key:
        secret_key = generate_secret_key()
        print(f"⚠️  SECRET_KEY não está no .env (gerada uma nova):")
        print(f"    SECRET_KEY={secret_key}")
    else:
        print(f"✅ SECRET_KEY já definida")
    
    print()
    print("🗄️  SUPABASE (copie do seu .env):")
    supabase_vars = [
        'SUPABASE_URL',
        'SUPABASE_ANON_KEY',
        'SUPABASE_SERVICE_ROLE_KEY',
        'PG_NAME',
        'PG_USER',
        'PG_PASSWORD',
        'PG_HOST',
        'PG_PORT',
    ]
    
    for var in supabase_vars:
        value = env.get(var, '❌ NÃO CONFIGURADO')
        if value and value != '❌ NÃO CONFIGURADO':
            # Mascarar valores sensíveis
            if 'KEY' in var or 'PASSWORD' in var:
                value = value[:10] + '...' if len(str(value)) > 10 else value
            print(f"   {var}={value}")
        else:
            print(f"   {var}={value}")
    
    print()
    print("📧 EMAIL (opcional, copie do seu .env):")
    email_vars = [
        'EMAIL_HOST',
        'EMAIL_PORT',
        'EMAIL_USE_TLS',
        'EMAIL_HOST_USER',
        'EMAIL_HOST_PASSWORD',
    ]
    
    for var in email_vars:
        value = env.get(var, '(opcional)')
        if value and value != '(opcional)':
            if 'PASSWORD' in var:
                value = '***'
            print(f"   {var}={value}")
    
    print()
    print("🌐 DJANGO:")
    print(f"   DEBUG=False")
    print(f"   ALLOWED_HOSTS=seu-app.railway.app,localhost")
    print()


def show_deployment_steps():
    """Mostra passo a passo do deploy"""
    print("\n" + "="*70)
    print("🚀 PASSOS PARA DEPLOY EM RAILWAY")
    print("="*70)
    print()
    print("1️⃣  Faça commit de tudo:")
    print("    git add .")
    print("    git commit -m 'Deploy: Preparar para Railway'")
    print("    git push")
    print()
    print("2️⃣  Acesse: https://railway.app")
    print("    Faça login com GitHub")
    print()
    print("3️⃣  Crie novo projeto:")
    print("    + New Project → Deploy from GitHub")
    print("    Selecione: erp_agricola_novo")
    print()
    print("4️⃣  Configure variáveis de ambiente:")
    print("    Railway → Variables → adicione as variáveis acima")
    print()
    print("5️⃣  Aguarde deploy:")
    print("    Railway vai detectar Django e fazer build automático")
    print()
    print("6️⃣  Executar migrações (primeira vez):")
    print("    Railway → Deploy → Console → python manage.py migrate")
    print()
    print("7️⃣  Seu app está ONLINE! 🎉")
    print()


def main():
    """Main function"""
    print("\n" + "="*70)
    print("🚀 PREPARAR DEPLOY EM RAILWAY - HELPER SCRIPT")
    print("="*70)
    print()
    
    # Verificar pré-requisitos
    print("📋 VERIFICANDO PRÉ-REQUISITOS...")
    print()
    
    procfile_ok = check_procfile()
    requirements_ok = check_requirements()
    git_ok = check_git()
    
    print()
    
    if not all([procfile_ok, requirements_ok, git_ok]):
        print("❌ Alguns pré-requisitos estão faltando!")
        print("   Corrija acima antes de continuar")
        return 1
    
    # Mostrar variáveis
    show_environment_variables()
    
    # Mostrar passos
    show_deployment_steps()
    
    print("="*70)
    print("✅ Seu projeto está pronto para Railway!")
    print("="*70)
    print()
    
    return 0


if __name__ == '__main__':
    import sys
    exit(main())
