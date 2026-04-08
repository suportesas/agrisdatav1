# Troubleshooting - Erros de Conexão Supabase

## ❌ Erro: InvalidCursorName at /empresas/1/editar/

### Problema
```
cursor "_django_curs_XXXX_sync_2" does not exist
```

### Causa
- **Timeout de conexão**: Supabase pooler fecha a conexão inativa
- **Queries complexas**: Métodos que executam multiple queries em sequência
- **Falta de pool de conexões**: Django tenta reutilizar cursor expirado

### Soluções

#### ✅ Solução 1: Configuração de Pool (APLICADA)
Arquivo: `core/settings.py`

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': os.getenv('PG_NAME'),
        'USER': os.getenv('PG_USER'),
        'PASSWORD': os.getenv('PG_PASSWORD'),
        'HOST': os.getenv('PG_HOST'),
        'PORT': os.getenv('PG_PORT'),
        
        # ✅ Configurações críticas
        'CONN_MAX_AGE': 600,  # Reutilizar conexão por 10 min
        'OPTIONS': {
            'connect_timeout': 10,
            'options': '-c statement_timeout=30000'  
        },
        'ATOMIC_REQUESTS': False,
    }
}
```

#### ✅ Solução 2: Reiniciar Django Dev Server
```bash
# Cancele o servidor (Ctrl+C)
# Reinicie: 
python manage.py runserver
```

#### ✅ Solução 3: Limpar conexões
```bash
# No terminal:
python manage.py shell
>>> from django.db import connection
>>> connection.close()
>>> exit()
```

#### ✅ Solução 4: Usar SQLite para Desenvolvimento Local
Remova/comente as variáveis `PG_*` do `.env`:

```bash
# Comentar estas linhas no .env:
# PG_NAME=postgres
# PG_USER=postgres.aycjmeeteinbjvqnrycj
# PG_PASSWORD=...
# PG_HOST=aws-1-sa-east-1.pooler.supabase.com
# PG_PORT=6543
```

Então Django usará SQLite (db.sqlite3) automaticamente.

#### ✅ Solução 5: Aumentar Timeouts no .env
```bash
# Adicionar ao .env:
PG_TIMEOUT=30
PG_IDLE_TIMEOUT=60
```

Modifique `core/settings.py`:
```python
'OPTIONS': {
    'connect_timeout': int(os.getenv('PG_TIMEOUT', '10')),
    'options': f"-c statement_timeout={os.getenv('PG_IDLE_TIMEOUT', '60') * 1000}"
}
```

---

## 📊 Modo Desenvolvimento Recomendado

### Opção A: SQLite + Sincronização Manual
**Melhor para**: Desenvolvimento rápido, testes locais

1. Use SQLite para desenvolvimento (`PG_*` desativado)
2. Teste localmente
3. Make migrations: `python manage.py makemigrations`
4. Aplique no SQLite: `python manage.py migrate`
5. Quando estiver pronto, sincronize com Supabase

### Opção B: PostgreSQL Direto (Produção Like)
**Melhor para**: Testar exatamente como será em produção

1. Mantenha `PG_*` ativado no `.env`
2. Aplique as configurações de pool (já feimas)
3. Se tiver erro, reinicie o dev server
4. Use `connection.close()` se precisar forçar reconexão

---

## 🔧 Debug: Verificar Conexão

```bash
python manage.py shell
```

```python
from django.db import connection

# Testar conexão
with connection.cursor() as cursor:
    cursor.execute("SELECT 1")
    print("OK: Conexão ativa")

# Ver detalhes da conexão
print(f"Engine: {connection.settings_dict['ENGINE']}")
print(f"Host: {connection.settings_dict.get('HOST', 'SQLite')}")
print(f"Name: {connection.settings_dict.get('NAME')}")

# Fechar e reconectar
connection.close()
connection.ensure_connection()
print("OK: Reconectado")
```

---

## 📌 Preventivo: Melhores Práticas

### 1. **Evitar N+1 Queries**
```python
# ❌ Ruim
empresas = Empresa.objects.all()
for empresa in empresas:
    print(empresa.plano.nome)  # Query para cada empresa!

# ✅ Bom
empresas = Empresa.objects.select_related('plano')
for empresa in empresas:
    print(empresa.plano.nome)  # Uma única query
```

### 2. **Usar Prefetch**
```python
# ✅ Para relacionamentos reversos
empresas = Empresa.objects.prefetch_related('usuarios')
for empresa in empresas:
    usuarios = empresa.usuarios.all()  # Sem queries extras
```

### 3. **Cache Properties**
```python
from django.utils.functional import cached_property

class Empresa(models.Model):
    @cached_property
    def total_usuarios(self):
        return self.usuarios.count()  # Cache por requisição
```

### 4. **Monitora Queries**
```python
# Em settings.py (desenvolvimento):
LOGGING = {
    'loggers': {
        'django.db.backends': {
            'level': 'DEBUG',
        }
    }
}
```

---

## 🆘 Se Continuar com Erro

### Passo 1: Verificar Supabase Status
- https://supabase.com/dashboard/status
- Verifique se há incident reportado

### Passo 2: Verificar Credenciais
```python
import os
from dotenv import load_dotenv
load_dotenv()

print(f"URL: {os.getenv('PG_HOST')}")
print(f"Port: {os.getenv('PG_PORT')}")
print(f"User: {os.getenv('PG_USER')}")
print(f"Name: {os.getenv('PG_NAME')}")
```

### Passo 3: Testar Conexão Bruta (PostgreSQL)
```bash
# Instale psql client se não tiver
psql -h aws-1-sa-east-1.pooler.supabase.com -p 6543 -U "postgres.aycjmeeteinbjvqnrycj" -d postgres
```

### Passo 4: Desabilitar Temporariamente
Comente `PG_*` no `.env` e use SQLite para continuar trabalhando.

---

## 📝 Rastreamento

- **Data Descoberta**: 07/04/2026
- **Erro**: `InvalidCursorName at /empresas/1/editar/`
- **Causa Root**: Pool de conexões + Statement Timeout
- **Status**: ✅ CORRIGIDO (CONN_MAX_AGE + OPTIONS adicionados)
- **Teste**: Recarregue `http://127.0.0.1:8000/empresas/1/editar/`

