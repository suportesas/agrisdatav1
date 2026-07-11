# 📋 ESPECIFICAÇÃO COMPLETA - MÓDULO RECEITUÁRIO AGRÔNOMO

**Data de Criação:** 2025-02-04  
**Status:** Pronto para Implementação  
**Esforço Estimado:** 8-11 horas  
**Prioridade:** Alta  

---

## 📌 RESUMO EXECUTIVO

Sistema completo de **Recomendações Automáticas de Defensivos** integrado ao **Receituário Agrônomo**, permitindo que o agrônomo crie receituários técnicos com sugestões automáticas de defensivos baseado na praga identificada no talhão.

---

## 🎯 REQUISITOS FUNCIONAIS

### RF-001: Recomendações de Defensivos por Praga

```
O sistema deve manter um registro de quais defensivos são recomendados
para cada praga, com ordem de preferência e dados técnicos.

Dados Necessários:
├─ Praga
├─ Defensivo (produto)
├─ Ordem de recomendação (1=melhor, 2=alternativa, etc)
├─ Efetividade (0-100%)
├─ Custo relativo (BAIXO, MÉDIO, ALTO)
├─ Dosagem mínima
├─ Dosagem máxima
├─ Unidade de dosagem (mL/100L, L/ha, etc)
├─ Carência mínima (dias)
├─ Quantidade máxima de aplicações
├─ Intervalo para reaplicação (dias)
└─ Observações
```

### RF-002: Receituário Agrônomo

```
O agrônomo deve poder criar receituários técnicos de defesa fitossanitária,
com todos os dados preenchidos automaticamente baseado na praga e defensivo.

Dados Necessários:
├─ Número único (auto-gerado: REC-YYYY-NNNNN)
├─ Talhão (campo onde será aplicado)
├─ Safra (contexto agrícola)
├─ Praga identificada
├─ Cultura plantada
├─ Defensivo recomendado
├─ Dosagem aplicar
├─ Unidade dosagem
├─ Data da aplicação
├─ Horário (opcional)
├─ Volume de calda (L/ha)
├─ Condições climáticas:
│  ├─ Temperatura (°C)
│  ├─ Umidade (%)
│  └─ Velocidade vento (km/h)
├─ Responsável (agrônomo)
├─ Status (RASCUNHO, PENDENTE, APROVADO, REJEITADO)
├─ Observações técnicas
└─ Auditoria (created_at, updated_at, created_by)
```

### RF-003: Interface Inteligente

```
Form deve ter preenchimento automático em cascata:

1. Seleciona Talhão
   ↓ Carrega automaticamente:
   └─ Cultura plantada
   └─ Safra
   └─ Pragas conhecidas para essa cultura

2. Seleciona Praga
   ↓ Carrega automaticamente via AJAX:
   └─ Defensivos recomendados (até 5)
   └─ Ordenados por efetividade
   └─ Com badges (1º opção, alternativa, etc)

3. Seleciona Defensivo
   ↓ Preenche automaticamente:
   └─ Dosagem mínima
   └─ Dosagem máxima
   └─ Unidade dosagem
   └─ Carência
   └─ Quantidade máxima de aplicações
   └─ Intervalo reaplicação
   └─ Efetividade
   └─ Custo relativo

4. Agrônomo só complementa:
   ├─ Dosagem exata (validação min/máx)
   ├─ Data aplicação
   ├─ Horário (opcional)
   ├─ Volume calda
   ├─ Condições climáticas
   ├─ Observações
   └─ Salva receituário

Total de cliques: ~5-10 (em vez de digitar tudo manualmente)
```

---

## 🏗️ ARQUITETURA TÉCNICA

### Modelos Django

#### 1. RecomendacaoDefensivo

