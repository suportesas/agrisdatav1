# Configuração de Email e WhatsApp para Relatórios

## Email (SMTP)

Para enviar relatórios por email, adicione as seguintes configurações ao `core/settings.py`:

```python
# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'  # ou seu servidor SMTP
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'seu_email@gmail.com'
EMAIL_HOST_PASSWORD = 'sua_senha_ou_app_password'  # Para Gmail, use App Password
DEFAULT_FROM_EMAIL = 'seu_email@gmail.com'
```

### Obtendo App Password do Gmail:

1. Ative 2FA em sua conta Google
2. Vá para https://myaccount.google.com/apppasswords
3. Gere uma senha de aplicativo para "Mail"
4. Use essa senha no `EMAIL_HOST_PASSWORD`

### Para outro servidor SMTP:

- **Office 365/Outlook**: EMAIL_HOST = 'smtp.office365.com', EMAIL_PORT = 587
- **SendGrid**: EMAIL_HOST = 'smtp.sendgrid.net', EMAIL_HOST_USER = 'apikey'
- **AWS SES**: Use django-ses ou configure manualmente

## WhatsApp (Twilio)

Para enviar mensagens por WhatsApp, configure o Twilio:

```python
# Twilio Configuration
TWILIO_ACCOUNT_SID = 'seu_account_sid'
TWILIO_AUTH_TOKEN = 'seu_auth_token'
TWILIO_PHONE_NUMBER = '+55xxxxxxxxxxxx'  # Seu número Twilio
```

### Obtendo Credenciais Twilio:

1. Crie uma conta em https://www.twilio.com
2. Ative o Sandbox do WhatsApp
3. Copie seu `Account SID` e `Auth Token` do console
4. Configure seu número Twilio para WhatsApp
5. Teste a integração com o número de sandbox fornecido

### Teste de WhatsApp:

```python
from estoque.enviador import EnviadorWhatsApp

sucesso, msg = EnviadorWhatsApp.enviar_relatorio(
    numero_whatsapp='551199999999',
    empresa_nome='Minha Empresa',
    arquivo_bytes=b'...',
    nome_arquivo='relatorio.pdf',
    tipo_arquivo='pdf'
)
print(f"Sucesso: {sucesso}, Mensagem: {msg}")
```

## Variáveis de Ambiente (Recomendado)

Para maior segurança, use variáveis de ambiente:

```bash
# .env
EMAIL_HOST_USER=seu_email@gmail.com
EMAIL_HOST_PASSWORD=sua_app_password
TWILIO_ACCOUNT_SID=seu_sid
TWILIO_AUTH_TOKEN=seu_token
TWILIO_PHONE_NUMBER=+55xxxxxxxxxxxx
```

E em `settings.py`:

```python
import os

EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER')
```

## Teste de Funcionalidade

### Teste de Email:

```python
from django.core.mail import send_mail

send_mail(
    subject='Teste',
    message='Funcionando!',
    from_email='seu_email@gmail.com',
    recipient_list=['destinatario@example.com'],
)
```

### Teste do Gerador de Relatório:

1. Acesse `/estoque/relatorio/`
2. Selecione os filtros desejados
3. Escolha o formato (PDF ou Excel)
4. Selecione o método de envio
5. Insira os contatos
6. Clique em "Gerar Relatório"

## Integração Customizada

Se deseja adicionar novos canais de envio (SMS, Telegram, etc), edite `estoque/enviador.py` e adicione novas classes.

## Resolução de Problemas

### Email não está sendo enviado:

1. Verifique as credenciais no settings.py
2. Ative "App Passwords" se usar Gmail
3. Verifique firewall/proxy
4. Teste com: `python manage.py shell` e execute send_mail

### WhatsApp não está funcionando:

1. Verifique credenciais Twilio
2. Adicione número ao Sandbox do WhatsApp
3. Instale twilio: `pip install twilio`
4. Verifique se o número está no formato correto (+55 com código do país)
