# RF-055: Guia de Extensão - Alertas Automáticos

## 📧 Configuração de Email Automático (Celery + Django)

### 1. Instalação de Dependências

```bash
pip install celery redis django-celery-beat
```

### 2. Configuração do settings.py

```python
# core/settings.py

# Celery Configuration
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'America/Sao_Paulo'

# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'seu-email@gmail.com'
EMAIL_HOST_PASSWORD = 'sua-senha-app'
DEFAULT_FROM_EMAIL = 'seu-email@gmail.com'
```

### 3. Arquivo: estoque/tasks.py

```python
"""Tasks assíncronas para alertas de estoque"""
from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.db.models import Sum, Q
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta

from .models import Produto, Lote, MovimentacaoEstoque
from empresas.models import Empresa
from usuarios.models import Usuario


def calcular_saldo(produto):
    """Calcula saldo real do produto"""
    # 1. Total de lotes disponiveis/bloqueados
    total_lotes = Lote.objects.filter(
        produto=produto,
        status__in=['DISPONIVEL', 'BLOQUEADO']
    ).aggregate(total=Sum('quantidade_atual'))['total'] or Decimal('0')
    
    # 2. Movimentacoes diretas (sem lote) EXECUTADAS
    movs_diretas_entrada = MovimentacaoEstoque.objects.filter(
        produto=produto,
        lote__isnull=True,
        tipo='ENTRADA',
        status='EXECUTADO'
    ).aggregate(total=Sum('quantidade'))['total'] or Decimal('0')
    
    movs_diretas_saida = MovimentacaoEstoque.objects.filter(
        produto=produto,
        lote__isnull=True,
        tipo='SAIDA',
        status='EXECUTADO'
    ).aggregate(total=Sum('quantidade'))['total'] or Decimal('0')
    
    # Saldo = Lotes + (Entradas diretas - Saidas diretas)
    saldo = Decimal(total_lotes) + (Decimal(movs_diretas_entrada) - Decimal(movs_diretas_saida))
    return saldo


def categorizar_alerta(produto, saldo):
    """Categoriza o alerta do produto"""
    if saldo <= 0:
        return 'CRITICO', f'Estoque zerado - Saldo: {saldo}'
    elif saldo < produto.estoque_minimo:
        return 'BAIXO', f'Abaixo do mínimo - Saldo: {saldo}, Mínimo: {produto.estoque_minimo}'
    elif produto.estoque_maximo > 0 and saldo > produto.estoque_maximo:
        return 'EXCESSO', f'Acima do máximo - Saldo: {saldo}, Máximo: {produto.estoque_maximo}'
    else:
        return None, None


@shared_task
def enviar_alertas_estoque_diarios():
    """
    Task agendada para enviar alertas de estoque diariamente
    Execute: python manage.py celery beat
    """
    empresas = Empresa.objects.all()
    
    for empresa in empresas:
        produtos_alertas = {
            'CRITICO': [],
            'BAIXO': [],
            'EXCESSO': [],
        }
        
        produtos = Produto.objects.filter(ativo=True, categoria__empresa=empresa)
        
        # Calcula alertas
        for produto in produtos:
            saldo = calcular_saldo(produto)
            tipo_alerta, descricao = categorizar_alerta(produto, saldo)
            
            if tipo_alerta:
                produtos_alertas[tipo_alerta].append({
                    'produto': produto,
                    'saldo': saldo,
                    'descricao': descricao,
                })
        
        # Se houver alertas, envia para gerentes
        if any(produtos_alertas.values()):
            gerentes = Usuario.objects.filter(
                empresa=empresa,
                groups__name__in=['Gerente', 'Admin'],
                is_active=True
            )
            
            for gerente in gerentes:
                enviar_email_alertas(gerente, empresa, produtos_alertas)
            
            # Registra log
            print(f"[{timezone.now()}] Alertas enviados para {empresa.nome}")


def enviar_email_alertas(usuario, empresa, produtos_alertas):
    """Envia email com alertas para um usuário"""
    contexto = {
        'usuario': usuario,
        'empresa': empresa,
        'alertas': produtos_alertas,
        'total_alertas': sum(len(prods) for prods in produtos_alertas.values()),
    }
    
    # Renderiza template HTML
    html_message = render_to_string(
        'estoque/email/alertas_estoque.html',
        contexto
    )
    
    # Envia email
    send_mail(
        subject=f'[{empresa.nome}] Alertas de Estoque - {timezone.now().strftime("%d/%m/%Y")}',
        message='Veja os alertas de estoque abaixo.',
        from_email='noreply@erpagricola.com',
        recipient_list=[usuario.email],
        html_message=html_message,
        fail_silently=False,
    )


@shared_task
def verificar_alertas_em_tempo_real(produto_id):
    """
    Verifica se um produto entrou em alerta
    Chamada quando produto é movimentado
    """
    try:
        produto = Produto.objects.get(id=produto_id)
        saldo = calcular_saldo(produto)
        tipo_alerta, descricao = categorizar_alerta(produto, saldo)
        
        if tipo_alerta:
            # Notifica gerentes da empresa
            gerentes = Usuario.objects.filter(
                empresa=produto.categoria.empresa,
                is_staff=True,
                is_active=True
            )
            
            for gerente in gerentes:
                # Cria notificação in-app
                criar_notificacao_alerta(gerente, produto, tipo_alerta, descricao)
                
                # Envia email (opcional)
                # enviar_email_alerta_urgente(gerente, produto, tipo_alerta)
    
    except Produto.DoesNotExist:
        pass


def criar_notificacao_alerta(usuario, produto, tipo_alerta, descricao):
    """Cria uma notificação in-app de alerta"""
    from .models import NotificacaoEstoque
    
    NotificacaoEstoque.objects.create(
        usuario=usuario,
        produto=produto,
        tipo=tipo_alerta,
        descricao=descricao,
        lida=False,
    )
```

