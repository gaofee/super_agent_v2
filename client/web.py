from __future__ import annotations

from datetime import datetime
from pathlib import Path

from core.config import Settings
from core.models import WorkflowInput
from core.utils import ensure_dir, run_local_command, shell_quote
from script.extractor.extractor import ScriptExtractor
from script.rewriter.rewriter import ScriptRewriter
from workflow.pipeline import FullWorkflow


def _download_video(video_url: str, settings_path: str) -> tuple[str | None, str | None, str]:
    url = video_url.strip()
    if not url:
        return None, None, "请输入视频 URL。"

    settings = Settings.load(Path(settings_path))
    output_root = ensure_dir(settings.output_root / "downloads")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_template = output_root / f"source_{stamp}.%(ext)s"
    cmd = f"yt-dlp -o {shell_quote(out_template)} {shell_quote(url)}"
    completed = run_local_command(cmd, check=False)
    if completed.returncode != 0:
        # Fallback for direct media URLs when yt-dlp is unavailable.
        direct_mp4 = output_root / f"source_{stamp}.mp4"
        ffmpeg_cmd = f"ffmpeg -y -i {shell_quote(url)} -c copy {shell_quote(direct_mp4)}"
        ffmpeg_done = run_local_command(ffmpeg_cmd, check=False)
        if ffmpeg_done.returncode != 0:
            reason = completed.stderr.strip() or completed.stdout.strip() or "unknown error"
            reason2 = ffmpeg_done.stderr.strip() or ffmpeg_done.stdout.strip() or "unknown error"
            return None, None, f"下载失败：yt-dlp={reason[:120]} | ffmpeg={reason2[:120]}"

    video_files = sorted(output_root.glob(f"source_{stamp}.*"))
    if not video_files:
        return None, None, "下载失败：未找到输出文件。"

    video_path = str(video_files[-1].resolve())
    return video_path, video_path, f"下载完成：{video_path}"


def _extract_copy(material_video: str | None, settings_path: str) -> str:
    if not material_video:
        return "请先上传或下载视频素材。"

    settings = Settings.load(Path(settings_path))
    extractor = ScriptExtractor(settings)
    workdir = ensure_dir(settings.output_root / "manual_extract" / datetime.now().strftime("%Y%m%d_%H%M%S"))
    transcript_path, _segments = extractor.extract(Path(material_video), workdir)
    return transcript_path.read_text(encoding="utf-8").strip()


def _rewrite_copy(source_text: str, language: str, model_name: str) -> str:
    src = source_text.strip() or "这里是待仿写文案。"
    settings = Settings({"rewriter": {"command": ""}})
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


def _gen_title_tags(script_text: str) -> tuple[str, str, str, str]:
    text = script_text.strip() or "3步搭建本地自动化短视频系统"
    main_title = text.splitlines()[0][:20]
    sub_title = "从提取到发布一条龙"
    hot_title = "新手也能快速跑通"
    tags = "AI短视频,数字人,自动化发布,本地工作流"
    return main_title, sub_title, hot_title, tags


def _preview_video(uploaded_video: str | None) -> str | None:
    return uploaded_video


def _copy_audio_preview(uploaded_audio: str | None) -> str | None:
    return uploaded_audio


def _publish(
    material_video: str | None,
    voice_upload: str | None,
    settings_path: str,
    platforms: list[str],
) -> tuple[str, str, str, str, str]:
    if not material_video:
        return "", "", "", "请先上传视频素材。", "等待发布"

    settings = Settings.load(Path(settings_path))
    flow = FullWorkflow(settings)
    result = flow.run(
        WorkflowInput(
            input_video=Path(material_video),
            avatar_id="host_a",
            voice_ref=Path(voice_upload) if voice_upload else None,
            platforms=platforms,
        )
    )
    logs = "\n".join(f"{k}: {v}" for k, v in result.publish_results.items())
    status = (
        "发布完成\n"
        f"成片: {result.final_video}\n"
        f"封面: {result.cover_image}\n"
        f"标题: {result.title}"
    )
    return str(result.final_video), str(result.cover_image), result.title, logs, status


