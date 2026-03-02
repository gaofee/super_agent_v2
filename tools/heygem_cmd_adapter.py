from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import time
from pathlib import Path
import shutil
import urllib.request


def run_cmd(cmd: str) -> int:
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if proc.stdout.strip():
        print(proc.stdout.strip())
    if proc.returncode != 0 and proc.stderr.strip():
        print(proc.stderr.strip())
    return proc.returncode


def run_capture(cmd: str) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def shell_quote(path_or_text: str | Path) -> str:
    text = str(path_or_text)
    if os.name == "nt":
        return subprocess.list2cmdline([text])
    return shlex.quote(text)


def _auth_header() -> str:
    api_key = os.getenv("HEYGEM_API_KEY", "").strip()
    return f"-H 'Authorization: Bearer {api_key}'" if api_key else ""


def _submit_remote(api_url: str, args: argparse.Namespace, audio_in: Path, source_video: str) -> dict | None:
    submit_path = os.getenv("HEYGEM_API_SUBMIT_PATH", "/v1/video/generate").strip()
    auth = _auth_header()
    url = f"{api_url.rstrip('/')}{submit_path}"
    form = [
        f"-F avatar_id={shell_quote(args.avatar_id)}",
        f"-F infer_batch={shell_quote(str(args.infer_batch))}",
        f"-F infer_factor={shell_quote(str(args.infer_factor))}",
        f"-F audio=@{shell_quote(audio_in)}",
    ]
    if source_video and Path(source_video).exists():
        form.append(f"-F source_video=@{shell_quote(source_video)}")
    cmd = f"curl -sS -X POST {auth} {' '.join(form)} {shell_quote(url)}"
    code, out, err = run_capture(cmd)
    if code != 0:
        if err:
            print(err)
        return None
    try:
        return json.loads(out) if out else None
    except json.JSONDecodeError:
        print(out)
        return None


def _poll_remote(api_url: str, job_id: str, timeout_sec: int) -> dict | None:
    status_path = os.getenv("HEYGEM_API_STATUS_PATH", "/v1/video/status/{job_id}").strip()
    auth = _auth_header()
    url = f"{api_url.rstrip('/')}{status_path.replace('{job_id}', job_id)}"
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        cmd = f"curl -sS -X GET {auth} {shell_quote(url)}"
        code, out, err = run_capture(cmd)
        if code == 0 and out:
            try:
                payload = json.loads(out)
            except json.JSONDecodeError:
                payload = {}
            if payload:
                status = str(payload.get('status', '')).lower()
                if status in {"success", "done", "completed"} or payload.get("video_url") or payload.get("video_path"):
                    return payload
        elif err:
            print(err)
        time.sleep(3)
    return None


def _materialize_remote_output(payload: dict, video_out: Path) -> int:
    video_url = str(payload.get("video_url", "")).strip()
    video_path = str(payload.get("video_path", "")).strip()
    if video_path and Path(video_path).exists():
        shutil.copy2(video_path, video_out)
        return 0
    if video_url:
        try:
            with urllib.request.urlopen(video_url, timeout=120) as resp:
                video_out.write_bytes(resp.read())
            return 0
        except Exception as exc:
            print(str(exc))
            return 1
    return 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--avatar-id", required=True)
    parser.add_argument("--audio-in", required=True)
    parser.add_argument("--source-video", default="")
    parser.add_argument("--video-out", required=True)
    parser.add_argument("--infer-batch", default="20")
    parser.add_argument("--infer-factor", default="1.5")
    args = parser.parse_args()

    audio_in = Path(args.audio_in).resolve()
    video_out = Path(args.video_out).resolve()
    video_out.parent.mkdir(parents=True, exist_ok=True)

    source_video = "" if args.source_video == "__EMPTY__" else args.source_video
    model_dir = Path(args.model_dir).resolve()
    if not model_dir.exists():
        print(f"model_dir not found: {model_dir}")
        return 2

    heygem_api = os.getenv("HEYGEM_API_URL", "").strip()
    if heygem_api:
        timeout_sec = int(os.getenv("HEYGEM_API_TIMEOUT_SEC", "600"))
        submit = _submit_remote(heygem_api, args, audio_in, source_video)
        if submit:
            if submit.get("video_url") or submit.get("video_path"):
                ret = _materialize_remote_output(submit, video_out)
                if ret == 0 and video_out.exists():
                    return 0
            job_id = str(submit.get("job_id", "")).strip()
            if job_id:
                done = _poll_remote(heygem_api, job_id, timeout_sec)
                if done:
                    ret = _materialize_remote_output(done, video_out)
                    if ret == 0 and video_out.exists():
                        return 0
        print("remote API failed or timed out, fallback to local compose mode")

    if source_video and Path(source_video).exists():
        cmd = (
            f"ffmpeg -y -stream_loop -1 -i {shell_quote(source_video)} "
            f"-i {shell_quote(audio_in)} "
            f"-vf \"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920\" "
            f"-map 0:v -map 1:a -c:v libx264 -pix_fmt yuv420p -shortest {shell_quote(video_out)}"
        )
        return run_cmd(cmd)

    cmd = (
        f"ffmpeg -y -f lavfi -i color=c=0x1e3a8a:s=1080x1920:r=25:d=8 "
        f"-i {shell_quote(audio_in)} "
        f"-map 0:v -map 1:a -c:v libx264 -pix_fmt yuv420p -shortest {shell_quote(video_out)}"
    )
    return run_cmd(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
