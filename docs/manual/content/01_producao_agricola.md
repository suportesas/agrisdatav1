# Produção Agrícola

## Cadastros Agrícolas (`/cadastros/`)

### Visão geral

Antes de operar o campo, a estrutura física da produção precisa estar cadastrada: **Fazenda → Área → Talhão**, as **Culturas** plantadas, as **Safras** de cada ciclo produtivo, e cadastros de apoio como **Pragas** e **Poços/Bombas** (irrigação). Esses cadastros alimentam praticamente todo o restante do sistema: Ordens de Serviço, MIP, Estufas, Planejamento de Custo e os relatórios de rastreabilidade.

### Conceitos principais

| Conceito | Papel |
|---|---|
| Fazenda | Propriedade rural — unidade organizacional de mais alto nível |
| Área | Subdivisão da fazenda (ex: um bloco de produção) |
| Talhão | Menor unidade de área plantável, dentro de uma Área; é o nível em que os custos de campo são apurados |
| Cultura | O que é plantado (ex: melão, melancia, milho) |
| Safra | Um ciclo produtivo específico, vinculado a uma fazenda e um período |
| Praga | Cadastro de pragas/doenças usado pelo módulo MIP |
| Poço/Bomba | Ponto de captação de água usado na irrigação |

### Fluxo passo a passo — estruturar uma fazenda do zero

1. Cadastre a **Fazenda** (dados básicos + documentação + endereço).
2. Dentro da fazenda, cadastre uma ou mais **Áreas** (blocos de produção).
3. Dentro de cada Área, cadastre os **Talhões** (a menor unidade de plantio).
4. Cadastre as **Culturas** que serão plantadas (se ainda não existirem no sistema).
5. Abra a **Safra** do ciclo (vinculada à fazenda) e defina o planejamento (talhões/culturas do ciclo).
6. Só a partir daqui é possível abrir Ordens de Serviço, Monitoramento MIP e outras operações — todas exigem talhão e, na maioria dos casos, safra.

### Tela: Lista de Fazendas

<figure>
  <img src="screenshots/cadastros_agro/01-fazendas-lista.png" alt="Lista de Fazendas">
  <figcaption>Fazendas cadastradas (`/cadastros/fazendas/`).</figcaption>
</figure>

### Tela: Detalhe da Fazenda

<figure>
  <img src="screenshots/cadastros_agro/02-fazenda-detalhe.png" alt="Detalhe de uma Fazenda">
  <figcaption>Dados gerais, endereços, contatos, contas bancárias e documentos vinculados à fazenda.</figcaption>
</figure>

### Tela: Formulário de Nova Fazenda

<figure>
  <img src="screenshots/cadastros_agro/11-fazenda-form.png" alt="Formulário de Nova Fazenda">
  <figcaption>Formulário dividido em 5 abas: Dados Básicos, Documentação, Dados da Propriedade, Contato, Observações.</figcaption>
</figure>

**Como preencher (aba Dados Básicos):**

| Campo | Obrigatório | Descrição |
|---|---|---|
| Tipo de Pessoa | Sim | Pessoa Física ou Jurídica — define o formato exigido do documento abaixo |
| CNPJ/CPF | Sim | Documento da fazenda/proprietário. Para Pessoa Jurídica, o botão **Buscar** preenche automaticamente Nome/Razão Social e endereço via API da Receita |
| Nome da Fazenda/Razão Social | Sim | Nome oficial da propriedade |
| Nome Fantasia | Não | Nome comercial, se diferente do oficial |
| Fazenda Ativa | Não (padrão ligado) | Desligar em vez de excluir uma fazenda que parou de operar |

As demais abas cobrem: **Documentação** (inscrição estadual, documentos anexos), **Dados da Propriedade** (área total, matrícula, coordenadas), **Contato** (telefone/e-mail) e **Observações** (texto livre). Preencha ao menos a aba Dados Básicos para salvar; as demais podem ser completadas depois editando a fazenda.

