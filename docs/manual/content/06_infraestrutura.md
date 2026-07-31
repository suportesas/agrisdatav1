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

### Tela: Formulário de Nova Usina

<figure>
  <img src="screenshots/energia/09-usina-form.png" alt="Formulário de Nova Usina">
  <figcaption>Código, nome, capacidade instalada e geração acordada.</figcaption>
</figure>

**Como preencher:**

| Campo | Obrigatório | Descrição |
|---|---|---|
| Código | Sim | Identificador único da usina na empresa |
| Nome/Descrição | Sim | |
| Capacidade (kWp) | Sim | Potência instalada |
| Geração Acordada Mensal/Anual (kWh) | Não | Valor contratado/esperado, usado como referência para comparar com a geração real |
| Prognóstico Mensal (kWh) | Não | Estimativa técnica de geração, mais granular que o valor acordado |
| Data de Instalação | Não | |

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

### Tela: Formulário de Nova Unidade Consumidora

<figure>
  <img src="screenshots/energia/10-unidade-form.png" alt="Formulário de Nova Unidade Consumidora">
  <figcaption>Número da UC (concessionária), tipo e, se beneficiária, a usina de origem dos créditos.</figcaption>
</figure>

**Como preencher:** informe o número da unidade consumidora (conforme a concessionária de energia), o **Tipo** (Geradora/Beneficiária/Convencional) e, se Beneficiária, a usina que fornece os créditos de compensação.

### Tela: Lançamentos Mensais

<figure>
  <img src="screenshots/energia/06-lancamentos-lista.png" alt="Lançamentos Mensais">
  <figcaption>Lançamentos de geração/consumo por mês (`/energia/lancamentos/`).</figcaption>
</figure>

### Tela: Formulário de Novo Lançamento Mensal

<figure>
  <img src="screenshots/energia/11-lancamento-form.png" alt="Formulário de Novo Lançamento Mensal">
  <figcaption>Usina/unidade, mês de referência, geração e consumo do período.</figcaption>
</figure>

**Como preencher:** escolha a usina ou unidade consumidora, o **mês de referência**, e informe a geração e/ou consumo (kWh) do período, normalmente lidos da fatura da concessionária ou do sistema de monitoramento da usina.

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

### Tela: Formulário de Nova Ocorrência

<figure>
  <img src="screenshots/energia/12-ocorrencia-form.png" alt="Formulário de Nova Ocorrência">
  <figcaption>Usina afetada, tipo de ocorrência, data e descrição.</figcaption>
</figure>

### Fluxo passo a passo — acompanhar a geração mensal

1. Cadastre a **Usina** com capacidade e geração acordada.
2. Vincule as **Unidades Consumidoras** beneficiárias à usina.
3. Todo mês, registre o **Lançamento Mensal** de geração (da usina) e consumo (de cada unidade).
4. Compare no **Consolidado** a geração real contra o acordado/prognóstico.
5. Se houver queda de geração ou falha, registre uma **Ocorrência** — isso mantém o histórico de problemas rastreável, em vez de só observar no lançamento mensal.
6. Marque a ocorrência como **resolvida** quando o problema for sanado.

### Dicas e erros comuns

- Uma queda de geração recorrente numa usina deve ser registrada como **ocorrência**, não só observada no lançamento mensal — isso mantém o histórico de problemas rastreável.
- O prognóstico mensal serve de referência para identificar desvios; geração muito abaixo do prognóstico é o principal sinal de alerta a acompanhar no Consolidado.
