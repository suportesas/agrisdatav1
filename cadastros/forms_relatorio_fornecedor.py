"""
Form para relatorio de fornecedores
"""
from django import forms
from .models import CategoriaFornecedor, UF_CHOICES


class FiltroRelatorioFornecedorForm(forms.Form):
    FORMATO_CHOICES = [
        ('pdf', 'PDF'),
        ('excel', 'Excel'),
    ]

    ENVIO_CHOICES = [
        ('tela', 'Visualizar na tela'),
        ('nenhum', 'Apenas Baixar'),
        ('email', 'Enviar por Email'),
        ('whatsapp', 'Enviar por WhatsApp'),
        ('ambos', 'Email e WhatsApp'),
    ]

    STATUS_CHOICES = [
        ('', 'Todos'),
        ('ATIVO', 'Ativo'),
        ('INATIVO', 'Inativo'),
    ]

    RISCO_CHOICES = [
        ('', 'Todos'),
        ('BAIXO', 'Baixo'),
        ('MEDIO', 'Medio'),
        ('ALTO', 'Alto'),
    ]

    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        label='Status',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    cidade = forms.CharField(
        required=False,
        label='Cidade',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Cidade'})
    )

    uf = forms.ChoiceField(
        choices=[('', 'Todos')] + list(UF_CHOICES),
        required=False,
        label='UF',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    categoria = forms.ModelChoiceField(
        queryset=CategoriaFornecedor.objects.none(),
        required=False,
        label='Categoria',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    classificacao_risco = forms.ChoiceField(
        choices=RISCO_CHOICES,
        required=False,
        label='Classificacao de Risco',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    formato = forms.ChoiceField(
        choices=FORMATO_CHOICES,
        widget=forms.RadioSelect,
        initial='pdf',
        label='Formato do Relatorio'
    )

    enviar_para = forms.ChoiceField(
        choices=ENVIO_CHOICES,
        widget=forms.RadioSelect,
        initial='tela',
        label='Envio/Visualizacao',
        required=True
    )

    email_destino = forms.EmailField(
        required=False,
        label='Email de Destino',
        help_text='Email para enviar o relatorio',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@exemplo.com'})
    )

    whatsapp_destino = forms.CharField(
        required=False,
        label='WhatsApp de Destino',
        help_text='Numero com codigo do pais (ex: 55119999999)',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '5511999999999'})
    )

    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        qs = CategoriaFornecedor.objects.all()
        if empresa:
            qs = qs.filter(empresa=empresa)
        self.fields['categoria'].queryset = qs.order_by('nome')

    def clean(self):
        cleaned_data = super().clean()
        enviar_para = cleaned_data.get('enviar_para')
        email = cleaned_data.get('email_destino')
        whatsapp = cleaned_data.get('whatsapp_destino')

        if enviar_para in ['email', 'ambos'] and not email:
            raise forms.ValidationError(
                'Email de destino e obrigatorio para envio por email'
            )

        if enviar_para in ['whatsapp', 'ambos'] and not whatsapp:
            raise forms.ValidationError(
                'WhatsApp de destino e obrigatorio para envio por WhatsApp'
            )

        return cleaned_data
