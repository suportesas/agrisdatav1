# Fase 1: Backlog Executável - NF-e XML Import

**Status**: Pronto para iniciar  
**Sprint**: Week 1-2 (17.5 horas estimadas)  
**Feature Flag**: `COMPRAS_XML_IMPORT` (Fase 0 - já criada, desligada)  
**Aprovação Gate Fase 0**: ✅ Completa

---

## 🎯 Tarefas da Sprint

### Task 1.1: Setup Branch e Estrutura (0.5h)
**Status**: ⬜ Not Started  
**Assignee**: Dev  

```bash
# Checklist
□ git checkout -b feature/nfe-xml-import
□ mkdir -p compras/parsers compras/utils
□ touch compras/parsers/__init__.py
□ touch compras/utils/__init__.py
□ touch compras/parsers/nfe_parser.py
□ touch compras/utils/nfe_validators.py
□ manage.py check  # ✅ Must pass
□ git add . && git commit -m "setup(fase1): Create branches and directory structure"
```

**Deliverables**:
- ✅ Branch criado e local
- ✅ Estrutura de diretórios pronta
- ✅ Django health check OK

---

### Task 1.2: Parser XML NF-e Básico (3h)
**Status**: ⬜ Not Started  
**Assignee**: Dev  
**Depends On**: 1.1  

**Arquivo**: `compras/parsers/nfe_parser.py`

```python
"""
NF-e XML Parser - Extrai dados de arquivo XML em formato NFe v4.0
"""
import xmltodict
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Any

class ParseError(Exception):
    """Erro ao fazer parse do XML"""
    pass

class NFEParser:
    """Parser genérico para NF-e XML"""
    
    def parse(self, xml_path: str) -> Dict[str, Any]:
        """
        Parse XML file e retorna dict com dados estruturados
        
        Args:
            xml_path: Caminho absoluto para arquivo .xml
            
        Returns:
            Dict com estrutura:
            {
                'numero_nf': str,
                'serie': str,
                'chave_nfe': str (44 dígitos),
                'data_emissao': datetime,
                'fornecedor': {
                    'cnpj': str,
                    'nome': str,
                },
                'totais': {
                    'valor_total': Decimal,
                    'valor_frete': Decimal,
                    'valor_desconto': Decimal,
                },
                'itens': [
                    {
                        'produto_nome': str,
                        'quantidade': Decimal,
                        'preco_unitario': Decimal,
                        'ncm': str,
                        'cfop': str,
                    },
                    ...
                ]
            }
            
        Raises:
            ParseError: Se XML inválido ou estrutura inesperada
        """
        try:
            with open(xml_path, 'r', encoding='utf-8') as f:
                xml_content = f.read()
        except Exception as e:
            raise ParseError(f"Erro lendo arquivo: {e}")
        
        # Parse com xmltodict
        try:
            doc = xmltodict.parse(xml_content)
        except Exception as e:
            raise ParseError(f"XML mal-formado: {e}")
        
        # Extração (simplificada - expandir conforme necessário)
        try:
            nfe = doc['nfeProc']['NFe']['infNFe']
            ide = nfe['ide']
            emit = nfe['emit']
            total_nfe = nfe['total']['ICMStot']
            
            # Parse itens
            det = nfe.get('det', [])
            if not isinstance(det, list):
                det = [det]
            
            itens = []
            for item in det:
                prod = item['prod']
                itens.append({
                    'produto_nome': prod.get('xProd', 'Produto sem nome'),
                    'quantidade': Decimal(prod.get('qCom', 0)),
                    'preco_unitario': Decimal(prod.get('vUnCom', 0)),
                    'ncm': prod.get('NCM', ''),
                    'cfop': prod.get('CFOP', ''),
                })
            
            # Parse datas
            data_emissao_str = ide.get('dhEmi', ide.get('dEmi'))
            if 'T' in data_emissao_str:
                data_emissao = datetime.fromisoformat(data_emissao_str.replace('Z', '+00:00')).date()
            else:
                data_emissao = datetime.strptime(data_emissao_str, '%Y-%m-%d').date()
            
            # Extrair chave (do protocolo se disponível, senão gerar a partir de infNFe Id)
            chave_nfe = ''
            if 'protNFe' in doc['nfeProc']:
                chave_nfe = doc['nfeProc']['protNFe']['infProt'].get('chNFe', '')
            if not chave_nfe and 'Id' in nfe:
                # Id = "NFe" + 44 dígitos
                chave_nfe = nfe['Id'].replace('NFe', '')
            
            return {
                'numero_nf': str(ide.get('nNF', '')),
                'serie': str(ide.get('serie', '1')),
                'chave_nfe': chave_nfe,
                'data_emissao': data_emissao,
                'fornecedor': {
                    'cnpj': emit.get('CNPJ', '').replace('.', '').replace('-', ''),
                    'nome': emit.get('xNome', ''),
                },
                'totais': {
                    'valor_total': Decimal(total_nfe.get('vNF', 0)),
                    'valor_frete': Decimal(total_nfe.get('vFrete', 0)),
                    'valor_desconto': Decimal(total_nfe.get('vDesc', 0)),
                },
                'itens': itens,
            }
        
        except KeyError as e:
            raise ParseError(f"Campo esperado não encontrado: {e}")
        except Exception as e:
            raise ParseError(f"Erro processando dados: {e}")
```

