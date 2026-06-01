from django.db import models


class UsinaFotovoltaica(models.Model):
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='usinas_fotovoltaicas',
        verbose_name='Empresa',
    )
    codigo = models.CharField('Código', max_length=20)
    nome = models.CharField('Nome / Descrição', max_length=120)
    capacidade_kwp = models.DecimalField('Capacidade (kWp)', max_digits=8, decimal_places=2)
    geracao_acordada_mensal_kwh = models.DecimalField(
        'Geração Acordada Mensal (kWh)', max_digits=10, decimal_places=2, default=0)
    geracao_acordada_anual_kwh = models.DecimalField(
        'Geração Acordada Anual (kWh)', max_digits=10, decimal_places=2, default=0)
    prognostico_mensal_kwh = models.DecimalField(
        'Prognóstico de Geração Mensal (kWh)', max_digits=10, decimal_places=2, default=0)
    data_instalacao = models.DateField('Data de Instalação', null=True, blank=True)
    ativa = models.BooleanField('Ativa', default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Usina Fotovoltaica'
        verbose_name_plural = 'Usinas Fotovoltaicas'
        ordering = ['nome']
        unique_together = [('empresa', 'codigo')]

    def __str__(self):
        return f'{self.codigo} — {self.nome} ({self.capacidade_kwp} kWp)'


class UnidadeConsumidora(models.Model):
    TIPO_CHOICES = [
        ('GERADORA', 'Geradora (onde os painéis estão instalados)'),
        ('BENEFICIARIA', 'Beneficiária (recebe créditos de energia)'),
        ('CONVENCIONAL', 'Convencional (sem energia solar)'),
    ]

    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='unidades_consumidoras',
        verbose_name='Empresa',
    )
    usina = models.ForeignKey(
        UsinaFotovoltaica,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='unidades_consumidoras',
        verbose_name='Usina',
    )
    tipo = models.CharField('Tipo', max_length=12, choices=TIPO_CHOICES, default='BENEFICIARIA')
    codigo_cliente = models.CharField('Código do Cliente', max_length=20)
    codigo_instalacao = models.CharField('Código de Instalação', max_length=20, blank=True)
    nome = models.CharField('Nome / Descrição', max_length=120)
    classificacao = models.CharField('Classificação', max_length=80, blank=True)
    tipo_fornecimento = models.CharField('Tipo de Fornecimento', max_length=80, blank=True)
    numero_medidor = models.CharField('Número do Medidor', max_length=20, blank=True)
    ativa = models.BooleanField('Ativa', default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Unidade Consumidora'
        verbose_name_plural = 'Unidades Consumidoras'
        ordering = ['nome']
        unique_together = [('empresa', 'codigo_cliente')]

    def __str__(self):
        return f'{self.nome} ({self.codigo_cliente})'


class LancamentoMensal(models.Model):
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='lancamentos_energia',
        verbose_name='Empresa',
    )
    unidade_consumidora = models.ForeignKey(
        UnidadeConsumidora,
        on_delete=models.CASCADE,
        related_name='lancamentos',
        verbose_name='Unidade Consumidora',
    )
    mes_referencia = models.DateField('Mês de Referência')
    data_leitura_anterior = models.DateField('Leitura Anterior', null=True, blank=True)
    data_leitura_atual = models.DateField('Leitura Atual', null=True, blank=True)
    num_dias = models.IntegerField('Nº de Dias', default=30)
    consumo_registrado_kwh = models.DecimalField(
        'Consumo Registrado (kWh)', max_digits=12, decimal_places=2, default=0)
    energia_compensada_kwh = models.DecimalField(
        'Energia Compensada (kWh)', max_digits=12, decimal_places=2, default=0)
    energia_faturada_kwh = models.DecimalField(
        'Energia Faturada (kWh)', max_digits=12, decimal_places=2, default=0)
    energia_injetada_kwh = models.DecimalField(
        'Energia Injetada (kWh)', max_digits=12, decimal_places=2, default=0,
        help_text='Somente para UC Geradora')
    credito_anterior_kwh = models.DecimalField(
        'Crédito Anterior (kWh)', max_digits=12, decimal_places=2, default=0)
    credito_acumulado_kwh = models.DecimalField(
        'Crédito Acumulado (kWh)', max_digits=12, decimal_places=2, default=0)
    valor_faturado_rs = models.DecimalField(
        'Valor Faturado (R$)', max_digits=12, decimal_places=2, default=0)
    valor_economizado_rs = models.DecimalField(
        'Valor Economizado (R$)', max_digits=12, decimal_places=2, default=0)
    desconto_incondicional_rs = models.DecimalField(
        'Desconto Incondicional (R$)', max_digits=12, decimal_places=2, default=0)
    observacoes = models.TextField('Observações', blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Lançamento Mensal'
        verbose_name_plural = 'Lançamentos Mensais'
        ordering = ['-mes_referencia', 'unidade_consumidora']
        unique_together = [('unidade_consumidora', 'mes_referencia')]

    def __str__(self):
        return f'{self.unidade_consumidora} — {self.mes_referencia.strftime("%m/%Y")}'


class RelatorioMensalUsina(models.Model):
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='relatorios_usina',
        verbose_name='Empresa',
    )
    usina = models.ForeignKey(
        UsinaFotovoltaica,
        on_delete=models.CASCADE,
        related_name='relatorios',
        verbose_name='Usina',
    )
    mes_referencia = models.DateField('Mês de Referência')
    geracao_kwh = models.DecimalField('Geração (kWh)', max_digits=12, decimal_places=2, default=0)
    desempenho_pct = models.DecimalField('Desempenho (%)', max_digits=5, decimal_places=2, default=0)
    consumo_total_kwh = models.DecimalField(
        'Consumo Total (kWh)', max_digits=12, decimal_places=2, default=0)
    consumo_registrado_kwh = models.DecimalField(
        'Consumo Registrado (kWh)', max_digits=12, decimal_places=2, default=0)
    uc_geradora_kwh = models.DecimalField(
        'Unidade Geradora (kWh)', max_digits=12, decimal_places=2, default=0)
    consumo_instantaneo_kwh = models.DecimalField(
        'Consumo Instantâneo (kWh)', max_digits=12, decimal_places=2, default=0)
    energia_injetada_kwh = models.DecimalField(
        'Energia Injetada (kWh)', max_digits=12, decimal_places=2, default=0)
    economia_rs = models.DecimalField('Economia (R$)', max_digits=12, decimal_places=2, default=0)
    faturado_rs = models.DecimalField('Faturado (R$)', max_digits=12, decimal_places=2, default=0)
    retorno_financeiro_pct = models.DecimalField(
        'Retorno Financeiro (%)', max_digits=6, decimal_places=2, default=0)
    economia_total_rs = models.DecimalField(
        'Economia Total Acumulada (R$)', max_digits=14, decimal_places=2, default=0)
    retorno_financeiro_total_pct = models.DecimalField(
        'Retorno Financeiro Total (%)', max_digits=8, decimal_places=2, default=0)
    co2_nao_produzido_t = models.DecimalField(
        'CO₂ não Produzido (t)', max_digits=10, decimal_places=2, default=0)
    arvores_salvas = models.IntegerField('Árvores Salvas', default=0)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Relatório Mensal de Usina'
        verbose_name_plural = 'Relatórios Mensais de Usinas'
        ordering = ['-mes_referencia', 'usina']
        unique_together = [('usina', 'mes_referencia')]

    def __str__(self):
        return f'{self.usina.codigo} — {self.mes_referencia.strftime("%m/%Y")}'


