# Método utilitário para recalcular estoque do produto
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models

def recalcular_estoque(self):
    """
    Recalcula o estoque_atual baseado em todos os lotes
    Útil para ajustes manuais ou correções
    """
    total = self.lotes.filter(
        status__in=['DISPONIVEL', 'BLOQUEADO']
    ).aggregate(total=models.Sum('quantidade_atual'))['total']
    self.estoque_atual = Decimal(total) if total is not None else Decimal('0.000')
    self.save(update_fields=['estoque_atual'])

# Adicione ao modelo Produto:
setattr(models.Model, 'recalcular_estoque', recalcular_estoque)
from django.db import models
from cadastros.models import NCM, Fornecedor, CFOP


class TipoProduto(models.Model):
    """Tipo de Produto (Revenda, Consumo, etc.) - Cadastro dinâmico"""
    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='tipos_produto', verbose_name='Empresa')
    nome = models.CharField(max_length=100, verbose_name='Nome')
    codigo = models.CharField(max_length=30, verbose_name='Código', help_text='Código interno para controle')
    ativo = models.BooleanField(default=True, verbose_name='Ativo')
    
    class Meta:
        verbose_name = 'Tipo de Produto'
        verbose_name_plural = 'Tipos de Produto'
        ordering = ['nome']
        unique_together = [['empresa', 'codigo']]
    
    def __str__(self):
        return self.nome


class Marca(models.Model):
    """Marca comercial vinculável a produtos/etiquetas (ex: em etiquetas_avulsas)."""
    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='marcas', verbose_name='Empresa')
    nome = models.CharField(max_length=100, verbose_name='Nome')
    ativo = models.BooleanField(default=True, verbose_name='Ativo')

    class Meta:
        verbose_name = 'Marca'
        verbose_name_plural = 'Marcas'
        ordering = ['nome']
        constraints = [
            models.UniqueConstraint(fields=['empresa', 'nome'], name='unique_marca_por_empresa'),
        ]

    def __str__(self):
        return self.nome


class UnidadeMedida(models.Model):
    TIPO_CHOICES = [
        ('PESO', 'Peso'),
        ('VOLUME', 'Volume'),
        ('UNIDADE', 'Unidade'),
        ('AREA', 'Área'),
        ('COMPRIMENTO', 'Comprimento'),
    ]
    
    # Multi-tenant
    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='unidades_medida', verbose_name='Empresa')
    
    sigla = models.CharField(max_length=10, verbose_name='Sigla')
    nome = models.CharField(max_length=50, verbose_name='Nome')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, verbose_name='Tipo')
    ativo = models.BooleanField(default=True, verbose_name='Ativo')
    
    class Meta:
        verbose_name = 'Unidade de Medida'
        verbose_name_plural = 'Unidades de Medida'
        ordering = ['nome']
        unique_together = [['empresa', 'sigla']]
    
    def __str__(self):
        return f"{self.sigla} - {self.nome}"


class Categoria(models.Model):
    # Multi-tenant
    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='categorias_produto', verbose_name='Empresa')
    
    codigo = models.CharField(max_length=20, verbose_name='Código')
    nome = models.CharField(max_length=100, verbose_name='Nome')
    descricao = models.TextField(blank=True, verbose_name='Descrição')
    ativo = models.BooleanField(default=True, verbose_name='Ativo')
    condiciona_campos = models.BooleanField(default=False, verbose_name='Condiciona Campos')
    patrimonial = models.BooleanField(default=False, verbose_name='Categoria Patrimonial')
    
    class Meta:
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorias'
        ordering = ['nome']
        unique_together = [['empresa', 'codigo']]
    
    def __str__(self):
        return f"{self.codigo} - {self.nome}"


class SubCategoria(models.Model):
    # Multi-tenant (herdado da categoria)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name='subcategorias', verbose_name='Categoria')
    codigo = models.CharField(max_length=20, verbose_name='Código')
    nome = models.CharField(max_length=100, verbose_name='Nome')
    descricao = models.TextField(blank=True, verbose_name='Descrição')
    ativo = models.BooleanField(default=True, verbose_name='Ativo')
    
    class Meta:
        verbose_name = 'Subcategoria'
        verbose_name_plural = 'Subcategorias'
        ordering = ['categoria', 'nome']
        unique_together = [['categoria', 'codigo']]
    
    def __str__(self):
        return f"{self.categoria.codigo}.{self.codigo} - {self.nome}"


class NaturezaOperacao(models.Model):
    """
    Natureza da Operação - Descrições padronizadas para operações fiscais
    """
    # Multi-tenant
    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='naturezas_operacao', verbose_name='Empresa')
    
    codigo = models.CharField(max_length=20, verbose_name='Código')
    descricao = models.CharField(max_length=200, verbose_name='Descrição')
    tipo = models.CharField(max_length=10, choices=[
        ('ENTRADA', 'Entrada'),
        ('SAIDA', 'Saída'),
        ('AMBOS', 'Ambos'),
    ], default='AMBOS', verbose_name='Tipo')
    observacoes = models.TextField(blank=True, verbose_name='Observações')
    ativo = models.BooleanField(default=True, verbose_name='Ativo')
    
    # Auditoria
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')
    
    class Meta:
        verbose_name = 'Natureza da Operação'
        verbose_name_plural = 'Naturezas de Operação'
        ordering = ['codigo']
        unique_together = [['empresa', 'codigo']]
    
    def __str__(self):
        return f"{self.codigo} - {self.descricao}"


