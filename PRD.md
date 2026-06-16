PRD - ERP Agrícola Salutaris
Versão 1.0 - Documento Consolidado

## Release Notes

- 2025-12-15 — Safra: adicionado CRUD de `Safra` (modelos `Safra`, `SafraPlan`, `SafraReal`), views, forms e templates; comparativo Planejado x Real; correção em `SafraForm.save` para remover referência a campo inexistente; adicionados testes unitários e de integração (`cadastros.tests.*`). PR: https://github.com/EMSSousa/erp_agricola/pull/3
- 2026-02-12 — Enterprise Plus / Grupos Corporativos: criado modelo `GrupoCorporativo`, vínculo `Empresa.grupo_corporativo`, CRUD completo (listas, detalhes, edição, exclusão, adicionar/remover empresas), relatório consolidado; plano `ENTERPRISE_PLUS` adicionado; limpeza de planos de teste; páginas de ajuda para Grupos Corporativos e para Usuários/Grupos; melhorias de templates em fluxos de grupos.


1. VISÃO GERAL DO PRODUTO
1.1 Nome do Sistema
ERP Agrícola Salutaris - Plataforma SaaS Integrada para Gestão Agroindustrial, Exportação e Compliance
1.2 Objetivo Principal
Entregar uma solução completa que integre produção agrícola, packing house, exportação, logística, financeiro, fiscal, RH, certificações, BI e portais externos, centralizando todos os dados do agronegócio em uma única plataforma multiempresa, segura e escalável.
1.3 Público-Alvo

Pequenos, médios e grandes produtores agrícolas
Fazendas de exportação
Packing houses
Cooperativas agrícolas
Tradings e exportadoras
Prestadores de serviço agrícola
Consultores e auditores

1.4 Modelo de Negócio
SaaS multiempresa com planos escalonados por:

Número de usuários
Módulos habilitados
Volume de operações
Espaço de armazenamento
Integrações adicionais

Planos:

Starter - Pequenos produtores
Professional - Médios produtores
Enterprise - Grandes produtores e exportadoras
Enterprise Plus - Grupos corporativos

1.5 Plataformas

Web responsiva
Mobile (online/offline)
APIs REST
Portais externos (Produtor, Cliente, Fornecedor, Despachante)


2. MÓDULOS DO SISTEMA
2.1 Dashboard Principal
2.2 Cadastros Base
2.3 Gestão de Usuários e Segurança
2.4 Suprimentos e Compras
2.5 Almoxarifado e Armazéns
2.6 Produção Agrícola
2.7 Gestão de Estufas e Transplantio
2.8 Frota, Oficina e Manutenção
2.9 Packing House
2.10 Qualidade e Classificação
2.11 Logística e Expedição
2.12 Exportação e Documentação
2.13 Rolagem de Container
2.14 Conta Corrente de Produtores
2.15 Financeiro
2.16 Adiantamentos Internacionais
2.17 Account Sales e Rateio Comercial
2.18 Histórico Financeiro por Invoice/Container
2.19 Formação de Preço
2.20 Fiscal e Faturamento
2.21 CRM e Vendas
2.22 Certificações e Compliance
2.23 Sustentabilidade e Métrica de Carbono
2.24 Recursos Humanos
2.25 Portais Externos
2.26 Módulo Cooperativas
2.27 AgriCommunity
2.28 Business Intelligence
2.29 Gestão de Riscos e Cut-offs
2.30 Configurações do Sistema
2.31 Suporte e Ajuda
2.32 Aplicativo Mobile
2.33 Balanço de Massas

3. REQUISITOS FUNCIONAIS POR MÓDULO
3.1 Dashboard Principal
RF-001 Exibir visão geral consolidada da operação
RF-002 Alertas em tempo real (estoque, vencimentos, clima, máquinas, financeiro, cut-offs)
RF-003 KPIs customizáveis por usuário
RF-004 Atalhos rápidos configuráveis
RF-005 Lista de tarefas pendentes
RF-006 Indicadores ambientais (água, energia, carbono)
RF-007 Indicadores de exportação (embarques, qualidade, prazos)
RF-008 Painel de auditoria (pendências, certificações vencendo)

3.2 Cadastros Base
RF-020 Cadastro completo de empresa/filial com CNPJ, licenças e certificados
RF-021 Gestão de imóveis rurais com CAR, georreferenciamento, mapas
RF-022 Cadastro de áreas, talhões, limites, histórico de culturas
RF-023 Centros de custo com estrutura hierárquica
RF-024 Cadastro de colaboradores e funções
RF-025 Cadastro de clientes com moeda padrão e porto de destino
RF-026 Cadastro de fornecedores, transportadoras, motoristas
RF-027 Base de culturas, cultivares, pragas, doenças
RF-028 Cadastro de navios, armadores, portos (com criação rápida)
RF-029 Cadastro de poços e patrimônios
RF-030 Cadastro de produtos com indicador de registro no MAPA
RF-031 Filtro de produtos sem registro MAPA (visível apenas para administrador)

### Nota de implementação: Área Agricultável

O campo `area_agricultavel` da entidade `Fazenda` é um valor derivado e **é calculado automaticamente** como a soma dos campos `area_plantavel` das `Area` relacionadas (seções/setores) daquela fazenda. Isso evita divergência entre um valor manual e a soma das áreas internas.

Recomenda-se a seguinte UX/fluxo:

- Usuários editam `Area` para ajustar `area_total`, `area_reserva` e `area_plantavel`.
- O sistema recalcula `Fazenda.area_agricultavel` via sinais (`post_save`/`post_delete`) nas `Area`.
- No formulário de edição da `Fazenda`, `area_agricultavel` aparece como leitura com um tooltip explicativo.

Validações adicionais aplicadas:

- `AreaForm` valida que a soma das `area_plantavel` das áreas da fazenda não ultrapasse `Fazenda.area_total`.
- `Area` possui `area_reserva` para indicar áreas não plantáveis (estradas, APP, infraestrutura).

Motivação: manter consistência, reduzir suporte por dados divergentes e tornar a UI mais intuitiva.

3.3 Gestão de Usuários e Segurança
RF-750 Perfis por porte de produtor (pequeno/médio/grande)
RF-751 Permissões granulares por módulo e ação
RF-752 Logs completos de auditoria
RF-753 Autenticação 2FA
RF-754 Controle de sessões ativas
RF-755 Perfis especiais (administrador, packing, exportação, financeiro, despachante)
RF-756 Cooperado visualiza apenas suas áreas
RF-757 Controle de dispositivos

