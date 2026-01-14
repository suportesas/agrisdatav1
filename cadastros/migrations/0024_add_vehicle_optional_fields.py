from django.db import migrations, models


def add_column_if_missing(apps, schema_editor):
    conn = schema_editor.connection
    table = 'cadastros_vehicle'
    cur = conn.cursor()
    cur.execute("PRAGMA table_info('%s')" % table)
    existing = [r[1] for r in cur.fetchall()]

    # Define columns to add: (name, sql)
    cols = [
        ("renavam", "ALTER TABLE %s ADD COLUMN renavam varchar(30)" % table),
        ("chassis", "ALTER TABLE %s ADD COLUMN chassis varchar(50)" % table),
        ("numero_motor", "ALTER TABLE %s ADD COLUMN numero_motor varchar(50)" % table),
        ("tipo_combustivel", "ALTER TABLE %s ADD COLUMN tipo_combustivel varchar(20)" % table),
        ("codigo_patrimonio", "ALTER TABLE %s ADD COLUMN codigo_patrimonio varchar(50)" % table),
        ("consumo_medio", "ALTER TABLE %s ADD COLUMN consumo_medio decimal" % table),
    ]

    for name, sql in cols:
        if name not in existing:
            cur.execute(sql)


def noop(apps, schema_editor):
    # no-op for reverse
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('cadastros', '0023_rename_cadastr_vehicle_emp_0c7f3c_idx_cadastros_v_empresa_9a1464_idx_and_more'),
    ]

    operations = [
        migrations.RunPython(add_column_if_missing, reverse_code=noop),
    ]
