Owner: Documentacao (Legado)
Status: Deprecated
Last Updated: 2026-07-10
Scope: modos de operacao (Simples/Formal/Hibrido) em compras e estoque

Este é um registro histórico consolidado, mesclado a partir de 6 arquivos originais: `DIAGRAMA_MODOS_OPERACAO.md`, `GUIA_USUARIO_MODOS_OPERACAO.md`, `PLANO_IMPLEMENTACAO_MODOS_COMPRA.md`, `RESUMO_FINAL_MODOS_OPERACAO.md`, `SISTEMA_DUAL_RESUMO.md` e `SISTEMA_MODOS_OPERACAO.md` (preservados em `fontes/`). Os arquivos misturam um plano de projeto (com cronograma de 5 fases) e relatórios de conclusão — ver seção "Estado real vs plano" abaixo para a discrepância entre eles.

## O que foi implementado

Um sistema de "modos de operação" configurável por empresa para dois módulos, `compras/` e `estoque/`, com 3 opções cada:

- **SIMPLES** — fluxo rápido (2-3 cliques, 30-60s), sem cotação/aprovação formal.
- **FORMAL** — o fluxo completo pré-existente (Solicitação → Cotação → Pedido → Recebimento → Estoque; Movimentação com Lote/FIFO/rastreabilidade).
- **HIBRIDO** — o usuário escolhe em cada operação, via uma tela intermediária com dois cards.

### Configuração

Modelo novo `core/models_config.py::ConfiguracaoSistema`, por empresa, com campos `modo_compras` e `modo_estoque` (cada um `SIMPLES`/`FORMAL`/`HIBRIDO`) mais ~20 flags detalhadas (`exigir_aprovacao_solicitacao`, `limite_compra_sem_aprovacao`, `controle_lote_obrigatorio`, `permitir_estoque_negativo`, `exigir_numero_serie`, etc). Tela de configuração em `/configuracoes/sistema/` (view `usuarios.views.configuracao_sistema()`, template `core/templates/configuracao_sistema.html`).

### Compras — modo simples

- `compras/views_simples.py` (248 linhas): `compra_rapida()`, `recebimento_rapido()`, `escolher_modo_compra()`.
- URLs: `/compras/compra-rapida/`, `/compras/recebimento-rapido/`, `/compras/escolher-modo/`.
- Templates: `compras/templates/compras/compra_rapida.html`, `recebimento_rapido.html`, `escolher_modo.html`.
- Ajuste de modelo planejado (ver "Estado real vs plano"): tornar `PedidoCompra.cotacao` e `ItemPedidoCompra.proposta_fornecedor` `null=True, blank=True` para permitir pedido sem cotação prévia.

### Estoque — modo simples

- `estoque/views_simples.py` (337 linhas): `entrada_rapida()`, `saida_rapida()`, `ajuste_rapido()`, `escolher_modo_estoque()`.
- URLs: `/estoque/entrada-rapida/`, `/estoque/saida-rapida/`, `/estoque/ajuste-rapido/`, `/estoque/escolher-modo-estoque/`.
- Templates: `estoque/templates/estoque/entrada_rapida.html`, `saida_rapida.html`, `escolher_modo.html`.
- Entrada rápida gera lote automaticamente; saída rápida usa FIFO automático.

### Conceito-chave (citado nas fontes)

> "Simples por padrão, completo quando necessário" — não substitui o fluxo formal, oferece as duas opções e deixa a empresa/usuário escolher por módulo (compras vs. estoque) e, no modo híbrido, por operação individual.

## Quando foi feito

`SISTEMA_MODOS_OPERACAO.md` e `RESUMO_FINAL_MODOS_OPERACAO.md` registram data **04/02/2026**, Django 5.2.7, com o texto "IMPLEMENTADO E FUNCIONANDO" / "PRONTO PARA PRODUÇÃO".

## Estado real vs plano — leia antes de confiar no "pronto para produção"

