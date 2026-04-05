-- ═══════════════════════════════════════════════════════════════════════════════════
-- SUPABASE: Criar Tabelas + RLS para Autenticação
-- Cole este script no SQL Editor: https://supabase.com/dashboard/project/aycjmeeteinbjvqnrycj/editor
-- ═══════════════════════════════════════════════════════════════════════════════════

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

-- Índices (Performance)
CREATE INDEX IF NOT EXISTS usuarios_loginsupabase_timestamp_idx ON public.usuarios_loginsupabase(timestamp DESC);
CREATE INDEX IF NOT EXISTS usuarios_loginsupabase_usuario_id_idx ON public.usuarios_loginsupabase(usuario_id DESC);
CREATE INDEX IF NOT EXISTS usuarios_loginsupabase_email_timestamp_idx ON public.usuarios_loginsupabase(email, timestamp DESC);
CREATE INDEX IF NOT EXISTS usuarios_supabaseusuariosync_ultima_sincronizacao_idx ON public.usuarios_supabaseusuariosync(ultima_sincronizacao DESC);
CREATE INDEX IF NOT EXISTS usuarios_supabaseusuariosync_usuario_idx ON public.usuarios_supabaseusuariosync(usuario_id, ultima_sincronizacao DESC);
CREATE INDEX IF NOT EXISTS usuarios_supabaseusuariosync_supabase_uid_idx ON public.usuarios_supabaseusuariosync(supabase_uid);

-- Habilitar RLS (Row Level Security)
ALTER TABLE public.usuarios_loginsupabase ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.usuarios_supabaseusuariosync ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.usuarios_usuario ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cadastros_fazenda ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.estoque_armazem ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.compras_solicitacaocompra ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.financeiro_contapagar ENABLE ROW LEVEL SECURITY;

-- ═══════════════════════════════════════════════════════════════════════════════════
-- RLS POLICIES (Selects novas tabelas)
-- ═══════════════════════════════════════════════════════════════════════════════════

-- Tabela: usuarios_loginsupabase
DROP POLICY IF EXISTS "loginsupabase_view_own_or_admin" ON public.usuarios_loginsupabase;
CREATE POLICY "loginsupabase_view_own_or_admin"
  ON public.usuarios_loginsupabase
  FOR SELECT
  USING (usuario_id = (auth.jwt() ->> 'user_id')::bigint OR auth.jwt() ->> 'tipo' = 'SUPERADMIN');

DROP POLICY IF EXISTS "loginsupabase_insert_all" ON public.usuarios_loginsupabase;
CREATE POLICY "loginsupabase_insert_all"
  ON public.usuarios_loginsupabase
  FOR INSERT
  WITH CHECK (true);

-- Tabela: usuarios_supabaseusuariosync
DROP POLICY IF EXISTS "supabaseusuariosync_view_admin_only" ON public.usuarios_supabaseusuariosync;
CREATE POLICY "supabaseusuariosync_view_admin_only"
  ON public.usuarios_supabaseusuariosync
  FOR SELECT
  USING (auth.jwt() ->> 'tipo' = 'SUPERADMIN');

DROP POLICY IF EXISTS "supabaseusuariosync_insert_all" ON public.usuarios_supabaseusuariosync;
CREATE POLICY "supabaseusuariosync_insert_all"
  ON public.usuarios_supabaseusuariosync
  FOR INSERT
  WITH CHECK (true);

-- ═══════════════════════════════════════════════════════════════════════════════════
-- RLS POLICIES (Tabelas existentes - Isolamento por empresa)
-- ═══════════════════════════════════════════════════════════════════════════════════

-- Tabela: usuarios_usuario
DROP POLICY IF EXISTS "usuarios_view_own_empresa" ON public.usuarios_usuario;
CREATE POLICY "usuarios_view_own_empresa"
  ON public.usuarios_usuario
  FOR SELECT
  USING (empresa_id = (auth.jwt() ->> 'empresa_id')::int OR auth.jwt() ->> 'tipo' = 'SUPERADMIN');

DROP POLICY IF EXISTS "admin_manage_company_users" ON public.usuarios_usuario;
CREATE POLICY "admin_manage_company_users"
  ON public.usuarios_usuario
  FOR UPDATE
  USING ((auth.jwt() ->> 'empresa_id')::int = empresa_id AND ((auth.jwt() ->> 'tipo') = 'ADMIN' OR auth.jwt() ->> 'tipo' = 'SUPERADMIN'))
  WITH CHECK ((auth.jwt() ->> 'empresa_id')::int = empresa_id);

-- Tabela: cadastros_fazenda
DROP POLICY IF EXISTS "isolar_cadastros_por_empresa" ON public.cadastros_fazenda;
CREATE POLICY "isolar_cadastros_por_empresa"
  ON public.cadastros_fazenda
  FOR SELECT
  USING (empresa_id = (auth.jwt() ->> 'empresa_id')::int OR auth.jwt() ->> 'tipo' = 'SUPERADMIN');

-- Tabela: estoque_armazem
DROP POLICY IF EXISTS "isolar_estoque_por_empresa" ON public.estoque_armazem;
CREATE POLICY "isolar_estoque_por_empresa"
  ON public.estoque_armazem
  FOR SELECT
  USING (empresa_id = (auth.jwt() ->> 'empresa_id')::int OR auth.jwt() ->> 'tipo' = 'SUPERADMIN');

-- Tabela: compras_solicitacaocompra
DROP POLICY IF EXISTS "isolar_compras_por_empresa" ON public.compras_solicitacaocompra;
CREATE POLICY "isolar_compras_por_empresa"
  ON public.compras_solicitacaocompra
  FOR SELECT
  USING (empresa_id = (auth.jwt() ->> 'empresa_id')::int OR auth.jwt() ->> 'tipo' = 'SUPERADMIN');

-- Tabela: financeiro_contapagar
DROP POLICY IF EXISTS "isolar_financeiro_por_empresa" ON public.financeiro_contapagar;
CREATE POLICY "isolar_financeiro_por_empresa"
  ON public.financeiro_contapagar
  FOR SELECT
  USING (empresa_id = (auth.jwt() ->> 'empresa_id')::int OR auth.jwt() ->> 'tipo' = 'SUPERADMIN');

-- ═══════════════════════════════════════════════════════════════════════════════════
-- ✅ FIM - Todas as tabelas e RLS criadas com sucesso!
-- ═══════════════════════════════════════════════════════════════════════════════════
