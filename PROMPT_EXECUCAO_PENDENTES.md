# PROMPT DE EXECUÇÃO — Módulos Pendentes do ERP Agrícola Salutaris

## CONTEXTO DO PROJETO

Você está trabalhando no **ERP Agrícola Salutaris**, uma plataforma SaaS Django multiempresa para gestão de produtores de frutas, packing houses e exportadoras. O projeto usa:

- **Backend:** Django 4.x + Django REST Framework
- **Banco de dados:** PostgreSQL (via Supabase em produção)
- **Autenticação:** Supabase + 2FA customizado
- **Frontend:** Django Templates + Bootstrap 5
- **Multitenancy:** modelo `Empresa` com isolamento por tenant
- **RBAC:** modelo `Role` com permissões granulares por módulo/ação
- **Apps Django existentes:** `core`, `usuarios`, `empresas`, `dashboard`, `metricas`, `cadastros`, `patrimonio`, `produtos`, `estoque`, `compras`, `financeiro`

**Regras arquiteturais obrigatórias:**
1. Todo model deve ter campo `empresa = ForeignKey(Empresa)` para isolamento multitenant
2. Usar `get_object_or_404` com filtro `empresa=request.user.empresa` em todas as views
3. Templates herdam de `base.html` e usam o sidebar existente
4. Formulários usam `forms.ModelForm` com Bootstrap classes
5. URLs seguem padrão: `app_name/recurso/`, `app_name/recurso/<pk>/`, `app_name/recurso/<pk>/editar/`, `app_name/recurso/<pk>/excluir/`
6. Views retornam JSON para requisições AJAX (`request.headers.get('X-Requested-With') == 'XMLHttpRequest'`)
7. Nomes de templates: `app/recurso_list.html`, `app/recurso_detail.html`, `app/recurso_form.html`, `app/recurso_confirm_delete.html`

---

## BLOCO 1 — MÓDULO: ESTUFAS E TRANSPLANTIO (RF-1200 a RF-1254)
**Criar novo app Django `estufas` ou adicionar ao app `cadastros`**

### 1.1 Modelos a criar

```python
# Estufa: estrutura física onde mudas são produzidas
class Estufa(Model):
    empresa, nome, codigo, area_m2, capacidade_bandejas
    ativo, observacoes, created_at

# LoteMuda: lote de mudas produzidas em uma estufa
class LoteMuda(Model):
    empresa, estufa, cultura, cultivar
    codigo_lote (UUID único), data_semeadura, quantidade_semeada
    lote_semente (identificador externo da semente)
    status: SEMEADO | EM_CRESCIMENTO | PRONTO | TRANSPLANTADO | ENCERRADO
    responsavel (FK Funcionario)

# PerdaEstufa: registro de perdas durante produção de mudas
class PerdaEstufa(Model):
    lote_muda, data, quantidade_perdida
    motivo: DOENCA | PRAGA | AMBIENTE | QUALIDADE | OUTRO
    observacao, responsavel

# AplicacaoEstufa: defensivos/fertilizantes aplicados na estufa
class AplicacaoEstufa(Model):
    lote_muda, data, tipo: DEFENSIVO | FERTILIZANTE
    produto (FK Produto), quantidade, unidade_medida
    responsavel, observacao

# MonitoramentoEstufa: monitoramento de pragas na estufa
class MonitoramentoEstufa(Model):
    lote_muda, data, praga (FK Praga)
    nivel_infestacao: AUSENTE | BAIXO | MEDIO | ALTO
    acao_tomada, responsavel

# Transplantio: evento de transplantio do lote para talhão
class Transplantio(Model):
    empresa, lote_muda, talhao (FK Talhao)
    data_transplantio, quantidade_transplantada
    tipo: TOTAL | PARCIAL
    responsavel (FK Funcionario)
    observacao, fotos

# ReplantioTalhao: registro de replantios após perdas no campo
class ReplantioTalhao(Model):
    talhao, data, quantidade
    origem_muda: ESTUFA | COMPRA | OUTRA_AREA
    lote_muda (FK LoteMuda, nullable)
    motivo_perda: CLIMA | PRAGA | DOENCA | MECANICO | OUTRO
    custo_adicional (Decimal)
    responsavel, observacao
```

