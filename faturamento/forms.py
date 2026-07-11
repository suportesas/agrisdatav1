from decimal import Decimal

from django import forms
from django.core.validators import MinLengthValidator
from django.forms import inlineformset_factory, BaseInlineFormSet

from .models import (
    CartaCorrecaoNFe,
    CiotMDFe,
    ComponenteValorCTe,
    CondutorMDFe,
    ContratanteMDFe,
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
    NFeReferenciada,
    NotaFiscal,
    PackingList,
    PagamentoFreteMDFe,
    PagamentoNF,
    PercursoMDFe,
    ProdutoPredominanteMDFe,
    ReboqueMDFe,
    SeguroMDFe,
    ValePedagioMDFe,
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


class DevolucaoVendaForm(forms.Form):
    """Registra a devolução (entrada de estoque) de um produto vendido.

    `produto` é restrito aos produtos presentes na NF-e/Invoice quando possível
    (ver `__init__`); para Invoice de exportação, `ItemInvoice` não referencia
    `produtos.Produto` diretamente, então o campo fica aberto a todos os
    produtos da empresa.
    """
    produto = forms.ModelChoiceField(
        label='Produto',
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    lote = forms.ModelChoiceField(
        label='Lote (opcional)',
        queryset=None,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text='Se informado, o saldo devolvido entra nesse lote específico.',
    )
    quantidade = forms.DecimalField(
        label='Quantidade Devolvida',
        min_value=Decimal('0.001'),
        max_digits=14,
        decimal_places=3,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
    )
    justificativa = forms.CharField(
        label='Justificativa da Devolução',
        min_length=15,
        max_length=500,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4,
                                     'placeholder': 'Informe o motivo da devolução (mínimo 15 caracteres)'}),
        validators=[MinLengthValidator(15)],
    )

    def __init__(self, *args, empresa=None, produtos_queryset=None, **kwargs):
        super().__init__(*args, **kwargs)
        from produtos.models import Produto
        from estoque.models import Lote
        self.fields['produto'].queryset = (
            produtos_queryset if produtos_queryset is not None
            else Produto.objects.filter(empresa=empresa)
        )
        self.fields['lote'].queryset = Lote.objects.filter(empresa=empresa) if empresa else Lote.objects.none()

    def clean(self):
        cleaned = super().clean()
        lote = cleaned.get('lote')
        produto = cleaned.get('produto')
        if lote and produto and lote.produto_id != produto.pk:
            self.add_error('lote', 'O lote selecionado não pertence ao produto escolhido.')
        return cleaned


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
            'serie_cte',
            'numero_cte_inicial',
            'serie_mdfe',
            'numero_mdfe_inicial',
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
            'serie_nfe':          forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'numero_nfe_inicial':  forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'serie_cte':          forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'numero_cte_inicial':  forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'serie_mdfe':         forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'numero_mdfe_inicial': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
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
            'fornecedor',
            'natureza_operacao',
            'finalidade_nfe',
            'data_emissao',
            'data_saida',
            'cfop',
            'presenca_comprador',
            'modalidade_frete',
            'transportadora',
            'transp_cnpj',
            'transp_nome',
            'transp_ie',
            'transp_endereco',
            'transp_municipio',
            'transp_uf',
            'transp_rntc',
            'veic_placa',
            'veic_uf',
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
            # Local de retirada
            'retirada_ativo',
            'retirada_cnpj_cpf',
            'retirada_logradouro',
            'retirada_numero',
            'retirada_complemento',
            'retirada_bairro',
            'retirada_codigo_municipio',
            'retirada_nome_municipio',
            'retirada_uf',
            # Nota de Produtor Rural (documento de origem)
            'produtor_rural_uf',
            'produtor_rural_anomes',
            'produtor_rural_cnpj',
            'produtor_rural_cpf',
            'produtor_rural_ie',
            'produtor_rural_modelo',
            'produtor_rural_serie',
            'produtor_rural_numero',
            # Agropecuário — GTA
            'gta_tipo',
            'gta_uf',
            'gta_serie',
            'gta_numero',
            # Agropecuário — Defensivo Agrícola
            'defensivo_numero_receituario',
            'defensivo_cpf_responsavel',
            # Intermediador
            'ind_intermediador',
            'intermediador_cnpj',
            'intermediador_id_cadastro',
            # Faturamento Agrupado
            'tipo_operacao',
        ]
        _fc = {'class': 'form-control form-control-sm'}
        widgets = {
            'cliente': forms.Select(attrs={'class': 'form-select'}),
            'fornecedor': forms.Select(attrs={'class': 'form-select'}),
            'natureza_operacao': forms.TextInput(attrs={'class': 'form-control'}),
            'finalidade_nfe': forms.Select(attrs={'class': 'form-select'}),
            'data_emissao': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'data_saida': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'cfop': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '5102'}),
            'presenca_comprador': forms.Select(attrs={'class': 'form-select'}),
            'modalidade_frete': forms.Select(attrs={'class': 'form-select'}),
            'transportadora': forms.Select(attrs={'class': 'form-select'}),
            'transp_cnpj':      forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'CNPJ/CPF'}),
            'transp_nome':      forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Nome/Razão Social'}),
            'transp_ie':        forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Inscrição Estadual'}),
            'transp_endereco':  forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Endereço'}),
            'transp_municipio': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Município'}),
            'transp_uf':        forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'UF', 'maxlength': '2', 'style': 'text-transform:uppercase;'}),
            'transp_rntc':      forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'RNTC'}),
            'veic_placa':       forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'AAA0000', 'maxlength': '7', 'style': 'text-transform:uppercase;'}),
            'veic_uf':          forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'UF', 'maxlength': '2', 'style': 'text-transform:uppercase;'}),
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
            # Local de retirada
            'retirada_ativo': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_retirada_ativo'}),
            'retirada_cnpj_cpf': forms.TextInput(attrs={**_fc, 'placeholder': 'Somente dígitos (CNPJ 14 / CPF 11)', 'maxlength': '14'}),
            'retirada_logradouro': forms.TextInput(attrs={**_fc, 'placeholder': 'Rua, Av., Rodovia...'}),
            'retirada_numero': forms.TextInput(attrs={**_fc, 'placeholder': 'S/N'}),
            'retirada_complemento': forms.TextInput(attrs={**_fc, 'placeholder': 'Apto, Sala, Bloco...'}),
            'retirada_bairro': forms.TextInput(attrs={**_fc, 'placeholder': 'Bairro'}),
            'retirada_codigo_municipio': forms.TextInput(attrs={**_fc, 'placeholder': '7 dígitos IBGE', 'maxlength': '7'}),
            'retirada_nome_municipio': forms.TextInput(attrs={**_fc, 'placeholder': 'Município'}),
            'retirada_uf': forms.TextInput(attrs={**_fc, 'placeholder': 'UF', 'maxlength': '2', 'style': 'text-transform:uppercase;'}),
            # Nota de Produtor Rural
            'produtor_rural_uf': forms.TextInput(attrs={**_fc, 'placeholder': 'UF', 'maxlength': '2', 'style': 'text-transform:uppercase;'}),
            'produtor_rural_anomes': forms.TextInput(attrs={**_fc, 'placeholder': 'AAMM', 'maxlength': '4'}),
            'produtor_rural_cnpj': forms.TextInput(attrs={**_fc, 'placeholder': 'CNPJ (14 dígitos)', 'maxlength': '14'}),
            'produtor_rural_cpf': forms.TextInput(attrs={**_fc, 'placeholder': 'CPF (11 dígitos)', 'maxlength': '11'}),
            'produtor_rural_ie': forms.TextInput(attrs={**_fc, 'placeholder': 'Inscrição Estadual', 'maxlength': '14'}),
            'produtor_rural_modelo': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'produtor_rural_serie': forms.TextInput(attrs={**_fc, 'maxlength': '3'}),
            'produtor_rural_numero': forms.TextInput(attrs={**_fc, 'maxlength': '9'}),
            # Agropecuário — GTA
            'gta_tipo': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'gta_uf': forms.TextInput(attrs={**_fc, 'placeholder': 'UF', 'maxlength': '2', 'style': 'text-transform:uppercase;'}),
            'gta_serie': forms.TextInput(attrs={**_fc, 'maxlength': '9'}),
            'gta_numero': forms.TextInput(attrs={**_fc, 'maxlength': '9'}),
            # Agropecuário — Defensivo Agrícola
            'defensivo_numero_receituario': forms.TextInput(attrs={**_fc, 'placeholder': 'Nº do receituário', 'maxlength': '30'}),
            'defensivo_cpf_responsavel': forms.TextInput(attrs={**_fc, 'placeholder': 'CPF do responsável técnico', 'maxlength': '11'}),
            # Intermediador
            'ind_intermediador': forms.Select(attrs={'class': 'form-select form-select-sm', 'id': 'id_ind_intermediador'}),
            'intermediador_cnpj': forms.TextInput(attrs={**_fc, 'placeholder': 'Somente dígitos (14)', 'maxlength': '14'}),
            'intermediador_id_cadastro': forms.TextInput(attrs={**_fc, 'placeholder': 'Ex: login, CPF, código na plataforma'}),
            # Documento referenciado (devolução)
            'chave_nfe_referenciada': forms.TextInput(attrs={**_fc, 'placeholder': '44 dígitos — chave da NF-e original devolvida', 'maxlength': '44'}),
            # Faturamento Agrupado
            'tipo_operacao': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, empresa=empresa, **kwargs)
        if empresa:
            from cadastros.models import Cliente, Fornecedor, Transportadora
            self.fields['cliente'].queryset = Cliente.objects.filter(empresa=empresa, status='ATIVO').order_by('razao_social')
            self.fields['fornecedor'].queryset = Fornecedor.objects.filter(empresa=empresa, ativa=True).order_by('nome')
            self.fields['transportadora'].queryset = Transportadora.objects.filter(empresa=empresa).order_by('razao_social')
            self.fields['transportadora'].required = False
            self.fields['informacoes_fisco'].required = False
        # Cliente e Fornecedor são mutuamente exclusivos — nenhum é obrigatório individualmente
        self.fields['cliente'].required = False
        self.fields['fornecedor'].required = False
        # Campos de transporte e veículo são opcionais
        for f in ('transp_cnpj', 'transp_nome', 'transp_ie', 'transp_endereco',
                  'transp_municipio', 'transp_uf', 'transp_rntc', 'veic_placa', 'veic_uf'):
            self.fields[f].required = False
        # Campos de exportação e entrega são sempre opcionais
        for f in ('embarque_uf', 'embarque_local', 'embarque_local_despacho',
                  'entrega_cnpj_cpf', 'entrega_logradouro', 'entrega_numero',
                  'entrega_complemento', 'entrega_bairro',
                  'entrega_codigo_municipio', 'entrega_nome_municipio', 'entrega_uf',
                  'retirada_cnpj_cpf', 'retirada_logradouro', 'retirada_numero',
                  'retirada_complemento', 'retirada_bairro',
                  'retirada_codigo_municipio', 'retirada_nome_municipio', 'retirada_uf',
                  'produtor_rural_uf', 'produtor_rural_anomes', 'produtor_rural_cnpj',
                  'produtor_rural_cpf', 'produtor_rural_ie', 'produtor_rural_modelo',
                  'produtor_rural_serie', 'produtor_rural_numero',
                  'gta_tipo', 'gta_uf', 'gta_serie', 'gta_numero',
                  'defensivo_numero_receituario', 'defensivo_cpf_responsavel',
                  'ind_intermediador', 'intermediador_cnpj', 'intermediador_id_cadastro'):
            self.fields[f].required = False

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get('cliente') and not cleaned.get('fornecedor'):
            raise forms.ValidationError(
                'Informe o Cliente (NF-e normal) ou o Fornecedor (NF-e de devolução de compra).'
            )
        if cleaned.get('tipo_operacao') == 'REMESSA' and not cleaned.get('cliente'):
            self.add_error('cliente', 'Cliente é obrigatório para NF-e de Remessa.')
        return cleaned


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
    # DecimalFields que têm default=0 mas não blank=True no model — tornamos opcionais no form
    _DECIMAL_ZERO_FIELDS = (
        'valor_desconto',
        # ICMS
        'icms_reducao_base', 'aliquota_icms',
        # ICMS ST
        'icms_st_aliquota', 'icms_st_mva', 'icms_st_reducao_base',
        # IPI
        'aliquota_ipi',
        # PIS / COFINS
        'aliquota_pis', 'aliquota_cofins',
        # Unidade tributável (exportação)
        'quantidade_tributavel', 'valor_unitario_tributavel',
        # DI
        'di_valor_afrmm', 'di_desconto_adicao',
        # Rateio
        'valor_frete_item', 'valor_seguro_item', 'valor_outras_despesas',
        # FCP
        'fcp_aliquota', 'fcp_st_aliquota',
        # IBS/CBS (Reforma Tributária)
        'ibs_cbs_aliquota_uf', 'ibs_cbs_aliquota_municipal', 'ibs_cbs_aliquota_cbs',
        # Crédito Presumido / Exportação Indireta
        'credito_presumido_percentual', 'credito_presumido_valor',
        'exportacao_indireta_quantidade',
    )

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._empresa = empresa
        from produtos.models import Produto
        if empresa:
            self.fields['produto'].queryset = Produto.objects.filter(
                categoria__empresa=empresa, ativo=True
            ).select_related('unidade_venda').order_by('codigo', 'nome')
            from estoque.models import Lote
            self.fields['lote'].queryset = Lote.objects.filter(
                empresa=empresa, status='DISPONIVEL'
            ).select_related('produto').order_by('produto__nome', 'numero_lote')
        else:
            self.fields['produto'].queryset = Produto.objects.none()
            from estoque.models import Lote
            self.fields['lote'].queryset = Lote.objects.none()
        self.fields['lote'].required = False
        for f in self._DECIMAL_ZERO_FIELDS:
            self.fields[f].required = False
            self.fields[f].initial = Decimal('0')

    def _get_validation_exclusions(self):
        # Exclui numero_item da checagem de unique_together — o view atribui
        # o valor correto sequencialmente antes de persistir.
        exclude = super()._get_validation_exclusions()
        exclude.add('numero_item')
        return exclude

    def clean(self):
        cleaned_data = super().clean()
        from decimal import ROUND_HALF_UP
        for f in self._DECIMAL_ZERO_FIELDS:
            if cleaned_data.get(f) is None:
                cleaned_data[f] = Decimal('0')
        # Normaliza aliquotas para no máximo 6 casas decimais (alinha com ProdutoTributacao)
        for f in ('aliquota_pis', 'aliquota_cofins'):
            val = cleaned_data.get(f)
            if val is not None:
                try:
                    cleaned_data[f] = val.quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)
                except Exception:
                    pass
        # Validação de lote obrigatório para NF de Remessa (configurável por empresa)
        nota_tipo = self.data.get('tipo_operacao')
        if nota_tipo == 'REMESSA' and not cleaned_data.get('lote'):
            empresa = self._empresa
            if empresa:
                try:
                    cfg = empresa.configuracao_fiscal
                    if cfg.remessa_lote_obrigatorio:
                        self.add_error('lote', 'Lote obrigatório para itens de NF-e de Remessa (configuração da empresa).')
                except Exception:
                    pass
        return cleaned_data

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
            # Rateio por item
            'valor_frete_item', 'valor_seguro_item', 'valor_outras_despesas',
            # Pedido de Compra
            'pedido_compra', 'item_pedido_compra',
            # Benefício Fiscal / Desoneração
            'beneficio_fiscal', 'icms_motivo_desoneracao',
            # FCP
            'fcp_aliquota', 'fcp_st_aliquota',
            # IBS/CBS (Reforma Tributária)
            'ibs_cbs_situacao_tributaria', 'ibs_cbs_classificacao_tributaria',
            'ibs_cbs_aliquota_uf', 'ibs_cbs_aliquota_municipal', 'ibs_cbs_aliquota_cbs',
            # Crédito Presumido de ICMS
            'credito_presumido_codigo_beneficio', 'credito_presumido_percentual',
            'credito_presumido_valor',
            # Exportação Indireta (via trading)
            'exportacao_indireta_numero_re', 'exportacao_indireta_chave_nfe',
            'exportacao_indireta_quantidade',
            # Complemento
            'complemento_descricao',
            # Rastreabilidade
            'lote',
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
            'di_numero':             forms.TextInput(attrs={**_sm, 'maxlength': '10',
                                                             'placeholder': '0000000000',
                                                             'title': 'Máx 10 dígitos. Drawback s/ DI real: use 0000000000'}),
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
            'di_numero_drawback':    forms.TextInput(attrs={**_sm, 'maxlength': '11',
                                                            'placeholder': 'Ex: 20220031150',
                                                            'title': 'Exatamente 11 dígitos (ato concessório drawback)'}),
            # Rateio por item
            'valor_frete_item':      forms.NumberInput(attrs=_sm_num),
            'valor_seguro_item':     forms.NumberInput(attrs=_sm_num),
            'valor_outras_despesas': forms.NumberInput(attrs=_sm_num),
            # Pedido de Compra
            'pedido_compra':         forms.TextInput(attrs={**_sm, 'maxlength': '15',
                                                            'placeholder': 'Nº do pedido'}),
            'item_pedido_compra':    forms.TextInput(attrs={**_sm, 'maxlength': '6',
                                                            'placeholder': 'Item', 'style': 'width:70px'}),
            # Benefício Fiscal / Desoneração
            'beneficio_fiscal':         forms.TextInput(attrs={**_sm, 'maxlength': '10',
                                                               'placeholder': 'Ex: PR810001'}),
            'icms_motivo_desoneracao':  forms.Select(attrs=_sm_sel),
            # FCP
            'fcp_aliquota':    forms.NumberInput(attrs=_sm_num),
            'fcp_st_aliquota': forms.NumberInput(attrs=_sm_num),
            # IBS/CBS (Reforma Tributária)
            'ibs_cbs_situacao_tributaria':      forms.Select(attrs=_sm_sel),
            'ibs_cbs_classificacao_tributaria': forms.TextInput(attrs={**_sm, 'maxlength': '6',
                                                                       'placeholder': '000001',
                                                                       'title': 'cClassTrib — 6 dígitos'}),
            'ibs_cbs_aliquota_uf':        forms.NumberInput(attrs={**_sm_num, 'step': '0.0001'}),
            'ibs_cbs_aliquota_municipal': forms.NumberInput(attrs={**_sm_num, 'step': '0.0001'}),
            'ibs_cbs_aliquota_cbs':       forms.NumberInput(attrs={**_sm_num, 'step': '0.0001'}),
            # Crédito Presumido de ICMS
            'credito_presumido_codigo_beneficio': forms.TextInput(attrs={**_sm, 'maxlength': '10',
                                                                          'placeholder': 'Ex: PR810001'}),
            'credito_presumido_percentual': forms.NumberInput(attrs={**_sm_num, 'step': '0.0001'}),
            'credito_presumido_valor':      forms.NumberInput(attrs=_sm_num),
            # Exportação Indireta (via trading)
            'exportacao_indireta_numero_re':    forms.TextInput(attrs={**_sm, 'maxlength': '12',
                                                                        'placeholder': 'Registro de Exportação'}),
            'exportacao_indireta_chave_nfe':    forms.TextInput(attrs={**_sm, 'maxlength': '44',
                                                                        'placeholder': '44 dígitos'}),
            'exportacao_indireta_quantidade':   forms.NumberInput(attrs=_sm_num4),
            # Complemento
            'complemento_descricao': forms.TextInput(attrs={**_sm, 'maxlength': '500',
                                                            'placeholder': 'Complemento para DANFE (infAdProd)'}),
            # Rastreabilidade
            'lote': forms.Select(attrs=_sm_sel),
        }


