# -*- coding: utf-8 -*-
"""
Admin para Configurações do Sistema
"""
from django.contrib import admin
from .models import ConfiguracaoSistema


@admin.register(ConfiguracaoSistema)
class ConfiguracaoSistemaAdmin(admin.ModelAdmin):
    list_display = [
        'empresa', 
        'modo_compras', 
        'modo_estoque',
        'exigir_aprovacao_solicitacao',
        'entrada_estoque_automatica',
        'data_atualizacao'
    ]
    list_filter = [
        'modo_compras', 
        'modo_estoque',
        'exigir_aprovacao_solicitacao',
        'exigir_cotacao_obrigatoria',
        'controle_lote_obrigatorio'
    ]
    search_fields = ['empresa__nome']
    readonly_fields = ['data_criacao', 'data_atualizacao']
    
    fieldsets = (
        ('Empresa', {
            'fields': ('empresa',)
        }),
        ('🛒 Configurações de Compras', {
            'fields': (
                'modo_compras',
                'exigir_aprovacao_solicitacao',
                'exigir_cotacao_obrigatoria',
                'limite_compra_sem_aprovacao',
                'permitir_recebimento_sem_pedido',
                'entrada_estoque_automatica',
            ),
            'description': 'Define como as compras serão processadas no sistema'
        }),
        ('📦 Configurações de Estoque', {
            'fields': (
                'modo_estoque',
                'controle_lote_obrigatorio',
                'gerar_lote_automatico',
                'permitir_estoque_negativo',
                'validade_obrigatoria',
                'rastreamento_completo',
                'exigir_numero_serie',
                'exigir_motivo_movimentacao',
                'ajuste_estoque_requer_aprovacao',
            ),
            'description': 'Define como o estoque será controlado'
        }),
        ('📦 Configurações de Produtos', {
            'fields': (
                'ncm_obrigatorio',
                'preco_custo_obrigatorio',
            ),
            'description': 'Requisitos para cadastro de produtos'
        }),
        ('🔔 Notificações', {
            'fields': (
                'notificar_estoque_minimo',
                'notificar_solicitacao_pendente',
            ),
            'description': 'Controle de alertas automáticos'
        }),
        ('📅 Auditoria', {
            'fields': (
                'data_criacao',
                'data_atualizacao',
                'atualizado_por',
            ),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.atualizado_por = request.user
        else:
            obj.atualizado_por = request.user
        super().save_model(request, obj, form, change)
