from django.db import migrations, models
import django.db.models.deletion


def create_fornecedor_group(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')

    group, _ = Group.objects.get_or_create(name='FORNECEDOR')

    codenames = [
        'view_pedidocompra',
        'view_itempedidocompra',
        'view_recebimentocompra',
        'view_divergenciarecebimento',
        'view_avaliacaofornecedor',
        'view_pedidocompramensagem',
        'add_pedidocompramensagem',
    ]

    perms = Permission.objects.filter(codename__in=codenames)
    for perm in perms:
        group.permissions.add(perm)


def remove_fornecedor_group(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name='FORNECEDOR').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('compras', '0019_tipodivergencia_divergenciarecebimento_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='PedidoCompraMensagem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mensagem', models.TextField(verbose_name='Mensagem')),
                ('data_envio', models.DateTimeField(auto_now_add=True, verbose_name='Data de Envio')),
                ('autor', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='mensagens_pedido_compra', to='usuarios.usuario', verbose_name='Autor')),
                ('pedido', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mensagens', to='compras.pedidocompra', verbose_name='Pedido')),
            ],
            options={
                'verbose_name': 'Mensagem do Pedido de Compra',
                'verbose_name_plural': 'Mensagens dos Pedidos de Compra',
                'ordering': ['data_envio'],
            },
        ),
        migrations.RunPython(create_fornecedor_group, remove_fornecedor_group),
    ]
