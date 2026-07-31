# Gestão do Sistema

## Dashboard (`/dashboard/`)

### Visão geral

Tela inicial do sistema para a maioria dos usuários: um resumo rápido da situação da empresa (contas a pagar vencidas, a receber em aberto, compras e vendas do mês, cadastros principais) com atalhos para os módulos mais usados.

### Tela: Dashboard Geral

<figure>
  <img src="screenshots/dashboard/01-geral.png" alt="Dashboard Geral">
  <figcaption>Indicadores do mês, ações necessárias (aprovações pendentes, mensagens não lidas) e acesso rápido aos módulos.</figcaption>
</figure>

## Empresas (`/empresas/`)

### Visão geral

Cadastro das empresas (tenants) do sistema — cada empresa é isolada das demais, e cada usuário só enxerga os dados da sua própria empresa (exceto superusuários, que têm visão de todas). Aqui também ficam **Funções/Roles** (perfis de permissão personalizáveis), **Planos** de assinatura e as **Preferências** da empresa.

### Tela: Lista de Empresas

<figure>
  <img src="screenshots/empresas/01-lista.png" alt="Lista de Empresas">
  <figcaption>Empresas visíveis para o usuário logado — um administrador de empresa vê apenas a própria; um superusuário vê todas.</figcaption>
</figure>

Criar uma nova empresa (botão **Nova Empresa**) é uma ação restrita a **superusuários** — um administrador comum de empresa não vê esse formulário, mesmo estando logado como Administrador da própria empresa.

### Tela: Painel Admin

<figure>
  <img src="screenshots/empresas/02-painel-admin.png" alt="Painel Admin">
  <figcaption>Painel administrativo da empresa.</figcaption>
</figure>

### Tela: Funções/Roles

<figure>
  <img src="screenshots/empresas/03-roles-lista.png" alt="Funções/Roles">
  <figcaption>Perfis de permissão (`/empresas/roles/`) que podem ser atribuídos a usuários, com permissões granulares por módulo.</figcaption>
</figure>

### Tela: Formulário de Nova Role

<figure>
  <img src="screenshots/empresas/07-role-form.png" alt="Formulário de Nova Role">
  <figcaption>Nome, descrição e templates de função sugeridos (Gerente de Compras, Supervisor de Estoque, Operador de Sistema, Analista Financeiro).</figcaption>
</figure>

**Como preencher:** dê um **Nome** descritivo (ex: "Gerente de Compras") e, opcionalmente, uma **Descrição** das responsabilidades. A tela sugere alguns **templates prontos** — clicar em um deles pré-preenche nome/descrição com um papel comum. A função criada é exclusiva da sua empresa (outras empresas não têm acesso a ela).

### Fluxo passo a passo — criar e usar uma função personalizada

1. Crie a Role com nome e descrição (ou parta de um template sugerido).
2. Salve — o próximo passo é **configurar as permissões** específicas da função (quais módulos/ações ela permite).
3. Se uma função existente for parecida com o que você precisa, use **Clonar** ou **Personalizar** em vez de criar do zero.
4. Atribua a função ao(s) usuário(s) desejado(s) em Usuários → editar usuário → campo Funções.

### Tela: Planos

<figure>
  <img src="screenshots/empresas/04-planos-lista.png" alt="Planos">
  <figcaption>Planos de assinatura disponíveis (`/empresas/planos/`), usados para limitar recursos por empresa.</figcaption>
</figure>

### Tela: Preferências da Empresa

<figure>
  <img src="screenshots/empresas/05-preferencias.png" alt="Preferências da Empresa">
  <figcaption>Configurações gerais da empresa (logo, dados cadastrais, preferências de exibição).</figcaption>
</figure>

### Dicas e erros comuns

- Antes de criar uma Role do zero, veja se um **template de permissões** existente já cobre a maior parte do que é preciso — é mais rápido clonar e ajustar.
- Precisa de uma nova empresa cadastrada no sistema? Isso exige um superusuário — solicite ao administrador da plataforma.

## Usuários (`/usuarios/`)

### Visão geral

Gerencia os usuários internos do sistema (tipos ADMIN, GERENTE, FUNC, PROD, VENDEDOR, FINANCEIRO), autenticação (incluindo 2FA) e logs de acesso.

### Tela: Lista de Usuários

<figure>
  <img src="screenshots/usuarios/01-lista.png" alt="Lista de Usuários">
  <figcaption>Usuários cadastrados (`/usuarios/`), com tipo de acesso e status.</figcaption>
</figure>

### Tela: Formulário de Novo Usuário

<figure>
  <img src="screenshots/usuarios/05-usuario-form.png" alt="Formulário de Novo Usuário">
  <figcaption>Formulário em 3 abas: Conta, Dados Pessoais, Senha.</figcaption>
</figure>

**Como preencher (aba Conta):**

| Campo | Obrigatório | Descrição |
|---|---|---|
| Empresa | Sim | Pré-preenchida; só é editável para superusuário |
| Usuário | Sim | Nome de login único |
| E-mail | Sim | |
| Tipo de Usuário | Sim | Ex: Funcionário, Administrador, Vendedor — define o escopo geral de acesso |
| Funções | Não | Lista de múltipla escolha combinando funções **específicas da empresa** (ex: "Gerente de Compras (AGRICOLA SALUTARIS S.A)") e funções **globais** disponíveis a qualquer empresa (ex: "Financeiro (Global)", "Vendedor (Global)") — controla as permissões granulares por módulo |
| Ativo | Não (padrão ligado) | Desligar em vez de excluir um usuário que saiu da empresa |

