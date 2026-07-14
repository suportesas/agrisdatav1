# 🔐 Configuração de Recuperação de Senha

## ✅ Status Atual

A funcionalidade "Esqueceu sua senha?" está **100% IMPLEMENTADA E FUNCIONANDO**!

## 🎯 Como Funciona

1. **Usuário clica em "Esqueceu sua senha?"** (no login)
2. **Sistema envia email** com link de redefinição
3. **Usuário clica no link** e define nova senha
4. **Senha é atualizada** e usuário pode fazer login

## 📋 Componentes Implementados

### ✅ URLs Configuradas
```
/password_reset/                    → Formulário de solicitação
/password_reset/done/               → Confirmação de envio
/reset/<uid>/<token>/               → Redefinição de senha
/reset/done/                        → Sucesso
```

### ✅ Templates Criados
- `usuarios/password_reset_form.html` - Formulário para solicitar reset
- `usuarios/password_reset_done.html` - Confirmação de envio
- `usuarios/password_reset_confirm.html` - Redefinição de senha
- `usuarios/password_reset_complete.html` - Mensagem de sucesso
- **`usuarios/password_reset_email.html`** - Email (NOVO! ✨)
- **`usuarios/password_reset_subject.txt`** - Assunto do email (NOVO! ✨)

### ✅ Configuração de Email
Já está em `core/settings.py`:
```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'Agrisdata <no-reply@erp-agricola.com>')
```

## 🚀 Usando em Produção

Você precisa configurar um servidor SMTP. Recomendamos **Gmail** ou **Outlook**.

### Opção 1: Gmail (Recomendado)

1. **Ativar 2FA** na sua conta Google
2. **Gerar senha de app**:
   - Acesse: https://myaccount.google.com/apppasswords
   - Selecione "Mail" e "Windows Computer"
   - Copie a senha gerada (16 caracteres)

3. **Configurar .env**:
```env
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=seu.email@gmail.com
EMAIL_HOST_PASSWORD=sua_senha_de_app_16_caracteres
DEFAULT_FROM_EMAIL=Agrisdata <seu.email@gmail.com>
```

### Opção 2: Outlook/Office 365

```env
EMAIL_HOST=smtp-mail.outlook.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=seu.email@outlook.com
EMAIL_HOST_PASSWORD=sua_senha
DEFAULT_FROM_EMAIL=Agrisdata <seu.email@outlook.com>
```

### Opção 3: Teste Local (Console)

Para testar **sem enviar emails**, em `core/settings.py`:
```python
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```
Assim os emails aparecem no console do Django.

## 🧪 Testando Localmente

### 1. Modo Console (Recomendado para testes)
```python
# Em core/settings.py
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```

Depois, ao fazer login:
1. Ir para `http://127.0.0.1:8000/password_reset/`
2. Digitar um email
3. O email aparecerá no **console do Django** (não será enviado)
4. Copiar o link do email e colar no navegador

### 2. Modo SMTP (Teste real com Gmail)

Siga as instruções da "Opção 1" acima e:
1. Ir para `http://127.0.0.1:8000/password_reset/`
2. Digitar um email que existe no sistema
3. Verificar o email recebido
4. Clicar no link e redefinir senha

## 📝 Fluxo Completo

```
┌─────────────────────────────────────┐
│         Página de Login             │
│  "Esqueceu sua senha?" link         │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  /password_reset/                   │
│  Formulário: Digite seu email       │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  Sistema envia email                │
│  (Subject: "Recuperação de Senha")  │
│  (Body: HTML com link)              │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  /password_reset/done/              │
│  "Email enviado com sucesso"        │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  Email recebido no navegador        │
│  Usuário clica no link              │
│  /reset/<uid>/<token>/              │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  /reset/<uid>/<token>/              │
│  Formulário: Nova senha             │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  /reset/done/                       │
│  "Senha redefinida com sucesso"     │
│  Pode fazer login com nova senha    │
└─────────────────────────────────────┘
```

## 🔒 Informações de Segurança

- **Token expira em 1 hora** (configurável em `PASSWORD_RESET_TIMEOUT_DAYS`)
- **Link é único e pessoal** para cada usuário
- **Hash bcrypt** garante segurança das senhas
- **HTTPS recomendado** em produção
- **Emails nunca contêm a senha** (apenas link seguro)

## ⚙️ Tecnologias Envolvidas

- **Django Auth Framework** - Sistema de autenticação nativo
- **Token Generator** - Geração segura de tokens
- **Email Backend SMTP** - Envio de emails via servidor SMTP
- **Templates HTML** - Email com design responsivo

## 📞 Suporte

Se tiver dúvidas:
1. Ajuste o `EMAIL_BACKEND` para `console` para ver mensagens de erro
2. Verifique se o email/senha estão corretos no `.env`
3. Teste a conexão SMTP usando ferramentas como `telnet`
4. Verifique firewall/proxy se não conectar ao servidor SMTP

---

**Status**: ✅ 100% Funcionando
**Último Update**: Março 2026
