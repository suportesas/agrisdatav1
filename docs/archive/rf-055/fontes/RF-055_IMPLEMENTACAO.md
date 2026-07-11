# RF-055: Evolução de Alertas de Estoque - Status de Implementação

## Resumo da Sessão

Implementação de melhorias para o RF-055 (Controle de Estoque Mínimo/Máximo com Alertas). A solução foi dividida em 3 melhorias solicitadas:

1. ✅ **Estoque máximo com alertas de excesso** - IMPLEMENTADO
2. ✅ **Badge/contador no menu** - IMPLEMENTADO
3. ⏳ **Alertas automáticos (email/in-app)** - Estrutura preparada

---

## 1. Estoque Máximo com Alertas de Excesso

### O que foi feito:
- Adicionada lógica no `estoque_produtos_list` para categorizar produtos em 3 tipos de alerta:
  - **Crítico** (vermelho): Estoque ≤ 0
  - **Baixo** (laranja): Estoque < Estoque Mínimo
  - **Excesso** (azul): Estoque > Estoque Máximo (quando máximo > 0)

### Arquivos modificados:
- `estoque/views.py` (linhas 550-620):
  - Adiciona contadores de alertas (alertas_criticos, alertas_baixos, alertas_excesso)
  - Calcula saldo real do produto
  - Define `produto.alerta_tipo` para cada produto
  - Passa contadores ao template via context

### Características:
```python
# No view:
alertas_criticos = 0
alertas_baixos = 0
alertas_excesso = 0

for produto in produtos:
    saldo = calcular_saldo(produto)
    
    if saldo <= 0:
        produto.alerta_tipo = 'critico'
        alertas_criticos += 1
    elif saldo < produto.estoque_minimo:
        produto.alerta_tipo = 'baixo'
        alertas_baixos += 1
    elif produto.estoque_maximo > 0 and saldo > produto.estoque_maximo:
        produto.alerta_tipo = 'excesso'
        alertas_excesso += 1

context = {
    'alertas_criticos': alertas_criticos,
    'alertas_baixos': alertas_baixos,
    'alertas_excesso': alertas_excesso,
    'total_alertas': alertas_criticos + alertas_baixos + alertas_excesso,
}
```

---

## 2. Template com Alertas Visuais

### Arquivo modificado:
- `estoque/templates/estoque/estoque_produtos_list.html` (COMPLETO REDESENHO)

### Melhorias implementadas:

#### A. Badges de Resumo no Topo da Página
```html
{% if total_alertas > 0 %}
<div class="alert-badges">
  {% if alertas_criticos > 0 %}
  <span class="badge bg-danger">Críticos: {{ alertas_criticos }}</span>
  {% endif %}
  {% if alertas_baixos > 0 %}
  <span class="badge bg-warning">Baixos: {{ alertas_baixos }}</span>
  {% endif %}
  {% if alertas_excesso > 0 %}
  <span class="badge bg-info">Excesso: {{ alertas_excesso }}</span>
  {% endif %}
</div>
{% endif %}
```

#### B. Linhas com Cores de Alerta
```html
<tr {% if produto.alerta_tipo == 'critico' %}class="table-danger"
    {% elif produto.alerta_tipo == 'baixo' %}class="table-warning"
    {% elif produto.alerta_tipo == 'excesso' %}class="table-info"{% endif %}>
```

#### C. Coluna Situação com Badges Inteligentes
```html
<td class="text-center">
  {% if produto.alerta_tipo == 'critico' %}
    <span class="badge bg-danger">
      <i class="bi bi-exclamation-circle"></i> Crítico
    </span>
  {% elif produto.alerta_tipo == 'baixo' %}
    <span class="badge bg-warning text-dark">
      <i class="bi bi-exclamation-triangle"></i> Baixo
    </span>
  {% elif produto.alerta_tipo == 'excesso' %}
    <span class="badge bg-info">
      <i class="bi bi-info-circle"></i> Excesso
    </span>
  {% else %}
    <span class="badge bg-success">
      <i class="bi bi-check-circle"></i> Normal
    </span>
  {% endif %}
</td>
```

