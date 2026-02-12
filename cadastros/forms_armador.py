"""
Formulários do módulo Armador, Navio
Com validações e integração com APIs externas (CNPJ, CEP)
"""

from django import forms
from django.core.exceptions import ValidationError
from .models import (
    Armador, ArmadorEndereco, ArmadorContato, ArmadorDadoBancario,
    Navio
)


class ArmadorForm(forms.ModelForm):
    """Formulário de Armador com suporte a CNPJ e CEP via API"""

    buscar_cnpj = forms.BooleanField(
        required=False,
        initial=False,
        label='Buscar dados via CNPJ',
        help_text='Preencher automaticamente nome via ReceitaWS'
    )

    buscar_cep = forms.BooleanField(
        required=False,
        initial=False,
        label='Buscar dados via CEP',
        help_text='Preencher automaticamente endereço via ViaCEP'
    )

    class Meta:
        model = Armador
        fields = [
            'codigo', 'nome', 'nome_fantasia', 'cnpj', 'pais', 'website',
            'cep', 'endereco', 'numero', 'complemento', 'bairro', 'cidade', 'uf',
            'email', 'telefone', 'celular',
            'tipos_navio',
            'confiabilidade_percentual', 'percentual_rolagem_historico', 'custo_medio_rolagem',
            'ativo'
        ]
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'form-control'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'nome_fantasia': forms.TextInput(attrs={'class': 'form-control'}),
            'cnpj': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '00.000.000/0000-00'}),
            'pais': forms.TextInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://www.armador.com'}),
            'cep': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '00000-000'}),
            'endereco': forms.TextInput(attrs={'class': 'form-control'}),
            'numero': forms.TextInput(attrs={'class': 'form-control'}),
            'complemento': forms.TextInput(attrs={'class': 'form-control'}),
            'bairro': forms.TextInput(attrs={'class': 'form-control'}),
            'cidade': forms.TextInput(attrs={'class': 'form-control'}),
            'uf': forms.Select(attrs={'class': 'form-select'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(00) 0000-0000'}),
            'celular': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(00) 00000-0000'}),
            'tipos_navio': forms.CheckboxSelectMultiple(),
            'confiabilidade_percentual': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100, 'step': 0.01}),
            'percentual_rolagem_historico': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': 0.01}),
            'custo_medio_rolagem': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': 0.01}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        usuario = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)
        self.empresa = empresa
        self.usuario = usuario
        # Campos opcionais
        for f in ['nome_fantasia', 'cnpj', 'website', 'complemento', 'custo_medio_rolagem']:
            if f in self.fields:
                self.fields[f].required = False

    def save(self, commit=True):
        obj = super().save(commit=False)
        if getattr(self, 'empresa', None):
            obj.empresa = self.empresa
        if getattr(self, 'usuario', None):
            if hasattr(obj, 'criado_por'):
                obj.criado_por = self.usuario
        if commit:
            obj.save()
            self.save_m2m()  # Salvar ManyToMany fields (tipos_navio)
        return obj


class ArmadorEnderecoForm(forms.ModelForm):
    """Formulário para endereço de Armador"""

    class Meta:
        model = ArmadorEndereco
        fields = ['tipo', 'cep', 'logradouro', 'numero', 'complemento', 'bairro', 'cidade', 'uf', 'pais', 'padrao']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'cep': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '00000-000'}),
            'logradouro': forms.TextInput(attrs={'class': 'form-control'}),
            'numero': forms.TextInput(attrs={'class': 'form-control'}),
            'complemento': forms.TextInput(attrs={'class': 'form-control'}),
            'bairro': forms.TextInput(attrs={'class': 'form-control'}),
            'cidade': forms.TextInput(attrs={'class': 'form-control'}),
            'uf': forms.Select(attrs={'class': 'form-select'}),
            'pais': forms.TextInput(attrs={'class': 'form-control'}),
            'padrao': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ArmadorContatoForm(forms.ModelForm):
    """Formulário para contato de Armador"""

    class Meta:
        model = ArmadorContato
        fields = ['tipo', 'nome', 'cargo', 'telefone', 'celular', 'email', 'whatsapp', 'preferencial', 'observacoes']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'cargo': forms.TextInput(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(00) 0000-0000'}),
            'celular': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(00) 00000-0000'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'whatsapp': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'preferencial': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class ArmadorDadoBancarioForm(forms.ModelForm):
    """Formulário para dados bancários de Armador"""

    class Meta:
        model = ArmadorDadoBancario
        fields = [
            'codigo_banco', 'nome_banco', 'agencia', 'agencia_dv', 'conta', 'conta_dv', 'tipo_conta',
            'tem_pix', 'tipo_pix', 'chave_pix',
            'nome_titular', 'cpf_cnpj_titular',
            'padrao', 'ativo'
        ]
        widgets = {
            'codigo_banco': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 001'}),
            'nome_banco': forms.TextInput(attrs={'class': 'form-control'}),
            'agencia': forms.TextInput(attrs={'class': 'form-control'}),
            'agencia_dv': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '2'}),
            'conta': forms.TextInput(attrs={'class': 'form-control'}),
            'conta_dv': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '2'}),
            'tipo_conta': forms.Select(attrs={'class': 'form-select'}),
            'tem_pix': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tipo_pix': forms.Select(attrs={'class': 'form-select'}),
            'chave_pix': forms.TextInput(attrs={'class': 'form-control'}),
            'nome_titular': forms.TextInput(attrs={'class': 'form-control'}),
            'cpf_cnpj_titular': forms.TextInput(attrs={'class': 'form-control'}),
            'padrao': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class NavioForm(forms.ModelForm):
    """Formulário para Navio"""

    class Meta:
        model = Navio
        fields = [
            'codigo', 'nome', 'armador', 'imo', 'bandeira', 'tipo',
            'capacidade_containers', 'capacidade_toneladas',
            'ano_construcao', 'comprimento_metros', 'velocidade_media_nós',
            'portos_operacao', 'status', 'ativo'
        ]
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'form-control'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'armador': forms.Select(attrs={'class': 'form-select'}),
            'imo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número IMO'}),
            'bandeira': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'capacidade_containers': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'capacidade_toneladas': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': 0.01}),
            'ano_construcao': forms.NumberInput(attrs={'class': 'form-control', 'min': 1900, 'max': 2100}),
            'comprimento_metros': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': 0.01}),
            'velocidade_media_nós': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': 0.01}),
            'portos_operacao': forms.SelectMultiple(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        self.empresa = empresa
        # Campos opcionais
        for f in ['imo', 'capacidade_toneladas', 'ano_construcao', 'comprimento_metros', 'velocidade_media_nós']:
            if f in self.fields:
                self.fields[f].required = False
        # Filtrar armadores por empresa
        if self.empresa and 'armador' in self.fields:
            self.fields['armador'].queryset = self.fields['armador'].queryset.filter(empresa=self.empresa)
        # Filtrar portos por empresa
        if self.empresa and 'portos_operacao' in self.fields:
            self.fields['portos_operacao'].queryset = self.fields['portos_operacao'].queryset.filter(empresa=self.empresa)

    def save(self, commit=True):
        obj = super().save(commit=False)
        if getattr(self, 'empresa', None):
            obj.empresa = self.empresa
        if commit:
            obj.save()
            # Salva ManyToMany
            try:
                self.save_m2m()
            except Exception:
                pass
        return obj
