# 🔗 INTEGRAÇÃO COM ERP AGRISDATAV1
## Guia Completo de Adaptação do Módulo Packing

---

## 📋 ANÁLISE DO SEU ERP

**Repositório:** https://github.com/sueldoserafim/agrisdatav1

**Stack:**
- ✅ Django 4.2 (mesmo da documentação Packing!)
- ✅ Django REST Framework
- ✅ PostgreSQL 14+
- ✅ Multi-tenant (por empresa)
- ✅ SimpleJWT para APIs

**Status Módulo Embalagem:** ✅ **JÁ EXISTE** em `/embalagem/`

---

## 🎯 ESTRATÉGIA DE INTEGRAÇÃO

### **Opção 1: Expandir o Módulo Existente (RECOMENDADO)**

```
Seu projeto /packing → Expandir /embalagem/ do agrisdatav1

Vantagens:
✅ Segue padrão multi-tenant já estabelecido
✅ Reutiliza autenticação/permissões do ERP
✅ Integração perfeita com estoque/vendas
✅ Uma única base de código
```

### **Opção 2: Integrar como Módulo Separado (Menos recomendado)**

```
/packing/ funciona paralelo a /embalagem/

Desvantagens:
❌ Duplicação de dados
❌ Sincronização complexa
❌ Múltiplos bancos
```

**👉 Recomendamos: OPÇÃO 1 (Expandir existente)**

---

## 📊 MAPEAMENTO DE DADOS

### **Cadastros que JÁ EXISTEM no ERP**

| Seu Modelo | Modelo ERP | Tabela | Status |
|---|---|---|---|
| **User (autenticação)** | `usuarios.models.User` | `usuarios_user` | ✅ Usar |
| **Cultura** | `produtos.models.Produto` | `produtos_produto` | ✅ Usar |
| **Embalador** | `rh.models.Funcionario` | `rh_funcionario` | ✅ Usar |
| **Producao (Registros)** | `estoque.models.MovimentacaoEstoque` + `operacoes_campo.models.OrdemServico` | `estoque_movimentacao`, `operacoes_campo_os` | ⚠️ Adaptar |
| **Configuracao** | Novo modelo ou usar `core.models.ConfiguracaoEmpresa` | `core_configuracaempresa` | ⚠️ Criar |
| **Embalagem (Ordem)** | `embalagem.models.OrdemEmbalagem` | `embalagem_ordemembalagem` | ✅ Expandir |

---

## 🔧 PASSO 1: ESTRUTURA DE PASTAS

### **Estrutura Atual do agrisdatav1**

```
erp_agricola/
├── embalagem/                    ← Módulo já existe!
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── serializers.py (REST)
│   ├── forms.py
│   ├── admin.py
│   └── templates/embalagem/
│       ├── listar_ordens.html
│       ├── criar_ordem.html
│       └── romaneio.html
│
├── estoque/                      ← Integração
│   ├── models.py (Produto, MovimentacaoEstoque)
│   └── ...
│
├── vendas/                       ← Integração
│   ├── models.py (PedidoVenda)
│   └── ...
│
├── rh/                          ← Integração
│   ├── models.py (Funcionario)
│   └── ...
│
├── usuarios/                    ← Autenticação
│   ├── models.py (User, Role)
│   └── ...
│
└── core/
    ├── settings.py
    └── utils/ (Multi-tenant, Criptografia)
```

---

## 📝 PASSO 2: MAPEAR MODELOS

### **User (Autenticação)**

**Seu arquivo:** `4_CODIGO_PRONTO.md` (User Model)

**Substituir por:**
```python
# Usar direto do ERP
from usuarios.models import User
```

**Mudança importante:**
```python
# Seu código:
# id = models.UUIDField(primary_key=True, default=uuid.uuid4)

# Usar do ERP:
# id = models.BigAutoField(primary_key=True)
# Adicionar campo:
empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE)
```

### **Cultura → Produto**

**Seu arquivo:** `4_CODIGO_PRONTO.md` (Cultura Model)

