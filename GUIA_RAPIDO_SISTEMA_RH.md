# 🎯 Guia Rápido - Sistema RH Completo

## 🚀 Como Usar o Sistema RH

### Acessar o Dashboard RH
1. Faça login no ERP Agrícola
2. Vá para: **URL: `/cadastros/rh/`**
3. Você verá o dashboard com:
   - Total de funcionários ativos
   - Férias agendadas e em gozo
   - Afastamentos ativos
   - Próximas férias dos próximos 30 dias

### 📝 Registrar Férias

**Passo a Passo:**
1. No Dashboard RH, clique em **"Cadastrar Férias"** (botão azul)
2. Ou acesse: `/cadastros/rh/ferias/novo/`
3. Preencha os campos:
   - **Funcionário** - Selecione na dropdown
   - **Período Aquisitivo** - Datas do período de 12 meses trabalhados
   - **Período de Gozo** - Quando as férias serão tiradas
   - **Dias de Férias** - De 1 a 30 dias
   - **Dias de Abono** - De 0 a 10 dias (venda de 10 dias = 1/3 das férias)
   - **Valores** - Valor bruto, 1/3 constitucional, descontos
4. Upload do recibo assinado (PDF - opcional)
5. Clique em **"Salvar Férias"**

**Exemplo:**
```
Período Aquisitivo: 01/02/2025 - 31/01/2026
Período de Gozo: 15/07/2026 - 29/07/2026 (15 dias)
Abono Pecuniário: 5 dias (venda)
Valor Bruto: R$ 5.000,00
```

---

### 🏥 Registrar Afastamento/Atestado

**Passo a Passo:**
1. No Dashboard RH, clique em **"Registrar Afastamento"** (botão amarelo)
2. Ou acesse: `/cadastros/rh/afastamentos/novo/`
3. Preencha os dados:
   - **Funcionário** - Selecione
   - **Tipo de Afastamento** - Escolha:
     - Atestado Médico
     - Acidente de Trabalho
     - Licença Maternidade
     - Licença Paternidade
     - Auxílio Doença
   - **Data de Início** - Quando começou
   - **Data Prevista de Retorno** - Quando volta (estimativa)
   - **CID** - Código da doença (se houver)
   - **Médico** - Nome e CRM

**Se for Acidente de Trabalho:**
- Marque: "Emitiu CAT"
- Insira o número da CAT
- Upload do documento CAT

**Se Afastamento > 15 dias:**
- Sistema automaticamente marca como "Encaminhado INSS"
- Insira o número do benefício

4. Upload de documentos:
   - Atestado médico (PDF)
   - CAT (se acidente)
5. Clique em **"Salvar Afastamento"**

**Exemplo - Atestado Simples:**
```
Funcionário: João Silva
Tipo: Atestado Médico
Período: 10/02/2026 - 12/02/2026 (3 dias)
CID: M79.3
Médico: Dr. Pedro | CRM: 123456
```

**Exemplo - Acidente de Trabalho:**
```
Funcionário: Maria Santos
Tipo: Acidente de Trabalho
Período: 08/02/2026 - 15/02/2026 (7 dias)
CAT: Nº 12345678
INSS: Após 15 dias encaminha automaticamente
```

---

### 📋 Registrar Rescisão/Desligamento

**Passo a Passo:**
1. No Dashboard RH, clique em **"Registrar Rescisão"** (botão vermelho)
2. Ou acesse: `/cadastros/rh/rescisoes/novo/`
3. Selecione o **Funcionário** e **Tipo de Rescisão:**
   - Pedido de Demissão
   - Acordo
   - Justa Causa
   - Sem Justa Causa

4. Preencha **Data de Desligamento** e motivo

5. **Aviso Prévio:**
   - Data do aviso (se houver)
   - Dias (30 ou 90)
   - Se foi indenizado ou trabalhado

6. **Verbas Rescisórias** (preencha os valores):
   - Saldo de Salário
   - Férias vencidas
   - Férias proporcionais
   - 1/3 de férias
   - 13º proporcional
   - Outras verbas

7. **FGTS:**
   - Saldo FGTS
   - Multa automática (40% sem justa causa, 20% acordo)

8. **Descontos:**
   - INSS
   - IRRF
   - Outros descontos

9. **O Sistema Calcula Automaticamente:**
   - ✅ Valor total das verbas
   - ✅ Multa FGTS (40% ou 20%)
   - ✅ Valor líquido (total - descontos)

10. **Documentos:**
    - Data do exame demissional
    - Data da homologação (obrigatória se > 1 ano)
    - Upload TRCT
    - Marcar se tem direito a seguro-desemprego

11. Clique em **"Salvar Rescisão"**

**Exemplo - Rescisão sem Justa Causa:**
```
Funcionário: Carlos Alberto
Tipo: Sem Justa Causa
Data Desligamento: 20/02/2026
Tempo de serviço: 3 anos

VERBAS:
- Saldo Salário: R$ 3.000,00
- Férias Vencidas: R$ 2.500,00
- Férias Proporcionais: R$ 1.250,00
- 1/3 Férias: R$ 1.250,00
- 13º Proporcional: R$ 1.100,00
- Total: R$ 9.100,00

FGTS:
- Saldo: R$ 8.000,00
- Multa 40%: R$ 3.200,00

DESCONTOS:
- INSS: R$ 750,00
- IRRF: R$ 1.200,00
- Total Descontos: R$ 1.950,00

VALOR LÍQUIDO: R$ 7.150,00
```

