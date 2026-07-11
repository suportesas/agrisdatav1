# 🔍 Questionamento sobre Movimentações de Estoque

## Data: 03/03/2026

### Dúvida
Comportamento das movimentações de estoque na página http://127.0.0.1:8000/estoque/movimentacoes/4/

### Observação do Usuário
- Status da movimentação: **PENDENTE**
- Quando executa a movimentação: é **somado ao estoque**
- **Questão**: Não informa claramente o tipo de movimento (entrada/saída/transferência)

### Fluxo Esperado
1. **Status PENDENTE** = Movimentação criada, **estoque NÃO alterado**
2. **Ao executar** = Estoque é finalmente alterado

### Campos Disponíveis no Modelo
- **TIPO**: ENTRADA | SAÍDA | TRANSFERÊNCIA | AJUSTE | DEVOLUÇÃO
- **ORIGEM**: COMPRA | PRODUÇÃO | VENDA | CONSUMO PRODUÇÃO | DEVOLUÇÃO CLIENTE | etc

### O que Verificar
1. No template `movimentacao_detail.html` (linha ~40):
   - Está exibindo o **TIPO**? (com ícone correto)
   - Está exibindo a **ORIGEM**?

2. No método `_atualizar_estoque()` do model `MovimentacaoEstoque`:
   - ENTRADA → soma
   - SAÍDA → subtrai
   - A lógica está correta?

3. Teste Manual
   - Criar movimentação com TIPO=SAÍDA
   - Verificar se subtrai corretamente
   - Verificar se a interface deixa claro qual é o tipo

### Status
⏳ **PENDENTE DE ANÁLISE DETALHADA**

---
**Próximas Ações:**
- [ ] Usuário análisa diretamente na página
- [ ] Verificar se template exibe TIPO e ORIGEM corretamente
- [ ] Testar com diferentes tipos de movimentação
- [ ] Corrigir se houver inversão de lógica (soma quando deveria subtrair)
