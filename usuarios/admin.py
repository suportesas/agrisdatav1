"""
Admin do app usuarios
Configuração do painel administrativo do Django
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import TipoUsuario, Usuario, LoginRegistro, PerfilUsuario


@admin.register(TipoUsuario)
class TipoUsuarioAdmin(admin.ModelAdmin):
    list_display = [
        'codigo', 'nome', 'ordem', 'ativo', 'protegido',
        'administrador_empresa', 'permite_gerenciar_usuarios',
        'permite_acessar_financeiro', 'permite_fazer_vendas'
    ]
    list_filter = [
        'ativo', 'protegido', 'administrador_empresa',
        'permite_gerenciar_usuarios', 'permite_acessar_financeiro', 'permite_fazer_vendas'
    ]
    search_fields = ['codigo', 'nome', 'descricao']
    ordering = ['ordem', 'nome']


@admin.register(Usuario)
class UsuarioAdmin(BaseUserAdmin):
    """Admin customizado para modelo Usuario"""
    
    list_display = [
        'username', 'get_nome_completo', 'email', 'empresa',
        'get_roles', 'get_tipo_nome', 'telefone', 'is_active_badge', 'date_joined'
    ]
    
    list_filter = [
        'tipo', 'is_active', 'is_staff', 'is_superuser',
        'empresa', 'date_joined'
    ]
    
    search_fields = [
        'username', 'first_name', 'last_name', 'email',
        'telefone', 'cpf'
    ]
    
    ordering = ['-date_joined']
    
    list_per_page = 50
    
    fieldsets = (
        ('Informações de Login', {
            'fields': ('username', 'password')
        }),
        ('Informações Pessoais', {
            'fields': ('first_name', 'last_name', 'email', 'cpf',
                      'telefone', 'data_nascimento', 'foto')
        }),
        ('Empresa e Tipo', {
            'fields': ('empresa', 'tipo', 'comissao_vendas', 'roles')
        }),
        ('Datas', {
            'fields': ('data_admissao', 'data_demissao')
        }),
        ('Permissões', {
            'fields': ('is_active', 'is_staff', 'is_superuser',
                      'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Observações', {
            'fields': ('observacoes',),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'email',
                      'first_name', 'last_name', 'empresa', 'tipo'),
        }),
    )
    
    def get_nome_completo(self, obj):
        """Exibe nome completo"""
        return obj.get_full_name() or '-'
    get_nome_completo.short_description = 'Nome Completo'

    def get_tipo_nome(self, obj):
        return obj.get_tipo_display()
    get_tipo_nome.short_description = 'Tipo'
    
    def is_active_badge(self, obj):
        """Badge colorido para status ativo/inativo"""
        if obj.is_active:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Ativo</span>'
            )
        return format_html(
            '<span style="color: red; font-weight: bold;">✗ Inativo</span>'
        )
    is_active_badge.short_description = 'Status'

    def get_roles(self, obj):
        """Retorna as funções/roles atribuídas ao usuário"""
        roles = obj.roles.all()
        if roles:
            return ", ".join([r.name for r in roles])
        return '-'
    get_roles.short_description = 'Funções'


@admin.register(LoginRegistro)
class LoginRegistroAdmin(admin.ModelAdmin):
    """Admin para registros de login"""
    
    list_display = [
        'data_login', 'usuario', 'empresa', 'ip_address',
        'sucesso_badge', 'get_navegador'
    ]
    
    list_filter = [
        'sucesso', 'data_login', 'empresa'
    ]
    
    search_fields = [
        'usuario__username', 'usuario__email',
        'empresa__nome', 'ip_address'
    ]
    
    ordering = ['-data_login']
    
    list_per_page = 100
    
    readonly_fields = [
        'usuario', 'empresa', 'data_login',
        'ip_address', 'user_agent', 'sucesso'
    ]
    
    def has_add_permission(self, request):
        """Não permite adicionar manualmente"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Não permite editar"""
        return False
    
    def sucesso_badge(self, obj):
        """Badge para login bem-sucedido"""
        if obj.sucesso:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Sucesso</span>'
            )
        return format_html(
            '<span style="color: red; font-weight: bold;">✗ Falha</span>'
        )
    sucesso_badge.short_description = 'Status'
    
    def get_navegador(self, obj):
        """Exibe navegador"""
        return obj.get_navegador()
    get_navegador.short_description = 'Navegador'


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    """Admin para perfil de usuário"""
    
    list_display = [
        'usuario', 'cargo', 'departamento',
        'cidade', 'estado'
    ]
    
    list_filter = [
        'estado', 'receber_email_vendas',
        'receber_email_estoque', 'receber_email_financeiro'
    ]
    
    search_fields = [
        'usuario__username', 'usuario__email',
        'cargo', 'departamento', 'cidade'
    ]
    
    fieldsets = (
        ('Usuário', {
            'fields': ('usuario',)
        }),
        ('Informações Profissionais', {
            'fields': ('cargo', 'departamento')
        }),
        ('Endereço', {
            'fields': ('endereco', 'cidade', 'estado', 'cep')
        }),
        ('Notificações', {
            'fields': (
                'receber_email_vendas',
                'receber_email_estoque',
                'receber_email_financeiro'
            )
        }),
    )