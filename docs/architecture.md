# 架构 · Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  INPUT                                                           │
│  Bilibili URL · YouTube URL · X URL · ...                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1 · FETCHERS  (按 URL 路由)                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ Bilibili    │  │ YouTube     │  │ X           │  ...        │
│  │ Fetcher     │  │ Fetcher     │  │ Fetcher     │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│         │                │                │                     │
│         └────────────────┴────────────────┘                     │
│                          VideoMeta                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 2 · TRANSCRIPTION                                        │
│                                                                  │
│  ┌────────────────────┐      ┌────────────────────┐             │
│  │ Official subtitles │  →   │  TranscriptSeg[]   │  (priority) │
│  │ (YouTube, Vimeo)   │      │                    │             │
│  └────────────────────┘      └────────────────────┘             │
│  ┌────────────────────┐      ┌────────────────────┐             │
│  │ Whisper GPU/CPU    │  →   │  TranscriptSeg[]   │  (fallback) │
│  │ (B 站 / 无字幕)    │      │                    │             │
│  └────────────────────┘      └────────────────────┘             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 3 · SUMMARIZATION                                        │
│                                                                  │
│  metadata + transcript + danmaku  →  Summary 结构                │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                 │
│  │ 时间桶分段  │  │ 章节识别    │  │ 金句提取    │                 │
│  └────────────┘  └────────────┘  └────────────┘                 │
│                       │                                          │
│                       ▼                                          │
│              Summary (TL;DR + 12 sections + quotes)              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 4 · VISUAL ASSETS                                         │
│                                                                  │
│  PIL + Noto Serif/Sans SC + matplotlib                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐             │
│  │  cover   │ │infograph │ │ schedule │ │listening │             │
│  │  .png    │ │  .png    │ │  .png    │ │  .png    │             │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 5 · EXPORT                                                │
│                                                                  │
│  ┌────────────────────────┐  ┌────────────────────────┐        │
│  │ reportlab              │  │ python-docx            │        │
│  │ summary.pdf (14 页)    │  │ summary.docx (13 节)   │        │
│  └────────────────────────┘  └────────────────────────┘        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  OUTPUT                                                          │
│  ~/bili_summary/output/summary.pdf  ·  summary.docx            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 数据流

```
URL
  ↓ fetch_metadata
VideoMeta
  ↓ download_audio
audio.mp3 (cache: ~/.cache/ielts-tool/audio/)
  ↓ transcribe (or fetch_subtitles)
TranscriptSegment[]
  ↓ bucket by 5-min interval
StructuredContent
  ↓ summarize
Summary
  ↓ render_assets
{cover, infographic, schedule, listening}.png (cache: assets/)
  ↓ export
PDF + DOCX
```

---

## 关键技术决策

| 决策 | 理由 |
|------|------|
| **yt-dlp** 而非各平台 SDK | 统一 API，1000+ 站点支持，活跃维护 |
| **Whisper small** 默认 | 速度 / 精度平衡（GPU 18× 实时） |
| **PIL** 而非 matplotlib 做 PNG | 字体粗细可控、可变字体权重生效 |
| **reportlab** 而非 weasyprint | PDF 字体无需额外配置、跨平台一致 |
| **STSong-Light** (CID) 而非 ttf | 中文 PDF 字体内置，零字体嵌入问题 |
| **Noto Serif/Sans SC** 作 PNG | 思源系列是高质量开源中文字体 |

---

## 缓存策略

```
~/.cache/ielts-tool/
├── audio/<bvid>.m4a         # 原始音频，避免重下
├── transcripts/<bvid>.json  # Whisper 输出，避免重转
└── danmaku/<bvid>.xml       # 弹幕解压结果

# 跳过已完成的步骤：
if (cache/transcript/<bvid>.json).exists():
    transcript = load_cache()
else:
    transcript = transcribe(audio)
    save_cache(transcript)
```

---

## 重跑代价

| 步骤 | 耗时 | 能否跳过（缓存命中） |
|------|------|---------------------|
| fetch_metadata | < 5s | ✅ 重新拉取便宜 |
| download_audio | 3s (31MB) | ✅ 跳过 |
| transcribe | 3:40 (GPU) | ✅ 跳过（最大节省） |
| render_assets | < 5s | ✅ 便宜 |
| export PDF/DOCX | < 5s | ✅ 便宜 |

**全量重跑**：约 5 分钟（首次） / **10 秒**（增量）