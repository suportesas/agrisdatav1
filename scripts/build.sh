#!/usr/bin/env bash
# Build (e opcionalmente subir) o container do Agrisdata em uma máquina Linux.
#
# Uso:
#   ./scripts/build.sh                # clona (se necessário) e builda a imagem
#   ./scripts/build.sh --up           # builda e sobe o container com docker compose
#   REPO_URL=git@github.com:org/agrisdatav1.git ./scripts/build.sh
#
# Requisitos no host Linux: git, docker, docker compose (plugin v2).

set -euo pipefail

REPO_URL="${REPO_URL:-git@github.com:suportesas/agrisdatav1.git}"
TARGET_DIR="${TARGET_DIR:-$HOME/agrisdatav1}"
IMAGE_NAME="${IMAGE_NAME:-agrisdatav1:latest}"

log() { printf '\n[build.sh] %s\n' "$1"; }

command -v docker >/dev/null 2>&1 || { echo "docker não encontrado no PATH"; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "docker compose (plugin v2) não encontrado"; exit 1; }

if [ -d "$TARGET_DIR/.git" ]; then
    log "Repositório já existe em $TARGET_DIR, atualizando..."
    git -C "$TARGET_DIR" pull --ff-only
else
    log "Clonando $REPO_URL em $TARGET_DIR..."
    git clone "$REPO_URL" "$TARGET_DIR"
fi

cd "$TARGET_DIR"

if [ ! -f .env.docker ]; then
    log ".env.docker não encontrado — copiando .env.example como base."
    cp .env.example .env.docker
    echo ">>> Edite $TARGET_DIR/.env.docker com os valores reais (SECRET_KEY, Supabase, etc.) antes de subir o container."
fi

log "Buildando imagem $IMAGE_NAME..."
docker compose build

if [ "${1:-}" = "--up" ]; then
    log "Subindo container..."
    docker compose up -d
    docker compose ps
else
    log "Build concluído. Para subir o container: docker compose up -d (dentro de $TARGET_DIR)"
fi