```python
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

class RecomendacaoDefensivo(models.Model):
    """
    Recomendação de qual defensivo usar contra qual praga
    
    Exemplo:
    - Praga: "Lagarta-do-cartucho"
    - Defensivo: "Deltamethrin 25 WP"
    - Dosagem: 25-50 mL/100L
    - Carência: 7 dias
    - Efetividade: 95%
    """
    
    ORDEM_CHOICES = [
        (1, '1ª Opção (Recomendado)'),
        (2, '2ª Opção (Alternativa)'),
        (3, '3ª Opção (Alternativa)'),
        (4, '4ª Opção (Quando não houver outras)'),
        (5, '5ª Opção (Última alternativa)'),
    ]
    
    CUSTO_CHOICES = [
        ('BAIXO', 'Baixo'),
        ('MEDIO', 'Médio'),
        ('ALTO', 'Alto'),
    ]
    
    # Relacionamentos
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='recomendacoes_defensivos',
        verbose_name='Empresa'
    )
    praga = models.ForeignKey(
        'cadastros.Praga',
        on_delete=models.CASCADE,
        related_name='defensivos_recomendados',
        verbose_name='Praga/Doença'
    )
    produto = models.ForeignKey(
        'produtos.Produto',
        on_delete=models.CASCADE,
        related_name='pragas_recomendadas',
        verbose_name='Defensivo',
        limit_choices_to={'categoria_agricola': 'DEFENSIVO'}
    )
    
    # Dados de recomendação
    ordem = models.IntegerField(
        choices=ORDEM_CHOICES,
        default=1,
        verbose_name='Ordem de Recomendação'
    )
    efetividade = models.IntegerField(
        default=85,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Efetividade (%)',
        help_text='Percentual de efetividade contra a praga (0-100)'
    )
    custo_relativo = models.CharField(
        max_length=10,
        choices=CUSTO_CHOICES,
        default='MEDIO',
        verbose_name='Custo Relativo'
    )
    
    # Dosagem
    dosagem_minima = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))],
        verbose_name='Dosagem Mínima'
    )
    dosagem_maxima = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))],
        verbose_name='Dosagem Máxima'
    )
    unidade_dosagem = models.ForeignKey(
        'produtos.UnidadeMedida',
        on_delete=models.PROTECT,
        related_name='recomendacoes_dosagens',
        verbose_name='Unidade de Dosagem',
        help_text='Ex: mL/100L, L/ha, g/kg'
    )
    
    # Aplicação
    carencia_minima = models.IntegerField(
        validators=[MinValueValidator(0)],
        verbose_name='Carência Mínima (dias)',
        help_text='Dias entre última aplicação e colheita'
    )
    quantidade_maxima_aplicacoes = models.IntegerField(
        validators=[MinValueValidator(1)],
        default=3,
        verbose_name='Quantidade Máxima de Aplicações'
    )
    intervalo_reaplicacao = models.IntegerField(
        validators=[MinValueValidator(1)],
        default=7,
        verbose_name='Intervalo para Reaplicação (dias)'
    )
    
    # Observações
    observacoes = models.TextField(
        blank=True,
        verbose_name='Observações',
        help_text='Notas técnicas ou restrições específicas'
    )
    
    # Auditoria
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Recomendação de Defensivo'
        verbose_name_plural = 'Recomendações de Defensivos'
        unique_together = [['empresa', 'praga', 'produto']]
        ordering = ['praga', 'ordem', '-efetividade']
        indexes = [
            models.Index(fields=['empresa', 'praga']),
            models.Index(fields=['empresa', 'produto']),
            models.Index(fields=['praga', 'ordem']),
        ]
    
    def __str__(self):
        return f"{self.praga.nome_comum} → {self.produto.nome}"
    
    def get_ordem_display_badge(self):
        """Retorna um emoji para a ordem de recomendação"""
        badges = {1: '🥇', 2: '🥈', 3: '🥉', 4: '⭐', 5: '✨'}
        return badges.get(self.ordem, '•')
```

#### 2. Receituario

```python
class Receituario(models.Model):
    """
    Receituário Agronômico - Documento técnico de recomendação
    de defesa fitossanitária
    
    Segue padrão legal:
    - Número único sequencial
    - Assinatura do agrônomo
    - Dados técnicos completos
    - Rastreabilidade
    """
    
    STATUS_CHOICES = [
        ('RASCUNHO', 'Rascunho'),
        ('PENDENTE_ANALISE', 'Pendente Análise'),
        ('APROVADO', 'Aprovado'),
        ('REJEITADO', 'Rejeitado'),
        ('CANCELADO', 'Cancelado'),
    ]
    
    # Identificação
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='receituarios',
        verbose_name='Empresa'
    )
    numero = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='Número',
        help_text='Auto-gerado: REC-YYYY-NNNNN'
    )
    
    # Contexto agrícola
    talhao = models.ForeignKey(
        'cadastros.Talhao',
        on_delete=models.PROTECT,
        related_name='receituarios',
        verbose_name='Talhão (Campo)',
        help_text='Campo onde será aplicado o defensivo'
    )
    safra = models.ForeignKey(
        'cadastros.Safra',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name='Safra',
        help_text='Safra agrícola em que ocorre a aplicação'
    )
    
    # Praga e Cultura
    cultura = models.ForeignKey(
        'cadastros.Cultura',
        on_delete=models.PROTECT,
        related_name='receituarios',
        verbose_name='Cultura',
        help_text='Preenchida automaticamente pelo talhão'
    )
    praga = models.ForeignKey(
        'cadastros.Praga',
        on_delete=models.PROTECT,
        related_name='receituarios',
        verbose_name='Praga/Doença'
    )
    
    # Defensivo recomendado
    recomendacao = models.ForeignKey(
        'RecomendacaoDefensivo',
        on_delete=models.PROTECT,
        related_name='receituarios',
        verbose_name='Recomendação',
        help_text='Link para recomendação que gerou este receituário'
    )
    produto = models.ForeignKey(
        'produtos.Produto',
        on_delete=models.PROTECT,
        related_name='receituarios_aplicacao',
        verbose_name='Defensivo',
        limit_choices_to={'categoria_agricola': 'DEFENSIVO'}
    )
    
    # Dados de aplicação
    dosagem = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))],
        verbose_name='Dosagem a Aplicar',
        help_text='Quantidade a usar (deve estar entre min e máx recomendados)'
    )
    unidade_dosagem = models.ForeignKey(
        'produtos.UnidadeMedida',
        on_delete=models.PROTECT,
        related_name='receituarios_dosagens',
        verbose_name='Unidade de Dosagem'
    )
    volume_calda = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Volume de Calda (L/ha)',
        help_text='Litros de calda por hectare'
    )
    
    # Data e hora
    data_aplicacao = models.DateField(
        verbose_name='Data da Aplicação',
        help_text='Quando o defensivo será/foi aplicado'
    )
    horario_aplicacao = models.TimeField(
        null=True,
        blank=True,
        verbose_name='Horário da Aplicação',
        help_text='Opcional - para rastreamento mais preciso'
    )
    
    # Condições climáticas
    temperatura = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        verbose_name='Temperatura (°C)',
        help_text='Temperatura no momento/data da aplicação'
    )
    umidade = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Umidade Relativa (%)',
        help_text='Umidade do ar (0-100%)'
    )
    velocidade_vento = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name='Velocidade do Vento (km/h)',
        help_text='Velocidade do vento no momento da aplicação'
    )
    observacoes_clima = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Observações sobre Clima',
        help_text='Ex: chuva prevista em 48h, solo úmido, etc'
    )
    
    # Responsáveis
    agronomista = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='receituarios_criados',
        verbose_name='Agrônomo Responsável'
    )
    
    # Status e observações
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='RASCUNHO',
        verbose_name='Status',
        help_text='Estado do receituário'
    )
    observacoes = models.TextField(
        blank=True,
        verbose_name='Observações Técnicas',
        help_text='Notas adicionais, restrições, recomendações especiais'
    )
    motivo_rejeicao = models.TextField(
        blank=True,
        verbose_name='Motivo da Rejeição',
        help_text='Preenchido se status = REJEITADO'
    )
    
    # Auditoria
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Criado em'
    )
    created_by = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        related_name='receituarios_autores',
        verbose_name='Criado por'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Atualizado em'
    )
    updated_by = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='receituarios_atualizados_por',
        verbose_name='Atualizado por'
    )
    
    class Meta:
        verbose_name = 'Receituário Agronômico'
        verbose_name_plural = 'Receituários Agronômicos'
        ordering = ['-created_at']
        permissions = [
            ('aprovar_receituario', 'Pode aprovar receituários'),
            ('rejeitar_receituario', 'Pode rejeitar receituários'),
        ]
        indexes = [
            models.Index(fields=['empresa', 'status']),
            models.Index(fields=['talhao', 'created_at']),
            models.Index(fields=['praga', 'created_at']),
            models.Index(fields=['data_aplicacao']),
        ]
    
    def __str__(self):
        return f"{self.numero} - {self.talhao} - {self.praga}"
    
    def save(self, *args, **kwargs):
        # Auto-gerar número se não existir
        if not self.numero:
            from django.utils import timezone
            ano = timezone.now().year
            last = Receituario.objects.filter(
                numero__startswith=f'REC-{ano}'
            ).order_by('numero').last()
            
            if last:
                numero_seq = int(last.numero.split('-')[2]) + 1
            else:
                numero_seq = 1
            
            self.numero = f'REC-{ano}-{numero_seq:05d}'
        
        # Preencher cultura do talhão automaticamente
        if self.talhao and not self.cultura:
            self.cultura = self.talhao.area.cultura
        
        super().save(*args, **kwargs)
```

