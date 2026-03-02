from __future__ import annotations

from pathlib import Path

from core.config import Settings
from core.utils import ensure_dir, run_local_command, shell_quote, write_text
from audio.asr.whisper_asr import WhisperASR


class ScriptExtractor:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.asr = WhisperASR(settings)

    def extract(self, input_video: Path, workdir: Path) -> tuple[Path, list[dict]]:
        cfg = self.settings.section("extractor")
        audio_path = ensure_dir(workdir / "audio") / "benchmark.wav"
        cmd_template = str(cfg.get("ffmpeg_audio_cmd", "")).strip()
        if cmd_template:
            cmd = cmd_template.format(input_video=input_video, audio_out=audio_path)
        else:
            cmd = (
                f"ffmpeg -y -i {shell_quote(input_video)} -vn "
                f"-acodec pcm_s16le -ar 16000 -ac 1 {shell_quote(audio_path)}"
            )
        run_local_command(cmd)

        transcript_text, segments = self.asr.transcribe(audio_path, workdir)
        transcript_path = write_text(workdir / "script" / "extracted.txt", transcript_text)
        return transcript_path, segments
