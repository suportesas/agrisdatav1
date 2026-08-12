"""
Recursos Humanos — Funcionários, Contratos, Férias, Afastamentos, ASO, Rescisões
"""
from django.db import models
from django.core.validators import MinValueValidator, FileExtensionValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings
from decimal import Decimal
from calendar import monthrange
from datetime import date, timedelta
import os


# ============================================================================
# HISTÓRICO DO FUNCIONÁRIO
# ============================================================================

class HistoricoFuncionario(models.Model):
    """Histórico de recontratações, promoções, mudanças de salário, suspensões."""

    TIPO_EVENTO = [
        ("RECONTRATACAO", "Recontratação"),
        ("PROMOCAO", "Promoção"),
        ("MUDANCA_SALARIO", "Mudança de Salário"),
        ("SUSPENSAO", "Suspensão"),
        ("OUTRO", "Outro"),
    ]

    funcionario = models.ForeignKey(
        'Funcionario',
        on_delete=models.CASCADE,
        related_name='historicos',
        verbose_name='Funcionário'
    )
    data_evento = models.DateField('Data do Evento', auto_now_add=True)
    tipo_evento = models.CharField('Tipo de Evento', max_length=30, choices=TIPO_EVENTO)
    funcao = models.ForeignKey(
        'FuncaoFuncionario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Função/Cargo'
    )
    salario = models.DecimalField('Salário (R$)', max_digits=10, decimal_places=2, null=True, blank=True)
    motivo = models.TextField('Motivo/Observação', blank=True)
    usuario = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Usuário Responsável'
    )

    class Meta:
        db_table = 'cadastros_historicofuncionario'
        verbose_name = 'Histórico do Funcionário'
        verbose_name_plural = 'Históricos dos Funcionários'
        ordering = ['-data_evento']

    def __str__(self):
        return f"{self.funcionario.nome_completo} - {self.get_tipo_evento_display()} ({self.data_evento})"


# ============================================================================
# FUNÇÃO / CARGO
# ============================================================================

class FuncaoFuncionario(models.Model):
    """Funções/Cargos dos funcionários. Ex: Tratorista, Colhedor, Supervisor."""

    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='funcoes_funcionarios',
        verbose_name='Empresa'
    )

    nome = models.CharField('Nome da Função', max_length=100, help_text='Ex: Tratorista, Colhedor, Supervisor')
    descricao = models.TextField('Descrição', blank=True, help_text='Descrição das atividades da função')

    salario_base = models.DecimalField(
        'Salário Base (R$)', max_digits=10, decimal_places=2, blank=True, null=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Salário base sugerido para a função'
    )

    ativa = models.BooleanField('Função Ativa', default=True)

    GRAU_INSALUBRIDADE = [
        ('10', 'Mínimo (10%)'),
        ('20', 'Médio (20%)'),
        ('40', 'Máximo (40%)'),
    ]

    possui_insalubridade = models.BooleanField('Possui Insalubridade?', default=False)
    grau_insalubridade = models.CharField(
        'Grau de Insalubridade', max_length=2, choices=GRAU_INSALUBRIDADE, blank=True,
        help_text='Grau conforme NR-15 (preencher apenas se houver insalubridade)'
    )

    possui_periculosidade = models.BooleanField('Possui Periculosidade?', default=False)
    percentual_periculosidade = models.DecimalField(
        'Percentual de Periculosidade (%)', max_digits=5, decimal_places=2, default=30,
        help_text='Percentual padrão conforme NR-16 é 30%'
    )

    requer_laudo = models.BooleanField('Requer Laudo Técnico (PPRA/LTCAT)?', default=False)
    validade_laudo = models.DateField('Validade do Laudo', null=True, blank=True, help_text='Data de vencimento do laudo técnico')
    observacoes_risco = models.TextField('Observações sobre Riscos', blank=True, help_text='EPI necessários, agentes de risco, etc.')

    data_criacao = models.DateTimeField('Data de Criação', auto_now_add=True)

    class Meta:
        db_table = 'cadastros_funcaofuncionario'
        verbose_name = 'Função de Funcionário'
        verbose_name_plural = 'Funções de Funcionários'
        ordering = ['nome']
        constraints = [
            models.UniqueConstraint(fields=['empresa', 'nome'], name='unique_funcao_por_empresa')
        ]

    def __str__(self):
        return self.nome

    def get_total_funcionarios(self):
        return self.funcionarios.filter(ativo=True).count()


# ============================================================================
# RISCOS AMBIENTAIS
# ============================================================================

class CategoriaRiscoAmbiental(models.Model):
    """Categorias ambientais de risco por empresa."""

    CODIGO_FISICO = 'FISICO'
    CODIGO_QUIMICO = 'QUIMICO'
    CODIGO_BIOLOGICO = 'BIOLOGICO'
    CODIGO_ERGONOMICO = 'ERGONOMICO'
    CODIGO_ACIDENTES = 'ACIDENTES'
    CODIGO_OUTROS = 'OUTROS'

    CODIGOS_PADRAO = [
        (CODIGO_FISICO, 'Físico'),
        (CODIGO_QUIMICO, 'Químico'),
        (CODIGO_BIOLOGICO, 'Biológico'),
        (CODIGO_ERGONOMICO, 'Ergonômico'),
        (CODIGO_ACIDENTES, 'Acidentes'),
        (CODIGO_OUTROS, 'Outros'),
    ]

    empresa = models.ForeignKey(
        'empresas.Empresa', on_delete=models.CASCADE,
        related_name='categorias_risco_ambiental', verbose_name='Empresa'
    )
    codigo = models.CharField('Código', max_length=20, help_text='Código interno da categoria.')
    nome = models.CharField('Nome da Categoria', max_length=80)
    descricao = models.TextField('Descrição', blank=True)
    ativo = models.BooleanField('Ativa', default=True)
    eh_padrao_sistema = models.BooleanField('Categoria Padrão do Sistema', default=False)
    data_criacao = models.DateTimeField('Data de Criação', auto_now_add=True)
    data_atualizacao = models.DateTimeField('Última Atualização', auto_now=True)

    class Meta:
        db_table = 'cadastros_categoriariscoambiental'
        verbose_name = 'Categoria de Risco Ambiental'
        verbose_name_plural = 'Categorias de Risco Ambiental'
        ordering = ['nome']
        constraints = [
            models.UniqueConstraint(fields=['empresa', 'codigo'], name='unique_categoria_risco_codigo_empresa'),
            models.UniqueConstraint(fields=['empresa', 'nome'], name='unique_categoria_risco_nome_empresa'),
        ]

    def __str__(self):
        return f'{self.nome} ({self.empresa.nome})'

    @classmethod
    def criar_categorias_padrao_empresa(cls, empresa):
        categorias = []
        for codigo, nome in cls.CODIGOS_PADRAO:
            categoria, _ = cls.objects.get_or_create(
                empresa=empresa,
                codigo=codigo,
                defaults={'nome': nome, 'eh_padrao_sistema': True, 'ativo': True}
            )
            categorias.append(categoria)
        return categorias


