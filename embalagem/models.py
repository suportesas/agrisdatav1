from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from django.conf import settings
from django.db import models, transaction
from django.db.models import Count, Sum, Q
from django.utils import timezone


class CargaFreteError(Exception):
    """Erro de validação ao ratear uma CargaFrete."""


# ──────────────────────────── TipoEmbalagem ────────────────────────────────

class TipoEmbalagem(models.Model):
    """
    Configuração de embalagem padrão: define caixa e pallet para um produto/cultura.
    """
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='tipos_embalagem',
        verbose_name='Empresa',
    )
    produto = models.ForeignKey(
        'produtos.Produto',
        on_delete=models.PROTECT,
        related_name='tipos_embalagem',
        verbose_name='Produto',
        blank=True,
        null=True,
    )
    cultura = models.ForeignKey(
        'cadastros.Cultura',
        on_delete=models.PROTECT,
        related_name='tipos_embalagem',
        verbose_name='Cultura',
        blank=True,
        null=True,
    )
    subcategoria = models.ForeignKey(
        'produtos.SubCategoria',
        on_delete=models.PROTECT,
        related_name='tipos_embalagem',
        verbose_name='Subcategoria',
        blank=True,
        null=True,
        help_text='Aplica este tipo de embalagem a todos os produtos desta subcategoria.',
    )
    nome = models.CharField('Nome da Embalagem', max_length=100,
                            help_text='Ex: Caixa 5kg Manga Tommy')
    variedade = models.CharField('Variedade', max_length=100, blank=True)
    marca = models.CharField('Marca', max_length=100, blank=True)
    tipo_calibre = models.CharField('Tipo / Calibre', max_length=20, blank=True,
                                    help_text='Ex: 2, 3, 14')
    peso_liquido_cx = models.DecimalField(
        'Peso Líquido por Caixa (kg)', max_digits=10, decimal_places=3)
    peso_bruto_cx = models.DecimalField(
        'Peso Bruto por Caixa (kg)', max_digits=10, decimal_places=3,
        help_text='Inclui tara da embalagem')
    caixas_por_pallet = models.PositiveIntegerField('Caixas por Pallet')
    peso_pallet_vazio = models.DecimalField(
        'Tara do Pallet (kg)', max_digits=10, decimal_places=3, default=0)
    trace_code = models.CharField(
        'Trace Code (Rastreamento)',
        max_length=50,
        blank=True,
        help_text='Código de rastreamento específico da empresa. Ex: GLO-MEL-05',
    )
    classe_categoria = models.CharField(
        'Classe / Categoria (Class/Cat.)',
        max_length=10,
        blank=True,
        default='I',
        help_text='Classificação comercial impressa nas etiquetas. Ex: I, II, Extra',
    )
    codigo_chave_extra = models.CharField(
        'Código "Key" (Etiqueta de Caixa)',
        max_length=30,
        blank=True,
        help_text='Código adicional livre impresso na linha "Key" da etiqueta de caixa, se aplicável.',
    )
    ativo = models.BooleanField('Ativo', default=True)

    class Meta:
        verbose_name = 'Tipo de Embalagem'
        verbose_name_plural = 'Tipos de Embalagem'
        ordering = ['nome']

    def __str__(self):
        return self.nome

    @property
    def descricao_completa(self):
        """Concatena os atributos do tipo em uma descrição legível.
        Ex: Cx de Melão Amarelo Goldex Selecto Tp 05
        """
        partes = ['Cx de']
        if self.cultura:
            partes.append(self.cultura.nome)
            if self.cultura.variedade:
                partes.append(self.cultura.variedade)
        elif self.produto:
            partes.append(self.produto.nome)
        elif self.subcategoria:
            partes.append(self.subcategoria.nome)
        if self.variedade:
            partes.append(self.variedade)
        if self.marca:
            partes.append(self.marca)
        if self.nome and self.nome not in partes:
            # usa nome apenas se não for redundante com o que já foi montado
            pass
        if self.tipo_calibre:
            partes.append(f'Tp {self.tipo_calibre}')
        return ' '.join(partes) if len(partes) > 1 else self.nome

    @property
    def label_completo(self):
        """Rótulo para diferenciar tipos parecidos em selects/checkboxes.
        Ex: Melão Amarelo Goldex, pt. 05 - Terra Brasilis 13,000kg/cx
        """
        label = self.nome
        if self.variedade:
            label += f' {self.variedade}'
        if self.tipo_calibre:
            label += f', pt. {self.tipo_calibre}'
        if self.marca:
            label += f' - {self.marca}'
        peso = f'{self.peso_liquido_cx:.3f}'.replace('.', ',')
        label += f' {peso}kg/cx'
        return label

    @property
    def peso_liquido_pallet(self):
        return self.peso_liquido_cx * self.caixas_por_pallet

    @property
    def peso_bruto_pallet(self):
        return (self.peso_bruto_cx * self.caixas_por_pallet) + self.peso_pallet_vazio


