from django import forms
from core.widgets import DateBRInput
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal

from .models import (
    EstagioDesenvolvimento, MonitoramentoMIP,
    PragaNoMonitoramento, PontoMonitoramento,
)
from cadastros.models import Praga, Talhao, Safra, Cultura


class MonitoramentoMIPForm(forms.ModelForm):

    class Meta:
        model = MonitoramentoMIP
        fields = [
            'talhao', 'safra', 'cultura', 'os', 'data_monitoramento', 'tipo_monitoramento',
            'responsavel', 'quantidade_pontos',
            'condicoes_tempo', 'temperatura_media', 'umidade_media',
            'velocidade_vento_media', 'foto_area_geral',
            'observacoes_gerais'
        ]
        widgets = {
            'talhao': forms.Select(attrs={'class': 'form-control'}),
            'safra': forms.Select(attrs={'class': 'form-control'}),
            'cultura': forms.Select(attrs={'class': 'form-control'}),
            'os': forms.Select(attrs={'class': 'form-control'}),
            'data_monitoramento': DateBRInput(attrs={'class': 'form-control'}),
            'tipo_monitoramento': forms.Select(attrs={'class': 'form-control'}),
            'responsavel': forms.Select(attrs={'class': 'form-control'}),
            'quantidade_pontos': forms.NumberInput(attrs={'class': 'form-control', 'value': '20'}),
            'condicoes_tempo': forms.Select(attrs={'class': 'form-select'}),
            'temperatura_media': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': '°C'}),
            'umidade_media': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '100', 'placeholder': '%'}),
            'velocidade_vento_media': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': 'km/h'}),
            'foto_area_geral': forms.FileInput(attrs={'class': 'form-control'}),
            'observacoes_gerais': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)

        self.fields['condicoes_tempo'].required = False
        self.fields['os'].required = False

        valor_legado = (getattr(self.instance, 'condicoes_tempo', '') or '').strip() if self.instance else ''
        choices = [('', 'Selecione...')] + list(getattr(MonitoramentoMIP, 'CONDICOES_TEMPO_CHOICES', []))
        if valor_legado and valor_legado not in {codigo for codigo, _ in choices}:
            choices.append((valor_legado, f'Valor antigo: {valor_legado}'))
        self.fields['condicoes_tempo'].choices = choices

        if self.empresa:
            self.fields['talhao'].queryset = Talhao.objects.filter(
                area__fazenda__empresa=self.empresa,
                ativo=True
            ).select_related('area', 'fazenda').distinct().order_by('codigo')

            self.fields['talhao'].widget.attrs.update({'class': 'form-control form-select-lg'})

            self.fields['safra'].queryset = Safra.objects.filter(
                fazenda__empresa=self.empresa,
                culturas__status__in=['PLANEJADA', 'EM_ANDAMENTO']
            ).select_related('fazenda').prefetch_related('culturas__cultura').distinct().order_by('-ano', 'nome')

            self.fields['safra'].required = True

            self.fields['cultura'].queryset = Cultura.objects.filter(empresa=self.empresa)

            from operacoes_campo.models import OrdemServico
            self.fields['os'].queryset = OrdemServico.objects.filter(empresa=self.empresa).order_by('-data_cadastro')
            self.fields['os'].label_from_instance = lambda obj: f"{obj.numero} — {obj.descricao_servico}"

        if self.user:
            self.fields['responsavel'].initial = self.user.id
            self.fields['responsavel'].widget = forms.HiddenInput()

    def clean(self):
        cleaned = super().clean()
        dt = cleaned.get('data_monitoramento')
        if dt and dt > timezone.now().date():
            raise ValidationError('Data do monitoramento não pode ser no futuro')

        talhao = cleaned.get('talhao')
        safra = cleaned.get('safra')
        cultura = cleaned.get('cultura')

        if not cultura and safra and safra.culturas.exists():
            pass
        elif not cultura and talhao and talhao.cultura_atual:
            pass
        elif not cultura:
            raise ValidationError('Selecione uma cultura ou escolha um talhão/safra com cultura associada.')

        return cleaned