class Produto(models.Model):
    ORIGEM_MERCADORIA_CHOICES = [
        ('0', '0 - Nacional'),
        ('1', '1 - Estrangeira - Importação direta'),
        ('2', '2 - Estrangeira - Adquirida no mercado interno'),
        ('3', '3 - Nacional - Conteúdo superior 40% e inferior 70%'),
        ('4', '4 - Nacional - Processos produtivos básicos'),
        ('5', '5 - Nacional - Conteúdo inferior 40%'),
        ('6', '6 - Estrangeira - Importação direta sem similar'),
        ('7', '7 - Estrangeira - Mercado interno sem similar'),
        ('8', '8 - Nacional - Conteúdo superior 70%'),
    ]
    
    TIPO_ITEM_CHOICES = [
        ('00', '00 - Mercadoria para Revenda'),
        ('01', '01 - Matéria-Prima'),
        ('02', '02 - Embalagem'),
        ('03', '03 - Produto em Processo'),
        ('04', '04 - Produto Acabado'),
        ('05', '05 - Subproduto'),
        ('06', '06 - Produto Intermediário'),
        ('07', '07 - Material de Uso e Consumo'),
        ('08', '08 - Ativo Imobilizado'),
        ('09', '09 - Serviços'),
        ('10', '10 - Outros insumos'),
        ('99', '99 - Outras'),
    ]
    
    CATEGORIA_AGRICOLA_CHOICES = [
        ('DEFENSIVO', 'Defensivo Agrícola'),
        ('FERTILIZANTE', 'Fertilizante'),
        ('SEMENTE', 'Semente'),
        ('ADUBO', 'Adubo'),
        ('CORRETIVO', 'Corretivo de Solo'),
        ('INOCULANTE', 'Inoculante'),
        ('ADJUVANTE', 'Adjuvante'),
    ]
    
    CLASSE_AGRONOMICA_CHOICES = [
        ('HERBICIDA', 'Herbicida'),
        ('INSETICIDA', 'Inseticida'),
        ('FUNGICIDA', 'Fungicida'),
        ('ACARICIDA', 'Acaricida'),
        ('NEMATICIDA', 'Nematicida'),
        ('BACTERICIDA', 'Bactericida'),
        ('FORMICIDA', 'Formicida'),
        ('RODENTICIDA', 'Rodenticida'),
        ('DESSECANTE', 'Dessecante'),
        ('DESFOLHANTE', 'Desfolhante'),
    ]
    
    CLASSE_TOXICOLOGICA_CHOICES = [
        ('I', 'I - Extremamente Tóxico'),
        ('II', 'II - Altamente Tóxico'),
        ('III', 'III - Moderadamente Tóxico'),
        ('IV', 'IV - Pouco Tóxico'),
        ('V', 'V - Improvável de Causar Dano'),
    ]
    
    CLASSE_AMBIENTAL_CHOICES = [
        ('I', 'I - Produto Altamente Perigoso'),
        ('II', 'II - Produto Muito Perigoso'),
        ('III', 'III - Produto Perigoso'),
        ('IV', 'IV - Produto Pouco Perigoso'),
    ]
    
    TIPO_FERTILIZANTE_CHOICES = [
        ('SIMPLES', 'Fertilizante Simples'),
        ('COMPOSTO', 'Fertilizante Composto'),
        ('ORGANICO', 'Fertilizante Orgânico'),
        ('ORGANO_MINERAL', 'Fertilizante Organomineral'),
        ('FOLIAR', 'Fertilizante Foliar'),
        ('FLUIDO', 'Fertilizante Fluido'),
    ]
    
    MODO_APLICACAO_CHOICES = [
        ('FOLIAR', 'Aplicação Foliar'),
        ('SEMENTE', 'Tratamento de Sementes'),
        ('SULCO', 'Aplicação no Sulco'),
        ('COBERTURA', 'Aplicação em Cobertura'),
        ('FERTIRRIGACAO', 'Fertirrigação'),
    ]
    
    # Identificação
    codigo = models.CharField(max_length=50, unique=True, blank=True, verbose_name='Código')
    codigo_barras = models.CharField(max_length=50, blank=True, verbose_name='Código de Barras')
    nome = models.CharField(max_length=200, verbose_name='Nome')
    nome_resumido = models.CharField(max_length=100, blank=True, verbose_name='Nome Resumido')
    descricao = models.TextField(blank=True, verbose_name='Descrição')
    
    # Classificação
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, verbose_name='Categoria')
    subcategoria = models.ForeignKey(SubCategoria, on_delete=models.PROTECT, blank=True, null=True, verbose_name='Subcategoria')
    tipo_produto_antigo = models.CharField(max_length=20, blank=True, null=True, verbose_name='Tipo Antigo (migração)')
    tipo_produto = models.ForeignKey(TipoProduto, on_delete=models.PROTECT, blank=True, null=True, verbose_name='Tipo de Produto')
    
    # Unidades
    unidade_medida = models.ForeignKey(UnidadeMedida, on_delete=models.PROTECT, related_name='produtos', verbose_name='Unidade de Medida')
    unidade_compra = models.ForeignKey(UnidadeMedida, on_delete=models.PROTECT, related_name='produtos_compra', verbose_name='Unidade de Compra')
    unidade_venda = models.ForeignKey(UnidadeMedida, on_delete=models.PROTECT, related_name='produtos_venda', verbose_name='Unidade de Venda')
    fator_conversao = models.DecimalField(max_digits=10, decimal_places=4, default=1, verbose_name='Fator de Conversão')
    peso_liquido_unitario = models.DecimalField(
        'Peso Líq./Unidade (kg)', max_digits=10, decimal_places=3, default=0,
        help_text='Peso líquido por unidade/caixa em kg. Ex.: 10,000 para melão 10 kg')
    peso_bruto_unitario = models.DecimalField(
        'Peso Bruto/Unidade (kg)', max_digits=10, decimal_places=3, default=0,
        help_text='Peso bruto por unidade/caixa em kg (inclui embalagem). Ex.: 11,500')

    # Fiscal
    ncm = models.ForeignKey(NCM, on_delete=models.PROTECT, verbose_name='NCM')
    cest = models.CharField(max_length=7, blank=True, verbose_name='CEST')
    origem_mercadoria = models.CharField(max_length=1, choices=ORIGEM_MERCADORIA_CHOICES, default='0', verbose_name='Origem da Mercadoria')
    tipo_item = models.CharField(max_length=2, choices=TIPO_ITEM_CHOICES, default='00', verbose_name='Tipo do Item')
    
    # Financeiro
    preco_custo = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Preço de Custo')
    preco_venda = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Preço de Venda')
    margem_lucro = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='Margem de Lucro (%)')
    preco_minimo = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Preço Mínimo')
    
    # Estoque
    controla_estoque = models.BooleanField(default=True, verbose_name='Controla Estoque')
    estoque_minimo = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name='Estoque Mínimo')
    estoque_maximo = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name='Estoque Máximo')
    estoque_atual = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name='Estoque Atual')
    localizacao = models.CharField(max_length=50, blank=True, verbose_name='Localização')
    armazem_padrao = models.ForeignKey(
        'estoque.Armazem',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='produtos_padrao',
        verbose_name='Armazém Padrão',
        help_text='Armazém padrão para entrada de estoque deste produto'
    )
    
    # Rastreabilidade
    lote_obrigatorio = models.BooleanField(default=False, verbose_name='Lote Obrigatório')
    validade_obrigatoria = models.BooleanField(default=False, verbose_name='Validade Obrigatória')
    dias_validade = models.IntegerField(blank=True, null=True, verbose_name='Dias de Validade')
    
    # Informações Adicionais
    fornecedor_padrao = models.ForeignKey(Fornecedor, on_delete=models.SET_NULL, blank=True, null=True, verbose_name='Fornecedor Padrão')
    observacoes = models.TextField(blank=True, verbose_name='Observações')
    imagem = models.ImageField(upload_to='produtos/', blank=True, null=True, verbose_name='Imagem')
    ativo = models.BooleanField(default=True, verbose_name='Ativo')

    # Variantes
    produto_base = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='variantes',
        verbose_name='Produto Base',
        help_text='Se preenchido, este produto é uma variante do produto base selecionado.',
    )

    # Categoria Agrícola
    categoria_agricola = models.CharField(max_length=20, choices=CATEGORIA_AGRICOLA_CHOICES, blank=True, verbose_name='Categoria Agrícola')
    
    # Defensivos Agrícolas
    classe_agronomica = models.CharField(max_length=200, blank=True, verbose_name='Classe Agronômica')
    ingrediente_ativo = models.CharField(max_length=200, blank=True, verbose_name='Ingrediente Ativo')
    concentracao = models.CharField(max_length=50, blank=True, verbose_name='Concentração')
    registro_mapa = models.CharField(max_length=50, blank=True, verbose_name='Registro MAPA')
    possui_certificado = models.BooleanField(default=False, verbose_name='Possui Certificado')
    numero_certificado = models.CharField(max_length=100, blank=True, verbose_name='Número do Certificado')
    data_vencimento_certificado = models.DateField(blank=True, null=True, verbose_name='Vencimento do Certificado')
    arquivo_certificado = models.FileField(
        upload_to='produtos/certificados/%Y/%m/',
        blank=True,
        null=True,
        verbose_name='Arquivo do Certificado'
    )
    classe_toxicologica = models.CharField(max_length=3, choices=CLASSE_TOXICOLOGICA_CHOICES, blank=True, verbose_name='Classe Toxicológica')
    classe_ambiental = models.CharField(max_length=3, choices=CLASSE_AMBIENTAL_CHOICES, blank=True, verbose_name='Classe Ambiental')
    periodo_carencia = models.IntegerField(blank=True, null=True, verbose_name='Período de Carência (dias)')
    intervalo_reaplicacao = models.IntegerField(blank=True, null=True, verbose_name='Intervalo de Reaplicação (dias)')
    periodo_reentrada = models.IntegerField(blank=True, null=True, verbose_name='Período de Reentrada (horas)')
    paises_proibidos = models.TextField(blank=True, verbose_name='Países Proibidos', help_text='Lista de países que proíbem este ingrediente ativo (separados por vírgula)')
    
    # Fertilizantes
    tipo_fertilizante = models.CharField(max_length=20, choices=TIPO_FERTILIZANTE_CHOICES, blank=True, verbose_name='Tipo de Fertilizante')
    formula_npk = models.CharField(max_length=20, blank=True, verbose_name='Fórmula NPK')
    nitrogenio_n = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name='Nitrogênio (N) %')
    fosforo_p2o5 = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name='Fósforo (P2O5) %')
    potassio_k2o = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name='Potássio (K2O) %')
    enxofre_s = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name='Enxofre (S) %')
    calcio_ca = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name='Cálcio (Ca) %')
    magnesio_mg = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name='Magnésio (Mg) %')
    micronutrientes = models.TextField(blank=True, verbose_name='Micronutrientes')
    
    # Dosagem e Aplicação
    dosagem_minima = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True, verbose_name='Dosagem Mínima')
    dosagem_maxima = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True, verbose_name='Dosagem Máxima')
    unidade_dosagem = models.ForeignKey(UnidadeMedida, on_delete=models.PROTECT, related_name='produtos_dosagem', blank=True, null=True, verbose_name='Unidade de Dosagem')
    modo_aplicacao = models.CharField(max_length=20, choices=MODO_APLICACAO_CHOICES, blank=True, verbose_name='Modo de Aplicação')
    
    # Restrições e Segurança
    culturas_registradas = models.TextField(blank=True, verbose_name='Culturas Registradas')
    intervalo_seguranca = models.IntegerField(blank=True, null=True, verbose_name='Intervalo de Segurança (horas)')
    epi_obrigatorio = models.TextField(blank=True, verbose_name='EPI Obrigatório')
    incompatibilidades = models.TextField(blank=True, verbose_name='Incompatibilidades')
    
    # Armazenamento
    temperatura_armazenamento = models.CharField(max_length=50, blank=True, verbose_name='Temperatura de Armazenamento')
    inflamavel = models.BooleanField(default=False, verbose_name='Inflamável')
    corrosivo = models.BooleanField(default=False, verbose_name='Corrosivo')
    toxico = models.BooleanField(default=False, verbose_name='Tóxico')
    
    # Auditoria
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')
    
    class Meta:
        verbose_name = 'Produto'
        verbose_name_plural = 'Produtos'
        ordering = ['nome']

    CAMPOS_DEFENSIVO = [
        'classe_agronomica',
        'ingrediente_ativo',
        'concentracao',
        'registro_mapa',
        'classe_toxicologica',
        'classe_ambiental',
        'periodo_carencia',
        'intervalo_reaplicacao',
        'periodo_reentrada',
        'paises_proibidos',
    ]

    CAMPOS_FERTILIZANTE = [
        'tipo_fertilizante',
        'formula_npk',
        'nitrogenio_n',
        'fosforo_p2o5',
        'potassio_k2o',
        'enxofre_s',
        'calcio_ca',
        'magnesio_mg',
        'micronutrientes',
    ]

    CAMPOS_DOSAGEM_APLICACAO = [
        'dosagem_minima',
        'dosagem_maxima',
        'unidade_dosagem',
        'modo_aplicacao',
    ]

    CAMPOS_SEGURANCA_AGRICOLA = [
        'culturas_registradas',
        'intervalo_seguranca',
        'epi_obrigatorio',
        'incompatibilidades',
        'temperatura_armazenamento',
        'inflamavel',
        'corrosivo',
        'toxico',
    ]
    
    def __str__(self):
        return f"{self.codigo} - {self.nome}"

    @property
    def is_variante(self):
        return self.produto_base_id is not None

    @property
    def nome_completo(self):
        """Retorna nome concatenado com atributos ordenados, ex: 'Caixa 10 kg Goldmin Selecto 03'."""
        if not self.is_variante:
            return self.nome
        atributos = self.atributos.select_related('dimensao').order_by('dimensao__ordem', 'dimensao__nome')
        partes = [self.produto_base.nome] + [a.valor for a in atributos]
        return ' '.join(partes)

    def clean(self):
        super().clean()

        errors = {}

        if self.subcategoria and self.categoria_id and self.subcategoria.categoria_id != self.categoria_id:
            errors['subcategoria'] = 'A subcategoria selecionada não pertence à categoria informada.'

        self._validar_unidades(errors)
        self._validar_campos_agricolas(errors)
        self._validar_certificado(errors)

        if self.validade_obrigatoria and not self.dias_validade:
            errors['dias_validade'] = 'Informe os dias de validade quando a validade for obrigatória.'

        if self.dias_validade is not None and self.dias_validade < 0:
            errors['dias_validade'] = 'Os dias de validade não podem ser negativos.'

        if self.estoque_minimo and self.estoque_maximo and self.estoque_minimo > self.estoque_maximo:
            errors['estoque_maximo'] = 'O estoque máximo deve ser maior ou igual ao estoque mínimo.'

        if self.dosagem_minima is not None and self.dosagem_maxima is not None and self.dosagem_minima > self.dosagem_maxima:
            errors['dosagem_maxima'] = 'A dosagem máxima deve ser maior ou igual à dosagem mínima.'

        if errors:
            raise ValidationError(errors)

    def _validar_unidades(self, errors):
        unidades = [
            ('unidade_medida', self.unidade_medida),
            ('unidade_compra', self.unidade_compra),
            ('unidade_venda', self.unidade_venda),
        ]

        # Com fator_conversao > 1, unidade_medida é a unidade tributária (ex: KG para CX)
        # e pode ter tipo diferente. Valida apenas consistência entre compra e venda.
        fator = float(self.fator_conversao or 1)
        pares_validar = (
            [('unidade_compra', self.unidade_compra), ('unidade_venda', self.unidade_venda)]
            if fator > 1
            else unidades
        )

        tipos = {u.tipo for _, u in pares_validar if u}
        if len(tipos) > 1:
            mensagem = 'As unidades de compra e venda devem possuir o mesmo tipo.'
            for campo, unidade in pares_validar:
                if unidade:
                    errors[campo] = mensagem

        if self.fator_conversao is not None and self.fator_conversao <= 0:
            errors['fator_conversao'] = 'O fator de conversão deve ser maior que zero.'

    def _validar_certificado(self, errors):
        if self.possui_certificado:
            if not (self.numero_certificado or '').strip():
                errors['numero_certificado'] = 'Informe o número do certificado.'
            if not self.data_vencimento_certificado:
                errors['data_vencimento_certificado'] = 'Informe a data de vencimento do certificado.'

            if self.arquivo_certificado and hasattr(self.arquivo_certificado, 'name'):
                nome = self.arquivo_certificado.name.lower()
                ext_permitidas = ('.pdf', '.png', '.jpg', '.jpeg')
                if not nome.endswith(ext_permitidas):
                    errors['arquivo_certificado'] = 'Arquivo de certificado deve ser PDF ou imagem (PNG/JPG).'

                tamanho = getattr(self.arquivo_certificado, 'size', 0) or 0
                if tamanho > 10 * 1024 * 1024:
                    errors['arquivo_certificado'] = 'Arquivo de certificado deve ter no máximo 10MB.'
        else:
            self.numero_certificado = ''
            self.data_vencimento_certificado = None
            self.arquivo_certificado = None

    def _validar_campos_agricolas(self, errors):
        categoria_agricola = (self.categoria_agricola or '').strip()

        if not categoria_agricola:
            self._limpar_campos_nao_agricolas()
            return

        if categoria_agricola == 'DEFENSIVO':
            if not self.classe_agronomica:
                errors['classe_agronomica'] = 'Classe agronômica é obrigatória para defensivos.'
            if not (self.ingrediente_ativo or '').strip():
                errors['ingrediente_ativo'] = 'Ingrediente ativo é obrigatório para defensivos.'
            if not (self.registro_mapa or '').strip():
                errors['registro_mapa'] = 'Registro MAPA é obrigatório para defensivos.'
            self._limpar_campos_fertilizante()
            return

        if categoria_agricola == 'FERTILIZANTE':
            possui_npk = any(
                valor is not None and valor > 0
                for valor in [self.nitrogenio_n, self.fosforo_p2o5, self.potassio_k2o]
            )
            if not self.tipo_fertilizante:
                errors['tipo_fertilizante'] = 'Tipo de fertilizante é obrigatório para fertilizantes.'
            if not (self.formula_npk or '').strip() and not possui_npk:
                errors['formula_npk'] = 'Informe a fórmula NPK ou ao menos um teor principal de N, P2O5 ou K2O.'
            self._limpar_campos_defensivo()
            return

        self._limpar_campos_defensivo()
        self._limpar_campos_fertilizante()

    def _limpar_campos_nao_agricolas(self):
        self._limpar_campos_defensivo()
        self._limpar_campos_fertilizante()
        for campo in self.CAMPOS_DOSAGEM_APLICACAO + self.CAMPOS_SEGURANCA_AGRICOLA:
            self._limpar_campo(campo)

    def _limpar_campos_defensivo(self):
        for campo in self.CAMPOS_DEFENSIVO:
            self._limpar_campo(campo)

    def _limpar_campos_fertilizante(self):
        for campo in self.CAMPOS_FERTILIZANTE:
            self._limpar_campo(campo)

    def _limpar_campo(self, campo):
        field = self._meta.get_field(campo)
        if isinstance(field, models.BooleanField):
            setattr(self, campo, False)
        elif getattr(field, 'null', False):
            setattr(self, campo, None)
        else:
            setattr(self, campo, '')
    
    def get_paises_proibidos_list(self):
        """Retorna lista de países proibidos"""
        if self.paises_proibidos:
            return [p.strip() for p in self.paises_proibidos.split(',') if p.strip()]
        return []

    def get_classes_agronomicas_list(self):
        """Retorna lista de códigos das classes agronômicas selecionadas."""
        if not self.classe_agronomica:
            return []
        return [v.strip() for v in self.classe_agronomica.split(',') if v.strip()]

    def get_classes_agronomicas_display(self):
        """Retorna lista de labels das classes agronômicas para exibição."""
        choices_map = dict(self.CLASSE_AGRONOMICA_CHOICES)
        return [choices_map.get(code, code) for code in self.get_classes_agronomicas_list()]
    
    def save(self, *args, **kwargs):
        # Normalizar nome: Title Case e remover espaços extras
        if self.nome:
            self.nome = self.nome.strip().title()

        self.full_clean()
        
        # Gerar código automático se não foi fornecido
        if not self.codigo:
            self.codigo = self._gerar_codigo()
        super().save(*args, **kwargs)
    
    def _gerar_codigo(self):
        """Gera código automático no formato: CATEGORIA-000001"""
        if self.categoria:
            prefixo = self.categoria.codigo
            # Buscar todos os produtos da categoria com padrão PREFIXO-NUMERO
            produtos = Produto.objects.filter(
                codigo__startswith=f"{prefixo}-",
                codigo__regex=r'^' + prefixo + r'-\d+$'  # Apenas formato PREFIXO-123456
            ).order_by('codigo')
            
            if produtos.exists():
                # Extrair todos os números e pegar o maior
                numeros = []
                for p in produtos:
                    try:
                        numero = int(p.codigo.split('-')[-1])
                        numeros.append(numero)
                    except (ValueError, IndexError):
                        continue
                
                if numeros:
                    novo_numero = max(numeros) + 1
                else:
                    novo_numero = 1
            else:
                novo_numero = 1
            
            return f"{prefixo}-{novo_numero:06d}"
        else:
            # Se não tiver categoria, usar sequencial simples
            ultimo = Produto.objects.order_by('id').last()
            numero = ultimo.id + 1 if ultimo else 1
            return f"PROD-{numero:06d}"
    
    def get_tributacao(self, cfop):
        """Retorna a tributação específica para um CFOP"""
        try:
            return self.tributacoes.get(cfop=cfop)
        except ProdutoTributacao.DoesNotExist:
            return None


