"""
Módulo Frota — veículos, motoristas, abastecimento, manutenção, telemetria.

Os modelos usam db_table apontando para as tabelas existentes (prefixo cadastros_)
para que nenhuma migração de banco seja necessária na separação do app.
"""
from django.db import models
from django.core.validators import MinValueValidator, FileExtensionValidator
from decimal import Decimal
from datetime import date
import os


VEHICLE_TYPES = [
    ('LEVE', 'Leve'),
    ('MEDIO', 'Médio'),
    ('PESADO', 'Pesado'),
    ('REBOQUE', 'Reboque'),
    ('IMPLEMENTO', 'Implemento'),
]

TIPO_RODADO_CHOICES = [
    ('01', '01 - Truck'),
    ('02', '02 - Toco'),
    ('03', '03 - Cavalo Mecânico'),
    ('04', '04 - VAN'),
    ('05', '05 - Quadro'),
    ('06', '06 - Outros'),
]

TIPO_CARROCERIA_CHOICES = [
    ('00', '00 - Não Aplicável'),
    ('01', '01 - Aberta'),
    ('02', '02 - Fechada/Baú'),
    ('03', '03 - Graneleira'),
    ('04', '04 - Porta Container'),
    ('05', '05 - Sider'),
]


# ==========================
# VEÍCULOS
# ==========================

class Vehicle(models.Model):
    """Cadastro de veículos (próprios ou de terceiros)."""

    empresa = models.ForeignKey(
        'empresas.Empresa', on_delete=models.CASCADE, related_name='veiculos', verbose_name='Empresa'
    )
    transportadora = models.ForeignKey(
        'cadastros.Transportadora', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='veiculos', verbose_name='Transportadora'
    )

    tipo = models.CharField('Tipo', max_length=20, choices=VEHICLE_TYPES, default='LEVE')
    marca = models.CharField('Marca', max_length=100, blank=True)
    modelo = models.CharField('Modelo', max_length=100, blank=True)
    ano_fabricacao = models.IntegerField('Ano Fabricação', null=True, blank=True)
    ano_modelo = models.IntegerField('Ano Modelo', null=True, blank=True)
    capacidade_ton = models.DecimalField('Capacidade (ton)', max_digits=8, decimal_places=2, null=True, blank=True)
    tara_kg = models.IntegerField('Tara (kg)', null=True, blank=True)
    eixos = models.IntegerField('Eixos', null=True, blank=True)
    cor = models.CharField('Cor', max_length=50, blank=True)
    descricao = models.CharField(
        'Nome/Descrição', max_length=150, blank=True,
        help_text='Ex: Trator Amarelo, Implemento XX, Caminhão Branco'
    )

    foto = models.ImageField(
        'Foto do Veiculo', upload_to='veiculos/fotos/%Y/%m/', blank=True, null=True,
        help_text='Foto do veiculo/implemento'
    )

    RENAVAM_CHOICES = []
    FUEL_CHOICES = [
        ('DIESEL', 'Diesel'),
        ('GASOLINA', 'Gasolina'),
        ('FLEX', 'Flex'),
        ('ELETRICO', 'Elétrico'),
        ('OUTRO', 'Outro')
    ]

    renavam = models.CharField('RENAVAM', max_length=30, blank=True)
    rntrc = models.CharField('RNTRC', max_length=8, blank=True, help_text='Registro Nacional de Transportadores Rodoviários de Cargas')
    tipo_rodado = models.CharField('Tipo de Rodado', max_length=2, blank=True, choices=TIPO_RODADO_CHOICES)
    tipo_carroceria = models.CharField('Tipo de Carroceria', max_length=2, blank=True, choices=TIPO_CARROCERIA_CHOICES)
    uf_licenciamento = models.CharField('UF de Licenciamento', max_length=2, blank=True, help_text='UF onde o veículo está registrado/licenciado')
    chassis = models.CharField('Chassi', max_length=50, blank=True)
    numero_motor = models.CharField('Número do Motor', max_length=50, blank=True)
    tipo_combustivel = models.CharField('Tipo de Combustível', max_length=20, choices=FUEL_CHOICES, blank=True)
    codigo_patrimonio = models.CharField(
        'Código de Patrimônio', max_length=50, blank=True,
        help_text='Usado em veículos/implementos sem placa'
    )

    CONSUMO_UNIDADE_CHOICES = [
        ('L_KM', 'L/km'),
        ('L_HORA', 'L/hora')
    ]
    consumo_medio = models.DecimalField(
        'Consumo Médio', max_digits=8, decimal_places=4, null=True, blank=True,
        help_text='Consumo médio: L/km (padrão) ou L/hora para tratores'
    )
    consumo_unidade = models.CharField(
        'Unidade de Consumo', max_length=10, choices=CONSUMO_UNIDADE_CHOICES, default='L_KM'
    )

    tank_capacity = models.DecimalField('Capacidade do Tanque (L)', max_digits=8, decimal_places=2, null=True, blank=True)

    valor_atual = models.DecimalField('Valor Atual (R$)', max_digits=12, decimal_places=2, null=True, blank=True)
    percentual_variacao = models.DecimalField('Percentual de Variação (%)', max_digits=5, decimal_places=2, null=True, blank=True)
    TIPO_VARIACAO_CHOICES = [
        ('VAL', 'Valorização'),
        ('DES', 'Desvalorização'),
    ]
    tipo_variacao = models.CharField('Tipo de Variação', max_length=3, choices=TIPO_VARIACAO_CHOICES, blank=True)

    observacoes = models.TextField('Observações', blank=True)

    ativo = models.BooleanField('Ativo', default=True)
    data_cadastro = models.DateTimeField('Data de Cadastro', auto_now_add=True)
    data_atualizacao = models.DateTimeField('Última Atualização', auto_now=True)

    class Meta:
        db_table = 'cadastros_vehicle'
        verbose_name = 'Veículo'
        verbose_name_plural = 'Veículos'
        ordering = ['-data_cadastro']
        indexes = [models.Index(fields=['empresa', 'ativo'])]

    @property
    def estimated_range_km(self):
        from decimal import Decimal, ROUND_HALF_UP
        if not self.tank_capacity or not self.consumo_medio:
            return None
        try:
            if self.consumo_unidade == 'L_HORA':
                return None
            if self.consumo_medio == Decimal('0'):
                return None
            return (self.tank_capacity / self.consumo_medio).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        except Exception:
            return None

    @property
    def estimated_hours_per_tank(self):
        from decimal import Decimal, ROUND_HALF_UP
        if not self.tank_capacity or not self.consumo_medio:
            return None
        try:
            if self.consumo_unidade == 'L_KM':
                return None
            if self.consumo_medio == Decimal('0'):
                return None
            return (self.tank_capacity / self.consumo_medio).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        except Exception:
            return None

    @property
    def display_name(self):
        if self.descricao:
            return self.descricao
        return f"{self.marca} {self.modelo}".strip()

    def __str__(self):
        plate = self.get_current_plate() or ''
        return f"{self.display_name} {plate}".strip()

    def get_current_plate(self):
        p = self.plates.filter(atual=True).first()
        return p.placa if p else None


