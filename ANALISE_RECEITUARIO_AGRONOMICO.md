# 🌾 ANÁLISE - RECOMENDAÇÕES + RECEITUÁRIO AGRÔNOMO

## 🎯 O Cenário Que Você Descreveu

```
1. Agrônomo cria/edita um TALHÃO (campo)
   └─ Identifica uma PRAGA naquele talhão
   
2. Agrônomo cria um RECEITUÁRIO
   (documento técnico de recomendação de aplicação)
   └─ Sistema sugere automaticamente DEFENSIVOS recomendados
   
3. Agrônomo escolhe defensivo
   └─ Sistema preenche automaticamente:
      • Dosagem recomendada
      • Carência
      • Efetividade
      • Modo de aplicação
      
4. Receituário fica pronto com tudo preenchido
```

---

## ✅ Isso FUNCIONARIA SIM!

### Por Quê?

**Estrutura Já Existe:**
```
Talhao (campo)
  └─ Relacionado com Safra
  └─ Cultura plantada
  └─ Localização geográfica

Praga
  └─ Nome comum
  └─ Relacionada com culturas
  └─ Dados de controle

Produto (Defensivo)
  └─ 88 defensivos pré-cadastrados
  └─ Dados de dosagem
  └─ Classe agronômica

ProdutoDefensivoCultura
  └─ JÁ EXISTE!
  └─ Relaciona Produto + Cultura + Praga
  └─ Tem dosagem, carência, efetividade
```

**Falta Criar:**
```
RecomendacaoDefensivo
  └─ Relaciona Praga + Defensivo
  └─ Prioridade (1º opção, alternativa, etc)
  └─ Dados de aplicação

Receituario (Documento)
  └─ Campo (Talhao)
  └─ Praga identificada
  └─ Defensivo recomendado
  └─ Observações técnicas
```

---

## 🔄 Fluxo Completo

### Fase 1: Preparação (O que já existe)
```
✅ Agrônomo cadastra Talhão (com cultura)
✅ Sistema tem 88 Pragas pré-cadastradas
✅ Sistema tem 88 Defensivos pré-cadastrados
✅ Modelo ProdutoDefensivoCultura JÁ EXISTE
```

### Fase 2: Recomendações (O que vamos criar)
```
➕ Criar modelo RecomendacaoDefensivo
   └─ Praga → Defensivos recomendados
   └─ Ordenado por efetividade/custo
   
➕ Seed com ~100-150 recomendações
   └─ Lagarta → 5 defensivos recomendados
   └─ Ferrugem → 4 defensivos recomendados
   └─ etc
```

### Fase 3: Receituário (O que desenvolver)
```
➕ Criar modelo Receituario
   └─ Campo (Talhao)
   └─ Praga identificada
   └─ Defensivo selecionado
   └─ Observações
   
➕ Form inteligente de Receituário
   1. Seleciona Talhão
      ↓
   2. Seleciona Praga
      ↓ (busca automática)
   3. Sistema mostra defensivos recomendados
      ↓
   4. Agrônomo escolhe defensivo
      ↓ (preenche automático)
   5. Sistema carrega:
      • Dosagem mín/máx
      • Carência
      • Efetividade
      • Modo de aplicação
      ↓
   6. Agrônomo salva receituário
      ↓
   7. Receituário pronto!
```

---

## 🏗️ Modelo Proposto

### RecomendacaoDefensivo

```python
class RecomendacaoDefensivo(models.Model):
    """
    Relaciona uma Praga com os Defensivos recomendados
    """
    praga = ForeignKey('cadastros.Praga', on_delete=CASCADE)
    produto = ForeignKey('produtos.Produto', on_delete=CASCADE)
    
    # Dados de recomendação
    ordem = IntegerField(default=1)  # 1=melhor, 2=alternativa
    efetividade = IntegerField(default=85)  # 0-100 %
    custo_relativo = CharField(choices=[
        ('BAIXO', 'Baixo'),
        ('MEDIO', 'Médio'),
        ('ALTO', 'Alto'),
    ])
    
    # Dosagem recomendada
    dosagem_minima = DecimalField()
    dosagem_maxima = DecimalField()
    unidade = CharField()  # mL/100L, L/ha, etc
    
    # Aplicação
    carencia_minima = IntegerField()  # dias
    quantidade_maxima_aplicacoes = IntegerField()
    intervalo_reaplicacao = IntegerField()  # dias
    
    observacoes = TextField(blank=True)
    
    class Meta:
        unique_together = [['praga', 'produto']]
        ordering = ['praga', 'ordem']
```

### Receituario

