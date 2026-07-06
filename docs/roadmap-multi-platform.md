# 多平台扩展指南

把 `fetcher.py` 从「只支持 B 站」重构到「任意平台」。

---

## 现状

当前 `src/parse_bili_page.py` 直接处理 B 站 HTML / 弹幕协议。

要新增平台，最朴素的方式是 fork 一个 `parse_xxx_page.py`。
但这样会导致：
- 代码复制粘贴
- 主流程散落在多个文件
- CLI 无法智能路由

---

## 推荐：三层抽象 + 注册中心

### Step 1 — 统一数据模型

所有平台最终输出同一个 `VideoMeta`：

```python
# src/ielts_tool/models.py
from dataclasses import dataclass

@dataclass
class VideoMeta:
    url: str
    platform: str          # 'bilibili' | 'youtube' | 'x' | 'vimeo' | ...
    title: str
    uploader: str
    duration_sec: float
    description: str
    tags: list[str]
    view_count: int
    like_count: int
    upload_date: str       # ISO 8601
    bvid_or_id: str        # 平台原始 ID

@dataclass
class TranscriptSegment:
    start: float          # seconds
    end: float
    text: str

@dataclass
class DanmakuMessage:
    time: float           # seconds since video start
    text: str
```

### Step 2 — Fetcher 抽象接口

```python
# src/ielts_tool/fetchers/base.py
from abc import ABC, abstractmethod
from pathlib import Path

class VideoFetcher(ABC):
    name: str = "base"
    url_patterns: list[str] = []

    @abstractmethod
    def fetch_metadata(self, url: str) -> VideoMeta: ...
    @abstractmethod
    def download_audio(self, url: str, out_path: Path) -> Path: ...
    @abstractmethod
    def fetch_danmaku(self, url: str) -> list[DanmakuMessage]: ...
    @abstractmethod
    def fetch_subtitles(self, url: str) -> list[TranscriptSegment] | None:
        """返回 None 表示无字幕，走 Whisper；返回非空则跳过 Whisper。"""
```

### Step 3 — 各平台实现

#### B 站（重构自现有脚本）

```python
# src/ielts_tool/fetchers/bilibili.py
import re, gzip, json
from .base import VideoFetcher, VideoMeta, DanmakuMessage
from .registry import register

class BilibiliFetcher(VideoFetcher):
    name = "bilibili"
    url_patterns = [r"bilibili\.com/video/(BV[\w]+|av\d+)"]

    def fetch_metadata(self, url):
        # 复用现有 parse_bili_page.py 逻辑
        ...

    def download_audio(self, url, out_path):
        # 现有 yt-dlp + Referer/Origin headers
        ...

    def fetch_danmaku(self, url):
        # 现有 danmaku.xml + zlib raw deflate 解压
        ...

    def fetch_subtitles(self, url):
        return None  # B 站官方字幕需要登录

register(BilibiliFetcher())
```

#### YouTube（最容易加的平台）

```python
# src/ielts_tool/fetchers/youtube.py
from pathlib import Path
from .base import VideoFetcher, VideoMeta, TranscriptSegment
from .registry import register
import yt_dlp

class YouTubeFetcher(VideoFetcher):
    name = "youtube"
    url_patterns = [
        r"youtube\.com/watch\?v=[\w-]+",
        r"youtu\.be/[\w-]+",
    ]

    def fetch_metadata(self, url):
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
        return VideoMeta(
            platform=self.name,
            bvid_or_id=info['id'],
            title=info['title'],
            uploader=info['uploader'],
            duration_sec=info['duration'],
            description=info.get('description', ''),
            tags=info.get('tags', []),
            view_count=info.get('view_count', 0),
            like_count=info.get('like_count', 0),
            upload_date=str(info.get('upload_date', '')),
            url=url,
        )

    def download_audio(self, url, out_path):
        ydl_opts = {
            'format': 'worstaudio/worst',
            'outtmpl': str(out_path.with_suffix('')) + '.%(ext)s',
            'postprocessors': [{'key': 'FFmpegExtractAudio',
                                 'preferredcodec': 'mp3'}],
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return out_path.with_suffix('.mp3')

    def fetch_danmaku(self, url):
        return []  # YouTube 无弹幕

    def fetch_subtitles(self, url):
        """YouTube 通常有官方字幕，**优先使用 → 跳过 Whisper**"""
        try:
            with yt_dlp.YoutubeDL({
                'writesubtitles': True,
                'subtitleslangs': ['zh-Hans', 'zh-CN', 'en'],
                'skip_download': True,
                'quiet': True,
            }) as ydl:
                info = ydl.extract_info(url, download=False)
                subs = info.get('subtitles', {})
                # ... 解析 .vtt 返回 TranscriptSegment list
        except Exception:
            return None

register(YouTubeFetcher())
```

#### X (Twitter)

```python
# src/ielts_tool/fetchers/x_twitter.py
class XTwitterFetcher(VideoFetcher):
    name = "x"
    url_patterns = [r"(twitter|x)\.com/.+/status/\d+"]

    def download_audio(self, url, out_path):
        # X 视频一般是 mp4，先下视频再 ffmpeg 抽音频
        import yt_dlp
        with yt_dlp.YoutubeDL({
            'format': 'worst',
            'outtmpl': str(out_path.with_suffix('')) + '.mp4',
        }) as ydl:
            ydl.download([url])
        # ffmpeg 抽音
        import subprocess
        subprocess.run(['ffmpeg', '-y', '-i', str(out_path.with_suffix('.mp4')),
                         '-vn', '-acodec', 'libmp3lame', str(out_path)])
        return out_path

register(XTwitterFetcher())
```

