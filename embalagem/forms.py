from django import forms
from django.urls import reverse_lazy
from core.widgets import Select2AjaxWidget, DateBRInput, MoneyBRInput, DecimalBRInput
from .models import (
    ItemPallet, TipoEmbalagem, TipoEmbalagemCliente, OrdemEmbalagem, RomaneioVenda,
    CargaFrete, MaterialEmbalagem, FaixaPesoCalibre,
)


class TipoEmbalagemChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.label_completo


class TipoEmbalagemMultipleChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return obj.label_completo


class TipoEmbalagemForm(forms.ModelForm):
    class Meta:
        model = TipoEmbalagem
        fields = [
            'produto', 'cultura', 'subcategoria', 'nome', 'variedade', 'marca', 'tipo_calibre',
            'peso_liquido_cx', 'peso_bruto_cx', 'caixas_por_pallet', 'peso_pallet_vazio',
            'trace_code', 'classe_categoria', 'ativo',
        ]
        widgets = {
            'produto': Select2AjaxWidget(ajax_url=reverse_lazy('produtos:ajax_buscar_produtos'), placeholder='Buscar produto...'),
            'cultura': forms.Select(attrs={'class': 'form-select'}),
            'subcategoria': forms.Select(attrs={'class': 'form-select'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'variedade': forms.TextInput(attrs={'class': 'form-control'}),
            'marca': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo_calibre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 2, 3, 14'}),
            'peso_liquido_cx': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'peso_bruto_cx': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'caixas_por_pallet': forms.NumberInput(attrs={'class': 'form-control'}),
            'peso_pallet_vazio': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'trace_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: GLO-MEL-05'}),
            'classe_categoria': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: I'}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empresa = empresa
        if empresa:
            from produtos.models import Produto, SubCategoria
            from cadastros.models import Cultura
            self.fields['produto'].queryset = Produto.objects.filter(categoria__empresa=empresa, ativo=True).order_by('nome')
            self.fields['cultura'].queryset = Cultura.objects.filter(empresa=empresa).order_by('nome')
            self.fields['subcategoria'].queryset = SubCategoria.objects.filter(
                categoria__empresa=empresa, ativo=True
            ).select_related('categoria').order_by('categoria__nome', 'nome')
        self.fields['produto'].required = False
        self.fields['cultura'].required = False
        self.fields['subcategoria'].required = False

    def clean(self):
        cleaned = super().clean()
        peso_liq = cleaned.get('peso_liquido_cx')
        peso_bruto = cleaned.get('peso_bruto_cx')
        caixas = cleaned.get('caixas_por_pallet')

        if peso_liq is not None and peso_liq <= 0:
            self.add_error('peso_liquido_cx', 'Peso líquido deve ser maior que zero.')
        if peso_bruto is not None and peso_bruto <= 0:
            self.add_error('peso_bruto_cx', 'Peso bruto deve ser maior que zero.')
        if peso_liq and peso_bruto and peso_bruto < peso_liq:
            self.add_error('peso_bruto_cx', 'Peso bruto não pode ser menor que o peso líquido.')
        if caixas is not None and caixas < 1:
            self.add_error('caixas_por_pallet', 'Deve haver pelo menos 1 caixa por pallet.')

        produto = cleaned.get('produto')
        cultura = cleaned.get('cultura')
        subcategoria = cleaned.get('subcategoria')
        if not produto and not cultura and not subcategoria:
            raise forms.ValidationError('Informe pelo menos Produto, Cultura ou Subcategoria para o tipo de embalagem.')

        return cleaned


class TipoEmbalagemClienteForm(forms.ModelForm):
    class Meta:
        model = TipoEmbalagemCliente
        fields = ['cultura', 'variedade', 'marca', 'cliente', 'codigo_ian', 'codigo_key', 'codigo_referencia', 'ativo']
        widgets = {
            'cultura': forms.Select(attrs={'class': 'form-select'}),
            'variedade': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Goldex', 'list': 'variedades-sugeridas'}),
            'marca': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Terra Brasilis', 'list': 'marcas-sugeridas'}),
            'cliente': Select2AjaxWidget(
                ajax_url=reverse_lazy('cadastros:ajax_buscar_clientes'), placeholder='Buscar cliente...',
            ),
            'codigo_ian': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 80575'}),
            'codigo_key': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 120'}),
            'codigo_referencia': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: GR007198BBR999824'}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empresa = empresa
        self.variedades_sugeridas = []
        self.marcas_sugeridas = []
        if empresa:
            from cadastros.models import Cliente, Cultura
            self.fields['cultura'].queryset = Cultura.objects.filter(
                empresa=empresa, ativa=True
            ).order_by('nome')
            self.fields['cliente'].queryset = Cliente.objects.filter(
                empresa=empresa, status='ATIVO'
            ).order_by('razao_social')
            # sugestões pra evitar cadastrar variedade/marca com grafia diferente da
            # usada no Tipo de Embalagem (o match do código IAN é por texto exato).
            self.variedades_sugeridas = sorted(set(
                TipoEmbalagem.objects.filter(empresa=empresa, ativo=True).exclude(variedade='')
                .values_list('variedade', flat=True)
            ))
            self.marcas_sugeridas = sorted(set(
                TipoEmbalagem.objects.filter(empresa=empresa, ativo=True).exclude(marca='')
                .values_list('marca', flat=True)
            ))

    def clean(self):
        cleaned = super().clean()
        cultura = cleaned.get('cultura')
        variedade = cleaned.get('variedade', '')
        marca = cleaned.get('marca', '')
        cliente = cleaned.get('cliente')
        if cultura and cliente:
            qs = TipoEmbalagemCliente.objects.filter(
                cultura=cultura, variedade=variedade, marca=marca, cliente=cliente,
            )
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error('cliente', 'Já existe um código IAN cadastrado para este produto + Cliente.')
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        if self.empresa:
            obj.empresa = self.empresa
        if commit:
            obj.save()
        return obj


class FaixaPesoCalibreForm(forms.ModelForm):
    class Meta:
        model = FaixaPesoCalibre
        fields = ['cultura', 'peso_carton', 'calibre', 'peso_minimo', 'peso_maximo', 'ativo']
        widgets = {
            'cultura': forms.Select(attrs={'class': 'form-select'}),
            'peso_carton': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'placeholder': 'Ex: 10 ou 13'}),
            'calibre': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 8'}),
            'peso_minimo': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Ex: 1,70'}),
            'peso_maximo': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Ex: 1,75'}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empresa = empresa
        if empresa:
            from cadastros.models import Cultura
            self.fields['cultura'].queryset = Cultura.objects.filter(empresa=empresa, ativa=True).order_by('nome')

    def clean(self):
        cleaned = super().clean()
        cultura = cleaned.get('cultura')
        peso_carton = cleaned.get('peso_carton')
        calibre = cleaned.get('calibre')
        peso_min = cleaned.get('peso_minimo')
        peso_max = cleaned.get('peso_maximo')
        if peso_min is not None and peso_max is not None and peso_max < peso_min:
            self.add_error('peso_maximo', 'Peso máximo não pode ser menor que o peso mínimo.')
        if cultura and peso_carton and calibre and self.empresa:
            qs = FaixaPesoCalibre.objects.filter(
                empresa=self.empresa, cultura=cultura, peso_carton=peso_carton, calibre=calibre,
            )
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error('calibre', 'Já existe uma faixa cadastrada para esta Cultura + Peso do Carton + Calibre.')
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        if self.empresa:
            obj.empresa = self.empresa
        if commit:
            obj.save()
        return obj


class MaterialEmbalagemForm(forms.ModelForm):
    class Meta:
        model = MaterialEmbalagem
        fields = ['produto', 'tipo', 'codigo_reciclagem', 'ativo']
        widgets = {
            'produto': Select2AjaxWidget(
                ajax_url=reverse_lazy('produtos:ajax_buscar_produtos'),
                placeholder='Buscar produto de embalagem...',
            ),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'codigo_reciclagem': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 20 PAP'}),
        }
        help_texts = {
            'produto': 'Cadastre o material em Produtos, na categoria de Embalagens do seu catálogo, e informe o Fornecedor Padrão lá.',
            'codigo_reciclagem': 'Ex: 20 PAP (papelão ondulado) — impresso na etiqueta de caixa junto ao aviso PPWR.',
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empresa = empresa
        if empresa:
            from produtos.models import Produto
            self.fields['produto'].queryset = Produto.objects.filter(categoria__empresa=empresa, ativo=True).order_by('nome')

    def clean_produto(self):
        # empresa não é campo do form (é setado na view), então o Django não valida
        # sozinho o unique_together (empresa, produto) — checamos manualmente aqui.
        produto = self.cleaned_data.get('produto')
        if produto and self.empresa:
            qs = MaterialEmbalagem.objects.filter(empresa=self.empresa, produto=produto)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError('Este produto já está cadastrado como material de embalagem.')
        return produto


class OrdemEmbalagemForm(forms.ModelForm):
    tipos_embalagem = TipoEmbalagemMultipleChoiceField(
        queryset=TipoEmbalagem.objects.none(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        label='Tipos de Embalagem Permitidos',
    )

    class Meta:
        model = OrdemEmbalagem
        fields = [
            'data', 'safra', 'tipos_embalagem', 'lote_origem', 'quantidade_entrada_kg',
            'capacidade_caixas_pallet', 'armazem_destino', 'local_destino', 'responsavel', 'observacoes',
        ]
        widgets = {
            'data': DateBRInput(attrs={'class': 'form-control'}, format='%Y-%m-%d'),
            'safra': forms.Select(attrs={'class': 'form-select'}),
            'lote_origem': forms.Select(attrs={'class': 'form-select'}),
            'quantidade_entrada_kg': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'capacidade_caixas_pallet': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: 98',
                'min': '1',
            }),
            'armazem_destino': forms.Select(attrs={'class': 'form-select'}),
            'local_destino': forms.Select(attrs={'class': 'form-select'}),
            'responsavel': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empresa = empresa
        if empresa:
            from estoque.models import Lote, Armazem, LocalEstocagem
            from rh.models import Funcionario
            from cadastros.models import Safra
            self.fields['safra'].queryset = Safra.objects.filter(
                fazenda__empresa=empresa).select_related('fazenda').order_by('-ano', 'nome')
            self.fields['tipos_embalagem'].queryset = TipoEmbalagem.objects.filter(
                empresa=empresa, ativo=True).order_by('nome')
            # lote_origem é o granel colhido, não o produto embalado (caixa) do
            # TipoEmbalagem — por isso o filtro é pela categoria do produto (ex:
            # "Frutas"), não pelo produto exato, que aponta para a caixa final.
            # Exclui também lotes cujo produto já É uma caixa embalada (produto
            # de algum TipoEmbalagem), para não reembalar um lote já pronto.
            produtos_embalados = TipoEmbalagem.objects.filter(
                empresa=empresa, ativo=True, produto__isnull=False
            ).values_list('produto_id', flat=True)
            categorias_embalaveis = TipoEmbalagem.objects.filter(
                empresa=empresa, ativo=True, produto__isnull=False
            ).values_list('produto__categoria_id', flat=True)
            self.fields['lote_origem'].queryset = Lote.objects.filter(
                empresa=empresa, status='DISPONIVEL', produto__categoria_id__in=categorias_embalaveis
            ).exclude(produto_id__in=produtos_embalados).select_related('produto').order_by('-data_entrada')
            self.fields['armazem_destino'].queryset = Armazem.objects.filter(
                empresa=empresa).order_by('nome')
            self.fields['local_destino'].queryset = LocalEstocagem.objects.filter(
                armazem__empresa=empresa).order_by('codigo')
            self.fields['responsavel'].queryset = Funcionario.objects.filter(
                empresa=empresa, ativo=True).order_by('nome_completo')
        self.fields['safra'].required = False
        self.fields['local_destino'].required = False
        self.fields['responsavel'].required = False
        self.fields['capacidade_caixas_pallet'].required = False

    def clean_quantidade_entrada_kg(self):
        qty = self.cleaned_data.get('quantidade_entrada_kg')
        if qty is not None and qty <= 0:
            raise forms.ValidationError('A quantidade de entrada deve ser maior que zero.')
        return qty

    def clean(self):
        cleaned = super().clean()
        tipos = cleaned.get('tipos_embalagem')
        qty = cleaned.get('quantidade_entrada_kg')
        if tipos and qty:
            menor_caixa = min(te.peso_liquido_cx for te in tipos)
            if qty < menor_caixa:
                raise forms.ValidationError(
                    f'Quantidade ({qty} kg) menor que o peso da menor caixa entre os tipos escolhidos ({menor_caixa} kg).'
                )
        return cleaned


class GerarPalletsForm(forms.Form):
    tipo_embalagem = TipoEmbalagemChoiceField(
        queryset=TipoEmbalagem.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Tipo de Embalagem',
    )
    n_pallets = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
        label='Quantidade de Pallets',
    )

    def __init__(self, *args, ordem=None, **kwargs):
        super().__init__(*args, **kwargs)
        if ordem is not None:
            self.fields['tipo_embalagem'].queryset = ordem.tipos_embalagem.all().order_by('nome')


class RomaneioVendaForm(forms.ModelForm):
    class Meta:
        model = RomaneioVenda
        fields = [
            'tipo', 'cliente', 'data', 'booking', 'container', 'observacoes',
            'carga_frete', 'metodo_icms_frete', 'percentual_reducao_bc', 'aliquota_icms_frete',
        ]
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'cliente': Select2AjaxWidget(ajax_url=reverse_lazy('cadastros:ajax_buscar_clientes'), placeholder='Buscar cliente...'),
            'data': DateBRInput(attrs={'class': 'form-control'}, format='%Y-%m-%d'),
            'booking': forms.Select(attrs={'class': 'form-select'}),
            'container': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'carga_frete': forms.Select(attrs={'class': 'form-select'}),
            'metodo_icms_frete': forms.Select(attrs={'class': 'form-select'}),
            'percentual_reducao_bc': DecimalBRInput(decimals=2),
            'aliquota_icms_frete': DecimalBRInput(decimals=2),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empresa = empresa
        if empresa:
            from cadastros.models import Cliente
            from exportacao.models import Booking, BookingContainer
            self.fields['cliente'].queryset = Cliente.objects.filter(
                empresa=empresa, status='ATIVO').order_by('razao_social')
            self.fields['booking'].queryset = Booking.objects.filter(
                empresa=empresa, status__in=['ABERTO', 'CONFIRMADO']).order_by('-data_embarque_previsto')
            self.fields['container'].queryset = BookingContainer.objects.filter(
                booking__empresa=empresa).order_by('numero_container')
            self.fields['carga_frete'].queryset = CargaFrete.objects.filter(
                empresa=empresa, ativo=True).order_by('-data_embarque')
        self.fields['booking'].required = False
        self.fields['container'].required = False
        self.fields['carga_frete'].required = False
        self.fields['metodo_icms_frete'].required = False
        self.fields['percentual_reducao_bc'].required = False
        self.fields['aliquota_icms_frete'].required = False

    def clean(self):
        cleaned = super().clean()
        tipo = cleaned.get('tipo')
        booking = cleaned.get('booking')
        if tipo == 'EXPORTACAO' and not booking:
            self.add_error('booking', 'Booking é obrigatório para romaneios de Exportação.')
        return cleaned


class CargaFreteForm(forms.ModelForm):
    class Meta:
        model = CargaFrete
        fields = [
            'transportadora', 'identificador', 'data_embarque',
            'valor_frete_total', 'quantidade_caixas_total', 'valor_pedagio_total',
            'percentual_reducao_bc_padrao', 'aliquota_icms_padrao',
        ]
        widgets = {
            'transportadora': Select2AjaxWidget(
                ajax_url=reverse_lazy('cadastros:ajax_buscar_transportadoras'), placeholder='Buscar transportadora...'
            ),
            'identificador': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Carga 28/07 - Transp. X'}),
            'data_embarque': DateBRInput(attrs={'class': 'form-control'}, format='%Y-%m-%d'),
            'valor_frete_total': MoneyBRInput(),
            'quantidade_caixas_total': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'valor_pedagio_total': MoneyBRInput(),
            'percentual_reducao_bc_padrao': DecimalBRInput(decimals=2),
            'aliquota_icms_padrao': DecimalBRInput(decimals=2),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empresa = empresa
        if empresa:
            from cadastros.models import Transportadora
            self.fields['transportadora'].queryset = Transportadora.objects.filter(
                empresa=empresa, ativa=True).order_by('razao_social')
        self.fields['identificador'].required = False
        self.fields['valor_pedagio_total'].required = False

    def clean_quantidade_caixas_total(self):
        qtd = self.cleaned_data.get('quantidade_caixas_total')
        if qtd is not None and qtd <= 0:
            raise forms.ValidationError('A quantidade de caixas deve ser maior que zero.')
        return qtd


class TrocarClienteRomaneioForm(forms.ModelForm):
    class Meta:
        model = RomaneioVenda
        fields = ['cliente', 'booking', 'container']
        widgets = {
            'cliente': Select2AjaxWidget(ajax_url=reverse_lazy('cadastros:ajax_buscar_clientes'), placeholder='Buscar cliente...'),
            'booking': forms.Select(attrs={'class': 'form-select'}),
            'container': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        if empresa:
            from cadastros.models import Cliente
            from exportacao.models import Booking, BookingContainer
            self.fields['cliente'].queryset = Cliente.objects.filter(
                empresa=empresa, status='ATIVO').order_by('razao_social')
            self.fields['booking'].queryset = Booking.objects.filter(
                empresa=empresa, status__in=['ABERTO', 'CONFIRMADO']).order_by('-data_embarque_previsto')
            self.fields['container'].queryset = BookingContainer.objects.filter(
                booking__empresa=empresa).order_by('numero_container')
        self.fields['booking'].required = False
        self.fields['container'].required = False


class ItemPalletForm(forms.ModelForm):
    tipo_embalagem = TipoEmbalagemChoiceField(
        queryset=TipoEmbalagem.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Tipo de Embalagem',
    )

    class Meta:
        model = ItemPallet
        fields = ['tipo_embalagem', 'quantidade_caixas']
        widgets = {
            'quantidade_caixas': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
        }

    def __init__(self, *args, empresa=None, ordem=None, **kwargs):
        super().__init__(*args, **kwargs)
        if ordem is not None:
            self.fields['tipo_embalagem'].queryset = ordem.tipos_embalagem.all().select_related(
                'cultura', 'produto').order_by('nome')
        elif empresa:
            self.fields['tipo_embalagem'].queryset = TipoEmbalagem.objects.filter(
                empresa=empresa, ativo=True
            ).select_related('cultura', 'produto').order_by('nome')
