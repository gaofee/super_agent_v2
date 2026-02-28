from __future__ import annotations

from pathlib import Path

from core.config import Settings
from core.utils import run_local_command, write_text


class ScriptRewriter:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def rewrite(self, source_text: str, workdir: Path) -> Path:
        cfg = self.settings.section("rewriter")
        command = str(cfg.get("command", "")).strip()
        if command:
            prompt = source_text.replace('"', '\\"')
            completed = run_local_command(command.format(prompt=prompt, source_text=source_text.replace("\n", " ")))
            rewritten = completed.stdout.strip() or completed.stderr.strip()
        else:
            template = str(cfg.get("fallback_template", "{source_text}"))
            rewritten = template.format(source_text=source_text)

        return write_text(workdir / "script" / "rewritten.txt", rewritten)
