# PRD — Módulo de Controle de Drawback

**Versão:** 1.4 — FINAL  
**Data:** 2026-06-26  
**Status:** Aprovado para implementação

---

## 1. Contexto e Situação Real

### 1.1 Dados levantados

| Item | Resposta |
|------|----------|
| Quantidade de ACs ativos | **1** |
| Vigência do AC | **2 anos** |
| Lançamentos de 2025 no ERP | **NÃO** — parcial ou nenhum |
| Controle manual atual | **SIM** — planilha disponível |
| Tipo de insumos no AC | **Importação + Mercado Interno** (Caixa, cola, Mulching, Manta, etc.) |
| Documentos de exportação disponíveis | **Só NF-e** — RE/DUE será adicionado para controle futuro |
| Template XLSX | **Colorido com formatação amigável** |

### 1.2 Consequência para o projeto

Como os lançamentos de 2025 **não estão todos no ERP**, não é possível vincular retrospectivamente via `ItemRecebimento` ou `ItemNFe` para a maior parte dos dados históricos.

A estratégia será:

```
DADOS DE 2025 (histórico da planilha)
  → Lançamento manual direto no módulo Drawback
  → Sem exigir ItemRecebimento ou ItemNFe no ERP
  → Flag: retroativo = True + origem = MANUAL

DADOS A PARTIR DE HOJE (novos)
  → Vinculação no momento do recebimento/exportação
  → Origem = ERP (ligado ao ItemRecebimento / ItemNFe)
```

Isso elimina a necessidade de primeiro importar 2025 inteiro para compras/faturamento (seria retrabalho desnecessário).

---

## 2. Fluxo Completo