class RiscoAmbientalFuncao(models.Model):
    """Riscos ambientais cadastrados para uma função/cargo."""

    INTENSIDADE_BAIXA = 'BAIXA'
    INTENSIDADE_MEDIA = 'MEDIA'
    INTENSIDADE_ALTA = 'ALTA'
    INTENSIDADES = [
        (INTENSIDADE_BAIXA, 'Baixa'),
        (INTENSIDADE_MEDIA, 'Média'),
        (INTENSIDADE_ALTA, 'Alta'),
    ]

    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='riscos_ambientais_funcao', verbose_name='Empresa')
    funcao = models.ForeignKey(FuncaoFuncionario, on_delete=models.PROTECT, related_name='riscos_ambientais', verbose_name='Função/Cargo')
    categoria = models.ForeignKey(CategoriaRiscoAmbiental, on_delete=models.PROTECT, related_name='riscos_funcao', verbose_name='Categoria de Risco')
    agente_especifico = models.CharField('Agente Específico', max_length=200, help_text='Ex.: Ruído acima de 85dB, Poeira orgânica.')
    intensidade = models.CharField('Intensidade', max_length=10, choices=INTENSIDADES, default=INTENSIDADE_MEDIA)
    epi_obrigatorio = models.CharField('EPI Obrigatório', max_length=255, blank=True)
    observacoes = models.TextField('Observações', blank=True)
    ativo = models.BooleanField('Ativo', default=True)
    data_criacao = models.DateTimeField('Data de Criação', auto_now_add=True)
    data_atualizacao = models.DateTimeField('Última Atualização', auto_now=True)

    class Meta:
        db_table = 'cadastros_riscoambientalfuncao'
        verbose_name = 'Risco Ambiental da Função'
        verbose_name_plural = 'Riscos Ambientais da Função'
        ordering = ['categoria__nome', 'agente_especifico']
        constraints = [
            models.UniqueConstraint(fields=['funcao', 'categoria', 'agente_especifico'], name='unique_risco_ambiental_funcao_categoria_agente'),
        ]
        indexes = [
            models.Index(fields=['empresa', 'ativo']),
            models.Index(fields=['funcao']),
            models.Index(fields=['categoria']),
        ]

    def __str__(self):
        return f'{self.funcao.nome} - {self.categoria.nome}: {self.agente_especifico}'

    def clean(self):
        errors = {}
        if self.funcao_id and self.categoria_id and self.funcao.empresa_id != self.categoria.empresa_id:
            errors['categoria'] = 'A categoria selecionada não pertence à mesma empresa da função.'
        if self.empresa_id and self.funcao_id and self.empresa_id != self.funcao.empresa_id:
            errors['empresa'] = 'A empresa do risco deve ser a mesma empresa da função.'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.funcao_id and not self.empresa_id:
            self.empresa_id = self.funcao.empresa_id
        super().save(*args, **kwargs)


class RiscoAmbientalCatalogo(models.Model):
    """Catálogo de agentes de risco reutilizáveis por empresa/categoria."""

    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='riscos_ambientais_catalogo', verbose_name='Empresa')
    categoria = models.ForeignKey(CategoriaRiscoAmbiental, on_delete=models.PROTECT, related_name='itens_catalogo', verbose_name='Categoria de Risco')
    nome = models.CharField('Agente/Item de Risco', max_length=200)
    intensidade_padrao = models.CharField('Intensidade Padrão', max_length=10, choices=RiscoAmbientalFuncao.INTENSIDADES, default=RiscoAmbientalFuncao.INTENSIDADE_MEDIA)
    epi_padrao = models.CharField('EPI Padrão', max_length=255, blank=True)
    observacoes = models.TextField('Observações', blank=True)
    ativo = models.BooleanField('Ativo', default=True)
    data_criacao = models.DateTimeField('Data de Criação', auto_now_add=True)
    data_atualizacao = models.DateTimeField('Última Atualização', auto_now=True)

    class Meta:
        db_table = 'cadastros_riscoambientalcatalogo'
        verbose_name = 'Item de Catálogo de Risco Ambiental'
        verbose_name_plural = 'Itens de Catálogo de Risco Ambiental'
        ordering = ['categoria__nome', 'nome']
        constraints = [
            models.UniqueConstraint(fields=['empresa', 'categoria', 'nome'], name='unique_catalogo_risco_empresa_categoria_nome'),
        ]
        indexes = [
            models.Index(fields=['empresa', 'ativo']),
            models.Index(fields=['categoria']),
        ]

    def __str__(self):
        return f'{self.categoria.nome}: {self.nome}'

    def clean(self):
        errors = {}
        if self.empresa_id and self.categoria_id and self.empresa_id != self.categoria.empresa_id:
            errors['categoria'] = 'A categoria selecionada não pertence à mesma empresa do catálogo.'
        if errors:
            raise ValidationError(errors)


# ============================================================================
# VÍNCULO CONTRATUAL
# ============================================================================

class VinculoContrato(models.Model):
    """Vínculo contratual de um funcionário. Cada contratação/recontratação = novo vínculo."""

    TIPO_CONTRATO = [
        ('CLT', 'CLT'),
        ('TEMPORARIO', 'Temporário'),
        ('DIARISTA', 'Diarista'),
        ('AUTONOMO', 'Autônomo'),
        ('TERCEIRIZADO', 'Terceirizado'),
    ]

    STATUS_VINCULO = [
        ('PROGRAMADO', 'Programado'),
        ('ATIVO', 'Ativo'),
        ('ENCERRADO', 'Encerrado'),
        ('CANCELADO', 'Cancelado'),
    ]

    ORIGEM_CONTRATACAO = [
        ('NOVO', 'Nova Contratação'),
        ('RECONTRATACAO', 'Recontratação'),
        ('EFETIVACAO', 'Efetivação (Temporário → CLT)'),
    ]

    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='vinculos_contratos', verbose_name='Empresa')
    funcionario = models.ForeignKey('Funcionario', on_delete=models.CASCADE, related_name='vinculos', verbose_name='Funcionário')
    funcao = models.ForeignKey(FuncaoFuncionario, on_delete=models.SET_NULL, null=True, blank=True, related_name='vinculos', verbose_name='Função/Cargo')

    matricula = models.CharField('Matrícula do Vínculo', max_length=20, blank=True)
    tipo_contrato = models.CharField('Tipo de Contrato', max_length=20, choices=TIPO_CONTRATO, default='CLT')
    origem = models.CharField('Origem da Contratação', max_length=20, choices=ORIGEM_CONTRATACAO, default='NOVO')
    status = models.CharField('Status do Vínculo', max_length=20, choices=STATUS_VINCULO, default='ATIVO')

    data_inicio = models.DateField('Data de Início')
    data_fim_prevista = models.DateField('Data Fim Prevista', null=True, blank=True)
    data_fim_real = models.DateField('Data Fim Real', null=True, blank=True)

    periodo_experiencia = models.BooleanField('Possui Período de Experiência?', default=False)
    data_fim_experiencia = models.DateField('Fim do Período de Experiência', null=True, blank=True)

    salario = models.DecimalField('Salário (R$)', max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('0.00'))])

    possui_insalubridade = models.BooleanField('Insalubridade Aplicada?', default=False)
    grau_insalubridade = models.CharField('Grau de Insalubridade', max_length=2, blank=True)
    possui_periculosidade = models.BooleanField('Periculosidade Aplicada?', default=False)
    percentual_periculosidade = models.DecimalField('Percentual Periculosidade (%)', max_digits=5, decimal_places=2, default=30)

    cadastrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='vinculos_criados', verbose_name='Cadastrado por')
    observacoes = models.TextField('Observações', blank=True)
    data_criacao = models.DateTimeField('Data de Criação', auto_now_add=True)
    data_atualizacao = models.DateTimeField('Última Atualização', auto_now=True)

    class Meta:
        db_table = 'cadastros_vinculocontrato'
        verbose_name = 'Vínculo Contratual'
        verbose_name_plural = 'Vínculos Contratuais'
        ordering = ['-data_inicio']

    def __str__(self):
        return f'{self.funcionario} — {self.get_tipo_contrato_display()} ({self.data_inicio})'

    def clean(self):
        errors = {}
        if self.data_fim_prevista and self.data_inicio and self.data_fim_prevista < self.data_inicio:
            errors['data_fim_prevista'] = 'A data fim prevista não pode ser anterior à data de início.'
        if self.periodo_experiencia and not self.data_fim_experiencia:
            errors['data_fim_experiencia'] = 'Informe a data final do período de experiência.'
        if self.data_fim_experiencia and self.data_inicio and self.data_fim_experiencia < self.data_inicio:
            errors['data_fim_experiencia'] = 'A data do período de experiência não pode ser anterior ao início do vínculo.'
        if self.data_fim_experiencia and self.data_fim_prevista and self.data_fim_experiencia > self.data_fim_prevista:
            errors['data_fim_experiencia'] = 'O fim da experiência não pode ultrapassar o fim previsto do contrato.'
        if self.tipo_contrato == 'TEMPORARIO' and not self.data_fim_prevista:
            errors['data_fim_prevista'] = 'Contratos temporários devem ter data fim prevista.'
        if self.possui_insalubridade and not self.grau_insalubridade:
            errors['grau_insalubridade'] = 'Informe o grau de insalubridade aplicado ao vínculo.'
        if self.possui_periculosidade and self.percentual_periculosidade <= 0:
            errors['percentual_periculosidade'] = 'Informe um percentual de periculosidade maior que zero.'
        if self.status == 'ENCERRADO' and not self.data_fim_real:
            errors['data_fim_real'] = 'Informe a data fim real para vínculos encerrados.'
        if self.status in {'ATIVO', 'PROGRAMADO'} and self.data_fim_real:
            errors['data_fim_real'] = 'Vínculos ativos ou programados não podem ter data fim real preenchida.'
        if errors:
            raise ValidationError(errors)

    def encerrar(self, data_fim):
        self.data_fim_real = data_fim
        self.status = 'ENCERRADO'
        self.save(update_fields=['data_fim_real', 'status', 'data_atualizacao'])