class ProdutoFornecedor(models.Model):
    """
    Relacionamento M2M entre Produto e Fornecedor com informações adicionais
    Permite registrar código específico do fornecedor e condições comerciais
    """
    # Relacionamentos
    produto = models.ForeignKey(
        Produto, 
        on_delete=models.CASCADE, 
        related_name='fornecedores_relacionados',
        verbose_name='Produto'
    )
    fornecedor = models.ForeignKey(
        Fornecedor, 
        on_delete=models.CASCADE, 
        related_name='produtos_relacionados',
        verbose_name='Fornecedor'
    )
    
    # Identificação do produto no fornecedor
    codigo_fornecedor = models.CharField(
        max_length=100,
        verbose_name='Código no Fornecedor',
        help_text='Código que aparece na nota fiscal do fornecedor'
    )
    
    # Informações comerciais
    preco_compra = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=0,
        verbose_name='Preço de Compra'
    )
    prazo_entrega = models.IntegerField(
        blank=True, 
        null=True,
        verbose_name='Prazo de Entrega (dias)'
    )
    quantidade_minima = models.DecimalField(
        max_digits=15, 
        decimal_places=3, 
        default=0,
        verbose_name='Quantidade Mínima',
        help_text='Quantidade mínima de compra'
    )
    
    # Preferências
    fornecedor_preferencial = models.BooleanField(
        default=False,
        verbose_name='Fornecedor Preferencial',
        help_text='Marque se este é o fornecedor preferencial para este produto'
    )
    
    # Observações
    observacoes = models.TextField(
        blank=True,
        verbose_name='Observações'
    )
    
    # Status
    ativo = models.BooleanField(
        default=True,
        verbose_name='Ativo'
    )
    
    # Auditoria
    cadastrado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='produtos_fornecedores_cadastrados',
        verbose_name='Cadastrado por'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')
    
    class Meta:
        verbose_name = 'Produto-Fornecedor'
        verbose_name_plural = 'Produtos-Fornecedores'
        ordering = ['-fornecedor_preferencial', 'fornecedor__nome']
        unique_together = ['produto', 'fornecedor']
    
    def __str__(self):
        preferencial = " ⭐" if self.fornecedor_preferencial else ""
        return f"{self.produto.codigo} - {self.fornecedor.nome}{preferencial}"


