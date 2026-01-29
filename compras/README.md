# Módulo de Compras

## Visão Geral

O módulo de Compras implementa um sistema completo de gestão de solicitações de compra e cotações com múltiplos fornecedores, permitindo **cotação seletiva** onde o comprador escolhe quais itens cotar em cada momento.

## Funcionalidades Principais

### 1. Solicitação de Compra (SC)

**Fluxo:**
```
RASCUNHO → PENDENTE → APROVADA → PARCIALMENTE_COTADA → TOTALMENTE_COTADA → EM_COMPRA → CONCLUIDA
```

**Fluxo Emergencial:** ⚡
```
CRIAÇÃO → APROVADA AUTOMATICAMENTE (pula PENDENTE)
```

**Campos principais:**
- Número automático (SC-000001)
- Solicitante
- Data de necessidade
- Justificativa
- Departamento
- **Emergencial** (checkbox) - Nova funcionalidade
- **Justificativa Emergencial** (obrigatória se emergencial)
- Status com tracking de % cotado
- Aprovação com aprovador e data

**Compras Emergenciais:** ⚡
- Checkbox "Compra Emergencial" no formulário
- Se marcado, exige justificativa específica da emergência
- **Aprovação automática** ao criar (status = APROVADA)
- Aprovador = próprio solicitante
- Pula etapa de aprovação formal
- Badge visual vermelho com raio
- Ideal para: quebras de equipamento, falta de estoque crítico, problemas de produção urgentes

**Status dos Itens:**
- `PENDENTE`: Item ainda não foi selecionado para cotação
- `SELECIONADO`: Item marcado para ser incluído na próxima cotação
- `EM_COTACAO`: Item já vinculado a uma cotação ativa
- `COTADO`: Item com fornecedor vencedor selecionado
- `APROVADO`: Item aprovado para compra

### 2. Cotação Seletiva

**Inovação:** Sistema de checkboxes permite cotar apenas alguns itens da solicitação, deixando outros pendentes.

**Como funciona:**
1. Solicitação aprovada exibe checkboxes ao lado de cada item PENDENTE
2. Comprador seleciona os itens desejados (1 ou mais)
3. Clica em "Cotar Selecionados"
4. Sistema cria nova cotação apenas com itens selecionados
5. Itens não selecionados permanecem PENDENTES
6. Processo pode ser repetido várias vezes

**Cálculo do Status:**
- 0% cotado = `PENDENTE` ou `APROVADA`
- 1-99% cotado = `PARCIALMENTE_COTADA`
- 100% cotado = `TOTALMENTE_COTADA`

### 3. Cotação (COT)

**Fluxo:**
```
RASCUNHO → EM_ANDAMENTO → CONCLUIDA
```

**Campos principais:**
- Número automático (COT-000001)
- Vinculada à Solicitação origem
- Comprador responsável
- Data limite para resposta
- Status

**Rastreabilidade:**
- Cada item da cotação mantém link com o item original da solicitação
- Permite visualizar de onde veio cada produto cotado

### 4. Propostas de Fornecedores

**Comparação Multi-Fornecedor:**
- Múltiplas propostas por item
- Campos comparativos:
  * Preço unitário e total
  * Prazo de entrega (dias)
  * Forma de pagamento
  * Condição de pagamento
  * Marca
  * Observações
- Ordenação automática por menor preço
- Seleção do vencedor com marcação visual
- Apenas um fornecedor pode ser selecionado por item

**Ao selecionar vencedor:**
1. Desmarca outros fornecedores do mesmo item
2. Atualiza status do item para `COTADO`
3. Recalcula % da solicitação
4. Atualiza status da solicitação se necessário

## Casos de Uso

### Caso 1: Cotação Completa (Normal)

1. Solicitação criada com 5 itens
2. Solicitação aprovada pelo gerente
3. Comprador seleciona todos os 5 itens
4. Cria cotação com 5 itens
5. Adiciona propostas de 3 fornecedores
6. Seleciona vencedor para cada item
7. Status: 100% → `TOTALMENTE_COTADA`

### Caso 2: Cotação Parcial

1. Solicitação criada com 10 itens
2. Solicitação aprovada
3. **Primeira cotação:** Comprador seleciona 4 itens urgentes
4. Status: 40% → `PARCIALMENTE_COTADA`
5. Adiciona propostas e seleciona vencedores
6. **Segunda cotação:** Seleciona mais 3 itens
7. Status: 70% → `PARCIALMENTE_COTADA`
8. **Terceira cotação:** Seleciona últimos 3 itens
9. Status: 100% → `TOTALMENTE_COTADA`

### Caso 3: Compra Emergencial ⚡ (NOVO)

**Cenário:** Quebra de equipamento crítico na produção

1. Supervisor cria solicitação com peças necessárias
2. **Marca checkbox "Compra Emergencial"**
3. Preenche justificativa: "Quebra do trator principal, produção parada, perda estimada R$ 50.000/dia"
4. **Sistema aprova automaticamente** ao salvar
5. Status já é `APROVADA` (pula PENDENTE)
6. Badge vermelho com raio aparece na lista
7. Comprador pode selecionar itens e cotar imediatamente
8. Processo continua normal a partir da cotação