---

## 📊 Visualizar Listagens

### Férias
1. Acesse: `/cadastros/rh/ferias/`
2. Use os filtros:
   - **Status:** Agendada, Em Gozo, Concluída, Cancelada
   - **Funcionário:** Selecione na dropdown
   - **Busca:** Digite nome do funcionário

### Afastamentos
1. Acesse: `/cadastros/rh/afastamentos/`
2. Use os filtros:
   - **Status:** Ativo, Encerrado, Cancelado
   - **Tipo:** Atestado, Acidente, Maternidade, etc.
   - **Funcionário:** Selecione
   - **Busca:** Nome ou motivo

### Rescisões
1. Acesse: `/cadastros/rh/rescisoes/`
2. Use os filtros:
   - **Status:** Em Processo, Concluída, Cancelada
   - **Tipo:** Pedido Demissão, Acordo, Justa Causa, etc.
   - **Funcionário:** Selecione
   - **Busca:** Nome ou motivo

---

## 🔍 Visualizar Detalhes

1. Clique no card da férias/afastamento/rescisão
2. Ou clique no botão **"Detalhes"** (ícone de olho)
3. Veja todas as informações:
   - Dados do funcionário
   - Períodos e datas
   - Valores e cálculos
   - Documentos anexados
   - Histórico de cadastro

---

## ✏️ Editar Registros

1. Na listagem, clique no botão **"Editar"** (ícone de lápis)
2. Ou acesse a página de detalhes e clique em **"Editar"**
3. Modifique os campos necessários
4. Clique em **"Salvar"**

---

## 🗑️ Deletar Registros

1. Na listagem ou detalhes, clique em **"Excluir"** (ícone de lixo)
2. Confirme a exclusão na página de confirmação
3. O registro será deletado permanentemente

⚠️ **Atenção:** Essa ação não pode ser desfeita!

---

## 💡 Dicas e Boas Práticas

### ✅ Sempre Faça:
- Complete todos os campos obrigatórios (marcados com *)
- Upload de documentos em PDF para melhor qualidade
- Verifique os cálculos automáticos antes de salvar
- Registre afastamentos dentro de 24h do atestado
- Atualize o status ao funcionário retornar

### ❌ Evite:
- Deixar datas vazias
- Registrar valores negativos
- Salvar sem revisar os dados
- Excluir registros sem backup
- Cadastrar ferias duplicadas para mesmo período

---

## 📞 Campos Obrigatórios por Tipo

### Férias:
- ✓ Funcionário
- ✓ Período aquisitivo (data inicio e fim)
- ✓ Período de gozo (data inicio e fim)
- ✓ Dias de férias (1-30)
- ✓ Status

### Afastamento:
- ✓ Funcionário
- ✓ Tipo de afastamento
- ✓ Data de início
- ✓ Status

### Rescisão:
- ✓ Funcionário
- ✓ Tipo de rescisão
- ✓ Data de desligamento
- ✓ Status

---

## 🎨 Entendendo os Status

### Férias:
- 🔵 **AGENDADA** - Já foi registrada, aguardando o período
- 🟡 **EM_GOZO** - Funcionário está de férias agora
- 🟢 **CONCLUIDA** - Férias foram tiradas
- ⚫ **CANCELADA** - Férias foram canceladas

### Afastamentos:
- 🔴 **ATIVO** - Funcionário ainda está afastado
- 🟢 **ENCERRADO** - Funcionário retornou
- ⚫ **CANCELADO** - Afastamento foi cancelado

### Rescisões:
- 🟡 **EM_PROCESSO** - Rescisão está sendo processada
- 🟢 **CONCLUIDA** - Desligamento efetivado
- ⚫ **CANCELADA** - Rescisão foi cancelada

---

## 📱 Acesso Rápido (URLs)

| Página | URL |
|--------|-----|
| Dashboard RH | `/cadastros/rh/` |
| Listar Férias | `/cadastros/rh/ferias/` |
| Novo Afastamento | `/cadastros/rh/afastamentos/novo/` |
| Listar Rescisões | `/cadastros/rh/rescisoes/` |

---

## 🆘 Troubleshooting

**P: "Não consigo visualizar os funcionários no formulário"**
R: Verifique se os funcionários estão cadastrados e marcados como ativos.

**P: "O valor automaticamente não está calculando"**
R: Recarregue a página ou verifique se Javascript está habilitado.

**P: "Consigo ver dados de outros funcionários"**
R: Você deve estar vendo apenas da sua empresa (isolamento multi-tenant ativo).

**P: "Como fazer backup das férias registradas?"**
R: Exporte a página ou entre em contato com o administrador.

---

## 📈 Próximas Melhorias

- 📊 Relatórios PDF automáticos
- 📧 Notificações por email
- 📱 App mobile
- 🔔 Alertas de férias vencidas
- 📈 Dashboards com gráficos avançados

---

## 📚 Documentação Completa

Para mais detalhes técnicos, consulte:
- **SISTEMA_RH_COMPLETO.md** - Documentação técnica completa
- **HISTORICO_IMPLEMENTACAO_RH.md** - Histórico de implementação

---

**Versão:** 1.0  
**Data:** Fevereiro 2026  
**Django:** 5.2.7  
**Status:** ✅ Produção Pronto