class OcorrenciaUsina(models.Model):
    TIPO_CHOICES = [
        ('FALHA_EQUIPAMENTO', 'Falha de Equipamento'),
        ('MANUTENCAO',        'Manutenção Programada'),
        ('SUJEIRA',           'Sujeira / Limpeza'),
        ('SOMBRA',            'Sombreamento'),
        ('CONEXAO_REDE',      'Problema de Conexão com a Rede'),
        ('CLIMA',             'Condição Climática'),
        ('OUTRO',             'Outro'),
    ]

    GRAVIDADE_CHOICES = [
        ('BAIXA',  'Baixa'),
        ('MEDIA',  'Média'),
        ('ALTA',   'Alta'),
        ('CRITICA','Crítica'),
    ]

    empresa = models.ForeignKey(
        'empresas.Empresa', on_delete=models.CASCADE,
        related_name='ocorrencias_usina', verbose_name='Empresa',
    )
    usina = models.ForeignKey(
        UsinaFotovoltaica, on_delete=models.CASCADE,
        related_name='ocorrencias', verbose_name='Usina',
    )
    relatorio = models.ForeignKey(
        RelatorioMensalUsina, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='ocorrencias',
        verbose_name='Relatório Mensal (opcional)',
        help_text='Vincule ao relatório do mês para justificar o desempenho.',
    )
    tipo = models.CharField('Tipo', max_length=20, choices=TIPO_CHOICES)
    gravidade = models.CharField('Gravidade', max_length=8, choices=GRAVIDADE_CHOICES, default='MEDIA')
    titulo = models.CharField('Título', max_length=120)
    descricao = models.TextField('Descrição / Justificativa')
    data_ocorrencia = models.DateField('Data da Ocorrência')
    data_resolucao = models.DateField('Data de Resolução', null=True, blank=True)
    impacto_kwh_estimado = models.DecimalField(
        'Impacto Estimado (kWh)', max_digits=10, decimal_places=2, default=0,
        help_text='Geração estimada perdida por causa desta ocorrência.')
    resolvido = models.BooleanField('Resolvido', default=False)
    responsavel = models.CharField('Responsável', max_length=80, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Ocorrência de Usina'
        verbose_name_plural = 'Ocorrências de Usinas'
        ordering = ['-data_ocorrencia']

    def __str__(self):
        return f'{self.usina.codigo} — {self.titulo} ({self.data_ocorrencia})'
