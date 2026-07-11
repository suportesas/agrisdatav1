Owner: Documentacao (Legado)
Status: Deprecated
Last Updated: 2026-07-10
Scope: RF-055 (alertas de estoque min/max) e RF-056 (inventario ciclico)

Este é um registro histórico consolidado, mesclado a partir de 11 arquivos originais: `00_COMECE_AQUI_RF-055.md`, `INDICE_RF-055.md`, `QUICK_START_RF-055.md`, `ARQUITETURA_RF-055.md`, `RESUMO_RF-055.md`, `VERIFICACAO_FINAL_RF-055.md`, `STATUS_RF-055_20250203.md`, `RF-055_GUIA_VISUAL.md`, `RF-055_EXTENSAO_EMAIL_AUTOMATICO.md`, `RF-055_IMPLEMENTACAO.md` e `RF-056_IMPLEMENTACAO.md` (preservados em `fontes/`). Os arquivos originais eram, em sua maioria, o mesmo conteúdo reapresentado sob ângulos diferentes (quick-start, índice, arquitetura, checklist, status) — este documento sintetiza o que há de factual.

## O que é o RF-055

RF-055 é a funcionalidade de **Controle de Estoque Mínimo/Máximo com Alertas** do módulo `estoque/`. A "evolução" documentada nestes arquivos adicionou três melhorias sobre uma versão anterior que já existia (colunas mín/máx sem alertas de excesso nem badge no menu):

1. **Estoque máximo com alerta de excesso** — nova categoria de alerta `'excesso'` quando `saldo > produto.estoque_maximo` (antes só existiam alertas de crítico/baixo).
2. **Badge/contador no menu lateral** — novo context processor global `core/context_processors.alertas_estoque` registrado em `TEMPLATES.OPTIONS.context_processors` (settings.py), que calcula os totais de alerta em toda requisição e alimenta um badge em `templates/sidebar.html`.
3. **Estrutura para alertas automáticos (email/in-app)** — não implementado, apenas documentado/planejado (ver seção "Pendências" abaixo).

### Os 4 níveis de alerta

| Alerta | Condição | Cor | Classe CSS |
|---|---|---|---|
| Crítico | `saldo <= 0` | Vermelho | `table-danger` |
| Baixo | `saldo < estoque_minimo` | Laranja | `table-warning` |
| Excesso | `estoque_maximo > 0 and saldo > estoque_maximo` | Azul | `table-info` |
| Normal | dentro dos limites | Verde | `table-success` |

`saldo` é calculado como `Lotes (status DISPONIVEL/BLOQUEADO) + (Entradas diretas executadas - Saídas diretas executadas)`.

### Arquivos de código tocados (segundo a documentação original)

- `estoque/views.py` (função `estoque_produtos_list`, linhas ~550-620): lógica de categorização e contadores (`alertas_criticos`, `alertas_baixos`, `alertas_excesso`, `total_alertas`).
- `estoque/templates/estoque/estoque_produtos_list.html`: redesenho completo — badges de resumo no topo, linhas coloridas por tipo, coluna "Situação", colunas Est. Mínimo/Est. Máximo visíveis.
- `core/context_processors.py` (novo arquivo): função `alertas_estoque(request)`, filtra por `request.user.empresa`, retorna zeros com segurança se usuário não autenticado/sem empresa/erro (nunca quebra a página).
- `core/settings.py`: registro do context processor.
- `templates/sidebar.html`: badge vermelho no item de menu "Estoque" e no submenu "Estoque de Produtos".

Nenhuma migration foi necessária — os campos `estoque_minimo`/`estoque_maximo` já existiam no modelo `Produto`, e os alertas são calculados dinamicamente (não persistidos).

## Quando foi feito

Segundo os arquivos-fonte, a implementação principal do RF-055 (as 3 melhorias acima) ocorreu em **2025-02-03**, em uma sessão de aproximadamente 2 horas (timeline registrada em `STATUS_RF-055_20250203.md`: início 08:00, backend 08:30, template 08:45, context processor 09:00, menu 09:15, documentação 09:30-09:45, conclusão 10:00).

