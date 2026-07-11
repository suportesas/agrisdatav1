# 📋 GUIA DE USO - DIVERGÊNCIAS E AVALIAÇÃO DE FORNECEDOR

## ✨ O que foi implementado:

### 1️⃣ **Tipos de Divergência (CRUD)**
- Criar tipos de divergência personalizados por empresa
- Exemplos padrão: Danos Externos, Lacre Rompido, Sujeira, Vencido, Quantidade Diferente, Produto Errado, Defeito, etc.
- Cada tipo tem severidade (Leve, Médio, Grave) para priorização
- Gerenciado via Django Admin

### 2️⃣ **Conferência de Recebimento Melhorada**
- Seleção estruturada de tipos de divergência
- Múltiplas divergências por recebimento
- Para cada divergência:
  - ✅ Tipo (obrigatório)
  - ✅ Descrição detalhada (obrigatório)
  - Item afetado (opcional)
  - Quantidade afetada (opcional)
  - Ação proposta (ex: devolver 100%, ajustar preço)
  - Fotos (para integração futura)

### 3️⃣ **Avaliação do Fornecedor**
- Disponível após finalizar entrada no estoque (status = FINALIZADO)
- 5 critérios de avaliação (1-5 estrelas):
  1. Qualidade do Produto
  2. Cumprimento de Prazos
  3. Documentação/NF-e
  4. Qualidade do Atendimento
  5. Relação Preço/Qualidade
- Nota média calculada automaticamente
- Comentários livres: Pontos Positivos, Pontos a Melhorar, Recomendações
- Recomendação final (Sim/Não)

---

## 🚀 COMO USAR:

### PASSO 1: Configurar Tipos de Divergência
```
1. Executar setup:
   python criar_tipos_divergencia.py
   
2. Ou adicionar manualmente:
   - Acesse: http://127.0.0.1:8000/admin/compras/tipodivergencia/
   - Clique em "Adicionar Tipo de Divergência"
   - Preencha:
     * Código (ex: DANO_EXT)
     * Nome (ex: Danos Externos)
     * Descrição (opcional)
     * Severidade (Leve, Médio, Grave)
     * Ativo (marque para usar)
```

### PASSO 2: Conferir Recebimento com Divergência
```
1. Acesse o recebimento pendente
   URL: http://127.0.0.1:8000/compras/recebimentos/{id}/

2. Clique "Conferir Recebimento"

3. Na conferência:
   ☐ Selecione "Tudo OK" se sem problemas
   ☑ Selecione "Há Divergências" se encontrou problemas
   
4. Para CADA divergência:
   ① Selecione o Tipo (obrigatório)
   ② Descreva o problema detalhadamente (obrigatório)
   ③ (Opcional) Selecione item específico
   ④ (Opcional) Informe quantidade afetada
   ⑤ (Opcional) Proponha ação (devolver, ajustar preço, etc)
   
5. Clique "Adicionar Divergência" se tiver mais de uma
   
6. Finalize com "Confirmar Conferência"
```

### PASSO 3: Dar Entrada no Estoque
```
1. O recebimento agora pode ser processado mesmo com divergência
   
2. Clique "Dar entrada (com divergência)"
   
3. Sistema:
   ✅ Registra quantidade no estoque conforme recebido
   ✅ Mantém divergência documentada
   ✅ Muda status para FINALIZADO
```

### PASSO 4: Avaliar Fornecedor (após entrada)
```
1. No recebimento FINALIZADO, clique "Avaliar Fornecedor"

2. Selecione estrelas para os 5 critérios

3. (Opcional) Adicione comentários:
   - Pontos positivos
   - Pontos a melhorar
   - Recomendações futuras

4. Informe se recomenda o fornecedor (Sim/Não)

5. Clique "Salvar Avaliação"

O sistema calcula automaticamente a nota média (média das 5 estrelas)
```

---

## 📊 VISUALIZAÇÃO DE DADOS:

### No Recebimento (recebimento_detail.html)
- ✅ Lista todas as divergências estruturadas com:
  - Tipo e severidade
  - Produto/item afetado
  - Descrição completa
  - Ação proposta
  - Status (Pendente, Em Análise, Resolvido)