```
┌─────────────────────────────────────────────────────────────────────┐
│  FASE 0 — REGULARIZAÇÃO (dados da planilha de 2025)                 │
│                                                                     │
│  1. Cadastrar o AC (número, tipo, início 2025, vencimento 2027)     │
│  2. Cadastrar os produtos autorizados no AC (conforme AC emitido)   │
│  3. Importar compras 2025 da planilha                               │
│     → Tela de lançamento manual de entrada drawback                 │
│     → Campos: Fornecedor | NF | Data | Produto | Qtd | Valor        │
│  4. Importar exportações 2025 da planilha                           │
│     → Tela de lançamento manual de saída drawback                   │
│     → Campos: Cliente | NF/DUE/RE | Data Embarque | Produto | Qtd  │
│  5. Conferir saldo com a planilha → saldo deve bater                │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│  FASE 1 — OPERAÇÃO NORMAL (2026 em diante)                          │
│                                                                     │
│  Recebimento de compra → botão "Vincular ao Drawback" no ERP        │
│  Emissão de NF-e exportação → botão "Vincular ao Drawback" no ERP  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Modelos de Dados

### 3.1 `AtoConcessorio`

| Campo | Tipo | Detalhe |
|-------|------|---------|
| empresa | FK Empresa | Multi-tenant |
| numero_ac | CharField(30) | Ex: 23/0001234-0 — único por empresa |
| tipo | CharField | `SUSPENSAO` \| `ISENCAO` \| `RESTITUICAO` |
| data_inicio | DateField | Data real de emissão (pode ser 2025) |
| data_vencimento | DateField | Geralmente data_inicio + 2 anos |
| data_prorrogacao | DateField null | Nova data fim se houver prorrogação |
| status | CharField | `ATIVO` \| `VENCIDO` \| `ENCERRADO` \| `CANCELADO` |
| despachante | CharField blank | Nome do despachante aduaneiro |
| numero_processo_siscomex | CharField blank | |
| observacoes | TextField blank | |
| criado_por | FK Usuario | |
| data_cadastro | auto_now_add | |
| data_atualizacao | auto_now | |

**Propriedade:** `data_fim_efetiva = data_prorrogacao or data_vencimento`

---

### 3.2 `DrawbackProdutoAC`

| Campo | Tipo | Detalhe |
|-------|------|---------|
| ato_concessorio | FK AtoConcessorio CASCADE | |
| produto | FK produtos.Produto PROTECT | |
| ncm | CharField(10) | Pré-preenche do produto, editável |
| descricao_mercadoria | CharField(200) | Conforme texto do AC |
| unidade_medida | FK UnidadeMedida | |
| quantidade_autorizada | DecimalField | Total autorizado pelo MDIC |
| quantidade_minima_export | DecimalField | Mínimo para comprovar cumprimento |

**Calculados em tempo real (sem coluna no banco):**
```
quantidade_comprada   = soma de todas entradas drawback deste produto/AC
quantidade_exportada  = soma de todas saídas drawback deste produto/AC
saldo_compra          = quantidade_autorizada − quantidade_comprada
saldo_exportacao      = quantidade_comprada − quantidade_exportada
percentual_cumprido   = quantidade_exportada / quantidade_minima_export × 100
```

---

### 3.3 `EntradaDrawback` (entrada de insumo)

Registro unificado de entrada — pode vir do ERP (ItemRecebimento) ou ser lançado manualmente (planilha 2025).

> **Importante:** Os insumos do AC são de **dois tipos de origem**: produtos importados do exterior e produtos comprados no mercado interno (caixa, cola, Mulching, Manta, etc.). Ambos são controlados no mesmo AC e registrados aqui com o campo `tipo_compra`.

| Campo | Tipo | Detalhe |
|-------|------|---------|
| ato_concessorio | FK AtoConcessorio PROTECT | |
| drawback_produto | FK DrawbackProdutoAC PROTECT | |
| **item_recebimento** | FK compras.ItemRecebimento **null** | Preenchido quando a compra está no ERP |
| fornecedor | FK cadastros.Fornecedor null | Preenchido no lançamento manual |
| numero_nf | CharField(20) | Número da nota fiscal de entrada |
| serie_nf | CharField(5) blank | |
| data_nf | DateField | Data da nota fiscal |
| data_recebimento | DateField | Data efetiva de recebimento |
| quantidade | DecimalField | Quantidade recebida sob drawback |
| valor_unitario | DecimalField null | Valor unitário (para relatório) |
| **tipo_compra** | CharField | `IMPORTACAO` \| `MERCADO_INTERNO` |
| **origem** | CharField | `ERP` \| `MANUAL` |
| **retroativo** | BooleanField default=False | True para lançamentos de 2025 |
| anulado | BooleanField default=False | Soft-cancel |
| motivo_anulacao | TextField blank | Obrigatório se anulado=True |
| observacoes | TextField blank | |
| registrado_por | FK Usuario | |
| data_registro | auto_now_add | |

**Restrições:**
- `quantidade` ≤ `saldo_compra` disponível no AC para o produto
- `data_recebimento` ≤ `data_fim_efetiva` do AC
- Se `origem=ERP`: `item_recebimento` obrigatório
- Se `origem=MANUAL`: `fornecedor` + `numero_nf` + `data_nf` obrigatórios

---

### 3.4 `SaidaDrawback` (exportação)

| Campo | Tipo | Detalhe |
|-------|------|---------|
| ato_concessorio | FK AtoConcessorio PROTECT | |
| drawback_produto | FK DrawbackProdutoAC PROTECT | |
| **item_nfe** | FK faturamento.ItemNFe **null** | Preenchido quando NF-e está no ERP |
| cliente | FK cadastros.Cliente null | Preenchido no lançamento manual |
| numero_nfe | CharField(20) blank | Número da NF-e de exportação |
| numero_re | CharField(20) blank | Registro de Exportação (Siscomex) |
| numero_due | CharField(20) blank | Declaração Única de Exportação |
| data_embarque | DateField | Data efetiva de embarque |
| quantidade | DecimalField | |
| valor_fob_usd | DecimalField null | Valor FOB em dólares |
| **origem** | CharField | `ERP` \| `MANUAL` |
| **retroativo** | BooleanField default=False | True para lançamentos de 2025 |
| anulado | BooleanField default=False | |
| motivo_anulacao | TextField blank | |
| observacoes | TextField blank | |
| registrado_por | FK Usuario | |
| data_registro | auto_now_add | |

**Restrições:**
- `quantidade` ≤ `saldo_exportacao` disponível (comprado − já exportado)
- `data_embarque` ≤ `data_fim_efetiva` do AC

---

## 4. Interface de Usuário

### 4.1 Tela inicial — `/drawback/`

Cards de resumo do AC único:
```
[ Nº AC: 23/000xxx ]  [ Vigência: 15/03/2025 → 15/03/2027 ]  [ ATIVO ]