# ============================================================================
# FUNCIONÁRIO
# ============================================================================

class Funcionario(models.Model):
    def get_qtd_suspensoes(self):
        return self.afastamentos.filter(tipo_afastamento='SUSPENSAO').count() + self.historicos.filter(tipo_evento='SUSPENSAO').count()

    TIPO_CONTRATO = [
        ('CLT', 'CLT'), ('TEMPORARIO', 'Temporário'), ('DIARISTA', 'Diarista'),
        ('AUTONOMO', 'Autônomo'), ('TERCEIRIZADO', 'Terceirizado'),
    ]

    ESTADO_CIVIL = [
        ('SOLTEIRO', 'Solteiro(a)'), ('CASADO', 'Casado(a)'), ('DIVORCIADO', 'Divorciado(a)'),
        ('VIUVO', 'Viúvo(a)'), ('UNIAO_ESTAVEL', 'União Estável'),
    ]

    GENERO = [('M', 'Masculino'), ('F', 'Feminino'), ('OUTRO', 'Outro')]

    ESCOLARIDADE = [
        ('ANALFABETO', 'Analfabeto'), ('FUNDAMENTAL_INCOMPLETO', 'Fundamental Incompleto'),
        ('FUNDAMENTAL_COMPLETO', 'Fundamental Completo'), ('MEDIO_INCOMPLETO', 'Ensino Médio Incompleto'),
        ('MEDIO_COMPLETO', 'Ensino Médio Completo'), ('TECNICO', 'Ensino Técnico'),
        ('SUPERIOR_INCOMPLETO', 'Superior Incompleto'), ('SUPERIOR_COMPLETO', 'Superior Completo'),
        ('POS_GRADUACAO', 'Pós-Graduação'),
    ]

    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='funcionarios', verbose_name='Empresa')
    fazenda = models.ForeignKey('cadastros.Fazenda', on_delete=models.SET_NULL, null=True, blank=True, related_name='funcionarios', verbose_name='Fazenda')

    nome_completo = models.CharField('Nome Completo', max_length=200)
    matricula = models.CharField('Código da Matrícula', max_length=30, blank=True, null=True)
    cpf = models.CharField('CPF', max_length=14, unique=True, help_text='Formato: 000.000.000-00')
    rg = models.CharField('RG', max_length=20, blank=True)
    data_nascimento = models.DateField('Data de Nascimento', blank=True, null=True)
    genero = models.CharField('Gênero', max_length=10, choices=GENERO, blank=True)
    estado_civil = models.CharField('Estado Civil', max_length=20, choices=ESTADO_CIVIL, blank=True)

    telefone = models.CharField('Telefone', max_length=20, blank=True)
    celular = models.CharField('Celular', max_length=20, blank=True)
    email = models.EmailField('E-mail', blank=True)

    cep = models.CharField('CEP', max_length=9, blank=True)
    endereco = models.CharField('Endereço', max_length=200, blank=True)
    numero = models.CharField('Número', max_length=10, blank=True)
    complemento = models.CharField('Complemento', max_length=100, blank=True)
    bairro = models.CharField('Bairro', max_length=100, blank=True)
    cidade = models.CharField('Cidade', max_length=100, blank=True)
    uf = models.CharField('UF', max_length=2, blank=True)

    funcao = models.ForeignKey(FuncaoFuncionario, on_delete=models.PROTECT, related_name='funcionarios', verbose_name='Função/Cargo')
    tipo_contrato = models.CharField('Tipo de Contrato', max_length=20, choices=TIPO_CONTRATO, default='CLT')
    data_admissao = models.DateField('Data de Admissão', blank=True, null=True)
    data_demissao = models.DateField('Data de Demissão', blank=True, null=True)
    salario = models.DecimalField('Salário (R$)', max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])

    ctps = models.CharField('CTPS', max_length=20, blank=True)
    pis = models.CharField('PIS/PASEP', max_length=20, blank=True)
    cnh = models.CharField('CNH', max_length=20, blank=True)
    cnh_validade = models.DateField('Validade CNH', null=True, blank=True)
    escolaridade = models.CharField('Escolaridade', max_length=30, choices=ESCOLARIDADE, blank=True)
    numero_crea = models.CharField('Número CREA', max_length=50, blank=True)

    banco = models.CharField('Banco', max_length=100, blank=True)
    agencia = models.CharField('Agência', max_length=10, blank=True)
    conta = models.CharField('Conta', max_length=20, blank=True)
    pix_habilitado = models.BooleanField('PIX Habilitado', default=False)
    TIPO_PIX = [
        ('CPF', 'CPF'), ('CNPJ', 'CNPJ'), ('EMAIL', 'E-mail'),
        ('TELEFONE', 'Telefone'), ('CHAVE_ALEATORIA', 'Chave Aleatória')
    ]
    tipo_chave_pix = models.CharField('Tipo de Chave PIX', max_length=20, choices=TIPO_PIX, blank=True)
    chave_pix = models.CharField('Chave PIX', max_length=100, blank=True)
    TIPO_CONTA = [
        ('CORRENTE', 'Conta Corrente'), ('POUPANCA', 'Conta Poupança'), ('SALARIO', 'Conta Salário'),
    ]
    tipo_conta = models.CharField('Tipo de Conta', max_length=20, choices=TIPO_CONTA, blank=True)

    contato_emergencia_nome = models.CharField('Nome Contato Emergência', max_length=200, blank=True)
    contato_emergencia_telefone = models.CharField('Telefone Emergência', max_length=20, blank=True)
    contato_emergencia_parentesco = models.CharField('Parentesco', max_length=50, blank=True)

    observacoes = models.TextField('Observações', blank=True)
    foto = models.ImageField('Foto', upload_to='funcionarios/fotos/%Y/%m/', blank=True, null=True)
    ativo = models.BooleanField('Funcionário Ativo', default=True)

    pin_portal = models.CharField(
        'PIN (legado)', max_length=128, blank=True,
        help_text='Hash pré-migração para login unificado via Usuario. Não usado para autenticação após a migração.'
    )
    portal_ativo = models.BooleanField('Acesso ao Portal do Campo', default=False)
    usuario_vinculado = models.OneToOneField(
        'usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='funcionario_profile', verbose_name='Usuário do Portal do Campo',
        help_text='Conta de login unificado (via /login/) para acesso ao Portal do Campo'
    )

    data_cadastro = models.DateTimeField('Data de Cadastro', auto_now_add=True)
    cadastrado_por = models.ForeignKey('usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True, related_name='funcionarios_cadastrados', verbose_name='Cadastrado por')

    class Meta:
        db_table = 'cadastros_funcionario'
        verbose_name = 'Funcionário'
        verbose_name_plural = 'Funcionários'
        ordering = ['nome_completo']
        indexes = [
            models.Index(fields=['empresa', 'ativo']),
            models.Index(fields=['cpf']),
            models.Index(fields=['empresa', 'matricula']),
            models.Index(fields=['fazenda']),
        ]

    def __str__(self):
        return f"{self.nome_completo} - {self.funcao}"

    def set_pin(self, raw_pin):
        from django.contrib.auth.hashers import make_password
        self.pin_portal = make_password(str(raw_pin))

    def check_pin(self, raw_pin):
        from django.contrib.auth.hashers import check_password
        if not self.pin_portal:
            return False
        return check_password(str(raw_pin), self.pin_portal)

    def get_cpf_formatado(self):
        import re
        cpf = re.sub(r'\D', '', self.cpf)
        if len(cpf) == 11:
            return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
        return self.cpf

    def get_idade(self):
        if self.data_nascimento:
            from datetime import date
            hoje = date.today()
            idade = hoje.year - self.data_nascimento.year
            if (hoje.month, hoje.day) < (self.data_nascimento.month, self.data_nascimento.day):
                idade -= 1
            return idade
        return None

    def get_tempo_servico(self):
        from datetime import date
        if self.data_admissao:
            data_final = self.data_demissao or date.today()
            dias = (data_final - self.data_admissao).days
            anos = dias // 365
            meses = (dias % 365) // 30
            return f"{anos} ano(s) e {meses} mês(es)"
        return None

    def clean(self):
        from django.core.exceptions import ValidationError
        import re
        cpf_limpo = re.sub(r'\D', '', self.cpf)
        if len(cpf_limpo) != 11:
            raise ValidationError({'cpf': 'CPF deve ter 11 dígitos'})
        if self.data_demissao and self.data_admissao:
            if self.data_demissao < self.data_admissao:
                raise ValidationError({'data_demissao': 'Data de demissão não pode ser anterior à admissão'})


# ============================================================================
# DOCUMENTOS DO FUNCIONÁRIO
# ============================================================================

class DocumentoFuncionario(models.Model):
    """Documentos anexados ao funcionário (contratação, certificados, CREA, etc.)"""

    TIPO_DOCUMENTO = [
        ('CONTRATACAO', 'Contratação'), ('RESCISAO', 'Rescisão'), ('CREA', 'Registro CREA'),
        ('CERTIFICADO', 'Certificado/Treinamento'), ('DIPLOMA', 'Diploma/Formação'), ('CNH', 'CNH'),
        ('CTPS', 'CTPS'), ('COMPROVANTE_ENDERECO', 'Comprovante de Endereço'),
        ('COMPROVANTE_BANCARIO', 'Comprovante Bancário'),
        ('DECLARACAO_IMPOSTO_RENDA', 'Declaração de Imposto de Renda'),
        ('CONTRATO_EMERGENCIA', 'Contato de Emergência'), ('ASSINATURA', 'Termo de Assinatura'),
        ('OUTROS', 'Outros'),
    ]

    funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, related_name='documentos', verbose_name='Funcionário')
    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='documentos_funcionario', verbose_name='Empresa')
    tipo = models.CharField('Tipo de Documento', max_length=30, choices=TIPO_DOCUMENTO)
    titulo = models.CharField('Título/Descrição', max_length=200)
    numero_documento = models.CharField('Número do Documento', max_length=100, blank=True)
    arquivo = models.FileField(
        'Arquivo', upload_to='funcionarios/documentos/%Y/%m/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx', 'xls', 'xlsx'])]
    )

    data_emissao = models.DateField('Data de Emissão', blank=True, null=True)
    data_validade = models.DateField('Data de Validade', blank=True, null=True)
    gerar_alerta_vencimento = models.BooleanField('Gerar Alerta de Vencimento', default=True)
    dias_antecedencia_alerta = models.IntegerField('Dias de Antecedência para Alerta', default=30)

    observacoes = models.TextField('Observações', blank=True)
    data_upload = models.DateTimeField('Data do Upload', auto_now_add=True)
    enviado_por = models.ForeignKey('usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True, related_name='documentos_funcionario_enviados', verbose_name='Enviado por')

    class Meta:
        db_table = 'cadastros_documentofuncionario'
        verbose_name = 'Documento do Funcionário'
        verbose_name_plural = 'Documentos dos Funcionários'
        ordering = ['-data_upload']
        indexes = [
            models.Index(fields=['funcionario', '-data_upload']),
            models.Index(fields=['empresa', 'tipo']),
        ]

    def __str__(self):
        return f"{self.funcionario.nome_completo} - {self.get_tipo_display()}: {self.titulo}"

    def esta_vencido(self):
        if self.data_validade:
            return timezone.now().date() > self.data_validade
        return False

    def dias_para_vencimento(self):
        if self.data_validade:
            return (self.data_validade - timezone.now().date()).days
        return None

    def precisa_alerta(self):
        if not self.gerar_alerta_vencimento or not self.data_validade:
            return False
        dias_restantes = self.dias_para_vencimento()
        if dias_restantes is not None:
            return 0 <= dias_restantes <= self.dias_antecedencia_alerta
        return False

    def get_nome_arquivo(self):
        return os.path.basename(self.arquivo.name)


# ============================================================================
# CONTROLE DE RH — FÉRIAS, AFASTAMENTOS E RESCISÕES
# ============================================================================

class FeriasFuncionario(models.Model):
    """Controle de férias dos funcionários"""

    STATUS_FERIAS = [
        ('AGENDADA', 'Agendada'), ('EM_GOZO', 'Em Gozo'),
        ('CONCLUIDA', 'Concluída'), ('CANCELADA', 'Cancelada'),
    ]

    TIPO_FERIAS = [
        ('INTEGRAL', 'Férias Integrais (30 dias)'),
        ('FRACIONADA', 'Férias Fracionadas'),
        ('COLETIVA', 'Férias Coletivas'),
    ]

    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='ferias_funcionarios', verbose_name='Empresa')
    funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, related_name='ferias', verbose_name='Funcionário')

    periodo_aquisitivo_inicio = models.DateField('Início do Período Aquisitivo')
    periodo_aquisitivo_fim = models.DateField('Fim do Período Aquisitivo')
    data_inicio = models.DateField('Data de Início das Férias')
    data_fim = models.DateField('Data de Fim das Férias')
    dias_ferias = models.PositiveIntegerField('Quantidade de Dias', default=30)
    tipo_ferias = models.CharField('Tipo de Férias', max_length=20, choices=TIPO_FERIAS, default='INTEGRAL')

    abono_pecuniario = models.BooleanField('Abono Pecuniário (Venda de 10 dias)', default=False)
    dias_abono = models.PositiveIntegerField('Dias de Abono', default=0)

    valor_ferias = models.DecimalField('Valor das Férias (R$)', max_digits=10, decimal_places=2, default=0)
    valor_abono = models.DecimalField('Valor do Abono (R$)', max_digits=10, decimal_places=2, default=0)

    status = models.CharField('Status', max_length=20, choices=STATUS_FERIAS, default='AGENDADA')
    data_pagamento = models.DateField('Data de Pagamento', null=True, blank=True)
    observacoes = models.TextField('Observações', blank=True)
    recibo_ferias = models.FileField('Recibo de Férias', upload_to='rh/ferias/%Y/%m/', null=True, blank=True)

    cadastrado_por = models.ForeignKey('usuarios.Usuario', on_delete=models.SET_NULL, null=True, related_name='ferias_cadastradas', verbose_name='Cadastrado por')
    data_cadastro = models.DateTimeField('Data de Cadastro', auto_now_add=True)
    data_atualizacao = models.DateTimeField('Última Atualização', auto_now=True)

    class Meta:
        db_table = 'cadastros_feriasfuncionario'
        verbose_name = 'Férias de Funcionário'
        verbose_name_plural = 'Férias de Funcionários'
        ordering = ['-data_inicio']
        indexes = [
            models.Index(fields=['empresa', 'status']),
            models.Index(fields=['funcionario', 'status']),
            models.Index(fields=['data_inicio', 'data_fim']),
        ]

    def __str__(self):
        return f"{self.funcionario.nome_completo} - {self.data_inicio} a {self.data_fim}"

    def get_dias_corridos(self):
        return (self.data_fim - self.data_inicio).days + 1

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.data_fim < self.data_inicio:
            raise ValidationError({'data_fim': 'Data de fim não pode ser anterior à data de início'})
        if self.dias_ferias > 30:
            raise ValidationError({'dias_ferias': 'Máximo de 30 dias de férias'})
        if self.abono_pecuniario and self.dias_abono > 10:
            raise ValidationError({'dias_abono': 'Máximo de 10 dias de abono pecuniário'})
        if self.periodo_aquisitivo_fim < self.periodo_aquisitivo_inicio:
            raise ValidationError({'periodo_aquisitivo_fim': 'Período aquisitivo inválido'})