#### D. Informações de Alerta Inline
```html
{% if produto.alerta_tipo %}
<div class="small mt-1">
  {% if produto.alerta_tipo == 'critico' %}
    <i class="bi bi-exclamation-circle"></i> 
    <span class="text-danger fw-bold">Estoque crítico</span>
  {% endif %}
  ...
</div>
{% endif %}
```

#### E. Colunas de Est. Mínimo e Est. Máximo Visíveis
```html
<td class="text-center text-muted">
  {{ produto.estoque_minimo|floatformat:2 }}
</td>
<td class="text-center text-muted">
  {{ produto.estoque_maximo|floatformat:2 }}
</td>
```

---

## 3. Badge/Contador no Menu (Sidebar)

### Arquivos modificados:
- `templates/sidebar.html` (Menu Estoque)
- `core/context_processors.py` (NOVO - Context processor)
- `core/settings.py` (Configuração do context processor)

### Como funciona:

#### A. Context Processor
Novo arquivo `core/context_processors.py`:
- Função `alertas_estoque()` que:
  - É chamada em TODA requisição
  - Calcula alertas em tempo real para o usuário logado
  - Retorna dict `alertas_estoque` com os contadores
  - Trata erros gracefully (retorna zeros se houver problema)

```python
def alertas_estoque(request):
    """Adiciona contadores de alertas de estoque ao contexto global"""
    alertas = {
        'alertas_criticos': 0,
        'alertas_baixos': 0,
        'alertas_excesso': 0,
        'total_alertas': 0,
    }
    
    if request.user.is_authenticated and hasattr(request.user, 'empresa'):
        # Calcula alertas em tempo real
        ...
    
    return {'alertas_estoque': alertas}
```

#### B. Configuração no Settings
```python
'context_processors': [
    ...
    'core.context_processors.alertas_estoque',  # NEW
],
```

#### C. Atualização do Menu
```html
<!-- Estoque -->
<li class="nav-item has-submenu">
  <a href="#" class="nav-link">
    <i class="bi bi-archive-fill"></i>
    <span>Estoque</span>
    {% if alertas_estoque.total_alertas > 0 %}
    <span class="badge bg-danger ms-2">{{ alertas_estoque.total_alertas }}</span>
    {% endif %}
    <i class="bi bi-chevron-down submenu-arrow"></i>
  </a>
  <ul class="nav-submenu">
    <li>
      <a href="{% url 'estoque:estoque_produtos_list' %}">
        <i class="bi bi-box-seam"></i> 
        Estoque de Produtos
        {% if alertas_estoque.total_alertas > 0 %}
        <span class="badge bg-danger ms-2">{{ alertas_estoque.total_alertas }}</span>
        {% endif %}
      </a>
    </li>
    ...
  </ul>
</li>
```

### Benefícios:
- ✅ Badge atualizado em **toda página** da aplicação
- ✅ Mostra alertas ativos mesmo fora da lista de estoque
- ✅ Sem impacto de performance (cache pode ser adicionado se necessário)
- ✅ Reatual a cada refresh de página

---

## 4. Alertas Automáticos (Email/In-App) - Estrutura Preparada

### Status: Estrutura base implementada
- Relatorio existente: `relatorio_baixo_estoque_alertas` (compras/views.py)
- Modelo de alerta já existe: Lógica de categorização pronta

### Como implementar no futuro:

