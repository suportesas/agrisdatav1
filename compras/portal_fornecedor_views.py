
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash

@login_required
def perfil_usuario(request):
    user = request.user
    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        if nome:
            partes = nome.split()
            user.first_name = partes[0]
            user.last_name = ' '.join(partes[1:]) if len(partes) > 1 else ''
        if password1 or password2:
            if password1 != password2:
                messages.error(request, 'As senhas não conferem.')
            elif len(password1) < 6:
                messages.error(request, 'A senha deve ter pelo menos 6 caracteres.')
            else:
                user.set_password(password1)
                update_session_auth_hash(request, user)
                messages.success(request, 'Senha alterada com sucesso!')
        user.save()
        if nome:
            messages.success(request, 'Nome atualizado com sucesso!')
        return redirect('portal_fornecedor:perfil')
    return render(request, 'portal_fornecedor/perfil.html', {'user': user})
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from decimal import Decimal, InvalidOperation

from cadastros.models import DocumentoFornecedor, Fornecedor
from compras.models import (
    AvaliacaoFornecedor,
    Cotacao,
    DivergenciaRecebimento,
    FornecedorCotacao,
    ItemCotacao,
    PedidoCompra,
    PedidoCompraMensagem,
)


def _get_fornecedor_do_usuario(user):
    try:
        fornecedor = user.fornecedor_profile
    except Fornecedor.DoesNotExist:
        return None

    if not fornecedor.portal_enabled:
        return None

    if not user.empresa or fornecedor.empresa_id != user.empresa_id:
        return None

    return fornecedor


def _fornecedor_portal_guard(request):
    fornecedor = _get_fornecedor_do_usuario(request.user)
    if not fornecedor:
        raise PermissionDenied('Acesso permitido apenas para fornecedor com portal habilitado.')

    # Mantém o grupo FORNECEDOR sincronizado no primeiro acesso.
    group, _ = Group.objects.get_or_create(name='FORNECEDOR')
    if not request.user.groups.filter(pk=group.pk).exists():
        request.user.groups.add(group)

    return fornecedor


def _notificar_comprador_por_email(pedido, remetente_nome, texto_mensagem):
    """Envia e-mail ao comprador quando o fornecedor posta uma mensagem ou ação."""
    email_destino = getattr(pedido.comprador, 'email', None)
    if not email_destino:
        return
    try:
        send_mail(
            subject=f'[Portal Fornecedor] Pedido {pedido.numero} — ação do fornecedor',
            message=(
                f'Fornecedor {remetente_nome} — pedido {pedido.numero}:\n\n'
                f'{texto_mensagem}\n\n'
                f'Acesse o ERP para visualizar e responder.'
            ),
            from_email=None,
            recipient_list=[email_destino],
            fail_silently=True,
        )
    except Exception:
        pass


@login_required
def dashboard(request):
    fornecedor = _fornecedor_portal_guard(request)

    pedidos_qs = PedidoCompra.objects.filter(
        empresa=request.user.empresa,
        fornecedor=fornecedor
    )

    pedidos_recentes = pedidos_qs.order_by('-data_pedido')[:5]
    pedidos_abertos = pedidos_qs.exclude(status__in=['RECEBIDO', 'CANCELADO']).count()

    termo_assinado = DocumentoFornecedor.objects.filter(
        fornecedor=fornecedor,
        tipo='CONTRATO'
    ).exists()

    # Cotações EM_ANDAMENTO onde este fornecedor ainda não respondeu todos os itens
    cotacoes_pendentes = 0
    for cot in Cotacao.objects.filter(empresa=request.user.empresa, status='EM_ANDAMENTO'):
        total = cot.itens.count()
        respondidos = FornecedorCotacao.objects.filter(
            item_cotacao__cotacao=cot, fornecedor=fornecedor
        ).count()
        if respondidos < total:
            cotacoes_pendentes += 1

    context = {
        'fornecedor': fornecedor,
        'pedidos_recentes': pedidos_recentes,
        'pedidos_abertos': pedidos_abertos,
        'termo_assinado': termo_assinado,
        'cotacoes_pendentes': cotacoes_pendentes,
    }
    return render(request, 'portal_fornecedor/dashboard.html', context)


@login_required
def pedidos_list(request):
    fornecedor = _fornecedor_portal_guard(request)

    pedidos = PedidoCompra.objects.filter(
        empresa=request.user.empresa,
        fornecedor=fornecedor
    ).order_by('-data_pedido')

    return render(request, 'portal_fornecedor/pedidos_list.html', {
        'fornecedor': fornecedor,
        'pedidos': pedidos,
    })


