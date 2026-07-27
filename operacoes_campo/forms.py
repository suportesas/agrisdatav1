"""
Formulários do módulo Operações de Campo
"""
from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.urls import reverse_lazy
from django.utils import timezone

from core.widgets import Select2AjaxWidget
from .models import (
    OrdemServico, OrdemServicoInsumo, OSFuncionario, OSMaquina, CustoHoraMaquina,
    EtapaColheita, FrotaColheita, CarrocaoFrota, ViagemColheita,
    RegistroPluviometria, InspecaoQualidadeCampo,
    RegistroCadernoCampo, RegistroCadernoCampoInsumo, RegistroCadernoCampoFuncionario,
    PlanejamentoCustoSafra, PlanejamentoCustoItem,
    PlanejamentoCustoItemIndireto, FormacaoPreco,
    TipoServicoOS, SubtipoServicoOS, ModalidadeExecucaoOS,
    OSTransplantio, OSReplantio,
)


class OrdemServicoForm(forms.ModelForm):
    """Formulário principal de criação/edição de OS"""

    class Meta:
        model = OrdemServico
        fields = [
            'tipo_servico', 'subtipo_servico', 'modalidade_execucao',
            'talhao', 'safra', 'safra_cultura', 'poco', 'responsavel', 'data_prevista',
            'area_executada_ha', 'numero_corte', 'fornecedor_servico', 'valor_servico_externo',
            'unidade_cobranca', 'requisicao', 'observacoes', 'foto_evidencia',
            'custo_estimado_mao_obra', 'custo_estimado_maquinario', 'custo_estimado_insumos',
        ]
        widgets = {
            'tipo_servico': forms.Select(attrs={'class': 'form-select', 'id': 'id_tipo_servico'}),
            'subtipo_servico': forms.Select(attrs={'class': 'form-select', 'id': 'id_subtipo_servico'}),
            'modalidade_execucao': forms.Select(attrs={'class': 'form-select', 'id': 'id_modalidade_execucao'}),
            'talhao': Select2AjaxWidget(ajax_url=reverse_lazy('cadastros:ajax_buscar_talhoes'), placeholder='Buscar talhão...'),
            'safra': forms.Select(attrs={'class': 'form-select', 'id': 'id_safra'}),
            'safra_cultura': forms.Select(attrs={'class': 'form-select', 'id': 'id_safra_cultura'}),
            'poco': forms.Select(attrs={'class': 'form-select', 'id': 'id_poco'}),
            'responsavel': Select2AjaxWidget(ajax_url=reverse_lazy('rh:ajax_buscar_funcionarios'), placeholder='Buscar funcionário...'),
            'data_prevista': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'area_executada_ha': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001', 'placeholder': 'Ex: 2.5000'}),
            'numero_corte': forms.NumberInput(attrs={'class': 'form-control', 'step': '1', 'min': '1', 'placeholder': 'Ex: 1'}),
            'fornecedor_servico': Select2AjaxWidget(ajax_url=reverse_lazy('cadastros:ajax_buscar_fornecedores'), placeholder='Buscar fornecedor...'),
            'valor_servico_externo': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'unidade_cobranca': forms.Select(attrs={'class': 'form-select'}),
            'requisicao': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'foto_evidencia': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'custo_estimado_mao_obra': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'R$ 0,00'}),
            'custo_estimado_maquinario': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'R$ 0,00'}),
            'custo_estimado_insumos': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'R$ 0,00'}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        if empresa:
            self.fields['tipo_servico'].queryset = TipoServicoOS.objects.filter(
                Q(empresa=empresa) | Q(empresa=None), ativo=True
            ).order_by('ordem', 'nome')
            self.fields['modalidade_execucao'].queryset = ModalidadeExecucaoOS.objects.filter(
                Q(empresa=empresa) | Q(empresa=None), ativo=True
            ).order_by('ordem', 'nome')

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
                    tipo_servico_id=tipo_id, ativo=True
                ).filter(Q(empresa=empresa) | Q(empresa=None)).order_by('ordem', 'nome')
            else:
                self.fields['subtipo_servico'].queryset = SubtipoServicoOS.objects.none()

            from cadastros.models import Talhao, Safra, SafraCultura, Requisicao, Fornecedor
            self.fields['talhao'].queryset = Talhao.objects.filter(empresa=empresa, ativo=True).order_by('nome')
            self.fields['safra'].queryset = Safra.objects.filter(
                fazenda__empresa=empresa, culturas__status__in=['PLANEJADA', 'EM_ANDAMENTO']
            ).distinct().order_by('-ano', 'nome')

            safra_id = None
            if self.instance and self.instance.pk and self.instance.safra_id:
                safra_id = self.instance.safra_id
            elif self.data.get('safra'):
                try:
                    safra_id = int(self.data.get('safra'))
                except (TypeError, ValueError):
                    safra_id = None

            if safra_id:
                self.fields['safra_cultura'].queryset = SafraCultura.objects.filter(
                    safra_id=safra_id
                ).select_related('cultura').order_by('cultura__nome')
            else:
                self.fields['safra_cultura'].queryset = SafraCultura.objects.none()

            from rh.models import Funcionario
            self.fields['responsavel'].queryset = Funcionario.objects.filter(empresa=empresa, ativo=True).order_by('nome_completo')
            self.fields['fornecedor_servico'].queryset = Fornecedor.objects.filter(empresa=empresa, ativa=True).order_by('nome_fantasia', 'nome')
            self.fields['requisicao'].queryset = Requisicao.objects.filter(empresa=empresa).order_by('-data_requisicao')

            from cadastros.models import Poco
            self.fields['poco'].queryset = Poco.objects.filter(empresa=empresa, ativo=True).select_related('fazenda').order_by('fazenda__nome', 'identificacao')
            self.fields['poco'].label_from_instance = lambda obj: f"{obj.identificacao} — {obj.nome} ({obj.fazenda.nome})"

            # label_from_instance para melhor legibilidade
            self.fields['talhao'].label_from_instance = lambda obj: f"{obj.codigo} — {obj.nome} ({obj.fazenda.nome if obj.fazenda else '?'})"
            self.fields['responsavel'].label_from_instance = lambda obj: f"{obj.nome_completo} — {obj.funcao}"
            self.fields['safra'].label_from_instance = lambda obj: f"{obj.nome} ({obj.fazenda.nome if obj.fazenda else '?'})"

        for f in ['subtipo_servico', 'modalidade_execucao', 'safra', 'poco', 'numero_corte', 'responsavel',
                  'fornecedor_servico', 'valor_servico_externo', 'unidade_cobranca',
                  'requisicao', 'foto_evidencia',
                  'custo_estimado_mao_obra', 'custo_estimado_maquinario', 'custo_estimado_insumos']:
            self.fields[f].required = False

    def clean(self):
        cleaned_data = super().clean()
        tipo_servico = cleaned_data.get('tipo_servico')
        subtipo_servico = cleaned_data.get('subtipo_servico')
        if subtipo_servico and tipo_servico:
            if subtipo_servico.tipo_servico_id != tipo_servico.pk:
                self.add_error('subtipo_servico', 'A operação selecionada não pertence ao tipo de serviço escolhido.')
        fornecedor = cleaned_data.get('fornecedor_servico')
        valor = cleaned_data.get('valor_servico_externo')
        if fornecedor and not valor:
            self.add_error('valor_servico_externo', 'Informe o valor do serviço externo.')
        return cleaned_data


