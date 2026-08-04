"""
Utilitários para segurança e auditoria de login
Detecta anomalias, envia alertas e gerencia 2FA
"""

from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
import pyotp
import qrcode
from io import BytesIO
import base64

from .models import (
    LoginRegistro, LoginAnomalia, AlertaSeguranca,
    DoisFatoresAutenticacao, GraficoAcesso,
    get_codigos_tipos_admin_empresa,
)


# ============================================
# DETECÇÃO DE ANOMALIAS
# ============================================

def detectar_anomalias_login(usuario, empresa, ip_address, user_agent):
    """
    Detecta anomalias no padrão de login do usuário
    Cria registros de LoginAnomalia quando algo suspeito é detectado
    """
    anomalias = []
    
    # 1. Detectar IP novo
    ip_novo = detectar_ip_novo(usuario, ip_address)
    if ip_novo:
        anomalia = LoginAnomalia.objects.create(
            usuario=usuario,
            tipo='IP_NOVO',
            ip_address=ip_address,
            user_agent=user_agent,
            descricao=f"IP novo detectado: {ip_address}"
        )
        anomalias.append(anomalia)
    
    # 2. Detectar navegador novo
    navegador_novo = detectar_navegador_novo(usuario, user_agent)
    if navegador_novo:
        anomalia = LoginAnomalia.objects.create(
            usuario=usuario,
            tipo='NAVEGADOR_NOVO',
            ip_address=ip_address,
            user_agent=user_agent,
            descricao=f"Navegador novo detectado: {extrair_navegador(user_agent)}"
        )
        anomalias.append(anomalia)
    
    # 3. Detectar tentativa de força bruta
    forca_bruta = detectar_forca_bruta(usuario, ip_address)
    if forca_bruta:
        anomalia = LoginAnomalia.objects.create(
            usuario=usuario,
            tipo='FORCA_BRUTA',
            ip_address=ip_address,
            user_agent=user_agent,
            descricao=f"Múltiplas tentativas de login falhadas no IP {ip_address}"
        )
        anomalias.append(anomalia)
    
    # 4. Detectar múltiplos IPs em curto tempo
    multiplos_ips = detectar_multiplos_ips(usuario)
    if multiplos_ips:
        anomalia = LoginAnomalia.objects.create(
            usuario=usuario,
            tipo='MULTIPLOS_IPS',
            ip_address=ip_address,
            user_agent=user_agent,
            descricao=f"Multiple IPs detectados em curto espaço de tempo"
        )
        anomalias.append(anomalia)
    
    return anomalias


def detectar_ip_novo(usuario, ip_address):
    """Verifica se o IP já foi usado pelo usuário nos últimos 30 dias"""
    if not ip_address or ip_address == 'Unknown':
        return False
    
    # Verificar se IP existe nos últimos 30 dias
    data_limite = timezone.now() - timedelta(days=30)
    existe = LoginRegistro.objects.filter(
        usuario=usuario,
        ip_address=ip_address,
        data_login__gte=data_limite,
        sucesso=True
    ).exists()
    
    return not existe


def detectar_navegador_novo(usuario, user_agent):
    """Verifica se o navegador já foi usado pelo usuário nos últimos 30 dias"""
    if not user_agent:
        return False
    
    navegador_atual = extrair_navegador(user_agent)
    data_limite = timezone.now() - timedelta(days=30)
    
    logins_anteriores = LoginRegistro.objects.filter(
        usuario=usuario,
        data_login__gte=data_limite,
        sucesso=True
    )
    
    for login in logins_anteriores:
        if extrair_navegador(login.user_agent) == navegador_atual:
            return False
    
    return True


