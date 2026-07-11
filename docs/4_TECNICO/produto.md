# ESPECIFICAÇÃO TÉCNICA COMPLETA
## CADASTRO DE PRODUTOS E INSUMOS COM TRIBUTAÇÃO AUTOMATIZADA

**Projeto**: ERP Agrícola Salutaris  
**Versão**: 2.0  
**Data**: Janeiro 2026  
**Regime Tributário**: Lucro Real (Base)  
**Destinatário**: Equipe de Desenvolvimento

---

## 📑 SUMÁRIO

1. [Visão Geral e Objetivos](#1-visão-geral-e-objetivos)
2. [Modelo de Dados Completo](#2-modelo-de-dados-completo)
3. [Regras de Negócio](#3-regras-de-negócio)
4. [Interface do Usuário](#4-interface-do-usuário)
5. [Perfis de Tributação Automatizados](#5-perfis-de-tributação-automatizados)
6. [Integração com Tabela NCM](#6-integração-com-tabela-ncm)
7. [Dados Específicos de Insumos Agrícolas](#7-dados-específicos-de-insumos-agrícolas)
11. [Matriz Completa CFOP x Tributação](#11-matriz-completa-cfop-x-tributação)


---

## 1. VISÃO GERAL E OBJETIVOS

### 1.1 Objetivo do Módulo

Criar um sistema de cadastro único de produtos/insumos que:
- **Automatize 100% da tributação** baseada em CFOP
- **Elimine erros fiscais** através de validações automáticas
- **Reduza tempo de cadastro** de 20 minutos para 2 minutos
- **Garanta compliance fiscal** permanente
- **Simplifique operação** para usuários sem conhecimento fiscal profundo

### 1.2 Escopo

**Incluído:**
- Cadastro completo de produtos agrícolas, insumos, embalagens e materiais
- Tributação automatizada para ICMS, IPI, PIS e COFINS
- Gestão de estoque, custos e preços
- Controles específicos para defensivos e fertilizantes (MAPA)
- Integração com tabela NCM oficial (TIPI)
- Perfis fiscais por CFOP e cenário


**Excluído:**
- Emissão de documentos fiscais (NF-e, CT-e) - módulo separado
- Controle de movimentação de estoque - módulo separado
- Precificação dinâmica - módulo separado

### 1.3 Fluxo Resumido

```
┌─────────────────────────────────────────────────────────────┐
│ FLUXO DE CADASTRO E USO                                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ 1. CADASTRO                                                 │
│    ├─ Usuário preenche dados básicos                       │
│    ├─ Informa NCM (busca inteligente)                      │
│    ├─ Define tipo (Insumo/Uso Consumo/etc)                 │
│    └─               │
│                                   │
│ 4. MANUTENÇÃO                                               │
│    ├─ Sistema alerta mudanças legislação                   │
│    ├─ Atualiza perfis automaticamente                      │
│    └─ Mantém histórico de alterações                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. MODELO DE DADOS COMPLETO

### 2.1 Diagrama Entidade-Relacionamento

```
┌─────────────────┐
│    empresas     │
└────────┬────────┘
         │
         │ 1:N
         │
┌────────▼────────┐       ┌──────────────────┐
│    produtos     │◄──────┤   categorias     │
└────────┬────────┘  N:1  └──────────────────┘
         │
         ├─────┬──────────────────────────────┬─────────────┐
         │ 1:N │ 1:N                      1:N │             │ 1:1
         │     │                              │             │
┌────────▼─────▼──────┐  ┌───────────────────▼─────┐  ┌────▼─────────────────┐
│produtos_perfis_      │  │produtos_culturas_       │  │produtos_insumos_     │
│       fiscais        │  │     registradas          │  │    agricolas         │
└──────────────────────┘  └─────────────────────────┘  └──────────────────────┘
         │
         │ N:1
         │
┌────────▼─────────┐
│    ncm_tipi      │
└──────────────────┘
```

### 2.2 Tabela: `produtos` (Principal)

```sql
-- =====================================================
-- TABELA PRINCIPAL: PRODUTOS
-- Armazena todos os produtos, insumos e materiais
-- =====================================================

CREATE TABLE produtos (
    -- ============= IDENTIFICAÇÃO =============
    id BIGSERIAL PRIMARY KEY,
    codigo_interno VARCHAR(50) UNIQUE NOT NULL,
    codigo_barras VARCHAR(20),
    codigo_sku VARCHAR(50),
    codigo_fornecedor VARCHAR(50),
    
    -- ============= DESCRIÇÕES =============
    descricao_completa VARCHAR(500) NOT NULL,
    descricao_resumida VARCHAR(200),
    descricao_nf VARCHAR(120) NOT NULL, -- Limite SEFAZ NF-e
    observacoes TEXT,
    
    -- ============= CLASSIFICAÇÃO =============
    tipo_produto VARCHAR(50) NOT NULL,
    /* Valores permitidos:
       - MATERIA_PRIMA: Produto agrícola bruto
       - INSUMO_FERTILIZANTE: Fertilizante mineral/orgânico
       - INSUMO_DEFENSIVO: Defensivo agrícola
       - INSUMO_SEMENTE: Semente ou muda
       - INSUMO_OUTRO: Outros insumos agrícolas
       - EMBALAGEM: Material de embalagem
       - PRODUTO_ACABADO: Produto final para venda
       - USO_CONSUMO: Material que não integra produto
       - ATIVO_IMOBILIZADO: Bem do ativo
       - REVENDA: Produto para revenda sem transformação
    */
    
    categoria_id BIGINT REFERENCES categorias(id),
    subcategoria_id BIGINT REFERENCES subcategorias(id),
    grupo_id BIGINT REFERENCES grupos(id),
    familia_id BIGINT REFERENCES familias(id),
    
    -- ============= UNIDADES DE MEDIDA =============
    unidade_compra VARCHAR(6) NOT NULL,
    unidade_venda VARCHAR(6) NOT NULL,
    unidade_estoque VARCHAR(6) NOT NULL,
    /* Unidades permitidas (conforme SEFAZ):
       KG, L, UN, CX, SC, FD, T, M, M2, M3, DZ, PC, etc.
    */
    
    fator_conversao_compra DECIMAL(10,4) DEFAULT 1.0000,
    fator_conversao_venda DECIMAL(10,4) DEFAULT 1.0000,
    /* Exemplo: 
       - 1 SC (compra) = 50 KG (estoque) → fator = 50.0000
       - 1 CX (venda) = 10 UN (estoque) → fator = 10.0000
    */
    
    peso_bruto DECIMAL(10,4),
    peso_liquido DECIMAL(10,4),
    volume_m3 DECIMAL(10,6),
    
    -- ============= CLASSIFICAÇÃO FISCAL =============
    ncm VARCHAR(10) NOT NULL,
    /* Formato: 0000.00.00 (8 dígitos obrigatórios)
       Deve existir na tabela ncm_tipi
    */
    
    cest VARCHAR(9),
    /* Formato: 00.000.00 (7 dígitos)
       Obrigatório quando produto sujeito a ST
    */
    
    origem_mercadoria CHAR(1) NOT NULL DEFAULT '0',
    /* Valores:
       0 = Nacional, exceto as indicadas nos códigos 3 a 5
       1 = Estrangeira - Importação direta
       2 = Estrangeira - Adquirida no mercado interno
       3 = Nacional, mercadoria com Conteúdo de Importação > 40%
       4 = Nacional, produção com processos produtivos básicos
       5 = Nacional, mercadoria com Conteúdo de Importação ≤ 40%
       6 = Estrangeira - Importação direta, sem similar nacional
       7 = Estrangeira - Adquirida mercado interno, sem similar
       8 = Nacional, mercadoria com Conteúdo de Importação > 70%
    */
    
    beneficio_fiscal VARCHAR(100),
    codigo_beneficio VARCHAR(20),
    
    tipo_item CHAR(2) NOT NULL DEFAULT '01',
    /* Conforme tabela SPED:
       00 = Mercadoria para Revenda
       01 = Matéria-Prima
       02 = Embalagem
       03 = Produto em Processo
       04 = Produto Acabado
       05 = Subproduto
       06 = Produto Intermediário
       07 = Material de Uso e Consumo
       08 = Ativo Imobilizado
       09 = Serviços
       10 = Outros insumos
       99 = Outras
    */
    
    -- ============= CONTROLES DE ESTOQUE =============
    movimenta_estoque BOOLEAN DEFAULT TRUE,
    controla_lote BOOLEAN DEFAULT FALSE,
    controla_validade BOOLEAN DEFAULT FALSE,
    controla_numero_serie BOOLEAN DEFAULT FALSE,
    compoe_bom BOOLEAN DEFAULT FALSE, -- Bill of Materials
    produto_perecivel BOOLEAN DEFAULT FALSE,
    
    -- ============= PARÂMETROS DE ESTOQUE =============
    estoque_minimo DECIMAL(15,4) DEFAULT 0,
    estoque_maximo DECIMAL(15,4) DEFAULT 0,
    ponto_pedido DECIMAL(15,4) DEFAULT 0,
    estoque_seguranca DECIMAL(15,4) DEFAULT 0,
    
    prazo_validade_dias INTEGER,
    alerta_vencimento_dias INTEGER DEFAULT 30,
    
    lead_time_compra_dias INTEGER DEFAULT 0,
    /* Tempo médio entre pedido e recebimento */
    
    lote_economico DECIMAL(15,4),
    /* Quantidade ideal para minimizar custos */
    
    -- ============= ARMAZENAMENTO =============
    temp_min_celsius DECIMAL(5,2),
    temp_max_celsius DECIMAL(5,2),
    umidade_min_percent DECIMAL(5,2),
    umidade_max_percent DECIMAL(5,2),
    proteger_luz BOOLEAN DEFAULT FALSE,
    armazenamento_segregado BOOLEAN DEFAULT FALSE,
    area_ventilada BOOLEAN DEFAULT FALSE,
    
    armazem_padrao_id BIGINT REFERENCES armazens(id),
    endereco_padrao VARCHAR(50),
    /* Formato: ARM01-C02-P05-N01 
       (Armazém-Corredor-Prateleira-Nível)
    */
    
    -- ============= CUSTOS =============
    metodo_custeio VARCHAR(20) DEFAULT 'MEDIO',
    /* Valores: MEDIO, PEPS, UEPS, PADRAO */
    
    ultimo_custo DECIMAL(15,4) DEFAULT 0,
    custo_medio DECIMAL(15,4) DEFAULT 0,
    custo_reposicao DECIMAL(15,4) DEFAULT 0,
    
    incluir_frete_custo BOOLEAN DEFAULT TRUE,
    incluir_ipi_custo BOOLEAN DEFAULT TRUE,
    incluir_icms_st_custo BOOLEAN DEFAULT FALSE,
    incluir_outras_despesas_custo BOOLEAN DEFAULT TRUE,
    
    -- ============= PREÇOS =============
    preco_venda_padrao DECIMAL(15,4) DEFAULT 0,
    margem_desejada_percent DECIMAL(5,2),
    markup_percent DECIMAL(5,2),
    desconto_maximo_percent DECIMAL(5,2) DEFAULT 10,
    
    -- ============= IMAGENS E ANEXOS =============
    imagem_principal_url VARCHAR(500),
    imagem_thumb_url VARCHAR(500),
    ficha_tecnica_url VARCHAR(500),
    
    -- ============= STATUS E CONTROLE =============
    ativo BOOLEAN DEFAULT TRUE,
    bloqueado BOOLEAN DEFAULT FALSE,
    motivo_bloqueio TEXT,
    
    -- ============= AUDITORIA =============
    empresa_id BIGINT NOT NULL REFERENCES empresas(id),
    created_by BIGINT REFERENCES usuarios(id),
    updated_by BIGINT REFERENCES usuarios(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP, -- Soft delete
    
    -- ============= CONSTRAINTS =============
    CONSTRAINT chk_tipo_produto CHECK (tipo_produto IN (
        'MATERIA_PRIMA',
        'INSUMO_FERTILIZANTE',
        'INSUMO_DEFENSIVO',
        'INSUMO_SEMENTE',
        'INSUMO_OUTRO',
        'EMBALAGEM',
        'PRODUTO_ACABADO',
        'USO_CONSUMO',
        'ATIVO_IMOBILIZADO',
        'REVENDA'
    )),
    
    CONSTRAINT chk_origem CHECK (origem_mercadoria IN ('0','1','2','3','4','5','6','7','8')),
    
    CONSTRAINT chk_metodo_custeio CHECK (metodo_custeio IN ('MEDIO','PEPS','UEPS','PADRAO')),
    
    CONSTRAINT chk_ncm_format CHECK (ncm ~ '^\d{4}\.\d{2}\.\d{2}$'),
    
    CONSTRAINT chk_pesos CHECK (peso_liquido IS NULL OR peso_bruto IS NULL OR peso_liquido <= peso_bruto),
    
    CONSTRAINT chk_temperaturas CHECK (
        temp_min_celsius IS NULL OR 
        temp_max_celsius IS NULL OR 
        temp_min_celsius <= temp_max_celsius
    )
);

-- ============= ÍNDICES =============
CREATE INDEX idx_produtos_codigo ON produtos(codigo_interno);
CREATE INDEX idx_produtos_barras ON produtos(codigo_barras) WHERE codigo_barras IS NOT NULL;
CREATE INDEX idx_produtos_sku ON produtos(codigo_sku) WHERE codigo_sku IS NOT NULL;
CREATE INDEX idx_produtos_ncm ON produtos(ncm);
CREATE INDEX idx_produtos_tipo ON produtos(tipo_produto);
CREATE INDEX idx_produtos_categoria ON produtos(categoria_id);
CREATE INDEX idx_produtos_empresa ON produtos(empresa_id);
CREATE INDEX idx_produtos_ativo ON produtos(ativo) WHERE ativo = TRUE;
CREATE INDEX idx_produtos_bloqueado ON produtos(bloqueado) WHERE bloqueado = TRUE;

-- Índice Full-Text para busca
CREATE INDEX idx_produtos_descricao_fts ON produtos 
    USING GIN(to_tsvector('portuguese', 
        descricao_completa || ' ' || 
        COALESCE(descricao_resumida, '') || ' ' || 
        COALESCE(observacoes, '')
    ));

-- ============= COMENTÁRIOS =============
COMMENT ON TABLE produtos IS 'Cadastro mestre de produtos, insumos e materiais';
COMMENT ON COLUMN produtos.tipo_produto IS 'Classifica produto para definir tributação';
COMMENT ON COLUMN produtos.ncm IS 'Nomenclatura Comum do Mercosul - obrigatório para NF-e';
COMMENT ON COLUMN produtos.cest IS 'Código Especificador da Substituição Tributária';
COMMENT ON COLUMN produtos.tipo_item IS 'Tipo de item conforme tabela SPED/EFD';
```

### 2.3 Tabela: `produtos_insumos_agricolas`

```sql
-- =====================================================
-- DADOS ESPECÍFICOS PARA INSUMOS AGRÍCOLAS
-- Controles obrigatórios conforme legislação MAPA
-- =====================================================

CREATE TABLE produtos_insumos_agricolas (
    id BIGSERIAL PRIMARY KEY,
    produto_id BIGINT NOT NULL REFERENCES produtos(id) ON DELETE CASCADE,
    
    -- ============= TIPO DE INSUMO =============
    tipo_insumo VARCHAR(50) NOT NULL,
    /* Valores:
       - FERTILIZANTE
       - DEFENSIVO
       - SEMENTE_MUDA
       - CORRETIVO_SOLO
       - INOCULANTE
       - ADJUVANTE
       - HORMONIO_VEGETAL
       - OUTRO
    */
    
    -- ============= REGISTRO MAPA (OBRIGATÓRIO) =============
    registro_mapa VARCHAR(50),
    /* Número do registro no Ministério da Agricultura
       Obrigatório para defensivos e fertilizantes
       Formato varia por tipo de produto
    */
    
    status_registro VARCHAR(20),
    /* Valores: ATIVO, VENCIDO, SEM_REGISTRO */
    
    data_validade_registro DATE,
    titular_registro VARCHAR(200),
    cnpj_titular VARCHAR(18),
    
    -- ============= DEFENSIVOS AGRÍCOLAS =============
    classe_agronomica VARCHAR(50),
    /* Valores:
       - INSETICIDA
       - FUNGICIDA
       - HERBICIDA
       - ACARICIDA
       - NEMATICIDA
       - BACTERICIDA
       - REGULADOR_CRESCIMENTO
       - ESPALHANTE_ADESIVO
       - OUTRO
    */
    
    principio_ativo TEXT,
    /* Lista de princípios ativos (pode ser múltiplo)
       Exemplo: "Glifosato 480 g/L"
    */
    
    concentracao_percent DECIMAL(5,2),
    
    formulacao VARCHAR(20),
    /* Valores comuns:
       EC = Concentrado Emulsionável
       SC = Suspensão Concentrada
       WP = Pó Molhável
       WG = Granulado Dispersível
       CS = Suspensão de Cápsula
       OD = Dispersão Oleosa
       SE = Suspo-emulsão
       SL = Concentrado Solúvel
    */
    
    classe_toxicologica CHAR(1),
    /* Valores:
       I = Extremamente Tóxico (faixa vermelha)
       II = Altamente Tóxico (faixa amarela)
       III = Medianamente Tóxico (faixa azul)
       IV = Pouco Tóxico (faixa verde)
       V = Improvável de Causar Dano (faixa verde)
    */
    
    classe_ambiental CHAR(1),
    /* Valores:
       I = Produto Altamente Perigoso
       II = Produto Muito Perigoso
       III = Produto Perigoso
       IV = Produto Pouco Perigoso
    */
    
    periodo_carencia_dias INTEGER,
    /* Dias entre última aplicação e colheita */
    
    intervalo_reentrada_horas INTEGER,
    /* Horas antes de poder entrar na área tratada */
    
    lmr_mg_kg DECIMAL(10,4),
    /* Limite Máximo de Resíduos (mg/kg) */
    
    dose_min DECIMAL(10,4),
    dose_max DECIMAL(10,4),
    unidade_dose VARCHAR(20),
    /* Exemplos: L/ha, kg/ha, mL/100L, g/100L */
    
    volume_calda_l_ha DECIMAL(10,2),
    /* Volume de calda recomendado em litros por hectare */
    
    -- ============= FERTILIZANTES =============
    tipo_fertilizante VARCHAR(50),
    /* Valores:
       - MINERAL_SIMPLES
       - MINERAL_MISTO
       - MINERAL_COMPLEXO
       - ORGANOMINERAL
       - ORGANICO
       - FOLIAR
       - CONDICIONADOR_SOLO
    */
    
    formula_npk VARCHAR(20),
    /* Exemplo: 20-20-20, 10-10-10, 04-14-08 */
    
    nitrogenio_percent DECIMAL(5,2),
    fosforo_percent DECIMAL(5,2),
    potassio_percent DECIMAL(5,2),
    calcio_percent DECIMAL(5,2),
    magnesio_percent DECIMAL(5,2),
    enxofre_percent DECIMAL(5,2),
    micronutrientes TEXT,
    /* Exemplo JSON: 
       {"B": 0.05, "Cu": 0.03, "Fe": 0.15, "Mn": 0.08, "Zn": 0.10}
    */
    
    modo_aplicacao TEXT,
    /* Valores (pode ser múltiplo - JSON array):
       ["SOLO_FUNDACAO", "COBERTURA", "FERTIRRIGACAO", "FOLIAR"]
    */
    
    -- ============= SEMENTES/MUDAS =============
    cultura_id BIGINT REFERENCES culturas(id),
    variedade VARCHAR(100),
    
    tipo_semente VARCHAR(50),
    /* Valores:
       - CONVENCIONAL
       - HIBRIDA_F1
       - TRANSGENICA
       - ORGANICA_CERTIFICADA
    */
    
    taxa_germinacao_percent DECIMAL(5,2),
    pureza_percent DECIMAL(5,2),
    vigor VARCHAR(20), -- ALTO, MEDIO, BAIXO
    
    ciclo_cultura_dias INTEGER,
    populacao_recomendada_plantas_ha INTEGER,
    densidade_semeadura_sementes_ha INTEGER,
    
    tratamento_semente TEXT,
    /* Exemplo JSON:
       [
         {"tipo": "FUNGICIDA", "produto": "Thiram", "dose": "200g/100kg"},
         {"tipo": "INSETICIDA", "produto": "Imidacloprid", "dose": "100mL/100kg"}
       ]
    */
    
    -- ============= RESTRIÇÕES DE USO =============
    proibido_cultivo_organico BOOLEAN DEFAULT FALSE,
    uso_restrito BOOLEAN DEFAULT FALSE,
    /* Uso restrito = requer receituário especial */
    
    banido_paises TEXT,
    /* JSON array de países onde produto é banido
       Exemplo: ["USA", "DEU", "FRA"]
    */
    
    restricoes_aplicacao TEXT,
    /* Observações sobre restrições de uso */
    
    -- ============= AUDITORIA =============
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- ============= CONSTRAINTS =============
    CONSTRAINT chk_tipo_insumo CHECK (tipo_insumo IN (
        'FERTILIZANTE',
        'DEFENSIVO',
        'SEMENTE_MUDA',
        'CORRETIVO_SOLO',
        'INOCULANTE',
        'ADJUVANTE',
        'HORMONIO_VEGETAL',
        'OUTRO'
    )),
    
    CONSTRAINT chk_status_registro CHECK (status_registro IN ('ATIVO','VENCIDO','SEM_REGISTRO')),
    
    CONSTRAINT chk_classe_tox CHECK (classe_toxicologica IN ('I','II','III','IV','V')),
    
    CONSTRAINT chk_classe_amb CHECK (classe_ambiental IN ('I','II','III','IV')),
    
    CONSTRAINT chk_doses CHECK (dose_min IS NULL OR dose_max IS NULL OR dose_min <= dose_max),
    
    CONSTRAINT chk_percentuais CHECK (
        (nitrogenio_percent IS NULL OR nitrogenio_percent BETWEEN 0 AND 100) AND
        (fosforo_percent IS NULL OR fosforo_percent BETWEEN 0 AND 100) AND
        (potassio_percent IS NULL OR potassio_percent BETWEEN 0 AND 100)
    )
);

-- ============= ÍNDICES =============
CREATE INDEX idx_insumos_produto ON produtos_insumos_agricolas(produto_id);
CREATE INDEX idx_insumos_registro ON produtos_insumos_agricolas(registro_mapa) WHERE registro_mapa IS NOT NULL;
CREATE INDEX idx_insumos_tipo ON produtos_insumos_agricolas(tipo_insumo);
CREATE INDEX idx_insumos_status ON produtos_insumos_agricolas(status_registro);
CREATE INDEX idx_insumos_cultura ON produtos_insumos_agricolas(cultura_id) WHERE cultura_id IS NOT NULL;

-- ============= COMENTÁRIOS =============
COMMENT ON TABLE produtos_insumos_agricolas IS 'Dados específicos e controles legais para insumos agrícolas';
COMMENT ON COLUMN produtos_insumos_agricolas.registro_mapa IS 'Número do registro no MAPA - obrigatório para defensivos e fertilizantes';
COMMENT ON COLUMN produtos_insumos_agricolas.lmr_mg_kg IS 'Limite Máximo de Resíduos conforme Codex Alimentarius';
```

### 2.4 Tabela: `produtos_perfis_fiscais`

```sql
-- =====================================================
-- PERFIS FISCAIS POR CFOP
-- Armazena configurações tributárias por cenário
-- =====================================================

CREATE TABLE produtos_perfis_fiscais (
    id BIGSERIAL PRIMARY KEY,
    produto_id BIGINT NOT NULL REFERENCES produtos(id) ON DELETE CASCADE,
    
    -- ============= IDENTIFICAÇÃO DO PERFIL =============
    nome_perfil VARCHAR(100) NOT NULL,
    /* Exemplo: "Compra Dentro RN", "Venda Exportação" */
    
    descricao TEXT,
    
    -- ============= CENÁRIO DE APLICAÇÃO =============
    cfop VARCHAR(10) NOT NULL,
    /* Código Fiscal de Operações e Prestações
       Exemplos: 1.101, 2.101, 5.101, 6.101, 7.101
    */
    
    uf_origem VARCHAR(2),
    uf_destino VARCHAR(2),
    /* Quando NULL = aplica para qualquer UF */
    
    tipo_operacao VARCHAR(20) NOT NULL,
    /* Valores: ENTRADA, SAIDA */
    
    finalidade VARCHAR(50),
    /* Valores:
       - INDUSTRIALIZACAO
       - COMERCIALIZACAO
       - USO_CONSUMO
       - ATIVO_IMOBILIZADO
       - EXPORTACAO
       - BONIFICACAO
       - BRINDE
       - AMOSTRA_GRATIS
    */
    
    -- ============= ICMS =============
    icms_modalidade VARCHAR(10),
    /* Valores:
       - CST: Para Regime Normal
       - CSOSN: Para Simples Nacional
    */
    
    icms_cst VARCHAR(3),
    /* CST para Regime Normal (Lucro Real/Presumido)
       Valores comuns:
       00 = Tributada integralmente
       10 = Tributada e com cobrança do ICMS por ST
       20 = Com redução de BC
       30 = Isenta ou não tributada e com cobrança do ICMS por ST
       40 = Isenta
       41 = Não tributada
       50 = Suspensão
       51 = Diferimento
       60 = ICMS cobrado anteriormente por ST
       70 = Com redução de BC e cobrança do ICMS por ST
       90 = Outras
    */
    
    icms_csosn VARCHAR(4),
    /* CSOSN para Simples Nacional
       Valores comuns:
       101 = Tributada pelo SN com permissão de crédito
       102 = Tributada pelo SN sem permissão de crédito
       103 = Isenção do ICMS no SN
       201 = Tributada pelo SN com permissão de crédito e ST
       202 = Tributada pelo SN sem permissão de crédito e ST
       203 = Isenção do ICMS no SN e ST
       300 = Imune
       400 = Não tributada pelo SN
       500 = ICMS cobrado anteriormente por ST
       900 = Outros
    */
    
    icms_modalidade_bc VARCHAR(1),
    /* Modalidade determinação BC:
       0 = Margem Valor Agregado (%)
       1 = Pauta (Valor)
       2 = Preço Tabelado Máx. (Valor)
       3 = Valor da Operação
    */
    
    icms_base_calculo_percent DECIMAL(5,2) DEFAULT 100.00,
    /* Percentual da BC = 100% normalmente */
    
    icms_aliquota_percent DECIMAL(5,2),
    /* Alíquota do ICMS
       Varia por UF de destino:
       - Interna RN: 18%
       - Interestadual Sul/Sudeste: 7% ou 12%
       - Exportação: 0%
    */
    
    icms_reducao_bc_percent DECIMAL(5,2) DEFAULT 0,
    /* Percentual de redução da BC quando aplicável */
    
    icms_gera_credito BOOLEAN DEFAULT FALSE,
    /* TRUE = Operação gera crédito de ICMS */
    
    icms_aliquota_credito_percent DECIMAL(5,2),
    /* Alíquota do crédito (quando diferente da alíquota normal) */
    
    -- ============= DIFERENCIAL DE ALÍQUOTA (DIFAL) =============
    calcula_difal BOOLEAN DEFAULT FALSE,
    /* TRUE para operações interestaduais com consumidor final */
    
    difal_aliquota_origem_percent DECIMAL(5,2),
    /* Alíquota interestadual (origem) */
    
    difal_aliquota_destino_percent DECIMAL(5,2),
    /* Alíquota interna (destino) */
    
    difal_percent DECIMAL(5,2),
    /* Diferença = Destino - Origem */
    
    difal_gera_credito BOOLEAN DEFAULT FALSE,
    /* TRUE em alguns casos específicos (ex: Lucro Real em RN) */
    
    -- ============= SUBSTITUIÇÃO TRIBUTÁRIA =============
    st_substituto BOOLEAN DEFAULT FALSE,
    /* TRUE = Empresa é substituta (retém e recolhe ST) */
    
    st_substituido BOOLEAN DEFAULT FALSE,
    /* TRUE = ICMS já foi retido anteriormente */
    
    st_mva_percent DECIMAL(5,2),
    /* Margem de Valor Agregado para cálculo ST */
    
    st_reducao_bc_percent DECIMAL(5,2),
    /* Redução da BC do ICMS ST */
    
    -- ============= IPI =============
    ipi_cst VARCHAR(3),
    /* Código da Situação Tributária do IPI
       ENTRADAS (00-49):
       00 = Entrada com recuperação de crédito
       01 = Entrada tributada com alíquota zero
       02 = Entrada isenta
       03 = Entrada não-tributada
       04 = Entrada imune
       05 = Entrada com suspensão
       49 = Outras entradas
       
       SAÍDAS (50-99):
       50 = Saída tributada
       51 = Saída tributada com alíquota zero
       52 = Saída isenta
       53 = Saída não-tributada
       54 = Saída imune
       55 = Saída com suspensão
       99 = Outras saídas
    */
    
    ipi_aliquota_percent DECIMAL(5,2),
    /* Alíquota conforme tabela TIPI
       Insumos agropecuários geralmente = 0%
    */
    
    ipi_codigo_enquadramento VARCHAR(5) DEFAULT '999',
    /* Código de enquadramento legal do IPI
       999 = Outros (mais comum)
    */
    
    ipi_classe_enquadramento VARCHAR(10),
    /* Classe de enquadramento quando aplicável */
    
    ipi_gera_credito BOOLEAN DEFAULT FALSE,
    /* TRUE = Operação gera crédito de IPI */
    
    ipi_selo_controle BOOLEAN DEFAULT FALSE,
    /* TRUE para produtos que exigem selo IPI */
    
    ipi_qtd_selos INTEGER,
    /* Quantidade de selos quando aplicável */
    
    -- ============= PIS =============
    pis_cst VARCHAR(3),
    /* Código da Situação Tributária do PIS
       ENTRADAS (Crédito) - 50-56, 60-66, 70-75, 98:
       50 = Op. com Direito a Crédito - Vinculada Receita Tributada Mercado Interno
       51 = Op. com Dir. Créd. - Vinc. Rec. Não Tributada Mercado Interno
       52 = Op. com Dir. Créd. - Vinc. Rec. de Exportação
       53 = Op. com Dir. Créd. - Vinc. Rec. Trib. e Não Trib. Mercado Interno
       54 = Op. com Dir. Créd. - Vinc. Rec. Trib. Mercado Interno e Exportação
       55 = Op. com Dir. Créd. - Vinc. Rec. Não Trib. Mercado Interno e Exportação
       56 = Op. com Dir. Créd. - Vinc. Rec. Trib. e Não Trib. e Exportação
       60-66 = Crédito Presumido (variações)
       70 = Op. de Aquisição Sem Direito a Crédito
       71 = Op. de Aquisição com Isenção
       72 = Op. de Aquisição com Suspensão
       73 = Op. de Aquisição a Alíquota Zero
       74 = Op. de Aquisição Sem Incidência da Contribuição
       75 = Op. de Aquisição por Substituição Tributária
       98 = Outras Operações de Entrada
       
       SAÍDAS - 01-09, 49, 99:
       01 = Operação Tributável BC = Valor da Operação Alíquota Normal (Cumulativo)
       02 = Operação Tributável BC = Valor da Operação Alíquota Diferenciada
       03 = Operação Tributável BC = Quantidade Vendida x Alíquota por Unidade
       04 = Operação Tributável Monofásica - Revenda a Alíquota Zero
       05 = Operação Tributável por Substituição Tributária
       06 = Operação Tributável a Alíquota Zero
       07 = Operação Isenta da Contribuição
       08 = Operação Sem Incidência da Contribuição
       09 = Operação com Suspensão da Contribuição
       49 = Outras Operações de Saída
       99 = Outras Operações
    */
    
    pis_natureza_receita VARCHAR(20),
    /* Código da natureza da receita quando aplicável */
    
    pis_aliquota_percent DECIMAL(5,4),
    /* Alíquota do PIS
       - Regime Não-Cumulativo (Lucro Real): 1,65%
       - Regime Cumulativo: 0,65%
       - Importação: 2,10%
    */
    
    pis_gera_credito BOOLEAN DEFAULT FALSE,
    /* TRUE = Operação gera crédito de PIS */
    
    -- ============= COFINS =============
    cofins_cst VARCHAR(3),
    /* Mesmo código do PIS (tabela idêntica) */
    
    cofins_natureza_receita VARCHAR(20),
    
    cofins_aliquota_percent DECIMAL(5,4),
    /* Alíquota do COFINS
       - Regime Não-Cumulativo (Lucro Real): 7,60%
       - Regime Cumulativo: 3,00%
       - Importação: 9,65%
    */
    
    cofins_gera_credito BOOLEAN DEFAULT FALSE,
    /* TRUE = Operação gera crédito de COFINS */
    
    -- ============= INFORMAÇÕES COMPLEMENTARES =============
    observacoes TEXT,
    /* Observações sobre o perfil fiscal */
    
    motivo_desoneracao VARCHAR(100),
    /* Quando há desoneração (ex: "Exportação", "Zona Franca") */
    
    informacoes_adicionais TEXT,
    /* Texto para campo "Informações Adicionais" da NF-e */
    
    -- ============= CONTROLE =============
    ativo BOOLEAN DEFAULT TRUE,
    padrao BOOLEAN DEFAULT FALSE,
    /* TRUE = Perfil padrão para este CFOP */
    
    criado_automaticamente BOOLEAN DEFAULT FALSE,
    /* TRUE = Criado pelo assistente inteligente */
    
    validado BOOLEAN DEFAULT FALSE,
    /* TRUE = Validado por contador/fiscal */
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- ============= CONSTRAINTS =============
    CONSTRAINT chk_tipo_operacao CHECK (tipo_operacao IN ('ENTRADA','SAIDA')),
    
    CONSTRAINT chk_icms_modalidade CHECK (icms_modalidade IN ('CST','CSOSN')),
    
    CONSTRAINT chk_aliquotas_validas CHECK (
        (icms_aliquota_percent IS NULL OR icms_aliquota_percent BETWEEN 0 AND 100) AND
        (ipi_aliquota_percent IS NULL OR ipi_aliquota_percent BETWEEN 0 AND 100) AND
        (pis_aliquota_percent IS NULL OR pis_aliquota_percent BETWEEN 0 AND 100) AND
        (cofins_aliquota_percent IS NULL OR cofins_aliquota_percent BETWEEN 0 AND 100)
    ),
    
    -- Garantir unicidade por cenário
    UNIQUE(produto_id, cfop, COALESCE(uf_origem, ''), COALESCE(uf_destino, ''))
);

-- ============= ÍNDICES =============
CREATE INDEX idx_perfis_produto ON produtos_perfis_fiscais(produto_id);
CREATE INDEX idx_perfis_cfop ON produtos_perfis_fiscais(cfop);
CREATE INDEX idx_perfis_ativo ON produtos_perfis_fiscais(ativo) WHERE ativo = TRUE;
CREATE INDEX idx_perfis_padrao ON produtos_perfis_fiscais(padrao) WHERE padrao = TRUE;
CREATE INDEX idx_perfis_tipo_op ON produtos_perfis_fiscais(tipo_operacao);
CREATE INDEX idx_perfis_ufs ON produtos_perfis_fiscais(uf_origem, uf_destino) 
    WHERE uf_origem IS NOT NULL OR uf_destino IS NOT NULL;

-- ============= COMENTÁRIOS =============
COMMENT ON TABLE produtos_perfis_fiscais IS 'Perfis de tributação por CFOP e cenário';
COMMENT ON COLUMN produtos_perfis_fiscais.cfop IS 'Código Fiscal da Operação que ativa este perfil';
COMMENT ON COLUMN produtos_perfis_fiscais.criado_automaticamente IS 'Indica se foi criado pelo assistente inteligente';
```

### 2.5 Tabela: `ncm_tipi` (Dados Oficiais)

```sql
-- =====================================================
-- TABELA NCM/TIPI - DADOS OFICIAIS RECEITA FEDERAL
-- Importada da tabela TIPI oficial
-- =====================================================

CREATE TABLE ncm_tipi (
    id BIGSERIAL PRIMARY KEY,
    
    -- ============= CÓDIGO NCM =============
    codigo VARCHAR(10) NOT NULL UNIQUE,
    /* Formato: 0000.00.00 (8 dígitos)
       Exemplo: 3105.20.00
    */
    
    descricao TEXT NOT NULL,
    /* Descrição oficial do produto conforme TIPI */
    
    ex_tipi VARCHAR(3),
    /* EX (Exceção) quando aplicável
       Usado para classificações mais específicas
    */
    
    -- ============= ESTRUTURA HIERÁRQUICA =============
    capitulo VARCHAR(2) NOT NULL,
    /* Primeiros 2 dígitos - Exemplo: 31 */
    
    posicao VARCHAR(4) NOT NULL,
    /* Primeiros 4 dígitos - Exemplo: 3105 */
    
    subposicao VARCHAR(6),
    /* Primeiros 6 dígitos - Exemplo: 3105.20 */
    
    item VARCHAR(8),
    /* 8 dígitos completos - Exemplo: 3105.20.00 */
    
    subitem VARCHAR(10),
    /* Com EX quando aplicável - Exemplo: 3105.20.00 Ex 01 */
    
    -- ============= TRIBUTAÇÃO IPI =============
    aliquota_ipi_nacional DECIMAL(5,2) DEFAULT 0,
    /* Alíquota IPI para mercado nacional */
    
    aliquota_ipi_importacao DECIMAL(5,2) DEFAULT 0,
    /* Alíquota IPI para importação */
    
    incide_ipi BOOLEAN DEFAULT FALSE,
    /* TRUE = Produto sujeito a IPI */
    
    -- ============= UNIDADE =============
    unidade_medida_padrao VARCHAR(10),
    /* Unidade estatística padrão (KG, L, UN, etc.) */
    
    -- ============= ATO LEGAL =============
    tipo_ato VARCHAR(50),
    /* Tipo do ato normativo (Decreto, Lei, etc.) */
    
    numero_ato VARCHAR(20),
    /* Número do ato */
    
    ano_ato INTEGER,
    /* Ano de publicação do ato */
    
    -- ============= VIGÊNCIA =============
    data_inicio_vigencia DATE NOT NULL,
    data_fim_vigencia DATE,
    /* NULL = vigente indefinidamente */
    
    ativo BOOLEAN DEFAULT TRUE,
    /* FALSE = NCM foi revogado/substituído */
    
    ncm_substituto VARCHAR(10),
    /* NCM que substituiu este (quando aplicável) */
    
    -- ============= OBSERVAÇÕES =============
    observacoes TEXT,
    /* Notas complementares da TIPI */
    
    -- ============= METADADOS =============
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- ============= CONSTRAINTS =============
    CONSTRAINT chk_ncm_formato CHECK (codigo ~ '^\d{4}\.\d{2}\.\d{2})
);

-- ============= ÍNDICES =============
CREATE INDEX idx_ncm_codigo ON ncm_tipi(codigo);
CREATE INDEX idx_ncm_capitulo ON ncm_tipi(capitulo);
CREATE INDEX idx_ncm_posicao ON ncm_tipi(posicao);
CREATE INDEX idx_ncm_ativo ON ncm_tipi(ativo) WHERE ativo = TRUE;
CREATE INDEX idx_ncm_vigencia ON ncm_tipi(data_inicio_vigencia, data_fim_vigencia);

-- Índice Full-Text para busca por descrição
CREATE INDEX idx_ncm_descricao_fts ON ncm_tipi 
    USING GIN(to_tsvector('portuguese', descricao));

-- ============= COMENTÁRIOS =============
COMMENT ON TABLE ncm_tipi IS 'Tabela oficial NCM/TIPI da Receita Federal do Brasil';
COMMENT ON COLUMN ncm_tipi.codigo IS 'Código NCM no formato 0000.00.00';
COMMENT ON COLUMN ncm_tipi.ex_tipi IS 'Exceção TIPI para classificações específicas';
```

### 2.6 Tabelas Auxiliares

```sql
-- =====================================================
-- CATEGORIAS E CLASSIFICAÇÕES
-- =====================================================

CREATE TABLE categorias (
    id BIGSERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    codigo VARCHAR(20) UNIQUE,
    descricao TEXT,
    ordem INTEGER DEFAULT 0,
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE subcategorias (
    id BIGSERIAL PRIMARY KEY,
    categoria_id BIGINT REFERENCES categorias(id),
    nome VARCHAR(100) NOT NULL,
    codigo VARCHAR(20),
    ordem INTEGER DEFAULT 0,
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE grupos (
    id BIGSERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    codigo VARCHAR(20),
    ordem INTEGER DEFAULT 0,
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE familias (
    id BIGSERIAL PRIMARY KEY,
    grupo_id BIGINT REFERENCES grupos(id),
    nome VARCHAR(100) NOT NULL,
    codigo VARCHAR(20),
    ordem INTEGER DEFAULT 0,
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- =====================================================
-- RELAÇÕES PRODUTO x CULTURAS (DEFENSIVOS)
-- =====================================================

CREATE TABLE produtos_culturas_registradas (
    id BIGSERIAL PRIMARY KEY,
    produto_id BIGINT REFERENCES produtos(id) ON DELETE CASCADE,
    cultura_id BIGINT REFERENCES culturas(id),
    dose_recomendada DECIMAL(10,4),
    unidade_dose VARCHAR(20),
    observacoes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(produto_id, cultura_id)
);

CREATE INDEX idx_prod_culturas_produto ON produtos_culturas_registradas(produto_id);
CREATE INDEX idx_prod_culturas_cultura ON produtos_culturas_registradas(cultura_id);

-- =====================================================
-- RELAÇÕES PRODUTO x PRAGAS/DOENÇAS (DEFENSIVOS)
-- =====================================================

CREATE TABLE produtos_pragas_alvo (
    id BIGSERIAL PRIMARY KEY,
    produto_id BIGINT REFERENCES produtos(id) ON DELETE CASCADE,
    praga_doenca_id BIGINT REFERENCES pragas_doencas(id),
    eficacia_percent DECIMAL(5,2),
    observacoes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(produto_id, praga_doenca_id)
);

CREATE INDEX idx_prod_pragas_produto ON produtos_pragas_alvo(produto_id);
CREATE INDEX idx_prod_pragas_praga ON produtos_pragas_alvo(praga_doenca_id);

-- =====================================================
-- COMPATIBILIDADE ENTRE PRODUTOS (DEFENSIVOS)
-- =====================================================

CREATE TABLE produtos_compatibilidade (
    id BIGSERIAL PRIMARY KEY,
    produto_id BIGINT REFERENCES produtos(id) ON DELETE CASCADE,
    produto_compativel_id BIGINT REFERENCES produtos(id) ON DELETE CASCADE,
    tipo_compatibilidade VARCHAR(20) NOT NULL,
    /* Valores:
       - COMPATIVEL: Pode misturar sem problemas
       - INCOMPATIVEL: Não pode misturar (reação química)
       - CONDICIONAL: Pode misturar sob certas condições
    */
    observacao TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT chk_tipo_compat CHECK (tipo_compatibilidade IN ('COMPATIVEL','INCOMPATIVEL','CONDICIONAL')),
    CONSTRAINT chk_produtos_diferentes CHECK (produto_id != produto_compativel_id),
    UNIQUE(produto_id, produto_compativel_id)
);

CREATE INDEX idx_compatib_produto ON produtos_compatibilidade(produto_id);
CREATE INDEX idx_compatib_compat ON produtos_compatibilidade(produto_compativel_id);

-- =====================================================
-- HISTÓRICO DE ALTERAÇÕES
-- =====================================================

CREATE TABLE produtos_historico (
    id BIGSERIAL PRIMARY KEY,
    produto_id BIGINT REFERENCES produtos(id) ON DELETE CASCADE,
    
    -- Tipo de alteração
    tipo_alteracao VARCHAR(50) NOT NULL,
    /* Valores:
       - CRIACAO
       - EDICAO_DADOS
       - EDICAO_FISCAL
       - EDICAO_PRECO
       - ATIVACAO
       - INATIVACAO
       - BLOQUEIO
       - DESBLOQUEIO
    */
    
    -- Campos alterados
    tabela VARCHAR(50) NOT NULL,
    campo_alterado VARCHAR(100),
    valor_anterior TEXT,
    valor_novo TEXT,
    
    -- Justificativa
    motivo TEXT,
    
    -- Auditoria
    usuario_id BIGINT REFERENCES usuarios(id),
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_historico_produto ON produtos_historico(produto_id);
CREATE INDEX idx_historico_data ON produtos_historico(created_at DESC);
CREATE INDEX idx_historico_usuario ON produtos_historico(usuario_id);
CREATE INDEX idx_historico_tipo ON produtos_historico(tipo_alteracao);

-- =====================================================
-- TABELAS DE PREÇO
-- =====================================================

CREATE TABLE tabelas_preco (
    id BIGSERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    descricao TEXT,
    tipo VARCHAR(50),
    /* Valores: ATACADO, VAREJO, EXPORTACAO, PROMOCIONAL */
    ativo BOOLEAN DEFAULT TRUE,
    data_inicio DATE,
    data_fim DATE,
    empresa_id BIGINT REFERENCES empresas(id),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE produtos_tabelas_preco (
    id BIGSERIAL PRIMARY KEY,
    produto_id BIGINT REFERENCES produtos(id) ON DELETE CASCADE,
    tabela_preco_id BIGINT REFERENCES tabelas_preco(id) ON DELETE CASCADE,
    preco DECIMAL(15,4) NOT NULL,
    desconto_maximo_percent DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(produto_id, tabela_preco_id)
);

-- =====================================================
-- IMAGENS DO PRODUTO
-- =====================================================

CREATE TABLE produtos_imagens (
    id BIGSERIAL PRIMARY KEY,
    produto_id BIGINT REFERENCES produtos(id) ON DELETE CASCADE,
    url VARCHAR(500) NOT NULL,
    tipo VARCHAR(20),
    /* Valores: PRINCIPAL, GALERIA, TECNICA, ROTULO */
    ordem INTEGER DEFAULT 0,
    legenda VARCHAR(200),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_imagens_produto ON produtos_imagens(produto_id);
CREATE INDEX idx_imagens_tipo ON produtos_imagens(tipo);
```

---

## 3. REGRAS DE NEGÓCIO

### 3.1 Regras Gerais

**RN-PROD-001: Código Interno Único**
- Código interno deve ser único por empresa
- Sistema pode gerar automaticamente (sequencial ou baseado em padrão)
- Formato configurável por empresa (ex: PROD-0001, INS-FER-001)

**RN-PROD-002: NCM Obrigatório**
- Todo produto deve ter NCM válido (8 dígitos)
- NCM deve existir na tabela `ncm_tipi` e estar ativo
- Sistema valida formato: 0000.00.00

**RN-PROD-003: Descrição NF Limitada**
- Descrição para NF-e limitada a 120 caracteres (limite SEFAZ)
- Sistema alerta se ultrapassar
- Truncar automaticamente se necessário (com confirmação)

**RN-PROD-004: Unidades de Medida**
- Unidades devem estar na tabela oficial SEFAZ
- Fator de conversão obrigatório quando unidades diferentes
- Sistema calcula conversões automaticamente

**RN-PROD-005: Controle de Estoque**
- Se `movimenta_estoque = FALSE`, não registrar movimentações
- Se `controla_lote = TRUE`, exigir lote em todas as movimentações
- Se `controla_validade = TRUE`, validar datas de vencimento

### 3.2 Regras de Insumos Agrícolas

**RN-INS-001: Registro MAPA Obrigatório**
- Defensivos e fertilizantes DEVEM ter registro MAPA
- Produtos sem registro só visíveis conforme permissão 
- Sistema alerta uso em OS se sem registro válido
- Alerta 30 dias antes do vencimento do registro

**RN-INS-002: Classe Toxicológica**
- Obrigatória para defensivos
- Classes I e II exigem receituário especial
- Sistema valida formação do responsável técnico (CREA)

**RN-INS-003: Período de Carência**
- Sistema valida se colheita respeita período de carência
- Bloqueia colheita antes do período (com override admin)
- Alerta no planejamento de aplicação

**RN-INS-004: LMR (Limite Máximo de Resíduos)**
- Sistema calcula quantidade máxima permitida
- Alerta se ultrapassar dose recomendada
- Sistema pergunta se Bloqueia ou não embarque se detectado problema, se autoriza pede justificativa

**RN-INS-005: Compatibilidade de Produtos**
- Sistema valida misturas incompatíveis
- Alerta ao criar OS com produtos incompatíveis
- Sugere alternativas compatíveis

### 3.3 Regras de Tributação

**RN-TRIB-001: Perfil Fiscal por CFOP**
- Cada produto deve ter perfil fiscal para CFOPs utilizados
- Sistema cria automaticamente perfis principais
- Mínimo 3 perfis: Compra RN, Compra Fora, Venda RN

**RN-TRIB-002: Validação CST x CFOP**
- CST deve ser compatível com CFOP
- Exemplos de incompatibilidade:
  - CFOP 7.101 (Exportação) com ICMS tributado
  - CFOP 1.556 (Uso/Consumo) gerando crédito
- Sistema valida e bloqueia configurações inválidas

**RN-TRIB-003: Crédito Tributário**
- **Insumo de Produção**: Gera crédito (ICMS, IPI, PIS, COFINS)
- **Uso/Consumo**: NÃO gera crédito
- **Embalagem**: Gera crédito se integra produto final
- **Ativo Imobilizado**: Crédito parcelado em 48 meses (ICMS)

**RN-TRIB-004: DIFAL (Diferencial de Alíquota)**
- Calcular em operações interestaduais com consumidor final
- DIFAL = Alíquota Destino - Alíquota Origem
- Partilha: 100% para UF destino (desde 2022)
- Para empresa em Lucro Real RN: DIFAL gera crédito

**RN-TRIB-005: Substituição Tributária**
- Se produto sujeito a ST, CEST é obrigatório
- Não pode gerar crédito se ST já foi retido
- MVA conforme lista oficial por UF

**RN-TRIB-006: Exportação**
- CFOP 7.xxx = Imunidade de todos os impostos
- Alíquotas = 0%
- Manter créditos das entradas (não estornar)
- Motivo desoneração: "Exportação"

**RN-TRIB-007: IPI Insumos Agropecuários**
- Capítulos 31 e 38.08 da NCM = IPI 0% (Lei 10.925/2004)
- Automático baseado no NCM
- Mesmo zerado, informar CST corretamente

### 3.4 Regras de Validação

**RN-VAL-001: Validações em Tempo Real**
- NCM: Formato e existência na tabela
- CEST: Formato 00.000.00 quando informado
- Alíquotas: Entre 0 e 100%
- Pesos: Líquido ≤ Bruto
- Temperaturas: Mínima ≤ Máxima
- Doses: Mínima ≤ Máxima

**RN-VAL-002: Validações de Integridade**
- Produto não pode ser excluído se tiver movimentações
- Produto não pode ser excluído se estiver em pedido aberto
- Inativação não impede consulta histórico

**RN-VAL-003: Alertas Automáticos**
- 🔴 **Crítico**: Produto sem NCM, sem perfil fiscal
- 🟡 **Atenção**: Registro MAPA vencendo <30 dias
- 🟢 **Info**: Estoque abaixo do mínimo

---

## 4. INTERFACE DO USUÁRIO

### 4.1 Estrutura da Tela

A interface é organizada em **6 abas principais**:

1. **Dados Básicos**: Identificação, classificação, unidades
2. **Fiscal**: NCM, origem, tipo de item
3. **Estoque**: Controles, parâmetros, armazenamento
4. **Custos e Preços**: Custeio, valores, margens
5. **Insumo Agrícola**: Dados específicos (condicional)
6. **Perfis Fiscais**: Tributação por CFOP

### 4.2 ABA 1: DADOS BÁSICOS

```html
<!-- ==================== SEÇÃO: IDENTIFICAÇÃO ==================== -->
<div class="card mb-4">
    <div class="card-header">
        <h5>Identificação</h5>
    </div>
    <div class="card-body">
        <div class="row">
            <!-- Código Interno -->
            <div class="col-md-4 mb-3">
                <label class="form-label required">Código Interno</label>
                <div class="input-group">
                    <input 
                        type="text" 
                        class="form-control" 
                        id="codigo_interno"
                        required
                        maxlength="50"
                        placeholder="Ex: PROD-0001"
                    />
                    <button 
                        type="button" 
                        class="btn btn-outline-secondary"
                        onclick="gerarCodigoAutomatico()"
                        title="Gerar código automaticamente"
                    >
                        🔢 Auto
                    </button>
                </div>
                <small class="text-muted">Único por empresa</small>
            </div>
            
            <!-- Código de Barras -->
            <div class="col-md-4 mb-3">
                <label class="form-label">Código de Barras / EAN</label>
                <input 
                    type="text" 
                    class="form-control" 
                    id="codigo_barras"
                    maxlength="20"
                    placeholder="7891234567890"
                />
            </div>
            
            <!-- Código SKU -->
            <div class="col-md-4 mb-3">
                <label class="form-label">Código SKU</label>
                <input 
                    type="text" 
                    class="form-control" 
                    id="codigo_sku"
                    maxlength="50"
                    placeholder="SKU-ABC-123"
                />
            </div>
        </div>
        
        <!-- Descrição Completa -->
        <div class="row">
            <div class="col-md-12 mb-3">
                <label class="form-label required">Descrição Completa</label>
                <input 
                    type="text" 
                    class="form-control" 
                    id="descricao_completa"
                    required
                    maxlength="500"
                    placeholder="Descrição detalhada do produto"
                />
                <small class="text-muted">
                    <span id="contador_desc_completa">0</span>/500 caracteres
                </small>
            </div>
        </div>
        
        <div class="row">
            <!-- Descrição Resumida -->