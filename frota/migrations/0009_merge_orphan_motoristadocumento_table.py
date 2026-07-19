"""
Migra dados da tabela orfa "cadastros_motoristadodocumento" para a tabela
ativa "cadastros_motoristadadocumento", depois remove a orfa.

Mesmo bug de frota/0001_initial.py (typo no db_table) que afetou
PedagioVeiculo (ver 0008): o model MotoristaDocumento (originalmente
"MotoristadoDocumento" em cadastros/migrations/0042) tem
db_table='cadastros_motoristadadocumento' — nome diferente da tabela
original "cadastros_motoristadodocumento". Como a tabela com o nome
errado nao existia, frota/0002_create_missing_tables.py criou ela do
zero via SQL bruto, vazia.

Diferente do caso do PedagioVeiculo: aqui a tabela orfa tinha 3
registros reais (documentos de motoristas cadastrados em 04/2026,
invisiveis para o app desde entao porque o ORM le/escreve na tabela
errada). Confirmado por leitura direta do banco (2026-07-19): mesmo
schema, sem FKs de outras tabelas apontando pra nenhuma das duas,
motorista_id de todas as linhas ainda existe em cadastros_motorista.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('frota', '0008_drop_orphan_pedagioveiculo_table'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                INSERT INTO "cadastros_motoristadadocumento"
                    ("id", "tipo", "numero", "data_emissao", "data_validade",
                     "arquivo", "observacoes", "data_criacao", "motorista_id")
                SELECT
                    "id", "tipo", "numero", "data_emissao", "data_validade",
                    "arquivo", "observacoes", "data_criacao", "motorista_id"
                FROM "cadastros_motoristadodocumento"
                ON CONFLICT ("id") DO NOTHING;

                SELECT setval(
                    pg_get_serial_sequence('cadastros_motoristadadocumento', 'id'),
                    GREATEST(
                        (SELECT COALESCE(MAX("id"), 0) FROM "cadastros_motoristadadocumento"),
                        1
                    )
                );

                DROP TABLE IF EXISTS "cadastros_motoristadodocumento";
            """,
            reverse_sql="""
                CREATE TABLE IF NOT EXISTS "cadastros_motoristadodocumento" (
                    "id" bigserial NOT NULL PRIMARY KEY,
                    "tipo" varchar(20) NOT NULL,
                    "numero" varchar(100) NOT NULL DEFAULT '',
                    "data_emissao" date NULL,
                    "data_validade" date NULL,
                    "arquivo" varchar(100) NULL,
                    "observacoes" text NOT NULL DEFAULT '',
                    "data_criacao" timestamptz NOT NULL DEFAULT NOW(),
                    "motorista_id" bigint NOT NULL REFERENCES "cadastros_motorista" ("id") ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS "cadastros_motoristadodocumento_motorista_id"
                    ON "cadastros_motoristadodocumento" ("motorista_id");
            """,
        ),
    ]
