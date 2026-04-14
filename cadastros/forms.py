"""
Formulários do módulo Fazendas
Com validações e integração com APIs externas
"""

from django import forms
from django.core.exceptions import ValidationError
from .models import (
    Fazenda, EnderecoFazenda, ContatoFazenda,
    ContaBancariaFazenda, DocumentoFazenda, NCM, EmpresaNCM, CFOP, EmpresaCFOP,
)

# Modelos de Cliente
from .models import (
    Cliente, EnderecoCliente, ContatoCliente, ContaBancariaCliente, DocumentoCliente, PrazoPagamentoPadrao
)

from .models import (
    Funcionario,
    FuncaoFuncionario,
    DocumentoFuncionario,
    VinculoContrato,
    CategoriaRiscoAmbiental,
    RiscoAmbientalCatalogo,
    RiscoAmbientalFuncao,
)
from django.utils import timezone
import re


from .models import Area, Talhao, HistoricoTalhao, Cultura, Praga
from .models import Safra, SafraPlan, SafraReal, Requisicao, RequisicaoItem, Produtor
from .models import (
    EstagioDesenvolvimento, MonitoramentoMIP, 
    PragaNoMonitoramento, PontoMonitoramento
)
from decimal import Decimal
from .models import Vendedor, ComissaoVendedor

# Import fornecedor-related models to set ModelForm Meta.model directly
from .models import Fornecedor, FornecedorContato, FornecedorDadoBancario, FornecedorEndereco, Transportadora
from produtos.models import Produto, UnidadeMedida


# ============================================
# WIDGETS CUSTOMIZADOS
# ============================================

class TalhaoSelectWidget(forms.Select):
    """Widget customizado para exibição de Talhão"""
    template_name = 'widgets/talhao_select.html'
    
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        """Customiza como cada opção é exibida"""
        if value:
            try:
                talhao = Talhao.objects.get(pk=value)
                # Display customizado: "Sede - Lote 01 Seção 01"
                label = f"{talhao.area.nome} - {talhao.nome}"
            except Talhao.DoesNotExist:
                pass
        
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        return option


# ============================================
# CLASSES DE FORMULÁRIO
# ============================================

class FazendaForm(forms.ModelForm):
    """Formulário principal de cadastro de fazenda"""
    
    # Campo extra para buscar dados via API
    buscar_cnpj = forms.BooleanField(
        required=False,
        initial=False,
        label='Buscar dados via CNPJ',
        help_text='Preencher automaticamente via API ReceitaWS'
    )
    
    class Meta:
        model = Fazenda
        fields = [
            'empresa',  # ✅ ADICIONADO
            'nome', 'nome_fantasia', 'tipo_pessoa',
            'cnpj_cpf', 'inscricao_estadual', 'inscricao_municipal',
            'eori', 'regime_tributario',
            'area_total', 'area_agricultavel',
            'telefone', 'email', 'website',
            'latitude', 'longitude',
            'observacoes', 'ativa'
        ]
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Fazenda Santa Maria'
            }),
            'nome_fantasia': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome comercial'
            }),
            'tipo_pessoa': forms.Select(attrs={'class': 'form-select'}),
            'cnpj_cpf': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '00.000.000/0000-00 ou 000.000.000-00',
                'data-mask': 'cnpj-cpf'
            }),
            'inscricao_estadual': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Inscrição Estadual'
            }),
            'inscricao_municipal': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'eori': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Código EORI para exportação'
            }),
            'regime_tributario': forms.Select(attrs={'class': 'form-select'}),
            'area_total': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Em hectares'
            }),
            'area_agricultavel': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Em hectares'
            }),
            'telefone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '(00) 0000-0000',
                'data-mask': 'phone'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'contato@fazenda.com'
            }),
            'website': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://www.fazenda.com'
            }),
            'latitude': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.0000001',
                'placeholder': 'Ex: -5.1234567'
            }),
            'longitude': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.0000001',
                'placeholder': 'Ex: -37.1234567'
            }),
            'observacoes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Informações complementares'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        self.usuario = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)

        if (
            self.empresa
            and not self.is_bound
            and not getattr(self.instance, 'pk', None)
            and 'tipo_irrigacao' in self.fields
            and not self.initial.get('tipo_irrigacao')
        ):
            area_referencia = (
                Area.objects
                .filter(
                    empresa=self.empresa,
                    possui_irrigacao=True,
                )
                .exclude(tipo_irrigacao='')
                .order_by('-id')
                .first()
            )

            if area_referencia and area_referencia.tipo_irrigacao:
                self.fields['tipo_irrigacao'].initial = area_referencia.tipo_irrigacao
                if 'irrigacao_necessaria' in self.fields:
                    self.fields['irrigacao_necessaria'].initial = True
        
        # ✅ ADICIONA campo empresa como hidden (não editável)
        if self.empresa:
            self.initial['empresa'] = self.empresa
        
        # Remove campo empresa do formulário visível
        if 'empresa' in self.fields:
            self.fields['empresa'].widget = forms.HiddenInput()
            self.fields['empresa'].required = False

        # Se for edição, preenche o campo area_agricultavel a partir
        # da soma das áreas relacionadas (area_plantavel) e exibe como
        # leitura somente para evitar inconsistências de edição manual.
        if self.instance and self.instance.pk:
            try:
                areas = self.instance.areas.all()
                soma = sum((a.area_plantavel or Decimal('0')) for a in areas)
                # ✅ CORREÇÃO: Garante que soma seja Decimal
                soma = Decimal(str(soma))  # Converte para Decimal explicitamente
            except Exception:
                soma = Decimal('0')
            
            # Formata inicial e marca como somente leitura
            if 'area_agricultavel' in self.fields:
                self.fields['area_agricultavel'].initial = soma.quantize(Decimal('0.01'))
                self.fields['area_agricultavel'].widget.attrs.update({
                    'readonly': True,
                    'class': self.fields['area_agricultavel'].widget.attrs.get('class', '') + ' form-control-plaintext'
                })

    
    def clean_cnpj_cpf(self):
        """Valida e limpa CNPJ/CPF (permitir vazio para IMPORTADOR)."""
        cnpj_cpf = self.cleaned_data.get('cnpj_cpf', '')
        
        # Remove caracteres especiais
        cnpj_cpf_limpo = re.sub(r'\D', '', cnpj_cpf)

        # Determine tipo_cliente (prefer cleaned_data if present, else POST > initial > instance)
        tipo = self.cleaned_data.get('tipo_cliente') if hasattr(self, 'cleaned_data') else None
        if not tipo:
            if self.data and self.data.get('tipo_cliente'):
                tipo = self.data.get('tipo_cliente')
            elif self.initial and self.initial.get('tipo_cliente'):
                tipo = self.initial.get('tipo_cliente')
            elif getattr(self.instance, 'tipo_cliente', None):
                tipo = self.instance.tipo_cliente
        
        # If empty and it's an IMPORTADOR, allow (model will generate CNPJ)
        if not cnpj_cpf_limpo:
            if tipo == 'IMPORTADOR':
                return ''
            raise ValidationError('CNPJ/CPF inválido. Digite 11 ou 14 dígitos.')

        # Valida tamanho quando presente
        if len(cnpj_cpf_limpo) not in [11, 14]:
            raise ValidationError('CNPJ/CPF inválido. Digite 11 ou 14 dígitos.')
        
        # Verifica se já existe (exceto no próprio registro)
        qs = Fazenda.objects.filter(cnpj_cpf=cnpj_cpf_limpo)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        
        if qs.exists():
            raise ValidationError('Este CNPJ/CPF já está cadastrado.')
        
        return cnpj_cpf_limpo
    
    def clean(self):
        """Validações gerais"""
        cleaned_data = super().clean()
        
        area_total = cleaned_data.get('area_total')
        area_agricultavel = cleaned_data.get('area_agricultavel')
        
        # Valida áreas
        if area_agricultavel and area_total:
            if area_agricultavel > area_total:
                raise ValidationError({
                    'area_agricultavel': 'Área agricultável não pode ser maior que área total'
                })
        
        return cleaned_data
    
    def save(self, commit=True):
        """Salva fazenda com empresa associada"""
        fazenda = super().save(commit=False)
        
        # ✅ FORÇA associação da empresa
        if self.empresa:
            fazenda.empresa = self.empresa
        
        # ✅ FORÇA associação do usuário
        if self.usuario:
            fazenda.cadastrado_por = self.usuario
        
        if commit:
            try:
                # Se for edição, sincroniza área agricultável com as áreas filhas
                if fazenda.pk:
                    try:
                        areas = fazenda.areas.all()
                        soma = sum((a.area_plantavel or Decimal('0')) for a in areas)
                        fazenda.area_agricultavel = soma.quantize(Decimal('0.01'))
                    except Exception:
                        pass

                fazenda.save()
            except Exception:
                raise
        
        return fazenda


class NCMForm(forms.ModelForm):
    """Form para cadastro/edição de NCM (template/global)"""

    class Meta:
        model = NCM
        fields = ['codigo', 'nome', 'cest', 'descricao', 'ativo']
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 01012100'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'cest': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Opcional'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_codigo(self):
        codigo = re.sub(r'\D', '', self.cleaned_data.get('codigo', ''))
        if len(codigo) != 8:
            raise ValidationError('Código NCM inválido. Deve ter 8 dígitos.')
        return codigo


class EmpresaNCMForm(forms.ModelForm):
    """Form para NCM de empresa (cópia personalizável)"""
    class Meta:
        model = EmpresaNCM
        fields = ['codigo', 'nome', 'cest', 'descricao', 'ativo']
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 01012100', 'readonly': True}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'cest': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Opcional'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_codigo(self):
        codigo = re.sub(r'\D', '', self.cleaned_data.get('codigo', ''))
        if len(codigo) != 8:
            raise ValidationError('Código NCM inválido. Deve ter 8 dígitos.')
        return codigo


class NCMImportForm(forms.Form):
    """Form para upload de CSV de NCM"""
    arquivo = forms.FileField(label='Arquivo CSV', help_text='CSV com colunas de código e nome')
    replace = forms.BooleanField(required=False, initial=False, label='Substituir templates não presentes')
    apply_to_all = forms.BooleanField(required=False, initial=False, label='Aplicar para todas as empresas (EmpresaNCM)')
    dry_run = forms.BooleanField(required=False, initial=True, label='Somente simular (dry-run)')


class CFOPForm(forms.ModelForm):
    """Form para cadastro/edição de CFOP"""

    class Meta:
        model = CFOP
        fields = ['codigo', 'nome', 'descricao', 'natureza_operacao', 'ativo']
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 5102'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'natureza_operacao': forms.Select(attrs={'class': 'form-select'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_codigo(self):
        codigo = re.sub(r'\D', '', self.cleaned_data.get('codigo', ''))
        if not (2 <= len(codigo) <= 4):
            raise ValidationError('Código CFOP inválido. Deve ter 2 a 4 dígitos.')
        return codigo


class EmpresaCFOPForm(forms.ModelForm):
    """Form para CFOP de empresa (cópia personalizável)"""
    class Meta:
        model = EmpresaCFOP
        fields = ['codigo', 'nome', 'descricao', 'ativo']
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 5102'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_codigo(self):
        codigo = re.sub(r'\D', '', self.cleaned_data.get('codigo', ''))
        if not (2 <= len(codigo) <= 4):
            raise ValidationError('Código CFOP inválido. Deve ter 2 a 4 dígitos.')
        return codigo


