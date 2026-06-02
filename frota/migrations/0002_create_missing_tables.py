"""
Cria fisicamente as tabelas que não existiam no banco PostgreSQL.
Os models já estão registrados no estado Django (migration 0001 via SeparateDatabaseAndState).
Usamos RunSQL para criar apenas a estrutura física sem duplicar o estado.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('frota', '0001_initial'),
        ('cadastros', '0108_remove_frota_models'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE TABLE IF NOT EXISTS "cadastros_motoristadadocumento" (
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
                CREATE INDEX IF NOT EXISTS "cadastros_motoristadadocumento_motorista_id"
                    ON "cadastros_motoristadadocumento" ("motorista_id");
            """,
            reverse_sql='DROP TABLE IF EXISTS "cadastros_motoristadadocumento";',
        ),
        migrations.RunSQL(
            sql="""
                CREATE TABLE IF NOT EXISTS "cadastros_pedagogioveiculo" (
                    "id" bigserial NOT NULL PRIMARY KEY,
                    "data" date NOT NULL,
                    "praca" varchar(200) NOT NULL DEFAULT '',
                    "valor" numeric(8, 2) NOT NULL,
                    "observacoes" text NOT NULL DEFAULT '',
                    "criado_em" timestamptz NOT NULL DEFAULT NOW(),
                    "empresa_id" bigint NOT NULL REFERENCES "empresas_empresa" ("id") ON DELETE CASCADE,
                    "motorista_id" bigint NULL REFERENCES "cadastros_motorista" ("id") ON DELETE SET NULL,
                    "vehicle_id" bigint NOT NULL REFERENCES "cadastros_vehicle" ("id") ON DELETE CASCADE,
                    "viagem_id" bigint NULL REFERENCES "cadastros_viagem" ("id") ON DELETE SET NULL,
                    "conta_pagar_id" bigint NULL UNIQUE REFERENCES "financeiro_contapagar" ("id") ON DELETE SET NULL,
                    "criado_por_id" bigint NULL REFERENCES "usuarios_usuario" ("id") ON DELETE SET NULL
                );
                CREATE INDEX IF NOT EXISTS "cadastros_pedagogioveiculo_empresa_id"
                    ON "cadastros_pedagogioveiculo" ("empresa_id");
                CREATE INDEX IF NOT EXISTS "cadastros_pedagogioveiculo_vehicle_id"
                    ON "cadastros_pedagogioveiculo" ("vehicle_id");
                CREATE INDEX IF NOT EXISTS "cadastros_pedagogioveiculo_viagem_id"
                    ON "cadastros_pedagogioveiculo" ("viagem_id");
            """,
            reverse_sql='DROP TABLE IF EXISTS "cadastros_pedagogioveiculo";',
        ),
    ]
