Owner: DevOps
Status: Approved
Last Updated: 2026-07-10
Scope: Deploy cloud (Railway)

# Deploy no Railway

Railway é uma alternativa rápida ao deploy manual em VPS (Nginx + Gunicorn, ver `README.md` raiz) — publica o Django direto a partir do GitHub, sem provisionar servidor.

## Pré-requisitos
- Repositório no GitHub atualizado (`git push` do branch de deploy)
- Conta Railway (login via GitHub)
- Banco PostgreSQL já provisionado (Supabase ou o próprio Railway Postgres)
- `Procfile` e `requirements.txt` presentes na raiz do repositório

## Passo a passo

1. **Preparar o repositório**
   ```bash
   git status
   git add .
   git commit -m "Deploy: preparar para Railway"
   git push
   ```

2. **Criar o projeto no Railway**
   - Acesse https://railway.app/ → **Sign Up** → **Continue with GitHub**
   - **+ New Project** → **Deploy from GitHub** → selecione o repositório do ERP
   - Railway detecta o `Procfile` e o `requirements.txt` automaticamente

3. **Configurar variáveis de ambiente**
   Em **Variables**, adicione (uma por uma ou via "Raw Editor"):

   ```
   DEBUG=False
   SECRET_KEY=<gerar uma chave forte>
   ALLOWED_HOSTS=<seu-app>.railway.app

   PG_NAME=
   PG_USER=
   PG_PASSWORD=
   PG_HOST=
   PG_PORT=

   SUPABASE_URL=
   SUPABASE_ANON_KEY=
   SUPABASE_SERVICE_ROLE_KEY=

   FIELD_ENCRYPTION_KEY=<gerar com Fernet.generate_key()>

   EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
   EMAIL_HOST=smtp.gmail.com
   EMAIL_PORT=587
   EMAIL_USE_TLS=True
   EMAIL_HOST_USER=
   EMAIL_HOST_PASSWORD=
   ```
   Ver a lista completa e atualizada de variáveis em `CLAUDE.md` (seção "Key .env variables") e `README.md` (seção "Variáveis de Ambiente").

4. **Deploy automático**
   Railway instala `requirements.txt`, roda o build e inicia o Gunicorn definido no `Procfile`. Cada `git push` no branch conectado dispara um novo deploy automaticamente.

5. **Rodar migrações e criar superusuário** (uma vez, após o primeiro deploy)
   Pelo console do serviço no Railway:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

6. **Checklist final**
   - [ ] Código no GitHub e branch conectado ao projeto Railway
   - [ ] Variáveis de ambiente configuradas (`DEBUG=False` em produção)
   - [ ] Migrações executadas
   - [ ] Login funcionando na URL pública (`https://<seu-app>.railway.app`)
   - [ ] Upload de arquivo (ex: logo da empresa) testado
   - [ ] Envio de e-mail testado
   - [ ] Domínio customizado configurado (opcional)

## Falhas comuns

| Sintoma | Causa provável | Solução |
|---|---|---|
| Erro 500/502 nos logs do Railway | `SECRET_KEY` ausente ou banco inacessível | Conferir `SECRET_KEY` e variáveis `PG_*`/`SUPABASE_*` em Variables |
| `Invalid HTTP_HOST header` | `ALLOWED_HOSTS` não inclui o domínio do Railway | Copiar a URL pública gerada e adicionar em `ALLOWED_HOSTS` |
| `ModuleNotFoundError` no build | Dependência faltando | Adicionar ao `requirements.txt` e `git push` novamente |

## Referências
- [Railway docs](https://docs.railway.app/)
- [Django + Railway guide](https://docs.railway.app/guides/django)
- Deploy alternativo (VPS/Nginx/Gunicorn, Docker Compose, CI/CD): `README.md` raiz
