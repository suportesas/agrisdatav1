# Permissão Automática para Administradores - RF-055

## Resumo da Implementação

A permissão `view_other_fazendas_estoque` agora é **automaticamente concedida a todos os administradores** do sistema.

## Como Funciona

### 1. **Signal de Auto-Concessão** (usuarios/signals.py)
Quando um usuário é criado ou atualizado como administrador (superuser, staff ou tipo='ADMIN'), um Django signal automaticamente:
- Verifica se é admin
- Busca a permissão `cadastros.view_other_fazendas_estoque`
- Concede a permissão ao usuário (idempotente)
- Se deixar de ser admin, remove a permissão

### 2. **View Inteligente** (estoque/views.py)
A view `estoque_produtos_list()` agora verifica:
```python
can_choose_fazenda = is_admin(request.user) or request.user.has_perm('cadastros.view_other_fazendas_estoque')
```

Isso significa:
- **Admins** automaticamente veem o dropdown de escolha de fazenda
- **Usuários com permissão explícita** também veem (via Roles)
- **Outros usuários** só veem sua própria fazenda

### 3. **Aplicação Retroativa**
O script `setup_admin_permissions.py` foi executado e concedeu a permissão a todos os 4 admins existentes:
- ✓ (usuário vazio - superuser)
- ✓ edson@frutasterrabrasilis.com.br
- ✓ local@dev
- ✓ danieltavares@potiguarfruit.com

## Status

✓ **IMPLEMENTADO E ATIVO**

### Próximas Ações Automáticas:
1. Qualquer novo admin criado automaticamente terá a permissão (signal)
2. Se um admin for rebaixado (remover is_staff/is_superuser), perde a permissão automaticamente
3. Usuários não-admin podem receber a permissão via Roles (Roles UI)

## Teste Rápido

Acesse: http://localhost:8000/estoque/produtos/
- Se for admin, verá o dropdown "Escolher Fazenda"
- Se for usuário comum, não verá o dropdown

