from django import forms
from .models import UsinaFotovoltaica, UnidadeConsumidora, LancamentoMensal, RelatorioMensalUsina, OcorrenciaUsina

_CTRL = {'class': 'form-control'}
_SEL = {'class': 'form-select'}
_DATE = {'class': 'form-control', 'type': 'date'}
_NUM = {'class': 'form-control', 'step': 'any'}
_TEXTAREA = {'class': 'form-control', 'rows': '3'}


class UsinaFotovoltaicaForm(forms.ModelForm):
    def __init__(self, *args, empresa=None, **kwargs):
        self.empresa = empresa
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.empresa:
            instance.empresa = self.empresa
        if commit:
            instance.save()
        return instance

    class Meta:
        model = UsinaFotovoltaica
        fields = [
            'codigo', 'nome', 'capacidade_kwp',
            'geracao_acordada_mensal_kwh', 'geracao_acordada_anual_kwh',
            'prognostico_mensal_kwh', 'data_instalacao', 'ativa',
        ]
        widgets = {
            'codigo': forms.TextInput(attrs=_CTRL),
            'nome': forms.TextInput(attrs=_CTRL),
            'capacidade_kwp': forms.NumberInput(attrs=_NUM),
            'geracao_acordada_mensal_kwh': forms.NumberInput(attrs=_NUM),
            'geracao_acordada_anual_kwh': forms.NumberInput(attrs=_NUM),
            'prognostico_mensal_kwh': forms.NumberInput(attrs=_NUM),
            'data_instalacao': forms.DateInput(attrs=_DATE),
            'ativa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class UnidadeConsumidoraForm(forms.ModelForm):
    def __init__(self, *args, empresa=None, **kwargs):
        self.empresa = empresa
        super().__init__(*args, **kwargs)
        if empresa:
            self.fields['usina'].queryset = UsinaFotovoltaica.objects.filter(
                empresa=empresa, ativa=True)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.empresa:
            instance.empresa = self.empresa
        if commit:
            instance.save()
        return instance

    class Meta:
        model = UnidadeConsumidora
        fields = [
            'usina', 'tipo', 'codigo_cliente', 'codigo_instalacao',
            'nome', 'classificacao', 'tipo_fornecimento', 'numero_medidor', 'ativa',
        ]
        widgets = {
            'usina': forms.Select(attrs=_SEL),
            'tipo': forms.Select(attrs=_SEL),
            'codigo_cliente': forms.TextInput(attrs=_CTRL),
            'codigo_instalacao': forms.TextInput(attrs=_CTRL),
            'nome': forms.TextInput(attrs=_CTRL),
            'classificacao': forms.TextInput(attrs=_CTRL),
            'tipo_fornecimento': forms.TextInput(attrs=_CTRL),
            'numero_medidor': forms.TextInput(attrs=_CTRL),
            'ativa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class LancamentoMensalForm(forms.ModelForm):
    def __init__(self, *args, empresa=None, **kwargs):
        self.empresa = empresa
        super().__init__(*args, **kwargs)
        if empresa:
            self.fields['unidade_consumidora'].queryset = UnidadeConsumidora.objects.filter(
                empresa=empresa, ativa=True).select_related('usina')

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.empresa:
            instance.empresa = self.empresa
        if commit:
            instance.save()
        return instance

    class Meta:
        model = LancamentoMensal
        fields = [
            'unidade_consumidora', 'mes_referencia',
            'data_leitura_anterior', 'data_leitura_atual', 'num_dias',
            'consumo_registrado_kwh', 'energia_compensada_kwh', 'energia_faturada_kwh',
            'energia_injetada_kwh', 'credito_anterior_kwh', 'credito_acumulado_kwh',
            'valor_faturado_rs', 'valor_economizado_rs', 'desconto_incondicional_rs',
            'observacoes',
        ]
        widgets = {
            'unidade_consumidora': forms.Select(attrs=_SEL),
            'mes_referencia': forms.DateInput(attrs=_DATE),
            'data_leitura_anterior': forms.DateInput(attrs=_DATE),
            'data_leitura_atual': forms.DateInput(attrs=_DATE),
            'num_dias': forms.NumberInput(attrs=_CTRL),
            'consumo_registrado_kwh': forms.NumberInput(attrs=_NUM),
            'energia_compensada_kwh': forms.NumberInput(attrs=_NUM),
            'energia_faturada_kwh': forms.NumberInput(attrs=_NUM),
            'energia_injetada_kwh': forms.NumberInput(attrs=_NUM),
            'credito_anterior_kwh': forms.NumberInput(attrs=_NUM),
            'credito_acumulado_kwh': forms.NumberInput(attrs=_NUM),
            'valor_faturado_rs': forms.NumberInput(attrs=_NUM),
            'valor_economizado_rs': forms.NumberInput(attrs=_NUM),
            'desconto_incondicional_rs': forms.NumberInput(attrs=_NUM),
            'observacoes': forms.Textarea(attrs=_TEXTAREA),
        }


class RelatorioMensalUsinaForm(forms.ModelForm):
    def __init__(self, *args, empresa=None, **kwargs):
        self.empresa = empresa
        super().__init__(*args, **kwargs)
        if empresa:
            self.fields['usina'].queryset = UsinaFotovoltaica.objects.filter(
                empresa=empresa, ativa=True)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.empresa:
            instance.empresa = self.empresa
        if commit:
            instance.save()
        return instance

    class Meta:
        model = RelatorioMensalUsina
        fields = [
            'usina', 'mes_referencia',
            'geracao_kwh', 'desempenho_pct', 'consumo_total_kwh',
            'consumo_registrado_kwh', 'uc_geradora_kwh', 'consumo_instantaneo_kwh',
            'energia_injetada_kwh',
            'economia_rs', 'faturado_rs', 'retorno_financeiro_pct',
            'economia_total_rs', 'retorno_financeiro_total_pct',
            'co2_nao_produzido_t', 'arvores_salvas',
        ]
        widgets = {
            'usina': forms.Select(attrs=_SEL),
            'mes_referencia': forms.DateInput(attrs=_DATE),
            'geracao_kwh': forms.NumberInput(attrs=_NUM),
            'desempenho_pct': forms.NumberInput(attrs=_NUM),
            'consumo_total_kwh': forms.NumberInput(attrs=_NUM),
            'consumo_registrado_kwh': forms.NumberInput(attrs=_NUM),
            'uc_geradora_kwh': forms.NumberInput(attrs=_NUM),
            'consumo_instantaneo_kwh': forms.NumberInput(attrs=_NUM),
            'energia_injetada_kwh': forms.NumberInput(attrs=_NUM),
            'economia_rs': forms.NumberInput(attrs=_NUM),
            'faturado_rs': forms.NumberInput(attrs=_NUM),
            'retorno_financeiro_pct': forms.NumberInput(attrs=_NUM),
            'economia_total_rs': forms.NumberInput(attrs=_NUM),
            'retorno_financeiro_total_pct': forms.NumberInput(attrs=_NUM),
            'co2_nao_produzido_t': forms.NumberInput(attrs=_NUM),
            'arvores_salvas': forms.NumberInput(attrs=_CTRL),
        }


class OcorrenciaUsinaForm(forms.ModelForm):
    def __init__(self, *args, empresa=None, usina=None, **kwargs):
        self.empresa = empresa
        super().__init__(*args, **kwargs)
        if empresa:
            self.fields['usina'].queryset = UsinaFotovoltaica.objects.filter(
                empresa=empresa, ativa=True)
            self.fields['relatorio'].queryset = RelatorioMensalUsina.objects.filter(
                empresa=empresa).select_related('usina').order_by('-mes_referencia')
        if usina:
            self.fields['relatorio'].queryset = RelatorioMensalUsina.objects.filter(
                empresa=empresa, usina=usina).order_by('-mes_referencia')
            self.initial['usina'] = usina

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.empresa:
            instance.empresa = self.empresa
        if commit:
            instance.save()
        return instance

    class Meta:
        model = OcorrenciaUsina
        fields = [
            'usina', 'relatorio', 'tipo', 'gravidade', 'titulo',
            'descricao', 'data_ocorrencia', 'data_resolucao',
            'impacto_kwh_estimado', 'resolvido', 'responsavel',
        ]
        widgets = {
            'usina': forms.Select(attrs=_SEL),
            'relatorio': forms.Select(attrs=_SEL),
            'tipo': forms.Select(attrs=_SEL),
            'gravidade': forms.Select(attrs=_SEL),
            'titulo': forms.TextInput(attrs=_CTRL),
            'descricao': forms.Textarea(attrs={**_TEXTAREA, 'rows': '5'}),
            'data_ocorrencia': forms.DateInput(attrs=_DATE),
            'data_resolucao': forms.DateInput(attrs=_DATE),
            'impacto_kwh_estimado': forms.NumberInput(attrs=_NUM),
            'resolvido': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'responsavel': forms.TextInput(attrs=_CTRL),
        }