3.4 Suprimentos e Compras
RF-050 Solicitações de compra com aprovações por nível
RF-051 Cotações com múltiplos fornecedores
RF-052 Emissão de pedidos de compra
RF-053 Controle de recebimento (físico x fiscal)
RF-054 Entrada de NF-e via XML
RF-055 Controle de estoque mínimo/máximo com alertas
RF-056 Inventário cíclico
RF-057 Curva ABC de estoque
RF-058 Controle especial de defensivos e fertilizantes
RF-059 Ranking e avaliação de fornecedores

3.5 Almoxarifado e Armazéns
RF-080 Cadastro de armazéns e depósitos
RF-081 Controle de locais de estocagem com endereçamento
RF-082 Requisições internas
RF-083 Devoluções
RF-084 Inventário geral e parcial
RF-085 Entrada e saída por lote e validade
RF-086 Bloqueio de estoque contaminado
RF-087 Logística reversa de embalagens
RF-088 Empréstimos a produtores (integração com Conta Corrente)
RF-089 Rastreabilidade completa: insumo → talhão → produto final
RF-090 Transferência entre armazéns

### Status de Implementação (Atualizado em 2026-02-03)

**3.4 Suprimentos e Compras (verificado no código)**
- ✅ RF-050 Solicitações de compra com aprovações por nível
- ✅ RF-051 Cotações com múltiplos fornecedores
- ✅ RF-052 Emissão de pedidos de compra
- ✅ RF-053 Controle de recebimento (físico x fiscal)
- ✅ RF-057 Curva ABC de estoque (relatório disponível no módulo de estoque)
- ⚠️ RF-054 Entrada de NF-e via XML (entrada direta existe; parsing XML não evidenciado)
- ✅ RF-055 Controle de estoque mínimo/máximo com alertas 
  - ✅ Sistema de alertas em 2 níveis: Crítico (≤0) e Excesso (>máximo)
  - ✅ Badge no sidebar com contador de alertas
  - ✅ Lista de produtos com estoque em alerta (/estoque/produtos/)
  - ✅ Relatório exportável em Excel e PDF com dados detalhados
  - ✅ Acesso via menu: Estoque → Relatório de Alertas ou Relatórios → Estoque Avançado
- ⏳ RF-056 Inventário cíclico (não evidenciado)
- ⏳ RF-058 Controle especial de defensivos e fertilizantes (não evidenciado)
- ⏳ RF-059 Ranking e avaliação de fornecedores (não evidenciado)

**3.5 Almoxarifado e Armazéns (verificado no código)**
- ✅ RF-080 Cadastro de armazéns e depósitos
- ✅ RF-081 Controle de locais de estocagem com endereçamento
- ✅ RF-085 Entrada e saída por lote e validade
- ✅ RF-090 Transferência entre armazéns
- ⚠️ RF-089 Rastreabilidade completa (rastreio por lote/movimentação existente; integração insumo → talhão → produto final não evidenciada)
- ⏳ RF-082 Requisições internas (não evidenciado)
- ⏳ RF-083 Devoluções (não evidenciado)
- ⏳ RF-084 Inventário geral e parcial (não evidenciado)
- ⏳ RF-086 Bloqueio de estoque contaminado (não evidenciado)
- ⏳ RF-087 Logística reversa de embalagens (não evidenciado)
- ⏳ RF-088 Empréstimos a produtores (não evidenciado)

**Implementações adicionais registradas**
- ✅ Dashboards de rastreamento e validação de disponibilidade de estoque
- ✅ Entrada direta de NF-e (sem pedido) com movimentação automática de estoque
- ✅ Atualização automática do `Produto.preco_custo` no recebimento
- ✅ Validações para evitar duplicidade de entrada de estoque

3.6 Produção Agrícola
RF-100 Planejamento completo de safra
RF-101 Previsão de colheita por área
RF-102 Orçamento de safra e metas de produtividade
RF-103 Cadastro e ciclo de safra
RF-104 Monitoramento de pragas, doenças, fenologia
RF-105 Ordens de serviço: plantio, irrigação, aplicação, colheita
RF-106 Fertirrigação ligada ao controle de poços
RF-107 Registro de pluviometria
RF-108 Controle de qualidade de campo
RF-109 Lotes de produção e rastreabilidade
RF-110 Integração com packing house
RF-111 Caderno de campo digital (GLOBALG.A.P)
RF-112 Histórico completo por talhão
RF-113 Aplicações de defensivos e fertilizantes
RF-114 Consumo automático via almoxarifado
RF-115 Custos por talhão e safra
RF-116 Métricas por kg produzido (fertilizantes, defensivos, carbono)
RF-117 Fotos geolocalizadas
RF-118 Integração com FieldView e máquinas agrícolas

### Status de Implementação — 3.6 Produção Agrícola (Atualizado em 2026-06-15)

- ✅ RF-100 Planejamento de safra — `Safra`, `SafraPlan` em `cadastros/models.py`
- ✅ RF-101 Previsão de colheita por área — `SafraPlan.previsao_colheita`, `SafraReal`
- ✅ RF-102 Orçamento e metas — `PlanejamentoCustoSafra`, `FormacaoPreco` em `operacoes_campo/models.py`
- ✅ RF-103 Cadastro e ciclo de safra — CRUD completo, status PLANEJADA → EM_ANDAMENTO → FINALIZADA
- ✅ RF-104 Monitoramento MIP — `MonitoramentoMIP`, `PragaNoMonitoramento`, `EstagioDesenvolvimento` em `mip/`
- ✅ RF-105 Ordens de serviço — `OrdemServico`, `OSFuncionario`, `OSMaquina` em `operacoes_campo/models.py`
- ✅ RF-106 Fertirrigação + controle de poços — modelo `Poco` em `cadastros/models.py`; FK `poco` em `OrdemServico` e `OSRegistroExecucao`; CRUD em `/cadastros/pocos/`
- ✅ RF-107 Pluviometria — `RegistroPluviometria` em `operacoes_campo/models.py`
- ✅ RF-108 Qualidade de campo — `InspecaoQualidadeCampo` (Brix, peso, defeitos)
- ✅ RF-109 Lotes de produção e rastreabilidade — `LoteProducao` em `operacoes_campo/models.py`; gerado automaticamente ao concluir `EtapaColheita`; código único de rastreamento
- ✅ RF-110 Integração com packing house — `OrdemEmbalagem.lote_producao` FK; fluxo de recepção em `/operacoes_campo/lotes-producao/<pk>/recepcao/`
- ✅ RF-111 Caderno de campo digital (GLOBALG.A.P) — `RegistroCadernoCampo` em `operacoes_campo/`
- ✅ RF-112 Histórico completo por talhão — `HistoricoTalhao` em `cadastros/models.py`
- ✅ RF-113 Aplicações de defensivos/fertilizantes — `RegistroCadernoCampoInsumo`, `OrdemServicoInsumo`
- ✅ RF-114 Consumo automático via almoxarifado — `os_concluir` cria `MovimentacaoEstoque SAIDA` para cada insumo aplicado
- ✅ RF-115 Custos por talhão e safra — `CustoTalhao`, `PlanejamentoCustoSafra` com export Excel/PDF
- ✅ RF-116 Métricas por kg produzido — produtividade kg/ha, custo/kg via `FormacaoPreco`
- ⚠️ RF-117 Fotos geolocalizadas — campos `ImageField` existem em OS/Caderno/MIP; coordenadas GPS por foto não implementadas
- ❌ RF-118 Integração com FieldView e máquinas agrícolas — integração externa, fora do escopo atual (Fase 7 do roadmap)