class ItemNotaFiscalBaseFormSet(BaseInlineFormSet):
    def validate_unique(self):
        # numero_item é renumerado sequencialmente pelo view antes de salvar;
        # pular a checagem de unique_together evita erros espúrios quando
        # o JS submete um numero_item que coincide com um registro existente.
        pass


ItemNotaFiscalFormSet = inlineformset_factory(
    NotaFiscal,
    ItemNotaFiscal,
    form=ItemNotaFiscalForm,
    formset=ItemNotaFiscalBaseFormSet,
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


class NFeReferenciadaForm(forms.ModelForm):
    class Meta:
        model = NFeReferenciada
        fields = ['chave_acesso_referenciada', 'numero_referenciado', 'data_emissao_referenciada']
        widgets = {
            'chave_acesso_referenciada': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': '44 dígitos da chave de acesso',
                'maxlength': '44',
            }),
            'numero_referenciado': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Nº NF',
            }),
            'data_emissao_referenciada': forms.DateInput(attrs={
                'class': 'form-control form-control-sm',
                'type': 'date',
            }, format='%Y-%m-%d'),
        }


NFeReferenciadaFormSet = inlineformset_factory(
    NotaFiscal, NFeReferenciada,
    form=NFeReferenciadaForm,
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
            'banco_nome',
            'banco_endereco',
            'banco_swift',
            'banco_iban',
            'banco_numero_conta',
            'banco_beneficiario_nome',
            'banco_correspondente_nome',
            'banco_correspondente_swift',
            'regime_drawback',
            'ato_concessorio_numero',
            'ato_concessorio_data',
            'ato_concessorio_validade',
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
            'banco_nome': forms.TextInput(attrs={'class': 'form-control'}),
            'banco_endereco': forms.TextInput(attrs={'class': 'form-control'}),
            'banco_swift': forms.TextInput(attrs={'class': 'form-control'}),
            'banco_iban': forms.TextInput(attrs={'class': 'form-control'}),
            'banco_numero_conta': forms.TextInput(attrs={'class': 'form-control'}),
            'banco_beneficiario_nome': forms.TextInput(attrs={'class': 'form-control'}),
            'banco_correspondente_nome': forms.TextInput(attrs={'class': 'form-control'}),
            'banco_correspondente_swift': forms.TextInput(attrs={'class': 'form-control'}),
            'regime_drawback': forms.Select(attrs={'class': 'form-select'}),
            'ato_concessorio_numero': forms.TextInput(attrs={'class': 'form-control'}),
            'ato_concessorio_data': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'ato_concessorio_validade': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
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
            if not self.instance.pk:
                # Snapshot dos dados bancários da empresa como sugestão inicial —
                # a Invoice pode sobrescrever, mas não muda retroativamente se os
                # dados da empresa mudarem depois de emitida.
                self.fields['banco_nome'].initial = empresa.banco_nome
                self.fields['banco_endereco'].initial = empresa.banco_endereco
                self.fields['banco_swift'].initial = empresa.banco_swift
                self.fields['banco_iban'].initial = empresa.banco_iban
                self.fields['banco_numero_conta'].initial = empresa.banco_numero_conta
                self.fields['banco_beneficiario_nome'].initial = empresa.banco_beneficiario_nome

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
            'numero_fitossanitario',
            'observacoes',
        ]
        widgets = {
            'invoice': forms.Select(attrs={'class': 'form-select'}),
            'data_emissao': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'numero_fitossanitario': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nº do Certificado Fitossanitário (MAPA)'}),
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
            'serie',
            'tipo_cte',
            'remetente', 'destinatario', 'expedidor', 'recebedor',
            'tipo_tomador', 'tomador', 'transportadora',
            'motorista', 'veiculo',
            'data_emissao', 'cfop', 'natureza_operacao', 'tipo_servico',
            'globalizado', 'referencia_despacho', 'romaneio_venda',
            'uf_inicio', 'municipio_inicio', 'codigo_municipio_inicio',
            'uf_fim', 'municipio_fim', 'codigo_municipio_fim',
            'modalidade_frete', 'valor_servico', 'valor_receber',
            'valor_aproximado_tributos', 'produto_predominante',
            'valor_carga', 'peso_bruto_kg',
            # ICMS
            'cst_icms', 'base_calculo_icms', 'reducao_base_icms',
            'aliquota_icms', 'valor_icms',
            # Partilha ICMS
            'partilha_bc_icms', 'partilha_aliq_interna_uf_fim',
            'partilha_aliq_interestadual', 'partilha_percentual_uf_fim',
            'partilha_valor_icms_uf_inicio', 'partilha_valor_icms_uf_fim',
            'partilha_percentual_fcp_uf_fim', 'partilha_valor_fcp_uf_fim',
            # Modal rodoviário
            'placa_veiculo_override', 'rntrc_override',
            # Reforma tributária
            'reforma_cst', 'reforma_classificacao',
            # Fatura
            'fatura_numero', 'fatura_valor_original', 'fatura_valor_desconto',
            'observacoes',
        ]
        _dec2 = {'class': 'form-control', 'step': '0.01', 'min': '0'}
        _dec4 = {'class': 'form-control', 'step': '0.0001', 'min': '0'}
        _pct  = {'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}
        widgets = {
            'serie':             forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'style': 'width:80px'}),
            'tipo_cte':          forms.Select(attrs={'class': 'form-select'}),
            'remetente':         forms.Select(attrs={'class': 'form-select'}),
            'destinatario':      forms.Select(attrs={'class': 'form-select'}),
            'expedidor':         forms.Select(attrs={'class': 'form-select'}),
            'recebedor':         forms.Select(attrs={'class': 'form-select'}),
            'tipo_tomador':      forms.Select(attrs={'class': 'form-select', 'id': 'id_tipo_tomador'}),
            'tomador':           forms.Select(attrs={'class': 'form-select'}),
            'transportadora':    forms.Select(attrs={'class': 'form-select'}),
            'motorista':         forms.Select(attrs={'class': 'form-select'}),
            'veiculo':           forms.Select(attrs={'class': 'form-select'}),
            'data_emissao':      forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'cfop':              forms.TextInput(attrs={'class': 'form-control', 'placeholder': '6351'}),
            'natureza_operacao': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo_servico':      forms.Select(attrs={'class': 'form-select'}),
            'globalizado':       forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_globalizado'}),
            'referencia_despacho': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número do manifesto/despacho',
                'id': 'id_referencia_despacho',
            }),
            'romaneio_venda': forms.Select(attrs={'class': 'form-select'}),
            'uf_inicio':                 forms.TextInput(attrs={'class': 'form-control', 'maxlength': '2', 'placeholder': 'SP'}),
            'municipio_inicio':          forms.TextInput(attrs={'class': 'form-control'}),
            'codigo_municipio_inicio':   forms.TextInput(attrs={'class': 'form-control', 'maxlength': '7', 'placeholder': '2408003'}),
            'uf_fim':                    forms.TextInput(attrs={'class': 'form-control', 'maxlength': '2', 'placeholder': 'MG'}),
            'municipio_fim':             forms.TextInput(attrs={'class': 'form-control'}),
            'codigo_municipio_fim':      forms.TextInput(attrs={'class': 'form-control', 'maxlength': '7', 'placeholder': '3550308'}),
            'modalidade_frete':  forms.Select(attrs={'class': 'form-select'}),
            'valor_servico':          forms.NumberInput(attrs=_dec2),
            'valor_receber':          forms.NumberInput(attrs=_dec2),
            'valor_aproximado_tributos': forms.NumberInput(attrs=_dec2),
            'produto_predominante':   forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: SOJA, MILHO'}),
            'valor_carga':            forms.NumberInput(attrs=_dec2),
            'peso_bruto_kg':          forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'min': '0'}),
            # ICMS
            'cst_icms':          forms.Select(attrs={'class': 'form-select'}),
            'base_calculo_icms': forms.NumberInput(attrs=_dec2),
            'reducao_base_icms': forms.NumberInput(attrs=_pct),
            'aliquota_icms':     forms.NumberInput(attrs=_pct),
            'valor_icms':        forms.NumberInput(attrs=_dec2),
            # Partilha ICMS
            'partilha_bc_icms':              forms.NumberInput(attrs=_dec2),
            'partilha_aliq_interna_uf_fim':  forms.NumberInput(attrs=_pct),
            'partilha_aliq_interestadual':   forms.NumberInput(attrs=_pct),
            'partilha_percentual_uf_fim':    forms.NumberInput(attrs=_pct),
            'partilha_valor_icms_uf_inicio': forms.NumberInput(attrs=_dec2),
            'partilha_valor_icms_uf_fim':    forms.NumberInput(attrs=_dec2),
            'partilha_percentual_fcp_uf_fim': forms.NumberInput(attrs=_pct),
            'partilha_valor_fcp_uf_fim':     forms.NumberInput(attrs=_dec2),
            # Modal rodoviário
            'placa_veiculo_override': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Preenchida ao selecionar o veículo'}),
            'rntrc_override': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Preenchido ao selecionar a transportadora'}),
            # Reforma tributária
            'reforma_cst':           forms.Select(attrs={'class': 'form-select'}),
            'reforma_classificacao': forms.Select(attrs={'class': 'form-select'}),
            # Fatura
            'fatura_numero':         forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 001'}),
            'fatura_valor_original': forms.NumberInput(attrs=_dec2),
            'fatura_valor_desconto': forms.NumberInput(attrs=_dec2),
            'observacoes':       forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, empresa=empresa, **kwargs)
        if empresa:
            from cadastros.models import Cliente, Transportadora
            from frota.models import Motorista, Vehicle
            from embalagem.models import RomaneioVenda
            clientes_ativos = Cliente.objects.filter(empresa=empresa, status='ATIVO').order_by('razao_social')
            self.fields['remetente'].queryset = clientes_ativos
            self.fields['destinatario'].queryset = clientes_ativos
            self.fields['expedidor'].queryset = clientes_ativos
            self.fields['recebedor'].queryset = clientes_ativos
            self.fields['tomador'].queryset = clientes_ativos
            self.fields['transportadora'].queryset = Transportadora.objects.filter(empresa=empresa).order_by('razao_social')
            self.fields['motorista'].queryset = Motorista.objects.filter(empresa=empresa, ativo=True).order_by('nome')
            self.fields['veiculo'].queryset = Vehicle.objects.filter(empresa=empresa).order_by('descricao')
            self.fields['romaneio_venda'].queryset = RomaneioVenda.objects.filter(empresa=empresa).order_by('-criado_em')
        self.fields['motorista'].required = False
        self.fields['veiculo'].required = False
        self.fields['expedidor'].required = False
        self.fields['recebedor'].required = False
        self.fields['tomador'].required = False
        self.fields['romaneio_venda'].required = False

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('tipo_tomador') == '4' and not cleaned.get('tomador'):
            self.add_error('tomador', 'Informe o Tomador quando "Tomador do Serviço" for "4 - Outros".')
        return cleaned


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
    extra=0, can_delete=True, min_num=0, validate_min=False,
)


