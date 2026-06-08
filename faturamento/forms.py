from django import forms
from django.core.validators import MinLengthValidator
from django.forms import inlineformset_factory

from .models import (
    CartaCorrecaoNFe,
    ConfiguracaoFiscal,
    ConhecimentoTransporte,
    DocumentoVinculadoCTe,
    DocumentoVinculadoMDFe,
    DuplicataNF,
    InvoiceExportacao,
    InutilizacaoNFe,
    ItemInvoice,
    ItemNotaFiscal,
    ItemPackingList,
    ManifestoDocumentoFiscal,
    NotaFiscal,
    PackingList,
    PagamentoNF,
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


class CartaCorrecaoNFeForm(forms.Form):
    correcao = forms.CharField(
        label='Texto da Correção',
        min_length=15,
        max_length=1000,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Descreva a correção a ser feita (mínimo 15 caracteres)',
            'id': 'id_correcao_text',
        }),
        validators=[MinLengthValidator(15)],
    )


class InutilizacaoNFeForm(forms.Form):
    serie = forms.IntegerField(
        label='Série',
        initial=1,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )
    numero_ini = forms.IntegerField(
        label='Número Inicial',
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )
    numero_fim = forms.IntegerField(
        label='Número Final',
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )
    ano = forms.IntegerField(
        label='Ano',
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )
    justificativa = forms.CharField(
        label='Justificativa',
        min_length=15,
        max_length=255,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Motivo da inutilização (mínimo 15 caracteres)',
        }),
        validators=[MinLengthValidator(15)],
    )

    def clean(self):
        cleaned = super().clean()
        ini = cleaned.get('numero_ini')
        fim = cleaned.get('numero_fim')
        if ini and fim and fim < ini:
            self.add_error('numero_fim', 'Número final deve ser ≥ número inicial.')
        return cleaned


MANIFESTACAO_TIPO_CHOICES = [
    ('', '-- Selecione --'),
    ('ciencia_operacao', 'Ciência da Operação'),
    ('confirmacao_operacao', 'Confirmação da Operação'),
    ('desconhecimento_operacao', 'Desconhecimento da Operação'),
    ('operacao_nao_realizada', 'Operação Não Realizada'),
]


