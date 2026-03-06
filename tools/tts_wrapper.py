from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def run_cmd(cmd: str, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    # Avoid Intel/OpenMP SHM issues on macOS and constrained environments.
    env.setdefault("KMP_USE_SHM", "0")
    env.setdefault("OMP_NUM_THREADS", "1")
    env.setdefault("KMP_AFFINITY", "disabled")
    env.setdefault("MPLCONFIGDIR", "/tmp/cosyvoice_mpl")
    env.setdefault("NUMBA_CACHE_DIR", "/tmp/cosyvoice_numba")
    Path(env["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)
    Path(env["NUMBA_CACHE_DIR"]).mkdir(parents=True, exist_ok=True)
    if extra_env:
        env.update({k: v for k, v in extra_env.items() if v})
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, env=env)


def shell_quote(path_or_text: str | Path) -> str:
    text = str(path_or_text)
    if os.name == "nt":
        return subprocess.list2cmdline([text])
    return shlex.quote(text)


def transcribe_prompt_text(audio_in: Path) -> str:
    if not audio_in.exists() or shutil.which("whisper") is None:
        return ""
    with tempfile.TemporaryDirectory(prefix="cosyvoice_prompt_") as tmp_dir:
        output_dir = Path(tmp_dir)
        whisper_model = os.environ.get("COSYVOICE_PROMPT_ASR_MODEL", os.environ.get("WHISPER_MODEL_NAME", "small"))
        cmd = [
            "whisper",
            str(audio_in),
            "--language",
            "Chinese",
            "--model",
            whisper_model,
            "--output_format",
            "json",
            "--output_dir",
            str(output_dir),
        ]
        whisper_model_dir = os.environ.get("WHISPER_MODEL_DIR", "").strip()
        if whisper_model_dir:
            cmd.extend(["--model_dir", whisper_model_dir])
        env = os.environ.copy()
        env.setdefault("KMP_USE_SHM", "0")
        env.setdefault("OMP_NUM_THREADS", "1")
        env.setdefault("KMP_AFFINITY", "disabled")
        env.setdefault("MPLCONFIGDIR", "/tmp/cosyvoice_mpl")
        env.setdefault("NUMBA_CACHE_DIR", "/tmp/cosyvoice_numba")
        Path(env["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)
        Path(env["NUMBA_CACHE_DIR"]).mkdir(parents=True, exist_ok=True)
        proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
        out_file = output_dir / f"{audio_in.stem}.json"
        if proc.returncode != 0 or not out_file.exists():
            return ""
        try:
            payload = json.loads(out_file.read_text(encoding="utf-8"))
        except Exception:
            return ""
        text = str(payload.get("text", "")).replace("\n", " ").strip()
        return text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--text-file", required=True)
    parser.add_argument("--voice-ref", default="")
    parser.add_argument("--audio-out", required=True)
    parser.add_argument("--text", default="")
    parser.add_argument("--prompt-text", default="")
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
        prompt_text = args.prompt_text.strip()
        if not prompt_text and args.voice_ref and args.voice_ref != "__EMPTY__":
            prompt_text = transcribe_prompt_text(Path(args.voice_ref))
        prompt_text_safe = prompt_text.replace('"', '\\"')
        cmd = cosy_cmd.format(
            text_file=str(text_file),
            voice_ref=args.voice_ref,
            audio_out=str(audio_out),
            text=text_safe,
            prompt_text=prompt_text_safe,
            model_dir=model_dir,
            text_file_q=shell_quote(text_file),
            voice_ref_q=shell_quote(args.voice_ref),
            audio_out_q=shell_quote(audio_out),
            text_q=shell_quote(text_raw),
            prompt_text_q=shell_quote(prompt_text),
            model_dir_q=shell_quote(model_dir),
        )
        extra_env = {"COSYVOICE_PROMPT_TEXT": prompt_text}
        proc = run_cmd(cmd, extra_env=extra_env)
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
