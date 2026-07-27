from django import forms
from core.widgets import DateBRInput
from .models import APIKey, ConfiguracaoPlataforma, Empresa, Plano, Role


class EmpresaForm(forms.ModelForm):
    """Formulário para criar/editar empresas"""
    
    buscar_cnpj = forms.BooleanField(
        required=False,
        initial=False,
        label='Buscar CNPJ',
        help_text='Preencher automaticamente via API ReceitaWS'
    )
    
    buscar_cep = forms.BooleanField(
        required=False,
        initial=False,
        label='Buscar CEP',
        help_text='Preencher automaticamente via API ViaCEP'
    )
    
    class Meta:
        model = Empresa
        fields = [
            'nome', 'razao_social', 'cnpj', 'telefone', 'email',
            'endereco', 'numero_endereco', 'complemento_endereco', 'bairro',
            'cidade', 'uf', 'cep', 'codigo_municipio', 'logo',
            'plano',  # Campo de plano
            'valor_mensalidade', 'dia_vencimento', 'data_expiracao',
            'ativa', 'bloqueada', 'bloqueada_ate', 'motivo_bloqueio',
        ]
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome Fantasia'}),
            'razao_social': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Razão Social completa'}),
            'cnpj': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '00.000.000/0000-00'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'endereco': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_endereco': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número'}),
            'complemento_endereco': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Sala, Bloco, etc.'}),
            'bairro': forms.TextInput(attrs={'class': 'form-control'}),
            'cidade': forms.TextInput(attrs={'class': 'form-control'}),
            'uf': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 2}),
            'cep': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '00000-000', 'id': 'id_cep'}),
            'codigo_municipio': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '7 dígitos — ex: 3550308', 'maxlength': 7}),
            'logo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'plano': forms.Select(attrs={'class': 'form-select'}),
            'valor_mensalidade': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'dia_vencimento': forms.NumberInput(attrs={'class': 'form-control'}),
            'data_expiracao': DateBRInput(attrs={'class': 'form-control'}),
            'bloqueada_ate': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'motivo_bloqueio': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class EmpresaFiscalForm(forms.ModelForm):
    """Dados fiscais da Empresa para emissão de NF-e (razão social, CNPJ, IE, endereço)."""

    class Meta:
        model = Empresa
        fields = [
            'nome',
            'razao_social',
            'cnpj',
            'inscricao_estadual',
            'endereco',
            'numero_endereco',
            'complemento_endereco',
            'bairro',
            'cidade',
            'uf',
            'cep',
            'codigo_municipio',
            'banco_nome',
            'banco_endereco',
            'banco_swift',
            'banco_iban',
            'banco_numero_conta',
            'banco_beneficiario_nome',
        ]
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome Fantasia'}),
            'razao_social': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Razão Social completa'}),
            'cnpj': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '00.000.000/0000-00'}),
            'inscricao_estadual': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 123456789.01-23'}),
            'endereco': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Rua / Avenida'}),
            'numero_endereco': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número'}),
            'complemento_endereco': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Sala, Bloco, etc.'}),
            'bairro': forms.TextInput(attrs={'class': 'form-control'}),
            'cidade': forms.TextInput(attrs={'class': 'form-control'}),
            'uf': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 2}),
            'cep': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '00000-000', 'id': 'id_empresa_cep'}),
            'codigo_municipio': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '7 dígitos — ex: 3550308', 'maxlength': 7}),
            'banco_nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Banco Cooperativo SICREDI'}),
            'banco_endereco': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Cidade — UF/País'}),
            'banco_swift': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: BCSIBRRS'}),
            'banco_iban': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: BR3801181521022070000636754C1'}),
            'banco_numero_conta': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ag. 0000 C/C 00000-0'}),
            'banco_beneficiario_nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Razão Social / CNPJ do beneficiário'}),
        }