### 1.2 Views a criar (CRUD completo)
- `estufa_list`, `estufa_create`, `estufa_detail`, `estufa_update`, `estufa_delete`
- `lote_muda_list`, `lote_muda_create`, `lote_muda_detail`, `lote_muda_update`
- `perda_estufa_create` (inline no detalhe do lote)
- `aplicacao_estufa_create` (inline no detalhe do lote)
- `monitoramento_estufa_create` (inline no detalhe do lote)
- `transplantio_create`, `transplantio_list` — ao criar, transfere custo do lote para o talhão
- `replantio_create` (inline no detalhe do talhão)
- Dashboard de estufas: disponibilidade de mudas, custo por muda

### 1.3 Regras de negócio
- RN-17: Custo da estufa rateado ao talhão automaticamente no transplantio
- RN-18: Lote sem talhão até o transplantio
- RN-19: Transplantio só permitido para talhões com status APTO
- RN-20: Replantio obrigatoriamente registrado
- `LoteMuda.quantidade_disponivel` = `quantidade_semeada` - soma(perdas) - soma(transplantios)

---

## BLOCO 2 — MÓDULO: PACKING HOUSE (RF-200 a RF-214)
**Criar novo app Django `packing`**

### 2.1 Modelos a criar

```python
# RecebimentoPacking: entrada de frutas no packing house
class RecebimentoPacking(Model):
    empresa, data_hora, talhao (FK), safra (FK)
    produtor (FK Produtor), numero_romaneio
    peso_bruto_kg, peso_liquido_kg, quantidade_caixas_entrada
    motorista (FK), placa_veiculo
    status: AGUARDANDO | EM_INSPECAO | APROVADO | REJEITADO
    observacao

# InspecaoEntrada: inspeção inicial no recebimento
class InspecaoEntrada(Model):
    recebimento (FK RecebimentoPacking)
    responsavel (FK Funcionario), data_hora
    temperatura_medida (Decimal)
    brix (Decimal), textura, aparencia
    percentual_defeitos (Decimal)
    resultado: APROVADO | APROVADO_COM_RESSALVA | REJEITADO
    observacoes, fotos

# LotePacking: lote processado no packing house
class LotePacking(Model):
    empresa, recebimento (FK), codigo_lote (único)
    cultura (FK), cultivar, calibre
    status: EM_PROCESSAMENTO | EMBALADO | EXPEDIDO | CANCELADO
    data_processamento

# PalletPacking: pallet montado no processo de embalagem
class PalletPacking(Model):
    lote_packing (FK), codigo_pallet (único, UUID)
    tipo_embalagem, quantidade_caixas, peso_liquido_kg, peso_bruto_kg
    calibre, categoria_qualidade: EXTRA | CATEGORIA_1 | CATEGORIA_2
    camara_fria (FK CamaraFria)
    temperatura_entrada, temperatura_saida
    data_embalagem, data_entrada_camara
    etiqueta_gerada (Bool), codigo_qr

# CamaraFria: câmaras de armazenamento frio
class CamaraFria(Model):
    empresa, nome, codigo, capacidade_pallets
    temperatura_min, temperatura_max (target)
    status: OPERACIONAL | MANUTENCAO | INATIVA

# RegistroTemperaturaCamara: log de temperatura por câmara
class RegistroTemperaturaCamara(Model):
    camara_fria, data_hora, temperatura_atual
    registrado_por (FK Funcionario), alerta_gerado (Bool)

# NaoConformidadePacking: NC gerada no packing
class NaoConformidadePacking(Model):
    empresa, pallet (FK, nullable), lote (FK, nullable)
    tipo: QUALIDADE | TEMPERATURA | PESO | EMBALAGEM | RASTREABILIDADE | OUTRO
    descricao, data_hora, responsavel
    status: ABERTA | EM_ANALISE | CORRIGIDA | ENCERRADA
    acao_corretiva, data_fechamento, fotos
```