```python
class Receituario(models.Model):
    """
    Receituário Agronômico
    Documento técnico de recomendação de defesa fitossanitária
    """
    STATUS_CHOICES = [
        ('RASCUNHO', 'Rascunho'),
        ('PENDENTE', 'Pendente Análise'),
        ('APROVADO', 'Aprovado'),
        ('REJEITADO', 'Rejeitado'),
    ]
    
    # Identificação
    numero = CharField(max_length=20, unique=True)
    data_criacao = DateTimeField(auto_now_add=True)
    
    # Contexto
    talhao = ForeignKey('cadastros.Talhao', on_delete=PROTECT)
    praga = ForeignKey('cadastros.Praga', on_delete=PROTECT)
    recomendacao = ForeignKey(RecomendacaoDefensivo, on_delete=PROTECT)
    
    # Aplicação
    data_aplicacao = DateField()
    horario_aplicacao = TimeField(null=True, blank=True)
    
    # Detalhes da aplicação
    dosagem = DecimalField()
    unidade_dosagem = ForeignKey('produtos.UnidadeMedida', on_delete=PROTECT)
    volume_calda = DecimalField(null=True, blank=True)  # litros/ha
    
    # Condições climáticas
    temperatura = DecimalField(null=True, blank=True)
    umidade = IntegerField(null=True, blank=True)  # %
    velocidade_vento = DecimalField(null=True, blank=True)  # km/h
    
    # Responsáveis
    agronomista = ForeignKey('usuarios.Usuario', on_delete=SET_NULL, null=True)
    
    # Status
    status = CharField(max_length=20, choices=STATUS_CHOICES, default='RASCUNHO')
    
    observacoes = TextField(blank=True)
    
    class Meta:
        verbose_name = 'Receituário Agronômico'
        verbose_name_plural = 'Receituários Agronômicos'
        ordering = ['-data_criacao']
    
    def __str__(self):
        return f"Receituário {self.numero} - {self.talhao}"
```

---

## 📋 Estimativa de Esforço

### Para Sistema Completo:

```
1. Criar modelo RecomendacaoDefensivo ......... 30 min
2. Admin para gerenciar recomendações ....... 30 min
3. Seed com ~150 recomendações ............ 1-2 horas
4. Criar modelo Receituario ............... 30 min
5. Form inteligente com autocomplete ....... 2-3 horas
6. API para carregamento dinâmico ......... 1-2 horas
7. Validações e regras de negócio ......... 1 hora
8. Testes ............................ 1 hora
─────────────────────────────────────────────────
TOTAL: 8-11 horas (~1 dia inteiro)
```

### Timeline:

```
DIA 1 (4 horas):
├─ Modelos (30 min)
├─ Admin (30 min)
├─ Form básico (2 horas)
└─ API (1 hora)

DIA 2 (4-5 horas):
├─ Seed com 150 recomendações (1-2 horas)
├─ Form avançado com autocomplete (2 horas)
├─ Validações (30 min)
└─ Testes (30 min)

DIA 3 (1-2 horas):
├─ Refinamentos
├─ Documentação
└─ Deploy
```

---

## 🎨 Interface Proposta

### Form de Criar Receituário

```html
<form method="post">
  
  <!-- Seção 1: Campo -->
  <fieldset>
    <h5>Campo (Talhão)</h5>
    <select name="talhao" id="selectTalhao" onchange="carregarPragas()">
      <option>-- Selecione um talhão --</option>
      <option value="1">Talhão 01 - Soja (100 ha)</option>
      <option value="2">Talhão 02 - Milho (50 ha)</option>
    </select>
  </fieldset>
  
  <!-- Seção 2: Praga Identificada -->
  <fieldset>
    <h5>Praga Identificada</h5>
    <select name="praga" id="selectPraga" onchange="carregarDefensivos()">
      <option>-- Selecione a praga --</option>
      <!-- Carregado dinamicamente -->
    </select>
  </fieldset>
  
  <!-- Seção 3: Defensivos Recomendados -->
  <fieldset>
    <h5>Defensivos Recomendados</h5>
    <div id="defensivosRecomendados">
      <!-- Carregado via AJAX -->
      <div class="alert">
        <h6>🥇 1º Opção - Deltamethrin 25 WP</h6>
        <p>Efetividade: 95% | Custo: Médio</p>
        <button type="button" onclick="selecionarDefensivo(1)">
          Selecionar
        </button>
      </div>
      
      <div class="alert">
        <h6>🥈 2º Opção - Pyrethrin 50 EC</h6>
        <p>Efetividade: 85% | Custo: Alto</p>
        <button type="button" onclick="selecionarDefensivo(2)">
          Selecionar
        </button>
      </div>
    </div>
  </fieldset>
  
  <!-- Seção 4: Dados de Aplicação (Auto-preenchidos) -->
  <fieldset id="dadosAplicacao" style="display:none">
    <h5>Dados de Aplicação</h5>
    
    <div class="form-group">
      <label>Dosagem Mínima</label>
      <input type="number" name="dosagem_minima" 
             id="dosagem_minima" readonly>
      <small>Preenchido automaticamente</small>
    </div>
    
    <div class="form-group">
      <label>Dosagem Máxima</label>
      <input type="number" name="dosagem_maxima" 
             id="dosagem_maxima" readonly>
    </div>
    
    <div class="form-group">
      <label>Dosagem Recomendada *</label>
      <input type="number" name="dosagem" placeholder="Ex: 35">
      <small>Entre {{ dosagem_min }} e {{ dosagem_max }}</small>
    </div>
    
    <div class="form-group">
      <label>Unidade</label>
      <input type="text" name="unidade" id="unidade" readonly>
    </div>
    
    <div class="form-group">
      <label>Carência (dias)</label>
      <input type="number" name="carencia" id="carencia" readonly>
      <small>Preenchido automaticamente</small>
    </div>
    
    <div class="form-group">
      <label>Data da Aplicação</label>
      <input type="date" name="data_aplicacao" required>
    </div>
    
    <div class="form-group">
      <label>Observações</label>
      <textarea name="observacoes" rows="4"></textarea>
    </div>
  </fieldset>
  
  <button type="submit" class="btn btn-primary">
    Criar Receituário
  </button>
</form>
```

