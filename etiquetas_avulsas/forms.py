from django import forms

from .models import EtiquetaAvulsa, LoteEtiquetaAvulsa


class LoteEtiquetaAvulsaForm(forms.ModelForm):
    class Meta:
        model = LoteEtiquetaAvulsa
        fields = [
            'safra', 'safra_texto',
            'fazenda', 'fazenda_texto',
            'cliente', 'cliente_texto', 'cliente_final_texto',
            'porto_origem', 'porto_origem_texto',
            'porto_destino', 'porto_destino_texto',
            'navio', 'navio_texto',
            'produto', 'produto_texto', 'cultura',
            'variedade', 'embalagem', 'marca', 'cultivares', 'tipo_size',
            'temperatura', 'carimbo',
            'caixas_por_pallet', 'peso_liquido_cx', 'peso_bruto_cx',
            'total_pallets', 'comentarios',
        ]
        widgets = {
            'safra': forms.Select(attrs={'class': 'form-select'}),
            'safra_texto': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 202526 (se não cadastrada)'}),
            'fazenda': forms.Select(attrs={'class': 'form-select'}),
            'fazenda_texto': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome da fazenda (se não cadastrada)'}),
            'cliente': forms.Select(attrs={'class': 'form-select'}),
            'cliente_texto': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Importador (se não cadastrado)'}),
            'cliente_final_texto': forms.TextInput(attrs={'class': 'form-control'}),
            'porto_origem': forms.Select(attrs={'class': 'form-select'}),
            'porto_origem_texto': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Porto de origem (se não cadastrado)'}),
            'porto_destino': forms.Select(attrs={'class': 'form-select'}),
            'porto_destino_texto': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Porto de destino (se não cadastrado)'}),
            'navio': forms.Select(attrs={'class': 'form-select'}),
            'navio_texto': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Navio (se não cadastrado)'}),
            'produto': forms.Select(attrs={'class': 'form-select'}),
            'produto_texto': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Produto (se não cadastrado)'}),
            'cultura': forms.Select(attrs={'class': 'form-select'}),
            'variedade': forms.TextInput(attrs={'class': 'form-control'}),
            'embalagem': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 10 KG'}),
            'marca': forms.TextInput(attrs={'class': 'form-control'}),
            'cultivares': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo_size': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 06'}),
            'temperatura': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 10'}),
            'carimbo': forms.TextInput(attrs={'class': 'form-control'}),
            'caixas_por_pallet': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'peso_liquido_cx': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'peso_bruto_cx': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'total_pallets': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'comentarios': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empresa = empresa
        if empresa:
            from cadastros.models import Cliente, Cultura, Fazenda, Navio, Porto, Safra
            from produtos.models import Produto
            self.fields['safra'].queryset = Safra.objects.filter(
                fazenda__empresa=empresa).select_related('cultura', 'fazenda').order_by('-ano', 'nome')
            self.fields['fazenda'].queryset = Fazenda.objects.filter(empresa=empresa, ativa=True).order_by('nome')
            self.fields['cliente'].queryset = Cliente.objects.filter(empresa=empresa, status='ATIVO').order_by('razao_social')
            self.fields['porto_origem'].queryset = Porto.objects.filter(empresa=empresa, ativo=True).order_by('nome')
            self.fields['porto_destino'].queryset = Porto.objects.filter(empresa=empresa, ativo=True).order_by('nome')
            self.fields['navio'].queryset = Navio.objects.filter(empresa=empresa).order_by('nome')
            self.fields['produto'].queryset = Produto.objects.filter(categoria__empresa=empresa, ativo=True).order_by('nome')
            self.fields['cultura'].queryset = Cultura.objects.filter(empresa=empresa).order_by('nome')

        # Todas as FKs de cadastro são opcionais — o texto livre é o fallback.
        for campo in ('safra', 'fazenda', 'cliente', 'porto_origem', 'porto_destino', 'navio', 'produto', 'cultura'):
            self.fields[campo].required = False
        for campo in (
            'safra_texto', 'fazenda_texto', 'cliente_texto', 'cliente_final_texto',
            'porto_origem_texto', 'porto_destino_texto', 'navio_texto', 'produto_texto',
            'variedade', 'embalagem', 'marca', 'cultivares', 'tipo_size',
            'temperatura', 'carimbo', 'comentarios', 'peso_liquido_cx', 'peso_bruto_cx',
        ):
            self.fields[campo].required = False

    def clean(self):
        cleaned = super().clean()
        total_pallets = cleaned.get('total_pallets')
        if total_pallets is not None and total_pallets < 1:
            self.add_error('total_pallets', 'Informe pelo menos 1 pallet.')
        caixas = cleaned.get('caixas_por_pallet')
        if caixas is not None and caixas < 1:
            self.add_error('caixas_por_pallet', 'Deve haver pelo menos 1 caixa por pallet.')
        return cleaned


class EtiquetaAvulsaEditForm(forms.ModelForm):
    """Edição pontual de um pallet já gerado (ex: corrigir a quantidade de caixas)."""

    class Meta:
        model = EtiquetaAvulsa
        fields = ['caixas']
        widgets = {
            'caixas': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
        }

    def clean_caixas(self):
        caixas = self.cleaned_data.get('caixas')
        if caixas is not None and caixas < 1:
            raise forms.ValidationError('Deve haver pelo menos 1 caixa.')
        return caixas
