from __future__ import annotations

import math
from pathlib import Path

from core.config import Settings
from core.utils import ensure_dir, read_text, run_local_command, shell_quote


class CosyVoiceTTS:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def synthesize(self, rewritten_script: Path, voice_ref: str | None, workdir: Path) -> Path:
        cfg = self.settings.section("tts")
        audio_out = ensure_dir(workdir / "audio") / "tts.wav"
        text = read_text(rewritten_script).replace("\n", " ").strip()
        command_tmpl = str(cfg.get("command", "")).strip()
        if command_tmpl:
            voice_ref_arg = voice_ref if voice_ref else "__EMPTY__"
            run_local_command(
                command_tmpl.format(
                    text_file=rewritten_script,
                    voice_ref=voice_ref_arg,
                    audio_out=audio_out,
                    text=text,
                )
            )
            return audio_out

        # Local fallback: synthesize a neutral tone with length tied to script size.
        duration = max(4.0, min(30.0, math.ceil(len(text) / 8.0)))
        cmd = (
            f"ffmpeg -y -f lavfi -i sine=frequency=220:sample_rate=24000:duration={duration} "
            f"-af volume=0.12 {shell_quote(audio_out)}"
        )
        run_local_command(cmd)
        return audio_out
