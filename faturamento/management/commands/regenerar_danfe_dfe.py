"""
Regera o DANFE (PDF) de documentos já baixados via Distribuição de DF-e.

Usado depois de melhorias no gerador local (faturamento/services/dfe_danfe.py) —
os PDFs gerados antes da melhoria ficam com o layout/bug antigo, já que
`baixar_xml_completo_dfe` só gera o DANFE quando `pdf_danfe_url` ainda está
vazio. Este comando força a regeneração de todo mundo que já tem XML completo.

Uso:
    python manage.py regenerar_danfe_dfe
    python manage.py regenerar_danfe_dfe --empresa-id 1
"""
import base64

import requests
from django.core.management.base import BaseCommand

from faturamento.fiscal_storage import upload_pdf
from faturamento.models import DfeRecebido
from faturamento.services.dfe_danfe import gerar_danfe_pdf, versionar_url


class Command(BaseCommand):
    help = 'Regera o DANFE (PDF) de resNFe que já têm XML completo baixado'

    def add_arguments(self, parser):
        parser.add_argument('--empresa-id', type=int, default=None, help='Restringe a uma empresa')

    def handle(self, *args, **options):
        qs = DfeRecebido.objects.filter(schema='resNFe').exclude(xml_url='')
        if options['empresa_id']:
            qs = qs.filter(empresa_id=options['empresa_id'])

        total = qs.count()
        self.stdout.write(f'{total} documento(s) com XML completo — regerando DANFE...')

        sucesso = 0
        falhas = 0
        for doc in qs.iterator():
            try:
                resp = requests.get(doc.xml_url, timeout=30)
                resp.raise_for_status()
                # .content.decode('utf-8') explícito — .text deixa o requests adivinhar a
                # codificação (erra pra Latin-1 quando o Storage não declara charset),
                # corrompendo acentos antes mesmo de chegar no parser do XML.
                pdf_bytes = gerar_danfe_pdf(resp.content.decode('utf-8'), doc)
                if not pdf_bytes:
                    self.stdout.write(self.style.WARNING(f'  [{doc.pk}] chave {doc.chave_acesso}: não gerou PDF'))
                    falhas += 1
                    continue
                pdf_url = upload_pdf(
                    base64.b64encode(pdf_bytes).decode('ascii'), doc.empresa_id, 'dfe', f'{doc.chave_acesso}.pdf',
                )
                if not pdf_url:
                    self.stdout.write(self.style.WARNING(f'  [{doc.pk}] chave {doc.chave_acesso}: falha no upload'))
                    falhas += 1
                    continue
                doc.pdf_danfe_url = versionar_url(pdf_url)
                doc.save(update_fields=['pdf_danfe_url'])
                sucesso += 1
            except Exception as exc:
                self.stdout.write(self.style.WARNING(f'  [{doc.pk}] chave {doc.chave_acesso}: erro — {exc}'))
                falhas += 1

        self.stdout.write(self.style.SUCCESS(f'{sucesso} DANFE(s) regerado(s), {falhas} falha(s).'))