class ComponenteValorCTeForm(forms.ModelForm):
    class Meta:
        model = ComponenteValorCTe
        fields = ['nome', 'valor']
        widgets = {
            'nome':  forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Ex: FRETE PESO, FRETE VALOR, SEC/CAT, ADEME…',
            }),
            'valor': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm text-end',
                'step': '0.01', 'min': '0',
            }),
        }


ComponenteValorCTeFormSet = inlineformset_factory(
    ConhecimentoTransporte, ComponenteValorCTe,
    form=ComponenteValorCTeForm,
    extra=1, can_delete=True, min_num=0, validate_min=False,
)


# ═══════════════════════════════════════════════════════════════════
#  MDF-e — Formulários
# ═══════════════════════════════════════════════════════════════════

class ManifestoDocumentoFiscalForm(FaturamentoBaseForm):
    class Meta:
        model = ManifestoDocumentoFiscal
        fields = [
            'serie',
            'motorista', 'veiculo',
            'data_emissao',
            'booking',
            'uf_inicio', 'municipio_carregamento', 'codigo_municipio_carregamento', 'uf_fim',
            'tipo_emitente', 'tipo_transporte', 'valor_carga', 'peso_bruto_kg',
            # Modal Rodoviário — Veículo de Tração extras
            'rntrc_veiculo', 'cod_ag_porto', 'tipo_carroceria', 'tipo_rodado',
            'placa_tracao', 'uf_tracao', 'tara_tracao_kg',
            # Proprietário/Possuidor
            'proprietario_diferente',
            'prop_tipo', 'prop_cpf_cnpj', 'prop_nome',
            'prop_ie', 'prop_uf', 'prop_rntrc', 'prop_tipo_transportador',
            # Informações adicionais
            'informacoes_fisco', 'informacoes_contribuinte',
        ]
        widgets = {
            'serie':                     forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'style': 'width:80px'}),
            'motorista':                 forms.Select(attrs={'class': 'form-select'}),
            'veiculo':                   forms.Select(attrs={'class': 'form-select', 'id': 'id_veiculo'}),
            'data_emissao':              forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'booking':                   forms.Select(attrs={'class': 'form-select'}),
            'uf_inicio':                 forms.TextInput(attrs={'class': 'form-control', 'maxlength': '2', 'placeholder': 'SP'}),
            'municipio_carregamento':         forms.TextInput(attrs={'class': 'form-control'}),
            'codigo_municipio_carregamento':  forms.TextInput(attrs={'class': 'form-control', 'maxlength': '7', 'placeholder': '7 dígitos IBGE'}),
            'uf_fim':                         forms.TextInput(attrs={'class': 'form-control', 'maxlength': '2', 'placeholder': 'MG'}),
            'tipo_emitente':             forms.Select(attrs={'class': 'form-select'}),
            'tipo_transporte':           forms.Select(attrs={'class': 'form-select'}),
            'valor_carga':               forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'peso_bruto_kg':             forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'rntrc_veiculo':             forms.TextInput(attrs={'class': 'form-control', 'maxlength': '8', 'placeholder': '00000000'}),
            'cod_ag_porto':              forms.TextInput(attrs={'class': 'form-control', 'maxlength': '8'}),
            'tipo_carroceria':           forms.Select(attrs={'class': 'form-select'}),
            'tipo_rodado':               forms.Select(attrs={'class': 'form-select'}),
            'placa_tracao':              forms.TextInput(attrs={'class': 'form-control', 'maxlength': '7', 'placeholder': 'ABC1D23', 'style': 'text-transform:uppercase;'}),
            'uf_tracao':                 forms.TextInput(attrs={'class': 'form-control', 'maxlength': '2', 'placeholder': 'UF', 'style': 'text-transform:uppercase;'}),
            'tara_tracao_kg':            forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'kg'}),
            'proprietario_diferente':    forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_proprietario_diferente'}),
            'prop_tipo':                 forms.Select(attrs={'class': 'form-select'}),
            'prop_cpf_cnpj':             forms.TextInput(attrs={'class': 'form-control', 'maxlength': '14'}),
            'prop_nome':                 forms.TextInput(attrs={'class': 'form-control', 'maxlength': '60'}),
            'prop_ie':                   forms.TextInput(attrs={'class': 'form-control', 'maxlength': '14'}),
            'prop_uf':                   forms.TextInput(attrs={'class': 'form-control', 'maxlength': '2'}),
            'prop_rntrc':                forms.TextInput(attrs={'class': 'form-control', 'maxlength': '8'}),
            'prop_tipo_transportador':   forms.Select(attrs={'class': 'form-select'}),
            'informacoes_fisco':         forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'informacoes_contribuinte':  forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        instance = kwargs.get('instance')
        super().__init__(*args, empresa=empresa, **kwargs)
        if empresa:
            from frota.models import Motorista, Vehicle
            from exportacao.models import Booking
            self.fields['motorista'].queryset = Motorista.objects.filter(empresa=empresa, ativo=True).order_by('nome')
            self.fields['veiculo'].queryset = Vehicle.objects.filter(empresa=empresa).order_by('descricao')
            self.fields['booking'].queryset = Booking.objects.filter(empresa=empresa).order_by('-data_embarque_previsto')
        self.fields['booking'].required = False
        if instance and instance.veiculo:
            if not instance.tipo_carroceria:
                self.initial.setdefault('tipo_carroceria', instance.veiculo.tipo_carroceria)
            if not instance.tipo_rodado:
                self.initial.setdefault('tipo_rodado', instance.veiculo.tipo_rodado)
            if not instance.placa_tracao:
                plates = instance.veiculo.plates.order_by('-id').first()
                self.initial.setdefault('placa_tracao', plates.placa if plates else '')
            if not instance.uf_tracao:
                self.initial.setdefault('uf_tracao', instance.veiculo.uf_licenciamento or '')
            if instance.tara_tracao_kg is None:
                self.initial.setdefault('tara_tracao_kg', instance.veiculo.tara_kg)

    def clean_veiculo(self):
        veiculo = self.cleaned_data.get('veiculo')
        if not veiculo or not self.empresa:
            return veiculo
        qs = ManifestoDocumentoFiscal.objects.filter(
            empresa=self.empresa,
            veiculo=veiculo,
            status__in=('RASCUNHO', 'EMITIDO'),
        )
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        aberto = qs.order_by('-id').first()
        if aberto:
            num = aberto.numero or 'S/N'
            raise forms.ValidationError(
                f'Este veículo já possui o MDF-e {num}/{aberto.serie} '
                f'({aberto.get_status_display()}) em aberto. '
                f'Encerre ou cancele-o antes de criar um novo manifesto.'
            )
        return veiculo


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
        fields = ['tipo', 'chave', 'municipio_descarregamento', 'codigo_municipio_descarregamento', 'cep_descarregamento']
        widgets = {
            'tipo':                              forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'chave':                             forms.TextInput(attrs={'class': 'form-control form-control-sm', 'maxlength': '44', 'placeholder': 'Chave (44 dígitos)'}),
            'municipio_descarregamento':         forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Cidade de entrega'}),
            'codigo_municipio_descarregamento':  forms.TextInput(attrs={'class': 'form-control form-control-sm', 'maxlength': '7', 'placeholder': 'Cód. IBGE (7 dígitos)'}),
            'cep_descarregamento':               forms.TextInput(attrs={'class': 'form-control form-control-sm', 'maxlength': '8', 'placeholder': 'CEP (8 dígitos)'}),
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


# ── Condutor MDF-e (pré-emissão) ────────────────────────────────────────────

class CondutorMDFeForm(forms.ModelForm):
    class Meta:
        model = CondutorMDFe
        fields = ['nome', 'cpf', 'ordem']
        widgets = {
            'nome':  forms.TextInput(attrs={'class': 'form-control form-control-sm', 'maxlength': '60', 'placeholder': 'Nome completo'}),
            'cpf':   forms.TextInput(attrs={'class': 'form-control form-control-sm', 'maxlength': '14', 'placeholder': '000.000.000-00'}),
            'ordem': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'style': 'width:70px'}),
        }


