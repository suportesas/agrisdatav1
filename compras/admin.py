"""
Admin para o módulo de Compras
"""
from django.contrib import admin
from .models import (
    SolicitacaoCompra,
    ItemSolicitacaoCompra,
    Cotacao,
    ItemCotacao,
    FornecedorCotacao,
    RecebimentoCompra,
    ItemRecebimento,
    TipoDivergencia,
    DivergenciaRecebimento,
    AvaliacaoFornecedor,
)


class ItemSolicitacaoInline(admin.TabularInline):
    model = ItemSolicitacaoCompra
    extra = 1
    fields = ['produto', 'quantidade', 'unidade_medida', 'status_item', 'selecionado_para_cotar']


@admin.register(SolicitacaoCompra)
class SolicitacaoCompraAdmin(admin.ModelAdmin):
    list_display = ['numero', 'empresa', 'solicitante', 'data_solicitacao', 'data_necessidade', 'status', 'emergencial']
    list_filter = ['status', 'emergencial', 'empresa', 'data_solicitacao']
    search_fields = ['numero', 'solicitante__username', 'justificativa']
    readonly_fields = ['numero', 'data_cadastro', 'data_atualizacao']
    inlines = [ItemSolicitacaoInline]
    
    fieldsets = (
        ('Identificação', {
            'fields': ('numero', 'empresa', 'solicitante')
        }),
        ('Datas', {
            'fields': ('data_solicitacao', 'data_necessidade')
        }),
        ('Status', {
            'fields': ('status', 'aprovador', 'data_aprovacao')
        }),
        ('Emergencial', {
            'fields': ('emergencial', 'justificativa_emergencial'),
            'classes': ('collapse',),
            'description': 'Compras emergenciais são aprovadas automaticamente'
        }),
        ('Informações', {
            'fields': ('justificativa', 'departamento', 'observacoes')
        }),
        ('Auditoria', {
            'fields': ('data_cadastro', 'data_atualizacao'),
            'classes': ('collapse',)
        }),
    )


class ItemCotacaoInline(admin.TabularInline):
    model = ItemCotacao
    extra = 0
    fields = ['produto', 'quantidade', 'unidade_medida']


@admin.register(Cotacao)
class CotacaoAdmin(admin.ModelAdmin):
    list_display = ['numero', 'empresa', 'solicitacao', 'comprador', 'data_cotacao', 'status']
    list_filter = ['status', 'empresa', 'data_cotacao']
    search_fields = ['numero', 'solicitacao__numero']
    readonly_fields = ['numero', 'data_cadastro']
    inlines = [ItemCotacaoInline]
    
    fieldsets = (
        ('Identificação', {
            'fields': ('numero', 'empresa', 'solicitacao', 'comprador')
        }),
        ('Datas', {
            'fields': ('data_cotacao', 'data_limite_resposta', 'data_conclusao')
        }),
        ('Status', {
            'fields': ('status',)
        }),
        ('Observações', {
            'fields': ('observacoes',)
        }),
    )


class FornecedorCotacaoInline(admin.TabularInline):
    model = FornecedorCotacao
    extra = 1
    fields = ['fornecedor', 'preco_unitario', 'prazo_entrega', 'selecionado']


@admin.register(ItemCotacao)
class ItemCotacaoAdmin(admin.ModelAdmin):
    list_display = ['cotacao', 'produto', 'quantidade', 'unidade_medida']
    list_filter = ['cotacao__status']
    search_fields = ['produto__nome', 'cotacao__numero']
    inlines = [FornecedorCotacaoInline]


@admin.register(FornecedorCotacao)
class FornecedorCotacaoAdmin(admin.ModelAdmin):
    list_display = ['item_cotacao', 'fornecedor', 'preco_unitario', 'preco_total', 'prazo_entrega', 'selecionado']
    list_filter = ['selecionado', 'fornecedor']
    search_fields = ['fornecedor__nome_fantasia', 'item_cotacao__produto__nome']


class ItemRecebimentoInline(admin.TabularInline):
    model = ItemRecebimento
    extra = 0
    fk_name = 'recebimento'
    fields = ['get_produto', 'quantidade_recebida', 'local_estoque', 'lote']
    readonly_fields = ['get_produto']
    
    def get_produto(self, obj):
        if obj.item_pedido:
            return obj.item_pedido.produto.nome
        elif obj.produto:
            return obj.produto.nome
        return '-'
    get_produto.short_description = 'Produto'