3.7 Gestão de Estufas e Transplantio
RF-1200 Cadastro de estufas
RF-1201 Registro de lotes de mudas com ID único
RF-1202 Identificação do lote da semente
RF-1203 Registro de quantidade semeada
RF-1204 Controle de perdas na estufa
RF-1205 Aplicações de defensivos na estufa
RF-1206 Aplicações de fertilizantes na estufa
RF-1207 Monitoramento de pragas na estufa
RF-1208 Cálculo de custo da muda produzida
RF-1209 Fotos e evidências da estufa
RF-1210 Lote pode ser dividido entre vários talhões
RF-1211 Controle de quantidade disponível após perdas
RF-1220 Exibir somente talhões prontos para plantio/transplantio
RF-1221 Registro do processo de preparo da área
RF-1222 Liberação para plantio via workflow
RF-1223 Travar áreas com cultura ativa
RF-1230 Seleção de lote(s) de mudas para transplantio
RF-1231 Transplantio total ou parcial
RF-1232 Seleção de talhão destino
RF-1233 Transferência automática dos custos da estufa para o talhão
RF-1234 Transferência dos dados de pragas monitoradas
RF-1235 Registro com data, operador e evidências
RF-1236 Rastreabilidade: semente → estufa → transplantio → talhão
RF-1240 Plantio direto com registro de sementes
RF-1250 Registro de replantios por perdas
RF-1251 Origem das mudas para replantio (estufa/compra/outra área)
RF-1252 Custo adicional incluído no custo do talhão
RF-1253 Registro de motivo da perda
RF-1254 Atualização da produtividade

3.8 Frota, Oficina e Manutenção
RF-300 Cadastro de veículos, tratores, implementos, carretas
RF-301 Vincular carreta ao cavalo mecânico
RF-302 Controle de documentos do veículo (ANTT, seguro, licenciamento)
RF-303 Cadastro de motoristas com documentação (CNH, MOPP)
RF-310 Registrar viagens por container/invoice/booking
RF-311 Registro de coleta na fazenda
RF-312 Registro de entrada no porto
RF-313 Registro de eventos (espera, fila, emergência, avaria)
RF-314 Cadastro de rotas padrão
RF-320 Controle de combustível por viagem
RF-321 Manutenção preventiva
RF-322 Manutenção corretiva
RF-323 Controle de pneus (vida útil, troca, recapagem)
RF-324 Controle de pedágios
RF-325 Diárias de motorista
RF-326 Lavagem de container
RF-327 Avarias no container/carreta
RF-328 Multas
RF-329 Custo de seguro por viagem
RF-330 Custo da hora parada (porto, inspeções)
RF-340 Receita de frete cobrado
RF-341 Adicionais recebidos
RF-342 Margem por viagem
RF-350 Rastreamento GPS em tempo real
RF-351 Telemetria (frenagem, aceleração, marcha lenta)
RF-360 Dashboard de custo por veículo
RF-361 Dashboard de receita por veículo
RF-362 Margem por viagem/container
RF-363 Comparativo frota própria x terceirizada
RF-364 Horímetros e odômetros
RF-365 Checklists digitais
RF-366 Controle de peças usadas
RF-367 Indicadores de eficiência

3.9 Packing House
RF-200 Entrada de frutas com pesagem
RF-201 Inspeção inicial
RF-202 Classificação manual/automática por tamanho, cor, qualidade
RF-203 Lavagem, higienização, tratamentos pós-colheita
RF-204 Controle de linha e produtividade de embaladores
RF-205 Reembalagem e retrabalhos
RF-206 Geração de romaneio interno
RF-207 Controle de câmaras frias
RF-208 Etiquetas com rastreabilidade (QR/Code128)
RF-209 Registro de não conformidades
RF-210 Registro fotográfico por pallet
RF-211 Registro de temperatura por pallet e lote
RF-212 Checklists de inspeção pré-operacional
RF-213 Histórico de retrabalho e motivações
RF-214 Rastreabilidade interna completa

3.10 Qualidade e Classificação
RF-Q-001 Registro de relatório de qualidade por container
RF-Q-002 Suporte a múltiplos relatórios para culturas diferentes no mesmo container
RF-Q-003 Classificação por cores (Verde/Amarelo/Vermelho)
RF-Q-004 Anexo de evidências (fotos, vídeos, PDFs)
RF-Q-005 Impacto automático nos descontos do Account Sales
RF-Q-006 Alertas quando índices amarelos ou vermelhos são detectados
RF-Q-007 Estatísticas de qualidade por produtor
RF-Q-008 Ranking de calibres x defeitos
RF-Q-009 Histórico por navio e destino
RF-Q-010 Parâmetros técnicos (Brix, temperatura, textura, defeitos)
RF-Q-011 Vinculação aos pallets específicos
RF-Q-012 Integração com Packing House para alertas

