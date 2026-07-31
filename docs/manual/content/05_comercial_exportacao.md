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

### Tela: Novo Pedido de Venda

<figure>
  <img src="screenshots/vendas/03-pedido-novo.png" alt="Novo Pedido de Venda">
  <figcaption>Formulário de novo pedido: cliente, vendedor, itens e condição comercial.</figcaption>
</figure>

**Como preencher:** escolha o **Cliente** (a Tabela de Preço vinculada a ele, se houver, sugere os preços automaticamente), o **Vendedor** responsável, e adicione os **itens** (produto, quantidade, preço). Informe a condição de pagamento e, se aplicável, o romaneio de embalagem de origem.

### Fluxo passo a passo — de pedido a nota fiscal

1. Crie o Pedido de Venda com cliente, itens e condição comercial.
2. Um aprovador **aprova** o pedido.
3. Use **Emitir Documento** no detalhe do pedido para gerar a NF-e (ou Invoice, se exportação) diretamente no módulo Faturamento, já com os dados do pedido preenchidos.
4. Acompanhe o restante do ciclo fiscal em Faturamento.

### Tela: Tabelas de Preço

<figure>
  <img src="screenshots/vendas/04-tabelas-preco.png" alt="Tabelas de Preço">
  <figcaption>Tabelas de preço (`/vendas/tabelas-preco/`) usadas para sugerir preços por cliente/produto no pedido.</figcaption>
</figure>

**Como preencher:** dê um nome à tabela, defina o período de vigência e adicione os itens (produto + preço). Depois, associe a tabela ao(s) cliente(s) que devem usá-la (no cadastro do cliente, aba Dados Comerciais).

### Dicas e erros comuns

- Em operações de fruta/hortifruti, é comum o **romaneio de embalagem** nascer antes do pedido de venda estar fechado — o pedido é ajustado depois com o que efetivamente foi embalado. Veja a seção Embalagem abaixo.
- Um pedido sem Tabela de Preço vinculada ao cliente exige digitar o preço manualmente item a item — vale cadastrar a tabela antes se o cliente compra com frequência.

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

### Tela: Formulário de Novo Tipo de Embalagem

<figure>
  <img src="screenshots/embalagem/08-tipo-embalagem-form.png" alt="Formulário de Novo Tipo de Embalagem">
  <figcaption>Nome, capacidade (unidades por embalagem) e peso.</figcaption>
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

### Tela: Formulário de Nova Ordem de Embalagem

<figure>
  <img src="screenshots/embalagem/09-ordem-form.png" alt="Formulário de Nova Ordem de Embalagem">
  <figcaption>Produto, tipo de embalagem e quantidade a embalar.</figcaption>
</figure>

**Como preencher:** escolha o produto, o tipo de embalagem e a quantidade planejada. Depois de salva, use **Gerar Pallets** na tela de detalhe para criar os pallets a partir da ordem, e **Etiquetas (PDF)** para imprimir as etiquetas de identificação.

### Tela: Lista de Pallets

<figure>
  <img src="screenshots/embalagem/05-pallets-lista.png" alt="Lista de Pallets">
  <figcaption>Pallets gerados a partir das ordens de embalagem, incluindo pallets mistos (múltiplos produtos).</figcaption>
</figure>

Um **pallet misto** (mais de um produto) é criado a partir de uma ordem de embalagem (botão "Pallet Misto"), permitindo adicionar itens de produtos diferentes até **finalizar** o pallet.

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

### Tela: Formulário de Novo Romaneio

<figure>
  <img src="screenshots/embalagem/10-romaneio-form.png" alt="Formulário de Novo Romaneio">
  <figcaption>Cliente/destino, veículo/transportadora e pallets a incluir na carga.</figcaption>
</figure>

**Como preencher:** informe o destino (cliente), a transportadora/veículo, e adicione os **pallets** que compõem essa carga. Se houver frete e ICMS a ratear entre os itens, o sistema usa o método do **maior resto** para distribuir o valor sem deixar diferenças de arredondamento, e pode gerar automaticamente um pré-CT-e a partir dos dados do romaneio.

### Fluxo passo a passo — do produto embalado ao romaneio

1. Crie a **Ordem de Embalagem** (produto + tipo de embalagem + quantidade).
2. **Gere os pallets** a partir da ordem (ou monte um pallet misto, se necessário).
3. Crie o **Romaneio**, adicionando os pallets que vão para aquela carga/cliente.
4. Se houver frete/ICMS a ratear, confirme o rateio antes de fechar o romaneio.
5. O Pedido de Venda é ajustado (ou criado) com base no que foi efetivamente romaneado.
6. A partir do romaneio, gere o pré-CT-e se o transporte for por conta da empresa.

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

