# 本地模型部署步骤（Windows 优先，macOS 兼容说明）

## 1. 依赖开源项目（GitHub）

- Whisper: https://github.com/openai/whisper
- Faster-Whisper: https://github.com/SYSTRAN/faster-whisper
- CosyVoice: https://github.com/FunAudioLLM/CosyVoice
- HeyGem.ai: https://github.com/GuijiAI/HeyGem.ai
- FFmpeg: https://github.com/FFmpeg/FFmpeg
- social-auto-upload: https://github.com/dreammis/social-auto-upload

## 2. 目录规范

以项目根目录 `<project-root>` 为例：

- Whisper：`<project-root>/local_models/cache/whisper`
- CosyVoice：`<project-root>/local_models/cosyvoice/CosyVoice-main`
- HeyGem：`<project-root>/local_models/heygem/HeyGem.ai-main`
- social-auto-upload：`<project-root>/local_models/social-auto-upload-oh-v1.0`

## 3. Windows 下载与部署

### 3.1 Whisper 权重

```powershell
python -m pip install huggingface_hub
python - <<'PY'
from huggingface_hub import snapshot_download
snapshot_download("Systran/faster-whisper-medium", local_dir="local_models/cache/whisper")
PY
```

### 3.2 CosyVoice 权重

```powershell
python -m pip install huggingface_hub
python - <<'PY'
from huggingface_hub import snapshot_download
snapshot_download("FunAudioLLM/CosyVoice-300M", local_dir="local_models/cosyvoice/CosyVoice-main/pretrained_models/CosyVoice-300M")
snapshot_download("FunAudioLLM/CosyVoice-ttsfrd", local_dir="local_models/cosyvoice/CosyVoice-main/pretrained_models/CosyVoice-ttsfrd")
PY
```

### 3.3 HeyGem

- 使用 `HeyGem.ai` 源码 + 官方文档要求的运行方式（本地服务或 API）。
- 本项目通过 `HEYGEM_CMD` 或 `HEYGEM_API_URL` 对接，不强绑具体启动方式。

### 3.4 social-auto-upload

将仓库放到：
- `local_models/social-auto-upload-oh-v1.0`

并完成本地浏览器登录态配置（cookie/session）。

## 4. 环境变量

### Windows PowerShell

```powershell
$env:LOCAL_MODEL_ROOT = "$PWD\local_models"
$env:WHISPER_MODEL_NAME = "medium"
$env:WHISPER_MODEL_DIR = "$env:LOCAL_MODEL_ROOT\cache\whisper"
$env:COSYVOICE_MODEL_DIR = "$env:LOCAL_MODEL_ROOT\cosyvoice\CosyVoice-main"
$env:HEYGEM_MODEL_DIR = "$env:LOCAL_MODEL_ROOT\heygem\HeyGem.ai-main"
$env:SOCIAL_AUTO_UPLOAD_DIR = "$env:LOCAL_MODEL_ROOT\social-auto-upload-oh-v1.0"
$env:DEEPSEEK_API_KEY = "你的key"
$env:DEEPSEEK_MODEL = "deepseek-chat"
```

或直接复制并修改：
- `local_models/.env.windows.example`

## 5. 当前 macOS (Apple Silicon) 限制说明

- HeyGem 官方/社区 Docker 与部分依赖主要围绕 `linux/amd64`，在 Apple Silicon 上可能需要转译，性能与稳定性不如 Windows + NVIDIA。
- social-auto-upload 的浏览器自动化发布依赖本机登录态与浏览器权限；沙箱环境无法代表真实桌面发布成功率。
- URL 下载依赖 `yt-dlp` 和外网可达性；若网络受限会失败。

以上三项在 Windows 实机（可联网、可登录浏览器）更容易完整跑通。

## 6. 自检命令

```bash
python main.py doctor --settings config/settings.yaml
python main.py audit --settings config/settings.yaml
bash scripts/check_model_weights.sh
```