PRODUTO A           Autorizado: 500t | Comprado: 320t | Saldo: 180t | Exportado: 210t
████████████░░░░    42% cumprido

PRODUTO B           Autorizado: 200t | Comprado: 180t | Saldo: 20t  | Exportado: 150t
███████████████░    75% cumprido
```

Acesso rápido:
- [Lançar Entrada Drawback] [Lançar Saída Drawback]
- [Regularização 2025 — Entradas] [Regularização 2025 — Saídas]
- [Relatório de Comprovação]

---

### 4.2 Detalhe do AC — abas

| Aba | Conteúdo |
|-----|----------|
| **Resumo** | Cards de saldo por produto, barra de progresso, alerta de vencimento |
| **Entradas** | Lista de EntradaDrawback — com badge ERP/MANUAL e flag RETROATIVO |
| **Saídas** | Lista de SaidaDrawback — com badge ERP/MANUAL e flag RETROATIVO |
| **Histórico** | Log de cadastros, anulações, mudanças de status |

---

### 4.3 Formulário de lançamento manual (regularização 2025)

**Entrada (compra histórica da planilha):**
```
AC: [preenchido — único AC]
Produto: [select — produtos autorizados no AC]
Fornecedor: [autocomplete]
Número NF: ___  Série: _  Data NF: ___  Data Recebimento: ___
Quantidade: ___  Valor Unitário: ___
Observação: ___
[Saldo disponível antes: xxx → após: xxx]   ← validação em tempo real
```

**Saída (exportação histórica da planilha):**
```
AC: [preenchido]
Produto: [select]
Cliente: [autocomplete]
NF-e: ___  RE: ___  DUE: ___  Data Embarque: ___
Quantidade: ___  Valor FOB (USD): ___
Observação: ___
[Saldo comprado disponível antes: xxx → após: xxx]
```

---

### 4.4 Integração nas telas existentes do ERP

**Recebimento de Compra** (`compras/recebimento/detail`):
- Se o `ItemRecebimento` **não está** vinculado a drawback → exibir botão "Vincular ao Drawback"
- Abre modal: seleciona produto do AC, confirma quantidade → cria `EntradaDrawback` com `origem=ERP`

**NF-e de Exportação** (`faturamento/nfe/detail`):
- Se NF-e de exportação **não está** vinculada → botão "Vincular ao Drawback"
- Abre modal: produto do AC, RE/DUE, data embarque, qtd, valor FOB → cria `SaidaDrawback` com `origem=ERP`

---

## 5. Relatório de Comprovação

Gerado em **PDF** e **XLSX**, para apresentar ao MDIC ou despachante.

```
═══════════════════════════════════════════════════════════════
  RELATÓRIO DE COMPROVAÇÃO DE EXPORTAÇÃO — DRAWBACK
  [Empresa] | CNPJ: xx.xxx.xxx/0001-xx
  AC: [número] | Tipo: Suspensão | Vigência: dd/mm/aa a dd/mm/aa
  Gerado em: dd/mm/aaaa hh:mm
═══════════════════════════════════════════════════════════════

1. ENTRADAS DE INSUMOS — IMPORTAÇÃO DO EXTERIOR
───────────────────────────────────────────────────────────────
Produto        NCM       NF Entrada  Fornecedor      Recebimento  Qtd      Valor R$
Caixa PP 20kg  39231000  000123      Fornec. LTDA    15/03/2025   1.250 UN R$ 5.625,00
(*) Manta agr. 39269090  000456      Import. XYZ     02/06/2025     800 KG R$ 3.200,00
───────────────────────────────────────────────────────────────
SUBTOTAL IMPORTAÇÃO: [total]

