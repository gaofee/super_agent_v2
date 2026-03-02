from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil
import socket
import urllib.error
import urllib.request

from audio.tts.cosyvoice_tts import CosyVoiceTTS
from avatar.heygem.driver import HeyGemDriver
from core.config import Settings
from core.env_loader import load_local_env
from core.models import WorkflowInput
from core.utils import ensure_dir, media_duration_seconds, run_local_command, shell_quote, slugify_title
from script.extractor.extractor import ScriptExtractor
from script.rewriter.rewriter import ScriptRewriter
from uploader.multi_platform.publisher import MultiPlatformPublisher
from video.ffmpeg.pipeline import FFmpegPipeline
from workflow.pipeline import FullWorkflow

load_local_env()


def _extract_first_url(text: str) -> str:
    match = re.search(r"https?://[^\s，,。！!；;）)]+", text)
    return match.group(0) if match else text.strip()


def _split_sentences(text: str, max_chars: int = 18) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return []
    parts = [p.strip() for p in re.split(r"[。！？!?；;]", cleaned) if p.strip()]
    if not parts:
        parts = [cleaned]
    chunks: list[str] = []
    for part in parts:
        while len(part) > max_chars:
            chunks.append(part[:max_chars])
            part = part[max_chars:]
        if part:
            chunks.append(part)
    return chunks


def _to_srt_time(seconds: float) -> str:
    ms = int(seconds * 1000)
    h = ms // 3_600_000
    ms %= 3_600_000
    m = ms // 60_000
    ms %= 60_000
    s = ms // 1000
    ms %= 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _build_srt_from_text(text: str, duration: float) -> str:
    lines = _split_sentences(text)
    if not lines:
        lines = ["自动字幕生成中"]
    seg = max(0.8, duration / len(lines))
    start = 0.0
    rows: list[str] = []
    for idx, line in enumerate(lines, start=1):
        end = min(duration, start + seg)
        rows.extend([str(idx), f"{_to_srt_time(start)} --> {_to_srt_time(end)}", line, ""])
        start = end
    return "\n".join(rows).strip() + "\n"


def _deepseek_title_tags(script_text: str) -> tuple[str, str, str, str] | None:
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        return None

    model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1/chat/completions")
    system = "你是中文短视频标题专家，只输出JSON。"
    prompt = (
        "根据这段文案生成短视频标题信息，返回JSON对象，字段必须是："
        "main_title, sub_title, hot_title, tags。"
        "其中tags是字符串，用逗号分隔，不要markdown。\n\n"
        f"文案：{script_text}"
    )
    payload = {
        "model": model,
        "temperature": 0.7,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        content = str(body["choices"][0]["message"]["content"]).strip()
        matched = re.search(r"\{[\s\S]*\}", content)
        parsed = json.loads(matched.group(0) if matched else content)
        main = str(parsed.get("main_title", "")).strip()
        sub = str(parsed.get("sub_title", "")).strip()
        hot = str(parsed.get("hot_title", "")).strip()
        tags = str(parsed.get("tags", "")).strip()
        if not (main and sub and hot and tags):
            return None
        return main[:24], sub[:24], hot[:28], tags
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, KeyError, json.JSONDecodeError):
        return None


def _resolve_voice_ref(settings: Settings, ref_voice: str, voice_upload: str | None) -> tuple[str | None, str | None]:
    tts_cfg = settings.section("tts")
    if ref_voice == "自己声音":
        if voice_upload:
            return str(Path(voice_upload)), None
        return None, "请选择“自己声音”时上传参考音频。"

    if ref_voice == "标准女声":
        preset = str(tts_cfg.get("female_voice_ref", "")).strip()
        token = str(tts_cfg.get("female_voice_token", "female")).strip()
    else:
        preset = str(tts_cfg.get("male_voice_ref", "")).strip()
        token = str(tts_cfg.get("male_voice_token", "male")).strip()

    if preset and Path(preset).exists():
        return preset, None
    if token:
        return token, None
    return None, f"{ref_voice}未配置，请在 settings.yaml 的 tts 段配置对应音色。"


def _download_video(video_url: str, settings_path: str) -> tuple[str | None, str | None, str, str | None]:
    url = _extract_first_url(video_url)
    if not url:
        return None, None, "请输入视频 URL。", None

    settings = Settings.load(Path(settings_path))
    output_root = ensure_dir(settings.output_root / "downloads")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_template = output_root / f"source_{stamp}.%(ext)s"

    if shutil.which("yt-dlp") is not None:
        cmd = f"yt-dlp -o {shell_quote(out_template)} {shell_quote(url)}"
    elif shutil.which("python") is not None:
        cmd = f"python -m yt_dlp -o {shell_quote(out_template)} {shell_quote(url)}"
    elif shutil.which("python3") is not None:
        cmd = f"python3 -m yt_dlp -o {shell_quote(out_template)} {shell_quote(url)}"
    else:
        return None, None, "下载失败：未找到 yt-dlp 或可用 Python。", None

    completed = run_local_command(cmd, check=False)
    if completed.returncode != 0:
        reason = completed.stderr.strip() or completed.stdout.strip() or "unknown error"
        return None, None, f"下载失败：{reason[:320]}", None

    video_files = sorted(output_root.glob(f"source_{stamp}.*"))
    if not video_files:
        return None, None, "下载失败：未找到输出文件。", None

    video_path = str(video_files[-1].resolve())
    return video_path, video_path, f"下载完成：{video_path}（识别链接：{url}）", video_path


