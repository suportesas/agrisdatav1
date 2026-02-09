# 🌾 ERP Agrícola - Sistema Multi-empresa


Sistema de gestão agrícola com arquitetura **multi-tenant** (multiempresa), desenvolvido em **Python/Django** para produtores rurais, cooperativas e empresas do agronegócio.

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-4.2+-green.svg)](https://www.djangoproject.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 📋 Funcionalidades Principais

### 🚀 Instalação
1. Clone o repositório
2. Crie ambiente virtual: `python -m venv venv`
3. Ative: `venv\Scripts\activate` (Windows)
4. Instale: `pip install -r requirements.txt`
5. Migre: `python manage.py migrate`
6. Rode: `python manage.py runserver`

### 🏢 **Multi-tenant Completo**
- ✅ Isolamento total de dados por empresa
- ✅ Sistema de planos: Pequeno, Médio e Grande Produtor
- ✅ Controle automático de limites (fazendas, usuários, talhões, produtos)
- ✅ Bloqueio automático por expiração ou inadimplência

### 👥 **Gestão de Usuários**
- ✅ Múltiplos tipos: Admin, Gerente, Funcionário, Produtor, Vendedor, Financeiro
- ✅ Perfis personalizados com foto
- ✅ Auditoria completa de acessos (IP, navegador, horário)
- ✅ Detecção de logins suspeitos

### 🌾 **Cadastros Agrícolas**
- ✅ Fazendas com dados completos (CNPJ/CPF, localização GPS)
- ✅ Múltiplos endereços por fazenda
- ✅ Gerenciamento de contatos
- ✅ Upload de documentos (CCIR, certificados, licenças)
- ✅ Contas bancárias com suporte a PIX

### 💰 **Planos de Assinatura**
- 🌱 **Pequeno Produtor**: Ideal para começar (2 fazendas, 3 usuários)
- 🌾 **Médio Produtor**: Recursos avançados (5 fazendas, 10 usuários)
- 🚜 **Grande Produtor**: Recursos ilimitados + API + App Mobile

## 🚀 Tecnologias e Arquitetura

### **Backend**
- **Python 3.9+** - Linguagem principal
- **Django 4.2+** - Framework web
- **Django REST Framework** - API REST (opcional)
- **PostgreSQL** - Banco de dados (produção)
- **SQLite** - Banco de dados (desenvolvimento)

### **Frontend**
- **Bootstrap 5** - Framework CSS
- **HTML5 / CSS3** - Estrutura e estilo
- **JavaScript** - Interatividade
- **Bootstrap Icons** - Iconografia

### **Segurança e Infraestrutura**
- **Django Auth** - Sistema de autenticação customizado
- **Middleware** - Bloqueio automático de empresas
- **Signals** - Automações e notificações
- **Mixins** - Reutilização de código

## 📦 Estrutura do Projeto

```
erp_agricola/
│
├── empresas/          # App de gestão de empresas e planos
├── usuarios/          # App de autenticação e usuários
├── cadastros/         # App de cadastro de fazendas
├── dashboard/         # Dashboard principal
├── static/            # Arquivos estáticos
├── media/             # Uploads de usuários
└── erp_agricola/      # Configurações do projeto
```

## 🔧 Instalação Rápida

### 1️⃣ **Clone o Repositório**
```bash
git clone https://github.com/EMSSousa/erp_agricola_novo.git
cd erp_agricola
```

### 2️⃣ **Crie o Ambiente Virtual**

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3️⃣ **Instale as Dependências**
```bash
pip install -r requirements.txt
```

> 💡 **Dica:** Se não tiver o `requirements.txt`, gere com:
> ```bash
> pip freeze > requirements.txt
> ```

### 4️⃣ **Configure as Variáveis de Ambiente**
```bash
# Copie o template
cp .env.example .env

# Edite com seus dados
# Windows: notepad .env
# Linux/Mac: nano .env
```

**Gere uma SECRET_KEY:**
```python
python manage.py shell
>>> from django.core.management.utils import get_random_secret_key
>>> print(get_random_secret_key())
```

### 5️⃣ **Execute as Migrações**
```bash
python manage.py makemigrations
python manage.py migrate
```

### 6️⃣ **Crie o Superusuário**
```bash
python manage.py createsuperuser
```

### 7️⃣ **Inicialize os Planos Padrão**

Acesse no navegador após rodar o servidor:
```
http://127.0.0.1:8000/empresas/planos/inicializar/
```

Ou pelo shell do Django:
```bash
python manage.py shell
```
```python
from empresas.models import Plano

# Pequeno Produtor
Plano.objects.get_or_create(
    codigo='PEQUENO',
    defaults={
        'nome': 'Pequeno Produtor',
        'icone': '🌱',
        'valor_mensal': 99.00,
        'limite_fazendas': 2,
        'limite_usuarios': 3,
        'limite_talhoes': 10,
        'limite_produtos': 50,
        'ordem': 1
    }
)

# Médio Produtor
Plano.objects.get_or_create(
    codigo='MEDIO',
    defaults={
        'nome': 'Médio Produtor',
        'icone': '🌾',
        'valor_mensal': 249.00,
        'limite_fazendas': 5,
        'limite_usuarios': 10,
        'limite_talhoes': 30,
        'limite_produtos': 200,
        'acesso_relatorios_avancados': True,
        'acesso_app_mobile': True,
        'ordem': 2
    }
)

# Grande Produtor
Plano.objects.get_or_create(
    codigo='GRANDE',
    defaults={
        'nome': 'Grande Produtor',
        'icone': '🚜',
        'valor_mensal': 499.00,
        'limite_fazendas': 999,
        'limite_usuarios': 999,
        'limite_talhoes': 999,
        'limite_produtos': 999,
        'acesso_relatorios_avancados': True,
        'acesso_api': True,
        'acesso_app_mobile': True,
        'ordem': 3
    }
)
```

### 8️⃣ **Rode o Servidor**
```bash
python manage.py runserver
```

✅ **Acesse:** http://127.0.0.1:8000

🔐 **Admin Django:** http://127.0.0.1:8000/admin

## 👤 Primeiro Acesso

Após criar o superusuário, acesse:
- **Admin Django:** http://127.0.0.1:8000/admin
- **Sistema:** http://127.0.0.1:8000

## 📱 Funcionalidades Principais

### 🏢 Gestão de Empresas
- Cadastro de empresas com CNPJ
- Vinculação de planos de assinatura
- Controle de limites (fazendas, usuários, talhões)
- Bloqueio/ativação de empresas
- Controle de vencimento

### 👥 Gestão de Usuários
- Múltiplos tipos: Admin, Gerente, Funcionário, Produtor, Vendedor
- Perfis personalizados
- Foto de perfil
- Auditoria de logins (IP, navegador, data/hora)
- Alteração de senha

### 🌾 Cadastro de Fazendas
- Dados completos da fazenda
- Múltiplos endereços
- Contatos
- Documentos (CCIR, certificados, etc.)
- Contas bancárias (incluindo PIX)

### 💰 Planos de Assinatura
- **Pequeno Produtor:** Ideal para iniciantes
- **Médio Produtor:** Recursos avançados
- **Grande Produtor:** Ilimitado

## 🔐 Segurança Implementada

### ✅ **Recursos de Segurança Ativos**

| Recurso | Status | Descrição |
|---------|--------|-----------|
| 🔒 Multi-tenant | ✅ Ativo | Isolamento completo de dados por empresa |
| 🔑 Autenticação customizada | ✅ Ativo | Sistema próprio com validações |
| 📝 Auditoria de logins | ✅ Ativo | Registro de IP, navegador e horário |
| 🚫 Bloqueio automático | ✅ Ativo | Por expiração ou bloqueio manual |
| 🛡️ CSRF Protection | ✅ Ativo | Proteção contra ataques CSRF |
| 🔐 Senhas criptografadas | ✅ Ativo | Hash bcrypt automático |
| 📊 Validação de limites | ✅ Ativo | Controle por plano contratado |
| 🎯 Permissões por tipo | ✅ Ativo | Admin, Gerente, Funcionário, etc. |

### ⚠️ **Para Produção - Checklist**

```python
# settings.py - Configurações obrigatórias para produção

# 1. Debug DESATIVADO
DEBUG = False

# 2. Hosts permitidos
ALLOWED_HOSTS = ['seu-dominio.com', 'www.seu-dominio.com']

# 3. Banco PostgreSQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'erp_agricola',
        'USER': 'postgres',
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# 4. Segurança HTTPS
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# 5. Proteções adicionais
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
```

### 🔒 **Boas Práticas**

1. **NUNCA** commite arquivos com senhas ou tokens
2. Use `.env` para variáveis sensíveis
3. Mantenha `SECRET_KEY` sempre secreta
4. Ative HTTPS em produção
5. Configure backups automáticos
6. Monitore logins suspeitos
7. Atualize dependências regularmente

## 📊 Arquitetura Multi-Tenant

Cada empresa é isolada no sistema:
- Usuários só veem dados da própria empresa
- Superusuário tem visão global
- Limites baseados no plano contratado

## 🧪 Testes e Qualidade

### **Executar Testes**
```bash
# Todos os testes
python manage.py test

# App específico
python manage.py test usuarios
python manage.py test empresas

# Com verbosidade
python manage.py test --verbosity=2

# Manter banco de testes
python manage.py test --keepdb
```

### **Coverage (Cobertura de Testes)**
```bash
# Instalar coverage
pip install coverage

# Executar com coverage
coverage run --source='.' manage.py test

# Ver relatório no terminal
coverage report

# Gerar relatório HTML
coverage html
# Abre em: htmlcov/index.html
```

### **Linting e Formatação**
```bash
# Instalar ferramentas
pip install flake8 black isort

# Verificar PEP8
flake8 .

# Formatar código
black .

# Organizar imports
isort .
```

## 🛠️ Comandos Úteis Django

```bash
# ========== MIGRATIONS ==========
python manage.py makemigrations              # Criar migrations
python manage.py migrate                     # Aplicar migrations
python manage.py showmigrations              # Ver status
python manage.py sqlmigrate app_name 0001    # Ver SQL

# ========== SHELL ==========
python manage.py shell                       # Shell interativo
python manage.py shell_plus                  # Shell com models carregados

# ========== ADMIN ==========
python manage.py createsuperuser             # Criar admin
python manage.py changepassword username     # Mudar senha

# ========== DADOS ==========
python manage.py loaddata arquivo.json       # Importar dados
python manage.py dumpdata > backup.json      # Exportar dados
python manage.py flush                       # Limpar banco (CUIDADO!)

# ========== ESTÁTICOS ==========
python manage.py collectstatic               # Coletar arquivos estáticos
python manage.py collectstatic --noinput     # Sem confirmação

# ========== SERVIDOR ==========
python manage.py runserver                   # Servidor dev
python manage.py runserver 0.0.0.0:8000     # Acessível na rede

# ========== CHECAGENS ==========
python manage.py check                       # Verificar projeto
python manage.py check --deploy              # Check para produção
python manage.py validate                    # Validar models
```

## 📝 Variáveis de Ambiente (.env)

```env
SECRET_KEY=sua-chave-secreta-aqui
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (para produção)
DB_NAME=erp_agricola
DB_USER=postgres
DB_PASSWORD=senha
DB_HOST=localhost
DB_PORT=5432
```

## 🤝 Como Contribuir

1. Faça um fork do projeto
2. Crie uma branch: `git checkout -b feature/nova-funcionalidade`
3. Commit suas mudanças: `git commit -m 'Adiciona nova funcionalidade'`
4. Push para a branch: `git push origin feature/nova-funcionalidade`
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## 👨‍💻 Autor

Desenvolvido com ❤️ e apoio da IA

## 📞 Suporte

- Email: seu-email@exemplo.com
- Issues: https://github.com/EMSSousa/erp_agricola_novo/issues

## 🗺️ Roadmap

- [ ] Módulo de vendas
- [ ] Módulo financeiro
- [ ] Controle de estoque
- [ ] Relatórios avançados
- [ ] API REST
- [ ] App Mobile
- [ ] Integração com ViaCEP
- [ ] Notificações por email
- [ ] Dashboard com gráficos

## 📸 Screenshots

*Em breve...*

---

⭐ Se este projeto foi útil, deixe uma estrela no GitHub!

## 📝 Nota rápida sobre Área Agricultável

`Área Agricultável` na ficha da Fazenda é calculada automaticamente como a soma das **Áreas Plantáveis** (`area_plantavel`) das `Area` pertencentes àquela fazenda. Para alterar este valor, edite as `Area` (seções) da fazenda — o sistema sincroniza automaticamente a soma através de sinais Django.

- `Fazenda.area_agricultavel` (apresentado como leitura no formulário de edição da fazenda)
- `Area.area_total`, `Area.area_reserva`, `Area.area_plantavel` (edite por área)

Esta abordagem evita inconsistência entre um total armazenado manualmente e a soma das seções. Reservas/infraestrutura devem ser informadas por `area_reserva` nas `Area`.