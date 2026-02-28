# 本地模型部署与运行配置

本项目默认目录：
- 本地模型根目录：`/Users/gaofei/Desktop/工具代码/super_agent_v2/local_models`
- 模型下载脚本：`/Users/gaofei/Desktop/工具代码/super_agent_v2/scripts/download_local_models.sh`

## 1. 创建并下载本地模型

执行：

```bash
cd /Users/gaofei/Desktop/工具代码/super_agent_v2
bash scripts/download_local_models.sh
```

脚本目标：
- Whisper: `local_models/whisper/faster-whisper-medium`
- CosyVoice: `local_models/cosyvoice/CosyVoice-300M`
- HeyGem: `local_models/heygem/models`（由你放入驱动模型文件）

说明：
- 当前环境若无法访问 `huggingface.co`，下载会失败，但目录会创建完成。
- 可在可联网环境先下载，再拷贝整个 `local_models/` 到本机同路径。

## 2. 配置环境变量

```bash
export LOCAL_MODEL_ROOT=/Users/gaofei/Desktop/工具代码/super_agent_v2/local_models
export WHISPER_MODEL_NAME=medium
export WHISPER_MODEL_DIR=$LOCAL_MODEL_ROOT/whisper/faster-whisper-medium
export COSYVOICE_MODEL_DIR=$LOCAL_MODEL_ROOT/cosyvoice/CosyVoice-300M
export HEYGEM_MODEL_DIR=$LOCAL_MODEL_ROOT/heygem/models

# 文案仿写允许使用 DeepSeek API
export DEEPSEEK_API_KEY=你的key
export DEEPSEEK_MODEL=deepseek-chat

# 多平台发布
export SOCIAL_AUTO_UPLOAD_DIR=/你的/social-auto-upload

# 可选：注入真实模型推理命令（不配则自动降级）
# export COSYVOICE_CMD='python /path/to/cosyvoice_infer.py --model-dir {model_dir} --text-file {text_file} --prompt-wav {voice_ref} --out {audio_out}'
# export HEYGEM_CMD='python /path/to/heygem_driver.py --model-dir {model_dir} --avatar-id {avatar_id} --audio {audio_in} --out {video_out}'
```

## 3. 项目配置状态

当前 `config/settings.yaml` 已改为：
- ASR：本地 wrapper（Whisper 本地模型路径）
- 仿写：DeepSeek API wrapper
- TTS：本地 wrapper（支持 CosyVoice 本地模型）
- 数字人：本地 wrapper（支持 HeyGem 本地模型）
- 上传：social-auto-upload wrapper

## 4. 验证

```bash
python3 main.py doctor --settings config/settings.yaml
python3 main.py audit --settings config/settings.yaml
```

## 5. 运行

```bash
python3 main.py run --input-video /abs/path/input.mp4 --avatar-id host_a --settings config/settings.yaml
```

Web 界面：

```bash
python3 client/web.py
```
