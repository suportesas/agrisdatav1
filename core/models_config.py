# -*- coding: utf-8 -*-
"""
Configurações Globais do Sistema
Permite personalizar comportamento do ERP por empresa
"""
from django.db import models
from django.core.cache import cache


class ConfiguracaoSistema(models.Model):
    """
    Configurações globais que afetam comportamento do sistema
    Uma configuração por empresa
    """
    
    # Modos de Operação de Compras
    MODO_COMPRAS_CHOICES = [
        ('SIMPLES', 'Modo Simples - Compra direta e rápida'),
        ('FORMAL', 'Modo Formal - Com solicitação, cotação e aprovações'),
        ('HIBRIDO', 'Modo Híbrido - Escolhe o fluxo por compra'),
    ]
    
    # Modos de Operação de Estoque
    MODO_ESTOQUE_CHOICES = [
        ('SIMPLES', 'Modo Simples - Entrada/Saída direta'),
        ('FORMAL', 'Modo Formal - Lotes, validade e rastreamento completo'),
        ('HIBRIDO', 'Modo Híbrido - Escolhe o fluxo por movimentação'),
    ]
    
    # Relacionamento
    empresa = models.OneToOneField(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='configuracao_sistema',
        verbose_name='Empresa'
    )
    
    # ========================================
    # CONFIGURAÇÕES DE COMPRAS
    # ========================================
    
    modo_compras = models.CharField(
        'Modo de Compras',
        max_length=20,
        choices=MODO_COMPRAS_CHOICES,
        default='HIBRIDO',
        help_text='Define como as compras serão processadas no sistema'
    )
    
    exigir_aprovacao_solicitacao = models.BooleanField(
        'Exigir Aprovação de Solicitações',
        default=True,
        help_text='Se desabilitado, solicitações são aprovadas automaticamente'
    )
    
    exigir_cotacao_obrigatoria = models.BooleanField(
        'Cotação é Obrigatória',
        default=False,
        help_text='Se habilitado, não permite criar pedido sem cotação formal'
    )
    
    limite_compra_sem_aprovacao = models.DecimalField(
        'Limite para Compra Sem Aprovação',
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text='Valor máximo que pode ser comprado sem aprovação (0 = sempre exige)'
    )
    
    permitir_recebimento_sem_pedido = models.BooleanField(
        'Permitir Recebimento Direto',
        default=True,
        help_text='Permite registrar recebimento sem pedido prévio'
    )
    
    entrada_estoque_automatica = models.BooleanField(
        'Entrada Automática no Estoque',
        default=True,
        help_text='Ao confirmar recebimento, já dá entrada no estoque automaticamente'
    )
    
    # ========================================
    # CONFIGURAÇÕES DE ESTOQUE
    # ========================================
    
    modo_estoque = models.CharField(
        'Modo de Estoque',
        max_length=20,
        choices=MODO_ESTOQUE_CHOICES,
        default='HIBRIDO',
        help_text='Define como as movimentações de estoque serão processadas'
    )
    
    controle_lote_obrigatorio = models.BooleanField(
        'Controle de Lote Obrigatório',
        default=True,
        help_text='Exige lote em todas movimentações de estoque'
    )
    
    gerar_lote_automatico = models.BooleanField(
        'Gerar Lote Automaticamente',
        default=True,
        help_text='Cria lote automático quando não informado'
    )
    
    permitir_estoque_negativo = models.BooleanField(
        'Permitir Estoque Negativo',
        default=False,
        help_text='Permite saída mesmo sem estoque suficiente'
    )
    
    validade_obrigatoria = models.BooleanField(
        'Validade Obrigatória',
        default=False,
        help_text='Exige data de validade em todos produtos'
    )
    
    rastreamento_completo = models.BooleanField(
        'Rastreamento Completo',
        default=False,
        help_text='Ativa rastreamento detalhado de todas movimentações'
    )
    
    exigir_numero_serie = models.BooleanField(
        'Exigir Número de Série',
        default=False,
        help_text='Exige número de série para produtos específicos'
    )
    
    exigir_motivo_movimentacao = models.BooleanField(
        'Exigir Motivo em Movimentações',
        default=False,
        help_text='Exige justificativa em movimentações manuais de estoque'
    )
    
    ajuste_estoque_requer_aprovacao = models.BooleanField(
        'Ajuste de Estoque Requer Aprovação',
        default=True,
        help_text='Ajustes de estoque precisam de aprovação de supervisor'
    )
    
    # ========================================
    # CONFIGURAÇÕES DE PRODUTOS
    # ========================================
    
    ncm_obrigatorio = models.BooleanField(
        'NCM Obrigatório',
        default=False,
        help_text='Exige NCM no cadastro de produtos'
    )
    
    preco_custo_obrigatorio = models.BooleanField(
        'Preço de Custo Obrigatório',
        default=False,
        help_text='Exige preço de custo no cadastro'
    )
    
    # ========================================
    # CONFIGURAÇÕES DE NOTIFICAÇÕES
    # ========================================
    
    notificar_estoque_minimo = models.BooleanField(
        'Notificar Estoque Mínimo',
        default=True,
        help_text='Envia alerta quando produto atinge estoque mínimo'
    )
    
    notificar_solicitacao_pendente = models.BooleanField(
        'Notificar Solicitações Pendentes',
        default=True,
        help_text='Notifica aprovadores sobre solicitações pendentes'
    )
    
    # Auditoria
    data_criacao = models.DateTimeField('Data de Criação', auto_now_add=True)
    data_atualizacao = models.DateTimeField('Última Atualização', auto_now=True)
    atualizado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Atualizado Por'
    )
    
    class Meta:
        verbose_name = 'Configuração do Sistema'
        verbose_name_plural = 'Configurações do Sistema'
    
    def __str__(self):
        return f"Configurações - {self.empresa.nome}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Limpa cache quando configurações mudam
        cache.delete(f'config_sistema_{self.empresa_id}')
    
    @classmethod
    def get_config(cls, empresa):
        """
        Obtém configuração da empresa (com cache)
        Cria configuração padrão se não existir
        """
        cache_key = f'config_sistema_{empresa.id}'
        config = cache.get(cache_key)
        
        if config is None:
            config, created = cls.objects.get_or_create(
                empresa=empresa,
                defaults={
                    'modo_compras': 'HIBRIDO',
                    'exigir_aprovacao_solicitacao': True,
                    'exigir_cotacao_obrigatoria': False,
                    'permitir_recebimento_sem_pedido': True,
                    'entrada_estoque_automatica': True,
                    'gerar_lote_automatico': True,
                }
            )
            cache.set(cache_key, config, 3600)  # Cache por 1 hora
        
        return config
    
    def modo_simples_ativo(self):
        """Retorna True se modo simples está ativo"""
        return self.modo_compras in ['SIMPLES', 'HIBRIDO']
    
    def modo_formal_ativo(self):
        """Retorna True se modo formal está ativo"""
        return self.modo_compras in ['FORMAL', 'HIBRIDO']
    
    def deve_aprovar_solicitacao(self, valor_total=None):
        """
        Determina se solicitação precisa de aprovação
        """
        if not self.exigir_aprovacao_solicitacao:
            return False
        
        if valor_total and self.limite_compra_sem_aprovacao > 0:
            return valor_total > self.limite_compra_sem_aprovacao
        
        return True
    
    def pode_criar_pedido_sem_cotacao(self):
        """Retorna True se permite criar pedido sem cotação"""
        return not self.exigir_cotacao_obrigatoria
    
    # ==========================================
    # HELPERS PARA ESTOQUE
    # ==========================================
    
    def modo_estoque_simples_ativo(self):
        """Retorna True se modo estoque simples está ativo"""
        return self.modo_estoque in ['SIMPLES', 'HIBRIDO']
    
    def modo_estoque_formal_ativo(self):
        """Retorna True se modo estoque formal está ativo"""
        return self.modo_estoque in ['FORMAL', 'HIBRIDO']
    
    def pode_fazer_movimentacao_simples(self):
        """Retorna True se pode fazer entrada/saída direta"""
        return self.modo_estoque in ['SIMPLES', 'HIBRIDO']
    
    def exige_lote_na_movimentacao(self):
        """Retorna True se precisa informar lote"""
        return self.controle_lote_obrigatorio and self.modo_estoque == 'FORMAL'
    
    def exige_validade_produto(self):
        """Retorna True se validade é obrigatória"""
        return self.validade_obrigatoria and self.modo_estoque in ['FORMAL', 'HIBRIDO']
