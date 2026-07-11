# Checklist Homologação - Fase 1: Import XML NF-e

**Data**: 02/04/2026  
**Ambiente**: Homologação (staging)  
**Feature Flag**: `FF_COMPRAS_XML_IMPORT=True` (já ativada)  
**Responsável**: [QA/Tester]

---

## 📌 Pré-Requisitos

### Ambiente Preparado?

- [ ] **Flag ativada**: `.env` contém `FF_COMPRAS_XML_IMPORT=True`
  ```bash
  # Verificar
  grep "FF_COMPRAS_XML_IMPORT" .env
  # Esperado: FF_COMPRAS_XML_IMPORT=True
  ```

- [ ] **Servidor rodando**: Homologação está em pé
  ```bash
  # Ou acesse e veja se login funciona
  curl http://localhost:8000/admin/
  ```

- [ ] **Dados de teste disponíveis**:
  - [ ] Marca Empresa teste criada (para multi-tenant)
  - [ ] Fornecedor(es) com CNPJ válido cadastrado(s)
  - [ ] Produtos cadastrados com unidades, categorias, NCM
  - [ ] Ao menos 1 PedidoCompra aberto (status=PENDENTE ou PARCIAL)

- [ ] **Arquivo XML NF-e v4.0**:
  - [ ] Arquivo sample valid: `docs/fase1/nfe_sample.xml` (ou similar)
  - [ ] Arquivo invalid: `docs/fase1/nfe_invalid.xml` (para teste erro)

---

## 🧪 Testes de Funcionalidade

### Teste 1: Feature Flag Visível no Formulário

**Cenário**: Usuário acessa a página de entrada direta sem XML

**Passos**:
1. Abra: `http://localhost:8000/compras/entrada-direta-nf/`
2. Faça login como admin/usuário com permissão

**Validação**:
- [ ] Página carrega sem erro (200 OK)
- [ ] Existe botão/seção de upload de XML:
  - [ ] Label: "Importar dados de NF-e (XML)"
  - [ ] Ou: "Upload de Arquivo XML"
  - [ ] Ou: Input com accept=".xml"
- [ ] Se flag OFF: Elemento XML deve estar OCULTO

**Result**: ☐ PASS / ☐ FAIL

**Notas**:
```
[espaço para anotações]
```

---

### Teste 2: Upload de XML Válido → Extract

**Cenário**: NF-e válida, fornecedor existente no BD, sem duplicação

**Arquivo de Teste**: `nfe_valid_simp.xml`
```xml
<?xml version="1.0" encoding="UTF-8"?>
<nfe>
  <infNFe>
    <ide>
      <cUF>35</cUF>
      <natOp>COMPRA DE MATERIA PRIMA PARA PROCESSAMENTO</natOp>
      <mod>55</mod>
      <serie>1</serie>
      <nNF>123456</nNF>
      <dhEmi>2026-04-02T10:30:00</dhEmi>
    </ide>
    <emit>
      <CNPJ>35088122662099</CNPJ>
    </emit>
    <dest>
      <CNPJ>[CNPJ_EMPRESA_TEST]</CNPJ>
    </dest>
    <total>
      <ICMSTot>
        <vNF>1500.00</vNF>
      </ICMSTot>
    </total>
    <det nItem="1">
      <prod>
        <code>001</code>
        <xProd>Óleo de Motor 5L</xProd>
        <NCM>27101241</NCM>
        <qCom>100</qCom>
        <vUnCom>15.00</vUnCom>
      </prod>
    </det>
  </infNFe>
</nfe>
```

**Passos**:
1. Abra: `http://localhost:8000/compras/entrada-direta-nf/`
2. Selecione o arquivo XML válido
3. Clique em "Extrair XML" ou "Importar"
4. **Aguarde response** (pode levar 2-5s)

