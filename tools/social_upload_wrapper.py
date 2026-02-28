from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path


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
    if not cli.exists():
        print(f"cli not found: {cli}")
        return 1

    cmd = [
        "python3",
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
    if proc.stdout.strip():
        print(proc.stdout.strip())
    if proc.returncode != 0 and proc.stderr.strip():
        print(proc.stderr.strip())
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
