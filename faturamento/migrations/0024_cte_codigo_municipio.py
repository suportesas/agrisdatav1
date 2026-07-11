from django.db import migrations, models


class Migration(migrations.Migration):
    """
    codigo_municipio_inicio and codigo_municipio_fim already exist in the DB
    as NOT NULL columns without a default. This migration:
    1. Sets a DB-level default of '' so existing rows are not violated.
    2. Registers the fields in Django's migration state so the ORM includes
       them in INSERT/UPDATE statements (preventing the IntegrityError).
    """

    dependencies = [
        ('faturamento', '0023_cte_globalizado'),
        # As colunas assumidas como já existentes aqui são criadas de fato por
        # esta migration de um branch paralelo (unificado só em 0025) — sem essa
        # dependência explícita, um install do zero pode aplicar 0024 antes de
        # 0020 e o ALTER COLUMN falha porque a coluna ainda não existe.
        ('faturamento', '0020_cte_codigo_municipio_inicio_fim'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='conhecimentotransporte',
                    name='codigo_municipio_inicio',
                    field=models.CharField(blank=True, default='', max_length=7, verbose_name='Código IBGE Início'),
                ),
                migrations.AddField(
                    model_name='conhecimentotransporte',
                    name='codigo_municipio_fim',
                    field=models.CharField(blank=True, default='', max_length=7, verbose_name='Código IBGE Fim'),
                ),
            ],
            database_operations=[
                # Columns already exist — set a column-level default so new rows
                # that don't supply a value receive '' instead of NULL.
                migrations.RunSQL(
                    sql="ALTER TABLE faturamento_conhecimentotransporte ALTER COLUMN codigo_municipio_inicio SET DEFAULT ''",
                    reverse_sql="ALTER TABLE faturamento_conhecimentotransporte ALTER COLUMN codigo_municipio_inicio DROP DEFAULT",
                ),
                migrations.RunSQL(
                    sql="ALTER TABLE faturamento_conhecimentotransporte ALTER COLUMN codigo_municipio_fim SET DEFAULT ''",
                    reverse_sql="ALTER TABLE faturamento_conhecimentotransporte ALTER COLUMN codigo_municipio_fim DROP DEFAULT",
                ),
            ],
        ),
    ]
