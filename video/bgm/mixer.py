from __future__ import annotations

import shlex
from pathlib import Path

from core.config import Settings
from core.utils import run_local_command


class BGMMixer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def mix(self, video_in: Path, bgm_path: Path, video_out: Path) -> Path:
        cfg = self.settings.section("bgm")
        vol = float(cfg.get("volume", 0.12))
        video_in_q = shlex.quote(str(video_in))
        bgm_path_q = shlex.quote(str(bgm_path))
        video_out_q = shlex.quote(str(video_out))
        cmd = (
            f"ffmpeg -y -i {video_in_q} -i {bgm_path_q} "
            f"-filter_complex \"[1:a]volume={vol}[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[a]\" "
            f"-map 0:v -map \"[a]\" -c:v copy -shortest {video_out_q}"
        )
        run_local_command(cmd)
        return video_out
