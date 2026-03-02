# 🤖 Super Agent V2 - 本地 AI 短视频自动化流水线

完全开源的 9 步全自动短视频生成与发布系统，所有环节均可在本地运行，无需依赖云端 API（除文案改写外）。

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()

## ✨ 核心功能

| 步骤 | 功能 | 技术方案 | 运行模式 |
|------|------|----------|----------|
| 1 | **视频下载** | URL 解析 + yt-dlp | 本地 |
| 2 | **文案提取** | Whisper ASR / Faster-Whisper | 本地模型 |
| 3 | **文案仿写** | DeepSeek API | API 调用 |
| 4 | **语音合成** | CosyVoice TTS | 本地模型 |
| 5 | **数字人生成** | HeyGem.ai | 本地模型 |
| 6 | **字幕生成** | FFmpeg + 自定义样式 | 本地 |
| 7 | **背景音乐** | FFmpeg 混音 | 本地 |
| 8 | **封面/标题** | FFmpeg 截图 + AI 生成 | 本地 |
| 9 | **多平台发布** | social-auto-upload | 本地浏览器 |

## 📁 目录结构

```
super_agent_v2/
├── 📂 audio/                    # 音频处理模块
│   ├── asr/                     # 语音识别 (Whisper)
│   └── tts/                     # 语音合成 (CosyVoice)
├── 📂 avatar/                   # 数字人模块
│   └── heygem/                  # HeyGem.ai 驱动
├── 📂 video/                    # 视频处理模块
│   ├── subtitle/                # 字幕生成
│   ├── bgm/                     # 背景音乐合成
│   └── ffmpeg/                  # FFmpeg 管道
├── 📂 script/                   # 脚本处理
│   ├── extractor/               # 文案提取
│   └── rewriter/                # 文案改写
├── 📂 uploader/                 # 多平台上传
│   └── multi_platform/          # 统一发布接口
├── 📂 tools/                    # 命令适配器与包装器
├── 📂 client/                   # Web 客户端
├── 📂 workflow/                 # 流水线编排
├── 📂 core/                     # 核心配置与工具
├── 📂 config/                   # 配置文件
├── 📂 local_models/             # 本地模型目录
│   ├── cache/whisper/           # Whisper 模型权重
│   ├── cosyvoice/               # CosyVoice 代码与权重
│   ├── heygem/                  # HeyGem.ai 代码
│   └── social-auto-upload/      # 上传工具
├── 📂 scripts/                  # 一键脚本
└── 📂 outputs/                  # 输出目录
```

---

## 🚀 快速开始

### 环境要求

- **Python**: 3.10 或更高版本
- **FFmpeg**: 必须安装并加入 PATH
- **Git**: 用于克隆依赖项目
- **CUDA** (可选): NVIDIA GPU 加速推理

### 1. 克隆项目

```bash
git clone https://github.com/gaofee/super_agent_v2.git
cd super_agent_v2
```

### 2. 创建虚拟环境

**Windows PowerShell:**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**macOS/Linux:**
```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -e .
```

### 4. 配置环境

```bash
# 复制配置文件
cp config/settings.example.yaml config/settings.yaml

# 复制环境变量模板 (Windows)
cp local_models/.env.windows.example local_models/.env
```

### 5. 运行演示

无需配置模型，直接使用 FFmpeg 演示模式：

```bash
# 环境检查
python main.py doctor --settings config/settings.yaml

# 运行完整流程 (演示模式)
python main.py run \
  --input-video ./assets/demo.mp4 \
  --avatar-id host_a \
  --settings config/settings.yaml
```

---

## 🪟 Windows 详细部署指南

### 前置依赖安装

#### 1. 安装 Python 3.10+

