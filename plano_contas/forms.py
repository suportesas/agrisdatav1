from django import forms
from django.core.exceptions import ValidationError

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
        if empresa:
            pai_qs = ContaContabil.objects.filter(
                empresa=empresa,
                ativo=True,
                analitica=False,
            ).order_by('codigo')
            if self.instance.pk:
                pai_qs = pai_qs.exclude(pk=self.instance.pk)
        self.fields['conta_pai'].queryset = pai_qs
        self.fields['conta_pai'].empty_label = '— Sem conta pai (conta raiz) —'

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
            'conta_pai': forms.Select(attrs=_WIDGET_SELECT),
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
        if empresa:
            pai_qs = CentroCusto.objects.filter(empresa=empresa, ativo=True).order_by('codigo')
            if self.instance.pk:
                pai_qs = pai_qs.exclude(pk=self.instance.pk)
        self.fields['centro_pai'].queryset = pai_qs
        self.fields['centro_pai'].empty_label = '— Sem centro pai (raiz) —'

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
            'centro_pai': forms.Select(attrs=_WIDGET_SELECT),
            'ativo': forms.CheckboxInput(attrs=_WIDGET_CHECK),
        }
