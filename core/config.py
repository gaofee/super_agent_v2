from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Dict


class Settings:
    def __init__(self, raw: Dict[str, Any]) -> None:
        self.raw = raw

    @classmethod
    def load(cls, path: Path) -> "Settings":
        content = path.read_text(encoding="utf-8")
        data: Dict[str, Any]
        try:
            import yaml  # type: ignore

            loaded = yaml.safe_load(content)
            data = loaded if isinstance(loaded, dict) else {}
        except ModuleNotFoundError:
            data = _parse_simple_yaml(content)
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


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return ""
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        pass
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        try:
            return ast.literal_eval(value)
        except (SyntaxError, ValueError):
            return value[1:-1]
    return value


def _parse_simple_yaml(content: str) -> Dict[str, Any]:
    root: Dict[str, Any] = {}
    stack: list[tuple[int, Dict[str, Any]]] = [(-1, root)]

    for raw_line in content.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        key = key.strip()
        val = val.strip()

        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]

        if not val:
            child: Dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = _parse_scalar(val)
    return root
