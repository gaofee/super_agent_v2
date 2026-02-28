from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


def local_rewrite(text: str) -> str:
    src = text.strip() or "这里是待仿写文案。"
    return (
        "开场：你是否也遇到同样问题？\n"
        f"主体：{src}\n"
        "收束：按照这三个步骤执行，你今天就能跑出第一条可发布内容。"
    )


def deepseek_rewrite(prompt: str, api_key: str, model: str) -> str:
    url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1/chat/completions")
    system_msg = (
        "你是中文短视频文案专家。请在保持原始语义的前提下进行结构重组和口语化改写，"
        "输出完整文案，不要解释。"
    )
    payload = {
        "model": model,
        "temperature": 0.7,
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt},
        ],
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return body["choices"][0]["message"]["content"].strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--model", default=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"))
    args = parser.parse_args()

    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        print(local_rewrite(args.prompt))
        return 0

    try:
        rewritten = deepseek_rewrite(args.prompt, api_key, args.model)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, KeyError, json.JSONDecodeError) as exc:
        print(local_rewrite(args.prompt))
        print(f"\n[deepseek-fallback] {exc}", file=sys.stderr)
        return 0

    print(rewritten or local_rewrite(args.prompt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
