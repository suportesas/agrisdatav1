from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db import IntegrityError

from core.pagination import paginate
from .models import TipoDivergencia


@login_required
def tipo_divergencia_list(request):
    tipos_qs = TipoDivergencia.objects.filter(
        empresa=request.user.empresa
    ).order_by('severidade', 'nome')
    tipos, per_page, per_page_options = paginate(request, tipos_qs)
    return render(request, 'compras/tipo_divergencia_list.html', {
        'tipos': tipos,
        'per_page': per_page,
        'per_page_options': per_page_options,
    })


@login_required
def tipo_divergencia_create(request):
    if request.method == 'POST':
        codigo = (request.POST.get('codigo') or '').strip()
        nome = (request.POST.get('nome') or '').strip()
        descricao = request.POST.get('descricao', '').strip()
        severidade = request.POST.get('severidade') or 'MEDIO'
        ativo = request.POST.get('ativo') == 'on'
        gera_valor_pedido_completo = request.POST.get('gera_valor_pedido_completo') == 'on'

        if not codigo or not nome:
            messages.error(request, 'Código e Nome são obrigatórios.')
            return render(request, 'compras/tipo_divergencia_form.html', {
                'form_data': request.POST,
            })

        try:
            TipoDivergencia.objects.create(
                empresa=request.user.empresa,
                codigo=codigo,
                nome=nome,
                descricao=descricao,
                severidade=severidade,
                ativo=ativo,
                gera_valor_pedido_completo=gera_valor_pedido_completo,
            )
        except IntegrityError:
            messages.error(request, f'Já existe um tipo de divergência com o código "{codigo}".')
            return render(request, 'compras/tipo_divergencia_form.html', {
                'form_data': request.POST,
            })

        messages.success(request, 'Tipo de divergência cadastrado com sucesso!')
        return redirect('compras:tipo_divergencia_list')

    return render(request, 'compras/tipo_divergencia_form.html', {'form_data': {}})


@login_required
def tipo_divergencia_edit(request, pk):
    tipo = get_object_or_404(TipoDivergencia, pk=pk, empresa=request.user.empresa)
    if request.method == 'POST':
        codigo = (request.POST.get('codigo') or '').strip()
        nome = (request.POST.get('nome') or '').strip()

        if not codigo or not nome:
            messages.error(request, 'Código e Nome são obrigatórios.')
            return render(request, 'compras/tipo_divergencia_form.html', {'tipo': tipo, 'form_data': {}})

        tipo.codigo = codigo
        tipo.nome = nome
        tipo.descricao = request.POST.get('descricao', '').strip()
        tipo.severidade = request.POST.get('severidade') or 'MEDIO'
        tipo.ativo = request.POST.get('ativo') == 'on'
        tipo.gera_valor_pedido_completo = request.POST.get('gera_valor_pedido_completo') == 'on'

        try:
            tipo.save()
        except IntegrityError:
            messages.error(request, f'Já existe um tipo de divergência com o código "{codigo}".')
            return render(request, 'compras/tipo_divergencia_form.html', {'tipo': tipo, 'form_data': {}})

        messages.success(request, 'Tipo de divergência atualizado!')
        return redirect('compras:tipo_divergencia_list')

    return render(request, 'compras/tipo_divergencia_form.html', {'tipo': tipo, 'form_data': {}})


@login_required
@require_POST
def tipo_divergencia_toggle(request, pk):
    tipo = get_object_or_404(TipoDivergencia, pk=pk, empresa=request.user.empresa)
    tipo.ativo = not tipo.ativo
    tipo.save(update_fields=['ativo'])
    estado = 'ativado' if tipo.ativo else 'desativado'
    messages.success(request, f'Tipo de divergência "{tipo.nome}" {estado}.')
    return redirect('compras:tipo_divergencia_list')