class TipoEmbalagemCliente(models.Model):
    """Código IAN (Article Number) atribuído por um cliente a um Tipo de Embalagem —
    cada retailer tem seu próprio catálogo de artigos, por isso não é um campo
    direto em TipoEmbalagem."""
    empresa = models.ForeignKey(
        'empresas.Empresa', on_delete=models.CASCADE,
        related_name='ians_tipo_embalagem', verbose_name='Empresa',
    )
    tipo_embalagem = models.ForeignKey(
        TipoEmbalagem, on_delete=models.CASCADE,
        related_name='codigos_ian_cliente', verbose_name='Tipo de Embalagem',
    )
    cliente = models.ForeignKey(
        'cadastros.Cliente', on_delete=models.PROTECT,
        related_name='ians_tipo_embalagem', verbose_name='Cliente',
    )
    codigo_ian = models.CharField(
        'Código IAN', max_length=20,
        help_text='Código do artigo (IAN) atribuído por este cliente, impresso na etiqueta de caixa. Ex: 80575',
    )
    ativo = models.BooleanField('Ativo', default=True)
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)

    class Meta:
        verbose_name = 'Código IAN por Cliente'
        verbose_name_plural = 'Códigos IAN por Cliente'
        unique_together = [('tipo_embalagem', 'cliente')]
        ordering = ['tipo_embalagem__nome', 'cliente__razao_social']

    def __str__(self):
        return f'{self.tipo_embalagem} — {self.cliente}: {self.codigo_ian}'


# ──────────────────────────── OrdemEmbalagem ───────────────────────────────

