# Super Agent V2 (Local Only)

本项目实现你定义的 9 步全本地短视频自动化流水线：

1. 对标文案提取
2. 文案仿写
3. 声音克隆/语音合成
4. 数字人口播生成
5. 字幕生成
6. 背景音乐合成
7. 视频标题生成
8. 视频封面生成
9. 多平台自动发布

## 目录结构

```text
project-root/
├── script/
│   ├── extractor/
│   └── rewriter/
├── audio/
│   ├── asr/
│   └── tts/
├── avatar/
│   └── heygem/
├── video/
│   ├── subtitle/
│   ├── bgm/
│   └── ffmpeg/
├── uploader/
│   └── multi_platform/
├── client/
├── core/
├── workflow/
├── config/
└── outputs/
```

## 快速开始

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp config/settings.example.yaml config/settings.yaml
```

本地模型部署步骤见：
- [LOCAL_MODEL_SETUP.md](/Users/gaofei/Desktop/工具代码/super_agent_v2/LOCAL_MODEL_SETUP.md)

一键准备本地模型目录：

```bash
bash scripts/download_local_models.sh
```

只用 FFmpeg 也可以直接跑通全链路（演示模式）：

- ASR 未配置时自动生成降级文案和时间轴
- TTS 未配置时自动生成占位语音
- 数字人未配置时自动生成占位口播画面
- 上传命令未配置时自动模拟发布并产出报告

执行完整流程：

```bash
super-agent run \
  --input-video /abs/path/benchmark.mp4 \
  --avatar-id host_a
```

如果 `tts.command` 已配置真实 CosyVoice，建议补充：

```bash
--voice-ref /abs/path/voice_ref.wav
```

启动本地客户端：

```bash
super-agent-ui
```

检查本地环境与配置状态：

```bash
super-agent doctor
super-agent audit
```

## 本地依赖

- FFmpeg（必须）
- yt-dlp（建议，用于 URL 下载）
- Whisper（可通过 `whisper` 命令或你自己的 ASR 脚本）
- CosyVoice 推理脚本（通过命令行适配）
- HeyGem 本地驱动（通过命令行适配）
- social-auto-upload 或各平台 API 本地脚本

## 关键说明

- 本仓库默认不绑定云 API。
- 所有模块都通过“命令适配层”调用本地可执行脚本。
- 你只需在 `config/settings.yaml` 配置本地命令即可切换真实实现。
- 每次运行会在 `outputs/<timestamp>/video/publish_report.json` 写入发布结果。

## 接入真实组件

在 `config/settings.yaml` 填入下面 4 类命令即可完成从演示到生产切换：

1. `asr.command`: Whisper 本地命令，输出 JSON/TXT 到 `{output_dir}`
2. `tts.command`: CosyVoice 推理命令，写出 `{audio_out}`
3. `avatar.command`: HeyGem 驱动命令，写出 `{video_out}`
4. `uploader.command_*`: 各平台上传脚本（`{video}` `{cover}` `{title}`）

当前默认已提供 `tools/*.py` wrapper 模板，可直接运行并逐步替换：

- `tools/asr_wrapper.py`: Whisper 优先，失败自动降级
- `tools/rewriter_wrapper.py`: Ollama 优先，失败自动降级
- `tools/tts_wrapper.py`: 可用 `COSYVOICE_CMD` 注入真实 TTS 命令
- `tools/avatar_wrapper.py`: 占位数字人视频生成，可替换 HeyGem
- `tools/social_upload_wrapper.py`: 统一调用 social-auto-upload

上传前需设置：

```bash
export SOCIAL_AUTO_UPLOAD_DIR=/abs/path/social-auto-upload
```

## social-auto-upload 联调参数

- `platform`: `douyin | xhs | kuaishou | channels`
- `account`: 对应平台账号别名（你本地 social-auto-upload 已登录的账号名）
- `action`: 固定 `upload`
- `video`: 对应 `{video}`
- `-pt`: 对应 `{cover}`
- `-t`: 对应 `{title}`
