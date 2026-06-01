from django.core.management.base import BaseCommand
from django.db import transaction

from empresas.models import Empresa
from plano_contas.models import ContaContabil

# (codigo, nome, tipo, natureza, analitica, codigo_pai)
PLANO_PADRAO = [
    ('1', 'ATIVO', 'ATIVO', 'DEVEDORA', False, None),
    ('1.1', 'Ativo Circulante', 'ATIVO', 'DEVEDORA', False, '1'),
    ('1.1.01', 'Disponível', 'ATIVO', 'DEVEDORA', False, '1.1'),
    ('1.1.01.001', 'Caixa', 'ATIVO', 'DEVEDORA', True, '1.1.01'),
    ('1.1.01.002', 'Bancos Conta Movimento', 'ATIVO', 'DEVEDORA', True, '1.1.01'),
    ('1.1.02', 'Créditos a Receber', 'ATIVO', 'DEVEDORA', False, '1.1'),
    ('1.1.02.001', 'Clientes - Mercado Interno', 'ATIVO', 'DEVEDORA', True, '1.1.02'),
    ('1.1.02.002', 'Clientes - Exportação', 'ATIVO', 'DEVEDORA', True, '1.1.02'),
    ('1.1.02.003', 'Adiantamentos a Fornecedores', 'ATIVO', 'DEVEDORA', True, '1.1.02'),
    ('1.1.02.004', 'Outros Créditos a Receber', 'ATIVO', 'DEVEDORA', True, '1.1.02'),
    ('1.1.03', 'Estoques', 'ATIVO', 'DEVEDORA', False, '1.1'),
    ('1.1.03.001', 'Estoque de Produtos Agrícolas', 'ATIVO', 'DEVEDORA', True, '1.1.03'),
    ('1.1.03.002', 'Estoque de Insumos Agrícolas', 'ATIVO', 'DEVEDORA', True, '1.1.03'),
    ('1.1.03.003', 'Estoque de Embalagens', 'ATIVO', 'DEVEDORA', True, '1.1.03'),
    ('1.1.04', 'Despesas Antecipadas', 'ATIVO', 'DEVEDORA', False, '1.1'),
    ('1.1.04.001', 'Seguros a Apropriar', 'ATIVO', 'DEVEDORA', True, '1.1.04'),
    ('1.1.04.002', 'Outras Despesas Antecipadas', 'ATIVO', 'DEVEDORA', True, '1.1.04'),
    ('1.2', 'Ativo Não Circulante', 'ATIVO', 'DEVEDORA', False, '1'),
    ('1.2.01', 'Realizável a Longo Prazo', 'ATIVO', 'DEVEDORA', False, '1.2'),
    ('1.2.01.001', 'Créditos a Longo Prazo', 'ATIVO', 'DEVEDORA', True, '1.2.01'),
    ('1.2.02', 'Imobilizado', 'ATIVO', 'DEVEDORA', False, '1.2'),
    ('1.2.02.001', 'Terrenos e Terras', 'ATIVO', 'DEVEDORA', True, '1.2.02'),
    ('1.2.02.002', 'Benfeitorias e Construções', 'ATIVO', 'DEVEDORA', True, '1.2.02'),
    ('1.2.02.003', 'Máquinas e Equipamentos Agrícolas', 'ATIVO', 'DEVEDORA', True, '1.2.02'),
    ('1.2.02.004', 'Veículos e Tratores', 'ATIVO', 'DEVEDORA', True, '1.2.02'),
    ('1.2.02.005', 'Equipamentos de Informática', 'ATIVO', 'DEVEDORA', True, '1.2.02'),
    ('1.2.02.006', '(-) Depreciação Acumulada', 'ATIVO', 'CREDORA', True, '1.2.02'),
    ('2', 'PASSIVO', 'PASSIVO', 'CREDORA', False, None),
    ('2.1', 'Passivo Circulante', 'PASSIVO', 'CREDORA', False, '2'),
    ('2.1.01', 'Fornecedores', 'PASSIVO', 'CREDORA', False, '2.1'),
    ('2.1.01.001', 'Fornecedores - Mercado Interno', 'PASSIVO', 'CREDORA', True, '2.1.01'),
    ('2.1.01.002', 'Fornecedores - Importação', 'PASSIVO', 'CREDORA', True, '2.1.01'),
    ('2.1.02', 'Obrigações Fiscais', 'PASSIVO', 'CREDORA', False, '2.1'),
    ('2.1.02.001', 'ICMS a Recolher', 'PASSIVO', 'CREDORA', True, '2.1.02'),
    ('2.1.02.002', 'PIS/COFINS a Recolher', 'PASSIVO', 'CREDORA', True, '2.1.02'),
    ('2.1.02.003', 'IRPJ/CSLL a Recolher', 'PASSIVO', 'CREDORA', True, '2.1.02'),
    ('2.1.03', 'Obrigações Trabalhistas', 'PASSIVO', 'CREDORA', False, '2.1'),
    ('2.1.03.001', 'Salários a Pagar', 'PASSIVO', 'CREDORA', True, '2.1.03'),
    ('2.1.03.002', 'Encargos Sociais a Recolher', 'PASSIVO', 'CREDORA', True, '2.1.03'),
    ('2.1.04', 'Outras Obrigações', 'PASSIVO', 'CREDORA', False, '2.1'),
    ('2.1.04.001', 'Adiantamentos de Clientes', 'PASSIVO', 'CREDORA', True, '2.1.04'),
    ('2.2', 'Passivo Não Circulante', 'PASSIVO', 'CREDORA', False, '2'),
    ('2.2.01', 'Empréstimos e Financiamentos', 'PASSIVO', 'CREDORA', False, '2.2'),
    ('2.2.01.001', 'Financiamentos Bancários - LP', 'PASSIVO', 'CREDORA', True, '2.2.01'),
    ('2.2.01.002', 'Crédito Rural - LP', 'PASSIVO', 'CREDORA', True, '2.2.01'),
    ('3', 'PATRIMÔNIO LÍQUIDO', 'PATRIMONIO_LIQUIDO', 'CREDORA', False, None),
    ('3.1', 'Capital Social', 'PATRIMONIO_LIQUIDO', 'CREDORA', False, '3'),
    ('3.1.01', 'Capital Subscrito', 'PATRIMONIO_LIQUIDO', 'CREDORA', False, '3.1'),
    ('3.1.01.001', 'Capital Social Integralizado', 'PATRIMONIO_LIQUIDO', 'CREDORA', True, '3.1.01'),
    ('3.2', 'Reservas', 'PATRIMONIO_LIQUIDO', 'CREDORA', False, '3'),
    ('3.2.01.001', 'Reserva Legal', 'PATRIMONIO_LIQUIDO', 'CREDORA', True, '3.2'),
    ('3.3', 'Resultados Acumulados', 'PATRIMONIO_LIQUIDO', 'CREDORA', False, '3'),
    ('3.3.01.001', 'Lucros Acumulados', 'PATRIMONIO_LIQUIDO', 'CREDORA', True, '3.3'),
    ('3.3.01.002', 'Prejuízos Acumulados', 'PATRIMONIO_LIQUIDO', 'DEVEDORA', True, '3.3'),
    ('4', 'RECEITAS', 'RECEITA', 'CREDORA', False, None),
    ('4.1', 'Receita Bruta de Vendas', 'RECEITA', 'CREDORA', False, '4'),
    ('4.1.01', 'Vendas de Produtos Agrícolas', 'RECEITA', 'CREDORA', False, '4.1'),
    ('4.1.01.001', 'Vendas - Mercado Interno', 'RECEITA', 'CREDORA', True, '4.1.01'),
    ('4.1.01.002', 'Vendas - Exportação', 'RECEITA', 'CREDORA', True, '4.1.01'),
    ('4.2', 'Deduções da Receita Bruta', 'RECEITA', 'DEVEDORA', False, '4'),
    ('4.2.01.001', '(-) Devoluções e Abatimentos', 'RECEITA', 'DEVEDORA', True, '4.2'),
    ('4.2.01.002', '(-) ICMS sobre Vendas', 'RECEITA', 'DEVEDORA', True, '4.2'),
    ('4.3', 'Outras Receitas', 'RECEITA', 'CREDORA', False, '4'),
    ('4.3.01.001', 'Receitas Financeiras', 'RECEITA', 'CREDORA', True, '4.3'),
    ('4.3.01.002', 'Receitas de Prestação de Serviços', 'RECEITA', 'CREDORA', True, '4.3'),
    ('5', 'CUSTOS', 'CUSTO', 'DEVEDORA', False, None),
    ('5.1', 'Custo das Mercadorias Vendidas', 'CUSTO', 'DEVEDORA', False, '5'),
    ('5.1.01.001', 'CMV - Produtos Agrícolas', 'CUSTO', 'DEVEDORA', True, '5.1'),
    ('5.2', 'Custo de Produção Agrícola', 'CUSTO', 'DEVEDORA', False, '5'),
    ('5.2.01', 'Insumos Agrícolas', 'CUSTO', 'DEVEDORA', False, '5.2'),
    ('5.2.01.001', 'Sementes e Mudas', 'CUSTO', 'DEVEDORA', True, '5.2.01'),
    ('5.2.01.002', 'Fertilizantes e Corretivos', 'CUSTO', 'DEVEDORA', True, '5.2.01'),
    ('5.2.01.003', 'Defensivos Agrícolas', 'CUSTO', 'DEVEDORA', True, '5.2.01'),
    ('5.2.01.004', 'Combustíveis e Lubrificantes', 'CUSTO', 'DEVEDORA', True, '5.2.01'),
    ('5.2.02', 'Mão de Obra Rural', 'CUSTO', 'DEVEDORA', False, '5.2'),
    ('5.2.02.001', 'Salários - Trabalhadores Rurais', 'CUSTO', 'DEVEDORA', True, '5.2.02'),
    ('5.2.02.002', 'Encargos Sociais - Rural', 'CUSTO', 'DEVEDORA', True, '5.2.02'),
    ('5.2.03', 'Depreciação de Bens Rurais', 'CUSTO', 'DEVEDORA', False, '5.2'),
    ('5.2.03.001', 'Depreciação - Máquinas Agrícolas', 'CUSTO', 'DEVEDORA', True, '5.2.03'),
    ('5.2.03.002', 'Depreciação - Benfeitorias Rurais', 'CUSTO', 'DEVEDORA', True, '5.2.03'),
    ('6', 'DESPESAS', 'DESPESA', 'DEVEDORA', False, None),
    ('6.1', 'Despesas Administrativas', 'DESPESA', 'DEVEDORA', False, '6'),
    ('6.1.01.001', 'Salários - Administrativos', 'DESPESA', 'DEVEDORA', True, '6.1'),
    ('6.1.01.002', 'Encargos Sociais - Administrativos', 'DESPESA', 'DEVEDORA', True, '6.1'),
    ('6.1.01.003', 'Aluguel e Condomínio', 'DESPESA', 'DEVEDORA', True, '6.1'),
    ('6.1.01.004', 'Energia Elétrica', 'DESPESA', 'DEVEDORA', True, '6.1'),
    ('6.1.01.005', 'Comunicações e Internet', 'DESPESA', 'DEVEDORA', True, '6.1'),
    ('6.1.01.006', 'Serviços de Terceiros - PJ', 'DESPESA', 'DEVEDORA', True, '6.1'),
    ('6.1.01.007', 'Material de Escritório', 'DESPESA', 'DEVEDORA', True, '6.1'),
    ('6.2', 'Despesas Comerciais', 'DESPESA', 'DEVEDORA', False, '6'),
    ('6.2.01.001', 'Fretes e Carretos', 'DESPESA', 'DEVEDORA', True, '6.2'),
    ('6.2.01.002', 'Comissões de Vendedores', 'DESPESA', 'DEVEDORA', True, '6.2'),
    ('6.2.01.003', 'Propaganda e Publicidade', 'DESPESA', 'DEVEDORA', True, '6.2'),
    ('6.3', 'Despesas Financeiras', 'DESPESA', 'DEVEDORA', False, '6'),
    ('6.3.01.001', 'Juros Passivos', 'DESPESA', 'DEVEDORA', True, '6.3'),
    ('6.3.01.002', 'Multas e Encargos Financeiros', 'DESPESA', 'DEVEDORA', True, '6.3'),
    ('6.3.01.003', 'Tarifas Bancárias', 'DESPESA', 'DEVEDORA', True, '6.3'),
    ('6.3.01.004', 'Variação Cambial Passiva', 'DESPESA', 'DEVEDORA', True, '6.3'),
    ('6.4', 'Depreciação e Amortização', 'DESPESA', 'DEVEDORA', False, '6'),
    ('6.4.01.001', 'Depreciação - Equipamentos Admin.', 'DESPESA', 'DEVEDORA', True, '6.4'),
    ('6.4.01.002', 'Amortização de Intangíveis', 'DESPESA', 'DEVEDORA', True, '6.4'),
]


