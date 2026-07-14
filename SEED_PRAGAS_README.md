# 🐛 Sistema de Seed de Pragas Agrícolas

## Visão Geral

Este sistema permite popular automaticamente uma lista de pragas agrícolas pré-definidas quando uma nova empresa é criada no Agrisdata. Isso dá agilidade ao usuário, evitando que ele precise cadastrar manualmente as pragas mais comuns.

## Como Funciona

### 1. Seed Automático na Criação de Empresa

Quando uma nova **Empresa** é criada no sistema, as seguintes ações ocorrem automaticamente via Django Signal:

- ✅ Cria as pragas pré-definidas
- ✅ Associa as pragas à empresa criada
- ✅ Evita duplicatas (pragas com mesmo nome não são criadas duas vezes)
- ✅ Não bloqueia a criação da empresa se houver erro

### 2. Arquivo de Seed

O arquivo `cadastros/pragas_seed.py` contém:

- **PRAGAS_SEED**: Lista com ~40+ pragas comuns divididas por categoria:
  - 🐛 Insetos (13 tipos)
  - 🕷️ Ácaros (3 tipos)
  - 🦗 Nematoides (3 tipos)
  - 🍄 Fungos (10 tipos)
  - 🦠 Bactérias (3 tipos)
  - 💉 Vírus (4 tipos)
  - 🐌 Moluscos (2 tipos)
  - 🔧 Outros (3 tipos)

Cada praga inclui:
- `nome_comum`: Nome popular (ex: "Lagarta-do-cartucho")
- `nome_cientifico`: Nome científico (ex: "Spodoptera frugiperda")
- `tipo`: Categoria (Inseto, Fungo, Vírus, etc)

### 3. Signal Automático

No arquivo `empresas/signals.py`, foi adicionado:

```python
@receiver(post_save, sender=Empresa)
def seed_pragas_on_create(sender, instance, created, **kwargs):
    """Cria pragas pré-definidas quando uma Empresa é criada."""
    if not created:
        return
    
    try:
        from cadastros.pragas_seed import seed_pragas_for_company
        criadas, ignoradas = seed_pragas_for_company(instance)
    except Exception:
        pass  # Não bloqueia criação de empresa
```

## Uso Manual

### Comando via Terminal

Se precisar popular pragas em empresas existentes, execute:

#### Popular uma empresa específica:
```bash
python manage.py seed_pragas --empresa-id 1
```

#### Popular todas as empresas:
```bash
python manage.py seed_pragas --all
```

#### Forçar recriação (não pular empresas com pragas):
```bash
python manage.py seed_pragas --all --skip-existing False
```

### Exemplo de Saída:
```
🌾 Processando: Fazenda Agricola Ltda...✅ 40 pragas criadas, 0 ignoradas
✅ Total de pragas criadas: 40
⏭️  Total de pragas ignoradas: 0
```

## Cenários de Uso

### Cenário 1: Nova Empresa Criada
1. Usuário cria uma nova Empresa no painel admin ou via formulário
2. **Automaticamente** as 40+ pragas são criadas
3. Usuário já pode visualizar as pragas em `http://127.0.0.1:8000/cadastros/pragas/`

### Cenário 2: Empresa Existente sem Pragas
1. Execute o comando: `python manage.py seed_pragas --empresa-id 123`
2. As pragas são criadas para aquela empresa

### Cenário 3: Atualizar Seed (Adicionar mais Pragas)
1. Edite `cadastros/pragas_seed.py` e adicione novas pragas
2. Execute: `python manage.py seed_pragas --all --skip-existing False`
3. Pragas antigas são mantidas, novas são adicionadas

## Características Importantes

✅ **Idempotente**: Não cria duplicatas se já existir praga com mesmo nome
✅ **Seguro**: Se algo der errado, não bloqueia criação da empresa
✅ **Rápido**: Executado em background no sinal post_save
✅ **Customizável**: Fácil adicionar/remover pragas do seed
✅ **Multi-tenant**: Cada empresa tem suas próprias pragas

## Adicionando Novas Pragas

Para adicionar novas pragas ao seed, edite `cadastros/pragas_seed.py`:

```python
PRAGAS_SEED = [
    # ... pragas existentes ...
    {
        'nome_comum': 'Nova Praga',
        'nome_cientifico': 'Novo genus species',
        'tipo': 'Inseto',  # ou outro tipo
    },
]
```

Depois execute:
```bash
python manage.py seed_pragas --all --skip-existing False
```

## Estrutura de Dados

### Tipos de Pragas Suportados
- `Inseto`
- `Ácaro`
- `Nematoide`
- `Fungo`
- `Bactéria`
- `Vírus`
- `Molusco`
- `Outro`

### Status de Pragas
- Todas são criadas com `ativa=True` por padrão
- Usuário pode desativar pragas após criação

## Vantagens para o Usuário

1. ⚡ **Agilidade**: Não precisa cadastrar 40+ pragas manualmente
2. 📚 **Base de Dados Completa**: Acesso imediato a pragas comuns
3. 🔄 **Flexibilidade**: Pode adicionar/remover pragas conforme necessário
4. 📊 **Consistência**: Base de pragas consistente entre empresas
5. 🌐 **Multi-tenant**: Cada empresa tem sua própria lista isolada

## Troubleshooting

### Pragas não foram criadas automaticamente?
1. Verifique se a empresa foi criada após implementação deste código
2. Execute manualmente: `python manage.py seed_pragas --empresa-id <id>`
3. Verifique se `empresas/signals.py` foi atualizado

### Quer resetar pragas de uma empresa?
```bash
# Deleta todas as pragas da empresa
python manage.py shell
>>> from cadastros.models import Praga
>>> Praga.objects.filter(empresa_id=1).delete()

# Depois recria:
>>> python manage.py seed_pragas --empresa-id 1
```

## Próximos Passos

Sugestões para evoluir este sistema:

1. **Adicionar mais pragas** ao seed baseado em feedback de usuários
2. **Criar seeds similares** para Culturas, Fornecedores, etc
3. **Painel de configuração** para empresas customizarem qual seed usar
4. **Documentação** em PDF com fotos de sintomas de pragas
5. **Integração** com base de dados regional de pragas

---

**Data de Criação**: 04/02/2026
**Versão**: 1.0
**Status**: Ativo