2. ENTRADAS DE INSUMOS — MERCADO INTERNO
───────────────────────────────────────────────────────────────
Produto        NCM       NF Entrada  Fornecedor      Recebimento  Qtd      Valor R$
Cola hot melt  35069900  000789      Cola Sul LTDA   10/04/2025     500 KG R$ 7.500,00
(*) Mulching   39269090  000321      Agro Mat. LTDA  20/05/2025   1.000 KG R$ 4.000,00
───────────────────────────────────────────────────────────────
SUBTOTAL MERCADO INTERNO: [total]

TOTAL GERAL DE ENTRADAS: [total]

3. EXPORTAÇÕES REALIZADAS
───────────────────────────────────────────────────────────────
Produto        NF-e      RE Siscomex      DUE               Embarque    Qtd      FOB USD
Caixa PP 20kg  000999    25BR000123456-7  25BR001234567890  20/05/2025  800 UN   USD 2.400,00
(*) Manta agr. 001100    —                —                 30/06/2025  600 KG   USD 1.800,00
───────────────────────────────────────────────────────────────
TOTAL EXPORTADO: [total]
(*) RE/DUE não informado — lançamento retroativo, atualizar quando disponível

4. RESUMO DE CUMPRIMENTO POR PRODUTO
───────────────────────────────────────────────────────────────
Produto        Autorizado  Comprado  Saldo Compra  Exportado  % Cumprido  Situação
Caixa PP 20kg  2.000 UN    1.250 UN  750 UN        800 UN     40%         ⏳ Em andamento
Cola hot melt  1.000 KG    500 KG    500 KG        500 KG     50%         ⏳ Em andamento
Mulching       2.000 KG    1.000 KG  1.000 KG      600 KG     30%         ⏳ Em andamento
Manta agric.   1.500 KG    800 KG    700 KG        600 KG     40%         ⏳ Em andamento
───────────────────────────────────────────────────────────────
(*) Lançamento retroativo — regularização de período anterior
═══════════════════════════════════════════════════════════════
```

---

## 6. Regras de Negócio

| Cód | Regra |
|-----|-------|
| RN-01 | Lançamentos com `retroativo=True` e `origem=MANUAL` podem ter `data_recebimento` ou `data_embarque` fora da data atual, mas devem estar dentro da vigência do AC |
| RN-02 | `quantidade` (entrada) ≤ `saldo_compra` disponível no AC para o produto |
| RN-03 | `quantidade` (saída) ≤ `saldo_exportacao` (comprado − já exportado) |
| RN-04 | AC só pode ser `ENCERRADO` como cumprido se `quantidade_exportada ≥ quantidade_minima_export` em todos os produtos |
| RN-05 | Alerta 30 dias antes do vencimento (WARNING), 15 dias (DANGER), 5 dias (e-mail) |
| RN-06 | Registros nunca deletados — apenas anulados com `motivo_anulacao` |
| RN-07 | Um `ItemRecebimento` pode ter no máximo **um** `EntradaDrawback` com `origem=ERP` |
| RN-08 | Um `ItemNFe` pode ter no máximo **um** `SaidaDrawback` com `origem=ERP` |

---

## 7. Estrutura Técnica

```
drawback/
├── models.py          ← AtoConcessorio, DrawbackProdutoAC, EntradaDrawback, SaidaDrawback
├── forms.py           ← AtoConcessorioForm, ProdutoACFormSet, EntradaForm, SaidaForm
├── views.py           ← dashboard, detail, entrada_manual, saida_manual, vincular_erp, relatorio
├── urls.py
├── management/
│   └── commands/
│       └── atualizar_status_drawback.py
├── templates/drawback/
│   ├── dashboard.html
│   ├── detail.html
│   ├── form_ac.html
│   ├── entrada_manual.html    ← regularização + novos lançamentos manuais
│   ├── saida_manual.html
│   └── relatorio.html
└── migrations/
    └── 0001_initial.py