class VehicleValueHistory(models.Model):
    vehicle = models.ForeignKey('Vehicle', on_delete=models.CASCADE, related_name='value_history')
    previous_value = models.DecimalField('Valor Anterior (R$)', max_digits=12, decimal_places=2)
    new_value = models.DecimalField('Valor Novo (R$)', max_digits=12, decimal_places=2)
    percentual = models.DecimalField('Percentual (%)', max_digits=6, decimal_places=2)
    tipo = models.CharField('Tipo', max_length=3, choices=Vehicle.TIPO_VARIACAO_CHOICES)
    aplicado_por = models.ForeignKey('usuarios.Usuario', null=True, blank=True, on_delete=models.SET_NULL)
    data_aplicacao = models.DateTimeField('Data Aplicação', auto_now_add=True)

    class Meta:
        db_table = 'cadastros_vehiclevaluehistory'
        verbose_name = 'Histórico de Valor do Veículo'
        verbose_name_plural = 'Históricos de Valor de Veículos'
        ordering = ['-data_aplicacao']

    def __str__(self):
        return f"{self.vehicle} — {self.tipo} {self.percentual}% em {self.data_aplicacao.date()}"


class VehiclePlate(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='plates')
    placa = models.CharField('Placa', max_length=10)
    vigencia_inicio = models.DateField('Vigência Início')
    vigencia_fim = models.DateField('Vigência Fim', null=True, blank=True)
    atual = models.BooleanField('Placa Atual', default=False)

    class Meta:
        db_table = 'cadastros_vehicleplate'
        verbose_name = 'Placa do Veículo'
        verbose_name_plural = 'Placas do Veículo'
        ordering = ['-vigencia_inicio']

    def save(self, *args, **kwargs):
        if self.atual:
            VehiclePlate.objects.filter(vehicle=self.vehicle, atual=True).exclude(pk=self.pk).update(atual=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.placa} ({self.vehicle})"


