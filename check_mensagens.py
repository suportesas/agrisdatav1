import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from cadastros.models import EmprestimoMensagem, EmprestimoProdutor
from django.db.models import Count, Q

print('=== Mensagens no banco ===')
msgs = EmprestimoMensagem.objects.select_related('emprestimo__requisicao').all()
print(f'Total: {msgs.count()}')
for m in msgs:
    req = m.emprestimo.requisicao.numero if m.emprestimo.requisicao_id else '-'
    print(f'  pk={m.pk} emp={m.emprestimo_id} req={req} perfil={m.perfil_autor} lido_interno={m.lido_interno_em} lido_produtor={m.lido_produtor_em}')

print()
print('=== EmprestimoProdutor - mensagens nao lidas ===')
emps = EmprestimoProdutor.objects.select_related('requisicao', 'produto').annotate(
    unread=Count('mensagens', filter=Q(mensagens__perfil_autor='PRODUTOR', mensagens__lido_interno_em__isnull=True))
)
for e in emps:
    req = e.requisicao.numero if e.requisicao_id else '-'
    print(f'  emp_pk={e.pk} req={req} produto={e.produto.nome[:25]} unread={e.unread}')