### Step 4 — 注册中心 + 自动发现

```python
# src/ielts_tool/fetchers/registry.py
import re
from .base import VideoFetcher, UnsupportedURLError

class FetcherRegistry:
    _fetchers: list[VideoFetcher] = []

    @classmethod
    def register(cls, fetcher: VideoFetcher):
        cls._fetchers.append(fetcher)

    @classmethod
    def detect(cls, url: str) -> VideoFetcher:
        for f in cls._fetchers:
            for pat in f.url_patterns:
                if re.search(pat, url):
                    return f
        raise UnsupportedURLError(
            f"No fetcher for {url}. Supported: "
            f"{[f.name for f in cls._fetchers]}"
        )

    @classmethod
    def list_platforms(cls) -> list[str]:
        return [f.name for f in cls._fetchers]
```

每个 fetcher 文件末尾调用 `register(...)`，import 时自动注册。

### Step 5 — 主流程只关心抽象

```python
# src/ielts_tool/pipeline.py
from pathlib import Path
from .fetchers.registry import FetcherRegistry
from .transcriber import transcribe
from .summarizer import summarize
from .assets import render_all_assets
from .exporter import export_pdf, export_docx

def run_pipeline(url: str, output_dir: Path, platform: str = None):
    fetcher = (FetcherRegistry.get(platform) if platform
               else FetcherRegistry.detect(url))

    meta = fetcher.fetch_metadata(url)
    audio_path = fetcher.download_audio(url, output_dir / "audio.mp3")
    danmaku = fetcher.fetch_danmaku(url)
    official_subs = fetcher.fetch_subtitles(url)

    # 字幕优先 → Whisper 兜底
    transcript = (official_subs if official_subs
                  else transcribe(audio_path, language=detect_lang(meta)))

    summary = summarize(meta, transcript, danmaku)
    assets = render_all_assets(meta, summary, output_dir / "assets")
    export_pdf(summary, assets, output_dir / "summary.pdf")
    export_docx(summary, assets, output_dir / "summary.docx")
```

### Step 6 — CLI

```bash
# 自动检测
ielts-tool run "https://www.bilibili.com/video/BV1xxx"
ielts-tool run "https://www.youtube.com/watch?v=xxx"

# 强制指定
ielts-tool run URL --platform youtube

# 列出所有支持的平台
ielts-tool platforms
```

```python
# src/ielts_tool/cli.py
import click
from pathlib import Path
from .fetchers.registry import FetcherRegistry
from .pipeline import run_pipeline

@click.group()
def cli():
    """bili_summary — 视频一键总结工具"""

@cli.command()
@click.argument("url")
@click.option("-o", "--output", default="./out", type=Path)
@click.option("-p", "--platform", default=None)
def run(url, output, platform):
    """根据 URL 自动选择平台并运行完整流水线"""
    output.mkdir(parents=True, exist_ok=True)
    run_pipeline(url, output, platform)
    click.echo(f"✓ 完成 → {output}/")

@cli.command()
def platforms():
    """列出所有已注册的平台"""
    for name in FetcherRegistry.list_platforms():
        click.echo(f"· {name}")

if __name__ == "__main__":
    cli()
```

---

## 🧩 第三方插件（高阶）

如果你希望别人**不改核心代码**就能贡献新平台 fetcher：

```toml
# pyproject.toml — 核心包
[project.entry-points."ielts_tool.fetchers"]
youtube = "ielts_tool.fetchers.youtube:YouTubeFetcher"
```

```toml
# 社区包 ielts-tool-xiaohongshu 的 pyproject.toml
[project.entry-points."ielts_tool.fetchers"]
xiaohongshu = "ielts_tool_xhs:XiaohongshuFetcher"
```

```python
# 核心自动加载
import importlib.metadata as md
for ep in md.entry_points(group="ielts_tool.fetchers"):
    FetcherRegistry.register(ep.load()())
```

用户安装：
```bash
pip install ielts-tool           # YouTube / X
pip install ielts-tool-bilibili  # 社区贡献
```

---

## 📋 新平台接入清单

| 平台 | URL 正则 | 工作量 | 备注 |
|------|----------|--------|------|
| YouTube | `youtube\.com/watch\|youtu\.be/` | 🟢 低 | yt-dlp 原生 |
| X | `(twitter\|x)\.com/.*/status/\d+` | 🟢 低 | 需抽音频 |
| Vimeo | `vimeo\.com/\d+` | 🟢 低 | yt-dlp 原生 |
| 小红书 | `xiaohongshu\.com/.*/(\w+)` | 🟡 中 | 需 X-signer / cookies |
| 抖音 | `douyin\.com/video/\d+` | 🟡 中 | 需 X-Bogus 签名 |
| 微信视频号 | `channels.weixin.qq.com/...` | 🔴 高 | 反爬严 |
| Coursera | `coursera\.org/lecture/...` | 🟡 中 | 章节化友好 |

---

## ✅ 重构优先级

1. **MVP**（1-2 天）：YouTube fetcher（yt-dlp 白送）
2. **统一性**（半天）：把 B 站现有脚本迁到 `BilibiliFetcher` 接口
3. **自动检测**（半天）：URL 路由 + 注册中心
4. **字幕优先**（1 天）：YouTube 官方字幕跳过 Whisper，可节省 5 分钟
5. **CLI**（1 天）：typer + 进度条 + 彩色输出
6. **第三方插件**（可选）：entry_points 机制