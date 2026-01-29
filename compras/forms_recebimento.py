"""
Formulários para Recebimento de Compras
"""
from django import forms
from django.forms import inlineformset_factory
from .models import RecebimentoCompra, ItemRecebimento, ItemPedidoCompra
from estoque.models import LocalEstocagem


class RecebimentoCompraForm(forms.ModelForm):
    """Formulário para Recebimento de Compra"""
    
    class Meta:
        model = RecebimentoCompra
        fields = [
            'pedido',
            'nota_fiscal',
            'serie_nota',
            'chave_nfe',
            'data_emissao_nf',
            'data_recebimento',
            'hora_recebimento',
            'valor_total_nf',
            'observacoes',
            'divergencias',
            'arquivo_nfe',
        ]
        widgets = {
            'nota_fiscal': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Número da NF-e'
                }
            ),
            'serie_nota': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': '1'
                }
            ),
            'chave_nfe': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': '44 dígitos da chave de acesso',
                    'maxlength': '44'
                }
            ),
            'data_emissao_nf': forms.DateInput(
                attrs={
                    'type': 'date',
                    'class': 'form-control'
                }
            ),
            'data_recebimento': forms.DateInput(
                attrs={
                    'type': 'date',
                    'class': 'form-control'
                }
            ),
            'hora_recebimento': forms.TimeInput(
                attrs={
                    'type': 'time',
                    'class': 'form-control'
                }
            ),
            'valor_total_nf': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'step': '0.01',
                    'placeholder': '0.00'
                }
            ),
            'observacoes': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': 'Observações gerais sobre o recebimento'
                }
            ),
            'divergencias': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': 'Registre aqui divergências de quantidade, qualidade, etc'
                }
            ),
            'arquivo_nfe': forms.FileInput(
                attrs={
                    'class': 'form-control',
                    'accept': '.xml'
                }
            ),
        }


class ItemRecebimentoForm(forms.ModelForm):
    """Formulário para Item do Recebimento"""
    
    # Campo auxiliar para exibir informações do item do pedido
    item_pedido_display = forms.CharField(
        label='Item do Pedido',
        required=False,
        disabled=True,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control-plaintext',
                'readonly': True
            }
        )
    )
    
    quantidade_pedida_display = forms.DecimalField(
        label='Qtd. Pedida',
        required=False,
        disabled=True,
        widget=forms.NumberInput(
            attrs={
                'class': 'form-control-plaintext',
                'readonly': True
            }
        )
    )
    
    quantidade_ja_recebida_display = forms.DecimalField(
        label='Já Recebido',
        required=False,
        disabled=True,
        widget=forms.NumberInput(
            attrs={
                'class': 'form-control-plaintext',
                'readonly': True
            }
        )
    )
    
    quantidade_pendente_display = forms.DecimalField(
        label='Pendente',
        required=False,
        disabled=True,
        widget=forms.NumberInput(
            attrs={
                'class': 'form-control-plaintext',
                'readonly': True
            }
        )
    )
    
    preco_unitario = forms.DecimalField(
        label='Valor Unitário',
        required=False,
        min_value=0,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': '0.00'
        })
    )
    
    valor_desconto = forms.DecimalField(
        label='Valor de Desconto',
        required=False,
        min_value=0,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': '0.00'
        })
    )
    
    class Meta:
        model = ItemRecebimento
        fields = [
            'item_pedido',
            'quantidade_recebida',
            'local_estoque',
            'lote',
            'data_fabricacao',
            'data_validade',
            'observacoes',
            'preco_unitario',
            'valor_desconto',
        ]
        widgets = {
            'item_pedido': forms.Select(
                attrs={
                    'class': 'form-select'
                }
            ),
            'quantidade_recebida': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'step': '0.001',
                    'min': '0.001',
                    'placeholder': '0.000'
                }
            ),
            'local_estoque': forms.Select(
                attrs={
                    'class': 'form-select'
                }
            ),
            'lote': forms.Select(
                attrs={
                    'class': 'form-select',
                }
            ),
            'data_fabricacao': forms.DateInput(
                attrs={
                    'type': 'date',
                    'class': 'form-control'
                }
            ),
            'data_validade': forms.DateInput(
                attrs={
                    'type': 'date',
                    'class': 'form-control'
                }
            ),
            'observacoes': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 2,
                    'placeholder': 'Observações sobre este item'
                }
            ),
        }
    
    def __init__(self, *args, **kwargs):
        pedido = kwargs.pop('pedido', None)
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        
        # Filtra itens do pedido
        if pedido:
            self.fields['item_pedido'].queryset = ItemPedidoCompra.objects.filter(
                pedido=pedido
            ).select_related('produto', 'unidade_medida')
        
        # Filtra locais de estoque por armazéns da empresa
        if empresa:
            armazens_ids = empresa.armazens.values_list('id', flat=True)
            self.fields['local_estoque'].queryset = LocalEstocagem.objects.filter(
                armazem_id__in=armazens_ids,
                ativo=True
            )
        
        # Filtra lotes pelo produto do item do pedido, se disponível
        produto = None
        if self.instance and self.instance.pk:
            item_pedido = self.instance.item_pedido
            produto = item_pedido.produto
            self.fields['item_pedido_display'].initial = str(item_pedido)
            self.fields['quantidade_pedida_display'].initial = item_pedido.quantidade_pedida
            self.fields['quantidade_ja_recebida_display'].initial = item_pedido.quantidade_recebida
            self.fields['quantidade_pendente_display'].initial = item_pedido.quantidade_pendente
        elif 'item_pedido' in self.data:
            try:
                item_pedido_id = self.data.get('item_pedido')
                from compras.models import ItemPedidoCompra
                item_pedido = ItemPedidoCompra.objects.get(pk=item_pedido_id)
                produto = item_pedido.produto
            except Exception:
                produto = None
        if produto:
            from estoque.models import Lote
            self.fields['lote'].queryset = Lote.objects.filter(produto=produto)
        else:
            from estoque.models import Lote
            self.fields['lote'].queryset = Lote.objects.all()



# Custom formset para passar empresa para cada form
from django.forms.models import BaseInlineFormSet

class ItemRecebimentoBaseFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)

    def get_form_kwargs(self, index):
        kwargs = super().get_form_kwargs(index)
        if self.empresa:
            kwargs['empresa'] = self.empresa
        return kwargs

ItemRecebimentoFormSet = inlineformset_factory(
    RecebimentoCompra,
    ItemRecebimento,
    form=ItemRecebimentoForm,
    formset=ItemRecebimentoBaseFormSet,
    extra=0,
    can_delete=True,
    min_num=1,
    validate_min=True,
)
