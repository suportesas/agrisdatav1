from django.contrib import admin
from .models import (
    EmprestimoProdutor,
    EmprestimoMovimento,
    EmprestimoInteracao,
    EmprestimoMensagem,
    EmprestimoMensagemAnexo,
)


class EmprestimoMovimentoInline(admin.TabularInline):
    model = EmprestimoMovimento
    extra = 0
    readonly_fields = ['criado_em', 'criado_por']


class EmprestimoMensagemAnexoInline(admin.TabularInline):
    model = EmprestimoMensagemAnexo
    extra = 0
    readonly_fields = ['criado_em']


@admin.register(EmprestimoProdutor)
class EmprestimoProdutorAdmin(admin.ModelAdmin):
    list_display = ['produtor', 'produto', 'status', 'quantidade_emprestada', 'saldo_pendente', 'data_emprestimo']
    list_filter = ['status', 'empresa']
    search_fields = ['produtor__razao_social', 'produto__nome']
    readonly_fields = ['criado_em', 'atualizado_em', 'saldo_pendente']
    inlines = [EmprestimoMovimentoInline]


@admin.register(EmprestimoMovimento)
class EmprestimoMovimentoAdmin(admin.ModelAdmin):
    list_display = ['emprestimo', 'tipo_movimento', 'quantidade', 'saldo_resultante', 'data_movimento']
    list_filter = ['tipo_movimento', 'empresa']
    readonly_fields = ['criado_em']


@admin.register(EmprestimoInteracao)
class EmprestimoInteracaoAdmin(admin.ModelAdmin):
    list_display = ['emprestimo', 'tipo_interacao', 'usuario', 'sucesso', 'criado_em']
    list_filter = ['tipo_interacao', 'sucesso']
    readonly_fields = ['criado_em']


@admin.register(EmprestimoMensagem)
class EmprestimoMensagemAdmin(admin.ModelAdmin):
    list_display = ['emprestimo', 'perfil_autor', 'autor', 'criado_em']
    list_filter = ['perfil_autor']
    readonly_fields = ['criado_em']
    inlines = [EmprestimoMensagemAnexoInline]