### Tela: Lista de Áreas

<figure>
  <img src="screenshots/cadastros_agro/03-areas-lista.png" alt="Lista de Áreas">
  <figcaption>Áreas cadastradas (`/cadastros/areas/`), sempre vinculadas a uma fazenda.</figcaption>
</figure>

### Tela: Formulário de Nova Área

<figure>
  <img src="screenshots/cadastros_agro/12-area-form.png" alt="Formulário de Nova Área">
  <figcaption>Vincula a área a uma fazenda e registra o tipo de solo.</figcaption>
</figure>

**Como preencher:** escolha a **Fazenda** primeiro — o formulário não permite criar uma área "solta". Informe nome da área e, se souber, o tipo de solo (Arenoso, Argiloso, Siltoso, Humoso, Calcário, Gleissolo, Latossolo, Cambissolo).

### Tela: Lista de Talhões

<figure>
  <img src="screenshots/cadastros_agro/04-talhoes-lista.png" alt="Lista de Talhões">
  <figcaption>Talhões (`/cadastros/talhoes/`) — nível em que os custos de operações de campo são apurados.</figcaption>
</figure>

### Tela: Detalhe do Talhão

<figure>
  <img src="screenshots/cadastros_agro/05-talhao-detalhe.png" alt="Detalhe de um Talhão">
  <figcaption>Dados do talhão e histórico de ocupação/cultivo.</figcaption>
</figure>

### Tela: Formulário de Novo Talhão

<figure>
  <img src="screenshots/cadastros_agro/13-talhao-form.png" alt="Formulário de Novo Talhão">
  <figcaption>Formulário em 4 abas: Identificação, Medidas, Geolocalização & Características, Observações.</figcaption>
</figure>

**Como preencher (aba Identificação):**

| Campo | Obrigatório | Descrição |
|---|---|---|
| Fazenda | Sim | Escolher primeiro — carrega as opções de Área disponíveis |
| Área | Não | Filtrada pela fazenda escolhida |
| Nome do Talhão | Sim | Identificação livre (ex: "Talhão 12") |
| Código | Não | Código interno de referência |

Na aba **Medidas** informe a área em hectares (campo `Área (ha)`, aceita até 4 casas decimais). **Geolocalização & Características** guarda coordenadas e tipo de solo específico do talhão, se diferente da área.

### Tela: Lista de Culturas

<figure>
  <img src="screenshots/cadastros_agro/06-culturas-lista.png" alt="Lista de Culturas">
  <figcaption>Culturas cadastradas (`/cadastros/culturas/`).</figcaption>
</figure>

### Tela: Formulário de Nova Cultura

<figure>
  <img src="screenshots/cadastros_agro/14-cultura-form.png" alt="Formulário de Nova Cultura">
  <figcaption>Cadastro técnico da cultura: ciclo, espaçamento, irrigação e parâmetros de exportação.</figcaption>
</figure>

**Como preencher:** os campos obrigatórios básicos são **Nome** e **Unidade de Medida**. O restante é opcional mas recomendado para culturas que você monitora de perto: nome científico, variedade, ciclo de cultivo (dias), dias até colheita, espaçamento entre linhas/plantas, densidade de plantio, faixa de temperatura ideal, necessidade de água, produtividade esperada, preço médio e mercado destino. Se a cultura for exportada, preencha também temperatura/umidade/ventilação de exportação (usados em Packing List/Invoice).

### Tela: Lista de Safras

<figure>
  <img src="screenshots/cadastros_agro/07-safras-lista.png" alt="Lista de Safras">
  <figcaption>Safras (`/cadastros/safras/`), cada uma vinculada a uma fazenda e um período.</figcaption>
</figure>

### Tela: Detalhe da Safra

<figure>
  <img src="screenshots/cadastros_agro/08-safra-detalhe.png" alt="Detalhe de uma Safra">
  <figcaption>Planejamento da safra e talhões/culturas envolvidos no ciclo.</figcaption>
</figure>

