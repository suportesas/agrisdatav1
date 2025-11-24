"""
Admin do módulo Fazendas
"""

from django.contrib import admin
from .models import (
    Fazenda, EnderecoFazenda, ContatoFazenda,
    ContaBancariaFazenda, DocumentoFazenda
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
    readonly_fields = ['data_upload']


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
    list_display = ['fazenda', 'get_tipo_display', 'titulo', 'data_validade', 'esta_vencido', 'gerar_alerta_vencimento']
    list_filter = ['tipo', 'gerar_alerta_vencimento', 'data_validade']
    search_fields = ['fazenda__nome', 'titulo', 'numero_documento']
    readonly_fields = ['data_upload', 'enviado_por']
    
    def esta_vencido(self, obj):
        """Mostra status de vencimento"""
        if obj.esta_vencido():
            return '❌ Vencido'
        elif obj.precisa_alerta():
            return '⚠️ Vencendo'
        return '✅ Válido'
    esta_vencido.short_description = 'Status'