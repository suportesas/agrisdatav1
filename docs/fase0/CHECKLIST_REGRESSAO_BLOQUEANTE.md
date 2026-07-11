# Checklist de Regressao Bloqueante - Fase 0

Use este checklist antes de qualquer release de fase.

## 1. Compras

- [ ] Criar solicitacao com 1 item
- [ ] Aprovar solicitacao
- [ ] Gerar cotacao
- [ ] Gerar pedido
- [ ] Receber pedido e finalizar

## 2. Estoque

- [ ] Entrada com lote atualiza saldo
- [ ] Saida com lote respeita validacao
- [ ] Entrada sem lote atualiza saldo
- [ ] Saida sem lote atualiza saldo
- [ ] Relatorio de estoque carrega sem erro

## 3. Financeiro

- [ ] Conta a pagar criada manualmente
- [ ] Parcelas geradas
- [ ] Pagamento registrado
- [ ] Relatorio de contas a vencer
- [ ] Relatorio de contas vencidas

## 4. RH

- [ ] CRUD ferias
- [ ] CRUD afastamento
- [ ] CRUD rescisao
- [ ] Dashboard RH carrega

## 5. Seguranca e Multi-tenant

- [ ] Usuario sem empresa nao acessa dados de empresa
- [ ] Usuario A nao acessa dados da empresa B
- [ ] Rotas criticas exigem autenticacao

## Criterio bloqueante

Se qualquer item critico falhar, a release nao pode ser promovida.
