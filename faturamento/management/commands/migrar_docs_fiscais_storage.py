"""
Migra XMLs e PDFs fiscais do banco de dados (base64) para Supabase Storage.

Uso:
    python manage.py migrar_docs_fiscais_storage
    python manage.py migrar_docs_fiscais_storage --tipo nfe
    python manage.py migrar_docs_fiscais_storage --tipo cte --empresa-id 2
    python manage.py migrar_docs_fiscais_storage --dry-run
"""
from django.core.management.base import BaseCommand
from faturamento.fiscal_storage import upload_xml, upload_pdf


class Command(BaseCommand):
    help = 'Migra documentos fiscais base64 do banco para Supabase Storage'

    def add_arguments(self, parser):
        parser.add_argument('--tipo', choices=['nfe', 'cte', 'mdfe', 'all'], default='all')
        parser.add_argument('--empresa-id', type=int, default=None)
        parser.add_argument('--dry-run', action='store_true', help='Simula sem gravar')

    def handle(self, *args, **options):
        tipo = options['tipo']
        empresa_id = options.get('empresa_id')
        dry = options['dry_run']

        if tipo in ('nfe', 'all'):
            self._migrar_nfe(empresa_id, dry)
        if tipo in ('cte', 'all'):
            self._migrar_cte(empresa_id, dry)
        if tipo in ('mdfe', 'all'):
            self._migrar_mdfe(empresa_id, dry)

    # ── NF-e ────────────────────────────────────────────────────────────────────

    def _migrar_nfe(self, empresa_id, dry):
        from faturamento.models import NotaFiscal
        qs = NotaFiscal.objects.filter(xml_autorizacao__gt='') | NotaFiscal.objects.filter(pdf_danfe__gt='')
        if empresa_id:
            qs = qs.filter(empresa_id=empresa_id)
        qs = qs.exclude(xml_autorizacao_url__gt='', pdf_danfe_url__gt='').distinct()
        total = qs.count()
        self.stdout.write(f'NF-e: {total} registros a migrar')
        ok = 0
        for nf in qs.iterator():
            fields = []
            if nf.xml_autorizacao and not nf.xml_autorizacao_url:
                url = upload_xml(nf.xml_autorizacao, nf.empresa_id, 'nfe',
                                 f'XML_NF_{nf.numero}_{nf.serie}.xml')
                if url:
                    nf.xml_autorizacao_url = url
                    nf.xml_autorizacao = ''
                    fields += ['xml_autorizacao_url', 'xml_autorizacao']
            if nf.pdf_danfe and not nf.pdf_danfe_url:
                url = upload_pdf(nf.pdf_danfe, nf.empresa_id, 'nfe',
                                 f'DANFE_{nf.numero}_{nf.serie}.pdf')
                if url:
                    nf.pdf_danfe_url = url
                    nf.pdf_danfe = ''
                    fields += ['pdf_danfe_url', 'pdf_danfe']
            if fields and not dry:
                nf.save(update_fields=fields)
                ok += 1
            elif fields and dry:
                ok += 1
        self.stdout.write(self.style.SUCCESS(f'NF-e: {ok}/{total} migrados{"(dry)" if dry else ""}'))

    # ── CT-e ────────────────────────────────────────────────────────────────────

    def _migrar_cte(self, empresa_id, dry):
        from faturamento.models import ConhecimentoTransporte
        qs = (ConhecimentoTransporte.objects
              .filter(xml_autorizacao__gt='') |
              ConhecimentoTransporte.objects.filter(pdf_dacte__gt='') |
              ConhecimentoTransporte.objects.filter(xml_cancelamento__gt=''))
        if empresa_id:
            qs = qs.filter(empresa_id=empresa_id)
        total = qs.distinct().count()
        self.stdout.write(f'CT-e: {total} registros a migrar')
        ok = 0
        for ct in qs.distinct().iterator():
            fields = []
            if ct.xml_autorizacao and not ct.xml_autorizacao_url:
                url = upload_xml(ct.xml_autorizacao, ct.empresa_id, 'cte',
                                 f'XML_CTE_{ct.numero}_{ct.serie}.xml')
                if url:
                    ct.xml_autorizacao_url = url
                    ct.xml_autorizacao = ''
                    fields += ['xml_autorizacao_url', 'xml_autorizacao']
            if ct.pdf_dacte and not ct.pdf_dacte_url:
                url = upload_pdf(ct.pdf_dacte, ct.empresa_id, 'cte',
                                 f'DACTE_{ct.numero}_{ct.serie}.pdf')
                if url:
                    ct.pdf_dacte_url = url
                    ct.pdf_dacte = ''
                    fields += ['pdf_dacte_url', 'pdf_dacte']
            if ct.xml_cancelamento and not ct.xml_cancelamento_url:
                url = upload_xml(ct.xml_cancelamento, ct.empresa_id, 'cte',
                                 f'CANCEL_CTE_{ct.numero}_{ct.serie}.xml')
                if url:
                    ct.xml_cancelamento_url = url
                    ct.xml_cancelamento = ''
                    fields += ['xml_cancelamento_url', 'xml_cancelamento']
            if fields and not dry:
                ct.save(update_fields=fields)
                ok += 1
            elif fields and dry:
                ok += 1
        self.stdout.write(self.style.SUCCESS(f'CT-e: {ok}/{total} migrados{"(dry)" if dry else ""}'))

    # ── MDF-e ───────────────────────────────────────────────────────────────────

    def _migrar_mdfe(self, empresa_id, dry):
        from faturamento.models import ManifestoDocumentoFiscal
        qs = (ManifestoDocumentoFiscal.objects.filter(xml_autorizacao__gt='') |
              ManifestoDocumentoFiscal.objects.filter(pdf_damdfe__gt=''))
        if empresa_id:
            qs = qs.filter(empresa_id=empresa_id)
        total = qs.distinct().count()
        self.stdout.write(f'MDF-e: {total} registros a migrar')
        ok = 0
        for mdfe in qs.distinct().iterator():
            fields = []
            if mdfe.xml_autorizacao and not mdfe.xml_autorizacao_url:
                url = upload_xml(mdfe.xml_autorizacao, mdfe.empresa_id, 'mdfe',
                                 f'XML_MDFE_{mdfe.numero}_{mdfe.serie}.xml')
                if url:
                    mdfe.xml_autorizacao_url = url
                    mdfe.xml_autorizacao = ''
                    fields += ['xml_autorizacao_url', 'xml_autorizacao']
            if mdfe.pdf_damdfe and not mdfe.pdf_damdfe_url:
                url = upload_pdf(mdfe.pdf_damdfe, mdfe.empresa_id, 'mdfe',
                                 f'DAMDFE_{mdfe.numero}_{mdfe.serie}.pdf')
                if url:
                    mdfe.pdf_damdfe_url = url
                    mdfe.pdf_damdfe = ''
                    fields += ['pdf_damdfe_url', 'pdf_damdfe']
            if fields and not dry:
                mdfe.save(update_fields=fields)
                ok += 1
            elif fields and dry:
                ok += 1
        self.stdout.write(self.style.SUCCESS(f'MDF-e: {ok}/{total} migrados{"(dry)" if dry else ""}'))
