-- ═══════════════════════════════════════════════════════════════════════════════════
-- SUPABASE SCHEMA MIGRATION
-- Crie estas tabelas no SQL Editor do Supabase: https://supabase.com/dashboard
-- Cole este script completo e execute
-- ═══════════════════════════════════════════════════════════════════════════════════

-- TABELA 1: LoginSupabase (Auditoria de logins)
-- Registra todos os acessos (sucesso/falha) com IP e user-agent
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

-- TABELA 2: SupabaseUsuarioSync (Bridge Django ↔ Supabase)
-- Mapeia usuários Django com UIDs do Supabase
CREATE TABLE IF NOT EXISTS public.usuarios_supabaseusuariosync (
    id BIGSERIAL PRIMARY KEY,
    supabase_uid UUID NOT NULL UNIQUE,
    ultima_sincronizacao TIMESTAMP WITH TIME ZONE NOT NULL,
    sincronizado BOOLEAN NOT NULL,
    erro_sincronizacao TEXT NOT NULL,
    usuario_id BIGINT NOT NULL UNIQUE REFERENCES public.usuarios_usuario(id) ON DELETE CASCADE
);

-- ═══════════════════════════════════════════════════════════════════════════════════
-- ÍNDICES (Para performance)
-- ═══════════════════════════════════════════════════════════════════════════════════

-- Índices LoginSupabase
CREATE INDEX IF NOT EXISTS usuarios_loginsupabase_timestamp_idx 
    ON public.usuarios_loginsupabase(timestamp DESC);

CREATE INDEX IF NOT EXISTS usuarios_loginsupabase_usuario_id_idx 
    ON public.usuarios_loginsupabase(usuario_id DESC);

CREATE INDEX IF NOT EXISTS usuarios_loginsupabase_email_timestamp_idx 
    ON public.usuarios_loginsupabase(email, timestamp DESC);

CREATE INDEX IF NOT EXISTS usuarios_loginsupabase_usuario_timestamp_idx 
    ON public.usuarios_loginsupabase(usuario_id, timestamp DESC);

-- Índices SupabaseUsuarioSync
CREATE INDEX IF NOT EXISTS usuarios_supabaseusuariosync_ultima_sincronizacao_idx 
    ON public.usuarios_supabaseusuariosync(ultima_sincronizacao DESC);

CREATE INDEX IF NOT EXISTS usuarios_supabaseusuariosync_usuario_idx 
    ON public.usuarios_supabaseusuariosync(usuario_id, ultima_sincronizacao DESC);

CREATE INDEX IF NOT EXISTS usuarios_supabaseusuariosync_supabase_uid_idx 
    ON public.usuarios_supabaseusuariosync(supabase_uid);

-- ═══════════════════════════════════════════════════════════════════════════════════
-- RLS POLICIES - ISOLAMENTO POR TENANT (EMPRESA)
-- ═══════════════════════════════════════════════════════════════════════════════════

-- HABILITAR RLS
ALTER TABLE public.usuarios_loginsupabase ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.usuarios_supabaseusuariosync ENABLE ROW LEVEL SECURITY;

-- POLÍTICA 1: LoginSupabase - Usuários veem apenas seus logins ou admin vê todos
CREATE POLICY "loginsupabase_view_own_or_admin"
  ON public.usuarios_loginsupabase
  FOR SELECT
  USING (
    usuario_id = (auth.jwt() ->> 'user_id')::bigint 
    OR auth.jwt() ->> 'tipo' = 'SUPERADMIN'
  );

-- POLÍTICA 2: SupabaseUsuarioSync - Apenas admin pode ler
CREATE POLICY "supabaseusuariosync_view_admin_only"
  ON public.usuarios_supabaseusuariosync
  FOR SELECT
  USING (
    auth.jwt() ->> 'tipo' = 'SUPERADMIN'
  );

-- POLÍTICA 3: Permitir insert de LoginSupabase (auditoria)
CREATE POLICY "loginsupabase_insert_all"
  ON public.usuarios_loginsupabase
  FOR INSERT
  WITH CHECK (true);

