"""
Registra os 5 models de empréstimo no estado Django do app emprestimos.
Sem SQL — as tabelas permanecem com o mesmo nome (db_table = 'cadastros_*').
"""
from django.conf import settings
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('cadastros', '0109_remove_mip_models'),
        ('empresas', '0001_initial'),
        ('produtos', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name='EmprestimoProdutor',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('direcao', models.CharField(choices=[('EMPRESA_PARA_PRODUTOR', 'Empresa para Produtor'), ('PRODUTOR_PARA_EMPRESA', 'Produtor para Empresa')], default='EMPRESA_PARA_PRODUTOR', max_length=30, verbose_name='Direção')),
                        ('data_emprestimo', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Data do Empréstimo')),
                        ('data_promessa_devolucao', models.DateField(blank=True, null=True, verbose_name='Data Promessa de Devolução')),
                        ('status', models.CharField(choices=[('PROMESSA', 'Promessa de Devolução'), ('NORMAL', 'Empréstimo Normal'), ('PARCIAL', 'Devolução Parcial'), ('DEVOLVIDO', 'Devolvido'), ('CANCELADO', 'Cancelado')], default='NORMAL', max_length=20, verbose_name='Status')),
                        ('assinatura_liberador_imagem', models.ImageField(blank=True, null=True, upload_to='emprestimos/assinaturas/%Y/%m/', verbose_name='Assinatura Eletrônica do Liberador')),
                        ('assinatura_liberador_nome', models.CharField(blank=True, max_length=120, verbose_name='Nome do Liberador')),
                        ('assinatura_liberador_datahora', models.DateTimeField(blank=True, null=True, verbose_name='Data/Hora da Assinatura do Liberador')),
                        ('assinatura_produtor_imagem', models.ImageField(blank=True, null=True, upload_to='emprestimos/assinaturas/%Y/%m/', verbose_name='Assinatura Eletrônica do Produtor')),
                        ('assinatura_produtor_nome', models.CharField(blank=True, max_length=120, verbose_name='Nome do Produtor Assinante')),
                        ('assinatura_produtor_datahora', models.DateTimeField(blank=True, null=True, verbose_name='Data/Hora da Assinatura do Produtor')),
                        ('quantidade_emprestada', models.DecimalField(decimal_places=3, max_digits=15, verbose_name='Quantidade Emprestada')),
                        ('quantidade_devolvida', models.DecimalField(decimal_places=3, default=0, max_digits=15, verbose_name='Quantidade Devolvida')),
                        ('saldo_pendente', models.DecimalField(decimal_places=3, default=0, max_digits=15, verbose_name='Saldo Pendente')),
                        ('observacoes', models.TextField(blank=True, verbose_name='Observações')),
                        ('criado_em', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                        ('atualizado_em', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                        ('aceite_produtor', models.BooleanField(default=False, verbose_name='Aceite do Produtor')),
                        ('aceite_produtor_data', models.DateTimeField(blank=True, null=True, verbose_name='Data do Aceite')),
                        ('aceite_editavel', models.BooleanField(default=True, verbose_name='Aceite editável (apenas empresa pode reverter)')),
                        ('aceite_produtor_usuario', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='emprestimos_aceitos_como_produtor', to=settings.AUTH_USER_MODEL, verbose_name='Usuário que deu o aceite')),
                        ('assinatura_produtor_usuario', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='emprestimos_assinados_como_produtor', to=settings.AUTH_USER_MODEL, verbose_name='Usuário do Portal do Produtor')),
                        ('criado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='emprestimos_criados', to=settings.AUTH_USER_MODEL)),
                        ('empresa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='emprestimos_produtor', to='empresas.empresa')),
                        ('liberado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='emprestimos_liberados', to=settings.AUTH_USER_MODEL, verbose_name='Liberado por')),
                        ('produto', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='emprestimos_produtor', to='produtos.produto')),
                        ('produtor', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='emprestimos', to='cadastros.produtor')),
                        ('requisicao', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='emprestimos_gerados', to='cadastros.requisicao')),
                        ('requisicao_item', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='emprestimos_gerados', to='cadastros.requisicaoitem')),
                        ('unidade_medida', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='emprestimos_produtor', to='produtos.unidademedida')),
                    ],
                    options={
                        'verbose_name': 'Empréstimo de Produtor',
                        'verbose_name_plural': 'Empréstimos de Produtores',
                        'db_table': 'cadastros_emprestimoprodutor',
                        'ordering': ['-data_emprestimo'],
                    },
                ),
                migrations.CreateModel(
                    name='EmprestimoMovimento',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('tipo_movimento', models.CharField(choices=[('EMPRESTIMO', 'Empréstimo'), ('DEVOLUCAO', 'Devolução'), ('AJUSTE', 'Ajuste Manual'), ('ASSINATURA_LIBERACAO', 'Assinatura de Liberação'), ('ASSINATURA_PRODUTOR', 'Assinatura do Produtor')], max_length=20, verbose_name='Tipo de Movimento')),
                        ('quantidade', models.DecimalField(decimal_places=3, max_digits=15, verbose_name='Quantidade')),
                        ('saldo_resultante', models.DecimalField(decimal_places=3, default=0, max_digits=15, verbose_name='Saldo Resultante')),
                        ('data_movimento', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Data do Movimento')),
                        ('documento_referencia', models.CharField(blank=True, max_length=60, verbose_name='Documento Referência')),
                        ('comprovante', models.FileField(blank=True, null=True, upload_to='emprestimos/comprovantes/%Y/%m/', validators=[django.core.validators.FileExtensionValidator(allowed_extensions=['pdf', 'png', 'jpg', 'jpeg'])], verbose_name='Comprovante da Devolução')),
                        ('observacoes', models.TextField(blank=True, verbose_name='Observações')),
                        ('criado_em', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                        ('criado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='movimentos_emprestimo_criados', to=settings.AUTH_USER_MODEL)),
                        ('emprestimo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='movimentos', to='emprestimos.emprestimoprodutor')),
                        ('empresa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='movimentos_emprestimo', to='empresas.empresa')),
                    ],
                    options={
                        'verbose_name': 'Movimento de Empréstimo',
                        'verbose_name_plural': 'Movimentos de Empréstimo',
                        'db_table': 'cadastros_emprestimomovimento',
                        'ordering': ['-data_movimento', '-id'],
                    },
                ),
                migrations.CreateModel(
                    name='EmprestimoInteracao',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('tipo_interacao', models.CharField(choices=[('WHATSAPP_SUCESSO', 'WhatsApp enviado'), ('WHATSAPP_FALHA', 'Falha no WhatsApp'), ('NOTIFICACAO_INTERNA', 'Notificação interna'), ('MENSAGEM_INTERNA', 'Mensagem interna'), ('MENSAGEM_PRODUTOR', 'Mensagem do produtor'), ('DOWNLOAD_ANEXO', 'Download de anexo'), ('ALERTA_VISUAL_EXIBIDO', 'Alerta visual exibido')], max_length=30, verbose_name='Tipo de Interação')),
                        ('descricao', models.TextField(verbose_name='Descrição')),
                        ('destinatario', models.CharField(blank=True, max_length=120, verbose_name='Destinatário')),
                        ('sucesso', models.BooleanField(default=True, verbose_name='Sucesso')),
                        ('criado_em', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                        ('emprestimo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='interacoes', to='emprestimos.emprestimoprodutor')),
                        ('empresa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='interacoes_emprestimo', to='empresas.empresa')),
                        ('usuario', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='interacoes_emprestimo', to=settings.AUTH_USER_MODEL)),
                    ],
                    options={
                        'verbose_name': 'Interação do Empréstimo',
                        'verbose_name_plural': 'Interações do Empréstimo',
                        'db_table': 'cadastros_emprestimointeracao',
                        'ordering': ['-criado_em', '-id'],
                    },
                ),
                migrations.CreateModel(
                    name='EmprestimoMensagem',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('perfil_autor', models.CharField(choices=[('INTERNO', 'Interno'), ('PRODUTOR', 'Produtor')], max_length=20, verbose_name='Perfil do Autor')),
                        ('mensagem', models.TextField(verbose_name='Mensagem')),
                        ('lido_interno_em', models.DateTimeField(blank=True, null=True, verbose_name='Lido pelo Interno em')),
                        ('lido_produtor_em', models.DateTimeField(blank=True, null=True, verbose_name='Lido pelo Produtor em')),
                        ('criado_em', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                        ('autor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='mensagens_emprestimo', to=settings.AUTH_USER_MODEL)),
                        ('emprestimo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mensagens', to='emprestimos.emprestimoprodutor')),
                        ('empresa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mensagens_emprestimo', to='empresas.empresa')),
                    ],
                    options={
                        'verbose_name': 'Mensagem do Empréstimo',
                        'verbose_name_plural': 'Mensagens do Empréstimo',
                        'db_table': 'cadastros_emprestimomensagem',
                        'ordering': ['criado_em', 'id'],
                    },
                ),
                migrations.CreateModel(
                    name='EmprestimoMensagemAnexo',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('arquivo', models.FileField(upload_to='emprestimos/mensagens/%Y/%m/', validators=[django.core.validators.FileExtensionValidator(allowed_extensions=['pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx', 'xls', 'xlsx'])], verbose_name='Arquivo')),
                        ('nome_original', models.CharField(blank=True, max_length=255, verbose_name='Nome Original')),
                        ('criado_em', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                        ('mensagem', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='anexos', to='emprestimos.emprestimomensagem')),
                    ],
                    options={
                        'verbose_name': 'Anexo da Mensagem do Empréstimo',
                        'verbose_name_plural': 'Anexos das Mensagens do Empréstimo',
                        'db_table': 'cadastros_emprestimomensagemanexo',
                        'ordering': ['criado_em', 'id'],
                    },
                ),
            ],
        ),
    ]
