from django.db import migrations, models
import django.core.validators


def seed_tipos_usuario(apps, schema_editor):
    TipoUsuario = apps.get_model('usuarios', 'TipoUsuario')
    defaults = [
        {
            'codigo': 'ADMIN',
            'nome': 'Administrador',
            'descricao': 'Administrador da empresa com acesso ampliado.',
            'ordem': 10,
            'protegido': True,
            'administrador_empresa': True,
            'permite_gerenciar_usuarios': True,
            'permite_acessar_financeiro': True,
            'permite_fazer_vendas': True,
        },
        {
            'codigo': 'GERENTE',
            'nome': 'Gerente',
            'descricao': 'Gerencia usuários e acompanha operações da empresa.',
            'ordem': 20,
            'protegido': True,
            'administrador_empresa': False,
            'permite_gerenciar_usuarios': True,
            'permite_acessar_financeiro': True,
            'permite_fazer_vendas': True,
        },
        {
            'codigo': 'FUNC',
            'nome': 'Funcionário',
            'descricao': 'Perfil operacional padrão.',
            'ordem': 30,
            'protegido': True,
            'administrador_empresa': False,
            'permite_gerenciar_usuarios': False,
            'permite_acessar_financeiro': False,
            'permite_fazer_vendas': False,
        },
        {
            'codigo': 'PROD',
            'nome': 'Produtor',
            'descricao': 'Perfil voltado para operação de produção.',
            'ordem': 40,
            'protegido': True,
            'administrador_empresa': False,
            'permite_gerenciar_usuarios': False,
            'permite_acessar_financeiro': False,
            'permite_fazer_vendas': False,
        },
        {
            'codigo': 'VENDEDOR',
            'nome': 'Vendedor',
            'descricao': 'Perfil comercial com acesso a vendas.',
            'ordem': 50,
            'protegido': True,
            'administrador_empresa': False,
            'permite_gerenciar_usuarios': False,
            'permite_acessar_financeiro': False,
            'permite_fazer_vendas': True,
        },
        {
            'codigo': 'FINANCEIRO',
            'nome': 'Financeiro',
            'descricao': 'Perfil com acesso financeiro.',
            'ordem': 60,
            'protegido': True,
            'administrador_empresa': False,
            'permite_gerenciar_usuarios': False,
            'permite_acessar_financeiro': True,
            'permite_fazer_vendas': False,
        },
    ]

    for item in defaults:
        TipoUsuario.objects.update_or_create(codigo=item['codigo'], defaults=item)


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0006_trocasenhaemergencial'),
    ]

    operations = [
        migrations.CreateModel(
            name='TipoUsuario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo', models.CharField(help_text='Identificador interno usado nas regras do sistema. Ex.: SUPORTE.', max_length=30, unique=True, validators=[django.core.validators.RegexValidator(message='O código deve conter apenas letras maiúsculas, números e underscore.', regex='^[A-Z0-9_]+$')], verbose_name='Código')),
                ('nome', models.CharField(max_length=60, verbose_name='Nome')),
                ('descricao', models.TextField(blank=True, verbose_name='Descrição')),
                ('ordem', models.PositiveIntegerField(default=100, verbose_name='Ordem')),
                ('ativo', models.BooleanField(default=True, verbose_name='Ativo')),
                ('protegido', models.BooleanField(default=False, help_text='Tipos protegidos não podem ser excluídos pelo CRUD.', verbose_name='Protegido')),
                ('administrador_empresa', models.BooleanField(default=False, help_text='Libera as ações administrativas e permissões equivalentes a admin.', verbose_name='Conta como administrador da empresa')),
                ('permite_gerenciar_usuarios', models.BooleanField(default=False, verbose_name='Pode gerenciar usuários')),
                ('permite_acessar_financeiro', models.BooleanField(default=False, verbose_name='Pode acessar financeiro')),
                ('permite_fazer_vendas', models.BooleanField(default=False, verbose_name='Pode fazer vendas')),
            ],
            options={
                'verbose_name': 'Tipo de Usuário',
                'verbose_name_plural': 'Tipos de Usuário',
                'ordering': ['ordem', 'nome'],
            },
        ),
        migrations.RunPython(seed_tipos_usuario, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='usuario',
            name='tipo',
            field=models.CharField(db_index=True, default='FUNC', help_text='Código do tipo de usuário configurado no cadastro de tipos.', max_length=30, verbose_name='Tipo de Usuário'),
        ),
        migrations.AddIndex(
            model_name='tipousuario',
            index=models.Index(fields=['ativo', 'ordem'], name='usuarios_ti_ativo_4a63bc_idx'),
        ),
        migrations.AddIndex(
            model_name='tipousuario',
            index=models.Index(fields=['codigo'], name='usuarios_ti_codigo_1dfe07_idx'),
        ),
    ]