3.11 Logística e Expedição
RF-300 Programação de cargas
RF-301 Romaneios de expedição
RF-302 Rastreamento em tempo real
RF-303 Roteirização inteligente
RF-304 Controle de temperatura durante transporte
RF-305 Fretes próprios e terceiros (rodoviário/marítimo)
RF-306 Controle de drawback (ato concessório, saldos)
RF-307 Checklist de higiene do container
RF-308 Controle de lacres (armador, extra, substituição)
RF-309 Gate-in e Gate-out no porto
RF-310 Tracking portuário e marítimo
RF-311 ETA/ETD

3.12 Exportação e Documentação
RF-250 Gestão de booking
RF-251 Cadastro e tracking de containers
RF-252 Seleção de navio e voyage
RF-253 Coleta e entrega
RF-254 Emissão automática de Invoice
RF-255 Emissão de Packing List
RF-256 Instrução de embarque
RF-257 Certificados (fitossanitário, origem, temperatura)
RF-258 Pré-check documental
RF-259 Workflow GO/NO-GO obrigatório
RF-260 Anexos obrigatórios (fotos, pesagens, controle de frio)
RF-261 Integração com APIs de navios
RF-262 Controle de temperatura do container
RF-263 Checklists por cliente e destino
RF-264 Gestão de riscos logísticos e comerciais
RF-265 Controle automático de Cut-off (documental, operacional, VGM)
RF-266 Registro fotográfico obrigatório (lacres, carga, interior)
RF-267 Gestão de divergências (peso, qualidade, documentos)

3.13 Rolagem de Container
RF-800 Registro da rolagem com motivo
RF-801 Evidências anexas (e-mails, prints, EDI)
RF-802 Sugestão automática de novo navio
RF-803 Criação de novo booking
RF-804 Cálculo automático de custos extras:

Demurrage
Armazenagem
Shifting
Transporte adicional
Energia/frio

RF-805 Geração automática de carta ao armador
RF-806 Registro de resposta (aceito/parcial/recusado)
RF-807 Absorção de custo no financeiro quando recusado
RF-808 Indicadores por armador (confiabilidade, % rolagens, custos)
RF-809 Alertas automáticos para equipes

3.14 Conta Corrente de Produtores
RF-350 Empréstimos de materiais com integração ao almoxarifado
RF-351 Devoluções
RF-352 Extrato detalhado por período
RF-353 Simulador de pagamento
RF-354 Integração financeira e fiscal
RF-355 Saldo por safra
RF-356 Integração com Account Sales
RF-357 Rateio de custos negativos

3.15 Financeiro
RF-400 Contas a pagar e receber
RF-401 Aprovações financeiras por nível
RF-402 Fluxo de caixa completo e projetado
RF-403 DRE e projeções de rentabilidade
RF-404 Conciliação bancária (OFX/CNAB)
RF-405 ACC/ACE e hedge cambial
RF-406 Categorias financeiras e plano de contas
RF-407 Posição de caixa multiempresa
RF-408 Controle multimoeda
RF-409 Centro de custo por talhão
RF-410 Rentabilidade por cliente/lote/container
RF-411 Gestão de inadimplência internacional

3.16 Adiantamentos Internacionais
RF-960 Registro de adiantamentos por cliente
RF-961 Controle de moeda (EUR, USD, GBP, BRL, etc.)
RF-962 Conversão automática para BRL
RF-963 Histórico de abatimentos por invoice
RF-964 Saldo atualizado do cliente
RF-965 Exibição no Portal do Cliente
RF-966 Registro de forma de pagamento (TT, depósito)
RF-967 Arquivos anexos (Swift, comprovantes)
RF-968 Integração com Account Sales
RF-969 Extrato consolidado com câmbio do dia

3.17 Account Sales e Rateio Comercial
RF-AS-001 Registro do Account Sale
RF-AS-002 Importação automática via OCR (PDF)
RF-AS-003 Importação de controle via XLS
RF-AS-004 Classificação de qualidade por cores
RF-AS-005 Regras automáticas de desconto por cor
RF-AS-006 Rateio de custos por:

Exportador
Produtor
Cooperado
Cliente

RF-AS-007 Integração com Financeiro
RF-AS-008 Integração com Conta Corrente Produtor
RF-AS-009 Indicadores e BI
RF-AS-010 Abatimento automático de adiantamentos
RF-AS-011 Visão financeira consolidada
RF-AS-012 Histórico completo com evidências

3.18 Histórico Financeiro por Invoice/Container
RF-HF-001 Registro completo de receitas e despesas por invoice
RF-HF-002 Registro por container para exportação
RF-HF-003 Receitas detalhadas:

Valor da venda
Receita VIP (exportação)
Bonificações
Créditos

RF-HF-004 Despesas mercado interno:

ICMS
Frete
Avarias
Seguro
Comissão

RF-HF-005 Despesas portuárias de exportação:

Movimentações de pátio
Energia/frio porta a porta
Scanner
Lar Fee
Genset alugado
Alteração de Set Point
Quebra de lacre
Despesas DHL
Despachante aduaneiro
Armazenagem
Correção de documentação
Transbordos/shifting
Demurrage

RF-HF-006 Rateio automático de custos por:

Cultura
Paletes
Caixas
Peso
Valor proporcional

RF-HF-007 Timeline financeira completa
RF-HF-008 Cálculo de margem real
RF-HF-009 Integração com Account Sales
RF-HF-010 Integração com Adiantamentos
RF-HF-011 Comparação meta x realizado

3.19 Formação de Preço
RF-FP-001 Cálculo automático do custo total da produção
RF-FP-002 Formação de preço por cultura/cliente
RF-FP-003 Comparação com o preço negociado
RF-FP-004 ALERTA de prejuízo quando valor < custo
RF-FP-005 Cenários simulados (what-if)
RF-FP-006 Impressão da ficha de formação de preço
RF-FP-007 Inclusão de todos os custos:

Estufa
Transplantio
Replantio
Insumos
Mão de obra
Frota
Packing
Logística


3.20 Fiscal e Faturamento
RF-450 Emissor de NF-e, CT-e, MDF-e (manual e automático)
RF-451 Leitor e importação de XML
RF-452 Gestão de certificado digital
RF-453 Parâmetros fiscais (CFOP, CST, NCM)
RF-454 Invoice de exportação
RF-455 Relatórios fiscais e auditoria
RF-456 Comunicação completa com SEFAZ
RF-457 Reenvio de XML e contingência
RF-458 Emissão automática baseada em eventos:

