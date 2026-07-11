# Plano: Reestruturação do Sistema de Etiquetas de Pallet + Controle de Estoque

> **Status:** Em estudo — não iniciado  
> **Módulo:** `embalagem/`  
> **Impacto:** Sem migração de banco necessária

---

## 1. Problema Atual

O sistema tem **3 pontos diferentes para imprimir etiqueta** e o operador não sabe quando usar cada um:

| Ponto | URL | Tem cliente/navio? | Quando usar? |
|---|---|---|---|
| Lista de pallets (1 a 1) | `/pallets/{id}/etiqueta/` | Não | Qualquer hora |
| Etiquetas da Ordem (lote) | `/ordens/{id}/etiquetas/` | Não | Após gerar pallets |
| Etiquetas do Romaneio | `/romaneios/{id}/etiquetas/` | Sim | Após confirmar romaneio |

**Consequências:**
- Operador imprime na etapa 3 (sem cliente), depois reimpressa na etapa 6 (com cliente)
- A flag `etiqueta_gerada` existe no model mas não bloqueia nada
- Dashboard mostra 5 etapas mas etiqueta aparece em dois pontos com comportamentos diferentes
- Pallets têm `armazem` e `local_estocagem` mas não há visão consolidada de estoque

---

## 2. Como Outros Sistemas Fazem (Referência de Mercado)

Sistemas como **Produce Pro**, **TraceFirst** (Chile) e **OneSource** (África do Sul) seguem o padrão **GS1 Fresh Produce**:

- **Etiqueta do pallet** → gerada no packing, **nunca muda**, sem dados de cliente
- **Dados de destino** (cliente, navio, container) → ficam nos **documentos de expedição** (Invoice, Packing List, BL)

**Porém**, contratos de exportação do agronegócio brasileiro frequentemente exigem essas informações **na própria etiqueta**. Então a solução é formalizar dois tipos:

---

## 3. Solução Proposta: Dois Tipos de Etiqueta

### Tipo 1 — Etiqueta de Rastreamento
- **Impressa:** logo após a geração dos pallets (Ordem de Embalagem)
- **Conteúdo:** Exportador (empresa/CNPJ), código de barras, produto, pesos, lote, safra, data
- **Não tem:** cliente, porto, navio, container
- **Uso:** identificação e câmara fria — permanece colada ao pallet para sempre

### Tipo 2 — Etiqueta de Expedição
- **Impressa:** quando o pallet é vinculado a um Romaneio confirmado
- **Conteúdo:** tudo do Tipo 1 + Importador, porto destino, navio, viagem, armador, container
- **Uso:** exportação — exigida nos contratos com clientes

O pallet pode ter:
- **Só a Etiqueta de Rastreamento** → fruta ainda não vendida
- **As duas** → fruta vendida/exportada (cola a de expedição por cima ou ao lado)

---

## 4. Fluxo Corrigido

```
[1] Configurar TipoEmbalagem (1x por produto)
         ↓
[2] Criar OrdemEmbalagem (safra, lote, tipo, quantidade)
         ↓
[3] Gerar Pallets
         ↓
[4] 🖨️ IMPRIMIR ETIQUETA DE RASTREAMENTO  ← único momento para esta etiqueta
    Botão: "Etiquetas de Rastreamento" (Ordem)
    Conteúdo: produto, pesos, lote, safra, barcode
         ↓
[5] Pallet vai para câmara fria / armazém
         ↓
[6] Criar Romaneio → vincular pallets → Confirmar
         ↓
[7] 🖨️ IMPRIMIR ETIQUETA DE EXPEDIÇÃO  ← apenas quando tem cliente/booking
    Botão: "Etiquetas de Expedição" (Romaneio)
    Conteúdo: tudo + cliente + navio + container + porto
         ↓
[8] Conferência na doca (scanner)
         ↓
[9] Concluído
```

---

## 5. O que Precisa Ser Feito (Checklist)

### 5.1 Template de Etiqueta
- [ ] `templates/embalagem/pallet/etiqueta_pdf.html`
  - Adicionar variável `modo` no contexto (`'rastreamento'` ou `'expedicao'`)
  - Envolver bloco "Importador/Destino" com `{% if modo == 'expedicao' and romaneio %}`
  - Envolver bloco "Shipping/Exportação" com `{% if modo == 'expedicao' and romaneio.booking %}`
  - Footer indicar o tipo: `RASTREAMENTO` ou `EXPEDIÇÃO`
  - O restante (barcode, produto, pesos, caixas) permanece igual nos dois modos

### 5.2 Views
- [ ] `embalagem/views.py` — `_render_etiqueta_pdf()` (linha ~280)
  - Adicionar parâmetro `modo='rastreamento'` e passá-lo ao contexto
