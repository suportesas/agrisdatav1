# 📋 ANÁLISE - RECOMENDAÇÕES AUTOMÁTICAS DE DEFENSIVOS POR PRAGA

## 🎯 O Que Seria Necessário

### 1. Base de Dados - Mapeamento Praga ↔ Defensivo

```python
# Exemplo da estrutura necessária:
RECOMENDACOES_DEFENSIVOS = {
    'Lagarta-do-cartucho': {  # nome_comum da Praga
        'defensivos': [
            {
                'nome': 'Deltamethrin 25 WP',
                'dosagem_minima': 25,
                'dosagem_maxima': 50,
                'unidade': 'mL/100L',
                'carencia': 7,
                'efetividade': 95,  # %
                'custo_relativo': 'médio',
            },
            {
                'nome': 'Pyrethrin 50 EC',
                'dosagem_minima': 1,
                'dosagem_maxima': 2,
                'unidade': 'L/ha',
                'carencia': 3,
                'efetividade': 85,
                'custo_relativo': 'alto',
            },
            # ... mais defensivos
        ]
    },
    'Ferrugem': {
        'defensivos': [
            {
                'nome': 'Azoxystrobin 250 SC',
                'dosagem_minima': 200,
                'dosagem_maxima': 400,
                'unidade': 'mL/ha',
                'carencia': 14,
                'efetividade': 98,
                'custo_relativo': 'médio',
            },
            # ... mais defensivos
        ]
    },
}
```

---

## 🔧 Arquitetura Necessária

### Opção 1: Tabela de Relacionamento (Recomendado)

```python
# Novo modelo
class RecomendacaoDefensivo(models.Model):
    """
    Recomendação de qual defensivo usar contra qual praga
    """
    praga = ForeignKey('cadastros.Praga', on_delete=CASCADE)
    produto = ForeignKey('produtos.Produto', on_delete=CASCADE)
    
    # Dados de recomendação
    dosagem_minima = DecimalField()
    dosagem_maxima = DecimalField()
    unidade_dosagem = ForeignKey(UnidadeMedida)
    
    carencia_minima = IntegerField()  # dias
    efetividade = IntegerField(default=85)  # %
    custo_relativo = CharField(choices=[('BAIXO', 'Baixo'), ('MÉDIO', 'Médio'), ('ALTO', 'Alto')])
    
    # Prioridade
    ordem_recomendacao = IntegerField(default=1)  # 1=melhor, 2=alternativa, etc
    
    # Observações
    observacoes = TextField(blank=True)
    
    class Meta:
        unique_together = [['praga', 'produto']]
        ordering = ['praga', 'ordem_recomendacao']
```

**Vantagens:**
- Flexível e escalável
- Fácil editar recomendações no admin
- Permite histórico (adicionar campo `created_at`)
- Permite diferentes efetividades por defensivo

**Tempo:** ~2-3 horas

---

### Opção 2: Arquivo de Seed (Similar a Pragas/Defensivos)

```python
# produtos/recomendacoes_seed.py
RECOMENDACOES_SEED = [
    {
        'praga_nome': 'Lagarta-do-cartucho',
        'defensivo_nome': 'Deltamethrin 25 WP',
        'dosagem_minima': 25,
        'dosagem_maxima': 50,
        'unidade': 'mL/100L',
        'carencia': 7,
        'efetividade': 95,
        'ordem': 1,  # 1=melhor opção
    },
    {
        'praga_nome': 'Lagarta-do-cartucho',
        'defensivo_nome': 'Pyrethrin 50 EC',
        'dosagem_minima': 1,
        'dosagem_maxima': 2,
        'unidade': 'L/ha',
        'carencia': 3,
        'efetividade': 85,
        'ordem': 2,  # Alternativa
    },
    # ... centenas de recomendações
]
```

**Vantagens:**
- Rápido de implementar
- Similar ao sistema de pragas/defensivos
- Fácil versionamento

**Desvantagens:**
- Arquivo muito grande (1000+ linhas)
- Menos flexível para edições

**Tempo:** ~3-4 horas

---

## 🎨 Interface de Apresentação

### Opção 1: Modal na Praga (Simples)