CondutorMDFeFormSet = inlineformset_factory(
    ManifestoDocumentoFiscal, CondutorMDFe,
    form=CondutorMDFeForm,
    extra=0, can_delete=True, min_num=0,
)


# ── Reboque ──────────────────────────────────────────────────────────────────

class ReboqueMDFeForm(forms.ModelForm):
    class Meta:
        model = ReboqueMDFe
        fields = [
            'placa', 'uf', 'rntrc', 'tipo_carroceria', 'tara_kg', 'renavam',
            'capacidade_kg', 'capacidade_m3',
            'prop_tipo', 'prop_cpf_cnpj', 'prop_nome', 'prop_ie',
            'prop_uf', 'prop_rntrc', 'prop_tipo_transportador',
        ]
        widgets = {
            'placa':          forms.TextInput(attrs={'class': 'form-control form-control-sm', 'maxlength': '7', 'placeholder': 'ABC1234'}),
            'uf':             forms.TextInput(attrs={'class': 'form-control form-control-sm', 'maxlength': '2'}),
            'rntrc':          forms.TextInput(attrs={'class': 'form-control form-control-sm', 'maxlength': '8'}),
            'tipo_carroceria': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'tara_kg':        forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
            'renavam':        forms.TextInput(attrs={'class': 'form-control form-control-sm', 'maxlength': '9'}),
            'capacidade_kg':  forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
            'capacidade_m3':  forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
            'prop_tipo':      forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'prop_cpf_cnpj':  forms.TextInput(attrs={'class': 'form-control form-control-sm', 'maxlength': '14'}),
            'prop_nome':      forms.TextInput(attrs={'class': 'form-control form-control-sm', 'maxlength': '60'}),
            'prop_ie':        forms.TextInput(attrs={'class': 'form-control form-control-sm', 'maxlength': '14'}),
            'prop_uf':        forms.TextInput(attrs={'class': 'form-control form-control-sm', 'maxlength': '2'}),
            'prop_rntrc':     forms.TextInput(attrs={'class': 'form-control form-control-sm', 'maxlength': '8'}),
            'prop_tipo_transportador': forms.Select(attrs={'class': 'form-select form-select-sm'}),
        }


