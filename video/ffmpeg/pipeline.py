from __future__ import annotations

from pathlib import Path

from core.config import Settings
from core.utils import ensure_dir, run_local_command, shell_quote


class FFmpegPipeline:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def burn_subtitle(self, avatar_video: Path, subtitle_file: Path, workdir: Path) -> Path:
        cfg = self.settings.section("video")
        style = cfg.get("subtitle_style", "")
        out = ensure_dir(workdir / "video") / "video_subtitled.mp4"
        avatar_video_q = shell_quote(avatar_video)
        out_q = shell_quote(out)
        subtitle_filter = f"subtitles={subtitle_file}:force_style='{style}'"
        subtitle_filter_q = shell_quote(subtitle_filter)
        cmd = (
            f"ffmpeg -y -i {avatar_video_q} -vf "
            f"{subtitle_filter_q} -c:a copy {out_q}"
        )
        run_local_command(cmd)
        return out

    def add_title_and_cover(self, video_in: Path, title: str, workdir: Path) -> tuple[Path, Path]:
        video_cfg = self.settings.section("video")
        final_video = ensure_dir(workdir / "video") / "final.mp4"
        escaped_title = title.replace("'", "\\'")
        video_in_q = shell_quote(video_in)
        final_video_q = shell_quote(final_video)
        cmd_title = (
            f"ffmpeg -y -i {video_in_q} -vf "
            f"drawtext=text='{escaped_title}':x=(w-text_w)/2:y=40:fontsize=56:fontcolor=white:box=1:boxcolor=black@0.45 "
            f"-c:a copy {final_video_q}"
        )
        completed = run_local_command(cmd_title, check=False)
        if completed.returncode != 0:
            run_local_command(f"ffmpeg -y -i {video_in_q} -c copy {final_video_q}")

        cover_time = int(video_cfg.get("cover_time_sec", 1))
        cover = ensure_dir(workdir / "video") / "cover.jpg"
        cover_q = shell_quote(cover)
        run_local_command(f"ffmpeg -y -ss {cover_time} -i {final_video_q} -frames:v 1 {cover_q}")
        return final_video, cover
