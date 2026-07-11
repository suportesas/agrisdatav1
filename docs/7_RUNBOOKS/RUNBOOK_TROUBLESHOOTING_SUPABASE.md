Owner: Operacoes
Status: Approved
Last Updated: 2026-07-10
Scope: Banco/conexao (Supabase Postgres)

# Runbook de Troubleshooting Supabase

## Sinais de incidente
- `InvalidCursorName` (ex: `cursor "_django_curs_XXXX_sync_2" does not exist`) em rotas com múltiplas queries em sequência
- Erro intermitente de conexão em rotas de edição
- Timeouts em operações com várias queries encadeadas

## Causa raiz conhecida
O pooler do Supabase fecha conexões inativas; sem `CONN_MAX_AGE`/timeouts configurados, o Django tenta reutilizar um cursor expirado. Corrigido em `core/settings.py` com:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': os.getenv('PG_NAME'),
        'USER': os.getenv('PG_USER'),
        'PASSWORD': os.getenv('PG_PASSWORD'),
        'HOST': os.getenv('PG_HOST'),
        'PORT': os.getenv('PG_PORT'),
        'CONN_MAX_AGE': 600,  # reutiliza conexão por 10 min
        'OPTIONS': {
            'connect_timeout': 10,
            'options': '-c statement_timeout=30000',
        },
        'ATOMIC_REQUESTS': False,
    }
}
```
Confirme que essas opções ainda estão presentes em `core/settings.py` antes de investigar mais fundo — regressões nessa config são a causa mais comum de reaparecimento do erro.

## Diagnóstico inicial
1. Confirmar se o ambiente usa as variáveis `PG_*` (Postgres/Supabase) ativas no `.env` — se estiverem ausentes, o Django cai para SQLite automaticamente (comportamento esperado em dev).
2. Verificar os parâmetros de conexão em `core/settings.py` (`CONN_MAX_AGE`, `OPTIONS`).
3. Testar conexão simples via shell:
   ```python
   python manage.py shell
   from django.db import connection
   with connection.cursor() as cursor:
       cursor.execute("SELECT 1")
       print("OK: Conexão ativa")
   print(connection.settings_dict['ENGINE'], connection.settings_dict.get('HOST'))
   ```
4. Verificar se o problema desaparece após reiniciar o servidor local (`Ctrl+C` e `python manage.py runserver`) — se sim, é sintoma de conexão obsoleta, não de query malformada.

## Ações de mitigação (curto prazo)
1. Reiniciar o servidor de desenvolvimento.
2. Fechar e reabrir a conexão manualmente quando necessário:
   ```python
   from django.db import connection
   connection.close()
   connection.ensure_connection()
   ```
3. Em caso de bloqueio local prolongado, remover/comentar as variáveis `PG_*` do `.env` para cair em SQLite temporariamente e continuar trabalhando.
4. Verificar status do Supabase em https://supabase.com/dashboard/status antes de assumir causa local.

## Ações definitivas (prevenção)
- Revisar consultas com risco de N+1 e aplicar `select_related`/`prefetch_related`:
  ```python
  # Ruim: 1 query por empresa
  for empresa in Empresa.objects.all():
      print(empresa.plano.nome)

  # Bom: 1 query no total
  for empresa in Empresa.objects.select_related('plano'):
      print(empresa.plano.nome)
  ```
- Usar `prefetch_related` para relacionamentos reversos (ex: `Empresa.objects.prefetch_related('usuarios')`).
- Considerar `@cached_property` para valores derivados caros dentro de uma mesma requisição.
- Ativar `LOGGING` de `django.db.backends` em nível `DEBUG` apenas durante diagnóstico (não deixar ligado em produção — gera volume alto de log).

## Checklist de retorno à normalidade
- Rota afetada responde sem erro
- Conexão válida testada em shell
- Fluxo de negócio alvo executa de ponta a ponta
- Sem novos erros relacionados nos logs após o ajuste

## Histórico
- 2026-04-07: erro `InvalidCursorName` identificado em `/empresas/<id>/editar/`; causa raiz = ausência de pool/timeout de conexão; corrigido com `CONN_MAX_AGE` + `OPTIONS` em `core/settings.py` (ver acima).
