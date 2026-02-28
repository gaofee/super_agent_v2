from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml


class Settings:
    def __init__(self, raw: Dict[str, Any]) -> None:
        self.raw = raw

    @classmethod
    def load(cls, path: Path) -> "Settings":
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("settings yaml must be an object")
        return cls(data)

    def section(self, name: str) -> Dict[str, Any]:
        val = self.raw.get(name, {})
        if not isinstance(val, dict):
            raise ValueError(f"settings section '{name}' must be an object")
        return val

    @property
    def output_root(self) -> Path:
        return Path(self.raw.get("output_root", "outputs")).resolve()
