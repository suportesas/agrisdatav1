# Módulo de Produtos

## Relacionamento Categoria → Subcategoria

O módulo de produtos possui um relacionamento hierárquico entre Categorias e Subcategorias:

### Estrutura

```
Categoria (Fertilizante)
  ├─ Subcategoria (Químico)
  ├─ Subcategoria (Orgânico)
  ├─ Subcategoria (Foliar)
  └─ Subcategoria (Mineral)

Categoria (Defensivo)
  ├─ Subcategoria (Herbicida)
  ├─ Subcategoria (Inseticida)
  ├─ Subcategoria (Fungicida)
  └─ Subcategoria (Acaricida)

Categoria (Sementes)
  ├─ Subcategoria (Soja)
  ├─ Subcategoria (Milho)
  └─ Subcategoria (Trigo)
```

### Funcionalidades

#### 1. Filtro Dinâmico no Formulário de Produto

Quando você seleciona uma **Categoria** no formulário de produto, o campo **Subcategoria** é automaticamente filtrado para mostrar apenas as subcategorias pertencentes àquela categoria.

**Como funciona:**
- Ao carregar a página, todas as subcategorias são salvas no JavaScript
- Quando você seleciona uma categoria, o JavaScript filtra as opções de subcategoria
- Apenas subcategorias da categoria selecionada são exibidas
- Se você limpar a categoria, todas as subcategorias voltam a ser exibidas

#### 2. Listagem de Subcategorias

Na lista de subcategorias ([/produtos/subcategorias/](http://127.0.0.1:8000/produtos/subcategorias/)), você pode ver:
- Nome da Categoria à qual a subcategoria pertence
- Código da subcategoria
- Nome da subcategoria
- Status (Ativo/Inativo)

#### 3. Criação de Subcategorias

Ao criar uma nova subcategoria, é obrigatório selecionar a categoria pai.

### Exemplos de Uso

1. **Criar uma categoria:**
   - Acesse: [/produtos/categorias/novo/](http://127.0.0.1:8000/produtos/categorias/novo/)
   - Preencha: Código, Nome, Descrição

2. **Criar subcategorias:**
   - Acesse: [/produtos/subcategorias/novo/](http://127.0.0.1:8000/produtos/subcategorias/novo/)
   - Selecione a categoria pai
   - Preencha: Código, Nome, Descrição

3. **Criar produto com filtro automático:**
   - Acesse: [/produtos/novo/](http://127.0.0.1:8000/produtos/novo/)
   - Na aba "Geral", selecione uma Categoria
   - O campo Subcategoria mostrará apenas subcategorias daquela categoria
   - Selecione a subcategoria desejada

### Dados de Exemplo

Execute o script para criar categorias e subcategorias de exemplo:

```bash
python criar_exemplos_produtos.py
```

Este script cria:
- 3 categorias (Fertilizante, Defensivo, Sementes)
- 11 subcategorias relacionadas

### Modelo de Dados

**Categoria:**
- `codigo`: Código único (ex: FERT, DEF, SEM)
- `nome`: Nome da categoria
- `descricao`: Descrição detalhada
- `ativo`: Status ativo/inativo

**SubCategoria:**
- `categoria`: ForeignKey para Categoria (relação muitos-para-um)
- `codigo`: Código único (ex: FERT-QUIM, DEF-HERB)
- `nome`: Nome da subcategoria
- `descricao`: Descrição detalhada
- `ativo`: Status ativo/inativo

**Related Name:**
- `categoria.subcategorias.all()` retorna todas as subcategorias de uma categoria

### Tecnologias Utilizadas

- **Backend:** Django ORM com relacionamento ForeignKey
- **Frontend:** JavaScript vanilla para filtro dinâmico
- **Widget Personalizado:** `SubCategoriaSelect` adiciona atributos `data-categoria-id` nas opções HTML
