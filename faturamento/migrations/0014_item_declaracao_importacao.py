from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('faturamento', '0013_item_natureza_receita'),
    ]

    operations = [
        migrations.AddField(
            model_name='itemnotafiscal',
            name='di_numero',
            field=models.CharField(blank=True, max_length=12, verbose_name='Nº da DI',
                help_text='Número da Declaração de Importação'),
        ),
        migrations.AddField(
            model_name='itemnotafiscal',
            name='di_data_registro',
            field=models.DateField(blank=True, null=True, verbose_name='Data Registro DI'),
        ),
        migrations.AddField(
            model_name='itemnotafiscal',
            name='di_local_desembaraco',
            field=models.CharField(blank=True, max_length=60, verbose_name='Local do Desembaraço'),
        ),
        migrations.AddField(
            model_name='itemnotafiscal',
            name='di_uf_desembaraco',
            field=models.CharField(blank=True, max_length=2, verbose_name='UF Desembaraço'),
        ),
        migrations.AddField(
            model_name='itemnotafiscal',
            name='di_data_desembaraco',
            field=models.DateField(blank=True, null=True, verbose_name='Data Desembaraço'),
        ),
        migrations.AddField(
            model_name='itemnotafiscal',
            name='di_via_transporte',
            field=models.CharField(blank=True, max_length=2, verbose_name='Via de Transporte',
                choices=[('1','Marítima'),('2','Fluvial'),('3','Lacustre'),('4','Aérea'),
                         ('5','Postal'),('6','Ferroviária'),('7','Rodoviária'),('8','Conduto/Rede'),
                         ('9','Meios Próprios'),('10','Entrada/Saída Ficta'),('11','Courier'),
                         ('12','Em mãos'),('13','Por reboque')]),
        ),
        migrations.AddField(
            model_name='itemnotafiscal',
            name='di_valor_afrmm',
            field=models.DecimalField(default=0, max_digits=14, decimal_places=2,
                verbose_name='Valor AFRMM (R$)'),
        ),
        migrations.AddField(
            model_name='itemnotafiscal',
            name='di_tipo_intermediario',
            field=models.CharField(blank=True, max_length=1, verbose_name='Tipo Intermediário',
                choices=[('1','Conta Própria'),('2','Conta e Ordem'),('3','Encomenda')]),
        ),
        migrations.AddField(
            model_name='itemnotafiscal',
            name='di_cnpj_adquirente',
            field=models.CharField(blank=True, max_length=14, verbose_name='CNPJ Adquirente'),
        ),
        migrations.AddField(
            model_name='itemnotafiscal',
            name='di_codigo_exportador',
            field=models.CharField(blank=True, max_length=60, verbose_name='Código do Exportador'),
        ),
        migrations.AddField(
            model_name='itemnotafiscal',
            name='di_numero_adicao',
            field=models.CharField(blank=True, max_length=3, verbose_name='Nº Adição'),
        ),
        migrations.AddField(
            model_name='itemnotafiscal',
            name='di_codigo_fabricante',
            field=models.CharField(blank=True, max_length=60, verbose_name='Código do Fabricante'),
        ),
        migrations.AddField(
            model_name='itemnotafiscal',
            name='di_desconto_adicao',
            field=models.DecimalField(default=0, max_digits=14, decimal_places=2,
                verbose_name='Desconto da Adição (R$)'),
        ),
        migrations.AddField(
            model_name='itemnotafiscal',
            name='di_numero_drawback',
            field=models.CharField(blank=True, max_length=20,
                verbose_name='Nº Ato Concessório Drawback'),
        ),
    ]
