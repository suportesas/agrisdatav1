from django import forms
from django.core.exceptions import ValidationError
from django.urls import reverse_lazy

from core.widgets import Select2AjaxWidget
from .models import ContaContabil, CentroCusto

_WIDGET_TEXT = {'class': 'form-control'}
_WIDGET_SELECT = {'class': 'form-select'}
_WIDGET_CHECK = {'class': 'form-check-input'}
_WIDGET_TEXTAREA = {'class': 'form-control', 'rows': '3'}


class ContaContabilForm(forms.ModelForm):
    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empresa = empresa
        pai_qs = ContaContabil.objects.none()
        extra_params = {'analitica': '0'}
        if empresa:
            pai_qs = ContaContabil.objects.filter(
                empresa=empresa,
                ativo=True,
                analitica=False,
            ).order_by('codigo')
            if self.instance.pk:
                pai_qs = pai_qs.exclude(pk=self.instance.pk)
                extra_params['excluir_id'] = self.instance.pk
        # Widget precisa ser trocado ANTES do queryset: ModelChoiceField.queryset
        # (setter) propaga field.choices pro widget.choices vigente na hora —
        # se trocássemos depois, o Select2AjaxWidget novo ficaria sem o
        # ModelChoiceIterator e não conseguiria resolver a opção selecionada.
        self.fields['conta_pai'].widget = Select2AjaxWidget(
            ajax_url=reverse_lazy('plano_contas:conta_autocomplete'),
            extra_params=extra_params,
            placeholder='Sem conta pai (conta raiz)',
        )
        self.fields['conta_pai'].queryset = pai_qs

    def clean(self):
        cleaned = super().clean()
        codigo = cleaned.get('codigo')
        if codigo and self.empresa:
            qs = ContaContabil.objects.filter(empresa=self.empresa, codigo=codigo)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error('codigo', f'Já existe uma conta com o código "{codigo}" nesta empresa.')
        return cleaned

    class Meta:
        model = ContaContabil
        exclude = ('empresa', 'nivel', 'created_at', 'updated_at')
        widgets = {
            'codigo': forms.TextInput(attrs={**_WIDGET_TEXT, 'placeholder': 'Ex: 1.1.01.001'}),
            'nome': forms.TextInput(attrs=_WIDGET_TEXT),
            'tipo': forms.Select(attrs=_WIDGET_SELECT),
            'natureza': forms.Select(attrs=_WIDGET_SELECT),
            # 'conta_pai' widget é montado em __init__ (Select2AjaxWidget — precisa de excluir_id dinâmico)
            'descricao': forms.Textarea(attrs=_WIDGET_TEXTAREA),
            'observacoes': forms.Textarea(attrs=_WIDGET_TEXTAREA),
            'analitica': forms.CheckboxInput(attrs=_WIDGET_CHECK),
            'gerencial': forms.CheckboxInput(attrs=_WIDGET_CHECK),
            'ativo': forms.CheckboxInput(attrs=_WIDGET_CHECK),
        }


class CentroCustoForm(forms.ModelForm):
    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empresa = empresa
        pai_qs = CentroCusto.objects.none()
        extra_params = {}
        if empresa:
            pai_qs = CentroCusto.objects.filter(empresa=empresa, ativo=True).order_by('codigo')
            if self.instance.pk:
                pai_qs = pai_qs.exclude(pk=self.instance.pk)
                extra_params['excluir_id'] = self.instance.pk
        # Widget trocado antes do queryset — ver comentário em ContaContabilForm.
        self.fields['centro_pai'].widget = Select2AjaxWidget(
            ajax_url=reverse_lazy('plano_contas:centro_autocomplete'),
            extra_params=extra_params,
            placeholder='Sem centro pai (raiz)',
        )
        self.fields['centro_pai'].queryset = pai_qs

    def clean(self):
        cleaned = super().clean()
        codigo = cleaned.get('codigo')
        if codigo and self.empresa:
            qs = CentroCusto.objects.filter(empresa=self.empresa, codigo=codigo)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error('codigo', f'Já existe um centro de custo com o código "{codigo}" nesta empresa.')
        return cleaned

    class Meta:
        model = CentroCusto
        exclude = ('empresa', 'nivel', 'created_at', 'updated_at')
        widgets = {
            'codigo': forms.TextInput(attrs={**_WIDGET_TEXT, 'placeholder': 'Ex: CC-01'}),
            'nome': forms.TextInput(attrs=_WIDGET_TEXT),
            'descricao': forms.Textarea(attrs=_WIDGET_TEXTAREA),
            # 'centro_pai' widget é montado em __init__ (Select2AjaxWidget — precisa de excluir_id dinâmico)
            'ativo': forms.CheckboxInput(attrs=_WIDGET_CHECK),
        }