从 [Python 官网](https://www.python.org/downloads/) 下载安装，**务必勾选 "Add Python to PATH"**。

验证安装：
```powershell
python --version  # 应显示 3.10.x 或更高
pip --version
```

#### 2. 安装 FFmpeg

**方法 A - 使用 Chocolatey (推荐):**
```powershell
# 以管理员身份运行 PowerShell
choco install ffmpeg
```

**方法 B - 手动安装:**
1. 从 [FFmpeg 官网](https://ffmpeg.org/download.html#build-windows) 下载 Windows build
2. 解压到 `C:\ffmpeg`
3. 添加 `C:\ffmpeg\bin` 到系统 PATH

验证安装：
```powershell
ffmpeg -version
ffprobe -version
```

#### 3. 安装 Git

从 [Git 官网](https://git-scm.com/download/win) 下载安装。

### 项目初始化 (Windows)

```powershell
# 1. 进入项目目录
cd C:\path\to\super_agent_v2

# 2. 创建虚拟环境
python -m venv .venv

# 3. 激活环境
.venv\Scripts\Activate.ps1
# 如果执行策略限制，先运行: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 4. 安装依赖
pip install -e .

# 5. 安装额外依赖
pip install yt-dlp huggingface_hub

# 6. 复制配置文件
copy config\settings.example.yaml config\settings.yaml

# 7. 设置环境变量 (PowerShell)
$env:LOCAL_MODEL_ROOT = "$PWD\local_models"
$env:WHISPER_MODEL_NAME = "medium"
$env:WHISPER_MODEL_DIR = "$env:LOCAL_MODEL_ROOT\cache\whisper"
$env:COSYVOICE_MODEL_DIR = "$env:LOCAL_MODEL_ROOT\cosyvoice\CosyVoice-main"
$env:HEYGEM_MODEL_DIR = "$env:LOCAL_MODEL_ROOT\heygem\HeyGem.ai-main"
$env:SOCIAL_AUTO_UPLOAD_DIR = "$env:LOCAL_MODEL_ROOT\social-auto-upload-oh-v1.0"
$env:DEEPSEEK_API_KEY = "your_deepseek_api_key"
$env:DEEPSEEK_MODEL = "deepseek-chat"
```

---

## 🧠 大模型部署详解

### 模型 1: Whisper (语音识别)

**功能**: 将视频/音频转换为文字，支持多语言

**部署步骤:**

```powershell
# 1. 安装 huggingface_hub
pip install huggingface_hub

# 2. 下载模型权重 (PowerShell)
python -c "
from huggingface_hub import snapshot_download
snapshot_download('Systran/faster-whisper-medium', local_dir='local_models/cache/whisper')
"

# 或使用命令行
huggingface-cli download Systran/faster-whisper-medium --local-dir local_models/cache/whisper
```

**验证安装:**
```powershell
# 检查模型文件
ls local_models\cache\whisper
# 应包含: model.bin, config.json, tokenizer.json, vocabulary.txt

# 测试 ASR
python tools/asr_wrapper.py --audio-in ./assets/demo.mp3 --output-dir ./test_output
```

**可选模型版本:**
- `Systran/faster-whisper-tiny` - 最小最快，适合测试
- `Systran/faster-whisper-base` - 基础版本
- `Systran/faster-whisper-small` - 小模型
- `Systran/faster-whisper-medium` - 推荐，平衡速度与精度
- `Systran/faster-whisper-large-v3` - 最精确但最慢

---

### 模型 2: CosyVoice (语音合成)

**功能**: 文本转语音，支持声音克隆

**部署步骤:**

```powershell
# 1. 克隆 CosyVoice 仓库
git clone https://github.com/FunAudioLLM/CosyVoice.git local_models/cosyvoice/CosyVoice-main

# 2. 安装 CosyVoice 依赖
cd local_models/cosyvoice/CosyVoice-main
pip install -r requirements.txt

# 3. 下载预训练模型
python -c "
from huggingface_hub import snapshot_download
snapshot_download('FunAudioLLM/CosyVoice-300M', local_dir='pretrained_models/CosyVoice-300M')
snapshot_download('FunAudioLLM/CosyVoice-ttsfrd', local_dir='pretrained_models/CosyVoice-ttsfrd')
"
```

**配置声音克隆:**

准备参考音频文件：
```powershell
# 创建参考音频目录
mkdir local_models\cosyvoice\voices

# 放置你的参考音频 (16kHz, 单声道, WAV 格式)
# female.wav - 女声参考
# male.wav - 男声参考
```

**验证安装:**
```powershell
# 检查模型文件
ls local_models\cosyvoice\CosyVoice-main\pretrained_models\CosyVoice-300M
# 应包含: flow.pt, llm.pt, speech_tokenizer_v1.onnx 等
```

**配置 settings.yaml:**
```yaml
tts:
  command: "python tools/tts_wrapper.py --text-file {text_file} --voice-ref {voice_ref} --audio-out {audio_out} --text \"{text}\""
  female_voice_ref: "local_models/cosyvoice/voices/female.wav"
  male_voice_ref: "local_models/cosyvoice/voices/male.wav"
```

---

### 模型 3: HeyGem.ai (数字人)

**功能**: 根据音频生成数字人口播视频

**部署步骤:**

```powershell
# 1. 克隆 HeyGem 仓库
git clone https://github.com/GuijiAI/HeyGem.ai.git local_models/heygem/HeyGem.ai-main

# 2. 按照 HeyGem 官方文档安装依赖
# 注意: HeyGem 可能需要 Docker 或特定 CUDA 版本
cd local_models/heygem/HeyGem.ai-main
```

**运行方式 (二选一):**

**方式 A - Docker 部署:**
```powershell
# 按照 HeyGem 官方文档启动 Docker 容器
docker-compose up -d
```

**方式 B - API 模式:**
```powershell
# 设置 API 地址
$env:HEYGEM_API_URL = "http://localhost:8080"
```

**验证安装:**
```powershell
# 检查 HeyGem 服务状态
curl http://localhost:8080/health
```

**配置 settings.yaml:**
```yaml
avatar:
  command: "python tools/avatar_wrapper.py --avatar-id {avatar_id} --audio-in {audio_in} --video-out {video_out}"
```

---

### 模型 4: social-auto-upload (多平台发布)

**功能**: 自动发布视频到抖音、B站、小红书等平台

**部署步骤:**

```powershell
# 1. 下载或克隆 social-auto-upload
# 方式 A: 解压已下载的压缩包
Expand-Archive -Path local_models/social-auto-upload-oh-v1.0.zip -DestinationPath local_models/

# 方式 B: 从 GitHub 克隆
git clone https://github.com/dreammis/social-auto-upload.git local_models/social-auto-upload-oh-v1.0

# 2. 安装依赖
cd local_models/social-auto-upload-oh-v1.0
pip install -r requirements.txt
```

**配置平台登录:**

```powershell
# 抖音 - 获取 Cookie
python examples/get_douyin_cookie.py

# 小红书 - 获取 Cookie  
python examples/get_xhs_cookie.py

# B站 - 获取 Cookie
python examples/get_bilibili_cookie.py
```

**验证安装:**
```powershell
# 检查目录结构
ls $env:SOCIAL_AUTO_UPLOAD_DIR
# 应包含: bilibili_uploader/, douyin_uploader/, examples/ 等
```

---

## ⚙️ 配置文件详解

### settings.yaml 完整示例

```yaml
workspace_root: "."
output_root: "outputs"

# 音频提取
extractor:
  ffmpeg_audio_cmd: "ffmpeg -y -i {input_video} -vn -acodec pcm_s16le -ar 16000 -ac 1 {audio_out}"

# 语音识别 (Whisper)
asr:
  command: "python tools/asr_wrapper.py --audio-in {audio_in} --output-dir {output_dir}"
  transcript_file_pattern: "{stem}.json"

# 文案改写 (DeepSeek)
rewriter:
  command: "python tools/rewriter_deepseek_wrapper.py --prompt \"{prompt}\""
  fallback_template: "请基于以下文案进行语义级仿写并保持结构清晰：\n\n{source_text}"

# 语音合成 (CosyVoice)
tts:
  command: "python tools/tts_wrapper.py --text-file {text_file} --voice-ref {voice_ref} --audio-out {audio_out} --text \"{text}\""
  female_voice_ref: "local_models/cosyvoice/voices/female.wav"
  male_voice_ref: "local_models/cosyvoice/voices/male.wav"
  female_voice_token: "female"
  male_voice_token: "male"

# 数字人 (HeyGem)
avatar:
  command: "python tools/avatar_wrapper.py --avatar-id {avatar_id} --audio-in {audio_in} --video-out {video_out} --source-video {source_video} --infer-batch {infer_batch} --infer-factor {infer_factor}"

# 视频处理
video:
  subtitle_style: "FontName=PingFang SC,Fontsize=10,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=1,Shadow=0"
  cover_time_sec: 1
  title_max_length: 28

# 背景音乐
bgm:
  default_bgm: "assets/default_bgm.mp3"
  volume: 0.12

# 多平台上传
uploader:
  command_douyin: "python tools/social_upload_wrapper.py --platform douyin --account main --video {video} --cover {cover} --title '{title}'"
  command_hudiehao: "python tools/social_upload_wrapper.py --platform channels --account hudiehao --video {video} --cover {cover} --title '{title}'"
  command_kuaishou: "python tools/social_upload_wrapper.py --platform kuaishou --account main --video {video} --cover {cover} --title '{title}'"
  command_xiaohongshu: "python tools/social_upload_wrapper.py --platform xhs --account main --video {video} --cover {cover} --title '{title}'"
```

---

## 🔧 诊断与测试

### 一键环境检查

```powershell
# 检查所有依赖
python main.py doctor --settings config/settings.yaml

# 详细审计
python main.py audit --settings config/settings.yaml
```

### 模型权重检查

```powershell
# 检查所有模型文件是否完整
bash scripts/check_model_weights.sh

# 或在 Windows Git Bash 中
sh scripts/check_model_weights.sh
```

### 分步测试

```powershell
# 测试 ASR
python tools/asr_wrapper.py --audio-in ./test.mp3 --output-dir ./test_output

# 测试 TTS
python tools/tts_wrapper.py --text "这是一段测试文本" --voice-ref ./female.wav --audio-out ./test.wav

# 测试文案改写
python tools/rewriter_deepseek_wrapper.py --prompt "改写这段文案: 今天天气真好"

# 测试数字人
python tools/avatar_wrapper.py --avatar-id host_a --audio-in ./test.wav --video-out ./test_avatar.mp4
```

---

## 📋 一键脚本

### Windows 批处理脚本

创建 `start.bat`:
```batch
@echo off
cd /d "C:\path\to\super_agent_v2"
call .venv\Scripts\activate.bat
set LOCAL_MODEL_ROOT=%CD%\local_models
set WHISPER_MODEL_NAME=medium
set WHISPER_MODEL_DIR=%LOCAL_MODEL_ROOT%\cache\whisper
set COSYVOICE_MODEL_DIR=%LOCAL_MODEL_ROOT%\cosyvoice\CosyVoice-main
set HEYGEM_MODEL_DIR=%LOCAL_MODEL_ROOT%\heygem\HeyGem.ai-main
set SOCIAL_AUTO_UPLOAD_DIR=%LOCAL_MODEL_ROOT%\social-auto-upload-oh-v1.0
set DEEPSEEK_API_KEY=your_key
python main.py run --input-video %1 --avatar-id host_a --settings config/settings.yaml
pause
```

使用方法:
```powershell
.\start.bat "C:\Videos\input.mp4"
```

---

## 🐛 常见问题

### Q: Windows 下 PowerShell 无法激活虚拟环境？

```powershell
# 以管理员身份运行 PowerShell，然后执行
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Q: FFmpeg 命令找不到？

```powershell
# 检查 PATH
echo $env:PATH
# 确保包含 FFmpeg 的 bin 目录，如 C:\ffmpeg\bin

# 验证
Get-Command ffmpeg
```

### Q: Hugging Face 下载模型很慢？

```powershell
# 设置镜像 (PowerShell)
$env:HF_ENDPOINT = "https://hf-mirror.com"

# 或永久设置
[Environment]::SetEnvironmentVariable("HF_ENDPOINT", "https://hf-mirror.com", "User")
```

### Q: CUDA out of memory？

```powershell
# 使用更小的模型
$env:WHISPER_MODEL_NAME = "small"  # 替代 medium

# 或限制 GPU 显存
$env:CUDA_VISIBLE_DEVICES = "0"
```

### Q: HeyGem 在 macOS 上无法运行？

HeyGem 官方主要支持 Windows + NVIDIA GPU。macOS (Apple Silicon) 需要：
1. 使用 Docker Desktop for Mac
2. 启用 Rosetta 转译
3. 性能可能不如 Windows

建议在 Windows 实机或云服务器上运行 HeyGem。

---

## 📝 输出说明

每次运行会在 `outputs/<timestamp>/` 目录生成：

```
outputs/
└── 20260302_143022/           # 时间戳目录
    ├── audio/                 # 音频文件
    │   ├── extracted.wav     # 提取的原声
    │   └── generated.wav     # TTS 生成的声音
    ├── video/                 # 视频文件
    │   ├── avatar.mp4        # 数字人口播
    │   ├── final.mp4         # 最终成品
    │   ├── cover.jpg         # 封面图
    │   └── subtitle.srt      # 字幕文件
    ├── script/                # 文案文件
    │   ├── extracted.txt     # 提取的文案
    │   └── rewritten.txt     # 改写后的文案
    └── publish_report.json    # 发布报告
```

---

## 🤝 贡献指南

欢迎提交 Issue 和 PR！

1. Fork 本仓库
2. 创建特性分支: `git checkout -b feature/amazing-feature`
3. 提交更改: `git commit -m 'Add amazing feature'`
4. 推送分支: `git push origin feature/amazing-feature`
5. 创建 Pull Request

---

## 📄 许可证

本项目基于 MIT 许可证开源。

---

## 🔗 相关链接

- **Whisper**: https://github.com/openai/whisper
- **Faster-Whisper**: https://github.com/SYSTRAN/faster-whisper
- **CosyVoice**: https://github.com/FunAudioLLM/CosyVoice
- **HeyGem.ai**: https://github.com/GuijiAI/HeyGem.ai
- **social-auto-upload**: https://github.com/dreammis/social-auto-upload
- **FFmpeg**: https://ffmpeg.org/

---

**Made with ❤️ by gaofee**