### Tela: Formulário de Nova Safra

<figure>
  <img src="screenshots/cadastros_agro/15-safra-form.png" alt="Formulário de Nova Safra">
  <figcaption>Dados básicos da safra — o planejamento de talhões/culturas é feito depois, na tela de detalhe.</figcaption>
</figure>

**Como preencher:**

| Campo | Obrigatório | Descrição |
|---|---|---|
| Nome | Sim | Ex: "Safra 2026/27" |
| Código | Não | Ex: `202627`, até 10 caracteres |
| Fazenda | Sim | Busca com autocomplete |
| Ano | Sim | Ano de referência da safra |
| Imagem | Não | Foto/ilustração opcional |

Depois de salva, abra a Safra para adicionar o **planejamento** — quais culturas serão plantadas em quais talhões nesse ciclo. Sem esse planejamento, os formulários de OS e Monitoramento MIP não encontram opções de talhão/cultura para aquela safra.

### Tela: Lista de Pragas

<figure>
  <img src="screenshots/cadastros_agro/09-pragas-lista.png" alt="Lista de Pragas">
  <figcaption>Cadastro de pragas e doenças (`/cadastros/pragas/`), usado pelo módulo MIP.</figcaption>
</figure>

### Tela: Formulário de Nova Praga

<figure>
  <img src="screenshots/cadastros_agro/16-praga-form.png" alt="Formulário de Nova Praga">
  <figcaption>Cadastro simples: nome comum (obrigatório), nome científico, tipo de praga e foto.</figcaption>
</figure>

### Tela: Lista de Poços/Bombas

<figure>
  <img src="screenshots/cadastros_agro/10-pocos-lista.png" alt="Lista de Poços/Bombas">
  <figcaption>Pontos de captação de água (`/cadastros/pocos/`) usados na irrigação.</figcaption>
</figure>

### Tela: Formulário de Novo Poço

<figure>
  <img src="screenshots/cadastros_agro/17-poco-form.png" alt="Formulário de Novo Poço">
  <figcaption>Vincula o poço a uma fazenda e às áreas que ele irriga.</figcaption>
</figure>

**Como preencher:** escolha a **Fazenda** e as **Áreas** atendidas (múltipla escolha), dê um nome/identificação, e — se disponível — o tipo de bomba, potência (CV), profundidade, capacidade (m³/h), leitura inicial do horímetro e coordenadas. Todos esses técnicos são opcionais, mas quanto mais completos, melhor o controle de manutenção da bomba.

### Dicas e erros comuns

- Um Talhão sempre pertence a uma Área, que sempre pertence a uma Fazenda — cadastre nessa ordem, senão os seletores em cascata dos outros formulários (OS, MIP) ficam vazios.
- Uma Safra sem talhões/culturas associados (planejamento) não aparece nas opções de Ordem de Serviço nem no Planejamento de Custo — o cadastro da safra sozinho não basta.

## Ordens de Serviço (`/campo/ordens-servico/`)

### Visão geral

A Ordem de Serviço (OS) é o registro central de qualquer operação de campo: colheita, plantio (incluindo transplante e replantio), pulverização, adubação, preparo de solo, entre outras. Toda OS acumula três frentes de custo — **mão de obra**, **maquinário** e **insumos** — e ao final apura o custo total e o custo por hectare, que alimentam o Custo por Talhão/Safra e o Planejamento de Custo.

### Status e ciclo de vida

```
Aberta → Aprovada → Em Andamento → Concluída
```

Uma OS também pode ser **pausada** e **retomada** por um administrador durante a execução, e pode ficar bloqueada aguardando **horímetro pendente** quando envolve máquina cujo horímetro final ainda não foi lançado. Ao concluir a OS, o sistema desconta os insumos do estoque e — quando aplicável — atualiza o status de lotes de mudas envolvidos (transplante) ou registra a colheita.

### Tela: Lista de Ordens de Serviço

