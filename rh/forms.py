"""
Formulários do módulo de Recursos Humanos
"""
import re
from django import forms
from django.core.exceptions import ValidationError
from django.urls import reverse_lazy
from django.utils import timezone
from django.forms import inlineformset_factory

from core.widgets import Select2AjaxWidget
from .models import (
    FuncaoFuncionario, CategoriaRiscoAmbiental, RiscoAmbientalCatalogo,
    RiscoAmbientalFuncao, VinculoContrato, Funcionario, DocumentoFuncionario,
    FeriasFuncionario, AfastamentoFuncionario, LaudoRisco,
    TipoExameASO, SolicitacaoASO, RescisaoContrato,
)


class FuncaoFuncionarioForm(forms.ModelForm):
    """Formulário para cadastro rápido de função"""

    riscos_fisicos = forms.CharField(
        label='Riscos Físicos', required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Um risco por linha. Ex.: Ruído acima de 85dB'}),
        help_text='Use 1 linha por risco: Agente | Intensidade | EPI. Intensidade: BAIXA, MEDIA ou ALTA.'
    )
    riscos_quimicos = forms.CharField(
        label='Riscos Químicos', required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Um risco por linha. Ex.: Poeira orgânica'}),
        help_text='Use 1 linha por risco: Agente | Intensidade | EPI. Intensidade: BAIXA, MEDIA ou ALTA.'
    )
    riscos_biologicos = forms.CharField(
        label='Riscos Biológicos', required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Um risco por linha. Ex.: Fungos ambientais'}),
        help_text='Use 1 linha por risco: Agente | Intensidade | EPI. Intensidade: BAIXA, MEDIA ou ALTA.'
    )
    riscos_ergonomicos = forms.CharField(
        label='Riscos Ergonômicos', required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Um risco por linha. Ex.: Movimentos repetitivos'}),
        help_text='Use 1 linha por risco: Agente | Intensidade | EPI. Intensidade: BAIXA, MEDIA ou ALTA.'
    )
    riscos_acidentes = forms.CharField(
        label='Riscos de Acidentes', required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Um risco por linha. Ex.: Queda de mesmo nível'}),
        help_text='Use 1 linha por risco: Agente | Intensidade | EPI. Intensidade: BAIXA, MEDIA ou ALTA.'
    )
    riscos_outros = forms.CharField(
        label='Outros Riscos', required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Um risco por linha. Ex.: Exposição a intempéries'}),
        help_text='Use 1 linha por risco: Agente | Intensidade | EPI. Intensidade: BAIXA, MEDIA ou ALTA.'
    )

    riscos_fisicos_catalogo = forms.ModelMultipleChoiceField(label='Selecionar Riscos Físicos (catálogo)', required=False, queryset=RiscoAmbientalCatalogo.objects.none(), widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': 5}))
    riscos_quimicos_catalogo = forms.ModelMultipleChoiceField(label='Selecionar Riscos Químicos (catálogo)', required=False, queryset=RiscoAmbientalCatalogo.objects.none(), widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': 5}))
    riscos_biologicos_catalogo = forms.ModelMultipleChoiceField(label='Selecionar Riscos Biológicos (catálogo)', required=False, queryset=RiscoAmbientalCatalogo.objects.none(), widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': 5}))
    riscos_ergonomicos_catalogo = forms.ModelMultipleChoiceField(label='Selecionar Riscos Ergonômicos (catálogo)', required=False, queryset=RiscoAmbientalCatalogo.objects.none(), widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': 5}))
    riscos_acidentes_catalogo = forms.ModelMultipleChoiceField(label='Selecionar Riscos de Acidentes (catálogo)', required=False, queryset=RiscoAmbientalCatalogo.objects.none(), widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': 5}))
    riscos_outros_catalogo = forms.ModelMultipleChoiceField(label='Selecionar Outros Riscos (catálogo)', required=False, queryset=RiscoAmbientalCatalogo.objects.none(), widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': 5}))

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
            'nome': 'Nome da Função/Cargo', 'descricao': 'Descrição das Atividades',
            'salario_base': 'Salário Base Sugerido (R$)', 'ativa': 'Função Ativa',
        }
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Motorista, Tratorista, Colhedor'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'salario_base': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'ativa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'possui_insalubridade': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_possui_insalubridade'}),
            'grau_insalubridade': forms.Select(attrs={'class': 'form-select', 'id': 'id_grau_insalubridade'}),
            'possui_periculosidade': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_possui_periculosidade'}),
            'percentual_periculosidade': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
            'requer_laudo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'validade_laudo': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'observacoes_risco': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        empresa_ref = self.empresa or getattr(self.instance, 'empresa', None)
        self._popular_queryset_catalogo(empresa_ref)
        if self.instance and self.instance.pk:
            self._popular_campos_risco_ambiental()

    def clean_nome(self):
        nome = self.cleaned_data.get('nome', '').strip()
        if not nome:
            raise forms.ValidationError('O nome da função é obrigatório.')
        if len(nome) < 3:
            raise forms.ValidationError('O nome deve ter pelo menos 3 caracteres.')
        return nome

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('possui_insalubridade') and not cleaned_data.get('grau_insalubridade'):
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
            for item in RiscoAmbientalCatalogo.objects.filter(empresa=self.instance.empresa, ativo=True).only('id', 'categoria_id', 'nome')
        }
        for risco in riscos:
            campo = self.MAPA_CAMPOS_CATEGORIA.get(risco.categoria.codigo)
            if campo:
                agrupado[campo].append(self._formatar_linha_risco(risco))
            campo_catalogo = self.MAPA_CAMPOS_CATALOGO.get(risco.categoria.codigo)
            if campo_catalogo:
                chave = (risco.categoria_id, (risco.agente_especifico or '').strip().upper())
                item_id = catalogo_map.get(chave)
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
                empresa=empresa, ativo=True, categoria__codigo=codigo_categoria, categoria__ativo=True,
            ).select_related('categoria').order_by('nome')

    def _salvar_riscos_ambientais(self, funcao, empresa):
        CategoriaRiscoAmbiental.criar_categorias_padrao_empresa(empresa)
        categorias = {c.codigo: c for c in CategoriaRiscoAmbiental.objects.filter(empresa=empresa, codigo__in=self.MAPA_CAMPOS_CATEGORIA.keys())}
        for codigo_categoria, campo_form in self.MAPA_CAMPOS_CATEGORIA.items():
            categoria = categorias.get(codigo_categoria)
            if not categoria:
                continue
            campo_catalogo = self.MAPA_CAMPOS_CATALOGO.get(codigo_categoria)
            riscos_catalogo = self.cleaned_data.get(campo_catalogo) if campo_catalogo else []
            texto_riscos = (self.cleaned_data.get(campo_form) or '').strip()
            riscos_linha = [l.strip() for l in texto_riscos.splitlines() if l.strip()]
            RiscoAmbientalFuncao.objects.filter(funcao=funcao, categoria=categoria).delete()
            riscos_normalizados = set()
            for item_catalogo in riscos_catalogo or []:
                agente = (item_catalogo.nome or '').strip()
                if not agente:
                    continue
                chave = agente.upper()
                if chave in riscos_normalizados:
                    continue
                riscos_normalizados.add(chave)
                RiscoAmbientalFuncao.objects.create(
                    empresa=empresa, funcao=funcao, categoria=categoria,
                    agente_especifico=agente,
                    intensidade=item_catalogo.intensidade_padrao or RiscoAmbientalFuncao.INTENSIDADE_MEDIA,
                    epi_obrigatorio=(item_catalogo.epi_padrao or '').strip(),
                    observacoes=(item_catalogo.observacoes or '').strip(), ativo=True,
                )
            for linha in riscos_linha:
                agente, intensidade, epi = self._parse_linha_risco(linha)
                if not agente:
                    continue
                chave = agente.upper()
                if chave in riscos_normalizados:
                    continue
                riscos_normalizados.add(chave)
                RiscoAmbientalFuncao.objects.create(empresa=empresa, funcao=funcao, categoria=categoria, agente_especifico=agente, intensidade=intensidade, epi_obrigatorio=epi, ativo=True)

    def _parse_linha_risco(self, linha):
        partes = [p.strip() for p in linha.split('|')]
        if len(partes) == 1:
            return partes[0], RiscoAmbientalFuncao.INTENSIDADE_MEDIA, ''
        agente = partes[0]
        intensidade_raw = (partes[1] if len(partes) > 1 else '').upper().strip()
        intensidade_map = {'BAIXA': RiscoAmbientalFuncao.INTENSIDADE_BAIXA, 'MEDIA': RiscoAmbientalFuncao.INTENSIDADE_MEDIA, 'MÉDIA': RiscoAmbientalFuncao.INTENSIDADE_MEDIA, 'ALTA': RiscoAmbientalFuncao.INTENSIDADE_ALTA}
        intensidade = intensidade_map.get(intensidade_raw, RiscoAmbientalFuncao.INTENSIDADE_MEDIA)
        epi = partes[2] if len(partes) > 2 else ''
        return agente, intensidade, epi

    def _formatar_linha_risco(self, risco):
        intensidade = risco.intensidade or RiscoAmbientalFuncao.INTENSIDADE_MEDIA
        epi = (risco.epi_obrigatorio or '').strip()
        if epi:
            return f'{risco.agente_especifico} | {intensidade} | {epi}'
        return f'{risco.agente_especifico} | {intensidade}'


class RiscoAmbientalCatalogoForm(forms.ModelForm):
    """Formulário do catálogo de riscos ambientais."""

    class Meta:
        model = RiscoAmbientalCatalogo
        fields = ['categoria', 'nome', 'intensidade_padrao', 'epi_padrao', 'observacoes', 'ativo']
        widgets = {
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex.: Ruído acima de 85dB'}),
            'intensidade_padrao': forms.Select(attrs={'class': 'form-select'}),
            'epi_padrao': forms.TextInput(attrs={'class': 'form-control'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        empresa_ref = self.empresa or getattr(self.instance, 'empresa', None)
        if empresa_ref:
            CategoriaRiscoAmbiental.criar_categorias_padrao_empresa(empresa_ref)
            self.fields['categoria'].queryset = CategoriaRiscoAmbiental.objects.filter(empresa=empresa_ref, ativo=True).order_by('nome')
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

    buscar_cep_funcionario = forms.BooleanField(required=False, initial=False, label='Buscar CEP')

    class Meta:
        model = Funcionario
        fields = [
            'fazenda', 'nome_completo', 'matricula', 'cpf', 'rg',
            'data_nascimento', 'genero', 'estado_civil',
            'telefone', 'celular', 'email',
            'cep', 'endereco', 'numero', 'complemento', 'bairro', 'cidade', 'uf',
            'funcao', 'tipo_contrato', 'data_admissao', 'data_demissao',
            'salario', 'ctps', 'pis', 'cnh', 'cnh_validade',
            'escolaridade', 'numero_crea',
            'banco', 'agencia', 'conta', 'tipo_conta', 'pix_habilitado', 'tipo_chave_pix', 'chave_pix',
            'contato_emergencia_nome', 'contato_emergencia_telefone', 'contato_emergencia_parentesco',
            'observacoes', 'foto', 'ativo'
        ]
        widgets = {
            'fazenda': Select2AjaxWidget(ajax_url=reverse_lazy('cadastros:ajax_buscar_fazendas'), placeholder='Buscar fazenda...'),
            'nome_completo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome completo do funcionário'}),
            'matricula': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: MAT-0001'}),
            'cpf': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '000.000.000-00', 'data-mask': 'cpf'}),
            'tipo_conta': forms.Select(attrs={'class': 'form-select'}),
            'rg': forms.TextInput(attrs={'class': 'form-control'}),
            'data_nascimento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'genero': forms.Select(attrs={'class': 'form-select'}),
            'estado_civil': forms.Select(attrs={'class': 'form-select'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(00) 0000-0000'}),
            'celular': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(00) 00000-0000'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'cnh': forms.TextInput(attrs={'class': 'form-control'}),
            'cnh_validade': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'escolaridade': forms.Select(attrs={'class': 'form-select'}),
            'numero_crea': forms.TextInput(attrs={'class': 'form-control'}),
            'cep': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '00000-000'}),
            'endereco': forms.TextInput(attrs={'class': 'form-control'}),
            'numero': forms.TextInput(attrs={'class': 'form-control'}),
            'complemento': forms.TextInput(attrs={'class': 'form-control'}),
            'bairro': forms.TextInput(attrs={'class': 'form-control'}),
            'cidade': forms.TextInput(attrs={'class': 'form-control'}),
            'uf': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 2}),
            'funcao': forms.Select(attrs={'class': 'form-select', 'id': 'id_funcao', 'size': '10'}),
            'tipo_contrato': forms.Select(attrs={'class': 'form-select'}),
            'data_admissao': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'data_demissao': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'salario': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'ctps': forms.TextInput(attrs={'class': 'form-control'}),
            'pis': forms.TextInput(attrs={'class': 'form-control'}),
            'banco': forms.TextInput(attrs={'class': 'form-control'}),
            'agencia': forms.TextInput(attrs={'class': 'form-control'}),
            'conta': forms.TextInput(attrs={'class': 'form-control'}),
            'contato_emergencia_nome': forms.TextInput(attrs={'class': 'form-control'}),
            'contato_emergencia_telefone': forms.TextInput(attrs={'class': 'form-control'}),
            'contato_emergencia_parentesco': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Mãe, Pai, Esposo(a)'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'foto': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }

    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        self.usuario = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)

        if self.empresa:
            from cadastros.models import Fazenda
            self.fields['fazenda'].queryset = Fazenda.objects.filter(empresa=self.empresa, ativa=True)
            self.fields['funcao'].queryset = FuncaoFuncionario.objects.filter(empresa=self.empresa, ativa=True)

        if self.instance and self.instance.pk:
            if self.instance.data_nascimento:
                self.fields['data_nascimento'].initial = self.instance.data_nascimento.strftime('%Y-%m-%d')
            if self.instance.data_admissao:
                self.fields['data_admissao'].initial = self.instance.data_admissao.strftime('%Y-%m-%d')
            if self.instance.data_demissao:
                self.fields['data_demissao'].initial = self.instance.data_demissao.strftime('%Y-%m-%d')

    def clean_cpf(self):
        cpf = self.cleaned_data.get('cpf', '')
        cpf_limpo = re.sub(r'\D', '', cpf)
        if len(cpf_limpo) != 11:
            raise ValidationError('CPF deve ter 11 dígitos')
        qs = Funcionario.objects.filter(cpf=cpf_limpo)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('Este CPF já está cadastrado')
        return cpf_limpo

    def clean_matricula(self):
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

    def clean(self):
        cleaned = super().clean()
        funcao = cleaned.get('funcao')
        if funcao and getattr(funcao, 'nome', '').lower().find('motorista') != -1:
            cnh = cleaned.get('cnh')
            cnh_validade = cleaned.get('cnh_validade')
            errors = {}
            if not cnh:
                errors['cnh'] = 'Motorista deve ter CNH registrada.'
            if not cnh_validade:
                errors['cnh_validade'] = 'Motorista deve ter validade da CNH registrada.'
            elif cnh_validade <= timezone.now().date():
                errors['cnh_validade'] = 'Validade da CNH deve ser uma data futura.'
            if errors:
                raise ValidationError(errors)
        return cleaned

    def save(self, commit=True):
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
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'titulo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Contrato de Trabalho, Certificado de Treinamento'}),
            'numero_documento': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Número CREA, Protocolo, etc.'}),
            'arquivo': forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.jpeg,.png,.doc,.docx,.xls,.xlsx'}),
            'data_emissao': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_validade': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'gerar_alerta_vencimento': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'dias_antecedencia_alerta': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '365'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


