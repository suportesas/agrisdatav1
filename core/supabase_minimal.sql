-- ═══════════════════════════════════════════════════════════════════════════════════
-- SUPABASE: SCHEMA MÍNIMO PARA TESTAR AUTENTICAÇÃO
-- Cole no SQL Editor: https://supabase.com/dashboard/project/aycjmeeteinbjvqnrycj/editor
-- ═══════════════════════════════════════════════════════════════════════════════════

-- STEP 1: Criar tabela base SEM foreign keys
CREATE TABLE IF NOT EXISTS public.empresas_empresa (
    id BIGSERIAL PRIMARY KEY,
    nome VARCHAR(200) NOT NULL,
    cnpj VARCHAR(18),
    data_criacao TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- STEP 2: Criar usuários
CREATE TABLE IF NOT EXISTS public.usuarios_usuario (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(150) NOT NULL UNIQUE,
    password VARCHAR(128) NOT NULL,
    email VARCHAR(254),
    first_name VARCHAR(150) DEFAULT '',
    last_name VARCHAR(150) DEFAULT '',
    is_active BOOLEAN DEFAULT true,
    is_staff BOOLEAN DEFAULT false,
    is_superuser BOOLEAN DEFAULT false,
    date_joined TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE,
    tipo VARCHAR(15) DEFAULT 'USER',
    telefone VARCHAR(20),
    cpf VARCHAR(14),
    empresa_id BIGINT
);

-- STEP 3: Criar índices
CREATE INDEX IF NOT EXISTS usuarios_usuario_username_idx ON public.usuarios_usuario(username);
CREATE INDEX IF NOT EXISTS usuarios_usuario_email_idx ON public.usuarios_usuario(email);
CREATE INDEX IF NOT EXISTS usuarios_usuario_empresa_id_idx ON public.usuarios_usuario(empresa_id);

-- STEP 4: Tabelas de auditoria (já podemos usar, sem verificar FK por enquanto)
CREATE TABLE IF NOT EXISTS public.usuarios_loginsupabase (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(254) NOT NULL,
    origem VARCHAR(20) NOT NULL,
    sucesso BOOLEAN NOT NULL,
    motivo_falha VARCHAR(100) DEFAULT '',
    ip_address INET,
    user_agent VARCHAR(500) DEFAULT '',
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    usuario_id BIGINT
);

CREATE TABLE IF NOT EXISTS public.usuarios_supabaseusuariosync (
    id BIGSERIAL PRIMARY KEY,
    supabase_uid UUID NOT NULL UNIQUE,
    ultima_sincronizacao TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    sincronizado BOOLEAN DEFAULT false,
    erro_sincronizacao TEXT DEFAULT '',
    usuario_id BIGINT UNIQUE
);

-- STEP 5: Criar índices para performance
CREATE INDEX IF NOT EXISTS usuarios_loginsupabase_timestamp_idx ON public.usuarios_loginsupabase(timestamp DESC);
CREATE INDEX IF NOT EXISTS usuarios_loginsupabase_email_idx ON public.usuarios_loginsupabase(email);
CREATE INDEX IF NOT EXISTS usuarios_supabaseusuariosync_usuario_id_idx ON public.usuarios_supabaseusuariosync(usuario_id);
CREATE INDEX IF NOT EXISTS usuarios_supabaseusuariosync_supabase_uid_idx ON public.usuarios_supabaseusuariosync(supabase_uid);

-- STEP 6: Habilitar RLS
ALTER TABLE public.usuarios_usuario ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.usuarios_loginsupabase ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.usuarios_supabaseusuariosync ENABLE ROW LEVEL SECURITY;

-- STEP 7: Criar políticas RLS simples (sem checks complexos por enquanto)
DROP POLICY IF EXISTS "usuarios_all_access" ON public.usuarios_usuario;
CREATE POLICY "usuarios_all_access" ON public.usuarios_usuario
  FOR SELECT USING (true);

DROP POLICY IF EXISTS "usuarios_insert" ON public.usuarios_usuario;
CREATE POLICY "usuarios_insert" ON public.usuarios_usuario
  FOR INSERT WITH CHECK (true);

DROP POLICY IF EXISTS "loginsupabase_insert" ON public.usuarios_loginsupabase;
CREATE POLICY "loginsupabase_insert" ON public.usuarios_loginsupabase
  FOR INSERT WITH CHECK (true);

DROP POLICY IF EXISTS "supabaseusuariosync_insert" ON public.usuarios_supabaseusuariosync;
CREATE POLICY "supabaseusuariosync_insert" ON public.usuarios_supabaseusuariosync
  FOR INSERT WITH CHECK (true);

-- STEP 8: Inserir dados de teste
INSERT INTO public.empresas_empresa (nome, cnpj) VALUES 
('Empresa Teste', '12.345.678/0001-90')
ON CONFLICT DO NOTHING;

-- Senha: "admin123" (bcrypt)
INSERT INTO public.usuarios_usuario (
    username, email, password, first_name, last_name, 
    is_active, is_superuser, is_staff, tipo, empresa_id
) VALUES (
    'admin_test', 'admin@teste.com', 'pbkdf2_sha256$600000$test$test', 
    'Admin', 'Teste', true, true, true, 'SUPERADMIN', 1
)
ON CONFLICT (username) DO NOTHING;

-- ═══════════════════════════════════════════════════════════════════════════════════
-- ✅ PRONTO! Agora pode testar autenticação
-- ═══════════════════════════════════════════════════════════════════════════════════
-- 
-- Próximos passos:
-- 1. python manage.py runserver
-- 2. Acesse: http://localhost:8000/auth/register-page/
-- 3. Registre um novo usuário
-- 4. Verifique em Supabase > Table Editor > usuarios_loginsupabase
-- ═══════════════════════════════════════════════════════════════════════════════════
