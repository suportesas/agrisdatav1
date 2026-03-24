# Migration 0072 – Classificação estruturada de Ordens de Serviço
# Cria TipoServicoOS, SubtipoServicoOS, ModalidadeExecucaoOS
# Adiciona FKs em OrdemServico (tipo_servico, subtipo_servico, modalidade_execucao)
# Popula dados padrão e faz backfill das OS existentes

import django.db.models.deletion
from django.db import migrations, models


# ---------------------------------------------------------------------------
# Seed de dados padrão e backfill
# ---------------------------------------------------------------------------

def seed_tipos_servico(apps, schema_editor):
    TipoServicoOS = apps.get_model('cadastros', 'TipoServicoOS')
    SubtipoServicoOS = apps.get_model('cadastros', 'SubtipoServicoOS')
    ModalidadeExecucaoOS = apps.get_model('cadastros', 'ModalidadeExecucaoOS')
    OrdemServico = apps.get_model('cadastros', 'OrdemServico')

    # ---- Tipos e seus subtipos -------------------------------------------
    dados_tipos = [
        {
            'nome': 'Preparo do Solo',
            'tipo_legado': 'PREPARO_SOLO',
            'icone': 'bi-layers',
            'ordem': 1,
            'subtipos': [
                'Aração', 'Gradagem', 'Subsolagem', 'Escarificação', 'Nivelamento',
            ],
        },
        {
            'nome': 'Pulverização',
            'tipo_legado': 'PULV_MECANICA',
            'icone': 'bi-droplet',
            'ordem': 2,
            'subtipos': [
                'Herbicida', 'Inseticida', 'Fungicida', 'Nutrição Foliar', 'Aplicação Biológica',
            ],
        },
        {
            'nome': 'Plantio',
            'tipo_legado': 'PLANTIO',
            'icone': 'bi-tree',
            'ordem': 3,
            'subtipos': ['Semeadura', 'Transplante', 'Replantio'],
        },
        {
            'nome': 'Irrigação',
            'tipo_legado': 'IRRIGACAO',
            'icone': 'bi-water',
            'ordem': 4,
            'subtipos': ['Aspersão', 'Gotejamento', 'Sulco', 'Pivô Central'],
        },
        {
            'nome': 'Adubação',
            'tipo_legado': 'ADUBACAO',
            'icone': 'bi-bag',
            'ordem': 5,
            'subtipos': ['Adubação de Base', 'Cobertura', 'Fertirrigação'],
        },
        {
            'nome': 'Colheita',
            'tipo_legado': 'COLHEITA',
            'icone': 'bi-basket',
            'ordem': 6,
            'subtipos': ['Colheita Manual', 'Colheita Mecanizada'],
        },
        {
            'nome': 'Manutenção de Infraestrutura',
            'tipo_legado': 'MANUTENCAO',
            'icone': 'bi-wrench',
            'ordem': 7,
            'subtipos': ['Cerca', 'Estrada Interna', 'Canal/Drenagem', 'Sistema de Bombeamento'],
        },
        {
            'nome': 'Outro',
            'tipo_legado': 'OUTRO',
            'icone': 'bi-three-dots',
            'ordem': 8,
            'subtipos': ['Operação Diversa'],
        },
    ]

    tipo_map = {}  # tipo_legado -> TipoServicoOS instance
    for dados in dados_tipos:
        subtipos = dados.pop('subtipos')
        tipo = TipoServicoOS.objects.create(empresa=None, ativo=True, **dados)
        tipo_map[tipo.tipo_legado] = tipo
        for i, sub_nome in enumerate(subtipos, 1):
            SubtipoServicoOS.objects.create(
                tipo_servico=tipo,
                empresa=None,
                nome=sub_nome,
                descricao='',
                ordem=i,
                ativo=True,
            )

    # Pulverização também pode ter legado PULV_COSTAL (mapeado para o mesmo tipo)
    tipo_map['PULV_COSTAL'] = tipo_map['PULV_MECANICA']

    # ---- Modalidades -------------------------------------------------------
    modalidades_data = [
        ('Manual', 1),
        ('Costal', 2),
        ('Tratorizada', 3),
        ('Autopropelida', 4),
        ('Drone', 5),
        ('Terceirizada', 6),
    ]
    modalidade_map = {}
    for nome, ordem in modalidades_data:
        m = ModalidadeExecucaoOS.objects.create(
            empresa=None, nome=nome, descricao='', ordem=ordem, ativo=True,
        )
        modalidade_map[nome] = m

    # ---- Backfill OS existentes -------------------------------------------
    for os_obj in OrdemServico.objects.all():
        legado = os_obj.tipo
        tipo_obj = tipo_map.get(legado)
        if tipo_obj:
            os_obj.tipo_servico = tipo_obj
        if legado == 'PULV_COSTAL':
            os_obj.modalidade_execucao = modalidade_map.get('Costal')
        os_obj.save()


def reverse_seed(apps, schema_editor):
    TipoServicoOS = apps.get_model('cadastros', 'TipoServicoOS')
    ModalidadeExecucaoOS = apps.get_model('cadastros', 'ModalidadeExecucaoOS')
    # Remove apenas os globais criados pelo seed
    TipoServicoOS.objects.filter(empresa=None).delete()
    ModalidadeExecucaoOS.objects.filter(empresa=None).delete()


