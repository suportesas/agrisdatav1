"""
Formulários do módulo Fazendas
Com validações e integração com APIs externas
"""

from django import forms
from django.urls import reverse_lazy
from core.widgets import Select2AjaxWidget, DateBRInput
from django.core.exceptions import ValidationError
from .models import (
    Fazenda, EnderecoFazenda, ContatoFazenda,
    ContaBancariaFazenda, DocumentoFazenda, NCM, EmpresaNCM, CFOP, EmpresaCFOP,
)

# Modelos de Cliente
from .models import (
    Cliente, EnderecoCliente, ContatoCliente, ContaBancariaCliente, DocumentoCliente, PrazoPagamentoPadrao
)

from rh.models import (
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
from .models import Safra, SafraCultura, SafraPlan, SafraReal, Requisicao, RequisicaoItem, Produtor
from mip.models import (
    EstagioDesenvolvimento, MonitoramentoMIP,
    PragaNoMonitoramento, PontoMonitoramento
)
from decimal import Decimal
from .models import Vendedor, ComissaoVendedor
from .models import AgenteExportacao

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
            'eori', 'ggn_numero', 'usar_como_supplier_etiqueta', 'regime_tributario',
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
            'ggn_numero': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número GGN (GLOBALG.A.P.)'
            }),
            'usar_como_supplier_etiqueta': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
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


