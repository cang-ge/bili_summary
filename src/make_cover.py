"""
Cover v6 — Use PIL for proper Chinese font rendering with weights.
PIL's truetype engine handles variable font weights via font_variant().
"""
from PIL import Image, ImageDraw, ImageFont
import os

# Image dimensions: 6000 x 3375 (16:9 at high res)
W, H = 6000, 3375

# Palette
INK = (15, 23, 42)
GOLD = (184, 134, 11)
PAPER = (250, 248, 245)
SLATE = (100, 116, 139)
SOFT = (244, 240, 232)
LAVENDER = (239, 231, 252)
WHITE = (255, 255, 255)

# Helper to load Noto with a target weight via variation axis
def load_noto(font_path, size, weight='Regular'):
    f = ImageFont.truetype(font_path, size)
    try:
        f.set_variation_by_name(weight)
    except Exception:
        pass
    return f

# Load all fonts
serif_title = load_noto(r'C:\Windows\Fonts\NotoSerifSC-VF.ttf', 380, 'Black')
serif_sub   = load_noto(r'C:\Windows\Fonts\NotoSerifSC-VF.ttf', 160, 'Regular')
serif_quote = load_noto(r'C:\Windows\Fonts\NotoSerifSC-VF.ttf', 130, 'Black')
serif_bv    = load_noto(r'C:\Windows\Fonts\NotoSerifSC-VF.ttf', 70, 'Black')
serif_lav   = load_noto(r'C:\Windows\Fonts\NotoSerifSC-VF.ttf', 160, 'Bold')

sans_eyebrow = load_noto(r'C:\Windows\Fonts\NotoSansSC-VF.ttf', 64, 'Bold')
sans_label   = load_noto(r'C:\Windows\Fonts\NotoSansSC-VF.ttf', 50, 'Bold')
sans_body    = load_noto(r'C:\Windows\Fonts\NotoSansSC-VF.ttf', 80, 'Regular')
sans_small   = load_noto(r'C:\Windows\Fonts\NotoSansSC-VF.ttf', 50, 'Regular')
sans_topbar  = load_noto(r'C:\Windows\Fonts\NotoSansSC-VF.ttf', 50, 'Bold')

# Create image
img = Image.new('RGB', (W, H), PAPER)
draw = ImageDraw.Draw(img)

# Helper to draw text with optional alpha
def draw_text(xy, text, font, color=INK, anchor='la'):
    draw.text(xy, text, font=font, fill=color, anchor=anchor)

# ==== TOP DARK BAND ====
draw.rectangle([(0, 0), (W, 165)], fill=INK)
draw_text((165, 82), 'STUDY · ESSAY · NO.01', sans_topbar, color=PAPER, anchor='lm')
draw_text((W - 165, 82), 'KASA_ZYY  ·  2026', sans_topbar, color=GOLD, anchor='rm')

# ==== LEFT TITLE BLOCK ====
# Eyebrow
draw_text((420, 540), 'IELTS · SELF-STUDY PLAYBOOK', sans_eyebrow, color=GOLD, anchor='lm')
# Gold underline beneath eyebrow
draw.rectangle([(420, 645), (720, 655)], fill=GOLD)

# Main title — large serif BLACK
draw_text((420, 1280), '雅思自学', serif_title, color=INK, anchor='lm')

# Sub-title italic
draw_text((420, 1640), '从裸考一次开始', serif_sub, color=INK, anchor='lm')

# Gold horizontal rule
draw.rectangle([(420, 1900), (2880, 1914)], fill=GOLD)

# Subtitle
draw_text((420, 1980), '一份 66 分钟视频的全套方法论', sans_body, color=SLATE, anchor='lm')

# Author line
draw_text((420, 2120), '作者 Kasa_ZYY  ·  B 站 BV1cyDKBLEXY  ·  31.8 万播放',
          sans_small, color=SLATE, anchor='lm')

# ==== RIGHT DECORATIVE ELEMENT ====
# Vertical gold rule
draw.rectangle([(5400, 1600), (5416, 2400)], fill=GOLD)

# SELF / STUDY lavender italic
draw_text((5340, 1530), 'SELF', serif_lav, color=LAVENDER, anchor='rm')
draw_text((5340, 1700), 'STUDY', serif_lav, color=LAVENDER, anchor='rm')

