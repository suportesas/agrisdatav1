# Configuração de Envio de Emails no Agrisdata

## 🔍 O Problema

Você estava com o email configurado em modo **desenvolvimento** (`console.EmailBackend`), que apenas imprime os emails no terminal ao invés de enviar de verdade. Por isso aparecia a mensagem de "enviado com sucesso" mas o email nunca chegava.

## ✅ Solução Implementada

Atualizei as configurações para usar SMTP real e ler as credenciais de um arquivo `.env`.

## 📋 Passos para Configurar

### 1. Editar o arquivo `.env`

Abra o arquivo `.env` na raiz do projeto (`c:\erp_agricola\.env`) e preencha com seus dados:

```env
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=seu.email@gmail.com
EMAIL_HOST_PASSWORD=sua_senha_de_app_aqui
DEFAULT_FROM_EMAIL=Agrisdata <seu.email@gmail.com>
```

### 2. Obter Senha de App do Gmail (IMPORTANTE!)

⚠️ **NÃO use sua senha normal do Gmail!** Você precisa gerar uma "Senha de App":

1. **Ative a verificação em 2 etapas** (se ainda não tiver):
   - Acesse: https://myaccount.google.com/security
   - Procure por "Verificação em duas etapas"
   - Siga os passos para ativar

2. **Gere uma Senha de App**:
   - Acesse: https://myaccount.google.com/apppasswords
   - Na seção "App", selecione **"Outro (nome personalizado)"**
   - Digite: **"Agrisdata"**
   - Clique em **"Gerar"**

3. **Copie a senha gerada**:
   - O Google mostrará uma senha de 16 caracteres como: `abcd efgh ijkl mnop`
   - Copie e cole no `.env` **SEM espaços**: `abcdefghijklmnop`

### 3. Reiniciar o Servidor Django

Depois de configurar o `.env`, reinicie o servidor:

```powershell
# Pare o servidor (Ctrl+C) e reinicie:
python manage.py runserver
```

### 4. Testar o Envio

1. Vá em um pedido de compra
2. Clique em **"Enviar por Email"**
3. Digite o email de destino
4. Clique em **"Enviar"**
5. Verifique sua caixa de entrada (e spam)

## 📧 Provedores de Email Suportados

### Gmail (Recomendado)
```env
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=seu.email@gmail.com
EMAIL_HOST_PASSWORD=senha_de_app_16_caracteres
DEFAULT_FROM_EMAIL=Agrisdata <seu.email@gmail.com>
```

### Outlook/Hotmail
```env
EMAIL_HOST=smtp-mail.outlook.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=seu.email@outlook.com
EMAIL_HOST_PASSWORD=sua_senha_normal
DEFAULT_FROM_EMAIL=Agrisdata <seu.email@outlook.com>
```

### Office 365
```env
EMAIL_HOST=smtp.office365.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=seu.email@empresa.com
EMAIL_HOST_PASSWORD=sua_senha_normal
DEFAULT_FROM_EMAIL=Agrisdata <seu.email@empresa.com>
```

## 🔧 Modo de Desenvolvimento (sem enviar emails)

Se você quiser voltar ao modo de desenvolvimento (emails no console), edite o `.env`:

```env
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

## ❓ Problemas Comuns

### "Erro de autenticação" ou "Username and Password not accepted"
- ✅ Certifique-se de usar **Senha de App**, não sua senha normal
- ✅ Verifique se a verificação em 2 etapas está ativa
- ✅ Confirme que copiou a senha sem espaços

### Email não chega
- ✅ Verifique a pasta de **Spam/Lixeira**
- ✅ Confirme que o EMAIL_HOST_USER está correto
- ✅ Teste enviando para outro email seu

### "SMTPAuthenticationError"
- ✅ Credenciais incorretas - gere nova senha de app
- ✅ Verifique se o Gmail permite apps menos seguros (não necessário com senha de app)

### "Connection refused" ou "timeout"
- ✅ Verifique sua conexão com a internet
- ✅ Firewall pode estar bloqueando a porta 587
- ✅ Tente usar porta 465 com EMAIL_USE_SSL=True

## 📝 Observações

- O arquivo `.env` **NÃO deve ser commitado** no Git (já está no .gitignore)
- Mantenha suas credenciais seguras
- Em produção, use variáveis de ambiente do servidor, não o arquivo `.env`
- O PDF do pedido será anexado automaticamente ao email

## 🎯 Resumo das Alterações

### Arquivos Modificados:
1. **core/settings.py**: 
   - Mudou de `console.EmailBackend` para `smtp.EmailBackend`
   - Adicionou leitura de variáveis do `.env`
   - Importou `load_dotenv`

2. **.env**: Criado com template para configuração

3. **.env.example**: Atualizado com instruções detalhadas

### Nada quebrou:
- WhatsApp continua funcionando normalmente ✅
- PDF continua sendo gerado ✅
- Apenas o envio de email agora funcionará de verdade ✅