def _extract_copy(material_video: str | None, settings_path: str) -> str:
    if not material_video:
        return "请先上传或下载视频素材。"

    settings = Settings.load(Path(settings_path))
    extractor = ScriptExtractor(settings)
    workdir = ensure_dir(settings.output_root / "manual_extract" / datetime.now().strftime("%Y%m%d_%H%M%S"))
    transcript_path, _segments = extractor.extract(Path(material_video), workdir)
    return transcript_path.read_text(encoding="utf-8").strip()


def _rewrite_copy(source_text: str, language: str, model_name: str, settings_path: str) -> str:
    src = source_text.strip() or "这里是待仿写文案。"
    settings = Settings.load(Path(settings_path))
    rewriter = ScriptRewriter(settings)
    workdir = ensure_dir(Path("outputs") / "manual_rewrite" / datetime.now().strftime("%Y%m%d_%H%M%S"))
    rewritten_path = rewriter.rewrite(src, workdir)
    rewritten = rewritten_path.read_text(encoding="utf-8").strip()
    if rewritten and rewritten != src:
        return rewritten
    return (
        f"[{language} | {model_name}] 仿写结果：\n"
        f"开场：你是不是也遇到过同样问题？\n"
        f"主体：{src}\n"
        "结尾：按这套流程执行，今天就能开始稳定产出。"
    )


def _translate_copy(text: str, language: str) -> str:
    src = text.strip()
    if not src:
        return "请先输入文案。"
    if language == "中文":
        return src
    if language == "英文":
        return f"[EN]\n{src}"
    if language == "日文":
        return f"[JP]\n{src}"
    return src


def _tts_from_rewrite(
    rewritten_text: str,
    voice_upload: str | None,
    settings_path: str,
    ref_voice: str,
    pitch: float,
    delay: float,
) -> tuple[str | None, str, str | None]:
    text = rewritten_text.strip()
    if not text:
        return None, "请先生成或输入仿写文案。", None

    settings = Settings.load(Path(settings_path))
    voice_ref, voice_err = _resolve_voice_ref(settings, ref_voice, voice_upload)
    if voice_err:
        return None, voice_err, None

    tts = CosyVoiceTTS(settings)
    workdir = ensure_dir(settings.output_root / "manual_tts" / datetime.now().strftime("%Y%m%d_%H%M%S"))
    text_path = workdir / "script" / "rewritten.txt"
    text_path.parent.mkdir(parents=True, exist_ok=True)
    text_path.write_text(text, encoding="utf-8")
    raw_audio = tts.synthesize(text_path, voice_ref, workdir)

    adjusted_audio = raw_audio
    if abs(pitch - 1.0) > 1e-6 or delay > 1e-6:
        adjusted_audio = workdir / "audio" / "tts_adjusted.wav"
        delay_ms = int(delay * 1000)
        filters = [f"atempo={pitch}"]
        if delay_ms > 0:
            filters.append(f"adelay={delay_ms}|{delay_ms}")
        af = ",".join(filters)
        cmd = f"ffmpeg -y -i {shell_quote(raw_audio)} -af {shell_quote(af)} {shell_quote(adjusted_audio)}"
        run_local_command(cmd, check=False)
        if not adjusted_audio.exists():
            adjusted_audio = raw_audio

    if not adjusted_audio.exists():
        return None, "音频生成失败，请检查 CosyVoice 本地模型命令配置。", None
    return str(adjusted_audio), f"音频生成完成：{adjusted_audio}", str(adjusted_audio)


def _generate_avatar_video(
    material_video: str | None,
    material_select: str,
    rewritten_text: str,
    voice_upload: str | None,
    ref_voice: str,
    settings_path: str,
    infer_batch: float,
    infer_factor: float,
    current_audio: str | None,
) -> tuple[str | None, str | None, str]:
    if not material_video:
        return None, None, "请先上传视频素材。"

    settings = Settings.load(Path(settings_path))
    workdir = ensure_dir(settings.output_root / "manual_avatar" / datetime.now().strftime("%Y%m%d_%H%M%S"))

    audio_path: Path
    if current_audio:
        audio_path = Path(current_audio)
    else:
        voice_ref, voice_err = _resolve_voice_ref(settings, ref_voice, voice_upload)
        if voice_err:
            return None, None, voice_err
        tts = CosyVoiceTTS(settings)
        text = rewritten_text.strip() or "这是自动生成的口播内容。"
        text_path = workdir / "script" / "rewritten.txt"
        text_path.parent.mkdir(parents=True, exist_ok=True)
        text_path.write_text(text, encoding="utf-8")
        audio_path = tts.synthesize(text_path, voice_ref, workdir)

    driver = HeyGemDriver(settings)
    avatar_video = driver.generate(
        avatar_id="host_a",
        audio_in=audio_path,
        workdir=workdir,
        source_video=Path(material_video),
        infer_batch=int(infer_batch),
        infer_factor=float(infer_factor),
    )
    if not avatar_video.exists():
        return None, None, "数字人生成失败，请检查 HeyGem 本地命令或模型路径。"
    return str(avatar_video), str(avatar_video), f"数字人视频生成完成：{avatar_video}（素材类型：{material_select}）"