class VehicleDocument(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='documents')
    tipo = models.CharField('Tipo', max_length=50)
    numero = models.CharField('Número', max_length=100, blank=True)
    data_emissao = models.DateField('Emissão', null=True, blank=True)
    data_validade = models.DateField('Validade', null=True, blank=True)
    arquivo = models.FileField('Arquivo', upload_to='vehicle_docs/', null=True, blank=True)

    class Meta:
        db_table = 'cadastros_vehicledocument'
        verbose_name = 'Documento do Veículo'
        verbose_name_plural = 'Documentos do Veículo'

    def __str__(self):
        return f"{self.tipo} - {self.vehicle}"


def validity_is_past(validade_date, compare_dt):
    try:
        return validade_date < compare_dt.date() if hasattr(compare_dt, 'date') else validade_date < compare_dt
    except Exception:
        return False


# ==========================
# MOTORISTAS
# ==========================

class Motorista(models.Model):
    """Cadastro de motoristas (próprios, terceirizados ou agregados)"""

    TIPO_CHOICES = [
        ('PROPRIO', 'Próprio'),
        ('TERCEIRO', 'Terceirizado'),
        ('AGREGADO', 'Agregado'),
    ]

    CATEGORIA_CNH_CHOICES = [
        ('A', 'Categoria A'), ('B', 'Categoria B'), ('C', 'Categoria C'),
        ('D', 'Categoria D'), ('E', 'Categoria E'), ('AB', 'Categoria AB'),
        ('AC', 'Categoria AC'), ('AD', 'Categoria AD'), ('AE', 'Categoria AE'),
        ('BC', 'Categoria BC'), ('BD', 'Categoria BD'), ('BE', 'Categoria BE'),
        ('CD', 'Categoria CD'), ('CE', 'Categoria CE'), ('DE', 'Categoria DE'),
    ]

    empresa = models.ForeignKey(
        'empresas.Empresa', on_delete=models.CASCADE, related_name='motoristas', verbose_name='Empresa'
    )
    tipo = models.CharField(
        'Tipo de Motorista', max_length=10, choices=TIPO_CHOICES, default='PROPRIO',
        help_text='Selecione se é motorista próprio ou terceirizado'
    )
    transportadora = models.ForeignKey(
        'cadastros.Transportadora', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='motoristas', verbose_name='Transportadora',
        help_text='Obrigatório para motoristas terceirizados'
    )

    nome = models.CharField('Nome Completo', max_length=200)
    cpf = models.CharField('CPF', max_length=14, unique=True, help_text='Formato: 000.000.000-00')
    data_nascimento = models.DateField('Data de Nascimento', null=True, blank=True)
    foto = models.ImageField(
        'Foto', upload_to='motorista_fotos/', null=True, blank=True,
        help_text='Foto do motorista (opcional, recomendado para motoristas próprios e agregados)'
    )

    cnh = models.CharField('Número CNH', max_length=20, unique=True, help_text='Número da Carteira Nacional de Habilitação')
    categoria_cnh = models.CharField('Categoria CNH', max_length=5, choices=CATEGORIA_CNH_CHOICES, help_text='Categoria da CNH')
    data_emissao_cnh = models.DateField('Data Emissão CNH', null=True, blank=True)
    data_validade_cnh = models.DateField('Data Validade CNH')
    uf_cnh = models.CharField('UF CNH', max_length=2, blank=True, help_text='Estado emissor da CNH')

    telefone = models.CharField('Telefone', max_length=20, blank=True)
    celular = models.CharField('Celular/WhatsApp', max_length=20)
    email = models.EmailField('Email', blank=True)

    cep = models.CharField('CEP', max_length=10, blank=True)
    logradouro = models.CharField('Logradouro', max_length=200, blank=True)
    numero = models.CharField('Número', max_length=10, blank=True)
    complemento = models.CharField('Complemento', max_length=100, blank=True)
    bairro = models.CharField('Bairro', max_length=100, blank=True)
    cidade = models.CharField('Cidade', max_length=100, blank=True)
    uf = models.CharField('UF', max_length=2, blank=True)
    pais = models.CharField('País', max_length=100, default='Brasil')

    ativo = models.BooleanField('Ativo', default=True)
    motivo_inativacao = models.TextField('Motivo da Inativação', blank=True)
    data_inativacao = models.DateField('Data Inativação', null=True, blank=True)

    matricula = models.CharField('Matrícula', max_length=50, blank=True, help_text='Usada como login (username) do motorista no sistema')
    pin = models.CharField(
        'PIN (legado)', max_length=128, blank=True,
        help_text='Legado — pré-migração para login unificado via Usuario. Não usado para autenticação após a migração.'
    )
    usuario_vinculado = models.OneToOneField(
        'usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='motorista_profile', verbose_name='Usuário do Portal',
        help_text='Conta de login (django.contrib.auth) vinculada a este motorista'
    )

    data_criacao = models.DateTimeField('Data de Criação', auto_now_add=True)
    data_atualizacao = models.DateTimeField('Última Atualização', auto_now=True)

    def set_pin(self, raw_pin):
        from django.contrib.auth.hashers import make_password
        self.pin = make_password(str(raw_pin))

    def check_pin(self, raw_pin):
        from django.contrib.auth.hashers import check_password
        if not self.pin:
            return False
        return check_password(str(raw_pin), self.pin)

    class Meta:
        db_table = 'cadastros_motorista'
        verbose_name = 'Motorista'
        verbose_name_plural = 'Motoristas'
        ordering = ['nome']
        indexes = [
            models.Index(fields=['empresa', 'ativo']),
            models.Index(fields=['cpf']),
            models.Index(fields=['cnh']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(tipo__in=['TERCEIRO', 'AGREGADO']) | models.Q(transportadora__isnull=False),
                name='motorista_terceiro_agregado_requer_transportadora'
            ),
            models.UniqueConstraint(
                fields=['empresa', 'matricula'],
                condition=~models.Q(matricula=''),
                name='motorista_empresa_matricula_unique',
            ),
        ]

    def __str__(self):
        return f"{self.nome} ({self.cpf})"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.tipo in ['TERCEIRO', 'AGREGADO'] and not self.transportadora:
            raise ValidationError({
                'transportadora': f'Transportadora é obrigatória para motoristas {self.get_tipo_display().lower()}.'
            })

    @property
    def cnh_vencida(self):
        from django.utils import timezone
        return self.data_validade_cnh < timezone.now().date() if self.data_validade_cnh else False

    @property
    def dias_para_vencer_cnh(self):
        from django.utils import timezone
        if not self.data_validade_cnh:
            return None
        dias = (self.data_validade_cnh - timezone.now().date()).days
        return dias if dias >= 0 else None


