# ⚡ GUIA RÁPIDO DE INTEGRAÇÃO COM ERP

## 📍 SUA SITUAÇÃO

✅ Você tem: **Sistema ERP agrisdatav1** em funcionamento  
✅ Você quer: Integrar módulo Packing ao ERP existente  
✅ Você tem: Documentação Packing completa  

---

## 🎯 PRÓXIMOS PASSOS CONCRETOS

### **PASSO 1: Decidir Arquitetura (5 min)**

```
Sua escolha:

[ ] Standalone (Sistema Packing independente)
    └─ Segue guia normal (3_PROMPT_COMPLETO.md)
    └─ Próprio banco, usuários, autenticação
    
[✓] Integrado ao ERP (RECOMENDADO)
    └─ Expandir módulo /embalagem/ existente
    └─ Reutilizar User, Produto, Funcionário
    └─ Multi-tenant por Empresa
    └─ APIs compartilhadas
```

---

### **PASSO 2: Estudar ERP Existente (1 hora)**

```bash
# 1. Clonar
git clone https://github.com/sueldoserafim/agrisdatav1.git
cd agrisdatav1

# 2. Estudar estrutura
ls -la embalagem/          # Módulo já existe!
cat embalagem/models.py    # Ver o que já há
cat embalagem/views.py     # Ver funcionalidades

# 3. Entender multi-tenant
cat core/middleware.py     # Como funciona isolamento por Empresa
cat usuarios/models.py     # Roles e permissões

# 4. Listar modelos principais
cat cadastros/models.py    # Produto, Empresa, etc
cat rh/models.py           # Funcionário
cat estoque/models.py      # MovimentacaoEstoque
```

---

### **PASSO 3: Ler Guia de Integração (30 min)**

**Arquivo:** `INTEGRACAO_ERP_AGRISDATAV1.md`

**Seções chave:**
1. Passo 1: Estrutura de pastas
2. Passo 2: Mapeamento de Dados (tabela importante!)
3. Passo 3: Integração com fluxo ERP
4. Passo 4: Autenticação & Permissões
5. Passo 5: Criar Views/Templates
6. Passo 6: Settings.py adaptado
7. Passo 7: Migração de dados
8. Passo 8: Testes

---

### **PASSO 4: Preparar Ambiente (30 min)**

```bash
# 1. Clonar seu repo de packing (se houver)
git clone <seu-repo-packing> packing_temp

# 2. Criar branch para integração
cd agrisdatav1
git checkout -b feature/packing-expanded

# 3. Instalar deps (se necessário)
pip install -r requirements.txt

# 4. Verificar banco
python manage.py dbshell  # Testar conexão

# 5. Ver estrutura atual
python manage.py inspectdb | head -50
```

---

### **PASSO 5: Implementar Passo a Passo (5-10 dias)**

**Usar Checklist customizado:**

```
FASE ERP: INTEGRAÇÃO (do CHECKLIST)

[ ] Fase 1: Expandir models.py do /embalagem/
    └─ OrdemEmbalagem (com Empresa, Funcionário, Produto)
    └─ Romaneio
    └─ ConfiguracaoEmbalagem
    
[ ] Fase 2: Criar views e templates
    └─ Dashboard
    └─ Registrar embalagem
    └─ Relatórios
    
[ ] Fase 3: Criar APIs REST
    └─ GET /api/embalagem/ordens/
    └─ POST /api/embalagem/ordens/
    └─ PUT /api/embalagem/ordens/{id}/
    
[ ] Fase 4: Testes e validação
    └─ Testar multi-tenant
    └─ Testar autenticação
    └─ Testar fluxo: Venda → Embalagem → NF-e
    
[ ] Fase 5: Deploy
    └─ Migrations
    └─ Commit & Push
    └─ Deploy em produção
```

---

## 🗺️ MAPEAMENTO RÁPIDO

### O que você TEM no seu Packing