class OrdemServicoInsumoForm(forms.ModelForm):
    """Insumos lançados diretamente na OS"""

    class Meta:
        model = OrdemServicoInsumo
        fields = ['produto', 'unidade_medida', 'quantidade_planejada', 'quantidade_aplicada', 'custo_unitario', 'observacoes']
        widgets = {
            'produto': Select2AjaxWidget(ajax_url=reverse_lazy('produtos:ajax_buscar_produtos'), placeholder='Buscar produto...'),
            'unidade_medida': forms.Select(attrs={'class': 'form-select'}),
            'quantidade_planejada': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'quantidade_aplicada': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'custo_unitario': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
            'observacoes': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Observação opcional'}),
        }

    def __init__(self, *args, empresa=None, os=None, **kwargs):
        super().__init__(*args, **kwargs)
        if empresa:
            from produtos.models import Produto, UnidadeMedida
            self.fields['produto'].queryset = Produto.objects.filter(lotes__armazem__empresa=empresa).distinct().order_by('nome')
            self.fields['unidade_medida'].queryset = UnidadeMedida.objects.filter(empresa=empresa).order_by('nome')

            from decimal import Decimal
            from estoque.disponibilidade import reservas_por_produto
            os_id = os.id if os else None
            reservas = reservas_por_produto(empresa, excluir_os_id=os_id)

            def _label(produto):
                disponivel = Decimal(produto.estoque_atual or 0) - reservas.get(produto.id, Decimal('0'))
                return f"{produto.nome} - Disponível: {disponivel}"

            self.fields['produto'].label_from_instance = _label
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