class OrdemEmbalagem(models.Model):
    STATUS = [
        ('ABERTA', 'Aberta'),
        ('EM_ANDAMENTO', 'Em Andamento'),
        ('CONCLUIDA', 'Concluída'),
        ('CANCELADA', 'Cancelada'),
    ]

    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='ordens_embalagem',
        verbose_name='Empresa',
    )
    numero = models.CharField('Número', max_length=20, unique=True, blank=True)
    data = models.DateField('Data', default=timezone.now)
    tipos_embalagem = models.ManyToManyField(
        TipoEmbalagem,
        related_name='ordens_permitidas',
        verbose_name='Tipos de Embalagem Permitidos',
        help_text='Tipos de embalagem que podem ser gerados a partir desta ordem.',
    )
    lote_origem = models.ForeignKey(
        'estoque.Lote',
        on_delete=models.PROTECT,
        related_name='ordens_embalagem',
        verbose_name='Lote de Origem (Produto a Granel)',
    )
    quantidade_entrada_kg = models.DecimalField(
        'Qtd Entrada (kg)', max_digits=14, decimal_places=3,
        help_text='Kg de produto bruto que entrou no packing')
    armazem_destino = models.ForeignKey(
        'estoque.Armazem',
        on_delete=models.PROTECT,
        related_name='ordens_embalagem_destino',
        verbose_name='Armazém de Destino',
    )
    local_destino = models.ForeignKey(
        'estoque.LocalEstocagem',
        on_delete=models.SET_NULL,
        related_name='ordens_embalagem',
        verbose_name='Local de Estocagem',
        blank=True,
        null=True,
    )
    safra = models.ForeignKey(
        'cadastros.Safra',
        on_delete=models.PROTECT,
        related_name='ordens_embalagem',
        verbose_name='Safra',
        null=True,
        blank=True,
        help_text='Safra de origem — define o prefixo do código de barras dos pallets',
    )
    lote_producao = models.ForeignKey(
        'operacoes_campo.LoteProducao',
        on_delete=models.SET_NULL,
        related_name='ordens_embalagem',
        verbose_name='Lote de Produção',
        null=True,
        blank=True,
        help_text='Lote de produção de campo que deu origem a esta ordem (RF-110)',
    )
    capacidade_caixas_pallet = models.PositiveIntegerField(
        'Capacidade do Pallet (caixas)',
        null=True,
        blank=True,
        help_text='Quantidade esperada de caixas por pallet. Usada para validar pallets mistos.',
    )
    status = models.CharField('Status', max_length=20, choices=STATUS, default='ABERTA')
    responsavel = models.ForeignKey(
        'rh.Funcionario',
        on_delete=models.SET_NULL,
        related_name='ordens_embalagem_responsavel',
        verbose_name='Responsável',
        blank=True,
        null=True,
    )
    observacoes = models.TextField('Observações', blank=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='ordens_embalagem_criadas',
        verbose_name='Criado por',
        blank=True,
        null=True,
    )
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)

    class Meta:
        verbose_name = 'Ordem de Embalagem'
        verbose_name_plural = 'Ordens de Embalagem'
        ordering = ['-criado_em']
        indexes = [
            models.Index(fields=['empresa', 'status']),
            models.Index(fields=['empresa', 'data']),
        ]

    def __str__(self):
        return self.numero or f'OE-{self.pk}'

    @classmethod
    def _gerar_numero(cls, empresa):
        ano = timezone.now().year
        # select_for_update evita race condition em criações simultâneas
        ultimo = (cls.objects
                  .select_for_update()
                  .filter(empresa=empresa, numero__startswith=f'OE-{ano}-')
                  .order_by('numero')
                  .last())
        if ultimo and ultimo.numero:
            try:
                seq = int(ultimo.numero.split('-')[-1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        return f'OE-{ano}-{seq:04d}'

    @property
    def n_pallets(self):
        return self.pallets.count()

    def pallets_possiveis(self, tipo_embalagem):
        """Quantos pallets desse tipo cabem no saldo atual do lote de origem."""
        lp = tipo_embalagem.peso_liquido_pallet
        if not lp:
            return 0
        return int(self.lote_origem.quantidade_atual / lp)

    def lote_producao_efetivo(self):
        """Lote de produção (colheita) desta ordem — direto na campo `lote_producao`
        da própria ordem (legado, setado só pela recepção automática do packing) ou,
        preferencialmente, através do vínculo cadastrado no Lote de origem
        (`estoque.Lote.lote_producao`), que é a fonte de verdade quando o lote de
        estoque é reaproveitado em mais de uma ordem de embalagem."""
        if self.lote_origem_id and self.lote_origem.lote_producao_id:
            return self.lote_origem.lote_producao
        return self.lote_producao


# ──────────────────────────── MaterialEmbalagem ────────────────────────────

class MaterialEmbalagem(models.Model):
    """Classifica um produtos.Produto (categoria de Embalagens do catálogo da empresa)
    como material de transporte (TP) ou de venda (SP) para compor a rastreabilidade
    PPWR do romaneio. Nome e fornecedor vêm do próprio Produto — não duplicados aqui."""

    TIPO = [
        ('TRANSPORTE', 'Transport Package (TP)'),
        ('VENDA', 'Sales Package (SP)'),
    ]

    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='materiais_embalagem',
        verbose_name='Empresa',
    )
    produto = models.ForeignKey(
        'produtos.Produto',
        on_delete=models.PROTECT,
        related_name='materiais_embalagem',
        verbose_name='Produto',
    )
    tipo = models.CharField('Tipo', max_length=20, choices=TIPO, default='TRANSPORTE')
    codigo_reciclagem = models.CharField(
        'Código de Reciclagem',
        max_length=10,
        blank=True,
        help_text='Ex: 20 PAP (papelão ondulado) — impresso na etiqueta de caixa junto ao aviso PPWR.'
    )
    ativo = models.BooleanField('Ativo', default=True)
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)

    class Meta:
        verbose_name = 'Material de Embalagem'
        verbose_name_plural = 'Materiais de Embalagem'
        ordering = ['tipo', 'produto__nome']
        unique_together = [('empresa', 'produto')]

    def __str__(self):
        return self.produto.nome

    @property
    def nome(self):
        return self.produto.nome

    @property
    def fornecedor(self):
        """Fornecedor preferencial cadastrado em Produto > Fornecedores (ProdutoFornecedor).
        Cai para fornecedor_padrao (raramente preenchido, não exposto no form de Produto)
        só como último recurso."""
        pf = self.produto.fornecedores_relacionados.filter(ativo=True).order_by(
            '-fornecedor_preferencial', 'fornecedor__nome'
        ).select_related('fornecedor').first()
        if pf:
            return pf.fornecedor
        return self.produto.fornecedor_padrao


# ──────────────────────────── PalletEmbalado ───────────────────────────────

