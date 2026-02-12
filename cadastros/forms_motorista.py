"""
Formulários do módulo Motorista
Com validações de CPF, CNH e integração com CEP
"""

from django import forms
from django.core.exceptions import ValidationError
from .models import Motorista, MotoristadoDocumento
import re


class MotoristadoForm(forms.ModelForm):
    """Formulário para cadastro/edição de Motorista"""
    
    buscar_cep = forms.BooleanField(
        required=False,
        initial=False,
        label='Buscar dados via CEP',
        help_text='Preencher automaticamente endereço via ViaCEP'
    )

    class Meta:
        model = Motorista
        fields = [
            'tipo', 'transportadora', 'nome', 'cpf', 'data_nascimento', 'foto',
            'cnh', 'categoria_cnh', 'data_emissao_cnh', 'data_validade_cnh', 'uf_cnh',
            'telefone', 'celular', 'email',
            'cep', 'logradouro', 'numero', 'complemento', 'bairro', 'cidade', 'uf', 'pais',
            'ativo', 'motivo_inativacao'
        ]
        widgets = {
            'tipo': forms.RadioSelect(choices=Motorista.TIPO_CHOICES),
            'transportadora': forms.Select(attrs={'class': 'form-select'}),
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome completo'}),
            'cpf': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '000.000.000-00', 'data-mask': 'cpf'}),
            'data_nascimento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'foto': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'cnh': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número CNH'}),
            'categoria_cnh': forms.Select(attrs={'class': 'form-select'}),
            'data_emissao_cnh': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'data_validade_cnh': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'uf_cnh': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'SP', 'maxlength': '2', 'style': 'text-transform: uppercase;'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(00) 0000-0000'}),
            'celular': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(00) 00000-0000'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@exemplo.com'}),
            'cep': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '00000-000', 'id': 'id_cep'}),
            'logradouro': forms.TextInput(attrs={'class': 'form-control'}),
            'numero': forms.TextInput(attrs={'class': 'form-control'}),
            'complemento': forms.TextInput(attrs={'class': 'form-control'}),
            'bairro': forms.TextInput(attrs={'class': 'form-control'}),
            'cidade': forms.TextInput(attrs={'class': 'form-control'}),
            'uf': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'SP', 'maxlength': '2', 'style': 'text-transform: uppercase;'}),
            'pais': forms.TextInput(attrs={'class': 'form-control'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'motivo_inativacao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        self.empresa = empresa
        
        # Filtrar transportadoras por empresa
        if empresa:
            self.fields['transportadora'].queryset = self.fields['transportadora'].queryset.filter(empresa=empresa)
        
        # Transportadora obrigatória apenas se tipo for terceirizado
        self.fields['transportadora'].required = False
        
        # Campos opcionais
        optional_fields = ['transportadora', 'data_nascimento', 'data_emissao_cnh', 'uf_cnh', 
                          'telefone', 'email', 'complemento', 'motivo_inativacao']
        for field in optional_fields:
            if field in self.fields:
                self.fields[field].required = False

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo')
        transportadora = cleaned_data.get('transportadora')
        cnh = cleaned_data.get('cnh')
        data_validade_cnh = cleaned_data.get('data_validade_cnh')
        
        # Validar se motorista terceirizado ou agregado tem transportadora
        if tipo in ['TERCEIRO', 'AGREGADO'] and not transportadora:
            raise ValidationError({
                'transportadora': f'Transportadora é obrigatória para motoristas {dict(self.fields["tipo"].widget.choices).get(tipo, "")}.lower().'
            })
        
        # Validar se motorista próprio ou agregado tem CNH
        if tipo in ['PROPRIO', 'AGREGADO']:
            if not cnh:
                raise ValidationError({
                    'cnh': f'CNH é obrigatória para motoristas {dict(self.fields["tipo"].widget.choices).get(tipo, "").lower()}.'
                })
            if not data_validade_cnh:
                raise ValidationError({
                    'data_validade_cnh': 'Data de validade da CNH é obrigatória.'
                })
        
        return cleaned_data

    def clean_cpf(self):
        """Valida formato do CPF"""
        cpf = self.cleaned_data.get('cpf')
        if cpf:
            # Remove caracteres especiais
            cpf_limpo = re.sub(r'\D', '', cpf)
            
            if len(cpf_limpo) != 11:
                raise ValidationError('CPF deve ter 11 dígitos.')
            
            # Valida CPF (algoritmo módulo 11)
            if not self._validar_cpf(cpf_limpo):
                raise ValidationError('CPF inválido.')
        
        return cpf

    def clean_cnh(self):
        """Valida CNH"""
        cnh = self.cleaned_data.get('cnh')
        if cnh:
            cnh_limpo = re.sub(r'\D', '', cnh)
            if len(cnh_limpo) != 12:
                raise ValidationError('CNH deve ter 12 dígitos.')
        
        return cnh

    @staticmethod
    def _validar_cpf(cpf):
        """Valida CPF usando algoritmo módulo 11"""
        if cpf == cpf[0] * 11:  # CPF com todos dígitos iguais
            return False
        
        # Validar primeiro dígito verificador
        soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
        resto = soma % 11
        dv1 = 0 if resto < 2 else 11 - resto
        
        if int(cpf[9]) != dv1:
            return False
        
        # Validar segundo dígito verificador
        soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
        resto = soma % 11
        dv2 = 0 if resto < 2 else 11 - resto
        
        return int(cpf[10]) == dv2

    def save(self, commit=True):
        obj = super().save(commit=False)
        if self.empresa:
            obj.empresa = self.empresa
        if commit:
            obj.save()
        return obj


class MotoristadoDocumentoForm(forms.ModelForm):
    """Formulário para cadastro de documentos do motorista"""

    class Meta:
        model = MotoristadoDocumento
        fields = ['tipo', 'numero', 'data_emissao', 'data_validade', 'arquivo', 'observacoes']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'numero': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número do documento'}),
            'data_emissao': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'data_validade': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'arquivo': forms.FileInput(attrs={'class': 'form-control'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Campos opcionais
        optional_fields = ['numero', 'data_emissao', 'data_validade', 'arquivo', 'observacoes']
        for field in optional_fields:
            if field in self.fields:
                self.fields[field].required = False