class OSTransplantioForm(forms.ModelForm):
    """Dados de transplantio quando a OS é do tipo Plantio/subtipo Transplante."""

    class Meta:
        model = OSTransplantio
        fields = ['lote_muda', 'tipo', 'quantidade_transplantada']
        widgets = {
            'lote_muda': forms.Select(attrs={'class': 'form-select'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'quantidade_transplantada': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.required = False
        if empresa:
            from estufas.models import LoteMuda
            qs_lotes = LoteMuda.objects.filter(empresa=empresa, status='PRONTO').select_related('cultura', 'estufa')
            self.fields['lote_muda'].queryset = qs_lotes
            self.fields['lote_muda'].label_from_instance = lambda obj: (
                f"{obj.codigo_lote} — {obj.cultura.nome} ({obj.quantidade_disponivel} dispon.)"
            )

    def clean(self):
        cleaned = super().clean()
        lote_muda = cleaned.get('lote_muda')
        quantidade = cleaned.get('quantidade_transplantada')
        if lote_muda and quantidade and quantidade > lote_muda.quantidade_disponivel:
            self.add_error('quantidade_transplantada', f'Quantidade supera o disponível no lote ({lote_muda.quantidade_disponivel}).')
        return cleaned


class OSReplantioForm(forms.ModelForm):
    """Dados de replantio quando a OS é do tipo Plantio/subtipo Replantio."""

    class Meta:
        model = OSReplantio
        fields = ['quantidade', 'origem_muda', 'lote_muda', 'motivo_perda', 'custo_adicional']
        widgets = {
            'quantidade': forms.NumberInput(attrs={'class': 'form-control'}),
            'origem_muda': forms.Select(attrs={'class': 'form-select'}),
            'lote_muda': forms.Select(attrs={'class': 'form-select'}),
            'motivo_perda': forms.Select(attrs={'class': 'form-select'}),
            'custo_adicional': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.required = False
        if empresa:
            from estufas.models import LoteMuda
            self.fields['lote_muda'].queryset = LoteMuda.objects.filter(empresa=empresa).select_related('cultura')


class OSFuncionarioForm(forms.ModelForm):
    """Alocar funcionário em OS"""

    class Meta:
        model = OSFuncionario
        fields = ['funcionario', 'data_execucao', 'hora_inicio', 'hora_fim', 'observacoes']
        widgets = {
            'funcionario': Select2AjaxWidget(ajax_url=reverse_lazy('rh:ajax_buscar_funcionarios'), placeholder='Buscar funcionário...'),
            'data_execucao': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'hora_inicio': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'hora_fim': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'observacoes': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        if empresa:
            from rh.models import Funcionario
            self.fields['funcionario'].queryset = Funcionario.objects.filter(empresa=empresa, ativo=True).order_by('nome_completo')
            self.fields['funcionario'].label_from_instance = lambda obj: f"{obj.nome_completo} — {obj.funcao}"
        # Torna todos opcionais para que o formulário extra vazio (empty_permitted) não falhe quando
        # has_changed() retorna True por causa de None vs "" no widget Select.
        for f in self.fields.values():
            f.required = False

    def clean(self):
        cleaned = super().clean()
        funcionario = cleaned.get('funcionario')
        data_execucao = cleaned.get('data_execucao')
        hora_inicio = cleaned.get('hora_inicio')
        hora_fim = cleaned.get('hora_fim')
        # Só exige funcionário se qualquer campo da linha foi preenchido
        # Horários são opcionais: serão capturados automaticamente pelo portal (Iniciar/Pausar/Retomar)
        if any([funcionario, data_execucao, hora_inicio, hora_fim]):
            if not funcionario:
                self.add_error('funcionario', 'Informe o funcionário.')
        # Valida consistência de horário apenas quando ambos estão presentes
        if hora_inicio and hora_fim and hora_fim <= hora_inicio:
            self.add_error('hora_fim', 'Hora de término deve ser posterior à hora de início.')
        return cleaned


OSFuncionarioFormSet = forms.inlineformset_factory(
    OrdemServico, OSFuncionario, form=OSFuncionarioForm, extra=1, can_delete=True, min_num=0,
)


class OSMaquinaForm(forms.ModelForm):
    """Alocar máquina/veículo em OS"""

    class Meta:
        model = OSMaquina
        fields = ['veiculo', 'operador', 'data_execucao', 'horimetro_inicial', 'horimetro_final', 'custo_hora_config', 'observacoes']
        widgets = {
            'veiculo': Select2AjaxWidget(ajax_url=reverse_lazy('frota:ajax_buscar_veiculos'), placeholder='Buscar veículo...'),
            'operador': Select2AjaxWidget(ajax_url=reverse_lazy('rh:ajax_buscar_funcionarios'), placeholder='Buscar funcionário...'),
            'data_execucao': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'horimetro_inicial': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'h'}),
            'horimetro_final': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'h'}),
            'custo_hora_config': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        if empresa:
            from frota.models import Vehicle
            from rh.models import Funcionario
            self.fields['veiculo'].queryset = Vehicle.objects.filter(empresa=empresa, ativo=True).order_by('descricao', 'modelo')
            self.fields['operador'].queryset = Funcionario.objects.filter(empresa=empresa, ativo=True).order_by('nome_completo')
            self.fields['custo_hora_config'].queryset = CustoHoraMaquina.objects.filter(empresa=empresa, ativo=True).order_by('-data_referencia')
            self.fields['custo_hora_config'].label_from_instance = lambda obj: f"{obj.veiculo} — R$ {obj.custo_hora_calculado:.2f}/h ({obj.data_referencia})"
        # Torna todos opcionais — validação condicional no clean()
        for f in self.fields.values():
            f.required = False

    def clean(self):
        cleaned = super().clean()
        veiculo = cleaned.get('veiculo')
        data_execucao = cleaned.get('data_execucao')
        horimetro_inicial = cleaned.get('horimetro_inicial')
        horimetro_final = cleaned.get('horimetro_final')
        # Requer apenas veículo; data e horímetros são opcionais (podem vir do portal)
        if any([veiculo, data_execucao, horimetro_inicial, horimetro_final]):
            if not veiculo:
                self.add_error('veiculo', 'Informe o veículo/máquina.')
        # Horímetros são opcionais na criação; se ambos preenchidos, valida consistência
        if horimetro_inicial is not None and horimetro_final is not None:
            if horimetro_final < horimetro_inicial:
                self.add_error('horimetro_final', 'Horímetro final deve ser maior que o inicial.')
        return cleaned


OSMaquinaFormSet = forms.inlineformset_factory(
    OrdemServico, OSMaquina, form=OSMaquinaForm, extra=1, can_delete=True, min_num=0,
)


class CustoHoraMaquinaForm(forms.ModelForm):
    """Configurar custo/hora de máquina"""

    class Meta:
        model = CustoHoraMaquina
        fields = ['veiculo', 'data_referencia', 'preco_combustivel', 'reserva_manutencao_hora', 'horas_anuais_trabalho', 'ativo']
        widgets = {
            'veiculo': Select2AjaxWidget(ajax_url=reverse_lazy('frota:ajax_buscar_veiculos'), placeholder='Buscar veículo...'),
            'data_referencia': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'preco_combustivel': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'placeholder': 'R$/litro'}),
            'reserva_manutencao_hora': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'R$/h'}),
            'horas_anuais_trabalho': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'horas/ano'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        if empresa:
            from frota.models import Vehicle
            self.fields['veiculo'].queryset = Vehicle.objects.filter(empresa=empresa, ativo=True).order_by('descricao')