ReboqueMDFeFormSet = inlineformset_factory(
    ManifestoDocumentoFiscal, ReboqueMDFe,
    form=ReboqueMDFeForm,
    extra=0, can_delete=True, min_num=0,
)


# ── CIOT ─────────────────────────────────────────────────────────────────────

class CiotMDFeForm(forms.ModelForm):
    class Meta:
        model = CiotMDFe
        fields = ['ciot', 'cpf_cnpj']
        widgets = {
            'ciot':     forms.TextInput(attrs={'class': 'form-control form-control-sm', 'maxlength': '20', 'placeholder': '20 dígitos'}),
            'cpf_cnpj': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'maxlength': '14', 'placeholder': 'CPF ou CNPJ'}),
        }


CiotMDFeFormSet = inlineformset_factory(
    ManifestoDocumentoFiscal, CiotMDFe,
    form=CiotMDFeForm,
    extra=0, can_delete=True, min_num=0,
)


# ── Contratantes ─────────────────────────────────────────────────────────────

class ContratanteMDFeForm(forms.ModelForm):
    class Meta:
        model = ContratanteMDFe
        fields = ['cpf_cnpj', 'ie', 'n_contrato', 'v_contrato']
        widgets = {
            'cpf_cnpj':   forms.TextInput(attrs={'class': 'form-control form-control-sm', 'maxlength': '14', 'placeholder': 'CPF ou CNPJ'}),
            'ie':         forms.TextInput(attrs={'class': 'form-control form-control-sm', 'maxlength': '14'}),
            'n_contrato': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'maxlength': '20'}),
            'v_contrato': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01'}),
        }


