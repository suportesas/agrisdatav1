from django import forms
from django.core.validators import MinLengthValidator
from django.forms import inlineformset_factory

from .models import (
    ConfiguracaoFiscal,
    ConhecimentoTransporte,
    DocumentoVinculadoCTe,
    DocumentoVinculadoMDFe,
    InvoiceExportacao,
    ItemInvoice,
    ItemNotaFiscal,
    ItemPackingList,
    ManifestoDocumentoFiscal,
    NotaFiscal,
    PackingList,
    PercursoMDFe,
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
    # Campo sobrescrito: usa PasswordInput e nunca devolve o ciphertext ao browser
    token_integranotas = forms.CharField(
        label='Token IntegraNota',
        required=False,
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Deixe em branco para manter o token atual',
                'autocomplete': 'new-password',
            },
            render_value=False,
        ),
        help_text='Deixe em branco para não alterar o token existente.',
    )

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
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        raw_token = self.cleaned_data.get('token_integranotas', '').strip()
        if raw_token:
            instance.set_token(raw_token)
        else:
            # super().save(commit=False) já sobrescreveu token_integranotas com ''
            # Restauramos o valor atual do banco para não apagar o token existente
            if instance.pk:
                current = ConfiguracaoFiscal.objects.filter(pk=instance.pk).values_list(
                    'token_integranotas', flat=True
                ).first()
                instance.token_integranotas = current or ''
        if commit:
            instance.save()
        return instance


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

# ═══════════════════════════════════════════════════════════════════
#  CT-e — Formulários
# ═══════════════════════════════════════════════════════════════════

class ConhecimentoTransporteForm(FaturamentoBaseForm):
    class Meta:
        model = ConhecimentoTransporte
        fields = [
            'remetente', 'destinatario', 'tomador', 'transportadora',
            'motorista', 'veiculo',
            'data_emissao', 'cfop', 'natureza_operacao', 'tipo_servico',
            'uf_inicio', 'municipio_inicio', 'uf_fim', 'municipio_fim',
            'modalidade_frete', 'valor_servico', 'valor_carga', 'peso_bruto_kg',
            'observacoes',
        ]
        widgets = {
            'remetente':         forms.Select(attrs={'class': 'form-select'}),
            'destinatario':      forms.Select(attrs={'class': 'form-select'}),
            'tomador':           forms.Select(attrs={'class': 'form-select'}),
            'transportadora':    forms.Select(attrs={'class': 'form-select'}),
            'motorista':         forms.Select(attrs={'class': 'form-select'}),
            'veiculo':           forms.Select(attrs={'class': 'form-select'}),
            'data_emissao':      forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'cfop':              forms.TextInput(attrs={'class': 'form-control', 'placeholder': '6351'}),
            'natureza_operacao': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo_servico':      forms.Select(attrs={'class': 'form-select'}),
            'uf_inicio':         forms.TextInput(attrs={'class': 'form-control', 'maxlength': '2', 'placeholder': 'SP'}),
            'municipio_inicio':  forms.TextInput(attrs={'class': 'form-control'}),
            'uf_fim':            forms.TextInput(attrs={'class': 'form-control', 'maxlength': '2', 'placeholder': 'MG'}),
            'municipio_fim':     forms.TextInput(attrs={'class': 'form-control'}),
            'modalidade_frete':  forms.Select(attrs={'class': 'form-select'}),
            'valor_servico':     forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'valor_carga':       forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'peso_bruto_kg':     forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'observacoes':       forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, empresa=empresa, **kwargs)
        if empresa:
            from cadastros.models import Cliente, Motorista, Transportadora, Vehicle
            self.fields['remetente'].queryset = Cliente.objects.filter(empresa=empresa, status='ATIVO').order_by('razao_social')
            self.fields['destinatario'].queryset = Cliente.objects.filter(empresa=empresa, status='ATIVO').order_by('razao_social')
            self.fields['tomador'].queryset = Cliente.objects.filter(empresa=empresa, status='ATIVO').order_by('razao_social')
            self.fields['transportadora'].queryset = Transportadora.objects.filter(empresa=empresa).order_by('razao_social')
            self.fields['motorista'].queryset = Motorista.objects.filter(empresa=empresa, ativo=True).order_by('nome')
            self.fields['veiculo'].queryset = Vehicle.objects.filter(empresa=empresa).order_by('descricao')
            self.fields['motorista'].required = False
            self.fields['veiculo'].required = False