**Testes Básicos** (`compras/tests/test_nfe_parser.py`):
```python
from django.test import TestCase
from compras.parsers.nfe_parser import NFEParser, ParseError
import tempfile
import os

class TestNFEParser(TestCase):
    
    def test_parse_valid_xml(self):
        """Parse verdadeiro XML deve funcionar"""
        parser = NFEParser()
        # Usar arquivo XML exemplo
        result = parser.parse('path/to/test_nfe.xml')
        self.assertIn('numero_nf', result)
        self.assertIn('chave_nfe', result)
        self.assertEqual(len(result['itens']), 1)
    
    def test_parse_invalid_xml(self):
        """XML mal-formado deve levantador ParseError"""
        parser = NFEParser()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write('<invalid>xml <no fecha>')
            f.flush()
            with self.assertRaises(ParseError):
                parser.parse(f.name)
        os.unlink(f.name)
    
    def test_parse_missing_fields(self):
        """XML sem campos críticos deve levantador ParseError"""
        parser = NFEParser()
        # TODO: criar XML exemplo sem campo nNF
        pass
```

**Checklist**:
- [ ] Classe `NFEParser` implementada
- [ ] Método `parse()` retorna dict correto
- [ ] Tratamento de erros (ParseError)
- [ ] Testes unitários cobrem casos válido + inválido
- [ ] Comments documentam estrutura XML esperada
- [ ] ✅ `manage.py check` passa
- [ ] ✅ `manage.py test compras.tests.test_nfe_parser` passa

---

### Task 1.3: Validações de Negócio (2h)
**Status**: ⬜ Not Started  
**Assignee**: Dev  
**Depends On**: 1.2  

**Arquivo**: `compras/utils/nfe_validators.py`

```python
"""
Validações de negócios para NF-e XML
"""
from django.core.exceptions import ValidationError
from cadastros.models import Fornecedor, Produto
from compras.models import RecebimentoCompra
from decimal import Decimal

class NFEValidationError(ValidationError):
    pass

class RequiredFornecedorError(NFEValidationError):
    pass

class MissingProductError(NFEValidationError):
    pass

def validar_chave_duplicada(chave_nfe: str, empresa_id: int) -> bool:
    """
    Verifica se NF-e com mesma chave já foi importada
    
    Returns:
        True se duplicata encontrada
        
    Raises:
        NFEValidationError se duplicata
    """
    existe = RecebimentoCompra.objects.filter(
        chave_nfe=chave_nfe,
        empresa_id=empresa_id
    ).exists()
    
    if existe:
        raise NFEValidationError(
            f"⚠️ NF-e com chave {chave_nfe} já foi importada anteriormente"
        )
    return False

def validar_fornecedor_existe(cnpj: str, empresa_id: int) -> Fornecedor:
    """
    Busca fornecedor por CNPJ
    
    Raises:
        RequiredFornecedorError se não encontrado
    """
    cnpj_clean = cnpj.replace('.', '').replace('-', '')
    try:
        fornecedor = Fornecedor.objects.get(
            cnpj_cpf=cnpj_clean,
            empresa_id=empresa_id
        )
        return fornecedor
    except Fornecedor.DoesNotExist:
        raise RequiredFornecedorError(
            f"❌ Fornecedor com CNPJ {cnpj} não cadastrado. "
            f"Faça o cadastro antes de importar NF-e."
        )

def validar_produtos_existem(produtos_list: list, empresa_id: int) -> list:
    """
    Busca produtos por nome
    
    Args:
        produtos_list: Lista de dicts com 'produto_nome'
        
    Returns:
        Lista de tuplas (nome_xml, produto_obj_ou_none)
    """
    resultados = []
    nao_encontrados = []
    
    for item in produtos_list:
        nome = item.get('produto_nome', '')
        try:
            produto = Produto.objects.get(
                nome__icontains=nome,
                empresa_id=empresa_id
            )
            resultados.append((nome, produto))
        except Produto.DoesNotExist:
            resultados.append((nome, None))
            nao_encontrados.append(nome)
    
    if nao_encontrados:
        # Log warning mas não falhar
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Produtos não encontrados: {nao_encontrados}")
    
    return resultados

def validar_totais(nf_data: dict) -> bool:
    """
    Verifica se soma de itens ≈ vNF
    
    Tolerância: ±0.01
    
    Raises:
        NFEValidationError se divergência maior
    """
    soma_itens = sum(
        Decimal(item.get('quantidade', 0)) * Decimal(item.get('preco_unitario', 0))
        for item in nf_data.get('itens', [])
    )
    
    valor_nf = nf_data['totais']['valor_total']
    
    diferenca = abs(soma_itens - valor_nf)
    if diferenca > Decimal('0.01'):
        raise NFEValidationError(
            f"⚠️ Soma de itens ({soma_itens}) diferente do valor NF ({valor_nf}). "
            f"Diferença: R$ {diferenca}"
        )
    
    return True

def validar_datas(data_emissao, data_recebimento) -> bool:
    """
    Validações de fecha
    """
    from datetime import date, timedelta
    
    hoje = date.today()
    
    if data_emissao > hoje:
        raise NFEValidationError(
            f"❌ Data de emissão ({data_emissao}) não pode ser futura"
        )
    
    if data_emissao < (hoje - timedelta(days=180)):
        raise NFEValidationError(
            f"⚠️ NF-e com mais de 6 meses ({data_emissao}). "
            f"Recebimento defasado?"
        )
    
    if data_emissao > data_recebimento:
        raise NFEValidationError(
            f"❌ Data de emissão ({data_emissao}) maior que data de recebimento ({data_recebimento})"
        )
    
    return True
```

