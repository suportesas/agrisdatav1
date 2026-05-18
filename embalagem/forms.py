from django import forms
from .models import TipoEmbalagem, OrdemEmbalagem, RomaneioVenda


class TipoEmbalagemForm(forms.ModelForm):
    class Meta:
        model = TipoEmbalagem
        fields = [
            'produto', 'cultura', 'nome', 'variedade', 'marca', 'tipo_calibre',
            'peso_liquido_cx', 'peso_bruto_cx', 'caixas_por_pallet', 'peso_pallet_vazio', 'ativo',
        ]
        widgets = {
            'produto': forms.Select(attrs={'class': 'form-select'}),
            'cultura': forms.Select(attrs={'class': 'form-select'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'variedade': forms.TextInput(attrs={'class': 'form-control'}),
            'marca': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo_calibre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 2, 3, 14'}),
            'peso_liquido_cx': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'peso_bruto_cx': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'caixas_por_pallet': forms.NumberInput(attrs={'class': 'form-control'}),
            'peso_pallet_vazio': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empresa = empresa
        if empresa:
            from produtos.models import Produto
            from cadastros.models import Cultura
            self.fields['produto'].queryset = Produto.objects.filter(categoria__empresa=empresa, ativo=True).order_by('nome')
            self.fields['cultura'].queryset = Cultura.objects.filter(empresa=empresa).order_by('nome')
        self.fields['produto'].required = False
        self.fields['cultura'].required = False


class OrdemEmbalagemForm(forms.ModelForm):
    class Meta:
        model = OrdemEmbalagem
        fields = [
            'data', 'tipo_embalagem', 'lote_origem', 'quantidade_entrada_kg',
            'armazem_destino', 'local_destino', 'responsavel', 'observacoes',
        ]
        widgets = {
            'data': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'tipo_embalagem': forms.Select(attrs={'class': 'form-select'}),
            'lote_origem': forms.Select(attrs={'class': 'form-select'}),
            'quantidade_entrada_kg': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
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
        self.fields['local_destino'].required = False
        self.fields['responsavel'].required = False


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
