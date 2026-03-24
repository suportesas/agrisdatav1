"""
Admin do módulo Fazendas e Culturas
"""

from django.contrib import admin
from .models import (
    Fazenda, EnderecoFazenda, ContatoFazenda,
    ContaBancariaFazenda, DocumentoFazenda, Cultura, Praga,
    EstagioDesenvolvimento, MonitoramentoMIP, PragaNoMonitoramento, PontoMonitoramento
)
from .models import Area, Talhao, HistoricoTalhao, Safra, SafraPlan, SafraReal, FuncaoFuncionario
from .models import Vendedor, ComissaoVendedor

from .models import (
    Fornecedor, FornecedorEndereco, FornecedorContato, FornecedorDadoBancario, 
    Transportadora, Viagem, Porto, Moeda, NCM, EmpresaNCM, Vehicle, VehiclePlate, 
    VehicleDocument, VehicleValueHistory, CFOP, EmpresaCFOP, MotoristaVinculoPlaca,
    Armador, ArmadorEndereco, ArmadorContato, ArmadorDadoBancario,
    Navio, TipoNavio, Requisicao, RequisicaoItem,
    CustoHoraMaquina, OrdemServico, OSFuncionario, OSMaquina, CustoTalhao,
    TipoServicoOS, SubtipoServicoOS, ModalidadeExecucaoOS,
)

class EnderecoFazendaInline(admin.TabularInline):
    """Inline para endereços"""
    model = EnderecoFazenda
    extra = 0
    fields = ['tipo', 'cep', 'logradouro', 'numero', 'cidade', 'uf', 'padrao']


class ContatoFazendaInline(admin.TabularInline):
    """Inline para contatos"""
    model = ContatoFazenda
    extra = 0
    fields = ['tipo', 'nome', 'cargo', 'telefone', 'email', 'preferencial']


class ContaBancariaFazendaInline(admin.TabularInline):
    """Inline para contas bancárias"""
    model = ContaBancariaFazenda
    extra = 0
    fields = ['banco', 'agencia', 'conta', 'conta_digito', 'tipo_conta', 'conta_principal']


class DocumentoFazendaInline(admin.TabularInline):
    """Inline para documentos"""
    model = DocumentoFazenda
    extra = 0
    fields = ['tipo', 'titulo', 'data_validade', 'gerar_alerta_vencimento']
    readonly_fields = []


