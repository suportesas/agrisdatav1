"""
Formulários para Grupo Corporativo
Gestão de holdings e grupos de empresas (Enterprise Plus)
"""

from django import forms
from django.contrib.auth import get_user_model
from .models import GrupoCorporativo, Empresa

User = get_user_model()


class GrupoCorporativoForm(forms.ModelForm):
    """Formulário para criar/editar Grupo Corporativo"""
    
    class Meta:
        model = GrupoCorporativo
        fields = ['nome', 'cnpj', 'descricao', 'email', 'telefone', 'logo', 'status', 'administrador']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Holding ABC',
                'required': True
            }),
            'cnpj': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '00.000.000/0000-00',
                'data-mask': 'cnpj'
            }),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descrição do grupo corporativo'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'suport@grupo.com.br'
            }),
            'telefone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '(00) 0000-0000'
            }),
            'logo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'administrador': forms.Select(attrs={
                'class': 'form-select'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show admin users in the administrador dropdown
        self.fields['administrador'].queryset = User.objects.filter(
            is_staff=True
        ).order_by('first_name', 'last_name')
        self.fields['administrador'].required = False


class EmpresaGrupoForm(forms.ModelForm):
    """Formulário para vincular Empresa a um Grupo Corporativo"""
    
    class Meta:
        model = Empresa
        fields = ['grupo_corporativo']
        widgets = {
            'grupo_corporativo': forms.Select(attrs={
                'class': 'form-select'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)
        self.fields['grupo_corporativo'].required = False
        self.fields['grupo_corporativo'].label = 'Grupo Corporativo'
        self.fields['grupo_corporativo'].help_text = 'Selecione um grupo para associar esta empresa'
        
        # Filter grupos to only active ones
        if self.usuario:
            # Admins can see all grupos; others only see those they manage
            if self.usuario.is_superuser or self.usuario.is_staff:
                self.fields['grupo_corporativo'].queryset = GrupoCorporativo.objects.filter(
                    status='ATIVO'
                )
            else:
                self.fields['grupo_corporativo'].queryset = GrupoCorporativo.objects.filter(
                    status='ATIVO',
                    administrador=self.usuario
                )


class AdicionarEmpresasAoGrupoForm(forms.Form):
    """Formulário para adicionar múltiplas empresas a um grupo"""
    
    empresas = forms.ModelMultipleChoiceField(
        queryset=Empresa.objects.filter(ativa=True, grupo_corporativo__isnull=True),
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        label='Empresas para adicionar',
        help_text='Selecione as empresas que deseja adicionar ao grupo'
    )
    
    def __init__(self, *args, grupo_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Don't show empresas that already belong to other groups
        self.fields['empresas'].queryset = Empresa.objects.filter(
            ativa=True,
            grupo_corporativo__isnull=True
        ).order_by('nome')
