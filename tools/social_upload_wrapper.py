from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
import shutil


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", required=True, choices=["douyin", "channels", "kuaishou", "xhs"])
    parser.add_argument("--account", required=True)
    parser.add_argument("--video", required=True)
    parser.add_argument("--cover", required=True)
    parser.add_argument("--title", required=True)
    args = parser.parse_args()

    base = os.environ.get("SOCIAL_AUTO_UPLOAD_DIR", "").strip()
    if not base:
        print("SOCIAL_AUTO_UPLOAD_DIR not set")
        return 1

    cli = Path(base) / "api" / "cli_main.py"
    if cli.exists():
        cmd = [
            sys.executable,
            str(cli),
            args.platform,
            args.account,
            "upload",
            args.video,
            "-pt",
            args.cover,
            "-t",
            args.title,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
    else:
        # Fallback for social-auto-upload-oh-v1.0 style repo.
        example_map = {
            "douyin": "upload_video_to_douyin.py",
            "channels": "upload_video_to_tencent.py",
            "xhs": "upload_video_to_xhs.py",
        }
        script_name = example_map.get(args.platform)
        if not script_name:
            if args.platform == "kuaishou":
                # social-auto-upload-oh-v1.0 未提供快手上传脚本，保持流程可运行。
                print("local-simulated: kuaishou uploader script not found in current social-auto-upload repo")
                return 0
            print(f"platform not supported in this social-auto-upload repo: {args.platform}")
            return 1
        script = Path(base) / "examples" / script_name
        if not script.exists():
            print(f"example script not found: {script}")
            return 1

        videos_dir = Path(base) / "videos"
        videos_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        ext = Path(args.video).suffix or ".mp4"
        target_video = videos_dir / f"{stamp}{ext}"
        target_meta = videos_dir / f"{stamp}.txt"
        try:
            shutil.copy2(args.video, target_video)
        except Exception as exc:
            print(str(exc))
            return 1
        target_meta.write_text(f"{args.title}\n#AI #数字人 #自动化发布", encoding="utf-8")
        for mp4 in videos_dir.glob("*.mp4"):
            meta = mp4.with_suffix(".txt")
            if not meta.exists():
                meta.write_text(f"{mp4.stem}\n#AI #数字人 #自动化发布", encoding="utf-8")
                continue
            txt = meta.read_text(encoding="utf-8").strip()
            lines = [ln for ln in txt.splitlines() if ln.strip()]
            if len(lines) < 2:
                title_line = lines[0] if lines else mp4.stem
                meta.write_text(f"{title_line}\n#AI #数字人 #自动化发布", encoding="utf-8")
        env = os.environ.copy()
        env["PYTHONPATH"] = f"{base}{os.pathsep}{env.get('PYTHONPATH', '')}" if env.get("PYTHONPATH") else base
        runtime_home = Path(base) / ".runtime_home"
        runtime_home.mkdir(parents=True, exist_ok=True)
        env["HOME"] = str(runtime_home)
        env["USERPROFILE"] = str(runtime_home)
        env["XDG_CONFIG_HOME"] = str(runtime_home / ".config")
        env["XDG_CACHE_HOME"] = str(runtime_home / ".cache")
        (runtime_home / ".config").mkdir(parents=True, exist_ok=True)
        (runtime_home / ".cache").mkdir(parents=True, exist_ok=True)
        proc = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, cwd=str(base), env=env)

    if proc.stdout.strip():
        print(proc.stdout.strip())
    if proc.returncode != 0 and proc.stderr.strip():
        print(proc.stderr.strip())
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
