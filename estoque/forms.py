"""
Forms do módulo Estoque
"""
from django import forms
from django.core.exceptions import ValidationError
from .models import Armazem, LocalEstocagem, Lote, MovimentacaoEstoque


class ArmazemForm(forms.ModelForm):
    class Meta:
        model = Armazem
        fields = [
            'codigo', 'nome', 'tipo', 'localizacao', 'fazenda', 'responsavel',
            'comprimento', 'largura', 'altura', 'densidade_media',
            'capacidade_m3', 'capacidade_kg', 'controla_temperatura',
            'temperatura_min', 'temperatura_max', 'observacoes', 'ativo'
        ]
        labels = {
            'comprimento': 'Comprimento (metros)',
            'largura': 'Largura (metros)',
            'altura': 'Altura/Pé-direito (metros)',
            'densidade_media': 'Densidade Média (kg/m³)',
            'capacidade_m3': 'Capacidade Total (m³)',
            'capacidade_kg': 'Capacidade Total (kg)',
        }
        help_texts = {
            'comprimento': 'Comprimento do armazém em metros',
            'largura': 'Largura do armazém em metros',
            'altura': 'Altura útil (pé-direito) em metros',
            'densidade_media': 'Ex: Grãos ≈ 750 kg/m³, Fertilizantes ≈ 900 kg/m³',
            'capacidade_m3': 'Calculado automaticamente ou digite manualmente',
            'capacidade_kg': 'Calculado automaticamente ou digite manualmente',
        }
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'form-control'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'localizacao': forms.TextInput(attrs={'class': 'form-control'}),
            'fazenda': forms.Select(attrs={'class': 'form-select'}),
            'responsavel': forms.Select(attrs={'class': 'form-select'}),
            'comprimento': forms.NumberInput(attrs={
                'class': 'form-control', 
                'step': '0.01',
                'id': 'id_comprimento',
                'placeholder': '0,00'
            }),
            'largura': forms.NumberInput(attrs={
                'class': 'form-control', 
                'step': '0.01',
                'id': 'id_largura',
                'placeholder': '0,00'
            }),
            'altura': forms.NumberInput(attrs={
                'class': 'form-control', 
                'step': '0.01',
                'id': 'id_altura',
                'placeholder': '0,00'
            }),
            'densidade_media': forms.NumberInput(attrs={
                'class': 'form-control', 
                'step': '0.01',
                'id': 'id_densidade_media',
                'placeholder': '750,00'
            }),
            'capacidade_m3': forms.NumberInput(attrs={
                'class': 'form-control', 
                'step': '0.01',
                'id': 'id_capacidade_m3',
                'readonly': True
            }),
            'capacidade_kg': forms.NumberInput(attrs={
                'class': 'form-control', 
                'step': '0.01',
                'id': 'id_capacidade_kg',
                'readonly': True
            }),
            'controla_temperatura': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'temperatura_min': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'temperatura_max': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        self.usuario = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)
        
        # Filtrar fazendas pela empresa
        if self.empresa:
            from cadastros.models import Fazenda
            self.fields['fazenda'].queryset = Fazenda.objects.filter(empresa=self.empresa)
            
        # Filtrar funcionários pela empresa
        if self.empresa:
            from cadastros.models import Funcionario
            self.fields['responsavel'].queryset = Funcionario.objects.filter(empresa=self.empresa)

    def save(self, commit=True):
        armazem = super().save(commit=False)
        if self.empresa:
            armazem.empresa = self.empresa
        if self.usuario and not armazem.pk:
            armazem.cadastrado_por = self.usuario
        if commit:
            armazem.save()
        return armazem


class LocalEstocagemForm(forms.ModelForm):
    class Meta:
        model = LocalEstocagem
        fields = [
            'armazem', 'codigo', 'descricao', 'tipo', 'capacidade_kg', 'ativo'
        ]
        widgets = {
            'armazem': forms.Select(attrs={'class': 'form-select'}),
            'codigo': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'capacidade_kg': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        self.usuario = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)
        
        # Filtrar armazéns pela empresa
        if self.empresa:
            self.fields['armazem'].queryset = Armazem.objects.filter(empresa=self.empresa, ativo=True)

    def save(self, commit=True):
        local = super().save(commit=False)
        if self.usuario and not local.pk:
            local.cadastrado_por = self.usuario
        if commit:
            local.save()
        return local


