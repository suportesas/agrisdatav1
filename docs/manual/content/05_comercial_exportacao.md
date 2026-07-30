# Comercial & Exportação

## Vendas (`/vendas/`)

### Visão geral

Gerencia os Pedidos de Venda, o documento comercial que formaliza uma venda para um cliente antes da emissão da nota fiscal. Trabalha junto com Embalagem (o romaneio pode nascer antes do pedido fechado) e Tabelas de Preço (para precificar automaticamente os itens conforme o cliente).

### Tela: Pedidos de Venda

<figure>
  <img src="screenshots/vendas/01-pedidos-lista.png" alt="Pedidos de Venda">
  <figcaption>Lista de pedidos de venda (`/vendas/`).</figcaption>
</figure>

### Tela: Detalhe do Pedido de Venda

<figure>
  <img src="screenshots/vendas/02-pedido-detalhe.png" alt="Detalhe de um Pedido de Venda">
  <figcaption>Itens do pedido, valores, e ações de aprovação, emissão de documento fiscal e cancelamento.</figcaption>
</figure>

Um pedido aprovado pode **emitir o documento fiscal** correspondente diretamente a partir do detalhe, integrando com o módulo de Faturamento.

### Tela: Novo Pedido de Venda

<figure>
  <img src="screenshots/vendas/03-pedido-novo.png" alt="Novo Pedido de Venda">
  <figcaption>Formulário de novo pedido: cliente, vendedor, itens e condição comercial.</figcaption>
</figure>

### Tela: Tabelas de Preço

<figure>
  <img src="screenshots/vendas/04-tabelas-preco.png" alt="Tabelas de Preço">
  <figcaption>Tabelas de preço (`/vendas/tabelas-preco/`) usadas para sugerir preços por cliente/produto no pedido.</figcaption>
</figure>

### Dicas e erros comuns

- Em operações de fruta/hortifruti, é comum o **romaneio de embalagem** nascer antes do pedido de venda estar fechado — o pedido é ajustado depois com o que efetivamente foi embalado. Veja a seção Embalagem abaixo.

## Embalagem (`/embalagem/`)

### Visão geral

Controla a produção de embalagens para venda: ordens de embalagem que geram pallets, e romaneios que consolidam os pallets para uma venda/carga específica. O fluxo comum em operações de fruta é **romaneio-primeiro**: a embalagem acontece e o romaneio é fechado antes mesmo do pedido de venda estar formalmente concluído — o pedido nasce a partir do que foi efetivamente embalado, não o contrário.

### Tela: Dashboard de Embalagem

<figure>
  <img src="screenshots/embalagem/01-dashboard.png" alt="Dashboard de Embalagem">
  <figcaption>Indicadores gerais de produção de embalagem.</figcaption>
</figure>

### Tela: Tipos de Embalagem

<figure>
  <img src="screenshots/embalagem/02-tipos-embalagem.png" alt="Tipos de Embalagem">
  <figcaption>Tipos de embalagem cadastrados (`/embalagem/tipos/`) — caixa, pallet, etc.</figcaption>
</figure>

### Tela: Ordens de Embalagem

<figure>
  <img src="screenshots/embalagem/03-ordens-lista.png" alt="Ordens de Embalagem">
  <figcaption>Ordens de embalagem (`/embalagem/ordens/`).</figcaption>
</figure>

### Tela: Detalhe da Ordem de Embalagem

<figure>
  <img src="screenshots/embalagem/04-ordem-detalhe.png" alt="Detalhe de uma Ordem de Embalagem">
  <figcaption>Itens embalados; a partir daqui é possível gerar os pallets e imprimir etiquetas.</figcaption>
</figure>

### Tela: Lista de Pallets

<figure>
  <img src="screenshots/embalagem/05-pallets-lista.png" alt="Lista de Pallets">
  <figcaption>Pallets gerados a partir das ordens de embalagem, incluindo pallets mistos (múltiplos produtos).</figcaption>
