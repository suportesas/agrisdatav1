from django.conf import settings
from django.core.mail import EmailMessage
from django.core.management.base import BaseCommand
from django.utils import timezone

from rh.models import LogEnvioSolicitacaoASO, SolicitacaoASO


class Command(BaseCommand):
    help = 'Envia alertas de vencimento de ASO por email/WhatsApp e registra logs.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--empresa-id',
            type=int,
            help='ID da empresa para processar (opcional). Sem informar, processa todas.'
        )
        parser.add_argument(
            '--canal',
            choices=['email', 'whatsapp', 'ambos'],
            default='ambos',
            help='Canal de envio do alerta (padrao: ambos).'
        )
        parser.add_argument(
            '--incluir-vencidos',
            action='store_true',
            help='Inclui solicitacoes ja vencidas (dias restantes < 0).'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Apenas simula os envios sem enviar mensagens nem gravar log.'
        )

    def handle(self, *args, **options):
        hoje = timezone.now().date()
        empresa_id = options.get('empresa_id')
        canal = options.get('canal')
        incluir_vencidos = options.get('incluir_vencidos')
        dry_run = options.get('dry_run')

        qs = SolicitacaoASO.objects.filter(
            gerar_alerta_vencimento=True,
            data_vencimento__isnull=False,
            status__in=['ASSINADO', 'ENVIADO', 'CONCLUIDO'],
        ).select_related('empresa', 'funcionario')

        if empresa_id:
            qs = qs.filter(empresa_id=empresa_id)

        total_candidatas = qs.count()
        total_alerta = 0
        total_sucesso = 0
        total_falha = 0
        total_ignoradas = 0

        self.stdout.write(
            f'Iniciando alerta ASO | candidatas={total_candidatas} | canal={canal} | dry_run={dry_run}'
        )

        for solicitacao in qs.iterator():
            dias_restantes = solicitacao.dias_para_vencimento()
            if dias_restantes is None:
                total_ignoradas += 1
                continue

            if dias_restantes < 0 and not incluir_vencidos:
                total_ignoradas += 1
                continue

            if dias_restantes > solicitacao.dias_antecedencia_alerta:
                total_ignoradas += 1
                continue

            total_alerta += 1

            if canal in ['email', 'ambos']:
                sucesso, retorno = self._enviar_alerta_email(
                    solicitacao=solicitacao,
                    hoje=hoje,
                    dry_run=dry_run,
                )
                if sucesso:
                    total_sucesso += 1
                else:
                    total_falha += 1
                self.stdout.write(
                    f'ASO {solicitacao.pk} EMAIL: {retorno}'
                )

            if canal in ['whatsapp', 'ambos']:
                sucesso, retorno = self._enviar_alerta_whatsapp(
                    solicitacao=solicitacao,
                    hoje=hoje,
                    dry_run=dry_run,
                )
                if sucesso:
                    total_sucesso += 1
                else:
                    total_falha += 1
                self.stdout.write(
                    f'ASO {solicitacao.pk} WHATSAPP: {retorno}'
                )

        self.stdout.write(
            self.style.SUCCESS(
                'Resumo alerta ASO | '
                f'em_alerta={total_alerta} | sucesso={total_sucesso} | falha={total_falha} | ignoradas={total_ignoradas}'
            )
        )

    def _ja_enviado_hoje(self, solicitacao, canal, hoje):
        return LogEnvioSolicitacaoASO.objects.filter(
            solicitacao=solicitacao,
            canal=canal,
            data_envio__date=hoje,
            retorno__icontains='[ALERTA_VENCIMENTO]'
        ).exists()

    def _registrar_log(self, solicitacao, canal, destinatario, sucesso, retorno):
        LogEnvioSolicitacaoASO.objects.create(
            solicitacao=solicitacao,
            canal=canal,
            destinatario=destinatario or '-',
            status_envio='SUCESSO' if sucesso else 'FALHA',
            retorno=f'[ALERTA_VENCIMENTO] {retorno}',
        )

    def _enviar_alerta_email(self, solicitacao, hoje, dry_run=False):
        destinatario = (solicitacao.laboratorio_email or '').strip()

        if self._ja_enviado_hoje(solicitacao, 'EMAIL', hoje):
            return True, 'Ignorado: alerta por email ja enviado hoje.'

        if not destinatario:
            retorno = 'Falha: email do laboratorio nao informado.'
            if not dry_run:
                self._registrar_log(solicitacao, 'EMAIL', '-', False, retorno)
            return False, retorno

        dias = solicitacao.dias_para_vencimento()
        assunto = f'Alerta ASO - vencimento em {dias} dia(s) - {solicitacao.funcionario.nome_completo}'
        conteudo = f'''
        <html>
            <body>
                <p>Ola,</p>
                <p>Este e um alerta de vencimento da solicitacao de ASO.</p>
                <p>
                    <strong>Funcionario:</strong> {solicitacao.funcionario.nome_completo}<br>
                    <strong>Tipo de ASO:</strong> {solicitacao.get_tipo_aso_display()}<br>
                    <strong>Data de vencimento:</strong> {solicitacao.data_vencimento.strftime('%d/%m/%Y')}<br>
                    <strong>Dias restantes:</strong> {dias}
                </p>
                <p>Empresa: {solicitacao.empresa.nome}</p>
            </body>
        </html>
        '''

        if dry_run:
            return True, f'DRY-RUN: enviaria email para {destinatario}.'

        try:
            email = EmailMessage(
                subject=assunto,
                body=conteudo,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
                to=[destinatario],
            )
            email.content_subtype = 'html'
            email.send(fail_silently=False)

            retorno = 'Alerta enviado por email com sucesso.'
            self._registrar_log(solicitacao, 'EMAIL', destinatario, True, retorno)
            return True, retorno
        except Exception as exc:
            retorno = f'Erro ao enviar email: {exc}'
            self._registrar_log(solicitacao, 'EMAIL', destinatario, False, retorno)
            return False, retorno

    def _enviar_alerta_whatsapp(self, solicitacao, hoje, dry_run=False):
        destinatario = (solicitacao.trabalhador_whatsapp or '').strip()

        if self._ja_enviado_hoje(solicitacao, 'WHATSAPP', hoje):
            return True, 'Ignorado: alerta por WhatsApp ja enviado hoje.'

        if not destinatario:
            retorno = 'Falha: WhatsApp do trabalhador nao informado.'
            if not dry_run:
                self._registrar_log(solicitacao, 'WHATSAPP', '-', False, retorno)
            return False, retorno

        twilio_account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
        twilio_auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
        twilio_phone = getattr(settings, 'TWILIO_PHONE_NUMBER', None)

        if not all([twilio_account_sid, twilio_auth_token, twilio_phone]):
            retorno = 'Falha: Twilio nao configurado (TWILIO_ACCOUNT_SID/TWILIO_AUTH_TOKEN/TWILIO_PHONE_NUMBER).'
            if not dry_run:
                self._registrar_log(solicitacao, 'WHATSAPP', destinatario, False, retorno)
            return False, retorno

        numero = destinatario if destinatario.startswith('+') else f'+{destinatario}'
        dias = solicitacao.dias_para_vencimento()
        mensagem = (
            f'Ola, {solicitacao.funcionario.nome_completo}.\n\n'
            f'Alerta de vencimento ASO ({solicitacao.get_tipo_aso_display()}).\n'
            f'Vencimento: {solicitacao.data_vencimento.strftime("%d/%m/%Y")}\n'
            f'Dias restantes: {dias}.\n\n'
            f'{solicitacao.empresa.nome}'
        )

        if dry_run:
            return True, f'DRY-RUN: enviaria WhatsApp para {numero}.'

        try:
            from twilio.rest import Client
        except ImportError:
            retorno = 'Falha: pacote twilio nao instalado (pip install twilio).'
            self._registrar_log(solicitacao, 'WHATSAPP', numero, False, retorno)
            return False, retorno

        try:
            client = Client(twilio_account_sid, twilio_auth_token)
            msg = client.messages.create(
                from_=f'whatsapp:{twilio_phone}',
                body=mensagem,
                to=f'whatsapp:{numero}',
            )
            retorno = f'Alerta enviado por WhatsApp com sucesso (ID: {msg.sid}).'
            self._registrar_log(solicitacao, 'WHATSAPP', numero, True, retorno)
            return True, retorno
        except Exception as exc:
            retorno = f'Erro ao enviar WhatsApp: {exc}'
            self._registrar_log(solicitacao, 'WHATSAPP', numero, False, retorno)
            return False, retorno
