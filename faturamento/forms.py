from django import forms
from django.core.validators import MinLengthValidator
from django.forms import inlineformset_factory

from .models import (
    ConfiguracaoFiscal,
    InvoiceExportacao,
    ItemInvoice,
    ItemNotaFiscal,
    ItemPackingList,
    NotaFiscal,
    PackingList,
)


class FaturamentoBaseForm(forms.ModelForm):
    def __init__(self, *args, empresa=None, **kwargs):
        self.empresa = empresa
        super().__init__(*args, **kwargs)
        if 'empresa' in self.fields:
            self.fields['empresa'].widget = forms.HiddenInput()
            self.fields['empresa'].required = False
        if self.empresa:
            self.initial['empresa'] = self.empresa

    def save(self, commit=True, user=None):
        instance = super().save(commit=False)
        if self.empresa:
            instance.empresa = self.empresa
        if user:
            if not instance.pk:
                instance.criado_por = user
            instance.atualizado_por = user
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class CertificadoDigitalForm(forms.Form):
    arquivo_pfx = forms.FileField(
        label='Arquivo do Certificado (.pfx / .p12)',
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.pfx,.p12'}),
    )
    senha_certificado = forms.CharField(
        label='Senha do Certificado',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'}),
    )

    def clean_arquivo_pfx(self):
        arquivo = self.cleaned_data.get('arquivo_pfx')
        if arquivo:
            nome = arquivo.name.lower()
            if not (nome.endswith('.pfx') or nome.endswith('.p12')):
                raise forms.ValidationError('Somente arquivos .pfx ou .p12 são aceitos.')
            if arquivo.size > 1024 * 1024:  # 1 MB
                raise forms.ValidationError('O arquivo não pode exceder 1 MB.')
        return arquivo


class NotaFiscalCancelarForm(forms.Form):
    justificativa = forms.CharField(
        label='Justificativa do Cancelamento',
        min_length=15,
        max_length=255,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4,
                                     'placeholder': 'Informe o motivo do cancelamento (mínimo 15 caracteres)'}),
        validators=[MinLengthValidator(15)],
    )


class ConfiguracaoFiscalForm(forms.ModelForm):
    class Meta:
        model = ConfiguracaoFiscal
        fields = [
            'regime_tributario',
            'serie_nfe',
            'numero_nfe_inicial',
            'cfop_venda_interna',
            'cfop_venda_exportacao',
            'natureza_operacao_padrao',
            'observacoes_padrao_nfe',
            'observacoes_padrao_invoice',
            'ambiente_nfe',
            'token_integranotas',
        ]
        widgets = {
            'regime_tributario': forms.Select(attrs={'class': 'form-select'}),
            'serie_nfe': forms.NumberInput(attrs={'class': 'form-control'}),
            'numero_nfe_inicial': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'cfop_venda_interna': forms.TextInput(attrs={'class': 'form-control'}),
            'cfop_venda_exportacao': forms.TextInput(attrs={'class': 'form-control'}),
            'natureza_operacao_padrao': forms.TextInput(attrs={'class': 'form-control'}),
            'observacoes_padrao_nfe': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'observacoes_padrao_invoice': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'ambiente_nfe': forms.Select(attrs={'class': 'form-select'}),
            'token_integranotas': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Bearer token da API IntegraNota'}),
        }


class NotaFiscalForm(FaturamentoBaseForm):
    class Meta:
        model = NotaFiscal
        fields = [
            'cliente',
            'natureza_operacao',
            'data_emissao',
            'data_saida',
            'cfop',
            'modalidade_frete',
            'transportadora',
            'valor_frete',
            'valor_seguro',
            'valor_desconto',
            'informacoes_complementares',
        ]
        widgets = {
            'cliente': forms.Select(attrs={'class': 'form-select'}),
            'natureza_operacao': forms.TextInput(attrs={'class': 'form-control'}),
            'data_emissao': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'data_saida': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'cfop': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '5102'}),
            'modalidade_frete': forms.Select(attrs={'class': 'form-select'}),
            'transportadora': forms.Select(attrs={'class': 'form-select'}),
            'valor_frete': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'valor_seguro': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'valor_desconto': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'informacoes_complementares': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, empresa=empresa, **kwargs)
        if empresa:
            from cadastros.models import Cliente, Fornecedor
            self.fields['cliente'].queryset = Cliente.objects.filter(empresa=empresa, status='ATIVO').order_by('razao_social')
            self.fields['transportadora'].queryset = Fornecedor.objects.filter(empresa=empresa, ativa=True).order_by('nome')
            self.fields['transportadora'].required = False


