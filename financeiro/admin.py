from django.contrib import admin
from django.utils.html import format_html
from .models import (
    FormaPagemento,
    ConfiguracaoJurosMulta, 
    ContaPagar, 
    ParcelaContaPagar, 
    PagamentoContaPagar, 
    AjusteContaPagar
)


# ============================================
# ADMIN REGISTRATIONS
# ============================================

@admin.register(FormaPagemento)
class FormaPagementoAdmin(admin.ModelAdmin):
    """Admin para formas de pagamento"""
    list_display = ('nome', 'ativo', 'dias_processamento', 'taxa_administrativa', 'ordem_exibicao')
    list_filter = ('ativo', 'dias_processamento')
    search_fields = ('nome', 'descricao')
    list_editable = ('ativo', 'ordem_exibicao')
    ordering = ('ordem_exibicao',)
    
    fieldsets = (
        ('Identificação', {
            'fields': ('nome', 'ativo')
        }),
        ('Descrição', {
            'fields': ('descricao',),
            'classes': ('wide',)
        }),
        ('Configuração', {
            'fields': ('dias_processamento', 'taxa_administrativa', 'ordem_exibicao'),
            'description': 'Configurações técnicas da forma de pagamento'
        }),
    )


@admin.register(ConfiguracaoJurosMulta)
class ConfiguracaoJurosMultaAdmin(admin.ModelAdmin):
    """Admin para configuração de juros e multa por empresa"""
    list_display = ('empresa', 'taxa_juros_mensal', 'multa_atraso', 'tipo_multa', 'dias_tolerancia', 'ativo')
    list_filter = ('ativo', 'tipo_multa', 'empresa')
    search_fields = ('empresa__nome',)
    readonly_fields = ('data_atualizacao',)
    
    fieldsets = (
        ('Identificação', {
            'fields': ('empresa',)
        }),
        ('Configuração de Juros', {
            'fields': ('taxa_juros_mensal',),
            'description': 'Taxa mensal aplica a atrasos nas parcelas'
        }),
        ('Configuração de Multa', {
            'fields': ('multa_atraso', 'tipo_multa'),
            'description': 'Multa por atraso (percentual ou valor fixo)'
        }),
        ('Tolerância', {
            'fields': ('dias_tolerancia',),
            'description': 'Dias permitidos após vencimento sem cobrança'
        }),
        ('Auditoria', {
            'fields': ('ativo', 'data_atualizacao'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ContaPagar)
class ContaPageAdmin(admin.ModelAdmin):
    """Admin para contas a pagar (principal)"""
    list_display = ('numero', 'fornecedor_link', 'valor_total', 'status', 'dias_ate_proxima_parcela', 'requer_aprovacao')
    list_filter = ('status', 'empresa', 'data_emissao', 'requer_aprovacao')
    search_fields = ('numero', 'fornecedor__nome')
    readonly_fields = ('numero', 'valor_total', 'juros_acumulados', 'multa_acumulada', 'data_criacao', 'data_atualizacao', 'valor_ajustado')
    date_hierarchy = 'data_emissao'
    
    fieldsets = (
        ('Identificação', {
            'fields': ('numero', 'empresa', 'fornecedor')
        }),
        ('Recebimento Origem', {
            'fields': ('recebimento',),
            'classes': ('collapse',)
        }),
        ('Valores', {
            'fields': (
                'valor_total',
                'desconto_negociado',
                'valor_ajustado',
                'juros_acumulados',
                'multa_acumulada'
            )
        }),
        ('Status e Aprovação', {
            'fields': (
                'status',
                'requer_aprovacao',
                'aprovado_por',
                'data_aprovacao'
            ),
            'classes': ('collapse',)
        }),
        ('Datas', {
            'fields': ('data_emissao',),
            'classes': ('collapse',)
        }),
        ('Observações', {
            'fields': ('observacoes',)
        }),
        ('Auditoria', {
            'fields': ('criado_por', 'data_criacao', 'data_atualizacao'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = []  # Será definido depois
    
    def fornecedor_link(self, obj):
        return obj.fornecedor.nome
    fornecedor_link.short_description = 'Fornecedor'
    
    def dias_ate_proxima_parcela(self, obj):
        """Mostrar dias até a próxima parcela vencer"""
        proxima = obj.parcelas.filter(status__in=['ABERTA', 'VENCIDA']).order_by('data_vencimento').first()
        if proxima:
            from django.utils import timezone
            dias = (proxima.data_vencimento - timezone.now().date()).days
            if dias < 0:
                return format_html('<span style="color: red;"><b>{} dias (VENCIDA)</b></span>', abs(dias))
            elif dias <= 7:
                return format_html('<span style="color: orange;"><b>{} dias</b></span>', dias)
            else:
                return format_html('<span style="color: green;">{} dias</span>', dias)
        return '-'
    dias_ate_proxima_parcela.short_description = 'Próxima Parcela'


@admin.register(ParcelaContaPagar)
class ParcelaContaPageAdmin(admin.ModelAdmin):
    """Admin para parcelas de contas a pagar"""
    list_display = ('conta_pagar', 'numero_parcela', 'valor_parcela', 'data_vencimento', 'status', 'dias_atraso', 'valor_com_juros')
    list_filter = ('status', 'data_vencimento', 'conta_pagar__empresa')
    search_fields = ('conta_pagar__numero', 'conta_pagar__fornecedor__nome')
    readonly_fields = ('dias_atraso', 'juros_parcela', 'multa_parcela', 'valor_total_parcela', 'data_criacao', 'data_atualizacao')
    date_hierarchy = 'data_vencimento'
    
    fieldsets = (
        ('Identificação', {
            'fields': ('conta_pagar', 'numero_parcela')
        }),
        ('Valores da Parcela', {
            'fields': ('valor_parcela', 'juros_parcela', 'multa_parcela', 'valor_total_parcela')
        }),
        ('Datas', {
            'fields': ('data_vencimento', 'data_pagamento', 'dias_atraso')
        }),
        ('Status', {
            'fields': ('status',)
        }),
        ('Observações', {
            'fields': ('observacao',)
        }),
        ('Auditoria', {
            'fields': ('data_criacao', 'data_atualizacao'),
            'classes': ('collapse',)
        }),
    )
    
    def valor_com_juros(self, obj):
        return f"R$ {obj.valor_total_parcela:.2f}"
    valor_com_juros.short_description = 'Total (Parcela + Juros + Multa)'


@admin.register(PagamentoContaPagar)
class PagamentoContaPageAdmin(admin.ModelAdmin):
    """Admin para pagamentos de contas"""
    list_display = ('id', 'parcela_display', 'valor_pago', 'forma_pagamento', 'data_pagamento', 'status', 'comprovante_link')
    list_filter = ('status', 'forma_pagamento', 'data_pagamento', 'conta_pagar__empresa')
    search_fields = ('numero_documento', 'conta_pagar__numero', 'parcela__conta_pagar__fornecedor__nome')
    readonly_fields = ('conta_pagar', 'data_criacao')
    date_hierarchy = 'data_pagamento'
    
    fieldsets = (
        ('Identificação', {
            'fields': ('parcela', 'conta_pagar', 'pago_por')
        }),
        ('Valores', {
            'fields': ('valor_pago',)
        }),
        ('Método de Pagamento', {
            'fields': ('forma_pagamento', 'numero_documento', 'banco')
        }),
        ('Datas', {
            'fields': ('data_pagamento', 'data_compensacao')
        }),
        ('Status', {
            'fields': ('status',)
        }),
        ('Comprovante', {
            'fields': ('comprovante',),
            'classes': ('collapse',)
        }),
        ('Observações', {
            'fields': ('observacao',)
        }),
        ('Auditoria', {
            'fields': ('data_criacao',),
            'classes': ('collapse',)
        }),
    )
    
    def parcela_display(self, obj):
        return f"{obj.parcela.conta_pagar.numero} - Parcela {obj.parcela.numero_parcela}"
    parcela_display.short_description = 'Parcela'
    
    def comprovante_link(self, obj):
        if obj.comprovante:
            return format_html('<a href="{}">{}</a>', obj.comprovante.url, 'Baixar')
        return '-'
    comprovante_link.short_description = 'Comprovante'


@admin.register(AjusteContaPagar)
class AjusteContaPageAdmin(admin.ModelAdmin):
    """Admin para ajustes de contas"""
    list_display = ('conta_pagar', 'tipo', 'valor_ajuste', 'motivo', 'aprovado')
    list_filter = ('tipo', 'aprovado', 'data_criacao', 'conta_pagar__empresa')
    search_fields = ('conta_pagar__numero', 'motivo')
    readonly_fields = ('data_criacao', 'data_atualizacao')
    
    fieldsets = (
        ('Identificação', {
            'fields': ('conta_pagar', 'tipo')
        }),
        ('Ajuste', {
            'fields': ('valor_ajuste', 'motivo')
        }),
        ('Divergência Associada', {
            'fields': ('divergencia',),
            'classes': ('collapse',)
        }),
        ('Aprovação', {
            'fields': ('aprovado', 'aprovado_por'),
            'classes': ('collapse',)
        }),
        ('Observações', {
            'fields': ('observacao',)
        }),
        ('Auditoria', {
            'fields': ('data_criacao', 'data_atualizacao'),
            'classes': ('collapse',)
        }),
    )
