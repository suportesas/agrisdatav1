from django import forms

from .models import Produtor


class ProdutorForm(forms.ModelForm):
    class Meta:
        model = Produtor
        fields = [
            'razao_social',
            'nome_fantasia',
            'cnpj_cpf',
            'inscricao_estadual',
            'telefone',
            'email',
            'cep',
            'logradouro',
            'numero',
            'complemento',
            'bairro',
            'cidade',
            'uf',
            'status',
            'observacoes',
            'portal_enabled',
        ]
        widgets = {
            'razao_social': forms.TextInput(attrs={'class': 'form-control'}),
            'nome_fantasia': forms.TextInput(attrs={'class': 'form-control'}),
            'cnpj_cpf': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '00.000.000/0000-00'}),
            'inscricao_estadual': forms.TextInput(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'cep': forms.TextInput(attrs={'class': 'form-control'}),
            'logradouro': forms.TextInput(attrs={'class': 'form-control'}),
            'numero': forms.TextInput(attrs={'class': 'form-control'}),
            'complemento': forms.TextInput(attrs={'class': 'form-control'}),
            'bairro': forms.TextInput(attrs={'class': 'form-control'}),
            'cidade': forms.TextInput(attrs={'class': 'form-control'}),
            'uf': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '2'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'portal_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        usuario = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)
        # Só permite edição do campo portal_enabled para administradores da empresa
        if 'portal_enabled' in self.fields and usuario and not getattr(usuario, 'is_admin_empresa', lambda: False)():
            self.fields['portal_enabled'].disabled = True
            self.fields['portal_enabled'].help_text = 'Apenas administradores da empresa podem habilitar o portal do produtor.'