**Testes** (`compras/tests/test_nfe_validators.py`):
```python
from django.test import TestCase
from compras.utils.nfe_validators import *
from cadastros.models import Fornecedor
from empresas.models import Empresa

class TestNFEValidators(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            nome='Teste',
            cnpj_cpf='12345678901234'
        )
    
    def test_validar_chave_duplicada_primeira_vez(self):
        """Primeira importação deve passar"""
        validar_chave_duplicada('35080808812662996000152550010000003418234567890', self.empresa.id)
        # Não deve levant erro
    
    def test_validar_fornecedor_existe_true(self):
        """Fornecedor encontrado"""
        fornecedor = Fornecedor.objects.create(
            empresa=self.empresa,
            nome='Fornecedor ABC',
            cnpj_cpf='35088126629960'
        )
        result = validar_fornecedor_existe('35.088.126.629-96', self.empresa.id)
        self.assertEqual(result.id, fornecedor.id)
    
    def test_validar_fornecedor_existe_false(self):
        """Fornecedor não encontrado"""
        with self.assertRaises(RequiredFornecedorError):
            validar_fornecedor_existe('99999999999999', self.empresa.id)
```

**Checklist**:
- [ ] Função `validar_chave_duplicada()` implementada
- [ ] Função `validar_fornecedor_existe()` implementada
- [ ] Função `validar_produtos_existem()` implementada
- [ ] Função `validar_totais()` implementada
- [ ] Função `validar_datas()` implementada
- [ ] Erros customizados levantados com mensagens descritivas
- [ ] ✅ Testes cobrem casos OK + ❌ (erro)
- [ ] ✅ `manage.py test compras.tests.test_nfe_validators` passa (≥80% coverage)

---

### Task 1.4: Model ItemRecebimento + Migração (1.5h)
**Status**: ⬜ Not Started  
**Assignee**: Dev  
**Depends On**: None  

**Ação**: Verificar se `ItemRecebimento` existe em `compras/models.py`

```bash
# Verificar
grep -n "class ItemRecebimento" compras/models.py

# Se não existente, adicionar:
```

**Modelo** (adicionar a `compras/models.py` se necessário):
```python
class ItemRecebimento(models.Model):
    """
    Item individual de um recebimento
    """
    recebimento = models.ForeignKey(
        'RecebimentoCompra',
        on_delete=models.CASCADE,
        related_name='itens',
        verbose_name='Recebimento'
    )
    
    produto = models.ForeignKey(
        'produtos.Produto',
        on_delete=models.PROTECT,
        verbose_name='Produto'
    )
    
    quantidade = models.DecimalField(
        'Quantidade',
        max_digits=12,
        decimal_places=4,
        validators=[MinValueValidator(Decimal('0.0001'))]
    )
    
    preco_unitario = models.DecimalField(
        'Preço Unitário',
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    # Opcional: rastreabilidade NF-e
    ncm = models.CharField('NCM', max_length=8, blank=True)
    cfop = models.CharField('CFOP', max_length=4, blank=True)
    
    class Meta:
        verbose_name = 'Item de Recebimento'
        verbose_name_plural = 'Itens de Recebimento'
    
    def __str__(self):
        return f"{self.recebimento.numero} - {self.produto.nome}"
    
    @property
    def valor_total(self):
        return self.quantidade * self.preco_unitario
```

**Checklist**:
- [ ] Modelo existe em `compras/models.py`
- [ ] Campos: recebimento FK, produto FK, quantidade, preco_unitario, ncm (opt), cfop (opt)
- [ ] Migração criada: `manage.py makemigrations compras`
- [ ] Migração aplicada: `manage.py migrate`
- [ ] ✅ `manage.py check` passa
- [ ] Admin registrado (opcionalmente)

