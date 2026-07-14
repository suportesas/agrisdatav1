#!/usr/bin/env bash
# Entrypoint do container Agrisdata (Django).
# Roda migrate/collectstatic em runtime, pois settings.py exige SECRET_KEY e
# PG_NAME (Supabase) via variáveis de ambiente — indisponíveis durante o build.
set -euo pipefail

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec "$@"
