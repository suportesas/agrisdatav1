# ERP Agrícola — Sistema Multi-empresa

Sistema de gestão agrícola com arquitetura **multi-tenant** (multiempresa), desenvolvido em **Python/Django** para produtores rurais, cooperativas e empresas do agronegócio.

[![Python](https://img.shields.io/badge/Python-3.14.6-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-6.0.6-green.svg)](https://www.djangoproject.com/)

---

## Sumário

1. [Visão Geral](#visão-geral)
2. [Tecnologias](#tecnologias)
3. [Módulos do Sistema](#módulos-do-sistema)
4. [Configuração Local (Desenvolvimento)](#configuração-local-desenvolvimento)
5. [Variáveis de Ambiente](#variáveis-de-ambiente)
6. [Deploy em VPS/Ubuntu (Nginx + Gunicorn)](#deploy-em-vpsubuntu-nginx--gunicorn)
7. [Deploy com Docker Compose](#deploy-com-docker-compose)
8. [Deploy Contínuo com GitHub](#deploy-contínuo-com-github)
9. [Pós-Deploy — Dados Iniciais](#pós-deploy--dados-iniciais)
10. [Comandos de Manutenção](#comandos-de-manutenção)
10. [Checklist de Segurança para Produção](#checklist-de-segurança-para-produção)

---

## Visão Geral

O sistema isola dados por empresa: cada `Fazenda`, `OS`, `NF-e`, `Funcionário`, etc. está sempre vinculado à empresa do usuário autenticado. Superusuários têm visão global.

**Tipos de usuário:** `ADMIN`, `GERENTE`, `FUNC`, `PROD`, `VENDEDOR`, `FINANCEIRO`

---

## Tecnologias

| Camada | Tecnologia |
|--------|-----------|
| Backend | Python 3.14.6, Django 6.0.6 |
| API | Django REST Framework 3.17 + SimpleJWT |
| Banco (produção) | PostgreSQL 14+ |
| Banco (desenvolvimento) | SQLite (automático quando PG não configurado) |
| Storage de arquivos | Supabase Storage (fallback: `MEDIA_ROOT` local) |
| Servidor WSGI | Gunicorn 25.3 |
| Proxy reverso | Nginx |
| Frontend | Bootstrap 5.3.2 + Bootstrap Icons 1.11.1 |
| Criptografia de campos | Fernet (`cryptography`) |

---

## Módulos do Sistema

| App | Prefixo URL | Descrição |
|-----|------------|-----------|
| `cadastros` | `/cadastros/` | Clientes, fornecedores, produtores, transportadoras, CFOP, NCM |
| `financeiro` | `/financeiro/` | Contas a pagar/receber, parcelas, fluxo de caixa |
| `plano_contas` | `/plano-contas/` | Plano de contas contábeis hierárquico |
| `bancario` | `/bancario/` | Contas bancárias, extrato, conciliação OFX/CNAB |
| `faturamento` | `/faturamento/` | NF-e, CT-e, MDF-e, Invoice de exportação |
| `compras` | `/compras/` | Pedidos, cotações, recebimentos, importação XML NF-e |
| `estoque` | `/estoque/` | Movimentações, requisições, inventário |
| `vendas` | `/vendas/` | Pedidos de venda |
| `operacoes_campo` | `/campo/` | Ordens de Serviço, portal do campo (PWA), horímetros |
| `frota` | `/frota/` | Veículos e máquinas |
| `rh` | `/rh/` | Funcionários, salários |
| `exportacao` | `/exportacao/` | Bookings, armadores, ordens de coleta |
| `embalagem` | `/embalagem/` | Ordens de embalagem, pallets, romaneios |

---

## Configuração Local (Desenvolvimento)

### Pré-requisitos

- Python 3.14.6 ou superior
- Git
- PostgreSQL (opcional — SQLite é usado automaticamente sem ele)

### Passo a passo

```bash
# 1. Clone o repositório
git clone https://github.com/EMSSousa/erp_agricola_novo.git
cd erp_agricola

# 2. Crie e ative o ambiente virtual
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Configure o .env
cp .env.example .env
# Edite o .env com seus dados (SECRET_KEY obrigatória)

# 5. Aplique as migrações
python manage.py migrate

# 6. Crie o superusuário
python manage.py createsuperuser

# 7. Popule dados iniciais (opcional, mas recomendado)
python manage.py seed_roles
python manage.py seed_plano_contas
python manage.py import_cfop
python manage.py import_ncm
python manage.py seed_pragas

# 8. Inicie o servidor
python manage.py runserver
```

Acesse: `http://127.0.0.1:8000` | Admin: `http://127.0.0.1:8000/admin`

---

## Variáveis de Ambiente

Crie o arquivo `.env` na raiz do projeto. Todos os valores abaixo são reconhecidos por `erp_agricola/settings.py`.

```env
# ─────────────────────────────────────────
# OBRIGATÓRIO
# ─────────────────────────────────────────

# Gere com: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
SECRET_KEY=sua-chave-secreta-longa-e-aleatoria

# False em produção, True apenas em desenvolvimento
DEBUG=False

# Domínio(s) do servidor separados por vírgula
ALLOWED_HOSTS=erp.suaempresa.com.br,www.erp.suaempresa.com.br

# Origens confiáveis para CSRF (necessário quando há proxy reverso ou HTTPS)
CSRF_TRUSTED_ORIGINS=https://erp.suaempresa.com.br

# ─────────────────────────────────────────
# BANCO DE DADOS (PostgreSQL)
# ─────────────────────────────────────────
# Quando PG_NAME não está definido, o Django usa SQLite automaticamente

PG_NAME=erp_agricola
PG_USER=erp_user
PG_PASSWORD=senha_segura_aqui
PG_HOST=localhost        # ou IP/hostname do servidor PostgreSQL
PG_PORT=5432

# ─────────────────────────────────────────
# SUPABASE (Storage de arquivos + Auth)
# ─────────────────────────────────────────
# Obtenha em: https://supabase.com/dashboard → Project Settings → API

SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# ─────────────────────────────────────────
# CRIPTOGRAFIA DE CAMPOS SENSÍVEIS
# ─────────────────────────────────────────
# Necessário para tokens de API (IntegraNotas, etc.)
# Gere com: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
FIELD_ENCRYPTION_KEY=chave-fernet-gerada-aqui

# ─────────────────────────────────────────
# E-MAIL (SMTP)
# ─────────────────────────────────────────
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=seu.email@gmail.com
EMAIL_HOST_PASSWORD=senha-de-app-16-chars
DEFAULT_FROM_EMAIL=ERP Agrícola <seu.email@gmail.com>

# ─────────────────────────────────────────
# SEGURANÇA HTTPS (ativar em produção)
# ─────────────────────────────────────────
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True

# ─────────────────────────────────────────
# FEATURE FLAGS
# ─────────────────────────────────────────
FF_COMPRAS_XML_IMPORT=False
FF_ESTOQUE_QUARENTENA_BLOQUEIO=False
FF_ESTOQUE_DEVOLUCOES_FLUXO=False
FF_RASTREABILIDADE_FULL_CHAIN=False
FF_FINANCEIRO_RENEGOCIACAO=False
FF_RECEITUARIO_AGRONOMICO_V1=False
FF_ARMADOR_INTEGRACOES_EXTERNAS=False

# ─────────────────────────────────────────
# LOCALIZAÇÃO
# ─────────────────────────────────────────
TIME_ZONE=America/Sao_Paulo
LANGUAGE_CODE=pt-br
```

---

## Deploy em VPS/Ubuntu (Nginx + Gunicorn)

> Testado em Ubuntu 22.04 LTS. Adapte o caminho `/var/www/erp_agricola` conforme necessário.

### 1. Prepare o servidor

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git nginx postgresql postgresql-contrib
```

### 2. Configure o PostgreSQL

```bash
sudo -u postgres psql

-- No prompt do psql:
CREATE DATABASE erp_agricola;
CREATE USER erp_user WITH PASSWORD 'senha_segura_aqui';
ALTER ROLE erp_user SET client_encoding TO 'utf8';
ALTER ROLE erp_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE erp_user SET timezone TO 'America/Sao_Paulo';
GRANT ALL PRIVILEGES ON DATABASE erp_agricola TO erp_user;
\q
```

### 3. Clone e configure o projeto

```bash
cd /var/www
sudo git clone https://github.com/EMSSousa/erp_agricola_novo.git erp_agricola
sudo chown -R $USER:$USER /var/www/erp_agricola
cd /var/www/erp_agricola

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure o .env de produção
cp .env.example .env
nano .env    # preencha todos os campos obrigatórios
```

### 4. Inicialize o banco e arquivos estáticos

```bash
source venv/bin/activate

python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput

# Dados iniciais obrigatórios
python manage.py seed_roles
python manage.py seed_plano_contas
python manage.py import_cfop
python manage.py import_ncm
```

### 5. Configure o Gunicorn como serviço systemd

Crie o arquivo `/etc/systemd/system/erp_agricola.service`:

```ini
[Unit]
Description=ERP Agrícola - Gunicorn
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/erp_agricola
EnvironmentFile=/var/www/erp_agricola/.env
ExecStart=/var/www/erp_agricola/venv/bin/gunicorn \
    erp_agricola.wsgi:application \
    --workers 3 \
    --bind unix:/run/erp_agricola.sock \
    --timeout 120 \
    --access-logfile /var/log/erp_agricola/access.log \
    --error-logfile /var/log/erp_agricola/error.log
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
# Crie a pasta de logs e ajuste permissões
sudo mkdir -p /var/log/erp_agricola
sudo chown -R www-data:www-data /var/log/erp_agricola
sudo chown -R www-data:www-data /var/www/erp_agricola

# Ative e inicie o serviço
sudo systemctl daemon-reload
sudo systemctl enable erp_agricola
sudo systemctl start erp_agricola
sudo systemctl status erp_agricola
```

### 6. Configure o Nginx

Crie `/etc/nginx/sites-available/erp_agricola`:

```nginx
server {
    listen 80;
    server_name erp.suaempresa.com.br www.erp.suaempresa.com.br;

    # Redireciona HTTP → HTTPS (descomente após configurar o certificado SSL)
    # return 301 https://$host$request_uri;

    client_max_body_size 50M;

    location = /favicon.ico { access_log off; log_not_found off; }

    location /static/ {
        alias /var/www/erp_agricola/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias /var/www/erp_agricola/media/;
        expires 7d;
    }

    location / {
        proxy_pass http://unix:/run/erp_agricola.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120;
        proxy_connect_timeout 120;
    }

    access_log /var/log/nginx/erp_agricola_access.log;
    error_log  /var/log/nginx/erp_agricola_error.log;
}
```

```bash
sudo ln -s /etc/nginx/sites-available/erp_agricola /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 7. Configure HTTPS com Let's Encrypt

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d erp.suaempresa.com.br -d www.erp.suaempresa.com.br

# Renovação automática (já configurada pelo certbot, mas verifique):
sudo systemctl status certbot.timer
```

Após o certificado, ative as variáveis de segurança HTTPS no `.env` e reinicie:

```bash
sudo systemctl restart erp_agricola
```

### Comandos úteis do serviço

```bash
sudo systemctl restart erp_agricola       # reiniciar após alterações
sudo systemctl stop erp_agricola          # parar
sudo journalctl -u erp_agricola -n 50     # ver últimas 50 linhas de log
tail -f /var/log/erp_agricola/error.log   # monitorar erros em tempo real
```

---

## Deploy com Docker Compose

O projeto já inclui `Dockerfile` e `docker-compose.yml`. O banco de dados **não roda em container** — usa PostgreSQL externo (Supabase ou servidor próprio).

### Pré-requisitos

- Docker Engine 24+
- Docker Compose v2+

### 1. Configure o .env.docker

```bash
cp .env.example .env.docker
nano .env.docker   # preencha com dados de produção
```

Exemplo mínimo para `.env.docker`:

```env
SECRET_KEY=chave-secreta-muito-longa-e-aleatoria
DEBUG=False
ALLOWED_HOSTS=erp.suaempresa.com.br
CSRF_TRUSTED_ORIGINS=https://erp.suaempresa.com.br

PG_NAME=erp_agricola
PG_USER=erp_user
PG_PASSWORD=senha_segura
PG_HOST=db.xxxxxxxxxxxx.supabase.co
PG_PORT=5432

SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...

FIELD_ENCRYPTION_KEY=chave-fernet-aqui
```

### 2. Build e subida dos containers

```bash
# Build
docker compose build

# Subir em background
docker compose up -d

# Ver logs
docker compose logs -f app
```

### 3. Inicializar banco e dados

```bash
# Migrações
docker compose exec app python manage.py migrate

# Superusuário
docker compose exec app python manage.py createsuperuser

# Estáticos
docker compose exec app python manage.py collectstatic --noinput

# Dados iniciais
docker compose exec app python manage.py seed_roles
docker compose exec app python manage.py seed_plano_contas
docker compose exec app python manage.py import_cfop
docker compose exec app python manage.py import_ncm
```

### 4. Nginx como proxy (para produção)

Descomente o bloco `nginx` no `docker-compose.yml` e crie `nginx.conf` na raiz:

```nginx
server {
    listen 80;
    server_name erp.suaempresa.com.br;

    client_max_body_size 50M;

    location /static/ {
        alias /static/;
        expires 30d;
    }

    location /media/ {
        alias /media/;
    }

    location / {
        proxy_pass http://app:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Atualização da aplicação (deploy contínuo)

```bash
git pull origin main
docker compose build app
docker compose up -d app
docker compose exec app python manage.py migrate
docker compose exec app python manage.py collectstatic --noinput
```

---

## Pós-Deploy — Dados Iniciais

Execute estes comandos uma única vez após o primeiro deploy (ou quando necessário):

```bash
# Perfis de acesso (roles)
python manage.py seed_roles

# Plano de contas contábil (101 contas padrão)
python manage.py seed_plano_contas --empresa-id 1

# Tabela CFOP (Códigos Fiscais de Operação)
python manage.py import_cfop

# Tabela NCM
python manage.py import_ncm

# Pragas e defensivos agrícolas
python manage.py seed_pragas

# Categorias agrícolas
python manage.py popula_categorias_agricolas

# Sincronizar superusuário global entre empresas
python manage.py sincronizar_superuser_global

# Atualizar planos de assinatura
python manage.py atualizar_planos
```

---

## Comandos de Manutenção

```bash
# ─── Estoque ───────────────────────────────────────────
python manage.py recalcular_estoque     # Recalcula saldo de todos os produtos
python manage.py auditar_estoque        # Detecta inconsistências

# ─── Migrations ────────────────────────────────────────
python manage.py showmigrations                     # Status de todas as migrations
python manage.py makemigrations <app>               # Criar migration para um app
python manage.py migrate                            # Aplicar pendentes
python manage.py sqlmigrate <app> <migration>       # Ver SQL gerado

# ─── Banco de dados ────────────────────────────────────
python manage.py dumpdata --indent 2 > backup.json         # Export completo
python manage.py dumpdata empresas --indent 2 > emp.json   # Export por app
python manage.py loaddata backup.json                      # Import

# ─── Diagnóstico ───────────────────────────────────────
python manage.py check                 # Verificações gerais
python manage.py check --deploy        # Checklist específico para produção

# ─── Chave de criptografia ─────────────────────────────
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# ─── SECRET_KEY ────────────────────────────────────────
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# ─── Estáticos ─────────────────────────────────────────
python manage.py collectstatic --noinput
```

---

## Deploy Contínuo com GitHub

Esta seção cobre duas abordagens: **deploy manual via `git pull`** (simples, recomendado para começar) e **deploy automático via GitHub Actions** (CI/CD, recomendado para produção).

---

### Abordagem 1 — Deploy Manual com `git pull` (VPS)

Configure o servidor para puxar atualizações direto do GitHub sem precisar de senha.

#### 1.1 — Gere uma SSH key no servidor

```bash
# Execute no servidor (como o usuário que roda a aplicação)
ssh-keygen -t ed25519 -C "deploy@erp_agricola" -f ~/.ssh/github_deploy
cat ~/.ssh/github_deploy.pub   # copie esta chave
```

#### 1.2 — Adicione a chave como Deploy Key no GitHub

1. Acesse o repositório no GitHub
2. **Settings → Deploy keys → Add deploy key**
3. Cole a chave pública (`github_deploy.pub`)
4. Marque **Allow write access** como **desmarcado** (leitura é suficiente)
5. Clique em **Add key**

#### 1.3 — Configure o SSH no servidor

```bash
# Crie ou edite ~/.ssh/config no servidor
nano ~/.ssh/config
```

```
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/github_deploy
    IdentitiesOnly yes
```

```bash
# Teste a conexão
ssh -T git@github.com
# Esperado: "Hi EMSSousa/erp_agricola_novo! You've successfully authenticated..."
```

#### 1.4 — Clone usando SSH (se ainda não clonou)

```bash
cd /var/www
git clone git@github.com:EMSSousa/erp_agricola_novo.git erp_agricola
```

#### 1.5 — Script de deploy (`deploy.sh`)

Crie `/var/www/erp_agricola/deploy.sh`:

```bash
#!/bin/bash
set -e

PROJECT_DIR="/var/www/erp_agricola"
VENV="$PROJECT_DIR/venv/bin/python"
MANAGE="$VENV $PROJECT_DIR/manage.py"

echo "==> Puxando atualizações do GitHub..."
cd "$PROJECT_DIR"
git pull origin main

echo "==> Instalando dependências..."
"$PROJECT_DIR/venv/bin/pip" install -r requirements.txt --quiet

echo "==> Aplicando migrações..."
$MANAGE migrate --noinput

echo "==> Coletando arquivos estáticos..."
$MANAGE collectstatic --noinput

echo "==> Reiniciando o serviço..."
sudo systemctl restart erp_agricola

echo "==> Deploy concluído com sucesso!"
```

```bash
chmod +x /var/www/erp_agricola/deploy.sh

# Permita reiniciar o serviço sem senha (adicione ao sudoers)
sudo visudo
# Adicione a linha abaixo (substitua 'ubuntu' pelo seu usuário):
# ubuntu ALL=(ALL) NOPASSWD: /bin/systemctl restart erp_agricola
```

Para fazer deploy, basta rodar no servidor:

```bash
/var/www/erp_agricola/deploy.sh
```

---

### Abordagem 2 — Deploy Automático com GitHub Actions (CI/CD)

A cada `git push` na branch `main`, o GitHub Actions se conecta ao servidor via SSH e executa o deploy automaticamente.

#### 2.1 — Configure os Secrets no GitHub

Acesse **Settings → Secrets and variables → Actions** e adicione:

| Secret | Valor |
|--------|-------|
| `SSH_HOST` | IP ou hostname do servidor (ex: `192.168.1.10`) |
| `SSH_USER` | Usuário SSH (ex: `ubuntu`) |
| `SSH_PRIVATE_KEY` | Conteúdo da chave privada SSH para acesso ao servidor |
| `SSH_PORT` | Porta SSH (normalmente `22`) |

Para gerar o par de chaves para o GitHub Actions acessar o servidor:

```bash
# Na sua máquina local
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/github_actions_deploy

# Copie a chave PÚBLICA para o servidor
ssh-copy-id -i ~/.ssh/github_actions_deploy.pub usuario@ip-do-servidor

# Copie o conteúdo da chave PRIVADA para o Secret SSH_PRIVATE_KEY
cat ~/.ssh/github_actions_deploy
```

#### 2.2 — Crie o workflow

Crie o arquivo `.github/workflows/deploy.yml` no repositório:

```yaml
name: Deploy para Produção

on:
  push:
    branches:
      - main

jobs:
  deploy:
    name: Deploy via SSH
    runs-on: ubuntu-latest

    steps:
      - name: Checkout do código
        uses: actions/checkout@v4

      - name: Deploy no servidor
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.SSH_HOST }}
          username: ${{ secrets.SSH_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          port: ${{ secrets.SSH_PORT }}
          script: |
            set -e
            cd /var/www/erp_agricola

            echo "Puxando alterações..."
            git pull origin main

            echo "Instalando dependências..."
            venv/bin/pip install -r requirements.txt --quiet

            echo "Aplicando migrações..."
            venv/bin/python manage.py migrate --noinput

            echo "Coletando estáticos..."
            venv/bin/python manage.py collectstatic --noinput

            echo "Reiniciando serviço..."
            sudo systemctl restart erp_agricola

            echo "Deploy finalizado!"
```

#### 2.3 — (Opcional) Adicionar testes antes do deploy

```yaml
name: Deploy para Produção

on:
  push:
    branches:
      - main

jobs:
  test:
    name: Testes
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: erp_test
          POSTGRES_USER: erp_user
          POSTGRES_PASSWORD: test_password
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - name: Configurar Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Instalar dependências
        run: pip install -r requirements.txt

      - name: Rodar testes
        env:
          DEBUG: "True"
          SECRET_KEY: "chave-temporaria-para-ci"
          PG_NAME: erp_test
          PG_USER: erp_user
          PG_PASSWORD: test_password
          PG_HOST: localhost
          PG_PORT: 5432
        run: python manage.py test --verbosity=2

  deploy:
    name: Deploy via SSH
    runs-on: ubuntu-latest
    needs: test          # só executa se os testes passarem

    steps:
      - name: Deploy no servidor
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.SSH_HOST }}
          username: ${{ secrets.SSH_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          port: ${{ secrets.SSH_PORT }}
          script: |
            cd /var/www/erp_agricola
            git pull origin main
            venv/bin/pip install -r requirements.txt --quiet
            venv/bin/python manage.py migrate --noinput
            venv/bin/python manage.py collectstatic --noinput
            sudo systemctl restart erp_agricola
```

#### 2.4 — Fluxo completo após configurado

```
Desenvolvedor faz git push origin main
         ↓
GitHub Actions inicia o workflow
         ↓
[Opcional] Roda testes automáticos
         ↓
Se passou: conecta ao servidor via SSH
         ↓
git pull → pip install → migrate → collectstatic → restart
         ↓
Sistema atualizado em produção ✓
```

---

### Abordagem 3 — Deploy com Docker Compose + GitHub Actions

Se estiver usando Docker, o workflow envia a imagem atualizada e reinicia o Compose:

```yaml
name: Deploy Docker

on:
  push:
    branches:
      - main

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - name: Deploy via SSH (Docker Compose)
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.SSH_HOST }}
          username: ${{ secrets.SSH_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          port: ${{ secrets.SSH_PORT }}
          script: |
            cd /var/www/erp_agricola
            git pull origin main
            docker compose build app
            docker compose up -d app
            docker compose exec -T app python manage.py migrate --noinput
            docker compose exec -T app python manage.py collectstatic --noinput
```

---

### Boas práticas para todos os fluxos

- **Nunca commite o `.env`** — adicione ao `.gitignore` e gerencie no servidor ou via GitHub Secrets
- **Branch `main` = produção** — use branches de feature e faça PR antes de mergear
- **Faça backup do banco antes de cada deploy** que envolva migrações estruturais
- **Teste as migrações em staging** antes de aplicar em produção

---

## Checklist de Segurança para Produção

Antes de colocar o sistema em produção, confirme cada item:

### Configurações obrigatórias no `.env`

- [ ] `DEBUG=False`
- [ ] `SECRET_KEY` com no mínimo 50 caracteres aleatórios
- [ ] `ALLOWED_HOSTS` com apenas os domínios reais do sistema
- [ ] `CSRF_TRUSTED_ORIGINS` com o domínio HTTPS completo
- [ ] `FIELD_ENCRYPTION_KEY` gerada e guardada em local seguro
- [ ] Banco PostgreSQL configurado (não SQLite)
- [ ] `SECURE_SSL_REDIRECT=True` (após configurar HTTPS)
- [ ] `SESSION_COOKIE_SECURE=True`
- [ ] `CSRF_COOKIE_SECURE=True`
- [ ] `SECURE_HSTS_SECONDS=31536000`

### Servidor

- [ ] Certificado SSL/TLS ativo (Let's Encrypt ou similar)
- [ ] Nginx configurado com `client_max_body_size 50M`
- [ ] Gunicorn rodando com `--workers` proporcional aos vCPUs (2 × vCPU + 1)
- [ ] Firewall: somente portas 80 e 443 abertas ao público; porta 8000 bloqueada externamente
- [ ] Arquivo `.env` com permissão `600` (`chmod 600 .env`)
- [ ] `.env` no `.gitignore` — nunca commitado

### Banco de dados

- [ ] Usuário do banco com privilégios mínimos (apenas o banco da aplicação)
- [ ] Backup automático configurado (cron ou serviço gerenciado)
- [ ] Acesso ao banco bloqueado externamente (apenas localhost ou VPN)

### Aplicação

- [ ] `python manage.py check --deploy` sem erros críticos
- [ ] `collectstatic` executado após cada deploy
- [ ] `migrate` executado após cada deploy
- [ ] Logs de erro monitorados

### Supabase (se usado)

- [ ] `SUPABASE_SERVICE_ROLE_KEY` nunca exposta no frontend
- [ ] Buckets de storage com políticas de acesso corretas (não públicos por padrão)
- [ ] RLS ativado nas tabelas se acessadas diretamente pelo cliente

---

## Estrutura de Pastas

```
erp_agricola/
├── erp_agricola/        # Configurações do projeto (settings, urls, wsgi)
├── core/                # Middleware, feature flags, utilitários globais
├── templates/           # Templates base (base.html, sidebar.html)
├── static/              # CSS, JS, imagens do projeto
├── staticfiles/         # Destino do collectstatic (não versionar)
├── media/               # Uploads locais (fallback do Supabase)
│
├── empresas/            # Gestão de empresas e planos de assinatura
├── usuarios/            # Autenticação e perfis de usuário
├── cadastros/           # Fazendas, clientes, fornecedores, CFOP, NCM
├── financeiro/          # Contas a pagar/receber, fluxo de caixa
├── plano_contas/        # Plano de contas contábil hierárquico
├── bancario/            # Contas bancárias, conciliação OFX/CNAB
├── faturamento/         # NF-e, CT-e, MDF-e, Invoice exportação
├── compras/             # Pedidos, cotações, XML NF-e
├── estoque/             # Movimentações, inventário
├── vendas/              # Pedidos de venda
├── produtos/            # Cadastro de produtos, NCM, tributação
├── operacoes_campo/     # Ordens de Serviço, portal do campo PWA
├── frota/               # Veículos e máquinas
├── rh/                  # Funcionários, cargos
├── exportacao/          # Bookings, armadores, ordens de coleta
├── embalagem/           # Ordens de embalagem, pallets
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example         # Template de variáveis de ambiente
└── manage.py
```

---

## Suporte

- Issues: https://github.com/EMSSousa/erp_agricola_novo/issues
- Email: ems1844200806@gmail.com