@login_required
def pedido_detail(request, pk):
    fornecedor = _fornecedor_portal_guard(request)

    pedido = get_object_or_404(
        PedidoCompra.objects.select_related('fornecedor', 'empresa', 'comprador').prefetch_related('itens'),
        pk=pk,
        empresa=request.user.empresa,
        fornecedor=fornecedor,
    )

    if request.method == 'POST':
        action = request.POST.get('action', 'mensagem')

        # ── 1. Confirmação / Rejeição do pedido ──────────────────────────
        if action == 'confirmar':
            if pedido.status != 'ENVIADO':
                messages.error(request, 'Somente pedidos com status "Enviado ao Fornecedor" podem ser confirmados.')
                return redirect('portal_fornecedor:pedido_detail', pk=pedido.pk)
            pedido.confirmar()
            messages.success(request, 'Pedido confirmado com sucesso!')
            _notificar_comprador_por_email(
                pedido,
                remetente_nome=fornecedor.nome_fantasia or fornecedor.nome,
                texto_mensagem=f'O fornecedor confirmou o pedido {pedido.numero}.',
            )
            return redirect('portal_fornecedor:pedido_detail', pk=pedido.pk)

        if action == 'rejeitar':
            if pedido.status != 'ENVIADO':
                messages.error(request, 'Somente pedidos com status "Enviado ao Fornecedor" podem ser rejeitados.')
                return redirect('portal_fornecedor:pedido_detail', pk=pedido.pk)
            motivo = (request.POST.get('motivo_rejeicao') or '').strip()
            if not motivo:
                messages.error(request, 'Informe o motivo da rejeição antes de rejeitar.')
                return redirect('portal_fornecedor:pedido_detail', pk=pedido.pk)
            pedido.cancelar(motivo)
            messages.warning(request, 'Pedido rejeitado. O gerente de compras será notificado.')
            _notificar_comprador_por_email(
                pedido,
                remetente_nome=fornecedor.nome_fantasia or fornecedor.nome,
                texto_mensagem=f'O fornecedor REJEITOU o pedido {pedido.numero}.\nMotivo: {motivo}',
            )
            return redirect('portal_fornecedor:pedido_detail', pk=pedido.pk)

        # ── 2. Resposta do fornecedor a uma divergência ───────────────────
        if action == 'responder_divergencia':
            div_id = request.POST.get('divergencia_id', '').strip()
            resposta = (request.POST.get('resposta_fornecedor') or '').strip()
            if not div_id or not resposta:
                messages.error(request, 'Preencha a resposta antes de enviar.')
                return redirect('portal_fornecedor:pedido_detail', pk=pedido.pk)
            div = get_object_or_404(DivergenciaRecebimento, pk=div_id, recebimento__pedido=pedido)
            if div.resposta_fornecedor:
                messages.info(request, 'Esta divergência já possui resposta registrada.')
                return redirect('portal_fornecedor:pedido_detail', pk=pedido.pk)
            div.resposta_fornecedor = resposta
            div.data_resposta_fornecedor = timezone.now()
            div.save(update_fields=['resposta_fornecedor', 'data_resposta_fornecedor'])
            messages.success(request, 'Resposta à divergência registrada com sucesso!')
            _notificar_comprador_por_email(
                pedido,
                remetente_nome=fornecedor.nome_fantasia or fornecedor.nome,
                texto_mensagem=f'O fornecedor respondeu a uma divergência do pedido {pedido.numero}:\n{resposta}',
            )
            return redirect('portal_fornecedor:pedido_detail', pk=pedido.pk)

        # ── 3. Envio de mensagem (padrão) ─────────────────────────────────
        texto = (request.POST.get('mensagem') or '').strip()
        if not texto:
            messages.error(request, 'Digite uma mensagem antes de enviar.')
            return redirect('portal_fornecedor:pedido_detail', pk=pedido.pk)

        PedidoCompraMensagem.objects.create(
            pedido=pedido,
            autor=request.user,
            mensagem=texto,
        )
        messages.success(request, 'Mensagem enviada para o gerente de compras.')
        _notificar_comprador_por_email(
            pedido,
            remetente_nome=fornecedor.nome_fantasia or fornecedor.nome,
            texto_mensagem=texto,
        )
        return redirect('portal_fornecedor:pedido_detail', pk=pedido.pk)

    # GET ─────────────────────────────────────────────────────────────────
    recebimentos = pedido.recebimentos.all()
    divergencias = DivergenciaRecebimento.objects.filter(
        recebimento__pedido=pedido
    ).select_related('tipo_divergencia', 'recebimento')
    avaliacoes = AvaliacaoFornecedor.objects.filter(recebimento__pedido=pedido, fornecedor=fornecedor)
    mensagens_pedido = pedido.mensagens.select_related('autor').order_by('data_envio')

    context = {
        'fornecedor': fornecedor,
        'pedido': pedido,
        'recebimentos': recebimentos,
        'divergencias': divergencias,
        'avaliacoes': avaliacoes,
        'mensagens_pedido': mensagens_pedido,
    }
    return render(request, 'portal_fornecedor/pedido_detail.html', context)


