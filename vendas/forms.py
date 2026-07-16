from django import forms
from django.forms import inlineformset_factory
from core.widgets import MoneyBRInput, DecimalBRInput
from .models import PedidoVenda, ItemPedidoVenda, TabelaPreco


class PedidoVendaForm(forms.ModelForm):
    class Meta:
        model = PedidoVenda
        fields = [
            'cliente', 'vendedor', 'data_pedido', 'data_entrega_prevista',
            'tipo_venda', 'moeda', 'taxa_cambio',
            'natureza_operacao', 'condicao_pagamento', 'forma_pagamento',
            'valor_desconto', 'valor_frete',
            'gerar_nota_fiscal', 'gerar_conta_receber',
            'observacoes', 'observacoes_fiscais',
        ]
        widgets = {
            'cliente': forms.Select(attrs={'class': 'form-select'}),
            'vendedor': forms.Select(attrs={'class': 'form-select'}),
            'data_pedido': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_entrega_prevista': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'tipo_venda': forms.Select(attrs={'class': 'form-select', 'id': 'id_tipo_venda'}),
            'moeda': forms.Select(attrs={'class': 'form-select'}),
            'taxa_cambio': DecimalBRInput(decimals=4),
            'natureza_operacao': forms.TextInput(attrs={'class': 'form-control'}),
            'condicao_pagamento': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 30/60/90 dias'}),
            'forma_pagamento': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Boleto, TED, Wire Transfer'}),
            'valor_desconto': MoneyBRInput(),
            'valor_frete': MoneyBRInput(),
            'gerar_nota_fiscal': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'gerar_conta_receber': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'observacoes_fiscais': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        if empresa:
            from cadastros.models import Cliente
            from usuarios.models import Usuario
            self.fields['cliente'].queryset = Cliente.objects.filter(empresa=empresa, status='ATIVO')
            self.fields['vendedor'].queryset = Usuario.objects.filter(empresa=empresa, is_active=True)
        self.fields['vendedor'].required = False
        self.fields['taxa_cambio'].required = False
        self.fields['data_entrega_prevista'].required = False


class ItemPedidoVendaForm(forms.ModelForm):
    class Meta:
        model = ItemPedidoVenda
        fields = ['produto', 'descricao', 'ncm', 'cfop', 'unidade', 'quantidade', 'preco_unitario', 'desconto_item']
        widgets = {
            'produto': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'descricao': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'ncm': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': '00000000'}),
            'cfop': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': '5102'}),
            'unidade': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'UN'}),
            'quantidade': DecimalBRInput(attrs={'class': 'form-control-sm'}, decimals=3),
            'preco_unitario': DecimalBRInput(attrs={'class': 'form-control-sm'}, decimals=4),
            'desconto_item': MoneyBRInput(attrs={'class': 'form-control-sm'}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        if empresa:
            from produtos.models import Produto
            self.fields['produto'].queryset = Produto.objects.filter(categoria__empresa=empresa, ativo=True).order_by('nome')
        self.fields['produto'].required = False
        self.fields['ncm'].required = False
        self.fields['cfop'].required = False
        self.fields['desconto_item'].required = False


ItemPedidoVendaFormSet = inlineformset_factory(
    PedidoVenda,
    ItemPedidoVenda,
    form=ItemPedidoVendaForm,
    extra=1,
    min_num=1,
    can_delete=True,
)


class TabelaPrecoForm(forms.ModelForm):
    class Meta:
        model = TabelaPreco
        fields = [
            'cliente', 'produto', 'porto_destino', 'moeda', 'preco_unitario',
            'vigencia_inicio', 'vigencia_fim', 'ativo', 'observacoes',
        ]
        widgets = {
            'cliente': forms.Select(attrs={'class': 'form-select'}),
            'produto': forms.Select(attrs={'class': 'form-select'}),
            'porto_destino': forms.Select(attrs={'class': 'form-select'}),
            'moeda': forms.Select(attrs={'class': 'form-select'}),
            'preco_unitario': DecimalBRInput(decimals=4),
            'vigencia_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'vigencia_fim': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        self.empresa = empresa
        super().__init__(*args, **kwargs)
        if empresa:
            from cadastros.models import Cliente, Porto
            from produtos.models import Produto
            self.fields['cliente'].queryset = Cliente.objects.filter(empresa=empresa, status='ATIVO').order_by('razao_social')
            self.fields['produto'].queryset = Produto.objects.filter(categoria__empresa=empresa, ativo=True).order_by('nome')
            self.fields['porto_destino'].queryset = Porto.objects.filter(empresa=empresa, ativo=True).order_by('nome')
        self.fields['cliente'].required = False
        self.fields['porto_destino'].required = False

    def clean(self):
        cleaned = super().clean()
        instance = self.instance
        instance.empresa = self.empresa
        for field in ('cliente', 'produto', 'porto_destino', 'moeda', 'vigencia_inicio', 'vigencia_fim'):
            if field in cleaned:
                setattr(instance, field, cleaned[field])
        try:
            instance.clean()
        except forms.ValidationError as exc:
            if hasattr(exc, 'error_dict'):
                for field, errors in exc.error_dict.items():
                    for error in errors:
                        self.add_error(field if field in self.fields else None, error)
            else:
                raise
        return cleaned
