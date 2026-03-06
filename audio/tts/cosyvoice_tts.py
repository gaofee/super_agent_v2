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
        if audio_out.exists():
            audio_out.unlink()
        text = read_text(rewritten_script).replace("\n", " ").strip()
        command_tmpl = str(cfg.get("command", "")).strip()
        if command_tmpl:
            voice_ref_arg = voice_ref if voice_ref else "__EMPTY__"
            # Provide both raw and shell-escaped placeholders to improve compatibility.
            cmd = command_tmpl.format(
                text_file=rewritten_script,
                voice_ref=voice_ref_arg,
                audio_out=audio_out,
                text=text,
                text_file_q=shell_quote(rewritten_script),
                voice_ref_q=shell_quote(voice_ref_arg),
                audio_out_q=shell_quote(audio_out),
                text_q=shell_quote(text),
            )
            completed = run_local_command(cmd, check=False)
            if completed.returncode == 0 and audio_out.exists() and audio_out.stat().st_size > 0:
                return audio_out
            # If command exists but failed to produce output, surface real error for debugging.
            err = (completed.stderr or completed.stdout or "").strip()
            if voice_ref:
                raise RuntimeError(
                    "CosyVoice 声音克隆失败：未生成音频。"
                    + (f" 详情: {err[:280]}" if err else "")
                )

        # Local fallback: synthesize a neutral tone with length tied to script size.
        duration = max(4.0, min(30.0, math.ceil(len(text) / 8.0)))
        cmd = (
            f"ffmpeg -y -f lavfi -i sine=frequency=220:sample_rate=24000:duration={duration} "
            f"-af volume=0.12 {shell_quote(audio_out)}"
        )
        run_local_command(cmd)
        return audio_out
