# Guia de Novo Modulo

Owner: Engenharia
Status: Draft
Last Updated: 2026-07-01
Scope: Expansao da plataforma

## Objetivo
Padronizar criacao de novos modulos com seguranca multiempresa e qualidade.

## Checklist de implementacao
1. Criar app Django e registrar em configuracao.
2. Criar models com campo empresa quando aplicavel.
3. Criar forms filtrando queryset por empresa.
4. Criar views com validacao de permissao e escopo.
5. Criar urls com namespace e incluir em core/urls.py.
6. Criar templates no padrao do projeto.
7. Criar testes unitarios e de integracao.
8. Criar documentacao do modulo em docs/2_MODULOS.

## Checklist de seguranca
- Filtro por empresa em todos os acessos de dados
- Proibicao de acesso cruzado entre tenants
- Permissoes por perfil claramente definidas

## Checklist de documentacao
- Modulo, fluxos, calculos e condicionais documentados
- Endpoints registrados na API reference
