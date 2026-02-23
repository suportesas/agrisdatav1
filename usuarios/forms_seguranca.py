"""
Forms para 2FA e Segurança
"""

from django import forms
from .models import DoisFatoresAutenticacao


class Form2FASetup(forms.Form):
    """
    Form para confirmar 2FA durante configuração
    """
    codigo = forms.CharField(
        label='Código de Verificação',
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg text-center',
            'placeholder': '000000',
            'autocomplete': 'off',
            'inputmode': 'numeric',
            'pattern': '[0-9]{6}',
            'maxlength': '6',
            'required': True
        }),
        help_text='Digite os 6 dígitos do seu aplicador de autenticação'
    )
    
    class Meta:
        fields = ['codigo']


class Form2FAVerificacao(forms.Form):
    """
    Form para verificar 2FA durante login
    """
    CHOICE_METODOS = (
        ('TOTP', 'Código do Autenticador'),
        ('BACKUP', 'Código de Backup'),
    )
    
    metodo = forms.ChoiceField(
        label='Método de Verificação',
        choices=CHOICE_METODOS,
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input'
        })
    )
    
    codigo = forms.CharField(
        label='Código de Verificação',
        max_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg text-center',
            'placeholder': '000000',
            'autocomplete': 'off',
            'inputmode': 'numeric'
        }),
        help_text='Digite o código de 6 dígitos'
    )
    
    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario
        
        # Se não houver códigos de backup, remover opção
        if usuario:
            try:
                auth_2fa = usuario.autenticacao_dois_fatores
                if not auth_2fa.codigos_backup:
                    self.fields['metodo'].choices = [self.CHOICE_METODOS[0]]
            except:
                pass


class FormAltenarMetodo2FA(forms.Form):
    """
    Form para alternar método de 2FA
    """
    METODOS = (
        ('TOTP', 'Autenticador (Google Authenticator, Authy, Microsoft Authenticator)'),
        ('SMS', 'SMS (texto)'),
        ('EMAIL', 'E-mail'),
    )
    
    metodo = forms.ChoiceField(
        label='Novo Método',
        choices=METODOS,
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input'
        })
    )
    
    telefone_novo = forms.CharField(
        label='Telefone (para SMS)',
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+55 84 99999-9999'
        })
    )
