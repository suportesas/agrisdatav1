from django import forms
from django.forms import inlineformset_factory, BaseInlineFormSet
from django.utils import timezone
from core.widgets import MoneyBRInput, DecimalBRInput
from .models import AtoConcessorio, DrawbackProdutoAC, EntradaDrawback, SaidaDrawback


class AtoConcessorioForm(forms.ModelForm):
    class Meta:
        model = AtoConcessorio
        fields = (
            'numero_ac', 'tipo', 'data_inicio', 'data_vencimento',
            'data_prorrogacao', 'status', 'despachante',
            'numero_processo_siscomex', 'observacoes',
        )
        widgets = {
            'numero_ac': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 23/0001234-0'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'data_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_vencimento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_prorrogacao': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'despachante': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_processo_siscomex': forms.TextInput(attrs={'class': 'form-control'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class DrawbackProdutoACForm(forms.ModelForm):
    class Meta:
        model = DrawbackProdutoAC
        fields = (
            'tipo_produto', 'produto', 'ncm', 'descricao_mercadoria', 'unidade_medida',
            'quantidade_autorizada', 'quantidade_minima_export', 'observacoes',
        )
        widgets = {
            'tipo_produto': forms.Select(attrs={'class': 'form-select'}),
            'produto': forms.Select(attrs={'class': 'form-select'}),
            'ncm': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '00000000'}),
            'descricao_mercadoria': forms.TextInput(attrs={'class': 'form-control'}),
            'unidade_medida': forms.Select(attrs={'class': 'form-select'}),
            'quantidade_autorizada': DecimalBRInput(decimals=3),
            'quantidade_minima_export': DecimalBRInput(decimals=3),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        from produtos.models import Produto, UnidadeMedida
        qs = Produto.objects.filter(ativo=True).order_by('nome')
        if empresa:
            qs = qs.filter(categoria__empresa=empresa)
        self.fields['produto'].queryset = qs
        um_qs = UnidadeMedida.objects.order_by('sigla')
        if empresa:
            um_qs = um_qs.filter(empresa=empresa)
        self.fields['unidade_medida'].queryset = um_qs
        self.fields['quantidade_minima_export'].required = False


class DrawbackProdutoACBaseFormSet(BaseInlineFormSet):
    def __init__(self, *args, empresa=None, **kwargs):
        self.empresa = empresa
        super().__init__(*args, **kwargs)

    def get_form_kwargs(self, index):
        kwargs = super().get_form_kwargs(index)
        kwargs['empresa'] = self.empresa
        return kwargs

    def clean(self):
        super().clean()
        if any(self.errors):
            return
        restantes = [
            form for form in self.forms
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False)
        ]
        if not restantes:
            raise forms.ValidationError('Adicione ao menos um produto ao Ato Concessório.')


# extra=0: a UI de produtos é inteiramente construída via JS (botão "Adicionar
# à lista" cria os hidden inputs "produtos-N-*" dinamicamente), então o
# formset não deve pré-renderizar nenhum form vazio. min_num/validate_min do
# Django forçariam ao menos 1 form com empty_permitted=False que a JS nunca
# preenche (ela sempre começa os índices do zero) — daí a validação "ao menos
# um produto" é feita manualmente em DrawbackProdutoACBaseFormSet.clean().
DrawbackProdutoACFormSet = inlineformset_factory(
    AtoConcessorio, DrawbackProdutoAC,
    form=DrawbackProdutoACForm,
    formset=DrawbackProdutoACBaseFormSet,
    extra=0, can_delete=True,
)


class EntradaDrawbackForm(forms.ModelForm):
    class Meta:
        model = EntradaDrawback
        fields = (
            'drawback_produto', 'produto_variante', 'fornecedor',
            'numero_nf', 'serie_nf', 'data_nf', 'data_recebimento',
            'quantidade', 'valor_unitario', 'observacoes',
        )
        widgets = {
            'drawback_produto': forms.Select(attrs={'class': 'form-select'}),
            'produto_variante': forms.Select(attrs={'class': 'form-select'}),
            'fornecedor': forms.Select(attrs={'class': 'form-select'}),
            'numero_nf': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '000000'}),
            'serie_nf': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '1'}),
            'data_nf': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_recebimento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'quantidade': DecimalBRInput(decimals=3),
            'valor_unitario': DecimalBRInput(decimals=4),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, ato_concessorio=None, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        if ato_concessorio:
            # Apenas insumos (importados ou domésticos) — não produtos de exportação
            self.fields['drawback_produto'].queryset = DrawbackProdutoAC.objects.filter(
                ato_concessorio=ato_concessorio,
                tipo_produto__in=['IMPORTACAO', 'MERCADO_INTERNO'],
            ).select_related('produto', 'unidade_medida').order_by('tipo_produto', 'produto__nome')
        from produtos.models import Produto
        self.fields['produto_variante'].required = False
        self.fields['produto_variante'].empty_label = '— Produto principal (sem variante) —'
        variantes_qs = Produto.objects.filter(produto_base__isnull=False, ativo=True)
        if empresa:
            variantes_qs = variantes_qs.filter(categoria__empresa=empresa)
            from cadastros.models import Fornecedor
            self.fields['fornecedor'].queryset = Fornecedor.objects.filter(
                empresa=empresa, ativo=True
            ).order_by('nome_fantasia')
        self.fields['produto_variante'].queryset = variantes_qs.order_by('produto_base__nome', 'nome')

        hoje = timezone.now().date()
        self.fields['data_recebimento'].initial = hoje
        self.fields['data_nf'].initial = hoje

    def clean(self):
        cleaned = super().clean()
        produto_ac = cleaned.get('drawback_produto')
        quantidade = cleaned.get('quantidade')
        if produto_ac and quantidade:
            saldo = produto_ac.saldo_compra
            if self.instance.pk:
                saldo += self.instance.quantidade
            if quantidade > saldo:
                raise forms.ValidationError(
                    f'Quantidade ({quantidade}) excede o saldo disponível no AC '
                    f'para este produto ({saldo}).'
                )
        return cleaned


