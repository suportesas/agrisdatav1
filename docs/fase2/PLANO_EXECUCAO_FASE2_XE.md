# 📋 Plano de Execução - Fase 2 XE
## SEFAZ Validation + Rastreabilidade de Lote

**Decisão**: 02/04/2026  
**Escolha**: Opção 1 (XML Enhancement)  
**Estimativa**: 22 horas  
**Sprint**: 2-3 semanas (1 dev)  
**Status**: 🔄 KICKOFF

---

## 🎯 Objetivo Final

Implementar validação automática com SEFAZ e rastreabilidade completa de lote, garantindo:
- ✅ Segurança: NF-e autorizado pela Receita Federal
- ✅ Rastreabilidade: Insumo → Lote → Validade
- ✅ Automação: Batch import de múltiplas NF-es
- ✅ Auditoria: Log completo para compliance

---

## 📦 Breakdown de Tasks

### **Bloco 1: Infraestrutura SEFAZ (8h)**

#### Task 1.1: Setup SEFAZ Web Service
- [ ] Pesquisar integração com Web Service da Receita (SOAP/REST)
- [ ] Instalar lib `zeep` (SOAP client) ou `requests` (REST)
- [ ] Criar classe `SEFAZClient` em `compras/sefaz.py`
- [ ] Implementar auth por certificado digital (A1)
- [ ] Cache decorator: 24h por chave NF-e
- **Files**: `compras/sefaz.py`, `requirements.txt`
- **Deps**: Certificado A1 disponível (pré-requisito)

#### Task 1.2: Validação de NF-e
- [ ] Método `validate_nfe(chave_nfe, cnpj_fornecedor)` 
- [ ] Comparar dados: XML local vs SEFAZ
  - Valor total
  - Quantidade itens
  - Data emissão
- [ ] Retornar: `{status: 'valid'|'mismatch'|'not_found'|'cancelled', data: {...}}`
- [ ] Tratamento de erros SEFAZ (timeout, cert inválido, etc)
- **Tests**: Mock SEFAZ responses (3+ cenários)

#### Task 1.3: Rate Limiting + Retry
- [ ] Queue com `django-rq` ou Celery
- [ ] Backoff exponencial: 1s → 2s → 4s → 8s (max 4 tentativas)
- [ ] Log todas as chamadas SEFAZ
- **Files**: `compras/tasks.py`

---

### **Bloco 2: Modelo LoteRecebimento (3h)**

#### Task 2.1: Migration + Model
- [ ] Criar model `LoteRecebimento`:
  ```python
  class LoteRecebimento(models.Model):
      empresa = ForeignKey(Empresa)
      recebimento = ForeignKey(RecebimentoCompra)
      chave_nfe = CharField(unique=True)
      numero_lote = CharField()
      data_validade = DateField()
      numero_sequencial = CharField()
      status_sefaz = CharField(choices=[('validado', 'Validado'), ('pendente', 'Pendente'), ('rejeitado', 'Rejeitado')])
      sefaz_data_validacao = DateTimeField()
      sefaz_response = JSONField()  # Cache da resposta SEFAZ
      created_at = DateTimeField(auto_now_add=True)
  ```
- [ ] Criar migration: `makemigrations` + `migrate`
- [ ] Índice: `(empresa, chave_nfe)`

#### Task 2.2: Manager + QuerySet
- [ ] `LoteRecebimento.objects.por_validar()` (status='pendente')
- [ ] `LoteRecebimento.objects.vencidos()` (data_validade < hoje)
- [ ] `LoteRecebimento.objects.por_fornecedor(fornecedor_id)`

#### Task 2.3: Relação com RecebimentoCompra
- [ ] RecebimentoCompra.lote = ForeignKey(LoteRecebimento, null=True)
- [ ] Migration: `python manage.py makemigrations` + `migrate`
- [ ] Validação: Ao salvar RecebimentoCompra, criar LoteRecebimento se não existir

---

### **Bloco 3: Processamento em Lote (4h)**

#### Task 3.1: Celery Task para Validação
- [ ] `validate_batch_nfe_from_xml.delay(recebimento_ids)`
- [ ] Iterar sobre lista de RecebimentoCompra
- [ ] Para cada um: chamada SEFAZ em fila (rate-limited)
- [ ] Atualizar LoteRecebimento com resultado
- [ ] Progressbar via Celery task state

