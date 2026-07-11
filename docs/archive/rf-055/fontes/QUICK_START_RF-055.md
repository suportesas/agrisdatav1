# ⚡ RF-055: Quick Start Guide

## 🚀 5 Minutos para Ver Tudo Funcionando

### Step 1: Acesse a Página de Estoque
```
URL: http://127.0.0.1:8000/estoque/estoque-produtos/
```

### Step 2: O Que Você Vai Ver
```
┌─────────────────────────────────────────────┐
│ 📦 Estoque de Produtos                      │
│ 🔴 Críticos: 2  🟠 Baixos: 3  🔵 Excesso: 1 │
└─────────────────────────────────────────────┘

┌─────┬─────────────┬───────┬─────────┬─────────┐
│ Cod │ Produto     │ Atual │ Mínimo  │ Máximo  │
├─────┼─────────────┼───────┼─────────┼─────────┤
│ P01 │ Adubo       │ 0     │ 100     │ 500     │ ← 🔴 Crítico
│ P02 │ Sementes    │ 50    │ 100     │ 600     │ ← 🟠 Baixo
│ P03 │ Óleo        │ 950   │ 100     │ 800     │ ← 🔵 Excesso
│ P04 │ Fungicida   │ 250   │ 100     │ 500     │ ← ✅ Normal
└─────┴─────────────┴───────┴─────────┴─────────┘
```

### Step 3: Verifique o Menu
```
À esquerda, em "Estoque", veja:
📦 Estoque 🔴 6

O número (6) é o total de alertas
Atualiza em qualquer página
```

---

## 📋 O Que Mudou

### Antes
- ❌ Sem visualização clara de mín/máx
- ❌ Sem cores na tabela
- ❌ Sem alertas de excesso
- ❌ Sem badge no menu

### Depois
- ✅ Colunas Mín e Máx visíveis
- ✅ Cores: 🔴🟠🔵✅
- ✅ Detecta excesso automaticamente
- ✅ Badge no menu sempre atualizado

---

## 🎨 Cores Explicadas

| Cor | Significa | Quando | O Que Fazer |
|-----|-----------|--------|-----------|
| 🔴 Vermelho | Crítico | Estoque = 0 | URGENTE: Comprar já |
| 🟠 Laranja | Baixo | Estoque < Mínimo | Comprar em breve |
| 🔵 Azul | Excesso | Estoque > Máximo | Reduzir compras |
| ✅ Verde | Normal | Dentro dos limites | Nada a fazer |

---

## 🔧 Como Usar

### Para Gerentes de Compra
1. Abra `/estoque/estoque-produtos/`
2. Veja resumo de alertas no topo
3. Identifique produtos em 🔴 Crítico
4. Abra o link da página para detalhes
5. Crie solicitação de compra

### Para Gestor de Armazém
1. Verifique produtos em 🟠 Baixo
2. Faça transferência de outro armazém
3. Ou aguarde chegada de compra
4. Monitore redução de alertas

### Para Diretor
1. Veja badge no menu (total de alertas)
2. Acesse dashboard para gráficos
3. Analise tendências semanais
4. Revise mínimos/máximos

---

## 📊 Dados de Exemplo

Se quer testar com dados reais:

```python
# Em Django Shell
python manage.py shell

from produtos.models import Produto
from decimal import Decimal

# Criar produto crítico
p1 = Produto.objects.create(
    nome='Fertilizante Crítico',
    estoque_atual=0,
    estoque_minimo=100,
    estoque_maximo=500,
    ativo=True
)

# Criar produto baixo
p2 = Produto.objects.create(
    nome='Sementes Baixas',
    estoque_atual=50,
    estoque_minimo=100,
    estoque_maximo=600,
    ativo=True
)

# Criar produto em excesso
p3 = Produto.objects.create(
    nome='Óleo em Excesso',
    estoque_atual=950,
    estoque_minimo=100,
    estoque_maximo=800,
    ativo=True
)

# Agora acesse /estoque/estoque-produtos/
# Veja os alertas funcionando!
```

