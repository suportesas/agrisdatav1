# 📸 Armazenamento de Imagens de Safra no Supabase Storage

## Visão Geral

As imagens do cadastro de safra agora são armazenadas automaticamente no **Supabase Storage**, garantindo:

✅ **Escalabilidade** - Storage ilimitado  
✅ **Segurança** - URLs públicas e acesso controlado  
✅ **Performance** - CDN integrado do Supabase  
✅ **Automatização** - Upload automático ao salvar a safra  

---

## 🔧 Configuração

### 1️⃣ Variáveis de Ambiente

Certifique-se que tem as credenciais do Supabase no `.env`:

```bash
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_KEY=sua-chave-publica
```

### 2️⃣ Inicializar Buckets

Crie os buckets no Supabase com um dos comandos a seguir:

**Via Django Management Command:**
```bash
python manage.py init_supabase_buckets
```

**Via Script Python:**
```bash
python setup_supabase_buckets.py
```

Output esperado:
```
📦 Inicializando 7 buckets no Supabase Storage...

✅ empresas-logos          → Já existe (Logos de empresas)
✅ documentos              → Já existe (Documentos (PDF, Word, Excel))
✅ produtos-imagens        → Já existe (Fotos de produtos)
✅ funcionarios-fotos      → Já existe (Fotos de colaboradores)
✅ compras-xml             → Já existe (Arquivos XML de compras)
✨ safra-imagens           → Criado (Imagens de safra)
✅ uploads-gerais          → Já existe (Uploads diversos)

📊 Resumo:
   ✨ Criados: 1
   ✅ Já existentes: 6
   📦 Total: 7

✓ Supabase Storage inicializado com sucesso!
```

---

## 📋 Uso

### Formulário de Safra

1. Abra o formulário de criação/edição de safra
2. Preencha os campos básicos (Nome, Fazenda, Cultura, Ano, etc.)
3. **Novo**: Selecione uma imagem na seção "Imagem da Safra"
4. Envie o formulário

A imagem será automaticamente:
- ✅ Validada
- ✅ Enviada para Supabase Storage  
- ✅ Uma URL pública será armazenada
- ✅ Exibida na página de detalhes da safra

### Detalhes da Safra

Na página de visualização da safra, a imagem é exibida no header do card principal.

---

## 🏗️ Arquitetura Técnica

### Arquivos Principais

| Arquivo | Descrição |
|---------|-----------|
| `core/supabase_storage.py` | Storage backend customizado para Django |
| `core/storage.py` | Helper para operações no Supabase Storage |
| `cadastros/signals.py` | Signal para upload automático de imagens |
| `cadastros/models.py` | Campo `imagem` adicionado ao modelo Safra |
| `cadastros/forms.py` | Campo de upload adicionado ao SafraForm |
| `cadastros/management/commands/init_supabase_buckets.py` | Comando para inicializar buckets |

### Fluxo de Upload

```
1. Usuário seleciona imagem na formulário
        ↓
2. Formulário é validado (SafraForm)
        ↓
3. Safra é salva no banco de dados
        ↓
4. Signal (safra_post_save_upload_imagem) é acionado
        ↓
5. Imagem é enviada para Supabase Storage
        ↓
6. URL pública é obtida e armazenada
        ↓
7. Imagem é exibida na página de detalhes
```

### Estrutura de Diretórios no Storage

```
safra-imagens/
├── {fazenda_id}/
│   ├── {safra_id}/
│   │   ├── imagem1.jpg
│   │   ├── imagem2.png
│   │   └── ...
```

---

## 🔒 Segurança

- ✅ Bucket `safra-imagens` é público (acesso leitura)
- ✅ Apenas usuários autenticados podem fazer upload (via Django)
- ✅ Validação de tipos MIME: apenas imagens aceitas
- ✅ Upsert automático não sobrescreve sem confirmação

---

## 📝 Migrações

A migração `0076_safra_imagem.py` foi criada automaticamente para:
- ✅ Adicionar campo `imagem` ao modelo Safra
- ✅ Campo é opcional (null=True, blank=True)
- ✅ Manter compatibilidade com dados existentes

Apply a migração com:
```bash
python manage.py migrate
```

---

## 🛠️ Desenvolvimento

### Adicionar Customizações

#### Modificar o bucket de armazenamento

Em `core/settings.py`:
```python
SUPABASE_STORAGE_BUCKETS = {
    'safra-imagens': 'Imagens de safra',  # ← Customize aqui
    # ...
}
```

#### Modificar o signal de upload

Em `cadastros/signals.py`, função `safra_post_save_upload_imagem()`:
- Customize o caminho do arquivo
- Adicione compressão de imagem
- Implemente thumbnails

#### Usar storage customizado

```python
from core.supabase_storage import SupabaseStorage

class MyModel(models.Model):
    imagem = models.ImageField(
        storage=SupabaseStorage(bucket_name='meu-bucket')
    )
```

---

## 📚 Referências

- [Supabase Storage Docs](https://supabase.com/docs/guides/storage)
- [Django Storage Backend](https://docs.djangoproject.com/en/stable/topics/files/storage/)
- [Problemas Comuns](./TROUBLESHOOTING_SUPABASE_STORAGE.md)

---

## ❓ FAQ

**P: A imagem foi salva localmente ou no Supabase?**  
R: Se `SUPABASE_STORAGE_ENABLED=True` e a credencial está configurada, foi enviada para Supabase. Caso contrário, fica localmente.

**P: Como deletar uma imagem?**  
R: Quando você deleta a safra, o signal `safra_post_delete` deleta a imagem do Supabase automaticamente.

**P: Posso usar a mesma imagem em múltiplas safras?**  
R: Sim, mas cada safra terá sua própria cópia no armazenamento.

**P: A imagem é comprimida?**  
R: Atualmente, a imagem é armazenada tal qual. Se precisar, implemente compressão no signal.

---

## 🐛 Troubleshooting

### Erro: "ModuleNotFoundError: No module named 'supabase'"

```bash
pip install supabase
```

### Erro: "Bucket does not exist"

O bucket precisa ser criado. Execute:
```bash
python manage.py init_supabase_buckets
```

### Imagem não aparece no detalhes da safra

Verifique:
1. Se a imagem foi enviada (verifique Supabase console)
2. Se o bucket é público
3. Se a URL está correta no banco de dados

---

## 📞 Suporte

Para problemas, abra uma issue ou consulte:
- [SUMMARY_API_KEYS_FIX.md](./SUMMARY_API_KEYS_FIX.md)
- [SECURITY_AUDIT_API_KEYS.md](./SECURITY_AUDIT_API_KEYS.md)
