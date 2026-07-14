from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Estufa(models.Model):
    TIPO_CHOICES = [
        ('PLASTICO', 'Plástico'),
        ('VIDRO', 'Vidro'),
        ('SOMBRITE', 'Sombrite'),
        ('OUTRO', 'Outro'),
    ]

    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='estufas')
    fazenda = models.ForeignKey('cadastros.Fazenda', on_delete=models.CASCADE, related_name='estufas')
    nome = models.CharField(max_length=100)
    codigo = models.CharField(max_length=20)
    area_m2 = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0.01'))], verbose_name='Área (m²)',
    )
    capacidade_bandejas = models.IntegerField(null=True, blank=True, verbose_name='Capacidade (bandejas)')
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES, default='PLASTICO')
    ativo = models.BooleanField(default=True)
    observacoes = models.TextField(blank=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    cadastrado_por = models.ForeignKey(
        'usuarios.Usuario', null=True, on_delete=models.SET_NULL, related_name='estufas_criadas',
    )

    class Meta:
        db_table = 'cadastros_estufa'
        unique_together = ['empresa', 'fazenda', 'codigo']
        ordering = ['fazenda', 'nome']
        verbose_name = 'Estufa'
        verbose_name_plural = 'Estufas'

    def __str__(self):
        return f"{self.nome} ({self.codigo}) — {self.fazenda.nome}"

    def get_lotes_ativos(self):
        return self.lotes.exclude(status__in=['TRANSPLANTADO', 'ENCERRADO'])


class LoteMuda(models.Model):
    STATUS_CHOICES = [
        ('SEMEADO', 'Semeado'),
        ('EM_CRESCIMENTO', 'Em Crescimento'),
        ('PRONTO', 'Pronto p/ Transplantio'),
        ('TRANSPLANTADO', 'Transplantado'),
        ('ENCERRADO', 'Encerrado'),
    ]
    STATUS_AVANCAR = {
        'SEMEADO': 'EM_CRESCIMENTO',
        'EM_CRESCIMENTO': 'PRONTO',
    }

    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='lotes_muda')
    estufa = models.ForeignKey(Estufa, on_delete=models.CASCADE, related_name='lotes')
    cultura = models.ForeignKey('cadastros.Cultura', on_delete=models.PROTECT, related_name='lotes_muda')
    cultivar = models.CharField(max_length=100, blank=True)
    codigo_lote = models.CharField(max_length=30, unique=True)
    lote_semente = models.CharField(
        max_length=100, blank=True, verbose_name='Lote da semente',
        help_text='Código do lote de semente para rastreabilidade (RF-1202)',
    )
    data_semeadura = models.DateField()
    quantidade_semeada = models.IntegerField(validators=[MinValueValidator(1)])
    data_prevista_pronto = models.DateField(null=True, blank=True, verbose_name='Data prevista para transplantio')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SEMEADO')
    responsavel = models.ForeignKey(
        'rh.Funcionario', null=True, blank=True, on_delete=models.SET_NULL, related_name='lotes_responsavel',
    )
    observacoes = models.TextField(blank=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    cadastrado_por = models.ForeignKey(
        'usuarios.Usuario', null=True, on_delete=models.SET_NULL, related_name='lotes_criados',
    )

    class Meta:
        db_table = 'cadastros_lotemuda'
        ordering = ['-data_semeadura']
        verbose_name = 'Lote de Mudas'
        verbose_name_plural = 'Lotes de Mudas'

    def __str__(self):
        return f"{self.codigo_lote} — {self.cultura.nome} ({self.get_status_display()})"

    @property
    def quantidade_perdida(self):
        return self.perdas.aggregate(t=models.Sum('quantidade_perdida'))['t'] or 0

    @property
    def quantidade_transplantada(self):
        return self.transplantios.aggregate(t=models.Sum('quantidade_transplantada'))['t'] or 0

    @property
    def quantidade_disponivel(self):
        return max(0, self.quantidade_semeada - self.quantidade_perdida - self.quantidade_transplantada)

    @property
    def custo_total_estufa(self):
        from django.db.models import F as DbF
        total = self.aplicacoes.aggregate(
            t=models.Sum(DbF('quantidade') * DbF('custo_unitario'))
        )['t']
        return total or Decimal('0.00')

    @property
    def custo_por_muda(self):
        if self.quantidade_disponivel > 0:
            return self.custo_total_estufa / self.quantidade_disponivel
        return Decimal('0.00')

    @property
    def percentual_perdas(self):
        if self.quantidade_semeada > 0:
            return round((self.quantidade_perdida / self.quantidade_semeada) * 100, 1)
        return 0

    @classmethod
    def gerar_codigo_lote(cls, empresa_id):
        ano = timezone.now().year
        prefixo = f"LM-{ano}-"
        ultimo = cls.objects.filter(codigo_lote__startswith=prefixo).order_by('-codigo_lote').first()
        if ultimo:
            try:
                seq = int(ultimo.codigo_lote.split('-')[-1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        return f"{prefixo}{seq:05d}"


class PerdaEstufa(models.Model):
    MOTIVO_CHOICES = [
        ('DOENCA', 'Doença'),
        ('PRAGA', 'Praga'),
        ('AMBIENTE', 'Fator Ambiental'),
        ('QUALIDADE', 'Qualidade da Semente'),
        ('OUTRO', 'Outro'),
    ]

    lote_muda = models.ForeignKey(LoteMuda, on_delete=models.CASCADE, related_name='perdas')
    data = models.DateField()
    quantidade_perdida = models.IntegerField(validators=[MinValueValidator(1)])
    motivo = models.CharField(max_length=30, choices=MOTIVO_CHOICES)
    observacao = models.TextField(blank=True)
    responsavel = models.ForeignKey(
        'rh.Funcionario', null=True, blank=True, on_delete=models.SET_NULL, related_name='perdas_estufa',
    )

    class Meta:
        db_table = 'cadastros_perdaestufa'
        ordering = ['-data']
        verbose_name = 'Perda na Estufa'
        verbose_name_plural = 'Perdas na Estufa'

    def __str__(self):
        return f"Perda {self.lote_muda.codigo_lote} — {self.data} — {self.quantidade_perdida} un"

    def clean(self):
        if self.quantidade_perdida and self.lote_muda_id:
            disponivel_atual = (
                self.lote_muda.quantidade_semeada
                - self.lote_muda.quantidade_transplantada
                - (self.lote_muda.perdas.exclude(pk=self.pk).aggregate(t=models.Sum('quantidade_perdida'))['t'] or 0)
            )
            if self.quantidade_perdida > disponivel_atual:
                raise ValidationError({
                    'quantidade_perdida': f'Quantidade ({self.quantidade_perdida}) supera o disponível ({disponivel_atual}).',
                })


class AplicacaoEstufa(models.Model):
    TIPO_CHOICES = [
        ('DEFENSIVO', 'Defensivo'),
        ('FERTILIZANTE', 'Fertilizante'),
        ('OUTRO', 'Outro'),
    ]

    lote_muda = models.ForeignKey(LoteMuda, on_delete=models.CASCADE, related_name='aplicacoes')
    data = models.DateField()
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    produto = models.ForeignKey('produtos.Produto', on_delete=models.PROTECT)
    quantidade = models.DecimalField(
        max_digits=10, decimal_places=3, validators=[MinValueValidator(Decimal('0.001'))],
    )
    unidade_medida = models.ForeignKey('produtos.UnidadeMedida', on_delete=models.PROTECT)
    custo_unitario = models.DecimalField(
        max_digits=12, decimal_places=4, default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))], verbose_name='Custo unitário (R$)',
    )
    responsavel = models.ForeignKey(
        'rh.Funcionario', null=True, blank=True, on_delete=models.SET_NULL, related_name='aplicacoes_estufa',
    )
    observacao = models.CharField(max_length=255, blank=True)
    receituario = models.CharField(max_length=50, blank=True, verbose_name='Nº Receituário Agronômico')

    class Meta:
        db_table = 'cadastros_aplicacaoestufa'
        ordering = ['-data']
        verbose_name = 'Aplicação na Estufa'
        verbose_name_plural = 'Aplicações na Estufa'

    def __str__(self):
        return f"{self.produto} — {self.lote_muda.codigo_lote} — {self.data}"

    @property
    def custo_total(self):
        return self.quantidade * self.custo_unitario