def _insert_title_video(current_video: str | None, title: str, settings_path: str) -> tuple[str | None, str | None, str]:
    if not current_video:
        return None, None, "请先生成视频。"
    settings = Settings.load(Path(settings_path))
    pipeline = FFmpegPipeline(settings)
    workdir = ensure_dir(settings.output_root / "manual_title" / datetime.now().strftime("%Y%m%d_%H%M%S"))
    final_video, cover = pipeline.add_title_and_cover(Path(current_video), title.strip() or "默认标题", workdir)
    return str(final_video), str(final_video), f"标题已插入，封面：{cover}"


def _insert_subtitle_video(
    current_video: str | None,
    subtitle_text: str,
    rewritten_text: str,
    font_name: str,
    font_size: str,
    font_weight: str,
    font_color: str,
    stroke_color: str,
    subtitle_margin: float,
    settings_path: str,
) -> tuple[str | None, str | None, str]:
    if not current_video:
        return None, None, "请先生成视频。"

    settings = Settings.load(Path(settings_path))
    workdir = ensure_dir(settings.output_root / "manual_subtitle" / datetime.now().strftime("%Y%m%d_%H%M%S"))
    duration = media_duration_seconds(Path(current_video), fallback=8.0)
    srt = workdir / "subtitle" / "manual.srt"
    srt.parent.mkdir(parents=True, exist_ok=True)
    text = subtitle_text.strip() or rewritten_text.strip()
    if not text:
        text = "自动字幕生成中"
    srt.write_text(_build_srt_from_text(text, duration), encoding="utf-8")

    size = int(str(font_size).replace("px", "") or "36")
    style = (
        f"FontName={font_name},Fontsize={size},"
        f"PrimaryColour=&H00{font_color.replace('#','')},"
        f"OutlineColour=&H00{stroke_color.replace('#','')},"
        f"Bold={1 if str(font_weight) in {'500','700'} else 0},"
        f"MarginV={int(subtitle_margin)},BorderStyle=1,Outline=1,Shadow=0"
    )

    out = workdir / "video" / "subtitled.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    subtitle_filter = f"subtitles={srt}:force_style='{style}'"
    cmd = f"ffmpeg -y -i {shell_quote(current_video)} -vf {shell_quote(subtitle_filter)} -c:a copy {shell_quote(out)}"
    run_local_command(cmd, check=False)
    if not out.exists():
        return current_video, current_video, "字幕插入失败，请检查字体或样式参数。"
    return str(out), str(out), f"字幕已插入：{out}"


def _insert_bgm_video(
    current_video: str | None,
    bgm_upload: str | None,
    bgm_select: str,
    bgm_volume: float,
    settings_path: str,
) -> tuple[str | None, str | None, str]:
    if not current_video:
        return None, None, "请先生成视频。"

    settings = Settings.load(Path(settings_path))
    workdir = ensure_dir(settings.output_root / "manual_bgm" / datetime.now().strftime("%Y%m%d_%H%M%S"))

    bgm_file = Path(bgm_upload) if bgm_upload else Path(str(settings.section("bgm").get("default_bgm", "")).strip())
    if not str(bgm_file) or not bgm_file.exists():
        tone = workdir / "audio" / "bgm_tone.mp3"
        tone.parent.mkdir(parents=True, exist_ok=True)
        freq = {"轻快节奏": 220, "科技律动": 260, "温暖叙事": 196}.get(bgm_select, 220)
        run_local_command(
            f"ffmpeg -y -f lavfi -i sine=frequency={freq}:duration=120 -c:a libmp3lame -q:a 6 {shell_quote(tone)}",
            check=False,
        )
        bgm_file = tone

    out = workdir / "video" / "bgm.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    vol = max(0.0, min(1.0, float(bgm_volume) / 100.0))
    cmd = (
        f"ffmpeg -y -i {shell_quote(current_video)} -i {shell_quote(bgm_file)} "
        f"-filter_complex \"[1:a]volume={vol}[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[a]\" "
        f"-map 0:v -map \"[a]\" -c:v copy -shortest {shell_quote(out)}"
    )
    run_local_command(cmd, check=False)
    if not out.exists():
        return current_video, current_video, "BGM 插入失败。"
    return str(out), str(out), f"BGM 已插入：{out}"


def _gen_title_tags(script_text: str) -> tuple[str, str, str, str]:
    text = script_text.strip() or "3步搭建本地自动化短视频系统"
    deepseek_result = _deepseek_title_tags(text)
    if deepseek_result:
        return deepseek_result
    main_title = text.splitlines()[0][:20]
    sub_title = "从提取到发布一条龙"
    hot_title = "新手也能快速跑通"
    tags = "AI短视频,数字人,自动化发布,本地工作流"
    return main_title, sub_title, hot_title, tags


def _preview_video(uploaded_video: str | None) -> tuple[str | None, str | None]:
    return uploaded_video, uploaded_video


def _copy_audio_preview(uploaded_audio: str | None) -> tuple[str | None, str | None]:
    return uploaded_audio, uploaded_audio


