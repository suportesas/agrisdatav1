# Pessoas & Parceiros

## Cadastros de Parceiros (`/cadastros/`)

### Visão geral

Reúne os cadastros de todas as pessoas físicas e jurídicas com quem a empresa se relaciona comercialmente: **Clientes** (quem compra), **Produtores** (fornecedores de matéria-prima agrícola, muitas vezes com acesso a um portal próprio), **Fornecedores** (quem vende insumos/serviços), **Transportadoras** e **Vendedores** internos.

### Tela: Lista de Clientes

<figure>
  <img src="screenshots/cadastros_pessoas/01-clientes-lista.png" alt="Lista de Clientes">
  <figcaption>Clientes cadastrados (`/cadastros/clientes/`).</figcaption>
</figure>

### Tela: Detalhe do Cliente

<figure>
  <img src="screenshots/cadastros_pessoas/02-cliente-detalhe.png" alt="Detalhe de um Cliente">
  <figcaption>Dados gerais, endereços, contatos, contas bancárias e documentos do cliente.</figcaption>
</figure>

### Tela: Formulário de Novo Cliente

<figure>
  <img src="screenshots/cadastros_pessoas/09-cliente-form.png" alt="Formulário de Novo Cliente">
  <figcaption>Formulário em 4 abas: Dados Básicos, Documentação Fiscal, Exportação/Importação, Dados Comerciais.</figcaption>
</figure>

**Como preencher (aba Dados Básicos):**

| Campo | Obrigatório | Descrição |
|---|---|---|
| Razão Social / Nome | Sim | Nome oficial do cliente |
| Nome Comercial | Não | Nome fantasia, se houver |
| CNPJ/CPF | Sim | O botão **Buscar** preenche dados automaticamente para CNPJ |
| Tipo Cliente | Não | Nacional ou Internacional — se Internacional, habilita a aba Exportação/Importação com dados de câmbio/país |
| Tipo Pessoa | Não | Física ou Jurídica |
| Contato Principal (nome/telefone/e-mail) | Não | Contato de referência rápida |

A aba **Documentação Fiscal** guarda inscrição estadual e regime tributário; **Exportação/Importação** só é relevante para clientes internacionais (moeda padrão, país, INCOTERM); **Dados Comerciais** guarda condições de pagamento e vendedor responsável padrão.

### Tela: Lista de Produtores

<figure>
  <img src="screenshots/cadastros_pessoas/03-produtores-lista.png" alt="Lista de Produtores">
  <figcaption>Produtores rurais cadastrados (`/cadastros/produtores/`).</figcaption>
</figure>

### Tela: Detalhe do Produtor

<figure>
  <img src="screenshots/cadastros_pessoas/04-produtor-detalhe.png" alt="Detalhe de um Produtor">
  <figcaption>Dados do produtor; a partir daqui é possível criar acesso ao Portal do Produtor.</figcaption>
</figure>

### Tela: Formulário de Novo Produtor

<figure>
  <img src="screenshots/cadastros_pessoas/10-produtor-form.png" alt="Formulário de Novo Produtor">
  <figcaption>Dados cadastrais do produtor rural.</figcaption>
</figure>

**Como preencher:** os campos obrigatórios são nome/razão social e CPF/CNPJ; o restante (endereço, contato, dados bancários) pode ser complementado depois. Depois de salvo, use o botão **Criar Acesso Portal** na tela de detalhe para gerar um login de autoatendimento para esse produtor.

### Tela: Lista de Fornecedores

<figure>
  <img src="screenshots/cadastros_pessoas/05-fornecedores-lista.png" alt="Lista de Fornecedores">
  <figcaption>Fornecedores cadastrados (`/cadastros/fornecedores/`).</figcaption>
</figure>

### Tela: Detalhe do Fornecedor

<figure>
  <img src="screenshots/cadastros_pessoas/06-fornecedor-detalhe.png" alt="Detalhe de um Fornecedor">
  <figcaption>Dados cadastrais, histórico de compras e acesso ao Portal do Fornecedor.</figcaption>
</figure>

### Tela: Formulário de Novo Fornecedor

<figure>
  <img src="screenshots/cadastros_pessoas/11-fornecedor-form.png" alt="Formulário de Novo Fornecedor">
  <figcaption>Estrutura em abas equivalente ao Cliente: dados básicos, documentação fiscal, categoria de fornecimento.</figcaption>