<figure>
  <img src="screenshots/operacoes_campo/01-os-lista.png" alt="Lista de Ordens de Serviço">
  <figcaption>OS cadastradas, com tipo de serviço, talhão, safra e status.</figcaption>
</figure>

### Tela: Detalhe da Ordem de Serviço

<figure>
  <img src="screenshots/operacoes_campo/02-os-detalhe.png" alt="Detalhe de uma Ordem de Serviço">
  <figcaption>Linha do tempo do status, custos por categoria (mão de obra/maquinário/insumos) e abas de Execução, Evidências, Custos, Histórico e Colheita.</figcaption>
</figure>

As abas da OS organizam: **Execução** (funcionários e máquinas alocados), **Evidências** (fotos anexadas no campo, geralmente via portal do campo), **Custos** (detalhamento por item), **Histórico** (linha do tempo de mudanças) e, quando aplicável, **Colheita** (quantidade colhida).

### Tela: Nova Ordem de Serviço

<figure>
  <img src="screenshots/operacoes_campo/03-os-nova.png" alt="Formulário de Nova Ordem de Serviço">
  <figcaption>Formulário em 6 abas: Identificação, Serviço Externo, Mão de Obra, Maquinário, Custo Estimado, Evidência Fotográfica.</figcaption>
</figure>

**Como preencher (aba Identificação):**

| Campo | Obrigatório | Descrição |
|---|---|---|
| Tipo de Serviço | Sim | Ex: Colheita, Plantio, Pulverização — define as opções de Operação abaixo |
| Operação | Não | Sub-tipo da operação; só habilita depois de escolher o Tipo de Serviço |
| Modalidade de Execução | Não | Ex: manual, mecanizada |
| Safra | Não | Auto-preenchida a partir do talhão, quando possível; senão escolha manualmente — filtra as opções de Cultura |
| Cultura da Safra | Não | Filtrada pela Safra escolhida |
| Talhão | Sim | Busca com autocomplete; ao escolher, mostra a "Cultura Atual" do talhão |
| Responsável pela Execução | Não | Busca de funcionário |
| Data Prevista | Não | Data planejada de execução |
| Área Executada (ha) | Não | Preenchido na conclusão, se diferente da área total do talhão |
| Requisição de Insumos | Não | Vincula uma requisição de estoque já aberta a esta OS |
| Observações | Não | Texto livre |

Preencha a aba Identificação e salve; as demais abas (Mão de Obra, Maquinário, Custo Estimado) podem ser preenchidas depois, na tela de detalhe, conforme a execução avança — não é preciso ter tudo definido no momento da abertura da OS.

### Fluxo passo a passo — abrir e concluir uma OS

1. Escolha o **Tipo de Serviço** (isso libera as opções de Operação).
2. Escolha o **Talhão** (a Safra/Cultura são sugeridas automaticamente quando possível).
3. Salve para criar a OS — ela nasce com status **Aberta**.
4. Um aprovador aprova a OS → status **Aprovada**.
5. Ao iniciar a execução, o status muda para **Em Andamento**; nesse momento aloque mão de obra, máquinas e insumos nas respectivas abas.
6. Se necessário, a OS pode ser **pausada** e **retomada** durante a execução.
7. Ao concluir, informe a área executada (e, se for colheita, a quantidade colhida) → status **Concluída**. Nesse momento o sistema desconta os insumos do estoque, recalcula os custos totais e — se a OS for de Plantio/Transplante — atualiza o lote de mudas de origem.

### Tela: Painel de Delegação

<figure>
  <img src="screenshots/operacoes_campo/04-painel-delegacao.png" alt="Painel de Delegação">
  <figcaption>Visão consolidada para delegar OS às equipes de campo (usado junto com o Portal do Campo).</figcaption>
</figure>

### Tela: Custo por Talhão/Safra

<figure>
  <img src="screenshots/operacoes_campo/05-custo-talhao.png" alt="Custo por Talhão/Safra">
  <figcaption>Consolidação de todos os custos de OS por talhão e safra.</figcaption>
