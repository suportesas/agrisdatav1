from django import forms
from django.urls import reverse_lazy

from core.widgets import Select2AjaxWidget
from .models import (
    AplicacaoEstufa,
    Estufa,
    LoteMuda,
    MonitoramentoEstufa,
    PerdaEstufa,
)
from cadastros.models import Cultura, Fazenda, Praga
from rh.models import Funcionario
from produtos.models import Produto, UnidadeMedida


class EstufaForm(forms.ModelForm):
    class Meta:
        model = Estufa
        fields = ['fazenda', 'nome', 'codigo', 'tipo', 'area_m2', 'capacidade_bandejas', 'ativo', 'observacoes']
        widgets = {
            'fazenda': Select2AjaxWidget(ajax_url=reverse_lazy('cadastros:ajax_buscar_fazendas'), placeholder='Buscar fazenda...'),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'codigo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: EST-01'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'area_m2': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'capacidade_bandejas': forms.NumberInput(attrs={'class': 'form-control'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['area_m2'].required = False
        self.fields['capacidade_bandejas'].required = False
        self.fields['observacoes'].required = False
        if self.user and self.user.empresa:
            self.fields['fazenda'].queryset = Fazenda.objects.filter(empresa=self.user.empresa, ativa=True)


class LoteMudaForm(forms.ModelForm):
    class Meta:
        model = LoteMuda
        fields = [
            'estufa', 'cultura', 'cultivar', 'lote_semente', 'data_semeadura',
            'quantidade_semeada', 'data_prevista_pronto', 'status', 'responsavel', 'observacoes',
        ]
        widgets = {
            'estufa': forms.Select(attrs={'class': 'form-select'}),
            'cultura': forms.Select(attrs={'class': 'form-select'}),
            'cultivar': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Híbrido BRS-12'}),
            'lote_semente': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código do lote da semente'}),
            'data_semeadura': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'quantidade_semeada': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Total de sementes'}),
            'data_prevista_pronto': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'responsavel': Select2AjaxWidget(ajax_url=reverse_lazy('rh:ajax_buscar_funcionarios'), placeholder='Buscar funcionário...'),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        for f in ['cultivar', 'lote_semente', 'data_prevista_pronto', 'responsavel', 'observacoes']:
            self.fields[f].required = False
        if self.user and self.user.empresa:
            self.fields['estufa'].queryset = Estufa.objects.filter(empresa=self.user.empresa, ativo=True)
            self.fields['cultura'].queryset = Cultura.objects.filter(empresa=self.user.empresa, ativa=True)
            self.fields['responsavel'].queryset = Funcionario.objects.filter(empresa=self.user.empresa, ativo=True)


class PerdaEstufaForm(forms.ModelForm):
    class Meta:
        model = PerdaEstufa
        fields = ['data', 'quantidade_perdida', 'motivo', 'observacao', 'responsavel']
        widgets = {
            'data': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'quantidade_perdida': forms.NumberInput(attrs={'class': 'form-control'}),
            'motivo': forms.Select(attrs={'class': 'form-select'}),
            'observacao': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'responsavel': Select2AjaxWidget(ajax_url=reverse_lazy('rh:ajax_buscar_funcionarios'), placeholder='Buscar funcionário...'),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['observacao'].required = False
        self.fields['responsavel'].required = False
        if self.user and self.user.empresa:
            self.fields['responsavel'].queryset = Funcionario.objects.filter(empresa=self.user.empresa, ativo=True)
        else:
            self.fields['responsavel'].queryset = Funcionario.objects.none()


class AplicacaoEstufaForm(forms.ModelForm):
    class Meta:
        model = AplicacaoEstufa
        fields = ['data', 'tipo', 'produto', 'quantidade', 'unidade_medida', 'custo_unitario', 'responsavel', 'observacao', 'receituario']
        widgets = {
            'data': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'produto': forms.Select(attrs={'class': 'form-select'}),
            'quantidade': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'unidade_medida': forms.Select(attrs={'class': 'form-select'}),
            'custo_unitario': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001', 'placeholder': 'R$'}),
            'responsavel': Select2AjaxWidget(ajax_url=reverse_lazy('rh:ajax_buscar_funcionarios'), placeholder='Buscar funcionário...'),
            'observacao': forms.TextInput(attrs={'class': 'form-control'}),
            'receituario': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nº Receituário Agronômico'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        for f in ['responsavel', 'observacao', 'receituario', 'custo_unitario']:
            self.fields[f].required = False
        if self.user and self.user.empresa:
            self.fields['responsavel'].queryset = Funcionario.objects.filter(empresa=self.user.empresa, ativo=True)
        else:
            self.fields['responsavel'].queryset = Funcionario.objects.none()


class MonitoramentoEstufaForm(forms.ModelForm):
    class Meta:
        model = MonitoramentoEstufa
        fields = ['data', 'praga', 'nivel_infestacao', 'acao_tomada', 'responsavel']
        widgets = {
            'data': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'praga': forms.Select(attrs={'class': 'form-select'}),
            'nivel_infestacao': forms.Select(attrs={'class': 'form-select'}),
            'acao_tomada': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'responsavel': Select2AjaxWidget(ajax_url=reverse_lazy('rh:ajax_buscar_funcionarios'), placeholder='Buscar funcionário...'),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['acao_tomada'].required = False
        self.fields['responsavel'].required = False
        if self.user and self.user.empresa:
            self.fields['praga'].queryset = Praga.objects.filter(empresa=self.user.empresa, ativa=True)
            self.fields['responsavel'].queryset = Funcionario.objects.filter(empresa=self.user.empresa, ativo=True)
        else:
            self.fields['praga'].queryset = Praga.objects.none()
            self.fields['responsavel'].queryset = Funcionario.objects.none()


# Transplantio e Replantio agora são executados via Ordem de Serviço
# (ver operacoes_campo.forms.OSTransplantioForm / OSReplantioForm).
