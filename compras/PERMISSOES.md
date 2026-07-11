# Configuração de Permissões - Módulo de Compras

## Permissões Customizadas a Implementar

### 1. Permissões de Solicitação

```python
# compras/models.py - adicionar em SolicitacaoCompra Meta
class Meta:
    permissions = [
        ('aprovar_solicitacaocompra', 'Pode aprovar solicitações de compra'),
        ('cancelar_solicitacaocompra', 'Pode cancelar solicitações de compra'),
        ('add_solicitacao_emergencial_basico', 'Pode criar compras emergenciais até R$ 10.000'),
        ('add_solicitacao_emergencial_medio', 'Pode criar compras emergenciais até R$ 50.000'),
        ('add_solicitacao_emergencial_total', 'Pode criar compras emergenciais sem limite'),
    ]
```

### 2. Permissões de Cotação

```python
# compras/models.py - adicionar em Cotacao Meta
class Meta:
    permissions = [
        ('selecionar_fornecedor', 'Pode selecionar fornecedor vencedor'),
        ('concluir_cotacao', 'Pode concluir cotações'),
    ]
```

## Implementação nas Views

### views.py - Validação Emergencial

```python
from django.contrib.auth.decorators import permission_required
from django.core.exceptions import PermissionDenied

@login_required
@transaction.atomic
def solicitacao_create(request):
    """Cria nova solicitação de compra"""
    if request.method == 'POST':
        form = SolicitacaoCompraForm(request.POST)
        formset = ItemSolicitacaoFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            solicitacao = form.save(commit=False)
            
            # VALIDAÇÃO EMERGENCIAL
            if solicitacao.emergencial:
                # Verifica se tem alguma permissão emergencial
                if not (request.user.has_perm('compras.add_solicitacao_emergencial_basico') or 
                       request.user.has_perm('compras.add_solicitacao_emergencial_medio') or
                       request.user.has_perm('compras.add_solicitacao_emergencial_total')):
                    messages.error(
                        request, 
                        'Você não tem permissão para criar compras emergenciais. '
                        'Contate seu supervisor.'
                    )
                    return redirect('compras:solicitacao_list')
                
                # TODO: Validar valor total vs permissão
                # valor_total = calcular_valor_total(formset)
                # validar_limite_emergencial(request.user, valor_total)
            
            # ... resto do código
```

### views.py - Validação de Aprovação

```python
@login_required
@permission_required('compras.aprovar_solicitacaocompra', raise_exception=True)
def solicitacao_aprovar(request, pk):
    """Aprova a solicitação"""
    solicitacao = get_object_or_404(
        SolicitacaoCompra,
        pk=pk,
        empresa=request.user.empresa
    )
    
    try:
        solicitacao.aprovar(request.user)
        messages.success(
            request,
            f'Solicitação {solicitacao.numero} aprovada com sucesso!'
        )
    except Exception as e:
        messages.error(request, str(e))
    
    return redirect('compras:solicitacao_detail', pk=pk)
```

### views.py - Validação Seleção de Fornecedor

```python
@login_required
@permission_required('compras.selecionar_fornecedor', raise_exception=True)
def selecionar_fornecedor(request, proposta_pk):
    """Marca um fornecedor como selecionado"""
    # ... código existente
```

## Implementação nos Templates

### solicitacao_form.html - Esconder checkbox se sem permissão

```django
<!-- Compra Emergencial -->
{% if perms.compras.add_solicitacao_emergencial_basico or 
      perms.compras.add_solicitacao_emergencial_medio or 
      perms.compras.add_solicitacao_emergencial_total %}
<div class="row mt-3">
    <div class="col-12">
        <div class="alert alert-warning border-warning">
            <!-- ... conteúdo da ajuda ... -->
        </div>
        
        <div class="form-check form-switch">
            {{ form.emergencial }}
            <label class="form-check-label" for="id_emergencial">
                <strong>{{ form.emergencial.label }}</strong>
                <span class="badge bg-danger ms-2">Pula Aprovação</span>
            </label>
        </div>
    </div>
</div>
{% else %}
<div class="row mt-3">
    <div class="col-12">
        <div class="alert alert-secondary">
            <i class="bi bi-lock"></i> <strong>Compras Emergenciais Restritas</strong><br>
            Você não tem permissão para criar compras emergenciais.
            Entre em contato com seu supervisor se necessário.
        </div>
    </div>
</div>
{% endif %}
```

### solicitacao_detail.html - Esconder botão aprovar

```django
<!-- Ações -->
{% if solicitacao.status == 'PENDENTE' and perms.compras.aprovar_solicitacaocompra %}
<a href="{% url 'compras:solicitacao_aprovar' solicitacao.pk %}" 
   class="btn btn-success btn-sm w-100 mb-2"
   onclick="return confirm('Deseja aprovar esta solicitação?')">
    <i class="fas fa-check"></i> Aprovar Solicitação
</a>
{% elif solicitacao.status == 'PENDENTE' %}
<div class="alert alert-secondary small">
    Aguardando aprovação de usuário com permissão.
</div>
{% endif %}
```

## Função Auxiliar - Validar Limite

