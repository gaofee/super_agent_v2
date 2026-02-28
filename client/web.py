from __future__ import annotations

from pathlib import Path

import gradio as gr

from core.config import Settings
from core.models import WorkflowInput
from workflow.pipeline import FullWorkflow


def _run_pipeline(input_video: str, voice_ref: str, avatar_id: str, platforms: list[str], settings_path: str):
    settings = Settings.load(Path(settings_path))
    flow = FullWorkflow(settings)
    result = flow.run(
        WorkflowInput(
            input_video=Path(input_video),
            avatar_id=avatar_id,
            voice_ref=Path(voice_ref) if voice_ref.strip() else None,
            platforms=platforms,
        )
    )
    logs = "\n".join(f"{k}: {v}" for k, v in result.publish_results.items())
    return (
        str(result.final_video),
        str(result.cover_image),
        result.title,
        logs,
        str(result.extracted_script),
        str(result.rewritten_script),
    )


def run() -> None:
    css = """
    .hero{background:linear-gradient(120deg,#0f172a,#1e3a8a);color:#fff;border-radius:18px;padding:20px}
    .app-title{font-family:'Avenir Next','PingFang SC',sans-serif;font-size:28px;font-weight:700}
    """

    with gr.Blocks(css=css, theme=gr.themes.Soft()) as demo:
        gr.HTML('<div class="hero"><div class="app-title">本地短视频自动生产工厂</div><div>提取 -> 仿写 -> 克隆 -> 数字人 -> 合成 -> 发布</div></div>')

        with gr.Row():
            input_video = gr.Textbox(label="对标视频路径")
            voice_ref = gr.Textbox(label="声音参考路径")
            avatar_id = gr.Textbox(label="数字人 ID", value="host_a")

        platforms = gr.CheckboxGroup(
            choices=["douyin", "hudiehao", "kuaishou", "xiaohongshu"],
            value=["douyin", "hudiehao", "kuaishou", "xiaohongshu"],
            label="发布平台",
        )
        settings_path = gr.Textbox(label="配置文件", value="config/settings.yaml")

        submit = gr.Button("一键生成并发布", variant="primary")

        with gr.Row():
            final_video = gr.Textbox(label="成片路径")
            cover = gr.Textbox(label="封面路径")
            title = gr.Textbox(label="标题")

        publish_logs = gr.Textbox(label="发布结果", lines=6)
        extracted = gr.Textbox(label="提取文案路径")
        rewritten = gr.Textbox(label="仿写文案路径")

        submit.click(
            fn=_run_pipeline,
            inputs=[input_video, voice_ref, avatar_id, platforms, settings_path],
            outputs=[final_video, cover, title, publish_logs, extracted, rewritten],
        )

    demo.launch(server_name="127.0.0.1", server_port=7860)


if __name__ == "__main__":
    run()
