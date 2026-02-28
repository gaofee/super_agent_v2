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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--avatar-id", required=True)
    parser.add_argument("--audio-in", required=True)
    parser.add_argument("--video-out", required=True)
    args = parser.parse_args()

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
            model_dir=heygem_model_dir,
        )
        ret = run_cmd(cmd)
        if ret == 0 and video_out.exists():
            return 0

    duration = media_duration_seconds(audio_in)
    cmd = (
        f"ffmpeg -y -f lavfi -i color=c=0x1e3a8a:s=1080x1920:r=25:d={duration} "
        f"-i {shlex.quote(str(audio_in))} "
        f"-vf \"drawbox=x=80:y=120:w=920:h=1680:color=white@0.12:t=fill,"
        f"drawbox=x=120:y=if(lt(mod(t\\,2)\\,1)\\,650\\,700):w=840:h=140:color=white@0.32:t=fill\" "
        f"-map 0:v -map 1:a -c:v libx264 -pix_fmt yuv420p -shortest {shlex.quote(str(video_out))}"
    )
    return run_cmd(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