| Modelo | Campo | O que fazer |
|--------|-------|------------|
| **User** | id, email, nome, perfil | ❌ REMOVER - Usar User do ERP |
| **Cultura** | id, nome, descricao | ↔️ MAPEAR para Produto do ERP |
| **Embalador** | id, nome, codigo_barra | ↔️ MAPEAR para Funcionário do ERP |
| **Producao** | quantidade, turno, data | ↔️ RENOMEAR para OrdemEmbalagem |

### O que USAR do ERP

| Modelo ERP | Para que | Status |
|------------|----------|--------|
| **User** (usuarios/) | Autenticação, permissões | ✅ Usar direto |
| **Produto** (produtos/) | Culturas | ✅ Usar direto |
| **Funcionário** (rh/) | Embaladores | ✅ Usar direto |
| **Empresa** (empresas/) | Multi-tenant | ✅ Adicionar em tudo |
| **MovimentacaoEstoque** (estoque/) | Integrar estoque | ✅ Usar se necessário |

---

## 📝 CHECKLIST RÁPIDO

- [ ] Estudei agrisdatav1 no GitHub
- [ ] Entendi que /embalagem/ já existe
- [ ] Li INTEGRACAO_ERP_AGRISDATAV1.md completamente
- [ ] Criei branch feature/packing-expanded
- [ ] Expandi models.py com OrdemEmbalagem
- [ ] Mapeei User → ERP User, Cultura → Produto, etc
- [ ] Criei views customizadas
- [ ] Testeique com dados do ERP
- [ ] Rodei migrations
- [ ] Testei multi-tenant
- [ ] Testei autenticação
- [ ] Fiz deploy em produção

---

## 🔗 ARQUIVOS IMPORTANTES

| Arquivo | Por que | Tempo |
|---------|--------|-------|
| `INTEGRACAO_ERP_AGRISDATAV1.md` | Guia técnico completo | 30 min |
| `3_PROMPT_COMPLETO.md` | Referência código patterns | 40 min |
| `6_CHECKLIST_IMPLEMENTACAO.md` | Fase ERP específica | 10 min |
| `7_FLUXOS_SISTEMA.md` | Entender fluxo de dados | 30 min |
| `4_CODIGO_PRONTO.md` | Copiar/adaptar código | On-demand |
| `5_QUICK_REFERENCE.md` | Lookup rápido | On-demand |

---

## ⚠️ ARMADILHAS COMUNS

| ⚠️ Armadilha | ✅ Solução |
|------------|----------|
| Criar novo User em vez de usar ERP | Use User do ERP direto em todos os forms |
| Esquecer campo `empresa` em models | Sempre adicionar: `empresa = ForeignKey('empresas.Empresa')` |
| Usar UUID em vez de BigAutoField | Use BigAutoField (padrão ERP) |
| Não isolar por tenant | Sempre filtrar por `empresa` em todas as queries |
| Criar autenticação própria | Use SimpleJWT do ERP |
| Duplicar Produtos/Funcionários | Use FK aos existentes, não copie |
| Não testar multi-tenant | Testar com 2+ empresas antes de deploy |

---

## 🎓 LEARNING PATH

```
1. Leia este arquivo (5 min) ✅
2. Leia INTEGRACAO_ERP_AGRISDATAV1.md (30 min)
3. Estude código /embalagem/ no agrisdatav1 (1 hora)
4. Crie branch e comece Phase ERP do CHECKLIST
5. Pedir revisão antes de deploy
```

---

## 📞 DÚVIDAS?

Consulte:
- **Multi-tenant:** INTEGRACAO_ERP_AGRISDATAV1.md → Passo 4
- **Autenticação:** INTEGRACAO_ERP_AGRISDATAV1.md → Passo 4
- **Modelos:** INTEGRACAO_ERP_AGRISDATAV1.md → Passo 2
- **Views:** 4_CODIGO_PRONTO.md → Views examples
- **Fluxo:** 7_FLUXOS_SISTEMA.md → Fluxogramas

---

**Status:** 🟢 Pronto para Implementação  
**Data:** 01/07/2026  
**Próximo:** Criar branch feature/packing-expanded e começar Fase ERP