### 2.2 Views a criar
- `recebimento_packing_list/create/detail/update`
- `inspecao_entrada_create` (inline)
- `lote_packing_list/detail`
- `pallet_list/create/detail` com geração de etiqueta QR
- `camara_fria_list/create/detail/update` com temperatura atual
- `temperatura_registrar` (endpoint AJAX para registro de temperatura)
- `nao_conformidade_list/create/detail/fechar`
- `dashboard_packing` — métricas de produtividade, câmara fria, NCs abertas

### 2.3 Regras de negócio
- RN-06: Pallet não liberado sem etiqueta válida
- RN-14: Divergências geram NC automaticamente
- Alerta automático quando temperatura da câmara sai do range configurado
- Rastreabilidade: RecebimentoPacking → LotePacking → PalletPacking → Container (módulo Exportação)

---

## BLOCO 3 — MÓDULO: QUALIDADE E CLASSIFICAÇÃO (RF-Q-001 a RF-Q-012)
**Criar models no app `packing` ou novo app `qualidade`**

### 3.1 Modelos a criar

```python
# RelatorioQualidadeContainer: relatório de qualidade por container
class RelatorioQualidadeContainer(Model):
    empresa, container (FK Container — módulo Exportação)
    cultura (FK), data_inspecao
    responsavel (FK Funcionario)
    # Parâmetros técnicos
    brix_min, brix_max, brix_medio
    temperatura_min, temperatura_max
    percentual_defeitos_externos, percentual_defeitos_internos
    # Classificação
    cor_qualidade: VERDE | AMARELO | VERMELHO
    # Impacto financeiro
    percentual_desconto_account_sales (Decimal, calculado por regra)
    observacoes, fotos

# ParametroQualidadePorCliente: regras de desconto por cor para cada cliente
class ParametroQualidadePorCliente(Model):
    empresa, cliente (FK)
    cor: AMARELO | VERMELHO
    percentual_desconto_minimo, percentual_desconto_maximo
    requer_justificativa (Bool)
```

### 3.2 Regras
- RF-Q-004: Fotos/evidências obrigatórias
- RF-Q-005: Desconto calculado automaticamente no Account Sales com base na cor
- RN-28: Qualidade vermelha exige justificativa + evidências (campo `observacoes` obrigatório)
- Alertas gerados quando cor AMARELO ou VERMELHO detectada (RF-Q-006)

---

## BLOCO 4 — MÓDULO: EXPORTAÇÃO E DOCUMENTAÇÃO (RF-250 a RF-267)
**Criar novo app Django `exportacao`**

### 4.1 Modelos a criar