def extrair_navegador(user_agent):
    """Extrai nome do navegador do user agent"""
    if not user_agent:
        return "Desconhecido"
    
    ua = user_agent.lower()
    if 'firefox' in ua:
        return 'Firefox'
    elif 'chrome' in ua and 'edg' not in ua:
        return 'Chrome'
    elif 'safari' in ua and 'chrome' not in ua:
        return 'Safari'
    elif 'edg' in ua:
        return 'Edge'
    elif 'opera' in ua or 'opr' in ua:
        return 'Opera'
    return 'Outro'


def detectar_forca_bruta(usuario, ip_address):
    """
    Detecta tentativas de força bruta
    5+ tentativas falhadas no mesmo IP em 10 minutos
    """
    if not ip_address:
        return False
    
    # Verificar tentativas nos últimos 10 minutos
    data_limite = timezone.now() - timedelta(minutes=10)
    
    tentativas_falhas = LoginRegistro.objects.filter(
        usuario=usuario,
        ip_address=ip_address,
        sucesso=False,
        data_login__gte=data_limite
    ).count()
    
    return tentativas_falhas >= 5


def detectar_multiplos_ips(usuario):
    """
    Detecta múltiplos IPs em 1 hora
    Indicativo de acesso simultâneo de múltiplos locais (suspeito)
    """
    data_limite = timezone.now() - timedelta(hours=1)
    
    ips_unicos = LoginRegistro.objects.filter(
        usuario=usuario,
        data_login__gte=data_limite,
        sucesso=True
    ).values_list('ip_address', flat=True).distinct()
    
    return len(ips_unicos) > 2  # Mais de 2 IPs em 1 hora é suspeito


# ============================================
# ALERTAS E NOTIFICAÇÕES
# ============================================

def criar_alerta(usuario, empresa, titulo, descricao, nivel='MEDIO', dados_adicionais=None):
    """
    Cria alerta de segurança e envia email
    """
    alerta = AlertaSeguranca.objects.create(
        usuario=usuario,
        empresa=empresa,
        titulo=titulo,
        descricao=descricao,
        nivel=nivel,
        dados_adicionais=dados_adicionais or {}
    )
    
    # Enviar email aos admins
    enviar_email_alerta(alerta)
    
    return alerta


def enviar_email_alerta(alerta):
    """
    Envia email sobre alerta de segurança
    Para proprietários e admins da empresa
    """
    try:
        # Buscar destinatários
        admins = alerta.empresa.usuarios.filter(tipo__in=get_codigos_tipos_admin_empresa(), is_active=True)
        superusers = alerta.empresa.usuarios.filter(is_superuser=True)
        
        destinatarios = list(set(
            list(admins.values_list('email', flat=True)) +
            list(superusers.values_list('email', flat=True))
        ))
        
        if not destinatarios:
            return False
        
        # Preparar contexto do email
        contexto = {
            'alerta': alerta,
            'nivel_classe': f'alerta-{alerta.get_nivel_display().lower()}',
            'url_admin': f"{settings.SITE_URL}/admin/"
        }
        
        # Renderizar template
        html_message = render_to_string('emails/alerta_seguranca.html', contexto)
        
        # Enviar email
        send_mail(
            subject=f"🚨 [{alerta.get_nivel_display()}] {alerta.titulo}",
            message=alerta.descricao,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=destinatarios,
            html_message=html_message,
            fail_silently=True
        )
        
        # Marcar como enviado
        alerta.enviado_email = True
        alerta.save()
        
        return True
    except Exception as e:
        print(f"Erro ao enviar email de alerta: {e}")
        return False


def notificar_anomalia(anomalia):
    """
    Notifica proprietário sobre anomalia detectada
    """
    criar_alerta(
        usuario=anomalia.usuario,
        empresa=anomalia.usuario.empresa,
        titulo=f"Atividade Suspeita - {anomalia.get_tipo_display()}",
        descricao=anomalia.descricao,
        nivel='ALTO',
        dados_adicionais={
            'tipo_anomalia': anomalia.tipo,
            'ip_address': anomalia.ip_address,
            'user_agent': anomalia.user_agent
        }
    )