### JavaScript para Carregar Dinamicamente

```javascript
// Quando seleciona talhão
document.getElementById('selectTalhao').addEventListener('change', async function() {
    const talhaoId = this.value;
    if (!talhaoId) return;
    
    // Busca pragas conhecidas para essa cultura
    const response = await fetch(`/api/talhao/${talhaoId}/pragas-possiveis/`);
    const pragas = await response.json();
    
    const selectPraga = document.getElementById('selectPraga');
    selectPraga.innerHTML = '<option>-- Selecione a praga --</option>';
    
    pragas.forEach(praga => {
        const option = document.createElement('option');
        option.value = praga.id;
        option.text = praga.nome_comum;
        selectPraga.appendChild(option);
    });
});

// Quando seleciona praga
document.getElementById('selectPraga').addEventListener('change', async function() {
    const pragaId = this.value;
    if (!pragaId) return;
    
    // Busca defensivos recomendados
    const response = await fetch(`/api/praga/${pragaId}/defensivos-recomendados/`);
    const recomendacoes = await response.json();
    
    const container = document.getElementById('defensivosRecomendados');
    container.innerHTML = '';
    
    recomendacoes.forEach((rec, index) => {
        const div = document.createElement('div');
        div.className = 'alert';
        div.innerHTML = `
            <h6>${['🥇 1º Opção', '🥈 2º Opção', '🥉 3º Opção'][index]} - ${rec.defensivo}</h6>
            <p>Efetividade: ${rec.efetividade}% | Dosagem: ${rec.dosagem_min}-${rec.dosagem_max} ${rec.unidade}</p>
            <button type="button" onclick="selecionarDefensivo(${rec.id}, ${rec.dosagem_min}, ${rec.dosagem_max}, '${rec.unidade}', ${rec.carencia})">
                Selecionar
            </button>
        `;
        container.appendChild(div);
    });
});

// Quando seleciona defensivo
function selecionarDefensivo(recId, dosMin, dosMax, unidade, carencia) {
    // Preenche automaticamente
    document.getElementById('dosagem_minima').value = dosMin;
    document.getElementById('dosagem_maxima').value = dosMax;
    document.getElementById('unidade').value = unidade;
    document.getElementById('carencia').value = carencia;
    
    // Mostra a seção de aplicação
    document.getElementById('dadosAplicacao').style.display = 'block';
    
    // Salva ID da recomendação
    document.getElementById('recomendacao_id').value = recId;
}
```

---

## 🎯 Quando Fazer?

### Timeline Recomendada:

```
HOJE/AMANHÃ:
└─ Implementar recomendações simples (3.5 horas)
   └─ Modal na praga

PRÓXIMA SEMANA:
└─ Criar modelo Receituario + Form (8-11 horas)
   └─ Integração completa com recomendações

SEMANA SEGUINTE:
└─ Refinamentos e testes
└─ Deploy em produção
```

### Minha Recomendação:

**Fase 1:** Recomendações com modal (~3.5h)
```
Agrônomo:
1. Va em /cadastros/pragas/
2. Clica "💊 Defensivos Recomendados"
3. Ve 4-5 defensivos com dosagem
4. Cria receituário manualmente
```

**Fase 2:** Receituário com AJAX (~8h)
```
Agrônomo:
1. Va em /receituarios/criar/
2. Seleciona Talhão
3. Seleciona Praga
4. Sistema lista defensivos automaticamente
5. Clica em um defensivo
6. Tudo preenche automático
7. So falta salvar
```

---

## 🚀 Próximos Passos

Quer que eu comece com:

### Opção A: Só Recomendações (Rápido)
```
3.5 horas
Modal na praga com defensivos recomendados
Agrônomo cria receituário depois manualmente
```

### Opção B: Tudo Integrado (Completo)
```
8-11 horas
Recomendações + Receituário com form inteligente
Agrônomo cria receituário em 2 minutos
```

### Opção C: Análise de Dados Primeiro
```
Quero revisar quais pragas aparecem mais
Ver quais defensivos existem
Definir as 150 recomendações com precisão
```

**Qual você prefere?**
