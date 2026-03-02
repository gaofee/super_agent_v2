from __future__ import annotations

import json
from pathlib import Path

from core.config import Settings
from core.utils import run_local_command, write_text


class MultiPlatformPublisher:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def publish(self, final_video: Path, cover: Path, title: str, platforms: list[str]) -> dict[str, str]:
        cfg = self.settings.section("uploader")
        results: dict[str, str] = {}

        for platform in platforms:
            key = f"command_{platform}"
            command = str(cfg.get(key, "")).strip()
            if not command:
                results[platform] = "local-simulated: no command configured"
                continue
            safe_title = title.replace('"', "").replace("'", "")
            completed = run_local_command(
                command.format(video=final_video, cover=cover, title=safe_title),
                check=False,
            )
            if completed.returncode == 0:
                results[platform] = "ok"
            else:
                detail = completed.stderr.strip() or completed.stdout.strip() or "unknown error"
                results[platform] = f"failed(rc={completed.returncode}): {detail[:2000]}"

        publish_report = {
            "title": title,
            "video": str(final_video),
            "cover": str(cover),
            "results": results,
        }
        report_path = final_video.parent / "publish_report.json"
        write_text(report_path, json.dumps(publish_report, ensure_ascii=False, indent=2))
        return results
