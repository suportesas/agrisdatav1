from django.contrib import admin
from .models import ConsumoRecurso, Alerta, MetricaDiaria, LogAcesso


@admin.register(ConsumoRecurso)
class ConsumoRecursoAdmin(admin.ModelAdmin):
    """Admin para ConsumoRecurso"""
    
    list_display = [
        'empresa', 'fazendas_usadas', 'percentual_fazendas',
        'usuarios_ativos', 'percentual_usuarios',
        'alerta_fazendas', 'alerta_usuarios', 'data_calculo'
    ]
    
    list_filter = [
        'alerta_fazendas', 'alerta_usuarios', 'alerta_talhoes', 'alerta_produtos',
        'data_calculo'
    ]
    
    search_fields = ['empresa__nome']
    
    readonly_fields = ['data_calculo']
    
    fieldsets = (
        ('Empresa', {
            'fields': ('empresa',)
        }),
        ('Consumo Atual', {
            'fields': ('fazendas_usadas', 'usuarios_ativos', 'talhoes_cadastrados', 'produtos_cadastrados')
        }),
        ('Limites do Plano', {
            'fields': ('limite_fazendas', 'limite_usuarios', 'limite_talhoes', 'limite_produtos'),
            'classes': ('collapse',)
        }),
        ('Percentuais', {
            'fields': ('percentual_fazendas', 'percentual_usuarios', 'percentual_talhoes', 'percentual_produtos'),
            'classes': ('collapse',)
        }),
        ('Alertas', {
            'fields': ('alerta_fazendas', 'alerta_usuarios', 'alerta_talhoes', 'alerta_produtos')
        }),
        ('Auditoria', {
            'fields': ('data_calculo',),
            'classes': ('collapse',)
        }),
    )


@admin.register(Alerta)
class AlertaAdmin(admin.ModelAdmin):
    """Admin para Alerta"""
    
    list_display = [
        'get_severidade_badge', 'get_tipo_badge', 'titulo',
        'empresa', 'ativo', 'lido', 'data_criacao'
    ]
    
    list_filter = [
        'severidade', 'tipo', 'ativo', 'lido', 'data_criacao'
    ]
    
    search_fields = ['titulo', 'descricao', 'empresa__nome']
    
    readonly_fields = ['data_criacao', 'data_leitura']
    
    fieldsets = (
        ('Identificação', {
            'fields': ('tipo', 'severidade', 'titulo')
        }),
        ('Conteúdo', {
            'fields': ('descricao',)
        }),
        ('Empresa', {
            'fields': ('empresa',),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('ativo', 'lido')
        }),
        ('Auditoria', {
            'fields': ('data_criacao', 'data_leitura'),
            'classes': ('collapse',)
        }),
    )
    
    def get_severidade_badge(self, obj):
        """Exibe severidade com cores"""
        cores = {
            'BAIXA': 'green',
            'MÉDIA': 'orange',
            'ALTA': 'red',
            'CRÍTICA': 'darkred',
        }
        cor = cores.get(obj.severidade, 'gray')
        return f'<span style="background-color: {cor}; color: white; padding: 3px 8px; border-radius: 3px;">{obj.get_severidade_display()}</span>'
    get_severidade_badge.short_description = 'Severidade'
    get_severidade_badge.allow_tags = True
    
    def get_tipo_badge(self, obj):
        """Exibe tipo com ícone"""
        icons = {
            'LIMITE_PROXIMO': '⚠️',
            'LIMITE_ATINGIDO': '⛔',
            'LIMITE_EXCEDIDO': '🚫',
            'VENCIMENTO': '⏰',
            'PAGAMENTO_PENDENTE': '💳',
            'ERRO_SISTEMA': '❌',
            'PERFORMANCE': '🐢',
        }
        icon = icons.get(obj.tipo, '❓')
        return f'{icon} {obj.get_tipo_display()}'
    get_tipo_badge.short_description = 'Tipo'


@admin.register(MetricaDiaria)
class MetricaDiariaAdmin(admin.ModelAdmin):
    """Admin para MetricaDiaria"""
    
    list_display = [
        'data', 'total_empresas', 'total_usuarios',
        'receita_total', 'alertas_ativos', 'alertas_criticos'
    ]
    
    list_filter = ['data']
    
    date_hierarchy = 'data'
    
    readonly_fields = ['data']
    
    fieldsets = (
        ('Data', {
            'fields': ('data',)
        }),
        ('Contadores', {
            'fields': ('total_empresas', 'total_empresas_ativas', 'total_usuarios', 'total_usuarios_ativos')
        }),
        ('Distribuição por Plano', {
            'fields': ('empresas_pequeno', 'empresas_medio', 'empresas_grande', 'empresas_enterprise'),
            'classes': ('collapse',)
        }),
        ('Financeiro', {
            'fields': ('receita_total',)
        }),
        ('Alertas', {
            'fields': ('alertas_ativos', 'alertas_criticos')
        }),
    )


@admin.register(LogAcesso)
class LogAcessoAdmin(admin.ModelAdmin):
    """Admin para LogAcesso"""
    
    list_display = [
        'usuario', 'modulo', 'ip_address', 'data_acesso'
    ]
    
    list_filter = ['modulo', 'data_acesso', 'usuario']
    
    search_fields = ['usuario__username', 'ip_address']
    
    readonly_fields = ['usuario', 'modulo', 'ip_address', 'user_agent', 'data_acesso']
    
    fieldsets = (
        ('Usuário', {
            'fields': ('usuario', 'ip_address')
        }),
        ('Acesso', {
            'fields': ('modulo', 'data_acesso')
        }),
        ('Agente', {
            'fields': ('user_agent',),
            'classes': ('collapse',)
        }),
    )
    
    can_delete = False
    can_add = False
