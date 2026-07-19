"""
Remove a tabela orfa "cadastros_pedagioveiculo".

Historico: frota/0001_initial.py registrou o model PedagioVeiculo com
db_table='cadastros_pedagogioveiculo' (typo — sobrou um "go"), em vez do
nome original criado em cadastros/migrations/0097 ("cadastros_pedagioveiculo").
Como a tabela com o nome errado nao existia, frota/0002_create_missing_tables.py
criou ela do zero via SQL bruto. Resultado: duas tabelas fisicas, a original
("cadastros_pedagioveiculo") orfa — nenhum model aponta mais pra ela — mas
ainda com FK ativa para cadastros_vehicle, o que impede TRUNCATE (ex: no
teardown dos testes Django/pytest).

Confirmado por leitura direta do banco (2026-07-19): ambas as tabelas
tinham 0 linhas, entao remover a orfa nao descarta nenhum dado. O model
continua usando "cadastros_pedagogioveiculo" (nenhuma mudanca de codigo).
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('frota', '0007_motorista_motorista_empresa_matricula_unique'),
    ]

    operations = [
        migrations.RunSQL(
            sql='DROP TABLE IF EXISTS "cadastros_pedagioveiculo";',
            reverse_sql="""
                CREATE TABLE IF NOT EXISTS "cadastros_pedagioveiculo" (
                    "id" bigserial NOT NULL PRIMARY KEY,
                    "data" date NOT NULL,
                    "praca" varchar(200) NOT NULL DEFAULT '',
                    "valor" numeric(8, 2) NOT NULL,
                    "observacoes" text NOT NULL DEFAULT '',
                    "criado_em" timestamptz NOT NULL DEFAULT NOW(),
                    "empresa_id" bigint NOT NULL REFERENCES "empresas_empresa" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED,
                    "motorista_id" bigint NULL REFERENCES "cadastros_motorista" ("id") ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED,
                    "vehicle_id" bigint NOT NULL REFERENCES "cadastros_vehicle" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED,
                    "viagem_id" bigint NULL REFERENCES "cadastros_viagem" ("id") ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED,
                    "conta_pagar_id" bigint NULL UNIQUE REFERENCES "financeiro_contapagar" ("id") ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED,
                    "criado_por_id" bigint NULL REFERENCES "usuarios_usuario" ("id") ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED
                );
                CREATE INDEX IF NOT EXISTS "cadastros_pedagioveiculo_empresa_id_492d02f7"
                    ON "cadastros_pedagioveiculo" ("empresa_id");
                CREATE INDEX IF NOT EXISTS "cadastros_pedagioveiculo_motorista_id_654de2f8"
                    ON "cadastros_pedagioveiculo" ("motorista_id");
                CREATE INDEX IF NOT EXISTS "cadastros_pedagioveiculo_vehicle_id_3d0374d0"
                    ON "cadastros_pedagioveiculo" ("vehicle_id");
                CREATE INDEX IF NOT EXISTS "cadastros_pedagioveiculo_viagem_id_d6c50d7e"
                    ON "cadastros_pedagioveiculo" ("viagem_id");
                CREATE INDEX IF NOT EXISTS "cadastros_p_empresa_319c74_idx"
                    ON "cadastros_pedagioveiculo" ("empresa_id", "vehicle_id", "data");
                CREATE INDEX IF NOT EXISTS "cadastros_p_empresa_a074f5_idx"
                    ON "cadastros_pedagioveiculo" ("empresa_id", "viagem_id");
            """,
        ),
    ]