### 4. Arquivo: estoque/models.py (Adicionar Modelo)

```python
from django.db import models
from django.contrib.auth import get_user_model
from .models import Produto

User = get_user_model()


class NotificacaoEstoque(models.Model):
    """Notificações de alerta de estoque in-app"""
    
    TIPOS_ALERTA = [
        ('CRITICO', 'Crítico'),
        ('BAIXO', 'Baixo'),
        ('EXCESSO', 'Excesso'),
    ]
    
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notificacoes_estoque')
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=20, choices=TIPOS_ALERTA)
    descricao = models.TextField()
    lida = models.BooleanField(default=False)
    criada_em = models.DateTimeField(auto_now_add=True)
    lida_em = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-criada_em']
        verbose_name_plural = 'Notificações de Estoque'
        indexes = [
            models.Index(fields=['usuario', '-criada_em']),
            models.Index(fields=['usuario', 'lida']),
        ]
    
    def __str__(self):
        return f"{self.get_tipo_display()} - {self.produto.nome}"
    
    def marcar_como_lida(self):
        if not self.lida:
            from django.utils import timezone
            self.lida = True
            self.lida_em = timezone.now()
            self.save()


class AlertaEstoqueHistorico(models.Model):
    """Histórico de alertas para relatórios"""
    
    TIPOS_ALERTA = [
        ('CRITICO', 'Crítico'),
        ('BAIXO', 'Baixo'),
        ('EXCESSO', 'Excesso'),
    ]
    
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE)
    tipo = models.CharField(max_length=20, choices=TIPOS_ALERTA)
    saldo = models.DecimalField(max_digits=15, decimal_places=4)
    limite_min = models.DecimalField(max_digits=15, decimal_places=4)
    limite_max = models.DecimalField(max_digits=15, decimal_places=4)
    data_alerta = models.DateTimeField(auto_now_add=True)
    resolvido = models.BooleanField(default=False)
    data_resolucao = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-data_alerta']
        verbose_name_plural = 'Histórico de Alertas'
        indexes = [
            models.Index(fields=['produto', '-data_alerta']),
            models.Index(fields=['empresa', '-data_alerta']),
            models.Index(fields=['resolvido']),
        ]
    
    def __str__(self):
        return f"{self.produto.nome} - {self.get_tipo_display()}"
```

### 5. Arquivo: estoque/signals.py

```python
"""Signals para criar alertas ao salvar movimentações"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import MovimentacaoEstoque
from .tasks import verificar_alertas_em_tempo_real


@receiver(post_save, sender=MovimentacaoEstoque)
def criar_alerta_ao_movimentar_estoque(sender, instance, created, **kwargs):
    """
    Quando uma movimentação é executada, verifica se há alerta
    """
    if created and instance.status == 'EXECUTADO':
        # Verifica alertas do produto (task assíncrona)
        verificar_alertas_em_tempo_real.delay(instance.produto.id)
```

