# ANÁLISE: Separação de Menus por Tipo de Usuário

## PROBLEMA ATUAL

Não existe separação correta entre:
- **Superuser Admin** (is_superuser=True, empresa=NULL)
- **Empresa Admin** (is_superuser=False, tipo='ADMIN', empresa=id)
- **Operador** (is_superuser=False, tipo='OPERADOR', empresa=id)

---

## O QUE DEVERIA APARECER

### 1️⃣ SUPERUSER ADMIN (Gestor da Plataforma SaaS)
```
✅ Dashboard
   - Geral
   - Estoque
   - Compras
   - Rastreamento

✅ GESTÃO DO SISTEMA
   - Empresas (listar, criar, planos, funções)
   - Grupos Corporativos (listar, criar)
   - Dashboard Executivo (KPIs, Consumo, Alertas)

✅ Usuários (gerenciar usuários GLOBAIS)
   - Listar
   - Novo Usuário
   - Logs de Login

❌ TODO O OPERACIONAL (Agro, Cadastros, etc)
```

### 2️⃣ EMPRESA ADMIN (Gerente de Empresa Contratante)
```
✅ Dashboard
   - Geral
   - Estoque
   - Compras
   - Rastreamento

✅ GESTÃO DA EMPRESA
   - Configurações
     - Minha Empresa
     - Funções/Cargos
   - Minha Empresa (atalho)

✅ Usuários (gerenciar usuários DA EMPRESA)
   - Listar (apenas da sua empresa)
   - Novo Usuário (apenas para sua empresa)
   - Logs de Login

✅ TODO O OPERACIONAL (Agro, Cadastros, etc)
   - Agro (Fazendas, Áreas, Talhões, etc)
   - Cadastros (Funcionários, Clientes, Fornecedores, etc)
   - Patrimônio
   - Produtos
   - ... (todos os módulos operacionais)

❌ NÃO deve ver: Empresas, Grupos Corporativos, Dashboard Executivo
```

### 3️⃣ OPERADOR DA EMPRESA (Usuário Normal)
```
✅ Dashboard
   - Geral
   - Estoque
   - Compras
   - Rastreamento

✅ Minha Empresa (atalho direto)

✅ OPERACIONAL (parcial, conforme permissões)
   - Agro (Fazendas, Áreas, Talhões, etc)
   - Cadastros (apenas os que tem acesso)
   - Produtos (visualização)

❌ NÃO deve ver: Usuários (não gerencia usuários)
❌ NÃO deve ver: Configurações/GESTÃO DA EMPRESA
```

---

## PROBLEMAS NA sidebar.html IDENTIFICADOS

### ❌ PROBLEMA 1: Linha ~119
```html
{% if user.is_staff or user.is_superuser %}
<li class="nav-item has-submenu">
  <a href="#" class="nav-link">
    <i class="bi bi-people"></i>
    <span>Usuários</span>
```

**ERRO**: `is_staff` está sendo usado para controlar acesso a Usuários globais!
- Qualquer admin de empresa tem is_staff=True
- Isso permite que vejam e gerenciem usuários GLOBAIS (não apenas da empresa)

**SOLUÇÃO**: Deve ser apenas `{% if user.is_superuser %}`

---

### ✅ PROBLEMA 2: Menu OPERACIONAL (sem condição)
```html
<li class="nav-section">
  <span>OPERACIONAL</span>
</li>

<li class="nav-item has-submenu">
  <a href="#" class="nav-link">
    <span>Agro</span>
```

**PROBLEMA**: Todos os menus OPERACIONAIS não têm nenhuma condição!
- Superuser vê menus operacionais (DEVERIA ver? Ou só dados agregados?)
- Empresa Admin vê menus operacionais (CORRETO)
- Operador vê menus operacionais (CORRETO, parcialmente)