class LoteForm(forms.ModelForm):
    class Meta:
        model = Lote
        fields = [
            'produto', 'armazem', 'local_estocagem', 'numero_lote',
            'data_fabricacao', 'data_validade', 'data_entrada',
            'quantidade_inicial', 'quantidade_atual', 'unidade_medida',
            'fornecedor', 'nota_fiscal', 'valor_unitario', 'observacoes'
        ]
        labels = {
            'numero_lote': 'Número do Lote',
            'data_fabricacao': 'Data de Fabricação',
            'data_validade': 'Data de Validade',
            'data_entrada': 'Data de Entrada',
            'quantidade_inicial': 'Quantidade Inicial',
            'quantidade_atual': 'Quantidade Atual',
            'valor_unitario': 'Valor Unitário',
        }
        help_texts = {
            'numero_lote': 'Código único do lote do fabricante. Ex: L20240115-A, LOTE-001, 2024.01.001',
            'data_fabricacao': 'Data em que o produto foi fabricado/produzido',
            'data_validade': 'Data de vencimento do produto (importante para controle de validade)',
            'data_entrada': 'Data em que o lote entrou no estoque',
            'quantidade_inicial': 'Quantidade total recebida neste lote',
            'quantidade_atual': 'Quantidade disponível atualmente (pode diminuir com saídas)',
            'fornecedor': 'Fornecedor que entregou este lote',
            'nota_fiscal': 'Número da nota fiscal de entrada',
            'valor_unitario': 'Custo unitário do produto neste lote',
        }
        widgets = {
            'produto': forms.Select(attrs={'class': 'form-select'}),
            'armazem': forms.Select(attrs={'class': 'form-select'}),
            'local_estocagem': forms.Select(attrs={'class': 'form-select'}),
            'numero_lote': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: L20240115-A ou LOTE-001'
            }),
            'data_fabricacao': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_validade': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_entrada': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'quantidade_inicial': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': '0,00'
            }),
            'quantidade_atual': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': '0,00'
            }),
            'unidade_medida': forms.Select(attrs={'class': 'form-select'}),
            'fornecedor': forms.Select(attrs={'class': 'form-select'}),
            'nota_fiscal': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: 12345'
            }),
            'valor_unitario': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': '0,00'
            }),
            'observacoes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Observações adicionais sobre o lote...'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        self.usuario = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)
        
        if self.empresa:
            from produtos.models import Produto, UnidadeMedida
            from cadastros.models import Fornecedor
            
            # Filtrar por empresa (Produto usa categoria__empresa)
            self.fields['produto'].queryset = Produto.objects.filter(categoria__empresa=self.empresa, ativo=True)
            self.fields['armazem'].queryset = Armazem.objects.filter(empresa=self.empresa, ativo=True)
            self.fields['local_estocagem'].queryset = LocalEstocagem.objects.filter(
                armazem__empresa=self.empresa, ativo=True
            )
            self.fields['unidade_medida'].queryset = UnidadeMedida.objects.filter(empresa=self.empresa)
            self.fields['fornecedor'].queryset = Fornecedor.objects.filter(empresa=self.empresa, ativa=True)

    def save(self, commit=True):
        lote = super().save(commit=False)
        if self.empresa:
            lote.empresa = self.empresa
        if self.usuario and not lote.pk:
            lote.cadastrado_por = self.usuario
        if commit:
            lote.save()
        return lote


