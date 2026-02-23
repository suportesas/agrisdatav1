"""
Views para Autenticação de Dois Fatores (2FA)
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
import json

from .models import DoisFatoresAutenticacao
from .forms_seguranca import Form2FASetup, Form2FAVerificacao, FormAltenarMetodo2FA
from .utils_login import (
    habilitar_2fa, confirmar_2fa, validar_codigo_backup,
    validar_token_totp, gerar_codigos_backup
)


@login_required
def configurar_2fa(request):
    """
    View para configurar 2FA pela primeira vez
    Exibe QR Code e códigos de backup
    """
    usuario = request.user
    
    # Verificar se já tem 2FA
    try:
        auth_2fa = usuario.autenticacao_dois_fatores
        if auth_2fa.ativo:
            messages.info(request, '2FA já está ativo para sua conta')
            return redirect('usuarios:info_seguranca')
    except:
        pass
    
    # Habilitar novo 2FA
    dados_2fa = habilitar_2fa(usuario, metodo='TOTP')
    
    if request.method == 'POST':
        form = Form2FASetup(request.POST)
        if form.is_valid():
            token = form.cleaned_data.get('codigo', '')
            sucesso, mensagem = confirmar_2fa(usuario, token)
            
            if sucesso:
                messages.success(
                    request,
                    '✅ ' + mensagem + '\n\n'
                    '⚠️ Guarde os códigos de backup em um local seguro. '
                    'Você pode usá-los se perder acesso ao autenticador.'
                )
                return redirect('usuarios:listar_codigos_backup')
            else:
                messages.error(request, '❌ ' + mensagem)
    else:
        form = Form2FASetup()
    
    context = {
        'form': form,
        'qrcode_img': dados_2fa['qrcode_img'],
        'chave_secreta': dados_2fa['chave_secreta'],
        'codigos_backup': dados_2fa['codigos_backup'],
        'title': 'Configurar Autenticação de Dois Fatores'
    }
    
    return render(request, 'usuarios/configurar_2fa.html', context)


@login_required
def verificacao_2fa_login(request):
    """
    View para verificar 2FA durante login
    Chamada após autenticação normal bem-sucedida
    """
    usuario = request.user
    
    # Verificar se usuário tem 2FA ativo
    try:
        auth_2fa = usuario.autenticacao_dois_fatores
        if not auth_2fa.ativo:
            # 2FA não ativo, skip
            return redirect('usuariodetail')
    except:
        # Sem 2FA, skip
        return redirect('usuariodetail')
    
    if request.method == 'POST':
        form = Form2FAVerificacao(request.POST, usuario=usuario)
        if form.is_valid():
            codigo = form.cleaned_data['codigo']
            metodo = form.cleaned_data.get('metodo', 'TOTP')
            
            verificado = False
            
            if metodo == 'TOTP':
                verificado = validar_token_totp(auth_2fa.chave_secreta, codigo)
            elif metodo == 'BACKUP':
                verificado = validar_codigo_backup(auth_2fa, codigo)
            
            if verificado:
                # Marcar 2FA como verificado na sessão
                request.session['2fa_verificado'] = True
                auth_2fa.ultimo_uso = timezone.now()
                auth_2fa.save()
                
                messages.success(request, '✅ 2FA verificado com sucesso!')
                return redirect('usuariodetail')
            else:
                messages.error(request, '❌ Código inválido')
    else:
        form = Form2FAVerificacao(usuario=usuario)
    
    context = {
        'form': form,
        'title': 'Verificar Autenticação de Dois Fatores'
    }
    
    return render(request, 'usuarios/verificacao_2fa_login.html', context)


@login_required
def listar_codigos_backup(request):
    """
    Exibe os códigos de backup salvos
    """
    usuario = request.user
    
    try:
        auth_2fa = usuario.autenticacao_dois_fatores
    except:
        messages.error(request, 'Você não tem 2FA configurado')
        return redirect('usuarios:configurar_2fa')
    
    context = {
        'codigos_backup': auth_2fa.codigos_backup,
        'codigos_usados': 10 - len(auth_2fa.codigos_backup),
        'title': 'Códigos de Backup'
    }
    
    return render(request, 'usuarios/listar_codigos_backup.html', context)


@login_required
def desabilitar_2fa(request):
    """
    Desabilita 2FA da conta do usuário
    Requer confirmação
    """
    usuario = request.user
    
    try:
        auth_2fa = usuario.autenticacao_dois_fatores
    except:
        messages.error(request, 'Você não tem 2FA configurado')
        return redirect('usuarios:info_seguranca')
    
    if request.method == 'POST':
        confirmacao = request.POST.get('confirmacao') == 'sim'
        senha_confirmacao = request.POST.get('senha')
        
        if not confirmacao:
            messages.error(request, 'Você deve confirmar a desativação')
            return render(request, 'usuarios/desabilitar_2fa.html')
        
        # Verificar senha
        if not usuario.check_password(senha_confirmacao):
            messages.error(request, 'Senha incorreta')
            return render(request, 'usuarios/desabilitar_2fa.html')
        
        # Desabilitar
        auth_2fa.ativo = False
        auth_2fa.chave_secreta = ''
        auth_2fa.codigos_backup = []
        auth_2fa.save()
        
        messages.success(request, '✅ Autenticação de Dois Fatores desativada')
        return redirect('usuarios:info_seguranca')
    
    return render(request, 'usuarios/desabilitar_2fa.html', {
        'title': 'Desabilitar 2FA'
    })


@login_required
def info_seguranca(request):
    """
    Dashboard com informações de segurança do usuário
    """
    usuario = request.user
    
    # Obter 2FA
    try:
        usuario_2fa = usuario.autenticacao_dois_fatores
    except:
        usuario_2fa = None
    
    # Últimos logins
    from .models import LoginRegistro
    logins_recentes = LoginRegistro.objects.filter(
        usuario=usuario,
        sucesso=True
    ).order_by('-data_login')[:10]
    
    # Anomalias
    from .models import LoginAnomalia
    anomalias_recentes = LoginAnomalia.objects.filter(
        usuario=usuario
    ).order_by('-data_deteccao')[:5]
    
    context = {
        'usuario_2fa': usuario_2fa,
        'logins_recentes': logins_recentes,
        'anomalias_recentes': anomalias_recentes,
        'title': 'Informações de Segurança'
    }
    
    return render(request, 'usuarios/info_seguranca.html', context)


@login_required
def api_verificar_2fa_necessario(request):
    """
    API para verificar se 2FA é necessário
    """
    usuario = request.user
    
    try:
        auth_2fa = usuario.autenticacao_dois_fatores
        necessario = auth_2fa.ativo and not request.session.get('2fa_verificado', False)
    except:
        necessario = False
    
    return JsonResponse({
        'necessario': necessario
    })