</figure>

### Tela: Romaneios de Venda

<figure>
  <img src="screenshots/embalagem/06-romaneios-lista.png" alt="Romaneios de Venda">
  <figcaption>Romaneios (`/embalagem/romaneios/`) — consolidação de pallets para uma carga/venda.</figcaption>
</figure>

### Tela: Detalhe do Romaneio

<figure>
  <img src="screenshots/embalagem/07-romaneio-detalhe.png" alt="Detalhe de um Romaneio">
  <figcaption>Pallets incluídos no romaneio, com rateio de frete e ICMS por carga (maior resto) quando aplicável.</figcaption>
</figure>

Quando o romaneio envolve frete e ICMS a ratear entre os itens da carga, o sistema usa o método do **maior resto** para distribuir o valor sem deixar diferenças de arredondamento, e pode gerar automaticamente um pré-CT-e a partir dos dados do romaneio.

### Dicas e erros comuns

- Gerar os pallets a partir da Ordem de Embalagem evita ter que cadastrá-los manualmente no Romaneio depois.
- Pallets **mistos** (mais de um produto) só podem ser finalizados depois de todos os itens planejados serem adicionados.

## Etiquetas Avulsas (`/etiquetas-avulsas/`)

### Visão geral

Gera lotes de etiquetas para reimpressão ou emissão avulsa, fora do fluxo normal de uma Ordem de Embalagem — por exemplo, para repor uma etiqueta danificada ou gerar etiquetas extras sem reabrir a ordem original.

### Tela: Lotes de Etiquetas Avulsas

<figure>
  <img src="screenshots/etiquetas_avulsas/01-lotes-lista.png" alt="Lotes de Etiquetas Avulsas">
  <figcaption>Lotes gerados (`/etiquetas-avulsas/lotes/`).</figcaption>
</figure>

### Tela: Detalhe do Lote de Etiquetas

<figure>
  <img src="screenshots/etiquetas_avulsas/02-lote-detalhe.png" alt="Detalhe de um Lote de Etiquetas">
  <figcaption>Etiquetas do lote, com opção de reimpressão ou cancelamento individual.</figcaption>
</figure>

### Dicas e erros comuns

- Uma etiqueta avulsa **cancelada** não é reaproveitável — gere uma nova em vez de tentar reativar.

## Exportação (`/exportacao/`)

### Visão geral

Controla o processo de exportação marítima: solicitação e confirmação de booking (reserva de espaço no navio), containers vinculados ao booking, e ordens de coleta da carga. Os cadastros de apoio (portos, armadores, navios, agentes de exportação) ficam em Cadastros.

### Status do Booking

```
Solicitação → Booking confirmado → Embarcado
```

### Tela: Solicitações de Booking

<figure>
  <img src="screenshots/exportacao/01-solicitacoes-lista.png" alt="Solicitações de Booking">
  <figcaption>Solicitações de reserva de espaço no navio (`/exportacao/solicitacoes/`).</figcaption>
</figure>

### Tela: Lista de Bookings

<figure>
  <img src="screenshots/exportacao/02-bookings-lista.png" alt="Lista de Bookings">
  <figcaption>Bookings confirmados (`/exportacao/bookings/`).</figcaption>
</figure>

### Tela: Detalhe do Booking

<figure>
  <img src="screenshots/exportacao/03-booking-detalhe.png" alt="Detalhe de um Booking">
  <figcaption>Containers vinculados ao booking, com opção de transferir carga entre containers e ver o histórico.</figcaption>
</figure>

### Tela: Ordens de Coleta

<figure>
  <img src="screenshots/exportacao/04-ordens-coleta.png" alt="Ordens de Coleta">
  <figcaption>Ordens de coleta da carga para o porto de embarque.</figcaption>
</figure>

### Dicas e erros comuns

