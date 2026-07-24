"""
Forms para o módulo financeiro
"""
from datetime import timedelta

from django import forms
from django.forms.models import inlineformset_factory
from django.urls import reverse_lazy
from django.utils import timezone
from core.widgets import MoneyBRInput, Select2AjaxWidget
from .models import (
    ConfiguracaoJurosMulta,
    ContaPagar,
    ParcelaContaPagar,
    PagamentoContaPagar,
    AjusteContaPagar,
    ContaReceber,
    ParcelaContaReceber,
    RecebimentoContaReceber,
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

    quantidade_parcelas = forms.IntegerField(
        label='Quantidade de Parcelas',
        min_value=1,
        initial=1,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'max': '999'
        })
    )
    intervalo_dias = forms.IntegerField(
        label='Intervalo entre Parcelas (dias)',
        min_value=1,
        initial=30,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'max': '365'
        })
    )
    primeira_data_vencimento = forms.DateField(
        label='Primeiro Vencimento',
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        if empresa:
            from cadastros.models import Fornecedor
            from plano_contas.models import ContaContabil, CentroCusto
            self.fields['fornecedor'].queryset = Fornecedor.objects.filter(
                empresa=empresa, ativa=True
            ).order_by('nome')
            self.fields['conta_contabil'].queryset = ContaContabil.objects.filter(
                empresa=empresa, analitica=True, ativo=True
            ).order_by('codigo')
            self.fields['centro_custo'].queryset = CentroCusto.objects.filter(
                empresa=empresa, ativo=True
            ).order_by('codigo')

        if not self.instance.pk:
            data_base = timezone.now().date()
            self.fields['primeira_data_vencimento'].initial = data_base + timedelta(days=30)
            self.fields['quantidade_parcelas'].help_text = 'Exemplo: 24 parcelas para um consórcio.'
            self.fields['intervalo_dias'].help_text = 'Use 30 para vencimentos mensais.'
            self.fields['primeira_data_vencimento'].help_text = 'A lista de parcelas exibirá 1/24, 2/24 e assim por diante.'

    class Meta:
        model = ContaPagar
        fields = [
            'numero',
            'fornecedor',
            'empresa',
            'recebimento',
            'data_emissao',
            'valor_total',
            'desconto_negociado',
            'requer_aprovacao',
            'conta_contabil',
            'centro_custo',
            'observacoes'
        ]
        widgets = {
            'numero': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número da conta'
            }),
            'fornecedor': Select2AjaxWidget(ajax_url=reverse_lazy('cadastros:ajax_buscar_fornecedores'), placeholder='Buscar fornecedor...'),
            'empresa': forms.Select(attrs={'class': 'form-control'}),
            'recebimento': forms.Select(attrs={
                'class': 'form-control',
                'required': False
            }),
            'data_emissao': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
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
            'conta_contabil': Select2AjaxWidget(ajax_url=reverse_lazy('plano_contas:conta_autocomplete'), extra_params={'analitica': '1'}, placeholder='Buscar conta contábil...'),
            'centro_custo': Select2AjaxWidget(ajax_url=reverse_lazy('plano_contas:centro_autocomplete'), placeholder='Buscar centro de custo...'),
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

    def clean(self):
        cleaned_data = super().clean()
        if self.instance.pk:
            return cleaned_data

        quantidade_parcelas = cleaned_data.get('quantidade_parcelas') or 1
        intervalo_dias = cleaned_data.get('intervalo_dias') or 30
        primeira_data_vencimento = cleaned_data.get('primeira_data_vencimento')

        if quantidade_parcelas < 1:
            self.add_error('quantidade_parcelas', 'Informe ao menos uma parcela.')

        if intervalo_dias < 1:
            self.add_error('intervalo_dias', 'O intervalo deve ser maior que zero.')

        if not primeira_data_vencimento:
            self.add_error('primeira_data_vencimento', 'Informe o primeiro vencimento.')

        return cleaned_data


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
            'valor_parcela': MoneyBRInput(),
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


# ============================================
# CONTAS A RECEBER
# ============================================

class ContaReceberForm(forms.ModelForm):
    class Meta:
        model = ContaReceber
        fields = [
            'cliente', 'data_emissao', 'data_vencimento',
            'moeda', 'valor_moeda', 'taxa_cambio', 'valor_brl',
            'descricao', 'observacoes',
            'conta_contabil', 'centro_custo',
        ]
        widgets = {
            'cliente': Select2AjaxWidget(ajax_url=reverse_lazy('cadastros:ajax_buscar_clientes'), placeholder='Buscar cliente...'),
            'data_emissao': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_vencimento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'moeda': forms.Select(attrs={'class': 'form-select', 'id': 'id_moeda'}),
            'valor_moeda': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'taxa_cambio': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001', 'min': '0'}),
            'valor_brl': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'descricao': forms.TextInput(attrs={'class': 'form-control'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'conta_contabil': Select2AjaxWidget(ajax_url=reverse_lazy('plano_contas:conta_autocomplete'), extra_params={'analitica': '1'}, placeholder='Buscar conta contábil...'),
            'centro_custo': Select2AjaxWidget(ajax_url=reverse_lazy('plano_contas:centro_autocomplete'), placeholder='Buscar centro de custo...'),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        if empresa:
            from cadastros.models import Cliente
            from plano_contas.models import ContaContabil, CentroCusto
            self.fields['cliente'].queryset = Cliente.objects.filter(empresa=empresa, status='ATIVO')
            self.fields['conta_contabil'].queryset = ContaContabil.objects.filter(
                empresa=empresa, analitica=True, ativo=True
            ).order_by('codigo')
            self.fields['centro_custo'].queryset = CentroCusto.objects.filter(
                empresa=empresa, ativo=True
            ).order_by('codigo')


class ParcelaContaReceberForm(forms.ModelForm):
    class Meta:
        model = ParcelaContaReceber
        fields = ['numero_parcela', 'valor_parcela_moeda', 'valor_parcela_brl', 'data_vencimento', 'observacoes']
        widgets = {
            'numero_parcela': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'valor_parcela_moeda': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'valor_parcela_brl': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'data_vencimento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'observacoes': forms.TextInput(attrs={'class': 'form-control'}),
        }


ParcelaContaReceberFormSet = inlineformset_factory(
    ContaReceber,
    ParcelaContaReceber,
    form=ParcelaContaReceberForm,
    extra=1,
    min_num=1,
    can_delete=True,
)


class RecebimentoContaReceberForm(forms.ModelForm):
    class Meta:
        model = RecebimentoContaReceber
        fields = [
            'data_pagamento', 'valor_recebido_moeda', 'valor_recebido_brl',
            'taxa_cambio_realizada', 'forma_pagamento', 'numero_documento',
            'banco', 'comprovante', 'observacoes',
        ]
        widgets = {
            'data_pagamento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'valor_recebido_moeda': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'valor_recebido_brl': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'taxa_cambio_realizada': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
            'forma_pagamento': forms.Select(attrs={'class': 'form-select'}),
            'numero_documento': forms.TextInput(attrs={'class': 'form-control'}),
            'banco': forms.TextInput(attrs={'class': 'form-control'}),
            'comprovante': forms.FileInput(attrs={'class': 'form-control'}),
            'observacoes': forms.TextInput(attrs={'class': 'form-control'}),
        }
