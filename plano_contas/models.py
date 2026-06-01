import re
from django.db import models
from django.core.exceptions import ValidationError


TIPO_CONTA_CHOICES = [
    ('ATIVO', 'Ativo'),
    ('PASSIVO', 'Passivo'),
    ('PATRIMONIO_LIQUIDO', 'Patrimônio Líquido'),
    ('RECEITA', 'Receita'),
    ('DESPESA', 'Despesa'),
    ('CUSTO', 'Custo'),
]

NATUREZA_CHOICES = [
    ('DEVEDORA', 'Devedora'),
    ('CREDORA', 'Credora'),
]

BADGE_TIPO = {
    'ATIVO': 'primary',
    'PASSIVO': 'warning',
    'PATRIMONIO_LIQUIDO': 'info',
    'RECEITA': 'success',
    'DESPESA': 'danger',
    'CUSTO': 'secondary',
}


class ContaContabil(models.Model):
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='contas_contabeis',
        verbose_name='Empresa',
    )
    conta_pai = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subcontas',
        verbose_name='Conta Pai',
    )
    codigo = models.CharField(max_length=20, verbose_name='Código')
    nome = models.CharField(max_length=200, verbose_name='Nome')
    tipo = models.CharField(max_length=20, choices=TIPO_CONTA_CHOICES, verbose_name='Tipo')
    natureza = models.CharField(max_length=10, choices=NATUREZA_CHOICES, verbose_name='Natureza')
    nivel = models.IntegerField(default=1, editable=False, verbose_name='Nível')
    analitica = models.BooleanField(
        default=True,
        verbose_name='Analítica',
        help_text='Contas analíticas aceitam lançamentos. Sintéticas são apenas agrupamentos.',
    )
    gerencial = models.BooleanField(
        default=False,
        verbose_name='Gerencial',
        help_text='Marca a conta como categoria gerencial (além de contábil).',
    )
    descricao = models.TextField(blank=True, verbose_name='Descrição')
    observacoes = models.TextField(blank=True, verbose_name='Observações')
    ativo = models.BooleanField(default=True, verbose_name='Ativo')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Conta Contábil'
        verbose_name_plural = 'Contas Contábeis'
        ordering = ['empresa', 'codigo']
        unique_together = [['empresa', 'codigo']]
        indexes = [
            models.Index(fields=['empresa', 'tipo']),
            models.Index(fields=['empresa', 'conta_pai']),
            models.Index(fields=['empresa', 'ativo']),
        ]

    def __str__(self):
        return f'{self.codigo} — {self.nome}'

    def clean(self):
        errors = {}
        if self.codigo and not re.match(r'^\d+(\.\d+)*$', self.codigo):
            errors['codigo'] = 'Código deve ter formato numérico separado por pontos (ex: 1.1.01.001)'
        if self.conta_pai_id:
            if self.conta_pai.empresa_id != self.empresa_id:
                errors['conta_pai'] = 'A conta pai deve pertencer à mesma empresa'
            if self.pk and self.conta_pai_id == self.pk:
                errors['conta_pai'] = 'A conta não pode ser pai de si mesma'
            if self.conta_pai.analitica:
                errors['conta_pai'] = 'Uma conta analítica não pode ter subcontas'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.conta_pai_id:
            try:
                pai = ContaContabil.objects.get(pk=self.conta_pai_id)
                self.nivel = pai.nivel + 1
            except ContaContabil.DoesNotExist:
                self.nivel = 1
        else:
            self.nivel = 1
        super().save(*args, **kwargs)

    @property
    def tem_subcontas(self):
        return ContaContabil.objects.filter(conta_pai=self).exists()

    @property
    def tem_subcontas_ativas(self):
        return ContaContabil.objects.filter(conta_pai=self, ativo=True).exists()

    @property
    def get_indent(self):
        return (self.nivel - 1) * 20

    @property
    def badge_tipo(self):
        return BADGE_TIPO.get(self.tipo, 'secondary')

    def get_caminho(self):
        caminho = [self]
        atual = self
        while atual.conta_pai_id:
            try:
                atual = ContaContabil.objects.get(pk=atual.conta_pai_id)
                caminho.insert(0, atual)
            except ContaContabil.DoesNotExist:
                break
        return caminho


class CentroCusto(models.Model):
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='centros_custo',
        verbose_name='Empresa',
    )
    centro_pai = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subcentros',
        verbose_name='Centro Pai',
    )
    codigo = models.CharField(max_length=20, verbose_name='Código')
    nome = models.CharField(max_length=200, verbose_name='Nome')
    descricao = models.TextField(blank=True, verbose_name='Descrição')
    nivel = models.IntegerField(default=1, editable=False, verbose_name='Nível')
    ativo = models.BooleanField(default=True, verbose_name='Ativo')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Centro de Custo'
        verbose_name_plural = 'Centros de Custo'
        ordering = ['empresa', 'codigo']
        unique_together = [['empresa', 'codigo']]
        indexes = [
            models.Index(fields=['empresa', 'ativo']),
        ]

    def __str__(self):
        return f'{self.codigo} — {self.nome}'

    def clean(self):
        errors = {}
        if self.centro_pai_id:
            if self.centro_pai.empresa_id != self.empresa_id:
                errors['centro_pai'] = 'O centro pai deve pertencer à mesma empresa'
            if self.pk and self.centro_pai_id == self.pk:
                errors['centro_pai'] = 'O centro não pode ser pai de si mesmo'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.centro_pai_id:
            try:
                pai = CentroCusto.objects.get(pk=self.centro_pai_id)
                self.nivel = pai.nivel + 1
            except CentroCusto.DoesNotExist:
                self.nivel = 1
        else:
            self.nivel = 1
        super().save(*args, **kwargs)

    @property
    def tem_subcentros(self):
        return CentroCusto.objects.filter(centro_pai=self).exists()

    @property
    def tem_subcentros_ativos(self):
        return CentroCusto.objects.filter(centro_pai=self, ativo=True).exists()

    @property
    def get_indent(self):
        return (self.nivel - 1) * 20
