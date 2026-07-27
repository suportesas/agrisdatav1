"""
Forms para relatório de pedidos pendentes
"""
from django import forms
from core.widgets import DateBRInput
from cadastros.models import Fornecedor


class FiltroPedidosPendentesForm(forms.Form):
    """Form para filtros do relatório de pedidos pendentes"""
    
    FORMATO_CHOICES = [
        ('pdf', 'PDF'),
        ('excel', 'Excel'),
    ]
    
    ENVIO_CHOICES = [
        ('visualizar', 'Visualizar na Tela'),
        ('nenhum', 'Apenas Baixar'),
        ('email', 'Email'),
        ('whatsapp', 'WhatsApp'),
        ('ambos', 'Email e WhatsApp'),
    ]
    
    # Filtros
    fornecedor = forms.ModelMultipleChoiceField(
        queryset=Fornecedor.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Fornecedor'
    )
    
    data_inicio = forms.DateField(
        required=False,
        label='Data Início',
        widget=DateBRInput(attrs={})
    )
    
    data_fim = forms.DateField(
        required=False,
        label='Data Fim',
        widget=DateBRInput(attrs={})
    )
    
    apenas_parciais = forms.BooleanField(
        required=False,
        initial=False,
        label='Apenas Parcialmente Recebidos',
        help_text='Mostra apenas pedidos que foram parcialmente recebidos'
    )
    
    # Configurações de saída
    formato = forms.ChoiceField(
        choices=FORMATO_CHOICES,
        widget=forms.RadioSelect,
        initial='pdf',
        label='Formato'
    )
    
    enviar_para = forms.ChoiceField(
        choices=ENVIO_CHOICES,
        widget=forms.RadioSelect,
        initial='visualizar',
        label='Enviar Relatório'
    )
    
    email_destino = forms.EmailField(
        required=False,
        label='Email de Destino',
        widget=forms.EmailInput(attrs={'placeholder': 'email@exemplo.com'})
    )
    
    whatsapp_destino = forms.CharField(
        required=False,
        max_length=20,
        label='WhatsApp',
        widget=forms.TextInput(attrs={'placeholder': '+5511999999999'})
    )
    
    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        
        if empresa:
            self.fields['fornecedor'].queryset = Fornecedor.objects.filter(
                empresa=empresa, ativa=True
            ).order_by('nome')
    
    def clean(self):
        cleaned_data = super().clean()
        enviar_para = cleaned_data.get('enviar_para')
        email = cleaned_data.get('email_destino')
        whatsapp = cleaned_data.get('whatsapp_destino')
        
        if enviar_para in ['email', 'ambos'] and not email:
            self.add_error('email_destino', 'Email é obrigatório para este tipo de envio')
        
        if enviar_para in ['whatsapp', 'ambos'] and not whatsapp:
            self.add_error('whatsapp_destino', 'WhatsApp é obrigatório para este tipo de envio')
        
        # Validar datas
        data_inicio = cleaned_data.get('data_inicio')
        data_fim = cleaned_data.get('data_fim')
        
        if data_inicio and data_fim and data_inicio > data_fim:
            self.add_error('data_fim', 'Data fim deve ser maior que data início')
        
        return cleaned_data