</figure>

**Como preencher:** obrigatório é Razão Social/Nome e CNPJ/CPF (com o mesmo botão de busca automática). Vale já classificar a **categoria** do fornecedor (ex: insumos, serviços, transporte) — isso é usado nos relatórios de ranking de fornecedores por categoria.

### Tela: Lista de Transportadoras

<figure>
  <img src="screenshots/cadastros_pessoas/07-transportadoras-lista.png" alt="Lista de Transportadoras">
  <figcaption>Transportadoras cadastradas (`/cadastros/transportadoras/`), usadas em CT-e e MDF-e.</figcaption>
</figure>

### Tela: Formulário de Nova Transportadora

<figure>
  <img src="screenshots/cadastros_pessoas/12-transportadora-form.png" alt="Formulário de Nova Transportadora">
  <figcaption>Dados cadastrais e tabela de frete da transportadora.</figcaption>
</figure>

**Como preencher:** além dos dados cadastrais básicos (nome, CNPJ, RNTRC), a transportadora pode ter uma **tabela de frete** própria, editável depois na tela de detalhe (botão "Atualizar Frete") — usada para sugerir valores automaticamente ao gerar um CT-e a partir de um romaneio.

### Tela: Lista de Vendedores

<figure>
  <img src="screenshots/cadastros_pessoas/08-vendedores-lista.png" alt="Lista de Vendedores">
  <figcaption>Vendedores internos (`/cadastros/vendedores/`), vinculados aos pedidos de venda.</figcaption>
</figure>

### Tela: Formulário de Novo Vendedor

<figure>
  <img src="screenshots/cadastros_pessoas/13-vendedor-form.png" alt="Formulário de Novo Vendedor">
  <figcaption>Cadastro simples: nome, contato e comissão padrão.</figcaption>
</figure>

### Dicas e erros comuns

- Um cliente/fornecedor **inativo** não é excluído — apenas some das buscas de uso corrente, preservando o histórico de documentos já emitidos.
- Bloquear o acesso ao portal de um produtor/fornecedor não apaga o cadastro dele, só impede o login externo.
- Use sempre a **busca por CNPJ** ao cadastrar pessoa jurídica — evita erro de digitação em razão social/endereço.

## Frota (`/frota/`)

### Visão geral

Controla veículos e máquinas da empresa: dados cadastrais, histórico de valor, abastecimentos, manutenções, pedágios, viagens e telemetria. Também gerencia os **motoristas** e o vínculo entre motorista e veículo/placa ao longo do tempo — importante porque um mesmo veículo pode trocar de motorista e um motorista pode dirigir vários veículos.

### Tela: Dashboard de Frota

<figure>
  <img src="screenshots/frota/01-dashboard.png" alt="Dashboard de Frota">
  <figcaption>Indicadores gerais da frota: veículos ativos, alertas de manutenção, custos recentes.</figcaption>
</figure>

### Tela: Lista de Veículos

<figure>
  <img src="screenshots/frota/02-veiculos-lista.png" alt="Lista de Veículos">
  <figcaption>Veículos e máquinas cadastrados (`/frota/veiculos/`).</figcaption>
</figure>

### Tela: Detalhe do Veículo

<figure>
  <img src="screenshots/frota/03-veiculo-detalhe.png" alt="Detalhe de um Veículo">
  <figcaption>Dados do veículo, histórico de placas, valor e documentos vinculados.</figcaption>
</figure>

### Tela: Formulário de Novo Veículo

<figure>
  <img src="screenshots/frota/12-veiculo-form.png" alt="Formulário de Novo Veículo">
  <figcaption>Formulário em 6 abas, com caixa de ajuda explicando as regras de preenchimento.</figcaption>
</figure>

**Como preencher (aba Identificação)** — o próprio formulário traz uma caixa de ajuda com estas três regras:

| Regra | Explicação |
|---|---|
| Origem | Se **Terceiro**, é obrigatório informar a transportadora dona do veículo. Se **Próprio** (frota da empresa), a transportadora não é necessária |
| Placas | São opcionais neste formulário — para veículos com placa (carros, caminhões), cadastre a placa **depois**, na tela de detalhe do veículo já criado |
| Implementos/tratores sem placa | Use apenas os campos "Nome/Descrição" e/ou "Código de Patrimônio" para identificá-los, já que não têm placa |

