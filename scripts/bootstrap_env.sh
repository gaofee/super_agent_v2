#!/usr/bin/env bash
set -u

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
PY="$VENV_DIR/bin/python"
PIP="$VENV_DIR/bin/pip"

log() { echo "[bootstrap] $*"; }
warn() { echo "[bootstrap][warn] $*"; }

if [ ! -x "$PY" ]; then
  log "creating virtualenv at $VENV_DIR"
  python3 -m venv "$VENV_DIR" || { warn "venv create failed"; exit 1; }
fi

log "python: $($PY --version 2>/dev/null || true)"

$PY -m pip install --upgrade pip >/dev/null 2>&1 || warn "pip upgrade failed (network likely restricted)"
$PIP install gradio yt-dlp >/dev/null 2>&1 || warn "install gradio/yt-dlp failed (network likely restricted)"
$PIP install -e "$ROOT_DIR" >/dev/null 2>&1 || warn "install current project failed"

log "done"