Carregamento → MDF-e
Transporte → CT-e
Expedição → NF-e


3.21 CRM e Vendas
RF-500 Funil de vendas e oportunidades
RF-501 Pedidos e orçamentos
RF-502 Tabelas de preço e promoções
RF-503 Histórico de compras e limite de crédito
RF-504 Dashboard comercial e comissão
RF-505 Campo "Moeda Padrão do Cliente"
RF-506 Campo "Porto de Destino"
RF-507 Criação rápida de porto sem sair da tela
RF-508 Histórico de performance por cliente
RF-509 Regras comerciais por destino
RF-510 Integração com histórico de exportações

3.22 Certificações e Compliance
RF-CC-001 Checklists completos:

GLOBALG.A.P. IFA v6
GRASP
Orgânico (Lei 10.831/MAPA)
ISO 9001
ISO 14001
ISO 22000
BRC
Fair Trade
SEDEX/SMETA

RF-CC-002 Lista Mestra de Documentos com controle de versão
RF-CC-003 Gestão de evidências e anexos
RF-CC-004 Não conformidades (NC) e ações corretivas
RF-CC-005 Auditorias internas
RF-CC-006 Calendário de auditorias
RF-CC-007 Workflow de aprovação de documentos
RF-CC-008 Histórico de revisões
RF-CC-009 Rastreabilidade avançada para auditorias
RF-CC-010 Alertas de vencimento de certificados

3.23 Sustentabilidade e Métrica de Carbono
RF-CARB-001 Cadastro de fontes de emissão:

Diesel, gasolina, GLP
Energia elétrica
Fertilizantes nitrogenados
Defensivos
Plásticos agrícolas
Compostagem/fermentação
Irrigação (bombeamento)
Transporte

RF-CARB-002 Registro operacional automático via integração
RF-CARB-003 Cálculo da Pegada de Carbono usando:

Cool Farm Tool (CFT)
GHG Protocol
ISO 14064
IPCC TIER 1 & 2

RF-CARB-004 Exportação automática para Cool Farm Tool
RF-CARB-005 Relatório de Emissões (CO₂e):

Total
Por talhão
Por cultura
Por kg produzido
Comparação ano x ano

RF-CARB-006 Plano de ação para redução de emissões
RF-CARB-007 Histórico e evidências para auditoria
RF-CARB-008 Integração com GLOBALG.A.P.
RF-CARB-009 Dashboards de sustentabilidade
RF-CARB-010 Banco de dados de fatores de emissão (IPCC, MCTI, ANEEL)
RF-CARB-011 Controle de água, energia e resíduos
RF-CARB-012 Gestão de fertilizantes e defensivos por kg produzido

3.24 Recursos Humanos
RF-600 Cadastro completo do funcionário
RF-601 Ponto eletrônico
RF-602 Férias, afastamentos, atestados
RF-603 Folha de pagamento
RF-604 EPIs e CIPA
RF-605 Exames médicos (ASO)
RF-606 Treinamentos
RF-607 Avaliações de desempenho

3.25 Portais Externos
Portal do Produtor
RF-650 Acesso seguro
RF-651 Extrato de conta corrente
RF-652 Informações de safra
RF-653 Produtividade
RF-654 Participação nos containers
RF-655 Receitas líquidas
RF-656 Custos rateados
Portal do Cliente
RF-660 Pedidos e rastreamento
RF-661 Timeline completa do pedido
RF-662 Documentos de exportação
RF-663 Faturas e invoices
RF-664 Relatórios de qualidade
RF-665 Histórico financeiro
RF-666 Adiantamentos e saldo
RF-667 Tracking marítimo
RF-668 Chat integrado
Portal do Fornecedor
RF-670 Cotações
RF-671 Pedidos
RF-672 Entregas
RF-673 Notas fiscais
RF-674 Avaliação de qualidade
Portal do Despachante
RF-680 Upload de documentos (Fito, PTV, DUE, CO, BL)
RF-681 Validação automática de versões
RF-682 Integração com timeline
RF-683 Notificação ao financeiro

3.26 Módulo Cooperativas
RF-COOP-001 Cadastro de cooperados
RF-COOP-002 Produtividade individual e consolidada
RF-COOP-003 Rateio de custos configurável
RF-COOP-004 Rateio de receitas
RF-COOP-005 Conta corrente individual
RF-COOP-006 Safra compartilhada
RF-COOP-007 Relatórios para conselho
RF-COOP-008 Gestão de DAP/CAF
RF-COOP-009 Estoque individualizado por produtor
RF-COOP-010 Exportação multi-produtor no mesmo container
RF-COOP-011 Auditorias por produtor

3.27 AgriCommunity
RF-700 Fórum de discussão
RF-701 Sistema de perguntas e respostas
RF-702 Marketplace
RF-703 Sistema de reputação
RF-704 Eventos
RF-705 Biblioteca técnicaEContinuar
3.28 Business Intelligence
RF-850 Dashboards prontos por módulo
RF-851 Relatórios customizados
RF-852 KPIs estratégicos e alertas gerenciais
RF-853 Exportação (Excel/PDF/CSV)
RF-854 Agendamentos e envio automático
RF-855 Dashboard de Exportação com KPIs específicos
RF-856 Dashboard de Logística
RF-857 Dashboard de Riscos
RF-858 BI de Qualidade
RF-859 Indicadores de Carbono
RF-860 Indicadores de Frota
RF-861 Rentabilidade por container
RF-862 Performance por talhão
RF-863 Custo real por safra

3.29 Gestão de Riscos e Cut-offs
RF-2100 Matriz de risco
RF-2101 Registro de incidentes
RF-2102 Automação de cut-offs:

Documental
Operacional
VGM
Entrega portuária

RF-2103 Notificações antecipadas
RF-2104 Rastreio de desvios
RF-2105 Previsões via IA (opcional)
RF-2106 Gestão de riscos da exportação (navio, porto, cliente, rota)
RF-2107 Análise de severidade

3.30 Configurações do Sistema
RF-800 Idioma e regionalização
RF-801 Personalização de interface
RF-802 Gestão de planos SaaS
RF-803 Backup e restauração
RF-804 Integrações API/Webhook
RF-805 Campos customizados
RF-806 Regras de negócio configuráveis
RF-807 Motor de regras
RF-808 Parâmetros fiscais

### Status de Implementação (Atualizado em 2026-02-12)