class AfastamentoFuncionario(models.Model):
    """Controle de afastamentos de funcionários (Atestados, acidentes, licenças)"""

    TIPO_AFASTAMENTO = [
        ('ATESTADO_MEDICO', 'Atestado Médico'), ('ACIDENTE_TRABALHO', 'Acidente de Trabalho'),
        ('LICENCA_MATERNIDADE', 'Licença Maternidade'), ('LICENCA_PATERNIDADE', 'Licença Paternidade'),
        ('LICENCA_SAUDE', 'Licença Saúde (INSS)'), ('SUSPENSAO', 'Suspensão'), ('OUTROS', 'Outros'),
    ]

    STATUS_AFASTAMENTO = [
        ('ATIVO', 'Ativo/Em Andamento'), ('CONCLUIDO', 'Concluído'), ('CANCELADO', 'Cancelado'),
    ]

    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='afastamentos_funcionarios', verbose_name='Empresa')
    funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, related_name='afastamentos', verbose_name='Funcionário')

    tipo_afastamento = models.CharField('Tipo de Afastamento', max_length=30, choices=TIPO_AFASTAMENTO)
    data_inicio = models.DateField('Data de Início do Afastamento')
    data_prevista_retorno = models.DateField('Data Prevista de Retorno')
    data_retorno_efetivo = models.DateField('Data de Retorno Efetivo', null=True, blank=True)
    dias_afastamento = models.PositiveIntegerField('Dias de Afastamento', default=1)

    motivo = models.TextField('Motivo/Descrição')
    cid = models.CharField('CID', max_length=10, blank=True)
    numero_atestado = models.CharField('Número do Atestado/Documento', max_length=50, blank=True)
    medico_responsavel = models.CharField('Médico Responsável', max_length=200, blank=True)
    crm_medico = models.CharField('CRM do Médico', max_length=20, blank=True)
    arquivo_atestado = models.FileField('Arquivo do Atestado', upload_to='rh/afastamentos/%Y/%m/', null=True, blank=True)

    e_acidente_trabalho = models.BooleanField('É Acidente de Trabalho?', default=False)
    cat_emitida = models.BooleanField('CAT Emitida?', default=False)
    numero_cat = models.CharField('Número da CAT', max_length=50, blank=True)
    arquivo_cat = models.FileField('Arquivo da CAT', upload_to='rh/cat/%Y/%m/', null=True, blank=True)

    requer_inss = models.BooleanField('Requer Auxílio INSS?', default=False)
    numero_beneficio_inss = models.CharField('Número do Benefício INSS', max_length=50, blank=True)

    status = models.CharField('Status', max_length=20, choices=STATUS_AFASTAMENTO, default='ATIVO')
    observacoes = models.TextField('Observações', blank=True)

    cadastrado_por = models.ForeignKey('usuarios.Usuario', on_delete=models.SET_NULL, null=True, related_name='afastamentos_cadastrados', verbose_name='Cadastrado por')
    data_cadastro = models.DateTimeField('Data de Cadastro', auto_now_add=True)
    data_atualizacao = models.DateTimeField('Última Atualização', auto_now=True)

    class Meta:
        db_table = 'cadastros_afastamentofuncionario'
        verbose_name = 'Afastamento de Funcionário'
        verbose_name_plural = 'Afastamentos de Funcionários'
        ordering = ['-data_inicio']
        indexes = [
            models.Index(fields=['empresa', 'status']),
            models.Index(fields=['funcionario', 'status']),
            models.Index(fields=['tipo_afastamento']),
            models.Index(fields=['data_inicio', 'data_prevista_retorno']),
        ]

    def __str__(self):
        return f"{self.funcionario.nome_completo} - {self.get_tipo_afastamento_display()} ({self.data_inicio})"

    def get_dias_corridos(self):
        data_final = self.data_retorno_efetivo or self.data_prevista_retorno
        return (data_final - self.data_inicio).days + 1

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.data_prevista_retorno < self.data_inicio:
            raise ValidationError({'data_prevista_retorno': 'Data de retorno não pode ser anterior à data de início'})
        if self.data_retorno_efetivo and self.data_retorno_efetivo < self.data_inicio:
            raise ValidationError({'data_retorno_efetivo': 'Data de retorno efetivo não pode ser anterior à data de início'})
        if self.e_acidente_trabalho and not self.cat_emitida:
            raise ValidationError({'cat_emitida': 'CAT deve ser emitida para acidentes de trabalho'})


