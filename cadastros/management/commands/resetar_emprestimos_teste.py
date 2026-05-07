from django.core.management.base import BaseCommand
from django.db import transaction
from cadastros.models import Requisicao, EmprestimoProdutor
from estoque.models import MovimentacaoEstoque


class Command(BaseCommand):
    help = (
        'Reseta requisições de empréstimo para APROVADA, removendo todos os registros de '
        'EmprestimoProdutor, EmprestimoMovimento, EmprestimoMensagem e MovimentacaoEstoque gerados. '
        'Use apenas em ambiente de testes.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Lista o que seria alterado sem executar.')
        parser.add_argument('--requisicao', type=str, help='Filtrar por número (ex: REQ-000004). Sem filtro: todas as EMPRESTIMO.')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        filtro_req = options.get('requisicao')

        qs = Requisicao.objects.filter(tipo='EMPRESTIMO').prefetch_related('emprestimos_gerados')
        if filtro_req:
            qs = qs.filter(numero=filtro_req)

        # Apenas as que já têm registros de empréstimo ou foram atendidas
        qs = qs.filter(emprestimos_gerados__isnull=False).distinct()

        if not qs.exists():
            self.stdout.write('Nenhuma requisição de empréstimo com registros encontrada.')
            return

        total_reqs = qs.count()
        self.stdout.write(f'Requisições encontradas: {total_reqs}\n')

        for req in qs:
            emps = req.emprestimos_gerados.all()
            n_emp = emps.count()
            n_mov_est = MovimentacaoEstoque.objects.filter(documento=req.numero, origem='REQUISICAO').count()
            n_msg = sum(e.mensagens.count() for e in emps)
            n_mov_emp = sum(e.movimentos.count() for e in emps)

            self.stdout.write(
                f'  {req.numero} | Status atual: {req.status} | '
                f'EmprestimoProdutor: {n_emp} | EmprestimoMovimento: {n_mov_emp} | '
                f'Mensagens: {n_msg} | MovimentacaoEstoque: {n_mov_est}'
            )

            if not dry_run:
                with transaction.atomic():
                    # 1. Remover mensagens e movimentos de cada EmprestimoProdutor
                    for emp in emps:
                        emp.mensagens.all().delete()
                        emp.movimentos.all().delete()

                    # 2. Remover os EmprestimoProdutor
                    emps.delete()

                    # 3. Remover MovimentacaoEstoque geradas pela requisição
                    MovimentacaoEstoque.objects.filter(
                        documento=req.numero, origem='REQUISICAO'
                    ).delete()

                    # 4. Resetar campos da Requisicao
                    req.status = 'APROVADA'
                    req.assinatura_liberacao_interna_imagem = None
                    req.assinatura_liberacao_interna_nome = ''
                    req.assinatura_liberacao_interna_datahora = None
                    req.assinatura_liberacao_interna_usuario = None
                    req.assinatura_produtor_imagem = None
                    req.assinatura_produtor_nome = ''
                    req.assinatura_produtor_datahora = None
                    req.assinatura_produtor_usuario = None
                    req.save(update_fields=[
                        'status',
                        'assinatura_liberacao_interna_imagem',
                        'assinatura_liberacao_interna_nome',
                        'assinatura_liberacao_interna_datahora',
                        'assinatura_liberacao_interna_usuario',
                        'assinatura_produtor_imagem',
                        'assinatura_produtor_nome',
                        'assinatura_produtor_datahora',
                        'assinatura_produtor_usuario',
                    ])
                self.stdout.write(self.style.SUCCESS(f'    [OK] {req.numero} resetada para APROVADA.'))

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f'\n[DRY RUN] {total_reqs} requisição(ões) seriam resetadas. '
                'Execute sem --dry-run para confirmar.'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(f'\nConcluído: {total_reqs} requisição(ões) resetada(s) para APROVADA.'))