# ============================================================================
# COLHEITA
# ============================================================================

class EtapaColheitaForm(forms.ModelForm):
    class Meta:
        model = EtapaColheita
        fields = ['supervisor', 'data_inicio', 'observacoes']
        widgets = {
            'supervisor': Select2AjaxWidget(ajax_url=reverse_lazy('rh:ajax_buscar_funcionarios'), placeholder='Buscar funcionário...'),
            'data_inicio': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        if empresa:
            from rh.models import Funcionario
            qs = Funcionario.objects.filter(empresa=empresa, ativo=True)
            self.fields['supervisor'].queryset = qs
            self.fields['supervisor'].label_from_instance = lambda obj: f"{obj.nome_completo} — {obj.funcao}"
        self.fields['supervisor'].required = False
        self.fields['data_inicio'].required = False
        self.fields['observacoes'].required = False


class FrotaColheitaForm(forms.ModelForm):
    class Meta:
        model = FrotaColheita
        fields = ['trator', 'operador', 'horimetro_inicial', 'observacoes']
        widgets = {
            'trator': Select2AjaxWidget(
                ajax_url=reverse_lazy('frota:ajax_buscar_veiculos'),
                placeholder='Buscar veículo...',
                extra_params={'tipo': 'LEVE,MEDIO,PESADO'},
            ),
            'operador': Select2AjaxWidget(ajax_url=reverse_lazy('rh:ajax_buscar_funcionarios'), placeholder='Buscar funcionário...'),
            'horimetro_inicial': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': 'h'}),
            'observacoes': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        if empresa:
            from frota.models import Vehicle
            from rh.models import Funcionario
            self.fields['trator'].queryset = Vehicle.objects.filter(empresa=empresa, ativo=True, tipo__in=['LEVE', 'MEDIO', 'PESADO']).order_by('descricao')
            self.fields['operador'].queryset = Funcionario.objects.filter(empresa=empresa, ativo=True).order_by('nome_completo')
            self.fields['operador'].label_from_instance = lambda obj: f"{obj.nome_completo} ({obj.funcao})"
        self.fields['operador'].required = False
        self.fields['horimetro_inicial'].required = False
        self.fields['observacoes'].required = False


class CarrocaoFrotaForm(forms.ModelForm):
    class Meta:
        model = CarrocaoFrota
        fields = ['veiculo', 'numero_identificacao', 'capacidade_ton', 'tara_kg']
        widgets = {
            # Mantido como <select> nativo (não Select2AjaxWidget): a tela de
            # etapa_detalhe.html varre TODAS as <option> deste campo em JS pra
            # marcar carroções já em uso em outra viagem (marcarCarrocoesEmUso);
            # o widget AJAX só renderiza a opção selecionada, quebrando essa marcação.
            'veiculo': forms.Select(attrs={'class': 'form-select select-carrocao'}),
            'numero_identificacao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Carroção 03'}),
            'capacidade_ton': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'ton'}),
            'tara_kg': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'kg'}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        if empresa:
            from frota.models import Vehicle
            self.fields['veiculo'].queryset = Vehicle.objects.filter(empresa=empresa, ativo=True, tipo='REBOQUE').order_by('descricao')
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
            'peso_bruto_kg': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'kg bruto'}),
            'tara_usada_kg': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'kg tara'}),
            'umidade_pct': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '%'}),
            'impureza_pct': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '%'}),
            'desconto_kg': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'kg desconto'}),
            'hora_saida_campo': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'hora_chegada_balanca': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'foto_romaneio': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*,.pdf'}),
            'observacoes': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Observação opcional'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in ['umidade_pct', 'impureza_pct', 'desconto_kg', 'hora_saida_campo', 'hora_chegada_balanca', 'foto_romaneio', 'observacoes']:
            self.fields[f].required = False

    def clean(self):
        cleaned = super().clean()
        peso_bruto = cleaned.get('peso_bruto_kg')
        tara = cleaned.get('tara_usada_kg')
        if peso_bruto and tara and tara > peso_bruto:
            self.add_error('tara_usada_kg', 'Tara não pode ser maior que o peso bruto.')
        return cleaned


