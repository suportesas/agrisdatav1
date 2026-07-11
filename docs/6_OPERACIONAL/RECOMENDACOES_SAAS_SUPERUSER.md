# 📊 RECOMENDAÇÕES PARA DASHBOARD SAAS - SUPERUSER

## 1️⃣ MÓDULOS RECOMENDADOS PARA MENU LATERAL DO SUPERUSER

### ✅ JÁ EXISTENTES (em sidebar.html):
- Empresas (Listar, Nova, Planos, Funções)
- Grupos Corporativos
- Usuários (Listar, Novo, Logs de Login)

### ❌ FALTANDO (IMPLEMENTAR):

#### **A) GESTÃO FINANCEIRA**
- **Invoices/Faturas** - Listar, criar, visualizar status
- **Cobranças** - Plano de pagamento, histórico de pagamentos
- **Relatório de Receitas** - Por período, por cliente
- **Gestão de Planos** - Usar/reasignar planos
- **Cancelamentos/Upgrades** - Histórico de mudanças de plano

#### **B) MONITORAMENTO & PERFORMANCE**
- **Dashboard Executivo** - Metrícas principais (total de empresas, receita, usuários por plano)
- **Uso de Planos** - Consumo por empresa (fazendas, usuários, talhões)
- **Avisos de Limite** - Alertas quando empresa estiver próxima do limite
- **Saúde do Sistema** - API disponibilidade, tempos de resposta

#### **C) LOGS & AUDITORIA**
- **Logs Centralizados** - Ações de usuários (create, update, delete)
- **Logs de Sistema** - Erros, exceções, performance
- **Auditoria de Planos** - Quem fez mudanças, quando, o quê
- **Relatório de Atividades** - Por empresa, por usuário, por data

#### **D) ANÁLISE & VISUALIZAÇÃO**
- **Gráficos de Crescimento** - Novos clientes, churn rate
- **Distribuição por Plano** - Quantos em cada plano
- **Mapa de Usuários** - Por região (se tiver campo de localização)
- **Relatórios Customizados** - Exportar para CSV/PDF

#### **E) TROUBLESHOOTING & BUGS**
- **Logs de Erro** - Stack trace, ocorrência, módulo afetado
- **Avisos de Performance** - Queries lentas, timeout
- **Relatório de Bugs** - Reportados e resolvidos
- **Health Check** - Status de cada serviço

---

## 2️⃣ VISUALIZAR CONSUMO DO PLANO POR EMPRESA

### Dados que já existem em Empresa model:
```python
- limite_fazendas (int)
- limite_usuarios (int)
- limite_talhoes (int)
- limite_produtos (int)
```

### Como implementar:
1. **Criar view de consumo**: Contar registros reais vs limites
2. **Dashboard de uso**: Gráfico de barras com % de uso
3. **Alertas**: Se >= 80% do limite
4. **Endpoint JSON**: Para gráficos em tempo real

---

## 3️⃣ CONTROLE FINANCEIRO PARA COBRANÇA

### Modelo recomendado:

```python
class Fatura(models.Model):
    # Identificação
    numero = CharField (único por empresa)
    empresa = ForeignKey(Empresa)
    periodo_inicio = DateField
    periodo_fim = DateField
    
    # Valores
    valor_base = DecimalField (valor do plano)
    valor_desconto = DecimalField (se houver)
    valor_extra = DecimalField (se consumo extra)
    valor_total = DecimalField
    
    # Status
    status = CharField (RASCUNHO/EMITIDA/ENVIADA/PAGA/CANCELADA)
    data_emissao = DateTimeField
    data_vencimento = DateField
    data_pagamento = DateTimeField (null)
    
    # Controle
    metodo_pagamento = CharField (BOLETO/PIX/CARTAO/BANCO)
    numero_boleto = CharField (opcional)
    classe Meta:
        indexes = [Index(fields=['empresa', 'data_emissao'])]
```

### Fluxo de cobrança:
1. ✅ Criar fatura automaticamente no dia X do mês
2. ✅ Enviar por email ao admin da empresa
3. ✅ Integração com gateway de pagamento
4. ✅ Webhook para confirmar pagamento
5. ✅ Reativar/bloquear empresa conforme pagamento

---

## 4️⃣ IMPLEMENTAR LOGS DE USUÁRIOS

### Opção 1: Usar django-audit-log (recomendado)
```bash
pip install django-audit-log
```

### Opção 2: Criar modelo customizado:

```python
class AuditoriaLog(models.Model):
    ACTIONS = [
        ('CREATE', 'Criação'),
        ('UPDATE', 'Atualização'),
        ('DELETE', 'Deleção'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('ERROR', 'Erro'),
    ]
    
    usuario = ForeignKey(Usuario)
    empresa = ForeignKey(Empresa, null=True, blank=True)
    acao = CharField(choices=ACTIONS)
    tabela = CharField # Ex: "cadastros.Fazenda"
    registro_id = IntegerField # ID do objeto modificado
    dados_antigos = JSONField (antes da mudança)
    dados_novos = JSONField (depois da mudança)
    ip_address = GenericIPAddressField
    user_agent = CharField
    data = DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            Index(fields=['usuario', 'data']),
            Index(fields=['empresa', 'data']),
            Index(fields=['acao', 'data']),
        ]
```