A aba **Dados Pessoais** guarda nome completo/telefone; **Senha** define a senha inicial (o usuário pode trocá-la depois em Meu Perfil).

### Fluxo passo a passo — criar um novo usuário com o acesso certo

1. Preencha Usuário, E-mail e **Tipo de Usuário**.
2. Atribua as **Funções** necessárias — combine uma função específica da empresa (se existir uma sob medida) com funções globais genéricas, conforme o que a pessoa vai operar no sistema.
3. Defina a senha inicial na aba Senha.
4. Oriente o novo usuário a ativar o **2FA** no primeiro acesso, em Meu Perfil.

### Tela: Tipos de Usuário

<figure>
  <img src="screenshots/usuarios/02-tipos-lista.png" alt="Tipos de Usuário">
  <figcaption>Tipos de usuário configuráveis (`/usuarios/tipos/`).</figcaption>
</figure>

### Tela: Logs de Login

<figure>
  <img src="screenshots/usuarios/03-registros-login.png" alt="Logs de Login">
  <figcaption>Histórico de acessos ao sistema (`/usuarios/registros/`), com abas de Registros, Anomalias e Alertas — útil para auditoria de segurança.</figcaption>
</figure>

### Tela: Meu Perfil

<figure>
  <img src="screenshots/usuarios/04-meu-perfil.png" alt="Meu Perfil">
  <figcaption>Dados do próprio usuário logado, troca de senha e configuração de autenticação em duas etapas (2FA).</figcaption>
</figure>

### Dicas e erros comuns

- Um usuário do tipo `PROD` (produtor) ou os tipos de portal são automaticamente restritos ao respectivo portal — não têm acesso ao painel administrativo interno.
- Ativar o 2FA em **Meu Perfil** gera códigos de backup — guarde-os, pois são a única forma de recuperar acesso se o dispositivo de autenticação for perdido.
- Um usuário sem nenhuma **Função** atribuída pode logar mas não enxerga a maioria dos módulos — o Tipo de Usuário sozinho não concede permissões granulares.

## Dashboard Executivo / Métricas (`/dashboard-executivo/`)

### Visão geral

Painel de KPIs de alto nível, pensado para visão gerencial/executiva: métricas consolidadas, consumo de recursos por empresa (relevante em ambientes com múltiplas empresas/planos) e alertas operacionais. O conteúdo completo (comparativo entre empresas, consumo por plano) é visível para **superusuários**; um administrador de empresa comum vê uma versão equivalente ao dashboard padrão da própria empresa.

### Tela: Dashboard Executivo

<figure>
  <img src="screenshots/metricas/01-dashboard-executivo.png" alt="Dashboard Executivo">
  <figcaption>KPIs principais da empresa.</figcaption>
</figure>

### Tela: Consumo de Recursos

<figure>
  <img src="screenshots/metricas/02-consumo-recursos.png" alt="Consumo de Recursos">
  <figcaption>Consumo de recursos por empresa — visão completa disponível para superusuários.</figcaption>
</figure>

### Tela: Alertas

<figure>
  <img src="screenshots/metricas/03-alertas.png" alt="Alertas">
  <figcaption>Alertas operacionais consolidados.</figcaption>
</figure>

## Portal do Cliente (`/portal/cliente/`)

### Visão geral

Portal de autoatendimento para os clientes da empresa, com login próprio (separado do login interno) e acesso restrito às informações do próprio cliente: posição financeira e documentos. Não aparece na sidebar interna — o cliente acessa diretamente pela URL do portal, geralmente com um link/credencial fornecido pela empresa.

| Tela | Path |
|---|---|
| Login do Portal | `/portal/cliente/login/` |
| Dashboard do Portal | `/portal/cliente/` |
| Financeiro (lista/detalhe) | `/portal/cliente/financeiro/` |
| Documentos | `/portal/cliente/documentos/` |

Estruturalmente equivalente aos demais portais satélites do sistema — **Portal do Fornecedor** e **Portal do Produtor** (acessados a partir do botão "criar acesso" na ficha do fornecedor/produtor, em Cadastros) e **Portal do Motorista** / **Portal do Campo** (a partir de Frota e Ordens de Serviço, respectivamente) — cada um com login e escopo de dados próprios, isolados do painel administrativo interno.

### Fluxo passo a passo — dar acesso de portal a um cliente/fornecedor/produtor

1. Abra a ficha do cliente/fornecedor/produtor em Cadastros.
2. Use o botão **Criar Acesso Portal** — isso gera um login vinculado àquele cadastro.
3. Envie o link/credencial ao parceiro externo.
4. Se precisar revogar, use **Bloquear Portal** na mesma ficha — o cadastro continua existindo, só o login externo é desativado.

### Dicas e erros comuns

- O acesso ao portal de um cliente/fornecedor/produtor pode ser **bloqueado** a qualquer momento a partir da ficha correspondente no sistema interno, sem excluir o cadastro.
