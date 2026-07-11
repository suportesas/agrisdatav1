# 2_MODULOS

Owner: Lideres de Modulo
Status: Draft
Last Updated: 2026-07-01
Scope: Funcionalidades por modulo

## Objetivo
Documentar cada modulo com foco funcional e tecnico.

## Conteudo alvo por modulo
- Objetivo do modulo
- Entidades principais
- Regras de negocio
- Fluxos e estados
- Permissoes e integracoes
- Casos de teste associados

## Estrategia de cobertura
Todos os modulos com a mesma prioridade.

## Status atual
- 27 apps Django reais mapeados (ver `MAPA_COBERTURA_MODULOS.md`, lista extraída de `*/apps.py`).
- 5 documentos de módulo que não existiam foram criados nesta rodada: `drawback`, `estufas`, `etiquetas_avulsas`, `patrimonio`, `portal`.
- 6 módulos com conteúdo verificado contra código (`Approved`): compras, estoque (parcial), financeiro, cadastros, produtos.
- Demais módulos permanecem como esqueleto (`Draft — a expandir`) — nome, prefixo de URL e entidades principais reais, mas sem detalhamento de regras/fluxos ainda.
- Detalhamento incremental continua por modulo com aprofundamento em regras, calculos e testes.
