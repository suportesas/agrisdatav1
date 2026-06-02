"""Formulários do módulo Motorista."""
from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from datetime import date
import re

from .models import Motorista, MotoristadoDocumento, MotoristaVinculoPlaca, VehiclePlate


class MotoristadoForm(forms.ModelForm):
    buscar_cep = forms.BooleanField(
        required=False, initial=False, label='Buscar dados via CEP',
        help_text='Preencher automaticamente endereço via ViaCEP'
    )

    class Meta:
        model = Motorista
        fields = [
            'tipo', 'transportadora', 'nome', 'cpf', 'data_nascimento', 'foto',
            'cnh', 'categoria_cnh', 'data_emissao_cnh', 'data_validade_cnh', 'uf_cnh',
            'telefone', 'celular', 'email',
            'cep', 'logradouro', 'numero', 'complemento', 'bairro', 'cidade', 'uf', 'pais',
            'ativo', 'motivo_inativacao'
        ]
        widgets = {
            'tipo': forms.RadioSelect(choices=Motorista.TIPO_CHOICES),
            'transportadora': forms.Select(attrs={'class': 'form-select'}),
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome completo'}),
            'cpf': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '000.000.000-00', 'data-mask': 'cpf'}),
            'data_nascimento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'foto': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'cnh': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número CNH'}),
            'categoria_cnh': forms.Select(attrs={'class': 'form-select'}),
            'data_emissao_cnh': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'data_validade_cnh': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'uf_cnh': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'SP', 'maxlength': '2', 'style': 'text-transform: uppercase;'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(00) 0000-0000'}),
            'celular': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(00) 00000-0000'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@exemplo.com'}),
            'cep': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '00000-000', 'id': 'id_cep'}),
            'logradouro': forms.TextInput(attrs={'class': 'form-control'}),
            'numero': forms.TextInput(attrs={'class': 'form-control'}),
            'complemento': forms.TextInput(attrs={'class': 'form-control'}),
            'bairro': forms.TextInput(attrs={'class': 'form-control'}),
            'cidade': forms.TextInput(attrs={'class': 'form-control'}),
            'uf': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'SP', 'maxlength': '2', 'style': 'text-transform: uppercase;'}),
            'pais': forms.TextInput(attrs={'class': 'form-control'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'motivo_inativacao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        self.empresa = empresa
        if empresa:
            self.fields['transportadora'].queryset = self.fields['transportadora'].queryset.filter(empresa=empresa)
        self.fields['transportadora'].required = False
        optional_fields = ['transportadora', 'data_nascimento', 'data_emissao_cnh', 'uf_cnh',
                           'telefone', 'email', 'complemento', 'motivo_inativacao']
        for field in optional_fields:
            if field in self.fields:
                self.fields[field].required = False

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo')
        transportadora = cleaned_data.get('transportadora')
        cnh = cleaned_data.get('cnh')
        data_validade_cnh = cleaned_data.get('data_validade_cnh')

        if tipo in ['TERCEIRO', 'AGREGADO'] and not transportadora:
            raise ValidationError({'transportadora': f'Transportadora é obrigatória para motoristas terceirizados/agregados.'})

        if tipo in ['PROPRIO', 'AGREGADO']:
            if not cnh:
                raise ValidationError({'cnh': 'CNH é obrigatória para motoristas próprios e agregados.'})
            if not data_validade_cnh:
                raise ValidationError({'data_validade_cnh': 'Data de validade da CNH é obrigatória.'})

        return cleaned_data

    def clean_cpf(self):
        cpf = self.cleaned_data.get('cpf')
        if cpf:
            cpf_limpo = re.sub(r'\D', '', cpf)
            if len(cpf_limpo) != 11:
                raise ValidationError('CPF deve ter 11 dígitos.')
            if not self._validar_cpf(cpf_limpo):
                raise ValidationError('CPF inválido.')
        return cpf

    def clean_cnh(self):
        cnh = self.cleaned_data.get('cnh')
        if cnh:
            cnh_limpo = re.sub(r'\D', '', cnh)
            if len(cnh_limpo) != 12:
                raise ValidationError('CNH deve ter 12 dígitos.')
        return cnh

    @staticmethod
    def _validar_cpf(cpf):
        if cpf == cpf[0] * 11:
            return False
        soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
        resto = soma % 11
        dv1 = 0 if resto < 2 else 11 - resto
        if int(cpf[9]) != dv1:
            return False
        soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
        resto = soma % 11
        dv2 = 0 if resto < 2 else 11 - resto
        return int(cpf[10]) == dv2

    def save(self, commit=True):
        obj = super().save(commit=False)
        if self.empresa:
            obj.empresa = self.empresa
        if commit:
            obj.save()
        return obj


class MotoristadoDocumentoForm(forms.ModelForm):
    class Meta:
        model = MotoristadoDocumento
        fields = ['tipo', 'numero', 'data_emissao', 'data_validade', 'arquivo', 'observacoes']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'numero': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número do documento'}),
            'data_emissao': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'data_validade': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'arquivo': forms.FileInput(attrs={'class': 'form-control'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class MotoristaVinculoPlacaForm(forms.ModelForm):
    reboques = forms.ModelMultipleChoiceField(
        queryset=VehiclePlate.objects.none(), required=False, label='Placas de Reboque',
        widget=forms.SelectMultiple(attrs={'class': 'form-select'}),
        help_text='Apenas veículos cadastrados como tipo REBOQUE aparecem aqui'
    )

    class Meta:
        model = MotoristaVinculoPlaca
        fields = ['motorista', 'placa_principal', 'reboques', 'data_inicio', 'data_fim', 'ativo', 'observacoes']
        widgets = {
            'motorista': forms.Select(attrs={'class': 'form-select'}),
            'placa_principal': forms.Select(attrs={'class': 'form-select'}),
            'data_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_fim': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if self.empresa:
            self.fields['motorista'].queryset = Motorista.objects.filter(empresa=self.empresa, ativo=True).order_by('nome')
            placas_qs = VehiclePlate.objects.filter(vehicle__empresa=self.empresa).select_related('vehicle')
            self.fields['placa_principal'].queryset = placas_qs
            reboques_qs = VehiclePlate.objects.filter(vehicle__empresa=self.empresa, vehicle__tipo='REBOQUE').select_related('vehicle')
            self.fields['reboques'].queryset = reboques_qs

    def clean(self):
        cleaned = super().clean()
        motorista = cleaned.get('motorista')
        placa_principal = cleaned.get('placa_principal')
        reboques = cleaned.get('reboques') or []
        data_inicio = cleaned.get('data_inicio')
        data_fim = cleaned.get('data_fim')

        if data_inicio and data_fim and data_fim <= data_inicio:
            raise ValidationError({'data_fim': 'Data fim deve ser posterior a data inicio.'})
        if placa_principal and placa_principal in reboques:
            raise ValidationError({'reboques': 'A placa principal nao pode ser selecionada como reboque.'})
        if not self.empresa or not data_inicio:
            return cleaned

        if data_fim:
            overlap_q = Q(data_inicio__lte=data_fim) & (Q(data_fim__isnull=True) | Q(data_fim__gte=data_inicio))
        else:
            overlap_q = Q(data_fim__isnull=True) | Q(data_fim__gte=data_inicio)

        base_qs = MotoristaVinculoPlaca.objects.filter(empresa=self.empresa).exclude(pk=self.instance.pk)

        if motorista and base_qs.filter(motorista=motorista).filter(overlap_q).exists():
            raise ValidationError({'motorista': 'Ja existe vinculo ativo para este motorista neste periodo.'})

        placas_check = []
        if placa_principal:
            placas_check.append(placa_principal)
        placas_check.extend(list(reboques))
        for placa in placas_check:
            if base_qs.filter(overlap_q).filter(Q(placa_principal=placa) | Q(reboques=placa)).exists():
                raise ValidationError({'placa_principal': f'Placa {placa.placa} ja vinculada em outro motorista neste periodo.'})

        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        if self.empresa:
            obj.empresa = self.empresa
        if commit:
            obj.save()
            self.save_m2m()
        return obj


class MotoristaVinculoConsultaForm(forms.Form):
    TIPO_CONSULTA_CHOICES = [
        ('placa_data', 'Placa + Data (Quem estava com a placa?)'),
        ('motorista_periodo', 'Motorista + Período (Quais placas operou?)'),
    ]

    tipo_consulta = forms.ChoiceField(
        choices=TIPO_CONSULTA_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='placa_data', label='Tipo de Consulta'
    )
    placa = forms.ModelChoiceField(
        queryset=VehiclePlate.objects.none(), required=False,
        widget=forms.Select(attrs={'class': 'form-select'}), label='Placa',
    )
    data_referencia = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
        label='Data de Referência',
    )
    motorista = forms.ModelChoiceField(
        queryset=Motorista.objects.none(), required=False,
        widget=forms.Select(attrs={'class': 'form-select'}), label='Motorista'
    )
    data_inicio = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
        label='Data Início',
    )
    data_fim = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
        label='Data Fim',
    )

    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if empresa:
            self.fields['placa'].queryset = VehiclePlate.objects.filter(vehicle__empresa=empresa).order_by('placa')
            self.fields['motorista'].queryset = Motorista.objects.filter(empresa=empresa, ativo=True).order_by('nome')

    def clean(self):
        cleaned_data = super().clean()
        tipo_consulta = cleaned_data.get('tipo_consulta')
        if tipo_consulta == 'placa_data':
            if not cleaned_data.get('placa'):
                self.add_error('placa', 'Selecione uma placa para este tipo de consulta.')
            if not cleaned_data.get('data_referencia'):
                self.add_error('data_referencia', 'Informe a data de referência.')
        elif tipo_consulta == 'motorista_periodo':
            if not cleaned_data.get('motorista'):
                self.add_error('motorista', 'Selecione um motorista para este tipo de consulta.')
            if not cleaned_data.get('data_inicio'):
                self.add_error('data_inicio', 'Informe a data de início do período.')
            data_inicio = cleaned_data.get('data_inicio')
            data_fim = cleaned_data.get('data_fim')
            if data_inicio and data_fim and data_fim < data_inicio:
                self.add_error('data_fim', 'Data fim deve ser maior ou igual à data início.')
        return cleaned_data