---

## 🌐 ENDPOINTS API

### GET /api/talhao/{talhao_id}/dados/

Retorna dados do talhão para o form:

```json
{
    "talhao_id": 1,
    "talhao_nome": "Talhão 01",
    "area_ha": 100.5,
    "cultura_id": 5,
    "cultura_nome": "Soja",
    "safra_id": 3,
    "safra_ano": 2025,
    "pragas_possiveis": [
        {"id": 10, "nome_comum": "Lagarta-do-cartucho", "nome_cientifico": "Spodoptera frugiperda"},
        {"id": 15, "nome_comum": "Ferrugem", "nome_cientifico": "Phakopsora meibomiae"}
    ]
}
```

### GET /api/praga/{praga_id}/defensivos-recomendados/

Retorna defensivos recomendados para uma praga:

```json
{
    "praga_id": 10,
    "praga_nome": "Lagarta-do-cartucho",
    "total_recomendacoes": 3,
    "recomendacoes": [
        {
            "recomendacao_id": 1,
            "defensivo_id": 50,
            "defensivo_nome": "Deltamethrin 25 WP",
            "ordem": 1,
            "badge": "🥇",
            "efetividade": 95,
            "custo": "MEDIO",
            "dosagem_min": 25,
            "dosagem_max": 50,
            "unidade": "mL/100L",
            "carencia": 7,
            "qtd_max_aplicacoes": 3,
            "intervalo_reaplicacao": 7,
            "observacoes": ""
        },
        {
            "recomendacao_id": 2,
            "defensivo_id": 51,
            "defensivo_nome": "Pyrethrin 50 EC",
            "ordem": 2,
            "badge": "🥈",
            "efetividade": 85,
            "custo": "ALTO",
            "dosagem_min": 1.0,
            "dosagem_max": 2.0,
            "unidade": "L/ha",
            "carencia": 3,
            "qtd_max_aplicacoes": 4,
            "intervalo_reaplicacao": 5,
            "observacoes": "Melhor para controle rápido"
        }
    ]
}
```

---

## 🎨 INTERFACE (HTML/JS)

### Form Completo