- ✅ Gestão de planos SaaS: adicionado `ENTERPRISE_PLUS`; ampliado `Plano.codigo` para `max_length=20`; padronização e limpeza de planos de teste.
- ✅ Grupos Corporativos (Enterprise Plus): modelo `GrupoCorporativo`, vínculo com `Empresa`, CRUD completo e relatório consolidado.

3.31 Suporte e Ajuda
RF-900 Sistema de chat
RF-901 Gestão de tickets
RF-902 Base de conhecimento
RF-903 Tutoriais em vídeo
RF-904 Documentação técnica

### Status de Implementação (Atualizado em 2026-02-12)

- ✅ Base de conhecimento: páginas de ajuda para Grupos Corporativos e para Usuários/Grupos (arquitetura, fluxo de criação de usuários e permissões).

3.32 Aplicativo Mobile
RF-950 Atividades de campo offline
RF-951 Fotos georreferenciadas
RF-952 Mapas offline
RF-953 Checklists mobile
RF-954 Registro de tarefas agrícolas
RF-955 Inspeção de qualidade offline
RF-956 Sincronização automática quando online

3.33 Balanço de Massas
RF-BM-001 Controle total do destino dos frutos:

Exportação
Mercado interno
Doação
Descarte
Ração animal
Industrialização
Granel
Perdas/avarias

RF-BM-002 Divergências entre:

Colhido
Recebido no packing
Embalado
Vendido

RF-BM-003 Relatório obrigatório GLOBALG.A.P.

4. REQUISITOS NÃO FUNCIONAIS (RNF)
RNF-01 Sistema SaaS multiempresa, multiusuário, escalável
RNF-02 Autenticação segura (2FA, JWT, criptografia Argon2)
RNF-03 Auditoria completa de dados
RNF-04 Processamento de alto volume (packing, exportação)
RNF-05 Mobile offline com sincronização eventual
RNF-06 API REST completa
RNF-07 LGPD + GDPR compliance
RNF-08 Tempo de resposta < 2s em 95% das operações
RNF-09 Backups automáticos
RNF-10 Mínimo 99,5% uptime
RNF-11 Alta disponibilidade
RNF-12 Performance otimizada
RNF-13 Controle de dispositivos
RNF-14 SSL em todas as comunicações

5. INTEGRAÇÕES EXTERNAS

NF-e/CT-e/MDF-e (SEFAZ)
Bancos (OFX/CNAB)
GPS e rastreamento de frota
APIs de navios/armadores
Marketplace
Sensores IoT (clima, umidade, irrigação)
Máquinas agrícolas (CANBUS/ISOBUS, FieldView, John Deere, CNH, Trimble)
Balanças industriais
Impressoras de etiquetas
Cool Farm Tool
Portais de certificação
APIs portuárias (quando disponível)


6. REGRAS DE NEGÓCIO (RN)
RN-01 Solicitações de compra exigem aprovação por nível hierárquico
RN-02 Nenhum defensivo pode ser aplicado sem receituário agronômico
RN-03 Ordem de serviço só é concluída com evidência fotográfica
RN-04 Motorista só pode operar veículo se CNH válida
RN-05 Lote de produção deve ser único e rastreável até o talhão
RN-06 Packing house não libera pallet sem etiqueta válida
RN-07 Faturamento de exportação só após confirmação do booking
RN-08 Portal do Fornecedor só vê seus próprios pedidos
RN-09 Permissões controladas por ação (CRUD granular)
RN-10 Backup diário obrigatório
RN-11 Exportação gera histórico financeiro automaticamente
RN-12 Nenhum container pode sair sem foto interna, externa e lacre
RN-13 Cut-off documental deve ser monitorado automaticamente
RN-14 Divergências geram automaticamente uma Não Conformidade
RN-15 Nenhum produto segue para exportação sem checklist liberado
RN-16 Documentos não podem ser enviados ao cliente sem aprovação de 2 setores
RN-17 Custos da estufa devem ser rateados ao talhão no transplantio
RN-18 Até o transplantio, o lote não pertence a nenhum talhão
RN-19 Nenhum transplantio pode ser feito sem área apta
RN-20 Replantio é obrigatório registrar para GLOBALG.A.P.
RN-21 Estoque segregado para insumos distribuídos a produtores
RN-22 Rateio deve ser configurável por tipo de custo
RN-23 Account Sales multi-produtor seguem regras específicas
RN-24 Cooperativa deve conseguir acessar dados individuais e agregados
RN-25 Produtor cooperado visualiza exclusivamente seus dados
RN-26 Safra encerrada não permite edições (somente reabertura via workflow)
RN-27 Produto sem registro MAPA só aparece para administrador
RN-28 Qualidade vermelha exige justificativa e evidências
RN-29 Preço menor que custo gera alerta automático
RN-30 Valores negativos devem seguir contrato de rateio configurado

7. FLUXOS PRINCIPAIS
Fluxo de Compras
Solicitação → Aprovação → Cotação → Pedido → Recebimento → Entrada Fiscal
Fluxo de Safra
Planejamento → Plantio/Transplantio → Monitoramento → Colheita → Packing
Fluxo de Packing House
Recepção → Classificação → Embalagem → Etiquetagem → Expedição
Fluxo de Exportação
Booking → Container → Documentos → Gate-in → Embarque → Tracking
Fluxo de Faturamento
Pedido → Separação → Expedição → NF-e → Entrega
Fluxo de Rastreabilidade
Talhão → Caixa → Pallet → Container → Cliente
Fluxo de Expedição Logística
Programação → Carregamento → Rastreamento → Entrega
Fluxo Financeiro
Lançamento → Aprovação → Conciliação → Relatórios
Fluxo de Estufa
Semeadura → Monitoramento → Aplicações → Transplantio → Talhão
Fluxo de Rolagem
Notificação → Registro → Novo Booking → Cálculo de Custos → Cobrança
Fluxo de Account Sales
Recebimento → Classificação → Rateio → Integração Financeira
Fluxo de Timeline do Cliente
Pedido → Produção → Qualidade → Packing → Gate-in → Embarque → Chegada

8. ROADMAP DE DESENVOLVIMENTO
Fase 1 - Base (Meses 1-3)

Cadastros base
Gestão de usuários
Compras e estoque
Financeiro básico
Fiscal básico (NF-e)

Fase 2 - Produção Agrícola (Meses 4-6)

