#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT_DIR/local_models/.env"
ENV_FILE_EXAMPLE="$ROOT_DIR/local_models/.env.example"

if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$ENV_FILE"
elif [[ -f "$ENV_FILE_EXAMPLE" ]]; then
  # shellcheck disable=SC1090
  source "$ENV_FILE_EXAMPLE"
fi

WHISPER_MODEL_DIR="${WHISPER_MODEL_DIR:-$ROOT_DIR/local_models/cache/whisper}"
COSYVOICE_MODEL_DIR="${COSYVOICE_MODEL_DIR:-$ROOT_DIR/local_models/cosyvoice/CosyVoice-main}"
HEYGEM_MODEL_DIR="${HEYGEM_MODEL_DIR:-$ROOT_DIR/local_models/heygem/HeyGem.ai-main}"
SOCIAL_AUTO_UPLOAD_DIR="${SOCIAL_AUTO_UPLOAD_DIR:-$ROOT_DIR/local_models/social-auto-upload-oh-v1.0}"

weight_count() {
  local dir="$1"
  if [[ ! -d "$dir" ]]; then
    echo 0
    return
  fi
  find "$dir" -type f \( \
    -name "*.pt" -o -name "*.bin" -o -name "*.onnx" -o -name "*.safetensors" -o -name "*.ckpt" -o -name "*.pth" \
  \) | wc -l | tr -d ' '
}

check_dir() {
  local name="$1"
  local dir="$2"
  local n
  n="$(weight_count "$dir")"
  if [[ -d "$dir" ]]; then
    if [[ "$n" -gt 0 ]]; then
      echo "[OK]   $name dir exists: $dir (weight files: $n)"
    else
      echo "[MISS] $name dir exists but no weight files: $dir"
    fi
  else
    echo "[MISS] $name dir not found: $dir"
  fi
}

echo "== Local Model Weight Check =="
echo "ROOT: $ROOT_DIR"
echo

check_dir "Whisper" "$WHISPER_MODEL_DIR"
check_dir "CosyVoice" "$COSYVOICE_MODEL_DIR"
check_dir "HeyGem" "$HEYGEM_MODEL_DIR"
echo

if [[ -d "$SOCIAL_AUTO_UPLOAD_DIR" ]]; then
  if [[ -f "$SOCIAL_AUTO_UPLOAD_DIR/examples/upload_video_to_douyin.py" ]]; then
    echo "[OK]   social-auto-upload examples found: $SOCIAL_AUTO_UPLOAD_DIR/examples"
  else
    echo "[MISS] social-auto-upload examples missing in: $SOCIAL_AUTO_UPLOAD_DIR"
  fi
else
  echo "[MISS] SOCIAL_AUTO_UPLOAD_DIR not found: $SOCIAL_AUTO_UPLOAD_DIR"
fi

echo
if [[ -n "${DEEPSEEK_API_KEY:-}" ]]; then
  echo "[OK]   DEEPSEEK_API_KEY is set"
else
  echo "[MISS] DEEPSEEK_API_KEY is empty"
fi
if [[ -n "${COSYVOICE_CMD:-}" ]]; then
  echo "[OK]   COSYVOICE_CMD is set"
else
  echo "[MISS] COSYVOICE_CMD is empty (TTS will fallback to tone audio)"
fi
if [[ -n "${HEYGEM_CMD:-}" ]]; then
  echo "[OK]   HEYGEM_CMD is set"
else
  echo "[MISS] HEYGEM_CMD is empty (avatar will fallback mode)"
fi