**Substituir por:**
```python
# Usar do ERP
from produtos.models import Produto

# Seu "Cultura" = "Produto" no ERP
# Adicionar campos específicos para embalagem se necessário:
# - peso_unitario
# - volume_unitario
# - foto_produto
```

### **Embalador → Funcionário**

**Seu arquivo:** `4_CODIGO_PRONTO.md` (Embalador Model)

**Substituir por:**
```python
# Usar do ERP
from rh.models import Funcionario

# Seu "Embalador" = "Funcionário" no ERP
# Já tem:
# - nome
# - codigo_barra (adaptar ou criar campo similar)
# - ativo
# - salário (bônus para embalagem)
```

### **Producao → MovimentacaoEstoque + OrdemServico**

**Seu arquivo:** `4_CODIGO_PRONTO.md` (Producao Model)

**Mapear para:**
```python
# Option 1: Usar MovimentacaoEstoque do estoque
from estoque.models import MovimentacaoEstoque

# Option 2: Criar OrdemEmbalagem relacionada
from embalagem.models import OrdemEmbalagem
```

**Estrutura proposta:**
```python
# embalagem/models.py

class OrdemEmbalagem(models.Model):
    TURNO_CHOICES = [
        ('Manhã', 'Manhã (5h-12h)'),
        ('Tarde', 'Tarde (12h-18h)'),
        ('Noite', 'Noite (18h-5h)'),
    ]
    
    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE)
    embalador = models.ForeignKey('rh.Funcionario', on_delete=models.PROTECT)
    produto = models.ForeignKey('produtos.Produto', on_delete=models.PROTECT)
    quantidade = models.PositiveIntegerField()
    turno = models.CharField(max_length=10, choices=TURNO_CHOICES)
    
    # Auto-calculados
    valor_bonificacao = models.DecimalField(max_digits=10, decimal_places=2)
    valor_penalidade = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Timestamps
    data = models.DateField(auto_now_add=True)
    hora = models.TimeField(auto_now_add=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    criado_por = models.ForeignKey('usuarios.User', on_delete=models.SET_NULL, null=True)
    
    class Meta:
        db_table = 'embalagem_ordem_embalagem'
        indexes = [
            models.Index(fields=['-data']),
            models.Index(fields=['embalador', '-data']),
            models.Index(fields=['empresa']),
        ]
```

---

## 🔄 PASSO 3: INTEGRAÇÃO COM FLUXO DO ERP

### **Fluxo Proposto**

```
1. Pedido de Venda criado (vendas/)
   └─ Cliente, Produtos, Quantidade
   
2. Estoque reservado (estoque/)
   └─ Movimentação: "Reserva para Embalagem"
   
3. Ordem de Embalagem criada (embalagem/) ← SEU MÓDULO
   └─ Funcionário, Produto, Quantidade, Turno
   └─ Auto-calcula: Bonificação, Penalidade, Turno
   
4. Romaneio gerado (embalagem/)
   └─ Pallet, Código QR, Assinatura
   
5. Estoque atualizado (estoque/)
   └─ Movimentação: "Embalagem realizada"
   └─ Saldo diminui
   
6. NF-e gerada (faturamento/)
   └─ Referencia a Embalagem realizada
   
7. Expedição (operacoes_campo/)
   └─ Romaneio é documento de transporte
```

---

## 🔐 PASSO 4: AUTENTICAÇÃO & PERMISSÕES

### **Roles/Perfis do ERP**

```python
from usuarios.models import Role

# Roles disponíveis:
ADMIN       → Acesso total
GERENTE     → Gerenciar embalagem
FUNC        → Registrar embalagem
VENDEDOR    → Ver pedidos
FINANCEIRO  → Ver bonificação
```

### **Implementar Permissões em Views**

```python
# embalagem/views.py

from usuarios.decorators import requires_role

class RegistrarEmbalagemView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    permission_required = 'embalagem.add_ordemembalagem'
    
    # Apenas usuários com role FUNC ou GERENTE
    @requires_role(['FUNC', 'GERENTE'])
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

class RelatorioEmbalagemView(LoginRequiredMixin, FormView):
    # Gerentes veem todos, Funcionários veem apenas seus registros
    
    @requires_role(['GERENTE', 'FUNC'])
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.role == 'GERENTE':
            context['ordens'] = OrdemEmbalagem.objects.filter(empresa=self.request.user.empresa)
        else:
            context['ordens'] = OrdemEmbalagem.objects.filter(
                embalador__usuario=self.request.user,
                empresa=self.request.user.empresa
            )
        return context
```