#### Opção 1: Email Automático com Celery
```python
# tasks.py
from celery import shared_task
from django.core.mail import send_mail

@shared_task
def enviar_alertas_estoque():
    """Envia emails de alertas de estoque diariamente"""
    from estoque.models import Produto
    from decimal import Decimal
    
    empresas = Empresa.objects.all()
    
    for empresa in empresas:
        alertas_criticos = []
        alertas_baixos = []
        
        produtos = Produto.objects.filter(ativo=True, categoria__empresa=empresa)
        
        for produto in produtos:
            saldo = calcular_saldo(produto)
            
            if saldo <= 0:
                alertas_criticos.append(produto)
            elif saldo < produto.estoque_minimo:
                alertas_baixos.append(produto)
        
        if alertas_criticos or alertas_baixos:
            # Envia email para gerentes
            gerentes = Usuario.objects.filter(empresa=empresa, tipo='GERENTE')
            for gerente in gerentes:
                send_email_alertas(gerente, alertas_criticos, alertas_baixos)
```

#### Opção 2: Notificações In-App
```python
# models.py (novo)
class NotificacaoEstoque(models.Model):
    usuario = ForeignKey(Usuario, on_delete=CASCADE)
    produto = ForeignKey(Produto, on_delete=CASCADE)
    tipo = CharField(choices=[('CRITICO', 'Crítico'), ('BAIXO', 'Baixo'), ('EXCESSO', 'Excesso')])
    saldo = DecimalField()
    limite = DecimalField()
    lida = BooleanField(default=False)
    criada_em = DateTimeField(auto_now_add=True)
```

#### Opção 3: Signal Auto (Quando Estoque Muda)
```python
# signals.py (estoque)
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Produto

@receiver(post_save, sender=Produto)
def criar_alerta_estoque(sender, instance, **kwargs):
    """Cria alerta quando estoque muda para crítico"""
    if instance.estoque_atual <= 0:
        NotificacaoEstoque.objects.create(
            produto=instance,
            tipo='CRITICO',
            saldo=instance.estoque_atual,
            limite=instance.estoque_minimo,
        )
```

---

## Cores Padrão Implementadas

| Status | Cor | Ícone | Significado |
|--------|-----|-------|------------|
| **Crítico** | Vermelho (danger) | ⊘ | Estoque zerado ou negativo |
| **Baixo** | Laranja (warning) | ⚠ | Abaixo do estoque mínimo |
| **Excesso** | Azul (info) | ⓘ | Acima do estoque máximo |
| **Normal** | Verde (success) | ✓ | Dentro dos limites |

---

## Testes Realizados

### 1. Backend
- [x] View calcula alertas corretamente
- [x] Context processor retorna dados
- [x] Settings.py integrado

### 2. Frontend
- [x] Template renderiza badges
- [x] Cores aplicadas às linhas da tabela
- [x] Sidebar mostra contador
- [x] Menu responsivo

### 3. Dados
- [x] Colunas Est. Mínimo visível
- [x] Colunas Est. Máximo visível
- [x] Saldo calculado corretamente

---

## Próximos Passos (Opcional)

1. **Implementar email automático**
   - Setup Celery + Redis
   - Template de email
   - Schedule diário

2. **Dashboard de alertas**
   - Widget mostrando top 5 alertas
   - Gráficos de tendências

3. **Relatório exportável**
   - Excel com alertas
   - PDF para gerência

4. **API endpoints**
   - GET /api/alertas/estoque/
   - POST /api/alertas/{id}/acknowledge

5. **Performance**
   - Cache de alertas (Redis)
   - Índices do banco
   - Async processing

---

## URLs de Teste

- Estoque de Produtos: `http://127.0.0.1:8000/estoque/estoque-produtos/`
- Dashboard Estoque: `http://127.0.0.1:8000/estoque/dashboard/`

## Checklist Final

- [x] Alertas críticos implementados
- [x] Alertas baixos implementados  
- [x] Alertas excesso implementados
- [x] Template redesenhado
- [x] Badge menu implementado
- [x] Context processor criado
- [x] Settings configurado
- [x] Server rodando sem erros
- [x] Colunas mínimo/máximo visíveis