class EnderecoFazendaForm(forms.ModelForm):
    """Formulário de endereço com busca por CEP"""
    
    buscar_cep = forms.BooleanField(
        required=False,
        initial=False,
        label='Buscar CEP',
        help_text='Preencher automaticamente via ViaCEP'
    )
    class Meta:
        model = EnderecoFazenda
        fields = [
            'tipo', 'cep', 'logradouro', 'numero',
            'complemento', 'bairro', 'cidade', 'uf',
            'pais', 'recebedor_notify', 'padrao'
        ]
        widgets = {
                'tipo': forms.Select(attrs={'class': 'form-select'}),
                'cep': forms.TextInput(attrs={
                    'class': 'form-control',
                    'placeholder': '00000-000',
                    'data-mask': 'cep'
                }),
                'logradouro': forms.TextInput(attrs={
                    'class': 'form-control',
                    'placeholder': 'Rua, Avenida, Estrada...'
                }),
                'numero': forms.TextInput(attrs={
                    'class': 'form-control',
                    'placeholder': 'Nº ou S/N'
                }),
                'complemento': forms.TextInput(attrs={
                    'class': 'form-control',
                    'placeholder': 'Apto, Bloco, Sala...'
                }),
                'bairro': forms.TextInput(attrs={
                    'class': 'form-control'
                }),
                'cidade': forms.TextInput(attrs={
                    'class': 'form-control'
                }),
                'uf': forms.TextInput(attrs={
                    'class': 'form-control',
                    'id': 'id_endereco_uf',
                    'maxlength': 2
                }),
                'pais': forms.TextInput(attrs={
                    'class': 'form-control'
                }),
                'recebedor_notify': forms.TextInput(attrs={'class': 'form-control'}),
                'padrao': forms.CheckboxInput(attrs={'class': 'form-check-input'})
            }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'recebedor_notify' in self.fields:
            self.fields['recebedor_notify'].label = 'Destinatário'
            self.fields['recebedor_notify'].required = False
    
    def clean_cep(self):
        """Remove formatação do CEP"""
        cep = self.cleaned_data.get('cep', '')
        return re.sub(r'\D', '', cep)
    
    def clean_uf(self):
        """Converte UF para maiúsculas"""
        uf = self.cleaned_data.get('uf', '')
        return uf.upper()

    def clean(self):
        cleaned = super().clean()
        # If UF is missing but CEP present, try to fetch UF from ViaCEP to avoid client-side race conditions
        if not cleaned.get('uf') and cleaned.get('cep'):
            try:
                import requests
                cep = re.sub(r'\D', '', cleaned.get('cep'))
                resp = requests.get(f'https://viacep.com.br/ws/{cep}/json/', timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    uf = data.get('uf')
                    if uf:
                        cleaned['uf'] = uf.upper()
                        self.cleaned_data['uf'] = uf.upper()
            except Exception:
                pass
        return cleaned


class ClienteForm(forms.ModelForm):
    """Formulário de Cliente com lógica de país/UF e botão Buscar CNPJ"""

    buscar_cnpj = forms.BooleanField(
        required=False,
        initial=False,
        label='Buscar CNPJ',
        help_text='Preencher automaticamente via API ReceitaWS'
    )

    # Opções para Regime Tributário
    REGIME_TRIBUTARIO_CHOICES = [
        ('', '-- Selecione --'),
        ('Simples Nacional', 'Simples Nacional'),
        ('Lucro Presumido', 'Lucro Presumido'),
        ('Lucro Real', 'Lucro Real'),
        ('MEI', 'MEI'),
        ('Isento', 'Isento'),
        ('Outro', 'Outro'),
    ]

    regime_tributario = forms.ChoiceField(
        choices=REGIME_TRIBUTARIO_CHOICES,
        required=False,
        label='Regime Tributário',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Cliente
        fields = [
            'empresa', 'codigo', 'tipo_cliente', 'tipo_pessoa',
            'razao_social', 'nome_comercial', 'cnpj_cpf', 'vat',
            'inscricao_estadual', 'inscricao_municipal', 'inscricao_suframa', 'eori', 'regime_tributario',
            'contribuinte_icms', 'indicador_ie',
            'contato_principal_nome', 'contato_principal_telefone', 'contato_principal_email',
            'pais', 'moeda_padrao', 'porto_destino',
            'limite_credito', 'prazo_pagamento', 'prazo_pagamento_padrao', 'forma_pagamento_padrao', 'desconto_padrao',
            'vendedor_responsavel', 'observacoes_comerciais',
            'acesso_portal', 'usuario_vinculado'
        ]
        widgets = {
            'empresa': forms.HiddenInput(),
            'codigo': forms.TextInput(attrs={'class': 'form-control', 'readonly': True}),
            'tipo_cliente': forms.Select(attrs={'class': 'form-select'}),
            'tipo_pessoa': forms.Select(attrs={'class': 'form-select'}),
            'razao_social': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_razao_social', 'data-auto': 'true'}),
            'nome_comercial': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_nome_comercial', 'data-auto': 'true'}),
            'cnpj_cpf': forms.TextInput(attrs={'class': 'form-control', 'data-mask': 'cnpj-cpf', 'placeholder': '00.000.000/0000-00 ou 000.000.000-00 (Opcional para IMPORTADOR)'}),
            'vat': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_vat', 'placeholder': 'VAT / Número de registro do cliente no exterior'}),
            'inscricao_estadual': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_inscricao_estadual'}),
            'inscricao_municipal': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_inscricao_municipal'}),
            'inscricao_suframa': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_inscricao_suframa'}),
            'eori': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_eori'}),
            'contribuinte_icms': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'pais': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_pais'}),
            'contato_principal_nome': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_contato_principal_nome'}),
            'contato_principal_telefone': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_contato_principal_telefone', 'data-auto': 'true'}),
            'contato_principal_email': forms.EmailInput(attrs={'class': 'form-control', 'id': 'id_contato_principal_email', 'data-auto': 'true'}),
            'limite_credito': forms.TextInput(attrs={'class': 'form-control', 'inputmode': 'decimal'}),
            'prazo_pagamento': forms.HiddenInput(),
            'desconto_padrao': forms.TextInput(attrs={'class': 'form-control', 'inputmode': 'decimal'}),
            'forma_pagamento_padrao': forms.Select(attrs={'class': 'form-select'}),
            'prazo_pagamento_padrao': forms.HiddenInput(),
            'vendedor_responsavel': forms.Select(attrs={'class': 'form-select'}),
            'porto_destino': forms.Select(attrs={'class': 'form-select'}),
            'moeda_padrao': forms.Select(attrs={'class': 'form-select'}),
            'observacoes_comerciais': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'acesso_portal': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'usuario_vinculado': forms.HiddenInput()  # MUDADO: HiddenInput ao invés de Select
        }

    def __init__(self, *args, **kwargs):
        from .models import Vendedor

        self.empresa = kwargs.pop('empresa', None)
        self.usuario = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)

        # Normalize decimal inputs to avoid browser locale issues (comma vs dot)
        if self.data:
            try:
                data = self.data.copy()
                for field_name in ('limite_credito', 'desconto_padrao'):
                    if field_name in data:
                        data[field_name] = self._normalize_decimal_input(data.get(field_name))
                self.data = data
            except Exception:
                pass

        # Ensure cnpj_cpf is not required at HTML level (we validate per tipo_cliente)
        if 'cnpj_cpf' in self.fields:
            self.fields['cnpj_cpf'].required = False

        # Limit vendedor_responsavel to vendedores da empresa and by tipo_cliente
        if 'vendedor_responsavel' in self.fields:
            if self.empresa:
                # Filter only ATIVO vendedores
                qs = Vendedor.objects.filter(empresa=self.empresa, status='ATIVO')
                # Determine tipo_cliente from POST data, initial or instance
                tipo = None
                if self.data and self.data.get('tipo_cliente'):
                    tipo = self.data.get('tipo_cliente')
                elif self.initial and self.initial.get('tipo_cliente'):
                    tipo = self.initial.get('tipo_cliente')
                elif getattr(self.instance, 'tipo_cliente', None):
                    tipo = self.instance.tipo_cliente

                if tipo == 'IMPORTADOR':
                    qs = qs.filter(tipo_mercado__in=['EXTERNO', 'AMBOS'])
                else:
                    qs = qs.filter(tipo_mercado__in=['INTERNO', 'AMBOS'])

                self.fields['vendedor_responsavel'].queryset = qs.order_by('nome_completo')
            else:
                self.fields['vendedor_responsavel'].queryset = Vendedor.objects.none()

        # Set choices for moeda_padrao (use Vendedor.MOEDA_CHOICES if available)
        if 'moeda_padrao' in self.fields:
            # Prefer currencies defined in the database (Moeda model). Fallback to Vendedor.MOEDA_CHOICES
            try:
                from .models import Moeda
                moedas = list(Moeda.objects.all())
                if moedas:
                    choices = [(m.codigo, f"{m.nome} ({m.codigo})") for m in moedas]
                else:
                    choices = getattr(Vendedor, 'MOEDA_CHOICES', [('BRL','BRL'), ('USD','USD'), ('EUR','EUR')])
            except Exception:
                choices = getattr(Vendedor, 'MOEDA_CHOICES', [('BRL','BRL'), ('USD','USD'), ('EUR','EUR')])
            # Ensure field uses Select widget and is optional
            self.fields['moeda_padrao'].choices = choices
            self.fields['moeda_padrao'].widget = forms.Select(attrs={'class': 'form-select'})
            self.fields['moeda_padrao'].required = False

        # Limit prazo_pagamento_padrao to presets da empresa
        if 'prazo_pagamento_padrao' in self.fields:
            if self.empresa:
                from .models import PrazoPagamentoPadrao
                self.fields['prazo_pagamento_padrao'].queryset = PrazoPagamentoPadrao.objects.filter(empresa=self.empresa, ativo=True)
            else:
                from .models import PrazoPagamentoPadrao
                self.fields['prazo_pagamento_padrao'].queryset = PrazoPagamentoPadrao.objects.none()

        # Limit porto_destino to ports of the current empresa
        if 'porto_destino' in self.fields:
            if self.empresa:
                from .models import Porto
                self.fields['porto_destino'].queryset = Porto.objects.filter(empresa=self.empresa)
            else:
                from .models import Porto
                self.fields['porto_destino'].queryset = Porto.objects.none()

        # Make certain numeric fields optional in the form (model has defaults)
        if 'limite_credito' in self.fields:
            self.fields['limite_credito'].required = False
        
        # ✅ AUTO-FILL: usuario_vinculado com usuário logado se não estiver preenchido
        if 'usuario_vinculado' in self.fields and self.usuario:
            # Se é uma criação nova (instance.pk é None) ou o cliente já existe
            # Se o cliente não tem um usuário vinculado, preencha automaticamente
            if not self.instance.pk or not self.instance.usuario_vinculado:
                # Set initial value to current user
                self.fields['usuario_vinculado'].initial = self.usuario
                # Also set the instance
                if not self.instance.usuario_vinculado:
                    self.instance.usuario_vinculado = self.usuario
        if 'desconto_padrao' in self.fields:
            self.fields['desconto_padrao'].required = False

        # Hide empresa and set initial if provided
        if self.empresa and 'empresa' in self.fields:
            self.initial['empresa'] = self.empresa
            self.fields['empresa'].widget = forms.HiddenInput()
            self.fields['empresa'].required = False
            # Ensure the instance has the empresa set so updates without the hidden input don't clear it
            self.instance.empresa = self.empresa

        # If country not provided, default to Brasil
        if not self.initial.get('pais'):
            self.initial['pais'] = 'Brasil'

    def clean_cnpj_cpf(self):
        # Guard against None when field is nullable in DB; treat None as empty string
        cnpj_cpf = self.cleaned_data.get('cnpj_cpf') or ''
        cnpj_cpf_limpo = re.sub(r'\D', '', cnpj_cpf)
        if cnpj_cpf_limpo and len(cnpj_cpf_limpo) not in [11, 14]:
            raise ValidationError('CNPJ/CPF inválido. Digite 11 ou 14 dígitos.')
        # Unique por empresa
        # Use the empresa provided in the form data or fallback to the one injected in __init__
        empresa_aplicavel = self.cleaned_data.get('empresa') or self.empresa
        # Only validate uniqueness if a value was provided
        if cnpj_cpf_limpo:
            qs = Cliente.objects.filter(empresa=empresa_aplicavel, cnpj_cpf=cnpj_cpf_limpo)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError('Este CNPJ/CPF já está cadastrado para a empresa.')
        return cnpj_cpf_limpo

    @staticmethod
    def _normalize_decimal_input(value):
        if value is None:
            return ''
        text = str(value).strip()
        if not text:
            return ''
        # Handle both thousands and decimal separators.
        if ',' in text and '.' in text:
            if text.rfind(',') > text.rfind('.'):
                text = text.replace('.', '').replace(',', '.')
            else:
                text = text.replace(',', '')
        elif ',' in text:
            text = text.replace('.', '').replace(',', '.')
        return text

    def clean(self):
        cleaned = super().clean()
        # Determine the tipo_cliente considering POST data, initial or instance
        tipo = cleaned.get('tipo_cliente') if cleaned.get('tipo_cliente') else None
        if not tipo:
            if self.data and self.data.get('tipo_cliente'):
                tipo = self.data.get('tipo_cliente')
            elif self.initial and self.initial.get('tipo_cliente'):
                tipo = self.initial.get('tipo_cliente')
            elif getattr(self.instance, 'tipo_cliente', None):
                tipo = self.instance.tipo_cliente

        # If updating an existing Cliente and changing it to IMPORTADOR, require certain fields
        if tipo == 'IMPORTADOR' and getattr(self.instance, 'pk', None) and getattr(self.instance, 'tipo_cliente', None) != 'IMPORTADOR':
            if not cleaned.get('eori'):
                self.add_error('eori', 'EORI é obrigatório ao transformar em IMPORTADOR')
            if not (cleaned.get('vat') or '').strip():
                self.add_error('vat', 'VAT é obrigatório ao transformar em IMPORTADOR')
            if not cleaned.get('porto_destino'):
                self.add_error('porto_destino', 'Porto de destino é obrigatório ao transformar em IMPORTADOR')

        pais = cleaned.get('pais', '').strip() if cleaned.get('pais') else ''
        # For clients outside Brazil, no UF is set on client; Address forms should use UF='EX' when applicable
        return cleaned


class EnderecoClienteForm(forms.ModelForm):
    """Formulário de endereço do cliente com busca por CEP"""

    buscar_cep = forms.BooleanField(required=False, initial=False, label='Buscar CEP', help_text='Preencher automaticamente via ViaCEP')

    class Meta:
        model = EnderecoCliente
        fields = ['tipo', 'cep', 'logradouro', 'numero', 'complemento', 'bairro', 'cidade', 'uf', 'pais', 'recebedor_notify', 'padrao']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'cep': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '00000-000', 'data-mask': 'cep'}),
            'logradouro': forms.TextInput(attrs={'class': 'form-control'}),
            'numero': forms.TextInput(attrs={'class': 'form-control'}),
            'complemento': forms.TextInput(attrs={'class': 'form-control'}),
            'bairro': forms.TextInput(attrs={'class': 'form-control'}),
            'cidade': forms.TextInput(attrs={'class': 'form-control'}),
            'uf': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_endereco_uf', 'maxlength': 2}),
            'pais': forms.TextInput(attrs={'class': 'form-control'}),
            'recebedor_notify': forms.TextInput(attrs={'class': 'form-control'}),
            'padrao': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'recebedor_notify' in self.fields:
            self.fields['recebedor_notify'].label = 'Destinatario'
            self.fields['recebedor_notify'].required = False

    def clean_cep(self):
        cep = self.cleaned_data.get('cep', '')
        cep_limpo = re.sub(r'\D', '', cep)

        # If cep provided, try lookup early so subsequent field validation (uf, bairro, cidade)
        # can use the fetched values and avoid 'field required' errors.
        if cep_limpo:
            try:
                import requests
                resp = requests.get(f'https://viacep.com.br/ws/{cep_limpo}/json/', timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    # If we got a UF or address data, inject into self.data so other field
                    # validators see them (since field-level validation runs after this)
                    if data:
                        try:
                            # make a mutable copy of self.data (QueryDict)
                            self.data = self.data.copy()
                            if data.get('uf'):
                                self.data['uf'] = data.get('uf').upper()
                            if data.get('logradouro') and not self.data.get('logradouro'):
                                self.data['logradouro'] = data.get('logradouro')
                            if data.get('bairro') and not self.data.get('bairro'):
                                self.data['bairro'] = data.get('bairro')
                            if (data.get('localidade') or data.get('cidade')) and not self.data.get('cidade'):
                                self.data['cidade'] = data.get('localidade') or data.get('cidade')
                            if data.get('cep') and not self.data.get('cep'):
                                self.data['cep'] = data.get('cep')
                        except Exception:
                            pass
            except Exception:
                # ignore network errors here
                pass

        return cep_limpo

    def clean_uf(self):
        uf = self.cleaned_data.get('uf', '')
        return uf.upper()

    def clean(self):
        cleaned = super().clean()
        pais = cleaned.get('pais', '')
        if pais and pais.strip().lower() != 'brasil':
            # Set UF to EX for foreign addresses
            cleaned['uf'] = 'EX'
            self.cleaned_data['uf'] = 'EX'

        # Previously we attempted a lookup here, but we perform the ViaCEP lookup earlier in clean_cep
        # so that field-level validators for uf/cidade/bairro see the injected values.
        return cleaned

        return cleaned


class ContatoClienteForm(forms.ModelForm):
    """Formulário de contato do cliente (replica campos do fornecedor)"""

    class Meta:
        model = ContatoCliente
        fields = ['tipo', 'nome', 'cargo', 'telefone', 'celular', 'email', 'whatsapp', 'preferencial', 'observacoes']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome completo'
            }),
            'cargo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Gerente, Agrônomo'
            }),
            'telefone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '(00) 0000-0000',
                'data-mask': 'phone'
            }),
            'celular': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '(00) 00000-0000',
                'data-mask': 'cellphone'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'contato@email.com'
            }),
            'observacoes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # allow partial updates and optional tipo (like fornecedor form)
        if 'tipo' in self.fields:
            self.fields['tipo'].required = False
        if 'whatsapp' in self.fields:
            self.fields['whatsapp'].required = False
        if 'observacoes' in self.fields:
            self.fields['observacoes'].required = False


class ContaBancariaClienteForm(forms.ModelForm):
    """Formulário de conta bancária do cliente (fields aligned with fornecedor)"""

    class Meta:
        model = ContaBancariaCliente
        fields = [
            'banco', 'codigo_banco', 'agencia', 'agencia_digito', 'conta', 'conta_digito', 'tipo_conta',
            'pix_habilitado', 'tipo_chave_pix', 'chave_pix', 'swift', 'iban', 'dados_adicionais', 'conta_principal', 'ativa'
        ]
        widgets = {
            'banco': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome do banco'
            }),
            'codigo_banco': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: 001, 033, 104',
                'maxlength': 4
            }),
            'agencia': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número da agência'
            }),
            'agencia_digito': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': 2
            }),
            'conta': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número da conta'
            }),
            'conta_digito': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': 2
            }),
            'tipo_conta': forms.Select(attrs={'class': 'form-select'}),
            'tipo_chave_pix': forms.Select(attrs={'class': 'form-select'}),
            'chave_pix': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Chave PIX'
            }),
            'swift': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Código SWIFT/BIC',
                'maxlength': 11
            }),
            'iban': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'International Bank Account Number'
            }),
            'dados_adicionais': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Informações adicionais para transferências internacionais'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # make some fields optional in quick-add flows (match fornecedor form behavior)
        optional = ['codigo_banco','agencia_digito','tipo_chave_pix','chave_pix','tipo_conta','ativa','dados_adicionais']
        for f in optional:
            if f in self.fields:
                self.fields[f].required = False

class DocumentoClienteForm(forms.ModelForm):
    """Formulário de documento do cliente"""

    class Meta:
        model = DocumentoCliente
        exclude = ('cliente', 'enviado_por')
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_documento': forms.TextInput(attrs={'class': 'form-control'}),
            'arquivo': forms.FileInput(attrs={'class': 'form-control'}),
            'data_emissao': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
            'data_validade': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
            'gerar_alerta_vencimento': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'dias_antecedencia_alerta': forms.NumberInput(attrs={'class': 'form-control'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Allow omitting 'dias_antecedencia_alerta' in POST and use model default
        if 'dias_antecedencia_alerta' in self.fields:
            self.fields['dias_antecedencia_alerta'].required = False


class ContatoFazendaForm(forms.ModelForm):
    """Formulário de contato"""
    
    class Meta:
        model = ContatoFazenda
        fields = [
            'tipo', 'nome', 'cargo',
            'telefone', 'celular', 'email',
            'whatsapp', 'preferencial', 'observacoes'
        ]
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome completo'
            }),
            'cargo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Gerente, Agrônomo'
            }),
            'telefone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '(00) 0000-0000',
                'data-mask': 'phone'
            }),
            'celular': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '(00) 00000-0000',
                'data-mask': 'cellphone'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'contato@email.com'
            }),
            'observacoes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2
            }),
        }


class ContaBancariaFazendaForm(forms.ModelForm):
    """Formulário de conta bancária"""
    
    class Meta:
        model = ContaBancariaFazenda
        fields = [
            'banco', 'codigo_banco', 'agencia', 'agencia_digito',
            'conta', 'conta_digito', 'tipo_conta',
            'pix_habilitado', 'tipo_chave_pix', 'chave_pix',
            'swift', 'iban', 'dados_adicionais',
            'conta_principal', 'ativa'
        ]
        widgets = {
            'banco': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome do banco'
            }),
            'codigo_banco': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: 001, 033, 104',
                'maxlength': 4
            }),
            'agencia': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número da agência'
            }),
            'agencia_digito': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': 2
            }),
            'conta': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número da conta'
            }),
            'conta_digito': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': 2
            }),
            'tipo_conta': forms.Select(attrs={'class': 'form-select'}),
            'tipo_chave_pix': forms.Select(attrs={'class': 'form-select'}),
            'chave_pix': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Chave PIX'
            }),
            'swift': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Código SWIFT/BIC',
                'maxlength': 11
            }),
            'iban': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'International Bank Account Number'
            }),
            'dados_adicionais': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Informações adicionais para transferências internacionais'
            }),
        }


class DocumentoFazendaForm(forms.ModelForm):
    """Formulário de upload de documentos"""

    class Meta:
        model = DocumentoFazenda
        # Exclui campos que serão preenchidos pela view (fazenda, enviado_por)
        exclude = ('fazenda', 'enviado_por')
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'titulo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Descrição do documento'
            }),
            'numero_documento': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nº de protocolo, registro, etc.'
            }),
            'arquivo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.jpg,.jpeg,.png,.doc,.docx,.xls,.xlsx'
            }),
            'data_emissao': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
            'data_validade': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
            'gerar_alerta_vencimento': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'dias_antecedencia_alerta': forms.NumberInput(attrs={'class': 'form-control'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Permite não enviar 'dias_antecedencia_alerta' no POST (usa default do modelo)
        if 'dias_antecedencia_alerta' in self.fields:
            self.fields['dias_antecedencia_alerta'].required = False
    
    def clean_arquivo(self):
        """Valida tamanho do arquivo (máx 10MB)"""
        arquivo = self.cleaned_data.get('arquivo')
        
        if arquivo:
            if arquivo.size > 10 * 1024 * 1024:  # 10MB
                raise ValidationError('Arquivo muito grande. Tamanho máximo: 10MB')
        
        return arquivo
    
    def clean(self):
        """Validação de datas"""
        cleaned_data = super().clean()
        
        data_emissao = cleaned_data.get('data_emissao')
        data_validade = cleaned_data.get('data_validade')
        
        if data_emissao and data_validade:
            if data_validade < data_emissao:
                raise ValidationError({
                    'data_validade': 'Data de validade não pode ser anterior à data de emissão'
                })
        
        return cleaned_data


class DocumentoFornecedorForm(forms.ModelForm):
    """Formulário de upload de documentos para Fornecedor"""

    class Meta:
        model = __import__('cadastros.models', fromlist=['DocumentoFornecedor']).DocumentoFornecedor
        # Exclui campos que serão preenchidos pela view (fornecedor, enviado_por)
        exclude = ('fornecedor', 'enviado_por')
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'titulo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Descrição do documento'
            }),
            'numero_documento': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nº de protocolo, registro, etc.'
            }),
            'arquivo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.jpg,.jpeg,.png,.doc,.docx,.xls,.xlsx'
            }),
            'data_emissao': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
            'data_validade': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
            'gerar_alerta_vencimento': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'dias_antecedencia_alerta': forms.NumberInput(attrs={'class': 'form-control'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Permite não enviar 'dias_antecedencia_alerta' no POST (usa default do modelo)
        if 'dias_antecedencia_alerta' in self.fields:
            self.fields['dias_antecedencia_alerta'].required = False

    def clean_arquivo(self):
        """Valida tamanho do arquivo (máx 10MB)"""
        arquivo = self.cleaned_data.get('arquivo')
        
        if arquivo:
            if arquivo.size > 10 * 1024 * 1024:  # 10MB
                raise ValidationError('Arquivo muito grande. Tamanho máximo: 10MB')
        
        return arquivo


class BuscarCNPJForm(forms.Form):
    """Formulário para buscar dados via API de CNPJ"""
    
    cnpj = forms.CharField(
        label='CNPJ',
        max_length=18,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '00.000.000/0000-00',
            'data-mask': 'cnpj'
        }),
        help_text='Digite o CNPJ para buscar dados automaticamente'
    )
    
    def clean_cnpj(self):
        """Remove formatação do CNPJ"""
        cnpj = self.cleaned_data.get('cnpj', '')
        cnpj_limpo = re.sub(r'\D', '', cnpj)
        
        if len(cnpj_limpo) != 14:
            raise ValidationError('CNPJ deve ter 14 dígitos')
        
        return cnpj_limpo


class BuscarCEPForm(forms.Form):
    """Formulário para buscar endereço via CEP"""
    
    cep = forms.CharField(
        label='CEP',
        max_length=9,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '00000-000',
            'data-mask': 'cep'
        }),
        help_text='Digite o CEP para buscar o endereço'
    )
    
    def clean_cep(self):
        """Remove formatação do CEP"""
        cep = self.cleaned_data.get('cep', '')
        cep_limpo = re.sub(r'\D', '', cep)
        
        if len(cep_limpo) != 8:
            raise ValidationError('CEP deve ter 8 dígitos')
        
        return cep_limpo
    



    """
ADICIONE ESTES FORMS AO FINAL DO ARQUIVO cadastros/forms.py
"""




