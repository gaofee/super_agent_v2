from __future__ import annotations

import os
from pathlib import Path


def _parse_env_line(line: str) -> tuple[str, str] | None:
    text = line.strip()
    if not text or text.startswith("#"):
        return None
    if text.startswith("export "):
        text = text[7:].strip()
    if "=" not in text:
        return None
    key, value = text.split("=", 1)
    key = key.strip()
    value = value.strip()
    if not key:
        return None
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    return key, value


def load_local_env(workspace_root: Path | None = None) -> list[Path]:
    root = workspace_root or Path(__file__).resolve().parents[1]
    candidates = [
        root / ".env",
        root / ".env.local",
        root / "local_models" / ".env",
        root / "local_models" / ".env.local",
        root / "local_models" / ".env.example",
    ]
    loaded: list[Path] = []
    for env_file in candidates:
        if not env_file.exists():
            continue
        for line in env_file.read_text(encoding="utf-8").splitlines():
            parsed = _parse_env_line(line)
            if not parsed:
                continue
            key, value = parsed
            os.environ.setdefault(key, value)
        loaded.append(env_file)
    return loaded