class MotoristadoDocumento(models.Model):
    """Documentos adicionais do motorista (exames, certificados, etc)"""

    TIPO_DOCUMENTO_CHOICES = [
        ('EXAME_PSICO', 'Exame Psicotécnico'),
        ('EXAME_MEDICO', 'Exame Médico'),
        ('CERTIFICADO_ETEA', 'Certificado ETEA'),
        ('OUTRO', 'Outro'),
    ]

    motorista = models.ForeignKey(
        'Motorista', on_delete=models.CASCADE, related_name='documentos', verbose_name='Motorista'
    )
    tipo = models.CharField('Tipo de Documento', max_length=20, choices=TIPO_DOCUMENTO_CHOICES)
    numero = models.CharField('Número', max_length=100, blank=True)
    data_emissao = models.DateField('Data Emissão', null=True, blank=True)
    data_validade = models.DateField('Data Validade', null=True, blank=True)
    arquivo = models.FileField('Arquivo', upload_to='motorista_docs/', null=True, blank=True)
    observacoes = models.TextField('Observações', blank=True)
    data_criacao = models.DateTimeField('Data de Criação', auto_now_add=True)

    class Meta:
        db_table = 'cadastros_motoristadadocumento'
        verbose_name = 'Documento do Motorista'
        verbose_name_plural = 'Documentos do Motorista'
        ordering = ['-data_emissao']

    def __str__(self):
        return f"{self.motorista.nome} - {self.get_tipo_display()}"


