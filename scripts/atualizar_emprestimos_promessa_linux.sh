#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

cd "$PROJECT_ROOT"
mkdir -p logs

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Iniciando atualizacao de promessas de emprestimos" >> logs/emprestimos_promessa_scheduler.log
$PYTHON_BIN manage.py atualizar_emprestimos_promessa --quiet >> logs/emprestimos_promessa_scheduler.log 2>&1
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Finalizado" >> logs/emprestimos_promessa_scheduler.log