class EmpresaLogoForm(forms.ModelForm):
    """Formulario simples para atualizar apenas a logo da empresa"""

    class Meta:
        model = Empresa
        fields = ['logo']
        widgets = {
            'logo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }


class EmpresaPreferenciasForm(forms.ModelForm):
    """Preferências operacionais da empresa (produtos, estoque, etc.)"""

    class Meta:
        model = Empresa
        fields = ['exibir_estoque_base']
        widgets = {
            'exibir_estoque_base': forms.RadioSelect(attrs={'class': 'form-check-input'}),
        }


class PlanoForm(forms.ModelForm):
    """Formulário para criar/editar planos"""
    
    class Meta:
        model = Plano
        fields = [
            'codigo', 'nome', 'icone', 'ordem', 'ativo',
            'valor_mensal', 'valor_anual', 'desconto_anual',
            'limite_fazendas', 'limite_usuarios', 'limite_talhoes', 'limite_produtos',
            'acesso_relatorios_avancados', 'acesso_api', 
            'acesso_app_mobile', 'acesso_suporte_prioritario',
            'descricao'
        ]
        widgets = {
            'codigo': forms.Select(attrs={'class': 'form-select'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'icone': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 10}),
            'ordem': forms.NumberInput(attrs={'class': 'form-control'}),
            'valor_mensal': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'valor_anual': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'desconto_anual': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'limite_fazendas': forms.NumberInput(attrs={'class': 'form-control'}),
            'limite_usuarios': forms.NumberInput(attrs={'class': 'form-control'}),
            'limite_talhoes': forms.NumberInput(attrs={'class': 'form-control'}),
            'limite_produtos': forms.NumberInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        help_texts = {
            'valor_anual': 'Deixe em branco para calcular automaticamente',
            'desconto_anual': 'Percentual de desconto para pagamento anual',
            'ordem': 'Ordem de exibição (menor = primeiro)',
        }


class RoleForm(forms.ModelForm):
    """Formulário básico para criar/editar Roles de empresa"""

    class Meta:
        model = Role
        fields = ['name', 'description']
        labels = {
            'name': 'Nome da Função',
            'description': 'Descrição (opcional)',
        }
        help_texts = {
            'name': 'Digite o nome da função (ex: Gerente de Compras, Supervisor de Estoque)',
            'description': 'Descreva as responsabilidades desta função',
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Gerente de Compras',
                'required': True,
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Descreva as responsabilidades e permissões desta função...',
            }),
        }
    
    def clean_name(self):
        """Valida e limpa o nome da função"""
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise forms.ValidationError('O nome da função é obrigatório.')
        if len(name) < 3:
            raise forms.ValidationError('O nome deve ter pelo menos 3 caracteres.')
        return name


class APIKeyForm(forms.ModelForm):
    """Formulário para criar chaves de API. A chave em si é gerada pelo servidor."""

    class Meta:
        model = APIKey
        fields = ['nome']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Integração Sistema X',
            }),
        }


class ConfiguracaoPlataformaForm(forms.ModelForm):
    """Token mestre de revenda (softhouse) da IntegraNotas — usado para criar
    automaticamente o emitente de cada empresa. Só acessível ao superusuário."""

    token_softhouse = forms.CharField(
        label='Token Softhouse IntegraNotas',
        required=False,
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Deixe em branco para manter o token atual',
                'autocomplete': 'new-password',
            },
            render_value=False,
        ),
        help_text='Deixe em branco para não alterar o token existente.',
    )

    class Meta:
        model = ConfiguracaoPlataforma
        fields = ['token_softhouse']

    def clean_token_softhouse(self):
        return self.cleaned_data.get('token_softhouse', '').strip()

    def save(self, commit=True):
        instance = super().save(commit=False)
        raw_token = self.cleaned_data.get('token_softhouse', '').strip()
        if raw_token:
            instance.set_token(raw_token)
        elif instance.pk:
            current = ConfiguracaoPlataforma.objects.filter(pk=instance.pk).values_list(
                'token_softhouse', flat=True
            ).first()
            instance.token_softhouse = current or ''
        if commit:
            instance.save()
        return instance