"""
Data migration: encrypt existing plaintext token_integranotas values using Fernet.

Safe to run before FIELD_ENCRYPTION_KEY is set — encrypt_field is a no-op
in passthrough mode, so the migration does nothing and can be re-run after
the key is added.
"""
from django.db import migrations

from faturamento.encryption import decrypt_field, encrypt_field


def encrypt_existing_tokens(apps, schema_editor):
    ConfiguracaoFiscal = apps.get_model('faturamento', 'ConfiguracaoFiscal')
    to_update = [
        cfg for cfg in ConfiguracaoFiscal.objects.exclude(token_integranotas='')
        if not cfg.token_integranotas.startswith('fernet:')
    ]
    for cfg in to_update:
        cfg.token_integranotas = encrypt_field(cfg.token_integranotas)
    if to_update:
        ConfiguracaoFiscal.objects.bulk_update(to_update, ['token_integranotas'])


def decrypt_existing_tokens(apps, schema_editor):
    """Reverse migration: strip fernet: prefix back to plaintext."""
    ConfiguracaoFiscal = apps.get_model('faturamento', 'ConfiguracaoFiscal')
    to_update = [
        cfg for cfg in ConfiguracaoFiscal.objects.exclude(token_integranotas='')
        if cfg.token_integranotas.startswith('fernet:')
    ]
    for cfg in to_update:
        cfg.token_integranotas = decrypt_field(cfg.token_integranotas)
    if to_update:
        ConfiguracaoFiscal.objects.bulk_update(to_update, ['token_integranotas'])


class Migration(migrations.Migration):

    dependencies = [
        ('faturamento', '0005_conhecimentotransporte_documentovinculadocte_and_more'),
    ]

    operations = [
        migrations.RunPython(encrypt_existing_tokens, decrypt_existing_tokens),
    ]
