# Roles e Permissoes

Owner: Operacao
Status: Draft
Last Updated: 2026-07-01
Scope: Controle de acesso por empresa

## Objetivo
Consolidar o modelo de funcoes e permissoes por empresa para uso operacional.

## Fonte consolidada
- docs/ROLES.md

## O que existe
- Entidade Role vinculada a Empresa e auth.Group.
- Usuario pode possuir multiplas roles.
- Seed de funcoes padrao por empresa.
- Tela administrativa para listar, criar e editar funcoes.
- Endpoints JSON para ler/salvar permissoes e aplicar templates.

## Funcoes padrao
- Proprietario
- Almoxarife
- Operacional do Campo
- Financeiro
- Gerente
- Vendedor

## Operacao basica
1. Executar migracoes.
2. Executar seed de roles.
3. Acessar tela de funcoes por empresa.
4. Editar permissoes por modulo.
5. Salvar e validar resultado com usuario de teste.

## Regras de governanca
- Sempre validar isolamento por empresa.
- Evitar permissao ampla sem justificativa.
- Manter trilha de auditoria para alteracao massiva.

## Integracao com testes
- E2E deve cobrir criar role, alterar permissao e validar acesso.
- Testes de seguranca devem cobrir acesso indevido entre empresas.

## Referencia legada
- docs/ROLES.md