---

### Task 1.5: Form Estendido XMLNFe (1h)
**Status**: ⬜ Not Started  
**Assignee**: Dev  
**Depends On**: 1.2, 1.3  

**Arquivo**: `compras/forms_xml_nf.py` (reescrever)

```python
"""
Forms para importação e preview de NF-e XML
"""
from django import forms
from django.core.exceptions import ValidationError
from .parsers.nfe_parser import NFEParser, ParseError
from .utils.nfe_validators import (
    validar_chave_duplicada, 
    validar_datas,
    NFEValidationError
)
from compras.models import PedidoCompra
from datetime import date

class XMLNFeUploadForm(forms.Form):
    """Form para upload de arquivo XML"""
    
    xml_file = forms.FileField(
        label='Arquivo XML da NF-e',
        required=True,
        help_text='Selecione arquivo .xml com dados da nota fiscal',
        widget=forms.FileInput(attrs={
            'accept': '.xml',
            'class': 'form-control'
        })
    )
    
    def clean_xml_file(self):
        """Validação do arquivo"""
        file = self.cleaned_data.get('xml_file')
        
        if file:
            # Verificar extensão
            if not file.name.endswith('.xml'):
                raise ValidationError("Arquivo deve ser .xml")
            
            # Verificar tamanho (máximo 1MB)
            if file.size > 1024 * 1024:
                raise ValidationError("Arquivo não pode exceder 1MB")
        
        return file
    
    def clean(self):
        """Validação do form"""
        cleaned_data = super().clean()
        xml_file = cleaned_data.get('xml_file')
        
        if xml_file:
            # Tentar fazer parse (early validation)
            try:
                # Salvar temporariamente para ler
                import tempfile
                import os
                with tempfile.NamedTemporaryFile(delete=False, suffix='.xml') as tmp:
                    for chunk in xml_file.chunks():
                        tmp.write(chunk)
                    tmp_path = tmp.name
                
                parser = NFEParser()
                nfe_data = parser.parse(tmp_path)
                
                # Validações básicas
                validar_datas(nfe_data['data_emissao'], date.today())
                
                # Guardar dados parseados para usar depois
                self.cleaned_nfe_data = nfe_data
                
                os.unlink(tmp_path)
            
            except ParseError as e:
                raise ValidationError(f"Erro ao processar XML: {e}")
            except NFEValidationError as e:
                raise ValidationError(f"Validação falhou: {e}")
        
        return cleaned_data


class NFEPreviewForm(forms.Form):
    """Form para confirmar dados extraídos e vincular a pedido"""
    
    fornecedor_id = forms.IntegerField(
        widget=forms.HiddenInput()
    )
    
    valor_total_nf = forms.DecimalField(
        label='Valor Total NF (pode editar)',
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    
    data_recebimento = forms.DateField(
        label='Data do Recebimento',
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )
    
    pedido_id = forms.IntegerField(
        label='Vincular a Pedido Existente (opcional)',
        required=False,
        widget=forms.HiddenInput()
    )
    
    confirmar = forms.BooleanField(
        label='Confirmar dados acima',
        required=True
    )
```

**Checklist**:
- [ ] `XMLNFeUploadForm` com validação de arquivo
- [ ] `clean_xml_file()` verifica extensão e tamanho
- [ ] `clean()` faz parse e validações semânticas
- [ ] `NFEPreviewForm` para confirmar antes de salvar
- [ ] Campos editáveis críticos (valor_total_nf, data_recebimento)
- [ ] ✅ Forms com Bootstrap CSS (class='form-control')

---

### Task 1.6: View de Import e Preview (2h)
**Status**: ⬜ Not Started  
**Assignee**: Dev  
**Depends On**: 1.5  

**Arquivo**: `compras/views.py` (adicionar funções)