class ProdutoTributacao(models.Model):
    """
    Tabela intermediária que relaciona Produto + CFOP com suas tributações específicas.
    """
    
    CST_ICMS_CHOICES = [
        ('00', '00 - Tributada integralmente'),
        ('10', '10 - Tributada com cobrança do ICMS por ST'),
        ('20', '20 - Com redução de base de cálculo'),
        ('30', '30 - Isenta ou não tributada com cobrança do ICMS por ST'),
        ('40', '40 - Isenta'),
        ('41', '41 - Não tributada'),
        ('50', '50 - Suspensão'),
        ('51', '51 - Diferimento'),
        ('60', '60 - ICMS cobrado anteriormente por ST'),
        ('70', '70 - Com redução de base de cálculo e cobrança do ICMS por ST'),
        ('90', '90 - Outras'),
    ]
    
    CST_IPI_CHOICES = [
        ('00', '00 - Entrada com Recuperação de Crédito'),
        ('01', '01 - Entrada Tributada com Alíquota Zero'),
        ('02', '02 - Entrada Isenta'),
        ('03', '03 - Entrada Não-Tributada'),
        ('04', '04 - Entrada Imune'),
        ('05', '05 - Entrada com Suspensão'),
        ('49', '49 - Outras Entradas'),
        ('50', '50 - Saída Tributada'),
        ('51', '51 - Saída Tributada com Alíquota Zero'),
        ('52', '52 - Saída Isenta'),
        ('53', '53 - Saída Não-Tributada'),
        ('54', '54 - Saída Imune'),
        ('55', '55 - Saída com Suspensão'),
        ('99', '99 - Outras Saídas'),
    ]
    
    CST_PIS_COFINS_CHOICES = [
        ('01', '01 - Operação Tributável com Alíquota Básica'),
        ('02', '02 - Operação Tributável com Alíquota Diferenciada'),
        ('03', '03 - Operação Tributável com Alíquota por Unidade'),
        ('04', '04 - Operação Tributável Monofásica'),
        ('05', '05 - Operação Tributável por Substituição Tributária'),
        ('06', '06 - Operação Tributável a Alíquota Zero'),
        ('07', '07 - Operação Isenta da Contribuição'),
        ('08', '08 - Operação sem Incidência da Contribuição'),
        ('09', '09 - Operação com Suspensão da Contribuição'),
        ('49', '49 - Outras Operações de Saída'),
        ('99', '99 - Outras Operações'),
    ]
    
    MODALIDADE_BASE_ICMS_CHOICES = [
        ('0', '0 - Margem Valor Agregado (%)'),
        ('1', '1 - Pauta (Valor)'),
        ('2', '2 - Preço Tabelado Máx. (valor)'),
        ('3', '3 - Valor da operação'),
    ]
    
    ORIGEM_MERCADORIA_CHOICES = [
        ('0', '0 - Nacional'),
        ('1', '1 - Estrangeira - Importação direta'),
        ('2', '2 - Estrangeira - Adquirida no mercado interno'),
        ('3', '3 - Nacional - Conteúdo superior 40% e inferior 70%'),
        ('4', '4 - Nacional - Processos produtivos básicos'),
        ('5', '5 - Nacional - Conteúdo inferior 40%'),
        ('6', '6 - Estrangeira - Importação direta sem similar'),
        ('7', '7 - Estrangeira - Mercado interno sem similar'),
        ('8', '8 - Nacional - Conteúdo superior 70%'),
    ]
    
    # Relacionamentos
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name='tributacoes', verbose_name='Produto')
    cfop = models.ForeignKey(CFOP, on_delete=models.PROTECT, verbose_name='CFOP')
    
    # Natureza da Operação
    natureza_operacao = models.ForeignKey(NaturezaOperacao, on_delete=models.PROTECT, null=True, blank=True, verbose_name='Natureza da Operação')
    descricao = models.CharField(max_length=200, blank=True, verbose_name='Descrição', help_text='Preenchido automaticamente pela Natureza da Operação')
    
    # Origem da Mercadoria (obrigatório para NF-e)
    origem_mercadoria = models.CharField(max_length=1, choices=ORIGEM_MERCADORIA_CHOICES, default='0', verbose_name='Origem da Mercadoria')
    
    # Tributação ICMS
    icms_situacao_tributaria = models.CharField(max_length=3, choices=CST_ICMS_CHOICES, verbose_name='CST ICMS')
    icms_modalidade_base = models.CharField(max_length=1, choices=MODALIDADE_BASE_ICMS_CHOICES, default='3', verbose_name='Modalidade Base ICMS')
    icms_aliquota = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='Alíquota ICMS (%)')
    icms_reducao_base = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='Redução Base ICMS (%)')
    icms_base_calculo = models.DecimalField(max_digits=5, decimal_places=2, default=100, verbose_name='Base de Cálculo ICMS (%)')
    
    # ICMS ST
    icms_st_aliquota = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='Alíquota ICMS ST (%)')
    icms_st_mva = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='MVA ST (%)')
    icms_st_reducao_base = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='Redução Base ICMS ST (%)')
    
    # Tributação IPI
    ipi_situacao_tributaria = models.CharField(max_length=2, choices=CST_IPI_CHOICES, blank=True, verbose_name='CST IPI')
    ipi_aliquota = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='Alíquota IPI (%)')
    ipi_codigo_enquadramento = models.CharField(max_length=3, default='999', verbose_name='Código de Enquadramento IPI')
    
    # Tributação PIS
    pis_situacao_tributaria = models.CharField(max_length=2, choices=CST_PIS_COFINS_CHOICES, verbose_name='CST PIS')
    pis_aliquota = models.DecimalField(max_digits=9, decimal_places=6, default=0, verbose_name='Alíquota PIS (%)')
    pis_base_calculo = models.DecimalField(max_digits=5, decimal_places=2, default=100, verbose_name='Base de Cálculo PIS (%)')
    natureza_receita_pis = models.CharField(
        max_length=3, blank=True, verbose_name='Natureza da Receita PIS',
        help_text='Código 3 dígitos — obrigatório para CST 04-09, 49, 99 (ex: 116).',
    )

    # Tributação COFINS
    cofins_situacao_tributaria = models.CharField(max_length=2, choices=CST_PIS_COFINS_CHOICES, verbose_name='CST COFINS')
    cofins_aliquota = models.DecimalField(max_digits=9, decimal_places=6, default=0, verbose_name='Alíquota COFINS (%)')
    cofins_base_calculo = models.DecimalField(max_digits=5, decimal_places=2, default=100, verbose_name='Base de Cálculo COFINS (%)')
    natureza_receita_cofins = models.CharField(
        max_length=3, blank=True, verbose_name='Natureza da Receita COFINS',
        help_text='Código 3 dígitos — obrigatório para CST 04-09, 49, 99 (ex: 116).',
    )
    
    # Benefícios Fiscais
    beneficio_fiscal = models.CharField(max_length=10, blank=True, verbose_name='Código Benefício Fiscal')
    
    # Controle
    padrao = models.BooleanField(default=False, verbose_name='Tributação Padrão')
    ativo = models.BooleanField(default=True, verbose_name='Ativo')
    observacoes = models.TextField(blank=True, verbose_name='Observações')
    
    # Auditoria
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')
    
    class Meta:
        verbose_name = 'Tributação do Produto'
        verbose_name_plural = 'Tributações dos Produtos'
        ordering = ['produto', 'cfop']
        unique_together = [['produto', 'cfop']]
    
    def __str__(self):
        return f"{self.produto.codigo} - {self.cfop.codigo}"
    
    def save(self, *args, **kwargs):
        # Copiar descrição da natureza da operação se selecionada
        if self.natureza_operacao and not self.descricao:
            self.descricao = self.natureza_operacao.descricao
        super().save(*args, **kwargs)
    
    def calcular_icms(self, valor_produto):
        """Calcula o valor do ICMS"""
        base = valor_produto * (self.icms_base_calculo / 100)
        if self.icms_reducao_base > 0:
            base = base * (1 - self.icms_reducao_base / 100)
        return base * (self.icms_aliquota / 100)
    
    def calcular_icms_st(self, valor_produto):
        """Calcula o valor do ICMS ST"""
        if self.icms_st_aliquota == 0:
            return 0
        base_st = valor_produto * (1 + self.icms_st_mva / 100)
        if self.icms_st_reducao_base > 0:
            base_st = base_st * (1 - self.icms_st_reducao_base / 100)
        icms_st = (base_st * self.icms_st_aliquota / 100) - self.calcular_icms(valor_produto)
        return max(icms_st, 0)
    
    def calcular_ipi(self, valor_produto):
        """Calcula o valor do IPI"""
        return valor_produto * (self.ipi_aliquota / 100)
    
    def calcular_pis(self, valor_produto):
        """Calcula o valor do PIS"""
        base = valor_produto * (self.pis_base_calculo / 100)
        return base * (self.pis_aliquota / 100)
    
    def calcular_cofins(self, valor_produto):
        """Calcula o valor do COFINS"""
        base = valor_produto * (self.cofins_base_calculo / 100)
        return base * (self.cofins_aliquota / 100)
    
    def calcular_tributos(self, valor_produto):
        """Retorna um dicionário com todos os tributos calculados"""
        return {
            'icms': self.calcular_icms(valor_produto),
            'icms_st': self.calcular_icms_st(valor_produto),
            'ipi': self.calcular_ipi(valor_produto),
            'pis': self.calcular_pis(valor_produto),
            'cofins': self.calcular_cofins(valor_produto),
            'total': (
                self.calcular_icms(valor_produto) +
                self.calcular_icms_st(valor_produto) +
                self.calcular_ipi(valor_produto) +
                self.calcular_pis(valor_produto) +
                self.calcular_cofins(valor_produto)
            )
        }