Os 6 arquivos-fonte não são consistentes entre si sobre o que estava de fato concluído:

- `PLANO_IMPLEMENTACAO_MODOS_COMPRA.md` é um cronograma de **3 semanas** dividido em 5 fases. Na "Semana 1", o checklist mostra `ConfiguracaoSistema` com campos criados **[x]**, mas migration, admin e testes ainda **[ ]** não marcados; ajustes de `null=True/blank=True` em `PedidoCompra.cotacao` e `ItemPedidoCompra.proposta_fornecedor` aparecem como planejados, não confirmados como aplicados. As Fases 3 (analytics/KPIs), 4 (app mobile, automações por email/WhatsApp/SMS) e 5 (QR Code, compliance, integração com certificadoras) são descritas inteiramente como trabalho futuro — nada nesses arquivos indica que foram implementadas.
- `SISTEMA_DUAL_RESUMO.md` termina explicitamente com **"Status: Fase 1 (Arquitetura) concluída — Próximo: Migrations e ajustes de modelos — Prazo estimado: 3 semanas para implementação completa"**, ou seja, essa fonte se autodescreve como um marco intermediário, não uma entrega completa.
- Já `SISTEMA_MODOS_OPERACAO.md`, `RESUMO_FINAL_MODOS_OPERACAO.md` e `GUIA_USUARIO_MODOS_OPERACAO.md` declaram o sistema como **implementado, testado (URLs retornando 302/redirect esperado por exigir login) e pronto para produção**, listando os mesmos arquivos de views/templates como já criados.

Leitura mais provável: as views simples, templates de escolha de modo e o modelo `ConfiguracaoSistema` (parte central do que os documentos "finais" descrevem) foram de fato implementados; as fases posteriores do plano original (mobile, automações externas, QR code/compliance) permanecem apenas como plano, não implementação. **Antes de assumir que qualquer funcionalidade deste cluster está ativa em produção hoje, confirmar diretamente no código** (`compras/views_simples.py`, `estoque/views_simples.py`, `core/models_config.py`, migrations correspondentes) — os documentos-fonte se contradizem quanto ao grau de conclusão.

## Status final (conforme documentos "finais")

- `[x]` Views simples de compra e estoque criadas e funcionando.
- `[x]` Templates de escolha de modo (híbrido) para compras e estoque.
- `[x]` `ConfiguracaoSistema` com `modo_compras`/`modo_estoque` e flags detalhadas.
- `[x]` URLs configuradas e validadas (retorno 302 por exigir login, comportamento esperado).
- `[ ]` Integração do menu/navbar com links condicionais por modo — listado como próximo passo opcional em mais de uma fonte.
- `[ ]` Dashboard com shortcuts por modo, relatórios de tempo economizado — não implementado.
- `[ ]` Fases 3-5 do plano original (KPIs, mobile, automações externas, QR code/rastreabilidade, compliance/certificadoras) — não implementado, apenas planejado.

## Pendências / avisos ainda relevantes

- Confirmar se as migrations de `ConfiguracaoSistema` e os ajustes `null=True`/`blank=True` em `PedidoCompra`/`ItemPedidoCompra` foram de fato aplicados (o plano os lista como pendentes na Semana 1, mas os relatórios finais assumem que sim).
- Integração de menu/navbar com links condicionais por modo, dashboard de shortcuts e relatórios de tempo economizado seguem como "próximos passos opcionais" não confirmados como feitos.
- Nenhuma automação externa (email ao fornecedor, WhatsApp, SMS, QR code, app mobile) foi implementada — tudo isso é plano de fases futuras (3, 4 e 5) que não há evidência de execução.

Diagramas de fluxo completos e exemplos de tela ASCII (redundantes entre os 6 arquivos) permanecem nos originais em `fontes/`, especialmente `DIAGRAMA_MODOS_OPERACAO.md` para o fluxograma visual e `PLANO_IMPLEMENTACAO_MODOS_COMPRA.md` para o cronograma completo de 5 fases.
