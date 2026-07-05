"""
Daily schedule as a clean table image.
Row = time block, columns: 时段 / 活动 / 时长 / 内容 / 关键.
All text explicitly fits cells via fixed column widths.
"""
from PIL import Image, ImageDraw, ImageFont
import os

W, H = 4800, 2900  # 16:10 wide

# Palette
INK = (15, 23, 42)
GOLD = (184, 134, 11)
PAPER = (250, 248, 245)
SLATE = (100, 116, 139)
SOFT = (244, 240, 232)
BORDER_LIGHT = (232, 226, 213)
WHITE = (255, 255, 255)
PURPLE = (243, 232, 255)
PURPLE_BORDER = (124, 58, 237)
EMERALD = (209, 250, 229)
EMERALD_BORDER = (5, 150, 105)
AMBER = (254, 243, 199)
AMBER_BORDER = (217, 119, 6)
SLATE_LIGHT = (248, 250, 252)

def L(path, size, weight='Regular'):
    f = ImageFont.truetype(path, size)
    try: f.set_variation_by_name(weight)
    except: pass
    return f

# Fonts
serif_title = L(r'C:\Windows\Fonts\NotoSerifSC-VF.ttf', 140, 'Black')
serif_h2 = L(r'C:\Windows\Fonts\NotoSerifSC-VF.ttf', 80, 'Black')
serif_cell = L(r'C:\Windows\Fonts\NotoSerifSC-VF.ttf', 60, 'Bold')

sans_eyebrow = L(r'C:\Windows\Fonts\NotoSansSC-VF.ttf', 50, 'Bold')
sans_header = L(r'C:\Windows\Fonts\NotoSansSC-VF.ttf', 56, 'Bold')
sans_label = L(r'C:\Windows\Fonts\NotoSansSC-VF.ttf', 50, 'Bold')
sans_body = L(r'C:\Windows\Fonts\NotoSansSC-VF.ttf', 48, 'Regular')
sans_small = L(r'C:\Windows\Fonts\NotoSansSC-VF.ttf', 40, 'Regular')
sans_foot = L(r'C:\Windows\Fonts\NotoSansSC-VF.ttf', 36, 'Regular')

img = Image.new('RGB', (W, H), PAPER)
draw = ImageDraw.Draw(img)

# ===== HEADER =====
draw.text((200, 180), '雅思自学 · 每日作息表',
          font=serif_title, fill=INK, anchor='lm')
draw.text((200, 360), 'DAILY SCHEDULE  ·  13 小时高效备考节奏',
          font=sans_eyebrow, fill=GOLD, anchor='lm')

# Gold rule under header
draw.rectangle([(200, 460), (1100, 480)], fill=GOLD)

# ===== TABLE =====
# Margins
TABLE_X = 200
TABLE_Y = 600
TABLE_W = W - 2 * TABLE_X

# Column widths (proportional)
COLS = [
    ('时段',   700),   # time
    ('活动',  900),   # activity
    ('时长',  500),   # duration
    ('内容',  1700),  # content
    ('关键',  600),   # key
]
# Sum: 700 + 900 + 500 + 1700 + 600 = 4400, scale to 4400
scale = TABLE_W / sum(c[1] for c in COLS)
col_widths = [int(c[1] * scale) for c in COLS]
col_x = [TABLE_X]
for w in col_widths[:-1]:
    col_x.append(col_x[-1] + w)

# Header row
HEADER_H = 130
header_y = TABLE_Y
header_h = HEADER_H

# Header background
draw.rectangle([(TABLE_X, header_y),
                (TABLE_X + TABLE_W, header_y + header_h)],
               fill=INK)
# Gold accent stripe at bottom of header
draw.rectangle([(TABLE_X, header_y + header_h),
                (TABLE_X + TABLE_W, header_y + header_h + 8)],
               fill=GOLD)