class ManifestacaoNFeForm(forms.Form):
    tipo = forms.ChoiceField(
        label='Tipo de Manifestação',
        choices=MANIFESTACAO_TIPO_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_tipo_manifestacao'}),
    )
    justificativa = forms.CharField(
        label='Justificativa',
        required=False,
        max_length=255,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Obrigatório apenas para "Operação Não Realizada"',
            'id': 'id_justificativa_manifestacao',
        }),
    )

    def clean(self):
        cleaned = super().clean()
        tipo = cleaned.get('tipo')
        justif = cleaned.get('justificativa', '').strip()
        if tipo == 'operacao_nao_realizada' and not justif:
            self.add_error('justificativa', 'Justificativa obrigatória para "Operação Não Realizada".')
        return cleaned


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
    def clean_token_integranotas(self):
        token = self.cleaned_data.get('token_integranotas', '')
        return token.strip()
    

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
            'finalidade_nfe',
            'data_emissao',
            'data_saida',
            'cfop',
            'presenca_comprador',
            'modalidade_frete',
            'transportadora',
            'quantidade_volumes',
            'especie_volumes',
            'marca_volumes',
            'numeracao_volumes',
            'peso_bruto_kg',
            'peso_liquido_kg',
            'valor_frete',
            'valor_seguro',
            'valor_desconto',
            'informacoes_complementares',
            'informacoes_fisco',
            # Exportação
            'embarque_uf',
            'embarque_local',
            'embarque_local_despacho',
            # Endereço de entrega
            'entrega_ativo',
            'entrega_cnpj_cpf',
            'entrega_logradouro',
            'entrega_numero',
            'entrega_complemento',
            'entrega_bairro',
            'entrega_codigo_municipio',
            'entrega_nome_municipio',
            'entrega_uf',
        ]
        _fc = {'class': 'form-control form-control-sm'}
        widgets = {
            'cliente': forms.Select(attrs={'class': 'form-select'}),
            'natureza_operacao': forms.TextInput(attrs={'class': 'form-control'}),
            'finalidade_nfe': forms.Select(attrs={'class': 'form-select'}),
            'data_emissao': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'data_saida': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'cfop': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '5102'}),
            'presenca_comprador': forms.Select(attrs={'class': 'form-select'}),
            'modalidade_frete': forms.Select(attrs={'class': 'form-select'}),
            'transportadora': forms.Select(attrs={'class': 'form-select'}),
            'quantidade_volumes': forms.NumberInput(attrs={'class': 'form-control', 'step': '1', 'min': '0'}),
            'especie_volumes': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: SACOS'}),
            'marca_volumes': forms.TextInput(attrs={'class': 'form-control'}),
            'numeracao_volumes': forms.TextInput(attrs={'class': 'form-control'}),
            'peso_bruto_kg': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'peso_liquido_kg': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'valor_frete': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'valor_seguro': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'valor_desconto': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'informacoes_complementares': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'informacoes_fisco': forms.Textarea(attrs={'class': 'form-control', 'rows': 2,
                                                       'placeholder': 'Informações para o Fisco (infAdFisco)'}),
            # Exportação
            'embarque_uf': forms.TextInput(attrs={**_fc, 'placeholder': 'CE', 'maxlength': '2',
                                                   'style': 'text-transform:uppercase;'}),
            'embarque_local': forms.TextInput(attrs={**_fc, 'placeholder': 'Ex: Porto Mucuripe'}),
            'embarque_local_despacho': forms.TextInput(attrs={**_fc, 'placeholder': 'Ex: Recinto Alfandegado (opcional)'}),
            # Endereço de entrega
            'entrega_ativo': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_entrega_ativo'}),
            'entrega_cnpj_cpf': forms.TextInput(attrs={**_fc, 'placeholder': 'Somente dígitos (CNPJ 14 / CPF 11)', 'maxlength': '14'}),
            'entrega_logradouro': forms.TextInput(attrs={**_fc, 'placeholder': 'Rua, Av., Rodovia...'}),
            'entrega_numero': forms.TextInput(attrs={**_fc, 'placeholder': 'S/N'}),
            'entrega_complemento': forms.TextInput(attrs={**_fc, 'placeholder': 'Apto, Sala, Bloco...'}),
            'entrega_bairro': forms.TextInput(attrs={**_fc, 'placeholder': 'Bairro'}),
            'entrega_codigo_municipio': forms.TextInput(attrs={**_fc, 'placeholder': '7 dígitos IBGE', 'maxlength': '7'}),
            'entrega_nome_municipio': forms.TextInput(attrs={**_fc, 'placeholder': 'Município'}),
            'entrega_uf': forms.TextInput(attrs={**_fc, 'placeholder': 'UF', 'maxlength': '2', 'style': 'text-transform:uppercase;'}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, empresa=empresa, **kwargs)
        if empresa:
            from cadastros.models import Cliente, Fornecedor
            self.fields['cliente'].queryset = Cliente.objects.filter(empresa=empresa, status='ATIVO').order_by('razao_social')
            self.fields['transportadora'].queryset = Fornecedor.objects.filter(empresa=empresa, ativa=True).order_by('nome')
            self.fields['transportadora'].required = False
            self.fields['informacoes_fisco'].required = False
        # Campos de exportação e entrega são sempre opcionais
        for f in ('embarque_uf', 'embarque_local', 'embarque_local_despacho',
                  'entrega_cnpj_cpf', 'entrega_logradouro', 'entrega_numero',
                  'entrega_complemento', 'entrega_bairro',
                  'entrega_codigo_municipio', 'entrega_nome_municipio', 'entrega_uf'):
            self.fields[f].required = False


_sm = {'class': 'form-control form-control-sm'}
_sm_sel = {'class': 'form-select form-select-sm'}
_sm_num = {'class': 'form-control form-control-sm', 'step': '0.01'}
_sm_num4 = {'class': 'form-control form-control-sm', 'step': '0.0001'}

ORIGEM_CHOICES = [
    ('0', '0 - Nacional'),
    ('1', '1 - Estrangeira (importação direta)'),
    ('2', '2 - Estrangeira (mercado interno)'),
    ('3', '3 - Nacional c/ Importação > 40%'),
    ('4', '4 - Nacional (PPB)'),
    ('5', '5 - Nacional c/ Importação ≤ 40%'),
    ('6', '6 - Estrangeira direta s/ similar'),
    ('7', '7 - Estrangeira interna s/ similar'),
    ('8', '8 - Nacional c/ Importação > 70%'),
]

MODALIDADE_BC_ICMS_CHOICES = [
    ('0', '0 - Margem Valor Agregado (MVA)'),
    ('1', '1 - Pauta'),
    ('2', '2 - Preço Tabelado Máximo'),
    ('3', '3 - Valor da Operação'),
]

CST_IPI_CHOICES = [
    ('00', '00 - Entrada com Recuperação de Crédito'),
    ('49', '49 - Outras entradas'),
    ('50', '50 - Saída tributada'),
    ('51', '51 - Saída tributada com alíquota zero'),
    ('52', '52 - Saída isenta'),
    ('53', '53 - Saída não tributada'),
    ('54', '54 - Saída imune'),
    ('55', '55 - Saída com suspensão'),
    ('99', '99 - Outras saídas'),
]