class Command(BaseCommand):
    help = 'Popula o Plano de Contas padrão agrícola brasileiro para uma ou todas as empresas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--empresa-id',
            type=int,
            help='ID da empresa (omitir para todas as empresas ativas)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Reimportar mesmo que a empresa já possua contas',
        )

    def handle(self, *args, **options):
        empresa_id = options.get('empresa_id')
        force = options.get('force')

        if empresa_id:
            empresas = Empresa.objects.filter(pk=empresa_id)
            if not empresas.exists():
                self.stderr.write(self.style.ERROR(f'Empresa ID {empresa_id} não encontrada.'))
                return
        else:
            empresas = Empresa.objects.filter(ativa=True)

        for empresa in empresas:
            if not force and ContaContabil.objects.filter(empresa=empresa).exists():
                self.stdout.write(
                    f'[{empresa.nome}] Já possui contas cadastradas. '
                    'Use --force para reimportar.'
                )
                continue

            self._importar_para_empresa(empresa)

    def _importar_para_empresa(self, empresa):
        self.stdout.write(f'[{empresa.nome}] Importando plano de contas...')
        codigo_para_obj = {}

        with transaction.atomic():
            for codigo, nome, tipo, natureza, analitica, pai_codigo in PLANO_PADRAO:
                pai = codigo_para_obj.get(pai_codigo) if pai_codigo else None
                conta, created = ContaContabil.objects.update_or_create(
                    empresa=empresa,
                    codigo=codigo,
                    defaults={
                        'nome': nome,
                        'tipo': tipo,
                        'natureza': natureza,
                        'analitica': analitica,
                        'conta_pai': pai,
                        'ativo': True,
                    },
                )
                codigo_para_obj[codigo] = conta

        total = len(PLANO_PADRAO)
        self.stdout.write(
            self.style.SUCCESS(f'[{empresa.nome}] {total} contas importadas com sucesso.')
        )