class SaidaDrawbackForm(forms.ModelForm):
    class Meta:
        model = SaidaDrawback
        fields = (
            'drawback_produto', 'produto_variante', 'cliente',
            'numero_nfe', 'numero_re', 'numero_due',
            'data_embarque', 'quantidade', 'valor_fob_usd', 'observacoes',
        )
        widgets = {
            'drawback_produto': forms.Select(attrs={'class': 'form-select'}),
            'produto_variante': forms.Select(attrs={'class': 'form-select'}),
            'cliente': forms.Select(attrs={'class': 'form-select'}),
            'numero_nfe': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '000000'}),
            'numero_re': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 25BR000123456-7'}),
            'numero_due': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 25BR0012345678901'}),
            'data_embarque': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'quantidade': DecimalBRInput(decimals=3),
            'valor_fob_usd': MoneyBRInput(),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, ato_concessorio=None, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        if ato_concessorio:
            # Apenas produtos de Exportação (a fruta / produto final)
            self.fields['drawback_produto'].queryset = DrawbackProdutoAC.objects.filter(
                ato_concessorio=ato_concessorio,
                tipo_produto='EXPORTACAO',
            ).select_related('produto', 'unidade_medida').order_by('produto__nome')
        from produtos.models import Produto
        self.fields['produto_variante'].required = False
        self.fields['produto_variante'].empty_label = '— Produto principal (sem variante) —'
        variantes_qs = Produto.objects.filter(produto_base__isnull=False, ativo=True)
        if empresa:
            variantes_qs = variantes_qs.filter(categoria__empresa=empresa)
            from cadastros.models import Cliente
            self.fields['cliente'].queryset = Cliente.objects.filter(
                empresa=empresa, ativo=True
            ).order_by('nome_fantasia')
        self.fields['produto_variante'].queryset = variantes_qs.order_by('produto_base__nome', 'nome')

        self.fields['data_embarque'].initial = timezone.now().date()

    def clean(self):
        cleaned = super().clean()
        produto_ac = cleaned.get('drawback_produto')
        quantidade = cleaned.get('quantidade')
        if produto_ac and quantidade:
            saldo = produto_ac.saldo_exportacao
            if self.instance.pk:
                saldo += self.instance.quantidade
            if quantidade > saldo:
                raise forms.ValidationError(
                    f'Quantidade ({quantidade}) excede o saldo autorizado para exportação '
                    f'neste produto ({saldo}). '
                    f'Autorizado: {produto_ac.quantidade_autorizada} — Já exportado: {produto_ac.quantidade_exportada}.'
                )
        return cleaned


class ImportacaoXLSXForm(forms.Form):
    TIPO_CHOICES = [
        ('entradas', 'Entradas (Compras)'),
        ('saidas', 'Saídas (Exportações)'),
    ]
    tipo = forms.ChoiceField(
        label='Tipo de Importação',
        choices=TIPO_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    arquivo = forms.FileField(
        label='Arquivo XLSX',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.xlsx,.xls',
        }),
        help_text='Use o modelo disponível para download. Formato: .xlsx ou .xls',
    )

    def clean_arquivo(self):
        arquivo = self.cleaned_data.get('arquivo')
        if arquivo:
            nome = arquivo.name.lower()
            if not (nome.endswith('.xlsx') or nome.endswith('.xls')):
                raise forms.ValidationError('Apenas arquivos .xlsx ou .xls são aceitos.')
            if arquivo.size > 5 * 1024 * 1024:  # 5 MB
                raise forms.ValidationError('O arquivo não pode ter mais de 5 MB.')
        return arquivo
