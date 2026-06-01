from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Busca e salva as cotações PTAX do BCB para USD, EUR e GBP'

    def add_arguments(self, parser):
        parser.add_argument(
            '--data',
            type=str,
            default='',
            help='Data de referência no formato YYYY-MM-DD (padrão: hoje)',
        )

    def handle(self, *args, **options):
        from datetime import date
        from faturamento.bcb import buscar_cotacoes
        from faturamento.models import CotacaoBCB

        data_param = options.get('data', '')
        data_ref = None
        if data_param:
            try:
                data_ref = date.fromisoformat(data_param)
            except ValueError:
                self.stderr.write(self.style.ERROR(f'Data inválida: {data_param}'))
                return

        self.stdout.write('Consultando BCB...')
        try:
            resultado = buscar_cotacoes(moedas=['USD', 'EUR', 'GBP'], referencia=data_ref)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Erro ao consultar BCB: {e}'))
            return

        data_bcb = date.fromisoformat(resultado['data_iso'])
        salvos = []
        for moeda, dados in resultado['cotacoes'].items():
            obj, criado = CotacaoBCB.objects.update_or_create(
                data=data_bcb,
                moeda=moeda,
                defaults={'compra': dados['compra'], 'venda': dados['venda']},
            )
            acao = 'criado' if criado else 'atualizado'
            salvos.append(f'{moeda}: compra={dados["compra"]:.4f} venda={dados["venda"]:.4f} ({acao})')

        self.stdout.write(self.style.SUCCESS(
            f'Cotações salvas para {resultado["data"]}:\n  ' + '\n  '.join(salvos)
        ))
