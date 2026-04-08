from django.db import migrations


def create_unaccent_and_indexes(apps, schema_editor):
    # Only run on PostgreSQL
    if schema_editor.connection.vendor != 'postgresql':
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS unaccent;")
        cursor.execute(
            """
            CREATE OR REPLACE FUNCTION public.immutable_unaccent(text)
            RETURNS text
            LANGUAGE sql
            IMMUTABLE
            AS $$
                SELECT public.unaccent('public.unaccent', $1)
            $$;
            """
        )
        cursor.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS cadastros_ncm_descricao_unaccent_idx ON cadastros_ncm (lower(public.immutable_unaccent(descricao)));")
        cursor.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS cadastros_empresancm_descricao_unaccent_idx ON cadastros_empresancm (lower(public.immutable_unaccent(descricao)));")


def drop_unaccent_and_indexes(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("DROP INDEX IF EXISTS cadastros_ncm_descricao_unaccent_idx;")
        cursor.execute("DROP INDEX IF EXISTS cadastros_empresancm_descricao_unaccent_idx;")
        cursor.execute("DROP FUNCTION IF EXISTS public.immutable_unaccent(text);")
        cursor.execute("DROP EXTENSION IF EXISTS unaccent;")


class Migration(migrations.Migration):
    # We need to run CREATE INDEX CONCURRENTLY so migrations must be non-atomic
    atomic = False

    dependencies = [
        ('cadastros', '0031_add_empresancm'),
    ]

    operations = [
        migrations.RunPython(create_unaccent_and_indexes, reverse_code=drop_unaccent_and_indexes),
    ]
