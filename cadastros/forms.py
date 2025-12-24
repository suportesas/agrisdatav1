"""
Formulários do módulo Fazendas
Com validações e integração com APIs externas
"""

from django import forms
from django.core.exceptions import ValidationError
from .models import (
    Fazenda, EnderecoFazenda, ContatoFazenda,
    ContaBancariaFazenda, DocumentoFazenda,
)

from .models import Funcionario, FuncaoFuncionario
import re


from .models import Area, Talhao, HistoricoTalhao, Cultura, Vendedor, ComissaoVendedor
from .models import Safra, SafraPlan, SafraReal
from decimal import Decimal


from django.core.exceptions import ValidationError

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

        # Se for edição, preenche o campo area_agricultavel a partir
        # da soma das áreas relacionadas (area_plantavel) e exibe como
        # leitura somente para evitar inconsistências de edição manual.
        if self.instance and self.instance.pk:
            try:
                areas = self.instance.areas.all()
                soma = sum((a.area_plantavel or Decimal('0')) for a in areas)
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
                # Se for edição, sincroniza área agricultável com as áreas filhas
                if fazenda.pk:
                    try:
                        areas = fazenda.areas.all()
                        soma = sum((a.area_plantavel or Decimal('0')) for a in areas)
                        fazenda.area_agricultavel = soma.quantize(Decimal('0.01'))
                    except Exception:
                        pass

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
    



    """
ADICIONE ESTES FORMS AO FINAL DO ARQUIVO cadastros/forms.py
"""




class FuncaoFuncionarioForm(forms.ModelForm):
    """Formulário para cadastro rápido de função"""
    
    class Meta:
        model = FuncaoFuncionario
        fields = ['nome', 'descricao', 'salario_base', 'ativa']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Tratorista, Colhedor, Supervisor'
            }),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Descrição das atividades'
            }),
            'salario_base': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': '0.00'
            }),
        }


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
            'fazenda', 'nome_completo', 'cpf', 'rg',
            'data_nascimento', 'genero', 'estado_civil',
            'telefone', 'celular', 'email',
            'cep', 'endereco', 'numero', 'complemento',
            'bairro', 'cidade', 'uf',
            'funcao', 'tipo_contrato', 'data_admissao', 'data_demissao',
            'salario', 'ctps', 'pis',
            'banco', 'agencia', 'conta',
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
            'cpf': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '000.000.000-00',
                'data-mask': 'cpf'
            }),
            'rg': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'data_nascimento': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
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
                'id': 'id_funcao'
            }),
            'tipo_contrato': forms.Select(attrs={'class': 'form-select'}),
            'data_admissao': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'data_demissao': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
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
                'placeholder': 'Ex: Amarelo, Pele de Sapo'
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
                'placeholder': 'Plantas por hectare'
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





"""
ADICIONE ESTES FORMS AO ARQUIVO cadastros/forms.py
Forms com isolamento Multi-Tenant
"""




class AreaForm(forms.ModelForm):
    """
    Formulário para criar/editar áreas
    🔒 FILTRA FAZENDAS PELA EMPRESA DO USUÁRIO
    """
    
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
            'tipo_solo': forms.TextInput(attrs={'class': 'form-control'}),
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
        fields = ['nome', 'fazenda', 'cultura', 'ano', 'periodo_inicio', 'periodo_fim', 'status']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'fazenda': forms.Select(attrs={'class': 'form-select'}),
            'cultura': forms.Select(attrs={'class': 'form-select'}),
            'ano': forms.NumberInput(attrs={'class': 'form-control'}),
            'periodo_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'periodo_fim': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

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
        # Preenche nome padrão se não foi informado, usando `periodo_inicio` e `periodo_fim`.
        inicio = self.cleaned_data.get('periodo_inicio')
        fim = self.cleaned_data.get('periodo_fim')
        if not instance.nome:
            if inicio and fim:
                # Nome padrão: <inicio_year><fim_year_two_digits> -> 2025 + 26 => 202526
                instance.nome = f"{inicio.year}{fim.year % 100:02d}"
            elif inicio:
                instance.nome = str(inicio.year)

        if commit:
            instance.save()
            try:
                self.save_m2m()
            except Exception:
                pass

        return instance


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
SUBSTITUA TODO O CONTEÚDO das classes de Vendedor no cadastros/forms.py
por este código completo e corrigido.