**Validação** (esperado):
- [ ] Página **não redireciona** para erro 500
- [ ] **Mensagem de sucesso** exibida: "XML extraído com sucesso"
- [ ] **Preview formulário** aparece com campos preenchidos:
  - [ ] Número NF: `123456`
  - [ ] Série: `1`
  - [ ] Fornecedor: Detectado por CNPJ
  - [ ] Data Emissão: `02/04/2026`
  - [ ] Valor Total: `1500.00`
  - [ ] Item 1: `Óleo de Motor 5L | 100 un | R$ 15.00`
- [ ] **Botão Salvar** disponível para confirmar
- [ ] **Botão Cancelar** ou Voltar disponível

**Result**: ☐ PASS / ☐ FAIL

**Notas**:
```
[espaço para anotações]
```

---

### Teste 3: Upload de XML → Duplicação Detectada

**Cenário**: Mesmo arquivo XML do Teste 2 uploadado NOVAMENTE

**Passos**:
1. Volte para upload (clique Cancelar do preview anterior)
2. **Faça upload do MESMO arquivo** (123456/Serie1)
3. Clique em "Extrair XML"

**Validação** (esperado):
- [ ] **Erro exibido**: "Esta NF-e já foi importada anteriormente" ou similar
- [ ] **Campo bloqueado**: Número + Série marcados como duplicado
- [ ] **Usuário orientado**: "Use Nº diferente ou revise registros"
- [ ] **Sem exception 500**: Tratamento gracioso

**Result**: ☐ PASS / ☐ FAIL

**Notas**:
```
[espaço para anotações]
```

---

### Teste 4: Upload de XML → Fornecedor NÃO encontrado

**Cenário**: CNPJ do XML não existe no BD

**Arquivo de Teste**: `nfe_fornecedor_novo.xml` (CNPJ=99.999.999.000-00)

**Passos**:
1. Abra formulário de upload
2. Faça upload de arquivo com CNPJ inexistente
3. Clique em "Extrair XML"

**Validação** (esperado):
- [ ] **Aviso exibido**: "Fornecedor não identificado pelo CNPJ"
- [ ] **Preview ainda aparece** com dados extraídos (fallback)
- [ ] **Campo "Fornecedor"** em BRANCO esperando seleção manual
- [ ] **Usuário pode selecionar** fornecedor existente do dropdown
- [ ] **Confirmar salva com fornecedor correto**

**Result**: ☐ PASS / ☐ FAIL

**Notas**:
```
[espaço para anotações]
```

---

### Teste 5: Upload de XML Inválido

**Cenário**: Arquivo corrupto ou bad XML

**Arquivo de Teste**: `nfe_invalid.xml` (tags mal formadas)

**Passos**:
1. Crie arquivo com XML inválido:
   ```xml
   <?xml version="1.0"?>
   <nfe>
     <infNFe>
       <ide>
         <!-- Tag não fechada
         <mod>55
       </ide>
     </infNFe>
   </nfe>
   ```
2. Faça upload
3. Clique em "Extrair XML"

**Validação** (esperado):
- [ ] **Erro amigável**: "Arquivo XML inválido ou corrompido"
- [ ] **SEM exception 500** em logs
- [ ] **Fallback para manual**: "Você pode preencher manualmente abaixo"
- [ ] **Form de entrada manual** permanece viável

**Result**: ☐ PASS / ☐ FAIL

**Notas**:
```
[espaço para anotações]
```

---

### Teste 6: Upload de PNG/JPG (Tipo Inválido)

**Cenário**: Usuário tenta upload de arquivo não-XML

**Passos**:
1. Use arquivo: `screenshot.png` ou `documento.pdf`
2. Selecione para upload
3. Clique em "Extrair XML"

**Validação** (esperado):
- [ ] **Validação de tipo**: Arquivo rejeitado ANTES do processamento
- [ ] **Mensagem clara**: "Por favor, envie um arquivo XML (.xml)"
- [ ] **Input ainda vazio**: Pronto para novo upload

**Result**: ☐ PASS / ☐ FAIL

**Notas**:
```
[espaço para anotações]
```