</figure>

### Tela: Planejamento de Custo

<figure>
  <img src="screenshots/operacoes_campo/06-planejamento-custo-lista.png" alt="Planejamento de Custo">
  <figcaption>Orçamento planejado de custos por safra/talhão, comparado ao custo real das OS.</figcaption>
</figure>

### Tela: Formulário de Planejamento de Custo

<figure>
  <img src="screenshots/operacoes_campo/16-planejamento-custo-form.png" alt="Formulário de Planejamento de Custo">
  <figcaption>Escolha de safra/talhão/cultura para orçar; itens diretos e indiretos são lançados depois, na tela de detalhe.</figcaption>
</figure>

O planejamento permite lançar itens diretos (insumos, mão de obra, máquinas) e indiretos, e simular a formação de preço do produto final com base no custo projetado. Depois de criado, compare periodicamente o planejado com o realizado (Custo por Talhão/Safra) para identificar desvios.

### Tela: Custo/Hora de Máquinas

<figure>
  <img src="screenshots/operacoes_campo/07-custos-maquina.png" alt="Custo/Hora de Máquinas">
  <figcaption>Tabela de custo por hora de cada máquina, usada para ratear o custo de maquinário nas OS.</figcaption>
</figure>

### Tela: Formulário de Custo/Hora de Máquina

<figure>
  <img src="screenshots/operacoes_campo/12-custo-maquina-form.png" alt="Formulário de Custo/Hora de Máquina">
  <figcaption>Define o valor por hora usado para calcular o custo de maquinário quando a máquina é alocada numa OS.</figcaption>
</figure>

### Tela: Pluviometria

<figure>
  <img src="screenshots/operacoes_campo/08-pluviometria.png" alt="Pluviometria">
  <figcaption>Registro de chuvas por fazenda/período.</figcaption>
</figure>

### Tela: Formulário de Registro de Chuva

<figure>
  <img src="screenshots/operacoes_campo/13-pluviometria-form.png" alt="Formulário de Registro de Chuva">
  <figcaption>Fazenda, data e volume (mm) registrado no pluviômetro.</figcaption>
</figure>

### Tela: Qualidade de Campo

<figure>
  <img src="screenshots/operacoes_campo/09-qualidade-campo.png" alt="Qualidade de Campo">
  <figcaption>Inspeções de qualidade registradas em campo, com geração de PDF.</figcaption>
</figure>

### Tela: Formulário de Inspeção de Qualidade

<figure>
  <img src="screenshots/operacoes_campo/14-qualidade-campo-form.png" alt="Formulário de Inspeção de Qualidade">
  <figcaption>Talhão/safra inspecionado, critérios avaliados e resultado.</figcaption>
</figure>

### Tela: Caderno de Campo

<figure>
  <img src="screenshots/operacoes_campo/10-caderno-campo.png" alt="Caderno de Campo">
  <figcaption>Registro formal de aplicações (insumos e mão de obra) por talhão, exigido para rastreabilidade agronômica.</figcaption>
</figure>

### Tela: Formulário de Caderno de Campo

<figure>
  <img src="screenshots/operacoes_campo/15-caderno-campo-form.png" alt="Formulário de Caderno de Campo">
  <figcaption>Registro inicial; insumos e funcionários são adicionados depois, na tela de detalhe.</figcaption>
</figure>

O Caderno de Campo existe para documentar formalmente, por talhão, o que foi aplicado (defensivo, fertilizante) e por quem — é o documento que sustenta uma auditoria de rastreabilidade agronômica ou uma certificação.

### Tela: Lotes de Produção

<figure>
  <img src="screenshots/operacoes_campo/11-lotes-producao.png" alt="Lotes de Produção">
  <figcaption>Lotes gerados a partir da colheita, usados na recepção do packing house.</figcaption>
</figure>

### Dicas e erros comuns