### Tela: Formulário de Novo Lote de Etiquetas

<figure>
  <img src="screenshots/etiquetas_avulsas/03-lote-form.png" alt="Formulário de Novo Lote de Etiquetas">
  <figcaption>Produto e quantidade de etiquetas a gerar.</figcaption>
</figure>

**Como preencher:** escolha o produto e a quantidade de etiquetas; depois de criado o lote, use **Adicionar Pallets** para vincular pallets específicos, e **Concluir** para fechar o lote e liberar a impressão.

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

### Tela: Formulário de Nova Solicitação de Booking

<figure>
  <img src="screenshots/exportacao/05-solicitacao-form.png" alt="Formulário de Nova Solicitação de Booking">
  <figcaption>Cliente, porto de embarque/destino, previsão de quantidade e data.</figcaption>
</figure>

### Tela: Lista de Bookings

<figure>
  <img src="screenshots/exportacao/02-bookings-lista.png" alt="Lista de Bookings">
  <figcaption>Bookings confirmados (`/exportacao/bookings/`).</figcaption>
</figure>

### Tela: Formulário de Novo Booking

<figure>
  <img src="screenshots/exportacao/06-booking-form.png" alt="Formulário de Novo Booking">
  <figcaption>Formulário em 7 abas: Solicitação, Identificação, Rotas, Datas e Prazos, Agentes de Exportação, Financeiro, Observações.</figcaption>
</figure>

**Como preencher:** um Booking normalmente **nasce de uma Solicitação** já aprovada — escolha-a na primeira aba para herdar cliente e carga previstos. Complete Identificação (armador, navio), Rotas (porto de embarque/destino), Datas e Prazos (ETD/ETA, prazo de cut-off) e Agentes de Exportação (agente responsável pela documentação).

### Tela: Detalhe do Booking

<figure>
  <img src="screenshots/exportacao/03-booking-detalhe.png" alt="Detalhe de um Booking">
  <figcaption>Containers vinculados ao booking, com opção de transferir carga entre containers e ver o histórico.</figcaption>
</figure>

**Como preencher (containers):** use **Adicionar Container** informando número, tipo/tamanho e a carga alocada. Se for preciso remanejar carga entre containers já criados, use **Transferir**. Quando o booking está com todos os containers carregados, use **Confirmar** e, no embarque efetivo, **Embarcar**.

### Tela: Ordens de Coleta

<figure>
  <img src="screenshots/exportacao/04-ordens-coleta.png" alt="Ordens de Coleta">
  <figcaption>Ordens de coleta da carga para o porto de embarque.</figcaption>
</figure>

### Tela: Formulário de Nova Ordem de Coleta

<figure>
  <img src="screenshots/exportacao/07-ordem-coleta-form.png" alt="Formulário de Nova Ordem de Coleta">
  <figcaption>Booking de referência, local de coleta e data/veículo designado.</figcaption>
</figure>

### Fluxo passo a passo — de solicitação a embarque

1. Registre a **Solicitação de Booking** com o cliente e a carga prevista.
2. Depois de aprovada/confirmada com o armador, crie o **Booking** referenciando essa solicitação.
3. Adicione os **containers** e aloque a carga (transferindo entre containers se necessário).
4. Emita a **Ordem de Coleta** para buscar a carga e levá-la ao porto.
5. **Confirme** o booking quando os containers estiverem prontos, e marque **Embarcado** após o navio zarpar.

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

### Tela: Formulário de Novo Ato Concessório

<figure>
  <img src="screenshots/drawback/03-ac-form.png" alt="Formulário de Novo Ato Concessório">
  <figcaption>Número do AC, datas de validade e produtos autorizados.</figcaption>
</figure>