class MotoristaVinculoPlaca(models.Model):
    """Vinculo de motorista a conjunto de placas por periodo"""

    empresa = models.ForeignKey(
        'empresas.Empresa', on_delete=models.CASCADE,
        related_name='vinculos_motorista_placa', verbose_name='Empresa'
    )
    motorista = models.ForeignKey(
        'Motorista', on_delete=models.CASCADE, related_name='vinculos_placas', verbose_name='Motorista'
    )
    placa_principal = models.ForeignKey(
        'VehiclePlate', on_delete=models.PROTECT, related_name='vinculos_principal', verbose_name='Placa Principal'
    )
    reboques = models.ManyToManyField(
        'VehiclePlate', blank=True, related_name='vinculos_reboque', verbose_name='Placas de Reboque'
    )
    data_inicio = models.DateField('Data Inicio')
    data_fim = models.DateField('Data Fim', null=True, blank=True)
    ativo = models.BooleanField('Ativo', default=True, help_text='Vinculo ativo ou inativo')
    observacoes = models.TextField('Observacoes', blank=True)
    data_cadastro = models.DateTimeField('Data de Cadastro', auto_now_add=True)
    data_atualizacao = models.DateTimeField('Ultima Atualizacao', auto_now=True)

    class Meta:
        db_table = 'cadastros_motoristavinculoplaca'
        verbose_name = 'Vinculo Motorista x Placa'
        verbose_name_plural = 'Vinculos Motorista x Placa'
        ordering = ['-data_inicio']
        indexes = [
            models.Index(fields=['empresa', 'motorista']),
            models.Index(fields=['empresa', 'data_inicio']),
        ]

    def __str__(self):
        return f"{self.motorista} - {self.placa_principal}"

    @property
    def periodo_ativo(self):
        if not self.data_fim:
            return True
        return self.data_fim >= date.today()

    def placas_conjunto(self):
        placas = [self.placa_principal]
        placas.extend(list(self.reboques.all()))
        return placas


# ==========================
# ABASTECIMENTO
# ==========================