# ---------------------------------------------------------------------------
# Migration
# ---------------------------------------------------------------------------

class Migration(migrations.Migration):

    dependencies = [
        ('cadastros', '0071_custohoramaquina_ordemservico_custotalhao_and_more'),
        ('empresas', '0021_empresa_bairro'),
    ]

    operations = [
        # 1. Criar TipoServicoOS
        migrations.CreateModel(
            name='TipoServicoOS',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=100, verbose_name='Nome')),
                ('descricao', models.CharField(blank=True, max_length=255, verbose_name='Descrição')),
                ('icone', models.CharField(blank=True, default='bi-tools', max_length=60, verbose_name='Ícone Bootstrap')),
                ('ordem', models.PositiveSmallIntegerField(default=0, verbose_name='Ordem')),
                ('ativo', models.BooleanField(default=True, verbose_name='Ativo')),
                ('tipo_legado', models.CharField(blank=True, help_text='Valor correspondente no campo tipo legado da OS', max_length=30, verbose_name='Tipo Legado')),
                ('empresa', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='tipos_servico_os',
                    to='empresas.empresa',
                    verbose_name='Empresa',
                    help_text='Deixe em branco para tipos globais disponíveis a todas as empresas',
                )),
            ],
            options={
                'verbose_name': 'Tipo de Serviço (OS)',
                'verbose_name_plural': 'Tipos de Serviço (OS)',
                'ordering': ['ordem', 'nome'],
            },
        ),

        # 2. Criar SubtipoServicoOS
        migrations.CreateModel(
            name='SubtipoServicoOS',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=100, verbose_name='Nome')),
                ('descricao', models.CharField(blank=True, max_length=255, verbose_name='Descrição')),
                ('ordem', models.PositiveSmallIntegerField(default=0, verbose_name='Ordem')),
                ('ativo', models.BooleanField(default=True, verbose_name='Ativo')),
                ('empresa', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='subtipos_servico_os',
                    to='empresas.empresa',
                    verbose_name='Empresa',
                    help_text='Deixe em branco para registros globais',
                )),
                ('tipo_servico', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='subtipos',
                    to='cadastros.tiposervicoos',
                    verbose_name='Tipo de Serviço',
                )),
            ],
            options={
                'verbose_name': 'Operação de Serviço (OS)',
                'verbose_name_plural': 'Operações de Serviço (OS)',
                'ordering': ['tipo_servico__ordem', 'ordem', 'nome'],
            },
        ),

        # 3. Criar ModalidadeExecucaoOS
        migrations.CreateModel(
            name='ModalidadeExecucaoOS',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=100, verbose_name='Nome')),
                ('descricao', models.CharField(blank=True, max_length=255, verbose_name='Descrição')),
                ('ordem', models.PositiveSmallIntegerField(default=0, verbose_name='Ordem')),
                ('ativo', models.BooleanField(default=True, verbose_name='Ativo')),
                ('empresa', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='modalidades_execucao_os',
                    to='empresas.empresa',
                    verbose_name='Empresa',
                    help_text='Deixe em branco para modalidades globais',
                )),
            ],
            options={
                'verbose_name': 'Modalidade de Execução (OS)',
                'verbose_name_plural': 'Modalidades de Execução (OS)',
                'ordering': ['ordem', 'nome'],
            },
        ),

        # 4. Adicionar FKs em OrdemServico
        migrations.AddField(
            model_name='ordemservico',
            name='tipo_servico',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='ordens_servico',
                to='cadastros.tiposervicoos',
                verbose_name='Tipo de Serviço',
            ),
        ),
        migrations.AddField(
            model_name='ordemservico',
            name='subtipo_servico',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='ordens_servico',
                to='cadastros.subtiposervicoos',
                verbose_name='Operação',
            ),
        ),
        migrations.AddField(
            model_name='ordemservico',
            name='modalidade_execucao',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='ordens_servico',
                to='cadastros.modalidadeexecucaoos',
                verbose_name='Modalidade de Execução',
            ),
        ),

        # 5. Tornar tipo legado opcional (será sincronizado automaticamente)
        migrations.AlterField(
            model_name='ordemservico',
            name='tipo',
            field=models.CharField(
                blank=True,
                choices=[
                    ('PREPARO_SOLO', 'Preparo de Solo'),
                    ('PULV_MECANICA', 'Pulverização Mecânica'),
                    ('PULV_COSTAL', 'Pulverização Costal'),
                    ('PLANTIO', 'Plantio'),
                    ('IRRIGACAO', 'Irrigação'),
                    ('ADUBACAO', 'Adubação/Fertirrigação'),
                    ('COLHEITA', 'Colheita'),
                    ('MANUTENCAO', 'Manutenção de Infraestrutura'),
                    ('OUTRO', 'Outro'),
                ],
                max_length=30,
                verbose_name='Tipo de Serviço',
            ),
        ),

        # 6. Seed de dados padrão + backfill das OS existentes
        migrations.RunPython(seed_tipos_servico, reverse_code=reverse_seed),
    ]
