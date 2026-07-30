# Infraestrutura

## Energia Solar (`/energia/`)

### Visão geral

Acompanha a geração de energia solar da empresa: usinas fotovoltaicas próprias, as unidades consumidoras que recebem os créditos de energia gerados (compensação de energia entre unidades, comum em sistemas de geração distribuída), lançamentos mensais de geração/consumo, relatórios por usina e ocorrências (falhas, manutenções).

### Conceitos principais

| Conceito | Papel |
|---|---|
| Usina Fotovoltaica | Instalação geradora (capacidade em kWp, geração mensal/anual acordada) |
| Unidade Consumidora | Ponto de consumo — pode ser **geradora** (onde os painéis estão), **beneficiária** (recebe créditos) ou **convencional** (sem energia solar) |
| Lançamento Mensal | Registro mensal de geração e consumo, usado para acompanhar o desempenho frente ao acordado |
| Ocorrência | Falha ou evento registrado numa usina (queda de geração, manutenção, etc.) |

### Tela: Dashboard de Energia

<figure>
  <img src="screenshots/energia/01-dashboard.png" alt="Dashboard de Energia">
  <figcaption>Indicadores gerais de geração e consumo do período.</figcaption>
</figure>

### Tela: Consolidado / Ranking

<figure>
  <img src="screenshots/energia/02-consolidado.png" alt="Consolidado / Ranking">
  <figcaption>Comparativo entre usinas e unidades consumidoras, com ranking de desempenho.</figcaption>
</figure>

### Tela: Lista de Usinas

<figure>
  <img src="screenshots/energia/03-usinas-lista.png" alt="Lista de Usinas">
  <figcaption>Usinas fotovoltaicas cadastradas (`/energia/usinas/`).</figcaption>
</figure>

### Tela: Detalhe da Usina

<figure>
  <img src="screenshots/energia/04-usina-detalhe.png" alt="Detalhe de uma Usina">
  <figcaption>Capacidade instalada, geração acordada e histórico de lançamentos/ocorrências da usina.</figcaption>
</figure>

### Tela: Unidades Consumidoras

<figure>
  <img src="screenshots/energia/05-unidades-lista.png" alt="Unidades Consumidoras">
  <figcaption>Unidades consumidoras (`/energia/unidades/`), classificadas como geradora, beneficiária ou convencional.</figcaption>
</figure>

### Tela: Lançamentos Mensais

<figure>
  <img src="screenshots/energia/06-lancamentos-lista.png" alt="Lançamentos Mensais">
  <figcaption>Lançamentos de geração/consumo por mês (`/energia/lancamentos/`).</figcaption>
</figure>

### Tela: Relatórios de Usina

<figure>
  <img src="screenshots/energia/07-relatorios-usina.png" alt="Relatórios de Usina">
  <figcaption>Relatórios consolidados por usina e período.</figcaption>
</figure>

### Tela: Ocorrências

<figure>
  <img src="screenshots/energia/08-ocorrencias-lista.png" alt="Ocorrências">
  <figcaption>Ocorrências registradas por usina (`/energia/ocorrencias/`), com opção de marcar como resolvida.</figcaption>
</figure>

### Dicas e erros comuns

- Uma queda de geração recorrente numa usina deve ser registrada como **ocorrência**, não só observada no lançamento mensal — isso mantém o histórico de problemas rastreável.
- O prognóstico mensal serve de referência para identificar desvios; geração muito abaixo do prognóstico é o principal sinal de alerta a acompanhar no Consolidado.