class AbastecimentoVeiculo(models.Model):
    """Registro de abastecimentos de combustível por veículo."""

    TIPO_COMBUSTIVEL_CHOICES = [
        ('DIESEL_S10', 'Diesel S10'), ('DIESEL_S500', 'Diesel S500'),
        ('GASOLINA', 'Gasolina'), ('ETANOL', 'Etanol'), ('GNV', 'GNV'), ('OUTRO', 'Outro'),
    ]

    empresa = models.ForeignKey(
        'empresas.Empresa', on_delete=models.CASCADE, related_name='abastecimentos', verbose_name='Empresa'
    )
    vehicle = models.ForeignKey(
        Vehicle, on_delete=models.CASCADE, related_name='abastecimentos', verbose_name='Veículo'
    )
    motorista = models.ForeignKey(
        'Motorista', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='abastecimentos', verbose_name='Motorista'
    )
    data = models.DateField('Data do Abastecimento')
    tipo_combustivel = models.CharField('Tipo de Combustível', max_length=15, choices=TIPO_COMBUSTIVEL_CHOICES)
    litros = models.DecimalField('Litros', max_digits=10, decimal_places=3, validators=[MinValueValidator(Decimal('0.001'))])
    preco_por_litro = models.DecimalField('Preço por Litro (R$)', max_digits=8, decimal_places=3, validators=[MinValueValidator(Decimal('0.001'))])
    valor_total = models.DecimalField('Valor Total (R$)', max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    km_odometro = models.DecimalField('Hodômetro (km)', max_digits=12, decimal_places=1, null=True, blank=True, help_text='Leitura do hodômetro no momento do abastecimento')
    horimetro = models.DecimalField('Horímetro (h)', max_digits=10, decimal_places=1, null=True, blank=True, help_text='Para tratores/máquinas com horímetro')
    tanque_cheio = models.BooleanField('Tanque Cheio?', default=True, help_text='Se falso, o consumo calculado pode ser impreciso')
    local_abastecimento = models.CharField('Local / Posto', max_length=200, blank=True)
    fornecedor = models.ForeignKey(
        'cadastros.Fornecedor', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='abastecimentos', verbose_name='Fornecedor', help_text='Para gerar Conta a Pagar'
    )
    conta_pagar = models.OneToOneField(
        'financeiro.ContaPagar', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='abastecimento', verbose_name='Conta a Pagar gerada'
    )
    observacoes = models.TextField('Observações', blank=True)
    criado_por = models.ForeignKey(
        'usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='abastecimentos_criados'
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cadastros_abastecimentoveiculo'
        verbose_name = 'Abastecimento'
        verbose_name_plural = 'Abastecimentos'
        ordering = ['-data', '-criado_em']
        indexes = [
            models.Index(fields=['empresa', 'vehicle', 'data']),
            models.Index(fields=['empresa', 'data']),
        ]

    def __str__(self):
        return f"{self.vehicle} — {self.litros}L ({self.data})"

    def save(self, *args, **kwargs):
        self.valor_total = (self.litros * self.preco_por_litro).quantize(Decimal('0.01'))
        super().save(*args, **kwargs)

    @property
    def consumo_calculado(self):
        if not self.km_odometro or not self.tanque_cheio:
            return None
        anterior = (
            AbastecimentoVeiculo.objects
            .filter(vehicle=self.vehicle, km_odometro__lt=self.km_odometro, tanque_cheio=True)
            .order_by('-km_odometro')
            .first()
        )
        if not anterior or not anterior.km_odometro:
            return None
        km = self.km_odometro - anterior.km_odometro
        if km <= 0:
            return None
        return (self.litros / km).quantize(Decimal('0.0001'))


# ==========================
# MANUTENÇÃO
# ==========================

class ManutencaoVeiculo(models.Model):
    """Registro de manutenções preventivas e corretivas."""

    TIPO_CHOICES = [
        ('PREVENTIVA', 'Preventiva'), ('CORRETIVA', 'Corretiva'),
        ('PREDITIVA', 'Preditiva'), ('REVISAO', 'Revisão Periódica'),
    ]
    STATUS_CHOICES = [
        ('ABERTA', 'Aberta'), ('EM_ANDAMENTO', 'Em Andamento'),
        ('CONCLUIDA', 'Concluída'), ('CANCELADA', 'Cancelada'),
    ]

    empresa = models.ForeignKey(
        'empresas.Empresa', on_delete=models.CASCADE, related_name='manutencoes', verbose_name='Empresa'
    )
    vehicle = models.ForeignKey(
        Vehicle, on_delete=models.CASCADE, related_name='manutencoes', verbose_name='Veículo'
    )
    tipo = models.CharField('Tipo', max_length=15, choices=TIPO_CHOICES, default='PREVENTIVA')
    status = models.CharField('Status', max_length=15, choices=STATUS_CHOICES, default='ABERTA')
    descricao = models.CharField('Descrição do Serviço', max_length=300)
    data_abertura = models.DateField('Data de Abertura', default=date.today)
    data_conclusao = models.DateField('Data de Conclusão', null=True, blank=True)
    km_odometro = models.DecimalField('Hodômetro (km)', max_digits=12, decimal_places=1, null=True, blank=True)
    horimetro = models.DecimalField('Horímetro (h)', max_digits=10, decimal_places=1, null=True, blank=True)
    proxima_data = models.DateField('Próxima Manutenção (data)', null=True, blank=True)
    proximo_km = models.DecimalField('Próxima Manutenção (km)', max_digits=12, decimal_places=1, null=True, blank=True)
    eh_oficina_propria = models.BooleanField('Oficina Própria?', default=False, help_text='Se sim, gera baixa automática no estoque de peças')
    local_oficina = models.ForeignKey(
        'estoque.Armazem', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='manutencoes', verbose_name='Armazém / Oficina',
        help_text='Oficina própria — peças baixadas deste armazém'
    )
    fornecedor_externo = models.ForeignKey(
        'cadastros.Fornecedor', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='manutencoes_veiculos', verbose_name='Fornecedor Externo'
    )
    valor_servico = models.DecimalField(
        'Valor do Serviço (R$)', max_digits=12, decimal_places=2,
        default=Decimal('0'), validators=[MinValueValidator(Decimal('0'))]
    )
    conta_pagar = models.OneToOneField(
        'financeiro.ContaPagar', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='manutencao', verbose_name='Conta a Pagar gerada'
    )
    motorista_solicitante = models.ForeignKey(
        'Motorista', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='manutencoes_solicitadas', verbose_name='Motorista Solicitante',
        help_text='Preenchido quando a manutenção é solicitada via Portal do Motorista'
    )
    observacoes = models.TextField('Observações', blank=True)
    criado_por = models.ForeignKey(
        'usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='manutencoes_criadas'
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cadastros_manutencaoveiculo'
        verbose_name = 'Manutenção de Veículo'
        verbose_name_plural = 'Manutenções de Veículo'
        ordering = ['-data_abertura']
        indexes = [models.Index(fields=['empresa', 'vehicle', 'status'])]

    def __str__(self):
        return f"{self.vehicle} — {self.descricao} ({self.data_abertura})"

    @property
    def valor_total(self):
        custo_pecas = sum(i.custo_total for i in self.itens.all())
        return (self.valor_servico + custo_pecas).quantize(Decimal('0.01'))

    @property
    def placa_atual(self):
        return self.vehicle.get_current_plate()


class ManutencaoItem(models.Model):
    """Peça ou material usado em uma manutenção."""

    manutencao = models.ForeignKey(
        ManutencaoVeiculo, on_delete=models.CASCADE, related_name='itens', verbose_name='Manutenção'
    )
    descricao = models.CharField('Descrição da Peça/Material', max_length=200)
    lote = models.ForeignKey(
        'estoque.Lote', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='itens_manutencao', verbose_name='Lote em Estoque',
        help_text='Preencher para gerar baixa automática no estoque'
    )
    quantidade = models.DecimalField('Quantidade', max_digits=10, decimal_places=3, validators=[MinValueValidator(Decimal('0.001'))])
    valor_unitario = models.DecimalField('Valor Unitário (R$)', max_digits=12, decimal_places=4, validators=[MinValueValidator(Decimal('0'))])
    desconto = models.DecimalField('Desconto (R$)', max_digits=12, decimal_places=2, default=Decimal('0'), validators=[MinValueValidator(Decimal('0'))])
    nome_produto = models.CharField('Nome do Produto', max_length=200, blank=True, help_text='Preenchido automaticamente pelo lote')
    unidade_medida = models.CharField('Unidade de Medida', max_length=20, blank=True, help_text='Preenchida automaticamente pelo lote')
    valor_custo = models.DecimalField('Valor de Custo (R$)', max_digits=12, decimal_places=4, default=Decimal('0'), validators=[MinValueValidator(Decimal('0'))])

    class Meta:
        db_table = 'cadastros_manutencaoitem'
        verbose_name = 'Item de Manutenção'
        verbose_name_plural = 'Itens de Manutenção'

    def __str__(self):
        return self.descricao

    @property
    def custo_total(self):
        return ((self.quantidade * self.valor_custo) - self.desconto).quantize(Decimal('0.01'))


class DocumentoManutencao(models.Model):
    """Documentos anexados a uma manutenção."""

    TIPO_CHOICES = [
        ('NF_PECA', 'NF de Peças'), ('NF_SERVICO', 'NF de Serviço'),
        ('NF_CONSUMIDOR', 'Nota do Consumidor'), ('ORCAMENTO', 'Orçamento'), ('OUTRO', 'Outro'),
    ]

    manutencao = models.ForeignKey(
        ManutencaoVeiculo, on_delete=models.CASCADE, related_name='documentos', verbose_name='Manutenção'
    )
    tipo = models.CharField('Tipo', max_length=20, choices=TIPO_CHOICES, default='NF_PECA')
    descricao = models.CharField('Descrição', max_length=200, blank=True)
    numero_documento = models.CharField('Número do Documento', max_length=100, blank=True)
    arquivo = models.FileField(
        'Arquivo', upload_to='frota/manutencoes/documentos/%Y/%m/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx'])],
        help_text='PDF, JPG, PNG, DOC (máx. 10MB)'
    )
    enviado_por = models.ForeignKey(
        'usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='documentos_manutencao_enviados'
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cadastros_documentomanutencao'
        verbose_name = 'Documento de Manutenção'
        verbose_name_plural = 'Documentos de Manutenção'
        ordering = ['-criado_em']

    def __str__(self):
        return f"{self.get_tipo_display()} — {self.descricao or os.path.basename(self.arquivo.name) if self.arquivo else ''}"


class AlertaManutencao(models.Model):
    """Alerta gerado automaticamente quando manutenção está próxima do vencimento."""

    TIPO_GATILHO_CHOICES = [
        ('DATA', 'Por Data'), ('KM', 'Por Km/Horímetro'), ('AMBOS', 'Data e Km'),
    ]
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'), ('VISTO', 'Visto'), ('RESOLVIDO', 'Resolvido'),
    ]

    empresa = models.ForeignKey(
        'empresas.Empresa', on_delete=models.CASCADE, related_name='alertas_manutencao'
    )
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='alertas_manutencao')
    manutencao_origem = models.ForeignKey(
        ManutencaoVeiculo, on_delete=models.CASCADE, related_name='alertas', verbose_name='Manutenção de Origem'
    )
    tipo_gatilho = models.CharField('Gatilho', max_length=10, choices=TIPO_GATILHO_CHOICES)
    status = models.CharField('Status', max_length=10, choices=STATUS_CHOICES, default='PENDENTE')
    descricao = models.CharField('Descrição', max_length=300)
    data_alerta = models.DateField('Data do Alerta')
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cadastros_alertamanutencao'
        verbose_name = 'Alerta de Manutenção'
        verbose_name_plural = 'Alertas de Manutenção'
        ordering = ['-data_alerta']

    def __str__(self):
        return f"Alerta: {self.vehicle} — {self.descricao}"