```python
# Booking: reserva de espaço no navio
class Booking(Model):
    empresa, numero_booking (único)
    armador (FK), navio (FK), voyage
    porto_origem (FK Porto), porto_destino (FK Porto)
    data_corte_documental, data_corte_operacional, data_vgm
    data_gate_in_limite, data_etd, data_eta
    status: ABERTO | CONFIRMADO | CANCELADO | EMBARCADO
    observacoes

# Container: container de exportação
class Container(Model):
    empresa, booking (FK Booking)
    numero_container (único), tipo: DRY_20 | DRY_40 | REEFER_20 | REEFER_40
    tara_kg, peso_maximo_kg
    temperatura_set_point (para reefer)
    # Lacres
    lacre_armador, lacre_extra, lacre_custom
    status: VAZIO | EM_CARREGAMENTO | CARREGADO | GATE_IN | EMBARCADO | ENTREGUE
    # Gate-in / Gate-out
    data_gate_in, terminal_gate_in
    data_embarque
    # Rastreamento
    checklist_higiene_aprovado (Bool), fotos_interior, fotos_exterior, fotos_lacre
    observacoes

# ContainerPallet: relação Container ↔ Pallet
class ContainerPallet(Model):
    container (FK), pallet (FK PalletPacking)
    ordem, data_carregamento

# InvoiceExportacao: fatura de exportação
class InvoiceExportacao(Model):
    empresa, container (FK Container)
    numero_invoice (único), data_emissao
    cliente (FK), incoterm, moeda (FK Moeda)
    valor_total, valor_frete, valor_seguro
    status: RASCUNHO | EMITIDA | ENVIADA | PAGA
    # Documentos
    arquivo_invoice, arquivo_packing_list
    arquivo_certificado_origem, arquivo_fito
    arquivo_bl, arquivo_due

# DocumentoEmbarque: controle de documentos por container
class DocumentoEmbarque(Model):
    container (FK Container)
    tipo: INVOICE | PACKING_LIST | FITO | PTV | DUE | CO | BL | OUTRO
    status: PENDENTE | ENVIADO | APROVADO | RECUSADO
    versao, data_envio, enviado_por
    arquivo, observacao
    # Workflow GO/NO-GO: aprovado por dois setores (RF-260, RN-16)
    aprovado_comercial (Bool), aprovado_operacional (Bool)

# ChecklistContainer: checklist obrigatório antes de liberar o container
class ChecklistContainer(Model):
    container (FK), responsavel (FK Funcionario), data_hora
    foto_interior_ok, foto_exterior_ok, foto_lacre_ok
    temperatura_ok, higiene_ok, peso_vgm_ok
    status_geral: APROVADO | REPROVADO
    observacoes
```

### 4.2 Views a criar
- `booking_list/create/detail/update/cancel`
- `container_list/create/detail/update`
- `container_carregar` — associar pallets ao container
- `invoice_list/create/detail/update/emitir_pdf`
- `packing_list_gerar` — gera packing list automaticamente dos pallets
- `documento_embarque_list/upload/aprovar/recusar`
- `checklist_container_create/detail`
- `dashboard_exportacao` — KPIs: containers em aberto, cut-offs próximos, status por booking

### 4.3 Regras de negócio
- RN-07: Faturamento só após confirmação do booking
- RN-12: Container não sai sem foto interna, externa e lacre
- RN-15: Produto não vai para exportação sem checklist liberado
- RN-16: Documentos só enviados ao cliente com aprovação de 2 setores
- RF-265: Monitoramento automático de cut-offs com alertas antecipados
- RF-259: Workflow GO/NO-GO obrigatório

---

## BLOCO 5 — MÓDULO: ACCOUNT SALES E RATEIO COMERCIAL (RF-AS-001 a RF-AS-012)
**Adicionar ao app `financeiro` ou criar app `account_sales`**

### 5.1 Modelos a criar

```python
# AccountSale: demonstrativo de vendas enviado pelo importador
class AccountSale(Model):
    empresa, invoice (FK InvoiceExportacao)
    numero_account_sale, data_recebimento
    cliente (FK), moeda (FK Moeda)
    # Valores
    valor_bruto_venda, valor_frete_cobrado
    valor_outros_descontos, valor_liquido
    taxa_cambio_brl, valor_liquido_brl
    # Qualidade
    relatorio_qualidade (FK RelatorioQualidadeContainer, nullable)
    desconto_qualidade_pct, desconto_qualidade_valor
    status: RECEBIDO | EM_RATEIO | RATEADO | FINALIZADO
    arquivo_original (PDF/XLS), observacoes

# RateioAccountSale: rateio do account sale por produtor/cooperado
class RateioAccountSale(Model):
    account_sale (FK)
    produtor (FK Produtor)
    percentual_participacao (Decimal)
    # Receitas
    valor_bruto_produtor, descontos_produtor, valor_liquido_produtor
    # Custos rateados
    custo_frete, custo_packing, custo_logistica, custo_outros
    valor_final_produtor
    # Conta corrente
    abatimento_emprestimo (Decimal)
    abatimento_adiantamento (Decimal)
    valor_a_pagar_produtor (calculado)
    status: CALCULADO | APROVADO | PAGO

# RegraCustoRateio: configuração de como ratear cada tipo de custo
class RegraCustoRateio(Model):
    empresa, nome, tipo_custo
    criterio: POR_CAIXA | POR_PESO | POR_VALOR | IGUAL | PERSONALIZADO
    ativo (Bool)
```

