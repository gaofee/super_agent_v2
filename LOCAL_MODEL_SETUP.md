# 本地模型部署与运行配置（跨平台）

## 目录约定

- 项目根目录：`<project-root>`
- 本地模型目录：`<project-root>/local_models`

## 1) 准备模型

优先参考：
- `local_models/DEPLOY_STEPS.md`
- `local_models/WEIGHT_CHECKLIST.md`

可联网环境可用脚本初始化目录：

```bash
bash scripts/download_local_models.sh
```

若网络受限：在可联网机器下载后，整体拷贝 `local_models/` 到目标机器。

## 2) 配置环境变量

### macOS/Linux

```bash
export LOCAL_MODEL_ROOT=$(pwd)/local_models
export WHISPER_MODEL_NAME=medium
export WHISPER_MODEL_DIR=$LOCAL_MODEL_ROOT/cache/whisper
export COSYVOICE_MODEL_DIR=$LOCAL_MODEL_ROOT/cosyvoice/CosyVoice-main
export HEYGEM_MODEL_DIR=$LOCAL_MODEL_ROOT/heygem/HeyGem.ai-main
export SOCIAL_AUTO_UPLOAD_DIR=$LOCAL_MODEL_ROOT/social-auto-upload-oh-v1.0
export DEEPSEEK_API_KEY=你的key
export DEEPSEEK_MODEL=deepseek-chat
```

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

## 3) 验证

```bash
python main.py doctor --settings config/settings.yaml
python main.py audit --settings config/settings.yaml
```

## 4) 运行

```bash
python main.py run --input-video /abs/path/input.mp4 --avatar-id host_a --settings config/settings.yaml
python client/web.py
```

## 5) 关键说明

- 本项目除“文案改写”外均按本地模型/本地工具执行。
- 文案改写使用 DeepSeek API（需要 `DEEPSEEK_API_KEY`）。
- Windows 上步骤 1（URL 下载）需额外安装：

```bash
python -m pip install yt-dlp
```
