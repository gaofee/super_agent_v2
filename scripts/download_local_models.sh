#!/usr/bin/env bash
set -u

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
MODEL_DIR="$ROOT_DIR/local_models"
WHISPER_DIR="$MODEL_DIR/whisper"
COSY_DIR="$MODEL_DIR/cosyvoice"
HEYGEM_DIR="$MODEL_DIR/heygem"
CACHE_DIR="$MODEL_DIR/cache"

mkdir -p "$WHISPER_DIR" "$COSY_DIR" "$HEYGEM_DIR" "$CACHE_DIR"

export HF_HOME="$CACHE_DIR/hf"
export TRANSFORMERS_CACHE="$CACHE_DIR/transformers"

warn() { echo "[warn] $*"; }
info() { echo "[info] $*"; }

safe_download() {
  local repo="$1"
  local out="$2"
  if command -v hf >/dev/null 2>&1; then
    hf download "$repo" --local-dir "$out" || warn "download failed: $repo"
    return 0
  fi
  if command -v huggingface-cli >/dev/null 2>&1; then
    huggingface-cli download "$repo" --local-dir "$out" --local-dir-use-symlinks False || warn "download failed: $repo"
    return 0
  fi
  warn "huggingface cli not found. Install: pip install 'huggingface_hub[cli]'"
}

echo "[1/3] Download Whisper model (Systran faster-whisper-medium)..."
safe_download "Systran/faster-whisper-medium" "$WHISPER_DIR/faster-whisper-medium"

echo "[2/3] Download CosyVoice model..."
safe_download "FunAudioLLM/CosyVoice-300M" "$COSY_DIR/CosyVoice-300M"

echo "[3/3] Prepare HeyGem model directory..."
mkdir -p "$HEYGEM_DIR/models"
cat > "$HEYGEM_DIR/README_LOCAL_MODELS.txt" <<TXT
Put your HeyGem/数字人驱动模型文件 into this directory:
$HEYGEM_DIR/models

Example expected files (adjust to your driver):
- avatar_base.onnx
- lip_sync.onnx
- face_renderer.onnx
TXT

cat > "$MODEL_DIR/.env.example" <<TXT
export LOCAL_MODEL_ROOT=$MODEL_DIR
export WHISPER_MODEL_NAME=medium
export WHISPER_MODEL_DIR=$WHISPER_DIR/faster-whisper-medium
export COSYVOICE_MODEL_DIR=$COSY_DIR/CosyVoice-300M
export HEYGEM_MODEL_DIR=$HEYGEM_DIR/models
export DEEPSEEK_API_KEY=your_deepseek_api_key
export DEEPSEEK_MODEL=deepseek-chat
export SOCIAL_AUTO_UPLOAD_DIR=/abs/path/social-auto-upload

# Optional: inject real runtime commands
# export COSYVOICE_CMD='python /path/to/cosyvoice_infer.py --model-dir {model_dir} --text-file {text_file} --prompt-wav {voice_ref} --out {audio_out}'
# export HEYGEM_CMD='python /path/to/heygem_driver.py --model-dir {model_dir} --avatar-id {avatar_id} --audio {audio_in} --out {video_out}'
TXT

info "Done. Local model root: $MODEL_DIR"