### 5.2 Views a criar
- `account_sale_list/create/detail/update`
- `account_sale_ratear` — calcula e aplica rateio automático
- `rateio_detail/aprovar/pagar`
- `regra_custo_rateio_list/create/update`
- `dashboard_account_sales` — KPIs por safra, por produtor, por cliente

---

## BLOCO 6 — MÓDULO: ADIANTAMENTOS INTERNACIONAIS (RF-960 a RF-969)
**Adicionar ao app `financeiro`**

### 6.1 Modelos a criar

```python
# AdiantamentoInternacional: adiantamento recebido de cliente importador
class AdiantamentoInternacional(Model):
    empresa, cliente (FK)
    data_recebimento, moeda (FK Moeda)
    valor_moeda_estrangeira, taxa_cambio_brl, valor_brl
    forma_pagamento: TT | DEPOSITO | OUTRO
    referencia_swift, arquivo_comprovante
    observacoes
    saldo_disponivel_moeda (calculado: valor - soma abatimentos)

# AbatimentoAdiantamento: abatimento do adiantamento em um account sale
class AbatimentoAdiantamento(Model):
    adiantamento (FK), account_sale (FK RateioAccountSale)
    valor_abatido_moeda, taxa_cambio_brl, valor_abatido_brl
    data_abatimento
```

### 6.2 Views a criar
- `adiantamento_list/create/detail/update`
- `extrato_adiantamentos` — extrato por cliente com saldos em moeda e BRL
- Exibição no Portal do Cliente (RF-965)

---

## BLOCO 7 — MÓDULO: HISTÓRICO FINANCEIRO POR INVOICE (RF-HF-001 a RF-HF-011)
**Adicionar ao app `financeiro`**

### 7.1 Modelos a criar

```python
# HistoricoFinanceiroInvoice: consolidado de receitas e despesas por invoice
class HistoricoFinanceiroInvoice(Model):
    empresa, invoice (FK InvoiceExportacao)
    # Receitas
    receita_venda_brl, receita_vip_brl, bonificacoes_brl, creditos_brl
    # Despesas mercado interno
    icms, frete_interno, avarias_internas, seguro, comissao
    # Despesas portuárias
    movimentacao_patio, energia_frio, scanner, lar_fee
    genset_alugado, alteracao_set_point, quebra_lacre
    despesas_dhl, despachante_aduaneiro, armazenagem_porto
    correcao_documentacao, transbordo_shifting, demurrage
    # Cálculos
    receita_total_brl (calculado), despesa_total_brl (calculado)
    margem_bruta_brl (calculado), margem_percentual (calculado)
    # Comparação meta x realizado
    meta_valor_brl, desvio_brl (calculado)

# RateioCustoPorCriterio: divisão de custos entre culturas/pallets
class RateioCustoPorCriterio(Model):
    historico (FK), tipo_custo, valor_total
    criterio: CULTURA | PALETES | CAIXAS | PESO | VALOR_PROPORCIONAL
```

### 7.2 Views a criar
- `historico_invoice_list/detail/create`
- `historico_invoice_lancamento` — lançamento de custos por categoria
- `relatorio_margem_por_container` — RF-HF-008
- `relatorio_margem_por_cliente` — comparativo clientes
- `timeline_financeira_invoice` — RF-HF-007

---

## BLOCO 8 — MÓDULO: FORMAÇÃO DE PREÇO (RF-FP-001 a RF-FP-007)
**Adicionar ao app `financeiro` ou `cadastros`**

### 8.1 Modelos a criar