@admin.register(Fazenda)
class FazendaAdmin(admin.ModelAdmin):
    """Admin principal de Fazendas"""
    list_display = [
        'nome', 'get_cnpj_cpf_formatado', 'empresa', 
        'area_total', 'regime_tributario', 'ativa', 'data_cadastro'
    ]
    list_filter = ['ativa', 'empresa', 'regime_tributario', 'tipo_pessoa']
    search_fields = ['nome', 'nome_fantasia', 'cnpj_cpf', 'empresa__nome']
    readonly_fields = ['data_cadastro', 'data_atualizacao', 'cadastrado_por']
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('empresa', 'nome', 'nome_fantasia', 'tipo_pessoa', 'ativa')
        }),
        ('Documentação', {
            'fields': ('cnpj_cpf', 'inscricao_estadual', 'inscricao_municipal', 'eori', 'regime_tributario')
        }),
        ('Dados da Propriedade', {
            'fields': ('area_total', 'area_agricultavel', 'latitude', 'longitude')
        }),
        ('Contato', {
            'fields': ('telefone', 'email', 'website')
        }),
        ('Observações', {
            'fields': ('observacoes',),
            'classes': ('collapse',)
        }),
        ('Auditoria', {
            'fields': ('cadastrado_via_api', 'cadastrado_por', 'data_cadastro', 'data_atualizacao'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [EnderecoFazendaInline, ContatoFazendaInline, ContaBancariaFazendaInline, DocumentoFazendaInline]
    
    def get_queryset(self, request):
        """Filtra por empresa se não for superusuário"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'empresa') and request.user.empresa:
            return qs.filter(empresa=request.user.empresa)
        return qs.none()


@admin.register(EnderecoFazenda)
class EnderecoFazendaAdmin(admin.ModelAdmin):
    """Admin de Endereços"""
    list_display = ['fazenda', 'get_tipo_display', 'cidade', 'uf', 'padrao']
    list_filter = ['tipo', 'uf', 'padrao']
    search_fields = ['fazenda__nome', 'cidade', 'logradouro']


@admin.register(ContatoFazenda)
class ContatoFazendaAdmin(admin.ModelAdmin):
    """Admin de Contatos"""
    list_display = ['fazenda', 'nome', 'cargo', 'get_tipo_display', 'telefone', 'email', 'preferencial']
    list_filter = ['tipo', 'preferencial', 'whatsapp']
    search_fields = ['fazenda__nome', 'nome', 'email', 'telefone']


@admin.register(ContaBancariaFazenda)
class ContaBancariaFazendaAdmin(admin.ModelAdmin):
    """Admin de Contas Bancárias"""
    list_display = ['fazenda', 'banco', 'agencia', 'conta', 'tipo_conta', 'pix_habilitado', 'conta_principal']
    list_filter = ['tipo_conta', 'pix_habilitado', 'conta_principal', 'ativa']
    search_fields = ['fazenda__nome', 'banco', 'conta']


@admin.register(DocumentoFazenda)
class DocumentoFazendaAdmin(admin.ModelAdmin):
    """Admin de Documentos"""
    list_display = ['fazenda', 'get_tipo_display', 'titulo']
    list_filter = ['tipo']
    search_fields = ['fazenda__nome', 'titulo', 'numero_documento']
    readonly_fields = []
    
    def esta_vencido(self, obj):
        """Mostra status de vencimento"""
        if obj.esta_vencido():
            return '❌ Vencido'
        elif obj.precisa_alerta():
            return '⚠️ Vencendo'
        return '✅ Válido'
    esta_vencido.short_description = 'Status'


@admin.register(FuncaoFuncionario)
class FuncaoFuncionarioAdmin(admin.ModelAdmin):
    """Admin para funções de funcionário"""
    list_display = ['nome', 'empresa', 'ativa']
    search_fields = ['nome']
    fieldsets = (
        ('Informações', {
            'fields': ('empresa', 'nome', 'descricao', 'salario_base', 'ativa'),
            'description': 'Dica: crie uma função chamada "Motorista" para facilitar atribuições de veículos. Ao cadastrar motoristas, lembre-se de preencher CNH e data de validade.'
        }),
    )


@admin.register(Cultura)
class CulturaAdmin(admin.ModelAdmin):
    """Admin de Culturas"""
    list_display = [
        'nome', 'variedade', 'tipo', 'ciclo_cultivo', 
        'dias_colheita', 'produtividade_esperada', 'ativa', 'empresa'
    ]
    list_filter = ['ativa', 'tipo', 'ciclo_cultivo', 'empresa']
    search_fields = ['nome', 'variedade', 'nome_cientifico', 'codigo_interno']
    readonly_fields = ['data_cadastro', 'data_atualizacao', 'cadastrado_por']
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('empresa', 'nome', 'nome_cientifico', 'tipo', 'variedade', 'codigo_interno', 'ativa')
        }),
        ('Características de Plantio', {
            'fields': ('ciclo_cultivo', 'dias_colheita', 'espacamento_linhas', 'espacamento_plantas', 'densidade_plantio')
        }),
        ('Condições Climáticas', {
            'fields': ('temperatura_ideal_min', 'temperatura_ideal_max', 'necessidade_agua')
        }),
        ('Produtividade e Comercialização', {
            'fields': ('unidade_medida', 'produtividade_esperada', 'preco_medio', 'mercado_destino')
        }),
        ('Manejo', {
            'fields': ('irrigacao_necessaria', 'tipo_irrigacao', 'adubacao_recomendada', 'controle_pragas'),
            'classes': ('collapse',)
        }),
        ('Certificações', {
            'fields': ('certificacao_organica', 'certificacao_exportacao'),
        }),
        ('Mídia', {
            'fields': ('imagem',),
        }),
        ('Observações', {
            'fields': ('observacoes',),
            'classes': ('collapse',)
        }),
        ('Auditoria', {
            'fields': ('cadastrado_por', 'data_cadastro', 'data_atualizacao'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Filtra por empresa se não for superusuário"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'empresa') and request.user.empresa:
            return qs.filter(empresa=request.user.empresa)
        return qs.none()
    


@admin.register(Praga)
class PragaAdmin(admin.ModelAdmin):
    """Admin de Pragas"""
    list_display = [
        'nome_comum', 'nome_cientifico', 'ativa', 'empresa', 'data_cadastro'
    ]
    list_filter = ['ativa', 'empresa', 'data_cadastro']
    search_fields = ['nome_comum', 'nome_cientifico']
    readonly_fields = ['data_cadastro', 'data_atualizacao', 'cadastrado_por']
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('empresa', 'nome_comum', 'nome_cientifico', 'ativa')
        }),
        ('Auditoria', {
            'fields': ('cadastrado_por', 'data_cadastro', 'data_atualizacao'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Filtra por empresa se não for superusuário"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'empresa') and request.user.empresa:
            return qs.filter(empresa=request.user.empresa)
        return qs.none()



    

@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'fazenda', 'tipo_area', 'area_total', 'status', 'ativa']
    list_filter = ['tipo_area', 'status', 'ativa']
    search_fields = ['nome', 'fazenda__nome']

@admin.register(Talhao)
class TalhaoAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nome', 'area', 'fazenda', 'status', 'cultura_atual', 'ativo']
    list_filter = ['status', 'ativo']
    search_fields = ['codigo', 'nome', 'fazenda__nome']

@admin.register(HistoricoTalhao)
class HistoricoTalhaoAdmin(admin.ModelAdmin):
    list_display = ['talhao', 'cultura', 'data_plantio', 'data_colheita', 'producao_real']
    list_filter = ['data_plantio']
    search_fields = ['talhao__nome', 'cultura__nome']


class SafraPlanInline(admin.StackedInline):
    model = SafraPlan
    can_delete = False
    verbose_name = 'Planejamento de Safra'
    verbose_name_plural = 'Planejamentos de Safra'
    max_num = 1

@admin.register(Safra)
class SafraAdmin(admin.ModelAdmin):
    list_display = ['nome', 'fazenda', 'cultura', 'ano', 'status']
    list_filter = ['status', 'fazenda', 'cultura', 'ano']
    search_fields = ['nome', 'fazenda__nome', 'cultura__nome']
    inlines = [SafraPlanInline]


@admin.register(SafraPlan)
class SafraPlanAdmin(admin.ModelAdmin):
    list_display = ['safra', 'planned_production', 'planned_area', 'planned_plantio', 'planned_colheita']
    search_fields = ['safra__nome', 'safra__fazenda__nome']


@admin.register(SafraReal)
class SafraRealAdmin(admin.ModelAdmin):
    list_display = ['safra', 'talhao', 'production', 'plantio_real', 'colheita_real', 'source']
    list_filter = ['source']
    search_fields = ['safra__nome', 'talhao__nome']





@admin.register(TipoNavio)
class TipoNavioAdmin(admin.ModelAdmin):
    list_display = ['nome', 'codigo', 'ativo']
    list_filter = ['ativo']
    search_fields = ['nome', 'codigo']
    readonly_fields = ['data_criacao', 'data_atualizacao']
    
    fieldsets = (
        ('Identificação', {
            'fields': ('codigo', 'nome')
        }),
        ('Descrição', {
            'fields': ('descricao',)
        }),
        ('Status', {
            'fields': ('ativo',)
        }),
        ('Auditoria', {
            'fields': ('data_criacao', 'data_atualizacao'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Porto)
class PortoAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nome', 'pais', 'cidade', 'tipo', 'ativo', 'empresa']
    list_filter = ['tipo', 'ativo', 'empresa']
    search_fields = ['codigo', 'nome', 'cidade', 'pais']
    readonly_fields = ['data_criacao', 'data_atualizacao']


@admin.register(Moeda)
class MoedaAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nome', 'simbolo', 'pais', 'taxa_cambio', 'ativo', 'data_atualizacao']
    search_fields = ['codigo', 'nome', 'pais']
    list_filter = ['ativo', 'data_atualizacao']
    ordering = ['codigo']
    readonly_fields = ['data_criacao', 'data_atualizacao']
    
    fieldsets = (
        ('Identificação', {
            'fields': ('codigo', 'nome', 'simbolo', 'pais')
        }),
        ('Valor da Moeda', {
            'fields': ('taxa_cambio',),
            'description': 'Taxa de conversão para Real Brasileiro (1 unidade desta moeda = X BRL)'
        }),
        ('Status', {
            'fields': ('ativo',)
        }),
        ('Auditoria', {
            'fields': ('data_criacao', 'data_atualizacao'),
            'classes': ('collapse',)
        }),
    )


@admin.register(NCM)
class NCMAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nome', 'cest', 'ativo', 'criado_em']
    search_fields = ['codigo', 'nome']
    list_filter = ['ativo']
    ordering = ['codigo']


@admin.register(EmpresaNCM)
class EmpresaNCMAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nome', 'empresa', 'cest', 'ativo', 'criado_em']
    search_fields = ['codigo', 'nome', 'empresa__nome']
    list_filter = ['ativo', 'empresa']
    ordering = ['empresa', 'codigo']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # non-superusers see only their empresa
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'empresa') and request.user.empresa:
            return qs.filter(empresa=request.user.empresa)
        return qs.none()


@admin.register(CFOP)
class CFOPAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nome', 'natureza_operacao', 'ativo']
    search_fields = ['codigo', 'nome']
    list_filter = ['ativo', 'natureza_operacao']
    ordering = ['codigo']


@admin.register(EmpresaCFOP)
class EmpresaCFOPAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nome', 'empresa', 'ativo', 'criado_em']
    search_fields = ['codigo', 'nome', 'empresa__nome']
    list_filter = ['ativo', 'empresa']
    ordering = ['empresa', 'codigo']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'empresa') and request.user.empresa:
            return qs.filter(empresa=request.user.empresa)
        return qs.none()


@admin.register(Vendedor)
class VendedorAdmin(admin.ModelAdmin):
    list_display = ['nome_completo', 'empresa', 'tipo_mercado', 'status', 'data_admissao']
    list_filter = ['empresa', 'tipo_mercado', 'status']
    search_fields = ['nome_completo', 'cpf', 'email_corporativo']
    readonly_fields = ['data_criacao', 'data_atualizacao']
    
    fieldsets = (
        ('Identificação', {
            'fields': ('nome_completo', 'cpf', 'rg', 'data_nascimento', 'foto')
        }),
        ('Empresa', {
            'fields': ('empresa', 'usuario')
        }),
        ('Tipo', {
            'fields': ('tipo_mercado', 'tipo_vinculo')
        }),
        ('Contato', {
            'fields': ('telefone_principal', 'telefone_secundario', 'email_corporativo', 'email_pessoal', 'whatsapp')
        }),
        ('Comercial', {
            'fields': ('comissao_mercado_interno', 'comissao_exportacao', 'comissao_fixa_mensal', 'meta_mensal')
        }),
        ('Hierarquia', {
            'fields': ('supervisor', 'nivel_autonomia', 'acesso_crm')
        }),
        ('Status', {
            'fields': ('status', 'data_admissao', 'data_desligamento')
        }),
        ('Auditoria', {
            'fields': ('criado_por', 'data_criacao', 'data_atualizacao'),
            'classes': ('collapse',)
        }),
    )

@admin.register(ComissaoVendedor)
class ComissaoVendedorAdmin(admin.ModelAdmin):
    list_display = ['vendedor', 'referencia_mes', 'valor_comissao', 'status', 'data_pagamento']
    list_filter = ['empresa', 'status', 'referencia_mes']
    search_fields = ['vendedor__nome_completo']
    readonly_fields = ['data_criacao', 'valor_comissao']


# Fornecedor: Admin registrations
class FornecedorEnderecoInline(admin.TabularInline):
    """Inline para endereços do fornecedor"""
    model = FornecedorEndereco
    extra = 0
    fields = ['tipo', 'cep', 'logradouro', 'numero', 'cidade', 'uf', 'padrao']

class FornecedorContatoInline(admin.TabularInline):
    """Inline para contatos do fornecedor"""
    model = FornecedorContato
    extra = 0
    fields = ['tipo', 'nome', 'cargo', 'telefone', 'email', 'preferencial']

class FornecedorDadoBancarioInline(admin.TabularInline):
    """Inline para contas bancárias do fornecedor"""
    model = FornecedorDadoBancario
    extra = 0
    fields = ['banco', 'agencia', 'conta', 'conta_digito', 'tipo_conta', 'conta_principal']

@admin.register(Fornecedor)
class FornecedorAdmin(admin.ModelAdmin):
    """Admin principal de Fornecedores"""
    list_display = ['nome', 'nome_fantasia', 'cnpj_cpf', 'telefone', 'email', 'ativa']
    list_filter = ['ativa', 'is_exportador', 'moeda_padrao']
    search_fields = ['nome', 'nome_fantasia', 'cnpj_cpf', 'email', 'telefone']
    readonly_fields = ['data_criacao', 'data_atualizacao', 'criado_por']
    inlines = [FornecedorEnderecoInline, FornecedorContatoInline, FornecedorDadoBancarioInline]
    fieldsets = (
        ('Identificação', {'fields': ('empresa', 'nome', 'nome_fantasia', 'tipo_pessoa', 'ativa')}),
        ('Documentação', {'fields': ('cnpj_cpf', 'inscricao_estadual')}),
        ('Contato / Endereço', {'fields': ('telefone', 'celular', 'email', 'cep', 'endereco', 'numero', 'complemento', 'bairro', 'cidade', 'uf', 'pais')}),
        ('Portal', {'fields': ('portal_enabled', 'portal_user', 'portal_token', 'is_exportador', 'moeda_padrao', 'porto_preferencial')}),
        ('Auditoria', {'fields': ('criado_por', 'data_criacao', 'data_atualizacao'), 'classes': ('collapse',)}),
    )

    def get_queryset(self, request):
        """Filtra por empresa se não for superusuário"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'empresa') and request.user.empresa:
            return qs.filter(empresa=request.user.empresa)
        return qs.none()


class ViagemInline(admin.TabularInline):
    model = Viagem
    extra = 0
    fields = ['origem', 'destino', 'data', 'valor_frete', 'status']


@admin.register(Transportadora)
class TransportadoraAdmin(admin.ModelAdmin):
    """Admin de Transportadoras"""
    list_display = ['razao_social', 'nome_fantasia', 'cnpj', 'tipo', 'frete_padrao', 'ativa', 'empresa', 'get_total_viagens']
    list_filter = ['tipo', 'ativa', 'uf', 'empresa']
    search_fields = ['razao_social', 'cnpj', 'empresa__nome']
    readonly_fields = ['data_criacao', 'data_atualizacao']
    fieldsets = (
        ('Identificação', {'fields': ('empresa', 'razao_social', 'nome_fantasia', 'tipo', 'ativa')}),
        ('Documentação', {'fields': ('cnpj', 'inscricao_estadual')}),
        ('Contato / Endereço', {'fields': ('contato_principal_nome','contato_principal_telefone','contato_principal_email','cep','logradouro','numero','complemento','bairro','cidade','uf','pais')}),
        ('Financeiro', {'fields': ('banco','agencia','conta','tipo_conta','pix_key','frete_padrao','frete_por_km','moeda')}),
        ('Auditoria', {'fields': ('data_criacao','data_atualizacao'), 'classes': ('collapse',)}),
    )

    inlines = [ViagemInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'empresa') and request.user.empresa:
            return qs.filter(empresa=request.user.empresa)
        return qs.none()

    def get_total_viagens(self, obj):
        return obj.viagens.count()
    get_total_viagens.short_description = 'Total Viagens'


@admin.register(Viagem)
class ViagemAdmin(admin.ModelAdmin):
    list_display = ['transportadora', 'origem', 'destino', 'data', 'valor_frete', 'status']
    list_filter = ['status', 'data', 'transportadora__empresa']
    search_fields = ['transportadora__razao_social', 'origem', 'destino']


# ==========================
# Admin para Veículos
# ==========================
class VehiclePlateInline(admin.TabularInline):
    model = VehiclePlate
    extra = 0
    fields = ['placa', 'vigencia_inicio', 'vigencia_fim', 'atual']

class VehicleDocumentInline(admin.TabularInline):
    model = VehicleDocument
    extra = 0
    fields = ['tipo', 'numero', 'data_emissao', 'data_validade', 'arquivo']


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'empresa', 'transportadora', 'tipo', 'ativo', 'consumo_medio', 'consumo_unidade', 'tank_capacity', 'estimated_range_display', 'data_cadastro']
    list_filter = ['tipo', 'ativo', 'empresa']
    search_fields = ['marca', 'modelo', 'plates__placa']
    inlines = [VehiclePlateInline, VehicleDocumentInline]
    readonly_fields = ['data_cadastro', 'data_atualizacao']

    def estimated_range_display(self, obj):
        return f"{obj.estimated_range_km} km" if obj.estimated_range_km else '—'
    estimated_range_display.short_description = 'Estimativa (km)'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'empresa') and request.user.empresa:
            return qs.filter(empresa=request.user.empresa)
        return qs.none()


@admin.register(VehiclePlate)
class VehiclePlateAdmin(admin.ModelAdmin):
    list_display = ['vehicle', 'placa', 'vigencia_inicio', 'vigencia_fim', 'atual']
    search_fields = ['placa', 'vehicle__marca', 'vehicle__modelo']



@admin.register(VehicleValueHistory)
class VehicleValueHistoryAdmin(admin.ModelAdmin):
    list_display = ['vehicle', 'tipo', 'percentual', 'previous_value', 'new_value', 'aplicado_por', 'data_aplicacao']
    list_filter = ['tipo', 'aplicado_por']
    search_fields = ['vehicle__marca', 'vehicle__modelo']
    readonly_fields = ['previous_value', 'new_value', 'percentual', 'tipo', 'aplicado_por', 'data_aplicacao']
    ordering = ['-data_aplicacao']


@admin.register(FornecedorEndereco)
class FornecedorEnderecoAdmin(admin.ModelAdmin):
    """Admin de Endereços do Fornecedor"""
    list_display = ['fornecedor', 'get_tipo_display', 'cidade', 'uf', 'padrao']
    list_filter = ['tipo', 'uf', 'padrao']
    search_fields = ['fornecedor__nome', 'cidade', 'logradouro']
    readonly_fields = ['data_cadastro']

# ============================================
# ARMADOR - Admin registrations
# ============================================

class ArmadorEnderecoInline(admin.TabularInline):
    """Inline para endereços do armador"""
    model = ArmadorEndereco
    extra = 0
    fields = ['tipo', 'cep', 'logradouro', 'numero', 'cidade', 'uf', 'padrao', 'preenchido_via_api']
    readonly_fields = ['preenchido_via_api']


class ArmadorContatoInline(admin.TabularInline):
    """Inline para contatos do armador"""
    model = ArmadorContato
    extra = 0
    fields = ['tipo', 'nome', 'cargo', 'telefone', 'email', 'whatsapp', 'preferencial']


class ArmadorDadoBancarioInline(admin.TabularInline):
    """Inline para contas bancárias do armador"""
    model = ArmadorDadoBancario
    extra = 0
    fields = ['nome_banco', 'agencia', 'conta', 'tipo_conta', 'tem_pix', 'padrao']


@admin.register(Armador)
class ArmadorAdmin(admin.ModelAdmin):
    """Admin principal de Armadores - RF-028, RF-308, RF-805, RF-808"""
    list_display = [
        'nome', 'codigo', 'get_cnpj_formatado', 'pais', 
        'confiabilidade_percentual', 'percentual_rolagem_historico', 'ativo'
    ]
    list_filter = ['ativo', 'empresa', 'pais']
    search_fields = ['nome', 'nome_fantasia', 'cnpj', 'codigo', 'email']
    readonly_fields = ['data_criacao', 'data_atualizacao', 'criado_por', 'get_cnpj_formatado']
    
    fieldsets = (
        ('Identificação', {
            'fields': ('empresa', 'codigo', 'nome', 'nome_fantasia', 'ativo')
        }),
        ('Documentação', {
            'fields': ('cnpj', 'pais', 'website')
        }),
        ('Endereço Principal', {
            'fields': ('cep', 'endereco', 'numero', 'complemento', 'bairro', 'cidade', 'uf')
        }),
        ('Contato Principal', {
            'fields': ('email', 'telefone', 'celular')
        }),
        ('Operacional', {
            'fields': ('tipos_navio',)
        }),
        ('Indicadores (RF-808)', {
            'fields': ('confiabilidade_percentual', 'percentual_rolagem_historico', 'custo_medio_rolagem'),
            'description': 'Métricas de desempenho e confiabilidade do armador'
        }),
        ('Auditoria', {
            'fields': ('criado_por', 'data_criacao', 'data_atualizacao'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [ArmadorEnderecoInline, ArmadorContatoInline, ArmadorDadoBancarioInline]

    def get_queryset(self, request):
        """Filtra por empresa se não for superusuário"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'empresa') and request.user.empresa:
            return qs.filter(empresa=request.user.empresa)
        return qs.none()


@admin.register(ArmadorEndereco)
class ArmadorEnderecoAdmin(admin.ModelAdmin):
    """Admin de Endereços do Armador"""
    list_display = ['armador', 'get_tipo_display', 'cidade', 'uf', 'padrao']
    list_filter = ['tipo', 'uf', 'padrao', 'preenchido_via_api']
    search_fields = ['armador__nome', 'cidade', 'logradouro']
    readonly_fields = ['data_cadastro', 'preenchido_via_api']


@admin.register(ArmadorContato)
class ArmadorContatoAdmin(admin.ModelAdmin):
    """Admin de Contatos do Armador"""
    list_display = ['armador', 'nome', 'get_tipo_display', 'telefone', 'email', 'preferencial']
    list_filter = ['tipo', 'preferencial', 'whatsapp']
    search_fields = ['armador__nome', 'nome', 'email', 'telefone']
    readonly_fields = ['data_cadastro']


@admin.register(ArmadorDadoBancario)
class ArmadorDadoBancarioAdmin(admin.ModelAdmin):
    """Admin de Contas Bancárias do Armador"""
    list_display = ['armador', 'nome_banco', 'agencia', 'conta', 'tipo_conta', 'tem_pix', 'padrao', 'ativo']
    list_filter = ['tem_pix', 'tipo_conta', 'ativo', 'padrao']
    search_fields = ['armador__nome', 'nome_banco', 'agencia', 'conta']
    readonly_fields = ['data_cadastro']
    
    fieldsets = (
        ('Armador', {
            'fields': ('armador',)
        }),
        ('Banco', {
            'fields': ('codigo_banco', 'nome_banco', 'agencia', 'agencia_dv', 'conta', 'conta_dv', 'tipo_conta')
        }),
        ('PIX', {
            'fields': ('tem_pix', 'tipo_pix', 'chave_pix')
        }),
        ('Titular', {
            'fields': ('nome_titular', 'cpf_cnpj_titular')
        }),
        ('Status', {
            'fields': ('padrao', 'ativo')
        }),
        ('Auditoria', {
            'fields': ('data_cadastro',),
            'classes': ('collapse',)
        }),
    )


@admin.register(Navio)
class NavioAdmin(admin.ModelAdmin):
    """Admin de Navios - RF-028"""
    list_display = [
        'nome', 'codigo', 'armador', 'tipo', 'capacidade_containers', 
        'bandeira', 'status', 'ativo'
    ]
    list_filter = ['tipo', 'status', 'ativo', 'empresa', 'bandeira']
    search_fields = ['nome', 'codigo', 'imo', 'armador__nome']
    readonly_fields = ['data_criacao', 'data_atualizacao']
    
    fieldsets = (
        ('Identificação', {
            'fields': ('empresa', 'codigo', 'nome', 'imo', 'bandeira', 'ativo')
        }),
        ('Armador', {
            'fields': ('armador',)
        }),
        ('Tipo e Capacidade', {
            'fields': ('tipo', 'capacidade_containers', 'capacidade_toneladas')
        }),
        ('Características Físicas', {
            'fields': ('ano_construcao', 'comprimento_metros', 'velocidade_media_nós'),
            'classes': ('collapse',)
        }),
        ('Operacional', {
            'fields': ('status', 'portos_operacao')
        }),
        ('Auditoria', {
            'fields': ('data_criacao', 'data_atualizacao'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        """Filtra por empresa se não for superusuário"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'empresa') and request.user.empresa:
            return qs.filter(empresa=request.user.empresa)
        return qs.none()


# ======================== MONITORAMENTO MIP (Manejo Integrado de Pragas) =====================

class PontoMonitoramentoInline(admin.TabularInline):
    """Inline para pontos de monitoramento (samplings 1-20)"""
    model = PontoMonitoramento
    extra = 0
    fields = [
        'numero_ponto', 'praga_presente', 'quantidade', 'estagio', 
        'severidade', 'latitude', 'longitude'
    ]
    readonly_fields = ['data_criacao']


class PragaNoMonitoramentoInline(admin.TabularInline):
    """Inline para pragas detectadas em um monitoramento"""
    model = PragaNoMonitoramento
    extra = 0
    fields = [
        'praga', 'quantidade_pontos_com_praga', 'incidencia_percentual',
        'severidade', 'estagio_principal', 'ned_atingido', 'resultado_acao'
    ]
    readonly_fields = ['incidencia_percentual', 'ned_atingido', 'resultado_acao', 'data_criacao', 'data_atualizacao']


@admin.register(EstagioDesenvolvimento)
class EstagioDesenvolvimentoAdmin(admin.ModelAdmin):
    """Admin para Estágios de Desenvolvimento de Pragas"""
    list_display = [
        'praga', 'tipo_estagio', 'ordem_ciclo', 'duracao_minima_dias',
        'duracao_maxima_dias', 'eh_fase_critica', 'empresa', 'eh_template_icon', 'ativo'
    ]
    list_filter = ['tipo_estagio', 'eh_fase_critica', 'ativo', 'empresa', 'praga', 'eh_template']
    search_fields = ['praga__nome', 'tipo_estagio', 'descricao']
    readonly_fields = ['data_criacao', 'data_atualizacao', 'template_original']
    
    fieldsets = (
        ('Identificação', {
            'fields': ('empresa', 'praga', 'tipo_estagio', 'ordem_ciclo', 'ativo')
        }),
        ('Descrição', {
            'fields': ('descricao',)
        }),
        ('Duração do Estágio', {
            'fields': ('duracao_minima_dias', 'duracao_maxima_dias')
        }),
        ('Características', {
            'fields': ('eh_fase_critica',)
        }),
        ('Templates', {
            'fields': ('eh_template', 'template_original'),
            'description': 'Marque "É Estágio Template?" para criar um template padrão que será copiado para novas empresas',
            'classes': ('collapse',)
        }),
        ('Observações', {
            'fields': ('observacoes',),
            'classes': ('collapse',)
        }),
        ('Auditoria', {
            'fields': ('data_criacao', 'data_atualizacao'),
            'classes': ('collapse',)
        }),
    )
    
    def eh_template_icon(self, obj):
        """Mostra ícone se é template"""
        if obj.eh_template:
            return '⭐ Template'
        elif obj.template_original:
            return '🔗 Cópia'
        return '-'
    eh_template_icon.short_description = 'Tipo'

    def get_queryset(self, request):
        """Filtra por empresa do usuário"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'empresa') and request.user.empresa:
            return qs.filter(empresa=request.user.empresa)
        return qs.none()


@admin.register(MonitoramentoMIP)
class MonitoramentoMIPAdmin(admin.ModelAdmin):
    """Admin para Monitoramentos MIP (Manejo Integrado de Pragas)"""
    list_display = [
        'numero', 'talhao', 'data_monitoramento', 'responsavel',
        'quantidade_pontos', 'status', 'empresa', 'data_criacao'
    ]
    list_filter = ['status', 'data_monitoramento', 'empresa', 'talhao', 'safra']
    search_fields = ['numero', 'talhao__nome', 'responsavel__username']
    readonly_fields = ['numero', 'data_criacao', 'data_atualizacao', 'criado_por']
    date_hierarchy = 'data_monitoramento'
    inlines = [PragaNoMonitoramentoInline]
    
    fieldsets = (
        ('Identificação', {
            'fields': ('numero', 'empresa', 'talhao', 'safra', 'cultura')
        }),
        ('Monitoramento', {
            'fields': (
                'data_monitoramento', 'responsavel', 'quantidade_pontos',
                'condicoes_tempo'
            )
        }),
        ('Condições Ambientais', {
            'fields': (
                'temperatura_media', 'umidade_media', 'velocidade_vento',
                'chuva_ultimas_24h'
            ),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('status',)
        }),
        ('Observações', {
            'fields': ('observacoes',),
            'classes': ('collapse',)
        }),
        ('Auditoria', {
            'fields': ('data_criacao', 'data_atualizacao', 'criado_por'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        """Filtra por empresa do usuário"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'empresa') and request.user.empresa:
            return qs.filter(empresa=request.user.empresa)
        return qs.none()

    def save_model(self, request, obj, form, change):
        """Atribui empresa e usuário na criação"""
        if not change:
            obj.empresa = request.user.empresa
            obj.criado_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(PragaNoMonitoramento)
class PragaNoMonitoramentoAdmin(admin.ModelAdmin):
    """Admin para Pragas Detectadas em Monitoramentos"""
    list_display = [
        'monitoramento', 'praga', 'incidencia_percentual', 'severidade',
        'ned_atingido', 'resultado_acao', 'estagio_principal'
    ]
    list_filter = ['ned_atingido', 'resultado_acao', 'severidade', 'monitoramento__data_monitoramento']
    search_fields = ['monitoramento__numero', 'praga__nome']
    readonly_fields = ['incidencia_percentual', 'ned_atingido', 'resultado_acao', 'data_criacao', 'data_atualizacao']
    inlines = [PontoMonitoramentoInline]
    
    fieldsets = (
        ('Identificação', {
            'fields': ('monitoramento', 'praga', 'estagio_principal')
        }),
        ('Sampling', {
            'fields': ('quantidade_pontos_com_praga',)
        }),
        ('Incidência', {
            'fields': ('incidencia_percentual',)
        }),
        ('Análise NED', {
            'fields': ('ned_atingido', 'resultado_acao')
        }),
        ('Severidade', {
            'fields': ('severidade', 'detalhes_estagios'),
            'classes': ('collapse',)
        }),
        ('Auditoria', {
            'fields': ('data_criacao', 'data_atualizacao'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        """Filtra por empresa do usuário"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'empresa') and request.user.empresa:
            return qs.filter(monitoramento__empresa=request.user.empresa)
        return qs.none()


@admin.register(PontoMonitoramento)
class PontoMonitoramentoAdmin(admin.ModelAdmin):
    """Admin para Pontos de Amostragem (Sampling Points)"""
    list_display = [
        'numero_ponto', 'praga_monitoramento', 'praga_presente',
        'quantidade', 'severidade', 'estagio', 'data_criacao'
    ]
    list_filter = ['praga_presente', 'severidade', 'numero_ponto']
    search_fields = ['praga_monitoramento__monitoramento__numero', 'praga_monitoramento__praga__nome']
    readonly_fields = ['data_criacao']
    
    fieldsets = (
        ('Ponto de Amostragem', {
            'fields': ('praga_monitoramento', 'numero_ponto', 'praga_presente')
        }),
        ('Dados da Praga', {
            'fields': ('quantidade', 'estagio', 'severidade')
        }),
        ('Localização', {
            'fields': ('latitude', 'longitude'),
            'classes': ('collapse',)
        }),
        ('Foto/Evidência', {
            'fields': ('foto',),
            'classes': ('collapse',)
        }),
        ('Auditoria', {
            'fields': ('data_criacao',),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        """Filtra por empresa do usuário"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'empresa') and request.user.empresa:
            return qs.filter(praga_monitoramento__monitoramento__empresa=request.user.empresa)
        return qs.none()


@admin.register(MotoristaVinculoPlaca)
class MotoristaVinculoPlacaAdmin(admin.ModelAdmin):
    list_display = ['motorista', 'placa_principal', 'data_inicio', 'data_fim', 'ativo', 'empresa']
    list_filter = ['empresa', 'ativo', 'data_inicio']
    search_fields = ['motorista__nome', 'placa_principal__placa']


class RequisicaoItemInline(admin.TabularInline):
    model = RequisicaoItem
    extra = 0
    fields = ['produto', 'unidade_medida', 'quantidade_solicitada', 'quantidade_atendida', 'custo_estimado']


@admin.register(Requisicao)
class RequisicaoAdmin(admin.ModelAdmin):
    list_display = ['numero', 'tipo', 'status', 'empresa', 'data_requisicao']
    list_filter = ['empresa', 'status', 'tipo']
    search_fields = ['numero', 'fazenda__nome', 'safra__nome']
    readonly_fields = ['data_requisicao', 'data_aprovacao']
    inlines = [RequisicaoItemInline]


class OSFuncionarioInline(admin.TabularInline):
    model = OSFuncionario
    extra = 0
    fields = ['funcionario', 'data_execucao', 'hora_inicio', 'hora_fim', 'observacoes']


class OSMaquinaInline(admin.TabularInline):
    model = OSMaquina
    extra = 0
    fields = [
        'veiculo', 'operador', 'data_execucao',
        'horimetro_inicial', 'horimetro_final', 'custo_hora_config',
    ]


@admin.register(CustoHoraMaquina)
class CustoHoraMaquinaAdmin(admin.ModelAdmin):
    list_display = [
        'veiculo', 'empresa', 'data_referencia', 'preco_combustivel',
        'reserva_manutencao_hora', 'horas_anuais_trabalho', 'ativo',
    ]
    list_filter = ['empresa', 'ativo', 'data_referencia']
    search_fields = ['veiculo__marca', 'veiculo__modelo', 'veiculo__descricao']
    readonly_fields = ['data_cadastro', 'data_atualizacao']


@admin.register(OrdemServico)
class OrdemServicoAdmin(admin.ModelAdmin):
    list_display = [
        'numero', 'descricao_servico', 'status', 'talhao', 'safra', 'responsavel',
        'empresa', 'data_prevista', 'data_cadastro',
    ]
    list_filter = ['empresa', 'status', 'tipo_servico', 'data_prevista']
    search_fields = ['numero', 'talhao__nome', 'safra__nome', 'responsavel__nome_completo']
    readonly_fields = ['numero', 'data_cadastro', 'data_atualizacao', 'data_aprovacao']
    inlines = [OSFuncionarioInline, OSMaquinaInline]


@admin.register(CustoTalhao)
class CustoTalhaoAdmin(admin.ModelAdmin):
    list_display = [
        'os', 'talhao', 'safra', 'empresa',
        'custo_mao_obra', 'custo_maquinario', 'custo_insumos', 'custo_servico_externo',
    ]
    list_filter = ['empresa', 'safra']
    search_fields = ['os__numero', 'talhao__nome', 'safra__nome']
    readonly_fields = ['data_registro', 'data_atualizacao']


# ---------------------------------------------------------------------------
# Admin: Classificação estruturada de OS
# ---------------------------------------------------------------------------

class SubtipoServicoOSInline(admin.TabularInline):
    model = SubtipoServicoOS
    extra = 1
    fields = ['nome', 'descricao', 'empresa', 'ordem', 'ativo']


@admin.register(TipoServicoOS)
class TipoServicoOSAdmin(admin.ModelAdmin):
    list_display = ['nome', 'empresa', 'tipo_legado', 'ordem', 'ativo']
    list_filter = ['ativo', 'empresa']
    search_fields = ['nome']
    inlines = [SubtipoServicoOSInline]


@admin.register(SubtipoServicoOS)
class SubtipoServicoOSAdmin(admin.ModelAdmin):
    list_display = ['nome', 'tipo_servico', 'empresa', 'ordem', 'ativo']
    list_filter = ['tipo_servico', 'ativo', 'empresa']
    search_fields = ['nome']


@admin.register(ModalidadeExecucaoOS)
class ModalidadeExecucaoOSAdmin(admin.ModelAdmin):
    list_display = ['nome', 'empresa', 'ordem', 'ativo']
    list_filter = ['ativo', 'empresa']
    search_fields = ['nome']