# ============================================================================
# LAUDO DE RISCO
# ============================================================================

class LaudoRisco(models.Model):
    """Controle de laudos técnicos de risco ocupacional (insalubridade/periculosidade)."""

    TIPO_LAUDO = [
        ('PPRA', 'PPRA'), ('LTCAT', 'LTCAT'), ('PCMSO', 'PCMSO'),
        ('INSALUBRIDADE', 'Insalubridade'), ('PERICULOSIDADE', 'Periculosidade'), ('OUTRO', 'Outro'),
    ]

    STATUS_LAUDO = [
        ('VIGENTE', 'Vigente'), ('RENOVACAO_PENDENTE', 'Renovação Pendente'), ('VENCIDO', 'Vencido'),
    ]

    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='laudos_risco', verbose_name='Empresa')
    funcao = models.ForeignKey('FuncaoFuncionario', on_delete=models.PROTECT, related_name='laudos_risco', verbose_name='Função')
    vinculo = models.ForeignKey('VinculoContrato', on_delete=models.SET_NULL, null=True, blank=True, related_name='laudos_risco', verbose_name='Vínculo Contratual')

    tipo_laudo = models.CharField('Tipo de Laudo', max_length=20, choices=TIPO_LAUDO, default='LTCAT')
    data_emissao = models.DateField('Data de Emissão')
    data_validade = models.DateField('Data de Validade')
    responsavel_tecnico = models.CharField('Responsável Técnico', max_length=150)
    numero_art = models.CharField('Número ART/Registro', max_length=60, blank=True)
    arquivo_laudo = models.FileField(
        'Arquivo do Laudo', upload_to='rh/laudos/%Y/%m/', blank=True, null=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx'])]
    )
    status = models.CharField('Status', max_length=20, choices=STATUS_LAUDO, default='VIGENTE')
    observacoes = models.TextField('Observações', blank=True)

    cadastrado_por = models.ForeignKey('usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True, related_name='laudos_risco_cadastrados', verbose_name='Cadastrado por')
    data_cadastro = models.DateTimeField('Data de Cadastro', auto_now_add=True)
    data_atualizacao = models.DateTimeField('Última Atualização', auto_now=True)

    class Meta:
        db_table = 'cadastros_laudorisco'
        verbose_name = 'Laudo de Risco'
        verbose_name_plural = 'Laudos de Risco'
        ordering = ['data_validade', '-data_cadastro']
        indexes = [
            models.Index(fields=['empresa', 'status']),
            models.Index(fields=['empresa', 'data_validade']),
            models.Index(fields=['funcao']),
            models.Index(fields=['vinculo']),
        ]

    def __str__(self):
        return f"{self.funcao.nome} - {self.get_tipo_laudo_display()} ({self.data_validade:%d/%m/%Y})"

    def clean(self):
        errors = {}
        if self.data_validade and self.data_emissao and self.data_validade < self.data_emissao:
            errors['data_validade'] = 'A data de validade não pode ser anterior à data de emissão.'
        if self.vinculo_id and self.funcao_id and self.vinculo.funcao_id != self.funcao_id:
            errors['vinculo'] = 'O vínculo selecionado deve pertencer à mesma função informada no laudo.'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.data_validade:
            hoje = timezone.now().date()
            if self.data_validade < hoje:
                self.status = 'VENCIDO'
            elif (self.data_validade - hoje).days <= 30 and self.status == 'VIGENTE':
                self.status = 'RENOVACAO_PENDENTE'
        super().save(*args, **kwargs)


# ============================================================================
# ASO — EXAMES OCUPACIONAIS
# ============================================================================

class TipoExameASO(models.Model):
    """Catálogo de tipos de exames ASO por empresa."""

    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='tipos_exame_aso', verbose_name='Empresa')
    nome = models.CharField('Nome do Exame', max_length=100)
    codigo = models.CharField('Código', max_length=40)
    ativo = models.BooleanField('Ativo', default=True)
    ordem = models.PositiveIntegerField('Ordem de Exibição', default=0)
    eh_padrao_sistema = models.BooleanField('Exame Padrão do Sistema', default=False)
    observacoes = models.TextField('Observações', blank=True)
    data_cadastro = models.DateTimeField('Data de Cadastro', auto_now_add=True)
    data_atualizacao = models.DateTimeField('Última Atualização', auto_now=True)

    class Meta:
        db_table = 'cadastros_tipoexameaso'
        verbose_name = 'Tipo de Exame ASO'
        verbose_name_plural = 'Tipos de Exame ASO'
        ordering = ['ordem', 'nome']
        constraints = [
            models.UniqueConstraint(fields=['empresa', 'codigo'], name='unique_tipo_exame_aso_empresa_codigo'),
            models.UniqueConstraint(fields=['empresa', 'nome'], name='unique_tipo_exame_aso_empresa_nome'),
        ]
        indexes = [
            models.Index(fields=['empresa', 'ativo']),
            models.Index(fields=['empresa', 'ordem']),
        ]

    def __str__(self):
        return f"{self.nome} ({self.empresa.nome})"


