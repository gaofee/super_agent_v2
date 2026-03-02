#!/usr/bin/env bash
set -u

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
MODEL_ROOT="$ROOT_DIR/local_models"

if [ -f "$MODEL_ROOT/.env" ]; then
  set -a
  # shellcheck disable=SC1090
  source "$MODEL_ROOT/.env"
  set +a
fi

check_bin() {
  local b="$1"
  if command -v "$b" >/dev/null 2>&1; then
    echo "[ok] binary:$b -> $(command -v "$b")"
  else
    echo "[warn] binary:$b missing"
  fi
}

check_path() {
  local p="$1"
  if [ -e "$p" ]; then
    echo "[ok] path:$p"
  else
    echo "[warn] path missing:$p"
  fi
}

echo "=== Preflight Check ==="
check_bin ffmpeg
check_bin ffprobe
check_bin whisper
check_bin yt-dlp
check_bin python3

check_path "$MODEL_ROOT"
check_path "${WHISPER_MODEL_DIR:-$MODEL_ROOT/cache/whisper}"
check_path "${COSYVOICE_MODEL_DIR:-$MODEL_ROOT/cosyvoice/CosyVoice-main}"
check_path "${HEYGEM_MODEL_DIR:-$MODEL_ROOT/heygem/HeyGem.ai-main}"

for var in DEEPSEEK_API_KEY SOCIAL_AUTO_UPLOAD_DIR WHISPER_MODEL_DIR COSYVOICE_MODEL_DIR HEYGEM_MODEL_DIR; do
  if [ -n "${!var:-}" ]; then
    echo "[ok] env:$var set"
  else
    echo "[warn] env:$var not set"
  fi
done

python3 "$ROOT_DIR/main.py" doctor --settings "$ROOT_DIR/config/settings.yaml"
python3 "$ROOT_DIR/main.py" audit --settings "$ROOT_DIR/config/settings.yaml"
