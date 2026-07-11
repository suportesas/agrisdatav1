
# 🌾 Sistema de Seed Automático de Pragas

## 📋 Visão Geral

Sistema multi-tenant para pré-cadastro automático de pragas agrícolas. Quando uma nova empresa é criada, ela recebe automaticamente uma base de dados com pragas comuns, podendo editar, adicionar ou remover conforme necessário.

## ✨ Características Principais

### 🔐 Isolamento Multi-Tenant
- ✅ Cada empresa tem seus próprios dados de pragas
- ✅ Empresas não podem acessar dados umas das outras
- ✅ Alterações em uma empresa não afetam as outras
- ✅ Cada empresa pode editar, adicionar ou deletar pragas independentemente

### 🚀 Automação
- ✅ Quando uma empresa é criada, pragas são adicionadas automaticamente via signal
- ✅ Não requer ação manual do usuário
- ✅ Agiliza o onboarding de novas empresas
- ✅ Pragas não são duplicadas se já existem

### 📊 Base de Dados Abrangente
A lista de seed contém **88 pragas** diferentes, incluindo:
- **Insetos**: 42 espécies (lepidópteros, dípteros, homópteros, hemípteros, coleópteros, etc)
- **Ácaros**: 5 espécies
- **Nematoides**: 3 espécies
- **Fungos**: 20 espécies
- **Bactérias**: 6 espécies
- **Vírus**: 8 espécies
- **Moluscos**: 3 espécies
- **Outros**: 4 espécies

## 🔄 Como Funciona

### 1️⃣ Criação Automática (Signal Django)

Quando uma nova empresa é criada:

```python
@receiver(post_save, sender=Empresa)
def seed_pragas_on_create(sender, instance, created, **kwargs):
    """Cria pragas pré-definidas quando uma Empresa é criada."""
    if not created:
        return
    
    from cadastros.pragas_seed import seed_pragas_for_company
    criadas, ignoradas = seed_pragas_for_company(instance)
```

**Fluxo:**
1. Nova empresa é salva no banco de dados
2. Signal `post_save` é disparado
3. Função `seed_pragas_for_company()` é chamada
4. Pragas do PRAGAS_SEED são criadas para essa empresa
5. Processo é idempotente (não duplica se já existem)

### 2️⃣ Seed Manual (Management Command)

Para fazer seed em empresas existentes:

```bash
# Seed em empresa específica
python manage.py seed_pragas --empresa-id 1

# Seed em todas as empresas
python manage.py seed_pragas --all

# Listar pragas disponíveis
python manage.py seed_pragas --list
```

### 3️⃣ Isolamento Multi-Tenant

Cada empresa tem ForeignKey para `Empresa`:

```python
class Praga(models.Model):
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='pragas',
    )
    nome_comum = models.CharField(max_length=150)
    nome_cientifico = models.CharField(max_length=200)
    ativa = models.BooleanField(default=True)
```

**Constraint Único:**
```python
UniqueConstraint(
    fields=['empresa', 'nome_comum'],
    name='unique_praga_empresa'
)
```
Garante que cada empresa só pode ter um registro de cada praga.

## 👤 Ações dos Usuários

Cada empresa pode realizar:

### ✏️ Editar Pragas
- Modificar nome comum
- Atualizar nome científico
- Ativar/desativar
- Adicionar descrições e informações agronômicas

### ➕ Adicionar Novas Pragas
- Criar pragas específicas de sua região
- Pragas que não estão no seed padrão
- Pragas regionais ou sazonais

### 🗑️ Deletar Pragas
- Remover pragas não relevantes
- Limpar a base conforme necessário
- Excluir pragas descontinuadas

### 🔍 Filtrar e Buscar
- Buscar por nome comum ou científico
- Filtrar por status (ativa/inativa)
- Paginação de resultados

## 📁 Estrutura de Arquivos

```
cadastros/
├── models.py              # Modelo Praga com multi-tenancy
├── pragas_seed.py         # 📋 Lista de pragas pré-definidas
├── views.py               # Views para CRUD de pragas
├── templates/
│   └── praga_list.html    # 🎨 Interface com botão "Como Fazer?"
└── management/
    └── commands/
        └── seed_pragas.py # 🔧 Command para seed manual

empresas/
└── signals.py             # Signal que dispara seed na criação
```

## 🧪 Testando o Sistema

### Teste 1: Criação Automática
```python
# Criar empresa (signal cria pragas automaticamente)
from empresas.models import Empresa, Plano

plano = Plano.objects.first()
empresa = Empresa.objects.create(
    nome='Minha Fazenda',
    plano=plano
)

# Verificar pragas criadas
from cadastros.models import Praga
pragas = Praga.objects.filter(empresa=empresa)
print(f"Pragas criadas: {pragas.count()}")  # Deve ser 88
```