```html
{% extends 'base.html' %}
{% load static %}

{% block title %}Criar Receituário | ERP Agrícola{% endblock %}

{% block extra_css %}
<style>
    .receituario-form {
        max-width: 900px;
        margin: 0 auto;
    }
    
    .section-card {
        background: white;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin-bottom: 20px;
        overflow: hidden;
    }
    
    .section-header {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        padding: 15px 20px;
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    .section-body {
        padding: 20px;
    }
    
    .form-group {
        margin-bottom: 15px;
    }
    
    .form-label {
        font-weight: 600;
        margin-bottom: 5px;
    }
    
    .defensivos-recomendados {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 15px;
    }
    
    .defensivo-card {
        border: 2px solid #e5e7eb;
        border-radius: 6px;
        padding: 15px;
        cursor: pointer;
        transition: all 0.3s;
    }
    
    .defensivo-card:hover {
        border-color: #10b981;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.15);
    }
    
    .defensivo-card.selected {
        border-color: #10b981;
        background-color: #f0fdf4;
    }
    
    .badge-ordem {
        font-size: 24px;
        margin-right: 5px;
    }
    
    .efetividade-bar {
        height: 20px;
        background: #e5e7eb;
        border-radius: 4px;
        overflow: hidden;
        margin: 5px 0;
    }
    
    .efetividade-fill {
        height: 100%;
        background: linear-gradient(90deg, #ec4899, #10b981);
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-size: 12px;
        font-weight: 600;
    }
    
    .dados-aplicacao {
        display: none;
    }
    
    .dados-aplicacao.visible {
        display: block;
    }
    
    .alert-info {
        background: #dbeafe;
        border: 1px solid #93c5fd;
        color: #1e40af;
        padding: 12px;
        border-radius: 6px;
        margin-bottom: 15px;
    }
</style>
{% endblock %}

{% block content %}
<div class="container-fluid py-4">
    <div class="receituario-form">
        
        <!-- Header -->
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h1>
                <i class="bi bi-file-earmark-text"></i> 
                Criar Receituário Agronômico
            </h1>
            <small class="text-muted">Número será auto-gerado ao salvar</small>
        </div>
        
        <!-- Form -->
        <form method="post" id="receituarioForm" novalidate>
            {% csrf_token %}
            
            <!-- SEÇÃO 1: IDENTIFICAÇÃO DO TALHÃO -->
            <div class="section-card">
                <div class="section-header">
                    <i class="bi bi-map"></i>
                    Identificação do Talhão
                </div>
                <div class="section-body">
                    <div class="row">
                        <div class="col-md-6">
                            <div class="form-group">
                                <label class="form-label">Talhão (Campo) *</label>
                                <select name="talhao" id="selectTalhao" class="form-select" required onchange="carregarDadosTalhao()">
                                    <option value="">-- Selecione um talhão --</option>
                                    {% for talhao in talhoes %}
                                    <option value="{{ talhao.id }}">
                                        {{ talhao.nome }} - {{ talhao.area.nome }} ({{ talhao.area_hac }} ha)
                                    </option>
                                    {% endfor %}
                                </select>
                                <small class="text-muted">Selecione o campo onde será aplicado o defensivo</small>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="form-group">
                                <label class="form-label">Cultura</label>
                                <input type="text" id="cultura" class="form-control" readonly>
                                <small class="text-muted">Preenchido automaticamente</small>
                            </div>
                        </div>
                    </div>
                    
                    <div class="row">
                        <div class="col-md-6">
                            <div class="form-group">
                                <label class="form-label">Safra</label>
                                <input type="text" id="safra" class="form-control" readonly>
                                <small class="text-muted">Preenchido automaticamente</small>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="form-group">
                                <label class="form-label">Área do Talhão</label>
                                <input type="text" id="areaHa" class="form-control" readonly>
                                <small class="text-muted">Preenchido automaticamente</small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- SEÇÃO 2: IDENTIFICAÇÃO DA PRAGA -->
            <div class="section-card">
                <div class="section-header">
                    <i class="bi bi-bug"></i>
                    Praga Identificada
                </div>
                <div class="section-body">
                    <div class="form-group">
                        <label class="form-label">Qual praga foi identificada? *</label>
                        <select name="praga" id="selectPraga" class="form-select" required onchange="carregarDefensivosRecomendados()">
                            <option value="">-- Selecione a praga --</option>
                        </select>
                        <small class="text-muted">Selecione a praga que foi identificada neste talhão</small>
                    </div>
                </div>
            </div>
            
            <!-- SEÇÃO 3: DEFENSIVOS RECOMENDADOS -->
            <div class="section-card">
                <div class="section-header">
                    <i class="bi bi-droplet"></i>
                    Defensivos Recomendados
                </div>
                <div class="section-body">
                    <div class="alert-info">
                        <strong><i class="bi bi-info-circle"></i> Informação:</strong> 
                        Clique em um defensivo para selecioná-lo. Os dados de dosagem serão preenchidos automaticamente.
                    </div>
                    
                    <div id="defensivosRecomendados" class="defensivos-recomendados">
                        <div class="text-center text-muted py-4">
                            Selecione um talhão e uma praga para ver defensivos recomendados
                        </div>
                    </div>
                    
                    <!-- Campo hidden para armazenar recomendação selecionada -->
                    <input type="hidden" name="recomendacao" id="selectRecomendacao">
                </div>
            </div>
            
            <!-- SEÇÃO 4: DADOS DE APLICAÇÃO -->
            <div class="section-card dados-aplicacao" id="secaoDadosAplicacao">
                <div class="section-header">
                    <i class="bi bi-gear"></i>
                    Dados de Aplicação
                </div>
                <div class="section-body">
                    
                    <!-- Dosagem -->
                    <div class="row mb-3">
                        <div class="col-md-8">
                            <div class="form-group">
                                <label class="form-label">Dosagem a Aplicar *</label>
                                <div class="input-group">
                                    <input type="number" name="dosagem" id="dosagem" class="form-control" 
                                           step="0.001" placeholder="35" required>
                                    <span class="input-group-text" id="unidadeDosagem">mL/100L</span>
                                </div>
                                <small class="text-muted" id="dosageHelp">
                                    Mínimo: <span id="dosageMin">25</span> | 
                                    Máximo: <span id="dosageMax">50</span>
                                </small>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="form-group">
                                <label class="form-label">Volume de Calda (L/ha)</label>
                                <input type="number" name="volume_calda" id="volumeCalda" class="form-control" 
                                       step="0.01" placeholder="100">
                                <small class="text-muted">Opcional - litros de calda por hectare</small>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Data e Hora -->
                    <div class="row mb-3">
                        <div class="col-md-6">
                            <div class="form-group">
                                <label class="form-label">Data da Aplicação *</label>
                                <input type="date" name="data_aplicacao" id="dataAplicacao" class="form-control" required>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="form-group">
                                <label class="form-label">Horário da Aplicação (opcional)</label>
                                <input type="time" name="horario_aplicacao" id="horarioAplicacao" class="form-control">
                            </div>
                        </div>
                    </div>
                    
                    <!-- Informações do Defensivo (Read-only) -->
                    <div class="row mb-3">
                        <div class="col-md-3">
                            <div class="form-group">
                                <label class="form-label">Carência (dias)</label>
                                <input type="number" id="carencia" class="form-control" readonly>
                                <small class="text-muted">Preenchido automaticamente</small>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="form-group">
                                <label class="form-label">Qtd. Máx. de Aplicações</label>
                                <input type="number" id="qtdMaxAplicacoes" class="form-control" readonly>
                                <small class="text-muted">Preenchido automaticamente</small>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="form-group">
                                <label class="form-label">Intervalo Reaplicação (dias)</label>
                                <input type="number" id="intervaloReaplicacao" class="form-control" readonly>
                                <small class="text-muted">Preenchido automaticamente</small>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="form-group">
                                <label class="form-label">Efetividade</label>
                                <div class="input-group">
                                    <input type="number" id="efetividade" class="form-control" readonly>
                                    <span class="input-group-text">%</span>
                                </div>
                                <small class="text-muted">Preenchido automaticamente</small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- SEÇÃO 5: CONDIÇÕES CLIMÁTICAS -->
            <div class="section-card dados-aplicacao" id="secaoClima">
                <div class="section-header">
                    <i class="bi bi-cloud"></i>
                    Condições Climáticas (Opcional)
                </div>
                <div class="section-body">
                    <div class="row">
                        <div class="col-md-4">
                            <div class="form-group">
                                <label class="form-label">Temperatura (°C)</label>
                                <input type="number" name="temperatura" id="temperatura" class="form-control" 
                                       step="0.1" placeholder="25">
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="form-group">
                                <label class="form-label">Umidade Relativa (%)</label>
                                <input type="number" name="umidade" id="umidade" class="form-control" 
                                       min="0" max="100" placeholder="75">
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="form-group">
                                <label class="form-label">Velocidade do Vento (km/h)</label>
                                <input type="number" name="velocidade_vento" id="velocidadeVento" class="form-control" 
                                       step="0.1" placeholder="5">
                            </div>
                        </div>
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label">Observações sobre Clima</label>
                        <input type="text" name="observacoes_clima" id="observacoesClima" class="form-control" 
                               placeholder="Ex: chuva prevista em 48h, solo úmido, etc">
                    </div>
                </div>
            </div>
            
            <!-- SEÇÃO 6: OBSERVAÇÕES FINAIS -->
            <div class="section-card dados-aplicacao" id="secaoObservacoes">
                <div class="section-header">
                    <i class="bi bi-chat-left-text"></i>
                    Observações Técnicas (Opcional)
                </div>
                <div class="section-body">
                    <div class="form-group">
                        <label class="form-label">Observações</label>
                        <textarea name="observacoes" id="observacoes" class="form-control" rows="4" 
                                  placeholder="Notas adicionais, restrições, recomendações especiais..."></textarea>
                    </div>
                </div>
            </div>
            
            <!-- Botões -->
            <div class="d-flex gap-2 mb-4">
                <button type="submit" class="btn btn-primary btn-lg">
                    <i class="bi bi-check-circle"></i> Salvar Receituário
                </button>
                <button type="reset" class="btn btn-outline-secondary btn-lg">
                    <i class="bi bi-arrow-clockwise"></i> Limpar Formulário
                </button>
                <a href="{% url 'receituarios:receituario_list' %}" class="btn btn-outline-secondary btn-lg">
                    <i class="bi bi-arrow-left"></i> Voltar
                </a>
            </div>
        </form>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script>
    // Carrega dados do talhão
    async function carregarDadosTalhao() {
        const talhaoId = document.getElementById('selectTalhao').value;
        if (!talhaoId) {
            limparDados();
            return;
        }
        
        try {
            const response = await fetch(`/api/talhao/${talhaoId}/dados/`);
            const data = await response.json();
            
            // Preencher campos
            document.getElementById('cultura').value = data.cultura_nome;
            document.getElementById('safra').value = data.safra_ano;
            document.getElementById('areaHa').value = data.area_ha + ' ha';
            
            // Carregar pragas possíveis
            const selectPraga = document.getElementById('selectPraga');
            selectPraga.innerHTML = '<option value="">-- Selecione a praga --</option>';
            
            data.pragas_possiveis.forEach(praga => {
                const option = document.createElement('option');
                option.value = praga.id;
                option.text = `${praga.nome_comum} (${praga.nome_cientifico})`;
                selectPraga.appendChild(option);
            });
            
        } catch (error) {
            console.error('Erro ao carregar dados do talhão:', error);
            alert('Erro ao carregar dados. Tente novamente.');
        }
    }
    
    // Carrega defensivos recomendados
    async function carregarDefensivosRecomendados() {
        const pragaId = document.getElementById('selectPraga').value;
        if (!pragaId) {
            document.getElementById('defensivosRecomendados').innerHTML = 
                '<div class="text-center text-muted py-4">Selecione uma praga para ver defensivos recomendados</div>';
            return;
        }
        
        try {
            const response = await fetch(`/api/praga/${pragaId}/defensivos-recomendados/`);
            const data = await response.json();
            
            const container = document.getElementById('defensivosRecomendados');
            if (data.recomendacoes.length === 0) {
                container.innerHTML = '<div class="text-center text-warning py-4">Nenhum defensivo recomendado para esta praga</div>';
                return;
            }
            
            container.innerHTML = data.recomendacoes.map(rec => `
                <div class="defensivo-card" onclick="selecionarDefensivo(${rec.recomendacao_id}, ${rec.dosagem_min}, ${rec.dosagem_max}, '${rec.unidade}', ${rec.carencia}, ${rec.qtd_max_aplicacoes}, ${rec.intervalo_reaplicacao}, ${rec.efetividade})">
                    <div class="d-flex align-items-center mb-2">
                        <span class="badge-ordem">${rec.badge}</span>
                        <strong>${rec.defensivo_nome}</strong>
                    </div>
                    
                    <div class="efetividade-bar">
                        <div class="efetividade-fill" style="width: ${rec.efetividade}%">
                            ${rec.efetividade}%
                        </div>
                    </div>
                    
                    <small class="d-block text-muted mt-2">
                        <strong>Dosagem:</strong> ${rec.dosagem_min}-${rec.dosagem_max} ${rec.unidade}<br>
                        <strong>Carência:</strong> ${rec.carencia} dias<br>
                        <strong>Custo:</strong> <span class="badge bg-info">${rec.custo}</span>
                    </small>
                </div>
            `).join('');
            
        } catch (error) {
            console.error('Erro ao carregar defensivos:', error);
            alert('Erro ao carregar defensivos. Tente novamente.');
        }
    }
    
    // Seleciona um defensivo
    function selecionarDefensivo(recId, dosMin, dosMax, unidade, carencia, qtdMax, intervalo, efetividade) {
        // Salvar recomendação ID
        document.getElementById('selectRecomendacao').value = recId;
        
        // Preencher campos de dosagem
        document.getElementById('dosageMin').textContent = dosMin;
        document.getElementById('dosageMax').textContent = dosMax;
        document.getElementById('unidadeDosagem').textContent = unidade;
        document.getElementById('carencia').value = carencia;
        document.getElementById('qtdMaxAplicacoes').value = qtdMax;
        document.getElementById('intervaloReaplicacao').value = intervalo;
        document.getElementById('efetividade').value = efetividade;
        
        // Limpar dosagem anterior
        document.getElementById('dosagem').value = '';
        
        // Mostrar seção de dados de aplicação
        document.getElementById('secaoDadosAplicacao').classList.add('visible');
        document.getElementById('secaoClima').classList.add('visible');
        document.getElementById('secaoObservacoes').classList.add('visible');
        
        // Scroll até dados de aplicação
        document.getElementById('secaoDadosAplicacao').scrollIntoView({ behavior: 'smooth' });
        
        // Marcar card como selecionado
        document.querySelectorAll('.defensivo-card').forEach(card => {
            card.classList.remove('selected');
        });
        event.currentTarget.classList.add('selected');
    }
    
    // Limpar dados ao mudar talhão
    function limparDados() {
        document.getElementById('cultura').value = '';
        document.getElementById('safra').value = '';
        document.getElementById('areaHa').value = '';
        document.getElementById('selectPraga').innerHTML = '<option value="">-- Selecione a praga --</option>';
        document.getElementById('defensivosRecomendados').innerHTML = 
            '<div class="text-center text-muted py-4">Selecione um talhão para continuar</div>';
        document.getElementById('secaoDadosAplicacao').classList.remove('visible');
        document.getElementById('secaoClima').classList.remove('visible');
        document.getElementById('secaoObservacoes').classList.remove('visible');
    }
    
    // Validação de dosagem
    document.getElementById('dosagem').addEventListener('blur', function() {
        const min = parseFloat(document.getElementById('dosageMin').textContent);
        const max = parseFloat(document.getElementById('dosageMax').textContent);
        const value = parseFloat(this.value);
        
        if (isNaN(value)) return;
        
        if (value < min || value > max) {
            this.classList.add('is-invalid');
            alert(`Dosagem deve estar entre ${min} e ${max}`);
        } else {
            this.classList.remove('is-invalid');
        }
    });
</script>
{% endblock %}
```