`ARQUITETURA_RF-055.md` também registra uma mudança posterior e não relacionada à evolução original, datada de **2026-04-20**: unificação da assinatura de Liberação Interna e Assinatura do Produtor em um único campo por `Requisicao` (em vez de assinatura por produto). Essa nota parece ter sido anexada ao arquivo depois, fora do escopo original do RF-055 de estoque — registrada aqui apenas para não se perder a informação.

Um follow-up, **RF-056 — Inventário Cíclico com Amostragem ABC**, foi implementado em **2026-02-03** (conforme `RF-056_IMPLEMENTACAO.md`), no mesmo módulo `estoque/`. Não é uma evolução direta do RF-055, mas está documentado no mesmo cluster de arquivos porque referenciado nas mesmas sessões de trabalho.

### RF-056 — Inventário Cíclico (resumo)

Sistema completo de inventário cíclico com amostragem ABC (curva de Pareto — Classe A ~20% dos itens/80% do valor, B ~30%/15%, C ~50%/5%):

- Modelos novos: `InventarioCiclicoSchedule`, `InventarioCiclico`, `InventarioCiclicoItem` (em `estoque/models.py`).
- 7 views novas (`estoque/views.py`) cobrindo listagem, criação com amostragem automática, detalhe, registro de contagem (com cálculo de divergência em tempo real via JS), conciliação (gera movimentações de ajuste automaticamente), finalização e relatório de acurácia com exportação Excel.
- Fluxo: Criação → Contagem → Conciliação (cria ajustes de estoque automaticamente) → Finalização → Relatório.
- Métricas: Acurácia = `(items_corretos / total_items) × 100`; Valor Divergência = `divergência × valor_unitário`.
- Multi-tenant, `@login_required` em todas as views, migration própria em `estoque/migrations/0013_inventariociclico_...`.
- Status registrado como "pronto para produção".
- Melhorias futuras listadas mas não implementadas: agendamento automático, notificações de classe A pendente, gráfico de tendências, análise de operador, importação via QR code/mobile.

## Status final

Ambas as features (RF-055 evolução e RF-056) foram registradas nos arquivos-fonte como **100% completas, testadas e liberadas para produção** ("Score Final: 10/10", "APROVADO PARA PRODUÇÃO: SIM"). Sem erros de servidor relatados, sem impacto de performance relevante (100 produtos ~200ms, 1000 produtos ~2s), compatível com SQLite e PostgreSQL, multi-tenant validado.

## Pendências / avisos ainda relevantes

O terceiro requisito do RF-055 — **alertas automáticos via email e notificações in-app** — **não foi implementado**, apenas documentado como plano pronto para execução futura:

- `RF-055_EXTENSAO_EMAIL_AUTOMATICO.md` contém código pronto (não aplicado ao repo) para: setup Celery + Redis, `estoque/tasks.py` com `enviar_alertas_estoque_diarios()`, template de email HTML, configuração SMTP, modelo de notificação in-app.
- Os checklists nos arquivos originais marcam explicitamente como pendente: `[ ] Email automático`, `[ ] Notificações in-app`, `[ ] Dashboard widget`, `[ ] Cache Redis`.
- Antes de assumir que alertas por email/in-app existem em produção, confirmar no código atual de `estoque/` se essa fase foi de fato implementada depois — os documentos de origem não indicam que isso tenha ocorrido.

Para RF-056, melhorias futuras (não implementadas) incluem agendamento automático de inventários, notificações de pendência por classe ABC, e integração com permissões por operador — ver lista completa acima.

Detalhes adicionais de UI/mockups/diagramas ASCII (removidos aqui por serem redundantes entre os 11 arquivos) estão preservados nos originais em `fontes/`, especialmente `RF-055_GUIA_VISUAL.md` e `ARQUITETURA_RF-055.md` para quem precisar dos fluxogramas completos.