class PragaNoMonitoramentoForm(forms.ModelForm):

    class Meta:
        model = PragaNoMonitoramento
        fields = [
            'praga', 'quantidade_pontos_com_praga', 'incidencia_percentual',
            'estagio_principal', 'detalhes_estagios', 'severidade',
            'quantidade_total_pragas', 'ned_valor', 'observacoes'
        ]
        widgets = {
            'praga': forms.Select(attrs={'class': 'form-control'}),
            'quantidade_pontos_com_praga': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '20'}),
            'incidencia_percentual': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'readonly': 'readonly'}),
            'estagio_principal': forms.Select(attrs={'class': 'form-control'}),
            'detalhes_estagios': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'severidade': forms.RadioSelect(attrs={'class': 'form-check-input'}),
            'quantidade_total_pragas': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'ned_valor': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'value': '5.0'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        self.monitoramento = kwargs.pop('monitoramento', None)
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)

        self.fields['incidencia_percentual'].required = False

        if self.empresa:
            self.fields['praga'].queryset = Praga.objects.filter(empresa=self.empresa, ativa=True)

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
            raise ValidationError('Quantidade de pontos não pode exceder 20')
        if qty and qty < 0:
            raise ValidationError('Quantidade de pontos não pode ser negativa')

        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)

        if obj.quantidade_pontos_com_praga and self.monitoramento:
            obj.incidencia_percentual = (
                (obj.quantidade_pontos_com_praga /
                 self.monitoramento.quantidade_pontos) * 100
            )

        if obj.praga and self.monitoramento and obj.estagio_principal:
            try:
                from produtos.models import RecomendacaoDefensivo
                rec = RecomendacaoDefensivo.objects.filter(
                    empresa=self.monitoramento.empresa,
                    praga=obj.praga
                ).first()
                if rec:
                    obj.ned_valor = Decimal('5.0')
            except Exception:
                pass

        if commit:
            obj.save()
        return obj


class PontoMonitoramentoForm(forms.ModelForm):

    class Meta:
        model = PontoMonitoramento
        fields = [
            'numero_ponto', 'praga_presente', 'quantidade', 'estagio',
            'severidade', 'foto', 'observacoes', 'latitude', 'longitude'
        ]
        widgets = {
            'numero_ponto': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '20', 'readonly': 'readonly'}),
            'praga_presente': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'quantidade': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'estagio': forms.Select(attrs={'class': 'form-control'}),
            'severidade': forms.RadioSelect(attrs={'class': 'form-check-input'}),
            'foto': forms.FileInput(attrs={'class': 'form-control'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001', 'placeholder': 'GPS (opcional)'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001', 'placeholder': 'GPS (opcional)'}),
        }

    def clean(self):
        cleaned = super().clean()
        praga_presente = cleaned.get('praga_presente')
        quantidade = cleaned.get('quantidade')

        if praga_presente and not quantidade:
            raise ValidationError('Se praga está presente, informar quantidade')
        if praga_presente and not cleaned.get('estagio'):
            raise ValidationError('Se praga está presente, informar o estágio')

        return cleaned


class EstagioDesenvolvimentoForm(forms.ModelForm):

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
            'descricao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Larva de 3º ínstar'}),
            'duracao_minima_dias': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'duracao_maxima_dias': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'ordem_ciclo': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'eh_fase_critica': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)

        if self.empresa:
            queryset = Praga.objects.filter(
                empresa=self.empresa,
                ativa=True
            ).order_by('nome_comum')

            if self.instance and self.instance.pk and self.instance.praga:
                if self.instance.praga not in queryset:
                    queryset = queryset | Praga.objects.filter(pk=self.instance.praga.pk)

            self.fields['praga'].queryset = queryset