Demais campos da aba Identificação: **Tipo** (Leve, Pesado, Máquina/Implemento), Marca, Modelo, Cor — todos opcionais, mas recomendados. As abas seguintes cobrem Documentação Técnica (RENAVAM, ano/fabricação), Vínculo e Status (transportadora/motorista padrão), Valorização (valor de aquisição, para o histórico de valor), Especificações Físicas e Observações.

### Fluxo passo a passo — cadastrar um veículo com placa

1. Preencha a aba Identificação (Origem, Tipo, Marca/Modelo) e salve.
2. Abra o veículo recém-criado e adicione a **placa** na seção correspondente da tela de detalhe.
3. Se for veículo de terceiro, confirme que a Transportadora está corretamente vinculada — é ela quem aparece nos documentos fiscais de frete.

### Tela: Combustível/Abastecimentos

<figure>
  <img src="screenshots/frota/04-abastecimentos.png" alt="Abastecimentos">
  <figcaption>Registros de abastecimento (`/frota/abastecimentos/`), com opção de importação em lote via CSV.</figcaption>
</figure>

### Tela: Formulário de Novo Abastecimento

<figure>
  <img src="screenshots/frota/14-abastecimento-form.png" alt="Formulário de Novo Abastecimento">
  <figcaption>Veículo, data, litros, valor e odômetro no momento do abastecimento.</figcaption>
</figure>

Para abastecimentos em volume (ex: frota grande), use o botão **Importar CSV** na lista em vez de lançar um a um.

### Tela: Manutenções

<figure>
  <img src="screenshots/frota/05-manutencoes.png" alt="Manutenções">
  <figcaption>Manutenções preventivas/corretivas (`/frota/manutencoes/`), com itens e alertas programados.</figcaption>
</figure>

### Tela: Formulário de Nova Manutenção

<figure>
  <img src="screenshots/frota/15-manutencao-form.png" alt="Formulário de Nova Manutenção">
  <figcaption>Veículo, tipo (preventiva/corretiva), data e itens de serviço realizados.</figcaption>
</figure>

### Tela: Pedágios

<figure>
  <img src="screenshots/frota/06-pedagios.png" alt="Pedágios">
  <figcaption>Registros de pedágio por veículo/viagem.</figcaption>
</figure>

### Tela: Viagens

<figure>
  <img src="screenshots/frota/07-viagens.png" alt="Viagens">
  <figcaption>Viagens realizadas, associando veículo, motorista e trajeto.</figcaption>
</figure>

### Tela: Telemetria

<figure>
  <img src="screenshots/frota/08-telemetria.png" alt="Telemetria">
  <figcaption>Dados de telemetria recebidos dos veículos (quando integrados).</figcaption>
</figure>

### Tela: Alertas

<figure>
  <img src="screenshots/frota/09-alertas.png" alt="Alertas">
  <figcaption>Alertas de manutenção/documentação vencendo.</figcaption>
</figure>

### Tela: Lista de Motoristas

<figure>
  <img src="screenshots/frota/10-motoristas-lista.png" alt="Lista de Motoristas">
  <figcaption>Motoristas cadastrados (`/frota/motoristas/`); podem receber PIN de acesso ao Portal do Motorista.</figcaption>
</figure>

### Tela: Formulário de Novo Motorista

<figure>
  <img src="screenshots/frota/13-motorista-form.png" alt="Formulário de Novo Motorista">
  <figcaption>Dados pessoais, CNH e categoria de habilitação.</figcaption>
</figure>

**Como preencher:** nome, CPF e número/categoria da CNH são obrigatórios. Depois de criado, use **Portal-Acesso** na tela de detalhe para gerar o PIN de login do Portal do Motorista.

### Tela: Vínculos Motorista x Frota

<figure>
  <img src="screenshots/frota/11-vinculos-lista.png" alt="Vínculos Motorista x Frota">
  <figcaption>Histórico de qual motorista esteve vinculado a qual veículo/placa em cada período.</figcaption>
</figure>

### Dicas e erros comuns

- O histórico de **vínculos** é o que permite saber, numa data específica, qual motorista estava com qual veículo — útil para investigar multas ou ocorrências antigas.
- Documentos de veículo/motorista vencidos disparam **alertas**; vale revisar essa tela periodicamente.
- Veículo de terceiro sem transportadora vinculada trava a emissão de documentos fiscais de frete — cadastre a transportadora antes do veículo, se possível.

