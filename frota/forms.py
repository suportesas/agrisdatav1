"""Forms do módulo Frota."""
from django import forms
from django.core.exceptions import ValidationError
from django.urls import reverse_lazy

from core.widgets import Select2AjaxWidget
from .models import (
    Vehicle, VehiclePlate, VehicleValueHistory, VehicleDocument,
    AbastecimentoVeiculo, ManutencaoVeiculo, ManutencaoItem,
    DocumentoManutencao, PedagioVeiculo, TelemetriaVeiculo,
)


class VehicleForm(forms.ModelForm):
    origem = forms.ChoiceField(
        choices=[('PROPRIO', 'Proprio'), ('TERCEIRO', 'Terceiro')],
        initial='PROPRIO',
        label='Origem do Veiculo',
        widget=forms.Select(attrs={'class': 'form-select', 'data-toggle-transportadora': '1'})
    )
    aplicar_variacao_agora = forms.BooleanField(required=False, initial=False, label='Aplicar variação agora')

    class Meta:
        model = Vehicle
        exclude = ('empresa', 'data_cadastro', 'data_atualizacao')
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'marca': forms.TextInput(attrs={'class': 'form-control'}),
            'modelo': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Trator Amarelo, Implemento XX'}),
            'ano_fabricacao': forms.NumberInput(attrs={'class': 'form-control'}),
            'ano_modelo': forms.NumberInput(attrs={'class': 'form-control'}),
            'capacidade_ton': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tara_kg': forms.NumberInput(attrs={'class': 'form-control'}),
            'eixos': forms.NumberInput(attrs={'class': 'form-control'}),
            'cor': forms.TextInput(attrs={'class': 'form-control'}),
            'foto': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'renavam': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'RENAVAM'}),
            'chassis': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Chassi'}),
            'numero_motor': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número do Motor'}),
            'tipo_combustivel': forms.Select(attrs={'class': 'form-select'}),
            'codigo_patrimonio': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código de Patrimônio (se não há placa)'}),
            'consumo_medio': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
            'consumo_unidade': forms.Select(attrs={'class': 'form-select'}),
            'tank_capacity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'valor_atual': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'percentual_variacao': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tipo_variacao': forms.Select(attrs={'class': 'form-select'}),
            'transportadora': Select2AjaxWidget(
                attrs={'data-toggle-transportadora-target': '1'},
                ajax_url=reverse_lazy('cadastros:ajax_buscar_transportadoras'),
                placeholder='Buscar transportadora...',
            ),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }

    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if 'empresa' in self.fields:
            self.fields['empresa'].widget = forms.HiddenInput()
            self.fields['empresa'].required = False
        if self.empresa:
            self.initial['empresa'] = self.empresa
            # 🔒 Bug de escopo corrigido: antes mostrava transportadoras de
            # qualquer empresa (queryset nunca era filtrado).
            from cadastros.models import Transportadora
            self.fields['transportadora'].queryset = Transportadora.objects.filter(
                empresa=self.empresa, ativa=True
            ).order_by('razao_social')
        if self.instance and self.instance.pk:
            self.initial['origem'] = 'TERCEIRO' if self.instance.transportadora else 'PROPRIO'

    def clean(self):
        from decimal import Decimal
        cleaned = super().clean()
        origem = cleaned.get('origem')
        transportadora = cleaned.get('transportadora')
        aplicar = cleaned.get('aplicar_variacao_agora')
        perc = cleaned.get('percentual_variacao')
        tipo = cleaned.get('tipo_variacao')
        valor = cleaned.get('valor_atual')

        if origem == 'TERCEIRO' and not transportadora:
            raise ValidationError({'transportadora': 'Selecione a transportadora para veiculo de terceiro.'})
        if origem == 'PROPRIO':
            cleaned['transportadora'] = None

        if aplicar:
            if valor is None:
                raise ValidationError({'valor_atual': 'Para aplicar a variação é necessário informar o Valor Atual.'})
            if perc is None or perc == Decimal('0.00'):
                raise ValidationError({'percentual_variacao': 'Informe um percentual diferente de 0 para aplicar a variação.'})
            if not tipo:
                raise ValidationError({'tipo_variacao': 'Selecione o tipo de variação (Valorização/Desvalorização).'})
        return cleaned

    def save(self, commit=True, user=None):
        from decimal import Decimal
        obj = super().save(commit=False)
        if self.empresa:
            obj.empresa = self.empresa

        if self.cleaned_data.get('origem') == 'PROPRIO':
            obj.transportadora = None

        aplicar = self.cleaned_data.get('aplicar_variacao_agora')
        perc = self.cleaned_data.get('percentual_variacao')
        tipo = self.cleaned_data.get('tipo_variacao')

        if aplicar and perc and tipo and obj.valor_atual is not None:
            prev = obj.valor_atual or Decimal('0.00')
            factor = (Decimal('1.0') + (perc / Decimal('100'))) if tipo == 'VAL' else (Decimal('1.0') - (perc / Decimal('100')))
            new_val = (prev * factor).quantize(Decimal('0.01'))
            obj.valor_atual = new_val
            if commit:
                obj.save()
                try:
                    VehicleValueHistory.objects.create(
                        vehicle=obj, previous_value=prev, new_value=new_val,
                        percentual=perc, tipo=tipo, aplicado_por=user
                    )
                except Exception:
                    pass
            return obj

        if commit:
            obj.save()
        return obj