def _publish(
    current_video: str | None,
    material_video: str | None,
    voice_upload: str | None,
    rewritten_text: str,
    settings_path: str,
    platforms: list[str] | str | None,
    infer_batch: float,
    infer_factor: float,
) -> tuple[str, str, str, str, str, str | None]:
    settings = Settings.load(Path(settings_path))
    source_video = current_video or material_video
    platform_list = [platforms] if isinstance(platforms, str) else (platforms or [])

    if source_video:
        title_raw = (rewritten_text.splitlines()[0] if rewritten_text.strip() else "数字人口播")
        title = slugify_title(title_raw, 28).replace("_", " ")
        workdir = ensure_dir(settings.output_root / "manual_publish" / datetime.now().strftime("%Y%m%d_%H%M%S"))
        cover = workdir / "video" / "cover.jpg"
        cover.parent.mkdir(parents=True, exist_ok=True)
        run_local_command(f"ffmpeg -y -ss 1 -i {shell_quote(source_video)} -frames:v 1 {shell_quote(cover)}", check=False)
        publisher = MultiPlatformPublisher(settings)
        results = publisher.publish(Path(source_video), cover, title, platform_list)
        failed = [p for p, r in results.items() if not str(r).startswith("ok")]
        logs = "\n".join(f"{k}: {v}" for k, v in results.items())
        status_head = "发布完成" if not failed else f"发布部分失败（{len(failed)}/{len(results)}）"
        status = f"{status_head}\n成片: {source_video}\n封面: {cover}\n标题: {title}"
        return source_video, str(cover), title, logs, status, source_video

    if not material_video:
        return "", "", "", "请先上传视频素材。", "等待发布", None

    flow = FullWorkflow(settings)
    result = flow.run(
        WorkflowInput(
            input_video=Path(material_video),
            avatar_id="host_a",
            voice_ref=Path(voice_upload) if voice_upload else None,
            avatar_source_video=Path(material_video),
            infer_batch=int(infer_batch),
            infer_factor=float(infer_factor),
            platforms=platform_list,
        )
    )
    logs = "\n".join(f"{k}: {v}" for k, v in result.publish_results.items())
    status = (
        "发布完成\n"
        f"成片: {result.final_video}\n"
        f"封面: {result.cover_image}\n"
        f"标题: {result.title}"
    )
    return str(result.final_video), str(result.cover_image), result.title, logs, status, str(result.final_video)


def _diagnose_environment(settings_path: str) -> str:
    settings = Settings.load(Path(settings_path))

    def card(ok: bool, key: str, detail: str) -> str:
        cls = "diag-ok" if ok else "diag-warn"
        tag = "OK" if ok else "WARN"
        return (
            f"<div class='diag-card {cls}'>"
            f"<div class='diag-key'>{key}<span class='diag-tag'>{tag}</span></div>"
            f"<div class='diag-detail'>{detail}</div>"
            "</div>"
        )

    cards: list[str] = []
    for b in ["ffmpeg", "ffprobe", "whisper", "yt-dlp", "python3"]:
        found = shutil.which(b)
        cards.append(card(bool(found), f"binary:{b}", found or "not found"))

    try:
        import gradio  # type: ignore

        cards.append(card(True, "python:gradio", gradio.__version__))
    except ModuleNotFoundError:
        cards.append(card(False, "python:gradio", "not installed"))

    envs = {
        "DEEPSEEK_API_KEY": os.getenv("DEEPSEEK_API_KEY", "").strip(),
        "SOCIAL_AUTO_UPLOAD_DIR": os.getenv("SOCIAL_AUTO_UPLOAD_DIR", "").strip(),
        "WHISPER_MODEL_DIR": os.getenv("WHISPER_MODEL_DIR", "").strip(),
        "COSYVOICE_MODEL_DIR": os.getenv("COSYVOICE_MODEL_DIR", "").strip(),
        "HEYGEM_MODEL_DIR": os.getenv("HEYGEM_MODEL_DIR", "").strip(),
        "COSYVOICE_CMD": os.getenv("COSYVOICE_CMD", "").strip(),
        "HEYGEM_CMD": os.getenv("HEYGEM_CMD", "").strip(),
    }
    for k, v in envs.items():
        shown = "set" if v and k == "DEEPSEEK_API_KEY" else (v or "not set")
        cards.append(card(bool(v), f"env:{k}", shown))

    model_paths = [
        os.getenv("WHISPER_MODEL_DIR", "").strip(),
        os.getenv("COSYVOICE_MODEL_DIR", "").strip(),
        os.getenv("HEYGEM_MODEL_DIR", "").strip(),
    ]
    for p in model_paths:
        if not p:
            continue
        cards.append(card(Path(p).exists(), "path", p))

    uploader_cfg = settings.section("uploader")
    for platform in ["douyin", "hudiehao", "kuaishou", "xiaohongshu"]:
        key = f"command_{platform}"
        configured = bool(str(uploader_cfg.get(key, "")).strip())
        cards.append(card(configured, f"uploader:{platform}", "configured" if configured else "missing"))

    return "<div class='diag-grid'>" + "".join(cards) + "</div>"


