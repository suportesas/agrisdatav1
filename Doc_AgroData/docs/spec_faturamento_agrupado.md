


markdown# Especificação Técnica e Funcional
## Faturamento Agrupado com Lógica Invertida
### Agrisdata — Módulo faturamento/

*Versão:* 1.1 | *Data:* 2026-06-29 | *Autor:* Análise Sistêmica & Consultoria Fiscal

---

## 1. REGRAS DE NEGÓCIO E FLUXO FISCAL

### 1.1 Visão Geral do Fluxo

```text
PEDIDO DE VENDA
      │
      ▼
┌─────────────────────────────────────────────────────────────────┐
│  FASE 1 — REMESSA (N ocorrências, conforme saídas reais)        │
│                                                                 │
│  NF-e Filha #1  ──→  CFOP 5.949 / 6.949  ──→  Autorizada SEFAZ  │
│  NF-e Filha #2  ──→  CFOP 5.949 / 6.949  ──→  Autorizada SEFAZ  │
│  NF-e Filha #N  ──→  CFOP 5.949 / 6.949  ──→  Autorizada SEFAZ  │
│                                                                 │
│  → Cada autorização baixa estoque físico (saída real do         │
│    armazém) e entra no pool "pendente de faturamento"          │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  FASE 2 — FATURAMENTO (1 ocorrência ao final do período)        │
│                                                                 │
│  NF-e Mãe  ──→  CFOP 5.116 / 5.117 / 6.116 / 6.117              │
│                  Referencia chaves de acesso de todas as filhas │
│                  Valor total = Σ(valores das filhas)            │
│                  NÃO movimenta estoque                          │
│            ──→  Autorizada SEFAZ                                │
│                                                                 │
│  → Filhas marcadas como "faturadas" (vinculadas à Mãe)          │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Notas Filhas — Fluxo de Remessa

| Atributo | Valor |
|---|---|
| *Finalidade NF-e* | 1 — NF-e Normal |
| *CFOP Operação Interna* | 5.949 (Outra saída de mercadoria não especificada) |
| *CFOP Operação Interestadual* | 6.949 (Outra saída de mercadoria não especificada) |
| *Natureza da Operação* | REMESSA DE MERCADORIA PARA POSTERIOR FATURAMENTO |
| *tipo_operacao* | REMESSA (novo campo no modelo) |
| *status_faturamento* | PENDENTE → FATURADA (novo campo) |

*Regras obrigatórias:*

1. O campo cliente deve ser obrigatório para notas de remessa (sem cliente não há agrupamento possível).
2. Ao ser *autorizada pela SEFAZ* (status AUTORIZADA + chave_acesso preenchida), a nota entra automaticamente no pool de remessas pendentes de faturamento.
3. Uma nota filha cancelada deve ser *removida do pool* e NÃO pode ser vinculada a nenhuma nota mãe.
4. Uma nota filha já faturada (status_faturamento = FATURADA) deve ser bloqueada para cancelamento — exige estorno da nota mãe primeiro.
5. **[REGRA AGRÍCOLA]** O preenchimento do grupo de Rastreabilidade de Produto (`<rastro>`), contendo o número do lote, data de fabricação/validade e quantidade do lote, é obrigatório nas Notas Filhas para atender à legislação sanitária de sementes, grãos e defensivos.

### 1.3 Nota Mãe — Fluxo de Faturamento

| Atributo | Valor |
|---|---|
| *Finalidade NF-e* | 1 — NF-e Normal |
| *CFOP Operação Interna* | 5.116 (venda de produção própria) ou 5.117 (venda de mercadoria adquirida) |
| *CFOP Operação Interestadual* | 6.116 ou 6.117 |
| *Natureza da Operação* | FATURAMENTO DE REMESSAS ANTERIORES |
| *tipo_operacao* | FATURAMENTO (novo campo) |
| *Referência NF-e* | Grupo `<NFref>` com todas as chaves de acesso das filhas |

*Regras obrigatórias:*

1. A Nota Mãe deve ser criada *exclusivamente pelo processo de fechamento* (tela B) — nunca manualmente.
2. O campo `<infNFe><infAdic><infCpl>` (informações complementares) deve conter a lista de notas referenciadas no formato: *NF-e de Faturamento referente às remessas: NF 000001 (Chave: ...44 dígitos...), NF 000002 (Chave: ...44 dígitos...)*.
3. **[REGRA AGRÍCOLA]** Os *itens* da Nota Mãe devem ser a consolidação dos itens das filhas agrupados por **Produto + Lote**, somando as quantidades. Isso garante a correta transmissão e manutenção do grupo `<rastro>` no XML da Nota Mãe.
4. Todos os tributos (ICMS, PIS, COFINS, IPI) devem ser recalculados sobre os totais consolidados. A rotina do sistema deve aplicar ajustes de arredondamento monetário de centavos para garantir que a soma dos itens bata com precisão absoluta com o somatório do total financeiro das notas filhas, evitando rejeições da SEFAZ.
5. A data de emissão da Nota Mãe é sempre a data do fechamento, independente das datas das notas filhas.

### 1.4 Seleção de CFOP — Regra Decisória

```text
Nota Filha (Remessa Física):
  ├── Destinatário no mesmo estado → 5.949 (Remessa para posterior faturamento)
  └── Destinatário em outro estado → 6.949 (Remessa para posterior faturamento)