Safras, OS, monitoramentos
Estufa e transplantio
Pluviometria
Qualidade de campo
Caderno de campo

Fase 3 - Packing House (Meses 7-9)

Classificação
Produtividade
Etiquetas
Rastreabilidade
Expedição interna

Fase 4 - Logística + Exportação (Meses 10-12)

Booking e containers
Documentos
Rastreamento
Fretes
Frota completa

Fase 5 - BI Completo (Meses 13-15)

Dashboards por módulo
Relatórios customizados
KPIs avançados

Fase 6 - Portais + Mobile (Meses 16-18)

Portal do Cliente com Timeline
Portal do Produtor
Portal do Fornecedor
Portal do Despachante
App de campo offline

Fase 7 - Avançados (Meses 19-24)

Account Sales e rateio
Métrica de carbono
Cooperativas
Certificações completas
IA e automações


9. CRITÉRIOS DE ACEITE

Todos os módulos funcionando conforme RF
Testes unitários e de integração completos
Conformidade fiscal nacional
Dashboards operacionais completos
Níveis de permissão operacionais
Exportação e rastreabilidade ponta a ponta
Zero divergências documentais
Fluxo GO/NO-GO funcionando
Auditoria interna sem pendências
Cut-offs automatizados
KPIs configuráveis
Performance < 2s
Mobile offline funcional
Integrações testadas


## 📋 PRÓXIMOS PASSOS - ROADMAP 2026

### STATUS DE IMPLEMENTAÇÃO - ATUALIZADO EM 2026-02-12

#### ✅ **Funcionalidades Implementadas na Semana de 10-02-2026**

**3.2 Cadastros Base - Relatórios de Clientes e Fornecedores**
- ✅ **RF-025 Cadastro de clientes**: Novo relatório consolidado (PDF/Excel)
  - ✅ Filtro por tipo de cliente (MERCADO_INTERNO / IMPORTADOR)
  - ✅ Geração de PDF com header customizado contendo logo da empresa
  - ✅ Exportação para Excel com estilo profissional
  - ✅ Envio automático por Email e WhatsApp
  - ✅ Criação de classe `RelatorioClientesPDF` e `RelatorioClientesExcel`
  - ✅ Formulário de filtros com validação
  - ✅ Template responsivo com Bootstrap

- ✅ **RF-026 Cadastro de fornecedores**: Novo relatório completo e ranking
  - ✅ Filtros avançados:
    - ✅ Status (ATIVO / INATIVO / Todos)
    - ✅ Cidade (texto livre)
    - ✅ UF (dropdown)
    - ✅ Categoria (select da empresa)
    - ✅ Classificação de Risco (BAIXO / MÉDIO / ALTO)
  - ✅ Relatório de Fornecedores em PDF/Excel com tabela formatada
  - ✅ **Ranking de Compras**: Análise de compras por fornecedor baseado em `RecebimentoCompra`
    - ✅ Filtro por data (data_início / data_fim)
    - ✅ Agregação automática de valor total por fornecedor
    - ✅ Cálculo de percentual por fornecedor
    - ✅ Ordenação descrescente por valor
    - ✅ Geração em PDF e Excel
  - ✅ **PDF Individual de Fornecedor**:
    - ✅ 7 seções de dados (documentação, contatos, comercial, etc)
    - ✅ Endereços formatados com ocultação automática de CEP/UF para fornecedores internacionais
    - ✅ Botão "Ver PDF" na página de detalhe do fornecedor
    - ✅ Preservação de aspect ratio do logo em PDF via `ImageReader`
  - ✅ Envio por Email e WhatsApp
  - ✅ Menu da sidebar com links para ambos os relatórios

- ✅ **3.2 Gestão de Usuários - Campo "Vendedor Responsável"**
  - ✅ Fix: Dropdown de vendedor agora filtra apenas por `status='ATIVO'`
  - ✅ Fix: Ordenação alfabética por `nome_completo`
  - ✅ Fix: Filtro dinâmico por `tipo_mercado` baseado em `tipo_cliente` do cliente
  - ✅ Modificação em `ClienteForm.__init__()` para aplicar filtros corretos
  - ✅ Criação de vendor EXTERNO ("Carlos Silva - Exportação") para empresa que faltava

**Arquivos Criados/Modificados:**
- ✅ `cadastros/forms_relatorio_fornecedor.py` (novo formulário com filtros)
- ✅ `cadastros/forms_relatorio_fornecedor_ranking.py` (novo formulário para ranking)
- ✅ `cadastros/relatorio_utils_fornecedor.py` (geração PDF/Excel de lista e individual)
- ✅ `cadastros/relatorio_utils_fornecedor_ranking.py` (geração PDF/Excel de ranking)
- ✅ `cadastros/templates/cadastros/relatorios/relatorio_fornecedor.html` (template)
- ✅ `cadastros/templates/cadastros/relatorios/relatorio_fornecedor_ranking.html` (template)
- ✅ `cadastros/views.py`: Funções `relatorio_fornecedor()`, `relatorio_fornecedor_ranking()`, `fornecedor_pdf()`
- ✅ `cadastros/urls.py`: Rotas adicionadas
- ✅ `cadastros/enviador.py`: Classe `EnviadorRelatorioFornecedores` para envio de relatórios
- ✅ `templates/sidebar.html`: Menu items para relatórios de fornecedores
- ✅ `cadastros/forms.py`: Fix do filtro de `vendedor_responsavel` em `ClienteForm`

**Testes Realizados:**
- ✅ Relatório de clientes filtra corretamente por tipo_cliente
- ✅ Relatório de fornecedores com todos os filtros funcionando
- ✅ Ranking de compras calcula corretamente percentuais
- ✅ PDF individual exibe endereço internacional sem CEP/UF
- ✅ Envio por Email e WhatsApp funciona
- ✅ Dropdown de vendedor exibe opciones corretas
- ✅ Filtro dinâmico por tipo_mercado funciona



### FASE 1: MELHORIAS DE ESTOQUE (Semana de 03-02-2026)


#### 1.1 Aprimoramentos do RF-055 (Alertas)
- [ ] **Filtros avançados**: Por tipo de alerta, categoria, faixa de preço
- [ ] **Agendamento de relatórios**: Enviar por email automaticamente (diariamente/semanalmente)
- [ ] **Notificações em tempo real**: Push notifications quando estoque atinge limite crítico
- [ ] **Histórico de alertas**: Rastrear quando produtos entraram/saíram de alerta
- [ ] **Ações rápidas**: Botão para criar solicitação de compra direto do relatório
- [ ] **Análise de tendências**: Gráfico de evolução do estoque nos últimos meses