# Three gold dots
for i in range(3):
    cx = 5160 - i * 100
    draw.ellipse([(cx-22, 2050-22), (cx+22, 2050+22)], fill=GOLD)

# ==== MIDDLE: 3 STAT CALLOUTS ====
stat_y0 = 2280
stat_y1 = 2500
stat_gap = 60
stat_w = (W - 2*420 - 2*stat_gap) // 3

stats = [
    ('66', '视频时长', '分钟', '66 分钟浓缩'),
    ('13', '每日投入', '小时', '13 小时高效备考'),
    ('31.8', '播放量', '万次', 'B 站热门雅思视频'),
]
# Stat number font (smaller — emphasis on unit/label, not raw number)
stat_num = load_noto(r'C:\Windows\Fonts\NotoSerifSC-VF.ttf', 90, 'Black')
stat_unit = load_noto(r'C:\Windows\Fonts\NotoSansSC-VF.ttf', 50, 'Bold')
stat_key = load_noto(r'C:\Windows\Fonts\NotoSansSC-VF.ttf', 44, 'Bold')
stat_sub = load_noto(r'C:\Windows\Fonts\NotoSansSC-VF.ttf', 38, 'Regular')

for i, (num, key, unit, sub) in enumerate(stats):
    x0 = 420 + i * (stat_w + stat_gap)
    cx = x0 + stat_w // 2
    # Top gold accent line
    draw.rectangle([(x0, stat_y0), (x0 + stat_w, stat_y0 + 6)], fill=GOLD)
    # Number + unit on same line (number large, unit smaller to the right)
    num_bbox = stat_num.getbbox(num)
    num_w = num_bbox[2] - num_bbox[0]
    unit_bbox = stat_unit.getbbox(unit)
    unit_w = unit_bbox[2] - unit_bbox[0]
    total_w = num_w + 20 + unit_w
    start_x = cx - total_w // 2
    # Number
    draw.text((start_x + num_w // 2, stat_y0 + 100), num,
              font=stat_num, fill=INK, anchor='mm')
    # Unit (next to number, baseline-aligned)
    draw.text((start_x + num_w + 20 + unit_w // 2, stat_y0 + 110), unit,
              font=stat_unit, fill=GOLD, anchor='mm')
    # Key label
    draw_text((cx, stat_y0 + 200), key, stat_key, color=INK, anchor='mm')
    # Sub
    draw_text((cx, stat_y0 + 270), sub, stat_sub, color=SLATE, anchor='mm')

# ==== BOTTOM: PULL-QUOTE BAND ====
qbox_y0 = 2620
qbox_y1 = 3080
# Background card
draw.rounded_rectangle([(420, qbox_y0), (W - 420, qbox_y1)],
                        radius=30, fill=SOFT)
# Left gold bar
draw.rectangle([(420, qbox_y0), (450, qbox_y1)], fill=GOLD)

draw_text((550, qbox_y0 + 80), 'KEY INSIGHT', sans_label, color=GOLD, anchor='lm')

draw_text((550, qbox_y0 + 200),
          '"真正的捷径只有一条：单句精听。"',
          serif_quote, color=INK, anchor='lm')

draw_text((550, qbox_y1 - 100),
          '— 雅思信息透明 · AI 已能覆盖大部分自学需求 · 环境、语法、重复，才是真正的杠杆。',
          sans_small, color=SLATE, anchor='lm')

# ==== FOOTER BAND ====
draw.rectangle([(0, H - 240), (W, H)], fill=INK)
draw.rectangle([(0, H - 240), (W, H - 232)], fill=GOLD)

draw_text((420, H - 155), '整理 · MiniMax-M3', sans_label, color=GOLD, anchor='lm')
draw_text((420, H - 85), '转录 · Whisper (GPU, RTX 5060 Ti) + 人工精读',
          sans_small, color=PAPER, anchor='lm')

draw_text((W - 420, H - 155), 'BV 号', sans_label, color=GOLD, anchor='rm')
draw_text((W - 420, H - 85), 'BV1cyDKBLEXY', serif_bv, color=PAPER, anchor='rm')

# Save
out = r'C:\Users\Administrator\Desktop\雅思自学-封面.png'
img.save(out, 'PNG', optimize=True)
print('Saved:', out, '·', os.path.getsize(out), 'bytes')
print('Size:', img.size)