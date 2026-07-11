.py# Quick Reference - FASE 3 Relatórios

## 🚀 Acesso Rápido

| Recurso | URL | Função |
|---------|-----|--------|
| Dashboard | `/estoque/` | Visão geral e acesso rápido |
| Análise ABC | `/estoque/relatorio/abc/` | Classificação Pareto de produtos |
| Comparativo | `/estoque/relatorio/comparativo/` | Tendências entre períodos |
| Auditoria | `/estoque/relatorio/auditoria/` | Quem fez, o quê, quando, onde |
| Rastreamento | `/estoque/relatorio/rastreamento/` | Jornada completa de lote |
| Alertas | `/estoque/relatorio/alertas/` | Estoque crítico/baixo/alerta |
| API | `/estoque/api/dashboard/dados/` | Dados JSON em tempo real |

---

## 📊 Análise ABC

```python
# View
def relatorio_analise_abc(request):
    # Calcula valor total em estoque
    # Classifica: A (80%), B (15%), C (5%)
    # Retorna template com tabela e cards

# Template
relatorio_abc.html
  - Cards: Classe A, B, C com contagem
  - Tabela: Produtos com percentuais
  - Gráfico: Pizza mostrando distribuição
```

**Quando usar:**
- Decidir quais produtos merecem mais atenção
- Implementar políticas de controle por classe
- Decidir sobre investimento em estoque

---

## 📈 Comparativo de Períodos

```python
# View
def relatorio_comparativo_periodos(request):
    # Divide período em 3 sub-períodos iguais
    # Calcula entradas/saídas em cada período
    # Mostra comparativo em cards e gráfico

# Template
relatorio_comparativo.html
  - Formulário: Seleção de datas
  - Cards: 3 períodos lado a lado
  - Gráfico: Barras comparativas
```

**Quando usar:**
- Identificar períodos de pico/baixa
- Prever demanda futura
- Detectar anomalias

---

## 🔍 Auditoria

```python
# View
def relatorio_auditoria(request):
    # Filtra por: tipo, usuário, data
    # Retorna últimas 100 transações
    # Mostra: data, tipo, produto, qty, usuário, status

# Template
relatorio_auditoria.html
  - Filtros: Tipo, Usuário, Datas
  - Tabela: Histórico de movimentações
```

**Quando usar:**
- Investigar discrepâncias
- Conformidade/Compliance
- Rastrear responsabilidades
- Análise forense

---

## 🏷️ Rastreamento de Lotes

```python
# View
def relatorio_rastreamento_lote(request, lote_id=None):
    if lote_id:
        # Mostra detalhes do lote específico
        # + Jornada completa (todas as movimentações)
    else:
        # Lista todos os lotes com busca

# Template
relatorio_rastreamento_lote.html
  - Lista de lotes (com busca)
  - Detalhes de lote
  - Histórico de movimentações
```

**Quando usar:**
- Rastreabilidade regulatória
- Investigação de qualidade
- Validação de datas
- Track & Trace

---

## ⚠️ Alertas de Estoque

```python
# View
def relatorio_baixo_estoque_alertas(request):
    # Categoriza produtos:
    # - Críticos: estoque <= 0
    # - Baixos: estoque < mínimo
    # - Alerta: próximo ao mínimo

# Template
relatorio_alertas.html
  - Resumo: Cards com contagem
  - Tabelas: Produtos por categoria
  - Botões: Ação rápida (solicitar compra)
```

**Quando usar:**
- Prevenção de ruptura
- Automação de reposição
- Planejamento de compra

---

## 🔌 API Dashboard

```python
# View
def api_dashboard_dados(request):
    # Retorna JSON com:
    # - Movimentações últimos 30 dias
    # - Top 5 produtos com menor estoque

# Response
{
  "movimentacoes": [
    {"data": "01/12", "entradas": 100, "saidas": 50}
  ],
  "produtos_baixos": [
    {"nome": "Ureia", "estoque": 10, "minimo": 50, "alerta": true}
  ]
}
```

**Como consumir:**
```javascript
fetch('/estoque/api/dashboard/dados/')
  .then(r => r.json())
  .then(data => {
    // Usar em gráficos/visualizações
  });
```