```html
<!-- cadastros/praga/praga_list.html -->
<button class="btn btn-warning" 
        data-bs-toggle="modal" 
        data-bs-target="#modalDefensivosRecomendados">
  💊 Ver Defensivos Recomendados
</button>

<div class="modal" id="modalDefensivosRecomendados">
  <div class="modal-body">
    <h5>Defensivos Recomendados para {{ praga.nome_comum }}</h5>
    
    <div class="table-responsive">
      <table class="table">
        <thead>
          <tr>
            <th>Defensivo</th>
            <th>Dosagem</th>
            <th>Carência</th>
            <th>Efetividade</th>
            <th>Ação</th>
          </tr>
        </thead>
        <tbody>
          {% for rec in recomendacoes %}
          <tr>
            <td>{{ rec.defensivo.nome }}</td>
            <td>{{ rec.dosagem_minima }}-{{ rec.dosagem_maxima }} {{ rec.unidade }}</td>
            <td>{{ rec.carencia }} dias</td>
            <td>
              <div class="progress">
                <div class="progress-bar" style="width: {{ rec.efetividade }}%">
                  {{ rec.efetividade }}%
                </div>
              </div>
            </td>
            <td>
              <a href="{% url 'editar_defensivo' rec.defensivo.id %}" 
                 class="btn btn-sm btn-primary">
                Ver Detalhes
              </a>
            </td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </div>
</div>
```

**Tempo:** ~1-2 horas

---

### Opção 2: Página Dedicada (Avançado)

```
/cadastros/pragas/<id>/defensivos-recomendados/

Mostra:
✅ Top 3 defensivos recomendados (com badge "Melhor opção")
✅ Alternativas (com badge "Alternativa")
✅ Comparação de custos
✅ Simulação de efetividade
✅ Integração com histórico de aplicações
✅ Cálculo automático de dosagem
```

**Tempo:** ~4-6 horas

---

## 🔍 Funcionalidade de Busca

### AJAX - Buscar Defensivos para Praga

```javascript
// static/js/recomendacoes.js
document.getElementById('selectPraga').addEventListener('change', async function() {
    const pragaId = this.value;
    
    if (!pragaId) return;
    
    const response = await fetch(
        `/api/recomendacoes/praga/${pragaId}/defensivos/`
    );
    const data = await response.json();
    
    // Renderizar tabela
    const tbody = document.getElementById('defensivosTable');
    tbody.innerHTML = '';
    
    data.recomendacoes.forEach(rec => {
        const row = `
            <tr>
                <td>${rec.defensivo}</td>
                <td>${rec.dosagem_minima}-${rec.dosagem_maxima} ${rec.unidade}</td>
                <td>${rec.carencia} dias</td>
                <td>
                    <span class="badge badge-success">${rec.efetividade}%</span>
                </td>
            </tr>
        `;
        tbody.innerHTML += row;
    });
});
```

**Tempo:** ~2-3 horas

---

## 🔌 API REST (Opcional mas Útil)

```python
# api/views.py
class RecomendacoesDefensivosView(APIView):
    """
    GET /api/recomendacoes/praga/<praga_id>/defensivos/
    
    Retorna lista de defensivos recomendados para uma praga
    """
    def get(self, request, praga_id):
        recomendacoes = RecomendacaoDefensivo.objects.filter(
            praga_id=praga_id
        ).select_related('produto', 'praga').order_by('ordem_recomendacao')
        
        data = {
            'praga': {
                'id': recomendacoes.first().praga.id,
                'nome': recomendacoes.first().praga.nome_comum,
            },
            'recomendacoes': [
                {
                    'defensivo': r.produto.nome,
                    'dosagem_minima': str(r.dosagem_minima),
                    'dosagem_maxima': str(r.dosagem_maxima),
                    'unidade': r.unidade_dosagem.nome,
                    'carencia': r.carencia_minima,
                    'efetividade': r.efetividade,
                    'custo': r.custo_relativo,
                    'ordem': r.ordem_recomendacao,
                }
                for r in recomendacoes
            ]
        }
        return Response(data)
```

**Tempo:** ~1-2 horas

---

## 📊 Estimativa Completa de Esforço

### Cenário 1: Simples (Recomendado para começar)

```
✅ Criar modelo RecomendacaoDefensivo ......... 30 min
✅ Admin para gerenciar recomendações ....... 30 min
✅ Seed com ~100 recomendações iniciais .... 1 hora
✅ Modal na interface de praga ............ 1 hora
✅ Verificação e testes ................... 30 min
─────────────────────────────────────────────────
TOTAL: 3.5 horas
```

