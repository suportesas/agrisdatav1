Owner: Operacao
Status: Approved
Last Updated: 2026-07-10
Scope: Controle de acesso por empresa

# Roles e Permissões

## Objetivo
Consolidar o modelo de funções e permissões por empresa para uso operacional.

## O que existe
- Modelo `Role` em `empresas.models`, vinculado a uma `Empresa` e a um `auth.Group` do Django.
- Campo `roles` (ManyToMany) em `usuarios.models.Usuario` para atribuição de funções — um usuário pode ter múltiplas roles.
- Management command `python manage.py seed_roles` cria funções padrão para todas as empresas existentes: Proprietário, Almoxarife, Operacional do Campo, Financeiro, Gerente, Vendedor.
- Views/endpoints JSON para listar roles e ler/atualizar permissões: `empresas.views.role_list`, `empresas.views.role_permissions`.
- Templates: `empresas/roles_list.html` + partial `_roles_table.html` (JS carrega/salva permissões via AJAX).
- Templates de permissões (salvar/exportar/aplicar) e aplicação em massa (bulk) via endpoints JSON, com registro de auditoria.

Permissões ficam armazenadas no `auth.Group` associado à `Role`; ao receber uma `Role`, o usuário herda as permissões do `Group`.

## Instalação / operação básica
1. Migrações: `python manage.py makemigrations && python manage.py migrate`
2. Seed inicial: `python manage.py seed_roles`
3. Acessar `/empresas/roles/` (usuário admin da empresa; também acessível via botão "Gerenciar Funções (Permissões)" em "Minha Empresa"). Criar nova função em `/empresas/roles/novo/`.
4. Selecionar a função → tabela de permissões (Módulo | Cadastrar | Editar | Excluir | Visualizar) → marcar/desmarcar → Salvar.

## Endpoints de template/bulk
- `POST /empresas/roles/<role_id>/permissions/save-template/` — salva template a partir das permissões atuais da role.
- `GET /empresas/roles/templates/` — lista templates da empresa.
- `POST /empresas/roles/<role_id>/permissions/apply-template/` — aplica template a uma role.
- `POST /empresas/roles/templates/apply-bulk/` — aplica template a múltiplas roles.

## Regras de governança
- Sempre validar isolamento por empresa (uma `Role`/`Group` nunca deve vazar permissão entre empresas).
- Evitar permissão ampla sem justificativa.
- Manter trilha de auditoria para alteração massiva (bulk apply).

## Integração com testes
- E2E deve cobrir: criar role, alterar permissão, validar acesso.
- Testes de segurança devem cobrir acesso indevido entre empresas.

## Backlog conhecido (não implementado à época do registro original)
- UI para importação de JSON de permissões com validação.
- Página dedicada para gerenciar templates (CRUD) via frontend.

## Referências
- `empresas/models.py` (`Role`), `usuarios/models.py` (`Usuario.roles`), `empresas/views.py`
- Comando `seed_roles`