---

### Teste 7: Cancelar Preview → Voltar ao Upload

**Cenário**: Usuário extrai dados mas cancela antes de salvar

**Passos**:
1. Siga Teste 2 até o preview
2. Clique em **Cancelar** ou **Voltar**
3. Tente novo upload

**Validação** (esperado):
- [ ] **Retorna para upload**: Formulário vazio, pronto para novo XML
- [ ] **Session cache limpa**: Dados anteriores não persistem
- [ ] **Novo upload funciona normalmente**

**Result**: ☐ PASS / ☐ FAIL

**Notas**:
```
[espaço para anotações]
```

---

### Teste 8: Confirmar Preview → Salva RecebimentoCompra

**Cenário**: Usuário confirma preview e salva recebimento

**Passos**:
1. Siga Teste 2 até o preview (com dados corretos)
2. Revise os dados
3. Clique em **Salvar** ou **Confirmar**

**Validação** (esperado):
- [ ] **Redireção para sucesso**: Página de confirmação OU lista de recebimentos
- [ ] **Mensagem**: "RecebimentoCompra #XYZ criado com sucesso"
- [ ] **Banco de dados**: Novo `RecebimentoCompra` existe com:
  - [ ] `nota_fiscal=123456`
  - [ ] `serie_nota=1`
  - [ ] `chave_nfe` preenchida (se estava no XML)
  - [ ] `status='PENDENTE'` (novo recebimento)
  - [ ] `empresa` = empresa do usuário (multi-tenant)
- [ ] **Itens vinculados**: `ItemRecebimento` criados com quantidade e preço corretos
- [ ] **Arquivo anexado** (se implementado): XML salvo como arquivo

**Result**: ☐ PASS / ☐ FAIL

**Notas**:
```
[espaço para anotações]
```

---

### Teste 9: Listar Recebimentos → Mostrar Importados

**Cenário**: Após salvar, verificar se aparece na lista

**Passos**:
1. Vá para: `http://localhost:8000/compras/recebimento-compra/`
2. Procure pelo recebimento criado no Teste 8

**Validação** (esperado):
- [ ] **Recebimento visível** na lista com:
  - [ ] Número NF correto
  - [ ] Fornecedor correto
  - [ ] Status = PENDENTE
  - [ ] Data emissão correta
- [ ] **Identificação clara**: Deve ter indicação que foi importado de XML (ícone, label, etc)
- [ ] **Ação Editar funciona**: Pode abrir detalhes

**Result**: ☐ PASS / ☐ FAIL

**Notas**:
```
[espaço para anotações]
```

---

### Teste 10: MultiTenant - Empresa Isolamento

**Cenário**: User de Empresa A tenta ver recebimento de Empresa B

**Passos**:
1. Crie 2 usuários em empresas diferentes
2. User A: Faz login, faz upload, salva recebimento (Empresa A)
3. User B: Faz login em outra empresa
4. User B: Acessa lista de recebimentos

**Validação** (esperado):
- [ ] **User B NÃO vê** recebimento de User A
- [ ] **Isolamento mantido**: Multi-tenant funcionando
- [ ] **User B pode fazer upload próprio**: Sem conflito

**Result**: ☐ PASS / ☐ FAIL

**Notas**:
```
[espaço para anotações]
```

---

## 🔄 Testes de Integração Avançada

### Teste 11: XML com PedidoCompra Existente → Vinculação

**Cenário**: NF-e corresponde a PedidoCompra aberto

**Pré-condição**:
- [ ] PedidoCompra #999 criado:
  - Fornecedor: ABC Ltda (CNPJ=35.088.122.662-99)
  - Status: PENDENTE
  - Valor: R$ 1.500,00
  - Item: Óleo de Motor, 100 un