class PalletEmbalado(models.Model):
    STATUS = [
        ('DISPONIVEL', 'Disponível'),
        ('RESERVADO', 'Reservado'),
        ('CARREGADO', 'Carregado'),
        ('CANCELADO', 'Cancelado'),
    ]

    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='pallets_embalados',
        verbose_name='Empresa',
    )
    codigo_pallet = models.CharField('Código do Pallet', max_length=30, unique=True)
    ordem_embalagem = models.ForeignKey(
        OrdemEmbalagem,
        on_delete=models.CASCADE,
        related_name='pallets',
        verbose_name='Ordem de Embalagem',
    )
    tipo_embalagem = models.ForeignKey(
        TipoEmbalagem,
        on_delete=models.PROTECT,
        related_name='pallets',
        verbose_name='Tipo de Embalagem',
        null=True,
        blank=True,
        help_text='Nulo quando o pallet for misto (composição com múltiplos tipos)',
    )
    is_misto = models.BooleanField('Pallet Misto', default=False)
    estoque_baixado = models.BooleanField(
        'Baixa de Estoque Realizada', default=False,
        help_text='Pallets homogêneos já nascem com baixa feita; pallets mistos precisam ser finalizados.',
    )
    numero_sequencial = models.PositiveIntegerField('Nº Sequencial na Ordem')
    quantidade_caixas = models.PositiveIntegerField('Qtd de Caixas', default=0)
    peso_bruto_kg = models.DecimalField('Peso Bruto (kg)', max_digits=10, decimal_places=3, default=0)
    peso_liquido_kg = models.DecimalField('Peso Líquido (kg)', max_digits=10, decimal_places=3, default=0)
    data_embalagem = models.DateField('Data de Embalagem', default=timezone.now)
    armazem = models.ForeignKey(
        'estoque.Armazem',
        on_delete=models.PROTECT,
        related_name='pallets_embalados',
        verbose_name='Armazém',
    )
    local_estocagem = models.ForeignKey(
        'estoque.LocalEstocagem',
        on_delete=models.SET_NULL,
        related_name='pallets_embalados',
        verbose_name='Local de Estocagem',
        blank=True,
        null=True,
    )
    status = models.CharField('Status', max_length=20, choices=STATUS, default='DISPONIVEL')
    etiqueta_gerada = models.BooleanField('Etiqueta Gerada', default=False)
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)

    class Meta:
        verbose_name = 'Pallet Embalado'
        verbose_name_plural = 'Pallets Embalados'
        ordering = ['codigo_pallet']
        unique_together = [('ordem_embalagem', 'numero_sequencial')]
        indexes = [
            models.Index(fields=['empresa', 'status']),
            models.Index(fields=['empresa', 'data_embalagem']),
        ]

    def __str__(self):
        return self.codigo_pallet

    def recalcular_totais(self):
        """Recalcula quantidade e pesos somando os itens da composição (apenas para pallets mistos)."""
        if not self.is_misto:
            return
        totais = self.composicao.aggregate(
            caixas=Sum('quantidade_caixas'),
            bruto=Sum('peso_bruto_kg'),
            liquido=Sum('peso_liquido_kg'),
        )
        self.quantidade_caixas = totais['caixas'] or 0
        self.peso_bruto_kg = totais['bruto'] or Decimal('0')
        self.peso_liquido_kg = totais['liquido'] or Decimal('0')
        self.save(update_fields=['quantidade_caixas', 'peso_bruto_kg', 'peso_liquido_kg'])

    @property
    def alerta_capacidade(self):
        """Retorna True se o total de caixas divergir da capacidade esperada da ordem."""
        cap = self.ordem_embalagem.capacidade_caixas_pallet
        return cap and self.quantidade_caixas != cap

    @property
    def codigo_producao(self):
        """Código de rastreabilidade de produção (etiqueta de caixa PPWR), 10 dígitos:
        1 Produto (Empresa.codigo_produtor_rastreio) + 4 Talhão (Talhao.codigo) +
        2 Cultura (Cultura.codigo_interno) + 3 Calendário Juliano (data_embalagem).
        Retorna None se lote_producao (direto ou herdado — ver lote_producao_efetivo)
        ou algum dos códigos não estiver disponível/no formato certo.
        """
        lp = self.ordem_embalagem.lote_producao_efetivo()
        if not lp or not lp.talhao_id or not lp.cultura_id:
            return None
        prod = (self.empresa.codigo_produtor_rastreio or '').strip()
        talhao = (lp.talhao.codigo or '').strip()
        cultura = (lp.cultura.codigo_interno or '').strip()
        if not (len(prod) == 1 and prod.isdigit()
                and len(talhao) == 4 and talhao.isdigit()
                and len(cultura) == 2 and cultura.isdigit()):
            return None
        juliano = f'{self.data_embalagem.timetuple().tm_yday:03d}'
        return f'{prod}{talhao}{cultura}{juliano}'

    @property
    def codigo_chave_semana(self):
        """Segundo valor da linha "Key" da etiqueta de caixa: L{semana ISO} - {dia da semana ISO,
        1=segunda...7=domingo}, calculado a partir de data_embalagem — mesmo critério usado na
        planilha de referência do cliente (=CONCAT("L ";NÚMSEMANA(HOJE());" - ";DIA.DA.SEMANA(HOJE();2)))."""
        ano, semana, dia_iso = self.data_embalagem.isocalendar()
        return f'L {semana} - {dia_iso}'

    @classmethod
    def _gerar_codigo(cls, empresa, data=None, safra=None):
        """Gera o código único do pallet.

        Com safra definida e com código:
            formato 12 dígitos → {safra.codigo:6}{seq:06d}
            Ex: 202526000001

        Sem safra (fallback legado):
            formato → PLT-{YYYYMMDD}-{seq:04d}
        """
        from django.utils.timezone import now as tz_now

        if safra and safra.codigo:
            prefixo = safra.codigo
            ultimo = (cls.objects
                      .select_for_update()
                      .filter(empresa=empresa, codigo_pallet__startswith=prefixo)
                      .order_by('codigo_pallet')
                      .last())
            if ultimo:
                try:
                    seq = int(ultimo.codigo_pallet[len(prefixo):]) + 1
                except (ValueError, IndexError):
                    seq = 1
            else:
                seq = 1
            return f'{prefixo}{seq:06d}'

        # fallback: formato antigo baseado em data
        d = data or tz_now().date()
        prefixo = f'PLT-{d.strftime("%Y%m%d")}-'
        ultimo = (cls.objects
                  .select_for_update()
                  .filter(empresa=empresa, codigo_pallet__startswith=prefixo)
                  .order_by('codigo_pallet')
                  .last())
        if ultimo:
            try:
                seq = int(ultimo.codigo_pallet.split('-')[-1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        return f'{prefixo}{seq:04d}'


# ──────────────────────────── ItemPallet ───────────────────────────────────

class ItemPallet(models.Model):
    """Composição de um pallet misto: cada item é um TipoEmbalagem + quantidade."""

    pallet = models.ForeignKey(
        PalletEmbalado,
        on_delete=models.CASCADE,
        related_name='composicao',
        verbose_name='Pallet',
    )
    tipo_embalagem = models.ForeignKey(
        TipoEmbalagem,
        on_delete=models.PROTECT,
        related_name='itens_pallet',
        verbose_name='Tipo de Embalagem',
    )
    quantidade_caixas = models.PositiveIntegerField('Qtd de Caixas')
    peso_bruto_kg = models.DecimalField('Peso Bruto (kg)', max_digits=10, decimal_places=3)
    peso_liquido_kg = models.DecimalField('Peso Líquido (kg)', max_digits=10, decimal_places=3)

    class Meta:
        verbose_name = 'Item do Pallet'
        verbose_name_plural = 'Itens do Pallet'

    def __str__(self):
        return f'{self.quantidade_caixas}cx {self.tipo_embalagem}'

    def save(self, *args, **kwargs):
        # Calcula pesos automaticamente a partir do tipo de embalagem
        te = self.tipo_embalagem
        self.peso_bruto_kg = te.peso_bruto_cx * self.quantidade_caixas
        self.peso_liquido_kg = te.peso_liquido_cx * self.quantidade_caixas
        super().save(*args, **kwargs)
        self.pallet.recalcular_totais()

    def delete(self, *args, **kwargs):
        pallet = self.pallet
        super().delete(*args, **kwargs)
        pallet.recalcular_totais()


# ──────────────────────────── CargaFrete ───────────────────────────────────

class CargaFrete(models.Model):
    """
    Frete físico de um caminhão/carga (mercado interno), compartilhado por
    vários RomaneioVenda. Guarda os totais contratados com a transportadora
    (valor do frete, caixas, pedágio) para rateio por caixa entre os romaneios.
    """
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='cargas_frete',
        verbose_name='Empresa',
    )
    transportadora = models.ForeignKey(
        'cadastros.Transportadora',
        on_delete=models.PROTECT,
        related_name='cargas_frete',
        verbose_name='Transportadora',
    )
    identificador = models.CharField('Identificador', max_length=100, blank=True)
    data_embarque = models.DateField('Data do Embarque', default=timezone.now)
    valor_frete_total = models.DecimalField('Valor do Frete Total (R$)', max_digits=12, decimal_places=2)
    quantidade_caixas_total = models.PositiveIntegerField('Quantidade de Caixas Total')
    valor_pedagio_total = models.DecimalField(
        'Valor do Pedágio Total (R$)', max_digits=12, decimal_places=2, blank=True, null=True,
    )
    percentual_reducao_bc_padrao = models.DecimalField(
        'Redução de Base ICMS Padrão (%)', max_digits=5, decimal_places=2, default=Decimal('40.00'),
    )
    aliquota_icms_padrao = models.DecimalField(
        'Alíquota ICMS Padrão (%)', max_digits=5, decimal_places=2, default=Decimal('12.00'),
    )
    ativo = models.BooleanField('Ativo', default=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='cargas_frete_criadas',
        verbose_name='Criado por',
        blank=True,
        null=True,
    )
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)
    atualizado_em = models.DateTimeField('Atualizado em', auto_now=True)

    class Meta:
        verbose_name = 'Carga de Frete'
        verbose_name_plural = 'Cargas de Frete'
        ordering = ['-data_embarque', '-criado_em']
        indexes = [
            models.Index(fields=['empresa', 'ativo']),
        ]

    def __str__(self):
        if self.identificador:
            return self.identificador
        data = self.data_embarque.strftime('%d/%m/%Y') if self.data_embarque else '-'
        return f'Carga {data} - {self.transportadora}'

    @staticmethod
    def _ratear_por_maior_resto(valor_total, pesos):
        """
        Rateia valor_total (Decimal, 2 casas) entre itens proporcionalmente a
        `pesos` (ex.: caixas por romaneio), fechando exatamente o total pelo
        método do maior resto (sem sobra/falta de centavos).
        Retorna uma lista de Decimal (2 casas) na mesma ordem de `pesos`.
        """
        total_pesos = sum(pesos)
        if not total_pesos:
            return [Decimal('0.00')] * len(pesos)

        total_centavos = int((valor_total * 100).to_integral_value(rounding=ROUND_HALF_UP))

        pisos = []
        restos = []
        for peso in pesos:
            cota_centavos = (valor_total * 100) * Decimal(peso) / Decimal(total_pesos)
            piso = int(cota_centavos.to_integral_value(rounding=ROUND_DOWN))
            pisos.append(piso)
            restos.append(cota_centavos - piso)

        falta = total_centavos - sum(pisos)
        maiores_restos = sorted(range(len(pesos)), key=lambda i: restos[i], reverse=True)
        indices_com_extra = set(maiores_restos[:falta])

        return [
            (Decimal(piso + (1 if i in indices_com_extra else 0)) / 100).quantize(Decimal('0.01'))
            for i, piso in enumerate(pisos)
        ]

    def ratear(self):
        """
        Recalcula o rateio de frete/pedágio entre todos os romaneios vinculados
        (proporcional às caixas de cada um), fechando exatamente com
        valor_frete_total/valor_pedagio_total, e recalcula o ICMS de frete de
        cada romaneio. Levanta CargaFreteError se a carga estiver incompleta.
        """
        romaneios = list(self.romaneios.select_related('pedido_venda').all())
        if not romaneios:
            raise CargaFreteError('Nenhum romaneio vinculado a esta carga de frete.')

        caixas_por_romaneio = [r.total_caixas for r in romaneios]
        soma_caixas = sum(caixas_por_romaneio)
        if soma_caixas != self.quantidade_caixas_total:
            raise CargaFreteError(
                f'A soma das caixas dos romaneios vinculados ({soma_caixas}) não bate com '
                f'a quantidade total da carga ({self.quantidade_caixas_total}).'
            )

        fretes_rateados = self._ratear_por_maior_resto(self.valor_frete_total, caixas_por_romaneio)
        pedagios_rateados = (
            self._ratear_por_maior_resto(self.valor_pedagio_total, caixas_por_romaneio)
            if self.valor_pedagio_total else [Decimal('0.00')] * len(romaneios)
        )

        with transaction.atomic():
            for romaneio, frete, pedagio in zip(romaneios, fretes_rateados, pedagios_rateados):
                romaneio.valor_frete_rateado = frete
                romaneio.valor_pedagio_rateado = pedagio
                romaneio.calcular_icms_frete()
                romaneio.save(update_fields=[
                    'valor_frete_rateado', 'valor_pedagio_rateado',
                    'valor_bc_icms_frete', 'valor_icms_frete',
                    'percentual_reducao_bc', 'aliquota_icms_frete',
                ])
                if romaneio.pedido_venda_id:
                    pedido = romaneio.pedido_venda
                    pedido.valor_frete = frete
                    pedido.calcular_total()
                    pedido.save(update_fields=['valor_frete', 'valor_produtos', 'valor_total'])