#### 1.2 RF-056: Inventário Cíclico
- [ ] Criar modelo `InventarioCiclico` com agendamento de contagens
- [ ] Sistema de amostragem por categoria/valor ABC
- [ ] Registro de discrepâncias físico x sistema
- [ ] Conciliação automática
- [ ] Ajustes de estoque aprovados
- [ ] Relatório de acurácia do inventário

#### 1.3 RF-058: Controle de Defensivos e Fertilizantes
- [ ] Rastreamento adicional para produtos controlados (MAPA, ANVISA)
- [ ] Certificados de registro
- [ ] Datas de validade críticas
- [ ] Alertas especiais para produtos vencidos ou próximos a vencer
- [ ] Relatórios de consumo por talhão
- [ ] Integração com aplicações agrícolas

#### 1.4 RF-082: Requisições Internas
- [ ] CRUD de requisições entre departamentos/armazéns
- [ ] Fluxo de aprovação
- [ ] Integração com movimentações de estoque
- [ ] Rastreamento de status

#### 1.5 RF-083: Devoluções
- [ ] Processo de devolução de produtos
- [ ] Motivos de devolução
- [ ] Reintegração ao estoque
- [ ] Crédito para fornecedor/cliente

---

### FASE 2: COMPRAS E FORNECEDORES (Semana de 10-02-2026)

#### 2.1 RF-054: Parsing XML de NF-e
- [ ] Integração com serviço de parsing XML
- [ ] Validação automática de campos críticos
- [ ] Importação de CFOP, NCM, impostos
- [ ] Detecção de duplicatas
- [ ] Alertas para divergências (quantidade, valor)

#### 2.2 RF-059: Ranking e Avaliação de Fornecedores
- [ ] Scorecard: prazo entrega, qualidade, preço
- [ ] Histórico de compras por fornecedor
- [ ] Cálculo automático de ranking (A/B/C)
- [ ] Relatório comparativo de fornecedores
- [ ] Sugestão de fornecedor na solicitação de compra

#### 2.3 Melhorias de Cotação
- [ ] Cotação com múltiplos cenários (quantidade/prazo)
- [ ] Histórico de preços
- [ ] Alertas de preço anormal
- [ ] Integração com cotações de commodities (se aplicável)

---

### FASE 3: RASTREABILIDADE E QUALIDADE (Semana de 17-02-2026)

#### 3.1 RF-089: Rastreabilidade Completa (Insumo → Produto Final)
- [ ] Vincular insumo (estoque) → aplicação em talhão → colheita → produto final
- [ ] Cadeia reversa (produto final → qual talhão → qual insumo)
- [ ] Timeline visual de movimentação
- [ ] Relatório de rastreabilidade para certificações (GLOBALG.A.P, etc)

#### 3.2 RF-086: Bloqueio de Estoque Contaminado
- [ ] Status adicional: CONTAMINADO, EM_QUARENTENA
- [ ] Não permitir movimentação de lotes bloqueados
- [ ] Workflow de liberação com aprovação
- [ ] Registro de motivo e data

#### 3.3 Integrações com Produção
- [ ] Consumo automático de insumo quando aplicado em talhão
- [ ] Atualização de custo do talhão
- [ ] Alertas de falta de insumo para operação programada

---

### FASE 4: RELATÓRIOS E BI (Semana de 24-02-2026)

#### 4.1 Dashboards Analíticos
- [ ] Dashboard de custo de estoque
- [ ] Curva de consumo por produto
- [ ] Sazonalidade de demanda
- [ ] Dias de estoque média
- [ ] Cash flow de estoque

#### 4.2 Exportações de Dados
- [ ] Integração com Power BI
- [ ] Exportação para Google Sheets
- [ ] API para sistemas externos
- [ ] Webhooks para eventos de estoque

---

### FASE 5: MOBILE E OFFLINE (Semana de 03-03-2026)

#### 5.1 App Mobile para Estoque
- [ ] Leitura de QR Code / Código de Barras
- [ ] Contagem de estoque offline
- [ ] Síncronia automática
- [ ] Consulta rápida de saldo

#### 5.2 PWA (Progressive Web App)
- [ ] Offline mode para consultas
- [ ] Cache de dados críticos
- [ ] Push notifications

---

## 🎯 PRIORIDADES RECOMENDADAS

**CURTO PRAZO (Imediato):**
1. RF-056 Inventário Cíclico (reduz discrepâncias)
2. RF-054 Parsing de XML (integração fiscal)
3. Filtros e agendamento de RF-055 (melhora usabilidade)

**MÉDIO PRAZO (2-4 semanas):**
1. RF-089 Rastreabilidade completa (compliance e rastreamento)
2. RF-059 Ranking de fornecedores (reduz custos)
3. Dashboards analíticos de estoque

**LONGO PRAZO (1-3 meses):**
1. Mobile app com QR Code
2. Integrações com BI
3. RF-088 Empréstimos a produtores

---

10. GLOSSÁRIO
Account Sales: Demonstrativo de vendas enviado pelo importador
Booking: Reserva de espaço no navio
BL: Bill of Lading (Conhecimento de Embarque)
CAR: Cadastro Ambiental Rural
CFOP: Código Fiscal de Operações e Prestações
Cut-off: Prazo limite para entrega de documentos ou container
DUE: Declaração Única de Exportação
ETA/ETD: Estimated Time of Arrival/Departure
Fito: Certificado Fitossanitário
Gate-in/Gate-out: Entrada/Saída do container no terminal
GLOBALG.A.P.: Certificação de Boas Práticas Agrícolas
NC: Não Conformidade
Packing List: Lista de embalagem
PTV: Permissão de Trânsito de Vegetais
Rolagem: Não embarque do container no navio programado
VGM: Verified Gross Mass (Peso Bruto Verificado)
VIP: Valor de Importação Presumida

ANEXOS
Anexo A - Estrutura de Banco de Dados (a ser desenvolvido)
Anexo B - Diagramas de Fluxo BPMN (a ser desenvolvido)
Anexo C - Wireframes de Interface (a ser desenvolvido)
Anexo D - Matriz de Rastreabilidade (a ser desenvolvido)

Fim do Documento PRD v1.0