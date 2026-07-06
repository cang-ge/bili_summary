"""
Thin CLI wrapper around run_pipeline.

Designed for the Streamlit UI to invoke via subprocess (so it can be cancelled).
Progress is emitted as one JSON object per line on stdout:

    {"pct": 0.25, "msg": "正在下载音频..."}
    {"pct": 0.30, "msg": "OK: 音频 ..."}

The UI reads these lines and updates its progress widget in real time.

Cancel: when the parent process terminates us (SIGTERM on Unix, TerminateProcess
on Windows), Python's default behaviour is to raise SystemExit, which unwinds
the call stack. In-progress subprocesses (yt-dlp, ffmpeg, whisper) won't be
auto-killed — but their output is no longer consumed, and the parent's
terminate() returns control immediately.

Usage:
    python src/run_pipeline_cli.py <URL> [--out OUT_DIR] [--no-cache] [--skip-transcribe]
"""
import argparse
import json
import sys
from pathlib import Path

# Make sibling modules importable when launched as a script
sys.path.insert(0, str(Path(__file__).parent))

from pipeline import run_pipeline  # noqa: E402


# ---- Windows: force UTF-8 stdout so emoji / 中文 progress messages don't crash
# the subprocess with UnicodeEncodeError('gbk'). Stdlib reconfigure is a no-op
# on terminals that already default to UTF-8.
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass


def emit(pct: float, msg: str):
    """Write a single JSON line to stdout, flushed immediately."""
    sys.stdout.write(json.dumps({'pct': pct, 'msg': msg}, ensure_ascii=False) + '\n')
    sys.stdout.flush()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('url')
    ap.add_argument('--out', default='output')
    ap.add_argument('--no-cache', action='store_true')
    ap.add_argument('--skip-transcribe', action='store_true')
    args = ap.parse_args()

    def on_progress(msg, pct):
        emit(pct, msg)

    try:
        run_pipeline(
            url=args.url,
            out_dir=args.out,
            on_progress=on_progress,
            skip_transcribe=args.skip_transcribe,
            use_cache=not args.no_cache,
        )
        emit(1.0, '__DONE__')
    except Exception as e:
        emit(-1.0, f'__ERROR__:{e}')
        sys.exit(1)


if __name__ == '__main__':
    main()