# ──────────────────────────── RomaneioVenda ────────────────────────────────

class RomaneioVenda(models.Model):
    TIPO = [
        ('EXPORTACAO', 'Exportação'),
        ('MERCADO_INTERNO', 'Mercado Interno'),
    ]
    STATUS = [
        ('RASCUNHO', 'Rascunho'),
        ('CONFIRMADO', 'Confirmado'),
        ('CARREGANDO', 'Carregando'),
        ('CONCLUIDO', 'Concluído'),
        ('CANCELADO', 'Cancelado'),
    ]
    METODO_ICMS_FRETE = [
        ('REDUCAO', 'Com redução de base de cálculo'),
        ('CHEIO', 'Alíquota cheia sobre o frete'),
    ]

    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='romaneios_venda',
        verbose_name='Empresa',
    )
    numero = models.CharField('Número', max_length=20, unique=True, blank=True)
    tipo = models.CharField('Tipo', max_length=20, choices=TIPO, default='EXPORTACAO')
    cliente = models.ForeignKey(
        'cadastros.Cliente',
        on_delete=models.PROTECT,
        related_name='romaneios_venda',
        verbose_name='Cliente',
    )
    data = models.DateField('Data', default=timezone.now)
    pedido_venda = models.OneToOneField(
        'vendas.PedidoVenda',
        on_delete=models.SET_NULL,
        related_name='romaneio_venda',
        verbose_name='Pedido de Venda',
        blank=True,
        null=True,
    )
    # Exportação
    booking = models.ForeignKey(
        'exportacao.Booking',
        on_delete=models.SET_NULL,
        related_name='romaneios_venda',
        verbose_name='Booking',
        blank=True,
        null=True,
    )
    container = models.ForeignKey(
        'exportacao.BookingContainer',
        on_delete=models.SET_NULL,
        related_name='romaneios_venda',
        verbose_name='Container',
        blank=True,
        null=True,
    )
    # Frete/ICMS de frete (mercado interno)
    carga_frete = models.ForeignKey(
        CargaFrete,
        on_delete=models.SET_NULL,
        related_name='romaneios',
        verbose_name='Carga de Frete',
        blank=True,
        null=True,
    )
    metodo_icms_frete = models.CharField(
        'Método de Cálculo do ICMS de Frete', max_length=10,
        choices=METODO_ICMS_FRETE, default='REDUCAO', blank=True,
    )
    percentual_reducao_bc = models.DecimalField(
        'Redução de Base ICMS Frete (%)', max_digits=5, decimal_places=2, blank=True, null=True,
    )
    aliquota_icms_frete = models.DecimalField(
        'Alíquota ICMS Frete (%)', max_digits=5, decimal_places=2, blank=True, null=True,
    )
    valor_frete_rateado = models.DecimalField(
        'Valor do Frete Rateado (R$)', max_digits=12, decimal_places=2, blank=True, null=True,
    )
    valor_pedagio_rateado = models.DecimalField(
        'Valor do Pedágio Rateado (R$)', max_digits=12, decimal_places=2, blank=True, null=True,
    )
    valor_bc_icms_frete = models.DecimalField(
        'Base de Cálculo ICMS Frete (R$)', max_digits=12, decimal_places=2, blank=True, null=True,
    )
    valor_icms_frete = models.DecimalField(
        'Valor ICMS Frete (R$)', max_digits=12, decimal_places=2, blank=True, null=True,
    )
    status = models.CharField('Status', max_length=20, choices=STATUS, default='RASCUNHO')
    observacoes = models.TextField('Observações', blank=True)
    rastreabilidade_transporte = models.CharField(
        'Rastreabilidade TP', max_length=20, unique=True, blank=True, null=True,
        help_text='Código de rastreabilidade da embalagem de transporte (PPWR), gerado na confirmação.',
    )
    rastreabilidade_venda = models.CharField(
        'Rastreabilidade SP', max_length=20, unique=True, blank=True, null=True,
        help_text='Código de rastreabilidade da embalagem de venda (PPWR), gerado na confirmação.',
    )
    invoice_exportacao = models.OneToOneField(
        'faturamento.InvoiceExportacao',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='romaneio_origem',
        verbose_name='Invoice de Exportação',
    )
    nota_fiscal = models.OneToOneField(
        'faturamento.NotaFiscal',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='romaneio_origem',
        verbose_name='Nota Fiscal',
    )
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='romaneios_venda_criados',
        verbose_name='Criado por',
        blank=True,
        null=True,
    )
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)
    atualizado_em = models.DateTimeField('Atualizado em', auto_now=True)

    class Meta:
        verbose_name = 'Romaneio de Venda'
        verbose_name_plural = 'Romaneios de Venda'
        ordering = ['-criado_em']
        indexes = [
            models.Index(fields=['empresa', 'status']),
            models.Index(fields=['empresa', 'tipo', 'data']),
        ]

    def __str__(self):
        return self.numero or f'RV-{self.pk}'

    @classmethod
    def _gerar_numero(cls, empresa):
        ano = timezone.now().year
        # select_for_update evita race condition em criações simultâneas
        ultimo = (cls.objects
                  .select_for_update()
                  .filter(empresa=empresa, numero__startswith=f'RV-{ano}-')
                  .order_by('numero')
                  .last())
        if ultimo and ultimo.numero:
            try:
                seq = int(ultimo.numero.split('-')[-1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        return f'RV-{ano}-{seq:04d}'

    @classmethod
    def _gerar_rastreabilidade(cls, empresa, data=None):
        """Gera o par de códigos de rastreabilidade PPWR (TP/SP) do romaneio.

        Formato: {TP|SP}-{ANO}{SEMANA ISO:02d}{SEQ:04d}. O sequencial é
        compartilhado entre TP e SP do mesmo romaneio e reseta sempre que a
        semana ISO muda (não reseta por ano isoladamente).
        """
        data = data or timezone.now().date()
        ano, semana, _ = data.isocalendar()
        periodo = f'{ano}{semana:02d}'
        # select_for_update evita race condition em confirmações simultâneas
        ultimo = (cls.objects
                  .select_for_update()
                  .filter(empresa=empresa, rastreabilidade_transporte__startswith=f'TP-{periodo}')
                  .order_by('rastreabilidade_transporte')
                  .last())
        if ultimo and ultimo.rastreabilidade_transporte:
            try:
                seq = int(ultimo.rastreabilidade_transporte[-4:]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        sufixo = f'{periodo}{seq:04d}'
        return f'TP-{sufixo}', f'SP-{sufixo}'

    def _totais(self):
        """Retorna todos os totais em uma única query SQL."""
        return self.itens.aggregate(
            _pallets=Count('id'),
            _caixas=Sum('quantidade_caixas'),
            _bruto=Sum('peso_bruto_kg'),
            _liquido=Sum('peso_liquido_kg'),
            _conferidos=Count('id', filter=Q(status_conferencia='CONFERIDO')),
        )

    @property
    def total_pallets(self):
        return self.itens.count()

    @property
    def total_caixas(self):
        return self.itens.aggregate(t=Sum('quantidade_caixas'))['t'] or 0

    @property
    def peso_bruto_total(self):
        return self.itens.aggregate(t=Sum('peso_bruto_kg'))['t'] or Decimal('0')

    @property
    def peso_liquido_total(self):
        return self.itens.aggregate(t=Sum('peso_liquido_kg'))['t'] or Decimal('0')

    @property
    def pallets_conferidos(self):
        return self.itens.filter(status_conferencia='CONFERIDO').count()

    def save(self, *args, **kwargs):
        if self.carga_frete_id:
            if self.percentual_reducao_bc is None:
                self.percentual_reducao_bc = self.carga_frete.percentual_reducao_bc_padrao
            if self.aliquota_icms_frete is None:
                self.aliquota_icms_frete = self.carga_frete.aliquota_icms_padrao
        super().save(*args, **kwargs)

    def calcular_icms_frete(self):
        """
        Calcula a base e o valor do ICMS sobre o frete rateado deste romaneio.
        Segue o mesmo formato de cálculo usado em ProdutoTributacao.calcular_icms:
        BC = valor * (100 - reducao) / 100; icms = BC * aliquota / 100
        (arredondamento só no ponto de persistência).
        """
        if self.valor_frete_rateado is None:
            return
        base = self.valor_frete_rateado
        reducao = self.percentual_reducao_bc or Decimal('0')
        if self.metodo_icms_frete == 'REDUCAO' and reducao > 0:
            base = base * (Decimal('100') - reducao) / Decimal('100')
        self.valor_bc_icms_frete = base.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        aliquota = self.aliquota_icms_frete or Decimal('0')
        self.valor_icms_frete = (
            self.valor_bc_icms_frete * aliquota / Decimal('100')
        ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


# ──────────────────────────── ItemRomaneioVenda ────────────────────────────

class ItemRomaneioVenda(models.Model):
    STATUS_CONFERENCIA = [
        ('PENDENTE', 'Pendente'),
        ('CONFERIDO', 'Conferido'),
        ('DIVERGENTE', 'Divergente'),
    ]

    romaneio = models.ForeignKey(
        RomaneioVenda,
        on_delete=models.CASCADE,
        related_name='itens',
        verbose_name='Romaneio',
    )
    pallet = models.ForeignKey(
        PalletEmbalado,
        on_delete=models.PROTECT,
        related_name='itens_romaneio',
        verbose_name='Pallet',
    )
    quantidade_caixas = models.PositiveIntegerField('Qtd de Caixas')
    peso_bruto_kg = models.DecimalField('Peso Bruto (kg)', max_digits=10, decimal_places=3)
    peso_liquido_kg = models.DecimalField('Peso Líquido (kg)', max_digits=10, decimal_places=3)
    marks_numbers = models.CharField('Marks & Numbers', max_length=100, blank=True)
    status_conferencia = models.CharField(
        'Status Conferência', max_length=20,
        choices=STATUS_CONFERENCIA, default='PENDENTE',
    )
    data_conferencia = models.DateTimeField('Data da Conferência', blank=True, null=True)
    conferido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='itens_romaneio_conferidos',
        verbose_name='Conferido por',
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = 'Item do Romaneio'
        verbose_name_plural = 'Itens do Romaneio'
        ordering = ['pallet__codigo_pallet']
        unique_together = [('romaneio', 'pallet')]

    def __str__(self):
        return f'{self.romaneio} / {self.pallet}'


# ────────────────────────── RomaneioMaterialEmbalagem ──────────────────────

class RomaneioMaterialEmbalagem(models.Model):
    """Vincula um MaterialEmbalagem (e seu fornecedor) ao romaneio, para compor
    o relatório de rastreabilidade PPWR. O tipo (TP/SP) é sempre o do material."""

    romaneio = models.ForeignKey(
        RomaneioVenda,
        on_delete=models.CASCADE,
        related_name='materiais_embalagem',
        verbose_name='Romaneio',
    )
    material = models.ForeignKey(
        MaterialEmbalagem,
        on_delete=models.PROTECT,
        related_name='usos_em_romaneios',
        verbose_name='Material de Embalagem',
    )
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)

    class Meta:
        verbose_name = 'Material de Embalagem do Romaneio'
        verbose_name_plural = 'Materiais de Embalagem do Romaneio'
        ordering = ['material__tipo', 'material__produto__nome']
        unique_together = [('romaneio', 'material')]

    def __str__(self):
        return f'{self.romaneio} / {self.material}'
