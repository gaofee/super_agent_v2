from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from core.config import Settings
from core.models import WorkflowInput
from workflow.pipeline import FullWorkflow


def run_pipeline(args: argparse.Namespace) -> int:
    cfg = Settings.load(Path(args.settings))
    flow = FullWorkflow(cfg)
    result = flow.run(
        WorkflowInput(
            input_video=Path(args.input_video),
            avatar_id=args.avatar_id,
            voice_ref=Path(args.voice_ref) if args.voice_ref else None,
            platforms=args.platforms,
        )
    )

    print("Workflow Output")
    print(f"Extracted Script: {result.extracted_script}")
    print(f"Rewritten Script: {result.rewritten_script}")
    print(f"TTS Audio: {result.tts_audio}")
    print(f"Avatar Video: {result.avatar_video}")
    print(f"Subtitle: {result.subtitle_srt}")
    print(f"Final Video: {result.final_video}")
    print(f"Cover: {result.cover_image}")
    print(f"Title: {result.title}")
    print(f"Publish: {result.publish_results}")
    return 0


def doctor(args: argparse.Namespace) -> int:
    cfg = Settings.load(Path(args.settings))
    print("Environment Doctor")
    for cmd in ["ffmpeg", "ffprobe", "whisper", "yt-dlp"]:
        found = shutil.which(cmd)
        status = "ok" if found else "warn"
        print(f"binary:{cmd}: {status} ({found or 'not found'})")

    asr_cmd = str(cfg.section("asr").get("command", "")).strip()
    tts_cmd = str(cfg.section("tts").get("command", "")).strip()
    avatar_cmd = str(cfg.section("avatar").get("command", "")).strip()
    uploader_cfg = cfg.section("uploader")
    uploader_ready = any(str(v).strip() for k, v in uploader_cfg.items() if k.startswith("command_"))

    print(f"asr.command: {'ok' if asr_cmd else 'demo'}")
    print(f"tts.command: {'ok' if tts_cmd else 'demo'}")
    print(f"avatar.command: {'ok' if avatar_cmd else 'demo'}")
    print(f"uploader.command_*: {'ok' if uploader_ready else 'demo'}")
    return 0


def audit(args: argparse.Namespace) -> int:
    cfg = Settings.load(Path(args.settings))
    asr_cmd = str(cfg.section("asr").get("command", "")).strip()
    rewrite_cmd = str(cfg.section("rewriter").get("command", "")).strip()
    tts_cmd = str(cfg.section("tts").get("command", "")).strip()
    avatar_cmd = str(cfg.section("avatar").get("command", "")).strip()
    bgm_default = str(cfg.section("bgm").get("default_bgm", "")).strip()
    uploader_cfg = cfg.section("uploader")
    uploader_ready = {
        "douyin": bool(str(uploader_cfg.get("command_douyin", "")).strip()),
        "hudiehao": bool(str(uploader_cfg.get("command_hudiehao", "")).strip()),
        "kuaishou": bool(str(uploader_cfg.get("command_kuaishou", "")).strip()),
        "xiaohongshu": bool(str(uploader_cfg.get("command_xiaohongshu", "")).strip()),
    }

    checks = [
        ("1. 对标文案提取", "production" if asr_cmd else "demo"),
        ("2. 文案语义仿写", "production" if rewrite_cmd else "demo"),
        ("3. 声音克隆合成", "production" if tts_cmd else "demo"),
        ("4. 数字人口播", "production" if avatar_cmd else "demo"),
        ("5. 自动字幕", "production"),
        ("6. 自动BGM", "production" if bgm_default else "demo"),
        ("7. 自动标题", "production"),
        ("8. 自动封面", "production"),
        ("9. 多平台发布", "production" if all(uploader_ready.values()) else "partial"),
    ]
    print("Capability Audit")
    for name, status in checks:
        print(f"{name}: {status}")
    print(
        "uploader detail: "
        + ", ".join(f"{k}={'ok' if v else 'missing'}" for k, v in uploader_ready.items())
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local short-video automation pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    run_cmd = sub.add_parser("run", help="run full workflow")
    run_cmd.add_argument("--input-video", required=True, help="benchmark video path")
    run_cmd.add_argument("--voice-ref", default="", help="voice reference wav (optional in demo mode)")
    run_cmd.add_argument("--avatar-id", default="host_a", help="digital avatar id")
    run_cmd.add_argument(
        "--platforms",
        nargs="+",
        default=["douyin", "hudiehao", "kuaishou", "xiaohongshu"],
        help="publish platforms",
    )
    run_cmd.add_argument("--settings", default="config/settings.yaml", help="settings yaml path")
    run_cmd.set_defaults(func=run_pipeline)

    doctor_cmd = sub.add_parser("doctor", help="check local environment")
    doctor_cmd.add_argument("--settings", default="config/settings.yaml", help="settings yaml path")
    doctor_cmd.set_defaults(func=doctor)

    audit_cmd = sub.add_parser("audit", help="audit completion status for 9 capabilities")
    audit_cmd.add_argument("--settings", default="config/settings.yaml", help="settings yaml path")
    audit_cmd.set_defaults(func=audit)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