- Um booking só deve ser marcado como **embarcado** depois que todos os containers previstos estiverem devidamente carregados.

## Drawback (`/drawback/`)

### Visão geral

Controla o regime aduaneiro especial de Drawback (suspensão/isenção de tributos sobre insumos importados usados na produção de mercadorias exportadas), organizado por **Ato Concessório** (AC) — o documento que autoriza o regime — com registro de entradas (insumos importados/adquiridos) e saídas (produtos exportados) vinculadas ao AC.

### Tela: Dashboard de Drawback (Atos Concessórios)

<figure>
  <img src="screenshots/drawback/01-dashboard.png" alt="Dashboard de Drawback">
  <figcaption>Atos Concessórios cadastrados, com saldo de insumos disponível para uso.</figcaption>
</figure>

### Tela: Detalhe do Ato Concessório

<figure>
  <img src="screenshots/drawback/02-ac-detalhe.png" alt="Detalhe de um Ato Concessório">
  <figcaption>Entradas e saídas vinculadas ao AC, com saldo por produto e relatório exportável.</figcaption>
</figure>

Entradas e saídas podem ser importadas em lote via planilha (XLSX), ou vinculadas diretamente a um Recebimento de Compra / item de NF-e já existente no sistema, evitando digitação duplicada.

### Dicas e erros comuns

- Uma entrada ou saída **anulada** não conta mais no saldo do AC — use com cuidado, pois pode ser necessário para corrigir um lançamento incorreto.
- Vincular entradas/saídas aos documentos já existentes no ERP (compra/NF-e) é preferível a importar por planilha, pois mantém rastreabilidade cruzada.

## Faturamento (`/faturamento/`)

### Visão geral

Módulo fiscal central: emissão de **NF-e** (venda), **CT-e** (transporte), **MDF-e** (manifesto de carga), **Invoice de Exportação** e **Packing List**, além da configuração fiscal da empresa (certificado digital, ambiente SEFAZ) e da **Distribuição de DF-e** — recebimento automático de documentos fiscais de terceiros emitidos contra o CNPJ da empresa.

### Tela: Dashboard de Faturamento

<figure>
  <img src="screenshots/faturamento/01-dashboard.png" alt="Dashboard de Faturamento">
  <figcaption>Indicadores gerais: notas emitidas, pendências e alertas fiscais.</figcaption>
</figure>

### Tela: Lista de Notas Fiscais (NF-e)

<figure>
  <img src="screenshots/faturamento/02-nfe-lista.png" alt="Lista de Notas Fiscais">
  <figcaption>NF-e emitidas (`/faturamento/notas-fiscais/`).</figcaption>
</figure>

### Tela: Detalhe da NF-e

<figure>
  <img src="screenshots/faturamento/03-nfe-detalhe.png" alt="Detalhe de uma NF-e">
  <figcaption>Itens, status de autorização na SEFAZ, e ações (emitir, cancelar, consultar, DANFE, XML, carta de correção).</figcaption>
</figure>

Uma NF-e passa por: **rascunho → emissão** (envio à SEFAZ) **→ autorizada** (ou rejeitada/denegada). Após autorizada, ainda é possível emitir **carta de correção** para ajustes que não alteram valores, ou **cancelar** dentro do prazo legal.

### Tela: Remessas Pendentes

<figure>
  <img src="screenshots/faturamento/04-remessas-pendentes.png" alt="Remessas Pendentes">
  <figcaption>Pedidos/remessas aguardando faturamento, com opção de fechar lote e gerar nota-mãe.</figcaption>
</figure>

### Tela: Invoices de Exportação

<figure>
  <img src="screenshots/faturamento/05-invoices-lista.png" alt="Invoices de Exportação">
  <figcaption>Invoices comerciais de exportação (`/faturamento/invoices/`).</figcaption>
</figure>

### Tela: Detalhe da Invoice

