"""
Protótipo — testa o serviço de Distribuição de DF-e (distDFeInt) por CNPJ/CPF.

Usa o certificado A1 já cadastrado em ConfiguracaoFiscal (Faturamento →
Configuração) da empresa informada. O CNPJ/CPF consultado por padrão é o do
certificado (`certificado_cnpj`); passe --cnpj-cpf para consultar outro
documento (ex.: uma Fazenda com CNPJ/CPF próprio) — mas lembre-se que a
SEFAZ só aceita se o certificado usado pertencer a esse mesmo CNPJ/CPF, ou
tiver procuração eletrônica para consultar em nome dele.

Uso:
    python manage.py consultar_dfe --empresa-id 1
    python manage.py consultar_dfe --empresa-id 1 --cnpj-cpf 12345678000199
    python manage.py consultar_dfe --empresa-id 1 --ult-nsu 000000000000123
    python manage.py consultar_dfe --empresa-id 1 --chave 35260112345678000199550010000012345123456789
"""
from django.core.management.base import BaseCommand, CommandError

from faturamento.models import ConfiguracaoFiscal
from faturamento.services.distribuicao_dfe import (
    DistribuicaoDFeError,
    consultar_distribuicao_dfe,
)


class Command(BaseCommand):
    help = 'Protótipo: consulta o serviço de Distribuição de DF-e (distDFeInt) por CNPJ/CPF'

    def add_arguments(self, parser):
        parser.add_argument('--empresa-id', type=int, required=True, help='Empresa dona do certificado A1')
        parser.add_argument('--uf', type=str, default=None, help='UF autora (padrão: UF cadastrada na empresa, se houver)')
        parser.add_argument('--cnpj-cpf', type=str, default=None, help='Padrão: CNPJ do próprio certificado')
        parser.add_argument('--ult-nsu', type=str, default='0', help='Último NSU já recebido (padrão: 0 — primeira sincronização)')
        parser.add_argument('--nsu', type=str, default=None, help='Consulta um NSU específico (consNSU)')
        parser.add_argument('--chave', type=str, default=None, help='Consulta uma chave de acesso específica (consChNFe)')

    def handle(self, *args, **options):
        try:
            config = ConfiguracaoFiscal.objects.select_related('empresa').get(empresa_id=options['empresa_id'])
        except ConfiguracaoFiscal.DoesNotExist:
            raise CommandError(f"Empresa {options['empresa_id']} não tem Configuração Fiscal.")

        if not config.certificado_pfx:
            raise CommandError('Empresa não tem certificado digital A1 cadastrado (Faturamento → Configuração).')

        cnpj_cpf = options['cnpj_cpf'] or config.certificado_cnpj
        if not cnpj_cpf:
            raise CommandError('Informe --cnpj-cpf (o certificado não tem CNPJ identificado).')

        uf = options['uf'] or getattr(config.empresa, 'uf', None)
        if not uf:
            raise CommandError('Informe --uf (não foi possível descobrir a UF automaticamente).')

        if cnpj_cpf.strip() != (config.certificado_cnpj or '').strip():
            self.stdout.write(self.style.WARNING(
                f'Aviso: consultando CNPJ/CPF {cnpj_cpf}, mas o certificado pertence a '
                f'{config.certificado_cnpj}. A SEFAZ só aceita se houver procuração eletrônica.'
            ))

        self.stdout.write(f'Consultando distDFeInt para {cnpj_cpf} (ambiente={config.get_ambiente_nfe_display()})...')

        try:
            resultado = consultar_distribuicao_dfe(
                cnpj_cpf=cnpj_cpf,
                cert_pfx=bytes(config.certificado_pfx),
                senha_cert=config.senha_certificado,
                uf=uf,
                ambiente=config.ambiente_nfe,
                ult_nsu=options['ult_nsu'],
                nsu=options['nsu'],
                chave=options['chave'],
            )
        except DistribuicaoDFeError as exc:
            raise CommandError(str(exc))

        self.stdout.write(f'cStat={resultado.c_stat}  xMotivo={resultado.x_motivo}')
        self.stdout.write(f'ultNSU={resultado.ult_nsu}  maxNSU={resultado.max_nsu}')

        if not resultado.documentos:
            self.stdout.write(self.style.WARNING('Nenhum documento retornado neste lote.'))
            return

        self.stdout.write(self.style.SUCCESS(f'{len(resultado.documentos)} documento(s):'))
        for doc in resultado.documentos:
            self.stdout.write(f'  NSU={doc.nsu}  schema={doc.schema}  chave={doc.chave_acesso}')