class CancelarCTeForm(forms.Form):
    justificativa = forms.CharField(
        label='Justificativa do Cancelamento',
        min_length=15, max_length=255,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4,
                                     'placeholder': 'Informe o motivo do cancelamento (mínimo 15 caracteres)'}),
        validators=[MinLengthValidator(15)],
    )


class DocumentoVinculadoCTeForm(forms.ModelForm):
    class Meta:
        model = DocumentoVinculadoCTe
        fields = ['chave_nfe', 'descricao']
        widgets = {
            'chave_nfe':  forms.TextInput(attrs={'class': 'form-control form-control-sm', 'maxlength': '44', 'placeholder': 'Chave NF-e (44 dígitos)'}),
            'descricao':  forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Descrição / Produto (opcional)'}),
        }


DocumentoVinculadoCTeFormSet = inlineformset_factory(
    ConhecimentoTransporte, DocumentoVinculadoCTe,
    form=DocumentoVinculadoCTeForm,
    extra=1, can_delete=True, min_num=1, validate_min=True,
)


# ═══════════════════════════════════════════════════════════════════
#  MDF-e — Formulários
# ═══════════════════════════════════════════════════════════════════

class ManifestoDocumentoFiscalForm(FaturamentoBaseForm):
    class Meta:
        model = ManifestoDocumentoFiscal
        fields = [
            'motorista', 'veiculo',
            'data_emissao',
            'uf_inicio', 'municipio_carregamento', 'uf_fim',
            'tipo_transporte', 'valor_carga', 'peso_bruto_kg',
            'informacoes_fisco', 'informacoes_contribuinte',
        ]
        widgets = {
            'motorista':                 forms.Select(attrs={'class': 'form-select'}),
            'veiculo':                   forms.Select(attrs={'class': 'form-select'}),
            'data_emissao':              forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'uf_inicio':                 forms.TextInput(attrs={'class': 'form-control', 'maxlength': '2', 'placeholder': 'SP'}),
            'municipio_carregamento':    forms.TextInput(attrs={'class': 'form-control'}),
            'uf_fim':                    forms.TextInput(attrs={'class': 'form-control', 'maxlength': '2', 'placeholder': 'MG'}),
            'tipo_transporte':           forms.Select(attrs={'class': 'form-select'}),
            'valor_carga':               forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'peso_bruto_kg':             forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'informacoes_fisco':         forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'informacoes_contribuinte':  forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, empresa=empresa, **kwargs)
        if empresa:
            from cadastros.models import Motorista, Vehicle
            self.fields['motorista'].queryset = Motorista.objects.filter(empresa=empresa, ativo=True).order_by('nome')
            self.fields['veiculo'].queryset = Vehicle.objects.filter(empresa=empresa).order_by('descricao')


class EncerrarMDFeForm(forms.Form):
    municipio_encerramento = forms.CharField(
        label='Município de Encerramento',
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Cidade onde a viagem terminou'}),
    )


class CancelarMDFeForm(forms.Form):
    justificativa = forms.CharField(
        label='Justificativa do Cancelamento',
        min_length=15, max_length=255,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4,
                                     'placeholder': 'Informe o motivo do cancelamento (mínimo 15 caracteres)'}),
        validators=[MinLengthValidator(15)],
    )


class DocumentoVinculadoMDFeForm(forms.ModelForm):
    class Meta:
        model = DocumentoVinculadoMDFe
        fields = ['tipo', 'chave', 'municipio_descarregamento']
        widgets = {
            'tipo':                     forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'chave':                    forms.TextInput(attrs={'class': 'form-control form-control-sm', 'maxlength': '44', 'placeholder': 'Chave (44 dígitos)'}),
            'municipio_descarregamento': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Cidade de entrega'}),
        }


DocumentoVinculadoMDFeFormSet = inlineformset_factory(
    ManifestoDocumentoFiscal, DocumentoVinculadoMDFe,
    form=DocumentoVinculadoMDFeForm,
    extra=1, can_delete=True, min_num=1, validate_min=True,
)


class PercursoMDFeForm(forms.ModelForm):
    class Meta:
        model = PercursoMDFe
        fields = ['uf', 'ordem']
        widgets = {
            'uf':    forms.TextInput(attrs={'class': 'form-control form-control-sm', 'maxlength': '2', 'placeholder': 'Ex: RJ'}),
            'ordem': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'style': 'width:70px'}),
        }


PercursoMDFeFormSet = inlineformset_factory(
    ManifestoDocumentoFiscal, PercursoMDFe,
    form=PercursoMDFeForm,
    extra=1, can_delete=True, min_num=0,
)
