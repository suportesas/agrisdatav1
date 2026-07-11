# Modelos e Hierarquia de Dominio

Owner: Arquitetura
Status: Draft
Last Updated: 2026-07-01
Scope: Arquitetura de dominio

## Objetivo
Consolidar a hierarquia dos principais modelos e relacionamentos de negocio.

## Dominio Financeiro - Contas a Pagar
Fonte consolidada:
- ARQUITETURA_CONTAS_PAGAR.md

### Estrutura principal
- ContaPagar
  - Relaciona com recebimento de compra, fornecedor e empresa
  - Campos financeiros centrais: valor_total, valor_ajustado, desconto_negociado, juros_acumulados, multa_acumulada
  - Ciclo de vida: ABERTA, APROVADA, PAGA, CANCELADA, RENEGOCIADA
- ParcelaContaPagar
  - Derivada da ContaPagar
  - Campos: valor_parcela, vencimento, juros/multa por parcela e valor total calculado
  - Ciclo de vida: ABERTA, PAGA, VENCIDA, RENEGOCIADA
- PagamentoContaPagar
  - Registro do evento de pagamento e compensacao
  - Guarda forma de pagamento, documento e comprovante
- AjusteContaPagar
  - Materializa divergencias, descontos e renegociacoes
- ConfiguracaoJurosMulta
  - Parametros por empresa para juros, multa e tolerancia

### Fluxos arquiteturais relevantes
1. Recebimento finalizado pode originar ContaPagar automaticamente.
2. ContaPagar pode ser parcelada conforme condicao de pagamento.
3. Atraso em parcela gera juros e multa segundo configuracao.
4. Divergencias de recebimento podem reduzir valor ajustado.
5. Pagamento gera historico financeiro e comprovacao.

## Dominio Estoque - Alertas RF-055
Fonte consolidada:
- ARQUITETURA_RF-055.md

### Estrutura funcional
- View de listagem de estoque calcula saldo por produto.
- Classificacao de alerta por faixa:
  - Critico: saldo <= 0
  - Baixo: saldo < minimo
  - Excesso: saldo > maximo
- Context processor agrega totais de alerta para sidebar.
- Templates exibem badges, cores e coluna de situacao.

### Arquitetura multiempresa
- Usuario comum ve apenas dados de sua empresa.
- Superuser pode visualizar todas as empresas.
- Filtragem por empresa deve ser obrigatoria em consultas nao-superuser.

## Padroes de modelagem aplicados
- Escopo por empresa em modelos de negocio.
- Estados explicitos para rastrear ciclo de vida.
- Separacao entre entidade principal, entidade de detalhamento e entidade de evento.
- Campos de auditoria para criado/atualizado e autor quando aplicavel.

## Riscos arquiteturais a monitorar
- Falta de filtro por empresa em consultas sensiveis.
- Regras de juros/multa sem documentacao formulaica centralizada.
- Dependencia de processamentos periodicos para manter valores atualizados.

## Referencias legadas
- ARQUITETURA_CONTAS_PAGAR.md
- ARQUITETURA_RF-055.md