#### Task 3.2: Upload ZIP com múltiplas NF-es
- [ ] View `batch_upload_nfe_zip(request)` 
- [ ] Extrair XML do ZIP
- [ ] Validar nomes (e.g., `123456789012345.xml`)
- [ ] Disparar Celery task com lista de XMLs
- [ ] Retornar URL para monitorar progresso

#### Task 3.3: Progress Tracking
- [ ] WebSocket ou polling para atualizar status em tempo real
- [ ] Mostrar: "3/50 NF-es validadas, 2 erros, tempo estimado 5 min"

---

### **Bloco 4: Testes (5h)**

#### Task 4.1: Unit Tests - SEFAZ Client
- [ ] `test_sefaz_valid_nfe()` - chave válida, retorna dados
- [ ] `test_sefaz_invalid_nfe()` - chave inválida, status 'not_found'
- [ ] `test_sefaz_cancelled_nfe()` - chave cancelada, status 'cancelled'
- [ ] `test_sefaz_mismatch()` - dados não combinam
- [ ] `test_sefaz_timeout_retry()` - timeout, retry com backoff
- **Framework**: pytest + mock responses

#### Task 4.2: Integration Tests - LoteRecebimento
- [ ] Criar RecebimentoCompra → Validar SEFAZ → Criar LoteRecebimento
- [ ] Verificar status_sefaz atualizado
- [ ] Verificar cache por 24h funciona

#### Task 4.3: End-to-End Tests
- [ ] Upload ZIP com 5 XMLs
- [ ] Celery task processa todos
- [ ] Verificar ResultSet: 5 LoteRecebimentos criados, statuses corretos

---

### **Bloco 5: Documentação (2h)**

#### Task 5.1: Standard Operating Procedure (SOP)
- [ ] Como ativar validação SEFAZ (flag)
- [ ] Como fazer upload em lote
- [ ] Como interpretar status_sefaz
- [ ] O que fazer se NF-e foi rejeitada

#### Task 5.2: Troubleshooting Guide
- [ ] "Certificado inválido" → Solução
- [ ] "SEFAZ rate limited" → Backoff automático
- [ ] "NF-e cancelada" → Como proceder
- [ ] "Dados XML não batem com SEFAZ" → Debug checklist

#### Task 5.3: Architecture Diagram
- [ ] Fluxo: XML Upload → SEFAZ Validation → LoteRecebimento
- [ ] Integração com existentes models

---

## 🗂️ Arquivos a Criar/Modificar

| Arquivo | Tipo | Descrição |
|---------|------|-----------|
| `compras/models.py` | Modify | Adicionar FK em RecebimentoCompra, criar LoteRecebimento |
| `compras/sefaz.py` | Create | SEFAZClient class, validate_nfe() |
| `compras/tasks.py` | Modify | Adicionar validate_batch_nfe_from_xml() |
| `compras/views.py` | Modify | Adicionar batch_upload_nfe_zip() view |
| `compras/tests.py` | Modify | 8+ novos testes (SEFAZ, LoteRecebimento, batch) |
| `migrations/` | Create | Models LoteRecebimento + RelatedTo RecebimentoCompra |
| `docs/fase2/SOP_SEFAZ_VALIDACAO.md` | Create | Documentação operacional |
| `docs/fase2/TROUBLESHOOTING_SEFAZ.md` | Create | Guia de problemas |
| `.env` | Modify | Adicionar `SEFAZ_CERT_PATH`, `SEFAZ_ENABLED` flag |

---

## 🚀 Próximos Passos Imediatos

### ✅ Fase de Setup (hoje)
1. [ ] Revisar este plano com product/tech lead
2. [ ] Validar pré-requisitos:
   - [ ] Certificado digital A1 disponível?
   - [ ] Docstring do Web Service SEFAZ pesquisada?
3. [ ] Atualizar roadmap em `CHANGELOG.md`

### 📅 Sprint 1 (Semana 1 - 8h)
- [ ] **Task 1.1**: Setup SEFAZ Web Service
- [ ] **Task 1.2**: Validação de NF-e (com mocks)
- [ ] **Task 2.1**: Migration + Model LoteRecebimento