```python
"""
Views para importação de NF-e XML
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from core.feature_flags import is_feature_enabled
from .forms_xml_nf import XMLNFeUploadForm, NFEPreviewForm
from .parsers.nfe_parser import NFEParser, ParseError
from .utils.nfe_validators import (
    validar_chave_duplicada,
    validar_fornecedor_existe,
    validar_produtos_existem,
    validar_totais,
    validar_datas,
    NFEValidationError
)
from compras.models import PedidoCompra
from datetime import date, timedelta
import logging

logger = logging.getLogger(__name__)

@login_required
@require_http_methods(["GET", "POST"])
def import_nfe_xml(request):
    """
    GET: Exibe form de upload XML
    POST: Processa upload e redireciona para preview
    """
    
    # Verificar feature flag
    if not is_feature_enabled('COMPRAS_XML_IMPORT'):
        messages.error(request, '⚠️ Funcionalidade de importação NF-e indisponível')
        return redirect('compras:recebimento_list')
    
    if request.method == 'POST':
        form = XMLNFeUploadForm(request.POST, request.FILES)
        
        if form.is_valid():
            try:
                # Dados já foram validados e parseados em form.clean()
                nfe_data = form.cleaned_nfe_data
                
                # Validações adicionais
                validar_chave_duplicada(nfe_data['chave_nfe'], request.user.empresa.id)
                
                # Recuperar fornecedor
                try:
                    fornecedor = validar_fornecedor_existe(
                        nfe_data['fornecedor']['cnpj'],
                        request.user.empresa.id
                    )
                except validar_fornecedor_existe as e:
                    messages.error(request, str(e))
                    return render(request, 'compras/nfe/import_nfe.html', {'form': form})
                
                # Validar produtos
                produtos_found = validar_produtos_existem(
                    nfe_data['itens'],
                    request.user.empresa.id
                )
                
                # Armazenar em session para próximo step
                request.session['nfe_import_data'] = {
                    'nfe_data': nfe_data,  # serializable
                    'fornecedor_id': fornecedor.id,
                    'arquivo_nome': request.FILES['xml_file'].name,
                }
                
                return redirect('compras:preview_nfe')
            
            except NFEValidationError as e:
                messages.error(request, f"❌ {e}")
                return render(request, 'compras/nfe/import_nfe.html', {'form': form})
            except Exception as e:
                logger.exception(f"Erro no import NF-e: {e}")
                messages.error(request, f"Erro inesperado: {e}")
                return render(request, 'compras/nfe/import_nfe.html', {'form': form})
    
    else:  # GET
        form = XMLNFeUploadForm()
    
    return render(request, 'compras/nfe/import_nfe.html', {'form': form})


@login_required
@require_http_methods(["GET", "POST"])
def preview_nfe(request):
    """
    GET: Exibe preview dos dados extraídos para confirmação
    POST: Redireciona para confirm_nfe após edições
    """
    
    # Recuperar dados da session
    nfe_import = request.session.get('nfe_import_data')
    if not nfe_import:
        messages.error(request, 'Sessão expirada. Tente novamente.')
        return redirect('compras:import_nfe_xml')
    
    nfe_data = nfe_import['nfe_data']
    fornecedor_id = nfe_import['fornecedor_id']
    
    # Buscar pedidos compatíveis para sugestão
    from cadastros.models import Fornecedor
    fornecedor = Fornecedor.objects.get(id=fornecedor_id)
    
    sugestoes_pedido = buscar_pedidos_compatibles(
        fornecedor=fornecedor,
        data_nf=nfe_data['data_emissao'],
        valor_nf=nfe_data['totais']['valor_total'],
        empresa=request.user.empresa
    )
    
    if request.method == 'POST':
        # Usuário confirmou - redireciona para confirmação final
        form = NFEPreviewForm(request.POST)
        if form.is_valid():
            # Atualizar session com dados editados
            request.session['nfe_import_data']['data_recebimento'] = str(
                form.cleaned_data['data_recebimento']
            )
            request.session['nfe_import_data']['valor_total_nf'] = str(
                form.cleaned_data['valor_total_nf']
            )
            request.session['nfe_import_data']['pedido_id'] = form.cleaned_data.get('pedido_id')
            
            return redirect('compras:confirm_nfe')
    
    else:  # GET
        form = NFEPreviewForm(initial={
            'fornecedor_id': fornecedor_id,
            'valor_total_nf': nfe_data['totais']['valor_total'],
            'data_recebimento': date.today(),
        })
    
    context = {
        'form': form,
        'nfe_data': nfe_data,
        'fornecedor': fornecedor,
        'sugestoes_pedido': sugestoes_pedido,
    }
    
    return render(request, 'compras/nfe/preview_nfe.html', context)


def buscar_pedidos_compatibles(fornecedor, data_nf, valor_nf, empresa):
    """
    Busca pedidos compatíveis para vinculação automática
    
    Critérios:
    - Mesmo fornecedor
    - Status PENDENTE ou PARCIAL
    - Data ±90 dias
    - Valor similar (±5%)
    """
    candidatos = PedidoCompra.objects.filter(
        fornecedor=fornecedor,
        status__in=['PENDENTE', 'PARCIAL'],
        data_pedido__gte=data_nf - timedelta(days=90),
        data_pedido__lte=data_nf + timedelta(days=1),
        empresa=empresa
    )
    
    sugestoes = []
    for pedido in candidatos:
        # Verificar similaridade de valor
        diferenca_pct = abs(pedido.valor_total - valor_nf) / valor_nf
        if diferenca_pct < 0.05:  # 5% de tolerância
            sugestoes.append({
                'pedido': pedido,
                'diferenca': abs(pedido.valor_total - valor_nf),
                'percentual': f"{diferenca_pct * 100:.1f}%"
            })
    
    return sorted(sugestoes, key=lambda x: x['diferenca'])


@login_required
@require_http_methods(["POST"])
def confirm_nfe(request):
    """
    Processa confirmação e cria RecebimentoCompra + ItemRecebimentos
    """
    
    # TODO: Implementar em Task 1.7
    pass
```

