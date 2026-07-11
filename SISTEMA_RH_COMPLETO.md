# Sistema de Controle de RH - ERP Agrícola

## 📋 Visão Geral

Sistema completo para gerenciamento de:
- **Férias** - Controle de férias, abono pecuniário e períodos aquisitivos
- **Afastamentos** - Registro de licenças, atestados médicos, acidentes de trabalho com CAT e INSS
- **Rescisões** - Gerenciamento de desligamentos com cálculo automatizado de verbas rescisórias

## 🚀 Estrutura do Sistema

### URLs (rotas)
```
/cadastros/rh/                           - Dashboard de RH
/cadastros/rh/ferias/                    - Listar férias
/cadastros/rh/ferias/novo/               - Cadastrar férias
/cadastros/rh/ferias/<id>/               - Detalhes da férias
/cadastros/rh/ferias/<id>/editar/        - Editar férias
/cadastros/rh/ferias/<id>/excluir/       - Excluir férias

/cadastros/rh/afastamentos/              - Listar afastamentos
/cadastros/rh/afastamentos/novo/         - Cadastrar afastamento
/cadastros/rh/afastamentos/<id>/         - Detalhes do afastamento
/cadastros/rh/afastamentos/<id>/editar/  - Editar afastamento
/cadastros/rh/afastamentos/<id>/excluir/ - Excluir afastamento

/cadastros/rh/rescisoes/                 - Listar rescisões
/cadastros/rh/rescisoes/novo/            - Cadastrar rescisão
/cadastros/rh/rescisoes/<id>/            - Detalhes da rescisão
/cadastros/rh/rescisoes/<id>/editar/     - Editar rescisão
/cadastros/rh/rescisoes/<id>/excluir/    - Excluir rescisão
```

### Modelos de Dados

#### **FeriasFuncionario** (Férias)
**Campos Principais:**
- `funcionario` - FK para Funcionario
- Período aquisitivo (data_inicial, data_final)
- Período de gozo (data_inicio, data_fim)
- `dias_ferias` - Total de dias (máx 30)
- `dias_abono` - Abono pecuniário (máx 10 dias - venda de 1/3)
- `valor_abono` - Valor do abono
- Valores: `valor_bruto`, `valor_terco_constitucional`, `valor_descontos`
- `recibo_ferias` - Upload do recibo assinado
- `status` - AGENDADA, EM_GOZO, CONCLUIDA, CANCELADA

**Validações CLT:**
- Máximo 30 dias de férias
- Máximo 10 dias de abono pecuniário (1/3)
- Período concessivo de 12 meses

#### **AfastamentoFuncionario** (Licenças/Dias de Faltas)
**Campos Principais:**
- `funcionario` - FK para Funcionario
- `tipo_afastamento` - ATESTADO, ACIDENTE, MATERNIDADE, PATERNIDADE, AUXILIO_DOENCA
- Período: `data_inicio`, `data_prevista_retorno`, `data_retorno_efetivo`
- Informações médicas: `code_cid`, `nome_medico`, `crm_medico`
- `motivo` - Descrição do motivo
- **Acidente de Trabalho:**
  - `emitiu_cat` - Booleano
  - `numero_cat` - Número da CAT
  - `data_emissao_cat`
  - `documento_cat` - Upload da CAT
- **INSS:**
  - `encaminhado_inss` - Para afastamentos > 15 dias
  - `numero_beneficio_inss`
  - `data_concessao_beneficio`
- `status` - ATIVO, ENCERRADO, CANCELADO
- Uploads: `atestado_medico`, `documento_cat`, `outros_documentos`

**Regras de Negócio:**
- Afastamentos > 15 dias → Encaminhamento obrigatório ao INSS
- Acidente de trabalho → Geração de CAT (Comunicação de Acidente de Trabalho)
- Maternidade → 120 dias + 60 dias prorrogáveis
- Paternidade → 5 dias

#### **RescisaoContrato** (Desligamentos)
**Campos Principais:**
- `funcionario` - FK para Funcionario
- `tipo_rescisao` - PEDIDO_DEMISSAO, ACORDO, JUSTA_CAUSA, SEM_JUSTA_CAUSA
- `data_desligamento` - Data efetiva do desligamento
- `motivo_detalhado` - Descrição do motivo
- **Aviso Prévio:**
  - `data_aviso_previo`
  - `dias_aviso_previo` - 30 ou 90 dias
  - `aviso_previo_indenizado` - Booleano
  - `aviso_previo_indenizado_valor`
- **Verbas Rescisórias:**
  - `saldo_salario`
  - `ferias_vencidas` + `ferias_proporcionais`
  - `terco_ferias` (1/3 constitucional)
  - `decimo_terceiro_proporcional`
  - `outras_verbas` + `descricao_outras_verbas`
- **FGTS:**
  - `saldo_fgts`
  - `multa_fgts_percentual` - 40% (sem justa causa) ou 20% (acordo)
  - `multa_fgts_valor` (calculado automaticamente)
