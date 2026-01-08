# Roles e Gerenciamento de Permissões

Visão geral do novo módulo de Roles (Funções) por Empresa e como usá-lo.

## O que foi adicionado
- Modelo `Role` em `empresas.models`, vinculado a uma `Empresa` e a um `auth.Group` do Django.
- Campo `roles` (ManyToMany) em `usuarios.models.Usuario` para atribuição de funções.
- Management command `manage.py seed_roles` para criar funções padrão (Proprietário, Almoxarife, Operacional do Campo, Financeiro, Gerente, Vendedor) para todas as empresas.
- Views e endpoints JSON para listar roles e ler/atualizar permissões (`empresas.views.role_list` e `empresas.views.role_permissions`).
- Templates MVP: `empresas/roles_list.html` e partial `_roles_table.html` com JS para carregar e salvar permissões via AJAX.

## Passos para instalar / migrar
1. Criar migrações e aplicá-las:

```bash
python manage.py makemigrations
python manage.py migrate
```

2. Executar seed inicial de roles (cria roles padrão para cada empresa existente):

```bash
python manage.py seed_roles
```

3. Acessar a interface de Roles (usuário admin da empresa):
- URL: `/empresas/roles/` (necessário estar logado e ter uma empresa)

## Uso (MVP)
- Escolha uma função na lista.
- Clique na função para carregar a tabela de permissões (Módulo | Cadastrar | Editar | Excluir | Visualizar).
- Marque/desmarque checkboxes e clique em **Salvar** para aplicar as permissões à função.

As permissões são armazenadas no `auth.Group` associado à `Role`. Quando um usuário recebe a `Role` a partir do campo `roles`, ele herda as permissões do `Group`.

## Observações e próximos passos recomendados
- Atualmente o frontend é um MVP; podemos melhorar com agrupamento por módulo mais amigável, templates de permissões, import/export e logs/auditoria.
- Considerar adicionar página de administração de Roles no painel para criar/editar roles avançadas.

**Se quiser, prossigo agora com:** testes adicionais, aprimoramento da UI ou templates de import/export de permissões.