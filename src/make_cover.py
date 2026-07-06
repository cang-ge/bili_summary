"""
Cover generator — parameterized over LLM-provided data.

Public function:
    make_cover(data: dict, out_path: Path) -> None

Reads:
    data['cover']:    eyebrow / display_title / subtitle / tagline / author_line /
                      pull_quote / pull_quote_attribution / stats (list of 3 dicts)
    data['meta']:     uploader / bvid / pubdate (year derived)
    data['closing']:  credit (optional, default "整理 · MiniMax-M3")
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from design_tokens import (
    INK, GOLD, PAPER, SLATE, SOFT, LAVENDER, WHITE,
    font_path,
)

# Image dimensions: 6000 x 3375 (16:9 at high res)
W, H = 6000, 3375

# Resolve fonts with graceful fallback (Windows, macOS, Linux)
NOTO_SERIF = str(font_path('serif'))
NOTO_SANS = str(font_path('sans'))


def load_noto(font_path, size, weight='Regular'):
    f = ImageFont.truetype(font_path, size)
    try:
        f.set_variation_by_name(weight)
    except Exception:
        pass
    return f


def _draw_text(draw, xy, text, font, color=INK, anchor='la'):
    draw.text(xy, text, font=font, fill=color, anchor=anchor)


def _year(meta: dict) -> str:
    pd = str(meta.get('pubdate') or '')
    if pd and len(pd) >= 4 and pd[:4].isdigit():
        return pd[:4]
    return ''


def make_cover(data: dict, out_path: Path) -> None:
    cover = data.get('cover') or {}
    meta = data.get('meta') or {}
    closing = data.get('closing') or {}
    if not isinstance(closing, dict):
        closing = {}

    eyebrow = cover.get('eyebrow') or 'VIDEO · SUMMARY'
    display_title = cover.get('display_title') or meta.get('title') or '视频总结'
    subtitle = cover.get('subtitle') or ''
    tagline = cover.get('tagline') or ''
    author_line = cover.get('author_line') or (
        f"作者 {meta.get('uploader', '—')}  ·  B 站 {meta.get('bvid', '')}"
        + (f"  ·  {meta.get('view', '')} 播放" if meta.get('view') else '')
    )
    pull_quote = cover.get('pull_quote') or ''
    pull_quote_attr = cover.get('pull_quote_attribution') or ''
    stats = (cover.get('stats') or [])[:3]

    uploader = meta.get('uploader') or '—'
    year = _year(meta)
    bvid = meta.get('bvid') or ''
    credit = closing.get('credit') or '整理 · MiniMax-M3'

    # Fonts
    serif_title = load_noto(NOTO_SERIF, 380, 'Black')
    serif_sub = load_noto(NOTO_SERIF, 160, 'Regular')
    serif_quote = load_noto(NOTO_SERIF, 130, 'Black')
    serif_bv = load_noto(NOTO_SERIF, 70, 'Black')
    serif_lav = load_noto(NOTO_SERIF, 160, 'Bold')

    sans_eyebrow = load_noto(NOTO_SANS, 64, 'Bold')
    sans_label = load_noto(NOTO_SANS, 50, 'Bold')
    sans_body = load_noto(NOTO_SANS, 80, 'Regular')
    sans_small = load_noto(NOTO_SANS, 50, 'Regular')
    sans_topbar = load_noto(NOTO_SANS, 50, 'Bold')

    stat_num = load_noto(NOTO_SERIF, 90, 'Black')
    stat_unit = load_noto(NOTO_SANS, 50, 'Bold')
    stat_key = load_noto(NOTO_SANS, 44, 'Bold')
    stat_sub = load_noto(NOTO_SANS, 38, 'Regular')

    img = Image.new('RGB', (W, H), PAPER)
    draw = ImageDraw.Draw(img)

    # ==== TOP DARK BAND ====
    draw.rectangle([(0, 0), (W, 165)], fill=INK)
    _draw_text(draw, (165, 82), eyebrow, sans_topbar, color=PAPER, anchor='lm')
    top_right = f"{uploader}  ·  {year}" if year else uploader
    _draw_text(draw, (W - 165, 82), top_right, sans_topbar, color=GOLD, anchor='rm')

    # ==== LEFT TITLE BLOCK ====
    _draw_text(draw, (420, 540), eyebrow, sans_eyebrow, color=GOLD, anchor='lm')
    draw.rectangle([(420, 645), (720, 655)], fill=GOLD)

    _draw_text(draw, (420, 1280), display_title, serif_title, color=INK, anchor='lm')

    if subtitle:
        _draw_text(draw, (420, 1640), subtitle, serif_sub, color=INK, anchor='lm')

    draw.rectangle([(420, 1900), (2880, 1914)], fill=GOLD)
    if tagline:
        _draw_text(draw, (420, 1980), tagline, sans_body, color=SLATE, anchor='lm')
        author_y = 2120
    else:
        author_y = 2050
    _draw_text(draw, (420, author_y), author_line, sans_small, color=SLATE, anchor='lm')

    # ==== RIGHT DECORATIVE ====
    draw.rectangle([(5400, 1600), (5416, 2400)], fill=GOLD)

    # Use first two "words" of display_title as decorative fallback
    decor_words = (display_title + '   ').split()[:2] if display_title else ['视频', '总结']
    if len(decor_words) >= 2:
        _draw_text(draw, (5340, 1530), decor_words[0], serif_lav, color=LAVENDER, anchor='rm')
        _draw_text(draw, (5340, 1700), decor_words[1] if len(decor_words) > 1 else '',
                   serif_lav, color=LAVENDER, anchor='rm')

    for i in range(3):
        cx = 5160 - i * 100
        draw.ellipse([(cx - 22, 2050 - 22), (cx + 22, 2050 + 22)], fill=GOLD)

    # ==== 3 STAT CALLOUTS ====
    stat_y0 = 2280
    stat_gap = 60
    stat_w = (W - 2 * 420 - 2 * stat_gap) // 3

    for i, s in enumerate(stats):
        x0 = 420 + i * (stat_w + stat_gap)
        cx = x0 + stat_w // 2
        num = str(s.get('num') or '—')
        unit = str(s.get('unit') or '')
        label = str(s.get('label') or '')
        sub = str(s.get('sub') or '')

        draw.rectangle([(x0, stat_y0), (x0 + stat_w, stat_y0 + 6)], fill=GOLD)

        # num + unit
        if num and num != '—':
            num_bbox = stat_num.getbbox(num)
            num_w = num_bbox[2] - num_bbox[0]
            if unit:
                unit_bbox = stat_unit.getbbox(unit)
                unit_w = unit_bbox[2] - unit_bbox[0]
                total_w = num_w + 20 + unit_w
                start_x = cx - total_w // 2
                draw.text((start_x + num_w // 2, stat_y0 + 100), num,
                          font=stat_num, fill=INK, anchor='mm')
                draw.text((start_x + num_w + 20 + unit_w // 2, stat_y0 + 110), unit,
                          font=stat_unit, fill=GOLD, anchor='mm')
            else:
                draw.text((cx, stat_y0 + 100), num, font=stat_num, fill=INK, anchor='mm')

        if label:
            _draw_text(draw, (cx, stat_y0 + 200), label, stat_key, color=INK, anchor='mm')
        if sub:
            _draw_text(draw, (cx, stat_y0 + 270), sub, stat_sub, color=SLATE, anchor='mm')

    # ==== PULL-QUOTE BAND ====
    qbox_y0 = 2620
    qbox_y1 = 3080
    draw.rounded_rectangle([(420, qbox_y0), (W - 420, qbox_y1)],
                           radius=30, fill=SOFT)
    draw.rectangle([(420, qbox_y0), (450, qbox_y1)], fill=GOLD)

    _draw_text(draw, (550, qbox_y0 + 80), 'KEY INSIGHT', sans_label, color=GOLD, anchor='lm')
    if pull_quote:
        _draw_text(draw, (550, qbox_y0 + 200),
                   f'"{pull_quote}"', serif_quote, color=INK, anchor='lm')
    if pull_quote_attr:
        _draw_text(draw, (550, qbox_y1 - 100), pull_quote_attr,
                   sans_small, color=SLATE, anchor='lm')

    # ==== FOOTER BAND ====
    draw.rectangle([(0, H - 240), (W, H)], fill=INK)
    draw.rectangle([(0, H - 240), (W, H - 232)], fill=GOLD)

    _draw_text(draw, (420, H - 155), credit, sans_label, color=GOLD, anchor='lm')
    _draw_text(draw, (420, H - 85), '转录 · Whisper (GPU) + LLM 整理',
               sans_small, color=PAPER, anchor='lm')
    if bvid:
        _draw_text(draw, (W - 420, H - 155), 'BV 号', sans_label, color=GOLD, anchor='rm')
        _draw_text(draw, (W - 420, H - 85), bvid, serif_bv, color=PAPER, anchor='rm')

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(out_path), 'PNG', optimize=True)
    print(f'Cover saved: {out_path} ({out_path.stat().st_size // 1024} KB)')


if __name__ == '__main__':
    # Minimal smoke test
    sample = {
        'cover': {
            'eyebrow': 'STUDY · TEST',
            'display_title': '测试标题',
            'subtitle': '副标题',
            'tagline': '一句话描述',
            'author_line': '作者 测试',
            'pull_quote': '这是一句引言。',
            'pull_quote_attribution': '— 测试来源',
            'stats': [
                {'num': '1', 'unit': '分钟', 'label': '时长', 'sub': '一分钟'},
                {'num': '2', 'unit': '次', 'label': '观看', 'sub': '两次'},
                {'num': '3', 'unit': '万', 'label': '播放', 'sub': '三万'},
            ],
        },
        'meta': {'uploader': 'TestUser', 'bvid': 'BV1xxxx', 'pubdate': '2026-07-06'},
        'closing': {'credit': '整理 · TestUser'},
    }
    make_cover(sample, Path('output/assets/cover.png'))