- **Descontos:**
  - `desconto_inss`
  - `desconto_irrf`
  - `outros_descontos`
- **Cálculos Automáticos:**
  - `valor_total` = soma de todas as verbas
  - `valor_liquido` = valor_total - descontos
- **Documentos:**
  - `documento_trct` - Termo de Rescisão do Contrato de Trabalho
  - `documento_exame_demissional`
  - `data_homologacao` - Obrigatória para contratos > 1 ano
- **Benefícios:**
  - `direito_seguro_desemprego` - Booleano
- `status` - EM_PROCESSO, CONCLUIDA, CANCELADA

**Método Especial:**
```python
rescisao.calcular_valor_liquido()  # Auto-calcula valor_liquido
```

### Views (Funções)

#### Dashboard RH
```python
rh_dashboard()  # GET /cadastros/rh/
```
Exibe:
- Total de funcionários ativos
- Férias agendadas, em gozo, concluídas
- Próximas férias (30 dias)
- Afastamentos ativos com filtro por tipo
- Rescisões em processo e do mês atual
- Gráficos de distribuição

#### Férias (CRUD Completo)
```python
ferias_list(request)      # GET /cadastros/rh/ferias/
ferias_create(request)    # GET/POST /cadastros/rh/ferias/novo/
ferias_detail(request, pk)# GET /cadastros/rh/ferias/<id>/
ferias_update(request, pk)# GET/POST /cadastros/rh/ferias/<id>/editar/
ferias_delete(request, pk)# GET/POST /cadastros/rh/ferias/<id>/excluir/
```
**Filtros:** Status, Funcionário, Busca por nome

#### Afastamentos (CRUD Completo)
```python
afastamento_list(request)      # GET /cadastros/rh/afastamentos/
afastamento_create(request)    # GET/POST /cadastros/rh/afastamentos/novo/
afastamento_detail(request, pk)# GET /cadastros/rh/afastamentos/<id>/
afastamento_update(request, pk)# GET/POST /cadastros/rh/afastamentos/<id>/editar/
afastamento_delete(request, pk)# GET/POST /cadastros/rh/afastamentos/<id>/excluir/
```
**Filtros:** Status, Tipo, Funcionário, Busca por nome/motivo

#### Rescisões (CRUD Completo)
```python
rescisao_list(request)      # GET /cadastros/rh/rescisoes/
rescisao_create(request)    # GET/POST /cadastros/rh/rescisoes/novo/
rescisao_detail(request, pk)# GET /cadastros/rh/rescisoes/<id>/
rescisao_update(request, pk)# GET/POST /cadastros/rh/rescisoes/<id>/editar/
rescisao_delete(request, pk)# GET/POST /cadastros/rh/rescisoes/<id>/excluir/
```
**Filtros:** Status, Tipo, Funcionário, Busca por nome/motivo
**Auto-cálculo:** Valor líquido é calculado automaticamente ao salvar

### Formulários (Django Forms)

#### FeriasFuncionarioForm (16 campos)
- Funcionário (select com filtro por empresa)
- Período aquisitivo (data_inicio, data_fim)
- Período de gozo (data_inicio, data_fim, dias_ferias)
- Abono pecuniário (dias_abono até 10, valor_abono)
- Valores (valor_bruto, valor_terco, valor_descontos)
- Recibo (file upload)
- Observações
- Status

#### AfastamentoFuncionarioForm (23 campos)
- Funcionário
- Tipo de afastamento
- Todos os campos médicos (CID, nome médico, CRM)
- Período (data_inicio, data_prevista_retorno, data_retorno_efetivo)
- CAT (emitiu_cat, numero_cat, data_emissao, upload)
- INSS (encaminhado_inss, numero_beneficio, data_concessao)
- Uploads (atestado_medico, documento_cat, outros_documentos)
- Observações
- Status

#### RescisaoContratoForm (35 campos)
- Funcionário
- Tipo de rescisão
- Data desligamento + motivo
- Aviso prévio (data, dias, se indenizado, valor)
- **Todas as verbas rescisórias** (9 campos)
- FGTS (saldo, percentual, valor)
- **Descontos** (INSS, IRRF, outros)
- Totalizadora automática (valor_total, valor_liquido)
- Documentos (TRCT, exame demissional)
- Data homologação
- Direito seguro desemprego
- Status

### Templates

#### Dashboard
```
templates/cadastros/rh/dashboard.html
```

#### Férias
```
templates/cadastros/rh/ferias_list.html          # Lista com cards
templates/cadastros/rh/ferias_form.html          # Formulário
templates/cadastros/rh/ferias_detail.html        # Detalhes
templates/cadastros/rh/ferias_confirm_delete.html # Confirmação
```

#### Afastamentos
```
templates/cadastros/rh/afastamento_list.html          # Lista
templates/cadastros/rh/afastamento_form.html          # Formulário
templates/cadastros/rh/afastamento_detail.html        # Detalhes
templates/cadastros/rh/afastamento_confirm_delete.html # Confirmação
```