# Header text
for (name, _), x, w in zip(COLS, col_x, col_widths):
    cx = x + w // 2
    draw.text((cx, header_y + header_h // 2), name,
              font=sans_header, fill=WHITE, anchor='mm')

# Data rows
ROWS = [
    # (时段, 活动, 时长, 内容, 关键, 配色组)
    ('09:00\n12:00', '背单词 · 复习', '3h',
     '100-150 新词 + 复习 150-200\n三秒规则：想不出就标不认识',
     '重复\n就是一切', 'purple'),
    ('12:00\n13:30', '午餐 + 午睡', '1.5h',
     '离开学习环境\n建议小睡 5 分钟提神', '切换\n状态', 'slate'),
    ('13:30\n15:00', '听力 + 阅读', '1.5h',
     '完整一套机考\n下午时段固定 → 形成节奏', '下午\n练习', 'emerald'),
    ('15:00\n17:30', '复盘 + 精听', '2.5h',
     '单句精听 3 遍流程\n错题归档到飞书 / Excel', '提分\n关键', 'emerald'),
    ('17:30\n19:00', '晚饭 + 休息', '1.5h',
     '彻底离开学习环境\n切换状态，准备晚间写作', '切换\n状态', 'slate'),
    ('19:00\n22:00', '写作 + AI 改', '3h',
     '保持模板 → 让 AI 升级到下一档\n不要直接让 AI 写 9 分给你', '晚上\n输出', 'amber'),
]

ROW_H = 290  # tall enough for 2-3 lines of text
data_y_start = header_y + header_h + 8
color_map = {
    'purple':  (PURPLE, PURPLE_BORDER),
    'emerald': (EMERALD, EMERALD_BORDER),
    'amber':   (AMBER, AMBER_BORDER),
    'slate':   (SLATE_LIGHT, BORDER_LIGHT),
}

for r_i, (time, activity, duration, content, key, color_key) in enumerate(ROWS):
    y0 = data_y_start + r_i * ROW_H
    y1 = y0 + ROW_H
    fill, border = color_map[color_key]

    # Row background — alternating soft
    if r_i % 2 == 0:
        row_bg = fill
    else:
        row_bg = WHITE
    draw.rectangle([(TABLE_X, y0), (TABLE_X + TABLE_W, y1)],
                   fill=row_bg)

    # Bottom border (thicker between rows)
    if r_i > 0:
        draw.line([(TABLE_X, y0), (TABLE_X + TABLE_W, y0)],
                  fill=BORDER_LIGHT, width=3)

    # Vertical column separators
    for sep_x in col_x[1:]:
        draw.line([(sep_x, y0), (sep_x, y1)],
                  fill=BORDER_LIGHT, width=2)

    # ===== Cell content =====
    # Col 0: time (bold serif, gold)
    cx0 = col_x[0] + col_widths[0] // 2
    draw.text((cx0, y0 + ROW_H // 2 - 30), time.split('\n')[0],
              font=serif_cell, fill=GOLD, anchor='mm')
    draw.text((cx0, y0 + ROW_H // 2 + 50), time.split('\n')[1],
              font=sans_small, fill=SLATE, anchor='mm')

    # Col 1: activity (bold serif)
    cx1 = col_x[1] + col_widths[1] // 2
    draw.text((cx1, y0 + ROW_H // 2), activity,
              font=serif_h2, fill=INK, anchor='mm')

    # Col 2: duration (large serif black)
    cx2 = col_x[2] + col_widths[2] // 2
    draw.text((cx2, y0 + ROW_H // 2), duration,
              font=serif_cell, fill=INK, anchor='mm')

    # Col 3: content (multi-line)
    cx3 = col_x[3] + 40  # left-aligned with padding
    lines = content.split('\n')
    for li, line in enumerate(lines):
        draw.text((cx3, y0 + 80 + li * 80), line,
                  font=sans_body, fill=INK, anchor='lm')

    # Col 4: key (small caps style)
    cx4 = col_x[4] + col_widths[4] // 2
    key_lines = key.split('\n')
    key_label_font = sans_label
    for li, line in enumerate(key_lines):
        draw.text((cx4, y0 + ROW_H // 2 - 30 + li * 60), line,
                  font=key_label_font, fill=GOLD, anchor='mm')

# Outer border
draw.rectangle([(TABLE_X, header_y),
                (TABLE_X + TABLE_W, data_y_start + len(ROWS) * ROW_H)],
               outline=GOLD, width=6)

# ===== KEY INSIGHT BANNER (below table) =====
insight_y = data_y_start + len(ROWS) * ROW_H + 30
insight_h = 110
draw.rounded_rectangle(
    [(TABLE_X, insight_y), (TABLE_X + TABLE_W, insight_y + insight_h)],
    radius=16, fill=SOFT)
draw.rectangle([(TABLE_X, insight_y), (TABLE_X + 8, insight_y + insight_h)],
               fill=GOLD)

draw.text((TABLE_X + 40, insight_y + 30), '关键洞察',
          font=sans_label, fill=GOLD, anchor='lm')
draw.text((TABLE_X + 40, insight_y + insight_h - 25),
          '报考时段跟着练习时段走，让大脑在固定时段自动进入「考试模式」。',
          font=L(r'C:\Windows\Fonts\NotoSerifSC-VF.ttf', 52, 'Bold'),
          fill=INK, anchor='lm')

# ===== FOOTER =====
foot_y = H - 100
draw.rectangle([(0, foot_y), (W, H)], fill=INK)
draw.rectangle([(0, foot_y), (W, foot_y + 8)], fill=GOLD)
draw.text((200, foot_y + 60), '— 雅思自学流程 · Kasa_ZYY 整理稿',
          font=sans_foot, fill=PAPER, anchor='lm')
draw.text((W - 200, foot_y + 60), 'BV1cyDKBLEXY',
          font=L(r'C:\Windows\Fonts\NotoSansSC-VF.ttf', 44, 'Bold'),
          fill=GOLD, anchor='rm')

out = r'C:\Users\Administrator\Desktop\diagrams\daily-schedule.png'
img.save(out, 'PNG', optimize=True)
print('Saved:', out, '·', os.path.getsize(out), 'bytes')
print('Size:', img.size)