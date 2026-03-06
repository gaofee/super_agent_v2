from __future__ import annotations

import argparse
import math
import os
import shlex
import subprocess
import sys
from pathlib import Path


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def run_cmd(cmd: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    # Avoid Intel/OpenMP SHM issues on macOS and constrained environments.
    env.setdefault("KMP_USE_SHM", "0")
    env.setdefault("OMP_NUM_THREADS", "1")
    env.setdefault("KMP_AFFINITY", "disabled")
    env.setdefault("MPLCONFIGDIR", "/tmp/cosyvoice_mpl")
    env.setdefault("NUMBA_CACHE_DIR", "/tmp/cosyvoice_numba")
    Path(env["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)
    Path(env["NUMBA_CACHE_DIR"]).mkdir(parents=True, exist_ok=True)
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, env=env)


def shell_quote(path_or_text: str | Path) -> str:
    text = str(path_or_text)
    if os.name == "nt":
        return subprocess.list2cmdline([text])
    return shlex.quote(text)


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
    require_real_tts = bool(cosy_cmd) or bool(args.voice_ref and args.voice_ref != "__EMPTY__")
    if cosy_cmd:
        text_raw = args.text
        text_safe = text_raw.replace('"', '\\"')
        cmd = cosy_cmd.format(
            text_file=str(text_file),
            voice_ref=args.voice_ref,
            audio_out=str(audio_out),
            text=text_safe,
            model_dir=model_dir,
            text_file_q=shell_quote(text_file),
            voice_ref_q=shell_quote(args.voice_ref),
            audio_out_q=shell_quote(audio_out),
            text_q=shell_quote(text_raw),
            model_dir_q=shell_quote(model_dir),
        )
        proc = run_cmd(cmd)
        if proc.returncode == 0 and audio_out.exists():
            return 0
        err = (proc.stderr or proc.stdout or "").strip()
        if require_real_tts:
            print(
                "real tts failed; COSYVOICE_CMD execution error. "
                f"detail: {err[:400]}",
                file=sys.stderr,
            )
            return 9

    text = args.text.strip() or read_text(text_file).replace("\n", " ").strip()
    voice_hint = (args.voice_ref or "").lower()
    if "male" in voice_hint or "男" in voice_hint:
        freq = 185
    elif "female" in voice_hint or "女" in voice_hint:
        freq = 235
    else:
        freq = 220
    duration = max(4.0, min(30.0, math.ceil(len(text) / 8.0)))
    ffmpeg = (
        f"ffmpeg -y -f lavfi -i sine=frequency={freq}:sample_rate=24000:duration={duration} "
        f"-af volume=0.12 {shell_quote(audio_out)}"
    )
    proc = run_cmd(ffmpeg)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