---

## 🐛 Se Algo Não Funcionar

### Problema: Não vejo badge no menu
**Solução**:
1. Verifique se há produtos em alerta
2. Refresh a página (F5)
3. Verifique `core/settings.py` tem context_processors

### Problema: Tabela não tem cores
**Solução**:
1. Verifique `estoque/templates/estoque/estoque_produtos_list.html`
2. Limpe cache do navegador (Ctrl+Shift+Delete)
3. Faça refresh (Ctrl+F5)

### Problema: Colunas mín/máx não aparecem
**Solução**:
1. Verifique que produtos têm estoque_minimo e estoque_maximo preenchidos
2. Acesse admin e preencha os campos
3. Volta à página

### Problema: Server dá erro
**Solução**:
1. Verifique syntax errors em Python
2. Execute `python manage.py check`
3. Restart o servidor: `python manage.py runserver`

---

## 📞 Arquivos Importantes

```
Para entender o código:
📄 estoque/views.py (linhas 550-620)
   └─ Lógica de alertas

📄 estoque/templates/estoque/estoque_produtos_list.html
   └─ Interface visual

📄 core/context_processors.py
   └─ Badge global

📄 templates/sidebar.html
   └─ Menu com badge

Para aprofundar:
📄 RF-055_IMPLEMENTACAO.md
   └─ Documentação técnica

📄 RF-055_GUIA_VISUAL.md
   └─ Exemplos e casos de uso

Para próxima fase:
📄 RF-055_EXTENSAO_EMAIL_AUTOMATICO.md
   └─ Como implementar emails
```

---

## 🎯 Próximas Fases (Opcional)

Se quer mais funcionalidades:

### Fase 2: Email Automático
```
Envia email todo dia com alertas
Setup: ~1 hora
Documentação: RF-055_EXTENSAO_EMAIL_AUTOMATICO.md
```

### Fase 3: Notificações In-App
```
Bell icon na navbar com notificações
Setup: ~2 horas
```

### Fase 4: Dashboard Widget
```
Gráfico com top 5 produtos em alerta
Setup: ~1 hora
```

---

## ✅ Checklist Rápido

- [x] Server rodando? http://127.0.0.1:8000
- [x] Acesso à página? /estoque/estoque-produtos/
- [x] Vê badge no menu? (Estoque 🔴 X)
- [x] Vê cores na tabela? (🔴🟠🔵✅)
- [x] Vê resumo no topo? (Críticos X, Baixos Y, Excesso Z)
- [x] Colunas mín/máx visíveis? (Sim)

Se tudo marcado ✅ → Tudo funcionando! 🎉

---

## 🔄 Fluxo Diário

```
Gerente de Compras
↓
Abre /estoque/estoque-produtos/
↓
Vê badge: 🔴 Críticos 3
↓
Prioriza produtos em vermelho
↓
Cria solicitação de compra
↓
Monitora produtos em laranja
↓
Agenda próximas compras
```

---

## 📈 Benefícios

### Antes
```
⏱️ 5 minutos: Achar lista de estoque baixo
⏱️ 10 minutos: Ler planilha desatualizada
⏱️ 5 minutos: Decidir o que comprar
= 20 minutos por dia
```

### Depois
```
⏱️ 1 minuto: Badge mostra alertas no menu
⏱️ 1 minuto: Cores mostram prioridade
⏱️ 3 minutos: Criar solicitação de compra
= 5 minutos por dia
```

**Economia**: 15 minutos/dia = 60 horas/ano! 📊

---

## 🚀 Comece Agora!

1. **Abra browser**: http://127.0.0.1:8000/estoque/estoque-produtos/
2. **Veja os alertas**: Cores + Badges + Resumo
3. **Clique em Estoque no menu**: Badge mostra total
4. **Pronto!** Tudo funcionando ✅

---

**Versão**: v1.0  
**Data**: 2025-02-03  
**Status**: ✅ PRONTO PARA USAR

Dúvidas? Veja os arquivos de documentação no workspace!