# ---------------------------------------------------------------------------
# Cotações
# ---------------------------------------------------------------------------

@login_required
def cotacoes_list(request):
    """Lista cotações EM_ANDAMENTO da empresa para que o fornecedor envie propostas."""
    fornecedor = _fornecedor_portal_guard(request)

    cotacoes = Cotacao.objects.filter(
        empresa=request.user.empresa,
        status='EM_ANDAMENTO',
    ).prefetch_related('itens').order_by('-data_cotacao')

    # Marca as que o fornecedor já respondeu (tem pelo menos 1 proposta)
    cotacoes_com_status = []
    for cot in cotacoes:
        propostas_existentes = FornecedorCotacao.objects.filter(
            item_cotacao__cotacao=cot,
            fornecedor=fornecedor,
        ).count()
        cotacoes_com_status.append({
            'cotacao': cot,
            'total_itens': cot.itens.count(),
            'itens_respondidos': propostas_existentes,
            'respondida': propostas_existentes >= cot.itens.count() and cot.itens.count() > 0,
        })

    return render(request, 'portal_fornecedor/cotacoes_list.html', {
        'fornecedor': fornecedor,
        'cotacoes_com_status': cotacoes_com_status,
    })


@login_required
def cotacao_responder(request, pk):
    """Permite ao fornecedor informar preços para cada item de uma cotação."""
    fornecedor = _fornecedor_portal_guard(request)

    cotacao = get_object_or_404(
        Cotacao,
        pk=pk,
        empresa=request.user.empresa,
        status='EM_ANDAMENTO',
    )

    items = ItemCotacao.objects.filter(cotacao=cotacao).select_related(
        'produto', 'unidade_medida'
    )

    # Busca propostas já enviadas por este fornecedor (para pré-preencher)
    propostas_existentes = {
        fc.item_cotacao_id: fc
        for fc in FornecedorCotacao.objects.filter(
            item_cotacao__cotacao=cotacao,
            fornecedor=fornecedor,
        )
    }

    if request.method == 'POST':
        erros = []
        salvos = 0

        for item in items:
            preco_str = request.POST.get(f'preco_{item.pk}', '').strip().replace(',', '.')
            if not preco_str:
                continue  # item não preenchido — ignora

            try:
                preco = Decimal(preco_str)
                if preco <= 0:
                    raise ValueError
            except (InvalidOperation, ValueError):
                erros.append(f'Preço inválido para "{item.produto.nome}". Use ponto como separador decimal.')
                continue

            prazo_str = request.POST.get(f'prazo_{item.pk}', '0').strip()
            try:
                prazo = max(0, int(prazo_str))
            except (ValueError, TypeError):
                prazo = 0

            condicao = request.POST.get(f'condicao_{item.pk}', '').strip()
            marca    = request.POST.get(f'marca_{item.pk}', '').strip()
            obs      = request.POST.get(f'obs_{item.pk}', '').strip()

            FornecedorCotacao.objects.update_or_create(
                item_cotacao=item,
                fornecedor=fornecedor,
                defaults={
                    'preco_unitario': preco,
                    'preco_total': preco * item.quantidade,
                    'prazo_entrega': prazo,
                    'condicao_pagamento': condicao,
                    'marca': marca,
                    'observacoes': obs,
                },
            )
            item.atualizar_status()
            salvos += 1

        if erros:
            for e in erros:
                messages.error(request, e)
        if salvos:
            messages.success(request, f'{salvos} item(ns) enviado(s) com sucesso!')
            _notificar_comprador_por_email(
                type('obj', (object,), {
                    'numero': cotacao.numero,
                    'comprador': cotacao.comprador,
                })(),
                remetente_nome=fornecedor.nome_fantasia or fornecedor.nome,
                texto_mensagem=(
                    f'O fornecedor submeteu proposta(s) na cotação {cotacao.numero}.\n'
                    f'{salvos} item(ns) respondido(s). Acesse o ERP para visualizar.'
                ),
            )

        return redirect('portal_fornecedor:cotacao_responder', pk=cotacao.pk)

    # Monta lista enriquecida para o template
    items_data = [
        {'item': item, 'proposta': propostas_existentes.get(item.pk)}
        for item in items
    ]

    return render(request, 'portal_fornecedor/cotacao_responder.html', {
        'fornecedor': fornecedor,
        'cotacao': cotacao,
        'items_data': items_data,
    })
