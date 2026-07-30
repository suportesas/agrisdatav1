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

Produtores (e Fornecedores) podem receber um **acesso de portal** próprio — um login restrito onde eles acompanham suas próprias operações (entregas, pagamentos, empréstimos) sem precisar de um usuário completo do sistema interno. O acesso é criado e pode ser bloqueado a partir da própria ficha do produtor/fornecedor.

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

### Tela: Lista de Transportadoras

<figure>
  <img src="screenshots/cadastros_pessoas/07-transportadoras-lista.png" alt="Lista de Transportadoras">
  <figcaption>Transportadoras cadastradas (`/cadastros/transportadoras/`), usadas em CT-e e MDF-e.</figcaption>
</figure>

### Tela: Lista de Vendedores

<figure>
  <img src="screenshots/cadastros_pessoas/08-vendedores-lista.png" alt="Lista de Vendedores">
  <figcaption>Vendedores internos (`/cadastros/vendedores/`), vinculados aos pedidos de venda.</figcaption>
</figure>

### Dicas e erros comuns

- Um cliente/fornecedor **inativo** não é excluído — apenas some das buscas de uso corrente, preservando o histórico de documentos já emitidos.
- Bloquear o acesso ao portal de um produtor/fornecedor não apaga o cadastro dele, só impede o login externo.

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

### Tela: Combustível/Abastecimentos

<figure>
  <img src="screenshots/frota/04-abastecimentos.png" alt="Abastecimentos">
  <figcaption>Registros de abastecimento (`/frota/abastecimentos/`), com opção de importação em lote via CSV.</figcaption>
</figure>

### Tela: Manutenções

<figure>
  <img src="screenshots/frota/05-manutencoes.png" alt="Manutenções">
  <figcaption>Manutenções preventivas/corretivas (`/frota/manutencoes/`), com itens e alertas programados.</figcaption>
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

### Tela: Vínculos Motorista x Frota

<figure>
  <img src="screenshots/frota/11-vinculos-lista.png" alt="Vínculos Motorista x Frota">
  <figcaption>Histórico de qual motorista esteve vinculado a qual veículo/placa em cada período.</figcaption>
</figure>

### Dicas e erros comuns

- O histórico de **vínculos** é o que permite saber, numa data específica, qual motorista estava com qual veículo — útil para investigar multas ou ocorrências antigas.
- Documentos de veículo/motorista vencidos disparam **alertas**; vale revisar essa tela periodicamente.

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

### Tela: Funções/Cargos

<figure>
  <img src="screenshots/rh/04-funcoes-lista.png" alt="Funções/Cargos">
  <figcaption>Cadastro de funções (`/rh/funcoes/`), com faixa salarial de referência.</figcaption>
</figure>

### Tela: Férias

<figure>
  <img src="screenshots/rh/05-ferias-lista.png" alt="Férias">
  <figcaption>Controle de períodos de férias, com relatório de previsão em PDF.</figcaption>
</figure>

### Tela: Afastamentos

<figure>
  <img src="screenshots/rh/06-afastamentos-lista.png" alt="Afastamentos">
  <figcaption>Afastamentos registrados (licença, atestado, etc.).</figcaption>
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

Um veículo da Frota pode ser **exportado como Patrimônio**, evitando recadastrar os dados básicos já existentes no cadastro de veículo.

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
