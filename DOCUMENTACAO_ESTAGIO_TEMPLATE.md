# Documentação: Sistema de Estágios Template

## 📋 Visão Geral

O sistema de **Estágios Template** automatiza a população de estágios de desenvolvimento de pragas para novas empresas, oferecendo um diferencial competitivo:

✅ **Onboarding automático** - Novas empresas já iniciam com estágios padrão configurados  
✅ **Customização independente** - Cada empresa pode editar/excluir/criar seus estágios livremente  
✅ **Rastreamento de origem** - Mantém referência ao template original para análise  
✅ **Reutilização de conhecimento** - Base de dados continuamente melhorada  

---

## 🏗️ Arquitetura Técnica

### Modelo de Dados

```python
class EstagioDesenvolvimento(models.Model):
    # Novo para templates:
    eh_template: BooleanField        # True = é um template padrão do sistema
    template_original: ForeignKey    # Referência ao template de origem
    empresa: ForeignKey              # Null para templates, ID para cópias
```

**Estados possíveis:**
- `eh_template=True, empresa=None` → Template padrão (criado via comando)
- `eh_template=False, empresa=EMPRESA, template_original=TEMPLATE` → Cópia para empresa
- `eh_template=False, empresa=EMPRESA, template_original=None` → Criado pela empresa

### Signal Django

```python
@receiver(post_save, sender='empresas.Empresa')
def copiar_estagios_template_para_nova_empresa(sender, instance, created, **kwargs)
```

Quando uma nova Empresa é criada, este signal:
1. Localiza todos os estágios com `eh_template=True, empresa=None`
2. Para cada template, cria uma cópia para a nova empresa
3. Marca a cópia com `template_original` para rastreamento

---

## 📊 Dados de Exemplo

Dois grupos de estágios foram pré-carregados:

### 1. Lagarta-do-cartucho (8 estágios)
- Ovo (2-4 dias)
- Larva 1º ínstar (2-3 dias)
- Larva 2º ínstar (2-3 dias)
- Larva 3º ínstar (3-5 dias) ⭐ **Crítico**
- Larva 4º ínstar (3-5 dias) ⭐ **Crítico**
- Larva 5º/6º ínstar (4-7 dias) ⭐ **Crítico** - Mais destrutivo
- Pupa (5-14 dias)
- Adulto/Mariposa (10-20 dias)

### 2. Podridão Negra dos Frutos (4 estágios/lesões)
- Esporos dormentes (30-365 dias)
- Lesão inicial (1-3 dias)
- Lesão necrótica em expansão (3-7 dias) ⭐ **Crítico**
- Esporulação (5-10 dias) ⭐ **Crítico**

---

## 🚀 Uso

### 1. Criar Templates (Admin)
```bash
# Popula estágios padrão no banco (precisa ser feito UMA VEZ)
py manage.py popular_estagios_template
```

**Saída esperada:**
```
Populando estágios template padrão
📋 Processando: Lagarta-do-cartucho
  ✨ [CRIADO] Ovo (oviposição)
  ✨ [CRIADO] Larva de 1º ínstar
  ...
📋 Processando: Podridão-negrados-frutos
  ✨ [CRIADO] Esporos dormentes no solo
  ...
✅ Processo concluído!
   📊 Criados: 12
   ⏭️  Já existiam: 0
```

### 2. Criar Nova Empresa (Automático)

```python
# Qualquer operação que cria uma Empresa dispara o signal:
empresa = Empresa.objects.create(
    nome='Fazenda Nova Brasil',
    cnpj='12345678901234'
)
# ✅ 12 estágios foram automaticamente copiados para this empresa!
```

### 3. Customizar Estágios (UI Web)

Cada empresa acessa `/cadastros/estagios/` para:
- **Visualizar** estágios padrão copiados
- **Editar** descrição, duração, criticidade
- **Criar** novos estágios específicos
- **Deletar** estágios que não se aplicam
- Ver **origem** do estágio (template original)

---

## 🔍 Visualização no Admin Django

### Lista de Estágios (Destaque)
```
[Praga] [Tipo] [Ordem] [Duração Min] [Status] [Empresa] [Tipo] [Ativo]
Lagarta  OVO    1       2-4 dias     Crítico? Farm A    ⭐Templ ✓
Lagarta  LARVA  4       3-5 dias     Crítico  Farm A    🔗Cóp  ✓
```

**Legenda:**
- `⭐ Template` = É um template padrão do sistema
- `🔗 Cópia` = Foi copiado de um template
- `-` = Criado diretamente pela empresa

### Detail View
Cada estágio mostra:
- **Template Original** (readonly) - Link para o estágio de origem
- **É Estágio Template?** - Checkbox para criar novo template
- Histórico de **Data de Criação** e **Atualização**

---

## 🧪 Teste de Funcionalidade

Executar teste completo:
```bash
py test_estagio_template.py
```

**Verificações automáticas:**
1. ✅ 12 templates criados no sistema
2. ✅ Nova empresa criada, 12 estágios copiados
3. ✅ Rastreamento de origem funcional
4. ✅ Edição/exclusão independente por empresa
5. ✅ Nenhum impacto em outras empresas

---

## 📈 Benefícios do Sistema

### Para Agricultores
- **Menos configuração** - Estágios já vêm pré-preenchidos
- **Boas práticas** - Baseado em conhecimento acumulado de múltiplas empresas
- **Customização** - Podem ajustar conforme sua região/variedade

### Para o Negócio
- **Diferencial competitivo** - Onboarding mais rápido
- **Network effect** - Base de estágios melhora com mais empresas
- **Retenção** - Menos fricção na criação da conta
- **Dados** - Insights sobre estágios mais usados/críticos

### Para o Desenvolvimento
- **Escalável** - Novos pragas/estágios adicionados facilmente
- **Rastreável** - Know which stages came from templates
- **Isolado** - Mudanças em uma empresa não afetam outras

---

## 🔧 Próximas Melhorias

- [ ] Admin UI para criar/editar templates diretamente
- [ ] Versioning de templates (histórico de mudanças)
- [ ] Importação de estágios de empresa para empresa
- [ ] Dashboard com estatísticas (estágios mais críticos, etc)
- [ ] API pública para consultar estágios de outras empresas

---

## 📋 Checkpoints de Implementação

Já implementado:
- ✅ Migrations para campos `eh_template` e `template_original`
- ✅ Signal `copiar_estagios_template_para_nova_empresa`
- ✅ Comando `popular_estagios_template`
- ✅ Admin UI com filtros e visualização
- ✅ Teste automatizado de funcionalidade

Próximos:
- [ ] Documentação de admin para usuários
- [ ] Testes de carga (performance com muitos estágios)
- [ ] Export/import de templates

---

## 📞 Suporte

Para adicionar novos estágios template:
1. Editar dicionário `ESTAGIOS_PADRAO` em `popular_estagios_template.py`
2. Executar comando: `py manage.py popular_estagios_template --refresh`
3. Empresas novas receberão os estágios atualizados

