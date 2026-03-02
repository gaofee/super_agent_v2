from __future__ import annotations

from pathlib import Path

from core.config import Settings
from core.utils import ensure_dir, media_duration_seconds, run_local_command, shell_quote


class HeyGemDriver:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate(
        self,
        avatar_id: str,
        audio_in: Path,
        workdir: Path,
        source_video: Path | None = None,
        infer_batch: int = 20,
        infer_factor: float = 1.5,
    ) -> Path:
        cfg = self.settings.section("avatar")
        command = str(cfg.get("command", "")).strip()
        video_out = ensure_dir(workdir / "avatar") / "avatar_raw.mp4"
        if command:
            source_video_arg = source_video if source_video else "__EMPTY__"
            run_local_command(
                command.format(
                    avatar_id=avatar_id,
                    audio_in=audio_in,
                    video_out=video_out,
                    source_video=source_video_arg,
                    infer_batch=infer_batch,
                    infer_factor=infer_factor,
                )
            )
            return video_out

        # Local fallback: generate a simple talking-host placeholder video bound to audio duration.
        duration = media_duration_seconds(audio_in, fallback=8.0)
        audio_q = shell_quote(audio_in)
        video_q = shell_quote(video_out)
        cmd = (
            f"ffmpeg -y -f lavfi -i color=c=0x1e3a8a:s=1080x1920:r=25:d={duration} "
            f"-i {audio_q} "
            f"-vf \"drawbox=x=80:y=120:w=920:h=1680:color=white@0.12:t=fill,"
            f"drawbox=x=120:y=if(lt(mod(t\\,2)\\,1)\\,650\\,700):w=840:h=140:color=white@0.32:t=fill\" "
            f"-map 0:v -map 1:a -c:v libx264 -pix_fmt yuv420p -shortest {video_q}"
        )
        run_local_command(cmd)
        return video_out