@admin.register(RecebimentoCompra)
class RecebimentoCompraAdmin(admin.ModelAdmin):
    list_display = ['numero', 'pedido', 'nota_fiscal', 'data_recebimento', 'status', 'recebido_por']
    list_filter = ['status', 'data_recebimento', 'empresa']
    search_fields = ['numero', 'nota_fiscal', 'pedido__numero']
    readonly_fields = ['numero', 'data_cadastro', 'data_atualizacao']
    inlines = [ItemRecebimentoInline]
    
    fieldsets = (
        ('Identificação', {
            'fields': ('numero', 'empresa', 'pedido', 'status')
        }),
        ('Nota Fiscal', {
            'fields': ('nota_fiscal', 'serie_nota', 'chave_nfe', 'data_emissao_nf', 'valor_total_nf', 'arquivo_nfe')
        }),
        ('Recebimento', {
            'fields': ('data_recebimento', 'hora_recebimento', 'recebido_por')
        }),
        ('Observações', {
            'fields': ('observacoes', 'divergencias')
        }),
        ('Auditoria', {
            'fields': ('data_cadastro', 'data_atualizacao'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ItemRecebimento)
class ItemRecebimentoAdmin(admin.ModelAdmin):
    list_display = ['recebimento', 'item_pedido', 'quantidade_recebida', 'local_estoque', 'lote']
    list_filter = ['local_estoque', 'data_cadastro']
    search_fields = ['item_pedido__produto__nome', 'lote', 'recebimento__numero']


@admin.register(TipoDivergencia)
class TipoDivergenciaAdmin(admin.ModelAdmin):
    """Admin para CRUD de Tipos de Divergência"""
    list_display = ['codigo', 'nome', 'severidade', 'gera_valor_pedido_completo', 'ativo', 'empresa']
    list_filter = ['severidade', 'gera_valor_pedido_completo', 'ativo', 'empresa', 'data_criacao']
    search_fields = ['codigo', 'nome', 'descricao']
    readonly_fields = ['data_criacao', 'data_atualizacao']

    fieldsets = (
        ('Identificação', {
            'fields': ('empresa', 'codigo', 'nome')
        }),
        ('Detalhes', {
            'fields': ('descricao', 'severidade', 'ativo', 'gera_valor_pedido_completo')
        }),
        ('Auditoria', {
            'fields': ('data_criacao', 'data_atualizacao'),
            'classes': ('collapse',)
        }),
    )


class DivergenciaRecebimentoInline(admin.TabularInline):
    model = DivergenciaRecebimento
    extra = 0
    fields = ['tipo_divergencia', 'item_recebimento', 'quantidade_afetada', 'status_divergencia']
    readonly_fields = ['data_criacao']


@admin.register(DivergenciaRecebimento)
class DivergenciaRecebimentoAdmin(admin.ModelAdmin):
    """Admin para Divergências de Recebimento"""
    list_display = ['recebimento', 'tipo_divergencia', 'status_divergencia', 'registrado_por', 'data_criacao']
    list_filter = ['status_divergencia', 'tipo_divergencia__severidade', 'data_criacao']
    search_fields = ['recebimento__numero', 'descricao_detalhes']
    readonly_fields = ['data_criacao', 'data_atualizacao', 'registrado_por']
    
    fieldsets = (
        ('Recebimento', {
            'fields': ('recebimento', 'item_recebimento')
        }),
        ('Tipo de Divergência', {
            'fields': ('tipo_divergencia', 'quantidade_afetada')
        }),
        ('Descrição', {
            'fields': ('descricao_detalhes', 'acao_proposta')
        }),
        ('Fotos/Evidências', {
            'fields': ('foto_1', 'foto_2'),
            'classes': ('collapse',)
        }),
        ('Resolução', {
            'fields': ('status_divergencia', 'data_resolucao', 'descricao_resolucao')
        }),
        ('Auditoria', {
            'fields': ('registrado_por', 'data_criacao', 'data_atualizacao'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not obj.registrado_por_id:
            obj.registrado_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(AvaliacaoFornecedor)
class AvaliacaoFornecedorAdmin(admin.ModelAdmin):
    """Admin para Avaliações de Fornecedor"""
    list_display = ['fornecedor', 'recebimento', 'nota_media', 'recomenda', 'avaliador', 'data_avaliacao']
    list_filter = ['nota_media', 'recomenda', 'data_avaliacao', 'empresa']
    search_fields = ['fornecedor__nome', 'recebimento__numero']
    readonly_fields = ['nota_media', 'data_avaliacao', 'avaliador']
    
    fieldsets = (
        ('Identificação', {
            'fields': ('empresa', 'recebimento', 'fornecedor', 'avaliador')
        }),
        ('Critérios de Avaliação', {
            'fields': ('qualidade_produto', 'prazo_entrega', 'documentacao', 'atendimento', 'preco', 'nota_media'),
            'description': 'Avalie em escala de 1 a 5 estrelas'
        }),
        ('Comentários', {
            'fields': ('pontos_positivos', 'pontos_negativos', 'recomendacao')
        }),
        ('Recomendação', {
            'fields': ('recomenda',)
        }),
        ('Auditoria', {
            'fields': ('data_avaliacao',),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not obj.avaliador_id:
            obj.avaliador = request.user
        super().save_model(request, obj, form, change)