class ItemNotaFiscalForm(forms.ModelForm):
    class Meta:
        model = ItemNotaFiscal
        fields = [
            'numero_item',
            'descricao',
            'produto',
            'ncm',
            'cest',
            'ean',
            'cfop',
            'cst_icms',
            'cst_pis',
            'cst_cofins',
            'origem_mercadoria',
            'unidade',
            'quantidade',
            'valor_unitario',
            'valor_desconto',
            'aliquota_icms',
            'aliquota_ipi',
            'ipi_codigo_enquadramento',
            'aliquota_pis',
            'aliquota_cofins',
        ]
        widgets = {
            'numero_item': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'style': 'width:70px'}),
            'descricao': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'produto': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'ncm': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'maxlength': '8', 'placeholder': '00000000'}),
            'cest': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'maxlength': '7', 'placeholder': '0000000'}),
            'ean': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Deixe vazio para SEM GTIN'}),
            'cfop': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': '5102'}),
            'cst_icms': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': '000'}),
            'cst_pis': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': '07'}),
            'cst_cofins': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': '07'}),
            'origem_mercadoria': forms.Select(attrs={'class': 'form-select form-select-sm'},
                                              choices=[('0','0-Nacional'),('1','1-Estrangeira (importada)'),
                                                       ('2','2-Estrangeira (adquirida no mercado interno)'),
                                                       ('3','3-Nacional, mercadoria ou bem com Conteúdo de Importação > 40%'),
                                                       ('4','4-Nacional, cuja produção tenha sido feita em conformidade com os processos produtivos básicos'),
                                                       ('5','5-Nacional, mercadoria ou bem com Conteúdo de Importação ≤ 40%'),
                                                       ('6','6-Estrangeira (importada diretamente), sem produto nacional similar'),
                                                       ('7','7-Estrangeira (adquirida no mercado interno), sem produto nacional similar'),
                                                       ('8','8-Nacional, mercadoria ou bem com Conteúdo de Importação > 70%')]),
            'unidade': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'UN'}),
            'quantidade': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.0001'}),
            'valor_unitario': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.0001'}),
            'valor_desconto': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01'}),
            'aliquota_icms': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01'}),
            'aliquota_ipi': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01'}),
            'ipi_codigo_enquadramento': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': '999'}),
            'aliquota_pis': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01'}),
            'aliquota_cofins': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01'}),
        }


ItemNotaFiscalFormSet = inlineformset_factory(
    NotaFiscal,
    ItemNotaFiscal,
    form=ItemNotaFiscalForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
)