ContratanteMDFeFormSet = inlineformset_factory(
    ManifestoDocumentoFiscal, ContratanteMDFe,
    form=ContratanteMDFeForm,
    extra=0, can_delete=True, min_num=0,
)


# ── Vales Pedágio ─────────────────────────────────────────────────────────────

class ValePedagioMDFeForm(forms.ModelForm):
    class Meta:
        model = ValePedagioMDFe
        fields = ['cnpj_fornecedor', 'n_compra', 'valor', 'tp_vale']
        widgets = {
            'cnpj_fornecedor': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'maxlength': '14', 'placeholder': 'CNPJ do fornecedor'}),
            'n_compra':        forms.TextInput(attrs={'class': 'form-control form-control-sm', 'maxlength': '20', 'placeholder': 'Número da compra'}),
            'valor':           forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01'}),
            'tp_vale':         forms.Select(attrs={'class': 'form-select form-select-sm'}),
        }


ValePedagioMDFeFormSet = inlineformset_factory(
    ManifestoDocumentoFiscal, ValePedagioMDFe,
    form=ValePedagioMDFeForm,
    extra=0, can_delete=True, min_num=0,
)


# ── Pagamento do Frete ────────────────────────────────────────────────────────

class PagamentoFreteMDFeForm(forms.ModelForm):
    class Meta:
        model = PagamentoFreteMDFe
        fields = ['responsavel', 'x_nome', 'cpf_cnpj', 'ind_pag', 'vr_total', 'tp_antecip', 'componentes_json']
        widgets = {
            'responsavel':      forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'x_nome':           forms.TextInput(attrs={'class': 'form-control form-control-sm', 'maxlength': '60'}),
            'cpf_cnpj':         forms.TextInput(attrs={'class': 'form-control form-control-sm', 'maxlength': '14', 'placeholder': 'CPF ou CNPJ'}),
            'ind_pag':          forms.Select(attrs={'class': 'form-select form-select-sm'},
                                             choices=[('', '---------'), ('0', '0 - À Vista'), ('1', '1 - A Prazo')]),
            'vr_total':         forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01'}),
            'tp_antecip':       forms.Select(attrs={'class': 'form-select form-select-sm'},
                                             choices=[('', '---------'), ('1', '1 - Antecipado'), ('2', '2 - Não Antecipado')]),
            'componentes_json': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 2,
                                                      'placeholder': '[{"tp_comp":"01","v_comp":100.00}]'}),
        }


