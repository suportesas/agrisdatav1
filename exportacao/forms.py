from django import forms
from .models import Booking, BookingContainer, OrdemColeta, SolicitacaoBooking
from cadastros.models import Armador, Cultura, Motorista, Navio, Porto, Transportadora


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
            'tipo_exportacao',
            'tipo_exportacao_outros',
            'status',
            'observacoes',
        ]
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '202526 - SM19'}),
            'cultura': forms.Select(attrs={'class': 'form-select'}),
            'data_prevista_embarque': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'quantidade': forms.NumberInput(attrs={'class': 'form-control', 'step': '1'}),
            'porto_origem': forms.Select(attrs={'class': 'form-select'}),
            'porto_destino': forms.Select(attrs={'class': 'form-select'}),
            'armador': forms.Select(attrs={'class': 'form-select'}),
            'navio': forms.Select(attrs={'class': 'form-select'}),
            'frete': forms.Select(attrs={'class': 'form-select'}),
            'genset': forms.Select(attrs={'class': 'form-select'}),
            'tipo_exportacao': forms.Select(attrs={'class': 'form-select', 'id': 'id_tipo_exportacao'}),
            'tipo_exportacao_outros': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Descreva o tipo de exportação'}),
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
            'porto_origem',
            'porto_destino',
            'rota_navio',
            'data_embarque_previsto',
            'data_embarque_realizado',
            'deadline_draft',
            'deadline_carga',
            'etd',
            'eta',
            'status',
            'valor_fob',
            'observacoes',
        ]
        widgets = {
            'solicitacao': forms.Select(attrs={'class': 'form-select'}),
            'codigo': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo_exportacao': forms.Select(attrs={'class': 'form-select'}),
            'porto_origem': forms.Select(attrs={'class': 'form-select'}),
            'porto_destino': forms.Select(attrs={'class': 'form-select'}),
            'rota_navio': forms.TextInput(attrs={'class': 'form-control'}),
            'data_embarque_previsto': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
            'data_embarque_realizado': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
            'deadline_draft': forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'deadline_carga': forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'etd': forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'eta': forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'valor_fob': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.empresa:
            self.fields['solicitacao'].queryset = SolicitacaoBooking.objects.filter(empresa=self.empresa).order_by('-data_solicitacao')
            self.fields['porto_origem'].queryset = Porto.objects.filter(empresa=self.empresa, ativo=True).order_by('nome')
            self.fields['porto_destino'].queryset = Porto.objects.filter(empresa=self.empresa, ativo=True).order_by('nome')


class BookingContainerForm(ExportacaoBaseForm):
    class Meta:
        model = BookingContainer
        fields = [
            'booking',
            'numero_container', 'tipo_container', 'status',
            'cultura', 'porto_origem', 'porto_destino', 'data_coleta_prevista',
            'armador', 'transportadora', 'motorista',
            'placa_principal', 'placa_reboque',
            'peso_bruto_kg', 'tara_container', 'numero_genset',
            'lacre_armador', 'lacre_fiscal', 'lacre_terminal',
            'data_coleta_realizada', 'hora_coleta_realizada',
            'observacoes',
        ]
        widgets = {
            'booking':         forms.Select(attrs={'class': 'form-select'}),
            'numero_container': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: ABCU1234567'}),
            'tipo_container':  forms.Select(attrs={'class': 'form-select'}),
            'status':          forms.Select(attrs={'class': 'form-select'}),
            'cultura':         forms.Select(attrs={'class': 'form-select'}),
            'porto_origem':    forms.Select(attrs={'class': 'form-select'}),
            'porto_destino':   forms.Select(attrs={'class': 'form-select'}),
            'data_coleta_prevista':  forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_coleta_realizada': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'hora_coleta_realizada': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'armador':         forms.Select(attrs={'class': 'form-select'}),
            'transportadora':  forms.Select(attrs={'class': 'form-select'}),
            'motorista':       forms.Select(attrs={'class': 'form-select'}),
            'placa_principal': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'AAA-0000'}),
            'placa_reboque':   forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: AAA-0000, BBB-1111'}),
            'peso_bruto_kg':   forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tara_container':  forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'kg'}),
            'numero_genset':   forms.TextInput(attrs={'class': 'form-control'}),
            'lacre_armador':   forms.TextInput(attrs={'class': 'form-control'}),
            'lacre_fiscal':    forms.TextInput(attrs={'class': 'form-control'}),
            'lacre_terminal':  forms.TextInput(attrs={'class': 'form-control'}),
            'observacoes':     forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.empresa:
            self.fields['booking'].queryset = Booking.objects.filter(empresa=self.empresa).order_by('-data_embarque_previsto')
            self.fields['cultura'].queryset = Cultura.objects.filter(empresa=self.empresa).order_by('nome')
            self.fields['porto_origem'].queryset = Porto.objects.filter(empresa=self.empresa, ativo=True).order_by('nome')
            self.fields['porto_destino'].queryset = Porto.objects.filter(empresa=self.empresa, ativo=True).order_by('nome')
            self.fields['armador'].queryset = Armador.objects.filter(empresa=self.empresa).order_by('nome')
            self.fields['transportadora'].queryset = Transportadora.objects.filter(empresa=self.empresa, ativa=True).order_by('razao_social')
            self.fields['motorista'].queryset = Motorista.objects.filter(empresa=self.empresa, ativo=True).order_by('nome')