Nota Mãe (Faturamento Fiscal/Financeiro):
  ├── Produto de PRODUÇÃO PRÓPRIA
  │     ├── Mesmo estado → 5.116
  │     └── Outro estado → 6.116
  └── Produto ADQUIRIDO/REVENDIDO
        ├── Mesmo estado → 5.117
        └── Outro estado → 6.117
```

O sistema deve inferir o CFOP automaticamente com base no estado do destinatário vs. emitente, no tipo de produto e na etapa do fluxo (Remessa vs. Faturamento), mas permitir override manual restrito ao perfil administrador.

---

## 2. REGRAS DE ESTOQUE — MOVIMENTAÇÃO DO INVENTÁRIO

### 2.1 Princípio Central

> *A baixa física ocorre UMA ÚNICA VEZ: no momento da autorização da Nota Filha (Remessa).*
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
            lote=item.lote,                 # Controle por lote obrigatório no Agro
            tipo='SAIDA',
            origem='REMESSA_FATURAMENTO',   # Novo choice a adicionar
            quantidade=item.quantidade,
            armazem_origem=item.armazem,    # Armazém de onde saiu
            documento_origem=f'NF-e {nota_filha.numero}/{nota_filha.serie}',
            chave_nfe=nota_filha.chave_acesso,
            observacao=f'Remessa para posterior faturamento — Cliente: {nota_filha.cliente}',
            criado_por=nota_filha.criado_por,
        )

    nota_filha.status_faturamento = 'PENDENTE'
    nota_filha.save(update_fields=['status_faturamento'])
```

*Novo ORIGEM_CHOICES a adicionar em estoque/models.py:*

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