DocumentoFuncionarioFormSet = inlineformset_factory(
    Funcionario, DocumentoFuncionario,
    form=DocumentoFuncionarioForm,
    extra=1, can_delete=True, min_num=0, validate_min=False
)


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
            'funcionario': Select2AjaxWidget(ajax_url=reverse_lazy('rh:ajax_buscar_funcionarios'), placeholder='Buscar funcionário...'),
            'periodo_aquisitivo_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'periodo_aquisitivo_fim': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_fim': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'dias_ferias': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '30'}),
            'tipo_ferias': forms.Select(attrs={'class': 'form-select'}),
            'abono_pecuniario': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'dias_abono': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '10'}),
            'valor_ferias': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'valor_abono': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'data_pagamento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'recibo_ferias': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if self.empresa:
            self.fields['funcionario'].queryset = Funcionario.objects.filter(empresa=self.empresa, ativo=True).order_by('nome_completo')


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
            'funcionario': Select2AjaxWidget(ajax_url=reverse_lazy('rh:ajax_buscar_funcionarios'), placeholder='Buscar funcionário...'),
            'tipo_afastamento': forms.Select(attrs={'class': 'form-select'}),
            'data_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_prevista_retorno': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_retorno_efetivo': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'dias_afastamento': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'motivo': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'cid': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: M54.5'}),
            'numero_atestado': forms.TextInput(attrs={'class': 'form-control'}),
            'medico_responsavel': forms.TextInput(attrs={'class': 'form-control'}),
            'crm_medico': forms.TextInput(attrs={'class': 'form-control'}),
            'arquivo_atestado': forms.FileInput(attrs={'class': 'form-control'}),
            'e_acidente_trabalho': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'cat_emitida': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'numero_cat': forms.TextInput(attrs={'class': 'form-control'}),
            'arquivo_cat': forms.FileInput(attrs={'class': 'form-control'}),
            'requer_inss': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'numero_beneficio_inss': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if self.empresa:
            self.fields['funcionario'].queryset = Funcionario.objects.filter(empresa=self.empresa, ativo=True).order_by('nome_completo')


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
            'funcionario': Select2AjaxWidget(ajax_url=reverse_lazy('rh:ajax_buscar_funcionarios'), placeholder='Buscar funcionário...'),
            'funcao': forms.Select(attrs={'class': 'form-select'}),
            'matricula': forms.TextInput(attrs={'class': 'form-control'}),
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
            self.fields['funcionario'].queryset = Funcionario.objects.filter(empresa=self.empresa).order_by('nome_completo')
            self.fields['funcao'].queryset = FuncaoFuncionario.objects.filter(empresa=self.empresa, ativa=True).order_by('nome')

    def clean(self):
        cleaned_data = super().clean()
        funcionario = cleaned_data.get('funcionario')
        status = cleaned_data.get('status')
        data_inicio = cleaned_data.get('data_inicio')
        data_fim_prevista = cleaned_data.get('data_fim_prevista')
        if data_fim_prevista and data_inicio and data_fim_prevista < data_inicio:
            self.add_error('data_fim_prevista', 'Data fim prevista não pode ser menor que a data de início.')
        if funcionario and status == 'ATIVO':
            vinculos_ativos = VinculoContrato.objects.filter(empresa=self.empresa, funcionario=funcionario, status='ATIVO')
            if self.instance.pk:
                vinculos_ativos = vinculos_ativos.exclude(pk=self.instance.pk)
            if vinculos_ativos.exists():
                self.add_error('status', 'Este funcionário já possui um vínculo ATIVO.')
        return cleaned_data