```

**Registro em `core/urls.py`:**
```python
path('drawback/', include(('drawback.urls', 'drawback')))
```

**`INSTALLED_APPS`:**
```python
'drawback',
```

---

## 8. Plano de Implementação por Fase

### Fase 1 — Base (prioridade: rodar com a planilha)
- [ ] Criar app `drawback/` e registrar
- [ ] Models: `AtoConcessorio`, `DrawbackProdutoAC`, `EntradaDrawback`, `SaidaDrawback`
- [ ] Migration `0001_initial`
- [ ] Admin para cadastro do AC e produtos
- [ ] Cadastrar o AC único com os produtos autorizados

### Fase 2 — Regularização 2025 (prioridade: eliminar a planilha)
- [ ] Formulário de lançamento manual de entrada (retroativo=True, origem=MANUAL)
- [ ] Formulário de lançamento manual de saída (retroativo=True, origem=MANUAL)
- [ ] Validação de saldo em tempo real (AJAX)
- [ ] **Digitar os dados da planilha de 2025 no sistema**
- [ ] Conferir saldo resultante vs. planilha → devem bater

### Fase 3 — Operação normal
- [ ] Dashboard principal com saldo por produto
- [ ] Detalhe do AC com abas (Entradas, Saídas, Histórico)
- [ ] Botão "Vincular ao Drawback" no detalhe do RecebimentoCompra
- [ ] Botão "Vincular ao Drawback" no detalhe da NF-e de exportação

### Fase 4 — Alertas e relatório
- [ ] Alertas de vencimento no dashboard e sidebar
- [ ] Management command `atualizar_status_drawback`
- [ ] Relatório de comprovação em PDF (WeasyPrint)
- [ ] Exportação XLSX (openpyxl)

---

## 9. Regularização 2025 — Duas formas de entrada

O usuário pode escolher qualquer uma das duas formas para cada lançamento histórico:

### 9.1 Formulário manual (lançamento individual)

Formulário na tela `/drawback/entrada/nova/` e `/drawback/saida/nova/` com os campos descritos na seção 4.3. Adequado para poucos registros ou correções pontuais.

### 9.2 Importação via XLSX (lançamento em lote)

Fluxo:
```
1. Usuário baixa o modelo XLSX  →  /drawback/modelo/entradas.xlsx
                                    /drawback/modelo/saidas.xlsx

2. Preenche o arquivo com os dados da planilha de 2025

3. Acessa /drawback/importar/ → faz upload do XLSX

4. Sistema valida linha a linha (produto existe no AC? saldo ok? data na vigência?)
   → Exibe tabela de preview com status de cada linha: ✓ OK | ✗ ERRO

5. Usuário confirma → importa apenas as linhas válidas
   → Linhas com erro ficam destacadas com mensagem e podem ser corrigidas manualmente
```

---

## 10. Modelos de Planilha XLSX

### 10.1 Modelo — Entradas Drawback (`modelo_entradas_drawback.xlsx`)

**Visual do template:**
- Cabeçalho: fundo **roxo** (`#7c3aed`) + texto branco + negrito (cor primária do sistema)
- Colunas obrigatórias: fundo **amarelo claro** `#FFF9C4`
- Colunas opcionais: fundo **branco** `#FFFFFF`
- Linha de exemplo pré-preenchida com dados fictícios (cor cinza claro)
- Largura das colunas ajustada automaticamente

Aba: **"Entradas"**

| Col | Campo | Obrigatório | Formato | Exemplo |
|-----|-------|-------------|---------|---------|
| A | Tipo de Compra | **Sim** | `IMPORTACAO` ou `MERCADO_INTERNO` | `MERCADO_INTERNO` |
| B | Fornecedor (CNPJ ou Nome) | **Sim** | Texto ou 14 dígitos | `12.345.678/0001-90` |
| C | Número da NF | **Sim** | Texto | `000123` |
| D | Série da NF | Não | Texto | `1` |
| E | Data da NF | **Sim** | DD/MM/AAAA | `15/03/2025` |
| F | Data do Recebimento | **Sim** | DD/MM/AAAA | `17/03/2025` |
| G | Produto | **Sim** | Conforme lista aba Produtos | `Caixa de papelão 20kg` |
| H | Quantidade | **Sim** | Número decimal | `1250.500` |
| I | Unidade de Medida | **Sim** | Conforme lista aba Produtos | `UN` |
| J | Valor Unitário (R$) | Não | Número decimal | `4.50` |
| K | Observação | Não | Texto | `Lote fornecedor X` |

Aba: **"Produtos do AC"** (gerada automaticamente ao baixar)
- Lista exata dos produtos autorizados no AC com código, nome e unidade de medida
- Usuário consulta aqui para preencher a coluna G corretamente

