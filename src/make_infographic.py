"""
Infographic v3 — PIL fixed, all font= kwargs, balanced sizes.
"""
from PIL import Image, ImageDraw, ImageFont
import os

W, H = 4800, 3600

INK = (15, 23, 42)
GOLD = (184, 134, 11)
PAPER = (250, 248, 245)
SLATE = (100, 116, 139)
SOFT = (244, 240, 232)
LAVENDER = (239, 231, 252)
WHITE = (255, 255, 255)

def L(path, size, weight='Regular'):
    f = ImageFont.truetype(path, size)
    try: f.set_variation_by_name(weight)
    except: pass
    return f

serif_h1  = L(r'C:\Windows\Fonts\NotoSerifSC-VF.ttf', 280, 'Black')
serif_h2  = L(r'C:\Windows\Fonts\NotoSerifSC-VF.ttf', 110, 'Black')
serif_card = L(r'C:\Windows\Fonts\NotoSerifSC-VF.ttf', 80, 'Bold')

sans_eyebrow = L(r'C:\Windows\Fonts\NotoSansSC-VF.ttf', 70, 'Bold')
sans_label   = L(r'C:\Windows\Fonts\NotoSansSC-VF.ttf', 48, 'Bold')
sans_num     = L(r'C:\Windows\Fonts\NotoSansSC-VF.ttf', 70, 'Bold')
sans_num_sm  = L(r'C:\Windows\Fonts\NotoSansSC-VF.ttf', 56, 'Bold')
sans_body    = L(r'C:\Windows\Fonts\NotoSansSC-VF.ttf', 50, 'Regular')
sans_body_b  = L(r'C:\Windows\Fonts\NotoSansSC-VF.ttf', 50, 'Bold')
sans_small   = L(r'C:\Windows\Fonts\NotoSansSC-VF.ttf', 42, 'Regular')
sans_topbar  = L(r'C:\Windows\Fonts\NotoSansSC-VF.ttf', 44, 'Bold')
sans_foot    = L(r'C:\Windows\Fonts\NotoSansSC-VF.ttf', 36, 'Regular')

img = Image.new('RGB', (W, H), PAPER)
draw = ImageDraw.Draw(img)

# ===== TOP DARK BAND =====
draw.rectangle([(0, 0), (W, 200)], fill=INK)
draw.text((150, 100), 'IELTS · SELF-STUDY', font=sans_topbar, fill=PAPER, anchor='lm')
draw.text((W - 150, 100), 'KASA_ZYY · 2026', font=sans_topbar, fill=GOLD, anchor='rm')
draw.rectangle([(0, 200), (W, 215)], fill=GOLD)

# ===== HEADER =====
draw.text((150, 360), 'TL;DR · 核心结论', font=sans_eyebrow, fill=GOLD, anchor='lm')

draw.text((150, 540), '雅思自学', font=serif_h1, fill=INK, anchor='lm')
draw.text((150, 900), '七条不绕弯的结论', font=serif_h2, fill=INK, anchor='lm')

draw.rectangle([(150, 1100), (900, 1108)], fill=GOLD)
draw.text((150, 1140), '— 从 B 站 31.8 万播放视频中提炼', font=sans_body, fill=SLATE, anchor='lm')

# ===== BENTO GRID =====
grid_top = 1550
grid_bottom = H - 280

# Hero card (60% width)
hero_x0, hero_y0 = 150, grid_top
hero_x1, hero_y1 = 2900, grid_bottom

draw.rounded_rectangle([(hero_x0, hero_y0), (hero_x1, hero_y1)],
                        radius=40, fill=WHITE, outline=GOLD, width=8)

# Hero number
n_cx, n_cy = hero_x0 + 130, hero_y0 + 130
draw.ellipse([(n_cx-80, n_cy-80), (n_cx+80, n_cy+80)], fill=GOLD)
draw.text((n_cx, n_cy), '01', font=sans_num, fill=WHITE, anchor='mm')

# Hero title
draw.text((hero_x0 + 90, hero_y0 + 300), '能不报班就别报',
          font=serif_h2, fill=INK, anchor='lm')

