from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('patrimonio', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PatrimonioAuditoria',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ano', models.PositiveIntegerField(verbose_name='Ano')),
                ('status', models.CharField(choices=[('ABERTA', 'Aberta'), ('FECHADA', 'Fechada')], default='ABERTA', max_length=10, verbose_name='Status')),
                ('data_inicio', models.DateField(auto_now_add=True, verbose_name='Data de Início')),
                ('data_fechamento', models.DateField(blank=True, null=True, verbose_name='Data de Fechamento')),
                ('criado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='auditorias_patrimonio_criadas', to=settings.AUTH_USER_MODEL, verbose_name='Criado por')),
                ('empresa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='auditorias_patrimonio', to='empresas.empresa', verbose_name='Empresa')),
            ],
            options={
                'verbose_name': 'Auditoria de Patrimônio',
                'verbose_name_plural': 'Auditorias de Patrimônio',
                'ordering': ['-ano'],
            },
        ),
        migrations.CreateModel(
            name='PatrimonioAuditoriaItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('numero_patrimonio', models.CharField(max_length=50, verbose_name='Número do Patrimônio')),
                ('descricao', models.CharField(max_length=255, verbose_name='Descrição')),
                ('localizacao', models.CharField(blank=True, max_length=150, verbose_name='Localização')),
                ('responsavel_nome', models.CharField(blank=True, max_length=150, verbose_name='Responsável')),
                ('valor_atual', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, verbose_name='Valor Atual (R$)')),
                ('estado', models.CharField(blank=True, max_length=20, verbose_name='Estado')),
                ('status', models.CharField(choices=[('PENDENTE', 'Pendente'), ('OK', 'OK'), ('NAO_LOCALIZADO', 'Não Localizado'), ('DANIFICADO', 'Danificado'), ('BAIXA', 'Baixa')], default='PENDENTE', max_length=20, verbose_name='Status da Auditoria')),
                ('observacoes', models.TextField(blank=True, verbose_name='Observações')),
                ('foto', models.ImageField(blank=True, null=True, upload_to='patrimonio/auditorias/%Y/%m/', verbose_name='Foto')),
                ('data_verificacao', models.DateTimeField(blank=True, null=True, verbose_name='Data da Verificação')),
                ('auditoria', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='itens', to='patrimonio.patrimonioauditoria', verbose_name='Auditoria')),
                ('patrimonio', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='auditorias_itens', to='patrimonio.patrimonio', verbose_name='Patrimônio')),
            ],
            options={
                'verbose_name': 'Item de Auditoria',
                'verbose_name_plural': 'Itens de Auditoria',
                'ordering': ['numero_patrimonio'],
            },
        ),
        migrations.AddConstraint(
            model_name='patrimonioauditoria',
            constraint=models.UniqueConstraint(fields=('empresa', 'ano'), name='unique_auditoria_por_empresa_ano'),
        ),
    ]
