# Especificação Técnica e Funcional
## Faturamento Agrupado com Lógica Invertida
### ERP Agrícola — Módulo `faturamento/`

**Versão:** 1.0 | **Data:** 2026-06-29 | **Autor:** Análise Sistêmica

---

## 1. REGRAS DE NEGÓCIO E FLUXO FISCAL

### 1.1 Visão Geral do Fluxo

```
PEDIDO DE VENDA
      │
      ▼
┌─────────────────────────────────────────────────────────────────┐
│  FASE 1 — REMESSA (N ocorrências, conforme saídas reais)        │
│                                                                 │
│  NF-e Filha #1  ──→  CFOP 5.922 / 6.922  ──→  Autorizada SEFAZ│
│  NF-e Filha #2  ──→  CFOP 5.922 / 6.922  ──→  Autorizada SEFAZ│
│  NF-e Filha #N  ──→  CFOP 5.922 / 6.922  ──→  Autorizada SEFAZ│
│                                                                 │
│  → Cada autorização baixa estoque físico (saída real do        │
│    armazém) e entra no pool "pendente de faturamento"          │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  FASE 2 — FATURAMENTO (1 ocorrência ao final do período)        │
│                                                                 │
│  NF-e Mãe  ──→  CFOP 5.116 / 5.117 / 6.116 / 6.117           │
│                  Referencia chaves de acesso de todas as filhas │
│                  Valor total = Σ(valores das filhas)            │
│                  NÃO movimenta estoque                          │
│            ──→  Autorizada SEFAZ                               │
│                                                                 │
│  → Filhas marcadas como "faturadas" (vinculadas à Mãe)         │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Notas Filhas — Fluxo de Remessa

| Atributo | Valor |
|---|---|
| **Finalidade NF-e** | `1` — NF-e Normal |
| **CFOP Operação Interna** | `5.922` (Remessa para armazenagem) ou `5.949` (Outra remessa) |
| **CFOP Operação Interestadual** | `6.922` ou `6.949` |
| **Natureza da Operação** | `REMESSA PARA POSTERIOR FATURAMENTO` |
| **`tipo_operacao`** | `REMESSA` (novo campo no modelo) |
| **`status_faturamento`** | `PENDENTE` → `FATURADA` (novo campo) |

**Regras obrigatórias:**

1. O campo `cliente` deve ser obrigatório para notas de remessa (sem cliente não há agrupamento possível).
2. Ao ser **autorizada pela SEFAZ** (status `AUTORIZADA` + `chave_acesso` preenchida), a nota entra automaticamente no pool de remessas pendentes de faturamento.
3. Uma nota filha cancelada deve ser **removida do pool** e NÃO pode ser vinculada a nenhuma nota mãe.
4. Uma nota filha já faturada (`status_faturamento = FATURADA`) deve ser bloqueada para cancelamento — exige estorno da nota mãe primeiro.

### 1.3 Nota Mãe — Fluxo de Faturamento

| Atributo | Valor |
|---|---|
| **Finalidade NF-e** | `1` — NF-e Normal |
| **CFOP Operação Interna** | `5.116` (venda de produção própria) ou `5.117` (venda de mercadoria adquirida) |
| **CFOP Operação Interestadual** | `6.116` ou `6.117` |
| **Natureza da Operação** | `FATURAMENTO DE REMESSAS ANTERIORES` |
| **`tipo_operacao`** | `FATURAMENTO` (novo campo) |
| **Referência NF-e** | Grupo `<NFref>` com todas as chaves de acesso das filhas |

**Regras obrigatórias:**

1. A Nota Mãe deve ser criada **exclusivamente pelo processo de fechamento** (tela B) — nunca manualmente.
2. O campo `<infNFe><infAdic><infCpl>` (informações complementares) deve conter a lista de notas referenciadas no formato: `NF-e de Faturamento referente às remessas: NF 000001 (Chave: ...44 dígitos...), NF 000002 (Chave: ...44 dígitos...)`.
3. Os **itens** da Nota Mãe devem ser a consolidação dos itens das filhas agrupados por produto, somando as quantidades.
4. Todos os tributos (ICMS, PIS, COFINS, IPI) devem ser recalculados sobre os totais consolidados.
5. A data de emissão da Nota Mãe é sempre a data do fechamento, independente das datas das notas filhas.

### 1.4 Seleção de CFOP — Regra Decisória

```
Nota Filha (Remessa):
  ├── Destinatário no mesmo estado → 5.922 (armazenagem) ou 5.949 (outras)
  └── Destinatário em outro estado → 6.922 ou 6.949

