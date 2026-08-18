"""
Operações de Campo — OS, Colheita, Caderno de Campo, Pluviometria, Qualidade, Planejamento de Custo
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, FileExtensionValidator, RegexValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta

idiarn_validator = RegexValidator(
    regex=r'^\d{2}\.\d{6}\.\d{3}\.\d{2}\.\d{7}$',
    message='Formato esperado: NN.NNNNNN.NNN.NN.NNNNNNN (ex: 24.003071.318.22.0064006)'
)


# ============================================================================
# CONFIGURAÇÃO DE CUSTO DE MÁQUINA
# ============================================================================

class CustoHoraMaquina(models.Model):
    """Custo/hora de operação: depreciação + combustível + reserva de manutenção"""

    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='custos_hora_maquina', verbose_name='Empresa')
    veiculo = models.ForeignKey('frota.Vehicle', on_delete=models.CASCADE, related_name='configuracoes_custo', verbose_name='Veículo/Máquina')
    preco_combustivel = models.DecimalField('Preço do Combustível (R$/L)', max_digits=8, decimal_places=3, validators=[MinValueValidator(Decimal('0.001'))])
    reserva_manutencao_hora = models.DecimalField('Reserva de Manutenção (R$/h)', max_digits=8, decimal_places=2, default=Decimal('5.00'), validators=[MinValueValidator(Decimal('0.00'))])
    horas_anuais_trabalho = models.DecimalField('Horas Anuais de Trabalho', max_digits=8, decimal_places=2, default=Decimal('1000.00'), validators=[MinValueValidator(Decimal('1.00'))])
    ativo = models.BooleanField('Configuração Ativa', default=True)
    data_referencia = models.DateField('Data de Referência')
    data_cadastro = models.DateTimeField('Data de Cadastro', auto_now_add=True)
    data_atualizacao = models.DateTimeField('Última Atualização', auto_now=True)
    cadastrado_por = models.ForeignKey('usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True, related_name='custos_maquina_cadastrados', verbose_name='Cadastrado por')

    class Meta:
        db_table = 'cadastros_custohoramaquina'
        verbose_name = 'Custo/Hora de Máquina'
        verbose_name_plural = 'Custos/Hora de Máquinas'
        ordering = ['-data_referencia']
        indexes = [
            models.Index(fields=['empresa', 'ativo']),
            models.Index(fields=['veiculo', '-data_referencia']),
        ]

    def __str__(self):
        return f"{self.veiculo} — R$ {self.custo_hora_calculado:.2f}/h ({self.data_referencia})"

    @property
    def custo_hora_calculado(self):
        try:
            patrimonio = self.veiculo.patrimonio
            dep_anual = patrimonio.depreciacao_anual() if hasattr(patrimonio, 'depreciacao_anual') else (
                patrimonio.valor_inicial / max(patrimonio.vida_util_anos, 1)
            )
        except Exception:
            dep_anual = Decimal('0')
        dep_hora = dep_anual / self.horas_anuais_trabalho if self.horas_anuais_trabalho else Decimal('0')
        consumo = self.veiculo.consumo_medio or Decimal('0')
        custo_comb = consumo * self.preco_combustivel
        return dep_hora + custo_comb + self.reserva_manutencao_hora


# ============================================================================
# CLASSIFICAÇÃO DE SERVIÇOS AGRÍCOLAS
# ============================================================================

class TipoServicoOS(models.Model):
    """Tipo macro de serviço. empresa=None = registro global."""

    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, null=True, blank=True, related_name='tipos_servico_os', verbose_name='Empresa')
    nome = models.CharField('Nome', max_length=100)
    descricao = models.CharField('Descrição', max_length=255, blank=True)
    icone = models.CharField('Ícone Bootstrap', max_length=60, blank=True, default='bi-tools')
    ordem = models.PositiveSmallIntegerField('Ordem', default=0)
    ativo = models.BooleanField('Ativo', default=True)
    tipo_legado = models.CharField('Tipo Legado', max_length=30, blank=True)

    class Meta:
        db_table = 'cadastros_tiposervicoos'
        verbose_name = 'Tipo de Serviço (OS)'
        verbose_name_plural = 'Tipos de Serviço (OS)'
        ordering = ['ordem', 'nome']

    def __str__(self):
        return self.nome


class SubtipoServicoOS(models.Model):
    """Operação específica dentro de um tipo de serviço."""

    tipo_servico = models.ForeignKey(TipoServicoOS, on_delete=models.CASCADE, related_name='subtipos', verbose_name='Tipo de Serviço')
    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, null=True, blank=True, related_name='subtipos_servico_os', verbose_name='Empresa')
    nome = models.CharField('Nome', max_length=100)
    descricao = models.CharField('Descrição', max_length=255, blank=True)
    ordem = models.PositiveSmallIntegerField('Ordem', default=0)
    ativo = models.BooleanField('Ativo', default=True)
    subtipo_legado = models.CharField(
        'Subtipo Legado', max_length=30, blank=True,
        help_text='Valor interno usado por automações (ex: TRANSPLANTE, REPLANTIO)',
    )

    class Meta:
        db_table = 'cadastros_subtiposervicoos'
        verbose_name = 'Operação de Serviço (OS)'
        verbose_name_plural = 'Operações de Serviço (OS)'
        ordering = ['tipo_servico__ordem', 'ordem', 'nome']

    def __str__(self):
        return f"{self.tipo_servico.nome} / {self.nome}"


class ModalidadeExecucaoOS(models.Model):
    """Como o serviço foi realizado: Tratorizada, Costal, Drone, Manual, Terceirizada."""

    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, null=True, blank=True, related_name='modalidades_execucao_os', verbose_name='Empresa')
    nome = models.CharField('Nome', max_length=100)
    descricao = models.CharField('Descrição', max_length=255, blank=True)
    ordem = models.PositiveSmallIntegerField('Ordem', default=0)
    ativo = models.BooleanField('Ativo', default=True)

    class Meta:
        db_table = 'cadastros_modalidadeexecucaoos'
        verbose_name = 'Modalidade de Execução (OS)'
        verbose_name_plural = 'Modalidades de Execução (OS)'
        ordering = ['ordem', 'nome']

    def __str__(self):
        return self.nome


# ============================================================================
# ORDEM DE SERVIÇO
# ============================================================================

class OrdemServico(models.Model):
    """OS para atividades agrícolas em talhões. RN-03: conclusão exige foto."""

    TIPO_CHOICES = [
        ('PREPARO_SOLO', 'Preparo de Solo'), ('PULV_MECANICA', 'Pulverização Mecânica'),
        ('PULV_COSTAL', 'Pulverização Costal'), ('PLANTIO', 'Plantio'),
        ('IRRIGACAO', 'Irrigação'), ('ADUBACAO', 'Adubação/Fertirrigação'),
        ('COLHEITA', 'Colheita'), ('MANUTENCAO', 'Manutenção de Infraestrutura'), ('OUTRO', 'Outro'),
    ]
    STATUS_CHOICES = [
        ('ABERTA', 'Aberta'), ('APROVADA', 'Aprovada'),
        ('EM_ANDAMENTO', 'Em Andamento'), ('CONCLUIDA', 'Concluída'), ('CANCELADA', 'Cancelada'),
    ]
    UNIDADE_COBRANCA_CHOICES = [
        ('POR_HA', 'Por Hectare (R$/ha)'), ('DIARIA', 'Diária'), ('FECHADO', 'Valor Fechado'),
    ]

    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='ordens_servico', verbose_name='Empresa')
    numero = models.CharField('Número', max_length=30, unique=True, blank=True, help_text='Auto-gerado: OS-YYYY-NNNNN')
    tipo = models.CharField('Tipo de Serviço', max_length=30, choices=TIPO_CHOICES, blank=True)
    tipo_servico = models.ForeignKey(TipoServicoOS, on_delete=models.SET_NULL, null=True, blank=True, related_name='ordens_servico', verbose_name='Tipo de Serviço')
    subtipo_servico = models.ForeignKey(SubtipoServicoOS, on_delete=models.SET_NULL, null=True, blank=True, related_name='ordens_servico', verbose_name='Operação')
    modalidade_execucao = models.ForeignKey(ModalidadeExecucaoOS, on_delete=models.SET_NULL, null=True, blank=True, related_name='ordens_servico', verbose_name='Modalidade de Execução')
    status = models.CharField('Status', max_length=20, choices=STATUS_CHOICES, default='ABERTA')

    talhao = models.ForeignKey('cadastros.Talhao', on_delete=models.PROTECT, related_name='ordens_servico', verbose_name='Talhão')
    safra = models.ForeignKey('cadastros.Safra', on_delete=models.SET_NULL, null=True, blank=True, related_name='ordens_servico', verbose_name='Safra')
    safra_cultura = models.ForeignKey(
        'cadastros.SafraCultura', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='ordens_servico', verbose_name='Cultura da Safra',
        help_text='Qual cultura da safra esta OS se refere (necessário quando a safra tem mais de uma cultura)',
    )
    poco = models.ForeignKey(
        'cadastros.Poco', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='ordens_servico', verbose_name='Poço / Bomba',
        help_text='Preencher apenas para OS de Irrigação e Adubação/Fertirrigação',
    )
    requisicao = models.ForeignKey('cadastros.Requisicao', on_delete=models.SET_NULL, null=True, blank=True, related_name='ordens_servico', verbose_name='Requisição de Insumos')
    historico_talhao = models.ForeignKey(
        'cadastros.HistoricoTalhao', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='ordens_servico', verbose_name='Ciclo do Talhão',
        help_text='Ciclo de cultivo (HistoricoTalhao) aberto no talhão no momento desta OS',
    )

    idiarn = models.CharField(
        'IDIARN', max_length=30, blank=True, validators=[idiarn_validator],
        help_text='Número de controle obrigatório do ciclo de plantio (preenchido na aprovação da OS)',
    )

    solicitante = models.ForeignKey('usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True, related_name='os_solicitadas', verbose_name='Solicitante')
    responsavel = models.ForeignKey('rh.Funcionario', on_delete=models.SET_NULL, null=True, blank=True, related_name='os_responsavel', verbose_name='Responsável pela Execução')
    aprovador = models.ForeignKey('usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True, related_name='os_aprovadas', verbose_name='Aprovador')

    data_prevista = models.DateField('Data Prevista', null=True, blank=True)
    data_inicio = models.DateTimeField('Data/Hora de Início', null=True, blank=True)
    data_fim = models.DateTimeField('Data/Hora de Conclusão', null=True, blank=True)
    data_aprovacao = models.DateTimeField('Data de Aprovação', null=True, blank=True)

    area_executada_ha = models.DecimalField('Área Executada (ha)', max_digits=10, decimal_places=4, null=True, blank=True, validators=[MinValueValidator(Decimal('0'))])
    numero_corte = models.PositiveSmallIntegerField(
        'Número do Corte', null=True, blank=True, validators=[MinValueValidator(1)],
        help_text='Preencher apenas para OS de Colheita: 1º, 2º, 3º corte do ciclo (cana-de-açúcar, forragens etc.)',
    )

    fornecedor_servico = models.ForeignKey('cadastros.Fornecedor', on_delete=models.SET_NULL, null=True, blank=True, related_name='os_executadas', verbose_name='Fornecedor do Serviço')
    valor_servico_externo = models.DecimalField('Valor do Serviço Externo (R$)', max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('0'))])
    unidade_cobranca = models.CharField('Unidade de Cobrança', max_length=10, choices=UNIDADE_COBRANCA_CHOICES, null=True, blank=True)

    foto_evidencia = models.ImageField('Foto de Evidência (RN-03)', upload_to='ordens_servico/%Y/%m/', null=True, blank=True, help_text='Obrigatória para concluir a OS (RN-03)')
    observacoes = models.TextField('Observações', blank=True)

    # Custo estimado (orçado) — permite comparativo planejado vs. realizado
    custo_estimado_mao_obra = models.DecimalField('Custo Est. Mão de Obra (R$)', max_digits=12, decimal_places=2, null=True, blank=True)
    custo_estimado_maquinario = models.DecimalField('Custo Est. Maquinário (R$)', max_digits=12, decimal_places=2, null=True, blank=True)
    custo_estimado_insumos = models.DecimalField('Custo Est. Insumos (R$)', max_digits=12, decimal_places=2, null=True, blank=True)

    data_cadastro = models.DateTimeField('Data de Cadastro', auto_now_add=True)
    data_atualizacao = models.DateTimeField('Última Atualização', auto_now=True)
    cadastrado_por = models.ForeignKey('usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True, related_name='os_cadastradas', verbose_name='Cadastrado por')

    class Meta:
        db_table = 'cadastros_ordemservico'
        verbose_name = 'Ordem de Serviço'
        verbose_name_plural = 'Ordens de Serviço'
        ordering = ['-data_cadastro']
        indexes = [
            models.Index(fields=['empresa', 'status']),
            models.Index(fields=['talhao', '-data_cadastro']),
            models.Index(fields=['safra', 'tipo']),
        ]

    def __str__(self):
        return f"{self.numero} — {self.descricao_servico} / {self.talhao.nome}"

    @property
    def descricao_servico(self):
        parts = []
        if self.tipo_servico_id:
            parts.append(self.tipo_servico.nome)
        else:
            parts.append(self.get_tipo_display() or 'Sem tipo')
        if self.subtipo_servico_id:
            parts.append(self.subtipo_servico.nome)
        if self.modalidade_execucao_id:
            parts.append(self.modalidade_execucao.nome)
        return ' / '.join(parts)

    def save(self, *args, **kwargs):
        if not self.numero:
            ano = timezone.now().year
            ultima = OrdemServico.objects.filter(numero__startswith=f'OS-{ano}-').order_by('numero').last()
            seq = 1
            if ultima:
                try:
                    seq = int(ultima.numero.split('-')[-1]) + 1
                except (ValueError, IndexError):
                    seq = OrdemServico.objects.filter(numero__startswith=f'OS-{ano}-').count() + 1
            self.numero = f'OS-{ano}-{seq:05d}'
        if self.tipo_servico_id:
            legado = self.tipo_servico.tipo_legado or ''
            if (legado == 'PULV_MECANICA' and self.modalidade_execucao_id
                    and self.modalidade_execucao.nome == 'Costal'):
                self.tipo = 'PULV_COSTAL'
            elif legado:
                self.tipo = legado
        super().save(*args, **kwargs)

    def clean(self):
        if self.status == 'CONCLUIDA' and not self.foto_evidencia:
            raise ValidationError({'foto_evidencia': 'Evidência fotográfica é obrigatória para concluir a OS (RN-03).'})
        if self.fornecedor_servico and not self.valor_servico_externo:
            raise ValidationError({'valor_servico_externo': 'Informe o valor do serviço externo.'})
        if self.subtipo_servico_id and self.tipo_servico_id:
            if self.subtipo_servico.tipo_servico_id != self.tipo_servico_id:
                raise ValidationError({'subtipo_servico': 'A operação selecionada não pertence ao tipo de serviço escolhido.'})

    @property
    def custo_total(self):
        try:
            return self.custo_talhao.custo_total
        except Exception:
            return Decimal('0')

    @property
    def custo_estimado_total(self):
        return (
            (self.custo_estimado_mao_obra or Decimal('0'))
            + (self.custo_estimado_maquinario or Decimal('0'))
            + (self.custo_estimado_insumos or Decimal('0'))
        )

    @property
    def tem_custo_estimado(self):
        return any([
            self.custo_estimado_mao_obra,
            self.custo_estimado_maquinario,
            self.custo_estimado_insumos,
        ])

    @property
    def tipo_legado_efetivo(self):
        """Tipo legado efetivo desta OS (via tipo_servico, com fallback pro campo `tipo`)."""
        if self.tipo_servico_id:
            return self.tipo_servico.tipo_legado or ''
        return self.tipo or ''

    @property
    def pode_aprovar(self):
        return self.status == 'ABERTA'

    @property
    def pode_iniciar(self):
        return self.status == 'APROVADA'

    @property
    def pode_concluir(self):
        return self.status == 'EM_ANDAMENTO'

    @property
    def pode_cancelar(self):
        return self.status in ('ABERTA', 'APROVADA')


class OrdemServicoInsumo(models.Model):
    """Insumos lançados diretamente na OS."""

    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='os_insumos', verbose_name='Empresa')
    os = models.ForeignKey(OrdemServico, on_delete=models.CASCADE, related_name='insumos_os', verbose_name='Ordem de Serviço')
    produto = models.ForeignKey('produtos.Produto', on_delete=models.PROTECT, related_name='insumos_os', verbose_name='Produto')
    praga = models.ForeignKey(
        'cadastros.Praga', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='insumos_os', verbose_name='Praga/Doença Alvo',
        help_text='Praga que motivou a aplicação (usada para sugerir defensivos recomendados).',
    )
    unidade_medida = models.ForeignKey('produtos.UnidadeMedida', on_delete=models.PROTECT, null=True, blank=True, related_name='insumos_os', verbose_name='Unidade')
    quantidade_planejada = models.DecimalField('Quantidade Planejada', max_digits=15, decimal_places=3, null=True, blank=True, validators=[MinValueValidator(Decimal('0'))])
    quantidade_aplicada = models.DecimalField('Quantidade Aplicada', max_digits=15, decimal_places=3, default=Decimal('0'), validators=[MinValueValidator(Decimal('0'))])
    custo_unitario = models.DecimalField('Custo Unitário (R$)', max_digits=15, decimal_places=4, null=True, blank=True, validators=[MinValueValidator(Decimal('0'))])
    observacoes = models.CharField('Observações', max_length=255, blank=True)
    movimentacao = models.ForeignKey(
        'estoque.MovimentacaoEstoque', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='insumos_os_origem', verbose_name='Movimentação de Estoque',
        help_text='Preenchida ao concluir a OS; a baixa efetiva do estoque é feita pelo almoxarifado.'
    )
    data_cadastro = models.DateTimeField('Data de Cadastro', auto_now_add=True)
    data_atualizacao = models.DateTimeField('Última Atualização', auto_now=True)

    class Meta:
        db_table = 'cadastros_ordemservicoinsumo'
        verbose_name = 'Insumo da OS'
        verbose_name_plural = 'Insumos da OS'
        ordering = ['-data_cadastro']
        indexes = [
            models.Index(fields=['os']),
            models.Index(fields=['empresa', 'produto']),
        ]

    def __str__(self):
        return f"{self.os.numero} - {self.produto}"

    @property
    def custo_total(self):
        qtd = self.quantidade_aplicada or Decimal('0')
        custo = self.custo_unitario or Decimal('0')
        return (qtd * custo).quantize(Decimal('0.01'))

    @property
    def status_baixa(self):
        """Status da baixa de estoque deste item: None (OS ainda não concluída),
        'PENDENTE'/'APROVADO' (aguardando o almoxarifado) ou 'EXECUTADO'/'CANCELADO'."""
        return self.movimentacao.status if self.movimentacao_id else None

    def clean(self):
        if self.quantidade_aplicada is not None and self.quantidade_aplicada < 0:
            raise ValidationError({'quantidade_aplicada': 'A quantidade aplicada não pode ser negativa.'})
        if self.custo_unitario is not None and self.custo_unitario < 0:
            raise ValidationError({'custo_unitario': 'O custo unitário não pode ser negativo.'})

    def save(self, *args, **kwargs):
        if not self.unidade_medida_id and getattr(self.produto, 'unidade_medida_id', None):
            self.unidade_medida_id = self.produto.unidade_medida_id
        super().save(*args, **kwargs)

    @property
    def receituario_atual(self):
        """Receituário mais recente emitido para este item (rascunho, aprovado ou
        rejeitado) — se rejeitado, um novo pode ser emitido para o mesmo item."""
        return self.receituarios.order_by('-id').first()

    @property
    def alerta_divergencia_receituario(self):
        """Aviso de compliance quando a Qtd. Aplicada difere >10% do total de
        produto prescrito no receituário aprovado — não bloqueia, só sinaliza
        pra conferência antes de concluir a OS."""
        rec = self.receituario_atual
        if not rec or rec.status != 'APROVADO':
            return None
        total = rec.quantidade_produto_total
        if not total or not self.quantidade_aplicada:
            return None
        desvio = abs(self.quantidade_aplicada - total) / total
        if desvio <= Decimal('0.10'):
            return None
        return (
            f'Aplicado ({self.quantidade_aplicada} {self.unidade_medida.sigla if self.unidade_medida_id else ""}) '
            f'difere {(desvio * 100):.0f}% do prescrito no receituário {rec.numero} ({total}).'
        )


class Receituario(models.Model):
    """Receituário Agronômico: documento técnico que autoriza a aplicação de um
    defensivo contra uma praga específica, emitido por um responsável técnico
    (agrônomo com CREA) e sujeito a aprovação. Os dados de dosagem/carência/
    efetividade são um retrato (snapshot) de `ProdutoDefensivoCultura` no momento
    da emissão — não devem mudar se o cadastro base for editado depois."""

    STATUS_CHOICES = [
        ('RASCUNHO', 'Rascunho'),
        ('APROVADO', 'Aprovado'),
        ('REJEITADO', 'Rejeitado'),
    ]

    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='receituarios', verbose_name='Empresa')
    os = models.ForeignKey(OrdemServico, on_delete=models.CASCADE, related_name='receituarios', verbose_name='Ordem de Serviço')
    insumo = models.ForeignKey(OrdemServicoInsumo, on_delete=models.CASCADE, related_name='receituarios', verbose_name='Item de Insumo')
    numero = models.CharField('Número', max_length=30, unique=True, blank=True)

    # Snapshot no momento da emissão
    cultura = models.ForeignKey('cadastros.Cultura', on_delete=models.PROTECT, related_name='receituarios', verbose_name='Cultura')
    praga = models.ForeignKey('cadastros.Praga', on_delete=models.PROTECT, related_name='receituarios', verbose_name='Praga/Doença')
    produto = models.ForeignKey('produtos.Produto', on_delete=models.PROTECT, related_name='receituarios', verbose_name='Defensivo')
    dosagem_aplicar = models.DecimalField('Dosagem a Aplicar', max_digits=10, decimal_places=3, validators=[MinValueValidator(Decimal('0.001'))])
    unidade_dosagem = models.ForeignKey('produtos.UnidadeMedida', on_delete=models.PROTECT, related_name='receituarios', verbose_name='Unidade de Dosagem')
    volume_calda = models.DecimalField('Volume de Calda (L/ha)', max_digits=10, decimal_places=2, null=True, blank=True)
    carencia_dias = models.IntegerField('Carência (dias)', null=True, blank=True)
    quantidade_maxima_aplicacoes = models.IntegerField('Máx. Aplicações', null=True, blank=True)
    intervalo_reaplicacao_dias = models.IntegerField('Intervalo para Reaplicação (dias)', null=True, blank=True)
    efetividade_pct = models.PositiveSmallIntegerField('Efetividade (%)', null=True, blank=True)
    custo_relativo = models.CharField('Custo Relativo', max_length=6, blank=True)

    # Dados da aplicação
    data_aplicacao_prevista = models.DateField('Data Prevista de Aplicação', null=True, blank=True)
    temperatura_c = models.DecimalField('Temperatura (°C)', max_digits=4, decimal_places=1, null=True, blank=True)
    umidade_pct = models.PositiveSmallIntegerField('Umidade (%)', null=True, blank=True)
    vento_kmh = models.DecimalField('Vento (km/h)', max_digits=4, decimal_places=1, null=True, blank=True)

    # Responsável técnico
    responsavel_tecnico = models.ForeignKey(
        'rh.Funcionario', on_delete=models.PROTECT, related_name='receituarios_emitidos',
        verbose_name='Responsável Técnico',
    )
    numero_crea = models.CharField('Número CREA', max_length=50, blank=True, help_text='Retrato do CREA do responsável técnico no momento da emissão.')

    # Status e aprovação
    status = models.CharField('Status', max_length=10, choices=STATUS_CHOICES, default='RASCUNHO')
    motivo_rejeicao = models.TextField('Motivo da Rejeição', blank=True)
    aprovado_por = models.ForeignKey('usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True, related_name='receituarios_aprovados', verbose_name='Aprovado por')
    data_aprovacao = models.DateTimeField('Data de Aprovação', null=True, blank=True)

    observacoes = models.TextField('Observações', blank=True)
    created_by = models.ForeignKey('usuarios.Usuario', on_delete=models.SET_NULL, null=True, related_name='receituarios_criados', verbose_name='Criado por')
    created_at = models.DateTimeField('Criado em', auto_now_add=True)
    updated_at = models.DateTimeField('Atualizado em', auto_now=True)

    class Meta:
        verbose_name = 'Receituário Agronômico'
        verbose_name_plural = 'Receituários Agronômicos'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['empresa', 'status']),
            models.Index(fields=['insumo']),
        ]

    def __str__(self):
        return f"{self.numero} - {self.produto} - {self.praga}"

    def save(self, *args, **kwargs):
        if not self.numero:
            ano = timezone.now().year
            ultimo = Receituario.objects.filter(
                empresa=self.empresa, numero__startswith=f'REC-{ano}-'
            ).order_by('numero').last()
            seq = 1
            if ultimo:
                try:
                    seq = int(ultimo.numero.split('-')[-1]) + 1
                except (ValueError, IndexError):
                    seq = Receituario.objects.filter(empresa=self.empresa, numero__startswith=f'REC-{ano}-').count() + 1
            self.numero = f'REC-{ano}-{seq:05d}'
        if self.responsavel_tecnico_id and not self.numero_crea:
            self.numero_crea = self.responsavel_tecnico.numero_crea
        super().save(*args, **kwargs)

    def aprovar(self, usuario):
        if self.status != 'RASCUNHO':
            raise ValidationError('Apenas receituários em rascunho podem ser aprovados.')
        self.status = 'APROVADO'
        self.aprovado_por = usuario
        self.data_aprovacao = timezone.now()
        self.save(update_fields=['status', 'aprovado_por', 'data_aprovacao'])
        total = self.quantidade_produto_total
        if total is not None:
            self.insumo.quantidade_planejada = total
            self.insumo.save(update_fields=['quantidade_planejada'])

    def rejeitar(self, usuario, motivo):
        if self.status != 'RASCUNHO':
            raise ValidationError('Apenas receituários em rascunho podem ser rejeitados.')
        self.status = 'REJEITADO'
        self.motivo_rejeicao = motivo
        self.save(update_fields=['status', 'motivo_rejeicao'])

    @property
    def _defensivo_referencia(self):
        """Registro atual de Defensivo × Cultura × Praga para este receituário —
        usado só para alertar sobre faixas mín/máx, não para o snapshot (que já
        foi congelado em `save()`). Busca dados atuais de propósito: se a bula
        no cadastro mudou, o alerta deve refletir a regra vigente."""
        from produtos.models import ProdutoDefensivoCultura
        if not (self.produto_id and self.cultura_id and self.praga_id):
            return None
        if not hasattr(self, '_defensivo_referencia_cache'):
            self._defensivo_referencia_cache = ProdutoDefensivoCultura.objects.filter(
                produto_id=self.produto_id, cultura_id=self.cultura_id, praga_id=self.praga_id,
            ).select_related('unidade_dosagem').first()
        return self._defensivo_referencia_cache

    @property
    def alertas_faixa(self):
        """Avisos quando a dosagem ou o volume de calda informados estão fora da
        faixa mín/máx cadastrada em Defensivo × Cultura. Não bloqueia o
        salvamento — o agrônomo pode decidir aplicar fora da faixa sob sua
        responsabilidade, mas o sistema alerta para essa decisão ficar visível."""
        dc = self._defensivo_referencia
        if not dc:
            return []
        alertas = []
        if self.dosagem_aplicar is not None and self.unidade_dosagem_id == dc.unidade_dosagem_id:
            sigla = dc.unidade_dosagem.sigla
            if self.dosagem_aplicar < dc.dosagem_minima:
                alertas.append(
                    f'Dosagem informada ({self.dosagem_aplicar} {sigla}) está ABAIXO do mínimo recomendado '
                    f'({dc.dosagem_minima} {sigla}).'
                )
            elif self.dosagem_aplicar > dc.dosagem_maxima:
                alertas.append(
                    f'Dosagem informada ({self.dosagem_aplicar} {sigla}) está ACIMA do máximo recomendado '
                    f'({dc.dosagem_maxima} {sigla}).'
                )
        if self.volume_calda is not None:
            if self.volume_calda < dc.volume_calda_minimo:
                alertas.append(
                    f'Volume de calda informado ({self.volume_calda} L/ha) está ABAIXO do mínimo recomendado '
                    f'({dc.volume_calda_minimo} L/ha).'
                )
            elif self.volume_calda > dc.volume_calda_maximo:
                alertas.append(
                    f'Volume de calda informado ({self.volume_calda} L/ha) está ACIMA do máximo recomendado '
                    f'({dc.volume_calda_maximo} L/ha).'
                )
        return alertas

    @property
    def area_referencia_ha(self):
        """Área usada para o resumo de preparo do tanque: área executada da OS,
        com fallback para a área cadastrada do talhão (mesmo critério de
        `ajax_recomendacao_defensivo`)."""
        return self.os.area_executada_ha or (self.os.talhao.area_hac if self.os.talhao_id else None)

    @property
    def quantidade_produto_total(self):
        """Dosagem/ha × área do talhão = quantidade total do defensivo para o tanque."""
        area = self.area_referencia_ha
        if not (self.dosagem_aplicar and area):
            return None
        return (self.dosagem_aplicar * area).quantize(Decimal('0.001'))

    @property
    def volume_calda_total(self):
        """Volume de calda/ha × área do talhão = volume total de calda a preparar."""
        area = self.area_referencia_ha
        if not (self.volume_calda and area):
            return None
        return (self.volume_calda * area).quantize(Decimal('0.01'))

    @property
    def agua_pura_total(self):
        """Calda total − produto total. Só calculado quando a dosagem é numa
        unidade de VOLUME (L, mL) — dosagem em peso (kg/g) não subtrai
        diretamente de um volume de calda em litros."""
        if not (self.unidade_dosagem_id and self.unidade_dosagem.tipo == 'VOLUME'):
            return None
        calda = self.volume_calda_total
        produto = self.quantidade_produto_total
        if calda is None or produto is None:
            return None
        return (calda - produto).quantize(Decimal('0.01'))


# ============================================================================
# TRANSPLANTIO E REPLANTIO (execução de OS tipo Plantio)
# ============================================================================

class OSTransplantio(models.Model):
    """Dados de transplantio de mudas quando a OS é do tipo Plantio/subtipo Transplante."""

    TIPO_CHOICES = [
        ('TOTAL', 'Total'),
        ('PARCIAL', 'Parcial'),
    ]

    os = models.OneToOneField(OrdemServico, on_delete=models.CASCADE, related_name='transplantio', verbose_name='Ordem de Serviço')
    lote_muda = models.ForeignKey('estufas.LoteMuda', on_delete=models.PROTECT, related_name='transplantios', verbose_name='Lote de Mudas')
    tipo = models.CharField('Tipo', max_length=10, choices=TIPO_CHOICES, default='TOTAL')
    quantidade_transplantada = models.IntegerField('Quantidade Transplantada', validators=[MinValueValidator(1)])
    custo_transferido = models.DecimalField(
        'Custo Transferido (R$)', max_digits=14, decimal_places=2, default=Decimal('0'),
        help_text='Custo proporcional da estufa transferido para o talhão (RN-17)',
    )
    data_cadastro = models.DateTimeField('Data de Cadastro', auto_now_add=True)

    class Meta:
        db_table = 'operacoes_campo_ostransplantio'
        verbose_name = 'Transplantio da OS'
        verbose_name_plural = 'Transplantios da OS'

    def __str__(self):
        return f"Transplantio {self.lote_muda.codigo_lote} → {self.os.talhao.codigo} ({self.os.numero})"

    def save(self, *args, **kwargs):
        if not self.pk:
            self.custo_transferido = self.lote_muda.custo_por_muda * self.quantidade_transplantada
        super().save(*args, **kwargs)

    def clean(self):
        if self.lote_muda_id and self.quantidade_transplantada:
            disponivel = self.lote_muda.quantidade_disponivel
            if self.quantidade_transplantada > disponivel:
                raise ValidationError({
                    'quantidade_transplantada': f'Quantidade ({self.quantidade_transplantada}) supera o disponível no lote ({disponivel}).',
                })

    def marcar_lote_se_esgotado(self):
        """Chamado na conclusão da OS: atualiza status do lote quando não sobra mais muda disponível."""
        lote = self.lote_muda
        if lote.quantidade_disponivel <= 0 and lote.status not in ['TRANSPLANTADO', 'ENCERRADO']:
            lote.status = 'TRANSPLANTADO'
            lote.save(update_fields=['status'])


class OSReplantio(models.Model):
    """Dados de replantio quando a OS é do tipo Plantio/subtipo Replantio."""

    ORIGEM_CHOICES = [
        ('ESTUFA', 'Estufa Própria'),
        ('COMPRA', 'Compra Externa'),
        ('OUTRA_AREA', 'Outra Área'),
    ]
    MOTIVO_CHOICES = [
        ('CLIMA', 'Clima / Intempérie'),
        ('PRAGA', 'Praga'),
        ('DOENCA', 'Doença'),
        ('MECANICO', 'Dano Mecânico'),
        ('OUTRO', 'Outro'),
    ]

    os = models.OneToOneField(OrdemServico, on_delete=models.CASCADE, related_name='replantio', verbose_name='Ordem de Serviço')
    quantidade = models.IntegerField('Quantidade', validators=[MinValueValidator(1)])
    origem_muda = models.CharField('Origem da Muda', max_length=20, choices=ORIGEM_CHOICES)
    lote_muda = models.ForeignKey(
        'estufas.LoteMuda', on_delete=models.SET_NULL, null=True, blank=True, related_name='replantios',
        verbose_name='Lote de Mudas', help_text='Preencher somente se origem for "Estufa Própria"',
    )
    motivo_perda = models.CharField('Motivo da Perda', max_length=30, choices=MOTIVO_CHOICES)
    custo_adicional = models.DecimalField(
        'Custo Adicional (R$)', max_digits=12, decimal_places=2, default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))],
    )
    data_cadastro = models.DateTimeField('Data de Cadastro', auto_now_add=True)

    class Meta:
        db_table = 'operacoes_campo_osreplantio'
        verbose_name = 'Replantio da OS'
        verbose_name_plural = 'Replantios da OS'

    def __str__(self):
        return f"Replantio {self.os.talhao.codigo} — {self.quantidade} un ({self.os.numero})"


def _fator_encargos_empresa(empresa):
    """Retorna o fator de encargos configurado para a empresa (default 1.0)."""
    try:
        return empresa.portal_campo_config.fator_encargos
    except Exception:
        return Decimal('1.0')


class OSFuncionario(models.Model):
    """Funcionário alocado em OS. Calcula custo MO: (salário ÷ 220h) × horas × fator_encargos."""

    os = models.ForeignKey(OrdemServico, on_delete=models.CASCADE, related_name='funcionarios_os', verbose_name='Ordem de Serviço')
    funcionario = models.ForeignKey('rh.Funcionario', on_delete=models.PROTECT, related_name='alocacoes_os', verbose_name='Funcionário')
    data_execucao = models.DateField('Data de Execução', null=True, blank=True)
    hora_inicio = models.TimeField('Hora de Início', null=True, blank=True)
    hora_fim = models.TimeField('Hora de Término', null=True, blank=True)
    observacoes = models.CharField('Observações', max_length=200, blank=True)

    class Meta:
        db_table = 'cadastros_osfuncionario'
        verbose_name = 'Funcionário na OS'
        verbose_name_plural = 'Funcionários nas OS'
        ordering = ['data_execucao', 'hora_inicio']
        indexes = [models.Index(fields=['os', 'data_execucao'])]

    def __str__(self):
        return f"{self.funcionario.nome_completo} — {self.os.numero} ({self.data_execucao})"

    @property
    def horas_trabalhadas(self):
        if not self.hora_inicio or not self.hora_fim:
            return Decimal('0')
        from datetime import datetime, date
        inicio = datetime.combine(date.today(), self.hora_inicio)
        fim = datetime.combine(date.today(), self.hora_fim)
        delta = (fim - inicio).total_seconds()
        if delta <= 0:
            return Decimal('0')
        return Decimal(str(round(delta / 3600, 4)))

    @property
    def custo_calculado(self):
        try:
            custo_hora = self.funcionario.salario / Decimal('220')
            fator = _fator_encargos_empresa(self.os.empresa)
            return (custo_hora * fator * self.horas_trabalhadas).quantize(Decimal('0.01'))
        except Exception:
            return Decimal('0')

    def clean(self):
        if self.hora_fim and self.hora_inicio and self.hora_fim <= self.hora_inicio:
            raise ValidationError({'hora_fim': 'Hora de término deve ser posterior à hora de início.'})


class OSIntervalo(models.Model):
    """Intervalo contínuo de trabalho do operador em uma OS. Substitui o registro manual de horário."""

    os = models.ForeignKey(OrdemServico, on_delete=models.CASCADE, related_name='intervalos', verbose_name='Ordem de Serviço')
    funcionario = models.ForeignKey('rh.Funcionario', on_delete=models.PROTECT, related_name='intervalos_os', verbose_name='Funcionário')
    inicio = models.DateTimeField('Início')
    fim = models.DateTimeField('Fim', null=True, blank=True)
    latitude = models.DecimalField('Latitude', max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField('Longitude', max_digits=10, decimal_places=7, null=True, blank=True)

    class Meta:
        db_table = 'campo_os_intervalo'
        verbose_name = 'Intervalo de Trabalho'
        verbose_name_plural = 'Intervalos de Trabalho'
        ordering = ['inicio']

    def __str__(self):
        fim_str = self.fim.strftime('%d/%m %H:%M') if self.fim else 'em andamento'
        return f"{self.funcionario.nome_completo} — {self.inicio.strftime('%d/%m %H:%M')} → {fim_str}"

    @property
    def duracao_horas(self):
        if not self.fim:
            return None
        delta = (self.fim - self.inicio).total_seconds()
        if delta <= 0:
            return Decimal('0')
        return Decimal(str(round(delta / 3600, 4)))

    @property
    def custo_calculado(self):
        horas = self.duracao_horas
        if not horas:
            return Decimal('0')
        try:
            custo_hora = self.funcionario.salario / Decimal('220')
            fator = _fator_encargos_empresa(self.os.empresa)
            return (custo_hora * fator * horas).quantize(Decimal('0.01'))
        except Exception:
            return Decimal('0')

    @property
    def tem_gps(self):
        return self.latitude is not None and self.longitude is not None


class OSMaquina(models.Model):
    """Máquina/Veículo utilizado em OS. Calcula custo via CustoHoraMaquina."""

    os = models.ForeignKey(OrdemServico, on_delete=models.CASCADE, related_name='maquinas_os', verbose_name='Ordem de Serviço')
    veiculo = models.ForeignKey('frota.Vehicle', on_delete=models.PROTECT, related_name='usos_os', verbose_name='Veículo/Máquina')
    operador = models.ForeignKey('rh.Funcionario', on_delete=models.SET_NULL, null=True, blank=True, related_name='operacoes_maquina_os', verbose_name='Operador')
    data_execucao = models.DateField('Data de Execução', null=True, blank=True)
    horimetro_inicial = models.DecimalField('Horímetro Inicial (h)', max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('0'))])
    horimetro_final = models.DecimalField('Horímetro Final (h)', max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('0'))])
    custo_hora_config = models.ForeignKey(CustoHoraMaquina, on_delete=models.SET_NULL, null=True, blank=True, related_name='usos_os', verbose_name='Configuração de Custo/Hora')
    observacoes = models.CharField('Observações', max_length=200, blank=True)

    class Meta:
        db_table = 'cadastros_osmaquina'
        verbose_name = 'Máquina na OS'
        verbose_name_plural = 'Máquinas nas OS'
        ordering = ['data_execucao', 'horimetro_inicial']
        indexes = [models.Index(fields=['os', 'data_execucao'])]

    def __str__(self):
        return f"{self.veiculo} — {self.os.numero} ({self.data_execucao or 'sem data'})"

    @property
    def horas_trabalhadas(self):
        if self.horimetro_final is None or self.horimetro_inicial is None:
            return Decimal('0')
        return max(self.horimetro_final - self.horimetro_inicial, Decimal('0'))

    @property
    def litros_consumidos(self):
        consumo = self.veiculo.consumo_medio or Decimal('0')
        return (consumo * self.horas_trabalhadas).quantize(Decimal('0.01'))

    @property
    def custo_calculado(self):
        config = self.custo_hora_config
        if not config:
            config = CustoHoraMaquina.objects.filter(veiculo=self.veiculo, ativo=True).order_by('-data_referencia').first()
        if config:
            return (config.custo_hora_calculado * self.horas_trabalhadas).quantize(Decimal('0.01'))
        return Decimal('0')

    def clean(self):
        if self.horimetro_final is not None and self.horimetro_inicial is not None:
            if self.horimetro_final < self.horimetro_inicial:
                raise ValidationError({'horimetro_final': 'Horímetro final não pode ser menor que o inicial.'})


# ============================================================================
# CUSTO POR TALHÃO
# ============================================================================

class CustoTalhao(models.Model):
    """Consolidação de custos por OS/Talhão/Safra. Gerado ao concluir OS."""

    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='custos_talhao', verbose_name='Empresa')
    talhao = models.ForeignKey('cadastros.Talhao', on_delete=models.PROTECT, related_name='custos', verbose_name='Talhão')
    safra = models.ForeignKey('cadastros.Safra', on_delete=models.SET_NULL, null=True, blank=True, related_name='custos_talhao', verbose_name='Safra')
    os = models.OneToOneField(OrdemServico, on_delete=models.CASCADE, related_name='custo_talhao', verbose_name='Ordem de Serviço')

    custo_mao_obra = models.DecimalField('Custo Mão de Obra (R$)', max_digits=12, decimal_places=2, default=Decimal('0'))
    custo_maquinario = models.DecimalField('Custo Maquinário (R$)', max_digits=12, decimal_places=2, default=Decimal('0'))
    custo_insumos = models.DecimalField('Custo Insumos (R$)', max_digits=12, decimal_places=2, default=Decimal('0'))
    custo_servico_externo = models.DecimalField('Custo Serviço Externo (R$)', max_digits=12, decimal_places=2, default=Decimal('0'))
    custo_estufa = models.DecimalField('Custo Estufa/Transplantio (R$)', max_digits=12, decimal_places=2, default=Decimal('0'))
    area_executada_ha = models.DecimalField('Área Executada (ha)', max_digits=10, decimal_places=4, null=True, blank=True)

    data_registro = models.DateTimeField('Data de Registro', auto_now_add=True)
    data_atualizacao = models.DateTimeField('Última Atualização', auto_now=True)

    class Meta:
        db_table = 'cadastros_custotalhao'
        verbose_name = 'Custo por Talhão'
        verbose_name_plural = 'Custos por Talhão'
        ordering = ['-data_registro']
        indexes = [
            models.Index(fields=['empresa', 'talhao']),
            models.Index(fields=['safra', 'talhao']),
        ]

    def __str__(self):
        return f"Custo {self.os.numero} — {self.talhao.nome} (R$ {self.custo_total:.2f})"

    @property
    def custo_total(self):
        return self.custo_mao_obra + self.custo_maquinario + self.custo_insumos + self.custo_servico_externo + self.custo_estufa

    @property
    def custo_por_hectare(self):
        if self.area_executada_ha and self.area_executada_ha > 0:
            return (self.custo_total / self.area_executada_ha).quantize(Decimal('0.01'))
        return Decimal('0')

    def recalcular(self):
        # Intervalos de trabalho (rastreamento em tempo real via portal)
        intervalos_fechados = self.os.intervalos.filter(fim__isnull=False)
        custo_intervalos = sum(i.custo_calculado for i in intervalos_fechados) or Decimal('0')
        # Trabalhadores com intervalo têm custo pelo rastreamento portal;
        # só conta OSFuncionario para quem NÃO tem intervalo (alocação manual)
        workers_com_intervalo = set(intervalos_fechados.values_list('funcionario_id', flat=True))
        custo_outros = sum(
            f.custo_calculado for f in self.os.funcionarios_os.all()
            if f.funcionario_id not in workers_com_intervalo
        ) or Decimal('0')
        self.custo_mao_obra = custo_intervalos + custo_outros
        self.custo_maquinario = sum(m.custo_calculado for m in self.os.maquinas_os.all()) or Decimal('0')
        insumos_os = self.os.insumos_os.all()
        if insumos_os.exists():
            self.custo_insumos = sum((i.custo_total for i in insumos_os), Decimal('0'))
        elif self.os.requisicao:
            from django.db.models import Sum as DjSum
            total = self.os.requisicao.itens.aggregate(
                t=DjSum(models.F('quantidade_atendida') * models.F('custo_estimado'))
            )['t']
            self.custo_insumos = total or Decimal('0')
        else:
            self.custo_insumos = Decimal('0')
        self.custo_servico_externo = self.os.valor_servico_externo or Decimal('0')
        custo_estufa = Decimal('0')
        try:
            custo_estufa += self.os.transplantio.custo_transferido or Decimal('0')
        except OSTransplantio.DoesNotExist:
            pass
        try:
            custo_estufa += self.os.replantio.custo_adicional or Decimal('0')
        except OSReplantio.DoesNotExist:
            pass
        self.custo_estufa = custo_estufa
        self.area_executada_ha = self.os.area_executada_ha
        self.save()


# ============================================================================
# MÓDULO DE COLHEITA
# ============================================================================

class EtapaColheita(models.Model):
    """Rodada de colheita (1ª, 2ª, 3ª). Agrupa frota e pesagens."""

    STATUS_CHOICES = [('ABERTA', 'Aberta'), ('CONCLUIDA', 'Concluída')]

    os = models.ForeignKey(OrdemServico, on_delete=models.CASCADE, related_name='etapas_colheita', verbose_name='Ordem de Serviço', limit_choices_to={'tipo': 'COLHEITA'})
    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='etapas_colheita', verbose_name='Empresa')
    talhao = models.ForeignKey('cadastros.Talhao', on_delete=models.PROTECT, related_name='etapas_colheita', verbose_name='Talhão')
    safra = models.ForeignKey('cadastros.Safra', on_delete=models.SET_NULL, null=True, blank=True, related_name='etapas_colheita', verbose_name='Safra')
    numero_etapa = models.PositiveSmallIntegerField('Nº da Etapa')
    data_inicio = models.DateTimeField('Data/Hora de Início', null=True, blank=True)
    data_fim = models.DateTimeField('Data/Hora de Encerramento', null=True, blank=True)
    supervisor = models.ForeignKey('rh.Funcionario', on_delete=models.SET_NULL, null=True, blank=True, related_name='etapas_supervisionadas', verbose_name='Supervisor de Campo')
    status = models.CharField('Status', max_length=10, choices=STATUS_CHOICES, default='ABERTA')
    total_liquido_kg = models.DecimalField('Total Líquido (kg)', max_digits=14, decimal_places=2, default=Decimal('0'))
    ultimo_corte_ciclo = models.BooleanField(
        'Último corte do ciclo', default=False,
        help_text='Marcado ao concluir: indica que esta foi a última colheita do ciclo — libera o talhão e fecha o histórico/lote de produção.'
    )
    observacoes = models.TextField('Observações', blank=True)
    data_cadastro = models.DateTimeField('Data de Cadastro', auto_now_add=True)

    class Meta:
        db_table = 'cadastros_etapacolheita'
        verbose_name = 'Etapa de Colheita'
        verbose_name_plural = 'Etapas de Colheita'
        ordering = ['os', 'numero_etapa']
        unique_together = [('os', 'numero_etapa')]
        indexes = [
            models.Index(fields=['empresa', 'status']),
            models.Index(fields=['talhao', 'safra', 'numero_etapa']),
        ]

    def __str__(self):
        return f"{self.os.numero} — {self.numero_etapa}ª Colheita / {self.talhao.nome}"

    def recalcular_total(self):
        from django.db.models import Sum as DjSum
        total = ViagemColheita.objects.filter(carrocao__frota__etapa=self).aggregate(t=DjSum('peso_final_kg'))['t'] or Decimal('0')
        self.total_liquido_kg = total
        self.save(update_fields=['total_liquido_kg'])

    @classmethod
    def proximo_numero(cls, os_obj):
        ultimo = cls.objects.filter(os=os_obj).order_by('-numero_etapa').first()
        return (ultimo.numero_etapa + 1) if ultimo else 1


class FrotaColheita(models.Model):
    """Trator alocado em uma EtapaColheita. Pode rebocar N carroções."""

    etapa = models.ForeignKey(EtapaColheita, on_delete=models.CASCADE, related_name='frotas', verbose_name='Etapa de Colheita')
    trator = models.ForeignKey('frota.Vehicle', on_delete=models.PROTECT, related_name='frotas_colheita', verbose_name='Trator', limit_choices_to={'tipo__in': ['LEVE', 'MEDIO', 'PESADO']})
    operador = models.ForeignKey('rh.Funcionario', on_delete=models.SET_NULL, null=True, blank=True, related_name='operacoes_colheita', verbose_name='Operador/Tratorista')
    horimetro_inicial = models.DecimalField('Horímetro Inicial (h)', max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('0'))])
    horimetro_final = models.DecimalField('Horímetro Final (h)', max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('0'))])
    observacoes = models.CharField('Observações', max_length=200, blank=True)

    class Meta:
        db_table = 'cadastros_frotacolheita'
        verbose_name = 'Trator na Colheita'
        verbose_name_plural = 'Tratores na Colheita'
        ordering = ['etapa', 'trator']

    def __str__(self):
        return f"{self.trator} — {self.etapa}"

    def clean(self):
        if (self.horimetro_final is not None and self.horimetro_inicial is not None
                and self.horimetro_final < self.horimetro_inicial):
            raise ValidationError({'horimetro_final': 'Horímetro final não pode ser menor que o inicial.'})


class CarrocaoFrota(models.Model):
    """Carroção rebocado por FrotaColheita."""

    frota = models.ForeignKey(FrotaColheita, on_delete=models.CASCADE, related_name='carrocoes', verbose_name='Frota (Trator)')
    veiculo = models.ForeignKey('frota.Vehicle', on_delete=models.PROTECT, related_name='usos_colheita', verbose_name='Carroção', limit_choices_to={'tipo': 'REBOQUE'})
    numero_identificacao = models.CharField('Identificação', max_length=50)
    capacidade_ton = models.DecimalField('Capacidade (ton)', max_digits=8, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('0'))])
    tara_kg = models.IntegerField('Tara (kg)', null=True, blank=True, validators=[MinValueValidator(0)])

    class Meta:
        db_table = 'cadastros_carrocaofrota'
        verbose_name = 'Carroção na Frota'
        verbose_name_plural = 'Carroções na Frota'
        ordering = ['frota', 'numero_identificacao']

    def __str__(self):
        return f"{self.numero_identificacao} — {self.frota}"

    def clean(self):
        if self.veiculo_id and self.frota_id:
            etapa = self.frota.etapa
            qs = CarrocaoFrota.objects.filter(frota__etapa=etapa, veiculo=self.veiculo)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError({'veiculo': f'O carroção "{self.veiculo}" já está alocado em outro trator desta etapa.'})


class ViagemColheita(models.Model):
    """Viagem/carga de carroção. Registra pesagem bruto/tara/líquido com desconto."""

    STATUS_CHOICES = [
        ('AGUARDANDO_LIBERACAO', 'Aguardando Liberação'),
        ('LIBERADA', 'Liberada'),
    ]

    carrocao = models.ForeignKey(CarrocaoFrota, on_delete=models.CASCADE, related_name='viagens', verbose_name='Carroção')
    numero_viagem = models.PositiveSmallIntegerField('Nº da Viagem')
    hora_saida_campo = models.DateTimeField('Saída do Campo', null=True, blank=True)
    hora_chegada_balanca = models.DateTimeField('Chegada na Balança', null=True, blank=True)
    peso_bruto_kg = models.DecimalField('Peso Bruto (kg)', max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    tara_usada_kg = models.DecimalField('Tara (kg)', max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    peso_liquido_kg = models.DecimalField('Peso Líquido (kg)', max_digits=10, decimal_places=2, default=Decimal('0'))
    umidade_pct = models.DecimalField('Umidade (%)', max_digits=5, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('0'))])
    impureza_pct = models.DecimalField('Impureza (%)', max_digits=5, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('0'))])
    desconto_kg = models.DecimalField('Desconto (kg)', max_digits=10, decimal_places=2, default=Decimal('0'))
    peso_final_kg = models.DecimalField('Peso Final (kg)', max_digits=10, decimal_places=2, default=Decimal('0'))
    foto_romaneio = models.ImageField('Foto do Romaneio/Ticket', upload_to='colheita/romaneios/%Y/%m/', null=True, blank=True)
    observacoes = models.CharField('Observações', max_length=200, blank=True)
    data_registro = models.DateTimeField('Registrado em', auto_now_add=True)
    status = models.CharField('Status', max_length=25, choices=STATUS_CHOICES, default='AGUARDANDO_LIBERACAO')
    hora_liberacao_retorno = models.DateTimeField('Liberado para Retorno em', null=True, blank=True)
    liberado_por = models.ForeignKey(
        'usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='viagens_liberadas', verbose_name='Liberado por'
    )
    liberado_por_nome = models.CharField('Nome de quem liberou', max_length=120, blank=True)

    class Meta:
        db_table = 'cadastros_viagemcolheita'
        verbose_name = 'Viagem de Colheita'
        verbose_name_plural = 'Viagens de Colheita'
        ordering = ['carrocao', 'numero_viagem']
        unique_together = [('carrocao', 'numero_viagem')]
        indexes = [models.Index(fields=['carrocao', 'numero_viagem'])]

    def __str__(self):
        return f"{self.carrocao.numero_identificacao} — Viagem {self.numero_viagem} ({self.peso_final_kg:.0f} kg)"

    def save(self, *args, **kwargs):
        self.peso_liquido_kg = max(self.peso_bruto_kg - self.tara_usada_kg, Decimal('0'))
        self.peso_final_kg = max(self.peso_liquido_kg - self.desconto_kg, Decimal('0'))
        super().save(*args, **kwargs)
        self.carrocao.frota.etapa.recalcular_total()

    def clean(self):
        if (self.peso_bruto_kg is not None and self.tara_usada_kg is not None
                and self.tara_usada_kg > self.peso_bruto_kg):
            raise ValidationError({'tara_usada_kg': 'Tara não pode ser maior que o peso bruto.'})

    @classmethod
    def proximo_numero(cls, carrocao):
        ultimo = cls.objects.filter(carrocao=carrocao).order_by('-numero_viagem').first()
        return (ultimo.numero_viagem + 1) if ultimo else 1

    def liberar_retorno(self, usuario):
        self.status = 'LIBERADA'
        self.hora_liberacao_retorno = timezone.now()
        self.liberado_por = usuario
        self.liberado_por_nome = usuario.get_full_name() or usuario.username
        self.save(update_fields=['status', 'hora_liberacao_retorno', 'liberado_por', 'liberado_por_nome'])

    def reverter_liberacao(self):
        self.status = 'AGUARDANDO_LIBERACAO'
        self.hora_liberacao_retorno = None
        self.liberado_por = None
        self.liberado_por_nome = ''
        self.save(update_fields=['status', 'hora_liberacao_retorno', 'liberado_por', 'liberado_por_nome'])


# ============================================================================
# LOTE DE PRODUÇÃO — RF-109 e RF-110 (rastreabilidade colheita → packing)
# ============================================================================

class LoteProducao(models.Model):
    """
    Lote centralizado de produção gerado ao concluir uma EtapaColheita.
    Cria o vínculo rastreável entre talhão/safra → packing house.
    """
    STATUS_CHOICES = [
        ('COLHIDO',          'Colhido — Aguardando Packing'),
        ('RECEBIDO_PACKING', 'Recebido no Packing'),
        ('EM_PROCESSAMENTO', 'Em Processamento'),
        ('CONCLUIDO',        'Concluído'),
        ('CANCELADO',        'Cancelado'),
    ]

    empresa = models.ForeignKey(
        'empresas.Empresa', on_delete=models.CASCADE,
        related_name='lotes_producao', verbose_name='Empresa',
    )
    numero_lote = models.CharField(
        'Número do Lote', max_length=50, unique=True,
        help_text='Auto-gerado: LP-YYYYMMDD-NNNNN',
    )
    talhao = models.ForeignKey(
        'cadastros.Talhao', on_delete=models.PROTECT,
        related_name='lotes_producao', verbose_name='Talhão',
    )
    safra = models.ForeignKey(
        'cadastros.Safra', on_delete=models.PROTECT,
        related_name='lotes_producao', verbose_name='Safra',
    )
    cultura = models.ForeignKey(
        'cadastros.Cultura', on_delete=models.PROTECT,
        related_name='lotes_producao', verbose_name='Cultura',
    )
    etapa_colheita = models.ForeignKey(
        EtapaColheita, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='lotes_producao', verbose_name='Etapa de Colheita',
    )

    # Dados agregados das viagens de colheita
    peso_total_colhido_kg = models.DecimalField(
        'Peso Total Colhido (kg)', max_digits=12, decimal_places=3, default=Decimal('0'),
    )
    data_colheita_inicio = models.DateField('Início da Colheita', null=True, blank=True)
    data_colheita_fim = models.DateField('Fim da Colheita', null=True, blank=True)
    umidade_media_pct = models.DecimalField(
        'Umidade Média (%)', max_digits=5, decimal_places=2, null=True, blank=True,
    )
    impureza_media_pct = models.DecimalField(
        'Impureza Média (%)', max_digits=5, decimal_places=2, null=True, blank=True,
    )

    # Status e recepção no packing
    status = models.CharField(
        'Status', max_length=30, choices=STATUS_CHOICES, default='COLHIDO',
    )
    data_recepcao_packing = models.DateTimeField('Data de Recepção no Packing', null=True, blank=True)
    recebido_por = models.ForeignKey(
        'usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='lotes_recebidos', verbose_name='Recebido por',
    )

    # Código único de rastreabilidade
    codigo_rastreamento = models.CharField(
        'Código de Rastreamento', max_length=100, unique=True,
        help_text='Formato: {safra.codigo}-TL{talhao.id}-{seq}',
    )

    observacoes = models.TextField('Observações', blank=True)
    criado_por = models.ForeignKey(
        'usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='lotes_producao_criados', verbose_name='Criado por',
    )
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)
    atualizado_em = models.DateTimeField('Atualizado em', auto_now=True)

    class Meta:
        db_table = 'campo_lote_producao'
        verbose_name = 'Lote de Produção'
        verbose_name_plural = 'Lotes de Produção'
        ordering = ['-criado_em']
        indexes = [
            models.Index(fields=['empresa', 'status']),
            models.Index(fields=['safra', 'talhao']),
        ]

    def __str__(self):
        return f'{self.numero_lote} — {self.talhao} / {self.safra}'

    def save(self, *args, **kwargs):
        if not self.numero_lote:
            from django.utils import timezone as tz
            hoje = tz.now().strftime('%Y%m%d')
            ultimo = LoteProducao.objects.filter(
                numero_lote__startswith=f'LP-{hoje}-'
            ).order_by('numero_lote').last()
            seq = 1
            if ultimo:
                try:
                    seq = int(ultimo.numero_lote.split('-')[-1]) + 1
                except (ValueError, IndexError):
                    seq = LoteProducao.objects.filter(numero_lote__startswith=f'LP-{hoje}-').count() + 1
            self.numero_lote = f'LP-{hoje}-{seq:05d}'

        if not self.codigo_rastreamento:
            safra_cod = getattr(self.safra, 'codigo', str(self.safra_id)) if self.safra_id else 'S0'
            talhao_id = self.talhao_id or 0
            seq_cod = self.numero_lote.split('-')[-1] if self.numero_lote else '00001'
            self.codigo_rastreamento = f'{safra_cod}-TL{talhao_id:03d}-{seq_cod}'

        super().save(*args, **kwargs)

    def calcular_totais(self):
        """Recalcula peso e médias a partir das ViagemColheita da EtapaColheita."""
        if not self.etapa_colheita_id:
            return
        from django.db.models import Sum, Avg
        viagens = ViagemColheita.objects.filter(carrocao__frota__etapa=self.etapa_colheita)
        agg = viagens.aggregate(total=Sum('peso_final_kg'))
        self.peso_total_colhido_kg = agg['total'] or Decimal('0')
        umidade = viagens.exclude(umidade_pct__isnull=True).aggregate(m=Avg('umidade_pct'))
        self.umidade_media_pct = umidade['m']
        impureza = viagens.exclude(impureza_pct__isnull=True).aggregate(m=Avg('impureza_pct'))
        self.impureza_media_pct = impureza['m']
        if self.etapa_colheita.data_inicio:
            self.data_colheita_inicio = self.etapa_colheita.data_inicio.date()
        if self.etapa_colheita.data_fim:
            self.data_colheita_fim = self.etapa_colheita.data_fim.date()
        self.save(update_fields=[
            'peso_total_colhido_kg', 'umidade_media_pct', 'impureza_media_pct',
            'data_colheita_inicio', 'data_colheita_fim',
        ])


# ============================================================================
# PLUVIOMETRIA (RF-107)
# ============================================================================

class RegistroPluviometria(models.Model):
    TIPO_CHOICES = [('MANUAL', 'Manual'), ('AUTOMATICO', 'Automático')]

    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='registros_pluviometria')
    fazenda = models.ForeignKey('cadastros.Fazenda', on_delete=models.CASCADE, related_name='registros_pluviometria')
    data = models.DateField()
    mm_chuva = models.DecimalField(max_digits=6, decimal_places=1, validators=[MinValueValidator(Decimal('0'))], verbose_name='Precipitação (mm)')
    tipo_registro = models.CharField(max_length=20, choices=TIPO_CHOICES, default='MANUAL')
    fonte = models.CharField(max_length=100, blank=True, help_text='Pluviômetro, estação meteorológica, etc.')
    responsavel = models.ForeignKey('usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True, related_name='registros_pluviometria')
    observacoes = models.TextField(blank=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cadastros_registropluviometria'
        ordering = ['-data']
        unique_together = ['fazenda', 'data']
        verbose_name = 'Registro de Pluviometria'
        verbose_name_plural = 'Registros de Pluviometria'

    def __str__(self):
        return f"{self.fazenda.nome} — {self.data.strftime('%d/%m/%Y')} — {self.mm_chuva} mm"


# ============================================================================
# QUALIDADE DE CAMPO (RF-108)
# ============================================================================

class InspecaoQualidadeCampo(models.Model):
    TIPO_CHOICES = [
        ('FENOLOGICA', 'Fenológica'), ('VISUAL', 'Visual'),
        ('PRE_COLHEITA', 'Pré-colheita'), ('POS_COLHEITA', 'Pós-colheita'),
    ]
    COLORACAO_CHOICES = [
        ('VERDE', 'Verde'), ('INICIO_MATURACAO', 'Início de Maturação'),
        ('MADURO', 'Maduro'), ('PASSADO', 'Passado'),
    ]
    RESULTADO_CHOICES = [
        ('APROVADO', 'Aprovado'), ('APROVADO_COM_RESSALVA', 'Aprovado c/ Ressalva'), ('REPROVADO', 'Reprovado'),
    ]

    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='inspecoes_qualidade_campo')
    talhao = models.ForeignKey('cadastros.Talhao', on_delete=models.PROTECT, related_name='inspecoes_qualidade')
    safra = models.ForeignKey('cadastros.Safra', on_delete=models.SET_NULL, null=True, blank=True, related_name='inspecoes_qualidade')
    os = models.ForeignKey(OrdemServico, on_delete=models.SET_NULL, null=True, blank=True, related_name='inspecoes_qualidade', verbose_name='Ordem de Serviço')
    data_inspecao = models.DateField()
    responsavel = models.ForeignKey('rh.Funcionario', on_delete=models.SET_NULL, null=True, related_name='inspecoes_qualidade_campo')
    tipo_inspecao = models.CharField(max_length=30, choices=TIPO_CHOICES)
    estagio_cultura = models.CharField(max_length=50, blank=True)
    brix = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name='Brix (°Bx)')
    peso_medio_fruto_g = models.DecimalField(max_digits=7, decimal_places=1, null=True, blank=True, verbose_name='Peso médio do fruto (kg)')
    percentual_defeitos = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))], verbose_name='% Defeitos')
    coloracao = models.CharField(max_length=30, choices=COLORACAO_CHOICES, blank=True)
    resultado = models.CharField(max_length=30, choices=RESULTADO_CHOICES)
    previsao_colheita_dias = models.IntegerField(null=True, blank=True, verbose_name='Previsão p/ colheita (dias)')
    fotos = models.ImageField(upload_to='qualidade_campo/%Y/%m/', null=True, blank=True)
    observacoes = models.TextField(blank=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    cadastrado_por = models.ForeignKey('usuarios.Usuario', related_name='inspecoes_qualidade_criadas', null=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = 'cadastros_inspecaoqualidadecampo'
        ordering = ['-data_inspecao']
        verbose_name = 'Inspeção de Qualidade de Campo'
        verbose_name_plural = 'Inspeções de Qualidade de Campo'

    def __str__(self):
        return f"Inspeção {self.talhao.codigo} — {self.data_inspecao.strftime('%d/%m/%Y')} — {self.get_resultado_display()}"


# ============================================================================
# CADERNO DE CAMPO (RF-111)
# ============================================================================

class RegistroCadernoCampo(models.Model):
    TIPO_ATIVIDADE_CHOICES = [
        ('PREPARO_SOLO', 'Preparo de Solo'), ('PLANTIO', 'Plantio'), ('IRRIGACAO', 'Irrigação'),
        ('ADUBACAO', 'Adubação'), ('APLICACAO_DEFENSIVO', 'Aplicação de Defensivo'),
        ('COLHEITA', 'Colheita'), ('MANUTENCAO', 'Manutenção'), ('MONITORAMENTO', 'Monitoramento'), ('OUTRO', 'Outro'),
    ]
    CONDICAO_TEMPO_CHOICES = [
        ('ENSOLARADO', 'Ensolarado'), ('NUBLADO', 'Nublado'), ('CHUVOSO', 'Chuvoso'),
        ('VENTO_FORTE', 'Vento Forte'), ('PARCIALMENTE_NUBLADO', 'Parcialmente Nublado'),
    ]

    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='caderno_campo')
    talhao = models.ForeignKey('cadastros.Talhao', on_delete=models.PROTECT, related_name='caderno_campo')
    safra = models.ForeignKey('cadastros.Safra', on_delete=models.SET_NULL, null=True, blank=True, related_name='caderno_campo')
    os = models.ForeignKey(OrdemServico, on_delete=models.SET_NULL, null=True, blank=True, related_name='caderno_campo', verbose_name='Ordem de Serviço')
    data_atividade = models.DateField()
    tipo_atividade = models.CharField(max_length=30, choices=TIPO_ATIVIDADE_CHOICES)
    atividade = models.CharField(max_length=200, help_text='Descrição resumida da atividade realizada')
    temperatura = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, verbose_name='Temperatura (°C)')
    umidade = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)], verbose_name='Umidade relativa (%)')
    condicao_tempo = models.CharField(max_length=30, choices=CONDICAO_TEMPO_CHOICES, blank=True)
    responsavel = models.ForeignKey('usuarios.Usuario', on_delete=models.SET_NULL, null=True, related_name='registros_caderno_campo')
    observacoes = models.TextField(blank=True)
    fotos = models.ImageField(upload_to='caderno_campo/%Y/%m/', null=True, blank=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    cadastrado_por = models.ForeignKey('usuarios.Usuario', related_name='caderno_campo_criados', null=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = 'cadastros_registrocadernocampo'
        ordering = ['-data_atividade', '-data_cadastro']
        verbose_name = 'Registro do Caderno de Campo'
        verbose_name_plural = 'Registros do Caderno de Campo'

    def __str__(self):
        return f"{self.talhao.codigo} — {self.get_tipo_atividade_display()} — {self.data_atividade.strftime('%d/%m/%Y')}"


class RegistroCadernoCampoInsumo(models.Model):
    registro = models.ForeignKey(RegistroCadernoCampo, on_delete=models.CASCADE, related_name='insumos_utilizados')
    produto = models.ForeignKey('produtos.Produto', on_delete=models.PROTECT)
    praga = models.ForeignKey(
        'cadastros.Praga', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='insumos_caderno_campo', verbose_name='Praga/Doença Alvo',
    )
    quantidade = models.DecimalField(max_digits=12, decimal_places=3, validators=[MinValueValidator(Decimal('0.001'))])
    unidade_medida = models.ForeignKey('produtos.UnidadeMedida', on_delete=models.PROTECT)
    receituario_numero = models.CharField(max_length=50, blank=True, verbose_name='Nº Receituário Agronômico')
    carencia_dias = models.IntegerField(null=True, blank=True, verbose_name='Carência (dias)')
    observacoes = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = 'cadastros_registrocadernocampoinsumo'
        verbose_name = 'Insumo do Caderno de Campo'
        verbose_name_plural = 'Insumos do Caderno de Campo'

    def __str__(self):
        return f"{self.produto} — {self.quantidade} {self.unidade_medida}"


class RegistroCadernoCampoFuncionario(models.Model):
    registro = models.ForeignKey(RegistroCadernoCampo, on_delete=models.CASCADE, related_name='funcionarios_atividade')
    funcionario = models.ForeignKey('rh.Funcionario', on_delete=models.PROTECT)
    horas_trabalhadas = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('0.01'))], verbose_name='Horas trabalhadas')

    class Meta:
        db_table = 'cadastros_registrocadernocampofuncionario'
        verbose_name = 'Funcionário do Caderno de Campo'
        verbose_name_plural = 'Funcionários do Caderno de Campo'
        unique_together = ['registro', 'funcionario']

    def __str__(self):
        return f"{self.funcionario} — {self.horas_trabalhadas or '—'} h"


def proximo_numero_corte(talhao, safra=None, excluir_pk=None):
    """
    Calcula o próximo número de corte de colheita para o talhão informado,
    contando as OS de Colheita já registradas (excluindo canceladas) — 1º, 2º,
    3º corte etc. do mesmo ciclo (cana-de-açúcar, forragens etc.).

    Escopo por safra quando informada, para não somar cortes de ciclos/safras
    diferentes. `excluir_pk` descarta a própria OS ao recalcular numa edição.
    """
    qs = OrdemServico.objects.filter(talhao=talhao, tipo='COLHEITA').exclude(status='CANCELADA')
    if safra:
        qs = qs.filter(safra=safra)
    if excluir_pk:
        qs = qs.exclude(pk=excluir_pk)
    return qs.count() + 1


def cultura_atual_talhao(talhao, safra=None):
    """Retorna a `Cultura` (cadastros.Cultura) plantada no talhão para a safra informada,
    resolvida via `SafraCultura` (o talhão não tem FK direta para cultura)."""
    if not safra:
        return None
    safra_cultura = safra.culturas.filter(talhoes=talhao).select_related('cultura').first()
    return safra_cultura.cultura if safra_cultura else None


def verificar_carencia_defensivos(talhao, safra=None):
    """
    Verifica, a partir do Caderno de Campo, se há aplicação de defensivo no talhão
    cuja carência (período entre aplicação e colheita) ainda não foi cumprida.

    Retorna uma lista de pendências (dicts com produto/data_aplicacao/carencia_dias/
    data_liberacao/dias_restantes), ordenada da mais restritiva para a menos restritiva.
    Lista vazia = apto para colheita.
    """
    from produtos.models import ProdutoDefensivoCultura

    hoje = timezone.now().date()
    cultura = cultura_atual_talhao(talhao, safra)

    registros = RegistroCadernoCampo.objects.filter(
        talhao=talhao, tipo_atividade='APLICACAO_DEFENSIVO',
    ).prefetch_related('insumos_utilizados__produto')
    if safra:
        registros = registros.filter(safra=safra)

    pendencias = []
    for registro in registros:
        for insumo in registro.insumos_utilizados.all():
            carencia_dias = insumo.carencia_dias
            if not carencia_dias and cultura:
                carencia_dias = ProdutoDefensivoCultura.objects.filter(
                    produto=insumo.produto, cultura=cultura
                ).aggregate(models.Max('carencia'))['carencia__max']
            if not carencia_dias:
                carencia_dias = insumo.produto.periodo_carencia
            if not carencia_dias:
                continue

            data_liberacao = registro.data_atividade + timedelta(days=carencia_dias)
            if data_liberacao > hoje:
                pendencias.append({
                    'produto': insumo.produto,
                    'data_aplicacao': registro.data_atividade,
                    'carencia_dias': carencia_dias,
                    'data_liberacao': data_liberacao,
                    'dias_restantes': (data_liberacao - hoje).days,
                })

    return sorted(pendencias, key=lambda p: p['data_liberacao'], reverse=True)


# ============================================================================
# PLANEJAMENTO DE CUSTO DE SAFRA
# ============================================================================

class PlanejamentoCustoSafra(models.Model):
    CATEGORIA_CHOICES = [
        ('MO', 'Mão de Obra'), ('MAQUINARIO', 'Maquinário'), ('INSUMO', 'Insumo'),
        ('SERVICO_EXTERNO', 'Serviço Externo'), ('ESTUFA', 'Estufa / Transplantio'),
    ]

    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='planejamentos_custo')
    safra = models.ForeignKey('cadastros.Safra', on_delete=models.SET_NULL, null=True, blank=True, related_name='planejamentos_custo')
    cultura = models.ForeignKey('cadastros.Cultura', on_delete=models.PROTECT, related_name='planejamentos_custo')
    talhao = models.ForeignKey('cadastros.Talhao', on_delete=models.SET_NULL, null=True, blank=True, related_name='planejamentos_custo')
    nome = models.CharField(max_length=120, help_text='Ex: Planejamento Tomate 2026')
    area_ha = models.DecimalField(max_digits=10, decimal_places=4, verbose_name='Área (ha)')
    observacoes = models.TextField(blank=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    criado_por = models.ForeignKey('usuarios.Usuario', null=True, on_delete=models.SET_NULL, related_name='planejamentos_custo_criados')

    # Receita esperada (para cálculo de margem e break-even)
    produtividade_esperada_ha = models.DecimalField(
        'Produtividade Esperada (por ha)', max_digits=12, decimal_places=4,
        null=True, blank=True,
        help_text='Ex: 60 sc/ha para soja, 80 t/ha para cana.',
    )
    preco_venda_unitario = models.DecimalField(
        'Preço de Venda Unitário (R$)', max_digits=12, decimal_places=4,
        null=True, blank=True,
        help_text='Preço esperado por unidade produzida.',
    )
    unidade_producao = models.CharField(
        'Unidade de Produção', max_length=20, default='sc', blank=True,
        help_text='Ex: sc, kg, t, cx, dz.',
    )
    kg_por_unidade = models.DecimalField(
        'kg por Unidade de Produção', max_digits=10, decimal_places=4,
        default=Decimal('60'), blank=True,
        help_text='Fator de conversão kg→unidade. Ex: 60 para soja (saca de 60kg).',
    )

    class Meta:
        db_table = 'cadastros_planejamentocustosafra'
        ordering = ['-data_criacao']
        verbose_name = 'Planejamento de Custo'
        verbose_name_plural = 'Planejamentos de Custo'

    def __str__(self):
        return self.nome

    @property
    def custo_total_planejado(self):
        return sum((item.custo_total for item in self.itens.all()), Decimal('0'))

    @property
    def custo_planejado_por_ha(self):
        if self.area_ha and self.area_ha > 0:
            return (self.custo_total_planejado / self.area_ha).quantize(Decimal('0.01'))
        return Decimal('0')

    @property
    def receita_esperada(self):
        if self.produtividade_esperada_ha and self.preco_venda_unitario and self.area_ha:
            return (self.produtividade_esperada_ha * self.preco_venda_unitario * self.area_ha).quantize(Decimal('0.01'))
        return None

    @property
    def margem_bruta(self):
        receita = self.receita_esperada
        if receita is None:
            return None
        return (receita - self.custo_total_planejado).quantize(Decimal('0.01'))

    @property
    def margem_pct(self):
        receita = self.receita_esperada
        if not receita or receita == 0:
            return None
        margem = self.margem_bruta
        if margem is None:
            return None
        return (margem / receita * Decimal('100')).quantize(Decimal('0.1'))

    @property
    def ponto_equilibrio_ha(self):
        """Área mínima para cobrir o custo total ao preço de venda informado."""
        if self.produtividade_esperada_ha and self.preco_venda_unitario:
            receita_ha = self.produtividade_esperada_ha * self.preco_venda_unitario
            custo_ha = self.custo_planejado_por_ha
            if receita_ha and receita_ha > 0 and custo_ha:
                return (self.custo_total_planejado / receita_ha).quantize(Decimal('0.01'))
        return None

    @property
    def tem_receita(self):
        return bool(self.produtividade_esperada_ha and self.preco_venda_unitario)


CATEGORIA_CUSTO_CHOICES = [
    ('MO', 'Mão de Obra'), ('MAQUINARIO', 'Maquinário'), ('INSUMO', 'Insumo'),
    ('SERVICO_EXTERNO', 'Serviço Externo'), ('ESTUFA', 'Estufa / Transplantio'),
]


class SubcategoriaItemCusto(models.Model):
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CUSTO_CHOICES, verbose_name='Categoria')
    nome = models.CharField(max_length=100, verbose_name='Nome')
    ativo = models.BooleanField(default=True)

    class Meta:
        db_table = 'pc_subcategoria_item_custo'
        ordering = ['categoria', 'nome']
        unique_together = [('categoria', 'nome')]
        verbose_name = 'Subcategoria de Custo'
        verbose_name_plural = 'Subcategorias de Custo'

    def __str__(self):
        return self.nome


class PlanejamentoCustoItem(models.Model):
    CATEGORIA_CHOICES = CATEGORIA_CUSTO_CHOICES
    FASE_CHOICES = [
        ('GERAL', 'Geral'),
        ('PREPARO_SOLO', 'Preparo de Solo'),
        ('PLANTIO', 'Plantio / Semeadura'),
        ('TRATOS_CULTURAIS', 'Tratos Culturais'),
        ('COLHEITA', 'Colheita'),
        ('POS_COLHEITA', 'Pós-Colheita'),
    ]

    planejamento = models.ForeignKey(PlanejamentoCustoSafra, on_delete=models.CASCADE, related_name='itens')
    fase = models.CharField('Fase de Cultivo', max_length=20, choices=FASE_CHOICES, default='GERAL', blank=True)
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, verbose_name='Categoria')
    subcategoria = models.ForeignKey(
        SubcategoriaItemCusto, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='Subcategoria', related_name='itens_custo',
    )
    tipo_servico = models.ForeignKey(
        'operacoes_campo.TipoServicoOS', on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='Tipo de Serviço', related_name='itens_planejamento',
    )
    subtipo_servico = models.ForeignKey(
        'operacoes_campo.SubtipoServicoOS', on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='Operação', related_name='itens_planejamento',
    )
    produto = models.ForeignKey('produtos.Produto', on_delete=models.SET_NULL, null=True, blank=True, help_text='Preencher para insumos')
    descricao = models.CharField(max_length=200)
    dose_por_ha = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True, verbose_name='Dose/ha')
    unidade_medida = models.ForeignKey('produtos.UnidadeMedida', on_delete=models.SET_NULL, null=True, blank=True)
    custo_unitario = models.DecimalField(max_digits=12, decimal_places=4, validators=[MinValueValidator(Decimal('0'))], verbose_name='Custo unitário (R$)')
    area_ha = models.DecimalField(max_digits=10, decimal_places=4, verbose_name='Área (ha)')

    class Meta:
        db_table = 'cadastros_planejamentocustoitem'
        verbose_name = 'Item de Planejamento de Custo'
        verbose_name_plural = 'Itens de Planejamento de Custo'

    def __str__(self):
        return f"{self.descricao} ({self.get_categoria_display()})"

    @property
    def quantidade_total(self):
        if self.dose_por_ha and self.area_ha:
            return (self.dose_por_ha * self.area_ha).quantize(Decimal('0.001'))
        return Decimal('0')

    @property
    def custo_total(self):
        if self.dose_por_ha and self.area_ha:
            return (self.dose_por_ha * self.area_ha * self.custo_unitario).quantize(Decimal('0.01'))
        if self.area_ha:
            return (self.area_ha * self.custo_unitario).quantize(Decimal('0.01'))
        return Decimal('0')


class PlanejamentoCustoItemIndireto(models.Model):
    """Custos pós-campo (embalagem, comissão, energia, frete) do planejamento de safra."""

    TIPO_CHOICES = [
        ('EMBALAGEM', 'Embalagem'),
        ('COMISSAO', 'Comissão de Venda (%)'),
        ('ENERGIA', 'Energia Elétrica'),
        ('FRETE', 'Frete / Logística'),
        ('OUTROS', 'Outros'),
    ]

    planejamento = models.ForeignKey(
        PlanejamentoCustoSafra, on_delete=models.CASCADE, related_name='itens_indiretos',
        verbose_name='Planejamento',
    )
    tipo = models.CharField('Tipo', max_length=20, choices=TIPO_CHOICES)
    descricao = models.CharField('Descrição', max_length=200)
    valor_fixo = models.DecimalField(
        'Valor Fixo (R$)', max_digits=12, decimal_places=2, null=True, blank=True,
        help_text='Valor absoluto em reais. Use este ou o percentual.',
    )
    percentual_receita = models.DecimalField(
        '% da Receita', max_digits=5, decimal_places=2, null=True, blank=True,
        help_text='Percentual da receita esperada. Use este ou o valor fixo.',
    )
    inclui_no_total = models.BooleanField(
        'Incluir no Total Geral', default=True,
        help_text='Se marcado, esse custo entra no custo total do planejamento.',
    )

    class Meta:
        db_table = 'pc_item_indireto'
        verbose_name = 'Custo Pós-Campo'
        verbose_name_plural = 'Custos Pós-Campo'
        ordering = ['tipo', 'descricao']

    def __str__(self):
        return f"{self.get_tipo_display()} — {self.descricao}"

    @property
    def custo_calculado(self):
        if self.percentual_receita is not None:
            receita = self.planejamento.receita_esperada
            if receita:
                return (receita * self.percentual_receita / Decimal('100')).quantize(Decimal('0.01'))
            return Decimal('0')
        return self.valor_fixo or Decimal('0')


class FormacaoPreco(models.Model):
    """Formação de preço mínimo e preço-meta em BRL/USD/EUR para um planejamento de safra."""

    planejamento = models.OneToOneField(
        PlanejamentoCustoSafra, on_delete=models.CASCADE, related_name='formacao_preco',
        verbose_name='Planejamento',
    )
    producao_prevista_total = models.DecimalField(
        'Produção Prevista Total', max_digits=12, decimal_places=4, null=True, blank=True,
        help_text='Total na unidade de produção do planejamento (sc, kg, t…).',
    )
    pct_avaria_prevista = models.DecimalField(
        '% Avaria / Descarte', max_digits=5, decimal_places=2, default=Decimal('0'),
        help_text='Percentual da produção bruta que se perde por avaria ou descarte.',
    )
    margem_desejada_pct = models.DecimalField(
        'Margem Desejada (%)', max_digits=5, decimal_places=2, default=Decimal('20'),
    )
    inclui_custos_indiretos = models.BooleanField(
        'Incluir Custos Pós-Campo', default=True,
        help_text='Somar os itens indiretos marcados ao custo de campo.',
    )

    class Meta:
        db_table = 'pc_formacao_preco'
        verbose_name = 'Formação de Preço'
        verbose_name_plural = 'Formações de Preço'

    def __str__(self):
        return f"Formação de Preço — {self.planejamento.nome}"

    @property
    def producao_comercializavel(self):
        if not self.producao_prevista_total:
            return None
        fator = Decimal('1') - (self.pct_avaria_prevista / Decimal('100'))
        return (self.producao_prevista_total * fator).quantize(Decimal('0.0001'))

    @property
    def custo_campo(self):
        return self.planejamento.custo_total_planejado

    @property
    def custo_indireto_total(self):
        return sum(
            (i.custo_calculado for i in self.planejamento.itens_indiretos.filter(inclui_no_total=True)),
            Decimal('0'),
        )

    @property
    def custo_total_base(self):
        base = self.custo_campo
        if self.inclui_custos_indiretos:
            base += self.custo_indireto_total
        return base

    @property
    def custo_por_unidade(self):
        prod = self.producao_comercializavel
        if not prod or prod == 0:
            return None
        return (self.custo_total_base / prod).quantize(Decimal('0.01'))

    @property
    def preco_minimo_brl(self):
        cpu = self.custo_por_unidade
        if cpu is None:
            return None
        return (cpu * (Decimal('1') + self.margem_desejada_pct / Decimal('100'))).quantize(Decimal('0.01'))


# ============================================================================
# REGISTRO DE EXECUÇÃO (dados específicos por tipo de serviço)
# ============================================================================

class OSRegistroExecucao(models.Model):
    """Dados de campo registrados pelo operador ao executar/concluir a OS."""

    VENTO_CHOICES = [
        ('CALMO', 'Calmo (< 5 km/h)'),
        ('LEVE', 'Leve (5–15 km/h)'),
        ('MODERADO', 'Moderado (15–30 km/h)'),
        ('FORTE', 'Forte (> 30 km/h)'),
    ]
    TRATO_CHOICES = [
        ('CAPINA', 'Capina'),
        ('VIRAR_FRUTO', 'Virar Fruto'),
        ('PODA', 'Poda'),
        ('AMARRIO', 'Amarrio'),
        ('RALEIO', 'Raleio'),
        ('COBERTURA_MORTA', 'Cobertura Morta'),
        ('OUTRO', 'Outro'),
    ]

    ordem_servico = models.OneToOneField(
        OrdemServico, on_delete=models.CASCADE,
        related_name='registro_execucao', verbose_name='Ordem de Serviço',
    )
    empresa = models.ForeignKey(
        'empresas.Empresa', on_delete=models.CASCADE,
        related_name='registros_execucao_os', verbose_name='Empresa',
    )
    registrado_por = models.ForeignKey(
        'rh.Funcionario', on_delete=models.SET_NULL, null=True,
        related_name='registros_execucao', verbose_name='Registrado por',
    )
    registrado_em = models.DateTimeField('Data/Hora do Registro', auto_now_add=True)

    # Campos comuns
    area_executada_ha = models.DecimalField(
        'Área Executada (ha)', max_digits=10, decimal_places=4,
        null=True, blank=True, validators=[MinValueValidator(Decimal('0'))],
    )
    observacoes = models.TextField('Observações', blank=True)

    # Pulverização (PULV_MECANICA, PULV_COSTAL)
    volume_calda_litros = models.DecimalField('Volume de Calda (L)', max_digits=10, decimal_places=2, null=True, blank=True)
    vazao_bicos_lmin = models.DecimalField('Vazão dos Bicos (L/min)', max_digits=8, decimal_places=3, null=True, blank=True)
    velocidade_kmh = models.DecimalField('Velocidade de Aplicação (km/h)', max_digits=6, decimal_places=2, null=True, blank=True)
    condicao_vento = models.CharField('Condição do Vento', max_length=10, choices=VENTO_CHOICES, blank=True)
    temperatura_c = models.DecimalField('Temperatura (°C)', max_digits=5, decimal_places=1, null=True, blank=True)
    umidade_relativa_pct = models.DecimalField('Umidade Relativa (%)', max_digits=5, decimal_places=1, null=True, blank=True)

    # Irrigação / Fertirrigação (IRRIGACAO, ADUBACAO)
    poco = models.ForeignKey(
        'cadastros.Poco', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='registros_execucao', verbose_name='Poço utilizado',
    )
    horas_bomba = models.DecimalField('Horas de Bomba', max_digits=7, decimal_places=2, null=True, blank=True)
    volume_agua_m3 = models.DecimalField('Volume de Água (m³)', max_digits=10, decimal_places=2, null=True, blank=True)
    setor_irrigado = models.CharField('Setor Irrigado', max_length=100, blank=True)

    # Preparo de Solo (PREPARO_SOLO)
    profundidade_cm = models.DecimalField('Profundidade (cm)', max_digits=6, decimal_places=1, null=True, blank=True)
    implemento_utilizado = models.CharField('Implemento Utilizado', max_length=100, blank=True)

    # Plantio (PLANTIO) — campo aberto e estufa/viveiro
    quantidade_mudas = models.IntegerField('Quantidade de Mudas', null=True, blank=True, validators=[MinValueValidator(0)])
    espacamento_m = models.DecimalField('Espaçamento (m)', max_digits=6, decimal_places=2, null=True, blank=True)
    plantio_em_estufa = models.BooleanField('Plantio em Estufa/Viveiro', default=False)

    # Tratos Culturais (MANUTENCAO / tratos)
    tipo_trato = models.CharField('Tipo de Trato', max_length=20, choices=TRATO_CHOICES, blank=True)
    tipo_trato_outro = models.CharField('Trato (outro)', max_length=100, blank=True)

    # Fallback JSON para campos não mapeados
    dados_extras = models.JSONField('Dados Extras', default=dict, blank=True)

    class Meta:
        db_table = 'campo_os_registro_execucao'
        verbose_name = 'Registro de Execução da OS'
        verbose_name_plural = 'Registros de Execução de OS'

    def __str__(self):
        return f"Execução — {self.ordem_servico.numero}"


# ============================================================================
# PUSH SUBSCRIPTIONS (Portal Campo PWA)
# ============================================================================

class PushSubscriptionCampo(models.Model):
    """Subscription Web Push de funcionário de campo para notificações PWA."""

    funcionario = models.ForeignKey(
        'rh.Funcionario', on_delete=models.CASCADE,
        related_name='push_subscriptions', verbose_name='Funcionário',
    )
    empresa = models.ForeignKey(
        'empresas.Empresa', on_delete=models.CASCADE,
        related_name='push_subscriptions_campo', verbose_name='Empresa',
    )
    endpoint = models.TextField('Endpoint')
    p256dh = models.TextField('Chave Pública (p256dh)')
    auth = models.TextField('Token de Autenticação (auth)')
    ativo = models.BooleanField('Ativo', default=True)
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)

    class Meta:
        db_table = 'campo_push_subscription'
        verbose_name = 'Push Subscription do Campo'
        verbose_name_plural = 'Push Subscriptions do Campo'
        indexes = [
            models.Index(fields=['funcionario', 'ativo']),
        ]

    def __str__(self):
        return f"Push — {self.funcionario}"


# ============================================================================
# CONFIGURAÇÕES DO PORTAL DO CAMPO
# ============================================================================

class PortalCampoConfig(models.Model):
    """Configurações do Portal do Campo por empresa."""

    HORARIO_TRABALHADORES_AUTO = 'AUTO'
    HORARIO_TRABALHADORES_OMITIR = 'OMITIR'
    HORARIO_TRABALHADORES_CHOICES = [
        (HORARIO_TRABALHADORES_AUTO,   'Auto-preencher com horário do operador (editável)'),
        (HORARIO_TRABALHADORES_OMITIR, 'Usar horário do operador automaticamente (sem perguntar)'),
    ]

    empresa = models.OneToOneField(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='portal_campo_config',
        verbose_name='Empresa',
    )
    horario_trabalhadores = models.CharField(
        'Horário dos trabalhadores adicionais',
        max_length=10,
        choices=HORARIO_TRABALHADORES_CHOICES,
        default=HORARIO_TRABALHADORES_AUTO,
        help_text='Define como o horário é preenchido ao adicionar outros trabalhadores na execução de uma OS.',
    )
    fator_encargos = models.DecimalField(
        'Fator de Encargos Trabalhistas',
        max_digits=5,
        decimal_places=4,
        default=Decimal('1.0000'),
        help_text=(
            'Multiplica o custo/hora da mão de obra para incluir encargos. '
            'Exemplo: 1.70 para CLT (INSS + FGTS + férias + 13º ≈ +70%). '
            'Use 1.0 para considerar apenas o salário base.'
        ),
    )
    data_atualizacao = models.DateTimeField('Última atualização', auto_now=True)

    class Meta:
        db_table = 'campo_portal_config'
        verbose_name = 'Configuração do Portal do Campo'
        verbose_name_plural = 'Configurações do Portal do Campo'

    def __str__(self):
        return f"Config Portal — {self.empresa}"