- Uma OS **pausada** não permite lançar novos custos até ser retomada por um administrador.
- Uma OS de tipo "Plantio" com subtipo Transplante ou Replantio atualiza automaticamente o status do lote de mudas de origem (em Estufas e Mudas) ao ser concluída — não é preciso atualizar o lote manualmente.
- O custo de uma OS só é considerado "final" após a conclusão; enquanto em andamento, os valores mostrados são parciais.
- Se o Talhão escolhido não tiver Safra/Cultura vinculada via planejamento, os campos de Safra e Cultura da OS ficam sem opções — volte ao cadastro da Safra e complete o planejamento primeiro.

## MIP — Manejo Integrado de Pragas (`/mip/`)

### Visão geral

O módulo MIP registra o monitoramento fitossanitário: visitas a talhões para inspecionar a presença de pragas/doenças, com múltiplos pontos de amostragem (georreferenciados) por praga monitorada. Diferente das demais operações de campo, o monitoramento MIP tem seu próprio ciclo de vida — incluindo um status pós-conclusão de **análise** — e pode opcionalmente gerar uma Ordem de Serviço (ex: para uma aplicação de defensivo recomendada a partir do resultado).

### Tela: Estágios de Desenvolvimento

<figure>
  <img src="screenshots/mip/01-estagios.png" alt="Estágios de Desenvolvimento">
  <figcaption>Estágios fenológicos da cultura (`/mip/estagios/`), usados para contextualizar o monitoramento.</figcaption>
</figure>

### Tela: Formulário de Novo Estágio

<figure>
  <img src="screenshots/mip/05-estagio-form.png" alt="Formulário de Novo Estágio">
  <figcaption>Cadastro do estágio fenológico associado a uma cultura.</figcaption>
</figure>

### Tela: Lista de Monitoramento MIP

<figure>
  <img src="screenshots/mip/02-monitoramento-lista.png" alt="Lista de Monitoramento MIP">
  <figcaption>Visitas de monitoramento registradas (`/mip/monitoramento/`).</figcaption>
</figure>

### Tela: Detalhe do Monitoramento MIP

<figure>
  <img src="screenshots/mip/03-monitoramento-detalhe.png" alt="Detalhe de um Monitoramento MIP">
  <figcaption>Pragas monitoradas na visita, cada uma com seus pontos de amostragem e nível de incidência calculado.</figcaption>
</figure>

### Tela: Formulário de Novo Monitoramento MIP

<figure>
  <img src="screenshots/mip/04-monitoramento-form.png" alt="Formulário de Novo Monitoramento MIP">
  <figcaption>Formulário em 3 abas: Informações Básicas, Condições Climáticas, Observações.</figcaption>
</figure>

**Como preencher (aba Informações Básicas):**

| Campo | Obrigatório | Descrição |
|---|---|---|
| Safra Ativa | Sim | Só lista safras em andamento |
| Cultura | Sim | Habilita depois de escolher a Safra |
| Talhão | Sim | Habilita depois de escolher a Cultura |
| Data do Monitoramento | Sim | Data da visita a campo |
| Tipo de Monitoramento | Sim | Ex: "Monitoramento Regular" |
| Responsável (Pragueiro) | Sim | Funcionário que fez a visita |
| Quantidade de Pontos | Sim | Número de pontos de amostragem a percorrer no talhão (padrão sugerido: 20) |

A aba **Condições Climáticas** registra temperatura/umidade/vento do dia da visita (relevante para interpretar a incidência). Depois de criado o monitoramento, use a tela de detalhe para **adicionar cada praga** observada e, para cada uma, lançar os **pontos de amostragem**.

### Fluxo passo a passo — monitorar e agir

1. Crie o monitoramento informando safra/cultura/talhão/data/responsável.
2. Na tela de detalhe, **adicione cada praga** encontrada na visita.
3. Para cada praga, registre os **pontos de amostragem** (idealmente todos os pontos previstos) — é isso que alimenta o cálculo de incidência.
4. Avalie o nível de incidência calculado; se justificar tratamento, use o botão **Gerar OS** para criar automaticamente uma Ordem de Serviço de tratamento com talhão/safra já preenchidos.
5. Gere o **PDF** do laudo se precisar arquivar ou compartilhar o resultado.