**URLs** (`compras/urls.py` - adicionar):
```python
path('import-nfe-xml/', views.import_nfe_xml, name='import_nfe_xml'),
path('preview-nfe/', views.preview_nfe, name='preview_nfe'),
path('confirm-nfe/', views.confirm_nfe, name='confirm_nfe'),
```

**Checklist**:
- [ ] View `import_nfe_xml()` com upload form
- [ ] View `preview_nfe()` com edição antes de confirmar
- [ ] Stub para `confirm_nfe()` (implementar em 1.7)
- [ ] URLs adicionadas
- [ ] Feature flag check
- [ ] Mensagens de erro/sucesso
- [ ] Session management para fluxo multi-step

---

### Task 1.7: Criar RecebimentoCompra from NF-e (1.5h)
**Status**: ⬜ Not Started  
**Assignee**: Dev  
**Depends On**: 1.4, 1.6  

**Função** (adicionar a `compras/views.py`):

```python
from compras.models import RecebimentoCompra, ItemRecebimento
from decimal import Decimal
from django.db import transaction

def criar_recebimento_from_nfe(nfe_data: dict, fornecedor_id: int, pedido=None, usuario=None, empresa=None) -> RecebimentoCompra:
    """
    Cria RecebimentoCompra + ItemRecebimentos desde dados de NF-e
    
    Args:
        nfe_data: Dict com dados parseados (do parser)
        fornecedor_id: ID do fornecedor
        pedido: PedidoCompra (optional)
        usuario: Usuario (required - quem criou)
        empresa: Empresa (required)
    
    Returns:
        Objeto RecebimentoCompra criado
        
    Raises:
        DuplicateNFEError, ValidationError
    """
    from cadastros.models import Fornecedor
    from produtos.models import Produto
    
    fornecedor = Fornecedor.objects.get(id=fornecedor_id)
    
    # Validação final de duplicação
    validar_chave_duplicada(nfe_data['chave_nfe'], empresa.id)
    
    with transaction.atomic():
        # Criar RecebimentoCompra
        numero = gerar_numero_recebimento(empresa)
        
        recebimento = RecebimentoCompra.objects.create(
            empresa=empresa,
            numero=numero,
            pedido=pedido,
            fornecedor=fornecedor,
            
            nota_fiscal=nfe_data['numero_nf'],
            serie_nota=nfe_data['serie'],
            chave_nfe=nfe_data['chave_nfe'],
            data_emissao_nf=nfe_data['data_emissao'],
            
            data_recebimento=date.today(),
            recebido_por=usuario,
            
            status='PENDENTE',
            
            valor_total_nf=nfe_data['totais']['valor_total'],
            valor_frete=nfe_data['totais']['valor_frete'],
            valor_desconto=nfe_data['totais']['valor_desconto'],
            
            arquivo_nfe=None,  # Será preenchido se houver salvamento de arquivo
        )
        
        # Criar ItemRecebimentos
        for item_data in nfe_data['itens']:
            # Buscar produto (assumir que já validado em preview)
            try:
                produto = Produto.objects.get(
                    nome__icontains=item_data['produto_nome'],
                    empresa=empresa
                )
            except Produto.DoesNotExist:
                logger.warning(f"Produto '{item_data['produto_nome']}' não encontrado")
                continue
            
            ItemRecebimento.objects.create(
                recebimento=recebimento,
                produto=produto,
                quantidade=Decimal(str(item_data['quantidade'])),
                preco_unitario=Decimal(str(item_data['preco_unitario'])),
                ncm=item_data.get('ncm', ''),
                cfop=item_data.get('cfop', ''),
            )
    
    return recebimento


def gerar_numero_recebimento(empresa):
    """Gera número único para recebimento"""
    from datetime import date
    ultimo = RecebimentoCompra.objects.filter(empresa=empresa).order_by('-id').first()
    seq = 1
    if ultimo:
        seq = int(ultimo.numero.split('-')[-1]) + 1
    
    hoje = date.today()
    return f"{empresa.id}-{hoje.strftime('%Y%m%d')}-{seq:05d}"
```

**View Final** (`confirm_nfe`):

```python
@login_required
@require_http_methods(["POST"])
def confirm_nfe(request):
    """
    Processa confirmação final e cria RecebimentoCompra
    """
    
    nfe_import = request.session.get('nfe_import_data')
    if not nfe_import:
        messages.error(request, 'Sessão expirada.')
        return redirect('compras:import_nfe_xml')
    
    try:
        nfe_data = nfe_import['nfe_data']
        fornecedor_id = nfe_import['fornecedor_id']
        pedido_id = nfe_import.get('pedido_id')
        
        pedido = None
        if pedido_id:
            pedido = PedidoCompra.objects.get(id=pedido_id)
        
        # Criar recebimento
        recebimento = criar_recebimento_from_nfe(
            nfe_data=nfe_data,
            fornecedor_id=fornecedor_id,
            pedido=pedido,
            usuario=request.user,
            empresa=request.user.empresa
        )
        
        # Limpar session
        del request.session['nfe_import_data']
        
        messages.success(
            request,
            f'✅ Recebimento #{recebimento.numero} criado com sucesso!'
        )
        
        return redirect('compras:recebimento_detail', pk=recebimento.id)
    
    except Exception as e:
        logger.exception(f"Erro ao confirmar NF-e: {e}")
        messages.error(request, f"Erro: {e}")
        return redirect('compras:import_nfe_xml')
```

