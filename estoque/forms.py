"""
Forms do módulo Estoque
"""
from django import forms
from django.core.exceptions import ValidationError
from django.urls import reverse_lazy
from core.widgets import Select2AjaxWidget, DateBRInput
from .models import Armazem, LocalEstocagem, Lote, MovimentacaoEstoque
from produtos.models import Produto, UnidadeMedida


class ArmazemForm(forms.ModelForm):
    class Meta:
        model = Armazem
        fields = [
            'codigo', 'nome', 'tipo', 'localizacao', 'ggn_numero', 'fazenda', 'responsavel',
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
            'ggn_numero': forms.TextInput(attrs={'class': 'form-control'}),
            'fazenda': Select2AjaxWidget(ajax_url=reverse_lazy('cadastros:ajax_buscar_fazendas'), placeholder='Buscar fazenda...'),
            'responsavel': Select2AjaxWidget(ajax_url=reverse_lazy('rh:ajax_buscar_funcionarios'), placeholder='Buscar funcionário...'),
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
            from rh.models import Funcionario
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
            'fornecedor', 'nota_fiscal', 'valor_unitario', 'lote_producao', 'observacoes'
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
            'lote_producao': 'Lote de produção (colheita) que originou este lote, se aplicável. '
                              'Usado para rastreabilidade de Grower/GGN nas etiquetas de caixa.',
        }
        widgets = {
            'produto': Select2AjaxWidget(ajax_url=reverse_lazy('produtos:ajax_buscar_produtos'), placeholder='Buscar produto...'),
            'armazem': forms.Select(attrs={'class': 'form-select'}),
            'local_estocagem': forms.Select(attrs={'class': 'form-select'}),
            'numero_lote': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: L20240115-A ou LOTE-001'
            }),
            'data_fabricacao': DateBRInput(attrs={'class': 'form-control'}),
            'data_validade': DateBRInput(attrs={'class': 'form-control'}),
            'data_entrada': DateBRInput(attrs={'class': 'form-control'}),
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
            'fornecedor': Select2AjaxWidget(ajax_url=reverse_lazy('cadastros:ajax_buscar_fornecedores'), placeholder='Buscar fornecedor...'),
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
            'lote_producao': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        self.usuario = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)

        if self.empresa:
            from produtos.models import Produto, UnidadeMedida
            from cadastros.models import Fornecedor
            from operacoes_campo.models import LoteProducao

            # Filtrar por empresa (Produto usa categoria__empresa)
            self.fields['produto'].queryset = Produto.objects.filter(categoria__empresa=self.empresa, ativo=True)
            self.fields['armazem'].queryset = Armazem.objects.filter(empresa=self.empresa, ativo=True)
            self.fields['local_estocagem'].queryset = LocalEstocagem.objects.filter(
                armazem__empresa=self.empresa, ativo=True
            )
            self.fields['unidade_medida'].queryset = UnidadeMedida.objects.filter(empresa=self.empresa)
            self.fields['fornecedor'].queryset = Fornecedor.objects.filter(empresa=self.empresa, ativa=True)
            self.fields['lote_producao'].queryset = LoteProducao.objects.filter(
                empresa=self.empresa
            ).select_related('talhao', 'cultura').order_by('-id')
            self.fields['lote_producao'].required = False

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
    
    # Campo customizado para 'origem' com as choices definidas
    origem = forms.ChoiceField(
        label='Origem',
        choices=[('', '---------')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    
    # Campo lote como opcional
    lote = forms.ModelChoiceField(
        queryset=Lote.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    
    # Campos produto e unidade de medida
    produto = forms.ModelChoiceField(
        queryset=None,
        required=False,
        widget=Select2AjaxWidget(ajax_url=reverse_lazy('produtos:ajax_buscar_produtos'), placeholder='Buscar produto...'),
        label='Produto'
    )
    
    unidade_medida = forms.ModelChoiceField(
        queryset=None,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Unidade de Medida'
    )
    
    class Meta:
        model = MovimentacaoEstoque
        fields = [
            'tipo', 'origem', 'lote', 'produto', 'unidade_medida', 'quantidade', 'armazem_origem', 'local_origem',
            'armazem_destino', 'local_destino', 'documento',
            'observacao', 'justificativa'
        ]
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'origem': forms.Select(attrs={'class': 'form-select'}),
            'lote': forms.Select(attrs={'class': 'form-select'}),
            'produto': forms.Select(attrs={'class': 'form-select'}),
            'unidade_medida': forms.Select(attrs={'class': 'form-select'}),
            'quantidade': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0,00'}),
            'armazem_origem': forms.Select(attrs={'class': 'form-select'}),
            'local_origem': forms.Select(attrs={'class': 'form-select'}),
            'armazem_destino': forms.Select(attrs={'class': 'form-select'}),
            'local_destino': forms.Select(attrs={'class': 'form-select'}),
            'documento': forms.TextInput(attrs={'class': 'form-control'}),
            'observacao': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'justificativa': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        usuario = kwargs.pop('usuario', None)
        tipo_movimentacao = kwargs.pop('tipo_movimentacao', None)
        super().__init__(*args, **kwargs)
        
        self.empresa = empresa
        self.usuario = usuario
        self.tipo_movimentacao = tipo_movimentacao
        
        # Determina o tipo de movimentação
        tipo_mov = self.tipo_movimentacao or self.initial.get('tipo') or self.data.get('tipo') or 'ENTRADA'
        
        # Seta o initial value GARANTIDAMENTE
        self.initial['tipo'] = tipo_mov
        if 'tipo' in self.fields:
            self.fields['tipo'].initial = tipo_mov
        
        if self.empresa:
            # Popular querysets de produto e unidade_medida filtrados por empresa
            if 'produto' in self.fields:
                self.fields['produto'].queryset = Produto.objects.filter(
                    categoria__empresa=self.empresa, ativo=True
                ).order_by('nome')

            if 'unidade_medida' in self.fields:
                self.fields['unidade_medida'].queryset = UnidadeMedida.objects.filter(
                    empresa=self.empresa
                ).order_by('sigla')

            # Filtrar lotes da empresa
            if tipo_mov == 'ENTRADA':
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
            if 'armazem_origem' in self.fields:
                self.fields['armazem_origem'].queryset = Armazem.objects.filter(empresa=self.empresa, ativo=True)
            if 'armazem_destino' in self.fields:
                self.fields['armazem_destino'].queryset = Armazem.objects.filter(empresa=self.empresa, ativo=True)
            if 'local_origem' in self.fields:
                self.fields['local_origem'].queryset = LocalEstocagem.objects.filter(
                    armazem__empresa=self.empresa, ativo=True, bloqueado=False
                )
            if 'local_destino' in self.fields:
                self.fields['local_destino'].queryset = LocalEstocagem.objects.filter(
                    armazem__empresa=self.empresa, ativo=True, bloqueado=False
                )
        else:
            if 'produto' in self.fields:
                self.fields['produto'].queryset = Produto.objects.none()
            if 'unidade_medida' in self.fields:
                self.fields['unidade_medida'].queryset = UnidadeMedida.objects.none()
        # Ajustar campos baseado no tipo de movimentação
        if 'armazem_destino' in self.fields and tipo_mov in ['ENTRADA', 'SAIDA', 'AJUSTE', 'DEVOLUCAO']:
            self.fields['armazem_destino'].required = False
        if 'local_destino' in self.fields and tipo_mov in ['ENTRADA', 'SAIDA', 'AJUSTE', 'DEVOLUCAO']:
            self.fields['local_destino'].required = False
        # Filtrar origens relevantes por tipo
        origens_por_tipo = {
            'ENTRADA': ['COMPRA', 'PRODUCAO', 'DEVOLUCAO_CLIENTE', 'TRANSFERENCIA_ENTRADA', 'AJUSTE_ENTRADA'],
            'SAIDA': ['REQUISICAO', 'CONSUMO_PRODUCAO', 'VENDA', 'PERDA', 'TRANSFERENCIA_SAIDA', 'AJUSTE_SAIDA', 'DEVOLUCAO_FORNECEDOR'],
            'TRANSFERENCIA': ['TRANSFERENCIA_ENTRADA', 'TRANSFERENCIA_SAIDA'],
            'AJUSTE': ['AJUSTE_ENTRADA', 'AJUSTE_SAIDA'],
            'DEVOLUCAO': ['DEVOLUCAO_CLIENTE', 'DEVOLUCAO_FORNECEDOR'],
        }
        if 'origem' in self.fields:
            choices_filtradas = [
                choice for choice in MovimentacaoEstoque.ORIGEM_CHOICES
                if choice[0] in origens_por_tipo.get(tipo_mov, [])
            ]
            self.fields['origem'].choices = [('', '---------')] + choices_filtradas
            # Se houver apenas uma opção válida, seta como initial
            if len(choices_filtradas) == 1:
                self.fields['origem'].initial = choices_filtradas[0][0]
    
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
            # Se for movimentação direta (sem lote), recalcula estoque do produto
            if not movimentacao.lote and movimentacao.produto:
                if movimentacao.tipo in ['ENTRADA', 'SAIDA']:
                    self._atualizar_estoque_produto_direto(movimentacao)
        return movimentacao
    
    def _atualizar_estoque_produto_direto(self, movimentacao):
        """Atualiza estoque_atual do produto quando é movimentação direta sem lote"""
        from django.db.models import Sum, Q
        from decimal import Decimal
        
        produto = movimentacao.produto
        if not produto:
            return
        
        # Calcula estoque: soma de entradas - soma de saídas
        movimentacoes = MovimentacaoEstoque.objects.filter(
            Q(produto=produto) | Q(lote__produto=produto)
        )
        
        entrada = movimentacoes.filter(tipo='ENTRADA').aggregate(
            total=Sum('quantidade')
        )['total'] or Decimal('0.000')
        
        saida = movimentacoes.filter(tipo='SAIDA').aggregate(
            total=Sum('quantidade')
        )['total'] or Decimal('0.000')
        
        # Atualizar estoque do produto
        produto.estoque_atual = Decimal(entrada) - Decimal(saida)
        produto.save(update_fields=['estoque_atual'])


class EntradaEstoqueForm(MovimentacaoEstoqueForm):
    """Form específico para entrada de estoque"""
    
    def __init__(self, *args, **kwargs):
        # Extrai tipo_val antes de chamar super
        tipo_val = 'ENTRADA'
        if 'data' in kwargs and kwargs['data']:
            tipo_val = kwargs['data'].get('tipo', 'ENTRADA')
        elif 'initial' in kwargs and kwargs['initial']:
            tipo_val = kwargs['initial'].get('tipo', 'ENTRADA')
        
        # Garante que tipo_movimentacao seja passado para o formulário base
        kwargs['tipo_movimentacao'] = tipo_val
        
        # Garante que initial tenha o tipo correto
        if 'initial' not in kwargs:
            kwargs['initial'] = {}
        kwargs['initial']['tipo'] = tipo_val
        
        super().__init__(*args, **kwargs)
        
        # APÓS super().__init__(), garante que o campo 'tipo' tenha o valor inicial
        # Este passo CRUCIAL acontece DEPOIS que MovimentacaoEstoqueForm.__init__ já processou
        if 'tipo' in self.fields:
            self.fields['tipo'].initial = tipo_val
            # Força o valor no widget attrs se for um Select
            if hasattr(self.fields['tipo'].widget, 'attrs'):
                self.fields['tipo'].widget.attrs['data-initial'] = tipo_val
        
        # Remover apenas campos de localização não usados em entrada
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
