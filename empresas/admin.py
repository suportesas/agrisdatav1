"""
Admin do app empresas
Configuração do painel administrativo
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import Empresa, Plano, Role, RoleAudit, PermissionTemplate


@admin.register(Plano)
class PlanoAdmin(admin.ModelAdmin):
    """Admin para modelo Plano"""
    
    list_display = [
        'get_icone_nome', 'codigo', 'valor_mensal', 'valor_anual',
        'get_total_empresas', 'ativo_badge', 'ordem'
    ]
    
    list_filter = ['ativo', 'codigo']
    
    search_fields = ['nome', 'codigo', 'descricao']
    
    ordering = ['ordem', 'codigo']
    
    list_per_page = 20
    
    fieldsets = (
        ('Identificação', {
            'fields': ('codigo', 'nome', 'icone', 'ordem', 'ativo')
        }),
        ('Valores', {
            'fields': ('valor_mensal', 'valor_anual', 'desconto_anual')
        }),
        ('Limites', {
            'fields': (
                'limite_fazendas', 'limite_usuarios',
                'limite_talhoes', 'limite_produtos'
            )
        }),
        ('Recursos', {
            'fields': (
                'acesso_relatorios_avancados', 'acesso_api',
                'acesso_app_mobile', 'acesso_suporte_prioritario'
            )
        }),
        ('Descrição', {
            'fields': ('descricao',),
            'classes': ('collapse',)
        }),
        ('Auditoria', {
            'fields': ('data_criacao', 'data_atualizacao'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['data_criacao', 'data_atualizacao']
    
    def get_icone_nome(self, obj):
        """Exibe ícone e nome"""
        return f"{obj.icone} {obj.nome}"
    get_icone_nome.short_description = 'Plano'
    
    def ativo_badge(self, obj):
        """Badge para status ativo"""
        if obj.ativo:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Ativo</span>'
            )
        return format_html(
            '<span style="color: gray; font-weight: bold;">✗ Inativo</span>'
        )
    ativo_badge.short_description = 'Status'
    
    def get_total_empresas(self, obj):
        """Total de empresas usando o plano"""
        total = obj.get_total_empresas()
        if total > 0:
            return format_html(
                '<span style="font-weight: bold; color: blue;">{}</span>',
                total
            )
        return '0'
    get_total_empresas.short_description = 'Empresas'


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    """Admin para modelo Empresa"""
    
    list_display = [
        'nome', 'get_cnpj', 'plano', 'get_status',
        'get_usuarios_count', 'data_expiracao', 'data_criacao'
    ]
    
    list_filter = [
        'ativa', 'bloqueada', 'plano',
        'acesso_api', 'acesso_app_mobile',
        'data_criacao'
    ]
    
    search_fields = ['nome', 'cnpj', 'email', 'cidade', 'uf']
    
    ordering = ['-data_criacao']
    
    list_per_page = 50
    
    date_hierarchy = 'data_criacao'
    
    readonly_fields = [
        'data_criacao', 'data_ultima_atualizacao',
        'get_status_display', 'get_dias_vencimento'
    ]
    
    fieldsets = (
        ('Dados Básicos', {
            'fields': (
                'nome', 'cnpj', 'telefone', 'email'
            )
        }),
        ('Endereço', {
            'fields': ('endereco', 'cidade', 'uf'),
            'classes': ('collapse',)
        }),
        ('Plano e Limites', {
            'fields': (
                'plano',
                ('limite_fazendas', 'limite_usuarios'),
                ('limite_talhoes', 'limite_produtos'),
            )
        }),
        ('Recursos', {
            'fields': (
                'acesso_relatorios_avancados',
                'acesso_api',
                'acesso_app_mobile',
            )
        }),
        ('Financeiro', {
            'fields': (
                'valor_mensalidade',
                'dia_vencimento',
                'data_expiracao',
                'get_dias_vencimento',
            )
        }),
        ('Status', {
            'fields': (
                'ativa',
                'bloqueada',
                'bloqueada_ate',
                'motivo_bloqueio',
                'get_status_display',
            )
        }),
        ('Auditoria', {
            'fields': (
                'data_criacao',
                'data_ultima_atualizacao',
            ),
            'classes': ('collapse',)
        }),
    )
    
    actions = [
        'bloquear_empresas',
        'desbloquear_empresas',
        'ativar_empresas',
        'desativar_empresas',
        'aplicar_limites_plano'
    ]
    
    def get_cnpj(self, obj):
        """CNPJ formatado"""
        return obj.get_cnpj_formatado() or '-'
    get_cnpj.short_description = 'CNPJ'
    
    def get_status(self, obj):
        """Badge de status"""
        status = obj.get_status_display()
        
        cores = {
            'Ativa': 'green',
            'Bloqueada': 'red',
            'Expirada': 'orange',
            'Inativa': 'gray'
        }
        
        cor = cores.get(status, 'black')
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            cor, status
        )
    get_status.short_description = 'Status'
    
    def get_usuarios_count(self, obj):
        """Total de usuários"""
        total = obj.get_total_usuarios()
        limite = obj.limite_usuarios
        
        if limite >= 999:
            return f"{total} / ∞"
        
        # Cor baseada na ocupação
        percentual = (total / limite * 100) if limite > 0 else 0
        if percentual >= 90:
            cor = 'red'
        elif percentual >= 70:
            cor = 'orange'
        else:
            cor = 'green'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} / {}</span>',
            cor, total, limite
        )
    get_usuarios_count.short_description = 'Usuários'
    
    def get_dias_vencimento(self, obj):
        """Dias para vencimento"""
        dias = obj.get_dias_para_vencimento()
        if dias is None:
            return 'Sem data de expiração'
        
        if dias < 0:
            return format_html(
                '<span style="color: red; font-weight: bold;">Expirado há {} dias</span>',
                abs(dias)
            )
        elif dias == 0:
            return format_html(
                '<span style="color: red; font-weight: bold;">Expira hoje!</span>'
            )
        elif dias <= 7:
            return format_html(
                '<span style="color: orange; font-weight: bold;">{} dias</span>',
                dias
            )
        else:
            return f"{dias} dias"
    get_dias_vencimento.short_description = 'Vence em'
    
    @admin.action(description="Bloquear empresas selecionadas")
    def bloquear_empresas(self, request, queryset):
        """Bloqueia empresas selecionadas"""
        for empresa in queryset:
            empresa.bloqueada = True
            empresa.motivo_bloqueio = "Bloqueada manualmente pelo administrador"
            empresa.save()
        
        self.message_user(
            request,
            f"{queryset.count()} empresa(s) bloqueada(s) com sucesso."
        )
    
    @admin.action(description="Desbloquear empresas selecionadas")
    def desbloquear_empresas(self, request, queryset):
        """Desbloqueia empresas selecionadas"""
        for empresa in queryset:
            empresa.bloqueada = False
            empresa.bloqueada_ate = None
            empresa.motivo_bloqueio = ""
            empresa.save()
        
        self.message_user(
            request,
            f"{queryset.count()} empresa(s) desbloqueada(s) com sucesso."
        )
    
    @admin.action(description="Ativar empresas selecionadas")
    def ativar_empresas(self, request, queryset):
        """Ativa empresas selecionadas"""
        queryset.update(ativa=True)
        self.message_user(
            request,
            f"{queryset.count()} empresa(s) ativada(s) com sucesso."
        )
    
    @admin.action(description="Desativar empresas selecionadas")
    def desativar_empresas(self, request, queryset):
        """Desativa empresas selecionadas"""
        queryset.update(ativa=False)
        self.message_user(
            request,
            f"{queryset.count()} empresa(s) desativada(s) com sucesso."
        )
    
    @admin.action(description="Aplicar limites do plano")
    def aplicar_limites_plano(self, request, queryset):
        """Reaplica limites do plano para empresas selecionadas"""
        for empresa in queryset:
            empresa.aplicar_limites_plano()
            empresa.save()
        
        self.message_user(
            request,
            f"Limites do plano aplicados para {queryset.count()} empresa(s)."
        )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """Admin para funções (roles) de empresas"""

    list_display = ['name', 'empresa', 'builtin', 'data_criacao']
    list_filter = ['empresa', 'builtin']
    search_fields = ['name', 'empresa__nome']
    ordering = ['empresa__nome', 'name']
    readonly_fields = ['data_criacao', 'data_atualizacao']


@admin.register(RoleAudit)
class RoleAuditAdmin(admin.ModelAdmin):
    """Admin para registros de auditoria de roles"""

    list_display = ['timestamp', 'get_actor', 'get_usuario', 'action', 'role', 'short_details']
    list_filter = ['action', 'timestamp', 'role__empresa']
    search_fields = ['actor__username', 'usuario__username', 'details']
    readonly_fields = ['role', 'actor', 'usuario', 'action', 'details', 'timestamp']

    def get_actor(self, obj):
        return obj.actor or '-'
    get_actor.short_description = 'Executor'

    def get_usuario(self, obj):
        return obj.usuario or '-'
    get_usuario.short_description = 'Usuário afetado'

    def short_details(self, obj):
        try:
            return str(obj.details)[:120]
        except Exception:
            return ''
    short_details.short_description = 'Detalhes'


@admin.register(PermissionTemplate)
class PermissionTemplateAdmin(admin.ModelAdmin):
    list_display = ['nome', 'empresa', 'criado_por', 'data_criacao']
    list_filter = ['empresa']
    search_fields = ['nome', 'empresa__nome']
    readonly_fields = ['data_criacao']
    ordering = ['empresa__nome', 'nome']