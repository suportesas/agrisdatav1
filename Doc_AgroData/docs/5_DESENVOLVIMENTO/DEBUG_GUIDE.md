# Guia de Debug

Owner: Engenharia
Status: Draft
Last Updated: 2026-07-01
Scope: Diagnostico tecnico

## Objetivo
Padronizar a investigacao de bugs por fluxo funcional.

## Roteiro rapido
1. Reproduzir erro com passo a passo e dados.
2. Isolar modulo e endpoint afetado.
3. Validar empresa e permissao do usuario.
4. Verificar logs, stacktrace e estado no banco.
5. Confirmar regra de negocio e condicional esperada.
6. Criar teste de regressao apos correcao.

## Pontos de verificacao por dominio
- Compras/Financeiro: integracao recebimento -> conta -> parcela
- Estoque: movimentacao, saldo e bloqueio por quantidade
- Faturamento: campos fiscais e calculos tributarios
- Permissoes: role, grupo e escopo por empresa

## Anti-patterns comuns
- Falta de filtro por empresa em queryset
- Uso de float em calculos monetarios
- Mudanca de status sem regra de transicao
- Falta de guard para divisao por zero

## Evidencias obrigatorias em PR de correcao
- Cenário reproduzido
- Causa raiz
- Regra alterada
- Teste adicionado
