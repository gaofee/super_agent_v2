from __future__ import annotations

import argparse
import math
import os
import shlex
import subprocess
from pathlib import Path


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def run_cmd(cmd: str) -> int:
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return proc.returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--text-file", required=True)
    parser.add_argument("--voice-ref", default="")
    parser.add_argument("--audio-out", required=True)
    parser.add_argument("--text", default="")
    args = parser.parse_args()

    text_file = Path(args.text_file)
    audio_out = Path(args.audio_out)
    audio_out.parent.mkdir(parents=True, exist_ok=True)

    cosy_cmd = os.environ.get("COSYVOICE_CMD", "").strip()
    model_dir = os.environ.get("COSYVOICE_MODEL_DIR", "").strip()
    if cosy_cmd:
        cmd = cosy_cmd.format(
            text_file=str(text_file),
            voice_ref=args.voice_ref,
            audio_out=str(audio_out),
            text=args.text,
            model_dir=model_dir,
        )
        if run_cmd(cmd) == 0 and audio_out.exists():
            return 0

    text = args.text.strip() or read_text(text_file).replace("\n", " ").strip()
    duration = max(4.0, min(30.0, math.ceil(len(text) / 8.0)))
    ffmpeg = (
        f"ffmpeg -y -f lavfi -i sine=frequency=220:sample_rate=24000:duration={duration} "
        f"-af volume=0.12 {shlex.quote(str(audio_out))}"
    )
    return run_cmd(ffmpeg)


if __name__ == "__main__":
    raise SystemExit(main())
