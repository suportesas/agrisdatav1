from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from financeiro.models import FormaPagemento
from django.contrib.auth.decorators import login_required

@login_required
def forma_pagamento_list(request):
    formas = FormaPagemento.objects.filter(empresa=request.user.empresa).order_by('ordem_exibicao')
    return render(request, 'compras/forma_pagamento_list.html', {'formas': formas})

@login_required
def forma_pagamento_create(request):
    if request.method == 'POST':
        nome = request.POST.get('nome')
        ativo = request.POST.get('ativo') == 'on'
        ordem_exibicao = request.POST.get('ordem_exibicao') or 0
        dias_processamento = request.POST.get('dias_processamento') or 0
        taxa_administrativa = request.POST.get('taxa_administrativa') or 0
        if not nome:
            messages.error(request, 'Nome é obrigatório.')
            return redirect('compras:forma_pagamento_create')
        FormaPagemento.objects.create(
            empresa=request.user.empresa,
            nome=nome,
            ativo=ativo,
            ordem_exibicao=ordem_exibicao,
            dias_processamento=dias_processamento,
            taxa_administrativa=taxa_administrativa
        )
        messages.success(request, 'Forma de pagamento criada com sucesso!')
        return redirect('compras:forma_pagamento_list')
    return render(request, 'compras/forma_pagamento_form.html')

@login_required
def forma_pagamento_edit(request, pk):
    forma = get_object_or_404(FormaPagemento, pk=pk, empresa=request.user.empresa)
    if request.method == 'POST':
        forma.nome = request.POST.get('nome')
        forma.ativo = request.POST.get('ativo') == 'on'
        forma.ordem_exibicao = request.POST.get('ordem_exibicao') or 0
        forma.dias_processamento = request.POST.get('dias_processamento') or 0
        forma.taxa_administrativa = request.POST.get('taxa_administrativa') or 0
        forma.save()
        messages.success(request, 'Forma de pagamento atualizada!')
        return redirect('compras:forma_pagamento_list')
    return render(request, 'compras/forma_pagamento_form.html', {'forma': forma})

@login_required
def forma_pagamento_delete(request, pk):
    forma = get_object_or_404(FormaPagemento, pk=pk, empresa=request.user.empresa)
    if request.method == 'POST':
        forma.delete()
        messages.success(request, 'Forma de pagamento excluída!')
        return redirect('compras:forma_pagamento_list')
    return render(request, 'compras/forma_pagamento_confirm_delete.html', {'forma': forma})
