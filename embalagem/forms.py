from django import forms
from .models import ItemPallet, TipoEmbalagem, OrdemEmbalagem, RomaneioVenda


class TipoEmbalagemForm(forms.ModelForm):
    class Meta:
        model = TipoEmbalagem
        fields = [
            'produto', 'cultura', 'subcategoria', 'nome', 'variedade', 'marca', 'tipo_calibre',
            'peso_liquido_cx', 'peso_bruto_cx', 'caixas_por_pallet', 'peso_pallet_vazio',
            'trace_code', 'ativo',
        ]
        widgets = {
            'produto': forms.Select(attrs={'class': 'form-select'}),
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


class OrdemEmbalagemForm(forms.ModelForm):
    class Meta:
        model = OrdemEmbalagem
        fields = [
            'data', 'safra', 'tipo_embalagem', 'lote_origem', 'quantidade_entrada_kg',
            'capacidade_caixas_pallet', 'armazem_destino', 'local_destino', 'responsavel', 'observacoes',
        ]
        widgets = {
            'data': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'safra': forms.Select(attrs={'class': 'form-select'}),
            'tipo_embalagem': forms.Select(attrs={'class': 'form-select'}),
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
            from usuarios.models import Usuario
            from cadastros.models import Safra
            self.fields['safra'].queryset = Safra.objects.filter(
                fazenda__empresa=empresa).select_related('fazenda').order_by('-ano', 'nome')
            self.fields['tipo_embalagem'].queryset = TipoEmbalagem.objects.filter(
                empresa=empresa, ativo=True).order_by('nome')
            self.fields['lote_origem'].queryset = Lote.objects.filter(
                empresa=empresa, status='DISPONIVEL').select_related('produto').order_by('-data_entrada')
            self.fields['armazem_destino'].queryset = Armazem.objects.filter(
                empresa=empresa).order_by('nome')
            self.fields['local_destino'].queryset = LocalEstocagem.objects.filter(
                armazem__empresa=empresa).order_by('codigo')
            self.fields['responsavel'].queryset = Usuario.objects.filter(
                empresa=empresa, is_active=True).order_by('first_name')
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
        te = cleaned.get('tipo_embalagem')
        qty = cleaned.get('quantidade_entrada_kg')
        if te and qty and qty < te.peso_liquido_cx:
            raise forms.ValidationError(
                f'Quantidade ({qty} kg) menor que o peso de uma caixa ({te.peso_liquido_cx} kg).'
            )
        return cleaned


class RomaneioVendaForm(forms.ModelForm):
    class Meta:
        model = RomaneioVenda
        fields = ['tipo', 'cliente', 'data', 'booking', 'container', 'observacoes']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'cliente': forms.Select(attrs={'class': 'form-select'}),
            'data': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'booking': forms.Select(attrs={'class': 'form-select'}),
            'container': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
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
        self.fields['booking'].required = False
        self.fields['container'].required = False

    def clean(self):
        cleaned = super().clean()
        tipo = cleaned.get('tipo')
        booking = cleaned.get('booking')
        if tipo == 'EXPORTACAO' and not booking:
            self.add_error('booking', 'Booking é obrigatório para romaneios de Exportação.')
        return cleaned


class TrocarClienteRomaneioForm(forms.ModelForm):
    class Meta:
        model = RomaneioVenda
        fields = ['cliente', 'booking', 'container']
        widgets = {
            'cliente': forms.Select(attrs={'class': 'form-select'}),
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
    class Meta:
        model = ItemPallet
        fields = ['tipo_embalagem', 'quantidade_caixas']
        widgets = {
            'tipo_embalagem': forms.Select(attrs={'class': 'form-select'}),
            'quantidade_caixas': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        if empresa:
            self.fields['tipo_embalagem'].queryset = TipoEmbalagem.objects.filter(
                empresa=empresa, ativo=True
            ).select_related('cultura', 'produto').order_by('nome')