Nota Mãe (Faturamento):
  ├── Produto de PRODUÇÃO PRÓPRIA
  │     ├── Mesmo estado → 5.116
  │     └── Outro estado → 6.116
  └── Produto ADQUIRIDO/REVENDIDO
        ├── Mesmo estado → 5.117
        └── Outro estado → 6.117
```

O sistema deve inferir o CFOP automaticamente com base no estado do destinatário vs. emitente e no tipo de produto, mas permitir override manual com validação.

---

## 2. REGRAS DE ESTOQUE — MOVIMENTAÇÃO DO INVENTÁRIO

### 2.1 Princípio Central

> **A baixa física ocorre UMA ÚNICA VEZ: no momento da autorização da Nota Filha (Remessa).**
> A Nota Mãe é exclusivamente fiscal/financeira e NÃO toca o inventário.

### 2.2 Gatilho de Baixa Física — Nota Filha

A baixa de estoque deve ser disparada pelo signal/hook de autorização da NF-e, dentro de uma transação atômica:

```python
# Ponto de integração: faturamento/services/integranotas.py
# Evento: retorno de autorização da SEFAZ (status "100 - Autorizado o uso da NF-e")

@transaction.atomic
def processar_autorizacao_remessa(nota_filha: NotaFiscal) -> None:
    """
    Chamado quando nota do tipo REMESSA recebe chave_acesso + protocolo.
    Cria uma MovimentacaoEstoque de SAÍDA para cada ItemNotaFiscal.
    """
    if nota_filha.tipo_operacao != 'REMESSA':
        return

    for item in nota_filha.itens.select_related('produto', 'lote'):
        MovimentacaoEstoque.objects.create(
            empresa=nota_filha.empresa,
            produto=item.produto,
            lote=item.lote,            # se controlado por lote
            tipo='SAIDA',
            origem='REMESSA_FATURAMENTO',   # novo choice a adicionar
            quantidade=item.quantidade,
            armazem_origem=item.armazem,   # armazém de onde saiu
            documento_origem=f'NF-e {nota_filha.numero}/{nota_filha.serie}',
            chave_nfe=nota_filha.chave_acesso,
            observacao=f'Remessa para posterior faturamento — Cliente: {nota_filha.cliente}',
            criado_por=nota_filha.criado_por,
        )

    nota_filha.status_faturamento = 'PENDENTE'
    nota_filha.save(update_fields=['status_faturamento'])
```

**Novo `ORIGEM_CHOICES` a adicionar em `estoque/models.py`:**

```python
('REMESSA_FATURAMENTO', 'Remessa para Faturamento Posterior'),
```

### 2.3 Bloqueio de Movimentação — Nota Mãe

A camada de serviço deve impedir ativamente qualquer movimentação de estoque ao processar a Nota Mãe:

```python
@transaction.atomic
def processar_autorizacao_faturamento(nota_mae: NotaFiscal) -> None:
    """
    Chamado quando nota do tipo FATURAMENTO recebe autorização SEFAZ.
    Apenas atualiza status das filhas — NUNCA movimenta estoque.
    """
    if nota_mae.tipo_operacao != 'FATURAMENTO':
        return

    # Marca todas as filhas como faturadas
    nota_mae.notas_filhas.update(
        status_faturamento='FATURADA',
        nota_mae=nota_mae,
    )
    # Registra no financeiro (contas a receber) — ver integração financeiro/
    _criar_lancamento_financeiro(nota_mae)
```

### 2.4 Diagrama de Estados — Nota Filha

```
RASCUNHO
   │  (usuário emite)
   ▼
EMITIDA (transmitida à SEFAZ, aguarda retorno)
   │  (SEFAZ autoriza → baixa estoque)
   ▼
AUTORIZADA ──→ status_faturamento = PENDENTE
   │
   ├─── (incluída em fechamento e NF Mãe autorizada)
   │         ▼
   │    status_faturamento = FATURADA  [estado terminal]
   │
   └─── (cancelamento — somente se status_faturamento = PENDENTE)
              ▼
         CANCELADA ──→ Estorno de MovimentacaoEstoque (entrada de devolução)
