# Setup Local

Owner: Engenharia
Status: Draft
Last Updated: 2026-07-01
Scope: Ambiente de desenvolvimento

## Objetivo
Padronizar o setup local do projeto com o menor tempo de ativacao possivel.

## Pre-requisitos
- Python 3.9 ou superior
- Git
- PostgreSQL opcional (sem PG configurado, usa SQLite)

## Passo a passo
1. Clonar repositorio e entrar na pasta do projeto.
2. Criar e ativar ambiente virtual.
3. Instalar dependencias.
4. Criar arquivo .env a partir de .env.example.
5. Rodar migracoes.
6. Criar superusuario.
7. Popular seeds principais (opcional recomendado).
8. Iniciar servidor local.

## Seeds recomendadas
- seed_roles
- seed_plano_contas
- import_cfop
- import_ncm
- seed_pragas

## Validacao rapida
- Acessar homepage local
- Acessar admin
- Validar login
- Validar carregamento de menu por perfil

## Variaveis criticas
- SECRET_KEY
- DEBUG
- ALLOWED_HOSTS
- PG_* quando usar PostgreSQL
- SUPABASE_* quando usar storage/servicos Supabase
- FIELD_ENCRYPTION_KEY para campos sensiveis

## Referencia legada
- README.md