```python
# FormacaoPreco: cálculo de preço mínimo de venda por cultura/cliente
class FormacaoPreco(Model):
    empresa, safra (FK Safra), cultura (FK Cultura), cliente (FK)
    moeda (FK Moeda), data_calculo
    # Custos (preenchidos automaticamente de outros módulos)
    custo_estufa, custo_transplantio, custo_replantio
    custo_insumos, custo_mao_obra, custo_frota
    custo_packing, custo_logistica_interna
    custo_total_producao_brl (calculado)
    # Formação
    margem_desejada_pct, custo_por_kg, preco_minimo_kg
    # Comparação
    preco_negociado_moeda, preco_negociado_brl
    resultado: LUCRO | PREJUIZO | EQUILIBRIO
    alerta_prejuizo (Bool)  # RN-29
    observacoes
```

### 8.2 Views a criar
- `formacao_preco_list/create/detail/update`
- `formacao_preco_calcular` — busca custos automáticos de outros módulos
- `simulador_preco` — cenários what-if (RF-FP-005)
- Alerta automático quando preço < custo (RF-FP-004)

---

## BLOCO 9 — MÓDULO: ROLAGEM DE CONTAINER (RF-800 a RF-809)
**Adicionar ao app `exportacao`**

### 9.1 Modelos a criar

```python
# RolagemContainer: registro de não-embarque e reembarque
class RolagemContainer(Model):
    empresa, container (FK Container)
    data_notificacao, motivo: ARMADOR | NAVIO | OPERACIONAL | CLIMA | OUTRO
    descricao_motivo, evidencias
    # Novo booking
    novo_booking (FK Booking, nullable)
    status: REGISTRADA | NOVO_BOOKING_CRIADO | RESOLVIDA
    # Custos
    custo_demurrage, custo_armazenagem, custo_shifting
    custo_transporte_adicional, custo_energia_frio, custo_total
    # Resposta do armador
    resposta_armador: PENDENTE | ACEITO | PARCIAL | RECUSADO
    valor_aceito_armador, carta_ao_armador (arquivo)
    observacoes
```

### 9.2 Views a criar
- `rolagem_list/create/detail/update`
- `rolagem_gerar_carta_armador` — gera PDF da carta automática
- `rolagem_registrar_resposta`
- `dashboard_rolagensarmador` — indicadores por armador

---

## BLOCO 10 — MÓDULO: PORTAL DO CLIENTE COM TIMELINE (RF-660 a RF-668)
**Adicionar templates e views ao app `cadastros` ou criar app `portal_cliente`**

### 10.1 Views a criar
- `portal_cliente_login` — login por token ou credencial separada
- `portal_cliente_dashboard` — pedidos em andamento, saldo de adiantamentos
- `portal_cliente_timeline` — timeline completa do pedido: Produção → Qualidade → Packing → Gate-in → Embarque → Chegada
- `portal_cliente_documentos` — lista e download de documentos de embarque
- `portal_cliente_invoices` — faturas e invoices
- `portal_cliente_qualidade` — relatórios de qualidade (RF-664)
- `portal_cliente_adiantamentos` — extrato de adiantamentos e saldo (RF-666)
- `portal_cliente_tracking` — tracking marítimo via API navio (RF-667)

### 10.2 Template separado
- Layout próprio sem sidebar da empresa (acesso externo)
- Responsive e com logo da empresa exportadora
- Suporte a inglês (i18n)

---

## BLOCO 11 — PORTAL DO DESPACHANTE (RF-680 a RF-683)
**Adicionar ao app `exportacao`**

### 11.1 Views a criar
- `portal_despachante_login`
- `portal_despachante_containers` — containers atribuídos ao despachante
- `portal_despachante_upload_documento` — upload de Fito, PTV, DUE, CO, BL
- `portal_despachante_validar_versao` — verificação se versão enviada é a mais recente
- `portal_despachante_notificar_financeiro` — notificação automática após upload

---

## BLOCO 12 — FINANCEIRO COMPLETO (RF-400 a RF-411)
**Completar o app `financeiro`**

### 12.1 Modelos a criar

