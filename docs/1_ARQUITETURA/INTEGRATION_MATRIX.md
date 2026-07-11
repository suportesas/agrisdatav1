# Matriz de Integracao entre Modulos

Owner: Arquitetura
Status: Draft
Last Updated: 2026-07-01
Scope: Integracoes internas

## Objetivo
Mapear dependencias e eventos entre modulos para reduzir impacto de mudancas.

| Origem | Destino | Evento/Regra | Resultado |
|---|---|---|---|
| compras | estoque | recebimento de mercadoria | cria/atualiza lote |
| compras | financeiro | recebimento finalizado com NF | cria conta a pagar e parcelas |
| financeiro | compras | ajuste por divergencia | recalculo de valores |
| faturamento | financeiro | emissao/faturamento conforme regra | origem de titulo financeiro |
| estoque | faturamento | disponibilidade/rastreio por lote | suporte a documento fiscal |
| usuarios/empresas | todos | permissao e escopo por empresa | controle de acesso |

## Risco principal
Quebra de fluxo intermodulo por alteracao isolada sem teste integrado.

## Mitigacao
Manter testes de integracao por trilha critica de negocio.