class CFOPImportForm(forms.Form):
    """Form para upload de CSV de CFOP"""
    arquivo = forms.FileField(label='Arquivo CSV', help_text='CSV com colunas de código e nome')
    replace = forms.BooleanField(required=False, initial=False, label='Substituir templates não presentes')
    apply_to_all = forms.BooleanField(required=False, initial=False, label='Aplicar para todas as empresas (EmpresaCFOP)')
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
            'complemento', 'bairro', 'cidade', 'uf', 'codigo_municipio',
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
                'codigo_municipio': forms.TextInput(attrs={
                    'class': 'form-control',
                    'placeholder': '7 dígitos IBGE',
                    'maxlength': 7
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


PAIS_CHOICES = [
    ('', '— Selecione —'),
    ('1058', '1058 — Brasil'),
    ('1068', '1068 — Argentina'), ('1120', '1120 — Bolívia'), ('1589', '1589 — Chile'),
    ('1635', '1635 — Colômbia'), ('2143', '2143 — Equador'), ('4375', '4375 — Paraguai'),
    ('4391', '4391 — Peru'), ('5266', '5266 — Uruguai'), ('5290', '5290 — Venezuela'),
    ('1490', '1490 — Canadá'), ('4235', '4235 — Estados Unidos'), ('3700', '3700 — México'),
    ('3581', '3581 — Alemanha'), ('1040', '1040 — Áustria'), ('1074', '1074 — Bélgica'),
    ('2100', '2100 — Dinamarca'), ('4170', '4170 — Espanha'), ('1279', '1279 — Finlândia'),
    ('1155', '1155 — França'), ('3298', '3298 — Grécia'), ('4855', '4855 — Holanda'),
    ('3344', '3344 — Hungria'), ('3514', '3514 — Irlanda'), ('3735', '3735 — Itália'),
    ('4839', '4839 — Noruega'), ('4422', '4422 — Polônia'), ('4731', '4731 — Portugal'),
    ('4766', '4766 — Reino Unido'), ('2437', '2437 — República Tcheca'), ('4502', '4502 — Rússia'),
    ('4936', '4936 — Suécia'), ('4952', '4952 — Suíça'), ('5185', '5185 — Turquia'),
    ('4553', '4553 — Arábia Saudita'), ('1023', '1023 — Austrália'), ('1503', '1503 — China'),
    ('1694', '1694 — Coreia do Sul'), ('2127', '2127 — Emirados Árabes'), ('3395', '3395 — Índia'),
    ('3557', '3557 — Israel'), ('3549', '3549 — Japão'), ('4847', '4847 — Singapura'), ('4995', '4995 — Taiwan'),
    ('2186', '2186 — Egito'), ('3697', '3697 — Marrocos'), ('4804', '4804 — Nigéria'),
]


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
            'pais', 'codigo_pais', 'moeda_padrao', 'porto_destino', 'ppwr_responsavel',
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
            'codigo_pais': forms.Select(choices=PAIS_CHOICES, attrs={'class': 'form-select'}),
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
            'ppwr_responsavel': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Nome e endereço da entidade responsável pela embalagem (PPWR) no país deste importador',
            }),
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
        fields = ['tipo', 'cep', 'logradouro', 'numero', 'complemento', 'bairro', 'cidade', 'uf', 'codigo_municipio', 'pais', 'recebedor_notify', 'padrao']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'cep': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '00000-000', 'data-mask': 'cep'}),
            'logradouro': forms.TextInput(attrs={'class': 'form-control'}),
            'numero': forms.TextInput(attrs={'class': 'form-control'}),
            'complemento': forms.TextInput(attrs={'class': 'form-control'}),
            'bairro': forms.TextInput(attrs={'class': 'form-control'}),
            'cidade': forms.TextInput(attrs={'class': 'form-control'}),
            'uf': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_endereco_uf', 'maxlength': 2}),
            'codigo_municipio': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '7 dígitos IBGE', 'maxlength': 7}),
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
                            # Auto-fill código IBGE do município para NF-e
                            if data.get('ibge') and not self.data.get('codigo_municipio'):
                                self.data['codigo_municipio'] = data.get('ibge')
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
            'data_emissao': DateBRInput(format='%Y-%m-%d', attrs={'class': 'form-control'}),
            'data_validade': DateBRInput(format='%Y-%m-%d', attrs={'class': 'form-control'}),
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
            'data_emissao': DateBRInput(format='%Y-%m-%d', attrs={'class': 'form-control'}),
            'data_validade': DateBRInput(format='%Y-%m-%d', attrs={'class': 'form-control'}),
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
            'data_emissao': DateBRInput(format='%Y-%m-%d', attrs={'class': 'form-control'}),
            'data_validade': DateBRInput(format='%Y-%m-%d', attrs={'class': 'form-control'}),
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
            'data_homologacao': DateBRInput(attrs={'class': 'form-control'}),
            'validade_homologacao': DateBRInput(attrs={'class': 'form-control'}),
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

        # Só permite edição do campo portal_enabled para administradores da empresa
        if 'portal_enabled' in self.fields and usuario and not getattr(usuario, 'is_admin_empresa', lambda: False)():
            self.fields['portal_enabled'].disabled = True
            self.fields['portal_enabled'].help_text = 'Apenas administradores da empresa podem habilitar o portal do fornecedor.'

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
            from django.db.models import Q
            if 'portal_user' in self.fields:
                portal_user_id = self.instance.portal_user_id if self.instance.pk else None

                q = Q(is_active=True)
                if empresa:
                    q &= Q(empresa=empresa)
                # Garante que o usuário já vinculado sempre aparece no queryset, mesmo inativo.
                if portal_user_id:
                    q = q | Q(pk=portal_user_id)

                usuarios_qs = Usuario.objects.filter(q).order_by('first_name', 'last_name', 'username').distinct()
                self.fields['portal_user'].queryset = usuarios_qs
                self.fields['portal_user'].required = False
                self.fields['portal_user'].help_text = 'Selecione o usuário que fará login no portal deste fornecedor.'

                # Força a pré-seleção do usuário já vinculado ao fornecedor.
                if portal_user_id:
                    self.initial['portal_user'] = portal_user_id
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
        fields = ['tipo', 'cep', 'logradouro', 'numero', 'complemento', 'bairro', 'cidade', 'uf', 'codigo_municipio', 'pais', 'padrao']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'cep': forms.TextInput(attrs={'class': 'form-control'}),
            'logradouro': forms.TextInput(attrs={'class': 'form-control'}),
            'numero': forms.TextInput(attrs={'class': 'form-control'}),
            'complemento': forms.TextInput(attrs={'class': 'form-control'}),
            'bairro': forms.TextInput(attrs={'class': 'form-control'}),
            'cidade': forms.TextInput(attrs={'class': 'form-control'}),
            'uf': forms.TextInput(attrs={'class': 'form-control'}),
            'codigo_municipio': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '7 dígitos IBGE', 'maxlength': 7}),
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
            'exportacao_temperatura', 'exportacao_humidade', 'exportacao_ventilacao',
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
            'exportacao_temperatura': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1',
                'placeholder': '°C'
            }),
            'exportacao_humidade': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1',
                'placeholder': '%'
            }),
            'exportacao_ventilacao': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'cbm/h'
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
            'fazenda': Select2AjaxWidget(ajax_url=reverse_lazy('cadastros:ajax_buscar_fazendas'), placeholder='Buscar fazenda...'),
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
            'fazenda': Select2AjaxWidget(
                attrs={'onchange': 'carregarAreas(this.value)'},
                ajax_url=reverse_lazy('cadastros:ajax_buscar_fazendas'),
                placeholder='Buscar fazenda...',
            ),
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
    """Formulário para criar/editar `Safra` (período). As culturas cultivadas na safra
    são gerenciadas separadamente via `SafraCulturaFormSet`."""

    class Meta:
        model = Safra
        fields = ['nome', 'codigo', 'fazenda', 'ano', 'imagem']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'codigo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: 202526',
                'maxlength': '10',
            }),
            'fazenda': Select2AjaxWidget(ajax_url=reverse_lazy('cadastros:ajax_buscar_fazendas'), placeholder='Buscar fazenda...'),
            'ano': forms.NumberInput(attrs={'class': 'form-control'}),
            'imagem': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*', 'type': 'file'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if self.user and getattr(self.user, 'empresa', None):
            self.fields['fazenda'].queryset = Fazenda.objects.filter(empresa=self.user.empresa, ativa=True).order_by('nome')
        else:
            self.fields['fazenda'].queryset = Fazenda.objects.none()

    def clean(self):
        cleaned = super().clean()
        ano = cleaned.get('ano')
        fazenda = cleaned.get('fazenda')

        # Normaliza ano composto
        if ano and ano > 9999:
            try:
                ano_str = str(int(ano))
                ano = int(ano_str[:4])
                cleaned['ano'] = ano
            except Exception:
                pass

        # Valida unicidade do período por fazenda
        if fazenda and ano:
            qs = Safra.objects.filter(fazenda=fazenda, ano=ano)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError('Já existe uma safra para esta fazenda e ano')

        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
        return instance


