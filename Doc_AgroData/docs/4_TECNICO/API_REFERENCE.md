# API Reference Funcional

Owner: Engenharia
Status: Draft
Last Updated: 2026-07-01
Scope: Endpoints web e API

## Objetivo
Centralizar referencia de endpoints principais do sistema para navegacao tecnica e testes.

## Prefixos centrais
Fonte: core/urls.py

| Prefixo | Modulo |
|---|---|
| /dashboard/ | dashboard |
| /dashboard-executivo/ | metricas |
| /empresas/ | empresas |
| /usuarios/ | usuarios |
| /cadastros/ | cadastros |
| /produtos/ | produtos |
| /estoque/ | estoque |
| /compras/ | compras |
| /financeiro/ | financeiro |
| /plano-contas/ | plano_contas |
| /bancario/ | bancario |
| /adiantamentos/ | adiantamentos |
| /exportacao/ | exportacao |
| /faturamento/ | faturamento |
| /vendas/ | vendas |
| /embalagem/ | embalagem |
| /frota/ | frota |
| /rh/ | rh |
| /campo/ | operacoes_campo |
| /api/ | drf auth |

## Endpoints globais relevantes
| Metodo | Rota | Descricao |
|---|---|---|
| GET | /login/ | Tela de autenticacao |
| GET | /logout/ | Encerramento de sessao |
| GET | /password_reset/ | Recuperacao de senha |
| GET | /compras/recebimentos/entrada-direta/ | Entrada direta de NF |
| GET | /configuracoes/ | Hub de configuracoes |

## Contrato minimo por endpoint
Cada endpoint de modulo deve documentar:
- Metodo
- Rota
- Perfil minimo
- Entrada esperada
- Regras de negocio aplicadas
- Respostas de sucesso e erro

## Proxima expansao
- Gerar arquivo por modulo em 4_TECNICO/API_<MODULO>.md
- Completar exemplos de request/response com cenarios reais