CORREÇÕES FINAIS APLICADAS:
✅ Campos de data agora carregam valores ao editar (format='%Y-%m-%d')
✅ Campo supervisor mostra vendedores da empresa (verificado)
✅ Validação de telefone flexível (10-11 dígitos)
✅ Todos os widgets funcionando

COMO USAR:
1. Abra: cadastros/forms.py
2. Apague TODO o código das classes VendedorForm, ComissaoVendedorForm, VendedorFiltroForm
3. Cole este código completo no FINAL do arquivo
4. Salve
5. Reinicie o servidor
"""

import re
from django.core.exceptions import ValidationError


# ========================================================================
# FORMULÁRIOS DE VENDEDORES
# ========================================================================

class VendedorForm(forms.ModelForm):
    """
    Formulário para criar/editar vendedores
    Inclui validações e máscaras JavaScript
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
            # Comercial
            'comissao_mercado_interno', 'comissao_exportacao',
            'comissao_fixa_mensal', 'meta_mensal', 'moeda_padrao',
            'forma_pagamento_comissao', 'regioes_atuacao', 'paises_atuacao',
            # Bancário
            'banco', 'agencia', 'conta_corrente', 'tipo_conta', 'pix',
            # Documentação
            'passaporte_numero', 'passaporte_validade',
            'visto_trabalho', 'cnh', 'certificacoes',
            # Hierarquia
            'supervisor', 'nivel_autonomia', 'acesso_crm',
            # Administrativo
            'data_admissao', 'data_desligamento', 'status',
            # Observações
            'observacoes', 'idiomas', 'experiencia_anos',
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
                'data-mask': '000.000.000-00'
            }),
            'rg': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número do RG'
            }),
            # ✅ CORREÇÃO: formato especificado para carregar valor ao editar
            'data_nascimento': forms.DateInput(
                attrs={
                    'class': 'form-control',
                    'type': 'date'
                },
                format='%Y-%m-%d'
            ),
            'foto': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            
            # Tipo
            'tipo_mercado': forms.Select(attrs={'class': 'form-select'}),
            'tipo_vinculo': forms.Select(attrs={'class': 'form-select'}),
            
            # Contato (SEM validação de formato - aceita qualquer número)
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
                'placeholder': 'email@pessoal.com'
            }),
            'whatsapp': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '(84) 99999-9999'
            }),
            
            # Endereço
            'cep': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '00000-000',
                'data-mask': '00000-000'
            }),
            'logradouro': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Rua, Avenida, etc.'
            }),
            'numero': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nº'
            }),
            'complemento': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Apto, Sala, etc.'
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
                'placeholder': 'RN',
                'maxlength': '2',
                'style': 'text-transform: uppercase;'
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
                'max': '100',
                'placeholder': '0.00'
            }),
            'comissao_exportacao': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'max': '100',
                'placeholder': '0.00'
            }),
            'comissao_fixa_mensal': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            'meta_mensal': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            'moeda_padrao': forms.Select(attrs={'class': 'form-select'}),
            'forma_pagamento_comissao': forms.Select(attrs={'class': 'form-select'}),
            'regioes_atuacao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Ex: Norte, Nordeste, Centro-Oeste (separar por vírgula)'
            }),
            'paises_atuacao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Ex: USA, Europa, Ásia, América Latina (separar por vírgula)'
            }),
            
            # Bancário
            'banco': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome do Banco'
            }),
            'agencia': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '0000'
            }),
            'conta_corrente': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '00000-0'
            }),
            'tipo_conta': forms.Select(attrs={'class': 'form-select'}),
            'pix': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'CPF, E-mail, Telefone ou Chave Aleatória'
            }),
            
            # Documentação
            'passaporte_numero': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número do Passaporte'
            }),
            # ✅ CORREÇÃO: formato especificado para carregar valor ao editar
            'passaporte_validade': forms.DateInput(
                attrs={
                    'class': 'form-control',
                    'type': 'date'
                },
                format='%Y-%m-%d'
            ),
            'visto_trabalho': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número do Visto (se aplicável)'
            }),
            'cnh': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número da CNH'
            }),
            'certificacoes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Ex: SISCOMEX, Comércio Exterior, Exportação, etc.'
            }),
            
            # Hierarquia
            'supervisor': forms.Select(attrs={
                'class': 'form-select'
            }),
            'nivel_autonomia': forms.Select(attrs={'class': 'form-select'}),
            'acesso_crm': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            
            # Administrativo
            # ✅ CORREÇÃO: formato especificado para carregar valor ao editar
            'data_admissao': forms.DateInput(
                attrs={
                    'class': 'form-control',
                    'type': 'date'
                },
                format='%Y-%m-%d'
            ),
            'data_desligamento': forms.DateInput(
                attrs={
                    'class': 'form-control',
                    'type': 'date'
                },
                format='%Y-%m-%d'
            ),
            'status': forms.Select(attrs={'class': 'form-select'}),
            
            # Observações
            'observacoes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Informações adicionais sobre o vendedor'
            }),
            'idiomas': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Ex: Português (nativo), Inglês (fluente), Espanhol (intermediário)'
            }),
            'experiencia_anos': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': '0'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        
        # ✅ CORREÇÃO 1: Campo supervisor aceita "Nenhum"
        self.fields['supervisor'].required = False
        self.fields['supervisor'].empty_label = "--- Nenhum (Sem supervisor) ---"
        
        # ✅ CORREÇÃO 2: Filtra supervisores da mesma empresa
        if self.empresa:
            # Busca vendedores ATIVOS da mesma empresa
            queryset_supervisor = Vendedor.objects.filter(
                empresa=self.empresa,
                status='ATIVO'
            )
            
            # Se está editando, exclui o próprio vendedor (não pode ser supervisor de si mesmo)
            if self.instance and self.instance.pk:
                queryset_supervisor = queryset_supervisor.exclude(pk=self.instance.pk)
            
            self.fields['supervisor'].queryset = queryset_supervisor
            
            # ✅ DEBUG: Mostra quantos vendedores foram encontrados
            count = queryset_supervisor.count()
            print(f"DEBUG: Encontrados {count} vendedores para o dropdown supervisor (empresa: {self.empresa})")
        else:
            self.fields['supervisor'].queryset = Vendedor.objects.none()
            print("DEBUG: Empresa não definida - dropdown supervisor vazio")
        
        if 'empresa' in self.fields:
            del self.fields['empresa']
    
    def clean_cpf(self):
        """Valida CPF"""
        cpf = self.cleaned_data.get('cpf')
        if cpf:
            # Remove caracteres não numéricos
            cpf = re.sub(r'\D', '', cpf)
            
            if len(cpf) != 11:
                raise ValidationError('CPF deve ter 11 dígitos.')
            
            # Verifica unicidade por empresa
            if self.empresa:
                qs = Vendedor.objects.filter(empresa=self.empresa, cpf=cpf)
                if self.instance.pk:
                    qs = qs.exclude(pk=self.instance.pk)
                
                if qs.exists():
                    raise ValidationError('Já existe um vendedor com este CPF nesta empresa.')
        
        return cpf
    
    def clean_telefone_principal(self):
        """
        ✅ CORREÇÃO: Validação flexível de telefone
        Aceita qualquer formato de telefone brasileiro
        """
        telefone = self.cleaned_data.get('telefone_principal')
        if telefone:
            # Remove caracteres não numéricos
            apenas_numeros = re.sub(r'\D', '', telefone)
            
            # Telefone brasileiro deve ter entre 10 e 11 dígitos
            if len(apenas_numeros) < 10 or len(apenas_numeros) > 11:
                raise ValidationError(
                    'Telefone deve ter 10 dígitos (fixo) ou 11 dígitos (celular). '
                    f'Você digitou {len(apenas_numeros)} dígitos.'
                )
        
        return telefone
    
    def clean_email_corporativo(self):
        """Valida e-mail corporativo"""
        email = self.cleaned_data.get('email_corporativo')
        if email and self.empresa:
            qs = Vendedor.objects.filter(empresa=self.empresa, email_corporativo=email)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            
            if qs.exists():
                raise ValidationError('Já existe um vendedor com este e-mail nesta empresa.')
        
        return email
    
    def clean_data_desligamento(self):
        """Valida data de desligamento"""
        data_desligamento = self.cleaned_data.get('data_desligamento')
        data_admissao = self.cleaned_data.get('data_admissao')
        
        if data_desligamento and data_admissao:
            if data_desligamento < data_admissao:
                raise ValidationError(
                    'Data de desligamento não pode ser anterior à data de admissão.'
                )
        
        return data_desligamento
    
    def clean(self):
        """Validações gerais"""
        cleaned_data = super().clean()
        
        tipo_mercado = cleaned_data.get('tipo_mercado')
        passaporte_numero = cleaned_data.get('passaporte_numero')
        
        # Vendedores de exportação precisam de passaporte
        if tipo_mercado in ['EXTERNO', 'AMBOS']:
            if not passaporte_numero:
                self.add_error(
                    'passaporte_numero',
                    'Vendedores de exportação devem ter passaporte cadastrado.'
                )
        
        return cleaned_data
    
    def save(self, commit=True):
        vendedor = super().save(commit=False)
        
        if self.empresa and not vendedor.empresa_id:
            vendedor.empresa = self.empresa
        
        if self.user and not vendedor.pk:
            vendedor.criado_por = self.user
        
        if commit:
            vendedor.save()
        
        return vendedor


