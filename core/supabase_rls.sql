-- ═══════════════════════════════════════════════════════════
-- RLS POLICIES - ISOLAMENTO POR TENANT (EMPRESA)
-- Colt este script no SQL Editor do Supabase e execute
-- ═══════════════════════════════════════════════════════════

-- POLÍTICA 1: Usuários veem apenas dados da sua empresa
CREATE POLICY "usuarios_view_own_empresa"
  ON public.usuarios_usuario
  FOR SELECT
  USING (empresa_id = (auth.jwt() ->> 'empresa_id')::int OR auth.jwt() ->> 'tipo' = 'SUPERADMIN');

-- POLÍTICA 2: Admin da empresa pode atualizar seus usuários
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

-- POLÍTICA 3: Isolamento de dados de cadastro por empresa
CREATE POLICY "isolar_cadastros_por_empresa"
  ON public.cadastros_fazenda
  USING (empresa_id = (auth.jwt() ->> 'empresa_id')::int OR auth.jwt() ->> 'tipo' = 'SUPERADMIN');

-- POLÍTICA 4: Isolamento de estoque por empresa
CREATE POLICY "isolar_estoque_por_empresa"
  ON public.estoque_armazem
  USING (empresa_id = (auth.jwt() ->> 'empresa_id')::int OR auth.jwt() ->> 'tipo' = 'SUPERADMIN');

-- POLÍTICA 5: Isolamento de compras por empresa
CREATE POLICY "isolar_compras_por_empresa"
  ON public.compras_solicitacaocompra
  USING (empresa_id = (auth.jwt() ->> 'empresa_id')::int OR auth.jwt() ->> 'tipo' = 'SUPERADMIN');

-- POLÍTICA 6: Isolamento de financeiro por empresa
CREATE POLICY "isolar_financeiro_por_empresa"
  ON public.financeiro_contapagar
  USING (empresa_id = (auth.jwt() ->> 'empresa_id')::int OR auth.jwt() ->> 'tipo' = 'SUPERADMIN');

-- ═══════════════════════════════════════════════════════════
-- ATIVAR RLS (Row Level Security)
-- ═══════════════════════════════════════════════════════════

ALTER TABLE public.usuarios_usuario ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cadastros_fazenda ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.estoque_armazem ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.compras_solicitacaocompra ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.financeiro_contapagar ENABLE ROW LEVEL SECURITY;

-- ═══════════════════════════════════════════════════════════
-- NOTAS:
-- 1. Cade usuário autenticado terá acesso apenas aos dados
--    da sua empresa (isolamento multi-tenancy)
-- 2. Superadmin/SUPERADMIN pode ver tudo
-- 3. Adicione policies similares para outras tabelas
-- 4. O JWT contém: empresa_id, tipo, user_id
-- ═══════════════════════════════════════════════════════════
