from django import forms
from core.widgets import DateBRInput
from .models import BancoCorrespondente, ContaBancaria, ImportacaoExtrato

_CTRL = {'class': 'form-control'}
_SEL = {'class': 'form-select'}
_CHK = {'class': 'form-check-input'}
_TEXTAREA = {'class': 'form-control', 'rows': '3'}


class ContaBancariaForm(forms.ModelForm):
    class Meta:
        model = ContaBancaria
        fields = [
            'banco', 'codigo_banco',
            'agencia', 'agencia_digito',
            'conta', 'conta_digito',
            'tipo_conta',
            'pix_habilitado', 'tipo_chave_pix', 'chave_pix',
            'iban', 'swift_bic', 'endereco_banco', 'beneficiario_nome',
            'saldo_inicial', 'data_saldo_inicial',
            'conta_principal', 'ativa',
            'observacoes',
        ]
        widgets = {
            'banco': forms.TextInput(attrs={**_CTRL, 'placeholder': 'Ex: Banco do Brasil'}),
            'codigo_banco': forms.TextInput(attrs={**_CTRL, 'placeholder': '001', 'maxlength': '4'}),
            'agencia': forms.TextInput(attrs={**_CTRL, 'placeholder': '1234'}),
            'agencia_digito': forms.TextInput(attrs={**_CTRL, 'maxlength': '2', 'placeholder': 'X'}),
            'conta': forms.TextInput(attrs={**_CTRL, 'placeholder': '12345-6'}),
            'conta_digito': forms.TextInput(attrs={**_CTRL, 'maxlength': '2', 'placeholder': 'X'}),
            'tipo_conta': forms.Select(attrs=_SEL),
            'pix_habilitado': forms.CheckboxInput(attrs=_CHK),
            'tipo_chave_pix': forms.Select(attrs=_SEL),
            'chave_pix': forms.TextInput(attrs={**_CTRL, 'placeholder': 'Informe a chave PIX'}),
            'iban': forms.TextInput(attrs={**_CTRL, 'placeholder': 'Ex: BR3801181521022070000636754C1'}),
            'swift_bic': forms.TextInput(attrs={**_CTRL, 'placeholder': 'Ex: BCSIBRRS'}),
            'endereco_banco': forms.TextInput(attrs={**_CTRL, 'placeholder': 'Cidade — UF/País'}),
            'beneficiario_nome': forms.TextInput(attrs={**_CTRL, 'placeholder': 'Se vazio, usa a razão social da empresa'}),
            'saldo_inicial': forms.NumberInput(attrs={**_CTRL, 'step': '0.01'}),
            'data_saldo_inicial': DateBRInput(attrs={**_CTRL}),
            'conta_principal': forms.CheckboxInput(attrs=_CHK),
            'ativa': forms.CheckboxInput(attrs=_CHK),
            'observacoes': forms.Textarea(attrs=_TEXTAREA),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        # empresa aceito por compatibilidade com quem instancia o form — os
        # bancos correspondentes agora são vinculados via conta_bancaria_correspondente_add,
        # não mais por um campo deste form.
        super().__init__(*args, **kwargs)


class BancoCorrespondenteForm(forms.ModelForm):
    class Meta:
        model = BancoCorrespondente
        fields = ['nome', 'swift_bic', 'moeda', 'endereco', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={**_CTRL, 'placeholder': 'Ex: Citibank N.A.'}),
            'swift_bic': forms.TextInput(attrs={**_CTRL, 'placeholder': 'Ex: CITIUS33'}),
            'moeda': forms.Select(attrs=_SEL),
            'endereco': forms.TextInput(attrs={**_CTRL, 'placeholder': '111 Wall Street, New York - USA'}),
            'ativo': forms.CheckboxInput(attrs=_CHK),
        }


class ImportarExtratoForm(forms.Form):
    tipo_arquivo = forms.ChoiceField(
        choices=ImportacaoExtrato.TIPO_ARQUIVO,
        widget=forms.Select(attrs=_SEL),
        label='Tipo de Arquivo',
    )
    arquivo = forms.FileField(
        widget=forms.FileInput(attrs={
            **_CTRL,
            'accept': '.ofx,.OFX,.ret,.RET,.txt,.cnab,.CNAB',
        }),
        label='Arquivo de Extrato',
        help_text='Formatos aceitos: OFX (internet banking) ou CNAB 240 (retorno bancário)',
    )

    def clean_arquivo(self):
        arquivo = self.cleaned_data.get('arquivo')
        if arquivo:
            if arquivo.size > 10 * 1024 * 1024:
                raise forms.ValidationError('O arquivo não pode exceder 10 MB.')
        return arquivo


class ConciliacaoManualForm(forms.Form):
    descricao_manual = forms.CharField(
        max_length=300,
        widget=forms.TextInput(attrs={**_CTRL, 'placeholder': 'Descreva este lançamento...'}),
        label='Descrição',
    )
    observacoes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={**_TEXTAREA, 'rows': '2'}),
        label='Observações',
    )
