import re

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.urls import reverse
from django.utils import timezone

from .models import EmprestimoInteracao, EmprestimoMensagem, EmprestimoMensagemAnexo


def usuario_pode_interagir_emprestimo(usuario, emprestimo):
    if not usuario or not getattr(usuario, 'empresa', None):
        return False
    if usuario.empresa_id != emprestimo.empresa_id:
        return False
    if usuario.tipo in ['ADMIN', 'GERENTE']:
        return True
    return emprestimo.liberado_por_id == usuario.id


def registrar_interacao_emprestimo(emprestimo, tipo_interacao, descricao, usuario=None, destinatario='', sucesso=True):
    return EmprestimoInteracao.objects.create(
        empresa=emprestimo.empresa,
        emprestimo=emprestimo,
        tipo_interacao=tipo_interacao,
        usuario=usuario,
        descricao=descricao,
        destinatario=destinatario,
        sucesso=sucesso,
    )


def marcar_mensagens_emprestimo_como_lidas(emprestimo, perfil_leitor):
    if perfil_leitor == 'INTERNO':
        return emprestimo.mensagens.filter(
            perfil_autor='PRODUTOR',
            lido_interno_em__isnull=True,
        ).update(lido_interno_em=timezone.now())
    if perfil_leitor == 'PRODUTOR':
        return emprestimo.mensagens.filter(
            perfil_autor='INTERNO',
            lido_produtor_em__isnull=True,
        ).update(lido_produtor_em=timezone.now())
    return 0


def notificar_internos_mensagem_produtor(emprestimo, autor, texto_mensagem):
    destinatarios = set()

    if emprestimo.liberado_por and emprestimo.liberado_por.email:
        destinatarios.add(emprestimo.liberado_por.email)

    user_model = get_user_model()
    usuarios_internos = user_model.objects.filter(
        empresa=emprestimo.empresa,
        tipo__in=['ADMIN', 'GERENTE'],
        is_active=True,
    ).exclude(email='').exclude(email__isnull=True)
    destinatarios.update(usuarios_internos.values_list('email', flat=True))

    if not destinatarios:
        registrar_interacao_emprestimo(
            emprestimo,
            'NOTIFICACAO_INTERNA',
            'Mensagem do produtor registrada, mas não há e-mails internos configurados para notificação.',
            usuario=autor,
            sucesso=False,
        )
        return False

    link_interno = reverse('emprestimos:emprestimo_detalhe', args=[emprestimo.pk])
    remetente = autor.get_full_name() or autor.username
    texto_resumido = (texto_mensagem or '').strip()
    if len(texto_resumido) > 300:
        texto_resumido = texto_resumido[:297] + '...'

    try:
        send_mail(
            subject=f'[Empréstimo] Nova mensagem do produtor - requisição {emprestimo.requisicao.numero if emprestimo.requisicao_id else emprestimo.pk}',
            message=(
                f'Produtor: {emprestimo.produtor.razao_social}\n'
                f'Produto: {emprestimo.produto.nome}\n'
                f'Remetente: {remetente}\n\n'
                f'Mensagem:\n{texto_resumido or "Mensagem com anexo."}\n\n'
                f'Acesse o ERP para responder: {link_interno}'
            ),
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
            recipient_list=sorted(destinatarios),
            fail_silently=True,
        )
        registrar_interacao_emprestimo(
            emprestimo,
            'NOTIFICACAO_INTERNA',
            f'Notificação interna enviada após mensagem do produtor para {len(destinatarios)} destinatário(s).',
            usuario=autor,
            destinatario=', '.join(sorted(destinatarios)[:5]),
            sucesso=True,
        )
        return True
    except Exception as exc:
        registrar_interacao_emprestimo(
            emprestimo,
            'NOTIFICACAO_INTERNA',
            f'Falha ao notificar equipe interna após mensagem do produtor: {exc}',
            usuario=autor,
            sucesso=False,
        )
        return False


