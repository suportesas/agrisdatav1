"""
Sincroniza a Distribuição de DF-e (distDFeInt) — busca documentos novos por NSU,
grava DfeRecebido e baixa o XML completo das NF-e novas.

Reaproveitado pelo webhook `faturamento:dfe_sync_webhook` (chamado pelo cron do
Supabase a cada 2h) e disponível aqui pra rodar manualmente / depurar.

Uso:
    python manage.py sincronizar_dfe                    # todas as empresas com certificado
    python manage.py sincronizar_dfe --empresa-id 1
    python manage.py sincronizar_dfe --empresa-id 1 --max-xml 5
"""
from django.core.management.base import BaseCommand, CommandError

from faturamento.services.distribuicao_dfe import sincronizar_dfe_empresa


class Command(BaseCommand):
    help = 'Sincroniza a Distribuição de DF-e (documentos novos + XML completo) por empresa'

    def add_arguments(self, parser):
        parser.add_argument('--empresa-id', type=int, default=None, help='Só esta empresa (padrão: todas com certificado)')
        parser.add_argument('--max-xml', type=int, default=10, help='Máximo de XMLs completos a baixar por empresa nesta execução')

    def handle(self, *args, **options):
        max_xml = options['max_xml']

        if options['empresa_id']:
            from empresas.models import Empresa
            try:
                empresa = Empresa.objects.get(pk=options['empresa_id'])
            except Empresa.DoesNotExist:
                raise CommandError(f"Empresa {options['empresa_id']} não encontrada.")
            resultados = [sincronizar_dfe_empresa(empresa, max_xml=max_xml)]
        else:
            from faturamento.services.distribuicao_dfe import sincronizar_todas_empresas
            resultados = sincronizar_todas_empresas(max_xml=max_xml)

        for r in resultados:
            if r.get('erro'):
                self.stdout.write(self.style.WARNING(
                    f"Empresa {r['empresa_id']}: ERRO — {r['erro']}"
                ))
            else:
                self.stdout.write(self.style.SUCCESS(
                    f"Empresa {r['empresa_id']}: {r['novos']} documento(s) novo(s), "
                    f"{r['xml_baixados']} XML(s) completo(s) baixado(s)."
                ))