```

### 2.5 Estorno no Cancelamento de Nota Filha

Se uma nota filha autorizada (mas ainda `PENDENTE`) for cancelada, o sistema deve gerar um estorno de entrada de estoque:

```python
# origem = 'CANCELAMENTO_REMESSA'  (novo choice)
# tipo   = 'ENTRADA'
# quantidade = soma dos itens cancelados
```

---

## 3. REQUISITOS DE INTERFACE E TELAS (UI/UX)

### 3.1 Tela A — Dashboard de Remessas Pendentes de Faturamento

**URL sugerida:** `/faturamento/remessas-pendentes/`
**Nome de URL:** `faturamento:remessas_pendentes`

#### 3.1.1 Layout Geral

```
┌──────────────────────────────────────────────────────────────────────┐
│  NAVBAR (base.html)                                                  │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Remessas Pendentes de Faturamento        [+ Nova Remessa]           │
│  ─────────────────────────────────────────────────────               │
│                                                                      │
│  ┌── PAINEL DE FILTROS ──────────────────────────────────────────┐   │
│  │  [Cliente ▼]  [Período: De __/__/__  Até __/__/__]  [Buscar]  │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌── RESUMO DO AGRUPAMENTO (aparece quando há seleção) ──────────┐   │
│  │  ✓ 3 notas selecionadas   Total: R$ 48.750,00   [Fechar Lote]│   │
│  └───────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌── TABELA DE REMESSAS ─────────────────────────────────────────┐   │
│  │  [☐]  NF#   Data     Cliente          Valor       Status      │   │
│  │  [☐]  001   01/06    Fazenda Alfa     R$ 12.500   Pendente    │   │
│  │  [☐]  002   05/06    Fazenda Alfa     R$ 18.250   Pendente    │   │
│  │  [☐]  003   12/06    Fazenda Alfa     R$ 18.000   Pendente    │   │
│  │  [☐]  004   15/06    Fazenda Beta     R$ 9.300    Pendente    │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  [☐ Selecionar todas visíveis]            Total geral: R$ 58.050    │
└──────────────────────────────────────────────────────────────────────┘
```

#### 3.1.2 Componentes e Comportamentos

**Filtros:**

| Campo | Tipo | Comportamento |
|---|---|---|
| `cliente` | `<select>` com Select2 (autocomplete) | Filtra a tabela via GET; obrigatório antes de exibir checkboxes |
| `data_de` | `<input type="date">` | Filtra `data_emissao >= data_de` |
| `data_ate` | `<input type="date">` | Filtra `data_emissao <= data_ate`; default = hoje |
| `[Buscar]` | `<button>` submit | Recarrega a página com parâmetros GET |

**Restrição crítica:** os checkboxes só ficam ativos quando **um único cliente** está selecionado no filtro. Notas de clientes diferentes não podem ser agrupadas na mesma Nota Mãe. Exibir aviso inline: _"Selecione um cliente para habilitar o agrupamento."_

**Tabela:**

| Coluna | Fonte | Observação |
|---|---|---|
| `☐` | checkbox HTML | `name="notas_ids" value="{{ nota.pk }}"` |
| `NF #` | `nota.numero` | Link para detail da nota |
| `Data` | `nota.data_emissao` | Formatado `dd/mm/yyyy` |
| `Cliente` | `nota.cliente` | Exibido mesmo com filtro ativo |
| `Valor` | `nota.valor_total` | Formatado BRL |
| `CFOP` | `nota.cfop` | Badge cinza |
| `Status` | `nota.status_faturamento` | Badge `warning` = Pendente |
| `Chave` | `nota.chave_acesso[:8]…` | Tooltip com chave completa ao hover |

**Barra de resumo (sticky bottom, aparece com ≥ 1 seleção):**

```html
<!-- Renderizada via JS ao marcar checkboxes -->
<div class="position-sticky bottom-0 bg-white border-top shadow p-3">
  <div class="d-flex align-items-center justify-content-between">
    <span class="fw-semibold">
      <span id="qtd-selecionadas">0</span> nota(s) selecionada(s) —
      Total: <strong id="total-selecionado">R$ 0,00</strong>
    </span>
    <button type="submit" form="form-agrupamento"
            class="btn btn-primary"
            id="btn-fechar-lote" disabled>
      <i class="bi bi-check2-circle me-1"></i> Fechar Lote de Faturamento
    </button>
  </div>
</div>
```

**JavaScript necessário (`remessas_pendentes.js`):**

- Listener `change` nos checkboxes: acumula `valor_total` e `pk` das notas selecionadas.
- Atualiza `#qtd-selecionadas` e `#total-selecionado` em tempo real.
- Habilita `#btn-fechar-lote` somente quando `selecionadas.length >= 1`.
- Bloqueia seleção mista de clientes com alerta `alert()` ou `toast`.
- O formulário `form-agrupamento` envia `POST` para `/faturamento/fechar-lote/` com a lista de IDs.