# ============================================================================
# PLUVIOMETRIA
# ============================================================================

class RegistroPluviometriaForm(forms.ModelForm):
    class Meta:
        model = RegistroPluviometria
        fields = ['fazenda', 'data', 'mm_chuva', 'tipo_registro', 'fonte', 'responsavel', 'observacoes']
        widgets = {
            'fazenda': Select2AjaxWidget(ajax_url=reverse_lazy('cadastros:ajax_buscar_fazendas'), placeholder='Buscar fazenda...'),
            'data': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'mm_chuva': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': 'Ex: 12.5 mm'}),
            'tipo_registro': forms.Select(attrs={'class': 'form-select'}),
            'fonte': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Pluviômetro Campo Sul'}),
            'responsavel': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['responsavel'].required = False
        self.fields['fonte'].required = False
        self.fields['observacoes'].required = False
        if self.user and self.user.empresa:
            from cadastros.models import Fazenda
            from usuarios.models import Usuario
            self.fields['fazenda'].queryset = Fazenda.objects.filter(empresa=self.user.empresa, ativa=True).order_by('nome')
            self.fields['responsavel'].queryset = Usuario.objects.filter(empresa=self.user.empresa, is_active=True).order_by('first_name', 'last_name')
            self.fields['fazenda'].label_from_instance = lambda obj: f"{obj.nome} ({obj.municipio})" if obj.municipio else obj.nome

    def clean_data(self):
        data = self.cleaned_data.get('data')
        if data and data > timezone.now().date():
            raise forms.ValidationError('A data não pode ser futura.')
        return data


# ============================================================================
# QUALIDADE DE CAMPO
# ============================================================================

class InspecaoQualidadeCampoForm(forms.ModelForm):
    class Meta:
        model = InspecaoQualidadeCampo
        fields = [
            'talhao', 'safra', 'data_inspecao', 'tipo_inspecao', 'responsavel',
            'estagio_cultura', 'brix', 'peso_medio_fruto_g', 'percentual_defeitos',
            'coloracao', 'resultado', 'previsao_colheita_dias', 'fotos', 'observacoes',
        ]
        widgets = {
            'talhao': Select2AjaxWidget(ajax_url=reverse_lazy('cadastros:ajax_buscar_talhoes'), placeholder='Buscar talhão...'),
            'safra': forms.Select(attrs={'class': 'form-select'}),
            'data_inspecao': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'tipo_inspecao': forms.Select(attrs={'class': 'form-select'}),
            'responsavel': Select2AjaxWidget(ajax_url=reverse_lazy('rh:ajax_buscar_funcionarios'), placeholder='Buscar funcionário...'),
            'estagio_cultura': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Floração, Frutificação'}),
            'brix': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': '°Bx'}),
            'peso_medio_fruto_g': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': 'g'}),
            'percentual_defeitos': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '%'}),
            'coloracao': forms.Select(attrs={'class': 'form-select'}),
            'resultado': forms.Select(attrs={'class': 'form-select'}),
            'previsao_colheita_dias': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'dias'}),
            'fotos': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        for f in ['safra', 'estagio_cultura', 'brix', 'peso_medio_fruto_g',
                  'percentual_defeitos', 'coloracao', 'previsao_colheita_dias', 'fotos', 'observacoes']:
            self.fields[f].required = False
        if self.user and self.user.empresa:
            from cadastros.models import Talhao, Safra
            from rh.models import Funcionario
            emp = self.user.empresa
            self.fields['talhao'].queryset = Talhao.objects.filter(empresa=emp, ativo=True).order_by('nome')
            self.fields['safra'].queryset = Safra.objects.filter(fazenda__empresa=emp).order_by('-ano', 'nome')
            self.fields['responsavel'].queryset = Funcionario.objects.filter(empresa=emp, ativo=True).order_by('nome_completo')
            self.fields['talhao'].label_from_instance = lambda obj: f"{obj.codigo} — {obj.nome}"
            self.fields['responsavel'].label_from_instance = lambda obj: f"{obj.nome_completo} — {obj.funcao}"

    def clean_data_inspecao(self):
        data = self.cleaned_data.get('data_inspecao')
        if data and data > timezone.now().date():
            raise forms.ValidationError('A data não pode ser futura.')
        return data