```python
# ContaReceber: complemento do financeiro
class ContaReceber(Model):
    empresa, descricao, cliente (FK, nullable)
    invoice (FK InvoiceExportacao, nullable)
    valor_total, data_vencimento, data_recebimento (nullable)
    status: ABERTO | PARCIAL | RECEBIDO | CANCELADO
    forma_recebimento, conta_bancaria, observacoes

# ParcelaContaReceber
class ParcelaContaReceber(Model):
    conta_receber (FK), numero_parcela
    valor, data_vencimento, data_recebimento
    status: ABERTA | RECEBIDA | ATRASADA

# ContaBancaria: contas bancárias da empresa
class ContaBancaria(Model):
    empresa, banco, agencia, conta_corrente
    tipo: CORRENTE | POUPANCA | INVESTIMENTO
    moeda (FK Moeda), saldo_atual, ativa (Bool)

# LancamentoBancario: movimentações bancárias para conciliação
class LancamentoBancario(Model):
    conta_bancaria (FK), data, valor, tipo: CREDITO | DEBITO
    descricao, referencia_externa
    conciliado (Bool), conta_pagar (FK, nullable), conta_receber (FK, nullable)
```

### 12.2 Views a criar
- `conta_receber_list/create/detail/update`
- `parcela_receber_receber` — baixar recebimento
- `conciliacao_bancaria` — upload OFX e conciliação
- `fluxo_caixa_projetado` — DRE e projeções (RF-403)
- `relatorio_rentabilidade_container` — RF-410
- `posicao_caixa` — saldo atual por conta (RF-407)

---

## BLOCO 13 — BALANÇO DE MASSAS (RF-BM-001 a RF-BM-003)
**Adicionar ao app `packing` ou `cadastros`**

### 13.1 Modelos a criar

```python
# BalancoMassas: controle de destino dos frutos por safra
class BalancoMassas(Model):
    empresa, safra (FK), cultura (FK), talhao (FK, nullable)
    periodo_inicio, periodo_fim
    # Entrada
    kg_colhidos
    # Saída
    kg_exportacao, kg_mercado_interno, kg_doacao
    kg_descarte, kg_racao_animal, kg_industrializacao
    kg_granel, kg_perdas_avarias
    # Divergências (calculado)
    kg_recebido_packing (do RecebimentoPacking)
    kg_embalado (do LotePacking)
    kg_expedido (do Container)
    divergencia_campo_packing (calculado)
    divergencia_packing_expedido (calculado)
    # Relatório GLOBALG.A.P.
    aprovado_globalg_a_p (Bool)
```

### 13.2 Views
- `balanco_massas_list/create/detail`
- `balanco_massas_gerar` — preenche automaticamente buscando dados de outros módulos
- `relatorio_globalg_a_p` — relatório obrigatório para certificação

---

## BLOCO 14 — PENDÊNCIAS INTERNAS EM MÓDULOS EXISTENTES

### 14.1 Almoxarifado — RF-082 Requisições Internas
- Modelos: `RequisicaoInterna`, `ItemRequisicaoInterna` (verificar se `Requisicao` já existe no app `cadastros`)
- Views: `requisicao_list/create/detail/aprovar/cancelar`
- Fluxo: criar requisição → aprovar → movimentação automática de estoque

### 14.2 Almoxarifado — RF-083 Devoluções
- Modelo: `DevolucaoEstoque` com motivo, fornecedor/cliente e crédito
- Views: `devolucao_create/detail/processar`
- Ao processar: reintegra ao estoque e gera crédito

### 14.3 Almoxarifado — RF-086 Bloqueio de Estoque Contaminado
- Adicionar status `CONTAMINADO` e `QUARENTENA` ao model `Lote`
- View: `lote_bloquear/liberar` com workflow de aprovação
- Impedir movimentações de lotes bloqueados em `MovimentacaoEstoque`

### 14.4 Compras — RF-058 Controle de Defensivos
- Adicionar campos ao `Produto`: `numero_registro_mapa`, `data_vencimento_registro`, `classe_toxicologica`
- RN-27: Filtrar defensivos sem registro MAPA (somente admin vê)
- Alerta de produtos com registro vencido ou próximo a vencer (30 dias)