def run() -> None:
    try:
        import gradio as gr
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError("gradio is required for web UI. Install with: pip install gradio") from exc

    css = """
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700;800&display=swap');

    :root {
      --bg-top: #a8bde7;
      --bg-bottom: #d5c7ea;
      --card: #f4f5f7;
      --card-line: #e2e5ec;
      --text-main: #2f3747;
      --text-sub: #6f7888;
      --btn-a: #3f8ef5;
      --btn-b: #7f52ec;
      --brand: #232836;
      --accent: #6f52ff;
    }

    .gradio-container {
      font-family: 'Noto Sans SC', sans-serif !important;
      background: linear-gradient(180deg, var(--bg-top) 0%, #cec2e8 55%, #c7bce5 100%);
      max-width: 1360px !important;
      margin: 0 auto;
      padding: 14px !important;
    }

    .topbar {
      text-align: center;
      padding: 14px 0 10px;
      position: relative;
    }

    .brand {
      font-size: 56px;
      line-height: 1;
      font-weight: 800;
      color: var(--brand);
      margin: 0;
      letter-spacing: 1px;
    }

    .brand span {
      color: var(--accent);
      margin-left: 6px;
    }

    .subtitle {
      margin-top: 10px;
      font-size: 28px;
      color: #3d495f;
      font-weight: 500;
    }

    .avatar-dot {
      position: absolute;
      right: 4px;
      top: 6px;
      width: 54px;
      height: 54px;
      border-radius: 50%;
      background: radial-gradient(circle at 30% 30%, #6db5ff, #2b2f3b 75%);
      border: 2px solid rgba(255,255,255,0.8);
      box-shadow: 0 4px 14px rgba(0,0,0,0.22);
    }

    .grid-wrap { gap: 10px !important; }

    .module-card {
      background: var(--card);
      border: 1px solid var(--card-line);
      border-radius: 14px;
      padding: 10px;
      box-shadow: 0 2px 0 rgba(255,255,255,0.8) inset;
    }

    .module-head {
      height: 44px;
      display: flex;
      align-items: center;
      justify-content: center;
      margin-bottom: 8px;
      border-bottom: 1px solid #e6e9ef;
      position: relative;
      color: #4f6fe0;
      font-size: 28px;
      font-weight: 700;
    }

    .module-head::before {
      content: '';
      position: absolute;
      top: 0;
      width: 120px;
      height: 36px;
      background: #e9eef9;
      clip-path: polygon(10% 0, 90% 0, 80% 100%, 20% 100%);
      z-index: 0;
    }

    .module-head span {
      z-index: 1;
      font-size: 14px;
      font-weight: 700;
      color: #4b6fe4;
    }

    .module-no {
      position: absolute;
      left: 0;
      top: 2px;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      color: #818a98;
      font-size: 18px;
      font-weight: 700;
    }

    .module-no::before {
      content: '';
      width: 3px;
      height: 26px;
      border-radius: 4px;
      background: linear-gradient(180deg, #2583ff, #914dff);
      display: inline-block;
    }

    .module-no b {
      display: inline-block;
      font-size: 22px;
      color: #848b97;
    }

    .muted { color: var(--text-sub); font-size: 12px; }

    .gr-form, .gr-box, .gr-group {
      border-color: #dce1ea !important;
      border-radius: 8px !important;
    }

    .gr-button {
      border: none !important;
      background: linear-gradient(90deg, var(--btn-a), var(--btn-b)) !important;
      color: #fff !important;
      font-weight: 700 !important;
      border-radius: 8px !important;
      min-height: 38px;
    }

    .placeholder {
      background: #eceff4;
      border: 1px solid #dfe3eb;
      border-radius: 8px;
      min-height: 170px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #9ba4b4;
      font-size: 14px;
      margin-bottom: 8px;
    }

    .placeholder.tall { min-height: 240px; }
    .placeholder.xl { min-height: 440px; }

    .mini-sep {
      margin: 8px 0;
      border-top: 1px solid #e3e7ee;
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

    @media (max-width: 1200px) {
      .brand { font-size: 42px; }
      .subtitle { font-size: 22px; }
    }
    """

    def head(no: str, title: str) -> str:
        return (
            "<div class='module-head'>"
            f"<div class='module-no'><b>{no}</b></div>"
            f"<span>{title}</span>"
            "</div>"
        )

    with gr.Blocks(css=css, theme=gr.themes.Base(), title="茄条AI") as demo:
        gr.HTML(
            "<div class='topbar'>"
            "<h1 class='brand'>茄条<span>AI</span></h1>"
            "<div class='subtitle'>赶上AI浪潮，让AI智能体帮你跑赢2026</div>"
            "<div class='avatar-dot'></div>"
            "</div>"
        )

        with gr.Row(elem_classes=["grid-wrap"], equal_height=False):
            with gr.Column(scale=3):
                with gr.Group(elem_classes=["module-card"]):
                    gr.HTML(head("01", "文案生成"))
                    video_url = gr.Textbox(label="视频URL", placeholder="输入视频URL")
                    download_btn = gr.Button("下载视频")
                    gr.Markdown("视频预览", elem_classes=["muted"])
                    video_preview_01 = gr.Video(label=None, interactive=False)
                    extract_btn = gr.Button("提取视频文案")
                    script_text = gr.Textbox(label="文案内容", lines=5, placeholder="提取的文案将显示在这里...")
                    with gr.Row():
                        language = gr.Dropdown(["中文", "英文", "日文"], value="中文", label="语言")
                        llm_model = gr.Dropdown(["DeepSeek", "Qwen", "Llama"], value="DeepSeek", label="LLM模型")
                    rewrite_btn = gr.Button("执行仿写")
                    rewritten_text = gr.Textbox(label="新文案（中文）", lines=5, placeholder="仿写后的文案将显示在这里...")
                    translate_btn = gr.Button("翻译文案")

            with gr.Column(scale=3):
                with gr.Group(elem_classes=["module-card"]):
                    gr.HTML(head("02", "标题与标签"))
                    gen_title_btn = gr.Button("标题与话题标签生成")
                    main_title = gr.Textbox(label="封面主标题", placeholder="输入主标题")
                    sub_title = gr.Textbox(label="副标题", placeholder="输入副标题")
                    hot_title = gr.Textbox(label="爆款视频标题", placeholder="输入爆款标题")
                    tags = gr.Textbox(label="视频标签", placeholder="输入标签，用逗号分隔")

                with gr.Group(elem_classes=["module-card"]):
                    gr.HTML(head("03", "音频生成"))
                    ref_voice = gr.Dropdown(["自己声音", "标准女声", "标准男声"], value="自己声音", label="参考音频（音色）")
                    pitch_slider = gr.Slider(0.5, 2.0, value=1.0, step=0.1, label="调节语速")
                    delay_slider = gr.Slider(0.0, 3.0, value=1.0, step=0.1, label="延迟播音")
                    voice_upload = gr.File(label="上传音频", file_types=["audio"], type="filepath")
                    tts_btn = gr.Button("文案转音频")
                    gr.Markdown("音频预览", elem_classes=["muted"])
                    audio_preview = gr.Audio(label=None, interactive=False)

            with gr.Column(scale=3):
                with gr.Group(elem_classes=["module-card"]):
                    gr.HTML(head("04", "视频生成"))
                    material_select = gr.Dropdown(["闲聊", "知识口播", "产品讲解"], value="闲聊", label="选择视频素材")
                    with gr.Row():
                        infer_batch = gr.Number(value=20, label="推理批次", precision=0)
                        infer_factor = gr.Number(value=1.5, label="推理因子")
                    material_video = gr.File(label="上传视频素材", file_types=["video"], type="filepath")
                    gen_video_btn = gr.Button("生成视频")
                    gr.Markdown("视频预览", elem_classes=["muted"])
                    video_preview_04 = gr.Video(label=None, interactive=False)
                    insert_title_btn = gr.Button("插入标题")

            with gr.Column(scale=3):
                with gr.Group(elem_classes=["module-card"]):
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
                    insert_subtitle_btn = gr.Button("插入字幕")

                with gr.Group(elem_classes=["module-card"]):
                    gr.HTML(head("06", "添加BGM"))
                    bgm_volume = gr.Slider(0, 100, value=50, step=1, label="调整背景音量")
                    bgm_select = gr.Dropdown(["轻快节奏", "科技律动", "温暖叙事"], value="轻快节奏", label="选择背景音乐")
                    bgm_upload = gr.File(label="上传背景音乐文件", file_types=["audio"], type="filepath")
                    insert_bgm_btn = gr.Button("插入BGM")
                    platforms = gr.CheckboxGroup(
                        choices=["douyin", "kuaishou", "hudiehao", "xiaohongshu"],
                        value=["douyin"],
                        label="发布平台",
                    )
                    publish_btn = gr.Button("发布")

        gr.Markdown("---")
        with gr.Row():
            final_video = gr.Textbox(label="最终视频路径")
            final_cover = gr.Textbox(label="封面路径")
            final_title = gr.Textbox(label="最终标题")
        publish_logs = gr.Textbox(label="发布日志", lines=4)
        final_status = gr.Textbox(label="状态", lines=4, value="等待发布", elem_classes=["status-box"])
        settings_path = gr.Textbox(label="配置文件", value="config/settings.yaml")

        download_btn.click(
            fn=_download_video,
            inputs=[video_url, settings_path],
            outputs=[material_video, video_preview_01, final_status],
        )
        extract_btn.click(fn=_extract_copy, inputs=[material_video, settings_path], outputs=[script_text])
        rewrite_btn.click(fn=_rewrite_copy, inputs=[script_text, language, llm_model], outputs=[rewritten_text])
        gen_title_btn.click(fn=_gen_title_tags, inputs=[rewritten_text], outputs=[main_title, sub_title, hot_title, tags])

        material_video.change(fn=_preview_video, inputs=[material_video], outputs=[video_preview_04])
        gen_video_btn.click(fn=_preview_video, inputs=[material_video], outputs=[video_preview_04])
        voice_upload.change(fn=_copy_audio_preview, inputs=[voice_upload], outputs=[audio_preview])
        tts_btn.click(fn=_copy_audio_preview, inputs=[voice_upload], outputs=[audio_preview])

        publish_btn.click(
            fn=_publish,
            inputs=[material_video, voice_upload, settings_path, platforms],
            outputs=[final_video, final_cover, final_title, publish_logs, final_status],
        )

        # Styling-only buttons to keep prototype interaction complete.
        translate_btn.click(fn=lambda x: x, inputs=[rewritten_text], outputs=[rewritten_text])
        insert_title_btn.click(fn=lambda x: x, inputs=[video_preview_04], outputs=[video_preview_04])
        insert_subtitle_btn.click(fn=lambda x: x, inputs=[manual_subtitle], outputs=[manual_subtitle])
        insert_bgm_btn.click(fn=lambda x: x, inputs=[bgm_select], outputs=[bgm_select])

    demo.launch(server_name="127.0.0.1", server_port=7860)


if __name__ == "__main__":
    run()