---

### 3.2 Tela B — Fechamento / Prévia da Nota Mãe

**URL sugerida:** `/faturamento/fechar-lote/`
**Nome de URL:** `faturamento:fechar_lote`
**Método de entrada:** POST (recebe `notas_ids[]` da Tela A), renderiza como GET com dados na sessão ou query.

#### 3.2.1 Layout Geral

```
┌──────────────────────────────────────────────────────────────────────┐
│  ← Voltar    Fechamento de Lote — Prévia da Nota Fiscal Mãe         │
│  ────────────────────────────────────────────────────────────        │
│                                                                      │
│  ┌── CABEÇALHO DO FATURAMENTO ─────────────────────────────────┐    │
│  │  Cliente: Fazenda Alfa Ltda  (CNPJ 00.000.000/0001-00)      │    │
│  │  Período das remessas: 01/06/2026 a 12/06/2026              │    │
│  │  Data de emissão da NF Mãe: [  29/06/2026  ] (editável)    │    │
│  │  CFOP sugerido: [5.116 ▼]   Natureza: FATURAMENTO REMESSAS │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  ┌── NOTAS REFERENCIADAS (somente leitura) ────────────────────┐    │
│  │  NF#  Data       Valor          Chave de Acesso             │    │
│  │  001  01/06/26   R$ 12.500,00   3526 0600 0000 ... 0001     │    │
│  │  002  05/06/26   R$ 18.250,00   3526 0600 0000 ... 0002     │    │
│  │  003  12/06/26   R$ 18.000,00   3526 0600 0000 ... 0003     │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  ┌── ITENS CONSOLIDADOS (somente leitura) ─────────────────────┐    │
│  │  Produto          Qtd Total   Un   Valor Unit.  Subtotal     │    │
│  │  Soja grão        150,00      SC   R$ 320,00    R$ 48.000   │    │
│  │  Milho grão        18,00      SC   R$  41,67    R$    750   │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  ┌── TOTAIS (somente leitura) ─────────────────────────────────┐    │
│  │  Valor Produtos    R$ 48.750,00   [calculado das filhas]     │    │
│  │  Valor Desconto    R$      0,00                              │    │
│  │  Valor Total       R$ 48.750,00  ← NÃO EDITÁVEL             │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  ┌── INFORMAÇÕES ADICIONAIS (editável) ────────────────────────┐    │
│  │  Obs. Complementares: [textarea — pré-preenchido com lista  │    │
│  │                        de NFs referenciadas]                 │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  [← Voltar e Reeditar]          [✓ Gerar Nota Fiscal Mãe]           │
└──────────────────────────────────────────────────────────────────────┘
```

#### 3.2.2 Componentes e Comportamentos

**Campos editáveis:**

| Campo | Editável | Observação |
|---|---|---|
| `data_emissao` | **Sim** | Default = hoje |
| `cfop` | **Sim** | Select com opções válidas (5.116, 5.117, 6.116, 6.117) |
| `natureza_operacao` | **Sim** | Pré-preenchida |
| `informacoes_complementares` | **Sim** | Pré-preenchida automaticamente |
| `valor_total`, `valor_produtos` | **Não** | Exibidos como texto, sem `<input>` |
| Itens consolidados | **Não** | Gerados pelo sistema |
| Notas referenciadas | **Não** | Apenas exibição com ícone de lock |

**Pré-preenchimento das Informações Complementares:**

```python
def gerar_infcpl_faturamento(notas_filhas):
    linhas = [f"NF {n.numero:06d} em {n.data_emissao:%d/%m/%Y} "
              f"(Chave: {n.chave_acesso})"
              for n in notas_filhas]
    return ("NF-e de Faturamento referente às remessas anteriores:\n" +
            "\n".join(linhas))
```

**Botão "Gerar Nota Fiscal Mãe":**
- Faz POST para `/faturamento/gerar-nota-mae/`
- Exibe spinner de loading durante processamento (a emissão pode levar alguns segundos)
- Em caso de sucesso: redireciona para a tela de detalhe da Nota Mãe gerada
- Em caso de erro da SEFAZ: exibe mensagem de erro com código e descrição sem perder os dados

---

## 4. VALIDAÇÕES E TRAVAS DE SEGURANÇA

