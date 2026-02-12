"""
Utilitarios para envio de relatorios de clientes por email e WhatsApp
"""
from django.core.mail import EmailMessage
from django.conf import settings


class EnviadorRelatorioClientes:
    @staticmethod
    def enviar(destinatario_tipo, destinatario, empresa_nome, arquivo_bytes,
               nome_arquivo, tipo_arquivo='pdf'):
        if destinatario_tipo == 'email':
            assunto = f'Relatorio de Clientes - {empresa_nome}'
            conteudo = f'''
            <html>
                <body>
                    <p>Ola,</p>
                    <p>Segue em anexo o Relatorio de Clientes solicitado.</p>
                    <p>
                        <strong>Empresa:</strong> {empresa_nome}<br>
                        <strong>Data:</strong> {__import__('datetime').datetime.now().strftime('%d/%m/%Y %H:%M')}
                    </p>
                    <p>Atenciosamente,<br>Sistema de ERP</p>
                </body>
            </html>
            '''

            tipo_mime = 'application/pdf' if tipo_arquivo == 'pdf' else 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

            return _enviar_email(destinatario, assunto, conteudo, arquivo_bytes, nome_arquivo, tipo_mime)

        if destinatario_tipo == 'whatsapp':
            return _enviar_whatsapp(destinatario, empresa_nome, arquivo_bytes, nome_arquivo, tipo_arquivo)

        return False, 'Tipo de destinatario invalido'


class EnviadorRelatorioFornecedores:
    @staticmethod
    def enviar(destinatario_tipo, destinatario, empresa_nome, arquivo_bytes,
               nome_arquivo, tipo_arquivo='pdf'):
        if destinatario_tipo == 'email':
            assunto = f'Relatorio de Fornecedores - {empresa_nome}'
            conteudo = f'''
            <html>
                <body>
                    <p>Ola,</p>
                    <p>Segue em anexo o Relatorio de Fornecedores solicitado.</p>
                    <p>
                        <strong>Empresa:</strong> {empresa_nome}<br>
                        <strong>Data:</strong> {__import__('datetime').datetime.now().strftime('%d/%m/%Y %H:%M')}
                    </p>
                    <p>Atenciosamente,<br>Sistema de ERP</p>
                </body>
            </html>
            '''

            tipo_mime = 'application/pdf' if tipo_arquivo == 'pdf' else 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

            return _enviar_email(destinatario, assunto, conteudo, arquivo_bytes, nome_arquivo, tipo_mime)

        if destinatario_tipo == 'whatsapp':
            return _enviar_whatsapp_fornecedores(destinatario, empresa_nome, arquivo_bytes, nome_arquivo, tipo_arquivo)

        return False, 'Tipo de destinatario invalido'


def _enviar_whatsapp_fornecedores(numero_whatsapp, empresa_nome, arquivo_bytes, nome_arquivo, tipo_arquivo='pdf'):
    twilio_account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
    twilio_auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
    twilio_phone = getattr(settings, 'TWILIO_PHONE_NUMBER', None)

    if not all([twilio_account_sid, twilio_auth_token, twilio_phone]):
        return False, 'Twilio nao esta configurado. Configure TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN e TWILIO_PHONE_NUMBER em settings.py'

    try:
        from twilio.rest import Client

        client = Client(twilio_account_sid, twilio_auth_token)

        if not numero_whatsapp.startswith('+'):
            numero_whatsapp = '+' + numero_whatsapp

        mensagem = f'''Ola!

Segue em anexo o Relatorio de Fornecedores de {empresa_nome}.

Arquivo: {nome_arquivo}
Tipo: {tipo_arquivo.upper()}

Atenciosamente,
Sistema de ERP'''

        message = client.messages.create(
            from_=f'whatsapp:{twilio_phone}',
            body=mensagem,
            to=f'whatsapp:{numero_whatsapp}'
        )

        return True, f'Mensagem WhatsApp enviada com sucesso (ID: {message.sid})'

    except ImportError:
        return False, 'Twilio nao esta instalado. Execute: pip install twilio'
    except Exception as exc:
        return False, f'Erro ao enviar WhatsApp: {exc}'


def _enviar_email(destinatario, assunto, conteudo_html, arquivo_bytes, nome_arquivo, tipo_arquivo):
    try:
        email = EmailMessage(
            subject=assunto,
            body=conteudo_html,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[destinatario],
        )

        email.attach(nome_arquivo, arquivo_bytes, tipo_arquivo)
        email.content_subtype = 'html'
        email.send(fail_silently=False)
        return True, 'Email enviado com sucesso'

    except Exception as exc:
        return False, f'Erro ao enviar email: {exc}'


def _enviar_whatsapp(numero_whatsapp, empresa_nome, arquivo_bytes, nome_arquivo, tipo_arquivo='pdf'):
    twilio_account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
    twilio_auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
    twilio_phone = getattr(settings, 'TWILIO_PHONE_NUMBER', None)

    if not all([twilio_account_sid, twilio_auth_token, twilio_phone]):
        return False, 'Twilio nao esta configurado. Configure TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN e TWILIO_PHONE_NUMBER em settings.py'

    try:
        from twilio.rest import Client

        client = Client(twilio_account_sid, twilio_auth_token)

        if not numero_whatsapp.startswith('+'):
            numero_whatsapp = '+' + numero_whatsapp

        mensagem = f'''Ola!

Segue em anexo o Relatorio de Clientes de {empresa_nome}.

Arquivo: {nome_arquivo}
Tipo: {tipo_arquivo.upper()}

Atenciosamente,
Sistema de ERP'''

        message = client.messages.create(
            from_=f'whatsapp:{twilio_phone}',
            body=mensagem,
            to=f'whatsapp:{numero_whatsapp}'
        )

        return True, f'Mensagem WhatsApp enviada com sucesso (ID: {message.sid})'

    except ImportError:
        return False, 'Twilio nao esta instalado. Execute: pip install twilio'
    except Exception as exc:
        return False, f'Erro ao enviar WhatsApp: {exc}'