class ProdutoDefensivoCultura(models.Model):
    """
    Registro de cultura e praga combatida por defensivo agrícola
    Um defensivo pode ter múltiplos registros (uma linha por cultura/praga)
    """
    # Relacionamento
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name='defensivo_culturas', verbose_name='Produto')
    
    # Cultura e Praga
    cultura = models.ForeignKey('cadastros.Cultura', on_delete=models.PROTECT, verbose_name='Cultura')
    praga = models.ForeignKey('cadastros.Praga', on_delete=models.PROTECT, verbose_name='Praga/Doença')
    
    # Dosagem
    dosagem_minima = models.DecimalField(max_digits=10, decimal_places=3, verbose_name='Dosagem Mínima')
    dosagem_maxima = models.DecimalField(max_digits=10, decimal_places=3, verbose_name='Dosagem Máxima')
    unidade_dosagem = models.ForeignKey(UnidadeMedida, on_delete=models.PROTECT, related_name='defensivo_dosagens', verbose_name='Unidade de Dosagem')
    
    # Dosagem Convertida (Cálculo)
    dosagem_minima_calc = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name='Dosagem Mínima (Cálculo)', help_text='Dosagem convertida')
    dosagem_maxima_calc = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name='Dosagem Máxima (Cálculo)', help_text='Dosagem convertida')
    unidade_dosagem_calc = models.ForeignKey(UnidadeMedida, on_delete=models.PROTECT, related_name='defensivo_dosagens_calc', verbose_name='Unidade de Dosagem (Cálculo)', null=True, blank=True)
    
    # Cálculo Reverso (Volume → Dosagem)
    volume_calda_aplicacao = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='Volume de Calda para Aplicação (L)', help_text='Volume de calda que será aplicado')
    dosagem_calculada_ha = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name='Dosagem Calculada (ml/ha)', help_text='Dosagem calculada baseada no volume de calda')
    
    # Aplicação
    carencia = models.IntegerField(verbose_name='Carência (dias)', help_text='Período entre última aplicação e colheita')
    quantidade_maxima_aplicacoes = models.IntegerField(verbose_name='Quantidade Máxima de Aplicações')
    intervalo_reaplicacao = models.IntegerField(verbose_name='Intervalo para Reaplicação (dias)')
    
    # Limite Máximo de Resíduo
    mrl = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name='MRL', help_text='Limite Máximo de Resíduo (mg/kg)')
    
    # Volume de Calda
    volume_calda_minimo = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Volume Mínimo de Calda (L/ha)')
    volume_calda_maximo = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Volume Máximo de Calda (L/ha)')
    
    # Observações específicas
    observacoes = models.TextField(blank=True, verbose_name='Observações')
    
    # Auditoria
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')
    
    class Meta:
        verbose_name = 'Defensivo - Cultura/Praga'
        verbose_name_plural = 'Defensivos - Culturas/Pragas'
        ordering = ['produto', 'cultura', 'praga']
        unique_together = [['produto', 'cultura', 'praga']]
    
    def __str__(self):
        return f"{self.produto.nome} - {self.cultura.nome} - {self.praga.nome_comum}"


