# ⚡ Compras Emergenciais - Guia Rápido

## O que é?

Sistema que permite criar pedidos de compra **sem aprovação formal** para situações de emergência.

## Como funciona?

### Processo Normal
```
Criar Solicitação → PENDENTE → Aguardar Aprovação → APROVADA → Cotar
```
⏱️ Tempo: 24-48h até poder cotar

### Processo Emergencial ⚡
```
Criar Solicitação + Checkbox "Emergencial" → APROVADA AUTOMATICAMENTE → Cotar Imediatamente
```
⏱️ Tempo: Imediato (0h)

## Quando usar?

### ✅ Situações Válidas
- **Quebra de equipamento crítico** (trator, colheitadeira, sistema de irrigação)
- **Falta de insumo que para produção** (defensivo, semente, fertilizante)
- **Problema que gera perdas financeiras** (R$ 10.000+ por dia)
- **Emergência operacional** (não pode aguardar 24-48h)

### ❌ NÃO usar para
- Compras planejadas ou previsíveis
- Reposição normal de estoque
- Compras sem urgência real
- Situações sem justificativa sólida

## Como criar?

1. Acesse **Compras → Nova Solicitação**
2. Preencha normalmente: data, justificativa, departamento
3. **Marque o checkbox "Compra Emergencial"**
4. **Campo aparece:** "Justificativa da Emergência" (obrigatório)
5. Explique detalhadamente:
   - O que aconteceu
   - Impacto na produção
   - Perda estimada
   - Por que não pode aguardar aprovação
6. Adicione os itens necessários
7. **Salvar = Automaticamente aprovada** ✅

## Exemplo Real

**Situação:** Quebra do trator principal às 14h

```
[✓] Compra Emergencial

Justificativa da Emergência:
"Quebra do trator T-001 às 14h durante preparo do solo.
Rolamento do eixo traseiro comprometido.
Produção parada: 50 hectares aguardando plantio.
Janela de plantio fecha em 3 dias.
Perda estimada: R$ 45.000 se perder janela.
Necessário peça urgente para reparo amanhã.
Não pode aguardar aprovação formal (48h)."

Itens:
- Rolamento SKF 6215 (Qtd: 2)
- Retentor 85x120x12 (Qtd: 2)
- Graxa especial (Qtd: 1kg)
```

## O que acontece?

### 1. Aprovação Automática
- Status muda para **APROVADA** ao salvar
- Aprovador = Próprio solicitante
- Data de aprovação = Agora

### 2. Badge Visual
- **Lista:** Raio vermelho ao lado do número
- **Detalhes:** Badge "⚡ EMERGENCIAL" no cabeçalho
- **Justificativa:** Destacada em vermelho

### 3. Cotação Imediata
- Pode selecionar itens e cotar imediatamente
- Não precisa aguardar ninguém aprovar
- Processo continua normal a partir daqui

## Rastreabilidade

Todas as compras emergenciais ficam marcadas permanentemente:

- ✓ Campo `emergencial = True`
- ✓ Justificativa da emergência gravada
- ✓ Aprovador = solicitante (auto-aprovação)
- ✓ Relatórios podem filtrar compras emergenciais
- ✓ Auditoria pode revisar uso correto

## Controles e Alertas

### Validações
- ❌ Checkbox marcado sem justificativa = **erro**
- ❌ Justificativa vazia = **não salva**
- ✓ Justificativa preenchida = **aprovação automática**

### Futuro (próximas fases)
- 📊 Relatório de compras emergenciais por período
- 📈 Análise de uso (% emergencial vs normal)
- 🚨 Alerta se uso excessivo (> 20% do total)
- 📧 Notificação ao gerente sobre auto-aprovação
- 🔍 Auditoria retroativa com justificativas

## Interface

### Formulário
```
[ ] Compra Emergencial  [badge: Pula Aprovação]
    ↓
[Campo aparece se marcado]
Justificativa da Emergência *
[TextArea obrigatório com alerta vermelho]
```

### Listagem
```
SC-000025  [⚡]  João Silva  15/01  APROVADA  [▓▓▓▓░░░░] 45%
```

### Detalhes
```
Solicitação SC-000025  [⚡ EMERGENCIAL]

[EMERGENCIAL] Justificativa:
> Quebra do trator T-001, produção parada, 
> perda R$ 45.000/dia, necessário urgente...
```

## Permissões

**Atual:** Qualquer usuário pode criar emergencial (temporário)

**⚠️ IMPORTANTE - Será Implementado:**

A funcionalidade de compras emergenciais será **restrita por permissões** em breve. Apenas usuários autorizados poderão marcar o checkbox "Compra Emergencial".

**Níveis Planejados:**

| Nível | Limite de Valor | Permissão |
|-------|----------------|-----------|
| **Supervisor** | Até R$ 10.000 | `compras.add_solicitacao_emergencial_basico` |
| **Gerente** | Até R$ 50.000 | `compras.add_solicitacao_emergencial_medio` |
| **Diretor** | Sem limite | `compras.add_solicitacao_emergencial_total` |

**O que vai mudar:**
```
✓ Checkbox só aparece para usuários com permissão
✓ Validação no backend (não apenas esconder no frontend)
✓ Verificação de limite de valor por nível
✓ Notificação automática ao superior sobre uso
✓ Relatório mensal de compras emergenciais por usuário
✓ Alerta se uso excessivo (> 20% das solicitações)
```

**Por que temporariamente liberado:**
Durante a implantação inicial, a funcionalidade está aberta para todos testarem e se familiarizarem. Após período de adaptação, as permissões serão ativadas conforme política da empresa.

## Dúvidas Frequentes

**P: Posso usar emergencial toda vez para ser mais rápido?**
R: Não. Será monitorado e gerado relatório. Uso inadequado será questionado na auditoria.

**P: E se eu marcar emergencial sem justificativa?**
R: Sistema não permite salvar. Campo é obrigatório.

**P: Quem aprova a compra emergencial depois?**
R: Ninguém. É auto-aprovada. Por isso a justificativa detalhada é crítica.

**P: Posso desmarcar emergencial depois de salvar?**
R: Não. É permanente para rastreabilidade.

**P: Aparece diferente nos relatórios?**
R: Sim. Badge vermelho e filtro específico.

## Responsabilidade

⚠️ **IMPORTANTE:**

Ao marcar uma compra como emergencial, você assume responsabilidade pela:
- Veracidade da emergência
- Adequação do uso do recurso
- Justificativa documental
- Explicação futura se questionado

Use com consciência e apenas quando realmente necessário!

---

**Desenvolvido:** Janeiro 2025
**Módulo:** Compras - Agrisdata SAAS
