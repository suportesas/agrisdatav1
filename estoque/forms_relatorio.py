"""
Forms para relatórios do módulo Estoque
"""
from django import forms
from .models import Armazem, Lote
from produtos.models import Produto, Categoria


class FiltroRelatorioEstoqueForm(forms.Form):
    """Form para filtros do relatório de estoque"""
    
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
    
    # Filtros
    armazem = forms.ModelMultipleChoiceField(
        queryset=Armazem.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Armazém'
    )
    
    categoria = forms.ModelMultipleChoiceField(
        queryset=Categoria.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Categoria de Produto'
    )
    
    status_lote = forms.MultipleChoiceField(
        choices=Lote.STATUS_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Status do Lote'
    )
    
    apenas_baixo_estoque = forms.BooleanField(
        required=False,
        label='Apenas Produtos com Estoque Baixo',
        help_text='Mostra apenas produtos com estoque abaixo do mínimo'
    )
    
    apenas_vencidos = forms.BooleanField(
        required=False,
        label='Apenas Lotes Vencidos',
        help_text='Mostra apenas lotes com data de validade vencida'
    )
    
    # Formato e Envio
    formato = forms.ChoiceField(
        choices=FORMATO_CHOICES,
        widget=forms.RadioSelect,
        initial='pdf',
        label='Formato do Relatório'
    )

    enviar_para = forms.ChoiceField(
        choices=ENVIO_CHOICES,
        widget=forms.RadioSelect,
        initial='tela',
        label='Envio/Visualização',
        required=True
    )
    
    email_destino = forms.EmailField(
        required=False,
        label='Email de Destino',
        help_text='Email para enviar o relatório'
    )
    
    whatsapp_destino = forms.CharField(
        required=False,
        label='WhatsApp de Destino',
        help_text='Número com código do país (ex: 55119999999)'
    )
    
    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filtrar por empresa
        if empresa:
            self.fields['armazem'].queryset = Armazem.objects.filter(
                empresa=empresa
            ).order_by('nome')
            
            self.fields['categoria'].queryset = Categoria.objects.filter(
                empresa=empresa
            ).order_by('nome')
    
    def clean(self):
        cleaned_data = super().clean()
        enviar_para = cleaned_data.get('enviar_para')
        email = cleaned_data.get('email_destino')
        whatsapp = cleaned_data.get('whatsapp_destino')
        
        if enviar_para in ['email', 'ambos'] and not email:
            raise forms.ValidationError(
                'Email de destino é obrigatório para envio por email'
            )
        
        if enviar_para in ['whatsapp', 'ambos'] and not whatsapp:
            raise forms.ValidationError(
                'WhatsApp de destino é obrigatório para envio por WhatsApp'
            )
        
        return cleaned_data