- [ ] `embalagem/views.py` — `pallet_etiqueta_pdf()` (linha ~314)
  - Aceitar query param `?modo=expedicao`
  - Default: `modo='rastreamento'`
- [ ] `embalagem/views.py` — `ordem_etiquetas_pdf()` (linha ~338)
  - Sempre chamar com `modo='rastreamento'`
- [ ] `embalagem/views.py` — `romaneio_etiquetas_pdf()` (linha ~355)
  - Sempre chamar com `modo='expedicao'`

### 5.3 Botões nas Telas
- [ ] `templates/embalagem/ordem/detail.html`
  - Renomear: "Etiquetas PDF" → **"Etiquetas de Rastreamento"**
- [ ] `templates/embalagem/romaneio/detail.html`
  - Renomear: "Etiquetas PDF" → **"Etiquetas de Expedição"**
  - Cor/ícone diferente para diferenciar visualmente
- [ ] `templates/embalagem/pallet/list.html`
  - Botão individual: trocar por dropdown com duas opções
    - "Rastreamento" → sempre disponível
    - "Expedição" → só habilitado se pallet RESERVADO ou CARREGADO

### 5.4 Dashboard
- [ ] `templates/embalagem/dashboard.html`
  - Atualizar card "Etiquetas" para explicar os dois tipos
  - Adicionar link para tela de estoque de pallets

### 5.5 Controle de Estoque de Pallets *(novo)*
- [ ] `embalagem/views.py` — Nova view `pallet_estoque()`
  - Pallets agrupados por Armazém → Local de Estocagem
  - Filtros: status, tipo_embalagem, período
  - Totais por armazém: pallets, caixas, kg NET, kg GROSS
- [ ] `embalagem/views.py` — Nova view `pallet_transferir()`
  - Mover pallet entre armazéns/locais via form
- [ ] `embalagem/urls.py`
  - `path('estoque/', pallet_estoque, name='pallet_estoque')`
  - `path('pallets/<int:pk>/transferir/', pallet_transferir, name='pallet_transferir')`
- [ ] `templates/embalagem/pallet/estoque.html` *(novo)*
  - Layout de cards/tabela por armazém
  - Totalizadores

---

## 6. Arquivos que Mudam

| Arquivo | Tipo de mudança |
|---|---|
| `templates/embalagem/pallet/etiqueta_pdf.html` | Adicionar parâmetro `modo`; isolar blocos de cliente/shipping |
| `embalagem/views.py` | Parâmetro `modo` em 4 funções existentes; 2 novas views |
| `embalagem/urls.py` | 2 novas rotas |
| `templates/embalagem/ordem/detail.html` | Renomear botão |
| `templates/embalagem/romaneio/detail.html` | Renomear botão |
| `templates/embalagem/pallet/list.html` | Dropdown duplo no botão de impressão |
| `templates/embalagem/dashboard.html` | Atualizar card; link para estoque |
| `templates/embalagem/pallet/estoque.html` | **Novo** — tela de estoque de pallets |

**Nenhuma migração de banco.** Todos os dados já existem nos models.

---

## 7. O que NÃO muda

- Modelos de dados: `PalletEmbalado`, `OrdemEmbalagem`, `RomaneioVenda` — sem alteração
- Conferência na doca (scanner AJAX) — sem alteração
- Integração com Invoice, NF-e, CT-e — sem alteração
- Pallets MÃO criarão entradas em `MovimentacaoEstoque` do app `estoque/` (isso seria uma fase futura para relatório contábil integrado)

---

## 8. Questões Abertas para Decisão

- [ ] **Tamanho da etiqueta de expedição**: manter 100mm x 160mm ou aumentar para caber mais informações?
- [ ] **Etiqueta de expedição cola por cima ou ao lado da de rastreamento?** (define layout físico da etiqueta)
- [ ] **A Etiqueta de Rastreamento deve ter o nome da empresa?** Ou só o trace_code é suficiente para rastreamento interno?
- [ ] **Controle de estoque**: queremos apenas a visão por armazém/local, ou também registrar no `MovimentacaoEstoque` (integração contábil completa)?
- [ ] **Transferência de pallet**: quem pode transferir pallet de armazém? Qualquer usuário ou só Gerente/Admin?
- [ ] **Impressão da etiqueta de rastreamento é obrigatória antes de confirmar romaneio?** (bloquear se ainda não imprimiu)

---

## 9. Estimativa de Esforço

| Área | Complexidade | Estimativa |
|---|---|---|
| Template etiqueta (modo) | Baixa | 1h |
| Views — parâmetro modo | Baixa | 1h |
| Botões renomeados | Baixa | 1h |
| Dashboard atualizado | Baixa | 0,5h |
| View de estoque de pallets | Média | 3h |
| Template de estoque | Média | 2h |
| Testes e ajustes | — | 2h |
| **Total estimado** | | **~10h** |
