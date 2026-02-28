from __future__ import annotations

import argparse
import os
import shutil
import subprocess


def run_ollama(prompt: str, model: str) -> str:
    if shutil.which("ollama") is None:
        return ""
    cmd = ["ollama", "run", model, prompt]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def local_rewrite(text: str) -> str:
    text = text.strip() or "这里是对标文案。"
    return (
        "开场：你是否也遇到同样问题？\n"
        f"主体：{text}\n"
        "收束：按照这三个步骤执行，你今天就能跑出第一条可发布内容。"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--model", default=os.getenv("REWRITER_MODEL", "qwen2.5:7b"))
    args = parser.parse_args()

    llm_out = run_ollama(args.prompt, args.model)
    print(llm_out or local_rewrite(args.prompt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
