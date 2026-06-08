from django import forms
from django.core.exceptions import ValidationError
from django.forms.widgets import Select
from .models import UnidadeMedida, Categoria, SubCategoria, Produto, ProdutoTributacao, NaturezaOperacao, ProdutoDefensivoCultura, TipoProduto
from estoque.models import Armazem


class TipoProdutoForm(forms.ModelForm):
    class Meta:
        model = TipoProduto
        fields = ['nome', 'codigo', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'codigo': forms.TextInput(attrs={'class': 'form-control'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empresa = empresa


class SubCategoriaSelect(Select):
    """Widget personalizado para adicionar data-categoria-id nas opções"""
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        if value:
            try:
                # Extrair o valor real se for um ModelChoiceIteratorValue
                if hasattr(value, 'value'):
                    value = value.value
                # Converter para int se for string
                if isinstance(value, str) and value.isdigit():
                    value = int(value)
                
                subcategoria = SubCategoria.objects.get(pk=value)
                option['attrs']['data-categoria-id'] = str(subcategoria.categoria_id)
            except (SubCategoria.DoesNotExist, ValueError, TypeError):
                pass
        return option


class UnidadeMedidaForm(forms.ModelForm):
    class Meta:
        model = UnidadeMedida
        fields = ['sigla', 'nome', 'tipo', 'ativo']
        widgets = {
            'sigla': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: KG, L, UN'}),
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Quilograma'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['codigo', 'nome', 'descricao', 'ativo']
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: DEF, FERT'}),
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Defensivos'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class NaturezaOperacaoForm(forms.ModelForm):
    class Meta:
        model = NaturezaOperacao
        fields = ['codigo', 'descricao', 'tipo', 'observacoes', 'ativo']
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: VENDA, COMPRA'}),
            'descricao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Venda de mercadoria adquirida de terceiros'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class SubCategoriaForm(forms.ModelForm):
    class Meta:
        model = SubCategoria
        fields = ['categoria', 'codigo', 'nome', 'descricao', 'ativo']
        widgets = {
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'codigo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: HERB, FUNG'}),
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Herbicidas'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class CategoriaSelect(Select):
    """Widget personalizado para adicionar data-condiciona-campos nas opções"""
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        if value:
            try:
                # Extrair o valor real se for um ModelChoiceIteratorValue
                if hasattr(value, 'value'):
                    value = value.value
                # Converter para int se for string
                if isinstance(value, str) and value.isdigit():
                    value = int(value)
                from .models import Categoria
                categoria = Categoria.objects.get(pk=value)
                option['attrs']['data-condiciona-campos'] = 'true' if getattr(categoria, 'condiciona_campos', False) else 'false'
            except (Categoria.DoesNotExist, ValueError, TypeError):
                pass
        return option

class ProdutoForm(forms.ModelForm):
    classe_agronomica = forms.MultipleChoiceField(
        choices=Produto.CLASSE_AGRONOMICA_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False,
        label='Classe Agronômica',
    )

    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        # Tornar o campo código opcional (será gerado automaticamente)
        self.fields['codigo'].required = False
        self.fields['codigo'].help_text = 'Deixe em branco para gerar automaticamente'

        # Converte a string comma-separated do banco para lista para renderizar os checkboxes
        if self.instance.pk and self.instance.classe_agronomica:
            self.initial['classe_agronomica'] = [
                v.strip() for v in self.instance.classe_agronomica.split(',') if v.strip()
            ]

        # Filtrar por empresa
        if empresa:
            self.fields['categoria'].queryset = Categoria.objects.filter(empresa=empresa)
            self.fields['subcategoria'].queryset = SubCategoria.objects.filter(categoria__empresa=empresa)
            self.fields['unidade_medida'].queryset = UnidadeMedida.objects.filter(empresa=empresa)
            self.fields['unidade_compra'].queryset = UnidadeMedida.objects.filter(empresa=empresa)
            self.fields['unidade_venda'].queryset = UnidadeMedida.objects.filter(empresa=empresa)
            self.fields['unidade_dosagem'].queryset = UnidadeMedida.objects.filter(empresa=empresa)
            self.fields['armazem_padrao'].queryset = Armazem.objects.filter(empresa=empresa, ativo=True)

    def clean_classe_agronomica(self):
        values = self.cleaned_data.get('classe_agronomica') or []
        return ','.join(values)
    
    class Meta:
        model = Produto
        widgets = {
            'categoria': CategoriaSelect(attrs={'class': 'form-select'}),
        }
        fields = [
            # Identificação
            'codigo', 'codigo_barras', 'nome', 'nome_resumido', 'descricao',
            # Classificação
            'categoria', 'subcategoria',
            # Unidades e Pesos
            'unidade_medida', 'unidade_compra', 'unidade_venda', 'fator_conversao',
            'peso_liquido_unitario', 'peso_bruto_unitario',
            # Fiscal
            'ncm', 'cest', 'tipo_item',
            # Financeiro
            'preco_custo', 'preco_venda', 'margem_lucro', 'preco_minimo',
            # Estoque
            'controla_estoque', 'estoque_minimo', 'estoque_maximo', 'estoque_atual', 'localizacao', 'armazem_padrao',
            # Rastreabilidade
            'lote_obrigatorio', 'validade_obrigatoria', 'dias_validade',
            # Informações Adicionais
            'observacoes', 'imagem', 'ativo',
            # Categoria Agrícola
            'categoria_agricola',
            # Defensivos
            'classe_agronomica', 'ingrediente_ativo', 'concentracao', 'registro_mapa',
            'possui_certificado', 'numero_certificado', 'data_vencimento_certificado', 'arquivo_certificado',
            'classe_toxicologica', 'classe_ambiental', 'periodo_carencia', 'intervalo_reaplicacao',
            'periodo_reentrada', 'paises_proibidos',
            # Fertilizantes
            'tipo_fertilizante', 'formula_npk', 'nitrogenio_n', 'fosforo_p2o5', 'potassio_k2o',
            'enxofre_s', 'calcio_ca', 'magnesio_mg', 'micronutrientes',
            # Dosagem
            'dosagem_minima', 'dosagem_maxima', 'unidade_dosagem', 'modo_aplicacao',
            # Segurança
            'culturas_registradas', 'intervalo_seguranca', 'epi_obrigatorio', 'incompatibilidades',
            # Armazenamento
            'temperatura_armazenamento', 'inflamavel', 'corrosivo', 'toxico',
        ]
        widgets = {
            # Identificação
            'codigo': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Deixe vazio para gerar automaticamente'
            }),
            'codigo_barras': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'EAN/GTIN'}),
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome completo do produto'}),
            'nome_resumido': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome resumido'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            
            # Classificação
            'categoria': CategoriaSelect(attrs={'class': 'form-select'}),
            'subcategoria': SubCategoriaSelect(attrs={'class': 'form-select'}),
            
            # Unidades
            'unidade_medida': forms.Select(attrs={'class': 'form-select'}),
            'unidade_compra': forms.Select(attrs={'class': 'form-select'}),
            'unidade_venda': forms.Select(attrs={'class': 'form-select'}),
            'fator_conversao': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
            'peso_liquido_unitario': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'peso_bruto_unitario':   forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),

            # Fiscal
            'ncm': forms.Select(attrs={'class': 'form-select'}),
            'cest': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0000000', 'maxlength': '7'}),
            'tipo_item': forms.Select(attrs={'class': 'form-select'}),
            
            # Financeiro
            'preco_custo': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'preco_venda': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'margem_lucro': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'preco_minimo': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            
            # Estoque
            'controla_estoque': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'estoque_minimo': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'estoque_maximo': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'estoque_atual': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'readonly': 'readonly'}),
            'localizacao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Prateleira A1'}),
            'armazem_padrao': forms.Select(attrs={'class': 'form-select'}),
            
            # Rastreabilidade
            'lote_obrigatorio': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'validade_obrigatoria': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'dias_validade': forms.NumberInput(attrs={'class': 'form-control'}),
            
            # Informações Adicionais
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'imagem': forms.FileInput(attrs={'class': 'form-control'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            
            # Categoria Agrícola
            'categoria_agricola': forms.Select(attrs={'class': 'form-select'}),
            
            # Defensivos
            'ingrediente_ativo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Glifosato'}),
            'concentracao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 480 g/L'}),
            'registro_mapa': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nº do MAPA'}),
            'possui_certificado': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_possui_certificado'}),
            'numero_certificado': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número do certificado'}),
            'data_vencimento_certificado': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'arquivo_certificado': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'classe_toxicologica': forms.Select(attrs={'class': 'form-select'}),
            'classe_ambiental': forms.Select(attrs={'class': 'form-select'}),
            'periodo_carencia': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Dias'}),
            'intervalo_reaplicacao': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Dias'}),
            'periodo_reentrada': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Horas (ex: 24)'}),
            'paises_proibidos': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3, 
                'placeholder': 'Digite os países separados por vírgula. Ex: China, União Europeia, Japão'
            }),
            
            # Fertilizantes
            'tipo_fertilizante': forms.Select(attrs={'class': 'form-select'}),
            'formula_npk': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 20-05-20'}),
            'nitrogenio_n': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '%'}),
            'fosforo_p2o5': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '%'}),
            'potassio_k2o': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '%'}),
            'enxofre_s': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '%'}),
            'calcio_ca': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '%'}),
            'magnesio_mg': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '%'}),
            'micronutrientes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Ex: Zn, B, Fe'}),
            
            # Dosagem
            'dosagem_minima': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'dosagem_maxima': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'unidade_dosagem': forms.Select(attrs={'class': 'form-select'}),
            'modo_aplicacao': forms.Select(attrs={'class': 'form-select'}),
            
            # Segurança
            'culturas_registradas': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'intervalo_seguranca': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Horas'}),
            'epi_obrigatorio': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'incompatibilidades': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            
            # Armazenamento
            'temperatura_armazenamento': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 15-25°C'}),
            'inflamavel': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'corrosivo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'toxico': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()

        categoria_agricola = cleaned_data.get('categoria_agricola')
        categoria = cleaned_data.get('categoria')
        if not categoria_agricola and categoria:
            codigo = (getattr(categoria, 'codigo', '') or '').strip().upper()
            nome = (getattr(categoria, 'nome', '') or '').strip().lower()
            if codigo.startswith('FERT') or 'fertiliz' in nome:
                cleaned_data['categoria_agricola'] = 'FERTILIZANTE'
            elif codigo.startswith('DEF') or 'defensiv' in nome:
                cleaned_data['categoria_agricola'] = 'DEFENSIVO'

        for campo, valor in cleaned_data.items():
            setattr(self.instance, campo, valor)

        try:
            self.instance.clean()
        except ValidationError as exc:
            if hasattr(exc, 'message_dict'):
                for campo, mensagens in exc.message_dict.items():
                    if campo in self.fields:
                        for mensagem in mensagens:
                            self.add_error(campo, mensagem)
                    else:
                        for mensagem in mensagens:
                            self.add_error(None, mensagem)
            else:
                self.add_error(None, exc)

        return cleaned_data


class ProdutoTributacaoForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        # Filtrar por empresa
        if empresa:
            self.fields['natureza_operacao'].queryset = NaturezaOperacao.objects.filter(empresa=empresa)
            # Importar EmpresaCFOP e CFOP aqui para evitar import circular
            from cadastros.models import EmpresaCFOP, CFOP
            empresa_cfop_codigos = list(EmpresaCFOP.objects.filter(empresa=empresa, ativo=True).values_list('codigo', flat=True))
            print(f"[DEBUG] Empresa: {empresa}")
            print(f"[DEBUG] Códigos EmpresaCFOP: {empresa_cfop_codigos}")
            cfops_filtrados = list(CFOP.objects.filter(codigo__in=empresa_cfop_codigos, ativo=True))
            print(f"[DEBUG] CFOPs filtrados: {cfops_filtrados}")
            self.fields['cfop'].queryset = CFOP.objects.filter(codigo__in=empresa_cfop_codigos, ativo=True)
    
    class Meta:
        model = ProdutoTributacao
        fields = [
            'produto', 'cfop', 'natureza_operacao', 'descricao', 'origem_mercadoria',
            # ICMS
            'icms_situacao_tributaria', 'icms_modalidade_base', 'icms_aliquota',
            'icms_reducao_base', 'icms_base_calculo',
            # ICMS ST
            'icms_st_aliquota', 'icms_st_mva', 'icms_st_reducao_base',
            # IPI
            'ipi_situacao_tributaria', 'ipi_aliquota', 'ipi_codigo_enquadramento',
            # PIS
            'pis_situacao_tributaria', 'pis_aliquota', 'pis_base_calculo', 'natureza_receita_pis',
            # COFINS
            'cofins_situacao_tributaria', 'cofins_aliquota', 'cofins_base_calculo', 'natureza_receita_cofins',
            # Outros
            'beneficio_fiscal', 'padrao', 'ativo', 'observacoes',
        ]
        widgets = {
            'produto': forms.Select(attrs={'class': 'form-select'}),
            'cfop': forms.Select(attrs={'class': 'form-select'}),
            'natureza_operacao': forms.Select(attrs={'class': 'form-select'}),
            'descricao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Será preenchido automaticamente'}),
            'origem_mercadoria': forms.Select(attrs={'class': 'form-select'}),
            'icms_situacao_tributaria': forms.Select(attrs={'class': 'form-select'}),
            'icms_modalidade_base': forms.Select(attrs={'class': 'form-select'}),
            'icms_aliquota': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '%'}),
            'icms_reducao_base': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '%'}),
            'icms_base_calculo': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '%'}),
            
            # ICMS ST
            'icms_st_aliquota': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '%'}),
            'icms_st_mva': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '%'}),
            'icms_st_reducao_base': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '%'}),
            
            # IPI
            'ipi_situacao_tributaria': forms.Select(attrs={'class': 'form-select'}),
            'ipi_aliquota': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '%'}),
            'ipi_codigo_enquadramento': forms.TextInput(attrs={'class': 'form-control', 'value': '999'}),
            
            # PIS
            'pis_situacao_tributaria': forms.Select(attrs={'class': 'form-select', 'id': 'id_pis_situacao_tributaria'}),
            'pis_aliquota': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '%'}),
            'pis_base_calculo': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '%'}),
            'natureza_receita_pis': forms.TextInput(attrs={
                'class': 'form-control', 'maxlength': '3',
                'placeholder': 'Ex: 116', 'list': 'natureza-receita-list',
                'autocomplete': 'off',
            }),
            # COFINS
            'cofins_situacao_tributaria': forms.Select(attrs={'class': 'form-select', 'id': 'id_cofins_situacao_tributaria'}),
            'cofins_aliquota': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '%'}),
            'cofins_base_calculo': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '%'}),
            'natureza_receita_cofins': forms.TextInput(attrs={
                'class': 'form-control', 'maxlength': '3',
                'placeholder': 'Ex: 116', 'list': 'natureza-receita-list',
                'autocomplete': 'off',
            }),
            
            # Outros
            'beneficio_fiscal': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código'}),
            'padrao': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class ProdutoDefensivoCulturaForm(forms.ModelForm):
    """Formulário para registrar cultura e praga combatida por defensivo"""
    
    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        
        # Filtrar unidades de dosagem, culturas e pragas por empresa
        if empresa:
            self.fields['unidade_dosagem'].queryset = UnidadeMedida.objects.filter(empresa=empresa)
            self.fields['unidade_dosagem_calc'].queryset = UnidadeMedida.objects.filter(empresa=empresa)
            # Importar Cultura e Praga aqui para evitar import circular
            from cadastros.models import Cultura, Praga
            self.fields['cultura'].queryset = Cultura.objects.filter(empresa=empresa).order_by('nome')
            self.fields['praga'].queryset = Praga.objects.filter(empresa=empresa, ativa=True).order_by('nome_comum')
    
    class Meta:
        model = ProdutoDefensivoCultura
        fields = [
            'cultura', 'praga',
            'dosagem_minima', 'dosagem_maxima', 'unidade_dosagem',
            'dosagem_minima_calc', 'dosagem_maxima_calc', 'unidade_dosagem_calc',
            'volume_calda_aplicacao', 'dosagem_calculada_ha',
            'carencia', 'quantidade_maxima_aplicacoes', 'intervalo_reaplicacao', 'mrl',
            'volume_calda_minimo', 'volume_calda_maximo',
            'observacoes',
        ]
        widgets = {
            'cultura': forms.Select(attrs={
                'class': 'form-select'
            }),
            'praga': forms.Select(attrs={
                'class': 'form-select'
            }),
            'dosagem_minima': forms.NumberInput(attrs={
                'class': 'form-control', 
                'step': '0.001',
                'placeholder': 'Ex: 1.5'
            }),
            'dosagem_maxima': forms.NumberInput(attrs={
                'class': 'form-control', 
                'step': '0.001',
                'placeholder': 'Ex: 2.5'
            }),
            'unidade_dosagem': forms.Select(attrs={'class': 'form-select'}),
            'dosagem_minima_calc': forms.NumberInput(attrs={
                'class': 'form-control', 
                'step': '0.001',
                'placeholder': 'Conversão automática',
                'style': 'background-color: #e8f5e9;',
                'readonly': True
            }),
            'dosagem_maxima_calc': forms.NumberInput(attrs={
                'class': 'form-control', 
                'step': '0.001',
                'placeholder': 'Conversão automática',
                'style': 'background-color: #e8f5e9;',
                'readonly': True
            }),
            'unidade_dosagem_calc': forms.Select(attrs={
                'class': 'form-select',
                'style': 'background-color: #e8f5e9;'
            }),
            'volume_calda_aplicacao': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Ex: 500',
                'style': 'background-color: #fff3cd;'
            }),
            'dosagem_calculada_ha': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.001',
                'placeholder': 'Cálculo automático',
                'style': 'background-color: #fff3cd;',
                'readonly': True
            }),
            'carencia': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Dias entre última aplicação e colheita'
            }),
            'quantidade_maxima_aplicacoes': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: 3'
            }),
            'intervalo_reaplicacao': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Dias entre aplicações'
            }),
            'mrl': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.001',
                'placeholder': 'Ex: 0.001 (mg/kg)'
            }),
            'volume_calda_minimo': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Litros por hectare'
            }),
            'volume_calda_maximo': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Litros por hectare'
            }),
            'observacoes': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 2,
                'placeholder': 'Informações adicionais sobre esta aplicação'
            }),
        }