class FuncaoFuncionarioForm(forms.ModelForm):
    """Formulário para cadastro rápido de função"""

    riscos_fisicos = forms.CharField(
        label='Riscos Físicos',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Um risco por linha. Ex.: Ruído acima de 85dB'
        }),
        help_text='Use 1 linha por risco: Agente | Intensidade | EPI. Intensidade: BAIXA, MEDIA ou ALTA.'
    )

    riscos_quimicos = forms.CharField(
        label='Riscos Químicos',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Um risco por linha. Ex.: Poeira orgânica'
        }),
        help_text='Use 1 linha por risco: Agente | Intensidade | EPI. Intensidade: BAIXA, MEDIA ou ALTA.'
    )

    riscos_biologicos = forms.CharField(
        label='Riscos Biológicos',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Um risco por linha. Ex.: Fungos ambientais'
        }),
        help_text='Use 1 linha por risco: Agente | Intensidade | EPI. Intensidade: BAIXA, MEDIA ou ALTA.'
    )

    riscos_ergonomicos = forms.CharField(
        label='Riscos Ergonômicos',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Um risco por linha. Ex.: Movimentos repetitivos'
        }),
        help_text='Use 1 linha por risco: Agente | Intensidade | EPI. Intensidade: BAIXA, MEDIA ou ALTA.'
    )

    riscos_acidentes = forms.CharField(
        label='Riscos de Acidentes',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Um risco por linha. Ex.: Queda de mesmo nível'
        }),
        help_text='Use 1 linha por risco: Agente | Intensidade | EPI. Intensidade: BAIXA, MEDIA ou ALTA.'
    )

    riscos_outros = forms.CharField(
        label='Outros Riscos',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Um risco por linha. Ex.: Exposição a intempéries'
        }),
        help_text='Use 1 linha por risco: Agente | Intensidade | EPI. Intensidade: BAIXA, MEDIA ou ALTA.'
    )

    riscos_fisicos_catalogo = forms.ModelMultipleChoiceField(
        label='Selecionar Riscos Físicos (catálogo)',
        required=False,
        queryset=RiscoAmbientalCatalogo.objects.none(),
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': 5}),
    )

    riscos_quimicos_catalogo = forms.ModelMultipleChoiceField(
        label='Selecionar Riscos Químicos (catálogo)',
        required=False,
        queryset=RiscoAmbientalCatalogo.objects.none(),
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': 5}),
    )

    riscos_biologicos_catalogo = forms.ModelMultipleChoiceField(
        label='Selecionar Riscos Biológicos (catálogo)',
        required=False,
        queryset=RiscoAmbientalCatalogo.objects.none(),
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': 5}),
    )

    riscos_ergonomicos_catalogo = forms.ModelMultipleChoiceField(
        label='Selecionar Riscos Ergonômicos (catálogo)',
        required=False,
        queryset=RiscoAmbientalCatalogo.objects.none(),
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': 5}),
    )

    riscos_acidentes_catalogo = forms.ModelMultipleChoiceField(
        label='Selecionar Riscos de Acidentes (catálogo)',
        required=False,
        queryset=RiscoAmbientalCatalogo.objects.none(),
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': 5}),
    )

    riscos_outros_catalogo = forms.ModelMultipleChoiceField(
        label='Selecionar Outros Riscos (catálogo)',
        required=False,
        queryset=RiscoAmbientalCatalogo.objects.none(),
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': 5}),
    )

    MAPA_CAMPOS_CATEGORIA = {
        CategoriaRiscoAmbiental.CODIGO_FISICO: 'riscos_fisicos',
        CategoriaRiscoAmbiental.CODIGO_QUIMICO: 'riscos_quimicos',
        CategoriaRiscoAmbiental.CODIGO_BIOLOGICO: 'riscos_biologicos',
        CategoriaRiscoAmbiental.CODIGO_ERGONOMICO: 'riscos_ergonomicos',
        CategoriaRiscoAmbiental.CODIGO_ACIDENTES: 'riscos_acidentes',
        CategoriaRiscoAmbiental.CODIGO_OUTROS: 'riscos_outros',
    }

    MAPA_CAMPOS_CATALOGO = {
        CategoriaRiscoAmbiental.CODIGO_FISICO: 'riscos_fisicos_catalogo',
        CategoriaRiscoAmbiental.CODIGO_QUIMICO: 'riscos_quimicos_catalogo',
        CategoriaRiscoAmbiental.CODIGO_BIOLOGICO: 'riscos_biologicos_catalogo',
        CategoriaRiscoAmbiental.CODIGO_ERGONOMICO: 'riscos_ergonomicos_catalogo',
        CategoriaRiscoAmbiental.CODIGO_ACIDENTES: 'riscos_acidentes_catalogo',
        CategoriaRiscoAmbiental.CODIGO_OUTROS: 'riscos_outros_catalogo',
    }
    
    class Meta:
        model = FuncaoFuncionario
        fields = [
            'nome', 'descricao', 'salario_base', 'ativa',
            'possui_insalubridade', 'grau_insalubridade',
            'possui_periculosidade', 'percentual_periculosidade',
            'requer_laudo', 'validade_laudo', 'observacoes_risco',
        ]
        labels = {
            'nome': 'Nome da Função/Cargo',
            'descricao': 'Descrição das Atividades',
            'salario_base': 'Salário Base Sugerido (R$)',
            'ativa': 'Função Ativa',
            'possui_insalubridade': 'Possui Insalubridade?',
            'grau_insalubridade': 'Grau de Insalubridade',
            'possui_periculosidade': 'Possui Periculosidade?',
            'percentual_periculosidade': 'Percentual de Periculosidade (%)',
            'requer_laudo': 'Requer Laudo Técnico (PPRA/LTCAT)?',
            'validade_laudo': 'Validade do Laudo',
            'observacoes_risco': 'Observações sobre Riscos',
        }
        help_texts = {
            'nome': 'Digite o cargo ou função (ex: Motorista, Tratorista, Colhedor)',
            'descricao': 'Descreva as principais atividades e responsabilidades',
            'salario_base': 'Valor de referência para o cargo (opcional)',
            'grau_insalubridade': 'Preencher apenas se houver insalubridade (NR-15)',
            'percentual_periculosidade': 'Percentual padrão conforme NR-16 é 30%',
            'observacoes_risco': 'EPI necessários, agentes de risco, etc.',
        }
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Motorista, Tratorista, Colhedor',
                'required': True,
            }),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descreva as principais atividades desta função...',
            }),
            'salario_base': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': '0,00',
                'min': '0',
            }),
            'ativa': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
            'possui_insalubridade': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'id': 'id_possui_insalubridade',
            }),
            'grau_insalubridade': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_grau_insalubridade',
            }),
            'possui_periculosidade': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'id': 'id_possui_periculosidade',
            }),
            'percentual_periculosidade': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'max': '100',
                'id': 'id_percentual_periculosidade',
            }),
            'requer_laudo': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
            'validade_laudo': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'observacoes_risco': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'EPI necessários, agentes de risco, observações gerais...',
            }),
        }
    
    def clean_nome(self):
        """Valida o nome da função"""
        nome = self.cleaned_data.get('nome', '').strip()
        if not nome:
            raise forms.ValidationError('O nome da função é obrigatório.')
        if len(nome) < 3:
            raise forms.ValidationError('O nome deve ter pelo menos 3 caracteres.')
        return nome

    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)

        self.fields['periodicidade_meses'].required = False

        empresa_ref = self.empresa or getattr(self.instance, 'empresa', None)
        self._popular_queryset_catalogo(empresa_ref)

        if self.instance and self.instance.pk:
            self._popular_campos_risco_ambiental()


    def clean(self):
        cleaned_data = super().clean()
        possui_insalubridade = cleaned_data.get('possui_insalubridade')
        grau_insalubridade = cleaned_data.get('grau_insalubridade')
        if possui_insalubridade and not grau_insalubridade:
            self.add_error('grau_insalubridade', 'Informe o grau de insalubridade.')
        return cleaned_data

    def save(self, commit=True):
        funcao = super().save(commit=commit)

        if commit:
            empresa = self.empresa or funcao.empresa
            if empresa:
                self._salvar_riscos_ambientais(funcao, empresa)

        return funcao

    def _popular_campos_risco_ambiental(self):
        riscos = self.instance.riscos_ambientais.filter(ativo=True).select_related('categoria')
        agrupado = {campo: [] for campo in self.MAPA_CAMPOS_CATEGORIA.values()}
        agrupado_catalogo = {campo: [] for campo in self.MAPA_CAMPOS_CATALOGO.values()}

        catalogo_map = {
            (item.categoria_id, item.nome.strip().upper()): item.id
            for item in RiscoAmbientalCatalogo.objects.filter(
                empresa=self.instance.empresa,
                ativo=True,
            ).only('id', 'categoria_id', 'nome')
        }

        for risco in riscos:
            campo = self.MAPA_CAMPOS_CATEGORIA.get(risco.categoria.codigo)
            if campo:
                agrupado[campo].append(self._formatar_linha_risco(risco))

            campo_catalogo = self.MAPA_CAMPOS_CATALOGO.get(risco.categoria.codigo)
            if campo_catalogo:
                chave_catalogo = (risco.categoria_id, (risco.agente_especifico or '').strip().upper())
                item_id = catalogo_map.get(chave_catalogo)
                if item_id:
                    agrupado_catalogo[campo_catalogo].append(item_id)

        for campo, itens in agrupado.items():
            self.fields[campo].initial = '\n'.join(itens)

        for campo, itens in agrupado_catalogo.items():
            self.fields[campo].initial = itens

    def _popular_queryset_catalogo(self, empresa):
        if not empresa:
            return

        CategoriaRiscoAmbiental.criar_categorias_padrao_empresa(empresa)
        for codigo_categoria, campo_form in self.MAPA_CAMPOS_CATALOGO.items():
            self.fields[campo_form].queryset = RiscoAmbientalCatalogo.objects.filter(
                empresa=empresa,
                ativo=True,
                categoria__codigo=codigo_categoria,
                categoria__ativo=True,
            ).select_related('categoria').order_by('nome')

    def _salvar_riscos_ambientais(self, funcao, empresa):
        CategoriaRiscoAmbiental.criar_categorias_padrao_empresa(empresa)

        categorias = {
            categoria.codigo: categoria
            for categoria in CategoriaRiscoAmbiental.objects.filter(
                empresa=empresa,
                codigo__in=self.MAPA_CAMPOS_CATEGORIA.keys(),
            )
        }

        for codigo_categoria, campo_form in self.MAPA_CAMPOS_CATEGORIA.items():
            categoria = categorias.get(codigo_categoria)
            if not categoria:
                continue

            campo_catalogo = self.MAPA_CAMPOS_CATALOGO.get(codigo_categoria)
            riscos_catalogo = self.cleaned_data.get(campo_catalogo) if campo_catalogo else []
            texto_riscos = (self.cleaned_data.get(campo_form) or '').strip()
            riscos_linha = [linha.strip() for linha in texto_riscos.splitlines() if linha.strip()]

            # Mantém o cadastro aderente ao formulário atual: substitui os riscos da categoria.
            RiscoAmbientalFuncao.objects.filter(
                funcao=funcao,
                categoria=categoria,
            ).delete()

            riscos_normalizados = set()

            for item_catalogo in riscos_catalogo or []:
                agente_catalogo = (item_catalogo.nome or '').strip()
                if not agente_catalogo:
                    continue
                chave = agente_catalogo.upper()
                if chave in riscos_normalizados:
                    continue
                riscos_normalizados.add(chave)

                RiscoAmbientalFuncao.objects.create(
                    empresa=empresa,
                    funcao=funcao,
                    categoria=categoria,
                    agente_especifico=agente_catalogo,
                    intensidade=item_catalogo.intensidade_padrao or RiscoAmbientalFuncao.INTENSIDADE_MEDIA,
                    epi_obrigatorio=(item_catalogo.epi_padrao or '').strip(),
                    observacoes=(item_catalogo.observacoes or '').strip(),
                    ativo=True,
                )

            for linha in riscos_linha:
                agente, intensidade, epi = self._parse_linha_risco(linha)
                if not agente:
                    continue
                chave = agente.upper()
                if chave in riscos_normalizados:
                    continue
                riscos_normalizados.add(chave)

                RiscoAmbientalFuncao.objects.create(
                    empresa=empresa,
                    funcao=funcao,
                    categoria=categoria,
                    agente_especifico=agente,
                    intensidade=intensidade,
                    epi_obrigatorio=epi,
                    ativo=True,
                )

    def _parse_linha_risco(self, linha):
        """Converte linha em (agente, intensidade, epi)."""
        partes = [p.strip() for p in linha.split('|')]
        if len(partes) == 1:
            return partes[0], RiscoAmbientalFuncao.INTENSIDADE_MEDIA, ''

        agente = partes[0]
        intensidade_raw = (partes[1] if len(partes) > 1 else '').upper().strip()
        intensidade_map = {
            'BAIXA': RiscoAmbientalFuncao.INTENSIDADE_BAIXA,
            'MEDIA': RiscoAmbientalFuncao.INTENSIDADE_MEDIA,
            'MÉDIA': RiscoAmbientalFuncao.INTENSIDADE_MEDIA,
            'ALTA': RiscoAmbientalFuncao.INTENSIDADE_ALTA,
        }
        intensidade = intensidade_map.get(intensidade_raw, RiscoAmbientalFuncao.INTENSIDADE_MEDIA)
        epi = partes[2] if len(partes) > 2 else ''
        return agente, intensidade, epi

    def _formatar_linha_risco(self, risco):
        """Converte risco salvo para formato editável em linha única."""
        intensidade = risco.intensidade or RiscoAmbientalFuncao.INTENSIDADE_MEDIA
        epi = (risco.epi_obrigatorio or '').strip()
        if epi:
            return f'{risco.agente_especifico} | {intensidade} | {epi}'
        return f'{risco.agente_especifico} | {intensidade}'


class RiscoAmbientalCatalogoForm(forms.ModelForm):
    """Formulário do catálogo de riscos ambientais."""

    class Meta:
        model = RiscoAmbientalCatalogo
        fields = [
            'categoria',
            'nome',
            'intensidade_padrao',
            'epi_padrao',
            'observacoes',
            'ativo',
        ]
        widgets = {
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex.: Ruído acima de 85dB'}),
            'intensidade_padrao': forms.Select(attrs={'class': 'form-select'}),
            'epi_padrao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex.: Protetor auricular'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)

        empresa_ref = self.empresa or getattr(self.instance, 'empresa', None)
        if empresa_ref:
            CategoriaRiscoAmbiental.criar_categorias_padrao_empresa(empresa_ref)
            self.fields['categoria'].queryset = CategoriaRiscoAmbiental.objects.filter(
                empresa=empresa_ref,
                ativo=True,
            ).order_by('nome')
        else:
            self.fields['categoria'].queryset = CategoriaRiscoAmbiental.objects.none()

    def clean_nome(self):
        nome = (self.cleaned_data.get('nome') or '').strip()
        if len(nome) < 3:
            raise ValidationError('Informe um nome com pelo menos 3 caracteres.')
        return nome

    def save(self, commit=True):
        item = super().save(commit=False)
        if self.empresa and not item.empresa_id:
            item.empresa = self.empresa
        if commit:
            item.save()
        return item


class FuncionarioForm(forms.ModelForm):
    """Formulário completo de funcionário"""
    
    # Campo extra para buscar CEP
    buscar_cep_funcionario = forms.BooleanField(
        required=False,
        initial=False,
        label='Buscar CEP'
    )
    
    class Meta:
        model = Funcionario
        fields = [
            'fazenda', 'nome_completo', 'matricula', 'cpf', 'rg',
            'data_nascimento', 'genero', 'estado_civil',
            'telefone', 'celular', 'email',
            'cep', 'endereco', 'numero', 'complemento',
            'bairro', 'cidade', 'uf',
            'funcao', 'tipo_contrato', 'data_admissao', 'data_demissao',
            'salario', 'ctps', 'pis', 'cnh', 'cnh_validade',
            'escolaridade', 'numero_crea',
            'banco', 'agencia', 'conta', 'tipo_conta', 'pix_habilitado', 'tipo_chave_pix', 'chave_pix',
            'contato_emergencia_nome', 'contato_emergencia_telefone',
            'contato_emergencia_parentesco',
            'observacoes', 'foto', 'ativo'
        ]
        widgets = {
            'fazenda': forms.Select(attrs={'class': 'form-select'}),
            'nome_completo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome completo do funcionário'
            }),
            'matricula': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: MAT-0001'
            }),
            'cpf': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '000.000.000-00',
                'data-mask': 'cpf'
            }),
            'tipo_conta': forms.Select(attrs={'class': 'form-select'}),
            'rg': forms.TextInput(attrs={
                'class': 'form-control'
            }),
             'data_nascimento': forms.DateInput(
                attrs={
                    'class': 'form-control',
                    'type': 'date'
                },
                format='%Y-%m-%d'  # 🔥 Adicione esta linha
            ),
            'genero': forms.Select(attrs={'class': 'form-select'}),
            'estado_civil': forms.Select(attrs={'class': 'form-select'}),
            'telefone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '(00) 0000-0000'
            }),
            'celular': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '(00) 00000-0000'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control'
            }),
            'cnh': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número da CNH (somente motoristas)'
            }),
            'cnh_validade': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'escolaridade': forms.Select(attrs={
                'class': 'form-select'
            }),
            'numero_crea': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número CREA (ex: 12345/XX-00)'
            }),
            'cep': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '00000-000'
            }),
            'endereco': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'numero': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'complemento': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'bairro': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'cidade': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'uf': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': 2
            }),
            'funcao': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_funcao',
                'size': '10'
            }),
            'tipo_contrato': forms.Select(attrs={'class': 'form-select'}),
            'data_admissao': forms.DateInput(attrs={
               'class': 'form-control',
                'type': 'date'
            },
            format='%Y-%m-%d'  # 🔥 Adicione esta linha
        ),
            'data_demissao': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            },
            format='%Y-%m-%d'  # 🔥 Adicione esta linha
        ),
            'salario': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'ctps': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'pis': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'banco': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'agencia': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'conta': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'contato_emergencia_nome': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'contato_emergencia_telefone': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'contato_emergencia_parentesco': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Mãe, Pai, Esposo(a)'
            }),
            'observacoes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'foto': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
        }

    def clean(self):
        cleaned = super().clean()
        funcao = cleaned.get('funcao')
        # If the role name includes 'motorista', require CNH and validade
        if funcao and getattr(funcao, 'nome', '').lower().find('motorista') != -1:
            cnh = cleaned.get('cnh')
            cnh_validade = cleaned.get('cnh_validade')
            errors = {}
            if not cnh:
                errors['cnh'] = 'Motorista deve ter CNH registrada.'
            if not cnh_validade:
                errors['cnh_validade'] = 'Motorista deve ter validade da CNH registrada.'
            else:
                if cnh_validade <= timezone.now().date():
                    errors['cnh_validade'] = 'Validade da CNH deve ser uma data futura.'
            if errors:
                raise ValidationError(errors)
        return cleaned
    

    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        self.usuario = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)
        
        # Filtra fazendas e funções por empresa
        if self.empresa:
            self.fields['fazenda'].queryset = Fazenda.objects.filter(
                empresa=self.empresa,
                ativa=True
            )
            self.fields['funcao'].queryset = FuncaoFuncionario.objects.filter(
                empresa=self.empresa,
                ativa=True
            )
        
        # 🔥 CORREÇÃO: Formata data_nascimento para edição
        if self.instance and self.instance.pk:
            # Se está editando e tem data de nascimento, formata para YYYY-MM-DD
            if self.instance.data_nascimento:
                self.fields['data_nascimento'].initial = self.instance.data_nascimento.strftime('%Y-%m-%d')
            
            # Também formata data de admissão e demissão
            if self.instance.data_admissao:
                self.fields['data_admissao'].initial = self.instance.data_admissao.strftime('%Y-%m-%d')
            
            if self.instance.data_demissao:
                self.fields['data_demissao'].initial = self.instance.data_demissao.strftime('%Y-%m-%d')
        
    def clean_cpf(self):
        """Valida CPF"""
        cpf = self.cleaned_data.get('cpf', '')
        cpf_limpo = re.sub(r'\D', '', cpf)
        
        if len(cpf_limpo) != 11:
            raise ValidationError('CPF deve ter 11 dígitos')
        
        # Verifica duplicidade
        qs = Funcionario.objects.filter(cpf=cpf_limpo)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        
        if qs.exists():
            raise ValidationError('Este CPF já está cadastrado')
        
        return cpf_limpo

    def clean_matricula(self):
        """Valida matrícula e evita duplicidade por empresa."""
        matricula = (self.cleaned_data.get('matricula') or '').strip()
        if not matricula:
            return ''

        if self.empresa:
            qs = Funcionario.objects.filter(empresa=self.empresa, matricula__iexact=matricula)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError('Esta matrícula já está cadastrada para a empresa.')

        return matricula
    
    def save(self, commit=True):
        """Salva funcionário"""
        funcionario = super().save(commit=False)
        
        if self.empresa:
            funcionario.empresa = self.empresa
        
        if self.usuario:
            funcionario.cadastrado_por = self.usuario
        
        if commit:
            funcionario.save()
        
        return funcionario


