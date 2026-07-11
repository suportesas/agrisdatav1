# QUICK START - Sistema de Estoque Atualizado

## 🚀 Para Testar Agora

### Via Formulário Web (Recomendado)

1. **Acesse**: http://localhost:8000/estoque/entrada/
2. **Preencha**:
   - Tipo: ENTRADA (pré-preenchido)
   - Origem: Compra
   - Produto: "Fertilizante Ureia" (clique no select)
   - Unidade de Medida: Auto-preenchida com "KG"
   - Quantidade: 100
   - Lote: Deixe em branco
3. **Clique**: Salvar
4. **Resultado**: Veja o estoque atualizar em tempo real!

### Via Python (Para Debugging)

```python
from estoque.forms import EntradaEstoqueForm
from empresas.models import Empresa
from django.contrib.auth import get_user_model

User = get_user_model()
usuario = User.objects.first()
empresa = Empresa.objects.first()

form = EntradaEstoqueForm(data={
    'tipo': 'ENTRADA',
    'origem': 'COMPRA',
    'produto': 9,  # Fertilizante Ureia
    'unidade_medida': 1,  # KG
    'quantidade': '200',
    'lote': '',
    'justificativa': '',
}, empresa=empresa, usuario=usuario)

if form.is_valid():
    mov = form.save()
    print(f"Movimentacao {mov.id} criada!")
    print(f"Estoque atualizado automaticamente")
else:
    print(form.errors)
```

---

## 📊 Verificar Estoque

### Via Django Shell

```python
python manage.py shell

from produtos.models import Produto

produto = Produto.objects.get(nome='Fertilizante Ureia')
print(f"Estoque: {produto.estoque_atual} KG")
```

### Via SQL Direto

```sql
SELECT nome, estoque_atual 
FROM produtos_produto 
WHERE nome LIKE 'Fertilizante%';
```

---

## 🔄 Fluxos Suportados

### 1️⃣ Entrada Rápida (SEM Lote)
```
Ideal para: Entrada manual, compras pequenas, sem rastreabilidade
Tempo: Imediato (nenhuma aprovação necessária)
Atualização: Automática ao salvar formulário
```

### 2️⃣ Entrada com Lote (COM Rastreabilidade)
```
Ideal para: Pedidos de compra, controle PEPS/FIFO
Tempo: Via processo de recebimento
Atualização: Via .executar() com validação atomicamente
```

### 3️⃣ Saída (Sem Lote)
```
Ideal para: Vendas rápidas, consumo interno
Tempo: Imediato
Atualização: Automática ao salvar
```

---

## ✅ Checklist - Antes de Usar em Produção

- [ ] Testar entrada rápida (100 KG)
- [ ] Testar entrada + saída
- [ ] Testar fluxo de compra completo (Solicitação → Recebimento)
- [ ] Verificar estoque no dashboard
- [ ] Executar: `python manage.py recalcular_estoque`
- [ ] Fazer backup do banco de dados

---

## 🐛 Se Algo Não Funcionar

### Problema: "Estoque não atualiza"

**Solução**:
```bash
python manage.py recalcular_estoque
```

### Problema: "Campo Unidade de Medida vazio"

**Solução**: Verifique no navegador que o JavaScript está executando:
- Abra DevTools (F12)
- Console → Veja se há erros
- Recarregue a página

### Problema: "Erro ao salvar movimento"

**Solução**: Verifique se:
- Produto está ativo (campo `ativo=True`)
- Empresa está preenchida no formulário
- Usuário tem permissão

---

## 📚 Documentação Completa

Leia também:
- [ESTRATEGIA_ESTOQUE.md](./ESTRATEGIA_ESTOQUE.md) - Conceitos e decisões arquiteturais
- [FLUXOGRAMAS_ESTOQUE.md](./FLUXOGRAMAS_ESTOQUE.md) - Diagramas dos fluxos
- [RESUMO_CORRECCOES_ESTOQUE.md](./RESUMO_CORRECCOES_ESTOQUE.md) - Detalhes técnicos das mudanças
- [CONCLUSAO_VALIDACAO_ESTOQUE.md](./CONCLUSAO_VALIDACAO_ESTOQUE.md) - Testes realizados

---

## 🔗 URLs Úteis

| Funcionalidade | URL |
|---|---|
| Entrada de Estoque | /estoque/entrada/ |
| Lista de Movimentações | /estoque/movimentacoes/ |
| Detalhes de Lote | /estoque/lotes/{id}/ |
| Dashboard de Estoque | /estoque/dashboard/ |
| Gerenciar Armazéns | /estoque/armazens/ |

---

## 💡 Dicas Importantes

1. **Para Entrada Manual**: Use o formulário sem preencher "Lote"
2. **Para Rastreabilidade**: Use o fluxo de Pedido de Compra (com Lotes)
3. **Cálculo Automático**: Sempre SUM(ENTRADA) - SUM(SAIDA)
4. **Sem Aprovação**: Entrada sem lote é criada direto (PENDENTE)
5. **Com Validação**: Entrada com lote requer `executar()` e `@transaction.atomic`

---

## 📞 Suporte

Se encontrar problemas:

1. Verifique a terminal do servidor (erros aparecem lá)
2. Verifique DevTools do navegador (erros JavaScript)
3. Veja o arquivo de log do Django
4. Execute: `python manage.py test estoque` para testes automáticos

---

**Sistema Pronto para Uso!** ✅

Data: 02/02/2026  
Última atualização: Refatoração completa do sistema de estoque
