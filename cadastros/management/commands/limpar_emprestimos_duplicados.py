from django.core.management.base import BaseCommand
from django.db import transaction
from cadastros.models import EmprestimoProdutor


class Command(BaseCommand):
    help = 'Remove registros duplicados de EmprestimoProdutor gerados ao adicionar itens antes do atendimento da requisição.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Apenas lista duplicatas sem excluir.')
        parser.add_argument('--requisicao', type=str, help='Filtrar por número de requisição (ex: REQ-000004).')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        filtro_req = options.get('requisicao')

        qs = EmprestimoProdutor.objects.select_related('requisicao', 'produto', 'produtor')
        if filtro_req:
            qs = qs.filter(requisicao__numero=filtro_req)

        # Agrupar por chave natural de unicidade
        grupos = {}
        for emp in qs.order_by('id'):
            chave = (emp.empresa_id, emp.requisicao_id, emp.requisicao_item_id, emp.produto_id, emp.produtor_id)
            grupos.setdefault(chave, []).append(emp)

        duplicados = {k: v for k, v in grupos.items() if len(v) > 1}

        if not duplicados:
            self.stdout.write(self.style.SUCCESS('Nenhuma duplicata encontrada.'))
            return

        total_excluidos = 0
        total_mensagens = 0
        total_movimentos = 0

        for chave, registros in duplicados.items():
            # Manter o de maior pk (criado no atendimento); excluir os anteriores
            registros_ordenados = sorted(registros, key=lambda e: e.pk)
            manter = registros_ordenados[-1]
            excluir = registros_ordenados[:-1]

            req_num = manter.requisicao.numero if manter.requisicao_id else '-'
            produto = manter.produto.nome if manter.produto_id else '-'

            self.stdout.write(
                f'Requisição {req_num} | Produto: {produto} | '
                f'Mantendo pk={manter.pk} | Excluindo: {[e.pk for e in excluir]}'
            )

            if not dry_run:
                with transaction.atomic():
                    for dup in excluir:
                        # Migrar mensagens para o registro correto
                        n_msg = dup.mensagens.count()
                        if n_msg:
                            dup.mensagens.all().update(emprestimo=manter)
                            total_mensagens += n_msg

                        # Migrar movimentos para o registro correto
                        n_mov = dup.movimentos.count()
                        if n_mov:
                            dup.movimentos.all().update(emprestimo=manter)
                            total_movimentos += n_mov

                        dup.delete()
                        total_excluidos += 1

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f'\n[DRY RUN] {sum(len(v) - 1 for v in duplicados.values())} duplicatas detectadas em {len(duplicados)} grupos. '
                'Execute sem --dry-run para excluir.'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'\nConcluído: {total_excluidos} duplicatas excluídas | '
                f'{total_mensagens} mensagens migradas | '
                f'{total_movimentos} movimentos migrados.'
            ))
