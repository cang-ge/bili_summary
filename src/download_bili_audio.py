"""
Direct B 站 audio downloader using the legacy (non-wbi) playurl endpoint.

Why this exists:
- yt-dlp's BiliBili extractor calls /x/player/wbi/playurl, which gets HTTP 412
  in many environments due to wbi signature drift.
- The legacy endpoint /x/player/playurl still works with just SESSDATA,
  returning 720P MP4 video (we then extract audio with ffmpeg).

Inputs:
- Reads SESSDATA from .bili_cookies.txt (Netscape format) — same file yt-dlp uses.
- Or from BILI_SESSDATA env var.

Outputs:
- Writes the raw video to <bvid>.mp4, then runs ffmpeg -i to extract audio
  as mp3 into <bvid>.mp3.
"""
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlencode

PROJECT_ROOT = Path(__file__).parent.parent


def load_sessdata() -> str:
    env = os.environ.get('BILI_SESSDATA', '').strip()
    if env:
        return env
    cookies_file = PROJECT_ROOT / '.bili_cookies.txt'
    if cookies_file.exists():
        for line in cookies_file.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split('\t')
            if len(parts) >= 7 and parts[5] == 'SESSDATA':
                return parts[6].strip()
    return ''


def fetch_view_meta(bvid: str, sessdata: str) -> dict:
    """Hit /x/web-interface/view to get cid + aid."""
    url = f'https://api.bilibili.com/x/web-interface/view?bvid={bvid}'
    req = urllib.request.Request(url, headers={
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/131.0.0.0 Safari/537.36'
        ),
        'Referer': f'https://www.bilibili.com/video/{bvid}',
        'Cookie': f'SESSDATA={sessdata}',
    })
    with urllib.request.urlopen(req, timeout=15) as r:
        body = json.loads(r.read().decode())
    if body.get('code') != 0:
        raise RuntimeError(f'/view failed: code={body.get("code")} msg={body.get("message")}')
    return body['data']


def fetch_playurl(bvid: str, cid: int, sessdata: str) -> str:
    """Hit legacy /x/player/playurl (no wbi) and return the first video segment URL."""
    params = {
        'bvid': bvid,
        'cid': cid,
        'qn': 80,         # 1080P if available; falls back per B 站 logic
        'fnval': 1,       # MP4-only mode (skip DASH)
        'fourk': 0,
        'platform': 'html5',
    }
    url = f'https://api.bilibili.com/x/player/playurl?{urlencode(params)}'
    req = urllib.request.Request(url, headers={
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/131.0.0.0 Safari/537.36'
        ),
        'Referer': f'https://www.bilibili.com/video/{bvid}',
        'Cookie': f'SESSDATA={sessdata}',
    })
    with urllib.request.urlopen(req, timeout=15) as r:
        body = json.loads(r.read().decode())
    if body.get('code') != 0:
        raise RuntimeError(f'/playurl failed: code={body.get("code")} msg={body.get("message")}')
    durls = body['data'].get('durl') or []
    if not durls:
        raise RuntimeError('No durl segments returned')
    return durls[0]['url']


def download_video(video_url: str, out_path: Path, bvid: str, sessdata: str):
    req = urllib.request.Request(video_url, headers={
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/131.0.0.0 Safari/537.36'
        ),
        'Referer': f'https://www.bilibili.com/video/{bvid}',
        'Cookie': f'SESSDATA={sessdata}',
    })
    print(f'Downloading to {out_path} ...')
    with urllib.request.urlopen(req, timeout=600) as r, open(out_path, 'wb') as f:
        total = int(r.headers.get('Content-Length', '0'))
        read = 0
        chunk = 1024 * 1024
        while True:
            buf = r.read(chunk)
            if not buf:
                break
            f.write(buf)
            read += len(buf)
            if total:
                pct = read * 100 // total
                print(f'\r  {read // 1024 // 1024} MB / {total // 1024 // 1024} MB ({pct}%)', end='', flush=True)
    print()


def extract_audio(video_path: Path, audio_path: Path, ffmpeg: str):
    cmd = [ffmpeg, '-y', '-i', str(video_path), '-vn', '-acodec', 'libmp3lame',
           '-ab', '64k', str(audio_path)]
    print(' '.join(cmd))
    subprocess.run(cmd, check=True)


def main(bvid: str):
    sessdata = load_sessdata()
    if not sessdata:
        raise RuntimeError('No SESSDATA — set BILI_SESSDATA or write .bili_cookies.txt')

    meta = fetch_view_meta(bvid, sessdata)
    cid = meta['cid']
    print(f'Video: {meta["title"]}  (cid={cid})')

    video_url = fetch_playurl(bvid, cid, sessdata)
    print(f'Play URL: {video_url[:120]}...')

    transcripts_dir = PROJECT_ROOT / 'transcripts'
    transcripts_dir.mkdir(exist_ok=True)
    video_path = transcripts_dir / f'{bvid}.mp4'
    audio_path = transcripts_dir / f'{bvid}.mp3'

    download_video(video_url, video_path, bvid, sessdata)
    print(f'Downloaded: {video_path} ({video_path.stat().st_size // 1024} KB)')

    import imageio_ffmpeg
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    extract_audio(video_path, audio_path, ffmpeg)
    print(f'Audio extracted: {audio_path} ({audio_path.stat().st_size // 1024} KB)')


if __name__ == '__main__':
    bvid = sys.argv[1] if len(sys.argv) > 1 else 'BV1cyDKBLEXY'
    sessdata = load_sessdata()
    if not sessdata:
        sys.stderr.write(
            '\n'
            '═══════════════════════════════════════════════════════════\n'
            '  B 站音频下载需要登录态 (SESSDATA cookie)\n'
            '═══════════════════════════════════════════════════════════\n'
            '\n'
            '  获取方式：\n'
            '    1. 浏览器登录 https://www.bilibili.com\n'
            '    2. F12 → Application → Cookies → https://www.bilibili.com\n'
            '    3. 复制 SESSDATA 的 value\n'
            '\n'
            '  写入项目根目录的 .bili_cookies.txt (Netscape 格式)：\n'
            '\n'
            '    .bilibili.com\tTRUE\t/\tFALSE\t0\tSESSDATA\t<你的value>\n'
            '\n'
            '  或设置环境变量：\n'
            '    $env:BILI_SESSDATA = "<你的value>"  (PowerShell)\n'
            '\n'
            '═══════════════════════════════════════════════════════════\n'
        )
        sys.exit(2)
    main(bvid)