# ==========================
# PEDÁGIOS
# ==========================

class PedagioVeiculo(models.Model):
    """Registro de passagens em pedágios por viagem."""

    empresa = models.ForeignKey(
        'empresas.Empresa', on_delete=models.CASCADE, related_name='pedagios', verbose_name='Empresa'
    )
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='pedagios', verbose_name='Veículo')
    viagem = models.ForeignKey(
        'cadastros.Viagem', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='pedagios', verbose_name='Viagem'
    )
    motorista = models.ForeignKey(
        'Motorista', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='pedagios', verbose_name='Motorista'
    )
    data = models.DateField('Data')
    praca = models.CharField('Praça / Local', max_length=200, blank=True)
    valor = models.DecimalField('Valor (R$)', max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    conta_pagar = models.OneToOneField(
        'financeiro.ContaPagar', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='pedagio', verbose_name='Conta a Pagar gerada'
    )
    observacoes = models.TextField('Observações', blank=True)
    criado_por = models.ForeignKey(
        'usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='pedagios_criados'
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cadastros_pedagogioveiculo'
        verbose_name = 'Pedágio'
        verbose_name_plural = 'Pedágios'
        ordering = ['-data', '-criado_em']
        indexes = [
            models.Index(fields=['empresa', 'vehicle', 'data']),
            models.Index(fields=['empresa', 'viagem']),
        ]

    def __str__(self):
        return f"{self.vehicle} — R$ {self.valor} ({self.data})"


# ==========================
# TELEMETRIA
# ==========================

class TelemetriaVeiculo(models.Model):
    """Registro de posição/telemetria — entrada manual ou via GPS."""

    FONTE_CHOICES = [
        ('MANUAL', 'Manual'), ('GPS', 'GPS Automático'), ('APP', 'App Mobile'),
    ]

    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='telemetrias')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='telemetrias')
    motorista = models.ForeignKey(
        'Motorista', on_delete=models.SET_NULL, null=True, blank=True, related_name='telemetrias'
    )
    viagem = models.ForeignKey(
        'cadastros.Viagem', on_delete=models.SET_NULL, null=True, blank=True, related_name='telemetrias'
    )
    data_hora = models.DateTimeField('Data/Hora')
    latitude = models.DecimalField('Latitude', max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField('Longitude', max_digits=10, decimal_places=7, null=True, blank=True)
    local_descricao = models.CharField('Local (descrição)', max_length=300, blank=True, help_text='Ex: "Posto BR km 45 — SP-270"')
    velocidade_kmh = models.DecimalField('Velocidade (km/h)', max_digits=6, decimal_places=1, null=True, blank=True)
    km_odometro = models.DecimalField('Hodômetro (km)', max_digits=12, decimal_places=1, null=True, blank=True)
    fonte = models.CharField('Fonte', max_length=10, choices=FONTE_CHOICES, default='MANUAL')
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cadastros_telemetriaveiculo'
        verbose_name = 'Registro de Telemetria'
        verbose_name_plural = 'Registros de Telemetria'
        ordering = ['-data_hora']
        indexes = [models.Index(fields=['empresa', 'vehicle', 'data_hora'])]

    def __str__(self):
        return f"{self.vehicle} — {self.data_hora:%d/%m/%Y %H:%M}"


# ==========================
# PORTAL DO MOTORISTA
# ==========================

class FotoAbastecimento(models.Model):
    """Fotos enviadas pelo motorista via Portal do Motorista."""

    abastecimento = models.OneToOneField(
        AbastecimentoVeiculo, on_delete=models.CASCADE, related_name='foto', verbose_name='Abastecimento'
    )
    foto_bomba = models.ImageField(
        'Foto da Bomba', upload_to='frota/fotos/bomba/',
        help_text='Foto do display da bomba com litros e valor'
    )
    foto_odometro = models.ImageField(
        'Foto do Hodômetro/Horímetro', upload_to='frota/fotos/odometro/',
        blank=True, help_text='Foto do painel mostrando odômetro ou horímetro'
    )
    enviada_por = models.ForeignKey(
        'Motorista', on_delete=models.SET_NULL, null=True,
        related_name='fotos_abastecimento', verbose_name='Motorista'
    )
    data_envio = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cadastros_fotoabastecimento'
        verbose_name = 'Foto de Abastecimento'
        verbose_name_plural = 'Fotos de Abastecimentos'

    def __str__(self):
        return f"Fotos — {self.abastecimento}"