**XML de Teste**:
```xml
<nfe>
  <emit><CNPJ>35088122662099</CNPJ></emit>
  <infNFe><ide><nNF>123456</nNF>...</ide></infNFe>
  <total><ICMSTot><vNF>1500.00</vNF></ICMSTot></total>
  <det nItem="1">
    <prod><xProd>Óleo de Motor</xProd><qCom>100</qCom><vUnCom>15.00</vUnCom></prod>
  </det>
</nfe>
```

**Passos**:
1. Faça upload do XML
2. Sistema extrai e analisa
3. Preview deve **sugerir o PedidoCompra #999**

**Validação** (esperado):
- [ ] **Sugestão exibida**: "Pedido de Compra #999 encontrado (match automático)"
- [ ] **Campo Pedido** pré-preenchido
- [ ] **Usuário pode aceitar OU mudar manualmente**
- [ ] **Após salvar**: `RecebimentoCompra.pedido = PedidoCompra #999`

**Result**: ☐ PASS / ☐ FAIL

**Notas**:
```
[espaço para anotações]
```

---

### Teste 12: Divergência de Preço → Aviso

**Cenário**: NF-e com preço diferente do PedidoCompra

**NF-e**: 100 un @ R$ 12.00 = R$ 1.200,00  
**Pedido**: 100 un @ R$ 15.00 = R$ 1.500,00

**Passos**:
1. Faça upload de XML com preço divergente
2. Sistema encontra Pedido compatível
3. Preview exibido

**Validação** (esperado):
- [ ] **Aviso exibido**: ⚠️ "Preço divergente: NF @ R$ 12.00 vs Pedido @ R$ 15.00"
- [ ] **Campo destacado** em amarelo ou vermelho
- [ ] **Usuário esclarecido** do motivo (cor, mensagem)
- [ ] **Usuário pode salvar mesmo assim** (acetta divergência consciente)
- [ ] **Log criado** para auditoria

**Result**: ☐ PASS / ☐ FAIL

**Notas**:
```
[espaço para anotações]
```

---

### Teste 13: Performance - Arquivo Grande

**Cenário**: NF-e com muitos itens (100+)

**Arquivo**: `nfe_bulk_1000itens.xml`

**Passos**:
1. Faça upload de arquivo grande
2. Meça tempo de resposta
3. Monitore uso de CPU/memória

**Validação** (esperado):
- [ ] **Tempo < 10 segundos**: Resposta rápida mesmo com muitos itens
- [ ] **Sem timeout 504**: Gateway não timeout
- [ ] **Memória estável**: Sem memory leak visível

**Result**: ☐ PASS / ☐ FAIL

**Notas**:
```
Tempo medido: _____ segundos
CPU: _____ %
Memoria: _____ MB
```

---

### Teste 14: Logging & Auditoria

**Cenário**: Verificar se operações são auditadas

**Passos**:
1. Faça upload, extração, confirmação
2. Acesse logs da aplicação
3. Procure por entradas relacionadas

**Validação** (esperado):
- [ ] **Log entry para upload**: Usuario, timestamp, arquivo, resultado
- [ ] **Log entry para validação**: Duplicação check, fornecedor match
- [ ] **Log entry para criação**: RecebimentoCompra criado, ID, valores
- [ ] **Nenhuma informação sensível**: Senha, token não logged

**Result**: ☐ PASS / ☐ FAIL

**Notas**:
```
[espaço para anotações]
```

---

## 🔒 Testes de Segurança

### Teste 15: XSS - XML com Script Tag

**Cenário**: XML malformado com script injection

**XML malicioso**:
```xml
<nfe>
  <prod>
    <xProd><![CDATA[<script>alert('XSS')</script>Produto Teste]]></xProd>
  </prod>
</nfe>
```

**Passos**:
1. Faça upload
2. Observe se script é renderizado

**Validação** (esperado):
- [ ] **Script NÃO executado**: Text escaped corretamente
- [ ] **Conteúdo renderizado como string**: `<script>alert('XSS')</script>` shows como texto
- [ ] **Browser consola**: Nenhum erro de segurança

**Result**: ☐ PASS / ☐ FAIL