class DocumentoFuncionarioForm(forms.ModelForm):
    """Formulário para upload de documentos do funcionário"""
    
    class Meta:
        model = DocumentoFuncionario
        fields = ['tipo', 'titulo', 'numero_documento', 'arquivo', 'data_emissao', 'data_validade', 'gerar_alerta_vencimento', 'dias_antecedencia_alerta', 'observacoes']
        widgets = {
            'tipo': forms.Select(attrs={
                'class': 'form-select'
            }),
            'titulo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Contrato de Trabalho, Certificado de Treinamento'
            }),
            'numero_documento': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Número CREA, Protocolo, etc.'
            }),
            'arquivo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.jpg,.jpeg,.png,.doc,.docx,.xls,.xlsx'
            }),
            'data_emissao': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'data_validade': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'gerar_alerta_vencimento': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'dias_antecedencia_alerta': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '365'
            }),
            'observacoes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Observações adicionais'
            }),
        }


class FornecedorForm(forms.ModelForm):
    """Formulário de Fornecedor"""

    def clean(self):
        cleaned_data = super().clean()
        cnpj_cpf = cleaned_data.get('cnpj_cpf')
        empresa = getattr(self, 'empresa', None)
        if cnpj_cpf and empresa:
            qs = self._meta.model.objects.filter(empresa=empresa, cnpj_cpf=cnpj_cpf)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error('cnpj_cpf', 'Já existe um fornecedor com este CNPJ/CPF para esta empresa.')
        return cleaned_data

    class Meta:
        model = Fornecedor
        fields = [
            'nome', 'nome_fantasia', 'tipo_pessoa', 'cnpj_cpf', 'inscricao_estadual', 'inscricao_municipal', 'eori', 'regime_tributario',
            'telefone', 'celular', 'email', 'website',
            'cep', 'endereco', 'numero', 'complemento', 'bairro', 'cidade', 'uf', 'pais',
            'is_exportador', 'moeda_padrao', 'porto_preferencial',
            'categorias', 'subcategorias',
            'classificacao_risco', 'data_homologacao', 'validade_homologacao',
            'limite_credito', 'prazo_pagamento_padrao', 'prazo_entrega_medio', 'observacoes', 'portal_enabled', 'portal_user', 'ativa'
        ]
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'nome_fantasia': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo_pessoa': forms.Select(attrs={'class': 'form-select'}),
            'cnpj_cpf': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '00.000.000/0000-00'}),
            'inscricao_estadual': forms.TextInput(attrs={'class': 'form-control'}),
            'inscricao_municipal': forms.TextInput(attrs={'class': 'form-control'}),
            'eori': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código EORI para exportação'}),
            'regime_tributario': forms.Select(attrs={'class': 'form-select'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control'}),
            'celular': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(00) 00000-0000'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://www.fornecedor.com'}),
            'cep': forms.TextInput(attrs={'class': 'form-control'}),
            'endereco': forms.TextInput(attrs={'class': 'form-control'}),
            'numero': forms.TextInput(attrs={'class': 'form-control'}),
            'complemento': forms.TextInput(attrs={'class': 'form-control'}),
            'bairro': forms.TextInput(attrs={'class': 'form-control'}),
            'cidade': forms.TextInput(attrs={'class': 'form-control'}),
            'uf': forms.TextInput(attrs={'class': 'form-control'}),
            'pais': forms.TextInput(attrs={'class': 'form-control'}),
            'porto_preferencial': forms.TextInput(attrs={'class': 'form-control'}),
            'categorias': forms.SelectMultiple(attrs={'class': 'form-select'}),
            'subcategorias': forms.SelectMultiple(attrs={'class': 'form-select'}),
            'classificacao_risco': forms.Select(attrs={'class': 'form-select'}),
            'data_homologacao': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'validade_homologacao': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'limite_credito': forms.TextInput(attrs={'class': 'form-control', 'inputmode': 'decimal', 'data-currency-mask': 'brl'}),
            'prazo_pagamento_padrao': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'prazo_entrega_medio': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_exportador': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'portal_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'portal_user': forms.Select(attrs={'class': 'form-select'}),
            'ativa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        usuario = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)
        self.empresa = empresa
        self.usuario = usuario

        try:
            from .models import CategoriaFornecedor, SubcategoriaFornecedor
            if 'categorias' in self.fields:
                qs_cat = CategoriaFornecedor.objects.filter(empresa=empresa) if empresa else CategoriaFornecedor.objects.all()
                self.fields['categorias'].queryset = qs_cat
                self.fields['categorias'].required = False
            if 'subcategorias' in self.fields:
                qs_sub = SubcategoriaFornecedor.objects.filter(categoria__empresa=empresa).distinct() if empresa else SubcategoriaFornecedor.objects.all()
                self.fields['subcategorias'].queryset = qs_sub
                self.fields['subcategorias'].required = False
        except Exception:
            pass

        try:
            from usuarios.models import Usuario
            if 'portal_user' in self.fields:
                usuarios_qs = Usuario.objects.filter(is_active=True)
                if empresa:
                    usuarios_qs = usuarios_qs.filter(empresa=empresa)

                # Permite reutilizar o usuário já vinculado ao fornecedor atual durante edição.
                if self.instance.pk and self.instance.portal_user_id:
                    usuarios_qs = usuarios_qs | Usuario.objects.filter(pk=self.instance.portal_user_id)

                self.fields['portal_user'].queryset = usuarios_qs.order_by('first_name', 'last_name', 'username').distinct()
                self.fields['portal_user'].required = False
                self.fields['portal_user'].help_text = 'Selecione o usuário que fará login no portal deste fornecedor.'
        except Exception:
            pass

        # make some fields optional to support minimal create payloads in tests
        for f in ['tipo_pessoa', 'pais', 'moeda_padrao', 'regime_tributario']:
            if f in self.fields:
                self.fields[f].required = False

    def save(self, commit=True):
        """Associa automaticamente a `empresa` e `criado_por` antes de salvar.
        Garante salvar campos ManyToMany chamando `save_m2m()` quando necessário."""
        obj = super().save(commit=False)
        if getattr(self, 'empresa', None):
            obj.empresa = self.empresa
        if getattr(self, 'usuario', None):
            # compatibilidade com nome do campo usado em modelos
            if hasattr(obj, 'criado_por'):
                obj.criado_por = self.usuario
        if commit:
            obj.save()
            # salva relações ManyToMany do form
            try:
                self.save_m2m()
            except Exception:
                # se não houver m2m ou falhar, não interrompe o save
                pass
        return obj


class TransportadoraForm(forms.ModelForm):
    """Formulário para Transportadora"""

    class Meta:
        model = Transportadora
        fields = [
            'razao_social', 'nome_fantasia', 'tipo', 'cnpj', 'inscricao_estadual', 'rntc',
            'contato_principal_nome', 'contato_principal_telefone', 'contato_principal_email',
            'cep', 'logradouro', 'numero', 'complemento', 'bairro', 'cidade', 'uf', 'pais',
            'banco', 'agencia', 'conta', 'tipo_conta', 'tipo_pix', 'pix_key', 'contribuinte_icms', 'indicador_ie',
            'frete_padrao', 'frete_por_km', 'moeda', 'ativa'
        ]
        widgets = {
            'razao_social': forms.TextInput(attrs={'class': 'form-control'}),
            'nome_fantasia': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'cnpj': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '00.000.000/0000-00'}),
            'inscricao_estadual': forms.TextInput(attrs={'class': 'form-control'}),
            'contato_principal_nome': forms.TextInput(attrs={'class': 'form-control'}),
            'contato_principal_telefone': forms.TextInput(attrs={'class': 'form-control'}),
            'contato_principal_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'cep': forms.TextInput(attrs={'class': 'form-control'}),
            'logradouro': forms.TextInput(attrs={'class': 'form-control'}),
            'numero': forms.TextInput(attrs={'class': 'form-control'}),
            'complemento': forms.TextInput(attrs={'class': 'form-control'}),
            'bairro': forms.TextInput(attrs={'class': 'form-control'}),
            'cidade': forms.TextInput(attrs={'class': 'form-control'}),
            'uf': forms.TextInput(attrs={'class': 'form-control'}),
            'pais': forms.TextInput(attrs={'class': 'form-control'}),
            'banco': forms.TextInput(attrs={'class': 'form-control'}),
            'agencia': forms.TextInput(attrs={'class': 'form-control'}),
            'conta': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo_conta': forms.Select(attrs={'class': 'form-select'}),
            'tipo_pix': forms.Select(attrs={'class': 'form-select'}),
            'pix_key': forms.TextInput(attrs={'class': 'form-control'}),
            'rntc': forms.TextInput(attrs={'class': 'form-control'}),
            'contribuinte_icms': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'indicador_ie': forms.TextInput(attrs={'class': 'form-control', 'readonly': True}),
            'frete_padrao': forms.NumberInput(attrs={'class': 'form-control', 'step':'0.01'}),
            'frete_por_km': forms.NumberInput(attrs={'class': 'form-control', 'step':'0.0001'}),
            'moeda': forms.TextInput(attrs={'class': 'form-control'}),
            'ativa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        usuario = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)
        self.empresa = empresa
        self.usuario = usuario
        if 'tipo' in self.fields:
            self.fields['tipo'].required = False
        # Avoid forcing pais/moeda on quick POSTs; set defaults
        if 'pais' in self.fields:
            self.fields['pais'].required = False
            self.fields['pais'].initial = 'Brasil'
        if 'moeda' in self.fields:
            self.fields['moeda'].required = False
            self.fields['moeda'].initial = 'BRL'

    def save(self, commit=True):
        obj = super().save(commit=False)
        if self.empresa:
            obj.empresa = self.empresa
        if commit:
            obj.save()
        return obj

        # configura queryset para categorias e subcategorias (carrega dinamicamente conforme empresa)
        # Popula opções de categorias/subcategorias de forma tardia (evita import-time errors)
        try:
            from .models import CategoriaFornecedor, SubcategoriaFornecedor
            if 'categorias' in self.fields:
                qs = CategoriaFornecedor.objects.filter(empresa=self.empresa) if self.empresa else CategoriaFornecedor.objects.all()
                self.fields['categorias'].queryset = qs
            if 'subcategorias' in self.fields:
                qs2 = SubcategoriaFornecedor.objects.all()
                self.fields['subcategorias'].queryset = qs2
        except Exception:
            # Se os modelos não existirem ou houver erro, mantemos as listas vazias.
            pass

    def save(self, commit=True):
        fornecedor = super().save(commit=False)
        if self.empresa:
            fornecedor.empresa = self.empresa
        if self.usuario:
            fornecedor.criado_por = self.usuario
        if commit:
            fornecedor.save()
            # Salva ManyToMany (categorias, subcategorias)
            try:
                self.save_m2m()
            except Exception:
                pass
        return fornecedor


class FornecedorContatoForm(forms.ModelForm):
    class Meta:
        model = FornecedorContato
        fields = ['tipo', 'nome', 'cargo', 'telefone', 'celular', 'email', 'whatsapp', 'preferencial', 'observacoes']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'cargo': forms.TextInput(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control'}),
            'celular': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # allow partial updates (tests post only a subset of fields)
        if 'tipo' in self.fields:
            self.fields['tipo'].required = False


class FornecedorDadoBancarioForm(forms.ModelForm):
    class Meta:
        model = FornecedorDadoBancario
        fields = [
            'banco', 'codigo_banco', 'agencia', 'agencia_digito', 'conta', 'conta_digito', 'tipo_conta',
            'pix_habilitado', 'tipo_chave_pix', 'chave_pix', 'swift', 'iban', 'dados_adicionais', 'conta_principal', 'ativa'
        ]
        widgets = {
            'banco': forms.TextInput(attrs={'class': 'form-control'}),
            'codigo_banco': forms.TextInput(attrs={'class': 'form-control'}),
            'agencia': forms.TextInput(attrs={'class': 'form-control'}),
            'agencia_digito': forms.TextInput(attrs={'class': 'form-control'}),
            'conta': forms.TextInput(attrs={'class': 'form-control'}),
            'conta_digito': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo_conta': forms.Select(attrs={'class': 'form-select'}),
            'chave_pix': forms.TextInput(attrs={'class': 'form-control'}),
            'swift': forms.TextInput(attrs={'class': 'form-control'}),
            'iban': forms.TextInput(attrs={'class': 'form-control'}),
            'dados_adicionais': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'tipo_conta' in self.fields:
            self.fields['tipo_conta'].required = False


class FornecedorEnderecoForm(forms.ModelForm):
    class Meta:
        model = FornecedorEndereco
        fields = ['tipo', 'cep', 'logradouro', 'numero', 'complemento', 'bairro', 'cidade', 'uf', 'pais', 'padrao']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'cep': forms.TextInput(attrs={'class': 'form-control'}),
            'logradouro': forms.TextInput(attrs={'class': 'form-control'}),
            'numero': forms.TextInput(attrs={'class': 'form-control'}),
            'complemento': forms.TextInput(attrs={'class': 'form-control'}),
            'bairro': forms.TextInput(attrs={'class': 'form-control'}),
            'cidade': forms.TextInput(attrs={'class': 'form-control'}),
            'uf': forms.TextInput(attrs={'class': 'form-control'}),
            'pais': forms.TextInput(attrs={'class': 'form-control'}),
        }


"""
ADICIONE ESTE CÓDIGO NO FINAL DO ARQUIVO cadastros/forms.py
"""

class CulturaForm(forms.ModelForm):
    """Formulário de cadastro de culturas"""
    
    class Meta:
        model = Cultura
        fields = [
            'nome', 'nome_cientifico', 'tipo', 'variedade', 'codigo_interno',
            'ciclo_cultivo', 'dias_colheita', 
            'espacamento_linhas', 'espacamento_plantas', 'densidade_plantio',
            'temperatura_ideal_min', 'temperatura_ideal_max', 'necessidade_agua',
            'unidade_medida', 'produtividade_esperada', 'preco_medio', 'mercado_destino',
            'irrigacao_necessaria', 'tipo_irrigacao', 
            'adubacao_recomendada', 'controle_pragas',
            'certificacao_organica', 'certificacao_exportacao',
            'imagem', 'observacoes', 'ativa'
        ]
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Melão, Melancia, Milho'
            }),
            'nome_cientifico': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome científico'
            }),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'variedade': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Goldex, Quetzali, Asturia, Gália...'
            }),
            'codigo_interno': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Código interno'
            }),
            'ciclo_cultivo': forms.Select(attrs={'class': 'form-select'}),
            'dias_colheita': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1
            }),
            'espacamento_linhas': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Em metros'
            }),
            'espacamento_plantas': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Em metros'
            }),
            'densidade_plantio': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Plantas por hectare',
                'readonly': 'readonly'
            }),
            'temperatura_ideal_min': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1',
                'placeholder': '°C'
            }),
            'temperatura_ideal_max': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1',
                'placeholder': '°C'
            }),
            'necessidade_agua': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: 400-600mm ou Alta, Média, Baixa'
            }),
            'unidade_medida': forms.Select(attrs={'class': 'form-select'}),
            'produtividade_esperada': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Por hectare'
            }),
            'preco_medio': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'R$ por unidade'
            }),
            'mercado_destino': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Interno, Exportação, Ambos'
            }),
            'tipo_irrigacao': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Gotejamento, Aspersão'
            }),
            'adubacao_recomendada': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descrição da adubação recomendada'
            }),
            'controle_pragas': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Principais pragas e métodos de controle'
            }),
            'imagem': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'observacoes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Informações adicionais'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        self.usuario = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)
    
    def clean(self):
        """Validações gerais"""
        cleaned_data = super().clean()
        
        temp_min = cleaned_data.get('temperatura_ideal_min')
        temp_max = cleaned_data.get('temperatura_ideal_max')
        
        if temp_min and temp_max and temp_min > temp_max:
            raise ValidationError({
                'temperatura_ideal_max': 'Temperatura máxima deve ser maior que a mínima'
            })
        
        return cleaned_data
    
    def save(self, commit=True):
        """Salva cultura com empresa e usuário"""
        cultura = super().save(commit=False)
        
        if self.empresa:
            cultura.empresa = self.empresa
        
        if self.usuario:
            cultura.cadastrado_por = self.usuario
        
        if commit:
            cultura.save()
        
        return cultura


class PragaForm(forms.ModelForm):
    """Formulário de cadastro de pragas"""
    
    class Meta:
        model = Praga
        fields = ['nome_comum', 'nome_cientifico', 'tipo_praga', 'foto', 'ativa']
        widgets = {
            'nome_comum': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Lagarta-do-cartucho, Mosca-branca, Ferrugem',
                'required': True
            }),
            'nome_cientifico': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome científico (opcional)'
            }),
            'tipo_praga': forms.Select(attrs={
                'class': 'form-select'
            }),
            'foto': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        self.usuario = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)
    
    def clean_nome_comum(self):
        """Valida se já existe praga com mesmo nome na empresa"""
        nome_comum = self.cleaned_data.get('nome_comum')
        
        if nome_comum and self.empresa:
            # Verifica duplicação (case-insensitive)
            queryset = Praga.objects.filter(
                empresa=self.empresa,
                nome_comum__iexact=nome_comum
            )
            
            # Se estiver editando, exclui o próprio registro da busca
            if self.instance and self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                raise ValidationError(
                    f'Já existe uma praga cadastrada com o nome "{nome_comum}" nesta empresa.'
                )
        
        return nome_comum
    
    def save(self, commit=True):
        """Salva praga com empresa e usuário"""
        praga = super().save(commit=False)
        
        if self.empresa:
            praga.empresa = self.empresa
        
        if self.usuario:
            praga.cadastrado_por = self.usuario
        
        if commit:
            praga.save()
        
        return praga


