from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('cadastros', '0030_add_ncm'),
    ]

    operations = [
        migrations.CreateModel(
            name='EmpresaNCM',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo', models.CharField(max_length=8, verbose_name='Código NCM')),
                ('nome', models.CharField(max_length=255, verbose_name='Descrição')),
                ('descricao', models.TextField(blank=True, verbose_name='Observações')),
                ('cest', models.CharField(blank=True, max_length=10, verbose_name='CEST')),
                ('ativo', models.BooleanField(default=True, verbose_name='Ativo')),
                ('criado_em', models.DateTimeField(auto_now_add=True, verbose_name='Data de criação')),
                ('atualizado_em', models.DateTimeField(auto_now=True, verbose_name='Última atualização')),
                ('template', models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, to='cadastros.ncm')),
                ('empresa', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='ncms', to='empresas.empresa')),
            ],
            options={
                'verbose_name': 'NCM da Empresa',
                'verbose_name_plural': 'NCMs das Empresas',
                'ordering': ['codigo'],
            },
        ),
        migrations.AddIndex(
            model_name='empresancm',
            index=models.Index(fields=['empresa', 'codigo'], name='cadastros_empresan_codigo_idx'),
        ),
        migrations.AddConstraint(
            model_name='empresancm',
            constraint=models.UniqueConstraint(fields=('empresa', 'codigo'), name='unique_ncm_per_empresa'),
        ),
    ]
