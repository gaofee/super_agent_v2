from __future__ import annotations

from datetime import datetime
from pathlib import Path

from audio.tts.cosyvoice_tts import CosyVoiceTTS
from avatar.heygem.driver import HeyGemDriver
from core.config import Settings
from core.models import WorkflowArtifacts, WorkflowInput
from core.utils import ensure_dir, read_text, slugify_title
from script.extractor.extractor import ScriptExtractor
from script.rewriter.rewriter import ScriptRewriter
from uploader.multi_platform.publisher import MultiPlatformPublisher
from video.bgm.mixer import BGMMixer
from video.ffmpeg.pipeline import FFmpegPipeline
from video.subtitle.generator import SubtitleGenerator


class FullWorkflow:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.extractor = ScriptExtractor(settings)
        self.rewriter = ScriptRewriter(settings)
        self.tts = CosyVoiceTTS(settings)
        self.avatar = HeyGemDriver(settings)
        self.subtitle = SubtitleGenerator()
        self.video = FFmpegPipeline(settings)
        self.bgm = BGMMixer(settings)
        self.publisher = MultiPlatformPublisher(settings)

    def run(self, data: WorkflowInput) -> WorkflowArtifacts:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        workdir = ensure_dir(self.settings.output_root / stamp)

        extracted_script_path, segments = self.extractor.extract(data.input_video, workdir)
        source_text = read_text(extracted_script_path)

        rewritten_script_path = self.rewriter.rewrite(source_text, workdir)
        tts_audio = self.tts.synthesize(rewritten_script_path, data.voice_ref, workdir)
        avatar_video = self.avatar.generate(data.avatar_id, tts_audio, workdir)

        rewritten_text = read_text(rewritten_script_path)
        subtitle_srt = self.subtitle.generate(segments, rewritten_text, workdir)

        subtitled = self.video.burn_subtitle(avatar_video, subtitle_srt, workdir)

        bgm_cfg = self.settings.section("bgm")
        bgm_file = str(bgm_cfg.get("default_bgm", "")).strip()
        if bgm_file:
            bgm_out = ensure_dir(workdir / "video") / "video_bgm.mp4"
            merged_video = self.bgm.mix(subtitled, Path(bgm_file), bgm_out)
        else:
            merged_video = subtitled

        video_cfg = self.settings.section("video")
        title = self._generate_title(rewritten_text, int(video_cfg.get("title_max_length", 28)))
        final_video, cover = self.video.add_title_and_cover(merged_video, title, workdir)

        publish_results = self.publisher.publish(final_video, cover, title, data.platforms)

        return WorkflowArtifacts(
            extracted_script=extracted_script_path,
            rewritten_script=rewritten_script_path,
            tts_audio=tts_audio,
            avatar_video=avatar_video,
            subtitle_srt=subtitle_srt,
            final_video=final_video,
            cover_image=cover,
            title=title,
            publish_results=publish_results,
        )

    @staticmethod
    def _generate_title(text: str, max_len: int) -> str:
        first_line = text.splitlines()[0] if text.strip() else "数字人口播"
        return slugify_title(first_line, max_len=max_len).replace("_", " ")