class ContainerTransferenciaForm(forms.Form):
    booking_destino = forms.ModelChoiceField(
        queryset=Booking.objects.none(),
        label='Booking Destino',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    porto_destino = forms.ModelChoiceField(
        queryset=Porto.objects.none(),
        label='Porto de Destino (novo)',
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    cultura = forms.ModelChoiceField(
        queryset=Cultura.objects.none(),
        label='Cultura (novo)',
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    observacao = forms.CharField(
        label='Motivo da Transferência',
        required=False,
        max_length=300,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3,
                                     'placeholder': 'Descreva o motivo da transferência...'}),
    )

    def __init__(self, *args, empresa=None, container=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._container = container
        if empresa and container:
            self.fields['booking_destino'].queryset = (
                Booking.objects.filter(empresa=empresa)
                .exclude(pk=container.booking_id)
                .order_by('-data_embarque_previsto')
            )
            self.fields['porto_destino'].queryset = Porto.objects.filter(empresa=empresa, ativo=True).order_by('nome')
            self.fields['cultura'].queryset = Cultura.objects.filter(empresa=empresa).order_by('nome')
            self.fields['porto_destino'].initial = container.porto_destino_id
            self.fields['cultura'].initial = container.cultura_id

    def clean_booking_destino(self):
        destino = self.cleaned_data['booking_destino']
        numero = self._container.numero_container
        if BookingContainer.objects.filter(booking=destino, numero_container=numero).exists():
            raise forms.ValidationError(
                f'O container {numero} já existe no booking {destino.codigo}.'
            )
        return destino


class OrdemColetaForm(ExportacaoBaseForm):
    class Meta:
        model = OrdemColeta
        fields = [
            'booking',
            'segregado',
            'container',
            'lacre_armador',
            'lacre_fiscal',
            'lacre_terminal',
            'transportadora',
            'motorista',
            'numero',
            'data_prevista',
            'data_realizada',
            'status',
            'documento',
            'observacoes',
        ]
        widgets = {
            'booking': forms.Select(attrs={'class': 'form-select'}),
            'segregado': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'container': forms.Select(attrs={'class': 'form-select'}),
            'lacre_armador': forms.TextInput(attrs={'class': 'form-control'}),
            'lacre_fiscal': forms.TextInput(attrs={'class': 'form-control'}),
            'lacre_terminal': forms.TextInput(attrs={'class': 'form-control'}),
            'transportadora': forms.Select(attrs={'class': 'form-select'}),
            'motorista': forms.Select(attrs={'class': 'form-select'}),
            'numero': forms.TextInput(attrs={'class': 'form-control', 'readonly': True}),
            'data_prevista': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
            'data_realizada': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'documento': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['container'].required = False
        if self.empresa:
            self.fields['booking'].queryset = Booking.objects.filter(empresa=self.empresa).order_by('-data_embarque_previsto')
            self.fields['container'].queryset = BookingContainer.objects.filter(empresa=self.empresa).order_by('numero_container')
            self.fields['transportadora'].queryset = Transportadora.objects.filter(empresa=self.empresa, ativa=True).order_by('razao_social')
            self.fields['motorista'].queryset = Motorista.objects.filter(empresa=self.empresa, ativo=True).order_by('nome')

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('segregado') and not cleaned_data.get('container'):
            self.add_error('container', 'Contêiner é obrigatório para coleta segregada.')
        return cleaned_data