**Checklist**:
- [ ] Função `criar_recebimento_from_nfe()` implementada
- [ ] Função `gerar_numero_recebimento()` implementada
- [ ] `confirm_nfe()` view implementada
- [ ] Transação atômica (rollback automático em erro)
- [ ] ItemRecebimentos criados para cada item da NF-e
- [ ] ✅ RecebimentoCompra com status='PENDENTE'

---

### Task 1.8: Testes Unitários (3h)
**Status**: ⬜ Not Started  
**Assignee**: QA/Dev  
**Depends On**: 1.2, 1.3, 1.4, 1.7  

**Arquivos de Teste**:
```
compras/tests/
├── test_nfe_parser.py          [DONE in 1.2]
├── test_nfe_validators.py      [DONE in 1.3]
├── test_nfe_recebimento.py     [NEW - Create models]
└── test_nfe_views.py           [NEW - Create views]
```

**Estrutura Básica** (`compras/tests/test_nfe_recebimento.py`):

```python
from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import date
from compras.views import criar_recebimento_from_nfe, gerar_numero_recebimento
from compras.models import RecebimentoCompra, ItemRecebimento
from cadastros.models import Fornecedor
from produtos.models import Produto
from empresas.models import Empresa

User = get_user_model()

class TestCriarRecebimentoFromNFE(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            nome='Empresa Teste',
            cnpj_cpf='12345678901234'
        )
        self.usuario = User.objects.create(
            username='user_test',
            empresa=self.empresa
        )
        self.fornecedor = Fornecedor.objects.create(
            empresa=self.empresa,
            nome='Fornecedor Teste',
            cnpj_cpf='35088126629960'
        )
        self.produto = Produto.objects.create(
            empresa=self.empresa,
            nome='Produto Teste',
            preco_custo=Decimal('100.00')
        )
    
    def test_criar_recebimento_simples(self):
        """Criar recebimento desde NF-e válida"""
        nfe_data = {
            'numero_nf': '12345',
            'serie': '1',
            'chave_nfe': '35080808812662996000152550010000003418234567890',
            'data_emissao': date.today(),
            'fornecedor': {
                'cnpj': '35088126629960',
                'nome': 'Fornecedor Teste'
            },
            'totais': {
                'valor_total': Decimal('1000.00'),
                'valor_frete': Decimal('100.00'),
                'valor_desconto': Decimal('0.00')
            },
            'itens': [
                {
                    'produto_nome': 'Produto Teste',
                    'quantidade': Decimal('10.0000'),
                    'preco_unitario': Decimal('100.00'),
                    'ncm': '21069000',
                    'cfop': '5102'
                }
            ]
        }
        
        recebimento = criar_recebimento_from_nfe(
            nfe_data=nfe_data,
            fornecedor_id=self.fornecedor.id,
            usuario=self.usuario,
            empresa=self.empresa
        )
        
        # Assertions
        self.assertEqual(recebimento.status, 'PENDENTE')
        self.assertEqual(recebimento.nota_fiscal, '12345')
        self.assertEqual(recebimento.valor_total_nf, Decimal('1000.00'))
        self.assertEqual(recebimento.itens.count(), 1)
    
    def test_criar_recebimento_duplicata_falha(self):
        """Não permitir chave NF-e duplicada"""
        nfe_data = {
            'numero_nf': '99999',
            'series': '1',
            'chave_nfe': '35080808812662996000152550010000003418234567890',
            'data_emissao': date.today(),
            'fornecedor': {'cnpj': '35088126629960', 'nome': 'Fornecedor Teste'},
            'totais': {'valor_total': Decimal('500.00'), 'valor_frete': Decimal('0'), 'valor_desconto': Decimal('0')},
            'itens': []
        }
        
        # Primeira criação
        criar_recebimento_from_nfe(nfe_data, self.fornecedor.id, self.usuario, self.empresa)
        
        # Segunda deve falhar
        with self.assertRaises(Exception):  # NFEValidationError
            criar_recebimento_from_nfe(nfe_data, self.fornecedor.id, self.usuario, self.empresa)
```

**Checklist**:
- [ ] ≥ 10 testes unitários criados
- [ ] Coverage ≥ 80% em funções críticas
- [ ] Testes cobrem: sucesso, erro, validação, transação
- [ ] ✅ `manage.py test compras.tests` passa

---

