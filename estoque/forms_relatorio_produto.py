"""
Forms para relatório de estoque por produto
"""
from django import forms
from estoque.models import Armazem
from produtos.models import Categoria


class FiltroRelatorioProdutoForm(forms.Form):
    """Form para filtros do relatório de estoque por produto"""
    
    FORMATO_CHOICES = [
        ('pdf', 'PDF'),
        ('excel', 'Excel'),
    ]
    
    ORDENACAO_CHOICES = [
        ('produto', 'Produto'),
        ('categoria', 'Categoria'),
        ('estoque', 'Estoque Atual'),
        ('status', 'Status'),
    ]
    
    ENVIO_CHOICES = [
        ('visualizar', 'Visualizar na Tela'),
        ('nenhum', 'Apenas Baixar'),
        ('email', 'Email'),
        ('whatsapp', 'WhatsApp'),
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
        label='Categoria'
    )
    
    apenas_baixo_estoque = forms.BooleanField(
        required=False,
        label='Apenas Produtos com Estoque Baixo',
        help_text='Mostra apenas produtos com estoque abaixo do mínimo'
    )
    
    incluir_zerados = forms.BooleanField(
        required=False,
        initial=False,
        label='Incluir Produtos Zerados',
        help_text='Inclui produtos com estoque atual = 0'
    )
    
    # Ordenação
    ordenacao = forms.ChoiceField(
        choices=ORDENACAO_CHOICES,
        widget=forms.RadioSelect,
        initial='produto',
        label='Ordenar por'
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
            self.fields['armazem'].queryset = Armazem.objects.filter(
                empresa=empresa, ativo=True
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
            self.add_error('email_destino', 'Email é obrigatório para este tipo de envio')
        
        if enviar_para in ['whatsapp', 'ambos'] and not whatsapp:
            self.add_error('whatsapp_destino', 'WhatsApp é obrigatório para este tipo de envio')
        
        return cleaned_data
