# Guia Prático: Execução Checklist Homologação Fase 1

**Data**: 02/04/2026  
**Status**: 🔍 Em Execução

---

## 📋 Etapa 1: Verificação de Pré-Requisitos

### 1️⃣ Confirme que o servidor está rodando

```bash
# Em um terminal, vá para a raiz do projeto
cd C:\erp_agricola_novo

# Ative o virtual environment (se não estiver ativo)
.\venv\Scripts\activate

# Inicie o servidor de desenvolvimento
python manage.py runserver
```

**Esperado**: 
```
Starting development server at http://127.0.0.1:8000/
Quit the server with CTRL-BREAK.
```

### 2️⃣ Verifique a Flag de XML Import

Em outro terminal:
```bash
# Verifique se a flag está ativada no .env
grep "FF_COMPRAS_XML_IMPORT" .env
```

**Esperado**: 
```
FF_COMPRAS_XML_IMPORT=True
```

### 3️⃣ Crie dados de teste no banco

```bash
python manage.py shell
```

Cole o código abaixo:

```python
from django.contrib.auth.models import User
from empresas.models import Empresa
from compras.models import Fornecedor, Produto, Categoria, UnidadeMedida, NaturezaOperacao
from administrativo.models import TributacaoFiscal

# Criar empresa de teste (se não existir)
empresa, _ = Empresa.objects.get_or_create(
    nome="EMPRESA TESTE LTDA",
    defaults={
        "cnpj": "11222333000181",
        "estado_padrao": "SP",
    }
)

# Criar usuário comum para testes
user, _ = User.objects.get_or_create(
    username="qa_tester",
    defaults={
        "email": "qa@test.com",
        "is_staff": False,
    }
)
user.empresa = empresa
user.save()

# Criar fornecedor (este é o CNPJ do XML válido)
fornecedor, _ = Fornecedor.objects.get_or_create(
    cnpj="35088122662099",
    defaults={
        "nome_fornecedor": "TRANSPORTADORA ABC LTDA",
        "empresa": empresa,
    }
)

# Criar categoria, unidade de medida
categoria, _ = Categoria.objects.get_or_create(
    nome="Lubrificantes",
    empresa=empresa
)

unidade, _ = UnidadeMedida.objects.get_or_create(
    nome="Litro",
    sigla="L"
)

# Criar produto de teste
produto, _ = Produto.objects.get_or_create(
    descricao="Óleo de Motor 5L",
    empresa=empresa,
    defaults={
        "categoria": categoria,
        "ncm": 27101241,
    }
)

print("✅ Dados de teste criados com sucesso!")
print(f"   - Empresa: {empresa.nome}")
print(f"   - Usuário: {user.username}")
print(f"   - Fornecedor: {fornecedor.nome_fornecedor}")
print(f"   - Produto: {produto.descricao}")
exit()
```

**Esperado**: 
```
✅ Dados de teste criados com sucesso!
   - Empresa: EMPRESA TESTE LTDA
   - Usuário: qa_tester
   - Fornecedor: TRANSPORTADORA ABC LTDA
   - Produto: Óleo de Motor 5L
```

---

## 🧪 Etapa 2: Executar Testes (Teste 1 a 3)

### Teste 1: Feature Flag Visível

1. Abra no navegador: `http://localhost:8000/admin/` → Login
   - Usuário: `qa_tester` (ou admin se fez login antes)
   - Senha: [conforme seu setup]

2. Navegue para: `http://localhost:8000/compras/entrada-direta-nf/`

**Validação**:
- ✅ Página carrega sem erro 500
- ✅ Existe seção/botão de "Upload de XML"
- ✅ Se flag OFF, elemento estaria oculto (mas está ON, então visível)

**Resultado do Teste 1**: ☐ PASS / ☐ FAIL

---

### Teste 2: Upload XML Válido

1. Na página de entrada-direta, selecione arquivo:
   ```
   docs/fase1/nfe_samples/nfe_valid_simp.xml
   ```

2. Clique em **"Extrair XML"** ou **"Importar"**

3. **Aguarde** 2-5 segundos

**Validação Esperada**:
- ✅ Sem erro 500 (se houver, veja seção "Troubleshooting")
- ✅ Mensagem de sucesso: "XML extraído com sucesso" (ou similar)
- ✅ Preview com campos preenchidos:
  - NF Número: `123456`
  - Série: `1`
  - Fornecedor: `TRANSPORTADORA ABC LTDA`
  - Data: `02/04/2026`
  - Valor Total: `R$ 1.500,00`
  - Item 1: Óleo de Motor 5L | 100 un | R$ 15.00