<figure>
  <img src="screenshots/faturamento/06-invoice-detalhe.png" alt="Detalhe de uma Invoice">
  <figcaption>Itens da invoice, valores em moeda estrangeira e vínculo com adiantamentos internacionais.</figcaption>
</figure>

### Tela: Packing Lists

<figure>
  <img src="screenshots/faturamento/07-packing-lists.png" alt="Packing Lists">
  <figcaption>Packing Lists (`/faturamento/packing-lists/`) — detalhamento físico da carga de exportação.</figcaption>
</figure>

### Tela: CT-e (Conhecimento de Transporte)

<figure>
  <img src="screenshots/faturamento/08-cte-lista.png" alt="Lista de CT-e">
  <figcaption>CT-e emitidos (`/faturamento/cte/`).</figcaption>
</figure>

### Tela: Detalhe do CT-e

<figure>
  <img src="screenshots/faturamento/09-cte-detalhe.png" alt="Detalhe de um CT-e">
  <figcaption>Dados do frete, documentos vinculados (NF-e transportadas) e ações fiscais (emitir, cancelar, DACTE).</figcaption>
</figure>

Um CT-e pode ser gerado automaticamente a partir de uma NF-e (ligação NF-e → CT-e) ou de um Romaneio com frete a ratear, evitando redigitar os dados da carga transportada.

### Tela: MDF-e (Manifestos)

<figure>
  <img src="screenshots/faturamento/10-mdfe-lista.png" alt="Lista de MDF-e">
  <figcaption>MDF-e emitidos (`/faturamento/mdfe/`).</figcaption>
</figure>

### Tela: Detalhe do MDF-e

<figure>
  <img src="screenshots/faturamento/11-mdfe-detalhe.png" alt="Detalhe de um MDF-e">
  <figcaption>Condutor(es), veículo(s) e documentos fiscais (NF-e/CT-e) incluídos no manifesto; deve ser encerrado ao fim da viagem.</figcaption>
</figure>

### Tela: Cotações BCB

<figure>
  <img src="screenshots/faturamento/12-cotacoes-bcb.png" alt="Cotações BCB">
  <figcaption>Cotações de câmbio do Banco Central, usadas para converter valores em Invoice/Adiantamentos.</figcaption>
</figure>

### Tela: Configuração Fiscal

<figure>
  <img src="screenshots/faturamento/13-configuracao-fiscal.png" alt="Configuração Fiscal">
  <figcaption>Certificado digital, ambiente SEFAZ (homologação/produção) e parâmetros gerais de emissão.</figcaption>
</figure>

### Tela: Distribuição de DF-e

<figure>
  <img src="screenshots/faturamento/14-distribuicao-dfe.png" alt="Distribuição de DF-e">
  <figcaption>Notas e eventos de terceiros recebidos automaticamente da SEFAZ, com contadores de autorizadas/canceladas e manifestação pendente.</figcaption>
</figure>

Toda vez que um fornecedor emite uma NF-e contra o CNPJ da empresa, ela aparece aqui automaticamente (sincronização periódica com a SEFAZ). Cada NF-e recebida precisa ser **manifestada** (Ciência da Operação, Confirmação, Desconhecimento ou Operação não Realizada) — o botão de ação na coluna Manifestação permite isso individualmente ou em lote. Este fluxo se conecta ao módulo de Compras: uma NF-e manifestada com Ciência pode ser usada para abrir uma Entrada Direta / Recebimento.

### Dicas e erros comuns

- Uma NF-e **autorizada** com erro só pode ser corrigida por carta de correção (dados não fiscais) ou cancelamento dentro do prazo — nunca editada diretamente.
- Verifique a **Distribuição de DF-e** regularmente: notas de fornecedor não manifestadas por muito tempo podem gerar problemas fiscais para a empresa.
- O MDF-e precisa ser **encerrado** ao final da viagem — um manifesto aberto indefinidamente distorce relatórios de carga em trânsito.
