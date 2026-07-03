"""
Formulários para o módulo de Compras
"""
from django import forms
from django.forms import inlineformset_factory, BaseInlineFormSet
from .models import (
    SolicitacaoCompra,
    ItemSolicitacaoCompra,
    Cotacao,
    ItemCotacao,
    FornecedorCotacao,
    SolicitacaoMensagem,
    PlanejamentoComprasEmbalagem,
    ItemPlanejamentoEmbalagem,
)

# Classe base do formset para passar empresa para todos os formulários do formset de propostas
class BaseFornecedorCotacaoFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)

    def _construct_form(self, i, **kwargs):
        kwargs['empresa'] = self.empresa
        return super()._construct_form(i, **kwargs)
"""
Formulários para o módulo de Compras
"""
from django import forms
from django.forms import inlineformset_factory
from .models import (
    SolicitacaoCompra,
    ItemSolicitacaoCompra,
    Cotacao,
    ItemCotacao,
    FornecedorCotacao,
    SolicitacaoMensagem
)


class SolicitacaoCompraForm(forms.ModelForm):
    """Formulário para Solicitação de Compra"""
    
    class Meta:
        model = SolicitacaoCompra
        fields = [
            'data_necessidade',
            'justificativa',
            'departamento',
            'emergencial',
            'justificativa_emergencial',
            'observacoes',
        ]
        widgets = {
            'data_necessidade': forms.DateInput(
                attrs={
                    'type': 'date',
                    'class': 'form-control'
                }
            ),
            'justificativa': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': 'Descreva o motivo da solicitação'
                }
            ),
            'departamento': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Ex: Produção, Administrativo, etc'
                }
            ),
            'emergencial': forms.CheckboxInput(
                attrs={
                    'class': 'form-check-input',
                    'id': 'id_emergencial'
                }
            ),
            'justificativa_emergencial': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': 'Explique o motivo da emergência (obrigatório se marcado como emergencial)',
                    'id': 'id_justificativa_emergencial'
                }
            ),
            'observacoes': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 2,
                    'placeholder': 'Observações adicionais (opcional)'
                }
            ),
        }
        labels = {
            'data_necessidade': 'Data de Necessidade *',
            'justificativa': 'Justificativa *',
            'departamento': 'Departamento',
            'emergencial': 'Compra Emergencial',
            'justificativa_emergencial': 'Justificativa da Emergência *',
            'observacoes': 'Observações',
        }
    
    def clean(self):
        cleaned_data = super().clean()
        emergencial = cleaned_data.get('emergencial')
        justificativa_emergencial = cleaned_data.get('justificativa_emergencial')
        
        if emergencial and not justificativa_emergencial:
            raise forms.ValidationError(
                'É obrigatório fornecer uma justificativa para compras emergenciais.'
            )
        
        return cleaned_data


class ItemSolicitacaoCompraForm(forms.ModelForm):
    """Formulário para Item da Solicitação"""
    
    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        
        # Filtra produtos por empresa (através da categoria)
        if empresa:
            from produtos.models import Produto
            self.fields['produto'].queryset = Produto.objects.filter(
                categoria__empresa=empresa,
                ativo=True
            ).select_related('categoria').order_by('nome')
            
            from produtos.models import UnidadeMedida
            self.fields['unidade_medida'].queryset = UnidadeMedida.objects.filter(
                empresa=empresa
            ).order_by('nome')
    
    class Meta:
        model = ItemSolicitacaoCompra
        fields = [
            'produto',
            'quantidade',
            'unidade_medida',
            'especificacao',
            'observacoes',
        ]
        widgets = {
            'produto': forms.Select(
                attrs={
                    'class': 'form-select form-select-sm',
                    'required': True
                }
            ),
            'quantidade': forms.NumberInput(
                attrs={
                    'class': 'form-control form-control-sm',
                    'step': '0.001',
                    'min': '0.001',
                    'placeholder': '0,000',
                    'required': True
                }
            ),
            'unidade_medida': forms.Select(
                attrs={
                    'class': 'form-select form-select-sm',
                    'required': True
                }
            ),
            'especificacao': forms.Textarea(
                attrs={
                    'class': 'form-control form-control-sm',
                    'rows': 2,
                    'placeholder': 'Detalhes técnicos, marca, modelo...'
                }
            ),
            'observacoes': forms.Textarea(
                attrs={
                    'class': 'form-control form-control-sm',
                    'rows': 2,
                    'placeholder': 'Observações adicionais (opcional)'
                }
            ),
        }


