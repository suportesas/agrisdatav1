# 🚀 GUIA SUPABASE - BANCO DE DADOS NA NUVEM
## Setup Completo e Configuração Django

---

## 📋 O QUE É SUPABASE?

**Supabase** = PostgreSQL Gerenciado na Nuvem

```
Vantagens:
✅ PostgreSQL completo (não é "lite")
✅ Sem manutenção de servidor
✅ Backups automáticos (24h)
✅ SSL por padrão
✅ Escalável automaticamente
✅ Plano gratuito generoso
✅ Integração JWT automática
✅ Real-time listeners (bônus)

Perfeito para: Produção, Staging, Desenvolvimento compartilhado
```

---

## 🔧 SETUP SUPABASE (5 minutos)

### Passo 1: Criar Conta

1. Acesse: **https://supabase.com**
2. Clique: **"Sign Up"**
3. Escolha: **"Continue with GitHub"** (mais fácil)
4. Autorize Supabase
5. Pronto! Conta criada ✓

### Passo 2: Criar Projeto

1. Dashboard → **"New Project"**
2. Preencha:
   - **Name:** `packing-db`
   - **Password:** Mínimo 12 caracteres (salve em lugar seguro!)
   - **Region:** Escolha mais próximo (ex: São Paulo)
   - **Pricing Plan:** `Free` (grátis!)
3. Clique: **"Create new project"**
4. Aguarde: 2-3 minutos (Supabase está criando seu servidor)

### Passo 3: Copiar Credenciais

Quando pronto, você verá:

```
Project URL: https://[project-id].supabase.co
Anon Key: eyJ...
Service Role Key: eyJ...
```

**IMPORTANTE:** Vá para **"Settings" → "Database"** para pegar o URL de conexão:

```
PostgreSQL URL:
postgresql://postgres:[password]@[project-id].supabase.co:5432/postgres
```

Copie este URL! (Você precisa dele)

---

## 📝 CONFIGURAR DJANGO PARA SUPABASE

### Passo 1: Instalar Dependência

```bash
pip install dj-database-url
```

### Passo 2: Criar Arquivo .env

Crie arquivo `.env` na raiz do projeto (mesmo nível de manage.py):

```bash
# .env

# Supabase
DATABASE_URL=postgresql://postgres:[SUA_PASSWORD]@[PROJECT_ID].supabase.co:5432/postgres

# Django
SECRET_KEY=seu-secret-key-aqui
DEBUG=False (em produção)
ALLOWED_HOSTS=localhost,127.0.0.1,[seu-dominio].com
```

**Onde encontrar?**
- `[SUA_PASSWORD]` = Senha que você criou no Passo 2
- `[PROJECT_ID]` = Vem na URL (https://[PROJECT_ID].supabase.co)

### Passo 3: Adicionar ao settings.py

Abra `config/settings.py` e substitua a seção `DATABASES`:

```python
# config/settings.py

import dj_database_url
from decouple import config

# ===== SUPABASE DATABASE =====
DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL'),
        conn_max_age=600,  # Connection pooling
        conn_health_checks=True,
    )
}

# Para fallback em desenvolvimento local (opcional):
if not config('DATABASE_URL', default=''):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'packing_db',
            'USER': 'postgres',
            'PASSWORD': 'senha',
            'HOST': 'localhost',
            'PORT': '5432',
        }
    }
```

### Passo 4: Testar Conexão

```bash
python manage.py dbshell

# Se aparecer: "PostgreSQL 15.x"
# Significa que conectou com sucesso! ✓

# Sair: \q
```

### Passo 5: Fazer Migrations

```bash
python manage.py migrate

# Resposta esperada:
# "Running migrations..."
# "Applying core.0001_initial... OK"
# etc
```

Pronto! 🎉 Seu banco está na nuvem!

---

## 🔒 SEGURANÇA SUPABASE

### Proteger Credenciais

**NUNCA** coloque DATABASE_URL direto no código!

```python
# ❌ ERRADO
DATABASES = {
    'default': {
        'PASSWORD': 'minha_senha_123'  # Alguém vê no GitHub!
    }
}

# ✅ CORRETO
# Use .env + decouple
```

### .gitignore

Certifique-se que `.env` está em `.gitignore`:

```bash
# .gitignore
.env
.env.local
*.sqlite3
venv/
__pycache__/
```

### Variáveis de Ambiente em Produção

Se usar Heroku, Railway, ou similar:

```bash
# Heroku example
heroku config:set DATABASE_URL=postgresql://...

# Railway, Vercel, etc têm interface similares
```

---

## 🚨 TROUBLESHOOTING

### Erro: "psycopg2: could not connect"

**Causa:** DATABASE_URL incorreta

**Solução:**
1. Copie novamente de Settings → Database (na Supabase)
2. Verifique password (com caracteres especiais?)
3. Teste com psql local:
   ```bash
   psql "postgresql://postgres:[password]@[id].supabase.co:5432/postgres"
   ```

### Erro: "SSL certificate_verify_failed"

**Causa:** SSL do Supabase

**Solução:** Django geralmente resolve sozinho, mas se persistir:

```python
# Em settings.py
DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL'),
        conn_max_age=600,
        OPTIONS={
            'sslmode': 'require',
        }
    )
}
```

### Erro: "Too many connections"

**Causa:** Pool de conexões cheio

**Solução:**

```python
# Reduzir conexões simultâneas
CONN_MAX_AGE = 300  # 5 minutos ao invés de 600
```

---

## 📊 MONITORAR SUPABASE

### Dashboard

Seu dashboard mostra:
- **Active Connections** - Conexões ativas agora
- **Database Size** - Tamanho do banco (gratuito: 500MB)
- **Backups** - Histórico automático
- **Logs** - Queries lentas, erros

### Fazer Backup Manual

Dashboard → Settings → Backups → **"Create manual backup"**

---

## 💾 MIGRAR DE LOCAL PARA SUPABASE

Se já tem dados em PostgreSQL local:

### Backup Local

```bash
pg_dump -U postgres packing_db > backup.sql
```

### Restore em Supabase

```bash
psql "postgresql://postgres:[password]@[id].supabase.co:5432/postgres" < backup.sql
```

---

## 🎯 PRÓXIMOS PASSOS

- [x] Supabase account criado
- [x] Projeto criado
- [x] DATABASE_URL copiada
- [x] .env configurado
- [x] Django settings.py atualizado
- [x] Migrations rodadas
- [ ] Próximo: Implementar modelos (ver 6_CHECKLIST_IMPLEMENTACAO.md Fase 2)

---

## 📞 REFERÊNCIAS

- **Supabase Docs:** https://supabase.com/docs
- **DJ-Database-URL:** https://github.com/jazzband/dj-database-url
- **Django Database Setup:** https://docs.djangoproject.com/en/4.2/ref/settings/#databases

---

**Status:** ✅ Pronto para Usar  
**Data:** 01/07/2026  
**Versão:** 1.0