### 4.1 Novos Campos no Modelo `NotaFiscal`

```python
# faturamento/models.py — adicionar à classe NotaFiscal

TIPO_OPERACAO_CHOICES = [
    ('VENDA',        'Venda Direta'),
    ('REMESSA',      'Remessa para Faturamento Posterior'),
    ('FATURAMENTO',  'Faturamento de Remessas Anteriores'),
    ('DEVOLUCAO',    'Devolução'),
    ('COMPLEMENTAR', 'Complementar'),
]

STATUS_FATURAMENTO_CHOICES = [
    ('NAO_APLICA', 'Não se aplica'),
    ('PENDENTE',   'Aguardando Faturamento'),
    ('FATURADA',   'Faturada'),
]

tipo_operacao = models.CharField(
    'Tipo de Operação',
    max_length=20,
    choices=TIPO_OPERACAO_CHOICES,
    default='VENDA',
    db_index=True,
)
status_faturamento = models.CharField(
    'Status do Faturamento',
    max_length=20,
    choices=STATUS_FATURAMENTO_CHOICES,
    default='NAO_APLICA',
    db_index=True,
)
nota_mae = models.ForeignKey(
    'self',
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='notas_filhas',
    verbose_name='Nota Mãe (Faturamento)',
    help_text='Preenchido automaticamente ao fechar o lote de faturamento.',
)
```

### 4.2 Modelo de Referências Múltiplas — `NFeReferenciada`

O campo `chave_nfe_referenciada` existente suporta apenas **uma** referência (44 chars). Para a Nota Mãe, que pode referenciar N filhas, é necessário um modelo separado:

```python
class NFeReferenciada(models.Model):
    """
    Referências de NF-e no grupo <NFref> da NF-e.
    Suporta tanto o caso de devolução (uma referência) quanto
    o faturamento agrupado (N referências).
    """
    nota_fiscal = models.ForeignKey(
        NotaFiscal,
        on_delete=models.CASCADE,
        related_name='nfes_referenciadas',
        verbose_name='Nota Fiscal',
    )
    chave_acesso_referenciada = models.CharField(
        'Chave de Acesso Referenciada',
        max_length=44,
    )
    numero_referenciado = models.PositiveIntegerField(
        'Número NF Referenciada', null=True, blank=True
    )
    data_emissao_referenciada = models.DateField(
        'Data Emissão Referenciada', null=True, blank=True
    )

    class Meta:
        verbose_name = 'NF-e Referenciada'
        unique_together = [('nota_fiscal', 'chave_acesso_referenciada')]
        indexes = [
            models.Index(fields=['chave_acesso_referenciada'],
                         name='idx_nfe_ref_chave'),
        ]

    def clean(self):
        if len(self.chave_acesso_referenciada) != 44:
            raise ValidationError(
                'A chave de acesso referenciada deve ter exatamente 44 dígitos.'
            )
```

### 4.3 Trava: Nota Filha em Apenas Uma Nota Mãe

**Constraint de banco de dados** — cria unicidade no FK:

```python
# Na migration correspondente:
class Migration(migrations.Migration):
    operations = [
        migrations.AddConstraint(
            model_name='notafiscal',
            constraint=models.UniqueConstraint(
                fields=['nota_mae'],
                condition=models.Q(nota_mae__isnull=False),
                name='uniq_nota_filha_por_mae',
            ),
        ),
    ]
```

> **ATENÇÃO:** a constraint acima protege uma nota filha individual, mas a validação semântica (impedir que o mesmo PK apareça em dois fechamentos) deve ser reforçada na camada de serviço:

```python
# faturamento/services/faturamento_agrupado.py

def validar_notas_para_fechamento(notas_ids: list[int], empresa) -> QuerySet:
    notas = NotaFiscal.objects.filter(
        pk__in=notas_ids,
        empresa=empresa,
        tipo_operacao='REMESSA',
        status='EMITIDA',        # ou AUTORIZADA — depende do status final pós-SEFAZ
        status_faturamento='PENDENTE',
        nota_mae__isnull=True,   # garante que não está vinculada a nenhuma mãe
    )

    if notas.count() != len(notas_ids):
        pks_invalidos = set(notas_ids) - set(notas.values_list('pk', flat=True))
        raise ValidationError(
            f"As seguintes notas não estão disponíveis para faturamento: {pks_invalidos}. "
            "Verifique se já foram faturadas ou se pertencem a outro lote."
        )

    clientes = notas.values_list('cliente_id', flat=True).distinct()
    if clientes.count() > 1:
        raise ValidationError(
            "Todas as notas do lote devem pertencer ao mesmo cliente."
        )

    return notas
```