# Classe base do formset para passar empresa
class BaseItemSolicitacaoFormSet(forms.BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
    
    def _construct_form(self, i, **kwargs):
        kwargs['empresa'] = self.empresa
        return super()._construct_form(i, **kwargs)


# Formset para itens da solicitação
ItemSolicitacaoFormSet = inlineformset_factory(
    SolicitacaoCompra,
    ItemSolicitacaoCompra,
    form=ItemSolicitacaoCompraForm,
    formset=BaseItemSolicitacaoFormSet,
    extra=0,  # Começa sem formas extras (o JavaScript adiciona se necessário)
    can_delete=True,
    min_num=1,  # Mínimo de 1 item
    validate_min=True,
)


class CotacaoForm(forms.ModelForm):
    """Formulário para Cotação"""
    
    class Meta:
        model = Cotacao
        fields = [
            'data_limite_resposta',
            'observacoes',
        ]
        widgets = {
            'data_limite_resposta': forms.DateInput(
                attrs={
                    'type': 'date',
                    'class': 'form-control'
                }
            ),
            'observacoes': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': 'Instruções para fornecedores (opcional)'
                }
            ),
        }
        labels = {
            'data_limite_resposta': 'Data Limite para Resposta',
            'observacoes': 'Observações',
        }


class ItemCotacaoForm(forms.ModelForm):
    """Formulário para Item da Cotação"""
    
    class Meta:
        model = ItemCotacao
        fields = ['quantidade', 'especificacao']
        widgets = {
            'quantidade': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'readonly': True
                }
            ),
            'especificacao': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 2,
                    'readonly': True
                }
            ),
        }


class FornecedorCotacaoForm(forms.ModelForm):
    """Formulário para Proposta do Fornecedor"""
    
    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        from cadastros.models import Fornecedor
        if empresa:
            self.fields['fornecedor'].queryset = Fornecedor.objects.filter(empresa=empresa, ativa=True).order_by('nome')
        else:
            self.fields['fornecedor'].queryset = Fornecedor.objects.none()
        # Se for um formulário existente, mantém como HiddenInput (não editável)
        if self.instance.pk:
            self.fields['fornecedor'].widget = forms.HiddenInput()
        else:
            self.fields['fornecedor'].widget = forms.Select(attrs={'class': 'form-select fornecedor-select'})

    class Meta:
        model = FornecedorCotacao
        fields = [
            'fornecedor',
            'preco_unitario',
            'prazo_entrega',
            'forma_pagamento',
            'condicao_pagamento',
            'marca',
            'observacoes',
        ]
        widgets = {
            'fornecedor': forms.HiddenInput(),
            'preco_unitario': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'step': '0.01',
                    'min': '0.01',
                    'placeholder': 'R$ 0,00'
                }
            ),
            'prazo_entrega': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'min': '1',
                    'placeholder': 'Dias úteis'
                }
            ),
            'forma_pagamento': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Ex: Boleto, PIX, etc'
                }
            ),
            'condicao_pagamento': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Ex: 30/60 dias, à vista'
                }
            ),
            'marca': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Marca do produto'
                }
            ),
            'observacoes': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 2,
                    'placeholder': 'Observações adicionais'
                }
            ),
        }


# Formset para propostas dos fornecedores
FornecedorCotacaoFormSet = inlineformset_factory(
    ItemCotacao,
    FornecedorCotacao,
    form=FornecedorCotacaoForm,
    formset=BaseFornecedorCotacaoFormSet,
    extra=0,  # Não exibe formulários extras em branco
    can_delete=True,
)