class ProdutoDocumento(models.Model):
    """
    Documentos anexados a produtos (bulas, certificados, FISPQ, etc.)
    """
    TIPO_CHOICES = [
        ('BULA', 'Bula'),
        ('CERTIFICADO', 'Certificado'),
        ('FISPQ', 'FISPQ (Ficha de Informação de Segurança)'),
        ('FICHA_TECNICA', 'Ficha Técnica'),
        ('ANALISE', 'Análise'),
        ('LAUDO', 'Laudo'),
        ('REGISTRO', 'Registro (MAPA/Anvisa)'),
        ('ROTULO', 'Rótulo'),
        ('MANUAL', 'Manual de Uso'),
        ('OUTROS', 'Outros'),
    ]
    
    # Relacionamento
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name='documentos', verbose_name='Produto')
    
    # Informações do documento
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, verbose_name='Tipo de Documento')
    nome = models.CharField(max_length=200, verbose_name='Nome/Descrição')
    arquivo = models.FileField(upload_to='produtos/documentos/%Y/%m/', verbose_name='Arquivo')
    
    # Observações
    observacoes = models.TextField(blank=True, verbose_name='Observações')
    
    # Auditoria
    cadastrado_por = models.ForeignKey('usuarios.Usuario', on_delete=models.SET_NULL, null=True, related_name='documentos_cadastrados', verbose_name='Cadastrado por')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')
    
    class Meta:
        verbose_name = 'Documento do Produto'
        verbose_name_plural = 'Documentos dos Produtos'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.produto.nome} - {self.get_tipo_display()}"
    
    def extensao_arquivo(self):
        """Retorna a extensão do arquivo"""
        import os
        return os.path.splitext(self.arquivo.name)[1].lower()
    
    def tamanho_formatado(self):
        """Retorna o tamanho do arquivo formatado"""
        size = self.arquivo.size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"