---

## 📝 Templates Criados

```
estoque/templates/estoque/
├── relatorio_abc.html              # Análise ABC
├── relatorio_comparativo.html       # Comparativo
├── relatorio_auditoria.html        # Auditoria
├── relatorio_rastreamento_lote.html # Rastreamento
├── relatorio_alertas.html          # Alertas
└── lista_lotes_rastreamento.html   # Lista (extends rastreamento)
```

---

## 📚 Arquivos Modificados

### estoque/views.py
```python
# Adicionadas:
- relatorio_analise_abc()
- relatorio_comparativo_periodos()
- relatorio_auditoria()
- relatorio_rastreamento_lote()
- relatorio_baixo_estoque_alertas()
- api_dashboard_dados()
```

### estoque/urls.py
```python
# Adicionadas rotas:
path('relatorio/abc/', ...)
path('relatorio/comparativo/', ...)
path('relatorio/auditoria/', ...)
path('relatorio/rastreamento/', ...)
path('relatorio/rastreamento/<int:lote_id>/', ...)
path('relatorio/alertas/', ...)
path('api/dashboard/dados/', ...)
```

### estoque/templates/estoque/dashboard.html
```html
<!-- Adicionada seção:
<h5>Relatórios Avançados (FASE 3)</h5>
Com 5 botões de acesso rápido -->
```

---

## 🎯 Fluxo de Uso Típico

### Gerente de Estoque
```
1. Acessar Dashboard
2. Ver Alertas de estoque baixo
3. Se necessário, ir para Análise ABC
4. Decidir em qual produto investir
5. Usar Auditoria para investigar discrepâncias
```

### Analista de Operações
```
1. Acessar Dashboard
2. Ver Comparativo de períodos
3. Identificar trends
4. Usar Auditoria para investigar
5. Rastrear lote específico se necessário
```

### Compliance/Auditoria
```
1. Acessar Auditoria
2. Filtrar por período/usuário
3. Validar transações
4. Rastrear lotes questionáveis
5. Gerar relatório
```

---

## ✅ Checklist de Testes

- [ ] Acessar Dashboard - verificar links novos
- [ ] Análise ABC - verificar classificação
- [ ] Comparativo - testar mudança de datas
- [ ] Auditoria - testar filtros
- [ ] Rastreamento - clicar em um lote
- [ ] Alertas - verificar categorização
- [ ] API - consumir em JavaScript

---

## 🐛 Troubleshooting

### Chart.js não carrega
```html
<!-- Verificar em template -->
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
```

### Dados vazios em relatório
```python
# Verificar se tem movimentações executadas
MovimentacaoEstoque.objects.filter(status='EXECUTADO').exists()
```

### Filtro não funciona
```python
# Verificar filtro na URL
?tipo=ENTRADA&usuario=admin&data_inicio=2024-01-01
```

---

## 📊 Exemplos de Query para Debug

```python
from estoque.models import MovimentacaoEstoque
from django.db.models import Sum

# Contar movimentações por tipo
MovimentacaoEstoque.objects.values('tipo').annotate(count=Count('id'))

# Total de quantidade movimentada
MovimentacaoEstoque.objects.aggregate(total=Sum('quantidade'))

# Produtos com estoque baixo
from produtos.models import Produto
Produto.objects.filter(estoque_atual__lt=F('estoque_minimo'))

# Últimas 10 movimentações
MovimentacaoEstoque.objects.all().order_by('-data_criacao')[:10]
```

---

## 🔐 Segurança

Todos os endpoints:
- ✅ Requerem `@login_required`
- ✅ Filtram por `empresa=request.user.empresa`
- ✅ Validam permissões de acesso

---

## 📞 Suporte

Para dúvidas sobre:
- **ABC:** Ver `FASE3_RELATORIOS_AVANCADOS.md`
- **Status geral:** Ver `PROJECT_STATUS.md`
- **Sessão:** Ver `SESSAO_FASE3.md`
- **Código:** Ver docstrings em views.py

---

**Versão:** 3.0 - FASE 3 Completa  
**Data:** 2024  
**Status:** ✅ Produção  
**Próximo:** FASE 4 - Transferências
