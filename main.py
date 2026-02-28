from __future__ import annotations

import shutil
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table

from core.config import Settings
from core.models import WorkflowInput
from workflow.pipeline import FullWorkflow

app = typer.Typer(help="Local short-video automation pipeline")
console = Console()


@app.command()
def run(
    input_video: Path = typer.Option(..., help="benchmark video path"),
    voice_ref: Optional[Path] = typer.Option(None, help="voice reference wav (optional in demo mode)"),
    avatar_id: str = typer.Option("host_a", help="digital avatar id"),
    platforms: List[str] = typer.Option(["douyin", "hudiehao", "kuaishou", "xiaohongshu"], help="publish platforms"),
    settings: Path = typer.Option(Path("config/settings.yaml"), help="settings yaml path"),
) -> None:
    cfg = Settings.load(settings)
    flow = FullWorkflow(cfg)
    result = flow.run(
        WorkflowInput(
            input_video=input_video,
            avatar_id=avatar_id,
            voice_ref=voice_ref,
            platforms=platforms,
        )
    )

    table = Table(title="Workflow Output")
    table.add_column("Key")
    table.add_column("Value")
    table.add_row("Extracted Script", str(result.extracted_script))
    table.add_row("Rewritten Script", str(result.rewritten_script))
    table.add_row("TTS Audio", str(result.tts_audio))
    table.add_row("Avatar Video", str(result.avatar_video))
    table.add_row("Subtitle", str(result.subtitle_srt))
    table.add_row("Final Video", str(result.final_video))
    table.add_row("Cover", str(result.cover_image))
    table.add_row("Title", result.title)
    table.add_row("Publish", str(result.publish_results))
    console.print(table)


@app.command()
def doctor(settings: Path = typer.Option(Path("config/settings.yaml"), help="settings yaml path")) -> None:
    cfg = Settings.load(settings)
    table = Table(title="Environment Doctor")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Detail")

    for cmd in ["ffmpeg", "ffprobe", "whisper"]:
        found = shutil.which(cmd)
        table.add_row(
            f"binary:{cmd}",
            "ok" if found else "warn",
            found or "not found (optional except ffmpeg/ffprobe)",
        )

    asr_cmd = str(cfg.section("asr").get("command", "")).strip()
    tts_cmd = str(cfg.section("tts").get("command", "")).strip()
    avatar_cmd = str(cfg.section("avatar").get("command", "")).strip()
    uploader_cfg = cfg.section("uploader")
    uploader_ready = any(str(v).strip() for k, v in uploader_cfg.items() if k.startswith("command_"))

    table.add_row("asr.command", "ok" if asr_cmd else "demo", "configured" if asr_cmd else "fallback mode")
    table.add_row("tts.command", "ok" if tts_cmd else "demo", "configured" if tts_cmd else "fallback mode")
    table.add_row("avatar.command", "ok" if avatar_cmd else "demo", "configured" if avatar_cmd else "fallback mode")
    table.add_row(
        "uploader.command_*",
        "ok" if uploader_ready else "demo",
        "configured" if uploader_ready else "local simulated publish",
    )
    console.print(table)


if __name__ == "__main__":
    app()
