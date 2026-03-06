from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _pick_model_dir(root: Path) -> Path | None:
    env_name = os.getenv("COSYVOICE_INFER_MODEL", "").strip()
    candidates = []
    if env_name:
        candidates.append(root / "pretrained_models" / env_name)
    candidates.extend(
        [
            root / "pretrained_models" / "CosyVoice-300M",
            root / "pretrained_models" / "CosyVoice2-0.5B",
            root / "pretrained_models" / "Fun-CosyVoice3-0.5B",
            root / "CosyVoice-300M",
        ]
    )
    for c in candidates:
        if c.exists():
            return c
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", required=True, help="CosyVoice repo root")
    parser.add_argument("--text-file", required=True)
    parser.add_argument("--voice-ref", default="")
    parser.add_argument("--audio-out", required=True)
    parser.add_argument("--text", default="")
    args = parser.parse_args()

    repo_root = Path(args.model_dir).resolve()
    audio_out = Path(args.audio_out).resolve()
    audio_out.parent.mkdir(parents=True, exist_ok=True)

    if not repo_root.exists():
        print(f"model_dir not found: {repo_root}", file=sys.stderr)
        return 2

    if sys.version_info >= (3, 12):
        print(
            "python version not supported for CosyVoice clone pipeline: "
            f"{sys.version.split()[0]}. Please use Python 3.10/3.11 runtime.",
            file=sys.stderr,
        )
        return 10

    model_dir = _pick_model_dir(repo_root)
    if model_dir is None:
        print(
            f"no pretrained model found under: {repo_root}. "
            "expected e.g. pretrained_models/CosyVoice-300M",
            file=sys.stderr,
        )
        return 3

    sys.path.insert(0, str(repo_root))
    matcha = repo_root / "third_party" / "Matcha-TTS"
    if matcha.exists():
        sys.path.insert(0, str(matcha))

    try:
        from cosyvoice.cli.cosyvoice import AutoModel  # type: ignore
        import torchaudio  # type: ignore
    except Exception as exc:  # noqa: BLE001
        print(f"import cosyvoice failed: {exc}", file=sys.stderr)
        return 4

    text = args.text.strip()
    if not text:
        text = Path(args.text_file).read_text(encoding="utf-8").strip()
    if not text:
        print("empty text", file=sys.stderr)
        return 5

    voice_ref = "" if args.voice_ref == "__EMPTY__" else args.voice_ref.strip()
    speaker_hint = voice_ref.lower()
    try:
        cosyvoice = AutoModel(model_dir=str(model_dir))
        if voice_ref and Path(voice_ref).exists():
            prompt_text = "这是一段用于音色克隆的参考语音。"
            stream = cosyvoice.inference_zero_shot(text, prompt_text, voice_ref, stream=False)
        else:
            speaker = "中文男" if ("male" in speaker_hint or "男" in speaker_hint) else "中文女"
            stream = cosyvoice.inference_sft(text, speaker, stream=False)

        first = next(iter(stream), None)
        if not first or "tts_speech" not in first:
            print("cosyvoice inference returned empty audio", file=sys.stderr)
            return 6
        torchaudio.save(str(audio_out), first["tts_speech"], cosyvoice.sample_rate)
    except Exception as exc:  # noqa: BLE001
        print(f"cosyvoice inference failed: {exc}", file=sys.stderr)
        return 7

    return 0 if audio_out.exists() else 8


if __name__ == "__main__":
    raise SystemExit(main())
