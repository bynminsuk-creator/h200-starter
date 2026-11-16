#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1
export SCRATCH_DIR="${SCRATCH_DIR:-/app/scratch/h200-starter}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$SCRATCH_DIR/cache}"
export HF_HOME="${HF_HOME:-$SCRATCH_DIR/huggingface}"
export TORCH_HOME="${TORCH_HOME:-$SCRATCH_DIR/torch}"
export TMPDIR="${TMPDIR:-$SCRATCH_DIR/tmp}"
mkdir -p "$SCRATCH_DIR" "$XDG_CACHE_HOME" "$HF_HOME" "$TORCH_HOME" "$TMPDIR"
mode="${1:-smoke}"
if [ "$#" -gt 0 ]; then shift; fi
case "$mode" in
  smoke) exec python -u scripts/runner.py -- python -u scripts/smoke.py "$@" ;;
  run) exec python -u scripts/runner.py -- "$@" ;;
  *) echo "Usage: bash run.sh smoke | bash run.sh run python -u train.py" >&2; exit 2 ;;
esac