---

## 📱 PASSO 5: CRIAR VIEWS/TEMPLATES

### **URLs Structure**

```python
# embalagem/urls.py

from django.urls import path
from . import views

app_name = 'embalagem'

urlpatterns = [
    # Dashboard
    path('', views.EmbalagemDashboardView.as_view(), name='dashboard'),
    
    # Registrar Embalagem
    path('registrar/', views.RegistrarEmbalagemView.as_view(), name='registrar'),
    path('lista/', views.ListaEmbalagemView.as_view(), name='lista'),
    
    # Pallet/Romaneio
    path('pallet/criar/', views.CriarPalletView.as_view(), name='pallet_criar'),
    path('romaneio/<int:pk>/', views.RomaneioDetailView.as_view(), name='romaneio_detail'),
    path('romaneio/<int:pk>/imprimir/', views.ImprimirRomaneioView.as_view(), name='romaneio_imprimir'),
    
    # Relatórios
    path('relatorio/bonificacao/', views.RelatorioBonificacaoView.as_view(), name='relatorio_bonificacao'),
    path('relatorio/produtividade/', views.RelatorioProdutividadeView.as_view(), name='relatorio_produtividade'),
    
    # API REST
    path('api/ordens/', views.OrdemEmbalagemListCreateAPIView.as_view(), name='api_ordens'),
    path('api/ordens/<int:pk>/', views.OrdemEmbalagemDetailAPIView.as_view(), name='api_ordem_detail'),
]

# Registrar em core/urls.py:
# path('embalagem/', include('embalagem.urls')),
```

---

## 🛠️ PASSO 6: SETTINGS.PY - ADAPTAR

### **Diferenças do agrisdatav1**

```python
# Seu settings.py vs agrisdatav1 settings.py

# ✅ Já tem (não mude):
INSTALLED_APPS = [
    ...
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
    'crispy_forms',
    'crispy_bootstrap5',
    ...
]

# ⚠️ Adicione multi-tenant:
MIDDLEWARE = [
    ...
    'core.middleware.MultiTenantMiddleware',  # Do ERP
    ...
]

# ⚠️ Database: já vem configurado
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'agrisdatav1_db',
        'USER': 'postgres',
        'PASSWORD': '...',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# ✅ Cache & Storage (já tem configurado)
CACHES = {...}  # Redis
STORAGES = {...}  # Supabase

# ⚠️ Adicione REST Framework config:
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
}
```

---

## 📊 PASSO 7: MIGRAÇÃO DE DADOS

### **Se já tem dados no banco local**

```bash
# 1. Backup do banco local
pg_dump packing_db > backup_packing.sql

# 2. Estudar schema do agrisdatav1
python manage.py inspectdb > models_existing.py

# 3. Script de migração (criar em agrisdatav1)
# embalagem/management/commands/migrar_dados_packing.py

python manage.py migrar_dados_packing --from-backup backup_packing.sql
```

### **Exemplo de Script de Migração**

```python
# embalagem/management/commands/migrar_dados_packing.py

from django.core.management.base import BaseCommand
from rh.models import Funcionario
from produtos.models import Produto
from embalagem.models import OrdemEmbalagem
from usuarios.models import User
import datetime

class Command(BaseCommand):
    help = 'Migra dados do sistema Packing local para o ERP'
    
    def add_arguments(self, parser):
        parser.add_argument('--empresa-id', type=int, required=True, help='ID da empresa no ERP')
    
    def handle(self, *args, **options):
        empresa_id = options['empresa-id']
        
        # 1. Verificar que empresa existe
        from empresas.models import Empresa
        empresa = Empresa.objects.get(id=empresa_id)
        
        # 2. Importar embaladores como funcionários
        self.stdout.write('Importando embaladores...')
        # SELECT * FROM packing_embalador
        # INSERT INTO rh_funcionario (nome, codigo_barra, empresa_id, ...)
        
        # 3. Importar culturas como produtos
        self.stdout.write('Importando culturas...')
        # SELECT * FROM packing_cultura
        # INSERT INTO produtos_produto (nome, empresa_id, ...)
        
        # 4. Importar produções como ordens de embalagem
        self.stdout.write('Importando produções...')
        # SELECT * FROM packing_producao
        # INSERT INTO embalagem_ordemembalagem (...)
        
        self.stdout.write(self.style.SUCCESS('Migração concluída!'))
```

