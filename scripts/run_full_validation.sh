#!/usr/bin/env bash
set -u

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
if [ -f "$ROOT_DIR/local_models/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT_DIR/local_models/.env"
  set +a
fi
REPORT_DIR="$ROOT_DIR/outputs/logs"
mkdir -p "$REPORT_DIR"
STAMP="$(date +%Y%m%d_%H%M%S)"
REPORT="$REPORT_DIR/validation_${STAMP}.md"

{
  echo "# Validation Report"
  echo
  echo "- Time: $(date)"
  echo "- Root: $ROOT_DIR"
  echo
  echo "## Doctor"
  echo '```text'
  python3 "$ROOT_DIR/main.py" doctor --settings "$ROOT_DIR/config/settings.yaml" || true
  echo '```'
  echo
  echo "## Audit"
  echo '```text'
  python3 "$ROOT_DIR/main.py" audit --settings "$ROOT_DIR/config/settings.yaml" || true
  echo '```'
  echo
  echo "## Function Smoke"
  echo '```text'
  python3 - <<'PY'
import os
from pathlib import Path
from client.web import (
    _extract_first_url,
    _download_video,
    _extract_copy,
    _rewrite_copy,
    _gen_title_tags,
    _tts_from_rewrite,
    _generate_avatar_video,
    _insert_title_video,
    _insert_subtitle_video,
    _insert_bgm_video,
    _publish,
)

base = Path.cwd()
settings = str(base / 'config/settings.yaml')
input_video = str(base / 'outputs/demo_input.mp4')

print('url_extract:', _extract_first_url('copy https://v.douyin.com/-UrCWZnhAts/ end'))
dl, prev, dl_status, _ = _download_video('7.66 P@x.fO aNj:/ https://v.douyin.com/-UrCWZnhAts/ 复制此链接', settings)
print('download:', bool(dl), dl_status[:120], bool(prev))
print('extract_copy_head:', _extract_copy(input_video, settings)[:40])
rew = _rewrite_copy('这是回归测试文案。', '中文', 'DeepSeek', settings)
print('rewrite_len:', len(rew))
mt, st, ht, tags = _gen_title_tags(rew)
print('titles:', bool(mt), bool(st), bool(ht), bool(tags))
audio, st, ast = _tts_from_rewrite(rew, None, settings, '标准女声', 1.0, 0.1)
print('tts:', bool(audio), st)
os.environ['HEYGEM_CMD'] = 'ffmpeg -y -i {source_video} -i {audio_in} -map 0:v -map 1:a -c:v copy -shortest {video_out}'
vid, vst, msg = _generate_avatar_video(input_video, '知识口播', rew, None, '标准女声', settings, 20, 1.5, ast)
print('avatar:', bool(vid), msg)
v2, s2, m2 = _insert_title_video(vst, '回归测试标题', settings)
print('title:', bool(v2), m2)
v3, s3, m3 = _insert_subtitle_video(s2, '回归字幕', rew, '黑体', '36px', '400', '#DE0202', '#ECB1B1', 180, settings)
print('subtitle:', bool(v3), m3)
v4, s4, m4 = _insert_bgm_video(s3, None, '轻快节奏', 50, settings)
print('bgm:', bool(v4), m4)
pv, pc, pt, logs, pst, _ = _publish(
    s4,
    input_video,
    None,
    rew,
    settings,
    ['douyin'],
    20,
    1.5,
)
print('publish:', bool(pv), bool(pc), bool(pt), logs[:160], pst[:120])
PY
  echo '```'
} > "$REPORT"

echo "report: $REPORT"
