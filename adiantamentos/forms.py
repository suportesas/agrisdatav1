from django import forms
from django.utils import timezone

from .models import AdiantamentoInternacional, DescontoAdiantamento


class AdiantamentoInternacionalForm(forms.ModelForm):
    class Meta:
        model = AdiantamentoInternacional
        fields = [
            'numero_referencia', 'data_adiantamento', 'cliente', 'safra_referencia', 'safra',
            'invoice_origem', 'moeda', 'valor_estrangeiro', 'taxa_cambio', 'valor_brl',
            'tipo_regra_desconto', 'valor_desconto_padrao', 'percentual_desconto',
            'data_prevista_reembolso', 'status', 'observacoes',
        ]
        widgets = {
            'numero_referencia': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: AD-2026-001'}),
            'data_adiantamento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'cliente': forms.Select(attrs={'class': 'form-select'}),
            'safra_referencia': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 2025/2026'}),
            'safra': forms.Select(attrs={'class': 'form-select'}),
            'invoice_origem': forms.Select(attrs={'class': 'form-select'}),
            'moeda': forms.Select(attrs={'class': 'form-select'}),
            'valor_estrangeiro': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'taxa_cambio': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001', 'value': '1'}),
            'valor_brl': forms.NumberInput(attrs={'class': 'form-control', 'readonly': True}),
            'tipo_regra_desconto': forms.Select(attrs={'class': 'form-select', 'id': 'id_tipo_regra_desconto'}),
            'valor_desconto_padrao': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'percentual_desconto': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
            'data_prevista_reembolso': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cliente'].queryset = self.fields['cliente'].queryset.filter(empresa=empresa) if empresa else self.fields['cliente'].queryset.none()
        self.fields['safra'].queryset = self.fields['safra'].queryset.filter(fazenda__empresa=empresa) if empresa else self.fields['safra'].queryset.none()
        self.fields['invoice_origem'].queryset = self.fields['invoice_origem'].queryset.filter(empresa=empresa) if empresa else self.fields['invoice_origem'].queryset.none()
        self.fields['safra'].required = False
        self.fields['invoice_origem'].required = False
        self.fields['valor_desconto_padrao'].required = False
        self.fields['percentual_desconto'].required = False
        self.fields['data_prevista_reembolso'].required = False
        self.fields['observacoes'].required = False
        self.fields['valor_brl'].required = False

    def clean(self):
        cleaned = super().clean()
        tipo = cleaned.get('tipo_regra_desconto')
        val_fixo = cleaned.get('valor_desconto_padrao')
        percentual = cleaned.get('percentual_desconto')

        if tipo == 'VALOR_FIXO' and not val_fixo:
            self.add_error('valor_desconto_padrao', 'Informe o valor fixo de desconto por embarque.')
        if tipo == 'PERCENTUAL' and not percentual:
            self.add_error('percentual_desconto', 'Informe o percentual de desconto.')
        return cleaned


class AplicarDescontoForm(forms.Form):
    invoice = forms.ModelChoiceField(
        queryset=None,
        label='Invoice de Exportação',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    valor_desconto_estrangeiro = forms.DecimalField(
        label='Valor do Desconto (Moeda Estrangeira)',
        min_value=0,
        max_digits=15,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
    )
    taxa_cambio_aplicada = forms.DecimalField(
        label='Taxa de Câmbio Aplicada',
        min_value=0,
        max_digits=10,
        decimal_places=4,
        initial=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
    )
    data_desconto = forms.DateField(
        label='Data do Desconto',
        initial=timezone.now,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
    )
    observacoes = forms.CharField(
        label='Observações',
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
    )

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        from faturamento.models import InvoiceExportacao
        qs = InvoiceExportacao.objects.filter(empresa=empresa, status__in=['RASCUNHO', 'EMITIDA']) if empresa else InvoiceExportacao.objects.none()
        self.fields['invoice'].queryset = qs


class PularDescontoForm(forms.Form):
    motivo_pulo = forms.CharField(
        label='Motivo de Pular este Embarque',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Ex: Embarque adiado — desconto será aplicado no próximo.'}),
    )
    data_desconto = forms.DateField(
        label='Data de Referência',
        initial=timezone.now,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
    )


class MigrarAdiantamentoForm(forms.Form):
    safra_referencia_destino = forms.CharField(
        label='Safra de Destino',
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 2026/2027'}),
    )
    data_migracao = forms.DateField(
        label='Data da Migração',
        initial=timezone.now,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
    )
    motivo = forms.CharField(
        label='Motivo da Migração',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
    )