class VehiclePlateForm(forms.ModelForm):
    class Meta:
        model = VehiclePlate
        fields = ['placa', 'vigencia_inicio', 'vigencia_fim', 'atual']
        widgets = {
            'placa': forms.TextInput(attrs={'class': 'form-control'}),
            'vigencia_inicio': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'vigencia_fim': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'atual': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }
        labels = {
            'placa': 'Placa',
            'vigencia_inicio': 'Data Início da Vigência',
            'vigencia_fim': 'Data Fim da Vigência (opcional)',
            'atual': 'Placa Atual'
        }

    def __init__(self, *args, **kwargs):
        self.vehicle = kwargs.pop('vehicle', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        vi = cleaned.get('vigencia_inicio')
        vf = cleaned.get('vigencia_fim')
        if vi and vf and vf <= vi:
            raise ValidationError({'vigencia_fim': 'Data fim da vigência deve ser posterior à data início'})
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        if self.vehicle:
            obj.vehicle = self.vehicle
        if commit:
            obj.save()
        return obj


class AbastecimentoVeiculoForm(forms.ModelForm):
    class Meta:
        model = AbastecimentoVeiculo
        fields = [
            'vehicle', 'motorista', 'data', 'tipo_combustivel',
            'litros', 'preco_por_litro', 'km_odometro', 'horimetro',
            'tanque_cheio', 'local_abastecimento', 'fornecedor', 'observacoes',
        ]
        widgets = {
            'vehicle': Select2AjaxWidget(ajax_url=reverse_lazy('frota:ajax_buscar_veiculos'), placeholder='Buscar veículo...'),
            'motorista': Select2AjaxWidget(ajax_url=reverse_lazy('frota:ajax_buscar_motoristas'), placeholder='Buscar motorista...'),
            'data': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'tipo_combustivel': forms.Select(attrs={'class': 'form-select'}),
            'litros': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'preco_por_litro': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'km_odometro': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'horimetro': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'tanque_cheio': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'local_abastecimento': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do posto / local'}),
            'fornecedor': Select2AjaxWidget(ajax_url=reverse_lazy('cadastros:ajax_buscar_fornecedores'), placeholder='Buscar fornecedor...'),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        for f in ['motorista', 'km_odometro', 'horimetro', 'local_abastecimento', 'fornecedor', 'observacoes']:
            self.fields[f].required = False
        if self.user and self.user.empresa:
            emp = self.user.empresa
            from .models import Motorista
            from cadastros.models import Fornecedor
            self.fields['vehicle'].queryset = Vehicle.objects.filter(empresa=emp, ativo=True).order_by('descricao', 'modelo')
            self.fields['motorista'].queryset = Motorista.objects.filter(empresa=emp, ativo=True).order_by('nome')
            self.fields['fornecedor'].queryset = Fornecedor.objects.filter(empresa=emp, ativa=True).order_by('nome_fantasia', 'nome')


class ManutencaoVeiculoForm(forms.ModelForm):
    placa = forms.CharField(
        label='Placa', max_length=10, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control-plaintext', 'readonly': 'readonly'})
    )

    class Meta:
        model = ManutencaoVeiculo
        fields = [
            'vehicle', 'tipo', 'status', 'descricao', 'data_abertura', 'data_conclusao',
            'km_odometro', 'horimetro', 'proxima_data', 'proximo_km',
            'eh_oficina_propria', 'local_oficina', 'fornecedor_externo',
            'valor_servico', 'observacoes',
        ]
        widgets = {
            'vehicle': Select2AjaxWidget(ajax_url=reverse_lazy('frota:ajax_buscar_veiculos'), placeholder='Buscar veículo...'),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'descricao': forms.TextInput(attrs={'class': 'form-control'}),
            'data_abertura': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_conclusao': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'km_odometro': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'horimetro': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'proxima_data': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'proximo_km': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'eh_oficina_propria': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'local_oficina': forms.Select(attrs={'class': 'form-select'}),
            'fornecedor_externo': Select2AjaxWidget(ajax_url=reverse_lazy('cadastros:ajax_buscar_fornecedores'), placeholder='Buscar fornecedor...'),
            'valor_servico': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        optional = [
            'data_conclusao', 'km_odometro', 'horimetro', 'proxima_data', 'proximo_km',
            'local_oficina', 'fornecedor_externo', 'observacoes',
        ]
        for f in optional:
            self.fields[f].required = False
        if self.instance and self.instance.pk:
            self.fields['placa'].initial = self.instance.placa_atual
        if self.user and self.user.empresa:
            emp = self.user.empresa
            from cadastros.models import Fornecedor
            from estoque.models import Armazem
            self.fields['vehicle'].queryset = Vehicle.objects.filter(empresa=emp, ativo=True).order_by('descricao', 'modelo')
            self.fields['fornecedor_externo'].queryset = Fornecedor.objects.filter(empresa=emp, ativa=True).order_by('nome_fantasia', 'nome')
            self.fields['local_oficina'].queryset = Armazem.objects.filter(empresa=emp)


class ManutencaoItemForm(forms.ModelForm):
    class Meta:
        model = ManutencaoItem
        fields = ['descricao', 'lote', 'quantidade', 'valor_unitario', 'valor_custo', 'nome_produto', 'unidade_medida', 'desconto']
        widgets = {
            'descricao': forms.HiddenInput(),
            'lote': forms.HiddenInput(),
            'quantidade': forms.NumberInput(attrs={'class': 'form-control quantidade-input', 'step': '0.001'}),
            'valor_unitario': forms.HiddenInput(),
            'valor_custo': forms.NumberInput(attrs={'class': 'form-control-plaintext custo-input', 'readonly': 'readonly', 'step': '0.0001', 'tabindex': '-1'}),
            'nome_produto': forms.TextInput(attrs={'class': 'form-control produto-search-input', 'placeholder': 'Buscar produto...', 'autocomplete': 'off'}),
            'unidade_medida': forms.TextInput(attrs={'class': 'form-control-plaintext', 'readonly': 'readonly', 'tabindex': '-1'}),
            'desconto': forms.NumberInput(attrs={'class': 'form-control desconto-input', 'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['descricao'].required = False
        self.fields['lote'].required = False
        self.fields['valor_unitario'].required = False
        self.fields['valor_custo'].required = False
        self.fields['nome_produto'].required = False
        self.fields['unidade_medida'].required = False
        self.fields['desconto'].required = False
        if self.user and self.user.empresa:
            from estoque.models import Lote
            self.fields['lote'].queryset = Lote.objects.filter(
                empresa=self.user.empresa
            ).select_related('produto').order_by('produto__nome')

    def clean_valor_unitario(self):
        from decimal import Decimal
        v = self.cleaned_data.get('valor_unitario')
        if v is None:
            return self.cleaned_data.get('valor_custo') or Decimal('0')
        return v


class DocumentoManutencaoForm(forms.ModelForm):
    class Meta:
        model = DocumentoManutencao
        fields = ['tipo', 'descricao', 'numero_documento', 'arquivo']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'descricao': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Descrição opcional'}),
            'numero_documento': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Ex: NF 001234'}),
            'arquivo': forms.FileInput(attrs={'class': 'form-control form-control-sm', 'accept': '.pdf,.jpg,.jpeg,.png,.doc,.docx'}),
        }

    def clean_arquivo(self):
        arquivo = self.cleaned_data.get('arquivo')
        if arquivo and arquivo.size > 10 * 1024 * 1024:
            raise ValidationError('Arquivo muito grande. Tamanho máximo: 10MB.')
        return arquivo


class PedagioVeiculoForm(forms.ModelForm):
    class Meta:
        model = PedagioVeiculo
        fields = ['vehicle', 'viagem', 'motorista', 'data', 'praca', 'valor', 'observacoes']
        widgets = {
            'vehicle': Select2AjaxWidget(ajax_url=reverse_lazy('frota:ajax_buscar_veiculos'), placeholder='Buscar veículo...'),
            'viagem': forms.Select(attrs={'class': 'form-select'}),
            'motorista': Select2AjaxWidget(ajax_url=reverse_lazy('frota:ajax_buscar_motoristas'), placeholder='Buscar motorista...'),
            'data': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'praca': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Praça SP-270 km 45'}),
            'valor': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        for f in ['viagem', 'motorista', 'praca', 'observacoes']:
            self.fields[f].required = False
        if self.user and self.user.empresa:
            emp = self.user.empresa
            from .models import Motorista
            from cadastros.models import Viagem
            self.fields['vehicle'].queryset = Vehicle.objects.filter(empresa=emp, ativo=True).order_by('descricao', 'modelo')
            self.fields['motorista'].queryset = Motorista.objects.filter(empresa=emp, ativo=True).order_by('nome')
            self.fields['viagem'].queryset = Viagem.objects.filter(transportadora__empresa=emp).order_by('-data')


class TelemetriaVeiculoForm(forms.ModelForm):
    class Meta:
        model = TelemetriaVeiculo
        fields = ['vehicle', 'motorista', 'viagem', 'data_hora', 'latitude', 'longitude',
                  'local_descricao', 'velocidade_kmh', 'km_odometro', 'fonte', 'observacoes']
        widgets = {
            'vehicle': Select2AjaxWidget(ajax_url=reverse_lazy('frota:ajax_buscar_veiculos'), placeholder='Buscar veículo...'),
            'motorista': Select2AjaxWidget(ajax_url=reverse_lazy('frota:ajax_buscar_motoristas'), placeholder='Buscar motorista...'),
            'viagem': forms.Select(attrs={'class': 'form-select'}),
            'data_hora': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0000001'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0000001'}),
            'local_descricao': forms.TextInput(attrs={'class': 'form-control'}),
            'velocidade_kmh': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'km_odometro': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'fonte': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        for f in ['motorista', 'viagem', 'latitude', 'longitude', 'local_descricao',
                  'velocidade_kmh', 'km_odometro', 'observacoes']:
            self.fields[f].required = False
        if self.user and self.user.empresa:
            emp = self.user.empresa
            from .models import Motorista
            from cadastros.models import Viagem
            self.fields['vehicle'].queryset = Vehicle.objects.filter(empresa=emp, ativo=True).order_by('descricao', 'modelo')
            self.fields['motorista'].queryset = Motorista.objects.filter(empresa=emp, ativo=True).order_by('nome')
            self.fields['viagem'].queryset = Viagem.objects.filter(transportadora__empresa=emp).order_by('-data')


class ViagemFrotaForm(forms.ModelForm):
    class Meta:
        from cadastros.models import Viagem
        model = Viagem
        fields = ['transportadora', 'vehicle', 'motorista', 'origem', 'destino',
                  'data', 'valor_frete', 'km_inicial', 'km_final', 'status', 'observacoes']
        widgets = {
            'transportadora': Select2AjaxWidget(ajax_url=reverse_lazy('cadastros:ajax_buscar_transportadoras'), placeholder='Buscar transportadora...'),
            'vehicle': Select2AjaxWidget(ajax_url=reverse_lazy('frota:ajax_buscar_veiculos'), placeholder='Buscar veículo...'),
            'motorista': Select2AjaxWidget(ajax_url=reverse_lazy('frota:ajax_buscar_motoristas'), placeholder='Buscar motorista...'),
            'origem': forms.TextInput(attrs={'class': 'form-control'}),
            'destino': forms.TextInput(attrs={'class': 'form-control'}),
            'data': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'valor_frete': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'km_inicial': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'km_final': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        for f in ['vehicle', 'motorista', 'valor_frete', 'km_inicial', 'km_final', 'observacoes']:
            self.fields[f].required = False
        if self.user and self.user.empresa:
            emp = self.user.empresa
            from cadastros.models import Transportadora
            from .models import Motorista
            self.fields['transportadora'].queryset = Transportadora.objects.filter(empresa=emp, ativa=True).order_by('nome_fantasia', 'razao_social')
            self.fields['vehicle'].queryset = Vehicle.objects.filter(empresa=emp, ativo=True).order_by('descricao', 'modelo')
            self.fields['motorista'].queryset = Motorista.objects.filter(empresa=emp, ativo=True).order_by('nome')


class AbastecimentoImportForm(forms.Form):
    arquivo = forms.FileField(
        label='Arquivo CSV',
        widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.csv,.txt'}),
        help_text='Arquivo CSV com colunas: vehicle_placa, data, tipo_combustivel, litros, preco_por_litro, km_odometro, tanque_cheio, local'
    )


class MotoristaLoginForm(forms.Form):
    matricula = forms.CharField(
        label='Matrícula', max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Sua matrícula', 'autofocus': True}),
    )
    pin = forms.CharField(
        label='PIN', max_length=20,
        widget=forms.PasswordInput(attrs={'class': 'form-control form-control-lg', 'placeholder': '••••••'}),
    )


class AbastecimentoPortalForm(forms.ModelForm):
    foto_bomba = forms.ImageField(
        label='Foto da Bomba',
        widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*', 'capture': 'environment'}),
        required=True,
    )
    foto_odometro = forms.ImageField(
        label='Foto do Hodômetro',
        widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*', 'capture': 'environment'}),
        required=False,
    )

    class Meta:
        model = AbastecimentoVeiculo
        fields = ['vehicle', 'data', 'tipo_combustivel', 'litros', 'preco_por_litro',
                  'km_odometro', 'horimetro', 'tanque_cheio', 'local_abastecimento', 'observacoes']
        widgets = {
            'vehicle': forms.Select(attrs={'class': 'form-select form-select-lg'}),
            'data': forms.DateInput(attrs={'class': 'form-control form-control-lg', 'type': 'date'}),
            'tipo_combustivel': forms.Select(attrs={'class': 'form-select form-select-lg'}),
            'litros': forms.NumberInput(attrs={'class': 'form-control form-control-lg', 'step': '0.001', 'min': '0'}),
            'preco_por_litro': forms.NumberInput(attrs={'class': 'form-control form-control-lg', 'step': '0.001', 'min': '0'}),
            'km_odometro': forms.NumberInput(attrs={'class': 'form-control form-control-lg', 'step': '0.1'}),
            'horimetro': forms.NumberInput(attrs={'class': 'form-control form-control-lg', 'step': '0.1'}),
            'tanque_cheio': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'local_abastecimento': forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Nome do posto'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        vehicles_qs = kwargs.pop('vehicles_qs', None)
        super().__init__(*args, **kwargs)
        for f in ['km_odometro', 'horimetro', 'local_abastecimento', 'observacoes']:
            self.fields[f].required = False
        if vehicles_qs is not None:
            self.fields['vehicle'].queryset = vehicles_qs
        elif self.empresa:
            self.fields['vehicle'].queryset = Vehicle.objects.filter(empresa=self.empresa, ativo=True).order_by('descricao', 'modelo')


class SolicitacaoManutencaoForm(forms.ModelForm):
    class Meta:
        model = ManutencaoVeiculo
        fields = ['vehicle', 'tipo', 'descricao', 'km_odometro', 'horimetro', 'observacoes']
        widgets = {
            'vehicle': forms.Select(attrs={'class': 'form-select form-select-lg'}),
            'tipo': forms.Select(attrs={'class': 'form-select form-select-lg'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Descreva o problema ou serviço necessário...'}),
            'km_odometro': forms.NumberInput(attrs={'class': 'form-control form-control-lg', 'step': '0.1'}),
            'horimetro': forms.NumberInput(attrs={'class': 'form-control form-control-lg', 'step': '0.1'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        vehicles_qs = kwargs.pop('vehicles_qs', None)
        super().__init__(*args, **kwargs)
        for f in ['km_odometro', 'horimetro', 'observacoes']:
            self.fields[f].required = False
        if vehicles_qs is not None:
            self.fields['vehicle'].queryset = vehicles_qs
        elif self.empresa:
            self.fields['vehicle'].queryset = Vehicle.objects.filter(empresa=self.empresa, ativo=True).order_by('descricao', 'modelo')