class DimensaoVariante(models.Model):
    """Eixo de variação configurável por empresa (ex: Calibre, Marca, Variedade)."""
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='dimensoes_variante',
        verbose_name='Empresa',
    )
    nome  = models.CharField(max_length=100, verbose_name='Nome')
    ordem = models.PositiveSmallIntegerField(default=0, verbose_name='Ordem')
    ativo = models.BooleanField(default=True, verbose_name='Ativo')

    class Meta:
        verbose_name = 'Dimensão de Variante'
        verbose_name_plural = 'Dimensões de Variantes'
        ordering = ['ordem', 'nome']
        unique_together = [['empresa', 'nome']]

    def __str__(self):
        return self.nome


class ProdutoAtributo(models.Model):
    """Par dimensão→valor associado a um produto específico."""
    produto  = models.ForeignKey(
        Produto,
        on_delete=models.CASCADE,
        related_name='atributos',
        verbose_name='Produto',
    )
    dimensao = models.ForeignKey(
        DimensaoVariante,
        on_delete=models.PROTECT,
        related_name='atributos',
        verbose_name='Dimensão',
    )
    valor = models.CharField(max_length=200, verbose_name='Valor')

    class Meta:
        verbose_name = 'Atributo do Produto'
        verbose_name_plural = 'Atributos do Produto'
        ordering = ['dimensao__ordem', 'dimensao__nome']
        unique_together = [['produto', 'dimensao']]

    def __str__(self):
        return f'{self.dimensao.nome}: {self.valor}'