# ============================================
# AUTENTICAÇÃO DE DOIS FATORES (2FA)
# ============================================

def gerar_chave_totp():
    """Gera uma chave secreta TOTP nova"""
    return pyotp.random_base32()


def criar_qrcode_totp(usuario, chave_secreta):
    """
    Cria QR Code para TOTP
    Usuário escaneia com Google Authenticator, Authy, etc
    """
    totp = pyotp.TOTP(chave_secreta)
    
    # Provisioning URI é o padrão para gerar QR codes
    provisioning_uri = totp.provisioning_uri(
        name=usuario.email,
        issuer_name='Agrisdata'
    )
    
    # Gerar QR Code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Converter para base64 para exibição em HTML
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    return img_str, provisioning_uri


def validar_token_totp(chave_secreta, token):
    """Valida um token TOTP"""
    try:
        totp = pyotp.TOTP(chave_secreta)
        # Permite ±1 window (30 segundos antes e depois)
        return totp.verify(token, valid_window=1)
    except:
        return False


def gerar_codigos_backup():
    """Gera 10 códigos de backup para emergências"""
    import secrets
    codigos = []
    for _ in range(10):
        codigo = secrets.token_hex(4).upper()
        codigos.append(codigo)
    return codigos


def validar_codigo_backup(usuario_2fa, codigo):
    """Valida um código de backup e o remove da lista"""
    if codigo in usuario_2fa.codigos_backup:
        usuario_2fa.codigos_backup.remove(codigo)
        usuario_2fa.save()
        return True
    return False


def habilitar_2fa(usuario, metodo='TOTP'):
    """
    Cria registro 2FA para usuário
    Retorna chave_secreta e QR code para exibição
    """
    chave_secreta = gerar_chave_totp()
    
    # Criar registro (ainda não ativo)
    auth_2fa, created = DoisFatoresAutenticacao.objects.get_or_create(
        usuario=usuario,
        defaults={
            'chave_secreta': chave_secreta,
            'metodo_primario': metodo,
            'codigos_backup': gerar_codigos_backup()
        }
    )
    
    if not created:
        # Atualizar se já existe
        auth_2fa.chave_secreta = chave_secreta
        auth_2fa.metodo_primario = metodo
        auth_2fa.codigos_backup = gerar_codigos_backup()
        auth_2fa.save()
    
    # Gerar QR Code
    qrcode_img, provisioning_uri = criar_qrcode_totp(usuario, chave_secreta)
    
    return {
        'chave_secreta': chave_secreta,
        'qrcode_img': qrcode_img,
        'provisioning_uri': provisioning_uri,
        'codigos_backup': auth_2fa.codigos_backup,
        'auth_2fa': auth_2fa
    }


def confirmar_2fa(usuario, token_totp):
    """
    Confirma 2FA validando um token
    Ativa o 2FA após confirmação
    """
    try:
        auth_2fa = usuario.autenticacao_dois_fatores
    except:
        return False, "2FA não foi configurado"
    
    if validar_token_totp(auth_2fa.chave_secreta, token_totp):
        auth_2fa.ativo = True
        auth_2fa.data_habilitacao = timezone.now()
        auth_2fa.save()
        
        # Criar alerta
        criar_alerta(
            usuario=usuario,
            empresa=usuario.empresa,
            titulo="Autenticação de Dois Fatores Ativada",
            descricao=f"2FA foi ativado para a conta {usuario.username}",
            nivel='MEDIO'
        )
        
        return True, "2FA ativado com sucesso!"
    
    return False, "Código inválido. Tente novamente."


# ============================================
# GRÁFICOS E ESTATÍSTICAS
# ============================================

