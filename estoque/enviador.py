"""
Utilitários para envio de email e WhatsApp
"""
import os
from django.core.mail import EmailMessage
from django.conf import settings
import requests
from io import BytesIO


class EnviadorEmail:
    """Classe para enviar email com anexos"""
    
    @staticmethod
    def enviar_relatorio(destinatario, assunto, conteudo_html, arquivo_bytes, 
                        nome_arquivo, tipo_arquivo='application/pdf'):
        """
        Enviar email com relatório anexado
        
        Args:
            destinatario: Email do destinatário
            assunto: Assunto do email
            conteudo_html: Corpo do email em HTML
            arquivo_bytes: Bytes do arquivo a anexar
            nome_arquivo: Nome do arquivo anexado
            tipo_arquivo: Tipo MIME do arquivo
        """
        try:
            email = EmailMessage(
                subject=assunto,
                body=conteudo_html,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[destinatario],
            )
            
            # Anexar arquivo
            email.attach(nome_arquivo, arquivo_bytes, tipo_arquivo)
            email.content_subtype = 'html'
            
            # Enviar
            email.send(fail_silently=False)
            return True, 'Email enviado com sucesso'
            
        except Exception as e:
            return False, f'Erro ao enviar email: {str(e)}'


class EnviadorWhatsApp:
    """Classe para enviar mensagens via WhatsApp"""
    
    @staticmethod
    def enviar_relatorio(numero_whatsapp, empresa_nome, arquivo_bytes, 
                        nome_arquivo, tipo_arquivo='pdf'):
        """
        Enviar relatório via WhatsApp usando Twilio
        
        Args:
            numero_whatsapp: Número com código do país (ex: 55119999999)
            empresa_nome: Nome da empresa
            arquivo_bytes: Bytes do arquivo
            nome_arquivo: Nome do arquivo
            tipo_arquivo: Tipo do arquivo (pdf ou excel)
        """
        
        # Verificar se Twilio está configurado
        twilio_account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
        twilio_auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
        twilio_phone = getattr(settings, 'TWILIO_PHONE_NUMBER', None)
        
        if not all([twilio_account_sid, twilio_auth_token, twilio_phone]):
            return False, 'Twilio não está configurado. Configure TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN e TWILIO_PHONE_NUMBER em settings.py'
        
        try:
            from twilio.rest import Client
            
            client = Client(twilio_account_sid, twilio_auth_token)
            
            # Formatar número
            if not numero_whatsapp.startswith('+'):
                numero_whatsapp = '+' + numero_whatsapp
            
            # Mensagem
            mensagem = f'''Olá!

Segue em anexo o Relatório de Estoque de {empresa_nome}.

Arquivo: {nome_arquivo}
Tipo: {tipo_arquivo.upper()}

Atenciosamente,
Sistema de ERP'''
            
            # Enviar mensagem de texto
            message = client.messages.create(
                from_=f'whatsapp:{twilio_phone}',
                body=mensagem,
                to=f'whatsapp:{numero_whatsapp}'
            )
            
            return True, f'Mensagem WhatsApp enviada com sucesso (ID: {message.sid})'
            
        except ImportError:
            return False, 'Twilio não está instalado. Execute: pip install twilio'
        except Exception as e:
            return False, f'Erro ao enviar WhatsApp: {str(e)}'


class EnviadorRelatorio:
    """Classe coordenadora para envio de relatórios"""
    
    @staticmethod
    def enviar(destinatario_tipo, destinatario, empresa_nome, arquivo_bytes, 
               nome_arquivo, tipo_arquivo='pdf'):
        """
        Enviar relatório via email ou WhatsApp
        
        Args:
            destinatario_tipo: 'email' ou 'whatsapp'
            destinatario: Email ou número WhatsApp
            empresa_nome: Nome da empresa
            arquivo_bytes: Bytes do arquivo
            nome_arquivo: Nome do arquivo
            tipo_arquivo: Tipo do arquivo
        """
        
        if destinatario_tipo == 'email':
            assunto = f'Relatório de Estoque - {empresa_nome}'
            conteudo = f'''
            <html>
                <body>
                    <p>Olá,</p>
                    <p>Segue em anexo o Relatório de Estoque solicitado.</p>
                    <p>
                        <strong>Empresa:</strong> {empresa_nome}<br>
                        <strong>Data:</strong> {__import__('datetime').datetime.now().strftime('%d/%m/%Y %H:%M')}
                    </p>
                    <p>Atenciosamente,<br>Sistema de ERP</p>
                </body>
            </html>
            '''
            
            tipo_mime = 'application/pdf' if tipo_arquivo == 'pdf' else 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            
            return EnviadorEmail.enviar_relatorio(
                destinatario, assunto, conteudo, arquivo_bytes, 
                nome_arquivo, tipo_mime
            )
        
        elif destinatario_tipo == 'whatsapp':
            return EnviadorWhatsApp.enviar_relatorio(
                destinatario, empresa_nome, arquivo_bytes, 
                nome_arquivo, tipo_arquivo
            )
        
        else:
            return False, 'Tipo de destinatário inválido'