class ItemNotaFiscalForm(forms.ModelForm):
    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        from produtos.models import Produto
        if empresa:
            self.fields['produto'].queryset = Produto.objects.filter(
                categoria__empresa=empresa, ativo=True
            ).select_related('unidade_venda').order_by('codigo', 'nome')
        else:
            self.fields['produto'].queryset = Produto.objects.none()

    class Meta:
        model = ItemNotaFiscal
        fields = [
            'numero_item', 'descricao', 'produto',
            'ncm', 'cest', 'ean', 'origem_mercadoria',
            'cfop', 'unidade', 'quantidade', 'valor_unitario', 'valor_desconto',
            # Unidade Tributável (exportação CFOP 7xxx)
            'quantidade_tributavel', 'unidade_tributavel', 'valor_unitario_tributavel',
            # ICMS
            'cst_icms', 'icms_modalidade_base', 'icms_reducao_base', 'aliquota_icms',
            # ICMS ST
            'icms_st_aliquota', 'icms_st_mva', 'icms_st_reducao_base',
            # IPI
            'cst_ipi', 'aliquota_ipi', 'ipi_codigo_enquadramento',
            # PIS / COFINS
            'cst_pis', 'aliquota_pis', 'natureza_receita_pis',
            'cst_cofins', 'aliquota_cofins', 'natureza_receita_cofins',
            # DI - Declaração de Importação
            'di_numero', 'di_data_registro', 'di_local_desembaraco',
            'di_uf_desembaraco', 'di_data_desembaraco', 'di_via_transporte',
            'di_valor_afrmm', 'di_tipo_intermediario', 'di_cnpj_adquirente',
            'di_codigo_exportador', 'di_numero_adicao', 'di_codigo_fabricante',
            'di_desconto_adicao', 'di_numero_drawback',
        ]
        widgets = {
            'numero_item': forms.HiddenInput(),
            'descricao': forms.TextInput(attrs=_sm),
            'produto': forms.Select(attrs=_sm_sel),
            'ncm': forms.TextInput(attrs={**_sm, 'maxlength': '8', 'placeholder': '00000000'}),
            'cest': forms.TextInput(attrs={**_sm, 'maxlength': '7', 'placeholder': '0000000'}),
            'ean': forms.TextInput(attrs={**_sm, 'placeholder': 'Vazio = SEM GTIN'}),
            'origem_mercadoria': forms.Select(attrs=_sm_sel, choices=ORIGEM_CHOICES),
            'cfop': forms.TextInput(attrs={**_sm, 'placeholder': '5102'}),
            'unidade': forms.TextInput(attrs={**_sm, 'placeholder': 'UN'}),
            'quantidade': forms.NumberInput(attrs=_sm_num4),
            'valor_unitario': forms.NumberInput(attrs=_sm_num4),
            'valor_desconto': forms.NumberInput(attrs=_sm_num),
            # Unidade Tributável (exportação)
            'quantidade_tributavel':     forms.NumberInput(attrs=_sm_num4),
            'unidade_tributavel':        forms.TextInput(attrs={**_sm, 'placeholder': 'KG', 'style': 'width:55px'}),
            'valor_unitario_tributavel': forms.NumberInput(attrs=_sm_num4),
            # ICMS
            'cst_icms': forms.TextInput(attrs={**_sm, 'placeholder': '000', 'style': 'width:60px'}),
            'icms_modalidade_base': forms.Select(attrs=_sm_sel, choices=MODALIDADE_BC_ICMS_CHOICES),
            'icms_reducao_base': forms.NumberInput(attrs={**_sm_num, 'placeholder': '0.00'}),
            'aliquota_icms': forms.NumberInput(attrs=_sm_num),
            # ICMS ST
            'icms_st_aliquota': forms.NumberInput(attrs=_sm_num),
            'icms_st_mva': forms.NumberInput(attrs=_sm_num),
            'icms_st_reducao_base': forms.NumberInput(attrs=_sm_num),
            # IPI
            'cst_ipi': forms.Select(attrs=_sm_sel, choices=CST_IPI_CHOICES),
            'aliquota_ipi': forms.NumberInput(attrs=_sm_num),
            'ipi_codigo_enquadramento': forms.TextInput(attrs={**_sm, 'placeholder': '999', 'style': 'width:60px'}),
            # PIS / COFINS
            'cst_pis': forms.TextInput(attrs={**_sm, 'placeholder': '07', 'style': 'width:55px'}),
            'aliquota_pis': forms.NumberInput(attrs=_sm_num),
            'natureza_receita_pis': forms.TextInput(attrs={**_sm, 'placeholder': 'ex: 116',
                                                           'maxlength': '3', 'style': 'width:70px',
                                                           'title': 'Natureza da Receita PIS (3 dígitos)'}),
            'cst_cofins': forms.TextInput(attrs={**_sm, 'placeholder': '07', 'style': 'width:55px'}),
            'aliquota_cofins': forms.NumberInput(attrs=_sm_num),
            'natureza_receita_cofins': forms.TextInput(attrs={**_sm, 'placeholder': 'ex: 116',
                                                              'maxlength': '3', 'style': 'width:70px',
                                                              'title': 'Natureza da Receita COFINS (3 dígitos)'}),
            # DI - Declaração de Importação
            'di_numero':             forms.TextInput(attrs={**_sm, 'placeholder': '24/1234567-8', 'maxlength': '12'}),
            'di_data_registro':      forms.DateInput(attrs={**_sm, 'type': 'date'}, format='%Y-%m-%d'),
            'di_local_desembaraco':  forms.TextInput(attrs={**_sm, 'placeholder': 'Ex: Porto de Fortaleza'}),
            'di_uf_desembaraco':     forms.TextInput(attrs={**_sm, 'maxlength': '2', 'placeholder': 'CE',
                                                            'style': 'width:55px; text-transform:uppercase;'}),
            'di_data_desembaraco':   forms.DateInput(attrs={**_sm, 'type': 'date'}, format='%Y-%m-%d'),
            'di_via_transporte':     forms.Select(attrs=_sm_sel),
            'di_valor_afrmm':        forms.NumberInput(attrs=_sm_num),
            'di_tipo_intermediario': forms.Select(attrs=_sm_sel),
            'di_cnpj_adquirente':    forms.TextInput(attrs={**_sm, 'maxlength': '14', 'placeholder': 'Somente dígitos'}),
            'di_codigo_exportador':  forms.TextInput(attrs={**_sm, 'placeholder': 'Código do exportador'}),
            'di_numero_adicao':      forms.TextInput(attrs={**_sm, 'maxlength': '3', 'placeholder': '1',
                                                            'style': 'width:60px;'}),
            'di_codigo_fabricante':  forms.TextInput(attrs={**_sm, 'placeholder': 'Código do fabricante'}),
            'di_desconto_adicao':    forms.NumberInput(attrs=_sm_num),
            'di_numero_drawback':    forms.TextInput(attrs={**_sm, 'maxlength': '20',
                                                            'placeholder': 'Nº ato concessório drawback'}),
        }