**Como preencher:** informe o número do Ato Concessório emitido pelo órgão competente, a data de validade e os produtos/insumos autorizados no regime. Depois de criado, use as ações **Nova Entrada**/**Nova Saída** (ou importação via planilha XLSX) para registrar a movimentação de insumos e produtos exportados sob esse AC.

### Tela: Detalhe do Ato Concessório

<figure>
  <img src="screenshots/drawback/02-ac-detalhe.png" alt="Detalhe de um Ato Concessório">
  <figcaption>Entradas e saídas vinculadas ao AC, com saldo por produto e relatório exportável.</figcaption>
</figure>

Entradas e saídas podem ser importadas em lote via planilha (XLSX), ou vinculadas diretamente a um Recebimento de Compra / item de NF-e já existente no sistema, evitando digitação duplicada.

### Fluxo passo a passo — operar um Ato Concessório

1. Cadastre o **AC** com os produtos/insumos autorizados.
2. Registre as **entradas** de insumo (importado ou adquirido no mercado interno), vinculando a um recebimento de compra sempre que possível.
3. Registre as **saídas** conforme os produtos são exportados, vinculando à NF-e de exportação correspondente.
4. Acompanhe o **saldo** disponível por produto no detalhe do AC — é ele que mostra quanto insumo ainda pode ser usado dentro do regime.
5. Gere o **relatório** do AC quando precisar prestar contas do regime.

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

### Tela: Formulário de Nova NF-e

<figure>
  <img src="screenshots/faturamento/15-nfe-form.png" alt="Formulário de Nova NF-e">
  <figcaption>Formulário extenso, em 11 abas: Dados Gerais, Itens, Pagamentos, Duplicatas, Referências, Complementares, Transporte, Exportação, Entrega, Retirada, Agropecuário, Produtor Rural.</figcaption>
</figure>

**Como preencher (aba Dados Gerais):**

| Campo | Obrigatório | Descrição |
|---|---|---|
| Cliente | Sim (exceto notas sem destinatário definido) | Busca com autocomplete |
| Data de Emissão | Sim | Pré-preenchida com a data atual |
| Tipo de Operação | Sim | Ex: "Venda Direta" — cada tipo mostra uma explicação de quando usá-lo |
| Natureza da Operação | Sim | Ex: "VENDA DE MERCADORIA" |
| Finalidade NF-e | Sim | Normal, Complementar, Ajuste, Devolução |
| CFOP Padrão | Sim | Sugerido pela Natureza da Operação, pode ser ajustado |
| Presença do Comprador | Sim | Presencial, não presencial pela internet, etc. |
| Indicador de Intermediador | Condicional | Obrigatório para certos indicadores de presença (o próprio campo avisa quando) |

O painel lateral **Resumo de Valores** (frete, seguro, desconto, IPI, ICMS ST) é recalculado automaticamente conforme os **Itens** são adicionados na aba seguinte. As demais abas só precisam ser preenchidas quando aplicável ao caso: **Transporte** (se houver frete destacado), **Exportação** (NF-e vinculada a uma exportação), **Agropecuário**/**Produtor Rural** (operações com produtor rural pessoa física).

### Fluxo passo a passo — emitir uma NF-e

1. Preencha Dados Gerais (cliente, tipo/natureza da operação).
2. Adicione os **Itens** — o resumo de valores é recalculado automaticamente.
3. Complete as abas relevantes ao caso (Transporte, Exportação, etc.) — a nota fica **Rascunho** até aqui.
4. Clique em **Emitir** — a nota é transmitida à SEFAZ; se autorizada, o status muda para **Autorizada** e o DANFE fica disponível.
5. Se necessário corrigir algo não-fiscal depois de autorizada, use **Carta de Correção**; para cancelar dentro do prazo legal, use **Cancelar**.

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

### Tela: Formulário de Nova Invoice

<figure>
  <img src="screenshots/faturamento/16-invoice-form.png" alt="Formulário de Nova Invoice">
  <figcaption>Cliente internacional, itens, moeda e INCOTERM.</figcaption>
</figure>

**Como preencher:** escolha o **Cliente** internacional, a **moeda** e o **INCOTERM** da operação, e adicione os itens (produto, quantidade, preço na moeda da invoice). Se houver adiantamento internacional para esse cliente/safra, ele pode ser vinculado e descontado a partir daqui.

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

### Tela: Formulário de Nova Packing List

<figure>
  <img src="screenshots/faturamento/19-packing-list-form.png" alt="Formulário de Nova Packing List">
  <figcaption>Invoice de referência e detalhamento de volumes/pallets da carga.</figcaption>
</figure>

**Como preencher:** vincule a **Invoice** correspondente e detalhe os volumes (pallets, caixas, pesos líquido/bruto) — normalmente espelhando os pallets já romaneados em Embalagem.

### Tela: CT-e (Conhecimento de Transporte)

<figure>
  <img src="screenshots/faturamento/08-cte-lista.png" alt="Lista de CT-e">
  <figcaption>CT-e emitidos (`/faturamento/cte/`).</figcaption>
</figure>

### Tela: Formulário de Novo CT-e