class SafraCulturaForm(forms.ModelForm):
    """Formulário de uma linha de cultura dentro do formset de `Safra`"""

    class Meta:
        model = SafraCultura
        fields = ['cultura', 'periodo_inicio', 'periodo_fim', 'status', 'talhoes', 'paises_destino']
        widgets = {
            'cultura': forms.Select(attrs={'class': 'form-select'}),
            'periodo_inicio': DateBRInput(attrs={'class': 'form-control'}, format='%Y-%m-%d'),
            'periodo_fim': DateBRInput(attrs={'class': 'form-control'}, format='%Y-%m-%d'),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'talhoes': forms.SelectMultiple(attrs={'class': 'd-none'}),
            'paises_destino': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Ex: Argentina, Chile, União Europeia',
            }),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['status'].initial = 'PLANEJADA'
        self.fields['talhoes'].required = False
        if empresa:
            self.fields['cultura'].queryset = Cultura.objects.filter(empresa=empresa, ativa=True).order_by('nome')
            self.fields['talhoes'].queryset = Talhao.objects.filter(empresa=empresa, ativo=True).order_by('codigo')
        else:
            self.fields['cultura'].queryset = Cultura.objects.none()
            self.fields['talhoes'].queryset = Talhao.objects.none()

    def clean(self):
        cleaned = super().clean()
        inicio = cleaned.get('periodo_inicio')
        fim = cleaned.get('periodo_fim')
        if inicio and fim and inicio > fim:
            raise forms.ValidationError({'periodo_inicio': 'Data de início não pode ser posterior à data fim'})
        if inicio and fim and fim.year not in (inicio.year, inicio.year + 1):
            raise forms.ValidationError({'periodo_fim': 'Período inválido: o término deve estar no mesmo ano ou no ano seguinte ao início'})
        return cleaned


class BaseSafraCulturaFormSet(forms.BaseInlineFormSet):
    """Valida que um talhão não seja atribuído a uma cultura enquanto tiver um
    ciclo de cultivo em aberto (HistoricoTalhao sem colheita) em outra
    cultura/safra. Um talhão já colhido (ou nunca cultivado) pode ser
    livremente reatribuído a uma nova cultura, mesmo dentro da mesma safra."""

    def clean(self):
        super().clean()
        if any(self.errors):
            return

        culturas_validas = 0
        for form in self.forms:
            if not hasattr(form, 'cleaned_data') or form.cleaned_data.get('DELETE'):
                continue
            if form.cleaned_data.get('cultura'):
                culturas_validas += 1

            talhoes = form.cleaned_data.get('talhoes')
            if not talhoes:
                continue

            for talhao in talhoes:
                conflito_qs = HistoricoTalhao.objects.filter(
                    talhao=talhao, data_colheita__isnull=True
                )
                if form.instance.pk:
                    conflito_qs = conflito_qs.exclude(safra_cultura_id=form.instance.pk)
                conflito = conflito_qs.select_related('cultura', 'safra').first()
                if conflito:
                    detalhe = conflito.cultura.nome
                    if conflito.safra_id:
                        detalhe += f' ({conflito.safra})'
                    form.add_error(
                        'talhoes',
                        f'Talhão {talhao.codigo} já está em cultivo ativo de {detalhe}. '
                        'Aguarde a colheita para reatribuir a outra cultura.'
                    )

        if culturas_validas == 0:
            raise forms.ValidationError('Adicione ao menos uma cultura para esta safra.')


SafraCulturaFormSet = forms.inlineformset_factory(
    Safra, SafraCultura, form=SafraCulturaForm, formset=BaseSafraCulturaFormSet,
    extra=0, can_delete=True, min_num=0, validate_min=False,
)




