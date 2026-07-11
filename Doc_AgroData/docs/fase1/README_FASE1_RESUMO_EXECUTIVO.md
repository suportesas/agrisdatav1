# Fase 1: Resumo Executivo - NF-e XML Import

**Data**: 31/03/2026  
**Status**: Pronto para iniciar  
**Estimativa**: 17.5 horas (~2 semanas para 1 dev full-time)  
**Risco**: Baixo (técnica madura + XML parsing bem documentado)

---

## 🎯 Objetivo

Implementar **parsing automático de NF-e XML** para reduzir entrada manual de dados no fluxo de Compras > Recebimento. Usuário faz upload de arquivo `.xml` e sistema extrai/mapeia dados → preview com opção de editar → confirmação → `RecebimentoCompra` criado.

---

## 📊 O Que Você Terá

### Antes (Fluxo Atual)
```
Usuário recebe NF-e
  ↓
Digita manualmente em "Entrada Direta de NF-e":
  - Número da NF
  - Série
  - Fornecedor
  - Data emissão
  - Valor total
  - Cada item: produto, quantidade, preço
  ↓
Tempo: ~5-10 min por NF-e
Erro: Alto risco de digitação
```

### Depois (Com Fase 1)
```
Usuário faz upload de arquivo.xml
  ↓
Sistema extrai automaticamente:
  - Número, série, chave, datas
  - Fornecedor (busca por CNPJ)
  - Valor total e itens
  - Sugestiona pedido compatível (se existir)
  ↓
Usuário revisa/edita in preview
  ↓
Confirma → RecebimentoCompra criado
Tempo: ~1-2 min por NF-e
Erro: ~0% (dados do XML autorizado)
```

---

## 🏗️ Arquitetura Simplificada

```
Upload XML
    ↓
[Parser NFEParser] → Extrai dados brutos
    ↓
[Validators] → Valida: duplicação, fornecedor, totais, datas
    ↓
[Preview Form] → Usuário revisa/edita
    ↓
[Create RecebimentoCompra] → Salva com status=PENDENTE
    ↓
✅ Recebimento pronto para conferência
```

**Componentes Novos**:
- ✅ `compras/parsers/nfe_parser.py` - Parser genérico XML
- ✅ `compras/utils/nfe_validators.py` - Validações semânticas
- ✅ `compras/forms_xml_nf.py` - Forms estendidos
- ✅ `compras/views.py` - 3 views (upload, preview, confirm)
- ✅ `compras/templates/nfe/` - 2 templates (import, preview)

**Existente + Usar**:
- ✅ `RecebimentoCompra` model (95% pronto)
- ✅ `ItemRecebimento` model (já existe)
- ✅ `xmltodict` library (já em requirements.txt)
- ✅ Feature flag `COMPRAS_XML_IMPORT` (criada em Fase 0)

---

## 💡 Casos de Uso Cobertos

| Caso | O Quê | Benefício |
|------|-------|----------|
| **NF-e com Pedido existente** | Upload XXX.xml → Sistema encontra Pedido compatível → Vincula automático | Fluxo completo sem digitação |
| **Entrada direta** | Upload XXX.xml → Nenhum Pedido encontrado → Oferecer entrada sem pedido | Flexibilidade para devoluções/trocas |
| **Divergência de preço** | NF-e @ R$10, Pedido @ R$12 → Warning ao usuário | Detecção de erros automática |
| **XML inválido** | Upload corrompido → Fallback para entrada manual | Robustez (sempre tem opção) |
| **Duplicação** | Segunda importação da mesma chave → Rejeitar | Evita dobro processamento |

---

## 📋 Backlog de 10 Tarefas

```
1.1  Setup Branch                    0.5h   ✅ Pronto → Mkdir, git branch
1.2  Parser XML                      3h     ✅ Pronto → xmltodict-based parser
1.3  Validações de Negócio           2h     ✅ Pronto → Duplicação, fornecedor, totais
1.4  Model ItemRecebimento + Migração 1.5h  ✅ Pronto → Verificar + extender
1.5  Forms Estendidos                1h     ✅ Pronto → Upload + Preview forms
1.6  Views (Import, Preview)         2h     ✅ Pronto → 3 views + 2 templates
1.7  Salvar Recebimento             1.5h    ✅ Pronto → criar_recebimento_from_nfe()
1.8  Testes Unitários               3h      ✅ Pronto → Parser, validators, models
1.9  Testes de Integração           2h      ✅ Pronto → E2E upload → recebimento
1.10 Documentação SOP + Guia Usuário 1h     ✅ Pronto → Docs + screenshots

                              TOTAL: 17.5 horas
```

**Timeline** (1 dev full-time):
- **Segunda-Terça** (1.1-1.4): Parser + Models
- **Quarta** (1.5-1.6): Forms + Views
- **Quinta** (1.7-1.8): Create + Unit Tests
- **Sexta** (1.9-1.10): Integration + Docs

---

## ✅ Garantias