**Notas**:
```
[espaço para anotações]
```

---

### Teste 16: CSRF Protection

**Cenário**: Form submit sem CSRF token

**Passos**:
1. Intercepte request (via burp/dev-tools)
2. Remova `csrf_token` do form
3. Tente submit

**Validação** (esperado):
- [ ] **Erro 403 Forbidden**: Request bloqueado
- [ ] **Mensagem clara**: "CSRF token inválido ou ausente"

**Result**: ☐ PASS / ☐ FAIL

**Notas**:
```
[espaço para anotações]
```

---

### Teste 17: Permission Check

**Cenário**: Usuário sem permissão tenta acessar

**Passos**:
1. Crie usuário SEM permissão em compras
2. Tente acessar: `/compras/entrada-direta-nf/`

**Validação** (esperado):
- [ ] **Acesso negado**: Erro 403 OU redirecionado para login
- [ ] **Mensagem clara**: "Você não tem permissão para acessar esta página"

**Result**: ☐ PASS / ☐ FAIL

**Notas**:
```
[espaço para anotações]
```

---

## 📊 Resumo de Resultados

### Testes Funcionais
| # | Teste | Result | Prioridade |
|---|-------|--------|-----------|
| 1 | Feature Flag Visível | ☐ | ALTA |
| 2 | Upload XML Válido | ☐ | ALTA |
| 3 | Duplicação Detectada | ☐ | ALTA |
| 4 | Fornecedor Não Encontrado | ☐ | MÉDIA |
| 5 | XML Inválido | ☐ | ALTA |
| 6 | Upload Tipo Inválido | ☐ | MÉDIA |
| 7 | Cancelar Preview | ☐ | BAIXA |
| 8 | Salvar Recebimento | ☐ | ALTA |
| 9 | Listar Recebimentos | ☐ | ALTA |
| 10 | MultiTenant Isolamento | ☐ | ALTA |

### Testes Integração
| # | Teste | Result | Prioridade |
|---|-------|--------|-----------|
| 11 | PedidoCompra Vinculação | ☐ | ALTA |
| 12 | Divergência Preço | ☐ | MÉDIA |
| 13 | Performance Arquivo Grande | ☐ | MÉDIA |
| 14 | Logging & Auditoria | ☐ | MÉDIA |

### Testes Segurança
| # | Teste | Result | Prioridade |
|---|-------|--------|-----------|
| 15 | XSS Protection | ☐ | ALTA |
| 16 | CSRF Protection | ☐ | ALTA |
| 17 | Permission Check | ☐ | ALTA |

---

## ✅ Gate de Homologação

### Critérios de Aceição

- [ ] **Testes ALTA**: 100% passando (testes 1, 2, 3, 5, 8, 9, 10, 11, 15, 16, 17)
- [ ] **Testes MÉDIA/BAIXA**: 80%+ passando (testes 4, 6, 7, 12, 13, 14)
- [ ] **Nenhum erro 500**: Todos os flows tratam erros com mensagens amigáveis
- [ ] **Performance OK**: Tempo < 10s inclusive arquivos grandes
- [ ] **Logs limpos**: Nenhuma informação sensível exposta
- [ ] **Multi-tenant**: Isolamento total entre empresas

### Sign-Off

- [ ] **QA**: Homologação concluída ✅
- [ ] **Tech Lead**: Code review passou ✅
- [ ] **Product**: Aceitação do cliente ✅
- [ ] **DevOps**: Ready for production ✅

**Assinado por**:  
- QA: _________________ Data: _______
- Tech Lead: __________ Data: _______
- Product: ___________ Data: _______

---

## 🔗 Referências

- Code: `compras/views.py#L2044-L2233` (entrada_direta_nf)
- Parser: `compras/parsers/nfe_parser.py`
- Tests: `compras/tests.py#L155-L270` (EntradaDiretaNFViewTestCase)
- Docs: `docs/fase1/ESPECIFICACAO_FASE1_NF-E_XML.md`

