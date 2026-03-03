"""
Forms para o módulo financeiro
"""
from django import forms
from django.forms.models import inlineformset_factory
from .models import (
    ConfiguracaoJurosMulta,
    ContaPagar,
    ParcelaContaPagar,
    PagamentoContaPagar,
    AjusteContaPagar
)


class ConfiguracaoJurosMultaForm(forms.ModelForm):
    """Form para configuração de juros e multa"""
    
    class Meta:
        model = ConfiguracaoJurosMulta
        fields = ['empresa', 'taxa_juros_mensal', 'multa_atraso', 'tipo_multa', 'dias_tolerancia', 'ativo']
        widgets = {
            'empresa': forms.Select(attrs={'class': 'form-control'}),
            'taxa_juros_mensal': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'multa_atraso': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'tipo_multa': forms.Select(attrs={'class': 'form-control'}),
            'dias_tolerancia': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            }),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ContaPageForm(forms.ModelForm):
    """Form para criação/edição de conta a pagar"""
    
    class Meta:
        model = ContaPagar
        fields = [
            'numero',
            'fornecedor',
            'empresa',
            'recebimento',
            'valor_total',
            'desconto_negociado',
            'requer_aprovacao',
            'observacoes'
        ]
        widgets = {
            'numero': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número da conta'
            }),
            'fornecedor': forms.Select(attrs={'class': 'form-control'}),
            'empresa': forms.Select(attrs={'class': 'form-control'}),
            'recebimento': forms.Select(attrs={
                'class': 'form-control',
                'required': False
            }),
            'valor_total': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01'
            }),
            'desconto_negociado': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'value': '0.00'
            }),
            'requer_aprovacao': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'observacoes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Observações adicionais'
            }),
        }
    
    def clean_numero(self):
        numero = self.cleaned_data.get('numero')
        if numero:
            if self.instance.pk:
                # Editing existing - allow same number
                if ContaPagar.objects.filter(numero=numero).exclude(pk=self.instance.pk).exists():
                    raise forms.ValidationError('Este número de conta já existe.')
            else:
                # Creating new
                if ContaPagar.objects.filter(numero=numero).exists():
                    raise forms.ValidationError('Este número de conta já existe.')
        return numero


class ParcelaContaPageForm(forms.ModelForm):
    """Form para criação/edição de parcela"""
    
    class Meta:
        model = ParcelaContaPagar
        fields = [
            'numero_parcela',
            'valor_parcela',
            'data_vencimento',
            'observacao'
        ]
        widgets = {
            'numero_parcela': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1'
            }),
            'valor_parcela': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01'
            }),
            'data_vencimento': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'observacao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Observações'
            }),
        }


class PagamentoContaPageForm(forms.ModelForm):
    """Form para pagamento de parcela"""
    
    class Meta:
        model = PagamentoContaPagar
        fields = [
            'valor_pago',
            'forma_pagamento',
            'numero_documento',
            'banco',
            'data_pagamento',
            'comprovante',
            'observacao'
        ]
        widgets = {
            'valor_pago': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01'
            }),
            'forma_pagamento': forms.Select(attrs={'class': 'form-control'}),
            'numero_documento': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: número do cheque, boleto, etc'
            }),
            'banco': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Banco/Instituição'
            }),
            'data_pagamento': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'comprovante': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.jpg,.jpeg,.png'
            }),
            'observacao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Observações'
            }),
        }


class AjusteContaPageForm(forms.ModelForm):
    """Form para ajustes de conta"""
    
    class Meta:
        model = AjusteContaPagar
        fields = [
            'tipo',
            'valor_ajuste',
            'motivo',
            'divergencia',
            'observacao'
        ]
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'valor_ajuste': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'motivo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Motivo do ajuste'
            }),
            'divergencia': forms.Select(attrs={
                'class': 'form-control',
                'required': False
            }),
            'observacao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Observações'
            }),
        }
    
    def clean_valor_ajuste(self):
        valor = self.cleaned_data.get('valor_ajuste')
        # Validar se é um número válido
        return valor


# ============================================
# FORMSETS (for inline editing)
# ============================================

ParcelaContaPageFormSet = inlineformset_factory(
    ContaPagar,
    ParcelaContaPagar,
    form=ParcelaContaPageForm,
    extra=1,
    can_delete=True
)

PagamentoContaPageFormSet = inlineformset_factory(
    ContaPagar,
    PagamentoContaPagar,
    form=PagamentoContaPageForm,
    extra=1,
    can_delete=False
)

AjusteContaPageFormSet = inlineformset_factory(
    ContaPagar,
    AjusteContaPagar,
    form=AjusteContaPageForm,
    extra=1,
    can_delete=True
)