**DECISÃO**: 
- Se Superuser vir OPERACIONAL: você QUER? Ou isso é exclusivo para empresas?
- Recomendação: Superuser NÃO deveria ver OPERACIONAL (é de empresa específica)

---

## ESTRUTURA PROPOSTA (sidebar.html corrigida)

```html
<!-- 1. Dashboard (TODOS veem) -->
<li class="nav-item has-submenu">
  <a href="#" class="nav-link">
    <i class="bi bi-speedometer2"></i>
    <span>Dashboard</span>
  </a>
  <ul class="nav-submenu">
    <li><a href="...">Geral</a></li>
    ...
  </ul>
</li>

<!-- 2. GESTÃO DO SISTEMA (APENAS SUPERUSER) -->
{% if user.is_superuser %}
  <li class="nav-section"><span>GESTÃO DO SISTEMA</span></li>
  <li class="nav-item has-submenu">
    <a href="#"><span>Empresas</span></a>
    <ul class="nav-submenu">
      <li><a href="...">Listar</a></li>
      ...
    </ul>
  </li>
  <li class="nav-item has-submenu">
    <a href="#"><span>Grupos Corporativos</span></a>
    ...
  </li>
  <li class="nav-item has-submenu">
    <a href="#"><span>Dashboard Executivo</span></a>
    ...
  </li>
  <!-- Usuários GLOBAIS -->
  <li class="nav-item has-submenu">
    <a href="#"><span>Usuários</span></a>
    <ul class="nav-submenu">
      <li><a href="usuarios:usuario_list">Listar (GLOBAIS)</a></li>
      <li><a href="usuarios:usuario_create">Novo</a></li>
      ...
    </ul>
  </li>
{% endif %}

<!-- 3. GESTÃO DA EMPRESA (EMPRESA ADMIN APENAS) -->
{% if not user.is_superuser and user.empresa %}
  <li class="nav-section"><span>GESTÃO DA EMPRESA</span></li>
  
  {% if user.is_admin_empresa %}
    <li class="nav-item has-submenu">
      <a href="#"><span>Configurações</span></a>
      <ul class="nav-submenu">
        <li><a href="...">Minha Empresa</a></li>
        <li><a href="...">Funções/Cargos</a></li>
      </ul>
    </li>
  {% endif %}
  
  {% if not user.is_admin_empresa %}
    <li class="nav-item">
      <a href="..."><span>Minha Empresa</span></a>
    </li>
  {% endif %}
  
  <!-- Usuários DA EMPRESA -->
  <li class="nav-item has-submenu">
    <a href="#"><span>Usuários</span></a>
    <ul class="nav-submenu">
      <li><a href="usuarios:usuario_list_empresa">Listar (DA EMPRESA)</a></li>
      <li><a href="usuarios:usuario_create_empresa">Novo</a></li>
      ...
    </ul>
  </li>
{% endif %}

<!-- 4. OPERACIONAL (APENAS EMPRESA - não superuser) -->
{% if not user.is_superuser and user.empresa %}
  <li class="nav-section"><span>OPERACIONAL</span></li>
  <li class="nav-item has-submenu">
    <a href="#"><span>Agro</span></a>
    ...
  </li>
  <!-- Todos os outros menus operacionais -->
{% endif %}
```

---

## AÇÕES NECESSÁRIAS

### Opção A: Correção Imediata (Sem views novas)
1. ✅ Mudar condição de Usuários: `{% if user.is_superuser %}` (linha ~119)
2. ✅ Envolver OPERACIONAL em: `{% if not user.is_superuser and user.empresa %}`
3. ✅ Isso resolve 90% do problema

### Opção B: Correção Completa (Com views novas)
1. Criar 2 views para Usuários:
   - usuários_globais (apenas superuser)
   - usuários_empresa (empresa admin)
2. Criar 2 URLs diferentes
3. Usar URLs diferentes na sidebar por tipo de user

Qual você prefere? **A (rápida) ou B (completa)?**
