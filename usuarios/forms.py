"""
Formulários do app usuarios
Forms para autenticação e gerenciamento de usuários
"""

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, UserChangeForm
from django.core.exceptions import ValidationError
from .models import Usuario, PerfilUsuario


class LoginForm(AuthenticationForm):
    """
    Formulário de login customizado
    Adiciona campo de empresa (CNPJ) e validações específicas
    """
    
    username = forms.CharField(
        label='Usuário',
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Digite seu usuário',
            'autofocus': True
        })
    )
    
    password = forms.CharField(
        label='Senha',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Digite sua senha'
        })
    )
    
    remember_me = forms.BooleanField(
        label='Lembrar-me',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    class Meta:
        model = Usuario
        fields = ['username', 'password']


class UsuarioCreateForm(UserCreationForm):
    """
    Formulário para criar novo usuário
    Inclui validações e campos específicos do sistema
    """
    
    email = forms.EmailField(
        label='E-mail',
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'usuario@empresa.com'
        })
    )
    
    first_name = forms.CharField(
        label='Nome',
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nome'
        })
    )
    
    last_name = forms.CharField(
        label='Sobrenome',
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Sobrenome'
        })
    )
    
    telefone = forms.CharField(
        label='Telefone',
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '(84) 99999-9999',
            'data-mask': '(00) 00000-0000'
        })
    )
    
    cpf = forms.CharField(
        label='CPF',
        max_length=14,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '000.000.000-00',
            'data-mask': '000.000.000-00'
        })
    )
    
    password1 = forms.CharField(
        label='Senha',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mínimo 8 caracteres'
        })
    )
    
    password2 = forms.CharField(
        label='Confirmar Senha',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Digite a senha novamente'
        })
    )
    
    class Meta:
        model = Usuario
        fields = [
            'username', 'email', 'first_name', 'last_name',
            'tipo', 'telefone', 'cpf', 'empresa', 'roles',
            'password1', 'password2', 'is_active', 'is_staff'
        ]
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome de usuário único'
            }),
            'tipo': forms.Select(attrs={
                'class': 'form-select'
            }),
            'empresa': forms.Select(attrs={
                'class': 'form-select'
            }),
            'roles': forms.SelectMultiple(attrs={
                'class': 'form-select',
                'size': '10'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_staff': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)  # Usuário logado
        super().__init__(*args, **kwargs)
        
        # Se não for superusuário, limita escolha de empresa
        if self.user and not self.user.is_superuser:
            from empresas.models import Empresa
            if self.user.empresa:
                self.fields['empresa'].queryset = Empresa.objects.filter(id=self.user.empresa.id)
                self.fields['empresa'].initial = self.user.empresa
                self.fields['empresa'].disabled = True
            else:
                self.fields['empresa'].queryset = Empresa.objects.none()
        
        # Campos opcionais se não for superusuário
        if self.user and not self.user.is_superuser:
            self.fields['is_staff'].widget = forms.HiddenInput()
            self.fields['is_active'].initial = True

        # Tornar comissão opcional para quem não é vendedor
        tipo_val = None
        if self.data and self.data.get('tipo'):
            tipo_val = self.data.get('tipo')
        elif self.initial and self.initial.get('tipo'):
            tipo_val = self.initial.get('tipo')
        elif getattr(getattr(self, 'instance', None), 'tipo', None):
            tipo_val = self.instance.tipo

        if tipo_val != 'VENDEDOR' and 'comissao_vendas' in self.fields:
            # Não exigir comissão se não for vendedor
            self.fields['comissao_vendas'].required = False
            self.fields['comissao_vendas'].widget.attrs.update({'placeholder': 'Apenas para vendedores (opcional)'})

        # Configura queryset de roles
        from empresas.models import Role
        if 'roles' in self.fields:
            # PRIORIDADE 1: Se o usuário sendo CRIADO tem empresa, filtrar por ela
            if self.instance and self.instance.empresa:
                self.fields['roles'].queryset = Role.objects.filter(empresa=self.instance.empresa)
            # PRIORIDADE 2: Se quem está criando é admin de empresa, filtrar pela sua empresa
            elif self.user and not self.user.is_superuser and self.user.empresa:
                self.fields['roles'].queryset = Role.objects.filter(empresa=self.user.empresa)
            # PRIORIDADE 3: Caso contrário (superuser criando novo), mostrar todas
            else:
                self.fields['roles'].queryset = Role.objects.all()
    
    def clean_roles(self):
        """Valida que as roles selecionadas pertencem à empresa correta"""
        roles = self.cleaned_data.get('roles')
        
        # Se o usuário sendo criado tem empresa, valida contra ela
        if roles and self.instance and self.instance.empresa:
            invalid_roles = []
            for role in roles:
                if role.empresa != self.instance.empresa:
                    invalid_roles.append(role.name)
            
            if invalid_roles:
                raise ValidationError(
                    f'❌ Você não pode atribuir funções de outras empresas. '
                    f'Funções inválidas: {", ".join(invalid_roles)}'
                )
        # Senão, se quem está criando é admin de empresa, valida contra sua empresa
        elif roles and self.user and not self.user.is_superuser and self.user.empresa:
            invalid_roles = []
            for role in roles:
                if role.empresa != self.user.empresa:
                    invalid_roles.append(role.name)
            
            if invalid_roles:
                raise ValidationError(
                    f'❌ Você não pode atribuir funções de outras empresas. '
                    f'Funções inválidas: {", ".join(invalid_roles)}'
                )
        
        return roles
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if Usuario.objects.filter(email=email).exists():
            raise ValidationError('Este e-mail já está cadastrado.')
        return email
    
    def clean_cpf(self):
        cpf = self.cleaned_data.get('cpf')
        if cpf:
            # Remove formatação
            cpf = cpf.replace('.', '').replace('-', '')
            # Valida se existe
            if Usuario.objects.filter(cpf=cpf).exists():
                raise ValidationError('Este CPF já está cadastrado.')
        return cpf
    
    def save(self, commit=True):
        user = super().save(commit=False)
        
        # Define empresa se não for superusuário
        if self.user and not self.user.is_superuser and not user.empresa:
            user.empresa = self.user.empresa
        
        if commit:
            user.save()
        return user


class UsuarioUpdateForm(UserChangeForm):
    """
    Formulário para editar usuário existente
    Não inclui senha (usar formulário específico)
    """
    
    password = None  # Remove campo de senha
    
    email = forms.EmailField(
        label='E-mail',
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control'
        })
    )
    
    first_name = forms.CharField(
        label='Nome',
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control'
        })
    )
    
    last_name = forms.CharField(
        label='Sobrenome',
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control'
        })
    )
    
    telefone = forms.CharField(
        label='Telefone',
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'data-mask': '(00) 00000-0000'
        })
    )
    
    data_nascimento = forms.DateField(
        label='Data de Nascimento',
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    data_admissao = forms.DateField(
        label='Data de Admissão',
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    observacoes = forms.CharField(
        label='Observações',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3
        })
    )
    
    class Meta:
        model = Usuario
        fields = [
            'username', 'email', 'first_name', 'last_name',
            'tipo', 'telefone', 'cpf', 'data_nascimento',
            'data_admissao', 'comissao_vendas', 'roles', 'observacoes',
            'is_active', 'is_staff'
        ]
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': True  # Não permite alterar username
            }),
            'tipo': forms.Select(attrs={
                'class': 'form-select'
            }),
            'cpf': forms.TextInput(attrs={
                'class': 'form-control',
                'data-mask': '000.000.000-00'
            }),
            'comissao_vendas': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'max': '100'
            }),
            'roles': forms.SelectMultiple(attrs={
                'class': 'form-select',
                'size': '10'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_staff': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Esconde campos de staff se não for superusuário
        if self.user and not self.user.is_superuser:
            self.fields['is_staff'].widget = forms.HiddenInput()

        # Tornar comissão opcional para quem não é vendedor
        tipo_val = None
        if self.data and self.data.get('tipo'):
            tipo_val = self.data.get('tipo')
        elif self.initial and self.initial.get('tipo'):
            tipo_val = self.initial.get('tipo')
        elif getattr(getattr(self, 'instance', None), 'tipo', None):
            tipo_val = self.instance.tipo

        if tipo_val != 'VENDEDOR' and 'comissao_vendas' in self.fields:
            self.fields['comissao_vendas'].required = False
            self.fields['comissao_vendas'].widget.attrs.update({'placeholder': 'Apenas para vendedores (opcional)'})

        # Configura queryset de roles
        from empresas.models import Role
        if 'roles' in self.fields:
            # PRIORIDADE 1: Se o usuário sendo EDITADO tem empresa, filtrar por ela
            if self.instance and self.instance.empresa:
                self.fields['roles'].queryset = Role.objects.filter(empresa=self.instance.empresa)
            # PRIORIDADE 2: Se quem está editando é admin de empresa, filtrar pela sua empresa
            elif self.user and not self.user.is_superuser and self.user.empresa:
                self.fields['roles'].queryset = Role.objects.filter(empresa=self.user.empresa)
            # PRIORIDADE 3: Caso contrário (superuser editando superuser), mostrar todas
            else:
                self.fields['roles'].queryset = Role.objects.all()
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        # Verifica se email já existe em outro usuário
        if Usuario.objects.exclude(pk=self.instance.pk).filter(email=email).exists():
            raise ValidationError('Este e-mail já está cadastrado em outro usuário.')
        return email
    
    def clean_roles(self):
        """Valida que as roles selecionadas pertencem à empresa correta"""
        roles = self.cleaned_data.get('roles')
        
        # Se o usuário sendo editado tem empresa, valida contra ela
        if roles and self.instance and self.instance.empresa:
            invalid_roles = []
            for role in roles:
                if role.empresa != self.instance.empresa:
                    invalid_roles.append(role.name)
            
            if invalid_roles:
                raise ValidationError(
                    f'❌ Você não pode atribuir funções de outras empresas. '
                    f'Funções inválidas: {", ".join(invalid_roles)}'
                )
        # Senão, se quem está editando é admin de empresa, valida contra sua empresa
        elif roles and self.user and not self.user.is_superuser and self.user.empresa:
            invalid_roles = []
            for role in roles:
                if role.empresa != self.user.empresa:
                    invalid_roles.append(role.name)
            
            if invalid_roles:
                raise ValidationError(
                    f'❌ Você não pode atribuir funções de outras empresas. '
                    f'Funções inválidas: {", ".join(invalid_roles)}'
                )
        
        return roles


class AlterarSenhaForm(forms.Form):
    """
    Formulário para usuário alterar própria senha
    """
    
    senha_atual = forms.CharField(
        label='Senha Atual',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Digite sua senha atual'
        })
    )
    
    nova_senha = forms.CharField(
        label='Nova Senha',
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mínimo 8 caracteres'
        })
    )
    
    confirmar_senha = forms.CharField(
        label='Confirmar Nova Senha',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Digite a nova senha novamente'
        })
    )
    
    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
    
    def clean_senha_atual(self):
        senha_atual = self.cleaned_data.get('senha_atual')
        if not self.user.check_password(senha_atual):
            raise ValidationError('Senha atual incorreta.')
        return senha_atual
    
    def clean(self):
        cleaned_data = super().clean()
        nova_senha = cleaned_data.get('nova_senha')
        confirmar_senha = cleaned_data.get('confirmar_senha')
        
        if nova_senha and confirmar_senha:
            if nova_senha != confirmar_senha:
                raise ValidationError('As senhas não coincidem.')
        
        return cleaned_data
    
    def save(self):
        self.user.set_password(self.cleaned_data['nova_senha'])
        self.user.save()
        return self.user


class PerfilUsuarioForm(forms.ModelForm):
    """
    Formulário para editar perfil estendido do usuário
    """
    
    class Meta:
        model = PerfilUsuario
        fields = [
            'cargo', 'departamento', 'endereco', 'cidade',
            'estado', 'cep', 'receber_email_vendas',
            'receber_email_estoque', 'receber_email_financeiro'
        ]
        widgets = {
            'cargo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Gerente de Produção'
            }),
            'departamento': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Produção'
            }),
            'endereco': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Rua, número, complemento'
            }),
            'cidade': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Cidade'
            }),
            'estado': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'UF',
                'maxlength': '2'
            }),
            'cep': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '00000-000',
                'data-mask': '00000-000'
            }),
            'receber_email_vendas': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'receber_email_estoque': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'receber_email_financeiro': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }