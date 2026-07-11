# Deploy no Railway

Owner: DevOps
Status: Draft
Last Updated: 2026-07-01
Scope: Deploy cloud

## Objetivo
Registrar procedimento padrao de publicacao do sistema no Railway.

## Fluxo resumido
1. Publicar codigo atualizado no GitHub.
2. Criar projeto no Railway via import de repositorio.
3. Configurar variaveis de ambiente obrigatorias.
4. Disparar deploy e validar logs.
5. Rodar migracoes e criar usuario admin.

## Variaveis minimas
- DEBUG=False
- SECRET_KEY
- ALLOWED_HOSTS
- PG_NAME, PG_USER, PG_PASSWORD, PG_HOST, PG_PORT
- SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY

## Pos-deploy
- Rodar migracoes
- Criar superusuario
- Testar login
- Testar fluxo critico de negocio
- Testar upload/arquivos

## Falhas comuns
- Invalid host: ajustar ALLOWED_HOSTS
- Erro de banco: revisar PG_*
- Erro de import: garantir dependencia em requirements

## Referencia legada
- DEPLOY_RAILWAY.md