---

## 📊 SEED DATA - RECOMENDAÇÕES INICIAIS

```python
# ESTRUTURA DO ARQUIVO: produtos/recomendacoes_seed.py

RECOMENDACOES_SEED = [
    # Lagarta-do-cartucho
    {
        'praga_nome': 'Lagarta-do-cartucho',
        'defensivo_nome': 'Deltamethrin 25 WP',
        'ordem': 1,
        'efetividade': 95,
        'custo': 'MEDIO',
        'dosagem_min': Decimal('25'),
        'dosagem_max': Decimal('50'),
        'unidade_nome': 'mL/100L',
        'carencia': 7,
        'qtd_max_aplicacoes': 3,
        'intervalo_reaplicacao': 7,
        'observacoes': 'Melhor opção para controle rápido'
    },
    {
        'praga_nome': 'Lagarta-do-cartucho',
        'defensivo_nome': 'Pyrethrin 50 EC',
        'ordem': 2,
        'efetividade': 85,
        'custo': 'ALTO',
        'dosagem_min': Decimal('1.0'),
        'dosagem_max': Decimal('2.0'),
        'unidade_nome': 'L/ha',
        'carencia': 3,
        'qtd_max_aplicacoes': 4,
        'intervalo_reaplicacao': 5,
        'observacoes': 'Melhor carência, mais caro'
    },
    # ... mais recomendações
]
```

