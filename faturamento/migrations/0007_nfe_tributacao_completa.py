from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('faturamento', '0006_encrypt_token_integranotas'),
    ]

    operations = [
        # NotaFiscal — novos campos
        migrations.AddField(
            model_name='notafiscal',
            name='finalidade_nfe',
            field=models.CharField(
                choices=[('1', '1 - NF-e Normal'), ('2', '2 - NF-e Complementar'),
                         ('3', '3 - NF-e de Ajuste'), ('4', '4 - Devolução de Mercadoria')],
                default='1', max_length=1, verbose_name='Finalidade NF-e',
            ),
        ),
        migrations.AddField(
            model_name='notafiscal',
            name='informacoes_fisco',
            field=models.TextField(blank=True, verbose_name='Informações para o Fisco (infAdFisco)'),
        ),
        migrations.AddField(
            model_name='notafiscal',
            name='valor_icms_st',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14, verbose_name='Valor ICMS ST'),
        ),
        migrations.AlterField(
            model_name='notafiscal',
            name='presenca_comprador',
            field=models.CharField(
                choices=[('0', '0 - Não se aplica'), ('1', '1 - Operação presencial'),
                         ('2', '2 - Operação não presencial, Internet'),
                         ('3', '3 - Operação não presencial, Teleatendimento'),
                         ('4', '4 - NFC-e em operação com entrega em domicílio'),
                         ('9', '9 - Operação não presencial, Outros')],
                default='9', max_length=1, verbose_name='Presença do Comprador',
            ),
        ),

        # ItemNotaFiscal — campos ICMS / ST / IPI adicionais
        migrations.AddField(
            model_name='itemnotafiscal',
            name='icms_modalidade_base',
            field=models.CharField(
                default='3', max_length=1, verbose_name='Modalidade BC ICMS',
                help_text='0=MVA, 1=Pauta, 2=Preço Tabelado, 3=Valor da Operação',
            ),
        ),
        migrations.AddField(
            model_name='itemnotafiscal',
            name='icms_reducao_base',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5, verbose_name='Redução BC ICMS (%)'),
        ),
        migrations.AddField(
            model_name='itemnotafiscal',
            name='icms_st_aliquota',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5, verbose_name='Alíq. ICMS ST (%)'),
        ),
        migrations.AddField(
            model_name='itemnotafiscal',
            name='icms_st_mva',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5, verbose_name='MVA ST (%)'),
        ),
        migrations.AddField(
            model_name='itemnotafiscal',
            name='icms_st_reducao_base',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5, verbose_name='Redução BC ST (%)'),
        ),
        migrations.AddField(
            model_name='itemnotafiscal',
            name='icms_st_base_calculo',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14, verbose_name='BC ICMS ST'),
        ),
        migrations.AddField(
            model_name='itemnotafiscal',
            name='valor_icms_st',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14, verbose_name='Valor ICMS ST'),
        ),
        migrations.AddField(
            model_name='itemnotafiscal',
            name='cst_ipi',
            field=models.CharField(blank=True, default='99', max_length=2, verbose_name='CST IPI'),
        ),

        # Novo modelo PagamentoNF
        migrations.CreateModel(
            name='PagamentoNF',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('meio_pagamento', models.CharField(
                    choices=[('01', 'Dinheiro'), ('02', 'Cheque'), ('03', 'Cartão de Crédito'),
                             ('04', 'Cartão de Débito'), ('05', 'Crédito Loja'),
                             ('14', 'Duplicata Mercantil'), ('15', 'Boleto Bancário'),
                             ('16', 'Depósito Bancário'), ('17', 'PIX'),
                             ('18', 'Transferência Bancária / TED'), ('90', 'Sem Pagamento'), ('99', 'Outros')],
                    default='17', max_length=2, verbose_name='Meio de Pagamento',
                )),
                ('valor', models.DecimalField(decimal_places=2, default=0, max_digits=14, verbose_name='Valor')),
                ('nota_fiscal', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='pagamentos', to='faturamento.notafiscal', verbose_name='Nota Fiscal',
                )),
            ],
            options={'verbose_name': 'Pagamento NF', 'verbose_name_plural': 'Pagamentos NF'},
        ),

        # Novo modelo DuplicataNF
        migrations.CreateModel(
            name='DuplicataNF',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('numero', models.CharField(blank=True, max_length=60, verbose_name='Número')),
                ('vencimento', models.DateField(verbose_name='Vencimento')),
                ('valor', models.DecimalField(decimal_places=2, max_digits=14, verbose_name='Valor')),
                ('nota_fiscal', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='duplicatas', to='faturamento.notafiscal', verbose_name='Nota Fiscal',
                )),
            ],
            options={'verbose_name': 'Duplicata NF', 'verbose_name_plural': 'Duplicatas NF', 'ordering': ['vencimento']},
        ),
    ]