<figure>
  <img src="screenshots/faturamento/17-cte-form.png" alt="Formulário de Novo CT-e">
  <figcaption>Transportadora, veículo, documentos transportados (NF-e) e valor do frete.</figcaption>
</figure>

**Como preencher:** informe a transportadora e o veículo, e vincule as **NF-e transportadas** — o botão de vínculo automático (NF-e → CT-e) evita redigitar dados da carga quando o CT-e nasce de notas já emitidas. Informe o valor do frete e a forma de pagamento (pago, a pagar, etc.).

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

### Tela: Formulário de Novo MDF-e

<figure>
  <img src="screenshots/faturamento/18-mdfe-form.png" alt="Formulário de Novo MDF-e">
  <figcaption>Veículo, condutor(es) e documentos fiscais (NF-e/CT-e) incluídos na viagem.</figcaption>
</figure>

**Como preencher:** informe o veículo (e reboque, se houver) e o(s) condutor(es), depois use o vínculo automático **CT-e → MDF-e** (ou NF-e → MDF-e) para trazer os documentos fiscais da viagem sem redigitar.

### Tela: Detalhe do MDF-e

<figure>
  <img src="screenshots/faturamento/11-mdfe-detalhe.png" alt="Detalhe de um MDF-e">
  <figcaption>Condutor(es), veículo(s) e documentos fiscais (NF-e/CT-e) incluídos no manifesto; deve ser encerrado ao fim da viagem.</figcaption>
</figure>

### Fluxo passo a passo — encadear NF-e → CT-e → MDF-e

1. Emita a(s) **NF-e** da venda/remessa.
2. Ao criar o **CT-e** do frete, use o vínculo automático para trazer as NF-e já emitidas.
3. Ao criar o **MDF-e** da viagem, use o vínculo automático para trazer o(s) CT-e (ou NF-e diretamente, se não houver CT-e).
4. Emita o MDF-e antes da saída do veículo.
5. Ao final da viagem, **encerre** o MDF-e — um manifesto aberto indefinidamente distorce relatórios de carga em trânsito.

### Tela: Cotações BCB

<figure>
  <img src="screenshots/faturamento/12-cotacoes-bcb.png" alt="Cotações BCB">
  <figcaption>Cotações de câmbio do Banco Central, usadas para converter valores em Invoice/Adiantamentos.</figcaption>
</figure>

Use **Buscar Hoje** para importar a cotação do dia diretamente do Banco Central, em vez de digitar manualmente.

### Tela: Configuração Fiscal

<figure>
  <img src="screenshots/faturamento/13-configuracao-fiscal.png" alt="Configuração Fiscal">
  <figcaption>Certificado digital, ambiente SEFAZ (homologação/produção) e parâmetros gerais de emissão.</figcaption>
</figure>

**Como preencher:** faça upload do **certificado digital** (A1) da empresa, confirme o **ambiente** (comece em Homologação para testes, mude para Produção só quando validado) e revise a numeração/série inicial dos documentos. Sem essa configuração completa, nenhum documento fiscal pode ser emitido.

### Tela: Distribuição de DF-e

<figure>
  <img src="screenshots/faturamento/14-distribuicao-dfe.png" alt="Distribuição de DF-e">
  <figcaption>Notas e eventos de terceiros recebidos automaticamente da SEFAZ, com contadores de autorizadas/canceladas e manifestação pendente.</figcaption>
</figure>

Toda vez que um fornecedor emite uma NF-e contra o CNPJ da empresa, ela aparece aqui automaticamente (sincronização periódica com a SEFAZ, ou manualmente pelo botão **Sincronizar Agora**). Cada NF-e recebida precisa ser **manifestada** (Ciência da Operação, Confirmação, Desconhecimento ou Operação não Realizada) — o botão de ação na coluna Manifestação permite isso individualmente ou em lote (**Manifestar em Lote**). Este fluxo se conecta ao módulo de Compras: uma NF-e manifestada com Ciência pode ser usada para abrir uma Entrada Direta / Recebimento.

### Dicas e erros comuns

- Uma NF-e **autorizada** com erro só pode ser corrigida por carta de correção (dados não fiscais) ou cancelamento dentro do prazo — nunca editada diretamente.
- Verifique a **Distribuição de DF-e** regularmente: notas de fornecedor não manifestadas por muito tempo podem gerar problemas fiscais para a empresa.
- O MDF-e precisa ser **encerrado** ao final da viagem — um manifesto aberto indefinidamente distorce relatórios de carga em trânsito.
- Sempre teste emissões novas em ambiente de **Homologação** antes de migrar a Configuração Fiscal para Produção.