-- POLÍTICA 4: Permitir insert de SupabaseUsuarioSync
CREATE POLICY "supabaseusuariosync_insert_all"
  ON public.usuarios_supabaseusuariosync
  FOR INSERT
  WITH CHECK (true);

-- ═══════════════════════════════════════════════════════════════════════════════════
-- POLITICAS PRINCIPAIS (Tabelas Existentes)
-- ═══════════════════════════════════════════════════════════════════════════════════

-- Habilitar RLS em tabelas principales
ALTER TABLE public.usuarios_usuario ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cadastros_fazenda ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.estoque_armazem ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.compras_solicitacaocompra ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.financeiro_contapagar ENABLE ROW LEVEL SECURITY;

-- POLÍTICA: Usuários veem apenas dados da sua empresa
DROP POLICY IF EXISTS "usuarios_view_own_empresa" ON public.usuarios_usuario;
CREATE POLICY "usuarios_view_own_empresa"
  ON public.usuarios_usuario
  FOR SELECT
  USING (empresa_id = (auth.jwt() ->> 'empresa_id')::int OR auth.jwt() ->> 'tipo' = 'SUPERADMIN');

-- POLÍTICA: Admin gerencia usuários da sua empresa
DROP POLICY IF EXISTS "admin_manage_company_users" ON public.usuarios_usuario;
CREATE POLICY "admin_manage_company_users"
  ON public.usuarios_usuario
  FOR UPDATE
  USING (
    (auth.jwt() ->> 'empresa_id')::int = empresa_id 
    AND ((auth.jwt() ->> 'tipo') = 'ADMIN' OR auth.jwt() ->> 'tipo' = 'SUPERADMIN')
  )
  WITH CHECK (
    (auth.jwt() ->> 'empresa_id')::int = empresa_id
  );

-- POLÍTICA: Isolamento cadastros por empresa
DROP POLICY IF EXISTS "isolar_cadastros_por_empresa" ON public.cadastros_fazenda;
CREATE POLICY "isolar_cadastros_por_empresa"
  ON public.cadastros_fazenda
  FOR SELECT
  USING (empresa_id = (auth.jwt() ->> 'empresa_id')::int OR auth.jwt() ->> 'tipo' = 'SUPERADMIN');

-- POLÍTICA: Isolamento estoque por empresa
DROP POLICY IF EXISTS "isolar_estoque_por_empresa" ON public.estoque_armazem;
CREATE POLICY "isolar_estoque_por_empresa"
  ON public.estoque_armazem
  FOR SELECT
  USING (empresa_id = (auth.jwt() ->> 'empresa_id')::int OR auth.jwt() ->> 'tipo' = 'SUPERADMIN');

-- POLÍTICA: Isolamento compras por empresa
DROP POLICY IF EXISTS "isolar_compras_por_empresa" ON public.compras_solicitacaocompra;
CREATE POLICY "isolar_compras_por_empresa"
  ON public.compras_solicitacaocompra
  FOR SELECT
  USING (empresa_id = (auth.jwt() ->> 'empresa_id')::int OR auth.jwt() ->> 'tipo' = 'SUPERADMIN');

-- POLÍTICA: Isolamento financeiro por empresa
DROP POLICY IF EXISTS "isolar_financeiro_por_empresa" ON public.financeiro_contapagar;
CREATE POLICY "isolar_financeiro_por_empresa"
  ON public.financeiro_contapagar
  FOR SELECT
  USING (empresa_id = (auth.jwt() ->> 'empresa_id')::int OR auth.jwt() ->> 'tipo' = 'SUPERADMIN');

-- ═══════════════════════════════════════════════════════════════════════════════════
-- CONFIRMAÇÃO
-- ═══════════════════════════════════════════════════════════════════════════════════
-- ✅ Tabelas `usuarios_loginsupabase` e `usuarios_supabaseusuariosync` criadas
-- ✅ Índices criados para performance
-- ✅ RLS habilitado em todas as tabelas
-- ✅ Políticas de segurança aplicadas
-- ✅ Multi-tenancy por empresa_id configurado
-- ═══════════════════════════════════════════════════════════════════════════════════