# ============================================================================
# CADERNO DE CAMPO
# ============================================================================

class RegistroCadernoCampoForm(forms.ModelForm):
    class Meta:
        model = RegistroCadernoCampo
        fields = [
            'talhao', 'safra', 'os', 'data_atividade', 'tipo_atividade', 'atividade',
            'temperatura', 'umidade', 'condicao_tempo', 'responsavel', 'observacoes', 'fotos',
        ]
        widgets = {
            'talhao': Select2AjaxWidget(ajax_url=reverse_lazy('cadastros:ajax_buscar_talhoes'), placeholder='Buscar talhão...'),
            'safra': forms.Select(attrs={'class': 'form-select'}),
            'os': forms.Select(attrs={'class': 'form-select'}),
            'data_atividade': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'tipo_atividade': forms.Select(attrs={'class': 'form-select'}),
            'atividade': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Descrição da atividade realizada'}),
            'temperatura': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': '°C'}),
            'umidade': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '%'}),
            'condicao_tempo': forms.Select(attrs={'class': 'form-select'}),
            'responsavel': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'fotos': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        for f in ['safra', 'os', 'temperatura', 'umidade', 'condicao_tempo', 'observacoes', 'fotos']:
            self.fields[f].required = False
        if self.user and self.user.empresa:
            from cadastros.models import Talhao, Safra
            from usuarios.models import Usuario
            emp = self.user.empresa
            self.fields['talhao'].queryset = Talhao.objects.filter(empresa=emp, ativo=True).order_by('nome')
            self.fields['safra'].queryset = Safra.objects.filter(fazenda__empresa=emp).order_by('-ano', 'nome')
            self.fields['os'].queryset = OrdemServico.objects.filter(empresa=emp).order_by('-data_cadastro')
            self.fields['responsavel'].queryset = Usuario.objects.filter(empresa=emp, is_active=True).order_by('first_name')
            self.fields['talhao'].label_from_instance = lambda obj: f"{obj.codigo} — {obj.nome}"
            self.fields['os'].label_from_instance = lambda obj: f"{obj.numero} — {obj.descricao_servico}"


