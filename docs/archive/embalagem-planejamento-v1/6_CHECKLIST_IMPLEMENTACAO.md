# ✅ CHECKLIST DE IMPLEMENTAÇÃO - SISTEMA PACKING DJANGO
## Guia Passo a Passo para Desenvolvimento

---

## FASE 0: PREPARAÇÃO

### Ambiente
- [ ] Python 3.10+ instalado
- [ ] Escolher banco de dados:
  - [ ] **Opção A (Local):** PostgreSQL 13+ instalado e rodando
  - [ ] **Opção B (Nuvem):** Supabase account criado (https://supabase.com)
- [ ] pip/virtualenv disponível
- [ ] Git configurado
- [ ] Editor (VS Code) disponível

### Conhecimento Pré-requisito
- [ ] Conceitos básicos de Django
- [ ] SQL/PostgreSQL básico
- [ ] Git workflow
- [ ] HTML/CSS/Bootstrap 5

---

## ⚠️ FASE ERP: INTEGRAÇÃO COM SISTEMA EXISTENTE (Opcional - Fazer ANTES de Fase 1!)

**APENAS SE você tem um ERP já em funcionamento (como agrisdatav1)**

### Pré-análise
- [ ] Clonar repositório do ERP: `git clone https://github.com/sueldoserafim/agrisdatav1.git`
- [ ] Estudar estrutura de pastas do ERP
- [ ] Verificar módulo `/embalagem/` existente
- [ ] Entender multi-tenant (isolamento por Empresa)
- [ ] Revisar autenticação do ERP (roles, permissões)
- [ ] Listar modelos principais: User, Produto, Funcionário, Empresa
- [ ] Ler `INTEGRACAO_ERP_AGRISDATAV1.md` completamente

### Decisão Estratégica
- [ ] Escolher: Standalone vs Integrado ao ERP
  - [ ] **Standalone:** Usar estas 24 fases normalmente
  - [ ] **Integrado:** Seguir plano especial abaixo

### Se Integrado ao ERP:
- [ ] Criar branch: `git checkout -b feature/packing-expanded`
- [ ] Expandir `/embalagem/models.py`:
  - [ ] Adicionar model OrdemEmbalagem com campos:
    - [ ] `empresa` (ForeignKey → Empresa)
    - [ ] `embalador` (ForeignKey → Funcionário)
    - [ ] `produto` (ForeignKey → Produto)
    - [ ] `quantidade`, `turno`, `data`, `hora`
    - [ ] `valor_bonificacao`, `valor_penalidade` (auto-calculados)
  - [ ] Adicionar model Romaneio:
    - [ ] `codigo_qr`, `pallet_id`, `assinatura`
  - [ ] Adicionar model ConfiguracaoEmbalagem:
    - [ ] Valores de bonificação/penalidade por empresa

- [ ] Mapeamento de dados:
  - [ ] Culturas do Packing → Produtos do ERP
  - [ ] Embaladores do Packing → Funcionários do ERP
  - [ ] Usuários do Packing → Usuários do ERP com roles
  - [ ] Produções do Packing → OrdenséEmbalagem do ERP

- [ ] Criar script de migração:
  - [ ] `embalagem/management/commands/migrar_dados_packing.py`
  - [ ] Testar em banco de teste primeiro
  - [ ] Validar integridade de dados

- [ ] Integração com fluxo existente:
  - [ ] Pedido de Venda → Reserva de Estoque → Ordem de Embalagem → Estoque saída → NF-e
  - [ ] Verificar endpoints de API existentes
  - [ ] Adicionar endpoints necessários em `/api/embalagem/`

- [ ] Autenticação & Permissões:
  - [ ] Remover User model customizado
  - [ ] Usar User do ERP direto
  - [ ] Usar roles do ERP (ADMIN, GERENTE, FUNC, etc)
  - [ ] Adicionar permission_required em views

- [ ] Testes de integração:
  - [ ] [ ] Conectar ao banco do ERP
  - [ ] [ ] Listar Produtos como Culturas
  - [ ] [ ] Listar Funcionários como Embaladores
  - [ ] [ ] Registrar Ordem de Embalagem
  - [ ] [ ] Verificar movimentação de estoque
  - [ ] [ ] Testar multi-tenant (empresa isolation)
  - [ ] [ ] Testar APIs
  - [ ] [ ] Testar relatórios com dados do ERP

- [ ] Deploy:
  - [ ] Fazer migrations do módulo expandido: `python manage.py makemigrations embalagem`
  - [ ] Executar migrations: `python manage.py migrate`
  - [ ] Testar localmente
  - [ ] Fazer commit e push para branch feature
  - [ ] Criar Pull Request
  - [ ] Deploy no mesmo servidor do ERP

---

## FASE 1: SETUP INICIAL (Dia 1)

### Projeto Django
- [ ] Criar pasta do projeto
- [ ] Criar ambiente virtual: `python -m venv venv`
- [ ] Ativar venv: `source venv/bin/activate`
- [ ] Instalar Django: `pip install django`
- [ ] Criar projeto: `django-admin startproject config .`
- [ ] Criar apps:
  - [ ] `python manage.py startapp apps.core`
  - [ ] `python manage.py startapp apps.producao`
  - [ ] `python manage.py startapp apps.relatorio`
  - [ ] `python manage.py startapp apps.api`

### Dependências
- [ ] Criar `requirements.txt` (usar arquivo fornecido)
- [ ] Instalar: `pip install -r requirements.txt`
- [ ] Instalar `dj-database-url` (para Supabase): `pip install dj-database-url`
- [ ] Verificar instalação: `pip list`

### Banco de Dados - Escolha UMA opção:

**Opção A: PostgreSQL Local**
- [ ] Criar banco PostgreSQL: `createdb packing_db`
- [ ] Criar usuário: `createuser -P packing`
- [ ] Dar permissões
- [ ] Configurar `settings.py` com credenciais locais
- [ ] Testar: `python manage.py dbshell`

**Opção B: Supabase (RECOMENDADO)**
- [ ] Acessar https://supabase.com
- [ ] Criar novo projeto
- [ ] Copiar Database URL (postgresql://...)
- [ ] Criar arquivo `.env` com: `DATABASE_URL=postgresql://...`
- [ ] Configurar `settings.py` com `dj_database_url`
- [ ] Testar: `python manage.py dbshell`
- [ ] Configurar DATABASES
- [ ] Configurar INSTALLED_APPS
- [ ] Configurar TEMPLATES
- [ ] Configurar STATIC_ROOT
- [ ] Configurar EMAIL_BACKEND

### Estrutura de Pastas
- [ ] Criar `templates/` na raiz
- [ ] Criar `static/` na raiz
- [ ] Criar `apps/` na raiz
- [ ] Criar `logs/` na raiz
- [ ] Criar `.env.example`
- [ ] Criar `.gitignore`

---

## FASE 2: MODELOS (Dia 2-3)

### apps/core/models.py
- [ ] Criar model User customizado
  - [ ] Fields: id (UUID), email, nome, perfil, ativo, criado_em, modificado_em
  - [ ] Meta: verbose_name, ordering
  - [ ] Methods: __str__, eh_admin, eh_usuario_ativo
  - [ ] Admin registration
- [ ] Testar migration: `python manage.py makemigrations core`
- [ ] Testar migrate: `python manage.py migrate core`

### apps/producao/models.py
- [ ] Criar model Cultura
  - [ ] Fields: nome (unique), descricao, criado_em, modificado_em, modificado_por
  - [ ] Method: pode_deletar()
  - [ ] Indices
- [ ] Criar model Embalador
  - [ ] Fields: nome, codigo_barra (unique), ativo, criado_em, modificado_em, modificado_por
  - [ ] Method: pode_deletar(), properties (producao_total, etc)
  - [ ] Validators (MinLengthValidator)
  - [ ] Indices
- [ ] Criar model Producao
  - [ ] Fields: embalador_id, cultura_id, turno, quantidade, reembalagem, data, hora, valores, criado_por
  - [ ] TURNO_CHOICES
  - [ ] Properties: bonificacao_total, penalidade_total, final_liquido
  - [ ] Static method: calcular_turno()
  - [ ] Constraints (quantidade > 0)
  - [ ] Indices (data, embalador_id, etc)
- [ ] Criar model Configuracao
  - [ ] Fields: valor_bonificacao, valor_penalidade, criado_em, modificado_em, modificado_por
  - [ ] Class method: get_configuracao()
  - [ ] Override save() para garantir única instância

### apps/relatorio/models.py
- [ ] Criar model ConfiguracaoLog
  - [ ] Fields: valores anterior/novo, alterado_por, data_alteracao, motivo
  - [ ] Indices

### Migrations
- [ ] Rodar `python manage.py makemigrations`
- [ ] Rodar `python manage.py migrate`
- [ ] Testar no shell: `python manage.py shell`
  - [ ] Criar instâncias dos modelos
  - [ ] Testar queries
  - [ ] Testar properties

### Admin
- [ ] Registrar User em `core/admin.py`
- [ ] Registrar Cultura em `producao/admin.py`
- [ ] Registrar Embalador em `producao/admin.py`
- [ ] Registrar Producao em `producao/admin.py`
- [ ] Customizar list_display, list_filter, search_fields
- [ ] Testar acesso em `/admin/`

---

## FASE 3: AUTENTICAÇÃO (Dia 4)

### apps/core/forms.py
- [ ] Criar LoginForm
  - [ ] email (EmailField)
  - [ ] senha (CharField with PasswordInput)
  - [ ] clean() method (validar credenciais)
  - [ ] Form styling (form-control classes)
- [ ] Criar CriarUsuarioForm
  - [ ] Fields: first_name, last_name, email, perfil, senha, confirmar_senha
  - [ ] Password validation (8 chars min)
  - [ ] Confirm match check
  - [ ] Bcrypt hashing no save()

### apps/core/views.py
- [ ] Criar CustomLoginView
  - [ ] Herdar de LoginView
  - [ ] Usar LoginForm
  - [ ] form_valid com logging
  - [ ] Redirect para dashboard
- [ ] Criar DashboardView (placeholder)
  - [ ] LoginRequiredMixin
  - [ ] Renderizar template dashboard.html
- [ ] Testar login: acessar `/login/`

### apps/core/urls.py
- [ ] Criar URL patterns
  - [ ] login/ → CustomLoginView
  - [ ] logout/ → LogoutView
  - [ ] dashboard/ → DashboardView
  - [ ] password-reset/ → PasswordResetView

### apps/core/decorators.py
- [ ] Criar @admin_required
- [ ] Criar @login_required_custom

### apps/core/mixins.py
- [ ] Criar AdminRequiredMixin
- [ ] Criar OwnerOrAdminMixin

### Templates
- [ ] Criar `templates/base.html`
  - [ ] Bootstrap 5 CDN
  - [ ] Navbar
  - [ ] {% block content %}
  - [ ] Footer
  - [ ] Messages
- [ ] Criar `templates/auth/login.html`
  - [ ] Formulário de login
  - [ ] Campos: email, senha
  - [ ] Link para reset password
  - [ ] {% csrf_token %}
- [ ] Testar rendering

### Testes
- [ ] Testar login com credenciais corretas
- [ ] Testar login com credenciais erradas
- [ ] Testar redirecionamento autenticado
- [ ] Testar proteção de rotas

---

## FASE 4: DASHBOARD (Dia 5)

### views.py - DashboardView
- [ ] Implementar get_context_data()
  - [ ] Filtros: data_inicio, data_fim, cultura_id, turno
  - [ ] Query base com filtros
  - [ ] Cálculos de KPI (total_caixas, reembalagens, %)
  - [ ] Aggregations por dia, cultura, turno
  - [ ] Preparar dados para gráficos (JSON)
- [ ] Adicionar cache (15 min)

### templates/dashboard.html
- [ ] KPI Cards
  - [ ] Total de Caixas
  - [ ] Total de Reembalagens
  - [ ] % Retorno
  - [ ] Média Diária
- [ ] Filtros (data, cultura, turno)
- [ ] Gráficos (Chart.js)
  - [ ] Linha: Caixas por Dia
  - [ ] Pizza: Produção por Cultura
  - [ ] Barra: Produção por Turno
- [ ] Botão "Exportar Dashboard"

### Charts (Chart.js)
- [ ] Adicionar CDN Chart.js no base.html
- [ ] Criar `static/js/charts.js`
- [ ] Implementar renderização de gráficos
- [ ] Testar com dados mock

### Testes
- [ ] Testar acesso sem autenticação (redireciona para login)
- [ ] Testar KPI calculations
- [ ] Testar filtros
- [ ] Testar gráficos com dados reais

---

## FASE 5: REGISTRAR PRODUÇÃO (Dia 6)

### apps/producao/forms.py
- [ ] Criar ProducaoForm
  - [ ] codigo_barra (CharField, autofocus, placeholder)
  - [ ] cultura (ModelChoiceField, required)
  - [ ] quantidade (IntegerField, min=1, default=1)
  - [ ] reembalagem (BooleanField, optional)
  - [ ] Form styling
  - [ ] Widget customization

### apps/producao/views.py
- [ ] Criar RegistrarProducaoView
  - [ ] LoginRequiredMixin
  - [ ] form_valid():
    - [ ] Buscar embalador por codigo_barra
    - [ ] Validar existência
    - [ ] Calcular turno (calcularTurno())
    - [ ] Capturar data/hora atuais
    - [ ] Buscar configuração (bonificação/penalidade)
    - [ ] Salvar produção
    - [ ] Invalidar cache
    - [ ] Mensagem de sucesso
  - [ ] get_context_data():
    - [ ] Ultimas leituras (últimas 10)
    - [ ] Cultura selecionada (da sessão)
- [ ] Testar view

### templates/producao/registrar.html
- [ ] Formulário
  - [ ] Código de barras (foco no input)
  - [ ] Cultura (select)
  - [ ] Quantidade (number)
  - [ ] Checkbox reembalagem
  - [ ] {% csrf_token %}
  - [ ] Botão "Registrar"
- [ ] Histórico de últimas leituras
  - [ ] Tabela com últimas 10
  - [ ] Campos: Embalador, Cultura, Turno, Quantidade, Reembalagem
- [ ] Feedback visual
  - [ ] Messages (sucesso/erro)
  - [ ] Limpar campo código após sucesso

### JavaScript
- [ ] Auto-clear campo código após sucesso
- [ ] Auto-focus no input
- [ ] Enter para submeter
- [ ] Validação client-side

### Signals
- [ ] Criar `producao/signals.py`
  - [ ] @receiver(post_save, Producao)
  - [ ] Invalidar cache ao salvar novo registro
  - [ ] Log de criação

### Testes
- [ ] Testar com código válido
- [ ] Testar com código inválido
- [ ] Testar sem cultura selecionada
- [ ] Testar cálculo de turno
- [ ] Testar save de configuração (snapshot)
- [ ] Testar cache invalidation

---

## FASE 6: CRUD CULTURAS (Dia 7)

### apps/producao/forms.py - Atualizar
- [ ] Criar CulturaForm
  - [ ] nome (CharField, placeholder)
  - [ ] Styling Bootstrap

### apps/producao/views.py - Adicionar
- [ ] CriarCulturaView
  - [ ] CreateView
  - [ ] form_valid: registrar modified_by, mensagem sucesso
- [ ] ListaCulturasView
  - [ ] ListView
  - [ ] paginate_by = 20
  - [ ] ordem alfabética
- [ ] EditarCulturaView
  - [ ] UpdateView
  - [ ] form_valid: registrar modified_by, mensagem
- [ ] DeletarCulturaView
  - [ ] DeleteView
  - [ ] Antes de deletar: verificar pode_deletar()
  - [ ] Se vinculada: mensagem erro e redirect

### templates/producao/
- [ ] cultura_form.html (create/update)
- [ ] cultura_lista.html (read)
  - [ ] Tabela com DataTables
  - [ ] Colunas: Nome, Criado, Modificado, Ações
  - [ ] Botão "Nova Cultura"
  - [ ] Ações: Editar, Deletar
- [ ] cultura_confirm_delete.html (delete)
  - [ ] Confirmar mensagem
  - [ ] Aviso se vinculada

### URLs - apps/producao/urls.py
- [ ] /culturas/
- [ ] /culturas/criar/
- [ ] /culturas/editar/<id>/
- [ ] /culturas/deletar/<id>/

### DataTables
- [ ] Integrar jQuery DataTables
- [ ] Configurar em static/js/datatables-config.js
- [ ] Adicionar search, sort, pagination

### Testes
- [ ] Testar CRUD completo
- [ ] Testar proteção contra delete vinculado
- [ ] Testar mensagens
- [ ] Testar sorting/pagination

---

## FASE 7: CRUD EMBALADORES (Dia 8)

### apps/producao/forms.py - Atualizar
- [ ] Criar EmbaladorForm
  - [ ] nome, codigo_barra, ativo
  - [ ] Validators (MinLengthValidator)
  - [ ] Styling

### apps/producao/views.py - Adicionar
- [ ] CriarEmbaladorView
- [ ] ListaEmbaladoresView
- [ ] EditarEmbaladorView
- [ ] DeletarEmbaladorView
(Similar ao Culturas)

### templates/producao/
- [ ] embalador_form.html
- [ ] embalador_lista.html
  - [ ] Colunas: Nome, Código, Ativo, Caixas, Reembalagens, %
  - [ ] Usar properties do model
- [ ] embalador_confirm_delete.html

### URLs - apps/producao/urls.py
- [ ] /embaladores/
- [ ] /embaladores/criar/
- [ ] /embaladores/editar/<id>/
- [ ] /embaladores/deletar/<id>/

### Testes
- [ ] Testar CRUD
- [ ] Testar código único
- [ ] Testar properties (producao_total, etc)
- [ ] Testar proteção delete

---

## FASE 8: LISTA DE PRODUÇÃO (Dia 9)

### apps/producao/views.py - Atualizar
- [ ] ListaProducaoView
  - [ ] select_related (embalador, cultura, criado_por)
  - [ ] Filtros: data_inicio, data_fim, embalador_id, cultura_id, turno
  - [ ] Ordering: -data, -hora
  - [ ] paginate_by = 50

### apps/producao/forms.py - Atualizar
- [ ] FiltroProducaoForm (com campos de filtro)

### templates/producao/
- [ ] producao_lista.html
  - [ ] Formulário de filtros (acima da tabela)
  - [ ] Tabela com colunas: Data, Hora, Embalador, Cultura, Turno, Qtd, Reemb, Bonif, Penal, Ações
  - [ ] DataTables
  - [ ] Ações: Editar, Deletar

### URLs - apps/producao/urls.py
- [ ] /lista/
- [ ] /editar/<id>/
- [ ] /deletar/<id>/

### Testes
- [ ] Testar query optimization (select_related)
- [ ] Testar filtros
- [ ] Testar pagination
- [ ] Testar cálculos de bonificação/penalidade

---

## FASE 9: RELATÓRIO BONIFICAÇÃO (Dia 10)

### apps/relatorio/views.py
- [ ] RelatorioBonificacaoView
  - [ ] Filtros: data_inicio, data_fim
  - [ ] Loop por embaladores ativos
  - [ ] Query e cálculos por embalador
  - [ ] Totalizadores (sum de tudo)
  - [ ] Ordenação por final (desc)

### templates/relatorio/
- [ ] bonificacao.html
  - [ ] Filtro de datas
  - [ ] Tabela: Embalador, Caixas, Reemb, Bonificação, Penalidade, Final
  - [ ] Linha de totalizadores
  - [ ] Botão "Exportar PDF"
  - [ ] Botão "Exportar Excel"

### URLs - apps/relatorio/urls.py
- [ ] /bonificacao/

### Testes
- [ ] Testar cálculos (bonif = caixas × valor, penal = reemb × valor)
- [ ] Testar totalizadores
- [ ] Testar período

---

## FASE 10: EXPORTAÇÃO EXCEL (Dia 11)

### apps/relatorio/views.py
- [ ] ExportarDashboardExcelView
  - [ ] Criar Workbook (openpyxl)
  - [ ] Aba 1: Detalhes (linha por linha)
  - [ ] Aba 2: Resumo (por embalador)
  - [ ] Aba 3: Totalizadores
  - [ ] Formatação: cores, bordas, fórmulas
  - [ ] HttpResponse com arquivo

### apps/relatorio/views.py
- [ ] ExportarLeiturasExcelView
  - [ ] Similar ao Dashboard
  - [ ] Mais detalhes

### Templates
- [ ] Botões "Exportar Excel" em dashboard e relatório

### Testes
- [ ] Testar download
- [ ] Testar formatação
- [ ] Testar fórmulas Excel
- [ ] Testar com diferentes períodos

---

## FASE 11: CONFIGURAÇÕES (Dia 12)

### apps/producao/forms.py - Atualizar
- [ ] ConfiguracaoForm
  - [ ] valor_bonificacao (DecimalField)
  - [ ] valor_penalidade (DecimalField)

### apps/relatorio/views.py
- [ ] ConfiguracaoView (admin only)
  - [ ] UpdateView
  - [ ] form_valid: registrar modified_by, criar log

### templates/relatorio/
- [ ] configuracoes.html
  - [ ] Formulário de valores
  - [ ] Campo de motivo (opcional)
  - [ ] Botão "Salvar"

### signals.py
- [ ] Registrar mudanças em ConfiguracaoLog
- [ ] Invalidar cache de configuração

### URLs - apps/relatorio/urls.py
- [ ] /configuracoes/ (admin only)

### Decorator/Mixin
- [ ] Proteger view com AdminRequiredMixin

### Testes
- [ ] Testar atualização de valores
- [ ] Testar log de alterações
- [ ] Testar acesso não-admin (deve redirecionar)

---

## FASE 12: AUDITORIA (Dia 13)

### apps/relatorio/views.py
- [ ] AuditoriaView (admin only)
  - [ ] Listar ConfiguracaoLog
  - [ ] Filtrar por data
  - [ ] Mostrar quem alterou

### templates/relatorio/
- [ ] auditoria.html
  - [ ] Tabela: Data, Tipo, Valores Ant/Novo, Quem, Motivo

### URLs - apps/relatorio/urls.py
- [ ] /auditoria/ (admin only)

### Testes
- [ ] Testar criação de logs
- [ ] Testar listagem

---

## FASE 13: USUÁRIOS (Dia 14-15)

### apps/core/views.py - Adicionar
- [ ] CriarUsuarioView
- [ ] ListaUsuariosView
- [ ] EditarUsuarioView
- [ ] DeletarUsuarioView
(Proteger com AdminRequiredMixin)

### templates/core/
- [ ] usuario_form.html
- [ ] usuario_lista.html
- [ ] usuario_confirm_delete.html

### URLs - apps/core/urls.py
- [ ] /usuarios/
- [ ] /usuarios/criar/
- [ ] /usuarios/editar/<id>/
- [ ] /usuarios/deletar/<id>/

### Proteções
- [ ] Não permitir deletar a si mesmo
- [ ] Apenas admin pode gerenciar

### Testes
- [ ] Testar CRUD
- [ ] Testar proteção (não-admin não acessa)
- [ ] Testar auto-delete prevention

---

## FASE 14: TEMPLATES COMPLETOS (Dia 16)

### Layout Base
- [ ] base.html - Completo
  - [ ] Navbar com menus por perfil
  - [ ] Sidebar (opcional)
  - [ ] Messages placeholder
  - [ ] Footer
  - [ ] CSS/JS includes

### Navbar
- [ ] includes/navbar.html
  - [ ] Logo
  - [ ] Links por perfil
  - [ ] Dropdown usuário (logout)

### Menu
- [ ] includes/menu.html ou sidebar
  - [ ] Dashboard
  - [ ] Registrar Produção
  - [ ] Listas (Culturas, Embaladores, Produção)
  - [ ] Relatórios
  - [ ] Configurações (admin)
  - [ ] Usuários (admin)

### Messages
- [ ] includes/messages.html
  - [ ] Usar toasts Bootstrap
  - [ ] Diferentes cores por tipo

### Footer
- [ ] includes/footer.html
  - [ ] Copyright
  - [ ] Links

### Testes
- [ ] Renderização de todos os templates
- [ ] Links funcionando
- [ ] Responsividade mobile

---

## FASE 15: ESTILO E CUSTOMIZAÇÃO (Dia 17)

### CSS
- [ ] Criar static/css/custom.css
  - [ ] Cores customizadas
  - [ ] Tipografia
  - [ ] Espaçamento
  - [ ] Cards
  - [ ] Buttons

### Assets
- [ ] Logo da empresa (static/img/)
- [ ] Favicon

### Responsive
- [ ] Testar em mobile
- [ ] Ajustar tabelas (scrollable em mobile)
- [ ] Ajustar formulários

### Dark Mode (Opcional)
- [ ] Toggle theme
- [ ] Persistir preferência (localStorage)

---

## FASE 16: SEGURANÇA (Dia 18)

### CSRF
- [ ] {% csrf_token %} em todos os formulários ✓ (já implementado)
- [ ] Testar requisições POST

### SQL Injection
- [ ] Verificar todas as queries (ORM Django) ✓ (já implementado)
- [ ] Testar com strings maliciosas

### XSS
- [ ] {{ var|safe }} apenas onde necessário
- [ ] Escaping automático do Django
- [ ] Testar com script injection

### Rate Limiting (Opcional)
- [ ] Instalar django-ratelimit
- [ ] Proteger /login/ (5 tentativas/min)

### Password Reset
- [ ] Testar fluxo completo
- [ ] Verificar expiração de token
- [ ] Testar email

### Autenticação
- [ ] Testar login obrigatório
- [ ] Testar redirecionamento
- [ ] Testar session timeout

---

## FASE 17: PERFORMANCE (Dia 19)

### Queries
- [ ] Audit N+1 queries (django-debug-toolbar)
- [ ] Usar select_related/prefetch_related
- [ ] Adicionar índices (já no model)

### Cache
- [ ] Configurar Redis
- [ ] Cache de configuração (1h)
- [ ] Cache de dashboard (15min)
- [ ] Testar cache invalidation

### Pagination
- [ ] Testar com 1000+ registros
- [ ] Ajustar PAGE_SIZE

### Database
- [ ] Criar backups
- [ ] Testar query performance
- [ ] Vacuum/analyze

---

## FASE 18: TESTES (Dia 20)

### Testes Unitários
- [ ] tests/test_models.py
  - [ ] Testes de modelo User
  - [ ] Testes de modelo Producao
  - [ ] Testes de properties/methods
- [ ] tests/test_forms.py
  - [ ] Testes de LoginForm
  - [ ] Testes de ProducaoForm
  - [ ] Testes de validação

### Testes de Integração
- [ ] tests/test_views.py
  - [ ] Testar cada view
  - [ ] Testar autenticação
  - [ ] Testar permissões
  - [ ] Testar forms (POST)
- [ ] tests/test_auth.py
  - [ ] Login flow
  - [ ] Logout
  - [ ] Protected views

### Testes de Segurança
- [ ] tests/test_security.py
  - [ ] CSRF token required
  - [ ] SQL injection protection
  - [ ] XSS protection

### Coverage
- [ ] Rodar: `pytest --cov=apps tests/`
- [ ] Meta: > 80% coverage
- [ ] Gerar relatório HTML

---

## FASE 19: DOCUMENTAÇÃO (Dia 21)

### README.md
- [ ] Visão geral do projeto
- [ ] Stack tecnológico
- [ ] Como instalar
- [ ] Como rodar
- [ ] Como testar
- [ ] Como deployar

### Code Comments
- [ ] Docstrings em classes e functions
- [ ] Inline comments em lógica complexa

### API Docs
- [ ] Auto-docs via drf-spectacular
- [ ] Testar /api/docs/

### User Guide
- [ ] Como registrar produção
- [ ] Como gerar relatórios
- [ ] Como exportar

---

## FASE 20: DEPLOYMENT (Dia 22-23)

### Checklist Pré-Deploy
- [ ] DEBUG = False
- [ ] SECRET_KEY = gerado aleatoriamente
- [ ] ALLOWED_HOSTS = configurado
- [ ] Database = PostgreSQL produção
- [ ] Email = SMTP real
- [ ] Statics = collectstatic executado
- [ ] Migrations = executadas
- [ ] Superuser = criado
- [ ] Logs = configurados
- [ ] Cache = Redis
- [ ] SSL/HTTPS = configurado
- [ ] Backups = automáticos

### Produção
- [ ] Escolher serviço (Heroku, DigitalOcean, AWS)
- [ ] Configurar banco de dados
- [ ] Configurar variáveis de ambiente
- [ ] Deploy com Gunicorn + Nginx
- [ ] Testar em produção
- [ ] Monitoramento (Sentry)

### CI/CD (Opcional)
- [ ] GitHub Actions / GitLab CI
- [ ] Rodar testes automaticamente
- [ ] Deploy automático

---

## FASE 21: PÓS-LAUNCH (Contínuo)

### Monitoring
- [ ] [ ] Sentry para exceções
- [ ] [ ] Logs estruturados
- [ ] [ ] Métricas de performance
- [ ] [ ] Alertas

### Backup
- [ ] [ ] Backup diário do banco
- [ ] [ ] Retenção de 30 dias
- [ ] [ ] Testar restore

### Manutenção
- [ ] [ ] Atualizar dependências mensalmente
- [ ] [ ] Security patches
- [ ] [ ] Otimizar queries lentas

### Feedback
- [ ] [ ] Coletar feedback dos usuários
- [ ] [ ] Bug tracking
- [ ] [ ] Feature requests

---

## CHECKLIST FINAL

### Funcionalidades
- [ ] Autenticação completa
- [ ] Dashboard com KPIs
- [ ] Registro de produção
- [ ] CRUD Culturas
- [ ] CRUD Embaladores
- [ ] CRUD Usuários
- [ ] Relatório Bonificação
- [ ] Exportação Excel
- [ ] Configurações
- [ ] Auditoria
- [ ] Listagem de produção

### Qualidade
- [ ] Code cleanup
- [ ] Testes > 80% coverage
- [ ] Sem warnings
- [ ] Documentação completa
- [ ] Performance otimizada
- [ ] Segurança auditada

### Deploy
- [ ] Servidor configurado
- [ ] SSL/HTTPS
- [ ] Backups automáticos
- [ ] Monitoring ativo
- [ ] Logs estruturados
- [ ] Health check

### Documentação
- [ ] README atualizado
- [ ] API docs completa
- [ ] User guide
- [ ] Admin guide
- [ ] Developer guide

---

## ESTIMATIVA DE TEMPO

| Fase | Duração | Dias |
|------|---------|------|
| 0-1: Setup | 2 dias | 1-2 |
| 2-4: Models, Auth, Dashboard | 4 dias | 3-6 |
| 5-7: Registrar, CRUD Culturas/Embal | 4 dias | 7-10 |
| 8-10: Listas, Relatórios, Exports | 3 dias | 11-13 |
| 11-12: Config, Auditoria | 2 dias | 14-15 |
| 13-14: Usuários, Templates | 2 dias | 16-17 |
| 15-17: Estilo, Segurança, Performance | 3 dias | 18-20 |
| 18-19: Testes, Documentação | 2 dias | 21-22 |
| 20: Deploy | 1-2 dias | 23-24 |
| **Total** | | **~24 dias** |

*Estimativa: 1 dev, 4-5 semanas com testes e documentação*

---

## RECURSOS IMPORTANTES

📚 **Documentação do Projeto:**
- `DOCUMENTACAO_DJANGO.md` - Completa (150+ páginas)
- `CODIGO_DJANGO_PRONTO.md` - Exemplos de código
- `QUICK_REFERENCE.md` - Guia rápido

📖 **Referências Externas:**
- Django Docs: https://docs.djangoproject.com/
- DRF: https://www.django-rest-framework.org/
- Bootstrap 5: https://getbootstrap.com/
- PostgreSQL: https://www.postgresql.org/docs/

---

**Última atualização:** 01/07/2026  
**Versão:** 1.0  
**Status:** ✅ Pronto para Execução