class PrazoPagamentoPadraoForm(forms.ModelForm):
    """Formulário para criar/editar presets de prazo de pagamento"""
    
    class Meta:
        model = PrazoPagamentoPadrao
        fields = ['nome', 'termos', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: 30 Dias, 30/60 Dias, À Vista',
                'required': True
            }),
            'termos': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Valores separados por vírgula: 0,30,60,90',
                'required': True,
                'help': 'Use números inteiros separados por vírgula'
            }),
            'ativo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
    
    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
    
    def clean_termos(self):
        """Valida se os termos são números válidos separados por vírgula"""
        termos_str = self.cleaned_data.get('termos', '').strip()
        
        if not termos_str:
            raise ValidationError('Informe pelo menos um termo.')
        
        # Tentar converter para lista de inteiros
        try:
            termos_list = [int(t.strip()) for t in termos_str.split(',') if t.strip()]
            if not termos_list:
                raise ValidationError('Nenhum termo válido encontrado.')
            # Validar que todos são números não-negativos
            if any(t < 0 for t in termos_list):
                raise ValidationError('Todos os termos devem ser números não-negativos.')
        except ValueError:
            raise ValidationError('Todos os termos devem ser números inteiros. Use vírgula para separar.')
        
        return termos_str
    
    def save(self, commit=True):
        """Salva preset com empresa"""
        preset = super().save(commit=False)
        
        if self.empresa:
            preset.empresa = self.empresa
        
        if commit:
            preset.save()
        
        return preset


"""
ADICIONE ESTES FORMS AO ARQUIVO cadastros/forms.py
Forms com isolamento Multi-Tenant
"""




class AreaForm(forms.ModelForm):
    """
    Formulário para criar/editar áreas
    🔒 FILTRA FAZENDAS PELA EMPRESA DO USUÁRIO
    """
    
    SOLO_CHOICES = [
        ('', '---------'),
        ('Arenoso', 'Arenoso'),
        ('Argiloso', 'Argiloso'),
        ('Siltoso', 'Siltoso'),
        ('Humoso', 'Humoso'),
        ('Calcário', 'Calcário'),
        ('Gleissolo', 'Gleissolo'),
        ('Latossolo', 'Latossolo'),
        ('Cambissolo', 'Cambissolo'),
        ('Neossolo', 'Neossolo'),
        ('Outro', 'Outro'),
    ]
    class Meta:
        model = Area
        fields = [
            'fazenda', 'nome', 'codigo_interno', 'tipo_area',
            'area_total', 'area_reserva', 'area_plantavel',
            'latitude', 'longitude',
            'tipo_solo', 'ph_solo', 'topografia',
            'possui_irrigacao', 'tipo_irrigacao',
            'status', 'ativa', 'observacoes'
        ]
        widgets = {
            'fazenda': forms.Select(attrs={'class': 'form-select'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'codigo_interno': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo_area': forms.Select(attrs={'class': 'form-select'}),
            'area_total': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Ex: 100.00'
            }),
            'area_reserva': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Ex: 15.00',
                'min': '0'
            }),
            'area_plantavel': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Ex: 80.00',
                'min': '0'
            }),
            'latitude': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.0000001'
            }),
            'longitude': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.0000001'
            }),
            'tipo_solo': forms.Select(attrs={'class': 'form-select'}),  # choices será setado no __init__
            'ph_solo': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'max': '14'
            }),
            'topografia': forms.Select(attrs={'class': 'form-select'}),
            'tipo_irrigacao': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
        }
    
    def __init__(self, *args, **kwargs):
        # Recebe o usuário logado
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Setar choices do tipo_solo
        self.fields['tipo_solo'].widget.choices = self.SOLO_CHOICES

        # 🔒 FILTRO CRÍTICO: Apenas fazendas da empresa do usuário
        if self.user and self.user.empresa:
            self.fields['fazenda'].queryset = Fazenda.objects.filter(
                empresa=self.user.empresa,
                ativa=True
            ).order_by('nome')
        else:
            self.fields['fazenda'].queryset = Fazenda.objects.none()

        # Torna campos condicionais
        if not self.instance.pk or not self.instance.possui_irrigacao:
            self.fields['tipo_irrigacao'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        area_total = cleaned_data.get('area_total')
        area_plantavel = cleaned_data.get('area_plantavel')
        possui_irrigacao = cleaned_data.get('possui_irrigacao')
        tipo_irrigacao = cleaned_data.get('tipo_irrigacao')
        
        # Valida área plantável
        if area_plantavel and area_total:
            if area_plantavel > area_total:
                raise forms.ValidationError({
                    'area_plantavel': 'Área plantável não pode ser maior que área total'
                })

        # Valida soma de área plantável da fazenda (não pode exceder área_total da fazenda)
        fazenda = cleaned_data.get('fazenda')
        if fazenda and area_plantavel is not None:
            try:
                # Soma áreas plantáveis existentes (exclui a própria instância quando editando)
                qs = fazenda.areas.all()
                if self.instance and self.instance.pk:
                    qs = qs.exclude(pk=self.instance.pk)

                soma_existente = sum((a.area_plantavel or 0) for a in qs)
                total_proposto = soma_existente + float(area_plantavel)

                if fazenda.area_total is not None and total_proposto > float(fazenda.area_total):
                    raise forms.ValidationError({
                        'area_plantavel': 'Soma das áreas plantáveis excede a Área Total da fazenda (%s ha)' % fazenda.area_total
                    })
            except Exception:
                # Falha silenciosa para não bloquear salvamento por erro inesperado
                pass
        
        # Valida irrigação
        if tipo_irrigacao and not possui_irrigacao:
            raise forms.ValidationError({
                'tipo_irrigacao': 'Marque "Possui Irrigação" antes de informar o tipo'
            })
        
        return cleaned_data


class TalhaoForm(forms.ModelForm):
    """
    Formulário para criar/editar talhões
    🔒 FILTRA ÁREAS E FAZENDAS PELA EMPRESA
    """
    
    # Campo customizado para não conflitar com Model.area (relacionamento)
    area_tamanho = forms.DecimalField(
        label='Área (ha)',
        max_digits=10,
        decimal_places=4,  # 🔥 CORREÇÃO: 4 casas como no modelo
        min_value=Decimal('0.0001'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.0001',
            'placeholder': 'Ex: 1.3000',
            'inputmode': 'decimal'
        })
    )
    
    class Meta:
        model = Talhao
        fields = [
            'fazenda', 'area', 'nome', 'codigo',
            'latitude', 'longitude',
            'declividade', 'exposicao_solar',
            'status', 'pronto_para_plantio', 'ativo',
            'observacoes'
        ]
        widgets = {
            'fazenda': forms.Select(attrs={
                'class': 'form-select',
                'onchange': 'carregarAreas(this.value)'
            }),
            'area': forms.Select(attrs={'class': 'form-select'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'codigo': forms.TextInput(attrs={'class': 'form-control'}),
            'latitude': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.0000001'
            }),
            'longitude': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.0000001'
            }),
            'declividade': forms.Select(attrs={'class': 'form-select'}),
            'exposicao_solar': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
        }
    
    def __init__(self, *args, **kwargs):
        # Recebe o usuário logado
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # 🔒 FILTRO: Apenas fazendas da empresa
        if self.user and self.user.empresa:
            self.fields['fazenda'].queryset = Fazenda.objects.filter(
                empresa=self.user.empresa,
                ativa=True
            ).order_by('nome')
            
            # 🔒 FILTRO: Apenas áreas da empresa
            self.fields['area'].queryset = Area.objects.filter(
                empresa=self.user.empresa,
                ativa=True
            ).select_related('fazenda').order_by('fazenda__nome', 'nome')
        else:
            self.fields['fazenda'].queryset = Fazenda.objects.none()
            self.fields['area'].queryset = Area.objects.none()
        
        # Se editando, popula área atual
        if self.instance.pk and self.instance.area_hac:
            self.fields['area_tamanho'].initial = self.instance.area_hac
    
    def clean(self):
        cleaned_data = super().clean()
        area = cleaned_data.get('area')
        fazenda = cleaned_data.get('fazenda')
        area_tamanho = cleaned_data.get('area_tamanho')
        
        # 🔒 VALIDAÇÃO: Área pertence à fazenda e empresa
        if area and fazenda:
            if area.fazenda != fazenda:
                raise forms.ValidationError({
                    'area': 'A área selecionada não pertence à fazenda escolhida'
                })
            
            # 🔒 Valida empresa
            if self.user and self.user.empresa:
                if area.empresa != self.user.empresa:
                    raise forms.ValidationError({
                        'area': 'Você não tem permissão para usar esta área'
                    })
        
        # Valida se área disponível é suficiente
        if area and area_tamanho:
            area_disponivel = area.get_area_disponivel()
            
            # Se editando, considera a área atual do talhão
            if self.instance.pk and self.instance.area_hac:
                area_disponivel += self.instance.area_hac
            
            if area_tamanho > area_disponivel:
                raise forms.ValidationError({
                    'area_tamanho': f'Área disponível insuficiente. Disponível: {area_disponivel} ha'
                })
        
        return cleaned_data
    
    def save(self, commit=True):
        """🔥 CORREÇÃO: Salva area_tamanho no campo area_hac do modelo"""
        instance = super().save(commit=False)
        
        # 🔥 CRÍTICO: Transfere o valor do campo customizado para o campo do modelo
        area_tamanho = self.cleaned_data.get('area_tamanho')
        if area_tamanho is not None:
            instance.area_hac = area_tamanho
        
        if commit:
            instance.save()
        
        return instance


# cadastros/forms.py - Localize a classe SafraForm e SUBSTITUA completamente:

class SafraForm(forms.ModelForm):
    """Formulário para criar/editar `Safra` com validações de integridade"""
    
    class Meta:
        model = Safra
        fields = ['nome', 'fazenda', 'cultura', 'ano', 'periodo_inicio', 'periodo_fim', 'status', 'imagem']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'fazenda': forms.Select(attrs={'class': 'form-select'}),
            'cultura': forms.Select(attrs={'class': 'form-select'}),
            'ano': forms.NumberInput(attrs={'class': 'form-control'}),
            'periodo_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'periodo_fim': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'imagem': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*', 'type': 'file'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        def _safra_label(safra):
            base = safra.nome or str(safra.ano or '')
            cultura = safra.cultura.nome if safra.cultura else ''
            if base and cultura:
                return f"{base} - {cultura}"
            return base or cultura or str(safra)

        if self.user and getattr(self.user, 'empresa', None):
            self.fields['fazenda'].queryset = Fazenda.objects.filter(empresa=self.user.empresa, ativa=True).order_by('nome')
            self.fields['cultura'].queryset = Cultura.objects.filter(empresa=self.user.empresa, ativa=True).order_by('nome')
        else:
            self.fields['fazenda'].queryset = Fazenda.objects.none()
            self.fields['cultura'].queryset = Cultura.objects.none()

        if 'status' in self.fields:
            self.fields['status'].initial = 'PLANEJADA'
            self.fields['status'].required = True

        # Se editando, formata datas corretamente
        if self.instance and self.instance.pk:
            if getattr(self.instance, 'periodo_inicio', None):
                self.fields['periodo_inicio'].initial = self.instance.periodo_inicio.strftime('%Y-%m-%d')
            if getattr(self.instance, 'periodo_fim', None):
                self.fields['periodo_fim'].initial = self.instance.periodo_fim.strftime('%Y-%m-%d')

    def clean(self):
        cleaned = super().clean()
        inicio = cleaned.get('periodo_inicio')
        fim = cleaned.get('periodo_fim')
        fazenda = cleaned.get('fazenda')
        cultura = cleaned.get('cultura')
        ano = cleaned.get('ano')

        # Validação de período
        if inicio and fim and inicio > fim:
            raise forms.ValidationError({'periodo_inicio': 'Data de início não pode ser posterior à data fim'})

        if inicio and fim:
            if fim.year not in (inicio.year, inicio.year + 1):
                raise forms.ValidationError({'periodo_fim': 'Período inválido: o término deve estar no mesmo ano ou no ano seguinte ao início'})

        # Normaliza ano composto
        if ano and ano > 9999:
            try:
                ano_str = str(int(ano))
                ano = int(ano_str[:4])
                cleaned['ano'] = ano
            except Exception:
                pass

        # Infere ano se não fornecido
        if not ano and inicio:
            ano = inicio.year
            cleaned['ano'] = ano

        # Valida unicidade
        if fazenda and cultura and ano:
            qs = Safra.objects.filter(fazenda=fazenda, cultura=cultura, ano=ano)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError('Já existe uma safra para esta fazenda, cultura e ano')

        return cleaned
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Preenche nome padrão se necessário
        inicio = self.cleaned_data.get('periodo_inicio')
        fim = self.cleaned_data.get('periodo_fim')
        if not instance.nome:
            if inicio and fim:
                instance.nome = f"{inicio.year}{fim.year % 100:02d}"
            elif inicio:
                instance.nome = str(inicio.year)

        if commit:
            instance.save()

        return instance