### Dicas e erros comuns

- O nível de incidência é calculado a partir dos pontos de amostragem lançados — quanto mais pontos cobertos (idealmente os 20 previstos), mais preciso o cálculo.
- Gerar OS a partir do monitoramento evita ter que recriar manualmente os dados de talhão/safra na nova ordem de serviço.

## Estufas e Mudas (`/estufas/`)

### Visão geral

Controla a produção de mudas em estufa antes do transplante para o talhão definitivo: cadastro das estufas físicas, lotes de mudas em produção, aplicações e perdas registradas durante o cultivo em estufa, e o avanço de status do lote até o transplante.

### Tela: Dashboard de Estufas

<figure>
  <img src="screenshots/estufas/01-dashboard.png" alt="Dashboard de Estufas">
  <figcaption>Indicadores gerais de produção de mudas.</figcaption>
</figure>

### Tela: Lista de Estufas

<figure>
  <img src="screenshots/estufas/02-estufas-lista.png" alt="Lista de Estufas">
  <figcaption>Estufas cadastradas (`/estufas/`).</figcaption>
</figure>

### Tela: Formulário de Nova Estufa

<figure>
  <img src="screenshots/estufas/05-estufa-form.png" alt="Formulário de Nova Estufa">
  <figcaption>Cadastro da estufa física (identificação, capacidade e fazenda vinculada).</figcaption>
</figure>

### Tela: Lista de Lotes de Mudas

<figure>
  <img src="screenshots/estufas/03-lotes-mudas-lista.png" alt="Lista de Lotes de Mudas">
  <figcaption>Lotes de mudas em produção (`/estufas/lotes/`), com status do ciclo.</figcaption>
</figure>

### Tela: Detalhe do Lote de Mudas

<figure>
  <img src="screenshots/estufas/04-lote-mudas-detalhe.png" alt="Detalhe de um Lote de Mudas">
  <figcaption>Aplicações, perdas e monitoramentos registrados durante o cultivo do lote em estufa.</figcaption>
</figure>

### Tela: Formulário de Novo Lote de Mudas

<figure>
  <img src="screenshots/estufas/06-lote-mudas-form.png" alt="Formulário de Novo Lote de Mudas">
  <figcaption>Estufa, cultura, cultivar, datas de semeadura e transplantio previsto.</figcaption>
</figure>

**Como preencher:**

| Campo | Obrigatório | Descrição |
|---|---|---|
| Estufa | Sim | Onde o lote será cultivado |
| Cultura | Sim | O que está sendo semeado |
| Cultivar | Não | Variedade/híbrido específico (ex: "Híbrido BRS-12") |
| Lote da Semente | Não | Código do lote de origem da semente, para rastreabilidade |
| Data de Semeadura | Sim | Início do ciclo em estufa |
| Quantidade Semeada | Sim | Total de sementes/mudas |
| Data Prevista (Transplantio) | Não | Estimativa de quando o lote estará pronto para ir a campo |
| Responsável | Não | Funcionário responsável pelo lote |

### Fluxo passo a passo — da semeadura ao transplante

1. Cadastre o lote com estufa, cultura e data de semeadura.
2. Ao longo do ciclo, registre **aplicações** (defensivos/fertilizantes) e **perdas** na tela de detalhe do lote — isso mantém o custo do lote preciso.
3. Quando pronto, abra uma **Ordem de Serviço** do tipo Plantio/Transplante referenciando este lote.
4. Ao **concluir** essa OS, o sistema marca automaticamente o lote como **transplantado** — não é necessário voltar aqui para atualizar o status manualmente.

### Dicas e erros comuns

- Registrar perdas e aplicações ao longo do ciclo (não só no fim) mantém o custo do lote de mudas mais preciso quando ele é transferido para o custo do talhão no transplante.