---

## 🔌 VIEWS DJANGO

### Criar/Editar Receituário

```python
from django.views.generic import CreateView, UpdateView, ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q

class ReceituarioCreateView(LoginRequiredMixin, CreateView):
    model = Receituario
    form_class = ReceituarioForm
    template_name = 'cadastros/receituario/receituario_form.html'
    success_url = reverse_lazy('cadastros:receituario_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Buscar talhões da empresa
        context['talhoes'] = Talhao.objects.filter(
            area__fazenda__empresa=self.request.user.empresa
        ).select_related('area', 'area__cultura')
        return context
    
    def form_valid(self, form):
        form.instance.empresa = self.request.user.empresa
        form.instance.created_by = self.request.user
        return super().form_valid(form)
```

### API Endpoints

```python
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def talhao_dados(request, talhao_id):
    """Retorna dados do talhão e pragas possíveis"""
    try:
        talhao = Talhao.objects.get(
            id=talhao_id,
            area__fazenda__empresa=request.user.empresa
        )
        
        # Pragas possíveis para a cultura
        pragas = Praga.objects.filter(
            empresa=request.user.empresa,
            culturas__in=[talhao.area.cultura] if talhao.area.cultura else []
        ).distinct()
        
        return Response({
            'talhao_id': talhao.id,
            'talhao_nome': talhao.nome,
            'area_ha': float(talhao.area_hac),
            'cultura_id': talhao.area.cultura.id if talhao.area.cultura else None,
            'cultura_nome': talhao.area.cultura.nome if talhao.area.cultura else '',
            'safra_id': talhao.safra.id if talhao.safra else None,
            'safra_ano': talhao.safra.ano if talhao.safra else '',
            'pragas_possiveis': [
                {
                    'id': p.id,
                    'nome_comum': p.nome_comum,
                    'nome_cientifico': p.nome_cientifico,
                }
                for p in pragas
            ]
        })
    except Talhao.DoesNotExist:
        return Response({'error': 'Talhão não encontrado'}, status=404)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def praga_defensivos_recomendados(request, praga_id):
    """Retorna defensivos recomendados para uma praga"""
    try:
        praga = Praga.objects.get(
            id=praga_id,
            empresa=request.user.empresa
        )
        
        recomendacoes = RecomendacaoDefensivo.objects.filter(
            empresa=request.user.empresa,
            praga=praga
        ).select_related('produto').order_by('ordem')
        
        return Response({
            'praga_id': praga.id,
            'praga_nome': praga.nome_comum,
            'total_recomendacoes': recomendacoes.count(),
            'recomendacoes': [
                {
                    'recomendacao_id': rec.id,
                    'defensivo_id': rec.produto.id,
                    'defensivo_nome': rec.produto.nome,
                    'ordem': rec.ordem,
                    'badge': rec.get_ordem_display_badge(),
                    'efetividade': rec.efetividade,
                    'custo': rec.get_custo_relativo_display(),
                    'dosagem_min': float(rec.dosagem_minima),
                    'dosagem_max': float(rec.dosagem_maxima),
                    'unidade': rec.unidade_dosagem.nome,
                    'carencia': rec.carencia_minima,
                    'qtd_max_aplicacoes': rec.quantidade_maxima_aplicacoes,
                    'intervalo_reaplicacao': rec.intervalo_reaplicacao,
                    'observacoes': rec.observacoes,
                }
                for rec in recomendacoes
            ]
        })
    except Praga.DoesNotExist:
        return Response({'error': 'Praga não encontrada'}, status=404)
```