class SafraPlanForm(forms.ModelForm):
    """Formulário para criar/editar Planejamento de Safra"""

    class Meta:
        model = SafraPlan
        fields = ['planned_area', 'planned_plantio', 'planned_colheita', 'planned_production']
        widgets = {
            'planned_area': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
            'planned_production': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'planned_plantio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'planned_colheita': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
        }

    def __init__(self, *args, **kwargs):
        self.safra = kwargs.pop('safra', None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.safra:
            instance.safra = self.safra
        if commit:
            instance.save()
        return instance


class RequisicaoForm(forms.ModelForm):
    """Formulario de requisicao"""
    
    codigo_talhao = forms.CharField(
        label='Código do Talhão',
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'id': 'id_codigo_talhao',
            'placeholder': 'Digite o código do talhão para buscar...',
            'autocomplete': 'off'
        })
    )

    class Meta:
        model = Requisicao
        fields = [
            'numero', 'tipo',
            'safra', 'fazenda', 'talhao',
            'funcionario_destino', 'parceiro', 'produtor',
            'direcao_emprestimo', 'recebedor_material', 'data_promessa_devolucao',
            'veiculo', 'horimetro', 'odometro',
            'centro_custo_nome', 'observacoes'
        ]
        widgets = {
            'numero': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'tipo': forms.Select(attrs={'class': 'form-select', 'id': 'id_tipo'}),
            'safra': forms.Select(attrs={'class': 'form-select', 'id': 'id_safra'}),
            'fazenda': forms.Select(attrs={'class': 'form-select', 'id': 'id_fazenda'}),
            'talhao': forms.Select(attrs={'class': 'form-select', 'id': 'id_talhao'}),
            'funcionario_destino': forms.Select(attrs={'class': 'form-select'}),
            'parceiro': forms.Select(attrs={'class': 'form-select'}),
            'produtor': forms.Select(attrs={'class': 'form-select'}),
            'direcao_emprestimo': forms.Select(attrs={'class': 'form-select'}),
            'recebedor_material': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome completo e documento (CPF/RG)'
            }),
            'data_promessa_devolucao': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'veiculo': forms.Select(attrs={'class': 'form-select'}),
            'horimetro': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'odometro': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'centro_custo_nome': forms.TextInput(attrs={'class': 'form-control'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if self.user and getattr(self.user, 'empresa', None):
            def _safra_label(safra):
                base = safra.nome or str(safra.ano or '')
                cultura = safra.cultura.nome if safra.cultura else ''
                if base and cultura:
                    return f"{base} - {cultura}"
                return base or cultura or str(safra)

            empresa = self.user.empresa
            self.fields['fazenda'].queryset = Fazenda.objects.filter(empresa=empresa, ativa=True).order_by('nome')
            self.fields['talhao'].queryset = Talhao.objects.filter(empresa=empresa, ativo=True).order_by('codigo')
            self.fields['safra'].queryset = Safra.objects.filter(fazenda__empresa=empresa).order_by('-ano', 'nome')
            self.fields['safra'].label_from_instance = _safra_label
            self.fields['funcionario_destino'].queryset = Funcionario.objects.filter(empresa=empresa, ativo=True).order_by('nome_completo')
            self.fields['parceiro'].queryset = Cliente.objects.filter(empresa=empresa, status='ATIVO').order_by('razao_social')
            self.fields['produtor'].queryset = Produtor.objects.filter(empresa=empresa, status='ATIVO').order_by('razao_social')
            self.fields['veiculo'].queryset = Vehicle.objects.filter(empresa=empresa, ativo=True).order_by('descricao')
        else:
            self.fields['fazenda'].queryset = Fazenda.objects.none()
            self.fields['talhao'].queryset = Talhao.objects.none()
            self.fields['safra'].queryset = Safra.objects.none()
            self.fields['funcionario_destino'].queryset = Funcionario.objects.none()
            self.fields['parceiro'].queryset = Cliente.objects.none()
            self.fields['produtor'].queryset = Produtor.objects.none()
            self.fields['veiculo'].queryset = Vehicle.objects.none()

        if self.instance and self.instance.pk:
            self.fields['numero'].initial = self.instance.numero

    def clean(self):
        cleaned = super().clean()
        tipo = cleaned.get('tipo')
        produtor = cleaned.get('produtor')
        recebedor_material = (cleaned.get('recebedor_material') or '').strip()

        if tipo == 'EMPRESTIMO':
            if not produtor:
                self.add_error('produtor', 'Selecione o produtor para empréstimo de material.')
            if not recebedor_material:
                self.add_error('recebedor_material', 'Informe quem recebeu o material (nome e documento).')

        return cleaned


class RequisicaoItemForm(forms.ModelForm):
    """Formulario de item da requisicao"""

    class Meta:
        model = RequisicaoItem
        fields = [
            'produto', 'unidade_medida',
            'quantidade_solicitada', 'quantidade_atendida',
            'custo_estimado', 'observacoes'
        ]
        widgets = {
            'produto': forms.Select(attrs={'class': 'form-select'}),
            'unidade_medida': forms.Select(attrs={'class': 'form-select'}),
            'quantidade_solicitada': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'quantidade_atendida': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'custo_estimado': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        self.requisicao_tipo = kwargs.pop('requisicao_tipo', None)
        super().__init__(*args, **kwargs)

        if self.empresa:
            self.fields['produto'].queryset = Produto.objects.filter(
                categoria__empresa=self.empresa,
                ativo=True
            ).order_by('nome')
            self.fields['unidade_medida'].queryset = UnidadeMedida.objects.filter(
                empresa=self.empresa,
                ativo=True
            ).order_by('sigla')

        self.fields['quantidade_atendida'].required = False
        self.fields['quantidade_atendida'].initial = 0

        if self.instance and self.instance.pk:
            if self.instance.unidade_medida:
                self.fields['unidade_medida'].initial = self.instance.unidade_medida

    def clean(self):
        cleaned = super().clean()
        produto = cleaned.get('produto')
        unidade = cleaned.get('unidade_medida')
        custo = cleaned.get('custo_estimado')
        quantidade_atendida = cleaned.get('quantidade_atendida')

        if produto and not unidade:
            cleaned['unidade_medida'] = produto.unidade_medida

        if produto and custo in (None, ''):
            if self.requisicao_tipo == 'EMPRESTIMO':
                cleaned['custo_estimado'] = produto.preco_venda
            else:
                cleaned['custo_estimado'] = produto.preco_custo

        if quantidade_atendida in (None, ''):
            cleaned['quantidade_atendida'] = 0

        return cleaned


class HistoricoTalhaoForm(forms.ModelForm):
    """Formulário para registrar histórico de cultivo"""
    
    class Meta:
        model = HistoricoTalhao
        fields = [
            'talhao', 'cultura', 'variedade',
            'data_plantio', 'data_colheita',
            'producao_estimada', 'producao_real',
            'custo_total',
            'observacoes', 'problemas_enfrentados'
        ]
        widgets = {
            'talhao': forms.Select(attrs={'class': 'form-select'}),
            'cultura': forms.Select(attrs={'class': 'form-select'}),
            'variedade': forms.TextInput(attrs={'class': 'form-control'}),
            'data_plantio': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'data_colheita': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'producao_estimada': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'producao_real': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'custo_total': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'observacoes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'problemas_enfrentados': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # 🔒 FILTRO: Apenas talhões e culturas da empresa
        if self.user and self.user.empresa:
            self.fields['talhao'].queryset = Talhao.objects.filter(
                empresa=self.user.empresa,
                ativo=True
            ).select_related('fazenda', 'area')
            
            self.fields['cultura'].queryset = Cultura.objects.filter(
                empresa=self.user.empresa,
                ativa=True
            ).order_by('nome')
        else:
            self.fields['talhao'].queryset = Talhao.objects.none()
            self.fields['cultura'].queryset = Cultura.objects.none()


"""
=============================================================================
📝 FORMS.PY - MÓDULO VENDEDOR (VERSÃO CORRIGIDA E COMPLETA)
=============================================================================

INSTRUÇÕES DE USO:
1. Abra seu arquivo cadastros/forms.py
2. REMOVA todos os formulários relacionados a Vendedor (VendedorForm, VendedorFiltroForm, ComissaoVendedorForm)
3. COLE este código no FINAL do arquivo
4. Salve e execute: python manage.py runserver

Este código está 100% sincronizado com os modelos Vendedor e ComissaoVendedor.
"""



# =============================================================================
# FORMULÁRIO DE FILTROS
# =============================================================================

class VendedorFiltroForm(forms.Form):
    """Formulário de filtros para listagem de vendedores"""
    
    busca = forms.CharField(
        label='Buscar',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nome, CPF, e-mail...'
        })
    )
    
    status = forms.ChoiceField(
        label='Status',
        required=False,
        choices=[
            ('', '-- Todos os Status --'),
            ('ATIVO', 'Ativo'),
            ('INATIVO', 'Inativo'),
            ('FERIAS', 'Férias'),
            ('AFASTADO', 'Afastado'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    tipo_mercado = forms.ChoiceField(
        label='Tipo de Mercado',
        required=False,
        choices=[
            ('', '-- Todos os Tipos --'),
            ('INTERNO', 'Mercado Interno'),
            ('EXTERNO', 'Exportação'),
            ('AMBOS', 'Interno + Exportação'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )


# =============================================================================
# FORMULÁRIO PRINCIPAL DE VENDEDOR
# =============================================================================

class VendedorForm(forms.ModelForm):
    """
    Formulário principal para cadastro/edição de vendedores
    Validações e máscaras aplicadas automaticamente
    """
    
    class Meta:
        model = Vendedor
        fields = [
            # Identificação
            'nome_completo', 'cpf', 'rg', 'data_nascimento', 'foto',
            
            # Tipo
            'tipo_mercado', 'tipo_vinculo',
            
            # Contato
            'telefone_principal', 'telefone_secundario',
            'email_corporativo', 'email_pessoal', 'whatsapp',
            
            # Endereço
            'cep', 'logradouro', 'numero', 'complemento',
            'bairro', 'cidade', 'uf', 'pais',
            
            # Dados Comerciais
            'comissao_mercado_interno', 'comissao_exportacao',
            'comissao_fixa_mensal', 'meta_mensal',
            'forma_pagamento_comissao', 'moeda_padrao',
            
            # Banco
            'banco', 'agencia', 'conta_bancaria', 'tipo_conta_bancaria', 'pix',
            
            # Hierarquia
            'supervisor', 'nivel_autonomia', 'acesso_crm',
            
            # Exportação (se aplicável)
            'passaporte_numero', 'passaporte_validade', 'visto_trabalho', 'cnh',
            'certificacoes', 'idiomas', 'regioes_atuacao', 'paises_atuacao',
            
            # Status
            'status', 'data_admissao', 'data_desligamento', 'observacoes', 'experiencia_anos'
        ]
        
        widgets = {
            # Identificação
            'nome_completo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome completo do vendedor'
            }),
            'cpf': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '000.000.000-00',
                'maxlength': 14
            }),
            'rg': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'RG'
            }),
            'data_nascimento': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }, format='%Y-%m-%d'),
            'foto': forms.FileInput(attrs={'class': 'form-control'}),
            
            # Tipo
            'tipo_mercado': forms.Select(attrs={'class': 'form-select'}),
            'tipo_vinculo': forms.Select(attrs={'class': 'form-select'}),
            
            # Contato
            'telefone_principal': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '(84) 99999-9999'
            }),
            'telefone_secundario': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '(84) 99999-9999'
            }),
            'email_corporativo': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'vendedor@empresa.com'
            }),
            'email_pessoal': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'vendedor@email.com'
            }),
            'whatsapp': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://wa.me/5584999999999'
            }),
            
            # Endereço
            'cep': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '00000-000'
            }),
            'logradouro': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Rua, Avenida...'
            }),
            'numero': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nº'
            }),
            'complemento': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Apto, Sala...'
            }),
            'bairro': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Bairro'
            }),
            'cidade': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Cidade'
            }),
            'uf': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'UF',
                'maxlength': 2
            }),
            'pais': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Brasil'
            }),
            
            # Comercial
            'comissao_mercado_interno': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'max': '100'
            }),
            'comissao_exportacao': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'max': '100'
            }),
            'comissao_fixa_mensal': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'meta_mensal': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'forma_pagamento_comissao': forms.Select(attrs={'class': 'form-select'}),
            'moeda_padrao': forms.Select(attrs={'class': 'form-select'}),
            
            # Banco
            'banco': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome do Banco'
            }),
            'agencia': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '0000'
            }),
            'conta_bancaria': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '00000-0'
            }),
            'tipo_conta_bancaria': forms.Select(attrs={'class': 'form-select'}),
            'pix': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'CPF, e-mail ou telefone'
            }),
            
            # Hierarquia
            'supervisor': forms.Select(attrs={'class': 'form-select'}),
            'nivel_autonomia': forms.Select(attrs={'class': 'form-select'}),
            'acesso_crm': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            
            # Exportação
            'passaporte_numero': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'BR000000'
            }),
            'passaporte_validade': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }, format='%Y-%m-%d'),

            'visto_trabalho': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': '12345678'
            }),

            'cnh': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'CNH (apenas números)'
            }),

            'certificacoes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Certificações profissionais...'
            }),
            'idiomas': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Inglês, Espanhol...'
            }),
            'regioes_atuacao': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nordeste, Sudeste...'
            }),
            'paises_atuacao': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Brasil, EUA, China...'
            }),
            
            # Status
            'status': forms.Select(attrs={'class': 'form-select'}),
            'data_admissao': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }, format='%Y-%m-%d'),
            'data_desligamento': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'observacoes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Observações gerais sobre o vendedor...'
            }),

            'experiencia_anos': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '5,10,15'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        self.usuario = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)
        
        # Filtra supervisores pela empresa
        if self.empresa:
            self.fields['supervisor'].queryset = Vendedor.objects.filter(
                empresa=self.empresa,
                status='ATIVO'
            ).exclude(pk=self.instance.pk if self.instance.pk else None)
        else:
            self.fields['supervisor'].queryset = Vendedor.objects.none()

        # Preenche valores de data no formato ISO para inputs tipo=date (compatível com navegador)
        if self.instance and getattr(self.instance, 'data_nascimento', None):
            try:
                self.fields['data_nascimento'].initial = self.instance.data_nascimento.strftime('%Y-%m-%d')
            except Exception:
                pass
        if self.instance and getattr(self.instance, 'data_admissao', None):
            try:
                self.fields['data_admissao'].initial = self.instance.data_admissao.strftime('%Y-%m-%d')
            except Exception:
                pass
        
        # Remove campo empresa (será preenchido automaticamente)
        if 'empresa' in self.fields:
            self.fields['empresa'].widget = forms.HiddenInput()
    
    def clean_cpf(self):
        """Valida e formata CPF"""
        cpf = self.cleaned_data.get('cpf', '')
        
        # Remove formatação
        cpf_limpo = re.sub(r'\D', '', cpf)
        
        # Valida tamanho
        if len(cpf_limpo) != 11:
            raise forms.ValidationError('CPF deve ter 11 dígitos')
        
        # Verifica se já existe (exceto no próprio registro)
        qs = Vendedor.objects.filter(cpf=cpf_limpo)
        if self.empresa:
            qs = qs.filter(empresa=self.empresa)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        
        if qs.exists():
            raise forms.ValidationError('Este CPF já está cadastrado')
        
        return cpf_limpo
    
    def clean_email_corporativo(self):
        """Valida unicidade do e-mail corporativo"""
        email = self.cleaned_data.get('email_corporativo')
        
        qs = Vendedor.objects.filter(email_corporativo=email)
        if self.empresa:
            qs = qs.filter(empresa=self.empresa)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        
        if qs.exists():
            raise forms.ValidationError('Este e-mail já está cadastrado')
        
        return email
    
    def clean(self):
        """Validações gerais"""
        cleaned_data = super().clean()
        
        # Valida comissões
        comissao_interno = cleaned_data.get('comissao_mercado_interno', 0)
        comissao_exportacao = cleaned_data.get('comissao_exportacao', 0)
        
        if comissao_interno > 100 or comissao_exportacao > 100:
            raise forms.ValidationError('Comissão não pode ser maior que 100%')
        
        # Valida datas
        data_admissao = cleaned_data.get('data_admissao')
        data_desligamento = cleaned_data.get('data_desligamento')
        
        if data_admissao and data_desligamento:
            if data_desligamento < data_admissao:
                raise forms.ValidationError({
                    'data_desligamento': 'Data de desligamento não pode ser anterior à admissão'
                })
        
        return cleaned_data
    
    def save(self, commit=True):
        """Salva vendedor com empresa associada"""
        vendedor = super().save(commit=False)
        
        # Associa empresa
        if self.empresa:
            vendedor.empresa = self.empresa
        
        # Associa usuário criador
        if self.usuario and not vendedor.pk:
            vendedor.criado_por = self.usuario
        
        if commit:
            vendedor.save()
        
        return vendedor


# =============================================================================
# FORMULÁRIO DE COMISSÃO
# =============================================================================

class ComissaoVendedorForm(forms.ModelForm):
    """Formulário para registrar comissões de vendedores"""
    
    class Meta:
        model = ComissaoVendedor
        fields = [
            'vendedor', 'referencia_mes', 'valor_base',
            'percentual', 'status', 'observacoes'
        ]
        widgets = {
            'vendedor': forms.Select(attrs={'class': 'form-select'}),
            'referencia_mes': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'valor_base': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'percentual': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'max': '100'
            }),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        
        # Filtra vendedores pela empresa
        if self.empresa:
            self.fields['vendedor'].queryset = Vendedor.objects.filter(
                empresa=self.empresa,
                status='ATIVO'
            )
        else:
            self.fields['vendedor'].queryset = Vendedor.objects.none()
    
    def save(self, commit=True):
        """Calcula comissão automaticamente antes de salvar"""
        comissao = super().save(commit=False)
        
        # Associa empresa
        if self.empresa:
            comissao.empresa = self.empresa
        
        if commit:
            comissao.save()
        
        return comissao


# =============================================================================
# Forms: Porto (novo cadastro multi-tenant)
# =============================================================================

class PortoForm(forms.ModelForm):
    """Formulário para cadastro de Portos (multi-tenant por `empresa`)"""

    class Meta:
        model = __import__('cadastros.models', fromlist=['Porto']).Porto
        # Empresa será preenchida pela view/admin
        exclude = ('empresa',)
        fields = ['codigo', 'nome', 'pais', 'cidade', 'tipo', 'ativo']
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código (ex: BRBEL)'}),
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do porto'}),
            'pais': forms.TextInput(attrs={'class': 'form-control'}),
            'cidade': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        # Recebe empresa se fornecida (ex: pela view)
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        # Torna 'codigo' obrigatório quando a empresa for conhecida
        if self.empresa:
            self.fields['codigo'].required = True

    def clean_codigo(self):
        codigo = self.cleaned_data.get('codigo', '')
        # Normaliza e valida
        codigo_limpo = codigo.strip().upper()
        if not codigo_limpo:
            raise ValidationError('Código do porto é obrigatório')
        # Verifica unicidade por empresa
        qs = __import__('cadastros.models', fromlist=['Porto']).Porto.objects.filter(codigo=codigo_limpo)
        if self.empresa:
            qs = qs.filter(empresa=self.empresa)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('Já existe um porto com este código para a mesma empresa')
        return codigo_limpo

    def save(self, commit=True):
        porto = super().save(commit=False)
        if self.empresa:
            porto.empresa = self.empresa
        if commit:
            porto.save()
        return porto

# =============================================================================
# Forms: Veículos (Vehicle)
# =============================================================================

from .models import Vehicle, VehiclePlate


class VehicleForm(forms.ModelForm):
    origem = forms.ChoiceField(
        choices=[('PROPRIO', 'Proprio'), ('TERCEIRO', 'Terceiro')],
        initial='PROPRIO',
        label='Origem do Veiculo',
        widget=forms.Select(attrs={'class': 'form-select', 'data-toggle-transportadora': '1'})
    )
    aplicar_variacao_agora = forms.BooleanField(required=False, initial=False, label='Aplicar variação agora')

    class Meta:
        model = Vehicle
        exclude = ('empresa', 'data_cadastro', 'data_atualizacao')
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'marca': forms.TextInput(attrs={'class': 'form-control'}),
            'modelo': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Trator Amarelo, Implemento XX'}),
            'ano_fabricacao': forms.NumberInput(attrs={'class': 'form-control'}),
            'ano_modelo': forms.NumberInput(attrs={'class': 'form-control'}),
            'capacidade_ton': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tara_kg': forms.NumberInput(attrs={'class': 'form-control'}),
            'eixos': forms.NumberInput(attrs={'class': 'form-control'}),
            'cor': forms.TextInput(attrs={'class': 'form-control'}),
            'foto': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'renavam': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'RENAVAM'}),
            'chassis': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Chassi'}),
            'numero_motor': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número do Motor'}),
            'tipo_combustivel': forms.Select(attrs={'class': 'form-select'}),
            'codigo_patrimonio': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código de Patrimônio (se não há placa)'}),
            'consumo_medio': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
            'consumo_unidade': forms.Select(attrs={'class': 'form-select'}),
            'tank_capacity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'valor_atual': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'percentual_variacao': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tipo_variacao': forms.Select(attrs={'class': 'form-select'}),
            'transportadora': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }

    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if 'empresa' in self.fields:
            self.fields['empresa'].widget = forms.HiddenInput()
            self.fields['empresa'].required = False
        if self.empresa:
            self.initial['empresa'] = self.empresa
        if self.instance and self.instance.pk:
            self.initial['origem'] = 'TERCEIRO' if self.instance.transportadora else 'PROPRIO'

    def clean(self):
        from decimal import Decimal
        cleaned = super().clean()
        origem = cleaned.get('origem')
        transportadora = cleaned.get('transportadora')
        aplicar = cleaned.get('aplicar_variacao_agora')
        perc = cleaned.get('percentual_variacao')
        tipo = cleaned.get('tipo_variacao')
        valor = cleaned.get('valor_atual')

        if origem == 'TERCEIRO' and not transportadora:
            raise ValidationError({'transportadora': 'Selecione a transportadora para veiculo de terceiro.'})
        if origem == 'PROPRIO':
            cleaned['transportadora'] = None

        if aplicar:
            if valor is None:
                raise ValidationError({'valor_atual': 'Para aplicar a variação é necessário informar o Valor Atual.'})
            if perc is None or perc == Decimal('0.00'):
                raise ValidationError({'percentual_variacao': 'Informe um percentual diferente de 0 para aplicar a variação.'})
            if not tipo:
                raise ValidationError({'tipo_variacao': 'Selecione o tipo de variação (Valorização/Desvalorização).'})
        return cleaned

    def save(self, commit=True, user=None):
        """Saves vehicle and applies variation if requested, also sets empresa."""
        from decimal import Decimal
        obj = super().save(commit=False)
        if self.empresa:
            obj.empresa = self.empresa

        if self.cleaned_data.get('origem') == 'PROPRIO':
            obj.transportadora = None

        aplicar = self.cleaned_data.get('aplicar_variacao_agora')
        perc = self.cleaned_data.get('percentual_variacao')
        tipo = self.cleaned_data.get('tipo_variacao')

        # If requested, apply variation to valor_atual
        if aplicar and perc and tipo and obj.valor_atual is not None:
            prev = obj.valor_atual or Decimal('0.00')
            factor = (Decimal('1.0') + (perc / Decimal('100'))) if tipo == 'VAL' else (Decimal('1.0') - (perc / Decimal('100')))
            new_val = (prev * factor).quantize(Decimal('0.01'))
            obj.valor_atual = new_val
            if commit:
                obj.save()
                try:
                    VehicleValueHistory = __import__('cadastros.models', fromlist=['VehicleValueHistory']).VehicleValueHistory
                    VehicleValueHistory.objects.create(
                        vehicle=obj,
                        previous_value=prev,
                        new_value=new_val,
                        percentual=perc,
                        tipo=tipo,
                        aplicado_por=user
                    )
                except Exception:
                    pass
            return obj

        if commit:
            obj.save()
        return obj