PagamentoFreteMDFeFormSet = inlineformset_factory(
    ManifestoDocumentoFiscal, PagamentoFreteMDFe,
    form=PagamentoFreteMDFeForm,
    extra=0, can_delete=True, min_num=0,
)


# ── Seguro ────────────────────────────────────────────────────────────────────

class SeguroMDFeForm(forms.ModelForm):
    class Meta:
        model = SeguroMDFe
        fields = ['responsavel', 'cpf_cnpj', 'seguradora', 'cnpj_seguradora', 'n_apolice', 'n_averbacao']
        widgets = {
            'responsavel':     forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'cpf_cnpj':        forms.TextInput(attrs={'class': 'form-control form-control-sm', 'maxlength': '14', 'placeholder': 'CPF/CNPJ (só dígitos)'}),
            'seguradora':      forms.TextInput(attrs={'class': 'form-control form-control-sm', 'maxlength': '30', 'placeholder': 'Nome da Seguradora'}),
            'cnpj_seguradora': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'maxlength': '14', 'placeholder': 'CNPJ (14 dígitos)'}),
            'n_apolice':       forms.TextInput(attrs={'class': 'form-control form-control-sm', 'maxlength': '20'}),
            'n_averbacao':     forms.TextInput(attrs={'class': 'form-control form-control-sm', 'maxlength': '40'}),
        }