```text
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

Se uma nota filha autorizada (mas ainda PENDENTE) for cancelada, o sistema deve gerar um estorno de entrada de estoque:
* `origem = 'CANCELAMENTO_REMESSA'` (novo choice)
* `tipo = 'ENTRADA'`
* `quantidade = soma dos itens cancelados`

---

## 3. REQUISITOS DE INTERFACE E TELAS (UI/UX)

### 3.1 Tela A — Dashboard de Remessas Pendentes de Faturamento

* **URL sugerida:** `/faturamento/remessas-pendentes/`
* **Nome de URL:** `faturamento:remessas_pendentes`

#### 3.1.1 Layout Geral

```text
┌──────────────────────────────────────────────────────────────────────┐
│  NAVBAR (base.html)                                                  │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Remessas Pendentes de Faturamento               [+ Nova Remessa]   │
│  ─────────────────────────────────────────────────────               │
│                                                                      │
│  ┌── PAINEL DE FILTROS ──────────────────────────────────────────┐   │
│  │ [Cliente ▼]  [Período: De __/__/__ Até __/__/__]   [Buscar]   │   │
Use o código com cuidado.│  └───────────────────────────────────────────────────────────────┘   ││                                                                      ││  ┌── RESUMO DO AGRUPAMENTO (aparece quando há seleção) ──────────┐   ││  │ ✓ 3 notas selecionadas    Total: R$ 48.750,00     (Fechar Lote)│   ││  └───────────────────────────────────────────────────────────────┘   ││                                                                      ││  ┌── TABELA DE REMESSAS ─────────────────────────────────────────┐   ││  │ NF#   Data   Cliente       Valor       Status             │   ││  │ 001   01/06  Fazenda Alfa  R$ 12.500   Pendente           │   ││  │ 002   05/06  Fazenda Alfa  R$ 18.250   Pendente           │   ││  │ 003   12/06  Fazenda Alfa  R$ 18.000   Pendente           │   ││  │ 004   15/06  Fazenda Beta  R$  9.300   Pendente           │   ││  └───────────────────────────────────────────────────────────────┘   ││                                                                      ││  (Selecionar todas visíveis)               Total geral: R$ 58.050   │└──────────────────────────────────────────────────────────────────────┘%%MAGIT_PARSER_PROTECT%%```3.1.2 Componentes e ComportamentosFiltros:CampoTipoComportamentocliente<select> com Select2 (autocomplete)Filtra a tabela via GET; Opcional para visualização, mas restringe o agrupamento.data_de<input type="date">Filtra data_emissao >= data_dedata_ate<input type="date">Filtra data_emissao <= data_ate; default = hoje(Buscar)<button> submitRecarrega a página com parâmetros GETTabela:ColunaFonteObservação[ ]checkbox HTMLname="notas_ids" value="{{ nota.pk }}"NF #nota.numeroLink para a tela de detalhes da notaDatanota.data_emissaoFormatado em dd/mm/yyyyClientenota.clienteExibido em linha para conferência visualValornota.valor_totalFormatado em BRLCFOPnota.cfopBadge cinza estáticoStatusnota.status_faturamentoBadge warning = PendenteChavenota.chave_acesso[:8]...Tooltip com a chave de 44 dígitos completa ao passar o mouseBarra de resumo (sticky bottom, aparece com ≥ 1 seleção):%%MAGIT_PARSER_PROTECT%%```html0 nota(s) selecionada(s) —Total: R$ 0,00 Fechar Lote de Faturamento%%MAGIT_PARSER_PROTECT%%```Lógica de JavaScript Necessária (remessas_pendentes.js):Controle Dinâmico Inter-Clientes: Se o usuário marcar uma nota sem um cliente definido no filtro principal, o JavaScript captura o cliente_id dessa nota e desabilita imediatamente os checkboxes de todas as notas que pertençam a outros clientes. Desmarcar todas as notas reativa os checkboxes globalmente.Listener change nos checkboxes acumula o valor_total e o pk das notas selecionadas.Atualiza os seletores #qtd-selecionadas e #total-selecionado em tempo real.Habilita o botão #btn-fechar-lote somente quando selecionadas.length >= 1.O formulário envia uma requisição POST para /faturamento/fechar-lote/ enviando o array contendo os IDs das notas.3.2 Tela B — Fechamento / Prévia da Nota MãeURL sugerida: /faturamento/fechar-lote/Nome de URL: faturamento:fechar_loteMétodo de Entrada: POST (recebe notas_ids[] da Tela A), processa em memória e renderiza a prévia.3.2.1 Layout Geral%%MAGIT_PARSER_PROTECT%%text ┌──────────────────────────────────────────────────────────────────────┐ │  ← Voltar      Fechamento de Lote — Prévia da Nota Fiscal Mãe       │ │  ────────────────────────────────────────────────────────────        │ │                                                                      │ │  ┌── CABEÇALHO DO FATURAMENTO ─────────────────────────────────┐   │ │  │ Cliente: Fazenda Alfa Ltda (CNPJ 00.000.000/0001-00)        │   │ │  │ Período das remessas: 01/06/2026 a 12/06/2026               │   │ │  │ Data de emissão da NF Mãe: [ 29/06/2026 ] (editável)        │   │ │  │ CFOP sugerido: [5.116 ▼]   Natureza: FATURAMENTO REMESSAS   │   │ │  └─────────────────────────────────────────────────────────────┘   │ │                                                                      │ │  ┌── NOTAS REFERENCIADAS (somente leitura) ────────────────────┐   │ │  │ NF#   Data       Valor         Chave de Acesso              │   │ │  │ 001   01/06/26   R$ 12.500,00  3526 0600 0000 ... 0001      │   │ │  │ 002   05/06/26   R$ 18.250,00  3526 0600 0000 ... 0002      │   │ │  │ 003   12/06/26   R$ 18.000,00  3526 0600 0000 ... 0003      │   │ │  └─────────────────────────────────────────────────────────────┘   │ │                                                                      │ │  ┌── ITENS CONSOLIDADOS (somente leitura) ─────────────────────┐   │ │  │ Produto     Lote       Qtd Total   Un   Valor Unit.   Subtotal  │   │ │  │ Soja grão   L-04A      100,00      SC   R$ 320,00     R$ 32.000 │   │ │  │ Soja grão   L-09B       50,00      SC   R$ 320,00     R$ 16.000 │   │ │  │ Milho grão  L-01       18,00       SC   R$  41,67     R$    750 │   │ │  └─────────────────────────────────────────────────────────────┘   │ │                                                                      │ │  ┌── TOTAIS (somente leitura) ─────────────────────────────────┐   │ │  │ Valor Produtos   R$ 48.750,00    [calculado das filhas]     │   │ │  │ Valor Desconto   R$      0,00                               │   │ │  │ Valor Total      R$ 48.750,00    ← NÃO EDITÁVEL             │   │ │  └─────────────────────────────────────────────────────────────┘   │ │                                                                      │ │  ┌── INFORMAÇÕES ADICIONAIS (editável) ────────────────────────┐   │ │  │ Obs. Complementares: [textarea — pré-preenchido com lista   │   │ │  │ de NFs referenciadas e chaves para a SEFAZ]                 │   │ │  └─────────────────────────────────────────────────────────────┘   │ │                                                                      │ │  [← Voltar e Reeditar]                       [✓ Gerar Nota Fiscal Mãe]│ └──────────────────────────────────────────────────────────────────────┘ %%MAGIT_PARSER_PROTECT%%3.2.2 Componentes e ComportamentosCampos da Tela:CampoEditávelObservaçãodata_emissaoSimDefault = hojecfopSimSelect limitado aos CFOPs válidos de faturamento (5.116, 5.117, 6.116, 6.117)natureza_operacaoSimPré-preenchida com "FATURAMENTO DE REMESSAS ANTERIORES"informacoes_complementaresSimPré-preenchida de forma automática por função script.valor_total / valor_produtosNãoExibidos como texto estático (Bloqueado contra manipulação via inspecionar elemento).Itens consolidadosNãoGerados e sumarizados via backend por Produto + Lote.Notas referenciadasNãoApenas exibição em formato de tabela com ícones de cadeado.Pré-preenchimento Automático das Informações Complementares:%%MAGIT_PARSER_PROTECT%%python def gerar_infcpl_faturamento(notas_filhas): linhas = [f"NF {n.numero:06d} em {n.data_emissao:%d/%m/%Y} (Chave: {n.chave_acesso})" for n in notas_filhas] return ("NF-e de Faturamento referente às remessas anteriores:\n" + "\n".join(linhas)) %%MAGIT_PARSER_PROTECT%%Ações do Botão "Gerar Nota Fiscal Mãe":Dispara um POST definitivo para /faturamento/gerar-nota-mae/.Exibe um componente visual de bloqueio de tela (Spinner/Loading Overlay) enquanto aguarda o processamento síncrono com a SEFAZ.Sucesso: Redireciona o usuário para a view de detalhes da Nota Fiscal Mãe gerada com mensagem de sucesso.Erro SEFAZ / Rejeição: Mantém os dados na tela de prévia e injeta o alerta contendo o código do erro retornado pelo validador.4. VALIDAÇÕES E TRAVAS DE SEGURANÇA4.1 Novos Campos no Modelo NotaFiscal%%MAGIT_PARSER_PROTECT%%```pythonfaturamento/models.py — adicionar à classe NotaFiscalTIPO_OPERACAO_CHOICES = [('VENDA', 'Venda Direta'),('REMESSA', 'Remessa para Faturamento Posterior'),('FATURAMENTO', 'Faturamento de Remessas Anteriores'),('DEVOLUCAO', 'Devolução'),('COMPLEMENTAR', 'Complementar'),]STATUS_FATURAMENTO_CHOICES = [('NAO_APLICA', 'Não se aplica'),('PENDENTE', 'Aguardando Faturamento'),('FATURADA', 'Faturada'),]tipo_operacao = models.CharField('Tipo de Operação',max_length=20,choices=TIPO_OPERACAO_CHOICES,default='VENDA',db_index=True,)status_faturamento = models.CharField('Status do Faturamento',max_length=20,choices=STATUS_FATURAMENTO_CHOICES,default='NAO_APLICA',db_index=True,)nota_mae = models.ForeignKey('self',on_delete=models.SET_NULL,null=True,blank=True,related_name='notas_filhas',verbose_name='Nota Mãe (Faturamento)',help_text='Preenchido automaticamente ao fechar o lote de faturamento.',)%%MAGIT_PARSER_PROTECT%%```4.2 Modelo de Referências Múltiplas — NFeReferenciadaO campo padrão de referência única do banco não comporta o agrupamento de N notas filhas. É obrigatória a criação da tabela relacional:%%MAGIT_PARSER_PROTECT%%```pythonclass NFeReferenciada(models.Model):"""Referências de NF-e no grupo  da NF-e.Suporta tanto o caso de devolução (uma referência) quantoo faturamento agrupado (N referências)."""nota_fiscal = models.ForeignKey(NotaFiscal,on_delete=models.CASCADE,related_name='nfes_referenciadas',verbose_name='Nota Fiscal',)chave_acesso_referenciada = models.CharField('Chave de Acesso Referenciada',max_length=44,)numero_referenciado = models.PositiveIntegerField('Número NF Referenciada', null=True, blank=True)data_emissao_referenciada = models.DateField('Data Emissão Referenciada', null=True, blank=True)class Meta:verbose_name = 'NF-e Referenciada'unique_together = (('nota_fiscal', 'chave_acesso_referenciada'))indexes = [models.Index(fields=('chave_acesso_referenciada'), name='idx_nfe_ref_chave'),]def clean(self):if len(self.chave_acesso_referenciada) != 44:raise ValidationError('A chave de acesso referenciada deve ter exatamente 44 dígitos.')%%MAGIT_PARSER_PROTECT%%```4.3 Trava: Nota Filha em Apenas Uma Nota MãeGarantia de integridade lógica via constraint nativa de banco de dados na migration:%%MAGIT_PARSER_PROTECT%%```pythonNa migration correspondente:class Migration(migrations.Migration):operations = [migrations.AddConstraint(model_name='notafiscal',constraint=models.UniqueConstraint(fields=('nota_mae'),condition=models.Q(nota_mae__isnull=False),name='uniq_nota_filha_por_mae',),),]%%MAGIT_PARSER_PROTECT%%```A validação semântica obrigatória da camada de serviço deve atuar de forma ativa antes da persistência:%%MAGIT_PARSER_PROTECT%%```python