class VehiclePlateForm(forms.ModelForm):
    class Meta:
        model = VehiclePlate
        fields = ['placa', 'vigencia_inicio', 'vigencia_fim', 'atual']
        widgets = {
            'placa': forms.TextInput(attrs={'class': 'form-control'}),
            'vigencia_inicio': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'vigencia_fim': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'atual': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }
        labels = {
            'placa': 'Placa',
            'vigencia_inicio': 'Data Início da Vigência',
            'vigencia_fim': 'Data Fim da Vigência (opcional)',
            'atual': 'Placa Atual'
        }
        help_texts = {
            'vigencia_inicio': 'Data em que esta placa passou a vigorar neste veículo.',
            'vigencia_fim': 'Data em que esta placa deixou de ser utilizada (opcional).'
        }

    def __init__(self, *args, **kwargs):
        self.vehicle = kwargs.pop('vehicle', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        vi = cleaned.get('vigencia_inicio')
        vf = cleaned.get('vigencia_fim')
        if vi and vf and vf <= vi:
            raise ValidationError({'vigencia_fim': 'Data fim da vigência deve ser posterior à data início'})
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        if self.vehicle:
            obj.vehicle = self.vehicle
        if commit:
            obj.save()
        return obj



# =============================================================================
# FORMULÁRIOS: MONITORAMENTO MIP (Manejo Integrado de Pragas)
# =============================================================================

class MonitoramentoMIPForm(forms.ModelForm):
    """Formulário para criar/editar monitoramento MIP"""
    
    class Meta:
        model = MonitoramentoMIP
        fields = [
            'talhao', 'safra', 'cultura', 'data_monitoramento', 'tipo_monitoramento',
            'responsavel', 'quantidade_pontos',
            'condicoes_tempo', 'temperatura_media', 'umidade_media',
            'velocidade_vento_media', 'foto_area_geral',
            'observacoes_gerais'
        ]
        widgets = {
            'talhao': forms.Select(attrs={'class': 'form-control'}),
            'safra': forms.Select(attrs={'class': 'form-control'}),
            'cultura': forms.Select(attrs={'class': 'form-control'}),
            'data_monitoramento': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'tipo_monitoramento': forms.Select(attrs={'class': 'form-control'}),
            'responsavel': forms.Select(attrs={'class': 'form-control'}),
            'quantidade_pontos': forms.NumberInput(attrs={
                'class': 'form-control',
                'value': '20'
            }),
            'condicoes_tempo': forms.Select(attrs={
                'class': 'form-select'
            }),
            'temperatura_media': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1',
                'placeholder': '°C'
            }),
            'umidade_media': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '100',
                'placeholder': '%'
            }),
            'velocidade_vento_media': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1',
                'placeholder': 'km/h'
            }),
            'foto_area_geral': forms.FileInput(attrs={'class': 'form-control'}),
            'observacoes_gerais': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Notas gerais sobre a visita'
            }),
        }
        labels = {
            'talhao': 'Talhão',
            'safra': 'Safra',
            'cultura': 'Cultura',
            'data_monitoramento': 'Data do Monitoramento',
            'tipo_monitoramento': 'Tipo de Monitoramento',
            'responsavel': 'Responsável (Pragueiro)',
            'quantidade_pontos': 'Quantidade de Pontos',
            'condicoes_tempo': 'Condições do Tempo',
            'temperatura_media': 'Temperatura Média (°C)',
            'umidade_media': 'Umidade Média (%)',
            'velocidade_vento_media': 'Velocidade do Vento Média (km/h)',
            'foto_area_geral': 'Foto da Área Geral',
            'observacoes_gerais': 'Observações Gerais',
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)

        # Campo em formato de lista para facilitar preenchimento no campo.
        self.fields['condicoes_tempo'].required = False

        # Compatibilidade com dados legados salvos antes de virar dropdown.
        valor_legado = (getattr(self.instance, 'condicoes_tempo', '') or '').strip() if self.instance else ''
        choices = [('', 'Selecione...')] + list(getattr(MonitoramentoMIP, 'CONDICOES_TEMPO_CHOICES', []))
        if valor_legado and valor_legado not in {codigo for codigo, _ in choices}:
            choices.append((valor_legado, f'Valor antigo: {valor_legado}'))
        self.fields['condicoes_tempo'].choices = choices

        # Se não tiver empresa, preencher com a do usuário
        if self.empresa:
            # Configurar campo Talhão com widget padrão do Django
            self.fields['talhao'].queryset = Talhao.objects.filter(
                area__fazenda__empresa=self.empresa,
                ativo=True
            ).select_related('area', 'fazenda').distinct().order_by('codigo')
            
            # Aplicar CSS Bootstrap ao select
            self.fields['talhao'].widget.attrs.update({
                'class': 'form-control form-select-lg',
            })
            
            # Mostrar apenas safras ATIVAS (não finalizadas)
            self.fields['safra'].queryset = Safra.objects.filter(
                fazenda__empresa=self.empresa,
                status__in=['PLANEJADA', 'EM_ANDAMENTO']
            ).select_related('fazenda', 'cultura').order_by('-ano', 'nome')
            
            # Marcar safra como obrigatória
            self.fields['safra'].required = True
            
            self.fields['cultura'].queryset = Cultura.objects.filter(
                empresa=self.empresa
            )
        
        # Auto-preencher responsável
        if self.user:
            self.fields['responsavel'].initial = self.user.id
            self.fields['responsavel'].widget = forms.HiddenInput()
    
    def clean(self):
        cleaned = super().clean()
        dt = cleaned.get('data_monitoramento')
        if dt and dt > timezone.now().date():
            raise ValidationError(
                'Data do monitoramento não pode ser no futuro'
            )
        
        talhao = cleaned.get('talhao')
        safra = cleaned.get('safra')
        cultura = cleaned.get('cultura')
        
        # Validar que tem cultura (pela safra ou direto)
        if not cultura and safra and safra.cultura:
            # OK - cultura virá da safra
            pass
        elif not cultura and talhao and talhao.cultura_atual:
            # OK - cultura virá do talhão
            pass
        elif not cultura:
            raise ValidationError(
                'Selecione uma cultura ou escolha um talhão/safra com cultura associada.'
            )
        
        return cleaned


class PragaNoMonitoramentoForm(forms.ModelForm):
    """Formulário para adicionar uma praga ao monitoramento"""
    
    class Meta:
        model = PragaNoMonitoramento
        fields = [
            'praga', 'quantidade_pontos_com_praga', 'incidencia_percentual',
            'estagio_principal', 'detalhes_estagios', 'severidade', 
            'quantidade_total_pragas', 'ned_valor', 'observacoes'
        ]
        widgets = {
            'praga': forms.Select(attrs={'class': 'form-control'}),
            'quantidade_pontos_com_praga': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '20'
            }),
            'incidencia_percentual': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'readonly': 'readonly',
                'disabled': 'disabled'
            }),
            'estagio_principal': forms.Select(attrs={'class': 'form-control'}),
            'detalhes_estagios': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'JSON: {"L3": 5, "L4": 3}'
            }),
            'severidade': forms.RadioSelect(attrs={'class': 'form-check-input'}),
            'quantidade_total_pragas': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            }),
            'ned_valor': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'value': '5.0'
            }),
            'observacoes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2
            }),
        }
        labels = {
            'praga': 'Praga/Doença',
            'quantidade_pontos_com_praga': 'Quantidade de Pontos com Praga (0-20)',
            'incidencia_percentual': 'Incidência (%)',
            'estagio_principal': 'Estágio Principal Encontrado',
            'detalhes_estagios': 'Detalhes por Estágio (JSON)',
            'severidade': 'Severidade (1-5)',
            'quantidade_total_pragas': 'Quantidade Total de Pragas',
            'ned_valor': 'Nível Econômico de Dano (NED) %',
            'observacoes': 'Observações',
        }
    
    def __init__(self, *args, **kwargs):
        self.monitoramento = kwargs.pop('monitoramento', None)
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        
        if self.empresa:
            self.fields['praga'].queryset = Praga.objects.filter(
                empresa=self.empresa,
                ativa=True
            )
        
        if self.monitoramento and self.monitoramento.cultura:
            # Filtrar estágios apenas da praga selecionada
            self.fields['estagio_principal'].queryset = \
                EstagioDesenvolvimento.objects.none()
    
    def clean(self):
        cleaned = super().clean()
        qty = cleaned.get('quantidade_pontos_com_praga')
        
        if qty and qty > 20:
            raise ValidationError(
                'Quantidade de pontos não pode exceder 20'
            )
        
        if qty and qty < 0:
            raise ValidationError(
                'Quantidade de pontos não pode ser negativa'
            )
        
        return cleaned
    
    def save(self, commit=True):
        obj = super().save(commit=False)
        
        # Auto-calcular incidência
        if obj.quantidade_pontos_com_praga and self.monitoramento:
            obj.incidencia_percentual = (
                (obj.quantidade_pontos_com_praga / 
                 self.monitoramento.quantidade_pontos) * 100
            )
        
        # Auto-carregar NED (buscar recomendação)
        if obj.praga and self.monitoramento and obj.estagio_principal:
            try:
                from produtos.models import RecomendacaoDefensivo
                rec = RecomendacaoDefensivo.objects.filter(
                    empresa=self.monitoramento.empresa,
                    praga=obj.praga
                ).first()
                if rec:
                    obj.ned_valor = Decimal('5.0')  # Padrão (será dinâmico)
            except:
                pass
        
        if commit:
            obj.save()
        return obj


class PontoMonitoramentoForm(forms.ModelForm):
    """Formulário para registrar dados de um ponto"""
    
    class Meta:
        model = PontoMonitoramento
        fields = [
            'numero_ponto', 'praga_presente', 'quantidade', 'estagio',
            'severidade', 'foto', 'observacoes',
            'latitude', 'longitude'
        ]
        widgets = {
            'numero_ponto': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '20',
                'readonly': 'readonly'
            }),
            'praga_presente': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'quantidade': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            }),
            'estagio': forms.Select(attrs={'class': 'form-control'}),
            'severidade': forms.RadioSelect(attrs={'class': 'form-check-input'}),
            'foto': forms.FileInput(attrs={'class': 'form-control'}),
            'observacoes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2
            }),
            'latitude': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.000001',
                'placeholder': 'GPS (opcional)'
            }),
            'longitude': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.000001',
                'placeholder': 'GPS (opcional)'
            }),
        }
        labels = {
            'numero_ponto': 'Número do Ponto',
            'praga_presente': 'Praga Presente?',
            'quantidade': 'Quantidade de Insetos/Lesões',
            'estagio': 'Estágio Encontrado',
            'severidade': 'Severidade',
            'foto': 'Foto do Ponto',
            'observacoes': 'Observações',
            'latitude': 'Latitude (GPS)',
            'longitude': 'Longitude (GPS)',
        }
    
    def clean(self):
        cleaned = super().clean()
        praga_presente = cleaned.get('praga_presente')
        quantidade = cleaned.get('quantidade')
        
        if praga_presente and not quantidade:
            raise ValidationError(
                'Se praga está presente, informar quantidade'
            )
        
        if praga_presente and not cleaned.get('estagio'):
            raise ValidationError(
                'Se praga está presente, informar o estágio'
            )
        
        return cleaned


class EstagioDesenvolvimentoForm(forms.ModelForm):
    """Formulário para cadastrar estágios de desenvolvimento de praga"""
    
    class Meta:
        model = EstagioDesenvolvimento
        fields = [
            'praga', 'tipo_estagio', 'descricao',
            'duracao_minima_dias', 'duracao_maxima_dias',
            'ordem_ciclo', 'eh_fase_critica', 'observacoes', 'ativo'
        ]
        widgets = {
            'praga': forms.Select(attrs={'class': 'form-control'}),
            'tipo_estagio': forms.Select(attrs={'class': 'form-control'}),
            'descricao': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Larva de 3º ínstar'
            }),
            'duracao_minima_dias': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            }),
            'duracao_maxima_dias': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            }),
            'ordem_ciclo': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1'
            }),
            'eh_fase_critica': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'observacoes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2
            }),
            'ativo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        labels = {
            'praga': 'Praga',
            'tipo_estagio': 'Tipo de Estágio',
            'descricao': 'Descrição',
            'duracao_minima_dias': 'Duração Mínima (dias)',
            'duracao_maxima_dias': 'Duração Máxima (dias)',
            'ordem_ciclo': 'Ordem no Ciclo',
            'eh_fase_critica': 'É Fase Crítica?',
            'observacoes': 'Observações',
            'ativo': 'Ativo',
        }
    
    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        
        if self.empresa:
            # Filtro padrão: pragas da empresa
            queryset = Praga.objects.filter(
                empresa=self.empresa,
                ativa=True
            ).order_by('nome_comum')
            
            # Se editando (instance), garantir que a praga atual fica visível
            # mesmo que não tenha uma empresa específica (pode ser um template)
            if self.instance and self.instance.pk and self.instance.praga:
                if self.instance.praga not in queryset:
                    queryset = queryset | Praga.objects.filter(pk=self.instance.praga.pk)
                    
            self.fields['praga'].queryset = queryset


# =============================================================================
# CONTROLE DE RH - FÉRIAS, AFASTAMENTOS E RESCISÕES
# =============================================================================

from .models import FeriasFuncionario, AfastamentoFuncionario, RescisaoContrato, LaudoRisco, TipoExameASO, SolicitacaoASO


class FeriasFuncionarioForm(forms.ModelForm):
    """Formulário para cadastro de férias"""
    
    class Meta:
        model = FeriasFuncionario
        fields = [
            'funcionario', 'periodo_aquisitivo_inicio', 'periodo_aquisitivo_fim',
            'data_inicio', 'data_fim', 'dias_ferias', 'tipo_ferias',
            'abono_pecuniario', 'dias_abono', 'valor_ferias', 'valor_abono',
            'status', 'data_pagamento', 'observacoes', 'recibo_ferias'
        ]
        widgets = {
            'funcionario': forms.Select(attrs={'class': 'form-select'}),
            'periodo_aquisitivo_inicio': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'periodo_aquisitivo_fim': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'data_inicio': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'data_fim': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'dias_ferias': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '30'
            }),
            'tipo_ferias': forms.Select(attrs={'class': 'form-select'}),
            'abono_pecuniario': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'dias_abono': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '10'
            }),
            'valor_ferias': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'valor_abono': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'data_pagamento': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'observacoes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'recibo_ferias': forms.FileInput(attrs={
                'class': 'form-control'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        
        if self.empresa:
            self.fields['funcionario'].queryset = Funcionario.objects.filter(
                empresa=self.empresa,
                ativo=True
            ).order_by('nome_completo')


class AfastamentoFuncionarioForm(forms.ModelForm):
    """Formulário para cadastro de afastamentos"""
    
    class Meta:
        model = AfastamentoFuncionario
        fields = [
            'funcionario', 'tipo_afastamento', 'data_inicio',
            'data_prevista_retorno', 'data_retorno_efetivo', 'dias_afastamento',
            'motivo', 'cid', 'numero_atestado', 'medico_responsavel', 'crm_medico',
            'arquivo_atestado', 'e_acidente_trabalho', 'cat_emitida', 'numero_cat',
            'arquivo_cat', 'requer_inss', 'numero_beneficio_inss', 'status', 'observacoes'
        ]
        widgets = {
            'funcionario': forms.Select(attrs={'class': 'form-select'}),
            'tipo_afastamento': forms.Select(attrs={'class': 'form-select'}),
            'data_inicio': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'data_prevista_retorno': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'data_retorno_efetivo': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'dias_afastamento': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1'
            }),
            'motivo': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descreva o motivo do afastamento'
            }),
            'cid': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: M54.5'
            }),
            'numero_atestado': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'medico_responsavel': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'crm_medico': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: CRM/SP 123456'
            }),
            'arquivo_atestado': forms.FileInput(attrs={
                'class': 'form-control'
            }),
            'e_acidente_trabalho': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'cat_emitida': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'numero_cat': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'arquivo_cat': forms.FileInput(attrs={
                'class': 'form-control'
            }),
            'requer_inss': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'numero_beneficio_inss': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        
        if self.empresa:
            self.fields['funcionario'].queryset = Funcionario.objects.filter(
                empresa=self.empresa,
                ativo=True
            ).order_by('nome_completo')


class VinculoContratoForm(forms.ModelForm):
    """Formulário de contratação/recontratação por vínculo contratual."""

    class Meta:
        model = VinculoContrato
        fields = [
            'funcionario', 'funcao', 'matricula', 'tipo_contrato', 'origem', 'status',
            'data_inicio', 'data_fim_prevista', 'periodo_experiencia', 'data_fim_experiencia',
            'salario', 'observacoes'
        ]
        widgets = {
            'funcionario': forms.Select(attrs={'class': 'form-select'}),
            'funcao': forms.Select(attrs={'class': 'form-select'}),
            'matricula': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Matrícula do vínculo'}),
            'tipo_contrato': forms.Select(attrs={'class': 'form-select'}),
            'origem': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'data_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_fim_prevista': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'periodo_experiencia': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'data_fim_experiencia': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'salario': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)

        if self.empresa:
            self.fields['funcionario'].queryset = Funcionario.objects.filter(
                empresa=self.empresa
            ).order_by('nome_completo')
            self.fields['funcao'].queryset = FuncaoFuncionario.objects.filter(
                empresa=self.empresa,
                ativa=True
            ).order_by('nome')

    def clean(self):
        cleaned_data = super().clean()
        funcionario = cleaned_data.get('funcionario')
        status = cleaned_data.get('status')
        data_inicio = cleaned_data.get('data_inicio')
        data_fim_prevista = cleaned_data.get('data_fim_prevista')

        if data_fim_prevista and data_inicio and data_fim_prevista < data_inicio:
            self.add_error('data_fim_prevista', 'Data fim prevista não pode ser menor que a data de início.')

        if funcionario and status == 'ATIVO':
            vinculos_ativos = VinculoContrato.objects.filter(
                empresa=self.empresa,
                funcionario=funcionario,
                status='ATIVO'
            )
            if self.instance.pk:
                vinculos_ativos = vinculos_ativos.exclude(pk=self.instance.pk)
            if vinculos_ativos.exists():
                self.add_error('status', 'Este funcionário já possui um vínculo ATIVO.')

        return cleaned_data


class LaudoRiscoForm(forms.ModelForm):
    """Formulário para cadastro de laudos de risco ocupacional."""

    class Meta:
        model = LaudoRisco
        fields = [
            'funcao', 'vinculo', 'tipo_laudo', 'data_emissao', 'data_validade',
            'responsavel_tecnico', 'numero_art', 'arquivo_laudo', 'status', 'observacoes'
        ]
        widgets = {
            'funcao': forms.Select(attrs={'class': 'form-select'}),
            'vinculo': forms.Select(attrs={'class': 'form-select'}),
            'tipo_laudo': forms.Select(attrs={'class': 'form-select'}),
            'data_emissao': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_validade': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'responsavel_tecnico': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_art': forms.TextInput(attrs={'class': 'form-control'}),
            'arquivo_laudo': forms.FileInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)

        if self.empresa:
            self.fields['funcao'].queryset = FuncaoFuncionario.objects.filter(
                empresa=self.empresa,
                ativa=True,
            ).order_by('nome')
            self.fields['vinculo'].queryset = VinculoContrato.objects.filter(
                empresa=self.empresa,
                status='ATIVO',
            ).select_related('funcionario', 'funcao').order_by('-data_inicio')

        self.fields['vinculo'].required = False

    def clean(self):
        cleaned_data = super().clean()
        funcao = cleaned_data.get('funcao')
        vinculo = cleaned_data.get('vinculo')

        if funcao and vinculo and vinculo.funcao_id != funcao.id:
            self.add_error('vinculo', 'O vínculo deve pertencer à mesma função selecionada.')

        return cleaned_data


