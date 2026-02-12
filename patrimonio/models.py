"""
Módulo de Patrimônio (Ativos da Empresa)
Permite registrar e controlar todos os bens da empresa, incluindo:
- Veículos e implementos
- Máquinas agrícolas
- Equipamentos
- Ferramentas
- Móveis e imóveis
"""

from django.db import models
from django.utils import timezone
from decimal import Decimal


class Patrimonio(models.Model):
    """Cadastro geral de patrimônio (ativos) da empresa"""
    
    CATEGORIA_CHOICES = [
        ('VEICULO', 'Veículo'),
        ('IMPLEMENTO', 'Implemento/Máquina Agrícola'),
        ('MAQUINA', 'Máquina/Equipamento Industrial'),
        ('FERRAMENTA', 'Ferramenta'),
        ('MOBILIARIO', 'Móvel'),
        ('IMOVEL', 'Imóvel'),
        ('EQUIPAMENTO', 'Equipamento'),
        ('OUTRO', 'Outro'),
    ]
    
    ESTADO_CHOICES = [
        ('NOVO', 'Novo'),
        ('BOM', 'Bom'),
        ('REGULAR', 'Regular'),
        ('RUIM', 'Ruim'),
        ('SUCATA', 'Sucata'),
        ('INATIVO', 'Inativo'),
    ]
    
    TIPO_DEPRECIACAO_CHOICES = [
        ('LINEAR', 'Linear'),
        ('ACELERADA', 'Acelerada'),
        ('NENHUMA', 'Nenhuma'),
    ]

    # Relação com empresa
    empresa = models.ForeignKey(
        'empresas.Empresa', on_delete=models.CASCADE, related_name='patrimonios', verbose_name='Empresa'
    )
    
    # Dados básicos
    numero_patrimonio = models.CharField('Número do Patrimônio', max_length=50, unique=False,
        help_text='Código/ID único do ativo (ex: PAT-001, VEI-0042)')
    descricao = models.CharField('Descrição', max_length=255,
        help_text='Nome/descrição do bem (ex: Trator Amarelo, Implemento Plantadeira)')
    categoria = models.CharField('Categoria', max_length=20, choices=CATEGORIA_CHOICES, default='VEICULO')
    
    # Vinculação com veículo (opcional)
    veiculo = models.OneToOneField(
        'cadastros.Vehicle', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='patrimonio', verbose_name='Veículo Vinculado',
        help_text='Se for um veículo/implemento, vincule-o aqui para evitar duplicação'
    )
    
    # Dados financeiros
    valor_inicial = models.DecimalField('Valor Inicial (R$)', max_digits=12, decimal_places=2,
        help_text='Valor de aquisição do bem')
    valor_atual = models.DecimalField('Valor Atual (R$)', max_digits=12, decimal_places=2,
        null=True, blank=True, help_text='Valor residual após depreciação')
    valor_residual = models.DecimalField('Valor Residual (R$)', max_digits=12, decimal_places=2,
        null=True, blank=True, help_text='Valor esperado ao final da vida útil')
    
    # Depreciação
    tipo_depreciacao = models.CharField('Tipo de Depreciação', max_length=20,
        choices=TIPO_DEPRECIACAO_CHOICES, default='LINEAR')
    vida_util_anos = models.IntegerField('Vida Útil (anos)', null=True, blank=True,
        help_text='Quantos anos se espera que o bem dure')
    percentual_depreciacao_anual = models.DecimalField('Depreciação Anual (%)', 
        max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Datas importantes
    data_aquisicao = models.DateField('Data de Aquisição', help_text='Data que o bem foi adquirido')
    data_cadastro = models.DateTimeField('Data de Cadastro', auto_now_add=True)
    data_atualizacao = models.DateTimeField('Última Atualização', auto_now=True)
    data_baixa = models.DateField('Data de Baixa', null=True, blank=True,
        help_text='Data em que o bem foi descartado/sucateado')
    
    # Localização e responsabilidade
    localizacao = models.CharField('Localização', max_length=150, blank=True,
        help_text='Onde o bem está armazenado/em uso (ex: Galpão A, Campo 1)')
    responsavel = models.ForeignKey(
        'cadastros.Funcionario', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='patrimonios_responsavel', verbose_name='Responsável',
        help_text='Quem é responsável pelo bem'
    )
    
    # Status
    estado = models.CharField('Estado', max_length=20, choices=ESTADO_CHOICES, default='NOVO')
    ativo = models.BooleanField('Ativo', default=True)
    
    # Observações
    observacoes = models.TextField('Observações', blank=True)
    
    class Meta:
        verbose_name = 'Patrimônio'
        verbose_name_plural = 'Patrimônios'
        ordering = ['-data_cadastro']
        indexes = [
            models.Index(fields=['empresa', 'ativo']),
            models.Index(fields=['numero_patrimonio']),
            models.Index(fields=['categoria']),
        ]
    
    def __str__(self):
        return f"{self.numero_patrimonio} - {self.descricao}"
    
    def calcular_depreciacao_acumulada(self):
        """Calcula a depreciação acumulada até hoje"""
        if not self.data_aquisicao or not self.vida_util_anos or not self.valor_inicial:
            return Decimal('0.00')
        
        try:
            from datetime import date
            dias_transcorridos = (date.today() - self.data_aquisicao).days
            anos_transcorridos = dias_transcorridos / 365.25
            
            if self.tipo_depreciacao == 'LINEAR':
                depreciacao_anual = self.valor_inicial / Decimal(max(self.vida_util_anos, 1))
                total_depreciacao = depreciacao_anual * Decimal(str(anos_transcorridos))
            else:
                # Depreciação acelerada (20% ao ano)
                total_depreciacao = self.valor_inicial * Decimal('0.20') * Decimal(str(anos_transcorridos))
            
            return min(total_depreciacao, self.valor_inicial)
        except Exception:
            return Decimal('0.00')
    
    def atualizar_valor_atual(self):
        """Atualiza o valor atual com base na depreciação"""
        if self.tipo_depreciacao == 'NENHUMA':
            self.valor_atual = self.valor_inicial
        else:
            depreciacao = self.calcular_depreciacao_acumulada()
            self.valor_atual = self.valor_inicial - depreciacao
            self.valor_atual = max(self.valor_atual, Decimal('0.00'))
        self.save(update_fields=['valor_atual'])
    
    @property
    def dias_desde_aquisicao(self):
        """Retorna dias desde aquisição"""
        from datetime import date
        if self.data_aquisicao:
            return (date.today() - self.data_aquisicao).days
        return 0


class PatrimonioDepreciacaoHistorico(models.Model):
    """Registro histórico de depreciações aplicadas"""
    patrimonio = models.ForeignKey(Patrimonio, on_delete=models.CASCADE, related_name='historico_depreciacao')
    data = models.DateField('Data', auto_now_add=True)
    valor_anterior = models.DecimalField('Valor Anterior', max_digits=12, decimal_places=2)
    valor_novo = models.DecimalField('Valor Novo', max_digits=12, decimal_places=2)
    depreciacao_aplicada = models.DecimalField('Depreciação Aplicada', max_digits=12, decimal_places=2)
    observacoes = models.TextField('Observações', blank=True)
    
    class Meta:
        verbose_name = 'Depreciação do Patrimônio'
        verbose_name_plural = 'Histórico de Depreciações'
        ordering = ['-data']
    
    def __str__(self):
        return f"{self.patrimonio} - {self.data}"


class PatrimonioMovimentacao(models.Model):
    """Registro de movimentações/transferências de patrimônio"""
    
    TIPO_MOVIMENTO_CHOICES = [
        ('TRANSFERENCIA', 'Transferência'),
        ('EMPRESTIMO', 'Empréstimo'),
        ('DEVOLUCAO', 'Devolução'),
        ('MANUTENCAO', 'Manutenção'),
        ('REPARACAO', 'Reparação'),
        ('OUTRO', 'Outro'),
    ]
    
    patrimonio = models.ForeignKey(Patrimonio, on_delete=models.CASCADE, related_name='movimentacoes')
    tipo = models.CharField('Tipo de Movimento', max_length=20, choices=TIPO_MOVIMENTO_CHOICES)
    data = models.DateTimeField('Data', auto_now_add=True)
    responsavel_anterior = models.ForeignKey(
        'cadastros.Funcionario', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='patrimonio_movimentos_anterior', verbose_name='Responsável Anterior'
    )
    responsavel_novo = models.ForeignKey(
        'cadastros.Funcionario', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='patrimonio_movimentos_novo', verbose_name='Responsável Novo'
    )
    localizacao_anterior = models.CharField('Localização Anterior', max_length=150, blank=True)
    localizacao_nova = models.CharField('Localização Nova', max_length=150, blank=True)
    observacoes = models.TextField('Observações', blank=True)
    
    class Meta:
        verbose_name = 'Movimentação do Patrimônio'
        verbose_name_plural = 'Movimentações de Patrimônio'
        ordering = ['-data']
    
    def __str__(self):
        return f"{self.patrimonio} - {self.get_tipo_display()} - {self.data}"