---

## 📋 ADMIN INTERFACE

```python
from django.contrib import admin

@admin.register(RecomendacaoDefensivo)
class RecomendacaoDefensivoAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'ordem', 'efetividade', 'custo_relativo', 'carencia_minima']
    list_filter = ['ordem', 'custo_relativo', 'efetividade', 'empresa']
    search_fields = ['praga__nome_comum', 'produto__nome']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Relacionamentos', {
            'fields': ('empresa', 'praga', 'produto')
        }),
        ('Recomendação', {
            'fields': ('ordem', 'efetividade', 'custo_relativo')
        }),
        ('Dosagem', {
            'fields': ('dosagem_minima', 'dosagem_maxima', 'unidade_dosagem')
        }),
        ('Aplicação', {
            'fields': ('carencia_minima', 'quantidade_maxima_aplicacoes', 'intervalo_reaplicacao')
        }),
        ('Observações', {
            'fields': ('observacoes',)
        }),
        ('Auditoria', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Receituario)
class ReceituarioAdmin(admin.ModelAdmin):
    list_display = ['numero', 'talhao', 'praga', 'status', 'data_aplicacao', 'agronomista', 'created_at']
    list_filter = ['status', 'data_aplicacao', 'empresa', 'created_at']
    search_fields = ['numero', 'talhao__nome', 'praga__nome_comum']
    readonly_fields = ['numero', 'created_at', 'created_by', 'updated_at', 'updated_by']
    
    fieldsets = (
        ('Identificação', {
            'fields': ('numero', 'empresa', 'status')
        }),
        ('Contexto Agrícola', {
            'fields': ('talhao', 'safra', 'cultura', 'praga')
        }),
        ('Defensivo e Aplicação', {
            'fields': ('recomendacao', 'produto', 'dosagem', 'unidade_dosagem', 'volume_calda')
        }),
        ('Data e Hora', {
            'fields': ('data_aplicacao', 'horario_aplicacao')
        }),
        ('Condições Climáticas', {
            'fields': ('temperatura', 'umidade', 'velocidade_vento', 'observacoes_clima'),
            'classes': ('collapse',)
        }),
        ('Responsáveis', {
            'fields': ('agronomista', 'created_by')
        }),
        ('Observações', {
            'fields': ('observacoes', 'motivo_rejeicao')
        }),
        ('Auditoria', {
            'fields': ('created_at', 'updated_at', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        else:
            obj.updated_by = request.user
        super().save_model(request, obj, form, change)
```