Aba: **"Instruções"**
- Passo a passo de preenchimento
- Tabela de tipos de compra aceitos: `IMPORTACAO` / `MERCADO_INTERNO`
- Alerta: não alterar o nome das colunas
- Como salvar e enviar o arquivo

---

### 10.2 Modelo — Saídas Drawback (`modelo_saidas_drawback.xlsx`)

**Visual do template:** mesma paleta (cabeçalho roxo, obrigatórias amarelas, opcionais brancas).

Aba: **"Saídas"**

| Col | Campo | Obrigatório | Formato | Exemplo |
|-----|-------|-------------|---------|---------|
| A | Cliente (Nome ou CNPJ) | Não | Texto | `ACME CORP` |
| B | Número da NF-e / Invoice | Não | Texto | `000456` |
| C | RE (Registro de Exportação) | Não* | Texto | `25BR000123456-7` |
| D | DUE (Declaração Única de Exportação) | Não* | Texto | `25BR0012345678901` |
| E | Data de Embarque | **Sim** | DD/MM/AAAA | `20/05/2025` |
| F | Produto | **Sim** | Conforme lista aba Produtos | `Caixa de papelão 20kg` |
| G | Quantidade | **Sim** | Número decimal | `1200.000` |
| H | Unidade de Medida | **Sim** | Conforme lista aba Produtos | `UN` |
| I | Valor FOB (USD) | Não | Número decimal | `3600.00` |
| J | Observação | Não | Texto | `Embarque Santos` |

> **(*) RE e DUE:** Para os lançamentos retroativos de 2025, pode deixar em branco se não tiver o documento em mãos. O sistema permite completar depois editando o registro individualmente. Para novos lançamentos (2026 em diante), recomendado preencher pelo menos um dos dois para comprovação junto ao MDIC.

---

## 11. Lógica de Validação na Importação XLSX

Para cada linha do arquivo, o sistema valida na seguinte ordem:

```
ENTRADAS:
  1. Produto existe no AC? → produto cadastrado em DrawbackProdutoAC
  2. Fornecedor existe no ERP? → se não encontrado, cria aviso (não bloqueia)
  3. Data do recebimento está dentro da vigência do AC?
  4. Quantidade > 0?
  5. Saldo acumulado até esta linha ≤ saldo_compra disponível no AC?
     (valida em ordem de data — linha por linha acumulando)

SAÍDAS:
  1. Produto existe no AC?
  2. Data de embarque dentro da vigência do AC?
  3. Quantidade > 0?
  4. Saldo acumulado de saídas até esta linha ≤ saldo disponível para exportar?
     (comprado − já exportado − exportações anteriores desta importação)
```

**Resultado do preview:**

| # | Produto | Data | Qtd | Saldo Antes | Saldo Após | Status |
|---|---------|------|-----|-------------|------------|--------|
| 1 | Embalagem PP | 15/03/2025 | 500 kg | 1.000 kg | 500 kg | ✓ OK |
| 2 | Embalagem PP | 22/04/2025 | 600 kg | 500 kg | -100 kg | ✗ Saldo insuficiente |
| 3 | Fio Aço | 10/05/2025 | 200 kg | 800 kg | 600 kg | ✓ OK |

O usuário pode:
- **Importar apenas as linhas válidas** (ignorar erros)
- **Cancelar tudo** e corrigir o arquivo
- **Corrigir a linha** diretamente no campo de quantidade antes de confirmar

---

## 12. Estrutura Técnica

```
drawback/
├── models.py
├── forms.py
├── views.py
│   ├── dashboard()
│   ├── detalhe_ac()
│   ├── form_ac()
│   ├── entrada_manual()          ← lançamento individual
│   ├── saida_manual()
│   ├── importar_xlsx()           ← upload + preview + confirmação
│   ├── download_modelo_xlsx()    ← gera XLSX template dinamicamente
│   └── relatorio()
├── importacao.py                 ← lógica de leitura e validação do XLSX (openpyxl)
├── urls.py
├── management/commands/
│   └── atualizar_status_drawback.py
├── templates/drawback/
│   ├── dashboard.html
│   ├── detail.html
│   ├── form_ac.html
│   ├── entrada_manual.html
│   ├── saida_manual.html
│   ├── importar_xlsx.html        ← upload form + tabela de preview
│   └── relatorio.html
└── migrations/
    └── 0001_initial.py
```