### Middleware para capturar logs:
- Decorador em views para log automático
- Signals do Django para log de delete/update
- Middleware para capturar todas requisições

---

## 5️⃣ GRÁFICOS EM DASHBOARD

### Usar biblioteca: Chart.js ou Plotly

```html
<!-- Chart.js (simples) -->
<canvas id="chartPlanos"></canvas>

<script>
  new Chart(document.getElementById('chartPlanos'), {
    type: 'doughnut',
    data: {
      labels: ['Pequeno', 'Médio', 'Grande'],
      datasets: [{
        data: [{{ pequeno_count }}, {{ medio_count }}, {{ grande_count }}],
        backgroundColor: ['#FF6384', '#36A2EB', '#FFCE56']
      }]
    }
  });
</script>
```

### Gráficos Recomendados:
1. **Distribuição de Planos** - Pizza (Pequeno/Médio/Grande)
2. **Receita ao Longo do Tempo** - Linha (últimos 12 meses)
3. **Novos Clientes** - Barras (por mês)
4. **Churn Rate** - % de cancelamentos
5. **Uso de Recursos** - Gauge (% de limite utilizado)

---

## 6️⃣ VISUALIZAR ERROS/BUGS

### Opção 1: Usar Sentry
```bash
pip install sentry-sdk
```

### Opção 2: Criar modelo ErrorLog:

```python
class ErrorLog(models.Model):
    ERROR_TYPES = [
        ('SYNTAX', 'Erro de Sintaxe'),
        ('DATABASE', 'Erro de Banco'),
        ('TIMEOUT', 'Timeout'),
        ('PERMISSION', 'Permissão'),
        ('VALIDATION', 'Validação'),
        ('OTHER', 'Outro'),
    ]
    
    tipo = CharField(choices=ERROR_TYPES)
    modulo = CharField # Ex: "cadastros.views"
    funcao = CharField # Ex: "fazenda_create"
    mensagem = TextField
    stack_trace = TextField
    usuario = ForeignKey(Usuario, null=True, blank=True)
    empresa = ForeignKey(Empresa, null=True, blank=True)
    status = CharField (ABERTO/RESOLVIDO/IGNORADO)
    data = DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-data']
        indexes = [Index(fields=['tipo', 'data'])]
```

### Middleware para capturar exceções:
```python
# Em settings.py - Configure logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
        'file': {'class': 'logging.FileHandler', 'filename': 'debug.log'},
    },
    'loggers': {
        'django': {'handlers': ['console', 'file'], 'level': 'DEBUG'},
    },
}
```

---

## 7️⃣ ESTRUTURA DE PASTAS PARA NOVOS MÓDULOS

```
core/                          # Novo app para gestão central
├── models.py
│   ├── Fatura
│   ├── AuditoriaLog
│   ├── ErrorLog
│   ├── ConsumoRecurso
│   └── Alerta
├── views.py                   # Vistas do dashboard executivo
├── forms.py                   # Formulários de faturas
├── templates/
│   ├── dashboard_executivo.html
│   ├── faturas_list.html
│   ├── auditoria_list.html
│   ├── erros_list.html
│   └── relatorios.html
└── urls.py

usuarios/
└── models.py (ADD: AuditoriaLog)
```

---

## 8️⃣ CHECKLIST DE IMPLEMENTAÇÃO

### FASE 1 - MVP (Mínimo viável)
- [ ] Dashboard Executivo (total de empresas, receita mensal, usuários online)
- [ ] Visualizar consumo de plano por empresa
- [ ] Logs de Login (já existe, só melhorar visualização)
- [ ] Relatório simples de faturas

### FASE 2 - Intermediário
- [ ] Modelo de Fatura + admin
- [ ] Cobrança automática
- [ ] AuditoriaLog centralizado
- [ ] Gráficos básicos (Chart.js)

### FASE 3 - Avançado
- [ ] ErrorLog + alertas
- [ ] Sentry integration
- [ ] Relatórios avançados (Plotly)
- [ ] Health checks

---

## 9️⃣ PRÓXIMOS PASSOS

Recomendo implementar nesta ordem:
1. **Dashboard Executivo** (3-4 horas) - Metrícas principais
2. **Visualizar Consumo** (2 horas) - Gráfico de uso por empresa
3. **Modelo de Fatura** (4 horas) - CRUD de faturas
4. **AuditoriaLog** (3 horas) - Registrar ações
5. **ErrorLog** (2 horas) - Rastrear erros

```
Total: ~14 horas para MVP completo
```

---

Você quer que eu implemente quais módulos primeiro? Recomendo começar com:
1. Dashboard Executivo 📊
2. Consumo de Planos 📈
3. Modelo de Fatura 💳