class RegistroCadernoCampoInsumoForm(forms.ModelForm):
    class Meta:
        model = RegistroCadernoCampoInsumo
        fields = ['produto', 'quantidade', 'unidade_medida', 'receituario_numero', 'carencia_dias', 'observacoes']
        widgets = {
            'produto': Select2AjaxWidget(ajax_url=reverse_lazy('produtos:ajax_buscar_produtos'), placeholder='Buscar produto...'),
            'quantidade': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'unidade_medida': forms.Select(attrs={'class': 'form-select'}),
            'receituario_numero': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nº Receituário Agronômico'}),
            'carencia_dias': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'dias'}),
            'observacoes': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        if empresa:
            from produtos.models import Produto
            self.fields['produto'].queryset = Produto.objects.filter(categoria__empresa=empresa, ativo=True).order_by('nome')
        self.fields['receituario_numero'].required = False
        self.fields['carencia_dias'].required = False
        self.fields['observacoes'].required = False


class RegistroCadernoCampoFuncionarioForm(forms.ModelForm):
    class Meta:
        model = RegistroCadernoCampoFuncionario
        fields = ['funcionario', 'horas_trabalhadas']
        widgets = {
            'funcionario': Select2AjaxWidget(ajax_url=reverse_lazy('rh:ajax_buscar_funcionarios'), placeholder='Buscar funcionário...'),
            'horas_trabalhadas': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.25', 'placeholder': 'Ex: 8.0'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['horas_trabalhadas'].required = False
        if self.user and self.user.empresa:
            from rh.models import Funcionario
            self.fields['funcionario'].queryset = Funcionario.objects.filter(
                empresa=self.user.empresa, ativo=True
            ).order_by('nome_completo')
            self.fields['funcionario'].label_from_instance = lambda obj: f"{obj.nome_completo} ({obj.funcao})"


# ============================================================================
# PLANEJAMENTO DE CUSTO
# ============================================================================

class PlanejamentoCustoSafraForm(forms.ModelForm):
    class Meta:
        model = PlanejamentoCustoSafra
        fields = [
            'nome', 'cultura', 'safra', 'talhao', 'area_ha',
            'produtividade_esperada_ha', 'preco_venda_unitario', 'unidade_producao',
            'observacoes',
        ]
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Planejamento Tomate 2026'}),
            'cultura': forms.Select(attrs={'class': 'form-select'}),
            'safra': forms.Select(attrs={'class': 'form-select'}),
            # 'talhao' fica nativo de propósito: a tela tem cascata JS própria
            # cultura → safra → talhão (endpoint ajax_talhoes_planejamento_custo,
            # que também traz a área do talhão pra auto-preencher area_ha) —
            # o combobox genérico não filtra por safra e quebraria isso.
            'talhao': forms.Select(attrs={'class': 'form-select'}),
            'area_ha': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001', 'placeholder': 'Ex: 2.5000'}),
            'produtividade_esperada_ha': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001', 'placeholder': 'Ex: 60'}),
            'preco_venda_unitario': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'R$ 0,00'}),
            'unidade_producao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'sc, kg, t…'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['safra'].required = False
        self.fields['talhao'].required = False
        self.fields['observacoes'].required = False
        self.fields['produtividade_esperada_ha'].required = False
        self.fields['preco_venda_unitario'].required = False
        self.fields['unidade_producao'].required = False
        if self.user and self.user.empresa:
            from cadastros.models import Cultura, Safra, Talhao
            emp = self.user.empresa
            self.fields['cultura'].queryset = Cultura.objects.filter(empresa=emp).order_by('nome')

            cultura_ref = self.data.get('cultura') or self.initial.get('cultura')
            cultura_id = getattr(cultura_ref, 'pk', None) or (int(cultura_ref) if cultura_ref not in (None, '') else None)
            try:
                cultura_id = int(cultura_id) if cultura_id else None
            except (TypeError, ValueError):
                cultura_id = None

            if cultura_id:
                self.fields['safra'].queryset = Safra.objects.filter(
                    fazenda__empresa=emp, culturas__cultura_id=cultura_id
                ).distinct().order_by('-ano', 'nome')
            else:
                self.fields['safra'].queryset = Safra.objects.filter(fazenda__empresa=emp).order_by('-ano', 'nome')

            safra_ref = self.data.get('safra') or self.initial.get('safra')
            safra_id = getattr(safra_ref, 'pk', None) or (int(safra_ref) if safra_ref not in (None, '') else None)
            try:
                safra_id = int(safra_id) if safra_id else None
            except (TypeError, ValueError):
                safra_id = None

            if safra_id:
                self.fields['talhao'].queryset = Talhao.objects.filter(empresa=emp, ativo=True, culturas_safra__safra_id=safra_id).distinct().order_by('nome')
            elif cultura_id:
                self.fields['talhao'].queryset = Talhao.objects.filter(empresa=emp, ativo=True, culturas_safra__cultura_id=cultura_id).distinct().order_by('nome')
            else:
                self.fields['talhao'].queryset = Talhao.objects.filter(empresa=emp, ativo=True).order_by('nome')

            self.fields['talhao'].label_from_instance = lambda obj: f"{obj.codigo} — {obj.nome} ({obj.area_hac:.2f} ha)"


