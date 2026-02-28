from __future__ import annotations

from pathlib import Path

from core.utils import ensure_dir, write_text


class SubtitleGenerator:
    def generate(self, segments: list[dict], fallback_script: str, workdir: Path) -> Path:
        srt_path = ensure_dir(workdir / "subtitle") / "captions.srt"
        if segments:
            lines: list[str] = []
            for i, seg in enumerate(segments, start=1):
                start = self._to_srt_time(float(seg.get("start", 0.0)))
                end = self._to_srt_time(float(seg.get("end", seg.get("start", 0.0) + 2.0)))
                text = str(seg.get("text", "")).strip()
                lines.extend([str(i), f"{start} --> {end}", text, ""])
            return write_text(srt_path, "\n".join(lines))

        pseudo = "1\n00:00:00,000 --> 00:00:06,000\n" + fallback_script.strip()
        return write_text(srt_path, pseudo)

    @staticmethod
    def _to_srt_time(seconds: float) -> str:
        ms = int(seconds * 1000)
        h = ms // 3_600_000
        ms %= 3_600_000
        m = ms // 60_000
        ms %= 60_000
        s = ms // 1000
        ms %= 1000
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
