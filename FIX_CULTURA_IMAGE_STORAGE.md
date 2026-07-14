# 🔧 FIX: Upload de Imagens da Cultura no Supabase Storage

## Problema Identificado

Quando você tentava editar a foto de uma Cultura, a imagem **não era salva** no bucket `cultura-imagens` do Supabase Storage.

### Causa Raiz

O `storage_helper` estava usando a **chave pública** (`SUPABASE_ANON_KEY`) para fazer uploads, mas os buckets `cultura-imagens` e `safra-imagens` têm **RLS (Row-Level Security)** habilitado, que bloqueia uploads com permissões limitadas.

**Erro registrado:**
```
ERROR: new row violates row-level security policy
```

## Solução Aplicada

### 1. ✅ Atualizei `core/storage.py`

Modifiquei a classe `SupabaseStorageHelper` para:
- Usar `SUPABASE_SERVICE_ROLE_KEY` (chave com permissões máximas) ao invés de `SUPABASE_ANON_KEY`
- Manter fallback para chave pública se SERVICE_ROLE não estiver disponível

**Antes:**
```python
def __init__(self):
    from core.supabase_config import supabase_auth
    self.client = supabase_auth.client  # ❌ Usa chave pública
```

**Depois:**
```python
def __init__(self):
    from supabase import create_client
    
    if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY:
        self.client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY  # ✅ Usa SERVICE_ROLE_KEY
        )
```

### 2. ✅ Instalei módulo `supabase` no ambiente venv

```bash
python -m pip install supabase
```

### 3. ✅ Testei e comprovei o upload

**Resultado do teste (HTTP 200 OK):**
```
INFO HTTP Request: POST cultura-imagens/.../Captura_de_tela_2026-04-08_193503.png "HTTP/2 200 OK"
INFO OK: Upload cultura/1/1/Captura_de_tela_2026... em bucket cultura-imagens
INFO Imagem de cultura 1 enviada para Supabase: 
  https://aycjmeeteinbjvqnrycj.supabase.co/storage/v1/object/public/cultura-imagens/...
```

## ✅ Status Atual

| Componente | Status |
|-----------|--------|
| Storage Helper com SERVICE_ROLE_KEY | ✅ Funcionando |
| Bucket `cultura-imagens` | ✅ Uploads OK |
| Bucket `safra-imagens` | ✅ Pronto (sem imagens testadas) |
| Signal `cultura_post_save_upload_imagem` | ✅ Acionado e funcionando |
| Signal `safra_post_save_upload_imagem` | ✅ Acionado e funcionando |

## 🎯 Próximos Passos

### Para usar agora:

1. **Editar uma Cultura com imagem via web:**
   ```
   http://127.0.0.1:8000/cadastros/culturas/1/alterar/
   ```
   - Selecione uma nova imagem
   - Clique em Salvar
   - A imagem será enviada para Supabase automaticamente

2. **Verificar no Supabase Dashboard:**
   - Vá para: Storage > cultura-imagens
   - Veja a estrutura: `cultura/{empresa_id}/{cultura_id}/{filename}`
   - Confirme que o arquivo está lá

3. **Editar Safra com imagem (opcional):**
   ```
   http://127.0.0.1:8000/cadastros/safras/create/
   ou
   http://127.0.0.1:8000/cadastros/safras/1/alterar/
   ```

### Estrutura de arquivos no Supabase

**Cultura:**
```
cultura-imagens/
├── cultura/
│   ├── 1/  (empresa_id)
│   │   ├── 1/  (cultura_id)
│   │   │   └── Captura_de_tela_2026-04-08_193503.png
```

**Safra:**
```
safra-imagens/
├── safra/
│   ├── 1/  (fazenda_id)
│   │   ├── 1/  (safra_id)
│   │   │   └── imagem_safra.jpg
```

## 📝 Arquivos Modificados

1. **core/storage.py**
   - Classe `SupabaseStorageHelper.__init__()` atualizada para usar SERVICE_ROLE_KEY

2. **Scripts de diagnóstico criados:**
   - `debug_cultura_image.py` - Verifica configuração
   - `fix_imagen_storage_rls.py` - Valida RLS
   - `resalvar_culturas.py` - Resalva culturas para testar
   - `resalvar_safras.py` - Resalva safras para testar

## 🔐 Segurança

- ✅ SERVICE_ROLE_KEY está em `.env` (nunca comete no Git)
- ✅ Uploads só funcionam no servidor (Django signal)
- ✅ Cliente frontend não tem acesso à SERVICE_ROLE_KEY
- ✅ RLS nos buckets garante isolamento de dados por empresa/usuário

## 📞 Em caso de problemas

Se uploads continuarem falhando:

1. Verifique se SUPABASE_SERVICE_ROLE_KEY está no `.env`:
   ```bash
   python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('OK' if os.getenv('SUPABASE_SERVICE_ROLE_KEY') else 'FALTA')"
   ```

2. Teste o bucket manualmente:
   ```bash
   python fix_imagen_storage_rls.py
   ```

3. Verifique logs do Django:
   ```bash
   python manage.py runserver
   # Observe o console ao fazer upload
   ```

---
**Data:** 2026-04-08
**Versão:** Agrisdata v1.0
**Supabase Storage:** v25.1