class SolicitacaoMensagemForm(forms.ModelForm):
    class Meta:
        model = SolicitacaoMensagem
        fields = ['mensagem']
        widgets = {
            'mensagem': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Digite sua mensagem para o solicitante/aprovador...'
            })
        }
        labels = {
            'mensagem': 'Mensagem',
        }


# ============================================================
# PLANEJAMENTO DE COMPRAS DE EMBALAGENS
# ============================================================

class PlanejamentoComprasEmbalagemForm(forms.ModelForm):
    class Meta:
        model = PlanejamentoComprasEmbalagem
        fields = ['safra', 'nome', 'data_inicio', 'data_fim', 'responsavel', 'observacoes']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Planejamento Embalagens Manga Tommy 2025'}),
            'data_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'data_fim': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'safra': forms.Select(attrs={'class': 'form-select'}),
            'responsavel': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        if empresa:
            from cadastros.models import Safra
            from usuarios.models import Usuario
            self.fields['safra'].queryset = Safra.objects.filter(
                fazenda__empresa=empresa
            ).order_by('-ano', 'nome')
            self.fields['responsavel'].queryset = Usuario.objects.filter(
                empresa=empresa, is_active=True
            ).order_by('first_name', 'last_name')
        self.fields['safra'].required = False


class ItemPlanejamentoEmbalagemForm(forms.ModelForm):
    class Meta:
        model = ItemPlanejamentoEmbalagem
        fields = [
            'produto', 'fase', 'data_prevista',
            'quantidade_planejada', 'unidade_medida',
            'preco_estimado_unitario', 'preco_atual_unitario',
            'fornecedor_preferencial',
            'observacoes',
        ]
        widgets = {
            'produto': forms.HiddenInput(),
            'fase': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'data_prevista': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}, format='%Y-%m-%d'),
            'quantidade_planejada': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01', 'min': '0.01'}),
            'unidade_medida': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'preco_estimado_unitario': forms.NumberInput(attrs={'class': 'form-control form-control-sm preco-estimado', 'step': '0.0001', 'min': '0'}),
            'preco_atual_unitario': forms.NumberInput(attrs={'class': 'form-control form-control-sm preco-atual', 'step': '0.0001', 'min': '0'}),
            'fornecedor_preferencial': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'observacoes': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Obs...'}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        if empresa:
            from produtos.models import Produto, UnidadeMedida
            from cadastros.models import Fornecedor
            self.fields['produto'].queryset = Produto.objects.filter(
                categoria__empresa=empresa, ativo=True
            )
            self.fields['unidade_medida'].queryset = UnidadeMedida.objects.filter(
                empresa=empresa
            ).order_by('nome')
            self.fields['fornecedor_preferencial'].queryset = Fornecedor.objects.filter(
                empresa=empresa, ativa=True
            ).order_by('nome')
        self.fields['produto'].required = True
        self.fields['fornecedor_preferencial'].required = False
        self.fields['observacoes'].required = False
        self.fields['preco_atual_unitario'].required = False


class BaseItemPlanejamentoFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)

    def _construct_form(self, i, **kwargs):
        kwargs['empresa'] = self.empresa
        return super()._construct_form(i, **kwargs)

    def get_form_kwargs(self, index):
        kwargs = super().get_form_kwargs(index)
        kwargs['empresa'] = self.empresa
        return kwargs


ItemPlanejamentoFormSet = inlineformset_factory(
    PlanejamentoComprasEmbalagem,
    ItemPlanejamentoEmbalagem,
    form=ItemPlanejamentoEmbalagemForm,
    formset=BaseItemPlanejamentoFormSet,
    extra=1,
    min_num=1,
    validate_min=True,
    can_delete=True,
)


class RevisarPrecosItemForm(forms.ModelForm):
    """Form simplificado para a tela de revisão de preços."""
    class Meta:
        model = ItemPlanejamentoEmbalagem
        fields = ['preco_atual_unitario', 'observacoes']
        widgets = {
            'preco_atual_unitario': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm preco-campo',
                'step': '0.0001', 'min': '0',
            }),
            'observacoes': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Motivo da revisão...',
            }),
        }