class MovimentacaoEstoqueForm(forms.ModelForm):
    """Form para todas as movimentações de estoque"""
    
    class Meta:
        model = MovimentacaoEstoque
        fields = [
            'tipo', 'origem', 'lote', 'quantidade', 'armazem_origem', 'local_origem',
            'armazem_destino', 'local_destino', 'documento',
            'observacao', 'justificativa'
        ]
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'origem': forms.Select(attrs={'class': 'form-select'}),
            'lote': forms.Select(attrs={'class': 'form-select'}),
            'quantidade': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'armazem_origem': forms.Select(attrs={'class': 'form-select'}),
            'local_origem': forms.Select(attrs={'class': 'form-select'}),
            'armazem_destino': forms.Select(attrs={'class': 'form-select'}),
            'local_destino': forms.Select(attrs={'class': 'form-select'}),
            'documento': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'NF, Requisição, OS, etc'}),
            'observacao': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'justificativa': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Obrigatório para ajustes e perdas'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        self.usuario = kwargs.pop('usuario', None)
        self.tipo_movimentacao = kwargs.pop('tipo_movimentacao', None)
        super().__init__(*args, **kwargs)
        
        if self.empresa:
            # Filtrar lotes da empresa
            # Para ENTRADA: mostrar todos os lotes (inclusive esgotados que receberão estoque)
            # Para SAIDA/TRANSFERENCIA: apenas lotes disponíveis com quantidade
            if self.tipo_movimentacao == 'ENTRADA':
                self.fields['lote'].queryset = Lote.objects.filter(
                    empresa=self.empresa
                ).exclude(
                    status='VENCIDO'
                ).select_related('produto', 'armazem').order_by('produto__nome', 'numero_lote')
                self.fields['lote'].help_text = 'Selecione o lote para adicionar estoque (inclui lotes esgotados)'
            else:
                self.fields['lote'].queryset = Lote.objects.filter(
                    empresa=self.empresa,
                    status='DISPONIVEL',
                    quantidade_atual__gt=0
                ).select_related('produto', 'armazem').order_by('produto__nome', 'numero_lote')
                self.fields['lote'].help_text = 'Apenas lotes disponíveis com estoque'
            
            # Filtrar armazéns e locais
            self.fields['armazem_origem'].queryset = Armazem.objects.filter(empresa=self.empresa, ativo=True)
            self.fields['armazem_destino'].queryset = Armazem.objects.filter(empresa=self.empresa, ativo=True)
            self.fields['local_origem'].queryset = LocalEstocagem.objects.filter(
                armazem__empresa=self.empresa, ativo=True, bloqueado=False
            )
            self.fields['local_destino'].queryset = LocalEstocagem.objects.filter(
                armazem__empresa=self.empresa, ativo=True, bloqueado=False
            )
            
        # Ajustar campos baseado no tipo de movimentação
        if self.tipo_movimentacao:
            self.initial['tipo'] = self.tipo_movimentacao
            
            # Campos não necessários para certos tipos
            if self.tipo_movimentacao in ['ENTRADA', 'SAIDA', 'AJUSTE', 'DEVOLUCAO']:
                self.fields['armazem_destino'].required = False
                self.fields['local_destino'].required = False
            
            # Filtrar origens relevantes por tipo
            origens_por_tipo = {
                'ENTRADA': ['COMPRA', 'PRODUCAO', 'DEVOLUCAO_CLIENTE', 'TRANSFERENCIA_ENTRADA', 'AJUSTE_ENTRADA'],
                'SAIDA': ['REQUISICAO', 'CONSUMO_PRODUCAO', 'VENDA', 'PERDA', 'TRANSFERENCIA_SAIDA', 'AJUSTE_SAIDA', 'DEVOLUCAO_FORNECEDOR'],
                'TRANSFERENCIA': ['TRANSFERENCIA_ENTRADA', 'TRANSFERENCIA_SAIDA'],
                'AJUSTE': ['AJUSTE_ENTRADA', 'AJUSTE_SAIDA'],
                'DEVOLUCAO': ['DEVOLUCAO_CLIENTE', 'DEVOLUCAO_FORNECEDOR'],
            }
            
            choices_filtradas = [
                choice for choice in MovimentacaoEstoque.ORIGEM_CHOICES
                if choice[0] in origens_por_tipo.get(self.tipo_movimentacao, [])
            ]
            self.fields['origem'].choices = [('', '---------')] + choices_filtradas
    
    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo')
        origem = cleaned_data.get('origem')
        quantidade = cleaned_data.get('quantidade')
        lote = cleaned_data.get('lote')
        armazem_destino = cleaned_data.get('armazem_destino')
        armazem_origem = cleaned_data.get('armazem_origem')
        justificativa = cleaned_data.get('justificativa')
        
        # Validar transferência
        if tipo == 'TRANSFERENCIA':
            if not armazem_destino:
                raise ValidationError({'armazem_destino': 'Obrigatório para transferências'})
            if armazem_origem and armazem_origem == armazem_destino:
                raise ValidationError({'armazem_destino': 'Deve ser diferente do armazém de origem'})
        
        # Validar quantidade disponível
        if lote and quantidade:
            if tipo in ['SAIDA', 'TRANSFERENCIA'] and quantidade > lote.quantidade_atual:
                raise ValidationError({
                    'quantidade': f'Quantidade indisponível. Disponível: {lote.quantidade_atual} {lote.unidade_medida.sigla}'
                })
        
        # Validar justificativa obrigatória
        if origem in ['AJUSTE_ENTRADA', 'AJUSTE_SAIDA', 'PERDA'] and not justificativa:
            raise ValidationError({'justificativa': 'Obrigatória para este tipo de movimentação'})
        
        return cleaned_data
    
    def save(self, commit=True):
        movimentacao = super().save(commit=False)
        if self.empresa:
            movimentacao.empresa = self.empresa
        if self.usuario:
            movimentacao.cadastrado_por = self.usuario
            movimentacao.requisitante = self.usuario
        if commit:
            movimentacao.save()
        return movimentacao


class EntradaEstoqueForm(MovimentacaoEstoqueForm):
    """Form específico para entrada de estoque"""
    
    def __init__(self, *args, **kwargs):
        kwargs['tipo_movimentacao'] = 'ENTRADA'
        super().__init__(*args, **kwargs)
        
        # Remover campos desnecessários
        self.fields.pop('armazem_origem', None)
        self.fields.pop('local_origem', None)
        self.fields.pop('armazem_destino', None)
        self.fields.pop('local_destino', None)


class SaidaEstoqueForm(MovimentacaoEstoqueForm):
    """Form específico para saída de estoque"""
    
    def __init__(self, *args, **kwargs):
        kwargs['tipo_movimentacao'] = 'SAIDA'
        super().__init__(*args, **kwargs)
        
        # Remover campos desnecessários
        self.fields.pop('armazem_destino', None)
        self.fields.pop('local_destino', None)


class TransferenciaEstoqueForm(MovimentacaoEstoqueForm):
    """Form específico para transferência entre armazéns"""
    
    def __init__(self, *args, **kwargs):
        kwargs['tipo_movimentacao'] = 'TRANSFERENCIA'
        super().__init__(*args, **kwargs)
        
        # Tornar destino obrigatório
        self.fields['armazem_destino'].required = True