SeguroMDFeFormSet = inlineformset_factory(
    ManifestoDocumentoFiscal, SeguroMDFe,
    form=SeguroMDFeForm,
    extra=0, can_delete=True, min_num=0,
)


# ── Produto Predominante ──────────────────────────────────────────────────────

class ProdutoPredominanteMDFeForm(forms.ModelForm):
    class Meta:
        model = ProdutoPredominanteMDFe
        fields = ['c_prod', 'x_prod', 'tipo_carga', 'tipo_medida', 'q_carga']
        widgets = {
            'c_prod':       forms.TextInput(attrs={'class': 'form-control', 'maxlength': '20', 'placeholder': 'NCM ou código interno'}),
            'x_prod':       forms.TextInput(attrs={'class': 'form-control', 'maxlength': '120', 'placeholder': 'Descrição do produto'}),
            'tipo_carga':   forms.Select(attrs={'class': 'form-select'}),
            'tipo_medida':  forms.Select(attrs={'class': 'form-select'}),
            'q_carga':      forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
        }

    def clean(self):
        cd = super().clean()
        if not cd.get('x_prod'):
            raise forms.ValidationError(
                'Descrição do Produto (x_prod) é obrigatória.'
            )
        if not cd.get('tipo_carga'):
            raise forms.ValidationError(
                'Tipo de Carga é obrigatório.'
            )
        return cd
