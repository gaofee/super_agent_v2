# 本地模型权重检查清单

## Whisper（faster-whisper）

目标目录：
- `local_models/cache/whisper`

至少应存在：
- `model.bin`
- `config.json`
- `tokenizer.json`

## CosyVoice

目标目录：
- `local_models/cosyvoice/CosyVoice-main/pretrained_models/CosyVoice-300M`
- `local_models/cosyvoice/CosyVoice-main/pretrained_models/CosyVoice-ttsfrd`

至少应存在（示例）：
- `flow.pt`
- `llm.pt`
- `speech_tokenizer_v1.onnx`

## HeyGem

目标目录：
- `local_models/heygem/HeyGem.ai-main`

说明：
- HeyGem 常以服务/容器方式运行，不一定体现为固定的单个权重文件。
- 本项目以 `HEYGEM_CMD` / `HEYGEM_API_URL` 能否正常生成视频作为可用标准。

## social-auto-upload

目标目录：
- `local_models/social-auto-upload-oh-v1.0`

至少应存在：
- `examples/` 目录

## 一键检查

```bash
bash scripts/check_model_weights.sh
```

## Windows 下载示例

```powershell
python -m pip install huggingface_hub
python - <<'PY'
from huggingface_hub import snapshot_download
snapshot_download("Systran/faster-whisper-medium", local_dir="local_models/cache/whisper")
snapshot_download("FunAudioLLM/CosyVoice-300M", local_dir="local_models/cosyvoice/CosyVoice-main/pretrained_models/CosyVoice-300M")
snapshot_download("FunAudioLLM/CosyVoice-ttsfrd", local_dir="local_models/cosyvoice/CosyVoice-main/pretrained_models/CosyVoice-ttsfrd")
PY
```
