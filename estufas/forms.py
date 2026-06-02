from django import forms

from .models import (
    AplicacaoEstufa,
    Estufa,
    LoteMuda,
    MonitoramentoEstufa,
    PerdaEstufa,
    ReplantioTalhao,
    Transplantio,
)
from cadastros.models import Cultura, Fazenda, Praga, Safra, Talhao
from rh.models import Funcionario
from produtos.models import Produto, UnidadeMedida


class EstufaForm(forms.ModelForm):
    class Meta:
        model = Estufa
        fields = ['fazenda', 'nome', 'codigo', 'tipo', 'area_m2', 'capacidade_bandejas', 'ativo', 'observacoes']
        widgets = {
            'fazenda': forms.Select(attrs={'class': 'form-select'}),
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
            'responsavel': forms.Select(attrs={'class': 'form-select'}),
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
            'responsavel': forms.Select(attrs={'class': 'form-select'}),
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
            'responsavel': forms.Select(attrs={'class': 'form-select'}),
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
            'responsavel': forms.Select(attrs={'class': 'form-select'}),
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


class TransplantioForm(forms.ModelForm):
    class Meta:
        model = Transplantio
        fields = ['lote_muda', 'talhao', 'safra', 'data_transplantio', 'tipo', 'quantidade_transplantada', 'responsavel', 'observacao', 'fotos']
        widgets = {
            'lote_muda': forms.Select(attrs={'class': 'form-select'}),
            'talhao': forms.Select(attrs={'class': 'form-select'}),
            'safra': forms.Select(attrs={'class': 'form-select'}),
            'data_transplantio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'quantidade_transplantada': forms.NumberInput(attrs={'class': 'form-control'}),
            'responsavel': forms.Select(attrs={'class': 'form-select'}),
            'observacao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'fotos': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        for f in ['safra', 'responsavel', 'observacao', 'fotos']:
            self.fields[f].required = False
        if self.user and self.user.empresa:
            qs_lotes = LoteMuda.objects.filter(empresa=self.user.empresa, status='PRONTO').select_related('cultura', 'estufa')
            self.fields['lote_muda'].queryset = qs_lotes
            # Mostra disponível e cultura no label
            self.fields['lote_muda'].label_from_instance = lambda obj: (
                f"{obj.codigo_lote} — {obj.cultura.nome} ({obj.quantidade_disponivel} dispon.)"
            )
            self.fields['talhao'].queryset = Talhao.objects.filter(
                empresa=self.user.empresa, ativo=True, status__in=['DISPONIVEL', 'PREPARACAO'],
            )
            self.fields['safra'].queryset = Safra.objects.filter(
                fazenda__empresa=self.user.empresa, status__in=['PLANEJADA', 'EM_ANDAMENTO'],
            )
            self.fields['responsavel'].queryset = Funcionario.objects.filter(empresa=self.user.empresa, ativo=True)


class ReplantioTalhaoForm(forms.ModelForm):
    class Meta:
        model = ReplantioTalhao
        fields = ['talhao', 'safra', 'data_replantio', 'quantidade', 'origem_muda', 'lote_muda', 'motivo_perda', 'custo_adicional', 'responsavel', 'observacao']
        widgets = {
            'talhao': forms.Select(attrs={'class': 'form-select'}),
            'safra': forms.Select(attrs={'class': 'form-select'}),
            'data_replantio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'quantidade': forms.NumberInput(attrs={'class': 'form-control'}),
            'origem_muda': forms.Select(attrs={'class': 'form-select'}),
            'lote_muda': forms.Select(attrs={'class': 'form-select'}),
            'motivo_perda': forms.Select(attrs={'class': 'form-select'}),
            'custo_adicional': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'responsavel': forms.Select(attrs={'class': 'form-select'}),
            'observacao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        for f in ['safra', 'lote_muda', 'custo_adicional', 'responsavel', 'observacao']:
            self.fields[f].required = False
        if self.user and self.user.empresa:
            self.fields['talhao'].queryset = Talhao.objects.filter(empresa=self.user.empresa, ativo=True)
            self.fields['safra'].queryset = Safra.objects.filter(fazenda__empresa=self.user.empresa)
            self.fields['lote_muda'].queryset = LoteMuda.objects.filter(empresa=self.user.empresa).select_related('cultura')
            self.fields['responsavel'].queryset = Funcionario.objects.filter(empresa=self.user.empresa, ativo=True)