## RH (`/rh/`)

### Visão geral

Gestão de funcionários: dados cadastrais, funções/cargos, férias, afastamentos, vínculos contratuais, riscos ambientais/laudos (SST) e ASO (Atestado de Saúde Ocupacional). Funcionários cadastrados aqui são referenciados pelas Ordens de Serviço (mão de obra) e podem receber PIN de acesso ao Portal do Campo.

### Tela: Dashboard de RH

<figure>
  <img src="screenshots/rh/01-dashboard.png" alt="Dashboard de RH">
  <figcaption>Indicadores gerais: funcionários ativos, férias e ASOs próximos do vencimento.</figcaption>
</figure>

### Tela: Lista de Funcionários

<figure>
  <img src="screenshots/rh/02-funcionarios-lista.png" alt="Lista de Funcionários">
  <figcaption>Funcionários cadastrados (`/rh/funcionarios/`).</figcaption>
</figure>

### Tela: Detalhe do Funcionário

<figure>
  <img src="screenshots/rh/03-funcionario-detalhe.png" alt="Detalhe de um Funcionário">
  <figcaption>Dados cadastrais, função, documentos e PIN de acesso ao Portal do Campo.</figcaption>
</figure>

### Tela: Formulário de Novo Funcionário

<figure>
  <img src="screenshots/rh/11-funcionario-form.png" alt="Formulário de Novo Funcionário">
  <figcaption>Formulário em 8 abas: Dados Pessoais, Contato, Endereço, Dados Profissionais, Dados Bancários, Contato de Emergência, Observações e Foto, Documentos.</figcaption>
</figure>

**Como preencher (aba Dados Pessoais):**

| Campo | Obrigatório | Descrição |
|---|---|---|
| Nome Completo | Sim | |
| Código da Matrícula | Não | Se vazio, pode ser gerado automaticamente (ex: MAT-0001) |
| CPF | Sim | |
| RG, Data de Nascimento, Gênero, Estado Civil | Não | Complementares |

A aba **Dados Profissionais** (na sequência) é onde se define a **Função/Cargo** — obrigatória para o funcionário ser corretamente rateado em custo de mão de obra nas Ordens de Serviço. As demais abas (Contato, Endereço, Dados Bancários, Contato de Emergência, Documentos) podem ser completadas depois.

### Fluxo passo a passo — admitir um funcionário

1. Preencha Dados Pessoais e salve (ou avance pelas abas antes de salvar, se preferir preencher tudo de uma vez).
2. Na aba Dados Profissionais, defina a **Função** — sem isso, o custo de mão de obra do funcionário não é corretamente calculado nas OS.
3. Se o funcionário vai atuar em campo com apontamento próprio, gere o **PIN de acesso ao Portal do Campo** na tela de detalhe.
4. Registre o **Vínculo Contratual** correspondente (CLT, temporário, etc.) no submenu Vínculos.

### Tela: Funções/Cargos

<figure>
  <img src="screenshots/rh/04-funcoes-lista.png" alt="Funções/Cargos">
  <figcaption>Cadastro de funções (`/rh/funcoes/`), com faixa salarial de referência.</figcaption>
</figure>

### Tela: Formulário de Nova Função

<figure>
  <img src="screenshots/rh/12-funcao-form.png" alt="Formulário de Nova Função">
  <figcaption>Nome da função e salário de referência (usado para sugerir salário ao vincular um funcionário).</figcaption>
</figure>

### Tela: Férias

<figure>
  <img src="screenshots/rh/05-ferias-lista.png" alt="Férias">
  <figcaption>Controle de períodos de férias, com relatório de previsão em PDF.</figcaption>
</figure>

### Tela: Formulário de Novas Férias

<figure>
  <img src="screenshots/rh/13-ferias-form.png" alt="Formulário de Novas Férias">
  <figcaption>Funcionário, período aquisitivo e datas de gozo.</figcaption>
</figure>

### Tela: Afastamentos

<figure>
  <img src="screenshots/rh/06-afastamentos-lista.png" alt="Afastamentos">
  <figcaption>Afastamentos registrados (licença, atestado, etc.).</figcaption>