```python
# compras/utils.py (criar arquivo)
from decimal import Decimal
from django.core.exceptions import PermissionDenied

def validar_limite_emergencial(user, valor_total):
    """
    Valida se o usuário pode criar emergencial com o valor informado
    
    Args:
        user: Usuário atual
        valor_total: Valor total da solicitação (Decimal)
    
    Raises:
        PermissionDenied: Se exceder limite
    """
    valor_total = Decimal(str(valor_total))
    
    # Diretor - sem limite
    if user.has_perm('compras.add_solicitacao_emergencial_total'):
        return True
    
    # Gerente - até 50k
    if user.has_perm('compras.add_solicitacao_emergencial_medio'):
        if valor_total <= Decimal('50000.00'):
            return True
        raise PermissionDenied(
            f'Compras emergenciais acima de R$ 50.000 requerem aprovação de Diretor. '
            f'Valor solicitado: R$ {valor_total:,.2f}'
        )
    
    # Supervisor - até 10k
    if user.has_perm('compras.add_solicitacao_emergencial_basico'):
        if valor_total <= Decimal('10000.00'):
            return True
        raise PermissionDenied(
            f'Compras emergenciais acima de R$ 10.000 requerem aprovação de Gerente. '
            f'Valor solicitado: R$ {valor_total:,.2f}'
        )
    
    # Sem permissão
    raise PermissionDenied(
        'Você não tem permissão para criar compras emergenciais. '
        'Contate seu supervisor.'
    )


def calcular_valor_total_items(items):
    """
    Calcula valor total estimado dos itens
    Para usar quando produto tiver campo de preço médio
    
    Args:
        items: QuerySet ou lista de ItemSolicitacaoCompra
        
    Returns:
        Decimal: Valor total estimado
    """
    total = Decimal('0.00')
    for item in items:
        if hasattr(item.produto, 'preco_medio') and item.produto.preco_medio:
            total += item.produto.preco_medio * item.quantidade
    return total
```

## Configuração nos Groups (Django Admin)

### Criar Groups

1. **Supervisor Compras**
   - `compras.add_solicitacaocompra`
   - `compras.view_solicitacaocompra`
   - `compras.add_solicitacao_emergencial_basico` (até 10k)
   - `compras.add_cotacao`
   - `compras.view_cotacao`

2. **Gerente Compras**
   - `compras.add_solicitacaocompra`
   - `compras.view_solicitacaocompra`
   - `compras.change_solicitacaocompra`
   - `compras.aprovar_solicitacaocompra`
   - `compras.add_solicitacao_emergencial_medio` (até 50k)
   - `compras.add_cotacao`
   - `compras.view_cotacao`
   - `compras.change_cotacao`
   - `compras.selecionar_fornecedor`
   - `compras.concluir_cotacao`

3. **Diretor**
   - Todas as permissões acima +
   - `compras.add_solicitacao_emergencial_total` (sem limite)
   - `compras.cancelar_solicitacaocompra`
   - `compras.delete_solicitacaocompra`

## Notificações (Implementação Futura)

```python
# compras/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import SolicitacaoCompra

User = get_user_model()

@receiver(post_save, sender=SolicitacaoCompra)
def notificar_emergencial(sender, instance, created, **kwargs):
    """
    Notifica superiores quando compra emergencial é criada
    """
    if created and instance.emergencial:
        # Buscar superiores da hierarquia
        superiores = User.objects.filter(
            empresa=instance.empresa,
            tipo__in=['GERENTE', 'DIRETOR']
        )
        
        # Enviar notificação/email
        mensagem = (
            f"Compra EMERGENCIAL criada por {instance.solicitante.get_full_name()}\n"
            f"Número: {instance.numero}\n"
            f"Justificativa: {instance.justificativa_emergencial}\n"
            f"Data Necessidade: {instance.data_necessidade}\n"
        )
        
        # TODO: Implementar envio de email/notificação
        # send_notification(superiores, mensagem)
```

## Auditoria e Relatórios

### Relatório de Compras Emergenciais

```python
# compras/views.py
@login_required
@permission_required('compras.view_relatorio_emergenciais')
def relatorio_emergenciais(request):
    """Relatório de uso de compras emergenciais"""
    from django.db.models import Count, Q
    from datetime import datetime, timedelta
    
    # Últimos 30 dias
    data_inicio = datetime.now() - timedelta(days=30)
    
    # Total e emergenciais
    total = SolicitacaoCompra.objects.filter(
        empresa=request.user.empresa,
        data_solicitacao__gte=data_inicio
    ).count()
    
    emergenciais = SolicitacaoCompra.objects.filter(
        empresa=request.user.empresa,
        emergencial=True,
        data_solicitacao__gte=data_inicio
    ).count()
    
    percentual = (emergenciais / total * 100) if total > 0 else 0
    
    # Por usuário
    por_usuario = SolicitacaoCompra.objects.filter(
        empresa=request.user.empresa,
        emergencial=True,
        data_solicitacao__gte=data_inicio
    ).values(
        'solicitante__username',
        'solicitante__first_name'
    ).annotate(
        total=Count('id')
    ).order_by('-total')
    
    # Alerta se > 20%
    alerta = percentual > 20
    
    context = {
        'total': total,
        'emergenciais': emergenciais,
        'percentual': percentual,
        'por_usuario': por_usuario,
        'alerta': alerta,
        'data_inicio': data_inicio,
    }
    
    return render(request, 'compras/relatorio_emergenciais.html', context)
```

## Checklist de Implementação

- [ ] Adicionar permissões customizadas nos models (Meta)
- [ ] Criar migrations com as permissões
- [ ] Criar Groups no Django Admin (Supervisor, Gerente, Diretor)
- [ ] Implementar validação nas views
- [ ] Atualizar templates com verificação de permissões
- [ ] Criar função de validação de limite de valor
- [ ] Implementar signals para notificações
- [ ] Criar relatório de uso de emergenciais
- [ ] Criar tela de auditoria
- [ ] Documentar processo para administradores
- [ ] Treinar usuários sobre permissões
- [ ] Testar todos os cenários

## Notas de Implementação

**Prioridade:** Média (após completar fluxo básico de compras)

**Estimativa:** 2-3 dias de desenvolvimento + 1 dia de testes

**Dependências:** 
- Sistema de notificações (email/interno)
- Dashboard de relatórios

**Impacto:** Alto - muda workflow de todos os usuários de compras