class SolicitacaoASO(models.Model):
    """Solicitação de exame ASO por funcionário."""

    TIPO_ASO = [
        ('ADMISSIONAL', 'Admissional'), ('RECONTRATACAO', 'Recontratação'),
        ('PERIODICO', 'Periódico'), ('DEMISSIONAL', 'Demissional'),
    ]

    STATUS_SOLICITACAO = [
        ('RASCUNHO', 'Rascunho'), ('ASSINADO', 'Assinado'),
        ('ENVIADO', 'Enviado'), ('CONCLUIDO', 'Concluído'), ('CANCELADO', 'Cancelado'),
    ]

    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='solicitacoes_aso', verbose_name='Empresa')
    funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, related_name='solicitacoes_aso', verbose_name='Funcionário')
    vinculo = models.ForeignKey(VinculoContrato, on_delete=models.SET_NULL, null=True, blank=True, related_name='solicitacoes_aso', verbose_name='Vínculo Contratual')

    tipo_aso = models.CharField('Tipo de ASO', max_length=20, choices=TIPO_ASO)
    data_solicitacao = models.DateField('Data da Solicitação', default=timezone.now)
    data_prevista_exame = models.DateField('Data Prevista do Exame')
    data_vencimento = models.DateField('Data de Vencimento', null=True, blank=True)

    laboratorio_nome = models.CharField('Laboratório', max_length=150, blank=True)
    laboratorio_email = models.EmailField('Email do Laboratório', blank=True)
    trabalhador_whatsapp = models.CharField('WhatsApp do Trabalhador', max_length=20, blank=True)

    exames = models.ManyToManyField(TipoExameASO, related_name='solicitacoes', blank=True, verbose_name='Exames Solicitados')
    possui_outros_exames = models.BooleanField('Possui outros exames fora da lista?', default=False)
    outros_exames_descricao = models.TextField('Outros Exames', blank=True)

    assinatura_rh_imagem = models.ImageField('Assinatura Eletrônica RH', upload_to='rh/aso/assinaturas/%Y/%m/', null=True, blank=True)
    assinatura_rh_nome = models.CharField('Nome do Responsável RH', max_length=120, blank=True)
    assinatura_rh_datahora = models.DateTimeField('Data/Hora da Assinatura', null=True, blank=True)

    status = models.CharField('Status', max_length=20, choices=STATUS_SOLICITACAO, default='RASCUNHO')
    gerar_alerta_vencimento = models.BooleanField('Gerar Alerta de Vencimento', default=True)
    dias_antecedencia_alerta = models.IntegerField('Dias de Antecedência para Alerta', default=30)
    periodicidade_meses = models.IntegerField('Periodicidade em Meses', default=12)

    arquivo_pdf = models.FileField('Arquivo PDF da Solicitação', upload_to='rh/aso/solicitacoes/%Y/%m/', null=True, blank=True)

    cadastrado_por = models.ForeignKey('usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True, related_name='solicitacoes_aso_cadastradas', verbose_name='Cadastrado por')
    data_cadastro = models.DateTimeField('Data de Cadastro', auto_now_add=True)
    data_atualizacao = models.DateTimeField('Última Atualização', auto_now=True)

    class Meta:
        db_table = 'cadastros_solicitacaoaso'
        verbose_name = 'Solicitação de ASO'
        verbose_name_plural = 'Solicitações de ASO'
        ordering = ['-data_cadastro']
        indexes = [
            models.Index(fields=['empresa', 'status']),
            models.Index(fields=['empresa', 'tipo_aso']),
            models.Index(fields=['empresa', 'data_vencimento']),
            models.Index(fields=['funcionario']),
        ]

    def __str__(self):
        return f"ASO {self.get_tipo_aso_display()} - {self.funcionario.nome_completo}"

    def clean(self):
        errors = {}
        if self.tipo_aso == 'PERIODICO' and not self.data_vencimento:
            errors['data_vencimento'] = 'Informe a data de vencimento para ASO periódico.'
        if self.possui_outros_exames and not self.outros_exames_descricao.strip():
            errors['outros_exames_descricao'] = 'Descreva os outros exames quando essa opção estiver marcada.'
        if self.vinculo_id and self.funcionario_id and self.vinculo.funcionario_id != self.funcionario_id:
            errors['vinculo'] = 'O vínculo informado não pertence ao funcionário selecionado.'
        if self.data_prevista_exame and self.data_solicitacao and self.data_prevista_exame < self.data_solicitacao:
            errors['data_prevista_exame'] = 'A data prevista do exame não pode ser anterior à solicitação.'
        if self.dias_antecedencia_alerta is not None and self.dias_antecedencia_alerta < 0:
            errors['dias_antecedencia_alerta'] = 'Informe um valor maior ou igual a zero.'
        if errors:
            raise ValidationError(errors)

    def dias_para_vencimento(self):
        if not self.data_vencimento:
            return None
        return (self.data_vencimento - timezone.now().date()).days

    def precisa_alerta(self):
        if not self.gerar_alerta_vencimento or not self.data_vencimento:
            return False
        dias_restantes = self.dias_para_vencimento()
        if dias_restantes is None:
            return False
        return 0 <= dias_restantes <= self.dias_antecedencia_alerta

    def gerar_proxima_aso(self):
        if self.tipo_aso != 'PERIODICO':
            return None
        aso_existente = SolicitacaoASO.objects.filter(
            funcionario=self.funcionario, empresa=self.empresa,
            tipo_aso='PERIODICO', status__in=['RASCUNHO', 'ASSINADO', 'ENVIADO']
        ).exists()
        if aso_existente:
            return None
        from datetime import timedelta
        proxima_data_vencimento = self.data_vencimento + timedelta(days=self.periodicidade_meses * 30)
        proxima_data_prevista_exame = self.data_prevista_exame + timedelta(days=self.periodicidade_meses * 30)
        proxima_aso = SolicitacaoASO.objects.create(
            empresa=self.empresa, funcionario=self.funcionario, vinculo=self.vinculo,
            tipo_aso='PERIODICO', data_solicitacao=timezone.now().date(),
            data_prevista_exame=proxima_data_prevista_exame, data_vencimento=proxima_data_vencimento,
            laboratorio_nome=self.laboratorio_nome, laboratorio_email=self.laboratorio_email,
            trabalhador_whatsapp=self.trabalhador_whatsapp, status='RASCUNHO',
            gerar_alerta_vencimento=self.gerar_alerta_vencimento,
            dias_antecedencia_alerta=self.dias_antecedencia_alerta,
            periodicidade_meses=self.periodicidade_meses, cadastrado_por=self.cadastrado_por,
        )
        if self.exames.exists():
            proxima_aso.exames.set(self.exames.all())
        return proxima_aso


class LogEnvioSolicitacaoASO(models.Model):
    """Log de envios de solicitações de ASO por canal."""

    CANAL_ENVIO = [('EMAIL', 'Email'), ('WHATSAPP', 'WhatsApp')]
    STATUS_ENVIO = [('SUCESSO', 'Sucesso'), ('FALHA', 'Falha')]

    solicitacao = models.ForeignKey(SolicitacaoASO, on_delete=models.CASCADE, related_name='logs_envio', verbose_name='Solicitação ASO')
    canal = models.CharField('Canal', max_length=20, choices=CANAL_ENVIO)
    destinatario = models.CharField('Destinatário', max_length=200)
    status_envio = models.CharField('Status do Envio', max_length=20, choices=STATUS_ENVIO)
    retorno = models.TextField('Retorno', blank=True)
    data_envio = models.DateTimeField('Data do Envio', auto_now_add=True)

    class Meta:
        db_table = 'cadastros_logenviosolicitacaoaso'
        verbose_name = 'Log de Envio da Solicitação ASO'
        verbose_name_plural = 'Logs de Envio das Solicitações ASO'
        ordering = ['-data_envio']
        indexes = [
            models.Index(fields=['canal', 'status_envio']),
            models.Index(fields=['data_envio']),
        ]

    def __str__(self):
        return f"{self.solicitacao_id} - {self.canal} - {self.status_envio}"


# ============================================================================
# RESCISÃO DE CONTRATO
# ============================================================================

class RescisaoContrato(models.Model):
    """Controle de rescisões/desligamentos de funcionários"""

    TIPO_RESCISAO = [
        ('DEMISSAO_SEM_JUSTA_CAUSA', 'Demissão Sem Justa Causa'),
        ('DEMISSAO_COM_JUSTA_CAUSA', 'Demissão Com Justa Causa'),
        ('PEDIDO_DEMISSAO', 'Pedido de Demissão'),
        ('ACORDO_TRABALHISTA', 'Acordo Trabalhista'),
        ('TERMINO_CONTRATO', 'Término de Contrato (Temporário)'),
        ('APOSENTADORIA', 'Aposentadoria'),
        ('FALECIMENTO', 'Falecimento'),
    ]

    STATUS_RESCISAO = [
        ('EM_PROCESSO', 'Em Processo'), ('CONCLUIDA', 'Concluída'), ('CANCELADA', 'Cancelada'),
    ]

    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='rescisoes', verbose_name='Empresa')
    funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, related_name='rescisoes', verbose_name='Funcionário')
    vinculo = models.ForeignKey(VinculoContrato, on_delete=models.SET_NULL, null=True, blank=True, related_name='rescisoes', verbose_name='Vínculo Contratual')

    tipo_rescisao = models.CharField('Tipo de Rescisão', max_length=40, choices=TIPO_RESCISAO)
    data_aviso = models.DateField('Data do Aviso')
    data_desligamento = models.DateField('Data do Desligamento')
    trabalhou_aviso_previo = models.BooleanField('Trabalhou o Aviso Prévio?', default=True)
    dias_aviso_previo = models.PositiveIntegerField('Dias de Aviso Prévio', default=30)

    motivo_detalhado = models.TextField('Motivo Detalhado da Rescisão')

    saldo_salario = models.DecimalField('Saldo de Salário (R$)', max_digits=10, decimal_places=2, default=0)
    ferias_vencidas = models.DecimalField('Férias Vencidas (R$)', max_digits=10, decimal_places=2, default=0)
    ferias_proporcionais = models.DecimalField('Férias Proporcionais (R$)', max_digits=10, decimal_places=2, default=0)
    decimo_terceiro_proporcional = models.DecimalField('13º Proporcional (R$)', max_digits=10, decimal_places=2, default=0)
    aviso_previo_indenizado = models.DecimalField('Aviso Prévio Indenizado (R$)', max_digits=10, decimal_places=2, default=0)
    multa_fgts = models.DecimalField('Multa FGTS 40% (R$)', max_digits=10, decimal_places=2, default=0)
    outros_valores = models.DecimalField('Outros Valores (R$)', max_digits=10, decimal_places=2, default=0)
    descontos = models.DecimalField('Descontos (R$)', max_digits=10, decimal_places=2, default=0)
    valor_liquido = models.DecimalField('Valor Líquido a Pagar (R$)', max_digits=10, decimal_places=2, default=0)

    tem_direito_seguro_desemprego = models.BooleanField('Tem Direito a Seguro Desemprego?', default=False)
    liberar_fgts = models.BooleanField('Liberar Saque FGTS?', default=False)

    exame_demissional_realizado = models.BooleanField('Exame Demissional Realizado?', default=False)
    data_exame_demissional = models.DateField('Data do Exame Demissional', null=True, blank=True)
    trct_emitido = models.BooleanField('TRCT Emitido?', default=False)
    chave_conectividade_social = models.CharField('Chave Conectividade Social', max_length=50, blank=True)

    arquivo_trct = models.FileField('Arquivo TRCT', upload_to='rh/rescisoes/%Y/%m/', null=True, blank=True)
    arquivo_exame = models.FileField('Arquivo Exame Demissional', upload_to='rh/rescisoes/%Y/%m/', null=True, blank=True)

    data_homologacao = models.DateField('Data da Homologação', null=True, blank=True)
    local_homologacao = models.CharField('Local da Homologação', max_length=200, blank=True)
    data_pagamento = models.DateField('Data do Pagamento', null=True, blank=True)
    forma_pagamento = models.CharField('Forma de Pagamento', max_length=50, blank=True)

    status = models.CharField('Status', max_length=20, choices=STATUS_RESCISAO, default='EM_PROCESSO')
    observacoes = models.TextField('Observações', blank=True)

    cadastrado_por = models.ForeignKey('usuarios.Usuario', on_delete=models.SET_NULL, null=True, related_name='rescisoes_cadastradas', verbose_name='Cadastrado por')
    data_cadastro = models.DateTimeField('Data de Cadastro', auto_now_add=True)
    data_atualizacao = models.DateTimeField('Última Atualização', auto_now=True)

    class Meta:
        db_table = 'cadastros_rescisaocontrato'
        verbose_name = 'Rescisão de Contrato'
        verbose_name_plural = 'Rescisões de Contratos'
        ordering = ['-data_desligamento']
        indexes = [
            models.Index(fields=['empresa', 'status']),
            models.Index(fields=['funcionario']),
            models.Index(fields=['tipo_rescisao']),
            models.Index(fields=['data_desligamento']),
        ]

    def __str__(self):
        return f"{self.funcionario.nome_completo} - {self.get_tipo_rescisao_display()} ({self.data_desligamento})"

    @staticmethod
    def _to_decimal(value):
        if isinstance(value, Decimal):
            return value.quantize(Decimal('0.01'))
        if value in (None, ''):
            return Decimal('0.00')
        return Decimal(str(value)).quantize(Decimal('0.01'))

    @staticmethod
    def _add_years(base_date, years):
        try:
            return base_date.replace(year=base_date.year + years)
        except ValueError:
            return base_date.replace(month=2, day=28, year=base_date.year + years)

    @classmethod
    def calcular_estimativa_verbas(cls, funcionario, tipo_rescisao, data_desligamento,
                                   trabalhou_aviso_previo=True, dias_aviso_previo=30):
        salario = cls._to_decimal(funcionario.salario or 0)
        data_admissao = funcionario.data_admissao
        data_desligamento = data_desligamento or timezone.now().date()
        dias_aviso_previo = int(dias_aviso_previo or 30)

        zeros = {
            'saldo_salario': Decimal('0.00'), 'ferias_vencidas': Decimal('0.00'),
            'ferias_proporcionais': Decimal('0.00'), 'decimo_terceiro_proporcional': Decimal('0.00'),
            'aviso_previo_indenizado': Decimal('0.00'), 'multa_fgts': Decimal('0.00'),
            'outros_valores': Decimal('0.00'), 'descontos': Decimal('0.00'),
            'valor_total': Decimal('0.00'), 'valor_liquido': Decimal('0.00'),
            'tem_direito_seguro_desemprego': False, 'liberar_fgts': False, 'memoria': [],
        }

        if not data_admissao or data_desligamento < data_admissao:
            zeros['memoria'].append('Informe uma data de admissão válida para estimar as verbas.')
            return zeros

        dias_no_mes = monthrange(data_desligamento.year, data_desligamento.month)[1]
        saldo_salario = cls._to_decimal((salario / Decimal(dias_no_mes)) * Decimal(data_desligamento.day))

        periodos_vencidos = 0
        periodo_inicio = data_admissao
        while cls._add_years(periodo_inicio, 1) <= data_desligamento:
            periodo_fim = cls._add_years(periodo_inicio, 1) - timedelta(days=1)
            possui_ferias = funcionario.ferias.exclude(status='CANCELADA').filter(
                periodo_aquisitivo_inicio=periodo_inicio, periodo_aquisitivo_fim=periodo_fim
            ).exists()
            if not possui_ferias:
                periodos_vencidos += 1
            periodo_inicio = cls._add_years(periodo_inicio, 1)

        ferias_vencidas = cls._to_decimal(salario * Decimal(periodos_vencidos))
        meses_ferias_proporcionais = (
            (data_desligamento.year - periodo_inicio.year) * 12 +
            (data_desligamento.month - periodo_inicio.month)
        )
        if periodo_inicio.day > 15:
            meses_ferias_proporcionais -= 1
        if data_desligamento.day >= 15:
            meses_ferias_proporcionais += 1
        meses_ferias_proporcionais = min(max(meses_ferias_proporcionais, 0), 11)
        ferias_proporcionais = cls._to_decimal((salario / Decimal('12')) * Decimal(meses_ferias_proporcionais))

        inicio_ano = max(data_admissao, date(data_desligamento.year, 1, 1))
        meses_decimo = (data_desligamento.month - inicio_ano.month) + 1
        if inicio_ano.day > 15:
            meses_decimo -= 1
        if data_desligamento.day < 15:
            meses_decimo -= 1
        meses_decimo = min(max(meses_decimo, 0), 12)
        decimo_terceiro = cls._to_decimal((salario / Decimal('12')) * Decimal(meses_decimo))
        terco_constitucional = cls._to_decimal((ferias_vencidas + ferias_proporcionais) / Decimal('3'))

        tipos_com_aviso_indenizado = {'DEMISSAO_SEM_JUSTA_CAUSA', 'ACORDO_TRABALHISTA', 'TERMINO_CONTRATO', 'APOSENTADORIA'}
        aviso_previo_indenizado = Decimal('0.00')
        if not trabalhou_aviso_previo and tipo_rescisao in tipos_com_aviso_indenizado:
            aviso_previo_indenizado = cls._to_decimal((salario / Decimal('30')) * Decimal(dias_aviso_previo))

        meses_fgts = max(((data_desligamento.year - data_admissao.year) * 12) + (data_desligamento.month - data_admissao.month), 0)
        if data_desligamento.day >= data_admissao.day:
            meses_fgts += 1
        saldo_fgts_estimado = cls._to_decimal(salario * Decimal('0.08') * Decimal(meses_fgts))

        multa_fgts = Decimal('0.00')
        if tipo_rescisao == 'DEMISSAO_SEM_JUSTA_CAUSA':
            multa_fgts = cls._to_decimal(saldo_fgts_estimado * Decimal('0.40'))
        elif tipo_rescisao == 'ACORDO_TRABALHISTA':
            multa_fgts = cls._to_decimal(saldo_fgts_estimado * Decimal('0.20'))

        outros_valores = terco_constitucional
        descontos = Decimal('0.00')
        valor_total = cls._to_decimal(
            saldo_salario + ferias_vencidas + ferias_proporcionais +
            decimo_terceiro + aviso_previo_indenizado + multa_fgts + outros_valores
        )
        valor_liquido = cls._to_decimal(valor_total - descontos)

        memoria = [
            f'Saldo de salário: salário mensal de R$ {salario} dividido por {dias_no_mes} dias e multiplicado por {data_desligamento.day} dias trabalhados no mês.',
            f'Férias vencidas: {periodos_vencidos} período(s) aquisitivo(s) sem baixa no controle de férias.',
            f'Férias proporcionais: {meses_ferias_proporcionais}/12 avos sobre o salário atual.',
            f'13º proporcional: {meses_decimo}/12 avos no ano da rescisão.',
            f'1/3 constitucional: lançado em Outros Valores, sobre férias vencidas e proporcionais.',
            f'FGTS/multa: estimativa sobre 8% do salário por {meses_fgts} mês(es) de vínculo.',
            'Descontos legais e adiantamentos não são apurados automaticamente nesta versão.',
        ]

        return {
            'saldo_salario': saldo_salario, 'ferias_vencidas': ferias_vencidas,
            'ferias_proporcionais': ferias_proporcionais, 'decimo_terceiro_proporcional': decimo_terceiro,
            'aviso_previo_indenizado': aviso_previo_indenizado, 'multa_fgts': multa_fgts,
            'outros_valores': outros_valores, 'descontos': descontos,
            'valor_total': valor_total, 'valor_liquido': valor_liquido,
            'tem_direito_seguro_desemprego': tipo_rescisao in {'DEMISSAO_SEM_JUSTA_CAUSA', 'TERMINO_CONTRATO'},
            'liberar_fgts': tipo_rescisao in {'DEMISSAO_SEM_JUSTA_CAUSA', 'ACORDO_TRABALHISTA', 'TERMINO_CONTRATO'},
            'memoria': memoria,
        }

    def calcular_valor_liquido(self):
        return (
            self.saldo_salario + self.ferias_vencidas + self.ferias_proporcionais +
            self.decimo_terceiro_proporcional + self.aviso_previo_indenizado +
            self.multa_fgts + self.outros_valores - self.descontos
        )

    def clean(self):
        from django.core.exceptions import ValidationError
        errors = {}
        if self.data_desligamento < self.data_aviso:
            errors['data_desligamento'] = 'Data de desligamento não pode ser anterior ao aviso'
        if self.vinculo and self.funcionario_id and self.vinculo.funcionario_id != self.funcionario_id:
            errors['vinculo'] = 'O vínculo selecionado não pertence ao funcionário informado.'
        if self.tipo_rescisao != 'DEMISSAO_SEM_JUSTA_CAUSA' and self.multa_fgts > 0:
            errors['multa_fgts'] = 'Multa FGTS apenas para demissão sem justa causa'
        if self.tipo_rescisao == 'DEMISSAO_COM_JUSTA_CAUSA':
            if self.tem_direito_seguro_desemprego:
                errors['tem_direito_seguro_desemprego'] = 'Demissão por justa causa não gera seguro desemprego.'
            if self.liberar_fgts:
                errors['liberar_fgts'] = 'Demissão por justa causa não libera saque de FGTS.'
            if self.multa_fgts > 0:
                errors['multa_fgts'] = 'Demissão por justa causa não gera multa de FGTS.'
            if self.aviso_previo_indenizado > 0:
                errors['aviso_previo_indenizado'] = 'Demissão por justa causa não gera aviso prévio indenizado.'
        if self.tipo_rescisao == 'PEDIDO_DEMISSAO' and self.tem_direito_seguro_desemprego:
            errors['tem_direito_seguro_desemprego'] = 'Pedido de demissão não gera seguro desemprego.'
        if self.exame_demissional_realizado and not self.data_exame_demissional:
            errors['data_exame_demissional'] = 'Informe a data do exame demissional realizado.'
        if self.data_homologacao and self.data_homologacao < self.data_desligamento:
            errors['data_homologacao'] = 'A homologação não pode ocorrer antes do desligamento.'
        if self.status == 'CONCLUIDA' and not self.data_pagamento:
            errors['data_pagamento'] = 'Informe a data do pagamento para concluir a rescisão.'
        if errors:
            raise ValidationError(errors)