### 4.4 Trava: Imutabilidade de Valores na Tela de Fechamento

**Camada de view** — o form de fechamento deve ignorar quaisquer valores de totais submetidos pelo cliente e sempre recomputar do banco:

```python
# faturamento/views.py — view fechar_lote (POST final)

@login_required
@transaction.atomic
def gerar_nota_mae(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    notas_ids = request.POST.getlist('notas_ids')
    empresa   = request.user.empresa

    try:
        notas = validar_notas_para_fechamento(notas_ids, empresa)
    except ValidationError as e:
        messages.error(request, str(e))
        return redirect('faturamento:remessas_pendentes')

    # Valores SEMPRE calculados do banco — nunca do POST
    valor_total = notas.aggregate(t=Sum('valor_total'))['t'] or Decimal('0')

    # Aqui segue a criação da nota mãe com os valores computados...
```

**Camada de template** — os campos de total nunca são `<input>`, sempre `<span>` ou `<p>`:

```html
<!-- CORRETO — valor renderizado, não submetido -->
<p class="fw-bold fs-5 text-end">
  R$ {{ valor_total|floatformat:2 }}
  <small class="text-muted d-block" style="font-size:.75rem">
    <i class="bi bi-lock-fill"></i> Calculado automaticamente das remessas
  </small>
</p>

<!-- ERRADO — nunca fazer isso para totais -->
<!-- <input type="number" name="valor_total" value="{{ valor_total }}"> -->
```

### 4.5 Trava: Cancelamento Bloqueado para Filha Faturada

```python
# faturamento/models.py — método clean() em NotaFiscal

def clean(self):
    if self.pk:  # apenas em updates
        original = NotaFiscal.objects.get(pk=self.pk)
        if (original.status_faturamento == 'FATURADA'
                and self.status == 'CANCELADA'):
            raise ValidationError(
                "Esta nota de remessa já foi faturada na NF-e Mãe "
                f"#{self.nota_mae.numero}. "
                "Para cancelá-la, primeiro cancele ou estorne a Nota Mãe."
            )
```

### 4.6 Índices de Performance

Adicionar na migration:

```python
migrations.AddIndex(
    model_name='notafiscal',
    index=models.Index(
        fields=['empresa', 'tipo_operacao', 'status_faturamento'],
        name='idx_nf_remessa_pendente',
    ),
),
migrations.AddIndex(
    model_name='notafiscal',
    index=models.Index(
        fields=['empresa', 'cliente', 'status_faturamento'],
        name='idx_nf_cliente_faturamento',
    ),
),
```

---

## 5. RESUMO DE IMPACTO — ARQUIVOS A CRIAR/ALTERAR

| Arquivo | Ação | Descrição |
|---|---|---|
| `faturamento/models.py` | Alterar | Adicionar `tipo_operacao`, `status_faturamento`, `nota_mae` FK e modelo `NFeReferenciada` |
| `faturamento/migrations/0051_*.py` | Criar | Migration dos novos campos e índices |
| `faturamento/services/faturamento_agrupado.py` | Criar | `validar_notas_para_fechamento()`, `gerar_nota_mae()`, `processar_autorizacao_remessa()` |
| `faturamento/views.py` | Alterar | Views `remessas_pendentes`, `fechar_lote_preview`, `gerar_nota_mae` |
| `faturamento/urls.py` | Alterar | 3 novas rotas |
| `faturamento/forms.py` | Alterar | `FechamentoLoteForm` (apenas campos editáveis) |
| `estoque/models.py` | Alterar | Adicionar choices `REMESSA_FATURAMENTO` e `CANCELAMENTO_REMESSA` |
| `templates/faturamento/remessas_pendentes.html` | Criar | Tela A |
| `templates/faturamento/fechar_lote_preview.html` | Criar | Tela B |
| `static/js/remessas_pendentes.js` | Criar | Lógica de seleção e totalização da Tela A |
| `faturamento/services/integranotas.py` | Alterar | Hook de autorização para disparar baixa de estoque na remessa |

---

> **Nota de implementação:** o campo `chave_nfe_referenciada` existente em `NotaFiscal` (44 chars) deve ser mantido para compatibilidade com o fluxo de devolução de compra já existente. O novo modelo `NFeReferenciada` é **adicional** e específico para o faturamento agrupado.
