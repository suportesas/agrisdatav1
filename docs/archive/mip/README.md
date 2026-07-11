Owner: Documentacao (Legado)
Status: Deprecated
Last Updated: 2026-07-10
Scope: Monitoramento MIP (Manejo Integrado de Pragas) - backend, templates e melhorias

Este é um registro histórico consolidado, mesclado a partir de 4 arquivos originais: `IMPLEMENTACAO_MONITORAMENTO_MIP_COMPLETA.md`, `TESTE_MONITORAMENTO_MIP_RESULTADO.md`, `MELHORIAS_IMPLEMENTADAS_MIP.md` e `IMPLEMENTACAO_TEMPLATES_MIP_COMPLETA.md` (preservados em `fontes/`). Juntos, documentam as etapas sucessivas de construção do sistema de Monitoramento MIP em `cadastros/`: backend → templates → testes → melhorias de UX.

## ATENÇÃO — TODO não resolvido encontrado no código-fonte documentado

`IMPLEMENTACAO_MONITORAMENTO_MIP_COMPLETA.md` documenta o método `PragaNoMonitoramento.save()` com o seguinte trecho, citado literalmente na fonte:

```python
# Auto-cálculo 2: NED Atingido
ned_valor = 5.0  # TODO: integrar com RecomendacaoDefensivo
ned_atingido = incidencia_percentual >= ned_valor
```

Ou seja, o Nível Econômico de Dano (NED) usado para decidir se um defensivo é recomendado está **hardcoded em 5.0% para todas as pragas/culturas**, em vez de vir de uma tabela `RecomendacaoDefensivo` (que teria o NED correto por praga+cultura+estágio). Isso é confirmado no teste funcional em `TESTE_MONITORAMENTO_MIP_RESULTADO.md`, cujo resultado mostra `NED: 5.0%` e `Estágio Crítico: LARVA` independentemente da praga/cultura testada (`Podridão-negrados-frutos`). A própria fonte original lista essa integração como **"Prioridade: ALTA"** na seção "Integrações Futuras", junto com a integração ao Receituário Agronômico. Nenhum dos outros 3 arquivos do cluster (templates, testes, melhorias) indica que esse TODO foi resolvido — as melhorias posteriores (fevereiro 2026) cobriram apenas UI (cascading selects, menu, PDF, mapas), não a lógica de NED dinâmico.

**Antes de confiar nas recomendações de defensivo geradas pelo MIP, confirmar em `cadastros/models.py` (método `save()` de `PragaNoMonitoramento`) se esse hardcode de 5.0% ainda está presente ou se foi substituído por integração real com `RecomendacaoDefensivo`.**

## O que foi implementado

### Backend (modelos, forms, views, admin) — primeira fase

`IMPLEMENTACAO_MONITORAMENTO_MIP_COMPLETA.md` descreve a criação de 4 modelos Django em `cadastros/models.py` (~554 linhas):

- **EstagioDesenvolvimento** (18 campos) — catálogo do ciclo de vida de cada praga (ovo → larva → pupa → adulto), com duração min/max em dias e marcação de fase crítica.
- **MonitoramentoMIP** (20 campos) — registro de uma visita de monitoramento a um talhão, com auto-numeração `MIP-YYYY-NNNNN`, dados climáticos (temperatura, umidade, vento, chuva), status `RASCUNHO → COMPLETO → ANALISADO → CANCELADO`.
- **PragaNoMonitoramento** (16 campos) — M2M customizada entre monitoramento e praga, com auto-cálculo de `incidencia_percentual = (pontos_com_praga / total_pontos) × 100`, comparação com NED (ver aviso acima) e `resultado_acao` (`SEM_ACAO`/`MONITORAR`/`RECOMENDA_DEFENSIVO`).
- **PontoMonitoramento** (12 campos) — cada um dos 20 pontos de amostragem padrão, com presença/ausência, quantidade, estágio, severidade (1-5), GPS opcional e foto opcional.

Também: `cadastros/forms.py` (+500 linhas, 4 forms), `cadastros/views_monitoramento_mip.py` (novo arquivo, 470 linhas, 11 views + 3 endpoints AJAX), `cadastros/admin.py` (+280 linhas), `cadastros/urls.py` (+20 linhas, 11 rotas), migration `0045` aplicada (4 tabelas, 11 índices, 4 constraints). Multi-tenant em todos os níveis (model/view/admin/form), `@login_required` em todas as views.

Ao final dessa fase, o backend estava descrito como "100% completo", mas **as 11 templates HTML ainda não existiam** — views prontas, UI pendente.

### Templates — segunda fase

