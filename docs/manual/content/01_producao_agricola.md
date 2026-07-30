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

### Tela: Lista de Áreas

<figure>
  <img src="screenshots/cadastros_agro/03-areas-lista.png" alt="Lista de Áreas">
  <figcaption>Áreas cadastradas (`/cadastros/areas/`), sempre vinculadas a uma fazenda.</figcaption>
</figure>

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

### Tela: Lista de Culturas

<figure>
  <img src="screenshots/cadastros_agro/06-culturas-lista.png" alt="Lista de Culturas">
  <figcaption>Culturas cadastradas (`/cadastros/culturas/`).</figcaption>
</figure>

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

### Tela: Lista de Pragas

<figure>
  <img src="screenshots/cadastros_agro/09-pragas-lista.png" alt="Lista de Pragas">
  <figcaption>Cadastro de pragas e doenças (`/cadastros/pragas/`), usado pelo módulo MIP.</figcaption>
</figure>

### Tela: Lista de Poços/Bombas

<figure>
  <img src="screenshots/cadastros_agro/10-pocos-lista.png" alt="Lista de Poços/Bombas">
  <figcaption>Pontos de captação de água (`/cadastros/pocos/`) usados na irrigação.</figcaption>
</figure>

### Dicas e erros comuns

- Um Talhão sempre pertence a uma Área, que sempre pertence a uma Fazenda — cadastre nessa ordem.
- Uma Safra sem talhões/culturas associados não aparece nas opções de Ordem de Serviço nem no Planejamento de Custo.

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
  <figcaption>Escolha de tipo/subtipo de serviço, talhão, safra e datas planejadas.</figcaption>
</figure>

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

O planejamento de custo permite lançar itens diretos (insumos, mão de obra, máquinas) e indiretos, e simular a formação de preço do produto final com base no custo projetado.

### Tela: Custo/Hora de Máquinas

<figure>
  <img src="screenshots/operacoes_campo/07-custos-maquina.png" alt="Custo/Hora de Máquinas">
  <figcaption>Tabela de custo por hora de cada máquina, usada para ratear o custo de maquinário nas OS.</figcaption>
</figure>

### Tela: Pluviometria

<figure>
  <img src="screenshots/operacoes_campo/08-pluviometria.png" alt="Pluviometria">
  <figcaption>Registro de chuvas por fazenda/período.</figcaption>
</figure>

### Tela: Qualidade de Campo

<figure>
  <img src="screenshots/operacoes_campo/09-qualidade-campo.png" alt="Qualidade de Campo">
  <figcaption>Inspeções de qualidade registradas em campo, com geração de PDF.</figcaption>
</figure>

### Tela: Caderno de Campo

<figure>
  <img src="screenshots/operacoes_campo/10-caderno-campo.png" alt="Caderno de Campo">
  <figcaption>Registro formal de aplicações (insumos e mão de obra) por talhão, exigido para rastreabilidade agronômica.</figcaption>
</figure>

### Tela: Lotes de Produção

<figure>
  <img src="screenshots/operacoes_campo/11-lotes-producao.png" alt="Lotes de Produção">
  <figcaption>Lotes gerados a partir da colheita, usados na recepção do packing house.</figcaption>
</figure>

### Dicas e erros comuns

- Uma OS **pausada** não permite lançar novos custos até ser retomada por um administrador.
- Uma OS de tipo "Plantio" com subtipo Transplante ou Replantio atualiza automaticamente o status do lote de mudas de origem (em Estufas e Mudas) ao ser concluída — não é preciso atualizar o lote manualmente.
- O custo de uma OS só é considerado "final" após a conclusão; enquanto em andamento, os valores mostrados são parciais.

## MIP — Manejo Integrado de Pragas (`/mip/`)

### Visão geral

O módulo MIP registra o monitoramento fitossanitário: visitas a talhões para inspecionar a presença de pragas/doenças, com múltiplos pontos de amostragem (georreferenciados) por praga monitorada. Diferente das demais operações de campo, o monitoramento MIP tem seu próprio ciclo de vida — incluindo um status pós-conclusão de **análise** — e pode opcionalmente gerar uma Ordem de Serviço (ex: para uma aplicação de defensivo recomendada a partir do resultado).

### Tela: Estágios de Desenvolvimento

<figure>
  <img src="screenshots/mip/01-estagios.png" alt="Estágios de Desenvolvimento">
  <figcaption>Estágios fenológicos da cultura (`/mip/estagios/`), usados para contextualizar o monitoramento.</figcaption>
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

A partir do detalhe é possível **adicionar uma praga** à visita, registrar os **pontos de amostragem** de cada praga, gerar o **PDF** do laudo, e — se a incidência justificar — **gerar uma Ordem de Serviço** de tratamento diretamente a partir do monitoramento.

### Dicas e erros comuns

- O nível de incidência é calculado a partir dos pontos de amostragem lançados — quanto mais pontos, mais preciso o cálculo.
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

O lote de mudas avança por estágios até ficar pronto para o transplante. Quando uma Ordem de Serviço do tipo Plantio/Transplante referente a esse lote é concluída no módulo de Ordens de Serviço, o lote é automaticamente marcado como **transplantado** — não é necessário atualizar o status manualmente aqui.

### Dicas e erros comuns

- Registrar perdas e aplicações ao longo do ciclo (não só no fim) mantém o custo do lote de mudas mais preciso quando ele é transferido para o custo do talhão no transplante.