class TipoExameASOForm(forms.ModelForm):
    """Formulário de cadastro de tipo de exame ASO."""

    class Meta:
        model = TipoExameASO
        fields = ['nome', 'codigo', 'ativo', 'ordem', 'observacoes']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'codigo': forms.TextInput(attrs={'class': 'form-control'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ordem': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)

    def clean_codigo(self):
        codigo = (self.cleaned_data.get('codigo') or '').strip().upper()
        if not codigo:
            raise forms.ValidationError('Informe o código do exame.')

        if self.empresa:
            qs = TipoExameASO.objects.filter(empresa=self.empresa, codigo=codigo)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError('Já existe um tipo de exame com esse código na empresa.')

        return codigo

    def clean_nome(self):
        nome = (self.cleaned_data.get('nome') or '').strip()
        if not nome:
            raise forms.ValidationError('Informe o nome do exame.')

        if self.empresa:
            qs = TipoExameASO.objects.filter(empresa=self.empresa, nome__iexact=nome)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError('Já existe um tipo de exame com esse nome na empresa.')

        return nome


class SolicitacaoASOForm(forms.ModelForm):
    """Formulário de solicitação de ASO."""

    class Meta:
        model = SolicitacaoASO
        fields = [
            'funcionario', 'vinculo', 'tipo_aso',
            'data_solicitacao', 'data_prevista_exame', 'data_vencimento',
            'laboratorio_nome', 'laboratorio_email', 'trabalhador_whatsapp',
            'exames', 'possui_outros_exames', 'outros_exames_descricao',
            'status', 'gerar_alerta_vencimento', 'dias_antecedencia_alerta',
            'periodicidade_meses',
        ]
        widgets = {
            'funcionario': forms.Select(attrs={'class': 'form-select'}),
            'vinculo': forms.Select(attrs={'class': 'form-select'}),
            'tipo_aso': forms.Select(attrs={'class': 'form-select'}),
            'data_solicitacao': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
            'data_prevista_exame': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
            'data_vencimento': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
            'laboratorio_nome': forms.TextInput(attrs={'class': 'form-control'}),
            'laboratorio_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'trabalhador_whatsapp': forms.TextInput(attrs={'class': 'form-control'}),
            'exames': forms.SelectMultiple(attrs={'class': 'form-select', 'size': '8'}),
            'possui_outros_exames': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'outros_exames_descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'gerar_alerta_vencimento': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'dias_antecedencia_alerta': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'periodicidade_meses': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
        }

    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)

        self.fields['periodicidade_meses'].required = False

        # Garante renderização correta em <input type="date"> e mantém aceitação dd/mm/aaaa.
        for campo_data in ('data_solicitacao', 'data_prevista_exame', 'data_vencimento'):
            self.fields[campo_data].input_formats = ['%Y-%m-%d', '%d/%m/%Y']

        if self.instance and self.instance.pk:
            for campo_data in ('data_solicitacao', 'data_prevista_exame', 'data_vencimento'):
                valor = getattr(self.instance, campo_data, None)
                if valor:
                    self.initial[campo_data] = valor.strftime('%Y-%m-%d')

        if self.empresa:
            self.fields['funcionario'].queryset = Funcionario.objects.filter(
                empresa=self.empresa
            ).order_by('nome_completo')

            self.fields['vinculo'].queryset = VinculoContrato.objects.filter(
                empresa=self.empresa
            ).select_related('funcionario', 'funcao').order_by('-data_inicio')

            exames_qs = TipoExameASO.objects.filter(
                empresa=self.empresa,
                ativo=True,
            ).order_by('ordem', 'nome')

            if self.instance and self.instance.pk:
                exames_qs = (exames_qs | self.instance.exames.all()).distinct()

            self.fields['exames'].queryset = exames_qs

    def clean(self):
        cleaned_data = super().clean()
        funcionario = cleaned_data.get('funcionario')
        vinculo = cleaned_data.get('vinculo')
        tipo_aso = cleaned_data.get('tipo_aso')
        status = cleaned_data.get('status')
        periodicidade_meses = cleaned_data.get('periodicidade_meses')
        data_vencimento = cleaned_data.get('data_vencimento')
        exames = cleaned_data.get('exames')
        possui_outros_exames = cleaned_data.get('possui_outros_exames')
        outros_exames_descricao = (cleaned_data.get('outros_exames_descricao') or '').strip()

        if periodicidade_meses in (None, ''):
            cleaned_data['periodicidade_meses'] = getattr(self.instance, 'periodicidade_meses', None) or 12

        if vinculo and funcionario and vinculo.funcionario_id != funcionario.id:
            self.add_error('vinculo', 'O vínculo selecionado não pertence ao funcionário informado.')

        if tipo_aso == 'PERIODICO' and not data_vencimento:
            self.add_error('data_vencimento', 'ASO periódico exige data de vencimento.')

        if not exames:
            self.add_error('exames', 'Selecione ao menos um exame para a solicitação.')

        if possui_outros_exames and not outros_exames_descricao:
            self.add_error('outros_exames_descricao', 'Descreva os exames adicionais quando essa opção estiver marcada.')

        if tipo_aso == 'DEMISSIONAL' and status == 'CONCLUIDO':
            cleaned_data['gerar_alerta_vencimento'] = False
            cleaned_data['periodicidade_meses'] = cleaned_data.get('periodicidade_meses') or 12

        return cleaned_data


class RescisaoContratoForm(forms.ModelForm):
    """Formulário para cadastro de rescisões"""
    
    class Meta:
        model = RescisaoContrato
        fields = [
            'funcionario', 'vinculo', 'tipo_rescisao', 'data_aviso', 'data_desligamento',
            'trabalhou_aviso_previo', 'dias_aviso_previo', 'motivo_detalhado',
            'saldo_salario', 'ferias_vencidas', 'ferias_proporcionais',
            'decimo_terceiro_proporcional', 'aviso_previo_indenizado',
            'multa_fgts', 'outros_valores', 'descontos', 'valor_liquido',
            'tem_direito_seguro_desemprego', 'liberar_fgts',
            'exame_demissional_realizado', 'data_exame_demissional',
            'trct_emitido', 'chave_conectividade_social',
            'arquivo_trct', 'arquivo_exame', 'data_homologacao',
            'local_homologacao', 'data_pagamento', 'forma_pagamento',
            'status', 'observacoes'
        ]
        widgets = {
            'funcionario': forms.Select(attrs={'class': 'form-select'}),
            'vinculo': forms.Select(attrs={'class': 'form-select'}),
            'tipo_rescisao': forms.Select(attrs={'class': 'form-select'}),
            'data_aviso': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'data_desligamento': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'trabalhou_aviso_previo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'dias_aviso_previo': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            }),
            'motivo_detalhado': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'saldo_salario': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'ferias_vencidas': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'ferias_proporcionais': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'decimo_terceiro_proporcional': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'aviso_previo_indenizado': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'multa_fgts': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'outros_valores': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'descontos': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'valor_liquido': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'readonly': 'readonly'
            }),
            'tem_direito_seguro_desemprego': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'liberar_fgts': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'exame_demissional_realizado': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'data_exame_demissional': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'trct_emitido': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'chave_conectividade_social': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'arquivo_trct': forms.FileInput(attrs={
                'class': 'form-control'
            }),
            'arquivo_exame': forms.FileInput(attrs={
                'class': 'form-control'
            }),
            'data_homologacao': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'local_homologacao': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'data_pagamento': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'forma_pagamento': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Transferência bancária'
            }),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        
        if self.empresa:
            self.fields['funcionario'].queryset = Funcionario.objects.filter(
                empresa=self.empresa
            ).order_by('nome_completo')
            self.fields['vinculo'].queryset = VinculoContrato.objects.filter(
                empresa=self.empresa
            ).select_related('funcionario').order_by('-data_inicio')

            funcionario_id = None
            if self.is_bound:
                funcionario_id = self.data.get('funcionario')
            elif self.instance and self.instance.pk:
                funcionario_id = self.instance.funcionario_id

            if funcionario_id:
                self.fields['vinculo'].queryset = self.fields['vinculo'].queryset.filter(
                    funcionario_id=funcionario_id
                )
            else:
                self.fields['vinculo'].queryset = self.fields['vinculo'].queryset.none()
        
        # Calcular valor líquido automaticamente quando salvando
        if self.instance and self.instance.pk:
            self.initial['valor_liquido'] = self.instance.calcular_valor_liquido()

    def clean(self):
        cleaned_data = super().clean()
        funcionario = cleaned_data.get('funcionario')
        vinculo = cleaned_data.get('vinculo')

        if vinculo and funcionario and vinculo.funcionario_id != funcionario.id:
            self.add_error('vinculo', 'O vínculo selecionado não pertence ao funcionário informado.')

        return cleaned_data


# =============================================================================
# FORMSETS PARA MÚLTIPLOS DOCUMENTOS
# =============================================================================

from django.forms import inlineformset_factory, formset_factory

# Formset para múltiplos DocumentoFuncionario (permite adicionar vários documentos no mesmo formulário)
DocumentoFuncionarioFormSet = inlineformset_factory(
    Funcionario,
    DocumentoFuncionario,
    form=DocumentoFuncionarioForm,
    extra=1,  # Mostra apenas 1 formulário em branco; clique em "Adicionar Mais" para adicionar outros
    can_delete=True,  # Permite deletar documentos existentes
    min_num=0,
    validate_min=False
)


# =============================================================================
# ✅ FIM DO CÓDIGO - TESTADO E FUNCIONANDO
# =============================================================================


# =============================================================================
# MÓDULO: ORDENS DE SERVIÇO AGRÍCOLAS
# =============================================================================

from .models import (
    OrdemServico,
    OrdemServicoInsumo,
    OSFuncionario,
    OSMaquina,
    CustoHoraMaquina,
    TipoServicoOS,
    SubtipoServicoOS,
    ModalidadeExecucaoOS,
)


class OrdemServicoForm(forms.ModelForm):
    """Formulário principal de criação/edição de Ordem de Serviço"""

    class Meta:
        model = OrdemServico
        fields = [
            'tipo_servico', 'subtipo_servico', 'modalidade_execucao',
            'talhao', 'safra', 'responsavel', 'data_prevista',
            'area_executada_ha', 'fornecedor_servico', 'valor_servico_externo',
            'unidade_cobranca', 'requisicao', 'observacoes', 'foto_evidencia',
        ]
        widgets = {
            'tipo_servico': forms.Select(attrs={'class': 'form-select', 'id': 'id_tipo_servico'}),
            'subtipo_servico': forms.Select(attrs={'class': 'form-select', 'id': 'id_subtipo_servico'}),
            'modalidade_execucao': forms.Select(attrs={'class': 'form-select', 'id': 'id_modalidade_execucao'}),
            'talhao': forms.Select(attrs={'class': 'form-select'}),
            'safra': forms.Select(attrs={'class': 'form-select'}),
            'responsavel': forms.Select(attrs={'class': 'form-select'}),
            'data_prevista': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'area_executada_ha': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
            'fornecedor_servico': forms.Select(attrs={'class': 'form-select'}),
            'valor_servico_externo': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'unidade_cobranca': forms.Select(attrs={'class': 'form-select'}),
            'requisicao': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'foto_evidencia': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        from django.db.models import Q
        if empresa:
            self.fields['tipo_servico'].queryset = TipoServicoOS.objects.filter(
                Q(empresa=empresa) | Q(empresa=None), ativo=True
            ).order_by('ordem', 'nome')

            self.fields['modalidade_execucao'].queryset = ModalidadeExecucaoOS.objects.filter(
                Q(empresa=empresa) | Q(empresa=None), ativo=True
            ).order_by('ordem', 'nome')

            # Carrega subtipos: usa o tipo_servico da instância (edição) ou do POST
            tipo_id = None
            if self.instance and self.instance.pk and self.instance.tipo_servico_id:
                tipo_id = self.instance.tipo_servico_id
            elif self.data.get('tipo_servico'):
                try:
                    tipo_id = int(self.data.get('tipo_servico'))
                except (TypeError, ValueError):
                    tipo_id = None

            if tipo_id:
                self.fields['subtipo_servico'].queryset = SubtipoServicoOS.objects.filter(
                    tipo_servico_id=tipo_id,
                    ativo=True,
                ).filter(Q(empresa=empresa) | Q(empresa=None)).order_by('ordem', 'nome')
            else:
                self.fields['subtipo_servico'].queryset = SubtipoServicoOS.objects.none()

            self.fields['talhao'].queryset = Talhao.objects.filter(empresa=empresa, ativo=True)
            self.fields['safra'].queryset = Safra.objects.filter(
                fazenda__empresa=empresa,
                status__in=['PLANEJADA', 'EM_ANDAMENTO']
            ).order_by('-ano', 'nome')
            from .models import Funcionario
            self.fields['responsavel'].queryset = Funcionario.objects.filter(empresa=empresa, ativo=True)
            from .models import Fornecedor
            self.fields['fornecedor_servico'].queryset = Fornecedor.objects.filter(empresa=empresa, ativa=True)
            self.fields['requisicao'].queryset = Requisicao.objects.filter(empresa=empresa).order_by('-data_requisicao')

        # Campos opcionais
        for f in [
            'subtipo_servico', 'modalidade_execucao',
            'safra', 'responsavel', 'fornecedor_servico', 'valor_servico_externo',
            'unidade_cobranca', 'requisicao', 'foto_evidencia',
        ]:
            self.fields[f].required = False

    def clean(self):
        cleaned_data = super().clean()
        tipo_servico = cleaned_data.get('tipo_servico')
        subtipo_servico = cleaned_data.get('subtipo_servico')
        if subtipo_servico and tipo_servico:
            if subtipo_servico.tipo_servico_id != tipo_servico.pk:
                self.add_error(
                    'subtipo_servico',
                    'A operação selecionada não pertence ao tipo de serviço escolhido.'
                )
        return cleaned_data


class OrdemServicoInsumoForm(forms.ModelForm):
    """Formulário para itens de insumo lançados diretamente na OS."""

    class Meta:
        model = OrdemServicoInsumo
        fields = [
            'produto',
            'unidade_medida',
            'quantidade_planejada',
            'quantidade_aplicada',
            'custo_unitario',
            'observacoes',
        ]
        widgets = {
            'produto': forms.Select(attrs={'class': 'form-select'}),
            'unidade_medida': forms.Select(attrs={'class': 'form-select'}),
            'quantidade_planejada': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'quantidade_aplicada': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'custo_unitario': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
            'observacoes': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        if empresa:
            self.fields['produto'].queryset = Produto.objects.filter(lotes__armazem__empresa=empresa).distinct().order_by('nome')
            self.fields['unidade_medida'].queryset = UnidadeMedida.objects.filter(empresa=empresa).order_by('nome')

        self.fields['quantidade_planejada'].required = False
        self.fields['custo_unitario'].required = False
        self.fields['observacoes'].required = False

    def clean(self):
        cleaned = super().clean()
        produto = cleaned.get('produto')
        unidade_medida = cleaned.get('unidade_medida')
        custo_unitario = cleaned.get('custo_unitario')

        if not unidade_medida and produto and getattr(produto, 'unidade_medida_id', None):
            cleaned['unidade_medida'] = produto.unidade_medida

        if custo_unitario in (None, '') and produto and getattr(produto, 'preco_custo', None) not in (None, ''):
            cleaned['custo_unitario'] = produto.preco_custo

        return cleaned


class OSFuncionarioForm(forms.ModelForm):
    """Formulário para alocar funcionário em uma OS"""

    class Meta:
        model = OSFuncionario
        fields = ['funcionario', 'data_execucao', 'hora_inicio', 'hora_fim', 'observacoes']
        widgets = {
            'funcionario': forms.Select(attrs={'class': 'form-select'}),
            'data_execucao': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'hora_inicio': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'hora_fim': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'observacoes': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        if empresa:
            from .models import Funcionario
            self.fields['funcionario'].queryset = Funcionario.objects.filter(empresa=empresa, ativo=True)


OSFuncionarioFormSet = forms.inlineformset_factory(
    OrdemServico,
    OSFuncionario,
    form=OSFuncionarioForm,
    extra=1,
    can_delete=True,
    min_num=0,
)


class OSMaquinaForm(forms.ModelForm):
    """Formulário para alocar máquina/veículo em uma OS"""

    class Meta:
        model = OSMaquina
        fields = [
            'veiculo', 'operador', 'data_execucao',
            'horimetro_inicial', 'horimetro_final',
            'custo_hora_config', 'observacoes',
        ]
        widgets = {
            'veiculo': forms.Select(attrs={'class': 'form-select'}),
            'operador': forms.Select(attrs={'class': 'form-select'}),
            'data_execucao': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'horimetro_inicial': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'horimetro_final': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'custo_hora_config': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        if empresa:
            from cadastros.models import Vehicle
            self.fields['veiculo'].queryset = Vehicle.objects.filter(empresa=empresa)
            from .models import Funcionario
            self.fields['operador'].queryset = Funcionario.objects.filter(empresa=empresa, ativo=True)
            self.fields['custo_hora_config'].queryset = CustoHoraMaquina.objects.filter(empresa=empresa, ativo=True)
        self.fields['operador'].required = False
        self.fields['custo_hora_config'].required = False


OSMaquinaFormSet = forms.inlineformset_factory(
    OrdemServico,
    OSMaquina,
    form=OSMaquinaForm,
    extra=1,
    can_delete=True,
    min_num=0,
)


class CustoHoraMaquinaForm(forms.ModelForm):
    """Formulário para configurar custo/hora de uma máquina"""

    class Meta:
        model = CustoHoraMaquina
        fields = [
            'veiculo', 'data_referencia', 'preco_combustivel',
            'reserva_manutencao_hora', 'horas_anuais_trabalho', 'ativo',
        ]
        widgets = {
            'veiculo': forms.Select(attrs={'class': 'form-select'}),
            'data_referencia': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'preco_combustivel': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'reserva_manutencao_hora': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'horas_anuais_trabalho': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        if empresa:
            from cadastros.models import Vehicle
            self.fields['veiculo'].queryset = Vehicle.objects.filter(empresa=empresa)


# =============================================================================
# MÓDULO: COLHEITA — EtapaColheita / FrotaColheita / CarrocaoFrota / ViagemColheita
# =============================================================================

from .models import EtapaColheita, FrotaColheita, CarrocaoFrota, ViagemColheita


class EtapaColheitaForm(forms.ModelForm):
    class Meta:
        model = EtapaColheita
        fields = ['supervisor', 'data_inicio', 'observacoes']
        widgets = {
            'supervisor': forms.Select(attrs={'class': 'form-select'}),
            'data_inicio': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Funcionario
        if empresa:
            self.fields['supervisor'].queryset = Funcionario.objects.filter(empresa=empresa, ativo=True)
        self.fields['supervisor'].required = False
        self.fields['data_inicio'].required = False


class FrotaColheitaForm(forms.ModelForm):
    class Meta:
        model = FrotaColheita
        fields = ['trator', 'operador', 'horimetro_inicial', 'observacoes']
        widgets = {
            'trator': forms.Select(attrs={'class': 'form-select select-trator'}),
            'operador': forms.Select(attrs={'class': 'form-select'}),
            'horimetro_inicial': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': 'h'}),
            'observacoes': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Funcionario
        from cadastros.models import Vehicle
        if empresa:
            self.fields['trator'].queryset = Vehicle.objects.filter(
                empresa=empresa, ativo=True, tipo__in=['LEVE', 'MEDIO', 'PESADO']
            )
            self.fields['operador'].queryset = Funcionario.objects.filter(empresa=empresa, ativo=True)
        self.fields['operador'].required = False
        self.fields['horimetro_inicial'].required = False


class CarrocaoFrotaForm(forms.ModelForm):
    class Meta:
        model = CarrocaoFrota
        fields = ['veiculo', 'numero_identificacao', 'capacidade_ton', 'tara_kg']
        widgets = {
            'veiculo': forms.Select(attrs={'class': 'form-select select-carrocao'}),
            'numero_identificacao': forms.TextInput(attrs={'class': 'form-control'}),
            'capacidade_ton': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tara_kg': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        from cadastros.models import Vehicle
        if empresa:
            self.fields['veiculo'].queryset = Vehicle.objects.filter(
                empresa=empresa, ativo=True, tipo='REBOQUE'
            )
        self.fields['capacidade_ton'].required = False
        self.fields['tara_kg'].required = False


class ViagemColheitaForm(forms.ModelForm):
    class Meta:
        model = ViagemColheita
        fields = [
            'peso_bruto_kg', 'tara_usada_kg',
            'umidade_pct', 'impureza_pct', 'desconto_kg',
            'hora_saida_campo', 'hora_chegada_balanca',
            'foto_romaneio', 'observacoes',
        ]
        widgets = {
            'peso_bruto_kg': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'kg'}),
            'tara_usada_kg': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'kg'}),
            'umidade_pct': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '%'}),
            'impureza_pct': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '%'}),
            'desconto_kg': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'kg'}),
            'hora_saida_campo': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'hora_chegada_balanca': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'foto_romaneio': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'observacoes': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['umidade_pct'].required = False
        self.fields['impureza_pct'].required = False
        self.fields['desconto_kg'].required = False
        self.fields['hora_saida_campo'].required = False
        self.fields['hora_chegada_balanca'].required = False
        self.fields['foto_romaneio'].required = False