# Fase 1: Suporte a NF-e XML Import - Especificação Técnica Completa

**Data**: 31/03/2026  
**Status**: Pronto para iniciar  
**Estimativa**: 17.5 horas (~2 semanas com 1 dev full-time)  
**Feature Flag**: `COMPRAS_XML_IMPORT` (desligada por padrão)

---

## 📋 Índice

1. [Objetivo e Escopo](#objetivo-e-escopo)
2. [Análise de Código Existente](#análise-de-código-existente)
3. [Especificação XML (NF-e)](#especificação-xml-nf-e)
4. [Arquitetura da Solução](#arquitetura-da-solução)
5. [Mapeamento de Campos](#mapeamento-de-campos)
6. [Casos de Uso e Fluxos](#casos-de-uso-e-fluxos)
7. [Backlog Detalhado (10 Tarefas)](#backlog-detalhado-10-tarefas)
8. [Validações e Regras de Negócio](#validações-e-regras-de-negócio)
9. [Rollback e Fallback](#rollback-e-fallback)
10. [Critérios de Aceição](#critérios-de-aceição)

---

## Objetivo e Escopo

### Objetivo Principal
Implementar **parsing automático de NF-e em XML** para importar dados de recebimento diretamente para o fluxo Compras > Recebimento, minimizando entrada manual de dados.

### Escopo da Fase 1

| Incluído ✅ | Excluído ❌ |
|-----------|-----------|
| Parser XML genérico (NFe estrutura básica) | Validação com SEFAZ (Fase 2+) |
| Integração com Pedido de Compra (criar ou usar existente) | Automação de faturamento (Fase 3) |
| Detecção de duplicação por chave NF-e | Rastreabilidade de lote (Fase 2) |
| Validação de totais NF vs Pedido | Relatórios avançados (Fase 3+) |
| Fallback para entrada manual se XML inválido | Multi-fornecedor NFe |
| Testes unitários + integração | Integração com serviço SEFAZ |
| Feature flag para ativar/desativar | Recebimento parcial (futuro) |

---

## Análise de Código Existente

### 1. Model `RecebimentoCompra` (compras/models.py:1137)

```python
class RecebimentoCompra(models.Model):
    # Existentes
    empresa = models.ForeignKey('empresas.Empresa', ...)
    pedido = models.ForeignKey(PedidoCompra, ...)
    fornecedor = models.ForeignKey('cadastros.Fornecedor', ...)
    
    # NF-e data (JÁ IMPLEMENTADO)
    nota_fiscal = models.CharField('Número da NF-e', max_length=20)
    serie_nota = models.CharField('Série', max_length=5, default='1')
    chave_nfe = models.CharField('Chave NF-e', max_length=44, blank=True)
    data_emissao_nf = models.DateField('Data de Emissão NF')
    data_recebimento = models.DateField('Data do Recebimento', default=timezone.now)
    
    # Valores
    valor_total_nf = models.DecimalField('Valor Total da NF', ...)
    valor_frete = models.DecimalField('Frete', ...)
    valor_desconto = models.DecimalField('Desconto', ...)
    
    # Status
    status = models.CharField(choices=[...], default='PENDENTE')
    
    # Arquivo XML (JÁ EXISTE)
    arquivo_nfe = models.FileField('Arquivo XML da NF-e', upload_to='compras/nfe/%Y/%m/')
```

**Conclusão**: O model está **95% pronto**. Falta apenas:
- Campo para armazenar **chave primária de detecção de duplicata** (já existe `chave_nfe` - 44 dígitos)
- Opcionalmente: campo `parsed_from_xml` (bool) para rastrear origem

### 2. Estrutura de Diretórios Existente

```
compras/
├── models.py                  ✅ RecebimentoCompra definido
├── forms.py                   ⚠️ Precisa XMLNFeForm estendido
├── forms_xml_nf.py           ⚠️ Minimal (só XMLNFeUploadForm + campo)
├── views.py                   ⚠️ Precisa view de processamento XML
├── templates/
│   └── entrada_direta_nf.html ✅ Template base existe (upload + form)
└── migrations/                ✅ Campo arquivo_nfe já migrado
```

### 3. Dependências Disponíveis

- **xmltodict** (v1.0.3): Disponível em requirements.txt ✅
- **lxml** (parsing seguro): Necessário (adicionar)
- **io, xml.etree.ElementTree**: Builtin Python ✅

### 4. Fluxo de Entrada Direta Existente

```
Usuário → Upload XML → entrada_direta_nf.html 
→ POST /compras/entrada_direta/ 
→ Processamento manual de itens
→ Recebimento criado (SEM parsing automático)

MUDANÇA COM FASE 1:
Usuário → Upload XML → XMLNFeUploadForm
→ POST /compras/import_nfe_xml/
→ Parser automático extrai dados
→ Validação + mapping
→ Recebimento pré-preenchido OU vinculado a Pedido
→ Confirmação final com revisão manual (fallback)
```

---

## Especificação XML (NF-e)

### Estrutura Básica NF-e v4.0 (Relevante para Compras)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe">
  <NFe>
    <infNFe Id="NFe35080812662996000152550010000003411234567890" versao="4.00">
      <!-- IDENTIFICAÇÃO -->
      <ide>
        <cUF>35</cUF>
        <CNPJ>08.808.126.629-96</CNPJ>
        <assinaturaQRCode>...</assinaturaQRCode>
        <mod>55</mod>
        <serie>1</serie>
        <nNF>00000341</nNF>
        <dhEmi>2026-03-31T14:30:00-03:00</dhEmi>
        <tpDoc>00</tpDoc>
      </ide>
      
      <!-- EMITENTE (FORNECEDOR) -->
      <emit>
        <CNPJ>35.088.122.662-99</CNPJ>
        <xNome>Fornecedor ABC LTDA</xNome>
        <xFant>Fornecedor ABC</xFant>
        <enderEmit>
          <xLgr>Rua Principal</xLgr>
          <nro>123</nro>
          <xCpl>Apto 456</xCpl>
          <xBairro>Centro</xBairro>
          <cMun>3518402</cMun>
          <xMun>Araraquara</xMun>
          <UF>SP</UF>
          <CEP>14800000</CEP>
        </enderEmit>
      </emit>
      
      <!-- DESTINATÁRIO (SUA EMPRESA) -->
      <dest>
        <CNPJ>12.345.678.901-23</CNPJ>
        <xNome>SUA EMPRESA LTDA</xNome>
        <enderDest>
          <xLgr>Rua Destino</xLgr>
          <nro>999</nro>
          <xBairro>Bairro</xBairro>
          <cMun>3504008</cMun>
          <xMun>Guaiçara</xMun>
          <UF>SP</UF>
          <CEP>15120000</CEP>
        </enderDest>
      </dest>
      
      <!-- ITENS DA NF-e -->
      <det nItem="1">
        <prod>
          <cProd>12345</cProd>
          <cEAN>1234567890123</cEAN>
          <xProd>Produto ABC 50kg</xProd>
          <NCM>21069000</NCM>
          <CFOP>5102</CFOP>
          <uCom>UN</uCom>
          <qCom>100.0000</qCom>
          <vUnCom>125.50</vUnCom>
          <vProd>12550.00</vProd>
          <indTot>1</indTot>
          <vOutro20>0.00</vOutro20>
          <vDesc>0.00</vDesc>
        </prod>
        <imposto>
          <ICMS>
            <ICMS00>
              <orig>0</orig>
              <CST>00</CST>
              <modBC>0</modBC>
              <vBC>12550.00</vBC>
              <pICMS>7.00</pICMS>
              <vICMS>878.50</vICMS>
            </ICMS00>
          </ICMS>
          <IPI>
            <IPITrib>
              <CST>99</CST>
              <vBC>12550.00</vBC>
              <pIPI>0.00</pIPI>
              <vIPI>0.00</vIPI>
            </IPITrib>
          </IPI>
          <PIS>
            <PISAliq>
              <CST>01</CST>
              <vBC>12550.00</vBC>
              <pPIS>1.65</pPIS>
              <vPIS>207.08</vPIS>
            </PISAliq>
          </PIS>
          <COFINS>
            <COFINSAliq>
              <CST>01</CST>
              <vBC>12550.00</vBC>
              <pCOFINS>7.60</pCOFINS>
              <vCOFINS>953.80</vCOFINS>
            </COFINSAliq>
          </COFINS>
        </imposto>
      </det>
      
      <!-- TOTAIS -->
      <total>
        <ICMStot>
          <vBC>12550.00</vBC>
          <vICMS>878.50</vICMS>
          <vICMSDeson>0.00</vICMSDeson>
          <vBCST>0.00</vBCST>
          <vST>0.00</vST>
          <vProd>12550.00</vProd>
          <vFrete>100.00</vFrete>
          <vSeg>0.00</vSeg>
          <vDesc>0.00</vDesc>
          <vII>0.00</vII>
          <vIPI>0.00</vIPI>
          <vPIS>207.08</vPIS>
          <vCOFINS>953.80</vCOFINS>
          <vOutro>0.00</vOutro>
          <vNF>14689.38</vNF>
        </ICMStot>
      </total>
    </infNFe>
  </NFe>
  
  <!-- PROTOCOLO DE AUTORIZAÇÃO (Opcional) -->
  <protNFe versao="4.00">
    <infProt>
      <tpAmb>2</tpAmb>
      <verAplic>18.30</verAplic>
      <chNFe>35080808812662996000152550010000003418234567890</chNFe>
      <dhRecbto>2026-03-31T14:55:00-03:00</dhRecbto>
      <nProt>335260012345678</nProt>
      <digVal>loremipsum123456789digval</digVal>
      <cStat>100</cStat>
      <xMotivo>Autorizado o uso da NF-e</xMotivo>
    </infProt>
  </protNFe>
</nfeProc>
```

### Campos Críticos Extratos

| XML Path | Tipo | Mapeamento RecebimentoCompra | Obrigatório |
|----------|------|--------------------------|-----------|
| `//ide/nNF` | string | `nota_fiscal` | ✅ |
| `//ide/serie` | int | `serie_nota` | ⚠️ (default=1) |
| `//protNFe/infProt/chNFe` | string(44) | `chave_nfe` | ⚠️ |
| `//ide/dhEmi` | datetime | `data_emissao_nf` | ✅ |
| `//emit/CNPJ` | string | Buscar Fornecedor | ✅ |
| `//emit/xNome` | string | Log de validação | ⚠️ |
| `//total/ICMStot/vNF` | decimal | `valor_total_nf` | ✅ |
| `//total/ICMStot/vFrete` | decimal | `valor_frete` | ⚠️ |
| `//total/ICMStot/vDesc` | decimal | `valor_desconto` | ⚠️ |
| `//det/prod/xProd` | string | Buscar Produto |  ✅ |
| `//det/prod/qCom` | decimal | ItemRecebimento.quantidade | ✅ |
| `//det/prod/vUnCom` | decimal | ItemRecebimento.preco_unitario | ✅ |
| `//det/prod/NCM` | string(8) | NCM lookup | ⚠️ |
| `//det/prod/CFOP` | string | CFOP lookup | ⚠️ |

---

## Arquitetura da Solução

### Componentes Principais

```
compras/
├── parsers/
│   └── nfe_parser.py          [NOVO] Parser de XML NF-e
│
├── models.py
│   └── RecebimentoCompra      [EXISTENTE] + Campo parsed_from_xml
│
├── forms_xml_nf.py            [ESTENDER] Adicionar validações
│
├── views.py
│   └── import_nfe_xml_view()  [NOVO] View de processamento
│
├── utils/
│   └── nfe_validators.py      [NOVO] Validações de negócio
│
├── migrations/
│   └── XXXX_add_parsed_from_xml.py [NOVO] Se adicionar campo
│
└── templates/
    └── nfe/
        ├── import_nfe.html    [NOVO] Form de upload
        └── preview_nfe.html   [NOVO] Review antes de confirmar
```

### Fluxo de Parser

```
XML Upload
  ↓
[1] Validação Sintática (XML bem-formado?)
  ↓ ✅ Sim → [2] Parse
  ↓ ❌ Não → Erro: "XML inválido"
  ↓
[2] Extração de Dados (xmltodict)
  ↓
[3] Validação Semântica
    ├─ Chave NF-e duplicada?
    ├─ Fornecedor existe no BD?
    ├─ Produto(s) existe(m)?
    ├─ Total NF = soma itens?
    └─ Datas válidas?
  ↓ ✅ Tudo OK → [4] Mapeamento
  ↓ ❌ Erro não-critico → [5] Log + Continue com fallback
  ↓
[4] Mapeamento para modelo RecebimentoCompra
    ├─ Buscar Fornecedor por CNPJ
    ├─ Buscar/Create Produtos
    ├─ Preencher itens do recebimento
    └─ Calcular totais
  ↓
[5] Revisar dados (View preview)
    ├─ Usuário aprova
    ├─ Usuário faz correções manuais
    └─ Cria RecebimentoCompra ou Pedido+Recebimento
  ↓
[6] Vinculação automática com Pedido (se existir)
    ├─ Buscar por Fornecedor + data + valor similar
    └─ Sugerir match ao usuário
  ↓
✅ Recebimento criado (status=PENDENTE)
```

---

## Mapeamento de Campos

### Visão Geral

| Seção NF-e | Campo XML | Modelo RecebimentoCompra | Lógica |
|-----------|----------|-------------------------|--------|
| **Identificação** | nNF, serie | nota_fiscal, serie_nota | Direto |
| | chNFe | chave_nfe | Direto (44 dígitos) |
| | dhEmi | data_emissao_nf | Parse ISO8601 → DateField |
| **Emitente** | CNPJ | fornecedor (FK) | Buscar por CNPJ |
| | xNome | - | Log/Validação |
| **Totais** | vNF | valor_total_nf | Parse decimal |
| | vFrete | valor_frete | Parse decimal (default=0) |
| | vDesc | valor_desconto | Parse decimal (default=0) |
| **Itens** | xProd, qCom, vUnCom | ItemRecebimento itens | Loop + Create |
| | NCM, CFOP | NCM, CFOP FK | Buscar ou criar |

### Regra de Duplicação

```python
# Antes de criar RecebimentoCompra:
duplicata = RecebimentoCompra.objects.filter(
    chave_nfe=extracted_chave,
    empresa=request.user.empresa
).exists()

if duplicata:
    raise ValidationError("NF-e com chave duplicada encontrada")
```

### Busca de Fornecedor

```python
fornecedor = Fornecedor.objects.get(
    cnpj_cpf=normalizar(emit_cnpj),
    empresa=request.user.empresa
)
# Se não existe:
→ Erro com opção de "Criar novo fornecedor"
```

### Vinculação com Pedido

**Estratégia**: Busca "fuzzy" por critérios similares

```python
# Critérios para buscar Pedido compatível:
# 1. Mesmo fornecedor
# 2. Status = 'PENDENTE' ou 'PARCIAL'
# 3. Data do pedido ± N dias
# 4. Valor similar (±5%)

candidatos = PedidoCompra.objects.filter(
    fornecedor=fornecedor,
    status__in=['PENDENTE', 'PARCIAL'],
    data_pedido__gte=data_nf - timedelta(days=90),
    data_pedido__lte=data_nf + timedelta(days=1),
    empresa=empresa
)

# Filtrar por similaridade de valor
for pedido in candidatos:
    if abs(pedido.valor_total - nf_total) / nf_total < 0.05:
        sugestoes.append(pedido)

# UI apresenta sugestões ao usuário
```

---

## Casos de Uso e Fluxos

### Caso 1: NF-e com Pedido de Compra Existente

```
Usuário vai em: Compras → Importar NF-e XML
↓
Upload arquivo.xml
↓
Sistema extrai: Fornecedor ABC, 10 un Produto X, R$ 1.500
↓
Sistema busca Pedido de Compra existente com mesmo fornecedor
↓
Encontra: PedidoCompra #123 (Fornecedor ABC, R$ 1.500)
↓
UI exibe: "Encontramos 1 pedido compatível. Deseja vincular?"
↓
Usuário clica: "Vincular a Pedido #123"
↓
RecebimentoCompra criado vinculado a Pedido #123
Status: PENDENTE
↓
Fluxo normal: Conferir → Divergência (se houver) → Finalizar
```

### Caso 2: NF-e Entrada Direta (Sem Pedido)

```
Usuário vai em: Compras → Importar NF-e XML
↓
Upload arquivo.xml (Fornecedor PQR, 5 un Sementes, R$ 750)
↓
Sistema busca Pedido compatível
↓
Nenhum encontrado
↓
UI exibe: "Nenhum pedido encontrado. Criar entrada direta?"
↓
Usuário confirma
↓
RecebimentoCompra criado SEM pedido
Campo pedido = NULL
Status: PENDENTE
↓
Fluxo alternativo: Entrada direta com conferência manual
```

### Caso 3: NF-e com Divergência

```
Upload XML: 100 un @ R$ 10 = R$ 1.000
Pedido: 100 un @ R$ 12 = R$ 1.200
↓
Sistema detecta: Preço unitário diferente (10 vs 12)
↓
UI exibe warning: "⚠️ Preço maior que esperado"
↓
Usuário revisa:
  - Pode aceitar novo preço (ajusta Pedido ou cria divergência)
  - Pode cancelar importação
  - Pode editar manualmente antes de confirmar
↓
Após confirmação manual: RecebimentoCompra criado
Status: DIVERGENTE (se houver mismatch)
```

### Caso 4: XML Inválido (Fallback)

```
Upload arquivo.xml (corrupto, mal-formado)
↓
System tenta parser
↓
Erro XML: "Elemento esperado 'det' não encontrado"
↓
UI exibe: "❌ Não conseguimos extrair dados do XML"
↓
Opções oferecidas ao usuário:
  1. Fazer upload novo
  2. Entrar dados manualmente (Entrada Direta pura)
  3. Voltar para Compras (cancelar)
↓
Usuário escolhe opção 2
↓
Redireciona para entrada_direta_nf.html (já existe)
Usuário completa manualmente
```

---

## Backlog Detalhado (10 Tarefas)

### 1.1 Setup Branch e Estrutura

**Descrição**: Criar branch `feature/nfe-xml-import` e estrutura de diretórios  
**Prioridade**: Alta  
**Estimativa**: 0.5h  
**Dependências**: Nenhuma  
**Critérios de Aceição**:
- [ ] Branch criado e checkeado → `git checkout -b feature/nfe-xml-import`
- [ ] Pasta `compras/parsers/` criada com `__init__.py`
- [ ] Pasta `compras/utils/` criada com `__init__.py`
- [ ] Arquivo `compras/parsers/nfe_parser.py` criado (stub vazio)
- [ ] Arquivo `compras/utils/nfe_validators.py` criado (stub vazio)
- [ ] Django migrations zeradas (não deve haver migrations quebradas)

**Comandos**:
```bash
cd c:\erp_agricola_novo
git checkout -b feature/nfe-xml-import
mkdir -p compras/parsers compras/utils
touch compras/parsers/__init__.py compras/utils/__init__.py
touch compras/parsers/nfe_parser.py compras/utils/nfe_validators.py
manage.py check  # ✅ Deve passar
git add . && git commit -m "setup(fase1): Create branches and directory structure"
```

---

### 1.2 Implementar Parser de XML NF-e Básico

**Descrição**: Criar classe `NFEParser` que extrai dados brutos do XML  
**Prioridade**: Alta  
**Estimativa**: 3h  
**Dependências**: 1.1  
**Critérios de Aceição**:
- [ ] Classe `NFEParser` com método `parse(xml_path: str) → dict`
- [ ] Trata XML mal-formado (levanta `ParseError` customizado)
- [ ] Extrai campos: nNF, serie, chNFe, dhEmi, CNPJ emitente, vNF, vFrete, itens[].xProd/.qCom/.vUnCom
- [ ] Retorna dict estruturado com chaves normalizadas
- [ ] Usa `xmltodict` para parsing
- [ ] Tem testes unitários (parse XML válido + inválido)

**Exemplo de Output**:
```python
parser = NFEParser()
resultado = parser.parse('arquivo.xml')
# Retorna:
{
    'numero_nf': '123456',
    'serie': '1',
    'chave_nfe': '35080808812662996000152550010000003418234567890',
    'data_emissao': datetime(2026, 3, 31, 14, 30),
    'fornecedor': {
        'cnpj': '35088126629960',
        'nome': 'Fornecedor ABC LTDA'
    },
    'totais': {
        'valor_total': Decimal('14689.38'),
        'valor_frete': Decimal('100.00'),
        'valor_desconto': Decimal('0.00')
    },
    'itens': [
        {
            'produto_nome': 'Produto ABC 50kg',
            'quantidade': Decimal('100.0000'),
            'preco_unitario': Decimal('125.50'),
            'ncm': '21069000',
            'cfop': '5102'
        }
    ]
}
```

**Arquivo**: `compras/parsers/nfe_parser.py`  
**Testes**: `compras/tests/test_nfe_parser.py`

---

### 1.3 Validações de Negócio (Duplicação, Fornecedor, etc.)

**Descrição**: Implementar validações semânticas no arquivo `compras/utils/nfe_validators.py`  
**Prioridade**: Alta  
**Estimativa**: 2h  
**Dependências**: 1.2  
**Critérios de Aceição**:
- [ ] Função `validar_chave_duplicada(chave_nfe: str, empresa_id: int) → bool`
  - Retorna `True` se duplicata encontrada
  - Levanta `NFEValidationError` com mensagem descritiva
- [ ] Função `validar_fornecedor_existe(cnpj: str, empresa_id: int) → Fornecedor`
  - Busca fornecedor por CNPJ normalizado
  - Retorna objeto ou levanta `RequiredFornecedorError`
- [ ] Função `validar_produtos_existem(produtos_list: list, empresa_id: int) → list[Produto]`
  - Busca produtos por nome (fuzzy match se necessário)
  - Log de produtos não encontrados
  - Retorna lista ou levanta `MissingProductError`
- [ ] Função `validar_totais(nf_data: dict) → bool`
  - Verifica se soma de itens = vNF
  - Tolerância: ±R$ 0.01 por arredondamento
- [ ] Função `validar_datas(data_emissao, data_recebimento) → bool`
  - data_emissao ≤ data_recebimento
  - data_emissao ≥ data_recebimento - 180 dias (limite NBR)

**Testes**: `compras/tests/test_nfe_validators.py`

---

### 1.4 Modelo ItemRecebimento (se não existente) + Migração

**Descrição**: Garantir que `ItemRecebimento` existe e pode armazenar dados de NF-e  
**Prioridade**: Alta  
**Estimativa**: 1.5h  
**Dependências**: Nenhuma (verificar em 1.2)  
**Critérios de Aceição**:
- [ ] Model `ItemRecebimento` existe em `compras/models.py`
- [ ] Campos necessários:
  - `recebimento` (FK → RecebimentoCompra)
  - `produto` (FK → Produto)
  - `quantidade` (DecimalField)
  - `preco_unitario` (DecimalField)
  - `valor_total` (DecimalField, = quantidade × preco_unitario)
  - `ncm` (CharField, opcional)
  - `cfop` (CharField, opcional)
  - Todas com multi-tenant (empresa filter opcionalmente)
- [ ] Migração criada se necessário
- [ ] `manage.py migrate` executa sem erro

**Exemplo**:
```python
class ItemRecebimento(models.Model):
    recebimento = models.ForeignKey(RecebimentoCompra, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT)
    quantidade = models.DecimalField(max_digits=12, decimal_places=4)
    preco_unitario = models.DecimalField(max_digits=15, decimal_places=2)
    # Calculado via save()
    valor_total = property(lambda self: self.quantidade * self.preco_unitario)
```

---

### 1.5 Form Estendido com Validações (forms_xml_nf.py)

**Descrição**: Expandir `forms_xml_nf.py` com form completo  
**Prioridade**: Alta  
**Estimativa**: 1h  
**Dependências**: 1.2, 1.3  
**Critérios de Aceição**:
- [ ] Classe `XMLNFeUploadForm` estendida com:
  - Campo `xml_file` (FileField, aceita .xml)
  - Validação de tipo MIME ou extensão
  - Methodo `clean()` que tenta fazer parse (early validation)
- [ ] Classe `NFEPreviewForm` nova para confirmar dados antes de salvar:
  - Checkboxes/campos editáveis para: fornecedor, valor_total, data_recebimento
  - Opção de "Vincular a Pedido existente" (select widget)
- [ ] Ambas forms com multi-tenant (empresa do usuário)

**Arquivo**: `compras/forms_xml_nf.py`

---

### 1.6 View de Processamento / Preview (Import e Edição)

**Descrição**: Criar view POST que processa XML e exibe preview para edição  
**Prioridade**: Alta  
**Estimativa**: 2h  
**Dependências**: 1.2, 1.3, 1.5  
**Critérios de Aceição**:
- [ ] View `import_nfe_xml()` (POST /compras/import_nfe_xml/)
  - Recebe arquivo XML via form upload
  - Executa parser + validações
  - Se erro → redireciona para entrada manual (fallback)
  - Se OK → exibe página de preview
- [ ] Template `nfe/import_nfe.html` (GET + POST form)
  - Form de upload com instruções
  - Area para arrastar arquivo
- [ ] Template `nfe/preview_nfe.html` (POST form de confirmação)
  - Exibe dados extraídos em tabela
  - Checkboxes para editar campos críticos
  - Botão "Confirmar" que salva RecebimentoCompra
  - Botão "Editar" que volta para upload
  - Sugestões de Pedidos compatíveis (select)
- [ ] Integração com feature flag `COMPRAS_XML_IMPORT`
  - Se flag off → HTTP 404 ou message "Funcionalidade desativada"

**URL**: adicionar a `compras/urls.py`:
```python
path('import-nfe-xml/', views.import_nfe_xml, name='import_nfe_xml'),
path('preview-nfe/', views.preview_nfe, name='preview_nfe'),
path('confirm-nfe/', views.confirm_nfe, name='confirm_nfe'),
```

---

### 1.7 Salvar Recebimento a partir de Preview

**Descrição**: Implementar lógica final de criação de `RecebimentoCompra` + `ItemRecebimento`  
**Prioridade**: Alta  
**Estimativa**: 1.5h  
**Dependências**: 1.4, 1.6  
**Critérios de Aceição**:
- [ ] Função `criar_recebimento_from_nfe(nfe_data: dict, pedido: PedidoCompra = None, usuario: User) → RecebimentoCompra`
  - Extrai dados de nfe_data dict
  - Cria RecebimentoCompra com status='PENDENTE'
  - Cria ItemRecebimento para cada item da NF-e
  - Se pedido fornecido: vincula (pedido FK)
  - Se não: deixa pedido=NULL (entrada direta)
  - Gera numero único para RecebimentoCompra (sequence)
  - Log de quem criou (usuario)
  - Armazena arquivo XML em campo arquivo_nfe
- [ ] Transação atômica (rollback se falhar em qualquer item)
- [ ] Erro se chave já existe (verificação duplicata)
- [ ] Retorna RecebimentoCompra criado

**Arquivo**: `compras/views.py` (new function) + chamada em view `confirm_nfe`

---

### 1.8 Testes Unitários (Models, Parser, Validators)

**Descrição**: Cobertura de testes para parser, validators e criação de recebimento  
**Prioridade**: Alta  
**Estimativa**: 3h  
**Dependências**: 1.2, 1.3, 1.4, 1.7  
**Critérios de Aceição**:
- [ ] `test_nfe_parser.py`:
  - Parse XML válido → dados corretos extraídos
  - Parse XML inválido → levanta ParseError
  - Parse XML com campos faltando → levanta ParseError ou log warning
- [ ] `test_nfe_validators.py`:
  - Validação duplicata: true/false corretos
  - Validação fornecedor: encontra ou levanta erro
  - Validação produtos: encontra ou loga ausente
  - Validação totais: calcula corretamente
- [ ] `test_recebimento_from_nfe.py`:
  - Criar recebimento desde NF-e válida → objeto criado
  - Vincular a pedido → FK preenchida
  - Itens criados corretamente
  - Chave duplicada → rejection
- [ ] **Coverage**: mínimo 80% nas funções críticas
- [ ] Todos testes passam: `manage.py test compras.tests`

**Arquivos de Teste**:
```
compras/tests/
├── test_nfe_parser.py
├── test_nfe_validators.py
└── test_recebimento_nfe.py
```

---

### 1.9 Testes de Integração (Fluxo Completo Upload → Recebimento)

**Descrição**: Testes E2E: upload arquivo XML → recebimento criado  
**Prioridade**: Alta  
**Estimativa**: 2h  
**Dependências**: 1.6, 1.7, 1.8  
**Critérios de Aceição**:
- [ ] Teste: usuário autenticado faz POST com arquivo XML
  - Redirecta para preview
  - Página exibe dados corretos
  - Usuário clica "Confirmar"
  - RecebimentoCompra criado com status='PENDENTE'
  - ItemRecebimentos criados
- [ ] Teste: tentativa upload NF-e duplicada
  - Primeira upload: sucesso
  - Segunda upload mesmo arquivo: erro "Chave duplicada"
- [ ] Teste: fallback para entrada manual (XML inválido)
  - Arquivo corrompido → erro → opção "entrada manual"
  - Usuário escolhe → redireciona para entrada_direta_nf.html
- [ ] Teste: vinculação com Pedido existente
  - NF-e de fornecedor com Pedido pendente → sugestão exibida
  - Usuário aceita sugestão → pedido vinculado
  - Pedido muda status para 'RECEBIDO' (ou similar)

**Arquivo**: `compras/tests/test_nfe_integration.py`

---

### 1.10 Documentação SOP + Treinamento

**Descrição**: Criar guia de usuário e SOP técnico  
**Prioridade**: Media  
**Estimativa**: 1h  
**Dependências**: Todas (1.1-1.9)  
**Critérios de Aceição**:
- [ ] Documento `docs/fase1/GUIA_USUARIO_NF-E_IMPORT.md`:
  - Screenshots de cada tela
  - Passo a passo: upload → preview → confirmação
  - Explicação de cada campo
  - O que fazer em caso de erro/divergência
- [ ] Documento `docs/fase1/SOP_TECNICO_NF-E_PARSER.md`:
  - Estrutura de código
  - Como adicionar novos campos ao parser
  - Como customizar validações por empresa
  - Troubleshooting (logs, debug)
- [ ] Feature flag documentada em `.env.example`:
  - `FF_COMPRAS_XML_IMPORT=False` (default)
  - Instrução para ativar em staging/produção
- [ ] Comments em código crítico (parser, validators, views)

**Arquivos**:
```
docs/fase1/
├── GUIA_USUARIO_NF-E_IMPORT.md
├── SOP_TECNICO_NF-E_PARSER.md
└── CHANGELOG_FASE1.md
```

---

## Validações e Regras de Negócio

### R1. Validação de XML Bem-Formado
```
IF arquivo não é XML válido
  THEN levanta ParseError("XML inválido")
```

### R2. Detecção de Duplicação
```
IF existe RecebimentoCompra.chave_nfe == extracted_chave
  AND empresa_id == current_user.empresa_id
  THEN levanta DuplicateNFEError("NF-e com chave já importada")
```

### R3. Fornecedor Obrigatório
```
IF Fornecedor não encontrado por CNPJ
  THEN exibe opção: "Criar novo fornecedor" OU "Vincular a existente"
```

### R4. Validação de Totais
```
IF ABS(soma_itens - valor_total_nf) > 0.01
  THEN warning: "Total de itens diferente do valor NF"
  # Usuário decide ao confirmar
```

### R5. Vinculação com Pedido
```
IF existe Pedido com:
  - mesmo fornecedor
  - status = PENDENTE/PARCIAL
  - data_pedido ± 90 dias
  - valor_total similar (±5%)
  THEN sugerir vinculação ao usuário
```

### R6. Datas Válidas
```
IF data_emissao > hoje
  THEN error: "Data de emissão futura"
IF data_emissao < (hoje - 180 dias)
  THEN warning: "NF-e com mais de 6 meses"
```

### R7. Campos Obrigatórios
```
Recebimento:
  - empresa ✓ (from user)
  - fornecedor ✓ (from XML)
  - nota_fiscal ✓ (from XML)
  - data_emissao_nf ✓ (from XML)
  - valor_total_nf ✓ (from XML)
  - recebido_por ✓ (from user)
  - data_recebimento ✓ (today by default)
  
ItemRecebimento:
  - produto ✓ (from XML)
  - quantidade ✓ (from XML)
  - preco_unitario ✓ (from XML)
```

---

## Rollback e Fallback

### Teste de Rollback (Executado em Fase 0)

```bash
# 1. Desligar feature flag
FF_COMPRAS_XML_IMPORT=False

# 2. Fazer reload de settings Django
manage.py shell
>>> from django.conf import settings
>>> from core.feature_flags import is_feature_enabled
>>> is_feature_enabled('COMPRAS_XML_IMPORT')
False

# 3. Tentar acessar /compras/import-nfe-xml/
# Esperado: 404 ou message "Funcionalidade desativada"

# 4. Ligitar novamente
FF_COMPRAS_XML_IMPORT=True
# Esperado: funciona normalmente
```

### Procedimento de Rollback se Bug em Produção

```bash
# 1. Se houver bug crítico em importar NF-e após release:

# Passo 1: Desativar em produção (imediato)
export FF_COMPRAS_XML_IMPORT=False
systemctl restart gunicorn  # se usando Gunicorn

# Passo 2: Rótulos de recebimentos criados permanecem (não deletar)
# Continuar em "entrada direta manual" até fix

# Passo 3: Fix local em staging
git checkout -b bugfix/nfe-xml-import
# ... corrections ...
git commit -m "fix(fase1): Issue #XYZ - [descrição]"

# Passo 4: Re-enable após validação
FF_COMPRAS_XML_IMPORT=True
# Test em staging + produção com dados tail

# Passo 5: Documentar em CHANGELOG_FASE1.md
```

### Fallback Automático (Código)

```python
try:
    parsed_nfe = nfe_parser.parse(xml_file)
    validate_nfe(parsed_nfe)
    recebimento = create_recebimento_from_nfe(parsed_nfe)
except (ParseError, ValidationError) as e:
    logger.error(f"NFE parse failed: {e}")
    # FALLBACK
    return redirect('compras:entrada_direta_nf', {
        'error': 'Não conseguimos extrair dados do XML',
        'detail': str(e),
        'fornecedor': extracted_cnpj,  # pré-preenchido se disponível
    })
```

---

## Critérios de Aceição - Gate de Fase 1

| Item | Critério | Status |
|------|----------|--------|
| **Código** | Todas 10 tarefas concluídas ✅ | Abastecer |
| **Cobertura de Teste** | ≥ 80% nas novas funções | Abastecer |
| **Smoke Test** | Criar recebimento via XML em < 5s | Abastecer |
| **Documentação** | SOP técnico + Guia usuário | Abastecer |
| **Feature Flag** | Flag `COMPRAS_XML_IMPORT` funcionando | Abastecer |
| **Rollback** | Procedimento testado e documentado | Abastecer |
| **Regressão** | Smoke test Fase 0 ainda passa | Abastecer |
| **Aprovação** | Product + Tech Lead assinam gate | Abastecer |

---

## Roadmap Pós Fase 1

### Fase 2: Rastreabilidade + Validação SEFAZ
- [ ] Integração com SEFAZ para autorização NF-e
- [ ] Rastreabilidade completa (lote, validade, origem)
- [ ] Relatórios de recebimento

### Fase 3: Automação Avançada
- [ ] Faturamento automático após recebimento completo
- [ ] Renegociação de preços vs pedido
- [ ] Alertas de divergência por tolerância

---

## Anexos

### A. Exemplo XML Mínimo (para testes)

[Ver Seção "Especificação XML" acima]

### B. Dependências Necessárias

```txt
# requirements.txt (adicionar se não existente)
xmltodict==1.0.3       # ✅ Já existe
lxml==5.0.0           # ⚠️ Adicionar para parsing seguro
```

### C. Variáveis de Ambiente

```bash
# .env
FF_COMPRAS_XML_IMPORT=False         # Default: desligado
NFE_PARSER_TOLERANCE=0.01            # Tolerância cálculo (R$)
NFE_PEDIDO_MATCH_DAYS=90             # Dias para buscar pedidos
NFE_PEDIDO_PRICE_TOLERANCE=0.05      # 5% tolerância preço
```

---

**Plan Versionado**: v1.0 - 31/03/2026  
**Próximo Review**: Após conclusão da Tarefa 1.5  
**Owner**: Dev Team  
**Aprovado por**: [Aguardando assinatura]
