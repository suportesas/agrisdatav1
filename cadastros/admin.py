"""
Admin do módulo Fazendas e Culturas
"""

from django.contrib import admin
from .models import (
    Fazenda, EnderecoFazenda, ContatoFazenda,
    ContaBancariaFazenda, DocumentoFazenda, Cultura
)
from .models import Area, Talhao, HistoricoTalhao, Safra, SafraPlan, SafraReal
from .models import Vendedor, ComissaoVendedor

from .models import Fornecedor, FornecedorEndereco, FornecedorContato, FornecedorDadoBancario

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


@admin.register(Safra)
class SafraAdmin(admin.ModelAdmin):
    list_display = ['nome', 'fazenda', 'cultura', 'ano', 'status']
    list_filter = ['status', 'fazenda', 'cultura', 'ano']
    search_fields = ['nome', 'fazenda__nome', 'cultura__nome']


@admin.register(SafraPlan)
class SafraPlanAdmin(admin.ModelAdmin):
    list_display = ['safra', 'planned_production', 'planned_area', 'planned_plantio', 'planned_colheita']
    search_fields = ['safra__nome', 'safra__fazenda__nome']


@admin.register(SafraReal)
class SafraRealAdmin(admin.ModelAdmin):
    list_display = ['safra', 'talhao', 'production', 'plantio_real', 'colheita_real', 'source']
    list_filter = ['source']
    search_fields = ['safra__nome', 'talhao__nome']





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


@admin.register(FornecedorEndereco)
class FornecedorEnderecoAdmin(admin.ModelAdmin):
    """Admin de Endereços do Fornecedor"""
    list_display = ['fornecedor', 'get_tipo_display', 'cidade', 'uf', 'padrao']
    list_filter = ['tipo', 'uf', 'padrao']
    search_fields = ['fornecedor__nome', 'cidade', 'logradouro']
    readonly_fields = ['data_cadastro']
