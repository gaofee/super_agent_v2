from __future__ import annotations

import argparse
import os
import shlex
import subprocess
from pathlib import Path


def media_duration_seconds(media_file: Path, fallback: float = 8.0) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(media_file),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        return fallback
    try:
        value = float(proc.stdout.strip())
        return value if value > 0 else fallback
    except ValueError:
        return fallback


def run_cmd(cmd: str) -> int:
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return proc.returncode


def shell_quote(path_or_text: str | Path) -> str:
    text = str(path_or_text)
    if os.name == "nt":
        return subprocess.list2cmdline([text])
    return shlex.quote(text)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--avatar-id", required=True)
    parser.add_argument("--audio-in", required=True)
    parser.add_argument("--video-out", required=True)
    parser.add_argument("--source-video", default="")
    parser.add_argument("--infer-batch", type=int, default=20)
    parser.add_argument("--infer-factor", type=float, default=1.5)
    args = parser.parse_args()
    source_video = "" if args.source_video == "__EMPTY__" else args.source_video

    audio_in = Path(args.audio_in)
    video_out = Path(args.video_out)
    video_out.parent.mkdir(parents=True, exist_ok=True)

    heygem_cmd = os.environ.get("HEYGEM_CMD", "").strip()
    heygem_model_dir = os.environ.get("HEYGEM_MODEL_DIR", "").strip()
    if heygem_cmd:
        cmd = heygem_cmd.format(
            avatar_id=args.avatar_id,
            audio_in=str(audio_in),
            video_out=str(video_out),
            source_video=source_video,
            infer_batch=args.infer_batch,
            infer_factor=args.infer_factor,
            model_dir=heygem_model_dir,
        )
        ret = run_cmd(cmd)
        if ret == 0 and video_out.exists():
            return 0

    duration = media_duration_seconds(audio_in)
    if source_video and Path(source_video).exists():
        # Fallback path: keep user's avatar source video and align duration with synthesized audio.
        cmd = (
            f"ffmpeg -y -stream_loop -1 -i {shell_quote(source_video)} "
            f"-i {shell_quote(audio_in)} "
            f"-vf \"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920\" "
            f"-map 0:v -map 1:a -c:v libx264 -pix_fmt yuv420p -shortest {shell_quote(video_out)}"
        )
        return run_cmd(cmd)

    cmd = (
        f"ffmpeg -y -f lavfi -i color=c=0x1e3a8a:s=1080x1920:r=25:d={duration} "
        f"-i {shell_quote(audio_in)} "
        f"-vf \"drawbox=x=80:y=120:w=920:h=1680:color=white@0.12:t=fill,"
        f"drawbox=x=120:y=if(lt(mod(t\\,2)\\,1)\\,650\\,700):w=840:h=140:color=white@0.32:t=fill\" "
        f"-map 0:v -map 1:a -c:v libx264 -pix_fmt yuv420p -shortest {shell_quote(video_out)}"
    )
    return run_cmd(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