def criar_mensagem_emprestimo(emprestimo, autor, perfil_autor, texto_mensagem, arquivos=None):
    mensagem = EmprestimoMensagem.objects.create(
        empresa=emprestimo.empresa,
        emprestimo=emprestimo,
        autor=autor,
        perfil_autor=perfil_autor,
        mensagem=texto_mensagem,
        lido_interno_em=timezone.now() if perfil_autor == 'INTERNO' else None,
        lido_produtor_em=timezone.now() if perfil_autor == 'PRODUTOR' else None,
    )

    anexos = []
    for arquivo in arquivos or []:
        anexos.append(
            EmprestimoMensagemAnexo.objects.create(
                mensagem=mensagem,
                arquivo=arquivo,
                nome_original=getattr(arquivo, 'name', ''),
            )
        )

    tipo_interacao = 'MENSAGEM_PRODUTOR' if perfil_autor == 'PRODUTOR' else 'MENSAGEM_INTERNA'
    registrar_interacao_emprestimo(
        emprestimo,
        tipo_interacao,
        f'Mensagem registrada por {autor.get_full_name() or autor.username}.',
        usuario=autor,
        sucesso=True,
    )
    if perfil_autor == 'PRODUTOR':
        notificar_internos_mensagem_produtor(emprestimo, autor, texto_mensagem)
    return mensagem, anexos


def enviar_whatsapp_emprestimo(request, emprestimo):
    produtor = emprestimo.produtor
    if not produtor.portal_enabled or not produtor.portal_user_id:
        msg = 'Portal do produtor não está habilitado; o link interno não pode ser enviado por WhatsApp.'
        registrar_interacao_emprestimo(emprestimo, 'WHATSAPP_FALHA', msg, usuario=request.user, sucesso=False)
        return False, msg

    destinatario = (produtor.telefone or '').strip()
    if not destinatario:
        msg = 'Produtor sem telefone cadastrado para envio do WhatsApp.'
        registrar_interacao_emprestimo(emprestimo, 'WHATSAPP_FALHA', msg, usuario=request.user, sucesso=False)
        return False, msg

    numero_whatsapp = re.sub(r'\D', '', destinatario)
    if len(numero_whatsapp) < 10:
        msg = 'Telefone do produtor inválido para envio do WhatsApp.'
        registrar_interacao_emprestimo(emprestimo, 'WHATSAPP_FALHA', msg, usuario=request.user, destinatario=destinatario, sucesso=False)
        return False, msg

    if not numero_whatsapp.startswith('55'):
        numero_whatsapp = '55' + numero_whatsapp
    numero_whatsapp = '+' + numero_whatsapp

    twilio_account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
    twilio_auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
    twilio_phone = getattr(settings, 'TWILIO_PHONE_NUMBER', None)
    if not all([twilio_account_sid, twilio_auth_token, twilio_phone]):
        msg = 'Twilio não está configurado para o envio do WhatsApp.'
        registrar_interacao_emprestimo(emprestimo, 'WHATSAPP_FALHA', msg, usuario=request.user, destinatario=numero_whatsapp, sucesso=False)
        return False, msg

    try:
        from twilio.rest import Client
    except ImportError:
        msg = 'Twilio não está instalado no ambiente.'
        registrar_interacao_emprestimo(emprestimo, 'WHATSAPP_FALHA', msg, usuario=request.user, destinatario=numero_whatsapp, sucesso=False)
        return False, msg

    portal_url = request.build_absolute_uri(reverse('portal_produtor:emprestimo_detail', args=[emprestimo.pk]))
    nome_produtor = produtor.nome_fantasia or produtor.razao_social
    mensagem = (
        f'Olá, {nome_produtor}!\n\n'
        f'Seu empréstimo de material foi registrado no ERP.\n'
        f'Requisição: {emprestimo.requisicao.numero if emprestimo.requisicao_id else emprestimo.pk}\n'
        f'Produto: {emprestimo.produto.nome}\n'
        f'Quantidade: {emprestimo.quantidade_emprestada:.3f} {emprestimo.unidade_medida.sigla}\n'
        f'Recebedor informado: {(emprestimo.requisicao.recebedor_material if emprestimo.requisicao_id else "-") or "-"}\n\n'
        f'Acesse o portal para acompanhar e assinar: {portal_url}\n\n'
        f'{emprestimo.empresa.nome}'
    )

    try:
        client = Client(twilio_account_sid, twilio_auth_token)
        response = client.messages.create(
            from_=f'whatsapp:{twilio_phone}',
            body=mensagem,
            to=f'whatsapp:{numero_whatsapp}',
        )
        retorno = f'WhatsApp enviado com sucesso (ID: {response.sid})'
        registrar_interacao_emprestimo(emprestimo, 'WHATSAPP_SUCESSO', retorno, usuario=request.user, destinatario=numero_whatsapp, sucesso=True)
        return True, retorno
    except Exception as exc:
        retorno = f'Erro ao enviar WhatsApp: {exc}'
        registrar_interacao_emprestimo(emprestimo, 'WHATSAPP_FALHA', retorno, usuario=request.user, destinatario=numero_whatsapp, sucesso=False)
        return False, retorno
