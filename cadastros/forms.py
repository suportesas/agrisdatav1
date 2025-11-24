"""
Formulários do módulo Fazendas
Com validações e integração com APIs externas
"""

from django import forms
from django.core.exceptions import ValidationError
from .models import (
    Fazenda, EnderecoFazenda, ContatoFazenda,
    ContaBancariaFazenda, DocumentoFazenda
)
import re


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
        
        # ✅ ADICIONA campo empresa como hidden (não editável)
        if self.empresa:
            self.initial['empresa'] = self.empresa
        
        # Remove campo empresa do formulário visível
        if 'empresa' in self.fields:
            self.fields['empresa'].widget = forms.HiddenInput()
            self.fields['empresa'].required = False
    
    def clean_cnpj_cpf(self):
        """Valida e limpa CNPJ/CPF"""
        cnpj_cpf = self.cleaned_data.get('cnpj_cpf', '')
        
        # Remove caracteres especiais
        cnpj_cpf_limpo = re.sub(r'\D', '', cnpj_cpf)
        
        # Valida tamanho
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
                fazenda.save()
            except Exception as e:
                print(f"Erro ao salvar fazenda: {e}")
                raise
        
        return fazenda


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
            'pais', 'padrao'
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
                'maxlength': 2,
                'style': 'text-transform: uppercase;'
            }),
            'pais': forms.TextInput(attrs={
                'class': 'form-control'
            }),
        }
    
    def clean_cep(self):
        """Remove formatação do CEP"""
        cep = self.cleaned_data.get('cep', '')
        return re.sub(r'\D', '', cep)
    
    def clean_uf(self):
        """Converte UF para maiúsculas"""
        uf = self.cleaned_data.get('uf', '')
        return uf.upper()


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
        fields = [
            'tipo', 'titulo', 'numero_documento',
            'arquivo', 'data_emissao', 'data_validade',
            'gerar_alerta_vencimento', 'dias_antecedencia_alerta',
            'observacoes'
        ]
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
            'data_emissao': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'data_validade': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'dias_antecedencia_alerta': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 365
            }),
            'observacoes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2
            }),
        }
    
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