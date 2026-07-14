# Documentacao Oficial do Agrisdata

## Objetivo
Este diretorio centraliza toda a documentacao funcional, tecnica e operacional do sistema.

## Principios adotados (tecnicas atuais)
- Docs as Code: documentacao versionada no repositorio e revisada por PR.
- Diataxis: separar explicacao, how-to, referencia e tutorial por contexto.
- Rastreabilidade fim a fim: regra -> calculo -> codigo -> teste -> operacao.
- Decision tables: condicionais criticas descritas em tabelas de decisao.
- Ownership: cada documento tem dono e status.

## Como navegar
- 0_INICIO_RAPIDO: setup, onboarding e atalhos
- 1_ARQUITETURA: visao de alto nivel, seguranca e multitenancy
- 2_MODULOS: especificacao por app/modulo
- 3_FLUXOS_PROCESSOS: fluxos negocio-a-negocio
- 4_TECNICO: calculos, condicionais, API e schema
- 5_DESENVOLVIMENTO: padroes de codigo, testes e debug
- 6_OPERACIONAL: guias de uso por area
- 7_RUNBOOKS: resposta a incidentes e operacao critica
- 8_DADOS: seed, migracao e qualidade de dados
- 9_DEPLOYMENT: deploy e monitoramento
- 10_FASES_ROADMAP: historico e roadmap das fases
- TEMPLATES: modelos oficiais de documentacao
- NAVIGATION.md: mapa rapido por perfil e necessidade

## Metadados obrigatorios em cada arquivo
Todos os novos MDs devem iniciar com:

```md
Owner: <time ou pessoa>
Status: Draft | In Review | Approved | Deprecated
Last Updated: YYYY-MM-DD
Scope: <modulo, fluxo ou tema>
```

## Regra de PR
Se houver mudanca de regra de negocio, calculo, condicional ou fluxo, o PR deve incluir update da documentacao correspondente.

## Backlog inicial
- Consolidar documentos legados em cada trilha.
- Produzir matriz de calculos centralizados.
- Produzir tabela de condicionais criticas por modulo.
- Vincular regra documentada aos testes existentes.
