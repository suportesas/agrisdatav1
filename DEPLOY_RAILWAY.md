# 🚀 Deploy do ERP Agrícola em Railway.app

Railway é uma plataforma de deployment gratuita e muito fácil. Em 5 minutos seu Django está online!

## ✅ Pré-requisitos

- [x] GitHub (você já tem)
- [x] Conta Google ou GitHub para Railway
- [x] Projeto Django pronto (você já tem)
- [x] Supabase PostgreSQL configurado (você já tem)

---

## 📋 Passo 1: Preparar Git

Certifique-se que tudo está no Git:

```bash
cd c:\erp_agricola
git status
git add .
git commit -m "Deploy: Preparar para Railway"
git push
```

✅ **Verificar**: Vá para https://github.com/EMSSousa/erp_agricola_novo e confirme que tudo está lá.

---

## 🔧 Passo 2: Criar conta em Railway

1. Acesse: https://railway.app/
2. Clique em **"Sign Up"**
3. Escolha **"Continue with GitHub"**
4. Autorize Railway a acessar seu GitHub

✅ **Resultado**: Você está logado no Railway

---

## 🚀 Passo 3: Criar novo projeto

1. No Railway, clique em **"+ New Project"**
2. Escolha **"Deploy from GitHub"**
3. Procure por: `erp_agricola_novo`
4. Clique em **"Import GitHub Repository"**

✅ **Resultado**: Railway vai detectar seu Django e começar o setup

---

## 🔐 Passo 4: Configurar variáveis de ambiente

Railway vai pedir as variáveis de ambiente. Você precisa adicionar:

### ⚙️ Variáveis básicas do Django

```
DEBUG=False
SECRET_KEY=sua-chave-secreta-aqui
ALLOWED_HOSTS=seu-app.railway.app,localhost
```

### 🗄️ Variáveis do Supabase (copie do seu .env)

```
SUPABASE_URL=https://aycjmeeteinbjvqnrycj.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...

PG_NAME=postgres
PG_USER=postgres.aycjmeeteinbjvqnrycj
PG_PASSWORD=sua-senha-supabase
PG_HOST=aws-1-sa-east-1.pooler.supabase.com
PG_PORT=6543
```

### 📧 Variáveis de email (opcional)

```
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=seu-email@gmail.com
EMAIL_HOST_PASSWORD=sua-senha-gmail
```

✅ **Como fazer**:
1. No Railway, clique em **Variables**
2. Adicione cada variável (uma por uma)
3. Clique em **Save**

---

## 🌐 Passo 5: Deploy automático

Railway vai automaticamente:
1. Detectar `Procfile` (você já tem)
2. Instalar `requirements.txt` (você já tem)
3. Rodar migrações Django
4. Iniciar o servidor Gunicorn

✅ **Resultado**: Seu app estará em uma URL como `seu-app.railway.app`

---

## 🔄 Passo 6: Executar migrações (uma única vez)

Após o deploy inicial, você precisa rodar as migrações:

No Railway, vá para **Deploy** → **Run migrations**:

```bash
python manage.py migrate
python manage.py createsuperuser
```

Ou clique no aba "Console" e execute:

```
$ python manage.py migrate
$ python manage.py createsuperuser
```

✅ **Resultado**: Banco de dados está pronto

---

## ✨ Pronto! Agora seu app está online!

**Seu app está em**: `https://seu-app.railway.app`

---

## 📱 Testar no celular

Agora você consegue acessar no celular de qualquer lugar (não precisa mais estar no WiFi):

1. **De 4G/5G**: `https://seu-app.railway.app`
2. **Qualquer dispositivo**: Funciona!
3. **Email**: Funciona!
4. **Banco de dados**: Supabase (tudo sincronizado)

---

## 🔄 Atualizações contínuas (Auto-Deploy)

Toda vez que você faz `git push`, Railway **automaticamente**:
1. Detecta o novo código
2. Reconstrói a imagem Docker
3. Deploya a nova versão
4. Seu app fica online com os novos changess

Não precisa fazer nada! Só fazer `git push` 🎯

---

## 🚨 Se algo der errado

### ❌ Erro 500 ou 502

Vá para Railway → **Logs** e veja o erro:

```bash
# Comum: SECRET_KEY não configurado
# Solução: Adicione SECRET_KEY nas Variables

# Comum: Banco de dados não conecta
# Solução: Verifique PG_HOST, PG_USER, PG_PASSWORD
```

### ❌ Erro "Invalid host"

Problema: `ALLOWED_HOSTS` está wrong

Solução: Em Railway, clique em **Settings** → copie sua URL → adicione em `ALLOWED_HOSTS`

### ❌ Erro de import/módulo

Problema: Faltou instalar dependência

Solução: Adicione em `requirements.txt` e faça `git push`

---

## 📚 Referências

- [Railway docs](https://docs.railway.app/)
- [Django + Railway guide](https://docs.railway.app/guides/django)
- [Environment variables Railway](https://docs.railway.app/guides/variables)

---

## 🎉 Checklist final

- [ ] Código está no GitHub
- [ ] Projeto criado no Railway
- [ ] Variáveis de ambiente configuradas
- [ ] Procfile existe no repositório
- [ ] requirements.txt existe no repositório
- [ ] Migrações executadas
- [ ] App rodando em `https://seu-app.railway.app`
- [ ] Celular acessa de fora do WiFi ✅

---

**Próximos passos**:
1. Testar upload de arquivos (logo da empresa)
2. Testar envio de emails
3. Testar relatórios e PDFs
4. Configurar domínio customizado (opcional)

**Status**: 🚀 Seu ERP Agrícola agora é acessível de qualquer lugar!