class PlanejamentoCustoItemForm(forms.ModelForm):
    class Meta:
        model = PlanejamentoCustoItem
        fields = [
            'tipo_servico', 'subtipo_servico', 'categoria',
            'produto', 'descricao', 'dose_por_ha', 'unidade_medida', 'custo_unitario', 'area_ha',
        ]
        widgets = {
            'tipo_servico': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'subtipo_servico': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'categoria': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'produto': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'descricao': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Descrição do item de custo'}),
            'dose_por_ha': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.0001', 'placeholder': 'Dose/ha'}),
            'unidade_medida': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'custo_unitario': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.0001', 'placeholder': 'R$/un'}),
            'area_ha': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.0001', 'placeholder': 'ha'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['tipo_servico'].required = False
        self.fields['subtipo_servico'].required = False
        self.fields['produto'].required = False
        self.fields['dose_por_ha'].required = False
        self.fields['unidade_medida'].required = False
        empresa = self.user.empresa if self.user and self.user.empresa else None
        if empresa:
            from produtos.models import Produto, UnidadeMedida
            self.fields['produto'].queryset = Produto.objects.filter(categoria__empresa=empresa, ativo=True).order_by('nome')
            self.fields['unidade_medida'].queryset = UnidadeMedida.objects.filter(empresa=empresa).order_by('sigla')
            self.fields['tipo_servico'].queryset = TipoServicoOS.objects.filter(
                Q(empresa=empresa) | Q(empresa=None), ativo=True
            ).order_by('ordem', 'nome')
            tipo_id = (
                self.data.get('tipo_servico')
                or getattr(self.instance, 'tipo_servico_id', None)
            )
            if tipo_id:
                self.fields['subtipo_servico'].queryset = SubtipoServicoOS.objects.filter(
                    tipo_servico_id=tipo_id, ativo=True
                ).order_by('ordem', 'nome')
            else:
                self.fields['subtipo_servico'].queryset = SubtipoServicoOS.objects.none()


class PlanejamentoCustoItemIndiretoForm(forms.ModelForm):
    class Meta:
        model = PlanejamentoCustoItemIndireto
        fields = ['tipo', 'descricao', 'valor_fixo', 'percentual_receita', 'inclui_no_total']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'descricao': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Ex: Embalagem caixa 20kg'}),
            'valor_fixo': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01', 'placeholder': 'R$ 0,00'}),
            'percentual_receita': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01', 'placeholder': '% da receita'}),
            'inclui_no_total': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['valor_fixo'].required = False
        self.fields['percentual_receita'].required = False

    def clean(self):
        cleaned_data = super().clean()
        valor_fixo = cleaned_data.get('valor_fixo')
        percentual = cleaned_data.get('percentual_receita')
        if not valor_fixo and not percentual:
            raise ValidationError('Informe o valor fixo (R$) ou o percentual da receita.')
        return cleaned_data


class FormacaoPrecoForm(forms.ModelForm):
    class Meta:
        model = FormacaoPreco
        fields = ['producao_prevista_total', 'pct_avaria_prevista', 'margem_desejada_pct', 'inclui_custos_indiretos']
        widgets = {
            'producao_prevista_total': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001', 'placeholder': 'Ex: 1200 sc'}),
            'pct_avaria_prevista': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100', 'placeholder': '0.00'}),
            'margem_desejada_pct': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'placeholder': '20.00'}),
            'inclui_custos_indiretos': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['producao_prevista_total'].required = False
        self.fields['pct_avaria_prevista'].required = False
