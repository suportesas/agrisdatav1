"""
Formulários do módulo Patrimônio
"""

from django import forms
from django.core.exceptions import ValidationError
from decimal import Decimal
from .models import Patrimonio, PatrimonioMovimentacao
from cadastros.models import Vehicle, Fazenda


class PatrimonioForm(forms.ModelForm):
    """Formulário para cadastro e edição de patrimônio"""
    
    class Meta:
        model = Patrimonio
        exclude = ('empresa', 'data_cadastro', 'data_atualizacao', 'valor_atual')
        widgets = {
            'numero_patrimonio': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: PAT-001'}),
            'descricao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Descrição do bem'}),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'veiculo': forms.Select(attrs={'class': 'form-select'}),
            'valor_inicial': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'valor_residual': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tipo_depreciacao': forms.Select(attrs={'class': 'form-select'}),
            'vida_util_anos': forms.NumberInput(attrs={'class': 'form-control'}),
            'percentual_depreciacao_anual': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'data_aquisicao': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_baixa': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'localizacao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Galpão A, Campo 1, etc'}),
            'responsavel': forms.Select(attrs={'class': 'form-select'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if self.empresa:
            # Filtrar veículos da empresa
            self.fields['veiculo'].queryset = Vehicle.objects.filter(
                empresa=self.empresa, 
                ativo=True
            ).select_related()
            
            # Filtrar responsáveis da empresa
            self.fields['responsavel'].queryset = self.fields['responsavel'].queryset.filter(
                empresa=self.empresa
            )
    
    def clean(self):
        cleaned = super().clean()
        data_aquisicao = cleaned.get('data_aquisicao')
        data_baixa = cleaned.get('data_baixa')
        
        if data_aquisicao and data_baixa and data_baixa <= data_aquisicao:
            raise ValidationError({'data_baixa': 'Data de baixa deve ser após data de aquisição.'})
        
        vida_util = cleaned.get('vida_util_anos')
        if vida_util and vida_util <= 0:
            raise ValidationError({'vida_util_anos': 'Vida útil deve ser maior que zero.'})
        
        return cleaned
    
    def save(self, commit=True, user=None):
        obj = super().save(commit=False)
        if self.empresa:
            obj.empresa = self.empresa
        
        # Auto-calcular valor residual se não informado
        if not obj.valor_residual and obj.valor_inicial:
            obj.valor_residual = obj.valor_inicial * Decimal('0.1')  # 10% do valor inicial
        
        # Auto-calcular percentual de depreciação anual se não informado
        if not obj.percentual_depreciacao_anual and obj.vida_util_anos:
            obj.percentual_depreciacao_anual = Decimal('100') / Decimal(max(obj.vida_util_anos, 1))
        
        # Atualizar valor atual
        obj.atualizar_valor_atual()
        
        if commit:
            obj.save()
        
        return obj


class PatrimonioVeiculoExportForm(forms.Form):
    """Formulário para exportar um veículo como patrimônio"""
    
    numero_patrimonio = forms.CharField(
        label='Número de Patrimônio',
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: VEI-0001'})
    )
    valor_inicial = forms.DecimalField(
        label='Valor do Veículo (R$)',
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    data_aquisicao = forms.DateField(
        label='Data de Aquisição',
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    vida_util_anos = forms.IntegerField(
        label='Vida Útil (anos)',
        initial=10,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    fazenda = forms.ModelChoiceField(
        label='Localização (Fazenda)',
        queryset=Fazenda.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False,
        empty_label='Selecione uma fazenda ou deixe em branco'
    )
    localizacao_detalhada = forms.CharField(
        label='Localização Detalhada (opcional)',
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Galpão A, Campo Norte, etc'})
    )
    
    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if empresa:
            self.fields['fazenda'].queryset = Fazenda.objects.filter(empresa=empresa, ativa=True).order_by('nome')


class PatrimonioMovimentacaoForm(forms.ModelForm):
    """Formulário para registrar movimentação de patrimônio"""
    
    class Meta:
        model = PatrimonioMovimentacao
        fields = ['tipo', 'responsavel_anterior', 'responsavel_novo', 'localizacao_anterior', 'localizacao_nova', 'observacoes']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'responsavel_anterior': forms.Select(attrs={'class': 'form-select'}),
            'responsavel_novo': forms.Select(attrs={'class': 'form-select'}),
            'localizacao_anterior': forms.TextInput(attrs={'class': 'form-control'}),
            'localizacao_nova': forms.TextInput(attrs={'class': 'form-control'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