`IMPLEMENTACAO_TEMPLATES_MIP_COMPLETA.md` (datado apenas "2025", sem dia/mês) documenta a criação de 8 templates HTML (1.890 linhas) em `cadastros/templates/cadastros/monitoramento_mip/`: `monitoramento_mip_list.html`, `monitoramento_mip_form.html`, `monitoramento_mip_detail.html`, `praga_form.html`, `praga_detail.html`, `ponto_form.html`, `estagio_list.html`, `estagio_form.html`. Padrão Bootstrap 5 consistente com o resto do projeto (cards `.shadow-sm.border-0.rounded-4`, badges por status, breadcrumbs).

Ao final dessa fase, ficaram pendentes explicitamente: cascading selects via AJAX (praga→estágio, cultura→praga), integração ao menu de navegação, e melhorias visuais (mapa GPS, gráficos, export PDF) — tudo listado como "Próximas Etapas".

### Teste funcional de validação

`TESTE_MONITORAMENTO_MIP_RESULTADO.md`, datado **10/02/2026**, registra a execução de `test_monitoramento_mip.py`, validando o fluxo completo ponta a ponta: criação de monitoramento (`MIP-2026-00001`), 5 estágios de desenvolvimento criados, praga adicionada com incidência calculada em 40.0% (8 de 20 pontos), NED comparado (hardcoded 5.0%, ver aviso acima), 20 pontos de amostragem criados, resultado `RECOMENDA_DEFENSIVO`. Teste passou integralmente segundo a fonte.

### Melhorias de UX — terceira fase

`MELHORIAS_IMPLEMENTADAS_MIP.md`, datado **fevereiro de 2026**, implementa as 4 pendências deixadas pela fase de templates:

1. **AJAX cascading selects** — seleção de praga carrega dinamicamente os estágios disponíveis (`praga_form.html` + endpoint `ajax_get_estagios_praga`).
2. **Integração ao menu sidebar** — itens "Monitoramento MIP" e "Estágios de Desenvolvimento" adicionados à seção "Agro" de `templates/sidebar.html`.
3. **Exportação em PDF** — nova view `monitoramento_mip_pdf()` usando ReportLab (já usado no projeto para estoque), gera `MIP-NUMERO-DDMMYYYY.pdf` com dados básicos, clima, tabela de pragas e observações.
4. **Mapa GPS interativo (Leaflet.js + OpenStreetMap)** — em `praga_detail.html`, mostra os 20 pontos de amostragem no mapa com marcadores coloridos (vermelho = praga presente, verde = ausente), popups informativos, sem necessidade de API key.

## Quando foi feito

Cronologia aproximada, na ordem em que os documentos-fonte se referenciam:
1. Backend (modelos/views/forms/admin) — data não explícita no arquivo, mas anterior às demais fases.
2. Templates — "2025" (sem data exata).
3. Melhorias de UX (AJAX, menu, PDF, mapa) — fevereiro de 2026.
4. Teste de validação end-to-end — **10/02/2026**.

## Status final

Segundo as fontes, o sistema MIP está descrito como "100% completo com todas as features desejadas": backend, templates, cascading selects, menu, export PDF e mapa GPS todos implementados e testados. **Isso não inclui a resolução do TODO de NED dinâmico** (ver aviso no topo) — o texto "100% completo" nas fontes refere-se à camada de UI/UX, não à integração de negócio com `RecomendacaoDefensivo`.

## Pendências / avisos ainda relevantes

- **TODO crítico**: `ned_valor = 5.0` hardcoded em `PragaNoMonitoramento.save()` — não integrado com `RecomendacaoDefensivo` (ver seção de destaque acima). Classificado como prioridade ALTA na fonte original, sem confirmação de resolução em nenhum dos 4 documentos.
- Integração com Receituário Agronômico (gerar prescrições automaticamente a partir de monitoramentos com `ned_atingido=True`) — listada como "Prioridade: ALTA", não implementada.
- Integração com Caderno de Campo / rastreabilidade GLOBALG.A.P — listada como "Prioridade: MÉDIA", não implementada.
- Relatórios/dashboards (incidência por praga por período, evolução de estágios, eficácia de defensivos) — não implementados.
- Testes automatizados formais (unitários, integração, segurança) além do script manual `test_monitoramento_mip.py` — não confirmados.
- Ideias futuras não implementadas mencionadas em `MELHORIAS_IMPLEMENTADAS_MIP.md`: gráficos de tendência (Chart.js), heatmap de severidade, app mobile offline, machine learning para previsão de picos, alertas por SMS/push, API para terceiros.

Detalhes completos de cada template (estrutura de seções, JS de cada tela) e do script de teste permanecem nos originais em `fontes/`, especialmente `IMPLEMENTACAO_TEMPLATES_MIP_COMPLETA.md` para a listagem completa dos 8 templates.
