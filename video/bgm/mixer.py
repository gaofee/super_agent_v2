from __future__ import annotations

from pathlib import Path

from core.config import Settings
from core.utils import run_local_command, shell_quote


class BGMMixer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def mix(self, video_in: Path, bgm_path: Path, video_out: Path) -> Path:
        cfg = self.settings.section("bgm")
        vol = float(cfg.get("volume", 0.12))
        video_in_q = shell_quote(video_in)
        bgm_path_q = shell_quote(bgm_path)
        video_out_q = shell_quote(video_out)
        cmd = (
            f"ffmpeg -y -i {video_in_q} -i {bgm_path_q} "
            f"-filter_complex \"[1:a]volume={vol}[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[a]\" "
            f"-map 0:v -map \"[a]\" -c:v copy -shortest {video_out_q}"
        )
        run_local_command(cmd)
        return video_out