class SafraPlanForm(forms.ModelForm):
    """Formulário para criar/editar Planejamento de Safra"""

    class Meta:
        model = SafraPlan
        fields = [
            'planned_area', 'planned_plantio', 'planned_colheita', 'planned_production',
            'produtividade_esperada', 'preco_meta_saca', 'custo_meta_ha',
        ]
        widgets = {
            'planned_area': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
            'planned_production': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'planned_plantio': DateBRInput(attrs={'class': 'form-control'}, format='%Y-%m-%d'),
            'planned_colheita': DateBRInput(attrs={'class': 'form-control'}, format='%Y-%m-%d'),
            'produtividade_esperada': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'preco_meta_saca': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'custo_meta_ha': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
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
            'fazenda': Select2AjaxWidget(attrs={'id': 'id_fazenda'}, ajax_url=reverse_lazy('cadastros:ajax_buscar_fazendas'), placeholder='Buscar fazenda...'),
            'talhao': Select2AjaxWidget(attrs={'id': 'id_talhao'}, ajax_url=reverse_lazy('cadastros:ajax_buscar_talhoes'), placeholder='Buscar talhão...'),
            'funcionario_destino': forms.Select(attrs={'class': 'form-select'}),
            'parceiro': forms.Select(attrs={'class': 'form-select'}),
            'produtor': forms.Select(attrs={'class': 'form-select'}),
            'direcao_emprestimo': forms.Select(attrs={'class': 'form-select'}),
            'recebedor_material': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome completo e documento (CPF/RG)'
            }),
            'data_promessa_devolucao': DateBRInput(attrs={'class': 'form-control'}),
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
            empresa = self.user.empresa
            self.fields['fazenda'].queryset = Fazenda.objects.filter(empresa=empresa, ativa=True).order_by('nome')
            self.fields['talhao'].queryset = Talhao.objects.filter(empresa=empresa, ativo=True).order_by('codigo')
            self.fields['safra'].queryset = Safra.objects.filter(fazenda__empresa=empresa).prefetch_related('culturas__cultura').order_by('-ano', 'nome')
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
            'produto': Select2AjaxWidget(ajax_url=reverse_lazy('produtos:ajax_buscar_produtos'), placeholder='Buscar produto...'),
            'unidade_medida': forms.Select(attrs={'class': 'form-select'}),
            'quantidade_solicitada': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'quantidade_atendida': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'custo_estimado': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        self.requisicao_tipo = kwargs.pop('requisicao_tipo', None)
        requisicao = kwargs.pop('requisicao', None)
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

            from decimal import Decimal
            from estoque.disponibilidade import reservas_por_produto
            requisicao_id = requisicao.id if requisicao else None
            reservas = reservas_por_produto(self.empresa, excluir_requisicao_id=requisicao_id)

            def _label(produto):
                disponivel = Decimal(produto.estoque_atual or 0) - reservas.get(produto.id, Decimal('0'))
                return f"{produto.nome} - Disponível: {disponivel}"

            self.fields['produto'].label_from_instance = _label

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
            'talhao', 'cultura', 'variedade', 'idiarn',
            'data_plantio', 'data_colheita',
            'producao_estimada', 'producao_real',
            'custo_total',
            'observacoes', 'problemas_enfrentados'
        ]
        widgets = {
            'talhao': forms.Select(attrs={'class': 'form-select'}),
            'cultura': forms.Select(attrs={'class': 'form-select'}),
            'variedade': forms.TextInput(attrs={'class': 'form-control'}),
            'idiarn': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: 24.003071.318.22.0064006'
            }),
            'data_plantio': DateBRInput(attrs={
                'class': 'form-control'
            }),
            'data_colheita': DateBRInput(attrs={
                'class': 'form-control'
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

        # IDIARN obrigatório para novos ciclos; registros antigos sem o dado
        # continuam editáveis sem forçar o preenchimento retroativo.
        if not self.instance.pk:
            self.fields['idiarn'].required = True

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
            'data_nascimento': DateBRInput(attrs={
                'class': 'form-control'
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
            'passaporte_validade': DateBRInput(attrs={
                'class': 'form-control'
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
            'data_admissao': DateBRInput(attrs={
                'class': 'form-control'
            }, format='%Y-%m-%d'),
            'data_desligamento': DateBRInput(attrs={
                'class': 'form-control'
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
            'referencia_mes': DateBRInput(attrs={
                'class': 'form-control'
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


class AgenteExportacaoForm(forms.ModelForm):
    """Formulário para cadastro de Agentes de Exportação (multi-tenant por `empresa`)"""

    class Meta:
        model = AgenteExportacao
        exclude = ('empresa', 'data_criacao', 'data_atualizacao')
        fields = ['tipo', 'nome', 'pais', 'cidade', 'endereco', 'contato_nome',
                  'contato_telefone', 'contato_email', 'documento_fiscal', 'ativo']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'pais': forms.TextInput(attrs={'class': 'form-control'}),
            'cidade': forms.TextInput(attrs={'class': 'form-control'}),
            'endereco': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'contato_nome': forms.TextInput(attrs={'class': 'form-control'}),
            'contato_telefone': forms.TextInput(attrs={'class': 'form-control'}),
            'contato_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'documento_fiscal': forms.TextInput(attrs={'class': 'form-control'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        self.empresa = empresa
        super().__init__(*args, **kwargs)

    def clean_nome(self):
        nome = self.cleaned_data.get('nome', '').strip()
        tipo = self.data.get('tipo') or getattr(self.instance, 'tipo', None)
        if not nome:
            raise ValidationError('Nome do agente é obrigatório')
        qs = AgenteExportacao.objects.filter(nome=nome, tipo=tipo)
        if self.empresa:
            qs = qs.filter(empresa=self.empresa)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('Já existe um agente com este nome e tipo para a mesma empresa')
        return nome

    def save(self, commit=True):
        agente = super().save(commit=False)
        if self.empresa:
            agente.empresa = self.empresa
        if commit:
            agente.save()
        return agente

# =============================================================================
# Forms: Veículos (Vehicle)
# =============================================================================

from frota.models import Vehicle, VehiclePlate


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
            'vigencia_inicio': DateBRInput(attrs={'class': 'form-control'}),
            'vigencia_fim': DateBRInput(attrs={'class': 'form-control'}),
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
            'data_monitoramento': DateBRInput(attrs={
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
            ).select_related('fazenda').order_by('-ano', 'nome')
            
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
        if not cultura and safra and safra.culturas.exists():
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
            }),
            'estagio_principal': forms.Select(attrs={'class': 'form-control'}),
            'detalhes_estagios': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
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

        # A view calcula incidencia_percentual; o campo é apenas informativo no form
        self.fields['incidencia_percentual'].required = False

        if self.empresa:
            self.fields['praga'].queryset = Praga.objects.filter(
                empresa=self.empresa,
                ativa=True
            )

        # On POST, use submitted praga to validate estagio_principal;
        # on GET, default to none() (JS cascading will populate the select).
        praga_id = (self.data.get('praga') if self.data else None) or (
            self.instance.praga_id if self.instance and self.instance.pk else None
        )
        if praga_id:
            self.fields['estagio_principal'].queryset = (
                EstagioDesenvolvimento.objects.filter(praga_id=praga_id, ativo=True)
            )
        else:
            self.fields['estagio_principal'].queryset = EstagioDesenvolvimento.objects.none()
    
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



# MÓDULO FROTA — FORMS
# ==============================================================

from frota.models import (
    AbastecimentoVeiculo, ManutencaoVeiculo, ManutencaoItem,
    PedagioVeiculo, TelemetriaVeiculo,
)
from .models import Viagem


class AbastecimentoVeiculoForm(forms.ModelForm):
    class Meta:
        model = AbastecimentoVeiculo
        fields = [
            'vehicle', 'motorista', 'data', 'tipo_combustivel',
            'litros', 'preco_por_litro', 'km_odometro', 'horimetro',
            'tanque_cheio', 'local_abastecimento', 'fornecedor', 'observacoes',
        ]
        widgets = {
            'vehicle': forms.Select(attrs={'class': 'form-select'}),
            'motorista': forms.Select(attrs={'class': 'form-select'}),
            'data': DateBRInput(attrs={'class': 'form-control'}),
            'tipo_combustivel': forms.Select(attrs={'class': 'form-select'}),
            'litros': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'preco_por_litro': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'km_odometro': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'horimetro': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'tanque_cheio': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'local_abastecimento': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do posto / local'}),
            'fornecedor': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        for f in ['motorista', 'km_odometro', 'horimetro', 'local_abastecimento', 'fornecedor', 'observacoes']:
            self.fields[f].required = False
        if self.user and self.user.empresa:
            emp = self.user.empresa
            self.fields['vehicle'].queryset = Vehicle.objects.filter(empresa=emp, ativo=True).order_by('descricao', 'modelo')
            from frota.models import Motorista
            self.fields['motorista'].queryset = Motorista.objects.filter(empresa=emp, ativo=True).order_by('nome')
            self.fields['fornecedor'].queryset = Fornecedor.objects.filter(empresa=emp, ativa=True).order_by('nome_fantasia', 'nome')


class ManutencaoVeiculoForm(forms.ModelForm):
    placa = forms.CharField(
        label='Placa', max_length=10, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control-plaintext', 'readonly': 'readonly'})
    )

    class Meta:
        model = ManutencaoVeiculo
        fields = [
            'vehicle', 'tipo', 'status', 'descricao', 'data_abertura', 'data_conclusao',
            'km_odometro', 'horimetro', 'proxima_data', 'proximo_km',
            'eh_oficina_propria', 'local_oficina', 'fornecedor_externo',
            'valor_servico', 'observacoes',
        ]
        widgets = {
            'vehicle': forms.Select(attrs={'class': 'form-select'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'descricao': forms.TextInput(attrs={'class': 'form-control'}),
            'data_abertura': DateBRInput(attrs={'class': 'form-control'}),
            'data_conclusao': DateBRInput(attrs={'class': 'form-control'}),
            'km_odometro': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'horimetro': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'proxima_data': DateBRInput(attrs={'class': 'form-control'}),
            'proximo_km': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'eh_oficina_propria': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'local_oficina': forms.Select(attrs={'class': 'form-select'}),
            'fornecedor_externo': forms.Select(attrs={'class': 'form-select'}),
            'valor_servico': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        optional = [
            'data_conclusao', 'km_odometro', 'horimetro', 'proxima_data', 'proximo_km',
            'local_oficina', 'fornecedor_externo', 'observacoes',
        ]
        for f in optional:
            self.fields[f].required = False
        # Preencher placa se há instância
        if self.instance and self.instance.pk:
            self.fields['placa'].initial = self.instance.placa_atual
        if self.user and self.user.empresa:
            emp = self.user.empresa
            self.fields['vehicle'].queryset = Vehicle.objects.filter(empresa=emp, ativo=True).order_by('descricao', 'modelo')
            self.fields['fornecedor_externo'].queryset = Fornecedor.objects.filter(empresa=emp, ativa=True).order_by('nome_fantasia', 'nome')
            from estoque.models import Armazem
            self.fields['local_oficina'].queryset = Armazem.objects.filter(empresa=emp)


class ManutencaoItemForm(forms.ModelForm):
    class Meta:
        model = ManutencaoItem
        fields = ['descricao', 'lote', 'quantidade', 'valor_unitario', 'valor_custo', 'nome_produto', 'unidade_medida', 'desconto']
        widgets = {
            'descricao': forms.HiddenInput(),
            'lote': forms.HiddenInput(),
            'quantidade': forms.NumberInput(attrs={'class': 'form-control quantidade-input', 'step': '0.001'}),
            'valor_unitario': forms.HiddenInput(),
            'valor_custo': forms.NumberInput(attrs={'class': 'form-control custo-input text-end', 'step': '0.0001', 'min': '0'}),
            'nome_produto': forms.TextInput(attrs={'class': 'form-control produto-search-input', 'placeholder': 'Buscar produto...', 'autocomplete': 'off'}),
            'unidade_medida': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '20'}),
            'desconto': forms.NumberInput(attrs={'class': 'form-control desconto-input', 'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['descricao'].required = False
        self.fields['lote'].required = False
        self.fields['valor_unitario'].required = False
        self.fields['valor_custo'].required = False
        self.fields['nome_produto'].required = False
        self.fields['unidade_medida'].required = False
        self.fields['desconto'].required = False
        if self.user and self.user.empresa:
            from estoque.models import Lote
            self.fields['lote'].queryset = Lote.objects.filter(
                empresa=self.user.empresa
            ).select_related('produto').order_by('produto__nome')

    def clean_valor_unitario(self):
        from decimal import Decimal
        v = self.cleaned_data.get('valor_unitario')
        if v is None:
            return self.cleaned_data.get('valor_custo') or Decimal('0')
        return v


class DocumentoManutencaoForm(forms.ModelForm):
    class Meta:
        from frota.models import DocumentoManutencao
        model = DocumentoManutencao
        fields = ['tipo', 'descricao', 'numero_documento', 'arquivo']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'descricao': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Descrição opcional'}),
            'numero_documento': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Ex: NF 001234'}),
            'arquivo': forms.FileInput(attrs={'class': 'form-control form-control-sm', 'accept': '.pdf,.jpg,.jpeg,.png,.doc,.docx'}),
        }

    def clean_arquivo(self):
        arquivo = self.cleaned_data.get('arquivo')
        if arquivo and arquivo.size > 10 * 1024 * 1024:
            raise ValidationError('Arquivo muito grande. Tamanho máximo: 10MB.')
        return arquivo


class PedagioVeiculoForm(forms.ModelForm):
    class Meta:
        model = PedagioVeiculo
        fields = ['vehicle', 'viagem', 'motorista', 'data', 'praca', 'valor', 'observacoes']
        widgets = {
            'vehicle': forms.Select(attrs={'class': 'form-select'}),
            'viagem': forms.Select(attrs={'class': 'form-select'}),
            'motorista': forms.Select(attrs={'class': 'form-select'}),
            'data': DateBRInput(attrs={'class': 'form-control'}),
            'praca': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Praça SP-270 km 45'}),
            'valor': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        for f in ['viagem', 'motorista', 'praca', 'observacoes']:
            self.fields[f].required = False
        if self.user and self.user.empresa:
            emp = self.user.empresa
            self.fields['vehicle'].queryset = Vehicle.objects.filter(empresa=emp, ativo=True).order_by('descricao', 'modelo')
            from frota.models import Motorista
            self.fields['motorista'].queryset = Motorista.objects.filter(empresa=emp, ativo=True).order_by('nome')
            self.fields['viagem'].queryset = Viagem.objects.filter(transportadora__empresa=emp).order_by('-data')


class TelemetriaVeiculoForm(forms.ModelForm):
    class Meta:
        model = TelemetriaVeiculo
        fields = ['vehicle', 'motorista', 'viagem', 'data_hora', 'latitude', 'longitude',
                  'local_descricao', 'velocidade_kmh', 'km_odometro', 'fonte', 'observacoes']
        widgets = {
            'vehicle': forms.Select(attrs={'class': 'form-select'}),
            'motorista': forms.Select(attrs={'class': 'form-select'}),
            'viagem': forms.Select(attrs={'class': 'form-select'}),
            'data_hora': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0000001'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0000001'}),
            'local_descricao': forms.TextInput(attrs={'class': 'form-control'}),
            'velocidade_kmh': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'km_odometro': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'fonte': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        for f in ['motorista', 'viagem', 'latitude', 'longitude', 'local_descricao',
                  'velocidade_kmh', 'km_odometro', 'observacoes']:
            self.fields[f].required = False
        if self.user and self.user.empresa:
            emp = self.user.empresa
            self.fields['vehicle'].queryset = Vehicle.objects.filter(empresa=emp, ativo=True).order_by('descricao', 'modelo')
            from frota.models import Motorista
            self.fields['motorista'].queryset = Motorista.objects.filter(empresa=emp, ativo=True).order_by('nome')
            self.fields['viagem'].queryset = Viagem.objects.filter(transportadora__empresa=emp).order_by('-data')


class ViagemFrotaForm(forms.ModelForm):
    class Meta:
        model = Viagem
        fields = ['transportadora', 'vehicle', 'motorista', 'origem', 'destino',
                  'data', 'valor_frete', 'km_inicial', 'km_final', 'status', 'observacoes']
        widgets = {
            'transportadora': forms.Select(attrs={'class': 'form-select'}),
            'vehicle': forms.Select(attrs={'class': 'form-select'}),
            'motorista': forms.Select(attrs={'class': 'form-select'}),
            'origem': forms.TextInput(attrs={'class': 'form-control'}),
            'destino': forms.TextInput(attrs={'class': 'form-control'}),
            'data': DateBRInput(attrs={'class': 'form-control'}),
            'valor_frete': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'km_inicial': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'km_final': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        for f in ['vehicle', 'motorista', 'valor_frete', 'km_inicial', 'km_final', 'observacoes']:
            self.fields[f].required = False
        if self.user and self.user.empresa:
            emp = self.user.empresa
            self.fields['transportadora'].queryset = Transportadora.objects.filter(empresa=emp, ativa=True).order_by('nome_fantasia', 'razao_social')
            self.fields['vehicle'].queryset = Vehicle.objects.filter(empresa=emp, ativo=True).order_by('descricao', 'modelo')
            from frota.models import Motorista
            self.fields['motorista'].queryset = Motorista.objects.filter(empresa=emp, ativo=True).order_by('nome')


class AbastecimentoImportForm(forms.Form):
    arquivo = forms.FileField(
        label='Arquivo CSV',
        widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.csv,.txt'}),
        help_text='Arquivo CSV com colunas: vehicle_placa, data, tipo_combustivel, litros, preco_por_litro, km_odometro, tanque_cheio, local'
    )


class MotoristaLoginForm(forms.Form):
    matricula = forms.CharField(
        label='Matrícula',
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Sua matrícula', 'autofocus': True}),
    )
    pin = forms.CharField(
        label='PIN',
        max_length=20,
        widget=forms.PasswordInput(attrs={'class': 'form-control form-control-lg', 'placeholder': '••••••'}),
    )


class AbastecimentoPortalForm(forms.ModelForm):
    foto_bomba = forms.ImageField(
        label='Foto da Bomba',
        widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*', 'capture': 'environment'}),
        required=True,
    )
    foto_odometro = forms.ImageField(
        label='Foto do Hodômetro',
        widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*', 'capture': 'environment'}),
        required=False,
    )

    class Meta:
        model = AbastecimentoVeiculo
        fields = ['vehicle', 'data', 'tipo_combustivel', 'litros', 'preco_por_litro',
                  'km_odometro', 'horimetro', 'tanque_cheio', 'local_abastecimento', 'observacoes']
        widgets = {
            'vehicle': forms.Select(attrs={'class': 'form-select form-select-lg'}),
            'data': DateBRInput(attrs={'class': 'form-control form-control-lg'}),
            'tipo_combustivel': forms.Select(attrs={'class': 'form-select form-select-lg'}),
            'litros': forms.NumberInput(attrs={'class': 'form-control form-control-lg', 'step': '0.001', 'min': '0'}),
            'preco_por_litro': forms.NumberInput(attrs={'class': 'form-control form-control-lg', 'step': '0.001', 'min': '0'}),
            'km_odometro': forms.NumberInput(attrs={'class': 'form-control form-control-lg', 'step': '0.1'}),
            'horimetro': forms.NumberInput(attrs={'class': 'form-control form-control-lg', 'step': '0.1'}),
            'tanque_cheio': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'local_abastecimento': forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Nome do posto'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        vehicles_qs = kwargs.pop('vehicles_qs', None)
        super().__init__(*args, **kwargs)
        for f in ['km_odometro', 'horimetro', 'local_abastecimento', 'observacoes']:
            self.fields[f].required = False
        if vehicles_qs is not None:
            self.fields['vehicle'].queryset = vehicles_qs
        elif self.empresa:
            self.fields['vehicle'].queryset = Vehicle.objects.filter(empresa=self.empresa, ativo=True).order_by('descricao', 'modelo')


class SolicitacaoManutencaoForm(forms.ModelForm):
    class Meta:
        model = ManutencaoVeiculo
        fields = ['vehicle', 'tipo', 'descricao', 'km_odometro', 'horimetro', 'observacoes']
        widgets = {
            'vehicle': forms.Select(attrs={'class': 'form-select form-select-lg'}),
            'tipo': forms.Select(attrs={'class': 'form-select form-select-lg'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Descreva o problema ou serviço necessário...'}),
            'km_odometro': forms.NumberInput(attrs={'class': 'form-control form-control-lg', 'step': '0.1'}),
            'horimetro': forms.NumberInput(attrs={'class': 'form-control form-control-lg', 'step': '0.1'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        vehicles_qs = kwargs.pop('vehicles_qs', None)
        super().__init__(*args, **kwargs)
        for f in ['km_odometro', 'horimetro', 'observacoes']:
            self.fields[f].required = False
        if vehicles_qs is not None:
            self.fields['vehicle'].queryset = vehicles_qs
        elif self.empresa:
            self.fields['vehicle'].queryset = Vehicle.objects.filter(empresa=self.empresa, ativo=True).order_by('descricao', 'modelo')


# ============================================
# POÇO / BOMBA DE IRRIGAÇÃO (RF-029, RF-106)
# ============================================

class PocoForm(forms.ModelForm):
    """Cadastro de poços e bombas de irrigação/fertirrigação."""

    class Meta:
        from .models import Poco
        model = Poco
        fields = [
            'fazenda', 'areas', 'nome', 'identificacao',
            'tipo_bomba', 'potencia_cv', 'profundidade_m', 'capacidade_m3_h',
            'horaletro_inicial', 'latitude', 'longitude',
            'data_instalacao', 'ativo', 'observacoes',
        ]
        widgets = {
            'fazenda': forms.Select(attrs={'class': 'form-select'}),
            'areas': forms.SelectMultiple(attrs={'class': 'form-select', 'size': '5'}),
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Poço Norte'}),
            'identificacao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: P-01'}),
            'tipo_bomba': forms.Select(attrs={'class': 'form-select'}),
            'potencia_cv': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'profundidade_m': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'capacidade_m3_h': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'horaletro_inicial': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0000001'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0000001'}),
            'data_instalacao': DateBRInput(attrs={'class': 'form-control'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        self.empresa = empresa
        super().__init__(*args, **kwargs)
        for field in ['potencia_cv', 'profundidade_m', 'capacidade_m3_h',
                      'latitude', 'longitude', 'data_instalacao', 'observacoes']:
            self.fields[field].required = False
        self.fields['areas'].required = False
        if self.empresa:
            self.fields['fazenda'].queryset = Fazenda.objects.filter(
                empresa=self.empresa, ativa=True
            ).order_by('nome')
            self.fields['areas'].queryset = Area.objects.filter(
                empresa=self.empresa, ativa=True
            ).order_by('fazenda__nome', 'nome')
