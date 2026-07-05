# bili_summary · 视频一键总结 → PDF / DOCX demo

> 把任意视频（B 站、YouTube、X 等）变成结构化总结 + 编辑级 PDF / Word 文档。

---

## 📂 项目结构

```
D:\Study\bili_summary\
├── README.md                 ← 你正在看的
├── .gitignore
├── src/                      ← 所有生成脚本（按顺序可重跑）
│   ├── parse_bili_page.py    #   1. 解析 B 站 HTML 拿到 metadata
│   ├── parse_danmaku.py      #   2. 解压 danmaku XML
│   ├── transcribe.py         #   3. Whisper GPU 转录音频
│   ├── build_summary.py      #   4. 时间桶分段
│   ├── make_cover.py         #   5a. 生成封面 (PIL + Noto Serif SC)
│   ├── make_infographic.py   #   5b. 生成 TL;DR 信息图
│   ├── make_schedule_table.py#  5c. 生成每日作息表格图
│   ├── make_diagram_listening.py # 5d. 生成精听流程图
│   ├── make_pdf.py           #   6a. 用 reportlab 组装 PDF
│   └── make_docx.py          #   6b. 用 python-docx 组装 Word
│
├── assets/                   ← 生成的 PNG / SVG（嵌入 PDF/Word 用）
│   ├── cover.png
│   ├── infographic.png
│   ├── daily-schedule.png
│   └── intensive-listening-flow.png (+.svg)
│
├── transcripts/              ← 中间产物（输入 + 转录）
│   ├── bili_page.html        #   B 站页 HTML（gzip 解压后）
│   ├── bili_meta.json        #   解析后的视频元数据
│   ├── bili_danmaku.json     #   弹幕时间戳
│   ├── bili_transcript.json  #   Whisper 完整输出
│   ├── bili_transcript.txt   #   纯文本转录
│   └── yt-dlp-info.json      #   yt-dlp 抓的元数据
│
├── output/                   ← 最终交付物
│   ├── summary.pdf           #   编辑级 PDF（含封面、图、表）
│   └── summary.docx          #   同款 Word 版
│
└── docs/
    ├── architecture.md       # 整体架构图（待补）
    ├── design-system.md      # 配色 + 字体 + 排版规范
    └── multi-platform.md     # 多平台扩展指南
```

---

## 🎯 这个 demo 干了什么

输入：BV1cyDKBLEXY（Kasa_ZYY《雅思自学流程介绍，以及一些奇技淫巧》）

输出：
- **summary.pdf**（1.6 MB，14 页）
- **summary.docx**（1.1 MB，13 节）

PDF 内含：
- 封面（编辑级大标题 + 数据卡 + 关键洞察 pull-quote）
- 视频元数据表
- 7 条核心结论信息图（bento 布局）
- 每日作息时间表
- 精听 5 步流程图
- 词汇 / 听力 / 阅读 / 写作 / 口语 / 临场技巧 / 钱花在哪 / 关键金句 / 时间戳索引

---

## 🔧 核心依赖

```
Python ≥ 3.11
yt-dlp              # 视频下载
openai-whisper      # 语音转文字
imageio-ffmpeg      # ffmpeg 二进制（whisper 必需）
reportlab           # PDF 生成
python-docx         # Word 生成
Pillow              # 图像生成
matplotlib          # 辅助图像
pdfplumber          # PDF 验证（可选）
```

字体（系统自带，无需打包）：
- **Noto Serif SC**（思源宋体）— 标题
- **Noto Sans SC**（思源黑体）— 正文

---

## 🚀 快速复现（重跑管线）

```bash
# 0. 环境
pip install yt-dlp openai-whisper imageio-ffmpeg reportlab python-docx Pillow matplotlib pdfplumber

# 1. 抓数据（B 站示例）
python src/parse_bili_page.py
python src/parse_danmaku.py

# 2. 下载音频 + Whisper 转录（需 GPU: RTX 5060 Ti 实测 3:40 / 66min）
python src/transcribe.py

# 3. 生成图像资产
python src/make_cover.py
python src/make_infographic.py
python src/make_schedule_table.py
python src/make_diagram_listening.py

# 4. 组装 PDF + Word
python src/make_pdf.py
python src/make_docx.py

# 5. 验证
python -c "import pdfplumber; pdf=pdfplumber.open('output/summary.pdf'); print(len(pdf.pages), 'pages')"
```

---

## 🎨 设计系统

| Token | 值 | 用途 |
|-------|----|----|
| **主色 Ink** | `#0F172A` | 标题、正文 |
| **辅色 Gold** | `#B8860B` | 强调、数字、eyebrow |
| **背景 Paper** | `#FAF8F5` | 暖白纸 |
| **辅文 Slate** | `#64748B` | 副文 |
| **边线 Border** | `#E8E2D5` | 卡片、表格 |
| **强调 Soft** | `#F4F0E8` | 信息块底色 |
| **分类紫** | `#7C3AED` / `#F3E8FF` | 上午输入 |
| **分类绿** | `#059669` / `#D1FAE5` | 下午练习 |
| **分类琥珀** | `#D97706` / `#FEF3C7` | 晚上输出 |

字体：
- 中文标题：**Noto Serif SC** Black weight
- 中文正文：**Noto Sans SC** Regular/Bold
- 英文/数字：系统无衬线
- 装饰英文：Noto Serif SC Italic + 薰衣草色 `#EFE7FC`

---

## 🌐 多平台扩展

详见 [`docs/multi-platform.md`](docs/multi-platform.md)。

简而言之：每个平台一个 `*Fetcher.py`，实现 `VideoFetcher` 接口，
URL 自动路由，YouTube 等有官方字幕的可跳过 Whisper。

---

## 📋 已知限制

1. **B 站音频下载**：仅最小音质绕过大会员限制；高级画质需登录
2. **弹幕**：仅 B 站原生支持；其他平台为空数组
3. **Whisper**：首次运行会下载 ~500 MB 模型；之后本地缓存
4. **GPU 要求**：RTX 5060 Ti 实测转录 18× 实时；CPU 模式约 0.3× 实时
5. **PDF 中文**：依赖系统 `STSong-Light`（Mac/Linux 需替换为 Noto Serif SC）

---

## 📝 License

MIT — 自由使用、修改、商用。