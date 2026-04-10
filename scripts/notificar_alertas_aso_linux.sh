#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/alertas_aso_scheduler.log"

mkdir -p "$LOG_DIR"

{
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Inicio execucao notificar_alertas_aso"
  cd "$PROJECT_DIR"
  python manage.py notificar_alertas_aso --canal ambos
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Fim execucao"
  echo
} >> "$LOG_FILE" 2>&1