# Hero description
desc_y = hero_y0 + 580
draw.text((hero_x0 + 90, desc_y), '雅思信息透明，网上 + AI 都能找到答案。',
          font=sans_body, fill=INK, anchor='lm')
draw.text((hero_x0 + 90, desc_y + 90), '班级仅提供环境与刷不到的真题，不等于弥补信息差。',
          font=sans_body, fill=INK, anchor='lm')
draw.text((hero_x0 + 90, desc_y + 180), '动辄上万，本质靠自己，性价比极差。',
          font=sans_body, fill=INK, anchor='lm')

# Hero tag
tag_y = hero_y1 - 130
draw.text((hero_x0 + 90, tag_y), '— 唯一例外：环境本身的价值',
          font=sans_body_b, fill=GOLD, anchor='lm')

# Hero left accent
draw.rectangle([(hero_x0, hero_y0), (hero_x0 + 12, hero_y1)], fill=GOLD)

# ===== 6 SMALL CARDS =====
right_x0 = 3050
right_x1 = W - 150
small_gap = 40
small_w = (right_x1 - right_x0 - small_gap) // 2
small_h = (grid_bottom - grid_top - 2 * small_gap) // 3

items = [
    ('02', '环境 > 一切',
     ['图书馆 + 干净桌面', '+ 手机锁进书包', '专注力 ROI 最高的事']),
    ('03', 'AI 是 2026 杠杆',
     ['ChatGPT = 反馈', '+ 情绪价值', '写作用 AI：模板不动']),
    ('04', '捷径只有：精听',
     ['单句听 1-3 遍', '不懂 → 看译文', '还不懂 → 语法分析']),
    ('05', '语法 = 地基',
     ['听不懂 / 读不懂', '/ 写作错 90%', '都是语法不熟']),
    ('06', '重复 + 拼写',
     ['每天 100-150 新词', '三秒想不出 = 不认识', '拼写错 1 个 = 6.5 vs 7']),
    ('07', '第一次就裸考',
     ['先花 2000 块考一次', '熟悉流程', '+ 倒逼自己认真']),
]

for i, (num, title, lines) in enumerate(items):
    col = i % 2
    row = i // 2
    x0 = right_x0 + col * (small_w + small_gap)
    y0 = grid_top + row * (small_h + small_gap)
    x1 = x0 + small_w
    y1 = y0 + small_h

    draw.rounded_rectangle([(x0, y0), (x1, y1)],
                            radius=30, fill=WHITE, outline=GOLD, width=4)

    n_cx, n_cy = x0 + 80, y0 + 80
    draw.ellipse([(n_cx-55, n_cy-55), (n_cx+55, n_cy+55)], fill=GOLD)
    draw.text((n_cx, n_cy), num, font=sans_num_sm, fill=WHITE, anchor='mm')

    draw.text((x0 + 50, y0 + 200), title, font=serif_card, fill=INK, anchor='lm')

    desc_y = y0 + 360
    for j, line in enumerate(lines):
        draw.text((x0 + 50, desc_y + j * 75), line,
                  font=sans_small, fill=SLATE, anchor='lm')

    draw.rectangle([(x0, y1 - 8), (x0 + 120, y1)], fill=GOLD)

# ===== FOOTER =====
foot_y0 = H - 200
draw.rectangle([(0, foot_y0), (W, H)], fill=INK)
draw.rectangle([(0, foot_y0), (W, foot_y0 + 10)], fill=GOLD)
draw.text((150, foot_y0 + 105), '— 整理：MiniMax-M3  ·  Whisper 转录 + 人工精读',
          font=sans_foot, fill=PAPER, anchor='lm')
draw.text((W - 150, foot_y0 + 105), 'BV1cyDKBLEXY',
          font=L(r'C:\Windows\Fonts\NotoSansSC-VF.ttf', 44, 'Bold'),
          fill=GOLD, anchor='rm')

out = r'C:\Users\Administrator\Desktop\雅思自学-TL;DR-信息图.png'
img.save(out, 'PNG', optimize=True)
print('Saved:', out, '·', os.path.getsize(out), 'bytes')
print('Size:', img.size)