**Dependências Python adicionais necessárias:**
- `openpyxl` — leitura e geração de XLSX (já provavelmente instalado)
- `weasyprint` — geração de PDF do relatório (verificar se já instalado)

**Registro em `core/urls.py`:**
```python
path('drawback/', include(('drawback.urls', 'drawback')))
```

---

## 13. Plano de Implementação por Fase

### Fase 1 — Base de dados (1 dia)
- [ ] Criar app `drawback/` e registrar em `INSTALLED_APPS` e `core/urls.py`
- [ ] Models: `AtoConcessorio`, `DrawbackProdutoAC`, `EntradaDrawback`, `SaidaDrawback`
- [ ] Migration `0001_initial`
- [ ] Admin básico
- [ ] **Cadastrar o AC e produtos autorizados no admin**

### Fase 2 — Regularização 2025 (2 dias — prioridade: eliminar a planilha)
- [ ] Formulário manual de entrada (retroativo=True, origem=MANUAL)
- [ ] Formulário manual de saída
- [ ] `download_modelo_xlsx()` — gera template XLSX com aba de instruções e lista de produtos
- [ ] `importar_xlsx()` — upload, validação linha a linha, preview, confirmação
- [ ] `importacao.py` — engine de validação e importação
- [ ] **Importar dados da planilha de 2025 e conferir saldo**

### Fase 3 — Operação normal (1,5 dia)
- [ ] Dashboard principal com cards de saldo por produto
- [ ] Detalhe do AC com abas (Entradas, Saídas, Histórico)
- [ ] Botão "Vincular ao Drawback" no `RecebimentoCompra` (origem=ERP)
- [ ] Botão "Vincular ao Drawback" na NF-e de exportação (origem=ERP)

### Fase 4 — Alertas e relatório (1 dia)
- [ ] Alertas de vencimento no dashboard e no sidebar (`base.html`)
- [ ] Management command `atualizar_status_drawback`
- [ ] Relatório de comprovação PDF (WeasyPrint)
- [ ] Exportação XLSX do relatório (openpyxl)

**Total estimado: ~5,5 dias de desenvolvimento**

---

## 14. Decisões de Projeto Confirmadas

| Questão | Decisão |
|---------|---------|
| Produto no AC | **Insumo** (embalagem, cola, Mulching, Manta, etc.) — não o produto final exportado |
| Origem dos insumos | **Importação + Mercado Interno** — campo `tipo_compra` distingue os dois |
| Documentos de exportação históricos | **Apenas NF-e** disponível para 2025 — RE/DUE opcionais, completar quando disponível |
| Novos lançamentos | RE/DUE recomendado para comprovação junto ao MDIC |
| Template XLSX | **Colorido e amigável** — cabeçalho roxo, obrigatórias amarelas, linha de exemplo |

---

## 15. Glossário

| Termo | Significado |
|-------|-------------|
| AC | Ato Concessório — autorização emitida pelo MDIC para operação em regime de drawback |
| MDIC | Ministério do Desenvolvimento, Indústria, Comércio e Serviços |
| DUE | Declaração Única de Exportação — substitui o DSE no Siscomex |
| RE | Registro de Exportação no Siscomex |
| II | Imposto de Importação |
| IPI | Imposto sobre Produtos Industrializados |
| PIS/COFINS | Contribuições sociais suspensas no drawback suspensão |
| FOB | Free On Board — valor da mercadoria no porto de embarque (sem frete) |
| NCM | Nomenclatura Comum do Mercosul — código de classificação fiscal do produto |
| Retroativo | Vínculo lançado após o fato, para regularização de período anterior (2025) |
| Mercado Interno | Insumo adquirido de fornecedor nacional (sem importação) incluído no AC |
| Importação | Insumo adquirido do exterior com suspensão de II/IPI/PIS/COFINS |
| Siscomex | Sistema Integrado de Comércio Exterior — onde RE e DUE são registrados |
