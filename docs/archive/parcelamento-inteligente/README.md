Owner: Documentacao (Legado)
Status: Deprecated
Last Updated: 2026-07-10
Scope: Sistema inteligente de criação automática de parcelas em Contas a Pagar (financeiro)

# Parcelamento inteligente de Contas a Pagar

Registro histórico consolidado, mesclado a partir de 3 arquivos originais:
- `IMPLEMENTACAO_PARCELAMENTO_INTELIGENTE.md`
- `RESUMO_TECNICO_PARCELAMENTO.md`
- `TESTE_RAPIDO_PARCELAMENTO.md`

## O que foi implementado

Uma tela/fluxo para criação automática de múltiplas parcelas de uma `ContaPagar`, substituindo a entrada manual de `numero_parcela` + `valor_parcela` uma a uma.

### Principais features
- **6 condições de pagamento pré-configuradas**: À Vista (hoje), 30 Dias, 30/60 Dias, 30/60/90 Dias, 15/28 Dias, e Customizado (usuário informa a lista de dias).
- **Modelo novo `FormaPagemento`** (financeiro/models.py) com 7 formas de pagamento típicas: PIX, Transferência Bancária, Boleto (1.5% taxa), Cheque (0.5%), Dinheiro, Cartão de Crédito (2.5%), Crediário (5%) — cada uma com `dias_processamento` e `taxa_administrativa`.
- FK `ParcelaContaPagar.forma_pagamento → FormaPagemento` (SET_NULL, opcional).
- Cálculo automático: valor dividido igualmente entre parcelas, com **ajuste de centavos sempre na última parcela** (`valor = valor_total - valor_acumulado` na última iteração), e data de vencimento = `data_emissao + timedelta(days=dias)`.
- Preview em tempo real no template (JavaScript client-side, sem AJAX) antes de confirmar a criação.

### Arquivos afetados (à época da implementação)
- `financeiro/models.py` — model `FormaPagemento` (novo) + FK em `ParcelaContaPagar`.
- `financeiro/views.py` — view `parcela_criar(request, conta_pk)` reescrita: GET renderiza o formulário com as condições/formas disponíveis; POST processa dentro de `transaction.atomic()`, resolve a lista de dias (padrão ou customizado via `dias_customizado[]`), calcula valores/vencimentos e cria as `ParcelaContaPagar` em lote.
- `financeiro/templates/financeiro/parcela_criar_multiplas.html` (novo) — formulário com radio buttons das condições, dropdown de forma de pagamento, tabela de preview dinâmica e JS (`atualizarParcelas()`, `processarCustomizado()`).
- `financeiro/urls.py` — rota `contas/<int:conta_pk>/parcelas/criar/` → `views.parcela_criar` (`name='parcela_criar'`).
- `financeiro/admin.py` — `FormaPagementoAdmin` (list_display/list_editable/list_filter/search_fields).
- Migration para criar `FormaPagemento` e adicionar a FK em `ParcelaContaPagar` (aplicada).

### Segurança
`@login_required`, `get_object_or_404(ContaPagar, pk=conta_pk, empresa=empresa)` para isolamento por tenant, CSRF token no form, validação de fallback (`dias_list` vazio ou condição desconhecida usa `[0]`), e todo o loop de criação dentro de `transaction.atomic()`.

### Fluxo de integração no sistema
Pedido de Compra → Recebimento → Conta a Pagar criada automaticamente → usuário aciona "Criar Parcelas Automaticamente" (ou o fluxo alternativo de faturamento gera parcelas) → preview → confirmação → parcelas com valores/datas/forma de pagamento definidos → pagamentos registrados individualmente (`registrar_pagamento`) → conta marcada quitada quando todas as parcelas são pagas.

## Quando foi feito
Implementado e testado em **03/03/2026** (janela ~16:44–16:52, segundo o changelog original). Rodando sobre Django 5.2.7 na época (o repositório já está em 6.0.6 atualmente — ver `README.md` raiz).

## Status final
Marcado como "100% funcional e pronto para produção" nos documentos originais: `python manage.py check` sem issues, migrations aplicadas, template e JS validados manualmente. Testes automatizados (unitários/integração) foram apenas **sugeridos** nos documentos fonte (`test_parcela_criar_view_get`, `test_parcela_criar_30_60_dias`, `test_workflow_completo`, etc.) — não há confirmação de que tenham sido efetivamente escritos; considerar isso ao avaliar cobertura de testes atual do módulo.

## Roteiro de teste manual (preservado para referência)
1. `python manage.py runserver`, login em `/admin/` (ou app), navegar a Financeiro → Contas a Pagar.
2. Abrir uma conta sem parcelas e acessar `/financeiro/contas/<id>/parcelas/criar/`.
3. Alternar as condições de pagamento e conferir o preview recalculando em tempo real (datas, valores, ajuste de centavos na última parcela).
4. Selecionar forma de pagamento e confirmar "Criar Parcelas"; validar redirecionamento e mensagem de sucesso, e que as parcelas aparecem na tela de detalhe da conta com os valores/datas/status ("ABERTA") esperados.

## Gotchas / avisos ainda relevantes
- Se a página não carregar: conferir se a conta já possui parcelas (o fluxo original redireciona nesse caso).
- Valores "errados" no preview geralmente indicam `ContaPagar.valor_total` não preenchido ou JS não carregado.
- Datas inesperadas: conferir `data_emissao` da conta e timezone do servidor.
- A soma das parcelas deve sempre fechar com `valor_total` graças ao ajuste de centavos na última parcela — se não fechar, é sinal de regressão nessa lógica.

## Melhorias futuras sugeridas (não confirmadas como implementadas)
Desconto por pagamento antecipado, multa/juros por atraso, juros progressivos por parcela, notificação por e-mail/WhatsApp, relatórios/dashboard de parcelamento, integração com gateway de pagamento (Stripe/PagSeguro). Consultar o estado atual do módulo `financeiro/` antes de assumir que algo desta lista já existe.
