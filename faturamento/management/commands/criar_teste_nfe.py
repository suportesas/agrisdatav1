"""
Management command: criar_teste_nfe
Cria (ou limpa) dados de teste completos para emissão de NF-e em homologação.

Uso:
    python manage.py criar_teste_nfe
    python manage.py criar_teste_nfe --empresa-id 2
    python manage.py criar_teste_nfe --limpar
"""
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone


# ── marcadores para identificar registros de teste ─────────────────────────
_TAG_CLIENTE    = '[TESTE-NFE]'
_TAG_PRODUTO    = '[TESTE-NFE]'
_TAG_NF_NAT_OP  = 'TESTE NF-e HOMOLOGAÇÃO'


class Command(BaseCommand):
    help = 'Cria dados de teste completos para NF-e (homologação IntegraNota)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--empresa-id', type=int,
            help='ID da empresa (padrão: primeira ativa encontrada)',
        )
        parser.add_argument(
            '--limpar', action='store_true',
            help='Remove APENAS as notas de teste criadas por este comando',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        from empresas.models import Empresa
        from cadastros.models import NCM, CFOP, EmpresaCFOP, Cliente, EnderecoCliente
        from produtos.models import (
            Categoria, UnidadeMedida, Produto,
            ProdutoTributacao, NaturezaOperacao,
        )
        from faturamento.models import ConfiguracaoFiscal, NotaFiscal, ItemNotaFiscal

        # ── 1. Empresa ───────────────────────────────────────────────────────
        eid = options.get('empresa_id')
        if eid:
            try:
                empresa = Empresa.objects.get(pk=eid)
            except Empresa.DoesNotExist:
                raise CommandError(f'Empresa {eid} não encontrada.')
        else:
            empresa = Empresa.objects.filter(ativa=True).first()
            if not empresa:
                raise CommandError('Nenhuma empresa ativa encontrada. Use --empresa-id.')

        self.ok(f'Empresa: {empresa.nome} (ID {empresa.pk})')

        # ── 2. Limpar ────────────────────────────────────────────────────────
        if options.get('limpar'):
            deleted, _ = NotaFiscal.objects.filter(
                empresa=empresa, natureza_operacao=_TAG_NF_NAT_OP
            ).delete()
            self.ok(f'{deleted} nota(s) de teste removida(s).')
            return

        # ── 3. ConfiguracaoFiscal — garantir ambiente homologação ────────────
        config, _ = ConfiguracaoFiscal.objects.get_or_create(empresa=empresa)
        changed = []
        if config.ambiente_nfe != '2':
            config.ambiente_nfe = '2'
            changed.append('ambiente_nfe=2 (homologação)')
        # Preencher dados fiscais da empresa se estiverem vazios
        if not empresa.inscricao_estadual:
            empresa.inscricao_estadual = '111111111111'
            empresa.save(update_fields=['inscricao_estadual'])
            self.warn('  Inscrição Estadual da empresa preenchida com dado de teste: 111111111111')
        if not empresa.cep:
            empresa.cep = '01310100'
            empresa.numero_endereco = '1000'
            empresa.bairro = empresa.bairro or 'Centro'
            empresa.cidade = empresa.cidade or 'São Paulo'
            empresa.uf = empresa.uf or 'SP'
            empresa.codigo_municipio = '3550308'
            empresa.save(update_fields=['cep', 'numero_endereco', 'bairro', 'cidade', 'uf', 'codigo_municipio'])
            self.warn('  Endereço da empresa preenchido com dado de teste (SP/3550308)')
        if changed:
            config.save()
            self.warn(f'  ConfiguracaoFiscal ajustada: {", ".join(changed)}')
        else:
            self.info('  ConfiguracaoFiscal: OK')

        # ── 4. NCM ───────────────────────────────────────────────────────────
        ncm, created = NCM.objects.get_or_create(
            codigo='10059010',
            defaults={'nome': 'Milho em grão — outros', 'cest': '', 'ativo': True},
        )
        self.item('NCM 10059010', created)

        # ── 5. CFOP global ───────────────────────────────────────────────────
        cfop_5102, created = CFOP.objects.get_or_create(
            codigo='5102',
            defaults={
                'nome': 'Venda de mercadoria adquirida ou recebida de terceiros',
                'ativo': True,
            },
        )
        self.item('CFOP 5102 (global)', created)

        # ── 6. EmpresaCFOP (CFOP liberado para a empresa) ────────────────────
        emp_cfop, created = EmpresaCFOP.objects.get_or_create(
            empresa=empresa, codigo='5102',
            defaults={
                'nome': cfop_5102.nome,
                'ativo': True,
                'template': cfop_5102,
            },
        )
        self.item(f'EmpresaCFOP 5102 para {empresa.nome}', created)

        # ── 7. UnidadeMedida ─────────────────────────────────────────────────
        un, created = UnidadeMedida.objects.get_or_create(
            empresa=empresa, sigla='KG',
            defaults={'nome': 'Quilograma', 'tipo': 'PESO', 'ativo': True},
        )
        self.item('UnidadeMedida KG', created)

        # ── 8. NaturezaOperacao ──────────────────────────────────────────────
        nat_op, created = NaturezaOperacao.objects.get_or_create(
            empresa=empresa, codigo='5102',
            defaults={
                'descricao': 'Venda de Mercadoria',
                'tipo': 'SAIDA',
                'ativo': True,
            },
        )
        self.item('NaturezaOperacao 5102', created)

        # ── 9. Categoria ─────────────────────────────────────────────────────
        cat, created = Categoria.objects.get_or_create(
            empresa=empresa, codigo='GRAO',
            defaults={'nome': 'Grãos e Cereais', 'ativo': True},
        )
        self.item('Categoria GRAO', created)

        # ── 10. Produto ──────────────────────────────────────────────────────
        produto_qs = Produto.objects.filter(
            categoria=cat,
            nome__startswith=_TAG_PRODUTO,
        )
        produto = produto_qs.first()
        if not produto:
            produto = Produto(
                categoria=cat,
                nome=f'{_TAG_PRODUTO} Milho em Grão (Teste)',
                ncm=ncm,
                unidade_medida=un,
                unidade_compra=un,
                unidade_venda=un,
                fator_conversao=Decimal('1'),
                preco_venda=Decimal('85.00'),
                preco_custo=Decimal('65.00'),
                origem_mercadoria='0',
                tipo_item='00',
                ativo=True,
            )
            produto.save()
            self.item('Produto Milho em Grão (Teste)', True)
        else:
            self.item('Produto Milho em Grão (Teste)', False)

        # ── 11. ProdutoTributacao ────────────────────────────────────────────
        trib, created = ProdutoTributacao.objects.get_or_create(
            produto=produto,
            cfop=cfop_5102,
            defaults={
                'natureza_operacao': nat_op,
                'descricao': 'Venda de Mercadoria',
                'origem_mercadoria': '0',
                'icms_situacao_tributaria': '40',   # Isento
                'icms_modalidade_base': '3',
                'icms_aliquota': Decimal('0'),
                'icms_base_calculo': Decimal('100'),
                'icms_reducao_base': Decimal('0'),
                'ipi_situacao_tributaria': '99',
                'ipi_aliquota': Decimal('0'),
                'ipi_codigo_enquadramento': '999',
                'pis_situacao_tributaria': '07',    # Isento
                'pis_aliquota': Decimal('0'),
                'pis_base_calculo': Decimal('100'),
                'cofins_situacao_tributaria': '07',
                'cofins_aliquota': Decimal('0'),
                'cofins_base_calculo': Decimal('100'),
                'padrao': True,
                'ativo': True,
            },
        )
        self.item('ProdutoTributacao (CFOP 5102 / Isento)', created)

        # ── 12. Cliente ──────────────────────────────────────────────────────
        cli_qs = Cliente.objects.filter(empresa=empresa, razao_social__startswith=_TAG_CLIENTE)
        cliente = cli_qs.first()
        if not cliente:
            cliente = Cliente(
                empresa=empresa,
                razao_social=f'{_TAG_CLIENTE} Cliente Homologacao SEFAZ',
                nome_comercial='Cliente Teste NF-e',
                tipo_cliente='NACIONAL',
                tipo_pessoa='PJ',
                cnpj_cpf='11222333000181',   # CNPJ de teste com digito valido
                contribuinte_icms=False,
                status='ATIVO',
            )
            cliente.save()
            self.item('Cliente de teste', True)
        else:
            self.item('Cliente de teste', False)

        # ── 13. EnderecoCliente ──────────────────────────────────────────────
        end_qs = EnderecoCliente.objects.filter(cliente=cliente)
        if not end_qs.exists():
            EnderecoCliente.objects.create(
                cliente=cliente,
                tipo='PRINCIPAL',
                cep='01310100',
                logradouro='Avenida Paulista',
                numero='1000',
                bairro='Bela Vista',
                cidade='São Paulo',
                uf='SP',
                pais='Brasil',
                codigo_municipio='3550308',
                padrao=True,
            )
            self.item('EnderecoCliente (São Paulo / IBGE 3550308)', True)
        else:
            # Garantir que o endereço existente tenha codigo_municipio
            end = end_qs.first()
            if not end.codigo_municipio:
                end.codigo_municipio = '3550308'
                end.save(update_fields=['codigo_municipio'])
                self.warn('  EnderecoCliente: codigo_municipio preenchido com 3550308')
            self.item('EnderecoCliente', False)

        # ── 14. NotaFiscal (RASCUNHO) ────────────────────────────────────────
        nf_existente = NotaFiscal.objects.filter(
            empresa=empresa,
            natureza_operacao=_TAG_NF_NAT_OP,
            status='RASCUNHO',
        ).first()

        if nf_existente:
            self.warn(f'  Nota de teste já existe: NF {nf_existente.numero or "S/N"} (ID {nf_existente.pk}) — use --limpar para recriar')
            nf = nf_existente
        else:
            nf = NotaFiscal(
                empresa=empresa,
                cliente=cliente,
                serie=config.serie_nfe,
                data_emissao=timezone.now().date(),
                natureza_operacao=_TAG_NF_NAT_OP,
                status='RASCUNHO',
                modalidade_frete='SEM_FRETE',
                presenca_comprador='9',
                tipo_emissao=1,
                informacoes_complementares='NF-e gerada automaticamente para teste de homologação.',
            )
            nf.save()

            # ── 14a. ItemNotaFiscal ──────────────────────────────────────────
            qtd = Decimal('1000')
            vunit = produto.preco_venda
            item = ItemNotaFiscal(
                nota_fiscal=nf,
                numero_item=1,
                produto=produto,
                descricao=f'Milho em Grão — Teste NF-e Homologação',
                ncm='10059010',
                cfop='5102',
                unidade='KG',
                quantidade=qtd,
                valor_unitario=vunit,
                valor_desconto=Decimal('0'),
                cst_icms='40',
                aliquota_icms=Decimal('0'),
                cst_pis='07',
                aliquota_pis=Decimal('0'),
                cst_cofins='07',
                aliquota_cofins=Decimal('0'),
                aliquota_ipi=Decimal('0'),
                ipi_codigo_enquadramento='999',
                origem_mercadoria='0',
                ean='SEM GTIN',
            )
            item.save()
            nf.calcular_totais()
            self.item(f'NotaFiscal RASCUNHO (ID {nf.pk})', True)

        # ── 15. Resumo final ─────────────────────────────────────────────────
        self.stdout.write('')
        sep = '=' * 62
        self.stdout.write(self.style.SUCCESS(sep))
        self.stdout.write(self.style.SUCCESS('  DADOS DE TESTE CRIADOS - RESUMO'))
        self.stdout.write(self.style.SUCCESS(sep))
        self.stdout.write(f'  Empresa    : {empresa.nome}')
        self.stdout.write(f'  CNPJ       : {empresa.cnpj}')
        self.stdout.write(f'  IE         : {empresa.inscricao_estadual}')
        amb = 'HOMOLOGACAO (OK)' if config.ambiente_nfe == '2' else 'PRODUCAO (!)'
        self.stdout.write(f'  Ambiente   : {amb}')
        tok = 'configurado (OK)' if config.has_token else 'NAO configurado (!)'
        self.stdout.write(f'  Token API  : {tok}')
        self.stdout.write('')
        self.stdout.write(f'  Cliente    : {cliente.razao_social}')
        self.stdout.write(f'  CNPJ dest. : {cliente.cnpj_cpf}')
        self.stdout.write('')
        self.stdout.write(f'  Produto    : {produto.nome}')
        self.stdout.write(f'  NCM        : {ncm.codigo} - {ncm.nome}')
        self.stdout.write(f'  CFOP       : 5102 / CST ICMS 40 (Isento) / PIS-COFINS 07')
        self.stdout.write('')
        self.stdout.write(f'  Nota Fiscal: ID {nf.pk} - Status {nf.status}')
        self.stdout.write(f'  Valor Total: R$ {nf.valor_total}')
        self.stdout.write(self.style.SUCCESS(sep))
        self.stdout.write('')

        if not config.has_token:
            self.stdout.write(self.style.WARNING(
                '  [!] Token IntegraNota nao configurado.\n'
                '      Acesse: Faturamento > Configuracao Fiscal > Token IntegraNota\n'
                '      Obtenha em: painel.integranotas.com.br > Configuracoes > API\n'
            ))
        self.stdout.write(self.style.SUCCESS(
            '  Proximos passos:\n'
            f'  1. Acesse Faturamento > Notas Fiscais > ID {nf.pk}\n'
            '  2. Confira os dados da nota e dos itens\n'
            '  3. Clique em "Emitir" para transmitir a SEFAZ (homologacao)\n'
            '  4. Use --limpar para remover a nota de teste quando terminar\n'
        ))

    # ── helpers de output ────────────────────────────────────────────────────
    def ok(self, msg):
        self.stdout.write(self.style.SUCCESS(f'[OK] {msg}'))

    def warn(self, msg):
        self.stdout.write(self.style.WARNING(f'[!]  {msg}'))

    def info(self, msg):
        self.stdout.write(f'     {msg}')

    def item(self, label, created):
        if created:
            self.stdout.write(self.style.SUCCESS(f'  [+] {label} - criado'))
        else:
            self.stdout.write(f'  [.] {label} - ja existia')