### 📅 Sprint 2 (Semana 2 - 9h)
- [ ] **Task 1.3**: Rate Limiting + Retry
- [ ] **Task 2.2-2.3**: Manager + Relação com RecebimentoCompra
- [ ] **Task 3.1-3.2**: Batch processing + Upload ZIP
- [ ] **Task 4.1**: Unit tests SEFAZ

### 📅 Sprint 3 (Semana 3 - 5h)
- [ ] **Task 3.3**: Progress tracking
- [ ] **Task 4.2-4.3**: Integration + E2E tests
- [ ] **Task 5.1-5.3**: Documentação completa
- [ ] [ ] Code review + merge para `main`

---

## 📊 Checklist de Qualidade

- [ ] 8+ testes novos, todos passando
- [ ] Cobertura: `compras/sefaz.py` > 85%
- [ ] Code review aprovado (2 eyeballs)
- [ ] Documentação SOP completa
- [ ] Certificado SEFAZ testado em staging (quasi-produção)
- [ ] Feature flag `FF_SEFAZ_VALIDATION` criada
- [ ] Logs estruturados em `compras.sefaz` channel
- [ ] Migração testada: criar DB nova → migrate → sem erros

---

## ⚙️ Configurações Iniciais Necessárias

```env
# .env
FF_SEFAZ_VALIDATION=False          # Feature flag
SEFAZ_CERT_PATH=/path/to/cert.p12  # Certificado A1
SEFAZ_CERT_PASSWORD=secreto         # Senha do cert
SEFAZ_CACHE_HOURS=24               # Cache de validações
SEFAZ_MAX_RETRIES=4                # Tentativas com backoff
SEFAZ_TIMEOUT_SECONDS=30           # Timeout de conexão
```

---

## 🤝 Dependências Externas

- ✅ **Certificado Digital A1** (SEFAZ exige para auth)
- ✅ **WSDL da SEFAZ** (via portal)
- ✅ **Lib `zeep`** (SOAP client) - `pip install zeep`
- ✅ **Celery + Redis** (já implementado no projeto)

---

## 📍 Status de Bloqueadores

| Bloqueador | Status | Ação |
|-----------|--------|------|
| Cert A1 disponível? | ❓ | Confirmar com DevOps/Admin |
| WSDL SEFAZ documentado? | ❓ | Pesquisar portal.nfe.fazenda.gov.br |
| Staging tem acesso SEFAZ? | ❓ | Verificar firewall/VPN |
| Django env configurado? | ✅ | Pronto |
| DB migrations OK? | ✅ | Pronto |

---

## 📝 Notas Técnicas

### Rate Limiting SEFAZ
- A SEFAZ pode throttle: ~10 req/min por CNPJ
- Solução: Fila com backoff exponencial
- Se muitos rejeitados: esperar 1h, retry

### Cache Strategy
- 24h cache por `(chave_nfe, cnpj_fornecedor)`
- Redis key: `sefaz_validation:{chave}:{cnpj}`
- Manual invalidation se necessário via admin action

### Certificado Digital
- Formato: PKCS#12 (.p12 ou .pfx)
- Senha necessária para desencriptar
- Renovação anual (atentar para validade)

### Multi-Empresa
- Cada empresa pode ter seu certificado
- FK `LoteRecebimento.empresa` garante isolamento
- Flag per-empresa se necessário

---

## ✨ Sucesso Definido

✅ **Quando terminado, você terá:**

1. **Web Service SEFAZ integrado**
   - XMLs validados contra Receita Federal
   - Cache por 24h
   - Retry automático com backoff

2. **Modelo LoteRecebimento**
   - Rastreabilidade: Insumo → Lote → Validade
   - Status claro: validado/pendente/rejeitado

3. **Batch Operations**
   - Upload ZIP com 50+ NF-es
   - Processamento assíncrono
   - Progress tracking em tempo real

4. **Documentação Completa**
   - SOP para operação
   - Troubleshooting guide
   - Diagramas

5. **Testes Robustos**
   - 8+ cenários cobertos
   - Mocks para SEFAZ (não depende de ambiente externo)
   - CI/CD passando 100%

---

**Pronto para kickoff? 🚀**  
Próximo passo: Confirmar pré-requisitos (Certificado SEFAZ + WSDL) e iniciar Sprint 1.
