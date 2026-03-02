from __future__ import annotations

import json
import os
import shlex
import subprocess
from pathlib import Path
from typing import Optional


def run_local_command(command: str, *, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(command, shell=True, check=check, text=True, capture_output=True)


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def read_text(path: Path, fallback: str = "") -> str:
    if not path.exists():
        return fallback
    return path.read_text(encoding="utf-8")


def parse_whisper_json(path: Path) -> tuple[str, list[dict]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    text = data.get("text", "").strip()
    segments = data.get("segments", [])
    return text, segments


def slugify_title(title: str, max_len: int = 28) -> str:
    safe = "".join(ch for ch in title if ch.isalnum() or ch in "-_ ").strip().replace(" ", "_")
    return safe[:max_len] or "video"


def first_nonempty(*values: Optional[str]) -> str:
    for v in values:
        if v and v.strip():
            return v.strip()
    return ""


def shell_quote(path_or_text: str | Path) -> str:
    text = str(path_or_text)
    if os.name == "nt":
        return subprocess.list2cmdline([text])
    return shlex.quote(text)


def media_duration_seconds(media_file: Path, fallback: float = 6.0) -> float:
    cmd = (
        f"ffprobe -v error -show_entries format=duration "
        f"-of default=noprint_wrappers=1:nokey=1 {shell_quote(media_file)}"
    )
    completed = run_local_command(cmd, check=False)
    if completed.returncode != 0:
        return fallback
    try:
        val = float(completed.stdout.strip())
        if val > 0:
            return val
    except ValueError:
        pass
    return fallback
