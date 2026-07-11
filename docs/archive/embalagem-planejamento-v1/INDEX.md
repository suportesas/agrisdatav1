Owner: Documentacao (Legado)
Status: Deprecated
Last Updated: 2026-07-10
Scope: Planejamento pré-implementação do módulo embalagem (repo anterior agrisdatav1)

> ⚠️ Este conjunto de documentos foi escrito ANTES da implementação real do módulo, como planejamento para o repositório anterior (agrisdatav1). O módulo `embalagem/` já existe de fato neste repositório (agrisdatav2). Para a documentação atual, consulte `docs/2_MODULOS/MODULO_EMBALAGEM.md`.

# Índice: planejamento do "Sistema Packing Django" (pré-implementação, agrisdatav1)

Estes 12 arquivos (movidos aqui como estavam, sem edição de conteúdo, da antiga pasta `Doc_mod_Embalagem/`) documentam o planejamento de um "Sistema Packing Django" — gestão de produção de casa de embalagem de frutas/hortaliças — pensado originalmente como migração de um sistema PHP/MySQL legado, e depois adaptado como plano de integração ao ERP `agrisdatav1` (repositório anterior a este). Nenhum destes arquivos reflete o módulo `embalagem/` como ele existe hoje neste repositório (`agrisdatav2`).

- **`0_COMECE_AQUI.md`** — Guia de orientação inicial: qual documento ler primeiro conforme o perfil do leitor (gerente/stakeholder, desenvolvedor, revisor de integração).
- **`1_RESUMO_EXECUTIVO.md`** — Resumo de uma página do projeto: objetivo (migrar PHP/MySQL para Django/PostgreSQL), escopo (10 funcionalidades, 5 modelos, 20+ views), estimativa de ~24 dias com 1 desenvolvedor.
- **`3_PROMPT_COMPLETO.md`** — Prompt/especificação detalhada para desenvolvimento completo do sistema Packing em Django (stack, contexto do projeto, objetivos de segurança/auditoria/performance).
- **`4_CODIGO_PRONTO.md`** — Trechos de código prontos para copiar/colar (settings.py, models.py, views.py, forms.py, urls.py, signals.py, decorators/mixins, management command de criação de admin).
- **`5_QUICK_REFERENCE.md`** — Referência rápida de uma página: stack, estrutura de pastas do projeto Django proposto, modelos principais e funcionalidades.
- **`6_CHECKLIST_IMPLEMENTACAO.md`** — Checklist passo a passo por fases (preparação de ambiente, fase de integração opcional com ERP existente, desenvolvimento).
- **`7_FLUXOS_SISTEMA.md`** — Diagramas (Mermaid) e descrição dos fluxos do sistema: autenticação, dashboard, registro de produção, CRUD de culturas/embaladores, relatórios, exportação Excel, cache.
- **`GUIA_INTEGRACAO_RAPIDA.md`** — Guia rápido de decisão para quem já tem o ERP `agrisdatav1` funcionando: integrar o módulo Packing como standalone ou expandir o módulo `/embalagem/` já existente naquele repositório (opção recomendada).
- **`INTEGRACAO_ERP_AGRISDATAV1.md`** — Análise específica do repositório `agrisdatav1` (stack, multi-tenant, módulo `/embalagem/` já existente lá) e estratégia recomendada de expandir esse módulo em vez de criar um sistema separado.
- **`MAPA_VISUAL_RAPIDO.md`** — Mapa de navegação visual ligando cada etapa do fluxo do sistema aos arquivos de documentação e código correspondentes (ex.: Login → `7_FLUXOS_SISTEMA.md` + `4_CODIGO_PRONTO.md` + `6_CHECKLIST_IMPLEMENTACAO.md`).
- **`README.md`** — Índice geral original da pasta de documentação (estrutura dos 6+ arquivos, ~5.000 linhas ao todo).
- **`SUPABASE_SETUP.md`** — Guia de configuração do Supabase como banco PostgreSQL gerenciado na nuvem para o projeto Packing (criação de conta, setup, integração com Django).