### 6. Arquivo: estoque/admin.py (Adicionar)

```python
from django.contrib import admin
from .models import NotificacaoEstoque, AlertaEstoqueHistorico


@admin.register(NotificacaoEstoque)
class NotificacaoEstoqueAdmin(admin.ModelAdmin):
    list_display = ('produto', 'usuario', 'tipo', 'criada_em', 'lida')
    list_filter = ('tipo', 'lida', 'criada_em')
    search_fields = ('produto__nome', 'usuario__username')
    readonly_fields = ('criada_em', 'lida_em')
    
    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ['usuario', 'produto', 'tipo']
        return self.readonly_fields


@admin.register(AlertaEstoqueHistorico)
class AlertaEstoqueHistoricoAdmin(admin.ModelAdmin):
    list_display = ('produto', 'tipo', 'saldo', 'data_alerta', 'resolvido')
    list_filter = ('tipo', 'resolvido', 'data_alerta')
    search_fields = ('produto__nome',)
    readonly_fields = ('data_alerta', 'data_resolucao')
    date_hierarchy = 'data_alerta'
```

### 7. Template: estoque/email/alertas_estoque.html

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {
            font-family: Arial, sans-serif;
            color: #333;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 600px;
            margin: 20px auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .header {
            border-bottom: 3px solid #007bff;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }
        .header h1 {
            margin: 0;
            color: #007bff;
            font-size: 24px;
        }
        .alerta-section {
            margin-bottom: 20px;
        }
        .alerta-section h2 {
            padding: 10px;
            margin: 0 0 10px 0;
            color: white;
            border-radius: 4px;
        }
        .alerta-critico h2 {
            background-color: #dc3545;
        }
        .alerta-baixo h2 {
            background-color: #ffc107;
            color: #333;
        }
        .alerta-excesso h2 {
            background-color: #17a2b8;
        }
        .produto-item {
            border-left: 4px solid #ddd;
            padding: 10px 0 10px 15px;
            margin-bottom: 10px;
        }
        .alerta-critico .produto-item {
            border-color: #dc3545;
        }
        .alerta-baixo .produto-item {
            border-color: #ffc107;
        }
        .alerta-excesso .produto-item {
            border-color: #17a2b8;
        }
        .produto-nome {
            font-weight: bold;
            font-size: 14px;
        }
        .produto-detalhe {
            font-size: 12px;
            color: #666;
            margin-top: 5px;
        }
        .footer {
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            text-align: center;
            color: #999;
            font-size: 12px;
        }
        .action-button {
            display: inline-block;
            margin-top: 10px;
            padding: 10px 20px;
            background-color: #007bff;
            color: white;
            text-decoration: none;
            border-radius: 4px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚨 Alertas de Estoque</h1>
            <p>{{ empresa.nome }} - {{ data|date:"d/m/Y H:i" }}</p>
        </div>
        
        <div>
            <p>Olá <strong>{{ usuario.get_full_name }}</strong>,</p>
            <p>Existem <strong>{{ total_alertas }}</strong> produto(s) com alerta(s) de estoque. Verifique abaixo:</p>
        </div>

        <!-- Críticos -->
        {% if alertas.CRITICO %}
        <div class="alerta-section alerta-critico">
            <h2>🔴 Estoque Crítico ({{ alertas.CRITICO|length }})</h2>
            {% for item in alertas.CRITICO %}
            <div class="produto-item">
                <div class="produto-nome">{{ item.produto.nome }}</div>
                <div class="produto-detalhe">{{ item.descricao }}</div>
                <div class="produto-detalhe">Código: {{ item.produto.codigo }}</div>
            </div>
            {% endfor %}
        </div>
        {% endif %}

        <!-- Baixos -->
        {% if alertas.BAIXO %}
        <div class="alerta-section alerta-baixo">
            <h2>🟠 Estoque Baixo ({{ alertas.BAIXO|length }})</h2>
            {% for item in alertas.BAIXO %}
            <div class="produto-item">
                <div class="produto-nome">{{ item.produto.nome }}</div>
                <div class="produto-detalhe">{{ item.descricao }}</div>
                <div class="produto-detalhe">Código: {{ item.produto.codigo }}</div>
            </div>
            {% endfor %}
        </div>
        {% endif %}

        <!-- Excesso -->
        {% if alertas.EXCESSO %}
        <div class="alerta-section alerta-excesso">
            <h2>🔵 Estoque em Excesso ({{ alertas.EXCESSO|length }})</h2>
            {% for item in alertas.EXCESSO %}
            <div class="produto-item">
                <div class="produto-nome">{{ item.produto.nome }}</div>
                <div class="produto-detalhe">{{ item.descricao }}</div>
                <div class="produto-detalhe">Código: {{ item.produto.codigo }}</div>
            </div>
            {% endfor %}
        </div>
        {% endif %}

        <a href="http://127.0.0.1:8000/estoque/estoque-produtos/" class="action-button">
            Ver Estoque Completo →
        </a>

        <div class="footer">
            <p>Você recebeu este email porque é gerente/admin de {{ empresa.nome }}</p>
            <p>ERP Agrícola © 2025</p>
        </div>
    </div>
</body>
</html>
```

### 8. Arquivo: estoque/apps.py (Registrar Signals)

```python
from django.apps import AppConfig


class EstoqueConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'estoque'
    
    def ready(self):
        # Registra signals
        from . import signals  # noqa
```

### 9. Arquivo: core/celery.py

```python
"""Celery configuration for Django"""
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

app = Celery('core')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


# Schedule de tarefas
app.conf.beat_schedule = {
    'enviar-alertas-estoque': {
        'task': 'estoque.tasks.enviar_alertas_estoque_diarios',
        'schedule': crontab(hour=8, minute=0),  # 8h da manhã todo dia
    },
    'enviar-alertas-estoque-tarde': {
        'task': 'estoque.tasks.enviar_alertas_estoque_diarios',
        'schedule': crontab(hour=14, minute=0),  # 14h (2h da tarde) todo dia
    },
}


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
```

### 10. Executar Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 11. Executar Celery (3 abas do terminal)

```bash
# Terminal 1: Redis
redis-server

# Terminal 2: Celery Worker
celery -A core worker -l info

# Terminal 3: Celery Beat (scheduler)
celery -A core beat -l info

# Terminal 4: Django (já rodando)
python manage.py runserver
```

---

## 🔔 Views para Notificações In-App

```python
# estoque/views.py

from django.http import JsonResponse
from django.views.decorators.http import require_GET
from .models import NotificacaoEstoque


@require_GET
def obter_notificacoes_nao_lidas(request):
    """API endpoint para obter notificações não lidas"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    notificacoes = NotificacaoEstoque.objects.filter(
        usuario=request.user,
        lida=False
    ).values('id', 'produto__nome', 'tipo', 'descricao', 'criada_em')
    
    return JsonResponse({
        'count': notificacoes.count(),
        'notificacoes': list(notificacoes)
    })


@require_GET
def marcar_notificacao_como_lida(request, notificacao_id):
    """Marca uma notificação como lida"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    notificacao = NotificacaoEstoque.objects.filter(
        id=notificacao_id,
        usuario=request.user
    ).first()
    
    if notificacao:
        notificacao.marcar_como_lida()
        return JsonResponse({'success': True})
    
    return JsonResponse({'error': 'Not found'}, status=404)
```

---

## 📊 Dashboard Widget (Futuro)

```python
# dashboard/views.py

def dashboard_alertas_estoque(request):
    """Widget de alertas para dashboard"""
    from estoque.models import AlertaEstoqueHistorico
    from django.db.models import Count
    from datetime import timedelta
    from django.utils import timezone
    
    empresa = request.user.empresa
    dias_7 = timezone.now() - timedelta(days=7)
    
    # Top 5 produtos com mais alertas
    top_produtos = AlertaEstoqueHistorico.objects.filter(
        empresa=empresa,
        data_alerta__gte=dias_7
    ).values('produto__nome').annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    # Alertas por tipo (últimos 7 dias)
    alertas_por_tipo = AlertaEstoqueHistorico.objects.filter(
        empresa=empresa,
        data_alerta__gte=dias_7
    ).values('tipo').annotate(count=Count('id'))
    
    return {
        'top_produtos': top_produtos,
        'alertas_por_tipo': {item['tipo']: item['count'] for item in alertas_por_tipo},
    }
```

---

**Status**: 🟡 Código pronto para implementação  
**Prioridade**: Alta (Automação)  
**Tempo estimado**: 2-3 dias de desenvolvimento