### 14.5 Compras — RF-059 Ranking de Fornecedores
- Calcular score por: prazo_entrega_medio, percentual_divergencias, valor_total_comprado
- View: `ranking_fornecedores` com filtro por período e categoria
- Geração em PDF/Excel

### 14.6 Produção Agrícola — RF-107 Pluviometria
- Modelo: `RegistroPluviometria` (fazenda, data, mm_chuva, responsavel)
- Views: `pluviometria_list/create`, gráfico de histórico por mês

### 14.7 Produção Agrícola — RF-108/RF-111 Qualidade de Campo / Caderno de Campo
- Modelo: `CadernosCampo` com registros diários por talhão
- Campos: atividade realizada, insumos usados, funcionários, condições climáticas, fotos
- Exportação como PDF para GLOBALG.A.P.

### 14.8 Financeiro — Contas a Receber básico
- Já descrito no Bloco 12 — implementar como mínimo: ContaReceber + ParcelaContaReceber

---

## INSTRUÇÕES DE IMPLEMENTAÇÃO

### Ordem recomendada de implementação

1. **Bloco 13 — Balanço de Massas** (depende de Packing, implementar os modelos básicos primeiro)
2. **Bloco 1 — Estufas e Transplantio** (pré-requisito para Produção completa)
3. **Bloco 2 — Packing House** (pré-requisito para Exportação)
4. **Bloco 3 — Qualidade** (junto com Packing House)
5. **Bloco 4 — Exportação** (pré-requisito para Account Sales e Histórico Financeiro)
6. **Bloco 12 — Financeiro ContaReceber** (pré-requisito para Account Sales)
7. **Bloco 6 — Adiantamentos Internacionais**
8. **Bloco 5 — Account Sales e Rateio**
9. **Bloco 7 — Histórico Financeiro por Invoice**
10. **Bloco 8 — Formação de Preço**
11. **Bloco 9 — Rolagem de Container**
12. **Bloco 10 — Portal do Cliente**
13. **Bloco 11 — Portal do Despachante**
14. **Bloco 14 — Pendências Internas**

### Para cada bloco, siga este padrão:

```
1. Criar/modificar models.py
2. Criar migration: python manage.py makemigrations
3. Criar forms.py (ModelForm para cada model)
4. Criar views.py (CRUD completo + views especiais)
5. Criar urls.py (registrar no urls.py principal)
6. Criar templates (list, detail, form, confirm_delete)
7. Adicionar ao sidebar (templates/sidebar.html)
8. Adicionar ao RBAC (criar permissões nos planos SaaS)
9. Criar/atualizar testes básicos
```

### Padrão de permissões por plano

```python
# Verificar plano na view:
if not request.user.empresa.plano_permite('modulo_exportacao'):
    return HttpResponseForbidden()

# Planos que devem ter acesso:
# Exportação: Enterprise, Enterprise Plus
# Packing House: Professional, Enterprise, Enterprise Plus
# Estufas: Professional, Enterprise, Enterprise Plus
# Account Sales: Enterprise, Enterprise Plus
```

---

## NOTAS FINAIS

- Sempre testar com empresa multitenant (pelo menos 2 empresas no banco de teste)
- Manter consistência com nomes de variáveis em português (padrão do projeto)
- Todos os valores monetários em `DecimalField(max_digits=15, decimal_places=2)`
- Campos de data/hora em `DateTimeField`, datas simples em `DateField`
- Fotos/evidências em `ImageField` com `upload_to` separado por empresa
- Arquivos PDF/XLS em `FileField` com `upload_to` separado por empresa
- Status fields usam `CharField(choices=...)` com constantes em maiúsculas
- Usar `select_related` e `prefetch_related` para evitar N+1 queries

---

*Prompt gerado em 2026-04-27 a partir do PRD v1.0 e análise do código atual*
