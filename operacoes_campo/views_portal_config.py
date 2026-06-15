"""View de configurações do Portal do Campo (acessível ao admin da empresa)."""
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from django import forms

from .models import PortalCampoConfig


class PortalCampoConfigForm(forms.ModelForm):
    class Meta:
        model = PortalCampoConfig
        fields = ['horario_trabalhadores', 'fator_encargos']
        widgets = {
            'horario_trabalhadores': forms.RadioSelect(),
            'fator_encargos': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.0001', 'min': '1', 'max': '3',
                'placeholder': 'Ex: 1.70 para CLT',
            }),
        }
        labels = {
            'horario_trabalhadores': 'Horário dos trabalhadores adicionais',
            'fator_encargos': 'Fator de Encargos Trabalhistas',
        }


@login_required
def portal_campo_config_view(request):
    if not request.user.empresa:
        return redirect('dashboard:index')

    if not (request.user.is_admin_empresa or request.user.is_superuser):
        messages.error(request, 'Apenas administradores podem acessar as configurações do portal.')
        return redirect('operacoes_campo:os_list')

    empresa = request.user.empresa
    config, _ = PortalCampoConfig.objects.get_or_create(empresa=empresa)

    if request.method == 'POST':
        form = PortalCampoConfigForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, 'Configurações do Portal do Campo salvas.')
            return redirect('operacoes_campo:portal_campo_config')
    else:
        form = PortalCampoConfigForm(instance=config)

    return render(request, 'cadastros/os/portal_campo_config.html', {
        'form': form,
        'config': config,
    })
