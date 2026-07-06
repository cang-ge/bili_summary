"""
Infographic generator — parameterized over LLM-provided data.

Public function:
    make_infographic(data: dict, out_path: Path) -> None

Reads:
    data['infographic']:    eyebrow / hero_title / hero_source_line / cards (5-9)
    data['meta']:           uploader / bvid / pubdate (year)
    data['closing']:        credit (optional)
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from design_tokens import (
    INK, GOLD, PAPER, SLATE, SOFT, LAVENDER, WHITE,
    font_path,
)

W, H = 4800, 3600

# Resolve fonts with graceful fallback (Windows, macOS, Linux)
NOTO_SERIF = str(font_path('serif'))
NOTO_SANS = str(font_path('sans'))


def load_noto(path, size, weight='Regular'):
    f = ImageFont.truetype(path, size)
    try:
        f.set_variation_by_name(weight)
    except Exception:
        pass
    return f


def _wrap_cjk(text, max_chars):
    """Wrap CJK text by character count (each CJK char ≈ 1 em-width)."""
    if not text:
        return []
    lines = []
    for i in range(0, len(text), max_chars):
        lines.append(text[i:i + max_chars])
    return lines


def _auto_font_size(length, base_size, threshold=12, min_size=60, step=10):
    """Reduce font size when text is longer than threshold chars."""
    if length <= threshold:
        return base_size
    reduction = ((length - threshold) // 5) * step
    return max(min_size, base_size - reduction)


def _draw_card(draw, x0, y0, x1, y1, *, num, title, bullets, is_hero=False):
    """Render one card on the given bbox with auto-wrapping and dynamic font size."""
    radius = 40 if is_hero else 30
    line_w = 8 if is_hero else 4
    draw.rounded_rectangle([(x0, y0), (x1, y1)],
                           radius=radius, fill=WHITE, outline=GOLD, width=line_w)

    # Number circle
    n_size = 70 if is_hero else 56
    sans_num = load_noto(NOTO_SANS, n_size, 'Bold')
    n_r = 80 if is_hero else 55
    n_cx = x0 + (130 if is_hero else 80)
    n_cy = y0 + (130 if is_hero else 80)
    draw.ellipse([(n_cx - n_r, n_cy - n_r), (n_cx + n_r, n_cy + n_r)], fill=GOLD)
    draw.text((n_cx, n_cy), str(num), font=sans_num, fill=WHITE, anchor='mm')

    # ----- Title (wrapped, with dynamic font size) -----
    title_str = str(title) if title else ''
    if is_hero:
        title_font_size = _auto_font_size(len(title_str), 110, threshold=10, min_size=70)
        title_max_chars = 15 if title_font_size >= 90 else 18
        title_y_start = y0 + 300
        title_lh = title_font_size + 20
    else:
        title_font_size = _auto_font_size(len(title_str), 80, threshold=8, min_size=55)
        title_max_chars = 12 if title_font_size >= 65 else 14
        title_y_start = y0 + 200
        title_lh = title_font_size + 18

    serif_card = load_noto(NOTO_SERIF, title_font_size, 'Black' if is_hero else 'Bold')
    title_lines = _wrap_cjk(title_str, title_max_chars)
    title_lines = title_lines[:2]  # max 2 lines for title
    title_x = x0 + (90 if is_hero else 50)
    for j, line in enumerate(title_lines):
        draw.text((title_x, title_y_start + j * title_lh), line,
                  font=serif_card, fill=INK, anchor='lm')

    # Calculate bullet start Y (after title lines)
    title_used = len(title_lines) if title_lines else 1
    bullet_baseline = title_y_start + title_used * title_lh + (40 if is_hero else 30)

    # ----- Bullets (wrapped, dynamic font size) -----
    bullets = [str(b) for b in (bullets or []) if b]
    if not bullets:
        return

    if is_hero:
        body_font_size = _auto_font_size(
            max(len(b) for b in bullets) if bullets else 0,
            50, threshold=4, min_size=38,
        )
        max_chars_per_line = 45 if body_font_size >= 44 else 50
        lh = body_font_size + 30
        # available height for bullets
        avail_h = y1 - 140 - bullet_baseline
        max_lines = max(1, int(avail_h / lh))
        body_x = x0 + 90
        tag_y = y1 - 130
    else:
        body_font_size = _auto_font_size(
            max(len(b) for b in bullets) if bullets else 0,
            50, threshold=4, min_size=36,
        )
        max_chars_per_line = 28 if body_font_size >= 44 else 32
        lh = body_font_size + 22
        avail_h = y1 - 40 - bullet_baseline
        max_lines = max(1, int(avail_h / lh))
        body_x = x0 + 50

    body_font = load_noto(NOTO_SANS, body_font_size, 'Regular')
    rendered = 0
    for b in bullets:
        wrapped = _wrap_cjk(b, max_chars_per_line)
        for line in wrapped:
            if rendered >= max_lines:
                # Show "…" on the last line and stop
                if rendered == max_lines:
                    # Overwrite last line with truncation
                    last_y = bullet_baseline + (rendered - 1) * lh
                    # Draw a black rect to clear, then redraw truncated text
                    draw.rectangle([(body_x, last_y - body_font_size - 5),
                                    (x1 - 20, last_y + 10)],
                                   fill=WHITE)
                    draw.text((body_x, last_y), '… 更多内容',
                              font=body_font, fill=GOLD, anchor='lm')
                break
            draw.text((body_x, bullet_baseline + rendered * lh), line,
                      font=body_font, fill=SLATE if not is_hero else INK, anchor='lm')
            rendered += 1
        if rendered >= max_lines:
            break

    # ----- Hero: "核心要点" tag -----
    if is_hero and rendered > 0:
        sans_body_b = load_noto(NOTO_SANS, 50, 'Bold')
        draw.text((x0 + 90, y1 - 130), '— 核心要点',
                  font=sans_body_b, fill=GOLD, anchor='lm')

    # Bottom-left gold accent
    draw.rectangle([(x0, y1 - 8), (x0 + (120 if is_hero else 120), y1)], fill=GOLD)
    if is_hero:
        draw.rectangle([(x0, y0), (x0 + 12, y1)], fill=GOLD)


def _year(meta: dict) -> str:
    pd = str(meta.get('pubdate') or '')
    return pd[:4] if pd and len(pd) >= 4 and pd[:4].isdigit() else ''


def make_infographic(data: dict, out_path: Path) -> None:
    info = data.get('infographic') or {}
    if not isinstance(info, dict):
        info = {}
    meta = data.get('meta') or {}
    if not isinstance(meta, dict):
        meta = {}
    closing = data.get('closing') or {}
    if not isinstance(closing, dict):
        closing = {}

    eyebrow = info.get('eyebrow') or 'TL;DR · 核心结论'
    hero_title = info.get('hero_title') or data.get('cover', {}).get('display_title') or meta.get('title') or '视频'
    hero_source = info.get('hero_source_line') or ''
    cards = list(info.get('cards') or [])

    uploader = meta.get('uploader') or '—'
    year = _year(meta)
    bvid = meta.get('bvid') or ''
    credit = closing.get('credit') or '整理 · MiniMax-M3'

    if not cards:
        raise RuntimeError('infographic.cards 不能为空')

    # Split hero / smalls
    hero_card = None
    smalls = []
    for c in cards:
        if c.get('is_hero') and hero_card is None:
            hero_card = c
        else:
            smalls.append(c)
    if hero_card is None:
        hero_card, smalls = cards[0], cards[1:]
    if len(smalls) > 8:
        smalls = smalls[:8]

    # Fonts for header
    serif_h1 = load_noto(NOTO_SERIF, 280, 'Black')
    serif_h2 = load_noto(NOTO_SERIF, 110, 'Black')
    sans_eyebrow = load_noto(NOTO_SANS, 70, 'Bold')
    sans_body = load_noto(NOTO_SANS, 50, 'Regular')
    sans_topbar = load_noto(NOTO_SANS, 44, 'Bold')
    sans_foot = load_noto(NOTO_SANS, 36, 'Regular')

    img = Image.new('RGB', (W, H), PAPER)
    draw = ImageDraw.Draw(img)

    # ===== TOP DARK BAND =====
    draw.rectangle([(0, 0), (W, 200)], fill=INK)
    draw.text((150, 100), eyebrow, font=sans_topbar, fill=PAPER, anchor='lm')
    top_right = f"{uploader}  ·  {year}" if year else uploader
    draw.text((W - 150, 100), top_right, font=sans_topbar, fill=GOLD, anchor='rm')
    draw.rectangle([(0, 200), (W, 215)], fill=GOLD)

    # ===== HEADER =====
    draw.text((150, 360), eyebrow, font=sans_eyebrow, fill=GOLD, anchor='lm')

    # Hero title (wrap for longer titles)
    hero_title_str = str(hero_title)
    hero_title_font = serif_h1
    hero_title_max = 12
    if len(hero_title_str) > 12:
        hero_title_font = load_noto(NOTO_SERIF, 200, 'Black')
        hero_title_max = 18
    hero_title_lines = _wrap_cjk(hero_title_str, hero_title_max)
    for j, line in enumerate(hero_title_lines[:2]):
        draw.text((150, 540 + j * 320), line, font=hero_title_font, fill=INK, anchor='lm')

    # Hero sub-title (always shown, even if empty)
    sub_default = '核心要点一览'
    draw.text((150, 900), sub_default, font=serif_h2, fill=INK, anchor='lm')
    draw.rectangle([(150, 1100), (900, 1108)], fill=GOLD)
    if not hero_source:
        # auto-generate a hero source line
        view_str = meta.get('view') or ''
        hero_source = f"— 从视频内容中提炼" + (f" · {view_str} 播放" if view_str else "")
    draw.text((150, 1140), hero_source[:60], font=sans_body, fill=SLATE, anchor='lm')

    # ===== BENTO GRID =====
    grid_top = 1550
    grid_bottom = H - 280

    # Hero (left column, full height)
    hero_x0, hero_y0 = 150, grid_top
    hero_x1 = 2900
    hero_y1 = grid_bottom

    _draw_card(
        draw, hero_x0, hero_y0, hero_x1, hero_y1,
        num=hero_card.get('number') or '01',
        title=hero_card.get('title') or '核心',
        bullets=hero_card.get('bullets') or [],
        is_hero=True,
    )

    # Small cards (right column)
    right_x0 = 3050
    right_x1 = W - 150
    n_smalls = len(smalls)
    if n_smalls == 0:
        return _save(img, out_path)
    small_gap = 40
    small_w = (right_x1 - right_x0 - small_gap) // 2
    if n_smalls <= 4:
        # 1 column
        small_h = (grid_bottom - grid_top - (n_smalls - 1) * small_gap) // n_smalls
        for i, c in enumerate(smalls):
            x0 = right_x0
            x1 = right_x1
            y0 = grid_top + i * (small_h + small_gap)
            y1 = y0 + small_h
            _draw_card(draw, x0, y0, x1, y1,
                       num=c.get('number') or f'{i + 2:02d}',
                       title=c.get('title') or '',
                       bullets=c.get('bullets') or [],
                       is_hero=False)
    else:
        # 2 columns × ceil(n/2) rows
        n_rows = (n_smalls + 1) // 2
        small_h = (grid_bottom - grid_top - (n_rows - 1) * small_gap) // n_rows
        for i, c in enumerate(smalls):
            col = i % 2
            row = i // 2
            x0 = right_x0 + col * (small_w + small_gap)
            x1 = x0 + small_w
            y0 = grid_top + row * (small_h + small_gap)
            y1 = y0 + small_h
            _draw_card(draw, x0, y0, x1, y1,
                       num=c.get('number') or f'{i + 2:02d}',
                       title=c.get('title') or '',
                       bullets=c.get('bullets') or [],
                       is_hero=False)

    # ===== FOOTER =====
    foot_y0 = H - 200
    draw.rectangle([(0, foot_y0), (W, H)], fill=INK)
    draw.rectangle([(0, foot_y0), (W, foot_y0 + 10)], fill=GOLD)
    draw.text((150, foot_y0 + 105),
              f'— 整理：{credit}  ·  Whisper 转录 + LLM 整理',
              font=sans_foot, fill=PAPER, anchor='lm')
    if bvid:
        draw.text((W - 150, foot_y0 + 105), bvid,
                  font=load_noto(NOTO_SANS, 44, 'Bold'),
                  fill=GOLD, anchor='rm')

    _save(img, out_path)


def _save(img: Image.Image, out_path: Path) -> None:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(out_path), 'PNG', optimize=True)
    print(f'Infographic saved: {out_path} ({out_path.stat().st_size // 1024} KB)')


if __name__ == '__main__':
    sample = {
        'infographic': {
            'eyebrow': 'TL;DR · TEST',
            'hero_title': '测试视频',
            'cards': [
                {'number': '01', 'title': '核心要点', 'bullets': ['要点 A', '要点 B'], 'is_hero': True},
                {'number': '02', 'title': '小卡 A', 'bullets': ['a', 'b', 'c']},
                {'number': '03', 'title': '小卡 B', 'bullets': ['x', 'y']},
                {'number': '04', 'title': '小卡 C', 'bullets': ['1', '2']},
                {'number': '05', 'title': '小卡 D', 'bullets': ['a', 'b']},
                {'number': '06', 'title': '小卡 E', 'bullets': ['a']},
                {'number': '07', 'title': '小卡 F', 'bullets': ['a']},
            ],
        },
        'meta': {'uploader': 'TestUser', 'bvid': 'BV1xxxx', 'pubdate': '2026-07-06'},
        'closing': {'credit': 'TestUser'},
        'cover': {'display_title': '测试视频'},
    }
    make_infographic(sample, Path('output/assets/infographic.png'))