class MonitoramentoEstufa(models.Model):
    NIVEL_CHOICES = [
        ('AUSENTE', 'Ausente'),
        ('BAIXO', 'Baixo'),
        ('MEDIO', 'Médio'),
        ('ALTO', 'Alto'),
    ]

    lote_muda = models.ForeignKey(LoteMuda, on_delete=models.CASCADE, related_name='monitoramentos_estufa')
    data = models.DateField()
    praga = models.ForeignKey('cadastros.Praga', on_delete=models.PROTECT, related_name='monitoramentos_estufa')
    nivel_infestacao = models.CharField(max_length=20, choices=NIVEL_CHOICES)
    acao_tomada = models.TextField(blank=True)
    responsavel = models.ForeignKey(
        'rh.Funcionario', null=True, blank=True, on_delete=models.SET_NULL, related_name='monitoramentos_estufa',
    )

    class Meta:
        db_table = 'cadastros_monitoramentoestufa'
        ordering = ['-data']
        verbose_name = 'Monitoramento na Estufa'
        verbose_name_plural = 'Monitoramentos na Estufa'

    def __str__(self):
        return f"{self.praga.nome_comum} — {self.lote_muda.codigo_lote} — {self.data}"



# Transplantio e Replantio agora são executados como Ordem de Serviço
# (tipo Plantio, subtipo Transplante/Replantio) — ver operacoes_campo.models
# .OSTransplantio / .OSReplantio. Os models próprios foram removidos.
