from django import forms
from .models import Empresa, Plano


class EmpresaForm(forms.ModelForm):
    """Formulário para criar/editar empresas"""
    
    class Meta:
        model = Empresa
        fields = [
            'nome', 'cnpj', 'telefone', 'email',
            'endereco', 'cidade', 'uf',
            'plano',  # Campo de plano
            'valor_mensalidade', 'dia_vencimento', 'data_expiracao',
            'ativa', 'bloqueada', 'bloqueada_ate', 'motivo_bloqueio',
        ]
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'cnpj': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '00.000.000/0000-00'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'endereco': forms.TextInput(attrs={'class': 'form-control'}),
            'cidade': forms.TextInput(attrs={'class': 'form-control'}),
            'uf': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 2}),
            'plano': forms.Select(attrs={'class': 'form-select'}),
            'valor_mensalidade': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'dia_vencimento': forms.NumberInput(attrs={'class': 'form-control'}),
            'data_expiracao': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'bloqueada_ate': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'motivo_bloqueio': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class PlanoForm(forms.ModelForm):
    """Formulário para criar/editar planos"""
    
    class Meta:
        model = Plano
        fields = [
            'codigo', 'nome', 'icone', 'ordem', 'ativo',
            'valor_mensal', 'valor_anual', 'desconto_anual',
            'limite_fazendas', 'limite_usuarios', 'limite_talhoes', 'limite_produtos',
            'acesso_relatorios_avancados', 'acesso_api', 
            'acesso_app_mobile', 'acesso_suporte_prioritario',
            'descricao'
        ]
        widgets = {
            'codigo': forms.Select(attrs={'class': 'form-select'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'icone': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 10}),
            'ordem': forms.NumberInput(attrs={'class': 'form-control'}),
            'valor_mensal': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'valor_anual': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'desconto_anual': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'limite_fazendas': forms.NumberInput(attrs={'class': 'form-control'}),
            'limite_usuarios': forms.NumberInput(attrs={'class': 'form-control'}),
            'limite_talhoes': forms.NumberInput(attrs={'class': 'form-control'}),
            'limite_produtos': forms.NumberInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        help_texts = {
            'valor_anual': 'Deixe em branco para calcular automaticamente',
            'desconto_anual': 'Percentual de desconto para pagamento anual',
            'ordem': 'Ordem de exibição (menor = primeiro)',
        }