from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List


@dataclass
class Segment:
    start: float
    end: float
    text: str


@dataclass
class WorkflowInput:
    input_video: Path
    avatar_id: str
    voice_ref: Path | None = None
    platforms: List[str] = field(default_factory=lambda: ["douyin", "hudiehao", "kuaishou", "xiaohongshu"])


@dataclass
class WorkflowArtifacts:
    extracted_script: Path
    rewritten_script: Path
    tts_audio: Path
    avatar_video: Path
    subtitle_srt: Path
    final_video: Path
    cover_image: Path
    title: str
    publish_results: Dict[str, str] = field(default_factory=dict)
