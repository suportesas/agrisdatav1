Owner: Time compras
Status: Approved
Last Updated: 2026-07-10
Scope: compras (`/compras/`)

# Módulo Compras

## Visão geral
Gestão de solicitações de compra (SC) com cotação seletiva multi-fornecedor: o comprador escolhe quais itens de uma SC cotar em cada rodada, permite múltiplas rodadas de cotação parciais até cobrir 100% dos itens, e converte a cotação vencedora em pedido/recebimento (ver `docs/3_FLUXOS_PROCESSOS/FLUXO_COMPRA_FINANCEIRO.md` para o fluxo até a conta a pagar).

## Entidades principais
| Entidade | Papel |
|---|---|
| `SolicitacaoCompra` | Documento raiz (SC-######); status com % cotado calculado a partir dos itens |
| `ItemSolicitacaoCompra` | Item da SC; `selecionado_para_cotar` (bool) habilita a cotação seletiva; mantém FK de rastreabilidade até a cotação vencedora |
| `Cotacao` | Rodada de cotação (COT-######) vinculada a uma SC; pode conter só parte dos itens |
| `ItemCotacao` | Item cotado, com link de volta ao `ItemSolicitacaoCompra` original |
| `FornecedorCotacao` | Proposta de um fornecedor para um item cotado (preço, prazo, condição de pagamento); `selecionado=True` marca o vencedor |
| `PedidoCompra`, `ItemPedidoCompra` | Pedido gerado a partir da cotação concluída |
| `RecebimentoCompra`, `ItemRecebimento` | Recebimento físico + registro da NF; ver `docs/4_TECNICO/ESTRATEGIA_ESTOQUE.md` para o efeito no estoque |

## Fluxo — Solicitação de Compra
```
RASCUNHO → PENDENTE → APROVADA → PARCIALMENTE_COTADA → TOTALMENTE_COTADA → EM_COMPRA → CONCLUIDA
```
Fluxo emergencial (`emergencial=True` no formulário): pula `PENDENTE` e vai direto para `APROVADA` ao salvar, com o próprio solicitante como aprovador — exige preenchimento de `justificativa_emergencial`. Pensado para quebra de equipamento, falta de insumo crítico ou situações com perda financeira que não podem esperar aprovação formal (24-48h). **Atualmente qualquer usuário pode marcar emergencial** — permissões granulares por limite de valor (`compras.add_solicitacao_emergencial_basico/medio/total`, ver `docs/5_DESENVOLVIMENTO/BACKLOG_PERMISSOES_COMPRAS.md`) estão desenhadas mas não implementadas; tratar como gap de segurança conhecido até serem aplicadas.

Status de item da SC: `PENDENTE → SELECIONADO → EM_COTACAO → COTADO → APROVADO`.

## Fluxo — Cotação seletiva
1. SC aprovada mostra checkbox por item `PENDENTE`.
2. Comprador seleciona 1+ itens → "Cotar Selecionados" → cria `Cotacao` só com esses itens.
3. Itens não selecionados continuam `PENDENTE` para uma rodada futura.
4. % cotado = itens com fornecedor vencedor selecionado / total de itens da SC → 0% mantém `PENDENTE`/`APROVADA`, 1-99% vira `PARCIALMENTE_COTADA`, 100% vira `TOTALMENTE_COTADA`.
5. Selecionar um vencedor em `FornecedorCotacao` desmarca os demais do mesmo item, muda o item para `COTADO` e recalcula o % da SC.

Fluxo da cotação em si: `RASCUNHO → EM_ANDAMENTO → CONCLUIDA`.

## Rotas principais (`/compras/`)
| Rota | Uso |
|---|---|
| `solicitacoes/`, `solicitacoes/nova/`, `solicitacoes/<id>/` | CRUD de SC |
| `solicitacoes/<id>/aprovar/`, `solicitacoes/<id>/cancelar/` | Transições de status |
| `solicitacoes/<id>/selecionar-itens/` (POST) | Processa a seleção para cotação |
| `cotacoes/`, `cotacoes/nova/<solicitacao_id>/`, `cotacoes/<id>/` | CRUD de cotação e comparação de propostas |
| `cotacoes/<cot_id>/item/<item_id>/proposta/` | Adicionar proposta de fornecedor |
| `propostas/<id>/selecionar/` | Selecionar fornecedor vencedor |
| `compra-rapida/` | Modo simplificado — cria `PedidoCompra` direto, sem cotação/proposta (ver `docs/3_FLUXOS_PROCESSOS/FLUXO_COMPRA_FINANCEIRO.md`) |
| `pedido/<id>/receber/` | Registrar recebimento (parcial ou total) |
| `recebimento/<id>/fatura/` | Registrar NF do recebimento — dispara criação automática de `ContaPagar` (ver módulo financeiro) |

## Integrações
- **Estoque**: recebimento gera `Lote` e atualiza `Produto.estoque_atual` (`docs/4_TECNICO/ESTRATEGIA_ESTOQUE.md`).
- **Financeiro**: NF registrada no recebimento cria `ContaPagar` + `ParcelaContaPagar` automaticamente (`docs/2_MODULOS/MODULO_FINANCEIRO.md`, `docs/3_FLUXOS_PROCESSOS/FLUXO_COMPRA_FINANCEIRO.md`).

## Permissões e isolamento
- Filtro por `empresa` obrigatório em toda consulta de SC/cotação/pedido.
- Compra emergencial: ver gap de permissões acima — hoje não há bloqueio real por nível hierárquico.
- Backlog de permissões planejadas: `compras.aprovar_solicitacaocompra`, `compras.selecionar_fornecedor`, `compras.concluir_cotacao` (parte já existe como `Meta.permissions`, confirmar em `compras/models.py` antes de assumir que está ativo).

## Roadmap conhecido (não implementado)
- Avaliação de fornecedores pós-recebimento (qualidade, prazo, conformidade)
- Notificação automática ao superior em compra emergencial
- Relatório de uso de compras emergenciais / alerta de uso excessivo (>20%)

## Referências
- `compras/models.py`, `compras/urls.py`, `compras/views.py`, `compras/views_simples.py`
- Guia de uso de compras emergenciais: `docs/6_OPERACIONAL/GUIA_COMPRAS_EMERGENCIAIS.md`
- Backlog de permissões granulares (não implementado): `docs/5_DESENVOLVIMENTO/BACKLOG_PERMISSOES_COMPRAS.md`