### Segurança
- ✅ **Feature Flag**: Função ativada apenas se `COMPRAS_XML_IMPORT=True` (e.env)
- ✅ **Rollback**: Desativar flag → voltar ao manual em 30 segundos
- ✅ **Multi-tenant**: Cada empresa só vê sua própria NF-e

### Performance
- ✅ **XML Parse**: <100ms (xmltodict)
- ✅ **Validações**: <50ms
- ✅ **Recebimento Creation**: <500ms
- ✅ Total E2E: <2 seg (incluindo criação de ItemRecebimentos)

### Qualidade
- ✅ **Coverage**: ≥80% testes unitários
- ✅ **Regressão**: Smoke test Fase 0 continua passando
- ✅ **Documentação**: Guia técnico + guia usuário + SOP

### Confiabilidade
- ✅ **Validação de Chave**: Duplicação bloqueada
- ✅ **Validação de Fornecedor**: Erro claro se CNPJ não existe
- ✅ **Transação Atômica**: Se falhar em qualquer item → rollback automático
- ✅ **Logging**: Todos os passos registrados para troubleshooting

---

## 📚 Documentação Criada

| Documento | Propósito | Público |
|-----------|----------|---------|
| **ESPECIFICACAO_FASE1_NF-E_XML.md** | Detalhamento técnico completo | Dev/Tech Lead |
| **BACKLOG_EXECUTAVEL_FASE1.md** | 10 tarefas prontas para começar | Dev/Tech Lead |
| **GUIA_USUARIO_NF-E_IMPORT.md** | Como usar a funcionalidade | End User |
| **SOP_TECNICO_NF-E_PARSER.md** | Troubleshooting + extensibilidade | DevOps/Tech Lead |
| **README_FASE1_STATUS.md** | Status e progress tracking | Project Manager |

---

## 🚀 Próximos Passos

### Opção A: Iniciar Fase 1 AGORA
```bash
1. Ler BACKLOG_EXECUTAVEL_FASE1.md (5 min)
2. Assignar Task 1.1 → Dev (hoje)
3. Daily standup 14:00 BRT
4. Daily deployment if features ready
```

### Opção B: Revisar + Planejar
```bash
1. Ler ESPECIFICACAO_FASE1_NF-E_XML.md (15 min)
2. Discussão com Product
3. Ajustar escopo se necessário (RF-054 PRD)
4. Confirmar estimativas
5. Iniciar segunda-feira
```

---

## 🎁 Bônus: Fase 2 já planejada

Após Fase 1 de NF-e XML passar:

- **Fase 2**: Rastreabilidade + Validação SEFAZ
  - Integração com SEFAZ (check de autorização)
  - Rastreabilidade de lote/validade
  - Alertas de divergência

- **Fase 3**: Automação Avançada
  - Faturamento automático pós-recebimento
  - Scoring de fornecedor
  - Recomendações de ajuste de preço

---

## ❓ FAQ Rápido

**P: E se o XML for inválido?**  
R: Fallback automático para entrada manual pura (template entrada_direta_nf.html já existe)

**P: Quanto tempo leva por NF-e?**  
R: ~60 segundos (vs 5-10 min manual)

**P: Precisa desativar se tiver bug?**  
R: Sim - basta set `FF_COMPRAS_XML_IMPORT=False` no .env

**P: Qual a cobertura de teste?**  
R: ≥80% nas funções críticas (parser, validators, create)

**P: Preciso saber XML?**  
R: Não - usuário final só faz upload. Dev conhece estrutura NF-e

**P: Funciona com qualquer NF-e?**  
R: NF-e v4.0 (padrão do Brasil). Outros formatos em Fase 2.

---

## 📞 Suporte

**Dúvidas técnicas**?
- Ler `ESPECIFICACAO_FASE1_NF-E_XML.md` (seção Arquitetura)
- Contatar Tech Lead

**Bug após deploy**?
- Set `FF_COMPRAS_XML_IMPORT=False`
- Usar "Entrada Direta Manual"
- Report issue + snapshot

**Treinamento usuário**?
- Guia: `GUIA_USUARIO_NF-E_IMPORT.md`
- Video: TBD (após implementação)

---

**Versão**: v1.0 - Executive Summary  
**Status**: ✅ Pronto para começar  
**Próximo Checkpoint**: Após Task 1.1 (branch + setup)

---

## ✨ Resumo Final

- ✅ **Especificação técnica 100% completa** (análise do código existente, XML schema, arquitetura definida)
- ✅ **Backlog executável com 10 tarefas** (checklist, exemplos de código, testes) 
- ✅ **Risco baixo** (técnica madura, rollback simples, regressão = 0)
- ✅ **Tempo realista**  (17.5h = 2 semanas com 1 dev)
- ✅ **Pronto para começar segunda-feira**

**Deseja**: 
1. 🚀 **Iniciar Fase 1** agora → Assign Task 1.1
2. 📋 **Revisar escopo** → Ler ESPECIFICACAO...
3. ❌ **Pausar** → Executar outra coisa

---