---

## 🧪 TESTES

```python
from django.test import TestCase, Client
from django.contrib.auth import get_user_model

User = get_user_model()

class ReceituarioTestCase(TestCase):
    
    def setUp(self):
        # Criar empresa
        self.empresa = Empresa.objects.create(nome_fantasia='Teste')
        
        # Criar usuário
        self.usuario = User.objects.create_user(
            username='agronomista',
            password='senha123',
            empresa=self.empresa
        )
        
        # Criar dados de teste
        self.fazenda = Fazenda.objects.create(empresa=self.empresa, nome='Fazenda Teste')
        self.area = Area.objects.create(fazenda=self.fazenda, nome='Área 1')
        self.talhao = Talhao.objects.create(area=self.area, nome='Talhão 1', area_hac=100)
        self.praga = Praga.objects.create(empresa=self.empresa, nome_comum='Lagarta')
        self.produto = Produto.objects.create(empresa=self.empresa, nome='Defensivo Teste')
        self.unidade = UnidadeMedida.objects.create(nome='mL/100L')
        
        # Criar recomendação
        self.recomendacao = RecomendacaoDefensivo.objects.create(
            empresa=self.empresa,
            praga=self.praga,
            produto=self.produto,
            dosagem_minima=25,
            dosagem_maxima=50,
            unidade_dosagem=self.unidade,
            carencia_minima=7,
        )
    
    def test_criar_receituario(self):
        """Teste de criação de receituário"""
        receituario = Receituario.objects.create(
            empresa=self.empresa,
            talhao=self.talhao,
            cultura=self.area.cultura,
            praga=self.praga,
            recomendacao=self.recomendacao,
            produto=self.produto,
            dosagem=35,
            unidade_dosagem=self.unidade,
            data_aplicacao='2025-02-10',
            created_by=self.usuario,
        )
        
        self.assertIsNotNone(receituario.numero)
        self.assertTrue(receituario.numero.startswith('REC-'))
        self.assertEqual(receituario.status, 'RASCUNHO')
    
    def test_api_defensivos_recomendados(self):
        """Teste de API de defensivos recomendados"""
        client = Client()
        client.login(username='agronomista', password='senha123')
        
        response = client.get(f'/api/praga/{self.praga.id}/defensivos-recomendados/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['recomendacoes']), 1)
        self.assertEqual(data['recomendacoes'][0]['dosagem_min'], 25)
```

---

## 🚀 CHECKLIST DE IMPLEMENTAÇÃO

```
FASE 1: Modelos e Admin (4 horas)
├─ [ ] Criar modelo RecomendacaoDefensivo
├─ [ ] Criar model Receituario
├─ [ ] Criar migrations
├─ [ ] Adicionar ao admin
├─ [ ] Testar no admin
└─ [ ] Criar seed de recomendações

FASE 2: API e Views (3 horas)
├─ [ ] Criar endpoints de API
├─ [ ] Implementar views de criação/edição
├─ [ ] Testar endpoints
└─ [ ] Validações

FASE 3: Frontend (2 horas)
├─ [ ] Criar template HTML
├─ [ ] Implementar JavaScript de autocomplete
├─ [ ] CSS e styling
└─ [ ] Testes na interface

FASE 4: Testes e Deploy (2 horas)
├─ [ ] Testes unitários
├─ [ ] Testes de integração
├─ [ ] Documentação
└─ [ ] Deploy
```

---

## 📱 FUNCIONALIDADES FUTURAS

```
Phase 2:
├─ [ ] Upload de fotos do campo
├─ [ ] Georreferenciamento do talhão
├─ [ ] Histórico de receituários por talhão
└─ [ ] Relatórios em PDF

Phase 3:
├─ [ ] Integração com operações (executar receituário)
├─ [ ] Rastreamento de aplicação
├─ [ ] Alertas de carência
└─ [ ] Conformidade legal
```

---

**Data de Criação:** 2025-02-04  
**Atualizado em:** 2025-02-04  
**Status:** Pronto para Implementação  
**Versão:** 1.0  

**Proximamente:** Quando iniciar a implementação, use este documento como referência completa!