---

## 🔗 PASSO 8: TESTAR INTEGRAÇÃO

### **Checklist de Teste**

- [ ] Conectar ao banco PostgreSQL do ERP
- [ ] Listar produtos (culturas) do ERP
- [ ] Listar funcionários (embaladores) do ERP
- [ ] Criar ordem de embalagem
- [ ] Auto-calcular turno, bonificação, penalidade
- [ ] Registrar em banco
- [ ] Gerar romaneio com código QR
- [ ] API REST funcionando
- [ ] Dashboard mostrando dados corretos
- [ ] Multi-tenant isolando por empresa

---

## 🚀 PASSO 9: DEPLOY NO MESMO SERVIDOR DO ERP

```bash
# 1. Clonar repositório agrisdatav1
git clone https://github.com/sueldoserafim/agrisdatav1.git
cd agrisdatav1

# 2. Criar branch para expandir embalagem
git checkout -b feature/packing-expanded

# 3. Copiar seus modelos/views para /embalagem/
# Adaptar conforme mapeamento acima

# 4. Rodar migrations
python manage.py makemigrations embalagem
python manage.py migrate

# 5. Testar localmente
python manage.py runserver

# 6. Fazer commit e PR
git add .
git commit -m "feat: Expandir módulo embalagem com Packing"
git push origin feature/packing-expanded

# 7. Deploy em produção (mesmo servidor do ERP)
# Gunicorn + Nginx já configurado
```

---

## 📞 ESTRUTURA FINAL RECOMENDADA

```
agrisdatav1/
├── embalagem/  ← Seu módulo integrado aqui
│   ├── __init__.py
│   ├── models.py (OrdemEmbalagem, Pallet, Romaneio, ConfiguracaoEmbalagem)
│   ├── views.py (Dashboard, CRUD, Relatórios, API)
│   ├── urls.py
│   ├── forms.py
│   ├── serializers.py (DRF)
│   ├── admin.py
│   ├── signals.py (Invalidar cache)
│   ├── tests.py
│   ├── management/
│   │   └── commands/
│   │       └── migrar_dados_packing.py
│   ├── templates/embalagem/
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   ├── registrar.html
│   │   ├── lista.html
│   │   ├── romaneio.html
│   │   └── relatorio.html
│   └── static/embalagem/
│       ├── css/
│       └── js/
│
├── core/
├── usuarios/
├── cadastros/
├── financeiro/
├── estoque/
├── vendas/
├── rh/
└── ...
```

---

## ⚠️ PONTOS CRÍTICOS

| Ponto | Ação |
|---|---|
| **Multi-tenant** | Sempre usar `empresa` como filtro |
| **Autenticação** | Não criar novo User, usar do ERP |
| **Dados mestres** | Reutilizar Produto, Funcionário, etc |
| **Sincronização** | Usar Signals para manter dados consistentes |
| **Segurança** | Seguir padrão de criptografia do ERP |
| **APIs** | Usar SimpleJWT, CORS já configurado |

---

## 📚 REFERÊNCIAS

- **Repositório agrisdatav1:** https://github.com/sueldoserafim/agrisdatav1
- **Documentação Django:** https://docs.djangoproject.com/en/4.2/
- **Django REST Framework:** https://www.django-rest-framework.org/

---

**Status:** ✅ Pronto para Integração  
**Data:** 01/07/2026  
**Próximo Passo:** Estudar `/embalagem/` do agrisdatav1 e adaptar seu módulo Packing