def run() -> None:
    try:
        import gradio as gr
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError("gradio is required for web UI. Install with: pip install gradio") from exc

    css = """
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700;800&display=swap');

    :root {
      --bg-a: #98b4e6;
      --bg-b: #b6bce8;
      --bg-c: #c7b6e8;
      --card-bg: #f4f5f7;
      --card-border: #dde2ec;
      --button-a: #3e83f3;
      --button-b: #7955ea;
      --panel-height: 1160px;
      --col-width: 324px;
      --gap: 10px;
      --stage-width: calc(var(--col-width) * 4 + var(--gap) * 3);
    }

    html, body {
      background: linear-gradient(180deg, var(--bg-a) 0%, var(--bg-b) 57%, var(--bg-c) 100%);
    }

    .gradio-container {
      font-family: 'Noto Sans SC', sans-serif !important;
      background: transparent !important;
      max-width: 1536px !important;
      margin: 0 auto !important;
      padding: 6px 8px 10px !important;
      --button-primary-background-fill: linear-gradient(90deg, var(--button-a), var(--button-b));
      --button-primary-background-fill-hover: linear-gradient(90deg, #4b8df5, #8665ee);
      --button-primary-text-color: #ffffff;
      --button-secondary-background-fill: linear-gradient(90deg, var(--button-a), var(--button-b));
      --button-secondary-background-fill-hover: linear-gradient(90deg, #4b8df5, #8665ee);
      --button-secondary-text-color: #ffffff;
    }

    .topbar {
      position: relative;
      width: var(--stage-width);
      margin: 0 auto;
      text-align: center;
      padding: 14px 0 14px;
    }
    .brand {
      margin: 0;
      color: #1e2638;
      font-size: 54px;
      line-height: 1;
      font-weight: 800;
      letter-spacing: 0;
    }
    .brand .accent { color: #6a50f2; }
    .subtitle {
      margin-top: 8px;
      font-size: 31px;
      color: #3f4b61;
      font-weight: 600;
      line-height: 1.1;
    }
    .window-tools {
      position: absolute;
      right: 76px;
      top: 6px;
      display: flex;
      gap: 14px;
      color: #eef4ff;
      font-size: 16px;
      font-weight: 700;
      opacity: .95;
    }
    .avatar-dot {
      position: absolute;
      right: 8px;
      top: 41px;
      width: 50px;
      height: 50px;
      border-radius: 999px;
      border: 2px solid rgba(255,255,255,.86);
      background: radial-gradient(circle at 30% 30%, #77beff, #2a2f3a 75%);
      box-shadow: 0 6px 16px rgba(0,0,0,.24);
    }

    .grid-wrap {
      width: var(--stage-width);
      margin: 0 auto;
      display: grid !important;
      grid-template-columns: repeat(4, var(--col-width)) !important;
      gap: var(--gap) !important;
      min-height: var(--panel-height);
      align-items: stretch !important;
    }
    .grid-wrap > .gr-column {
      min-width: 0 !important;
      width: var(--col-width) !important;
      max-width: var(--col-width) !important;
      flex: initial !important;
    }
    .col-full { height: var(--panel-height); min-height: var(--panel-height); display: flex; }
    .col-split { height: var(--panel-height); min-height: var(--panel-height); display: flex; flex-direction: column; gap: var(--gap); }

    .module-card {
      width: 100%;
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 10px;
      box-shadow: 0 8px 20px rgba(100,116,152,.14), inset 0 1px 0 rgba(255,255,255,.9);
      overflow: visible !important;
      display: flex;
      flex-direction: column;
      box-sizing: border-box;
    }
    .module-tall { height: var(--panel-height); min-height: var(--panel-height); }
    .h02 { height: 404px; min-height: 404px; }
    .h03 { height: calc(var(--panel-height) - 404px - var(--gap)); min-height: calc(var(--panel-height) - 404px - var(--gap)); }
    .h05 { height: 620px; min-height: 620px; }
    .h06 { height: calc(var(--panel-height) - 620px - var(--gap)); min-height: calc(var(--panel-height) - 620px - var(--gap)); }

    .module-head {
      height: 40px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-bottom: 1px solid #e5e9f1;
      margin-bottom: 8px;
      position: relative;
      flex: 0 0 auto;
    }
    .module-head::before {
      content: '';
      position: absolute;
      top: 0;
      width: 124px;
      height: 36px;
      background: #e9eef9;
      clip-path: polygon(10% 0, 90% 0, 80% 100%, 20% 100%);
      z-index: 0;
    }
    .module-head span {
      z-index: 1;
      color: #4c71e4;
      font-size: 15px;
      font-weight: 800;
      line-height: 1;
    }
    .module-no {
      position: absolute;
      left: 0;
      top: 1px;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      color: #7f8896;
      font-size: 13px;
      font-weight: 700;
      z-index: 2;
    }
    .module-no::before {
      content: '';
      width: 3px;
      height: 24px;
      border-radius: 4px;
      background: linear-gradient(180deg, #2784ff, #8f4dff);
      display: inline-block;
    }
    .module-no b { font-size: 18px; color: #8d95a3; }

    .gr-form, .gr-box, .gr-group { border-color: #dbe2ee !important; border-radius: 8px !important; }
    .module-card .gr-group,
    .module-card .gr-form,
    .module-card .gr-box,
    .module-card .gr-block {
      overflow: visible !important;
    }
    .module-card * {
      scrollbar-width: none;
    }
    .module-card *::-webkit-scrollbar {
      width: 0 !important;
      height: 0 !important;
    }
    .gr-form label, .gr-block label, .gradio-container label {
      font-size: 11px !important;
      color: #566176 !important;
      line-height: 1.2 !important;
      margin-bottom: 3px !important;
    }
    .gr-block.gr-box, .gr-form, .gr-textbox, .gr-dropdown, .gr-number, .gr-slider { margin-bottom: 5px !important; }
    .gr-textbox textarea, .gr-textbox input, .gr-dropdown input, .gr-number input {
      min-height: 36px !important;
      font-size: 14px !important;
      color: #3a4255 !important;
    }
    .gr-textbox textarea {
      line-height: 1.44;
      resize: none !important;
      overflow-y: hidden !important;
    }
    .muted { color: #6c7688; font-size: 12px; margin-top: 0; margin-bottom: 3px; }

    .btn-main button,
    .btn-main > button {
      background: linear-gradient(90deg, var(--button-a), var(--button-b)) !important;
      border: 0 !important;
      border-radius: 7px !important;
      color: #fff !important;
      font-size: 15px !important;
      font-weight: 700 !important;
      min-height: 38px !important;
      box-shadow: 0 6px 14px rgba(56,105,214,.2);
    }
    .btn-main button:hover,
    .btn-main > button:hover { filter: brightness(1.04); }
    .bottom-btn {
      margin-top: auto !important;
    }
    .rewritten-large textarea {
      min-height: 210px !important;
    }
    .gradio-container .gr-file button {
      background: #f2f5fb !important;
      color: #4e5a71 !important;
      border: 1px solid #d5ddea !important;
      box-shadow: none !important;
    }
    .gradio-container .gr-file {
      border-style: dashed !important;
      border-color: #cfd7e6 !important;
      background: #f6f8fc !important;
    }
    .gradio-container .gr-colorpicker button {
      background: transparent !important;
      border: 1px solid #cfd7e6 !important;
      box-shadow: none !important;
    }
    .gradio-container .gr-colorpicker input[type="color"] {
      width: 100% !important;
      min-height: 34px !important;
      border: none !important;
      border-radius: 6px !important;
      background: transparent !important;
      padding: 0 !important;
    }

    .preview-short, .preview-tall {
      background: #eceff4;
      border: 1px solid #dfe3eb;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: hidden;
    }
    .preview-short {
      height: 170px !important;
      min-height: 170px !important;
    }
    .preview-tall {
      height: 500px !important;
      min-height: 500px !important;
    }
    .preview-short > div,
    .preview-tall > div,
    .preview-short .wrap,
    .preview-tall .wrap,
    .preview-short .empty,
    .preview-tall .empty {
      height: 100% !important;
      width: 100% !important;
      display: flex !important;
      align-items: center !important;
      justify-content: center !important;
      overflow: hidden !important;
    }
    .preview-short video {
      width: 96px !important;
      height: 170px !important;
      aspect-ratio: 9 / 16 !important;
      object-fit: cover;
      border-radius: 8px;
      background: #e8ebf2;
      overflow: hidden !important;
    }
    .preview-tall video {
      width: 214px !important;
      height: 380px !important;
      aspect-ratio: 9 / 16 !important;
      object-fit: cover;
      border-radius: 8px;
      background: #e8ebf2;
      overflow: hidden !important;
    }
    .preview-short .empty,
    .preview-tall .empty {
      color: #9ca5b4 !important;
      font-size: 13px !important;
      background: #eceff4 !important;
    }
    .audio-preview audio { width: 100%; min-height: 56px; }
    .gradio-container .gradio-radio .wrap {
      display: flex !important;
      flex-direction: row !important;
      gap: 10px !important;
      flex-wrap: wrap !important;
      align-items: center !important;
      overflow-x: visible !important;
    }
    .gradio-container .gradio-radio label {
      margin-bottom: 0 !important;
      font-size: 11px !important;
      color: #505a6c !important;
    }

    .footer-panel {
      margin-top: 8px;
      background: rgba(246,248,252,.84);
      border: 1px solid #dbe2ee;
      border-radius: 12px;
      padding: 10px;
    }
    .status-box {
      font-size: 12px;
      color: #4d5666;
      background: #edf1f7;
      border: 1px solid #dbe2ec;
      border-radius: 8px;
      padding: 8px;
      white-space: pre-wrap;
      min-height: 88px;
    }
    .diag-grid { display:grid; grid-template-columns:repeat(2,minmax(260px,1fr)); gap:8px; margin-top:8px; }
    .diag-card { border:1px solid #d5dbe7; border-radius:10px; background:#f7f9fd; padding:8px 10px; }
    .diag-ok { border-left:4px solid #1fa96b; }
    .diag-warn { border-left:4px solid #d65c5c; }
    .diag-key { font-size:12px; color:#2f3747; font-weight:700; display:flex; justify-content:space-between; align-items:center; gap:8px; }
    .diag-tag { font-size:11px; padding:2px 6px; border-radius:999px; background:#e8edf7; color:#4a5568; }
    .diag-ok .diag-tag { background:#dff4e9; color:#18794e; }
    .diag-warn .diag-tag { background:#fae3e3; color:#9f2f2f; }
    .diag-detail { margin-top:4px; font-size:11px; color:#647083; word-break:break-all; }

    @media (max-width: 1366px) {
      .brand { font-size: 40px; }
      .subtitle { font-size: 22px; }
      .module-head span { font-size: 20px; }
      .gr-form label, .gr-block label, .gradio-container label { font-size: 12px !important; }
      .gr-textbox textarea, .gr-textbox input, .gr-dropdown input, .gr-number input { font-size: 13px !important; }
      .btn-main button,
      .btn-main > button { font-size: 14px !important; }
      .grid-wrap {
        width: 100%;
        grid-template-columns: 1fr !important;
      }
      .grid-wrap > .gr-column { max-width: none !important; width: auto !important; }
      .col-full, .col-split, .module-tall, .h02, .h03, .h05, .h06 { height: auto; min-height: auto; }
      .diag-grid { grid-template-columns: 1fr; }
    }
    """

    def head(no: str, title: str) -> str:
        return "<div class='module-head'>" f"<div class='module-no'><b>{no}</b></div>" f"<span>{title}</span>" "</div>"

    with gr.Blocks(css=css, theme=gr.themes.Base(), title="AI获客") as demo:
        current_video_state = gr.State(value=None)
        current_audio_state = gr.State(value=None)

        gr.HTML(
            "<div class='topbar'>"
            "<div class='window-tools'><span>↻</span><span>—</span><span>□</span><span>✕</span></div>"
            "<h1 class='brand'>超级IP智能体</h1>"
            "<div class='subtitle'>AI时代，帮你快速获客！</div>"
            "<div class='avatar-dot'></div>"
            "</div>"
        )

        with gr.Row(elem_classes=["grid-wrap"], equal_height=True):
            with gr.Column(scale=1, elem_classes=["col-full"]):
                with gr.Group(elem_classes=["module-card", "module-tall"]):
                    gr.HTML(head("01", "文案生成"))
                    video_url = gr.Textbox(label="视频URL", placeholder="输入视频URL")
                    download_btn = gr.Button("下载视频", variant="primary", elem_classes=["btn-main"])
                    gr.Markdown("视频预览", elem_classes=["muted"])
                    video_preview_01 = gr.Video(label=None, interactive=False, elem_classes=["preview-short"])
                    extract_btn = gr.Button("提取视频文案", variant="primary", elem_classes=["btn-main"])
                    script_text = gr.Textbox(label="文案内容", lines=4, placeholder="提取的文案将显示在这里...")
                    with gr.Row():
                        language = gr.Dropdown(["中文", "英文", "日文"], value="中文", label="语言")
                        llm_model = gr.Dropdown(["DeepSeek", "Qwen", "Llama"], value="DeepSeek", label="LLM模型")
                    rewrite_btn = gr.Button("执行仿写", variant="primary", elem_classes=["btn-main"])
                    rewritten_text = gr.Textbox(label="新文案（中文）", lines=6, placeholder="仿写后的文案将显示在这里...", elem_classes=["rewritten-large"])
                    translate_btn = gr.Button("翻译文案", variant="primary", elem_classes=["btn-main", "bottom-btn"])

            with gr.Column(scale=1, elem_classes=["col-split"]):
                with gr.Group(elem_classes=["module-card", "module-half", "h02"]):
                    gr.HTML(head("02", "标题与标签"))
                    gen_title_btn = gr.Button("标题与话题标签生成", variant="primary", elem_classes=["btn-main"])
                    main_title = gr.Textbox(label="封面主标题", placeholder="输入主标题")
                    sub_title = gr.Textbox(label="副标题", placeholder="输入副标题")
                    hot_title = gr.Textbox(label="爆款视频标题", placeholder="输入爆款标题")
                    tags = gr.Textbox(label="视频标签", placeholder="输入标签，用逗号分隔")

                with gr.Group(elem_classes=["module-card", "module-half", "h03"]):
                    gr.HTML(head("03", "音频生成"))
                    ref_voice = gr.Dropdown(["自己声音", "标准女声", "标准男声"], value="自己声音", label="参考音频（音色）")
                    pitch_slider = gr.Slider(0.5, 2.0, value=1.0, step=0.1, label="调节语速")
                    delay_slider = gr.Slider(0.0, 3.0, value=1.0, step=0.1, label="延迟播音")
                    voice_upload = gr.File(label="上传音频", file_types=["audio"], type="filepath")
                    tts_btn = gr.Button("文案转音频", variant="primary", elem_classes=["btn-main"])
                    gr.Markdown("音频预览", elem_classes=["muted"])
                    audio_preview = gr.Audio(label=None, interactive=False, elem_classes=["audio-preview"])

            with gr.Column(scale=1, elem_classes=["col-full"]):
                with gr.Group(elem_classes=["module-card", "module-tall"]):
                    gr.HTML(head("04", "视频生成"))
                    material_select = gr.Dropdown(["闲聊", "知识口播", "产品讲解"], value="闲聊", label="选择视频素材")
                    with gr.Row():
                        infer_batch = gr.Number(value=20, label="推理批次", precision=0)
                        infer_factor = gr.Number(value=1.5, label="推理因子")
                    material_video = gr.File(label="上传视频素材", file_types=["video"], type="filepath")
                    gen_video_btn = gr.Button("生成视频", variant="primary", elem_classes=["btn-main"])
                    gr.Markdown("视频预览", elem_classes=["muted"])
                    video_preview_04 = gr.Video(label=None, interactive=False, elem_classes=["preview-tall"])
                    insert_title_btn = gr.Button("插入标题", variant="primary", elem_classes=["btn-main"])

            with gr.Column(scale=1, elem_classes=["col-split"]):
                with gr.Group(elem_classes=["module-card", "module-half", "h05"]):
                    gr.HTML(head("05", "添加字幕"))
                    with gr.Row():
                        font_name = gr.Dropdown(["黑体", "思源黑体", "苹方"], value="黑体", label="字体与字号")
                        font_size = gr.Dropdown(["24px", "30px", "36px", "42px"], value="36px", label="")
                    with gr.Row():
                        font_weight = gr.Dropdown(["300", "400", "500", "700"], value="400", label="字体粗细")
                        font_color = gr.ColorPicker(value="#DE0202", label="字体颜色")
                        stroke_color = gr.ColorPicker(value="#ECB1B1", label="描边颜色")
                    subtitle_margin = gr.Slider(0, 360, value=180, step=10, label="底部边距")
                    manual_subtitle = gr.Textbox(label="字幕调整", lines=6, placeholder="手动调整字幕内容...")
                    insert_subtitle_btn = gr.Button("插入字幕", variant="primary", elem_classes=["btn-main"])

                with gr.Group(elem_classes=["module-card", "module-half", "h06"]):
                    gr.HTML(head("06", "添加BGM"))
                    bgm_volume = gr.Slider(0, 100, value=50, step=1, label="调整背景音量")
                    bgm_select = gr.Dropdown(["轻快节奏", "科技律动", "温暖叙事"], value="轻快节奏", label="选择背景音乐")
                    bgm_upload = gr.File(label="上传背景音乐文件", file_types=["audio"], type="filepath")
                    insert_bgm_btn = gr.Button("插入BGM", variant="primary", elem_classes=["btn-main"])
                    platforms = gr.Radio(
                        choices=[("抖音", "douyin"), ("快手", "kuaishou"), ("视频号", "hudiehao"), ("小红书", "xiaohongshu")],
                        value="douyin",
                        label="发布平台",
                    )
                    publish_btn = gr.Button("发布", variant="primary", elem_classes=["btn-main"])

        with gr.Group(elem_classes=["footer-panel"]):
            with gr.Row():
                final_video = gr.Textbox(label="最终视频路径")
                final_cover = gr.Textbox(label="封面路径")
                final_title = gr.Textbox(label="最终标题")
            with gr.Row():
                publish_logs = gr.Textbox(label="发布日志", lines=4)
                final_status = gr.Textbox(label="状态", lines=4, value="等待发布", elem_classes=["status-box"])
            settings_path = gr.Textbox(label="配置文件", value="config/settings.yaml")
            diagnose_btn = gr.Button("诊断环境", variant="primary", elem_classes=["btn-main"])
            diagnose_output = gr.HTML("<div class='diag-grid'><div class='diag-card diag-warn'><div class='diag-key'>未执行诊断<span class='diag-tag'>WARN</span></div><div class='diag-detail'>点击“诊断环境”开始检测。</div></div></div>")

        download_btn.click(
            fn=_download_video,
            inputs=[video_url, settings_path],
            outputs=[material_video, video_preview_01, final_status, current_video_state],
        )
        extract_btn.click(fn=_extract_copy, inputs=[material_video, settings_path], outputs=[script_text])
        rewrite_btn.click(fn=_rewrite_copy, inputs=[script_text, language, llm_model, settings_path], outputs=[rewritten_text])
        translate_btn.click(fn=_translate_copy, inputs=[rewritten_text, language], outputs=[rewritten_text])
        gen_title_btn.click(fn=_gen_title_tags, inputs=[rewritten_text], outputs=[main_title, sub_title, hot_title, tags])

        material_video.change(fn=_preview_video, inputs=[material_video], outputs=[video_preview_04, current_video_state])
        voice_upload.change(fn=_copy_audio_preview, inputs=[voice_upload], outputs=[audio_preview, current_audio_state])
        tts_btn.click(
            fn=_tts_from_rewrite,
            inputs=[rewritten_text, voice_upload, settings_path, ref_voice, pitch_slider, delay_slider],
            outputs=[audio_preview, final_status, current_audio_state],
        )

        gen_video_btn.click(
            fn=_generate_avatar_video,
            inputs=[material_video, material_select, rewritten_text, voice_upload, ref_voice, settings_path, infer_batch, infer_factor, current_audio_state],
            outputs=[video_preview_04, current_video_state, final_status],
        )

        insert_title_btn.click(
            fn=_insert_title_video,
            inputs=[current_video_state, main_title, settings_path],
            outputs=[video_preview_04, current_video_state, final_status],
        )
        insert_subtitle_btn.click(
            fn=_insert_subtitle_video,
            inputs=[current_video_state, manual_subtitle, rewritten_text, font_name, font_size, font_weight, font_color, stroke_color, subtitle_margin, settings_path],
            outputs=[video_preview_04, current_video_state, final_status],
        )
        insert_bgm_btn.click(
            fn=_insert_bgm_video,
            inputs=[current_video_state, bgm_upload, bgm_select, bgm_volume, settings_path],
            outputs=[video_preview_04, current_video_state, final_status],
        )

        publish_btn.click(
            fn=_publish,
            inputs=[current_video_state, material_video, voice_upload, rewritten_text, settings_path, platforms, infer_batch, infer_factor],
            outputs=[final_video, final_cover, final_title, publish_logs, final_status, current_video_state],
        )
        diagnose_btn.click(fn=_diagnose_environment, inputs=[settings_path], outputs=[diagnose_output])

    def pick_port(start: int = 7860, end: int = 7890) -> int:
        for port in range(start, end + 1):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(("127.0.0.1", port)) != 0:
                    return port
        return start

    port = int(os.getenv("GRADIO_SERVER_PORT", str(pick_port())))
    demo.launch(server_name="127.0.0.1", server_port=port)


if __name__ == "__main__":
    run()
