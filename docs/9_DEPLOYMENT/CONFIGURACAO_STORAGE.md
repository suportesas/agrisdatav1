# Configuração do Supabase Storage - Próximos Passos

## ✅ O que foi feito

- [x] Criados 5 buckets no Supabase Storage:
  - `empresas-logos` - Logos das empresas
  - `documentos` - Documentos gerais
  - `produtos-imagens` - Imagens de produtos
  - `funcionarios-fotos` - Fotos de funcionários
  - `compras-xml` - Arquivos XML de notas fiscais

- [x] Implementado `core/storage.py` com helper class para uploads
- [x] Configurado signal handler em `empresas/signals.py` para auto-upload de logos
- [x] Testes de upload rodando (mas falhando com erro 403 RLS)

## ⚠️ Problema: RLS Policy Violation

Os uploads estão retornando erro 403:
```
ERRO: new row violates row-level security policy
```

Isso significa que os buckets de Storage têm RLS habilitado, bloqueando uploads.

## 🔧 Solução: Configurar RLS nos Buckets

### Opção 1: Desabilitar RLS (mais rápido)

1. Acesse: https://supabase.com/dashboard/
2. Navegue até: **SQL Editor**
3. Copie e execute este script SQL:

```sql
-- Desabilitar RLS para tabelas de storage
ALTER TABLE storage.buckets DISABLE ROW LEVEL SECURITY;
ALTER TABLE storage.objects DISABLE ROW LEVEL SECURITY;

-- Confirmar que está desabilitado
SELECT * FROM pg_tables WHERE schemaname = 'storage';
```

4. **Verifique resultado**: Depois disso, todos os 5 buckets devem permitir uploads.

---

### Opção 2: Configurar RLS Policies (mais seguro)

Se preferir manter RLS, adicione estas políticas para cada bucket:

1. Acesse: **Storage > Buckets**
2. Clique no bucket (ex: `empresas-logos`)
3. Vá para aba: **Policies**
4. Clique em **New Policy** e crie:

#### Policy: "Allow public read"
```sql
CREATE POLICY "Allow public read" 
ON storage.objects 
FOR SELECT 
USING (bucket_id = 'empresas-logos');
```

#### Policy: "Allow authenticated users to upload"
```sql
CREATE POLICY "Allow authenticated upload"
ON storage.objects
FOR INSERT
WITH CHECK (
  bucket_id = 'empresas-logos' AND
  auth.role() = 'authenticated'
);
```

#### Policy: "Allow users to delete their own files"
```sql
CREATE POLICY "Allow delete own files"
ON storage.objects
FOR DELETE
USING (
  bucket_id = 'empresas-logos' AND
  owner = auth.uid()
);
```

**Repita para cada bucket!**

---

## 📋 Checklist para Testar

Após configurar RLS:

```bash
# 1. Testar uploads
python test_storage_upload.py

# Expected output:
#   ✅ Logo da Empresa
#   ✅ Documento
#   ✅ URL Pública
#   ✅ Deleção de Arquivo
#   🎉 Todos os testes passaram!
```

---

## 🧪 Testar Upload Real na Interface

1. Inicie o servidor Django:
   ```bash
   python manage.py runserver
   ```

2. Acesse: http://127.0.0.1:8000/empresas/1/editar/

3. Faça upload de uma nova logo para a empresa

4. Verifique no console Django:
   ```
   INFO: Logo de 'Nexsafra Agrícola' enviada para Supabase Storage
   ```

5. Confirme no Supabase Dashboard:
   - Storage → empresas-logos
   - Você deve ver: `empresa1/2026/04/[filename]`

---

## 📚 Arquivos Criados/Modificados

- ✅ `core/storage.py` - Helper class para uploads
- ✅ `core/settings.py` - Configurações de buckets
- ✅ `empresas/signals.py` - Signal handler para auto-upload
- ✅ `generate_supabase_buckets.py` - Script para criar buckets (já executado)
- ✅ `test_storage_upload.py` - Suite de testes
- ✅ `disable_rls_buckets.py` - Info sobre RLS

---

## 🚀 Próximos Passos Após Configurar RLS

1. **Testar uploads automaticamente** via signal
2. **Implementar upload para outros tipos** de arquivo:
   - Documentos de funcionários
   - Imagens de produtos
   - Arquivos XML de notas fiscais
3. **Criar dashboard** para gerenciar arquivos enviados

---

## ❓ Troubleshooting

### "Error 403 Unauthorized"
- Verifique se RLS está desabilitado (ou policies estão corretas)
- Confirme que SUPABASE_SERVICE_ROLE_KEY está no .env

### "File not uploaded (URL returns None)"
- Verifique o nome do bucket (case-sensitive)
- Confirme que RLS policies permitem INSERT

### "File uploaded but not visible"
- Confirme que bucket policies permitem SELECT
- Verifique path do arquivo no Supabase Dashboard

---

## 📖 Referências

- [Supabase Storage Docs](https://supabase.com/docs/guides/storage)
- [Supabase RLS Docs](https://supabase.com/docs/guides/auth/row-level-security)
- [Supabase Python SDK](https://github.com/supabase/supabase-py)

---

**Status**: 🟡 Aguardando configuração de RLS no dashboard Supabase