### Task 1.9: Testes de Integração (2h)
**Status**: ⬜ Not Started  
**Assignee**: QA/Dev  
**Depends On**: 1.6, 1.7, 1.8  

**Exemplo** (`compras/tests/test_nfe_integration.py`):

```python
from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
# ... imports ...

class TestNFEImportIntegration(TestCase):
    def setUp(self):
        self.client = Client()
        # ... setup empresa, usuário, etc ...
    
    def test_fluxo_completo_upload_preview_confirmar(self):
        """E2E: Upload XML → Preview → Confirmação → Recebimento Criado"""
        # 1. Login
        self.client.login(username='user_test', password='pass123')
        
        # 2. POST upload com XML válido
        with open('path/to/test_nfe.xml', 'rb') as f:
            response = self.client.post(
                reverse('compras:import_nfe_xml'),
                {'xml_file': SimpleUploadedFile('test.xml', f.read(), content_type='text/xml')}
            )
        
        # 3. Verificar redirect para preview
        self.assertEqual(response.status_code, 302)
        self.assertIn('preview-nfe', response.url)
        
        # 4. GET preview
        response = self.client.get(reverse('compras:preview_nfe'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('nfe_data', response.context)
        
        # 5. POST confirmação
        response = self.client.post(
            reverse('compras:confirm_nfe'),
            {}
        )
        
        # 6. Verificar recebimento criado
        self.assertEqual(RecebimentoCompra.objects.count(), 1)
        recebimento = RecebimentoCompra.objects.first()
        self.assertEqual(recebimento.status, 'PENDENTE')
```

**Checklist**:
- [ ] ≥ 3 testes de integração E2E
- [ ] Fluxo completo: upload → preview → confirmação
- [ ] Teste fallback (XML inválido)
- [ ] Teste vinculação com Pedido
- [ ] Teste duplicação
- [ ] ✅ Todos os testes passam

---

### Task 1.10: Documentação SOP + Guia Usuário (1h)
**Status**: ⬜ Not Started  
**Assignee**: Tech Writer / Dev  
**Depends On**: Todas (1.1-1.9)  

**Arquivos a Criar**:

```
docs/fase1/
├── GUIA_USUARIO_NF-E_IMPORT.md     [Guia passo-a-passo para usuários]
├── SOP_TECNICO_NF-E_PARSER.md      [Documentação técnica]
├── CHANGELOG_FASE1.md              [Mudanças e versioning]
└── README_FASE1_STATUS.md          [Status e checklist]
```

**Checklist**:
- [ ] `GUIA_USUARIO_NF-E_IMPORT.md`: screenshots, passo-a-passo, FAQ
- [ ] `SOP_TECNICO_NF-E_PARSER.md`: arquitetura, extensibilidade, troubleshooting
- [ ] `CHANGELOG_FASE1.md`: features novas, breaking changes, notes
- [ ] `.env.example`: FF_COMPRAS_XML_IMPORT documentada
- [ ] Comments em código crítico (parser, validators, views)

---

## 📊 Progress Tracking

| Task | Desc | Est. | Status | Owner |
|------|------|------|--------|-------|
| 1.1 | Setup Branch | 0.5h | ⬜ | Dev |
| 1.2 | Parser NF-e | 3h | ⬜ | Dev |
| 1.3 | Validações | 2h | ⬜ | Dev |
| 1.4 | Model + Migração | 1.5h | ⬜ | Dev |
| 1.5 | Forms | 1h | ⬜ | Dev |
| 1.6 | Views | 2h | ⬜ | Dev |
| 1.7 | Save Recebimento | 1.5h | ⬜ | Dev |
| 1.8 | Unit Tests | 3h | ⬜ | QA |
| 1.9 | Integration | 2h | ⬜ | QA |
| 1.10 | Docs | 1h | ⬜ | Tech Writer |
| **TOTAL** | NF-e XML Import | **17.5h** | ⬜ | - |

---

## 🎯 Definition of Done

- ✅ Todas 10 tarefas concluídas
- ✅ Coverage ≥ 80%
- ✅ Smoke test final: criar recebimento via XML em < 5s
- ✅ Feature flag `COMPRAS_XML_IMPORT` testada (on/off)
- ✅ Rollback procedure testado
- ✅ Fase 0 smoke tests ainda passam (regressão = 0)
- ✅ Documentação completa
- ✅ Code review aprovado
- ✅ Gate de Fase 1 assinado

---

## 🚀 Próximas Ações

1. **Assignar tarefas** → Dev/QA
2. **Setup branch** → `git checkout -b feature/nfe-xml-import`
3. **Daily standup** → Acompanhar progresso (14:00 BRT)
4. **PR Review** → Após conclusão de 1.1-1.7
5. **Sign-off Fase 1** → Após 1.8-1.10

---

**Versão**: v1.0-Backlog  
**Data**: 31/03/2026  
**Próxima Revisão**: Após conclusão de Task 1.1