class ComissaoVendedorForm(forms.ModelForm):
    """Formulário para registrar comissões de vendedores"""
    
    class Meta:
        model = ComissaoVendedor
        fields = [
            'vendedor', 'referencia_mes', 'valor_base',
            'percentual', 'valor_comissao', 'status',
            'data_pagamento', 'observacoes'
        ]
        widgets = {
            'vendedor': forms.Select(attrs={'class': 'form-select'}),
            'referencia_mes': forms.DateInput(
                attrs={
                    'class': 'form-control',
                    'type': 'month'
                },
                format='%Y-%m'
            ),
            'valor_base': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': '0.00'
            }),
            'percentual': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': '0.00'
            }),
            'valor_comissao': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': '0.00',
                'readonly': True
            }),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'data_pagamento': forms.DateInput(
                attrs={
                    'class': 'form-control',
                    'type': 'date'
                },
                format='%Y-%m-%d'
            ),
            'observacoes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        
        if self.empresa:
            self.fields['vendedor'].queryset = Vendedor.objects.filter(
                empresa=self.empresa,
                status='ATIVO'
            )
        else:
            self.fields['vendedor'].queryset = Vendedor.objects.none()


class VendedorFiltroForm(forms.Form):
    """Formulário para filtrar vendedores na listagem"""
    
    STATUS_CHOICES = [('', 'Todos')] + list(Vendedor.STATUS_CHOICES)
    TIPO_MERCADO_CHOICES = [('', 'Todos')] + list(Vendedor.TIPO_MERCADO)
    
    busca = forms.CharField(
        label='Buscar',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nome, CPF ou E-mail'
        })
    )
    
    status = forms.ChoiceField(
        label='Status',
        required=False,
        choices=STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    tipo_mercado = forms.ChoiceField(
        label='Tipo de Mercado',
        required=False,
        choices=TIPO_MERCADO_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )




    """
========================================
CÓDIGO PARA ADICIONAR AO cadastros/forms.py
========================================

INSTRUÇÕES:
1. Abra o arquivo cadastros/forms.py
2. Vá até o FINAL do arquivo
3. Cole este código completo
4. Salve o arquivo
"""

# ============================================
# FORNECEDORES - FORMULÁRIOS
# ============================================

from .models import (
    Fornecedor, FornecedorEndereco, FornecedorContato,
    FornecedorDadoBancario, FornecedorDocumento, FornecedorAvaliacao,
    CategoriaFornecedor, SubcategoriaFornecedor
)


class FornecedorForm(forms.ModelForm):
    """Formulário principal do fornecedor"""
    
    class Meta:
        model = Fornecedor
        fields = [
            'tipo_pessoa', 'tipo_fornecedor', 'cnpj_cpf', 'codigo_fiscal_internacional',
            'razao_social', 'nome_fantasia',
            'inscricao_estadual', 'inscricao_municipal', 'eori', 'regime_tributario',
            'categorias', 'subcategorias',
            'status', 'classificacao_risco',
            'data_homologacao', 'validade_homologacao',
            'prazo_pagamento_padrao', 'prazo_entrega_medio',
            'pais_origem', 'moeda_padrao', 'incoterm_preferencial',
            'possui_certificacao_internacional',
            'telefone', 'email', 'website',
            'observacoes', 'motivo_bloqueio', 'ativo'
        ]
        widgets = {
            'tipo_pessoa': forms.Select(attrs={'class': 'form-select'}),
            'tipo_fornecedor': forms.Select(attrs={'class': 'form-select'}),
            'cnpj_cpf': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '00.000.000/0000-00 ou 000.000.000-00'}),
            'codigo_fiscal_internacional': forms.TextInput(attrs={'class': 'form-control'}),
            'razao_social': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Razão Social ou Nome Completo'}),
            'nome_fantasia': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome Fantasia (opcional)'}),
            'inscricao_estadual': forms.TextInput(attrs={'class': 'form-control'}),
            'inscricao_municipal': forms.TextInput(attrs={'class': 'form-control'}),
            'eori': forms.TextInput(attrs={'class': 'form-control'}),
            'regime_tributario': forms.Select(attrs={'class': 'form-select'}),
            'categorias': forms.SelectMultiple(attrs={'class': 'form-select', 'size': '5'}),
            'subcategorias': forms.SelectMultiple(attrs={'class': 'form-select', 'size': '5'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'classificacao_risco': forms.Select(attrs={'class': 'form-select'}),
            'data_homologacao': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'validade_homologacao': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'prazo_pagamento_padrao': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'prazo_entrega_medio': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'pais_origem': forms.TextInput(attrs={'class': 'form-control', 'value': 'Brasil'}),
            'moeda_padrao': forms.TextInput(attrs={'class': 'form-control', 'value': 'BRL'}),
            'incoterm_preferencial': forms.TextInput(attrs={'class': 'form-control'}),
            'possui_certificacao_internacional': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'motivo_bloqueio': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user and self.user.empresa:
            from django.db.models import Q
            self.fields['categorias'].queryset = CategoriaFornecedor.objects.filter(
                Q(empresa=self.user.empresa) | Q(empresa__isnull=True),
                ativa=True
            )
        
        if self.instance and self.instance.pk and self.instance.categorias.exists():
            cat_ids = self.instance.categorias.values_list('id', flat=True)
            self.fields['subcategorias'].queryset = SubcategoriaFornecedor.objects.filter(
                categoria_id__in=cat_ids, ativa=True
            )
    
    def clean_cnpj_cpf(self):
        import re
        cnpj_cpf = self.cleaned_data.get('cnpj_cpf')
        tipo_pessoa = self.cleaned_data.get('tipo_pessoa')
        tipo_fornecedor = self.cleaned_data.get('tipo_fornecedor')
        
        if not cnpj_cpf:
            raise ValidationError('CNPJ/CPF é obrigatório')
        
        numeros = re.sub(r'\D', '', cnpj_cpf)
        
        if tipo_fornecedor == 'NACIONAL':
            if tipo_pessoa == 'PJ' and len(numeros) != 14:
                raise ValidationError('CNPJ deve ter 14 dígitos')
            if tipo_pessoa == 'PF' and len(numeros) != 11:
                raise ValidationError('CPF deve ter 11 dígitos')
        
        qs = Fornecedor.objects.filter(empresa=self.user.empresa, cnpj_cpf=numeros)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('Já existe um fornecedor com este CNPJ/CPF')
        
        return numeros
    
    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        motivo_bloqueio = cleaned_data.get('motivo_bloqueio')
        
        if status == 'BLOQUEADO' and not motivo_bloqueio:
            raise ValidationError({'motivo_bloqueio': 'Motivo do bloqueio é obrigatório'})
        
        return cleaned_data
    
    def save(self, commit=True):
        fornecedor = super().save(commit=False)
        if not fornecedor.pk and self.user:
            fornecedor.empresa = self.user.empresa
            fornecedor.cadastrado_por = self.user
        if commit:
            fornecedor.save()
            self.save_m2m()
        return fornecedor


class FornecedorEnderecoForm(forms.ModelForm):
    """Formulário para endereços do fornecedor"""
    
    class Meta:
        model = FornecedorEndereco
        fields = ['tipo', 'cep', 'logradouro', 'numero', 'complemento', 'bairro', 'cidade', 'uf', 'pais', 'principal', 'ativo']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'cep': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '00000-000'}),
            'logradouro': forms.TextInput(attrs={'class': 'form-control'}),
            'numero': forms.TextInput(attrs={'class': 'form-control'}),
            'complemento': forms.TextInput(attrs={'class': 'form-control'}),
            'bairro': forms.TextInput(attrs={'class': 'form-control'}),
            'cidade': forms.TextInput(attrs={'class': 'form-control'}),
            'uf': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '2', 'style': 'text-transform: uppercase'}),
            'pais': forms.TextInput(attrs={'class': 'form-control', 'value': 'Brasil'}),
            'principal': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class FornecedorContatoForm(forms.ModelForm):
    """Formulário para contatos do fornecedor"""
    
    class Meta:
        model = FornecedorContato
        fields = ['nome', 'cargo', 'departamento', 'tipo', 'telefone', 'celular', 'email', 
                 'principal', 'recebe_cotacao', 'observacoes', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'cargo': forms.TextInput(attrs={'class': 'form-control'}),
            'departamento': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control'}),
            'celular': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'principal': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'recebe_cotacao': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class FornecedorDadoBancarioForm(forms.ModelForm):
    """Formulário para dados bancários"""
    
    class Meta:
        model = FornecedorDadoBancario
        fields = ['banco_codigo', 'banco_nome', 'agencia', 'conta', 'tipo_conta',
                 'pix_tipo', 'pix_chave', 'swift_bic', 'iban', 'principal']
        widgets = {
            'banco_codigo': forms.TextInput(attrs={'class': 'form-control'}),
            'banco_nome': forms.TextInput(attrs={'class': 'form-control'}),
            'agencia': forms.TextInput(attrs={'class': 'form-control'}),
            'conta': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo_conta': forms.Select(attrs={'class': 'form-select'}),
            'pix_tipo': forms.TextInput(attrs={'class': 'form-control'}),
            'pix_chave': forms.TextInput(attrs={'class': 'form-control'}),
            'swift_bic': forms.TextInput(attrs={'class': 'form-control'}),
            'iban': forms.TextInput(attrs={'class': 'form-control'}),
            'principal': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class FornecedorDocumentoForm(forms.ModelForm):
    """Formulário para documentos"""
    
    class Meta:
        model = FornecedorDocumento
        fields = ['tipo', 'titulo', 'descricao', 'arquivo', 'data_validade', 'obrigatorio', 'observacoes']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'arquivo': forms.FileInput(attrs={'class': 'form-control'}),
            'data_validade': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'obrigatorio': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class FornecedorAvaliacaoForm(forms.ModelForm):
    """Formulário para avaliações"""
    
    class Meta:
        model = FornecedorAvaliacao
        fields = [
            'tipo_avaliacao',
            'nota_qualidade', 'nota_prazo_entrega', 'nota_atendimento', 'nota_preco',
            'prazo_validade_ok', 'embalagem_ok', 'possui_etiqueta', 'dias_pedido_entrega',
            'pontos_fortes', 'pontos_melhoria', 'observacoes'
        ]
        widgets = {
            'tipo_avaliacao': forms.Select(attrs={'class': 'form-select'}),
            'nota_qualidade': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '10', 'step': '0.1'}),
            'nota_prazo_entrega': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '10', 'step': '0.1'}),
            'nota_atendimento': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '10', 'step': '0.1'}),
            'nota_preco': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '10', 'step': '0.1'}),
            'prazo_validade_ok': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'embalagem_ok': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'possui_etiqueta': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'dias_pedido_entrega': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'pontos_fortes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'pontos_melhoria': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class CategoriaFornecedorForm(forms.ModelForm):
    """Formulário para criar/editar categorias customizadas"""
    
    class Meta:
        model = CategoriaFornecedor
        fields = ['nome', 'descricao', 'icone', 'ordem', 'ativa']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'icone': forms.TextInput(attrs={'class': 'form-control'}),
            'ordem': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'ativa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class SubcategoriaFornecedorForm(forms.ModelForm):
    """Formulário para subcategorias"""
    
    class Meta:
        model = SubcategoriaFornecedor
        fields = ['categoria', 'nome', 'ativa']
        widgets = {
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'ativa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


"""
========================================
FIM DO CÓDIGO PARA ADICIONAR AO forms.py
========================================
"""