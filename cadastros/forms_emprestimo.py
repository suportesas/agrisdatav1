from django import forms
from django.utils import timezone

from .models import EmprestimoProdutor, Produtor
from produtos.models import Produto


class EmprestimoExtratoFiltroForm(forms.Form):
    produtor = forms.ModelChoiceField(
        label='Produtor',
        queryset=Produtor.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    produto = forms.ModelChoiceField(
        label='Produto',
        queryset=Produto.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    status = forms.ChoiceField(
        label='Status',
        required=False,
        choices=[('', 'Todos')] + EmprestimoProdutor.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    data_inicio = forms.DateField(
        label='Data Inicial',
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    data_fim = forms.DateField(
        label='Data Final',
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    apenas_vencidos = forms.BooleanField(
        label='Apenas promessas vencidas',
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    apenas_mensagens_nao_lidas = forms.BooleanField(
        label='Apenas com mensagens do produtor não lidas',
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if empresa:
            self.fields['produtor'].queryset = Produtor.objects.filter(empresa=empresa).order_by('razao_social')
            self.fields['produto'].queryset = Produto.objects.filter(categoria__empresa=empresa, ativo=True).order_by('nome')


class EmprestimoDevolucaoForm(forms.Form):
    emprestimo = forms.ModelChoiceField(
        label='Empréstimo',
        queryset=EmprestimoProdutor.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    quantidade = forms.DecimalField(
        label='Quantidade Devolvida',
        decimal_places=3,
        max_digits=15,
        min_value=0.001,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'})
    )
    data_movimento = forms.DateTimeField(
        label='Data da Devolução',
        required=False,
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'})
    )
    comprovante = forms.FileField(
        label='Comprovante',
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )
    observacoes = forms.CharField(
        label='Observações',
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )

    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if empresa:
            self.fields['emprestimo'].queryset = (
                EmprestimoProdutor.objects
                .filter(empresa=empresa)
                .exclude(status__in=['DEVOLVIDO', 'CANCELADO'])
                .exclude(saldo_pendente__lte=0)
                .select_related('produtor', 'produto')
                .order_by('-data_emprestimo')
            )
        self.fields['data_movimento'].initial = timezone.now().strftime('%Y-%m-%dT%H:%M')

    def clean(self):
        cleaned_data = super().clean()
        emprestimo = cleaned_data.get('emprestimo')
        quantidade = cleaned_data.get('quantidade')

        if emprestimo and quantidade and quantidade > emprestimo.saldo_pendente:
            self.add_error('quantidade', f'Quantidade excede saldo pendente ({emprestimo.saldo_pendente}).')

        return cleaned_data