### Cenário 2: Moderado (Mais funcional)

```
✅ Tudo do Cenário 1 ........................ 3.5 horas
✅ API REST para busca ...................... 2 horas
✅ AJAX para carregamento dinâmico ......... 1.5 horas
✅ Documentação ............................ 1 hora
─────────────────────────────────────────────────
TOTAL: 8 horas
```

### Cenário 3: Completo (Com todos os recursos)

```
✅ Tudo do Cenário 2 ........................ 8 horas
✅ Página dedicada com comparação ......... 3 horas
✅ Histórico de recomendações ............ 2 horas
✅ Cálculo inteligente de dosagem ....... 2 horas
✅ Testes automatizados .................. 2 horas
────────────────────────────────────────────────
TOTAL: 17 horas (~2-3 dias de trabalho)
```

---

## 🗂️ Estrutura de Dados Necessária

### Dados de Recomendação (~100-150 registros iniciais)

```
Pragas com Recomendações:
├─ Lagarta-do-cartucho → 5-7 defensivos recomendados
├─ Ferrugem → 4-5 defensivos recomendados
├─ Oídio → 3-4 defensivos recomendados
├─ Afídeo → 4-5 defensivos recomendados
└─ ... (para cada praga, 2-7 defensivos)

Total de recomendações: ~150-200 relacionamentos

Onde buscar dados:
✅ Bulas de defensivos
✅ Recomendações MAPA
✅ Documentos técnicos de empresas
✅ Pesquisa agrícola
```

---

## 🚀 Quando Pode Ser Feito?

### Timeline Sugerida:

```
IMEDIATO (Esta semana):
└─ Implementar Cenário 1 (3.5 horas) ← Recomendado!
   └─ Rápido, prático, já funciona

PRÓXIMA SEMANA:
└─ Expandir para Cenário 2 (8 horas total)
   └─ Mais polido, com API

MÊS QUE VEM:
└─ Cenário 3 (17 horas total)
   └─ Todas as funcionalidades avançadas
```

---

## 💡 Minha Recomendação

### Fase 1: Comece com Cenário 1 (Hoje ou Amanhã)

**Por quê?**
- Rápido (3.5 horas)
- Funciona perfeitamente
- Usuários veem valor imediato
- Fácil de expandir depois

**Resultado:**
```
Usuário vai para uma praga (ex: "Ferrugem")
↓
Clica botão "💊 Ver Defensivos Recomendados"
↓
Modal abre mostrando 4-5 defensivos recomendados
↓
Com dosagem, carência, efetividade
↓
Pode clicar para ver detalhes de cada defensivo
```

### Fase 2: Cenário 2 (Próxima semana)

**Adiciona:**
- Busca dinâmica (AJAX)
- API para integração futura
- Melhor UX

### Fase 3: Cenário 3 (Mês que vem)

**Adiciona:**
- Página dedicada
- Comparação avançada
- Cálculos inteligentes

---

## 📝 Próximos Passos

### Se quer começar hoje:
```bash
1. Criar modelo RecomendacaoDefensivo
2. Adicionar ao admin
3. Criar ~100 recomendações iniciais
4. Adicionar modal na interface
5. Testar

Tempo: ~3.5 horas
```

### Se quer que eu implemente:

Posso criar:
1. ✅ Modelo e migrations
2. ✅ Admin interface
3. ✅ Seed com 100+ recomendações
4. ✅ Modal na praga_list.html
5. ✅ Documentação

**Tempo:** ~1-2 horas de trabalho

---

## 🎯 Decisão Necessária

Você quer que eu:

### Opção A: Implementar Cenário 1 agora?
```
✅ Rápido (1-2 horas)
✅ Funcional
✅ Usuários felizes
✅ Base para expansão depois
```

### Opção B: Só planejamento + dados para depois?
```
✅ Você analisa com calma
✅ Reúne dados de recomendações
✅ Define prioridades
✅ Implementa quando estiver pronto
```

### Opção C: Cenário 2 completo?
```
✅ Mais completo
✅ Com API já pronta
✅ Melhor UX
✅ Tempo: 5-6 horas
```

**Qual você prefere?**
