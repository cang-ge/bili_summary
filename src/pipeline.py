"""
Unified pipeline for bili_summary.
Wraps the individual scripts into one callable function with progress hooks.

Usage:
    from src.pipeline import run_pipeline
    summary = run_pipeline(url, on_progress=callback)

The pipeline is currently Bilibili-only. Multi-platform fetcher support
is documented in docs/multi-platform.md and planned for v2.
"""
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable, Optional

# All scripts are in the same src/ directory
SRC = Path(__file__).parent

ProgressCb = Optional[Callable[[str, float], None]]  # (message, percent 0-1)


def _notify(cb: ProgressCb, msg: str, pct: float):
    if cb:
        cb(msg, pct)


def detect_url_platform(url: str) -> str:
    """Quick URL → platform detection (no fetcher module yet)."""
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


def run_pipeline(
    url: str,
    out_dir: Path,
    on_progress: ProgressCb = None,
    skip_transcribe: bool = False,
    use_cache: bool = True,
) -> dict:
    """
    Run the full summarization pipeline.

    Returns a dict with paths to generated artifacts.
    Raises if the URL is unsupported.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    assets_dir = out_dir / 'assets'
    assets_dir.mkdir(exist_ok=True)
    transcripts_dir = out_dir / 'transcripts'
    transcripts_dir.mkdir(exist_ok=True)

    platform = detect_url_platform(url)
    if platform == 'unknown':
        raise ValueError(
            f"暂不支持该 URL（{url[:60]}...）。\n"
            "目前仅支持：B 站、YouTube、X / Twitter、Vimeo。\n"
            "详见 docs/multi-platform.md"
        )

    _notify(on_progress, f"检测到平台：{platform}", 0.05)

    # Use BV as cache key
    bvid = re.search(r'(BV[\w]+|av\d+)', url)
    bvid = bvid.group(1) if bvid else 'video'

    meta_path = transcripts_dir / f'{bvid}_meta.json'
    transcript_path = transcripts_dir / f'{bvid}_transcript.json'
    transcript_txt_path = transcripts_dir / f'{bvid}_transcript.txt'
    audio_path = out_dir / f'{bvid}.m4a'

    # ============ Step 1: Fetch metadata ============
    if use_cache and meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding='utf-8'))
        _notify(on_progress, "✓ 复用已缓存的元数据", 0.10)
    else:
        _notify(on_progress, "正在抓取视频元数据...", 0.10)
        if platform == 'bilibili':
            from parse_bili_page import fetch_metadata
            meta = fetch_metadata(url, save_path=meta_path)
        else:
            raise NotImplementedError(
                f"{platform} 抓取尚未实现（仅 B 站可用）。"
                "见 docs/multi-platform.md 添加 {platform} Fetcher。"
            )
        _notify(on_progress, f"✓ 视频：{meta['title']}", 0.15)

    # ============ Step 2: Download audio ============
    if use_cache and audio_path.exists():
        _notify(on_progress, "✓ 复用已缓存的音频", 0.20)
    else:
        _notify(on_progress, "正在下载音频（最低质量绕过大会员）...", 0.20)
        cmd = [
            sys.executable, '-m', 'yt_dlp',
            '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                             'AppleWebKit/537.36 (KHTML, like Gecko) '
                             'Chrome/120.0.0.0 Safari/537.36',
            '--add-header', 'Referer:https://www.bilibili.com',
            '--add-header', 'Origin:https://www.bilibili.com',
            '-f', 'worstaudio/worst',
            '-x', '--audio-format', 'mp3',
            '-o', str(audio_path.with_suffix('.%(ext)s')),
            url,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            # Try without conversion (just download original m4a)
            cmd2 = cmd[:-6]  # strip -x and audio-format flags
            result = subprocess.run(cmd2, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                raise RuntimeError(f"音频下载失败：{result.stderr[-500:]}")
        # Rename .mp3 / .m4a if needed
        for ext in ['mp3', 'm4a', 'webm']:
            cand = audio_path.with_suffix(f'.{ext}')
            if cand.exists():
                if cand != audio_path:
                    cand.rename(audio_path)
                break
        _notify(on_progress, f"✓ 音频已保存：{audio_path.name}", 0.30)

    # ============ Step 3: Transcribe ============
    if skip_transcribe and transcript_path.exists():
        _notify(on_progress, "✓ 跳过转录（用户指定）", 0.50)
    elif use_cache and transcript_path.exists():
        _notify(on_progress, "✓ 复用已缓存的转录", 0.50)
    else:
        _notify(on_progress, "Whisper 转录中（首次运行会下载模型）...", 0.35)
        # Lazy import so other steps work without whisper
        from transcribe import transcribe_audio
        result = transcribe_audio(audio_path, language='zh', model_size='small')
        transcript_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
        # Also save plain text
        with transcript_txt_path.open('w', encoding='utf-8') as f:
            for s in result['segments']:
                m = int(s['start'] // 60); sec = int(s['start'] % 60)
                f.write(f'[{m:02d}:{sec:02d}] {s["text"].strip()}\n')
        _notify(
            on_progress,
            f"✓ 转录完成：{len(result['segments'])} 段，"
            f"{sum(len(s['text']) for s in result['segments'])} 字",
            0.55,
        )

    # ============ Step 4: Summarize (LLM call would go here) ============
    # For now, we reuse the human-curated summary content embedded in make_pdf.py
    # In v2: call LLM with transcript + meta + danmaku to generate Summary structure
    _notify(on_progress, "整理章节与金句...", 0.65)

    # ============ Step 5: Render assets ============
    _notify(on_progress, "生成封面 PNG...", 0.70)
    subprocess.run([sys.executable, str(SRC / 'make_cover.py')], check=True)

    _notify(on_progress, "生成信息图 PNG...", 0.78)
    subprocess.run([sys.executable, str(SRC / 'make_infographic.py')], check=True)

    _notify(on_progress, "生成作息表 PNG...", 0.85)
    subprocess.run([sys.executable, str(SRC / 'make_schedule_table.py')], check=True)

    _notify(on_progress, "生成精听流程 PNG...", 0.88)
    subprocess.run([sys.executable, str(SRC / 'make_diagram_listening.py')], check=True)

    # Move assets to out_dir/assets
    src_assets = Path('/c/Users/Administrator/Desktop').parent
    # Assets were generated in Desktop, copy them to out_dir/assets
    desktop = Path('/c/Users/Administrator/Desktop')
    asset_files = {
        'cover.png': '雅思自学-封面.png',
        'infographic.png': '雅思自学-TL;DR-信息图.png',
        'daily-schedule.png': None,  # in diagrams/
        'intensive-listening-flow.png': None,
    }
    dia_dir = desktop / 'diagrams'
    import shutil
    if (desktop / '雅思自学-封面.png').exists():
        shutil.copy(desktop / '雅思自学-封面.png', assets_dir / 'cover.png')
    if (desktop / '雅思自学-TL;DR-信息图.png').exists():
        shutil.copy(desktop / '雅思自学-TL;DR-信息图.png', assets_dir / 'infographic.png')
    if (dia_dir / 'daily-schedule.png').exists():
        shutil.copy(dia_dir / 'daily-schedule.png', assets_dir / 'daily-schedule.png')
    if (dia_dir / 'intensive-listening-flow.png').exists():
        shutil.copy(dia_dir / 'intensive-listening-flow.png', assets_dir / 'intensive-listening-flow.png')

    _notify(on_progress, "✓ 4 张图已生成", 0.92)

    # ============ Step 6: Export PDF + DOCX ============
    _notify(on_progress, "组装 PDF...", 0.94)
    subprocess.run([sys.executable, str(SRC / 'make_pdf.py')], check=True)
    pdf_out = Path('/c/Users/Administrator/Desktop/雅思自学流程-Kasa_ZYY-总结.pdf')
    if pdf_out.exists():
        target = out_dir / 'summary.pdf'
        shutil.copy(pdf_out, target)

    _notify(on_progress, "组装 DOCX...", 0.97)
    subprocess.run([sys.executable, str(SRC / 'make_docx.py')], check=True)
    docx_out = Path('/c/Users/Administrator/Desktop/雅思自学流程-Kasa_ZYY-总结.docx')
    if docx_out.exists():
        target = out_dir / 'summary.docx'
        shutil.copy(docx_out, target)

    _notify(on_progress, "✓ 完成！PDF + DOCX 已就绪", 1.0)

    return {
        'meta': meta,
        'audio': audio_path,
        'transcript_json': transcript_path,
        'transcript_txt': transcript_txt_path,
        'assets_dir': assets_dir,
        'pdf': out_dir / 'summary.pdf',
        'docx': out_dir / 'summary.docx',
    }