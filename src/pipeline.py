"""
Unified pipeline for bili_summary.
Orchestrates: metadata → audio → transcribe → LLM summarize → assets → PDF/DOCX.
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from llm_client import LLMClient
from make_cover import make_cover
from make_infographic import make_infographic
from render_pdf import render_pdf
from render_docx import render_docx


def _get_sessdata() -> str:
    """Return B 站 SESSDATA from env var, .bili_cookie (raw), or .bili_cookies.txt (Netscape)."""
    env_val = os.environ.get('BILI_SESSDATA')
    if env_val:
        return env_val.strip()
    cookie_file = Path(__file__).parent.parent / '.bili_cookie'
    if cookie_file.exists():
        return cookie_file.read_text(encoding='utf-8-sig').strip()
    # Fallback to Netscape-format cookie file used by download_bili_audio.py
    try:
        from download_bili_audio import load_sessdata
        sd = load_sessdata()
        if sd:
            return sd
    except Exception:
        pass
    return ''


SRC = Path(__file__).parent
ProgressCb = Optional[Callable[[str, float], None]]


def _notify(cb: ProgressCb, msg: str, pct: float):
    if cb:
        cb(msg, pct)


def detect_url_platform(url: str) -> str:
    url = url.strip()
    if re.search(r'bilibili\.com/video/', url):
        return 'bilibili'
    if re.search(r'youtube\.com/watch|youtu\.be/', url):
        return 'youtube'
    if re.search(r'(twitter|x)\.com/.*/status/\d+', url):
        return 'x'
    if re.search(r'vimeo\.com/\d+', url):
        return 'vimeo'
    return 'unknown'


def resolve_cache(filename: str, *search_dirs: Path) -> Path | None:
    for d in search_dirs:
        p = d / filename
        if p.exists():
            return p
    return None


# ============ Helpers ============

def _transcript_to_text(json_path: Path) -> str:
    """Join Whisper segments into one plain-text string."""
    if not json_path.exists():
        return ''
    data = json.loads(json_path.read_text(encoding='utf-8'))
    segs = data.get('segments') or []
    lines = []
    for s in segs:
        m = int(s.get('start', 0) // 60)
        sec = int(s.get('start', 0) % 60)
        txt = (s.get('text') or '').strip()
        if txt:
            lines.append(f'[{m:02d}:{sec:02d}] {txt}')
    return '\n'.join(lines)


def _format_count(n) -> str:
    """12345 -> '1.2 万'"""
    try:
        n = int(n or 0)
    except (TypeError, ValueError):
        return ''
    if n <= 0:
        return ''
    if n < 10000:
        return f'{n:,}'
    return f'{n / 10000:.1f} 万'


def _format_duration(sec) -> str:
    try:
        sec = int(sec or 0)
    except (TypeError, ValueError):
        return ''
    if sec <= 0:
        return ''
    h, m = divmod(sec, 3600)
    m, s = divmod(m, 60)
    if h:
        return f'{h} 小时 {m:02d} 分 {s:02d} 秒'
    return f'{m} 分 {s:02d} 秒'


def _format_pubdate(value) -> str:
    """Accepts unix seconds (int) or already-formatted string."""
    if not value:
        return ''
    try:
        ts = int(value)
        if ts > 0:
            return datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
    except (TypeError, ValueError):
        pass
    return str(value)


def _enrich_meta(raw: dict) -> dict:
    """Transform parse_bili_page output into the shape the renderer + LLM expect."""
    out = dict(raw)  # shallow copy
    out['title'] = raw.get('title') or ''
    out['uploader'] = raw.get('owner') or raw.get('uploader') or ''
    out['bvid'] = raw.get('bvid') or ''
    out['tname'] = raw.get('tname') or ''
    out['tags'] = list(raw.get('tags') or [])[:8]
    out['pubdate'] = _format_pubdate(raw.get('pubdate'))
    out['duration_label'] = _format_duration(raw.get('duration_sec'))

    view_int = int(raw.get('view') or 0)
    like_int = int(raw.get('like') or 0)
    fav_int = int(raw.get('favorite') or 0)
    danmaku_int = int(raw.get('danmaku') or 0)
    out['view_int'] = view_int
    out['like_int'] = like_int
    out['favorite_int'] = fav_int
    out['danmaku_int'] = danmaku_int
    out['view'] = _format_count(view_int)
    out['like'] = _format_count(like_int)
    out['favorite'] = _format_count(fav_int)
    out['danmaku'] = _format_count(danmaku_int)
    return out


# ============ Main pipeline ============

def run_pipeline(
    url: str,
    out_dir: Path,
    on_progress: ProgressCb = None,
    skip_transcribe: bool = False,
    use_cache: bool = True,
) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pictures_dir = out_dir / 'pictures'
    pictures_dir.mkdir(exist_ok=True)
    audio_dir = out_dir / 'audio'
    audio_dir.mkdir(exist_ok=True)
    video_dir = out_dir / 'video'
    video_dir.mkdir(exist_ok=True)
    transcripts_dir = out_dir / 'transcripts'
    transcripts_dir.mkdir(exist_ok=True)

    project_dir = Path(__file__).parent.parent  # D:\Study\bili_summary
    demo_transcripts = project_dir / 'transcripts'

    platform = detect_url_platform(url)
    if platform == 'unknown':
        raise ValueError(f'URL 格式不支持: {url[:60]}')

    _notify(on_progress, f'检测到平台: {platform}', 0.05)

    bvid_match = re.search(r'(BV[\w]+|av\d+)', url)
    bvid = bvid_match.group(1) if bvid_match else 'video'

    # ============ Step 1: Metadata ============
    _notify(on_progress, '正在抓取视频元数据...', 0.10)
    cached = resolve_cache(f'{bvid}_meta.json', demo_transcripts, transcripts_dir)
    if use_cache and cached:
        raw_meta = json.loads(cached.read_text(encoding='utf-8'))
        _notify(on_progress, f'OK: {raw_meta["title"]}', 0.12)
    else:
        if platform == 'bilibili':
            _notify(on_progress, '通过 Bilibili API 获取元数据...', 0.11)
            sessdata = _get_sessdata()
            if not sessdata:
                raise RuntimeError(
                    'B站获取元数据需要登录态。请配置 .bili_cookies.txt 或 '
                    '设置环境变量 BILI_SESSDATA (F12 → Application → Cookies → '
                    'https://www.bilibili.com 复制 SESSDATA 的 value)'
                )
            from download_bili_audio import fetch_view_meta
            try:
                api_data = fetch_view_meta(bvid, sessdata)
            except Exception as e:
                raise RuntimeError(f'Bilibili API 获取元数据失败: {e}')
            raw_meta = {
                'bvid': bvid,
                'title': api_data.get('title', ''),
                'desc': api_data.get('desc', ''),
                'owner': (
                    api_data['owner']['name']
                    if isinstance(api_data.get('owner'), dict)
                    else ''
                ),
                'tname': api_data.get('tname', ''),
                'tags': [
                    t['tag_name']
                    for t in (api_data.get('tags') or [])
                    if isinstance(t, dict) and t.get('tag_name')
                ],
                'pubdate': api_data.get('pubdate', 0),
                'duration_sec': api_data.get('duration', 0),
                **{k: api_data.get('stat', {}).get(k, 0)
                   for k in ('view', 'like', 'danmaku', 'reply', 'favorite', 'coin', 'share')},
            }
        else:
            # Non-bilibili: try legacy parser (best-effort)
            _notify(on_progress, '尝试解析页面...', 0.11)
            subprocess.run(
                [sys.executable, str(SRC / 'parse_bili_page.py')],
                capture_output=True, timeout=30,
            )
            fallback = demo_transcripts / 'bili_meta.json'
            if fallback.exists():
                raw_meta = json.loads(fallback.read_text(encoding='utf-8'))
            else:
                raise RuntimeError('无法解析视频元数据')
        # Cache for future runs
        (transcripts_dir / f'{bvid}_meta.json').write_text(
            json.dumps(raw_meta, ensure_ascii=False, indent=2), encoding='utf-8')
        _notify(on_progress, f'OK: {raw_meta.get("title", "")}', 0.12)

    raw_meta.setdefault('bvid', bvid)
    meta = _enrich_meta(raw_meta)

    # ============ Step 2: Audio ============
    audio_path = None
    for ext in ('m4a', 'mp3'):
        audio_path = resolve_cache(
            f'{bvid}.{ext}', audio_dir, transcripts_dir, demo_transcripts,
        )
        if audio_path:
            break
    if use_cache and audio_path:
        _notify(on_progress, f'OK: 复用已缓存的音频 {audio_path.name}', 0.25)
    else:
        _notify(on_progress, '正在下载音频...', 0.25)
        if platform == 'bilibili':
            if not _get_sessdata():
                raise RuntimeError(
                    'B 站下载需要登录态。请配置 .bili_cookies.txt 或设置 '
                    '环境变量 BILI_SESSDATA (F12 → Application → Cookies → '
                    'https://www.bilibili.com 复制 SESSDATA 的 value)'
                )
            cmd = [sys.executable, str(SRC / 'download_bili_audio.py'), bvid]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
            if r.returncode != 0:
                if r.returncode == 2:
                    raise RuntimeError(
                        'B 站下载需要登录态 (SESSDATA)。请按上方指引配置 '
                        '.bili_cookies.txt 或环境变量 BILI_SESSDATA'
                    )
                raise RuntimeError(
                    f'B 站音频下载失败: {(r.stderr or r.stdout)[-400:]}'
                )
            src_mp3 = demo_transcripts / f'{bvid}.mp3'
            dst_mp3 = audio_dir / f'{bvid}.mp3'
            if src_mp3.exists() and not dst_mp3.exists():
                dst_mp3.write_bytes(src_mp3.read_bytes())
            # Also copy video if present
            src_mp4 = demo_transcripts / f'{bvid}.mp4'
            dst_mp4 = video_dir / f'{bvid}.mp4'
            if src_mp4.exists() and not dst_mp4.exists():
                dst_mp4.write_bytes(src_mp4.read_bytes())
        else:
            ua = (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/131.0.0.0 Safari/537.36'
            )
            out_tmpl = str((audio_dir / bvid).with_suffix('.%(ext)s'))
            cmd = [
                sys.executable, '-m', 'yt_dlp',
                '--user-agent', ua,
                '--add-header', f'Referer:{url}',
                '--add-header', 'Accept-Language:zh-CN,zh;q=0.9',
                '-f', 'worstaudio/worst',
                '-x', '--audio-format', 'mp3',
                '-o', out_tmpl,
                url,
            ]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if r.returncode != 0:
                raise RuntimeError(f'音频下载失败: {r.stderr[-300:]}')
        for ext in ['mp3', 'm4a']:
            cand = (audio_dir / bvid).with_suffix(f'.{ext}')
            if cand.exists():
                audio_path = cand
                break
        if audio_path is None:
            raise RuntimeError('音频下载完成但未找到输出文件')
        _notify(on_progress, f'OK: 音频 {audio_path.name}', 0.30)

    # ============ Step 3: Transcribe ============
    transcript_json_name = f'{bvid}_transcript.json'
    transcript_path = resolve_cache(transcript_json_name, demo_transcripts, transcripts_dir)
    n_segments = 0
    if skip_transcribe and transcript_path:
        _notify(on_progress, 'OK: 跳过转录', 0.50)
    elif use_cache and transcript_path:
        _notify(on_progress, 'OK: 复用已缓存的转录', 0.50)
        try:
            n_segments = len(json.loads(transcript_path.read_text(encoding='utf-8')).get('segments', []))
        except Exception:
            pass
    else:
        _notify(on_progress, 'Whisper 转录中...', 0.35)
        import whisper
        import imageio_ffmpeg
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        os.environ['PATH'] = str(Path(ffmpeg).parent) + os.pathsep + os.environ.get('PATH', '')

        model = whisper.load_model('small', device='cuda')
        result = model.transcribe(
            str(audio_path), language='zh', task='transcribe',
            verbose=False, fp16=True,
        )
        n_segments = len(result.get('segments', []))
        transcript_json_path = transcripts_dir / transcript_json_name
        transcript_json_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        txt = transcripts_dir / f'{bvid}_transcript.txt'
        with txt.open('w', encoding='utf-8') as f:
            for s in result['segments']:
                m = int(s['start'] / 60)
                sec = int(s['start'] % 60)
                f.write(f'[{m:02d}:{sec:02d}] {s["text"].strip()}\n')
        _notify(on_progress, f'OK: {n_segments} 段', 0.55)

    # ============ Step 3.5: LLM Summarize ============
    summary_path = transcripts_dir / f'{bvid}_summary.json'
    if use_cache and summary_path.exists():
        data = json.loads(summary_path.read_text(encoding='utf-8'))
        _notify(on_progress, 'OK: 复用 LLM 总结缓存', 0.68)
    else:
        _notify(on_progress, '调用 LLM...', 0.56)
        transcript_text = _transcript_to_text(
            transcripts_dir / transcript_json_name
            if (transcripts_dir / transcript_json_name).exists()
            else transcript_path
        )
        if not transcript_text:
            raise RuntimeError('转录文本为空，无法调用 LLM')

        llm_input_meta = dict(meta)
        llm_input_meta['n_segments'] = n_segments
        try:
            data = LLMClient().summarize(
                transcript_text, llm_input_meta,
                on_progress=lambda m, p: _notify(on_progress, m, p),
            )
        except RuntimeError as e:
            raise RuntimeError(f'LLM 步骤失败: {e}') from e

        # Always overlay the parsed-meta fields (LLM may not know bvid / uploader).
        data['meta'] = meta

        summary_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        _notify(on_progress, f'OK: LLM 总结 {summary_path.stat().st_size // 1024} KB', 0.70)

    # ============ Step 4: Visual assets (in-process) ============
    _notify(on_progress, '生成封面 PNG...', 0.72)
    cover_path = pictures_dir / 'cover.png'
    make_cover(data, cover_path)
    _notify(on_progress, '生成信息图 PNG...', 0.78)
    infographic_path = pictures_dir / 'infographic.png'
    make_infographic(data, infographic_path)
    _notify(on_progress, 'OK: 视觉资产就绪', 0.82)

    # Inject asset paths so renderers can find them
    data['_assets'] = {
        'cover': str(cover_path),
        'infographic': str(infographic_path),
    }

    # ============ Step 5: Document export (in-process) ============
    _notify(on_progress, '组装 PDF...', 0.85)
    render_pdf(data, out_dir / 'summary.pdf')
    _notify(on_progress, '组装 DOCX...', 0.94)
    render_docx(data, out_dir / 'summary.docx')

    _notify(on_progress, 'OK: 完成!', 1.0)
    return {
        'meta': meta,
        'summary_json': summary_path,
        'pdf': out_dir / 'summary.pdf',
        'docx': out_dir / 'summary.docx',
        'cover': cover_path,
        'infographic': infographic_path,
    }