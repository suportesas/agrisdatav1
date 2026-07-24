from django import forms
from django.urls import reverse_lazy

from core.widgets import Select2AjaxWidget
from .models import EtiquetaAvulsa, LoteEtiquetaAvulsa


class CulturaVariedadeSelect(forms.Select):
    """Adiciona data-variedade em cada <option> para o JS auto-preencher o
    campo Variedade quando o usuário troca de Cultura (o valor continua
    livremente editável depois)."""

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        if value:
            from cadastros.models import Cultura
            try:
                real_value = value.value if hasattr(value, 'value') else value
                cultura = Cultura.objects.get(pk=real_value)
                option['attrs']['data-variedade'] = cultura.variedade or ''
            except (Cultura.DoesNotExist, ValueError, TypeError):
                pass
        return option


class LoteEtiquetaAvulsaForm(forms.ModelForm):
    """Dados da carga como um todo — fixos para todos os pallets do lote,
    independente de quantas levas de produto diferente forem adicionadas."""

    class Meta:
        model = LoteEtiquetaAvulsa
        fields = [
            'safra', 'safra_texto',
            'fazenda', 'fazenda_texto',
            'cliente', 'cliente_texto', 'cliente_final_texto',
            'porto_origem', 'porto_origem_texto',
            'porto_destino', 'porto_destino_texto',
            'navio', 'navio_texto',
            'comentarios',
        ]
        widgets = {
            'safra': forms.Select(attrs={'class': 'form-select'}),
            'safra_texto': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 202526 (se não cadastrada)'}),
            'fazenda': Select2AjaxWidget(ajax_url=reverse_lazy('cadastros:ajax_buscar_fazendas'), placeholder='Buscar fazenda...'),
            'fazenda_texto': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome da fazenda (se não cadastrada)'}),
            'cliente': Select2AjaxWidget(ajax_url=reverse_lazy('cadastros:ajax_buscar_clientes'), placeholder='Buscar cliente...'),
            'cliente_texto': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Importador (se não cadastrado)'}),
            'cliente_final_texto': forms.TextInput(attrs={'class': 'form-control'}),
            'porto_origem': forms.Select(attrs={'class': 'form-select'}),
            'porto_origem_texto': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Porto de origem (se não cadastrado)'}),
            'porto_destino': forms.Select(attrs={'class': 'form-select'}),
            'porto_destino_texto': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Porto de destino (se não cadastrado)'}),
            'navio': forms.Select(attrs={'class': 'form-select'}),
            'navio_texto': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Navio (se não cadastrado)'}),
            'comentarios': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empresa = empresa
        if empresa:
            from cadastros.models import Cliente, Fazenda, Navio, Porto, Safra
            self.fields['safra'].queryset = Safra.objects.filter(
                fazenda__empresa=empresa).select_related('fazenda').order_by('-ano', 'nome')
            self.fields['fazenda'].queryset = Fazenda.objects.filter(empresa=empresa, ativa=True).order_by('nome')
            self.fields['cliente'].queryset = Cliente.objects.filter(empresa=empresa, status='ATIVO').order_by('razao_social')
            self.fields['porto_origem'].queryset = Porto.objects.filter(empresa=empresa, ativo=True).order_by('nome')
            self.fields['porto_destino'].queryset = Porto.objects.filter(empresa=empresa, ativo=True).order_by('nome')
            self.fields['navio'].queryset = Navio.objects.filter(empresa=empresa).order_by('nome')

        # Todas as FKs de cadastro são opcionais — o texto livre é o fallback.
        for campo in ('safra', 'fazenda', 'cliente', 'porto_origem', 'porto_destino', 'navio'):
            self.fields[campo].required = False
        for campo in (
            'safra_texto', 'fazenda_texto', 'cliente_texto', 'cliente_final_texto',
            'porto_origem_texto', 'porto_destino_texto', 'navio_texto', 'comentarios',
        ):
            self.fields[campo].required = False


class ItemPalletForm(forms.ModelForm):
    """Especificação de produto + quantidade para uma leva de pallets.

    Uma carga (lote) pode ter mais de uma leva, cada uma com seu próprio
    produto — por isso esses campos vivem na EtiquetaAvulsa (por pallet), e
    este form é reaproveitado tanto na criação do lote (primeira leva)
    quanto em "Adicionar mais pallets" (levas seguintes).
    """

    quantidade = forms.IntegerField(
        label='Quantidade de Pallets', min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
    )

    class Meta:
        model = EtiquetaAvulsa
        fields = [
            'produto', 'produto_texto', 'cultura',
            'variedade', 'embalagem', 'marca', 'marca_texto', 'cultivares', 'tipo_size',
            'temperatura', 'carimbo',
            'caixas', 'peso_liquido_cx', 'peso_bruto_cx',
        ]
        labels = {'caixas': 'Caixas por Pallet'}
        widgets = {
            'produto': forms.Select(attrs={'class': 'form-select'}),
            'produto_texto': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Produto (se não cadastrado)'}),
            'cultura': CulturaVariedadeSelect(attrs={'class': 'form-select'}),
            'variedade': forms.TextInput(attrs={'class': 'form-control'}),
            'embalagem': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 10 KG'}),
            'marca': forms.Select(attrs={'class': 'form-select'}),
            'marca_texto': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Marca (se não cadastrada)'}),
            'cultivares': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo_size': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 06'}),
            'temperatura': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 10'}),
            'carimbo': forms.TextInput(attrs={'class': 'form-control'}),
            'caixas': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'peso_liquido_cx': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'peso_bruto_cx': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empresa = empresa
        if empresa:
            from cadastros.models import Cultura
            from produtos.models import Marca, Produto
            self.fields['produto'].queryset = Produto.objects.filter(categoria__empresa=empresa, ativo=True).order_by('nome')
            self.fields['cultura'].queryset = Cultura.objects.filter(empresa=empresa).order_by('nome')
            self.fields['marca'].queryset = Marca.objects.filter(empresa=empresa, ativo=True).order_by('nome')
        self.fields['produto'].required = False
        self.fields['cultura'].required = False
        self.fields['marca'].required = False
        for campo in (
            'produto_texto', 'variedade', 'embalagem', 'marca_texto', 'cultivares',
            'tipo_size', 'temperatura', 'carimbo', 'peso_liquido_cx', 'peso_bruto_cx',
        ):
            self.fields[campo].required = False

    def clean_caixas(self):
        caixas = self.cleaned_data.get('caixas')
        if caixas is not None and caixas < 1:
            raise forms.ValidationError('Deve haver pelo menos 1 caixa por pallet.')
        return caixas

    def item_data(self):
        """Dict pronto para `services.criar_lote_com_etiquetas`/`adicionar_pallets`."""
        campos = (
            'produto', 'produto_texto', 'cultura', 'variedade', 'embalagem', 'marca', 'marca_texto',
            'cultivares', 'tipo_size', 'temperatura', 'carimbo', 'peso_liquido_cx', 'peso_bruto_cx',
        )
        data = {campo: self.cleaned_data.get(campo) for campo in campos}
        data['caixas_por_pallet'] = self.cleaned_data['caixas']
        return data


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