- ✅ Exibe avaliação do fornecedor com:
  - Nota média (em destaque)
  - 5 notas individuais
  - Recomendação (Sim/Não)
  - Pontos positivos/negativos

### Django Admin
- Gerenciar Tipos de Divergência
- Listar todas as Divergências registradas
- Consultar histórico de Avaliações

---

## 🔧 PRÓXIMOS PASSOS (Novas Funcionalidades):

### PDF para Fornecedor ✅ (pronto para implementar)
```python
# Gerar PDF com:
- Dados da divergência
- Fotos (se adicionadas)
- Ação proposta
- Data/hora
# Pronto para envio automático quando integrar canal do fornecedor
```

### Relatórios de Desempenho
- Avaliação média por fornecedor
- Histórico de divergências
- Taxa de recomendação
- Trending (melhora/piora ao longo do tempo)

### Notificações
- Email para fornecedor com divergências (quando canal estiver pronto)
- Lembretes de avaliação não preenchida
- Alertas de fornecedores com baixa avaliação

### Integração com Canal do Fornecedor (Futuro)
- Envio automático de PDF de divergência
- Resposta/resolução do fornecedor
- Tracking de SLA

---

## 📋 MODELOS CRIADOS:

### 1. TipoDivergencia
- `empresa` - FK para Empresa (multi-tenant)
- `codigo` - Código único (ex: DANO_EXT)
- `nome` - Nome descritivo
- `descricao` - Detalhes
- `severidade` - LEVE / MEDIO / GRAVE
- `ativo` - Bool para incluir/exclusão

### 2. DivergenciaRecebimento
- `recebimento` - FK para RecebimentoCompra
- `tipo_divergencia` - FK para TipoDivergencia
- `item_recebimento` - FK para ItemRecebimento (opcional)
- `quantidade_afetada` - Decimal (opcional)
- `descricao_detalhes` - Texto obrigatório
- `acao_proposta` - Texto
- `foto_1`, `foto_2` - ImageField
- `status_divergencia` - PENDENTE / EM_ANALISE / RESOLVIDO / NEGAR
- `registrado_por` - FK Usuario

### 3. AvaliacaoFornecedor
- `recebimento` - OneToOneField
- `fornecedor` - FK para Fornecedor
- `qualidade_produto` - Int 1-5
- `prazo_entrega` - Int 1-5
- `documentacao` - Int 1-5
- `atendimento` - Int 1-5
- `preco` - Int 1-5
- `nota_media` - Decimal (calculada)
- `pontos_positivos` - Texto
- `pontos_negativos` - Texto
- `recomendacao` - Texto
- `recomenda` - Bool
- `avaliador` - FK Usuario

---

## 🎯 RESUMO DE FLUXO:

```
1. Criar Tipo de Divergência (uma vez)
   ↓
2. Receber Mercadoria
   ↓
3. ✅ Conferir Recebimento (sem ou COM divergência)
   ↓
4. Registrar Divergênc ias (estruturadas + fotos)
   ↓
5. Dar Entrada no Estoque (mesmocom divergência!)
   ↓
6. Avaliar Fornecedor (após entrada)
   ↓
7. (Futuro) PDF → Enviar ao Fornecedor
   ↓
8. (Futuro) Tracking → Resposta/Resolução do Fornecedor
```

---

## ✅ TESTES DE VALIDAÇÃO:

Execute este teste com um recebimento real:

```python
python criar_tipos_divergencia.py  # Popular tipos padrão

# Acesse:
# 1. http://127.0.0.1:8000/compras/recebimentos/8/
# 2. Clique "Conferir Recebimento"
# 3. Selecione "Há Divergências"
# 4. Adicione uma divergência com tipo "Danos Externos"
# 5. Clique "Confirmar Conferência"
# 6. Retorne e clique "Dar entrada (com divergência)"
# 7. Clique "Avaliar Fornecedor"
# 8. Preencha as 5 notas (estrelas)
# 9. Salve
# 10. Verifique dados no recebimento_detail
```

---

**Desenvolvido em 03/03/2026**
**Sistema ERP Agrícola v1.0**