#### Rescisões
```
templates/cadastros/rh/rescisao_list.html          # Lista
templates/cadastros/rh/rescisao_form.html          # Formulário
templates/cadastros/rh/rescisao_detail.html        # Detalhes
templates/cadastros/rh/rescisao_confirm_delete.html # Confirmação
```

## 📁 Armazenamento de Arquivos

```
MEDIA_ROOT/
├── rh/
│   ├── ferias/YYYY/MM/        # Recibos de férias
│   ├── afastamentos/YYYY/MM/  # Atestados médicos e CAT
│   ├── cat/YYYY/MM/           # Comunicações de Acidente
│   └── rescisoes/YYYY/MM/     # TRCT e exames demissionais
```

## 🔐 Segurança

**Isolamento Multi-Tenant:**
- Todas as views filtram por `request.user.empresa`
- Formulários filtram funcionários e afastamentos por empresa
- Paginação com 25 registros por página

**Validações:**
- Campos obrigatórios em formulários
- Máximos validados (férias 30 dias, abono 10 dias)
- Métodos `clean()` nos modelos para validações complexas

**Permissões:**
- Acesso validado com `@login_required`
- Operação delete requer confirmação com POST

## 📊 Funcionalidades Avançadas

### Dashboard RH
- **Widgets de estatísticas** com cores por status
- **Lista de próximas férias** (próximos 30 dias)
- **Afastamentos ativos** com detalhes de retorno
- **Gráfico de distribuição** por tipo de afastamento
- **Links rápidos** para criar novos registros

### Listagens
- **Filtros avançados:** Status, Tipo, Funcionário
- **Busca em tempo real** por nome ou motivo
- **Paginação:** 25 registros por página
- **Cards responsivos** com badge de status

### Formulários
- **Data pickers** com validação
- **Cálculos automáticos:**
  - Data fim de férias (baseado em dias)
  - Valor líquido de rescisão
  - Multa FGTS
- **File upload** com validação de tipo
- **Bootstrap 5 styled** com placeholders informativos

### Detalhes
- **Layout em duas colunas:** Dados + Sidebar
- **Downloads de documentos** anexados
- **Auditoria:** Quem cadastrou e quando
- **Badges coloridas** para status e tipos

## 🛠️ Tecnologias Utilizadas

- **Django 5.2.7** - Framework Web
- **Python 3.13.6** - Linguagem
- **Bootstrap 5** - UI Framework
- **SQLite** - Banco de dados

## 📝 Exemplo de Uso

### Registrar Férias
1. Acesse `/cadastros/rh/ferias/novo/`
2. Selecione o funcionário
3. Preencha os períodos (aquisitivo e gozo)
4. Insira os valores
5. Upload do recibo (opcional)
6. Clique em "Salvar Férias"

### Registrar Afastamento com CAT
1. Acesse `/cadastros/rh/afastamentos/novo/`
2. Selecione tipo "Acidente de Trabalho"
3. Preencha os dados de período e médicos
4. Marque "Emitiu CAT"
5. Upload da CAT e atestado
6. Salve o afastamento

### Processar Rescisão
1. Acesse `/cadastros/rh/rescisoes/novo/`
2. Selecione funcionário e tipo
3. Preencha aviso prévio e verbas
4. Sistema calcula automaticamente:
   - Multa FGTS (40% ou 20%)
   - Valor total das verbas
   - Valor líquido (total - descontos)
5. Upload documentos (TRCT, exame demissional)
6. Salve e acompanhe o status

## 🎯 Conformidade Legal

**Leis Brasileiras Contempladas:**
- **CLT (Consolidação das Leis do Trabalho)**
  - Férias: 30 dias + 1/3
  - Abono pecuniário: conversão de até 10 dias
  - Período aquisitivo: 12 meses
  
- **Lei 8.212/1991 (INSS)**
  - Afastamentos > 15 dias
  - Encaminhamento automático

- **Lei 8.213/1991 (Benefícios INSS)**
  - Auxílio-doença
  - Maternidade (120 + 60 dias)

- **Decreto 3.048/1999 (CAT)**
  - Comunicação de Acidente de Trabalho
  - Campos obrigatórios: CID, data, número CAT

- **CLT Art. 477 (Rescisão)**
  - TRCT (Termo de Rescisão)
  - Homologação obrigatória > 1 ano
  - Cálculo FGTS (40% sem justa causa)
  - Seguro-desemprego

## 📈 Melhorias Futuras

- [ ] Relatórios PDF com assinatura digital
- [ ] Integração com folha de pagamento
- [ ] Dashboard com gráficos avançados (Chart.js)
- [ ] Notificações automáticas de próximas férias
- [ ] Importação de dados em batch (Excel)
- [ ] E-mail automático ao colaborador
- [ ] Histórico completo de modificações
- [ ] Assinatura digital online para TRCT

## 📞 Suporte

Para erros ou dúvidas, consulte:
- Loja de apps Django
- Documentação oficial Django Forms
- Referência CLT e legislação trabalhista