ItemNotaFiscalFormSet = inlineformset_factory(
    NotaFiscal,
    ItemNotaFiscal,
    form=ItemNotaFiscalForm,
    extra=0,
    can_delete=True,
    min_num=1,
    validate_min=True,
)


class PagamentoNFForm(forms.ModelForm):
    class Meta:
        model = PagamentoNF
        fields = ['meio_pagamento', 'valor']
        widgets = {
            'meio_pagamento': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'valor': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01'}),
        }


PagamentoNFFormSet = inlineformset_factory(
    NotaFiscal, PagamentoNF,
    form=PagamentoNFForm,
    extra=0, can_delete=True, min_num=0,
)


class DuplicataNFForm(forms.ModelForm):
    class Meta:
        model = DuplicataNF
        fields = ['numero', 'vencimento', 'valor']
        widgets = {
            'numero': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': '001'}),
            'vencimento': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}, format='%Y-%m-%d'),
            'valor': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01'}),
        }


DuplicataNFFormSet = inlineformset_factory(
    NotaFiscal, DuplicataNF,
    form=DuplicataNFForm,
    extra=0, can_delete=True, min_num=0,
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
            'uf_inicio', 'municipio_inicio', 'codigo_municipio_inicio',
            'uf_fim', 'municipio_fim', 'codigo_municipio_fim',
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
            'uf_inicio':                 forms.TextInput(attrs={'class': 'form-control', 'maxlength': '2', 'placeholder': 'RN'}),
            'municipio_inicio':          forms.TextInput(attrs={'class': 'form-control'}),
            'codigo_municipio_inicio':   forms.TextInput(attrs={'class': 'form-control', 'maxlength': '7', 'placeholder': '7 dígitos'}),
            'uf_fim':                    forms.TextInput(attrs={'class': 'form-control', 'maxlength': '2', 'placeholder': 'SP'}),
            'municipio_fim':             forms.TextInput(attrs={'class': 'form-control'}),
            'codigo_municipio_fim':      forms.TextInput(attrs={'class': 'form-control', 'maxlength': '7', 'placeholder': '7 dígitos'}),
            'modalidade_frete':  forms.Select(attrs={'class': 'form-select'}),
            'valor_servico':     forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'valor_carga':       forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'peso_bruto_kg':     forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'observacoes':       forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, empresa=empresa, **kwargs)
        if empresa:
            from cadastros.models import Cliente, Transportadora
            from frota.models import Motorista, Vehicle
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
            from frota.models import Motorista, Vehicle
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
    extra=0, can_delete=True, min_num=1, validate_min=True,
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
