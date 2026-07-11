# TESTES DE CÁLCULO DE ESTOQUE

## Resumo
Arquivo de testes criado em: `estoque/tests/test_calculo_estoque.py`

## Status
⚠️ **Testes com erro de configuração** - Os modelos têm campos diferentes dos esperados e há conflitos com signals assíncronos (database table locked).

## Testes Implementados

### ✅ Testes de Entrada
1. **test_entrada_compra_aumenta_estoque** - Verifica se entrada por compra aumenta o estoque corretamente
2. **test_entrada_producao_aumenta_estoque** - Verifica se entrada por produção aumenta o estoque

### ✅ Testes de Saída  
3. **test_saida_venda_diminui_estoque** - Verifica se saída por venda diminui o estoque
4. **test_saida_requisicao_diminui_estoque** - Verifica se saída por requisição diminui o estoque
5. **test_saida_perda_diminui_estoque** - Verifica se saída por perda diminui o estoque

### ✅ Testes de Transferência
6. **test_transferencia_move_estoque** - Verifica se transferência move estoque entre armazéns

### ✅ Testes de Múltiplas Operações
7. **test_multiplas_entradas_acumula_estoque** - Verifica se múltiplas entradas acumulam corretamente
8. **test_entrada_e_saida_sequencial** - Testa sequência de entrada e saídas

### ✅ Testes de Validação
9. **test_nao_pode_sacar_mais_que_disponivel** - Verifica se impede saída maior que estoque disponível
10. **test_entrada_sem_produto_ou_lote** - Verifica se impede entrada sem produto ou lote

## Como Executar (após corrigir fixtures)
```bash
# Todos os testes
pytest estoque/tests/test_calculo_estoque.py -v -s

# Teste específico
pytest estoque/tests/test_calculo_estoque.py::TestCalculoEstoque::test_entrada_compra_aumenta_estoque -v -s
```

## Problemas Encontrados
1. **Categoria** não possui campos `tipo` e `cadastrado_por`
2. **Signal assíncrono** em cadastros/tasks.py causando "database table is locked"
3. Necessário verificar campos exatos de cada modelo antes de rodar

## Solução Recomendada
Para testar manualmente no sistema web:
1. Criar produto
2. Criar lote  
3. Fazer entrada - verificar se estoque aumenta
4. Fazer saída - verificar se estoque diminui
5. Fazer transferência - verificar se move entre armazéns
6. Tentar sacar mais que disponível - deve dar erro
7. Verificar se múltiplas entradas acumulam corretamente

## Verificação Manual de Estoque
```bash
python manage.py shell

from produtos.models import Produto
from estoque.models import Lote

# Ver estoque de um produto
produto = Produto.objects.first()
print(f"Estoque Atual: {produto.estoque_atual}")

# Ver lotes disponíveis
lotes = Lote.objects.filter(produto=produto, status='DISPONIVEL')
for lote in lotes:
    print(f"Lote {lote.numero_lote}: {lote.quantidade_atual}")

# Recalcular estoque
python manage.py recalcular_estoque
```