- ✅ Botão **Salvar** disponível
- ✅ Botão **Cancelar** disponível

**Se passar, prossiga ao Teste 3. Se falhar, veja Troubleshooting.**

**Resultado do Teste 2**: ☐ PASS / ☐ FAIL

---

### Teste 3: Detect Duplicação

1. **Clique Cancelar** para voltar ao upload
2. **Selecione o MESMO arquivo** (nfe_valid_simp.xml)
3. **Clique Extrair XML**

**Validação Esperada**:
- ✅ Erro exibido: "Esta NF-e já foi importada" ou "Duplicata detectada"
- ✅ Sistema oferece opção: "Edite o número ou revisar registro"
- ✅ Sem exception 500

**Resultado do Teste 3**: ☐ PASS / ☐ FAIL

---

## 🔧 Troubleshooting

### ❌ Erro 500 no upload

**Passo 1**: Verifique o console do servidor
```
# Na janela de terminal onde rodou 'python manage.py runserver'
# Procure por erro de stack trace
```

**Passo 2**: Verificar permissões do usuário
```python
# No shell Django
user = User.objects.get(username='qa_tester')
print(user.has_perm('compras.add_recebimentocompra'))
# Deve ser True
```

**Passo 3**: Verificar se parser funciona
```python
from compras.nfe_parser import parse_nfe_xml

xml_content = open('docs/fase1/nfe_samples/nfe_valid_simp.xml', 'r').read()
result = parse_nfe_xml(xml_content)
print(result)
# Debe mostrar dicionário com dados extraídos
```

### ❌ Arquivo não encontra fornecedor

Se fornecedor não foi criado na etapa de pré-requisitos, volte e execute:
```python
from compras.models import Fornecedor
from empresas.models import Empresa

empresa = Empresa.objects.get(nome="EMPRESA TESTE LTDA")
fornecedor, _ = Fornecedor.objects.get_or_create(
    cnpj="35088122662099",
    defaults={
        "nome_fornecedor": "TRANSPORTADORA ABC LTDA",
        "empresa": empresa,
    }
)
```

---

## 📊 Checklist de Progresso

### Etapa 1: Pré-requisitos
- [ ] Servidor rodando
- [ ] Flag ativada
- [ ] Dados de teste criados

### Etapa 2: Testes Básicos
- [ ] Teste 1: Feature Flag Visível - PASS
- [ ] Teste 2: Upload XML Válido - PASS
- [ ] Teste 3: Duplicação Detectada - PASS

### Próximos Passos
- [ ] Teste 4-10: Testes funcionais (formulário, BD)
- [ ] Teste 11-14: Testes integração (performance, logging)
- [ ] Teste 15-17: Testes segurança (XSS, CSRF, perms)

---

## ⏱️ Tempo Estimado por Etapa

| Etapa | Testes | Tempo |
|-------|--------|-------|
| 1. Setup | Pre-req | 15 min |
| 2. Básicos | 1-3 | 20 min |
| 3. Funcionais | 4-10 | 45 min |
| 4. Integração | 11-14 | 30 min |
| 5. Segurança | 15-17 | 30 min |
| **TOTAL** | **1-17** | **~2h 20 min** |

---

## 📝 Notas Importantes

1. **Entre testes**, limpe o cache se necessário:
   ```bash
   python manage.py clear_cache
   ```

2. **Se começar nova sessão**, defina usuário em nova aba:
   ```
   http://localhost:8000/admin/
   # Login novamente
   ```

3. **Artifacts de teste** estão em:
   - XMLs válidos: `docs/fase1/nfe_samples/nfe_valid_simp.xml`
   - XMLs inválidos: `docs/fase1/nfe_samples/nfe_invalid.xml`
   - XMLs fornecedor novo: `docs/fase1/nfe_samples/nfe_fornecedor_novo.xml`

---

**Próximo passo**: Confirme que completou Etapa 1 (pré-requisitos) e comece Etapa 2 (testes básicos).

👉 **Imediatamente após completar os 3 testes básicos, escreva em português:**
```
✅ Testes 1-3: PASS (ou descreva qualquer FAIL encontrado)
```