class LaudoRiscoForm(forms.ModelForm):
    """Formulário para cadastro de laudos de risco ocupacional."""

    class Meta:
        model = LaudoRisco
        fields = ['funcao', 'vinculo', 'tipo_laudo', 'data_emissao', 'data_validade', 'responsavel_tecnico', 'numero_art', 'arquivo_laudo', 'status', 'observacoes']
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
            self.fields['funcao'].queryset = FuncaoFuncionario.objects.filter(empresa=self.empresa, ativa=True).order_by('nome')
            self.fields['vinculo'].queryset = VinculoContrato.objects.filter(empresa=self.empresa, status='ATIVO').select_related('funcionario', 'funcao').order_by('-data_inicio')
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
            'status', 'gerar_alerta_vencimento', 'dias_antecedencia_alerta', 'periodicidade_meses',
        ]
        widgets = {
            'funcionario': Select2AjaxWidget(ajax_url=reverse_lazy('rh:ajax_buscar_funcionarios'), placeholder='Buscar funcionário...'),
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
        for campo_data in ('data_solicitacao', 'data_prevista_exame', 'data_vencimento'):
            self.fields[campo_data].input_formats = ['%Y-%m-%d', '%d/%m/%Y']
        if self.instance and self.instance.pk:
            for campo_data in ('data_solicitacao', 'data_prevista_exame', 'data_vencimento'):
                valor = getattr(self.instance, campo_data, None)
                if valor:
                    self.initial[campo_data] = valor.strftime('%Y-%m-%d')
        if self.empresa:
            self.fields['funcionario'].queryset = Funcionario.objects.filter(empresa=self.empresa).order_by('nome_completo')
            self.fields['vinculo'].queryset = VinculoContrato.objects.filter(empresa=self.empresa).select_related('funcionario', 'funcao').order_by('-data_inicio')
            exames_qs = TipoExameASO.objects.filter(empresa=self.empresa, ativo=True).order_by('ordem', 'nome')
            if self.instance and self.instance.pk:
                exames_qs = (exames_qs | self.instance.exames.all()).distinct()
            self.fields['exames'].queryset = exames_qs

    def clean(self):
        cleaned_data = super().clean()
        funcionario = cleaned_data.get('funcionario')
        vinculo = cleaned_data.get('vinculo')
        tipo_aso = cleaned_data.get('tipo_aso')
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
        if tipo_aso == 'DEMISSIONAL' and cleaned_data.get('status') == 'CONCLUIDO':
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
            'funcionario': Select2AjaxWidget(ajax_url=reverse_lazy('rh:ajax_buscar_funcionarios'), placeholder='Buscar funcionário...'),
            'vinculo': forms.Select(attrs={'class': 'form-select'}),
            'tipo_rescisao': forms.Select(attrs={'class': 'form-select'}),
            'data_aviso': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_desligamento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'trabalhou_aviso_previo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'dias_aviso_previo': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'motivo_detalhado': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'saldo_salario': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'ferias_vencidas': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'ferias_proporcionais': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'decimo_terceiro_proporcional': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'aviso_previo_indenizado': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'multa_fgts': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'outros_valores': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'descontos': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'valor_liquido': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'readonly': 'readonly'}),
            'tem_direito_seguro_desemprego': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'liberar_fgts': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'exame_demissional_realizado': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'data_exame_demissional': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'trct_emitido': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'chave_conectividade_social': forms.TextInput(attrs={'class': 'form-control'}),
            'arquivo_trct': forms.FileInput(attrs={'class': 'form-control'}),
            'arquivo_exame': forms.FileInput(attrs={'class': 'form-control'}),
            'data_homologacao': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'local_homologacao': forms.TextInput(attrs={'class': 'form-control'}),
            'data_pagamento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'forma_pagamento': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if self.empresa:
            self.fields['funcionario'].queryset = Funcionario.objects.filter(empresa=self.empresa).order_by('nome_completo')
            self.fields['vinculo'].queryset = VinculoContrato.objects.filter(empresa=self.empresa).select_related('funcionario').order_by('-data_inicio')
            funcionario_id = None
            if self.is_bound:
                funcionario_id = self.data.get('funcionario')
            elif self.instance and self.instance.pk:
                funcionario_id = self.instance.funcionario_id
            if funcionario_id:
                self.fields['vinculo'].queryset = self.fields['vinculo'].queryset.filter(funcionario_id=funcionario_id)
            else:
                self.fields['vinculo'].queryset = self.fields['vinculo'].queryset.none()
        if self.instance and self.instance.pk:
            self.initial['valor_liquido'] = self.instance.calcular_valor_liquido()

    def clean(self):
        cleaned_data = super().clean()
        funcionario = cleaned_data.get('funcionario')
        vinculo = cleaned_data.get('vinculo')
        if vinculo and funcionario and vinculo.funcionario_id != funcionario.id:
            self.add_error('vinculo', 'O vínculo selecionado não pertence ao funcionário informado.')
        return cleaned_data