</figure>

### Tela: Formulário de Novo Afastamento

<figure>
  <img src="screenshots/rh/14-afastamento-form.png" alt="Formulário de Novo Afastamento">
  <figcaption>Funcionário, motivo/tipo de afastamento e período.</figcaption>
</figure>

### Tela: Riscos Ambientais

<figure>
  <img src="screenshots/rh/07-riscos-ambientais.png" alt="Riscos Ambientais">
  <figcaption>Catálogo de riscos ambientais usado nos laudos de segurança do trabalho.</figcaption>
</figure>

### Tela: Vínculos Contratuais

<figure>
  <img src="screenshots/rh/08-vinculos-lista.png" alt="Vínculos Contratuais">
  <figcaption>Histórico de vínculo empregatício de cada funcionário.</figcaption>
</figure>

### Tela: Laudos de Risco

<figure>
  <img src="screenshots/rh/09-laudos-lista.png" alt="Laudos de Risco">
  <figcaption>Laudos de risco ambiental por função/setor.</figcaption>
</figure>

### Tela: ASO — Solicitações

<figure>
  <img src="screenshots/rh/10-aso-solicitacoes.png" alt="ASO - Solicitações">
  <figcaption>Solicitações de Atestado de Saúde Ocupacional, com tipos de exame configuráveis.</figcaption>
</figure>

### Dicas e erros comuns

- Um funcionário sem **função** cadastrada não aparece corretamente no rateio de custo de mão de obra nas Ordens de Serviço.
- ASOs vencidos ou próximos do vencimento aparecem como alerta no dashboard — acompanhar evita não-conformidade trabalhista.

## Patrimônio (`/patrimonio/`)

### Visão geral

Controla os bens patrimoniais da empresa (máquinas, equipamentos, imóveis, veículos convertidos em patrimônio), com depreciação e auditoria física periódica para conferir se o bem registrado ainda existe e está no local esperado.

### Tela: Lista de Patrimônios

<figure>
  <img src="screenshots/patrimonio/01-lista.png" alt="Lista de Patrimônios">
  <figcaption>Bens patrimoniais cadastrados (`/patrimonio/`).</figcaption>
</figure>

### Tela: Detalhe do Patrimônio

<figure>
  <img src="screenshots/patrimonio/02-detalhe.png" alt="Detalhe de um Patrimônio">
  <figcaption>Dados do bem, valor, depreciação acumulada e movimentações (transferência de local/responsável).</figcaption>
</figure>

### Tela: Formulário de Novo Patrimônio

<figure>
  <img src="screenshots/patrimonio/05-patrimonio-form.png" alt="Formulário de Novo Patrimônio">
  <figcaption>Identificação do bem, valor de aquisição e taxa/método de depreciação.</figcaption>
</figure>

**Como preencher:** informe nome/descrição do bem, categoria, valor de aquisição e data de aquisição — a partir desses dados o sistema calcula a depreciação acumulada automaticamente conforme o método configurado. Um veículo da Frota pode ser **exportado como Patrimônio** (botão na tela de veículo), evitando redigitar os dados básicos já existentes no cadastro de veículo.

### Fluxo passo a passo — controlar e auditar patrimônio

1. Cadastre o bem (manualmente ou exportando de um veículo da Frota).
2. Periodicamente, crie uma **Auditoria** informando quais bens serão conferidos fisicamente.
3. Para cada item da auditoria, confirme se o bem foi encontrado no local esperado — divergências ficam registradas no resultado da auditoria.
4. **Finalize** a auditoria depois de conferir todos os itens.

### Tela: Auditorias

<figure>
  <img src="screenshots/patrimonio/03-auditorias-lista.png" alt="Auditorias">
  <figcaption>Auditorias físicas programadas (`/patrimonio/auditorias/`); cada item é conferido e o resultado registrado.</figcaption>
</figure>

### Tela: Relatório de Patrimônios

<figure>
  <img src="screenshots/patrimonio/04-relatorio.png" alt="Relatório de Patrimônios">
  <figcaption>Relatório consolidado (PDF/Excel) de todos os bens, com valor atual e depreciação.</figcaption>
</figure>

### Dicas e erros comuns

- Finalizar uma auditoria sem conferir todos os itens deixa bens sem status de conferência — revise a lista de pendentes antes de finalizar.
