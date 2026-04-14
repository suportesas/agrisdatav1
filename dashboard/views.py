from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Count, Q, Sum
from django.utils import timezone

from cadastros.models import EmprestimoProdutor
from empresas.models import Empresa
from usuarios.models import Usuario

#@login_required
#def index(request):
    #return render(request, 'dashboard/index.html')


# Em dashboard/views.py
@login_required
def index(request):
    context = {
        'is_saas_admin': request.user.is_superuser,
    }

    if request.user.is_superuser:
        seven_days_ago = timezone.now() - timezone.timedelta(days=7)
        empresas = Empresa.objects.all()
        usuarios = Usuario.objects.all()

        empresas_recentes = list(
            empresas.order_by('-data_criacao').values('id', 'nome', 'ativa', 'bloqueada')[:6]
        )

        top_empresas_usuarios = list(
            empresas.annotate(total_users=Count('usuarios')).order_by('-total_users', 'nome').values('nome', 'total_users')[:8]
        )
        max_users_top = max([item['total_users'] for item in top_empresas_usuarios], default=0)
        for item in top_empresas_usuarios:
            item['pct'] = int((item['total_users'] / max_users_top) * 100) if max_users_top > 0 else 0

        context.update({
            'total_empresas': empresas.count(),
            'empresas_ativas': empresas.filter(ativa=True, bloqueada=False).count(),
            'empresas_bloqueadas': empresas.filter(Q(bloqueada=True) | Q(ativa=False)).count(),
            'total_usuarios': usuarios.count(),
            'usuarios_ativos': usuarios.filter(is_active=True).count(),
            'novos_usuarios_7d': usuarios.filter(date_joined__gte=seven_days_ago).count(),
            'usuarios_sem_empresa': usuarios.filter(empresa__isnull=True).count(),
            'empresas_internas': empresas.filter(is_interna_saas=True).count(),
            'empresas_recentes': empresas_recentes,
            'top_empresas_usuarios': top_empresas_usuarios,
        })
        return render(request, 'dashboard/index.html', context)

    empresa = request.user.empresa

    pendencias_mensagens_emprestimo = EmprestimoProdutor.objects.none()
    total_mensagens_produtor_nao_lidas = 0
    total_emprestimos_com_pendencia = 0
    titulo_pendencias_emprestimo = 'Mensagens do produtor pendentes'
    if empresa:
        pendencias_base = EmprestimoProdutor.objects.filter(empresa=empresa)
        if request.user.tipo not in ['ADMIN', 'GERENTE']:
            pendencias_base = pendencias_base.filter(liberado_por=request.user)
            titulo_pendencias_emprestimo = 'Minhas pendências de empréstimos'

        pendencias_mensagens_emprestimo = (
            pendencias_base
            .annotate(
                unread_mensagens_interno_count=Count(
                    'mensagens',
                    filter=Q(mensagens__perfil_autor='PRODUTOR', mensagens__lido_interno_em__isnull=True),
                )
            )
            .filter(unread_mensagens_interno_count__gt=0)
            .select_related('produtor', 'produto', 'requisicao')
            .order_by('-atualizado_em', '-id')
        )
        total_mensagens_produtor_nao_lidas = pendencias_mensagens_emprestimo.aggregate(
            total=Sum('unread_mensagens_interno_count')
        ).get('total') or 0
        total_emprestimos_com_pendencia = pendencias_mensagens_emprestimo.count()

    context.update({
        'total_fazendas': empresa.fazendas.filter(ativa=True).count() if empresa else 0,
        'total_usuarios': empresa.usuarios.filter(is_active=True).count() if empresa else 0,
        'total_mensagens_produtor_nao_lidas': total_mensagens_produtor_nao_lidas,
        'total_emprestimos_com_pendencia': total_emprestimos_com_pendencia,
        'titulo_pendencias_emprestimo': titulo_pendencias_emprestimo,
        'pendencias_mensagens_emprestimo': pendencias_mensagens_emprestimo[:5],
    })
    return render(request, 'dashboard/index.html', context)


