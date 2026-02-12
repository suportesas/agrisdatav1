"""
Form para relatorio de ranking de compras por fornecedor
"""
from django import forms


class FiltroRelatorioFornecedorRankingForm(forms.Form):
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

    data_inicio = forms.DateField(
        required=False,
        label='Data Inicial (Emissao NF)',
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )

    data_fim = forms.DateField(
        required=False,
        label='Data Final (Emissao NF)',
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
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

    def clean(self):
        cleaned_data = super().clean()
        enviar_para = cleaned_data.get('enviar_para')
        email = cleaned_data.get('email_destino')
        whatsapp = cleaned_data.get('whatsapp_destino')
        data_inicio = cleaned_data.get('data_inicio')
        data_fim = cleaned_data.get('data_fim')

        if data_inicio and data_fim and data_inicio > data_fim:
            raise forms.ValidationError('Data inicial nao pode ser maior que a data final')

        if enviar_para in ['email', 'ambos'] and not email:
            raise forms.ValidationError(
                'Email de destino e obrigatorio para envio por email'
            )

        if enviar_para in ['whatsapp', 'ambos'] and not whatsapp:
            raise forms.ValidationError(
                'WhatsApp de destino e obrigatorio para envio por WhatsApp'
            )

        return cleaned_data
