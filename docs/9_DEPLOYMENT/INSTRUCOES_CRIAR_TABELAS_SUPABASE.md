# 🗄️ INSTRUÇÕES: Como Criar Tabelas no Supabase

## ⚠️ IMPORTANTE
As tabelas criadas localmente estão em SQLite apenas. O Supabase ainda está vazio.
Você precisa executar o SQL **manualmente** no dashboard Supabase.

---

## 📋 PASSO A PASSO

### 1️⃣ Acesse o SQL Editor do Supabase

**URL:** https://supabase.com/dashboard/project/aycjmeeteinbjvqnrycj/editor

Ou:
1. Vá para https://supabase.com/dashboard
2. Selecione seu projeto
3. Clique em **"SQL Editor"** (menu esquerdo)

### 2️⃣ Copie o SQL Completo

Arquivo: `core/supabase_migration_complete.sql`

**Conteúdo principal:**
```sql
-- TABELA 1: Auditoria de Logins
CREATE TABLE IF NOT EXISTS public.usuarios_loginsupabase (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(254) NOT NULL,
    origem VARCHAR(20) NOT NULL,
    sucesso BOOLEAN NOT NULL,
    motivo_falha VARCHAR(100) NOT NULL,
    ip_address INET,
    user_agent VARCHAR(500) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    usuario_id BIGINT REFERENCES public.usuarios_usuario(id) ON DELETE CASCADE
);

-- TABELA 2: Sincronização Django ↔ Supabase
CREATE TABLE IF NOT EXISTS public.usuarios_supabaseusuariosync (
    id BIGSERIAL PRIMARY KEY,
    supabase_uid UUID NOT NULL UNIQUE,
    ultima_sincronizacao TIMESTAMP WITH TIME ZONE NOT NULL,
    sincronizado BOOLEAN NOT NULL,
    erro_sincronizacao TEXT NOT NULL,
    usuario_id BIGINT NOT NULL UNIQUE REFERENCES public.usuarios_usuario(id) ON DELETE CASCADE
);

-- ... (Índices e RLS policies no arquivo completo)
```

### 3️⃣ Cole no SQL Editor

1. No SQL Editor do Supabase
2. Delete qualquer SQL que estejaclar
3. Cole TODO o conteúdo de `core/supabase_migration_complete.sql`
4. Clique no botão **verde "Run"**

### 4️⃣ Verifique no Table Editor

Após executar:
1. Clique em **"Table Editor"** (menu esquerdo)
2. Procure pelas tabelas novas:
   - `usuarios_loginsupabase`
   - `usuarios_supabaseusuariosync`
3. Você também verá RLS **ENABLED** em:
   - usuarios_usuario
   - cadastros_fazenda
   - estoque_armazem
   - compras_solicitacaocompra
   - financeiro_contapagar

---

## 🔧 Se der Erro

### Erro: "relation does not exist"
- Significa que tabelas base (`usuarios_usuario`, etc) não existem
- Você precisa criar PRIMEIRO as tabelas principais
- Use `python manage.py dumpdata` + `python manage.py loaddata` para migrar dados

### Erro: "permission denied"
- Você pode estar usando ANON_KEY em vez de SERVICE_ROLE_KEY
- Solução: Use o dashboard (já autenticado como admin)

### Erro: "syntax error"
- Verifique se todo o conteúdo foi copiado
- Não deixe comentários soltos

---

## ✅ Após Executar

Você terá:
- ✅ 2 tabelas novas para rastreamento de autenticação
- ✅ Índices para performance
- ✅ RLS (Row Level Security) habilitado
- ✅ Políticas de isolamento por empresa (multi-tenancy)
- ✅ Sistema de auditoria funcionando

---

## 📁 Arquivo SQL Completo
Local: **c:\erp_agricola\core\supabase_migration_complete.sql**

Copie e cole este arquivo inteiro no SQL Editor.

---

## 🎯 Próxima Etapa
Após criar as tabelas:
1. Teste o login: `python manage.py runserver`
2. Acesse: http://localhost:8000/auth/login-page/
3. Tente registrar uma conta
4. Verifique se os dados aparecem em Supabase → Table Editor