def atualizar_grafico_acesso(empresa, data=None):
    """
    Atualiza dados agregados de acesso diário
    Executar diariamente via Celery/Cron
    """
    if data is None:
        data = timezone.now().date()
    
    # Query de logins do dia
    logins = LoginRegistro.objects.filter(
        empresa=empresa,
        data_login__date=data
    )
    
    # Calcular estatísticas
    total = logins.count()
    sucesso = logins.filter(sucesso=True).count()
    falha = logins.filter(sucesso=False).count()
    usuarios_unicos = logins.values('usuario').distinct().count()
    ips_unicos = logins.values('ip_address').distinct().count()
    
    # Contar anomalias
    anomalias = LoginAnomalia.objects.filter(
        usuario__empresa=empresa,
        data_deteccao__date=data
    ).count()
    
    # Criar ou atualizar gráfico
    grafico, created = GraficoAcesso.objects.update_or_create(
        empresa=empresa,
        data=data,
        defaults={
            'total_logins': total,
            'logins_sucesso': sucesso,
            'logins_falha': falha,
            'usuarios_unicos': usuarios_unicos,
            'ips_unicos': ips_unicos,
            'anomalias_detectadas': anomalias
        }
    )
    
    return grafico


def obter_estatisticas_acesso(empresa, dias=30):
    """
    Obtém estatísticas agregadas dos últimos N dias
    Para exibir em dashboard/gráficos
    """
    data_inicio = timezone.now().date() - timedelta(days=dias)
    
    graficos = GraficoAcesso.objects.filter(
        empresa=empresa,
        data__gte=data_inicio
    ).order_by('data')
    
    # Agregar dados
    totais = {
        'total_logins': sum(g.total_logins for g in graficos),
        'logins_sucesso': sum(g.logins_sucesso for g in graficos),
        'logins_falha': sum(g.logins_falha for g in graficos),
        'usuarios_unicos': len(set(g.usuarios_unicos for g in graficos)),
        'ips_unicos': len(set(g.ips_unicos for g in graficos)),
        'anomalias_detectadas': sum(g.anomalias_detectadas for g in graficos),
    }
    
    # Calcular taxa de sucesso
    if totais['total_logins'] > 0:
        totais['taxa_sucesso'] = round(
            (totais['logins_sucesso'] / totais['total_logins']) * 100, 2
        )
    else:
        totais['taxa_sucesso'] = 0
    
    return {
        'graficos': graficos,
        'totais': totais,
        'dados_para_json': list(graficos.values(
            'data', 'total_logins', 'logins_sucesso', 'logins_falha',
            'usuarios_unicos', 'ips_unicos', 'anomalias_detectadas'
        ))
    }


def get_client_ip(request):
    """Obtém IP do cliente da requisição"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR', 'Unknown')
    return ip


def get_user_agent(request):
    """Obtém user agent da requisição"""
    return request.META.get('HTTP_USER_AGENT', '')


# ============================================
# PÁGINA INICIAL PÓS-LOGIN
# ============================================

def resolver_pagina_inicial(request):
    """
    Resolve a tela de pouso pós-login: primeiro a `pagina_inicial` do próprio
    usuário, depois a da sua Função (a primeira, em ordem alfabética, que tiver
    uma definida). Ignora silenciosamente páginas inativas ou às quais o
    usuário não tem mais acesso, caindo para o próximo candidato.
    Retorna None se nenhum candidato aplicável (chamador cai no dashboard).
    """
    from django.urls import reverse, NoReverseMatch
    from empresas.acesso import usuario_tem_acesso

    user = request.user
    candidatos = []
    if user.pagina_inicial_id and user.pagina_inicial.ativo:
        candidatos.append(user.pagina_inicial)

    role_padrao = user.roles.filter(
        pagina_inicial__isnull=False, pagina_inicial__ativo=True
    ).order_by('name').first()
    if role_padrao:
        candidatos.append(role_padrao.pagina_inicial)

    for programa in candidatos:
        if not usuario_tem_acesso(request, programa.url_name):
            continue
        try:
            return reverse(programa.url_name)
        except NoReverseMatch:
            continue
    return None