### Teste 2: Isolamento Multi-Tenant
```python
# Empresa 1
empresa1 = Empresa.objects.create(nome='Empresa A')
praga1_count = Praga.objects.filter(empresa=empresa1).count()

# Empresa 2
empresa2 = Empresa.objects.create(nome='Empresa B')
praga2_count = Praga.objects.filter(empresa=empresa2).count()

# Ambas têm mesma quantidade de pragas
assert praga1_count == praga2_count == 88

# Editar praga em Empresa 1 não afeta Empresa 2
praga = Praga.objects.filter(empresa=empresa1).first()
praga.nome_comum = 'Nome Modificado'
praga.save()

# Empresa 2 não foi afetada
praga_emp2 = Praga.objects.filter(
    empresa=empresa2,
    nome_comum='Nome Modificado'
).exists()
assert not praga_emp2  # False - não existe em Empresa 2
```

### Teste 3: Seed Manual
```bash
# Executar seed em todas as empresas
python manage.py seed_pragas --all

# Executar seed em empresa específica
python manage.py seed_pragas --empresa-id 5

# Listar pragas disponíveis
python manage.py seed_pragas --list
```

## 📊 Dados Inclusos no Seed

### Insetos (42)
Lagarta-do-cartucho, Mosca-da-fruta, Mosca-branca, Pulgão-do-algodão, Percevejo-marrom, etc.

### Fungos (20)
Ferrugem, Oídio, Míldio, Mofo-cinzento, Antracnose, Septoriose, Fusariose, etc.

### Bactérias (6)
Murcha-bacteriana, Canela-preta, Mancha-angular, Mancha-bacteriana, etc.

### Vírus (8)
Mosaico-do-tomate, Enrolamento-da-folha, Vira-cabeça, Mosaico-do-milho, etc.

### Ácaros (5)
Ácaro-rajado, Ácaro-vermelho, Ácaro-branco, Ácaro-do-coco, etc.

### Nematoides (3)
Nematoide-das-galhas, Nematoide-do-cisto, Nematoide-das-lesões, etc.

### Moluscos (3)
Lesma-cinzenta, Caracol-gigante-africano, Caracol-marrom

### Outros (4)
Cochonilha-branca, Escama-de-São-José, etc.

## 🔧 Extensibilidade

### Adicionar Novas Pragas ao Seed

Edite `cadastros/pragas_seed.py`:

```python
PRAGAS_SEED = [
    # ... pragas existentes ...
    {
        'nome_comum': 'Nova Praga Regional',
        'nome_cientifico': 'Nouveaux pragaticus',
    },
]
```

Execute:
```bash
python manage.py seed_pragas --all
```

### Customizar por Plano

Futuro: Diferentes listas de seed por plano (Pequeno/Médio/Grande)

```python
# Não implementado, mas possível:
PRAGAS_SEED_PLANO_PEQUENO = [...]  # Subset
PRAGAS_SEED_PLANO_MEDIO = [...]    # Mais completo
PRAGAS_SEED_PLANO_GRANDE = [...]   # Completo + premium
```

## ✅ Benefícios

1. **Para o Usuário**
   - ✨ Agilidade no onboarding
   - 📊 Base inicial sólida de pragas
   - 🎯 Pode customizar para sua propriedade
   - 🔒 Dados isolados por empresa

2. **Para a Plataforma**
   - 🚀 Melhor experiência de novo usuário
   - 💰 Reduz tempo de setup
   - 📈 Aumenta engagement inicial
   - 🔐 Reforça isolamento multi-tenant

3. **Para Segurança**
   - 🔐 Cada empresa só vê suas pragas
   - 🛡️ Constraint de unicidade (empresa + nome)
   - 📝 Auditoria por cadastro_por
   - ⏰ Rastreamento de datas (criação/atualização)

## 🎯 Próximas Melhorias

- [ ] Interface para importar/exportar pragas
- [ ] Importação de arquivo CSV
- [ ] Sincronização com banco de dados regional de pragas
- [ ] Recomendações de controle por praga
- [ ] Histórico de alterações
- [ ] Relatórios de pragas por talhão
- [ ] Integração com alertas de sazonalidade

---

**Data:** 2025-02-04  
**Status:** ✅ Implementado e Testado  
**Multi-tenant:** ✅ Totalmente Isolado  
**Automático:** ✅ Via Signal Django