class InvoiceExportacaoForm(FaturamentoBaseForm):
    class Meta:
        model = InvoiceExportacao
        fields = [
            'booking',
            'cliente',
            'data_emissao',
            'data_embarque_previsto',
            'incoterm',
            'moeda',
            'taxa_cambio',
            'porto_embarque',
            'porto_destino',
            'condicao_pagamento',
            'banco_beneficiario',
            'valor_frete',
            'valor_seguro',
            'observacoes',
        ]
        widgets = {
            'booking': forms.Select(attrs={'class': 'form-select', 'id': 'id_booking'}),
            'cliente': forms.Select(attrs={'class': 'form-select'}),
            'data_emissao': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'data_embarque_previsto': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'incoterm': forms.Select(attrs={'class': 'form-select'}),
            'moeda': forms.Select(attrs={'class': 'form-select'}),
            'taxa_cambio': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
            'porto_embarque': forms.TextInput(attrs={'class': 'form-control'}),
            'porto_destino': forms.TextInput(attrs={'class': 'form-control'}),
            'condicao_pagamento': forms.TextInput(attrs={'class': 'form-control'}),
            'banco_beneficiario': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'valor_frete': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'valor_seguro': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, empresa=empresa, **kwargs)
        if empresa:
            from cadastros.models import Cliente
            from exportacao.models import Booking
            self.fields['booking'].queryset = Booking.objects.filter(
                empresa=empresa,
                status='CONFIRMADO',
            ).order_by('-data_embarque_previsto')
            self.fields['booking'].required = False
            self.fields['cliente'].queryset = Cliente.objects.filter(
                empresa=empresa,
                status='ATIVO',
            ).order_by('razao_social')
            self.fields['taxa_cambio'].required = False
            self.fields['data_embarque_previsto'].required = False

    def clean(self):
        cleaned = super().clean()
        booking = cleaned.get('booking')
        if booking and booking.status != 'CONFIRMADO':
            self.add_error('booking', 'Somente bookings com status CONFIRMADO podem ser faturados.')
        return cleaned


class ItemInvoiceForm(forms.ModelForm):
    class Meta:
        model = ItemInvoice
        fields = [
            'container',
            'descricao',
            'quantidade',
            'unidade',
            'peso_bruto_kg',
            'peso_liquido_kg',
            'valor_unitario_fob',
            'marks_numbers',
        ]
        widgets = {
            'container': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'descricao': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'quantidade': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.0001'}),
            'unidade': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'CTN'}),
            'peso_bruto_kg': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.001'}),
            'peso_liquido_kg': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.001'}),
            'valor_unitario_fob': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.0001'}),
            'marks_numbers': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['container'].required = False
        if empresa:
            from exportacao.models import BookingContainer
            self.fields['container'].queryset = BookingContainer.objects.filter(booking__empresa=empresa)
        else:
            self.fields['container'].queryset = ItemInvoice._meta.get_field('container').related_model.objects.none()


ItemInvoiceFormSet = inlineformset_factory(
    InvoiceExportacao,
    ItemInvoice,
    form=ItemInvoiceForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
)


class PackingListForm(FaturamentoBaseForm):
    class Meta:
        model = PackingList
        fields = [
            'invoice',
            'data_emissao',
            'observacoes',
        ]
        widgets = {
            'invoice': forms.Select(attrs={'class': 'form-select'}),
            'data_emissao': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, empresa=empresa, **kwargs)
        if empresa:
            self.fields['invoice'].queryset = InvoiceExportacao.objects.filter(
                empresa=empresa,
                status='EMITIDA',
            ).order_by('-data_emissao')


class ItemPackingListForm(forms.ModelForm):
    class Meta:
        model = ItemPackingList
        fields = [
            'container',
            'numero_container',
            'tipo_container',
            'lacre_armador',
            'lacre_fiscal',
            'descricao_produto',
            'quantidade_caixas',
            'quantidade_pallets',
            'peso_bruto_kg',
            'peso_liquido_kg',
            'volume_m3',
            'marks_numbers',
            'ordem',
        ]
        widgets = {
            'container': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'numero_container': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'tipo_container': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': '40HC'}),
            'lacre_armador': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'lacre_fiscal': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'descricao_produto': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'quantidade_caixas': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01'}),
            'quantidade_pallets': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01'}),
            'peso_bruto_kg': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.001'}),
            'peso_liquido_kg': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.001'}),
            'volume_m3': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.001'}),
            'marks_numbers': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'ordem': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'style': 'width:70px'}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        for f in ['container', 'quantidade_pallets', 'volume_m3']:
            self.fields[f].required = False
        if empresa:
            from exportacao.models import BookingContainer
            self.fields['container'].queryset = BookingContainer.objects.filter(booking__empresa=empresa)
        else:
            self.fields['container'].queryset = ItemPackingList._meta.get_field('container').related_model.objects.none()


ItemPackingListFormSet = inlineformset_factory(
    PackingList,
    ItemPackingList,
    form=ItemPackingListForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
)