**Quando usar Emergencial:**
- ✅ Quebra de equipamento que para produção
- ✅ Falta de insumo crítico (defensivo, semente)
- ✅ Problema que gera perdas financeiras significativas
- ✅ Situação que não pode aguardar aprovação (24-48h)
- ❌ Compras planejadas ou previsíveis
- ❌ Reposição de estoque regular
- ❌ Compras sem justificativa sólida

### Caso 4: Cotação com Itens Cancelados

1. Solicitação com 8 itens
2. Comprador cota 5 itens (62%)
3. Decide que 3 itens não são mais necessários
4. Status permanece: `PARCIALMENTE_COTADA`
5. *(Futuramente: opção para cancelar itens específicos)*

## Navegação

### URLs Principais

**Solicitações:**
- `/compras/solicitacoes/` - Lista todas as solicitações
- `/compras/solicitacoes/nova/` - Criar nova solicitação
- `/compras/solicitacoes/<id>/` - Detalhes e seleção de itens
- `/compras/solicitacoes/<id>/aprovar/` - Aprovar solicitação
- `/compras/solicitacoes/<id>/cancelar/` - Cancelar solicitação
- `/compras/solicitacoes/<id>/selecionar-itens/` - Processar seleção (POST)

**Cotações:**
- `/compras/cotacoes/` - Lista todas as cotações
- `/compras/cotacoes/nova/<solicitacao_id>/` - Criar cotação dos itens selecionados
- `/compras/cotacoes/<id>/` - Detalhes e comparação de propostas
- `/compras/cotacoes/<id>/concluir/` - Concluir cotação

**Propostas:**
- `/compras/cotacoes/<cot_id>/item/<item_id>/proposta/` - Adicionar propostas
- `/compras/propostas/<id>/selecionar/` - Selecionar fornecedor vencedor

### Menu Sidebar

```
Compras (novo badge)
├── Solicitações
├── Nova Solicitação
├── ─────────────
└── Cotações
```

## Tecnologias

- **Django 5.2.7**
- **PostgreSQL** (multi-tenant)
- **Bootstrap 5** (checkboxes, progress bars, badges)
- **JavaScript** (select all, submit handlers)

## Models

### SolicitacaoCompra
- Auto-número (SC-######)
- 8 status choices
- Métodos: `gerar_numero()`, `calcular_percentual_cotado()`, `atualizar_status_cotacao()`, `aprovar()`, `cancelar()`

### ItemSolicitacaoCompra
- **`selecionado_para_cotar`** (BooleanField) - Campo chave para cotação seletiva
- 5 status choices
- FK para cotacao_vinculada (rastreabilidade)

### Cotacao
- Auto-número (COT-######)
- FK para solicitacao
- 4 status choices

### ItemCotacao
- FK para item_solicitacao (rastreabilidade)
- FK para cotacao

### FornecedorCotacao
- FK para item_cotacao
- Campos de comparação (preço, prazo, condições)
- **`selecionado`** (BooleanField) - Marca vencedor
- Auto-cálculo de preço total

## Próximas Fases

### Fase 2: Pedido de Compra
- Gerar PO a partir de cotação concluída
- Vincular itens cotados ao pedido
- Tracking de entregas

### Fase 3: Avaliação de Fornecedores
- Avaliar após recebimento
- Critérios: qualidade, prazo, conformidade, atendimento, preço
- Histórico de avaliações
- Relatórios de performance

### Fase 4: Integração
- Vincular entrada de estoque ao recebimento
- Integração com financeiro (contas a pagar)
- NFe de entrada

## Permissões (Futuro)

### Permissões Gerais
- `compras.add_solicitacaocompra` - Criar solicitação
- `compras.aprovar_solicitacaocompra` - Aprovar solicitação
- `compras.add_cotacao` - Criar cotação
- `compras.add_fornecedorcotacao` - Adicionar propostas
- `compras.selecionar_fornecedor` - Escolher vencedor

### Permissões Emergenciais (A Implementar)
- `compras.add_solicitacao_emergencial` - Criar compras emergenciais

**Níveis de Autorização Sugeridos:**
```python
# Supervisor
- Compras emergenciais até R$ 10.000
- Justificativa obrigatória
- Notificação automática ao gerente

# Gerente  
- Compras emergenciais até R$ 50.000
- Justificativa obrigatória
- Notificação automática ao diretor

# Diretor
- Compras emergenciais sem limite
- Justificativa obrigatória
- Relatório mensal ao board
```

**Validações Futuras:**
- ✓ Verificar permissão antes de exibir checkbox
- ✓ Validar no backend (não apenas frontend)
- ✓ Limite de valor por nível hierárquico
- ✓ Notificação automática ao superior
- ✓ Auditoria mensal de uso
- ✓ Alerta se uso excessivo (> 20% do total)

**Implementação:**
```python
# views.py
if form.emergencial and not request.user.has_perm('compras.add_solicitacao_emergencial'):
    messages.error(request, 'Você não tem permissão para criar compras emergenciais')
    return redirect('compras:solicitacao_list')
```

## Autor

Desenvolvido como parte do ERP Agrícola SAAS Multi-tenant
Data: Janeiro 2025
