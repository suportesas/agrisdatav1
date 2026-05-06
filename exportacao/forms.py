from django import forms
from .models import Booking, BookingContainer, OrdemColeta, SolicitacaoBooking
from cadastros.models import Armador, Cultura, Navio, Porto, Transportadora


class ExportacaoBaseForm(forms.ModelForm):
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


class SolicitacaoBookingForm(ExportacaoBaseForm):
    class Meta:
        model = SolicitacaoBooking
        fields = [
            'nome',
            'cultura',
            'data_prevista_embarque',
            'quantidade',
            'porto_origem',
            'porto_destino',
            'armador',
            'navio',
            'frete',
            'genset',
            'status',
            'observacoes',
        ]
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '202526 - SM19'}),
            'cultura': forms.Select(attrs={'class': 'form-select'}),
            'data_prevista_embarque': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'quantidade': forms.NumberInput(attrs={'class': 'form-control', 'step': '1'}),
            'porto_origem': forms.Select(attrs={'class': 'form-select'}),
            'porto_destino': forms.Select(attrs={'class': 'form-select'}),
            'armador': forms.Select(attrs={'class': 'form-select'}),
            'navio': forms.Select(attrs={'class': 'form-select'}),
            'frete': forms.Select(attrs={'class': 'form-select'}),
            'genset': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['frete'].initial = 'FREIGHT_COLLECT'
        if self.empresa:
            self.fields['cultura'].queryset = Cultura.objects.filter(empresa=self.empresa).order_by('nome')
            self.fields['porto_origem'].queryset = Porto.objects.filter(empresa=self.empresa, ativo=True).order_by('nome')
            self.fields['porto_destino'].queryset = Porto.objects.filter(empresa=self.empresa, ativo=True).order_by('nome')
            self.fields['armador'].queryset = Armador.objects.filter(empresa=self.empresa, ativo=True).order_by('nome')
            self.fields['navio'].queryset = Navio.objects.filter(empresa=self.empresa, ativo=True).order_by('nome')


class BookingForm(ExportacaoBaseForm):
    class Meta:
        model = Booking
        fields = [
            'solicitacao',
            'codigo',
            'tipo_exportacao',
            'transportadora',
            'porto_origem',
            'porto_destino',
            'data_embarque_previsto',
            'data_embarque_realizado',
            'status',
            'valor_fob',
            'observacoes',
        ]
        widgets = {
            'solicitacao': forms.Select(attrs={'class': 'form-select'}),
            'codigo': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo_exportacao': forms.Select(attrs={'class': 'form-select'}),
            'transportadora': forms.Select(attrs={'class': 'form-select'}),
            'porto_origem': forms.Select(attrs={'class': 'form-select'}),
            'porto_destino': forms.Select(attrs={'class': 'form-select'}),
            'data_embarque_previsto': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_embarque_realizado': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'valor_fob': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.empresa:
            self.fields['solicitacao'].queryset = SolicitacaoBooking.objects.filter(empresa=self.empresa).order_by('-data_solicitacao')
            self.fields['transportadora'].queryset = Transportadora.objects.filter(empresa=self.empresa).order_by('razao_social')
            self.fields['porto_origem'].queryset = Porto.objects.filter(empresa=self.empresa, ativo=True).order_by('nome')
            self.fields['porto_destino'].queryset = Porto.objects.filter(empresa=self.empresa, ativo=True).order_by('nome')


class BookingContainerForm(ExportacaoBaseForm):
    class Meta:
        model = BookingContainer
        fields = [
            'booking',
            'numero_container',
            'tipo_container',
            'status',
            'cultura',
            'peso_bruto_kg',
            'lacre_armador',
            'lacre_fiscal',
            'lacre_terminal',
            'porto_origem',
            'porto_destino',
            'data_coleta_prevista',
            'data_coleta_realizada',
            'observacoes',
        ]
        widgets = {
            'booking': forms.Select(attrs={'class': 'form-select'}),
            'numero_container': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo_container': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'cultura': forms.Select(attrs={'class': 'form-select'}),
            'peso_bruto_kg': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'lacre_armador': forms.TextInput(attrs={'class': 'form-control'}),
            'lacre_fiscal': forms.TextInput(attrs={'class': 'form-control'}),
            'lacre_terminal': forms.TextInput(attrs={'class': 'form-control'}),
            'porto_origem': forms.Select(attrs={'class': 'form-select'}),
            'porto_destino': forms.Select(attrs={'class': 'form-select'}),
            'data_coleta_prevista': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_coleta_realizada': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.empresa:
            self.fields['booking'].queryset = Booking.objects.filter(empresa=self.empresa).order_by('-data_embarque_previsto')
            self.fields['cultura'].queryset = Cultura.objects.filter(empresa=self.empresa).order_by('nome')
            self.fields['porto_origem'].queryset = Porto.objects.filter(empresa=self.empresa, ativo=True).order_by('nome')
            self.fields['porto_destino'].queryset = Porto.objects.filter(empresa=self.empresa, ativo=True).order_by('nome')


class OrdemColetaForm(ExportacaoBaseForm):
    class Meta:
        model = OrdemColeta
        fields = [
            'booking',
            'container',
            'numero',
            'endereco_coleta',
            'responsavel_coleta',
            'data_prevista',
            'data_realizada',
            'status',
            'documento',
            'observacoes',
        ]
        widgets = {
            'booking': forms.Select(attrs={'class': 'form-select'}),
            'container': forms.Select(attrs={'class': 'form-select'}),
            'numero': forms.TextInput(attrs={'class': 'form-control'}),
            'endereco_coleta': forms.TextInput(attrs={'class': 'form-control'}),
            'responsavel_coleta': forms.TextInput(attrs={'class': 'form-control'}),
            'data_prevista': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_realizada': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'documento': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.empresa:
            self.fields['booking'].queryset = Booking.objects.filter(empresa=self.empresa).order_by('-data_embarque_previsto')
            self.fields['container'].queryset = BookingContainer.objects.filter(empresa=self.empresa).order_by('numero_container')
