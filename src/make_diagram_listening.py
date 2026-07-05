"""
Daily schedule diagram v2 — fixed layout, time axis above cards, no overlap.
"""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, Polygon, Rectangle, Circle
from matplotlib import font_manager
from matplotlib.font_manager import FontProperties
import os

# Register fonts
font_manager.fontManager.addfont(r'C:\Windows\Fonts\NotoSerifSC-VF.ttf')
font_manager.fontManager.addfont(r'C:\Windows\Fonts\NotoSansSC-VF.ttf')

SERIF = FontProperties(fname=r'C:\Windows\Fonts\NotoSerifSC-VF.ttf', weight='regular')
SERIF_BLD = FontProperties(fname=r'C:\Windows\Fonts\NotoSerifSC-VF.ttf', weight='black')
SANS = FontProperties(fname=r'C:\Windows\Fonts\NotoSansSC-VF.ttf', weight='regular')
SANS_BLD = FontProperties(fname=r'C:\Windows\Fonts\NotoSansSC-VF.ttf', weight='bold')

plt.rcParams['axes.unicode_minus'] = False

# Palette
PAPER = '#FAF8F5'
INK = '#0F172A'
GOLD = '#B8860B'
SLATE = '#64748B'
BORDER = '#E8E2D5'
PURPLE = '#7C3AED'
PURPLE_LIGHT = '#F3E8FF'
EMERALD = '#059669'
EMERALD_LIGHT = '#D1FAE5'
AMBER = '#D97706'
AMBER_LIGHT = '#FEF3C7'
SOFT = '#F4F0E8'

# Canvas: 16:9 wide
W, H = 14, 9
fig, ax = plt.subplots(figsize=(W, H), dpi=200)
ax.set_xlim(0, 100); ax.set_ylim(0, 56); ax.axis('off')
fig.patch.set_facecolor(PAPER); ax.set_facecolor(PAPER)

# ====== HEADER ======
ax.text(3, 52, '雅思自学 · 每日作息表', fontsize=18,
        fontproperties=SERIF_BLD, color=INK)
ax.text(3, 49, 'Daily Schedule  ·  13 小时高效备考',
        fontsize=9, color=SLATE, fontproperties=SANS)
ax.add_patch(Rectangle((3, 48), 10, 0.15, facecolor=GOLD, edgecolor='none'))

# ====== TIME SCALE (ABOVE the cards) ======
times = [('09:00', 8), ('12:00', 28), ('13:30', 38), ('15:00', 50),
         ('17:30', 70), ('19:00', 82), ('22:00', 95)]

# Time axis line at y=43
ax.add_patch(Rectangle((4, 43), 92, 0.05, facecolor=BORDER, edgecolor='none'))

# Time labels ABOVE the line at y=44.5 (so labels don't overlap cards below)
for t, x in times:
    # Tick mark
    ax.plot([x, x], [42.7, 43.3], color=SLATE, linewidth=0.7)
    # Label above
    ax.text(x, 44.8, t, fontsize=8.5, color=INK, ha='center',
            fontproperties=SANS_BLD)

# ====== CARDS (BELOW the time axis, starting y=31) ======
card_y = 27
card_h = 12

# Block 1: 09:00-12:00 Vocabulary (purple)
# Card spans x=8 to x=28 (width=20)
ax.add_patch(FancyBboxPatch((8, card_y), 20, card_h,
                              boxstyle="round,pad=0,rounding_size=0.4",
                              facecolor=PURPLE_LIGHT, edgecolor=PURPLE, lw=1.2))
ax.text(9, card_y + card_h - 1.5, '上午 · 输入',
        fontsize=8, color=PURPLE, fontproperties=SANS_BLD)
ax.text(9, card_y + card_h - 4, '背单词 · 复习',
        fontsize=11, color=INK, fontproperties=SERIF_BLD)
ax.text(9, card_y + card_h - 6, '+ 过单词',
        fontsize=11, color=INK, fontproperties=SERIF_BLD)
ax.text(9, card_y + 2.5, '100-150 新词',
        fontsize=8, color=INK, fontproperties=SANS)
ax.text(9, card_y + 1, '+ 复习 150-200',
        fontsize=8, color=INK, fontproperties=SANS)

# Block 2: 12:00-13:30 Lunch (slate)
ax.add_patch(FancyBboxPatch((28, card_y), 10, card_h,
                              boxstyle="round,pad=0,rounding_size=0.4",
                              facecolor='#F8FAFC', edgecolor=BORDER, lw=0.8))
ax.text(33, card_y + card_h - 2, '休息',
        fontsize=8, color=SLATE, fontproperties=SANS_BLD, ha='center')
ax.text(33, card_y + card_h - 5.5, '午餐',
        fontsize=10, color=INK, fontproperties=SERIF_BLD, ha='center')
ax.text(33, card_y + card_h - 7.5, '+ 午睡',
        fontsize=10, color=INK, fontproperties=SERIF_BLD, ha='center')
ax.text(33, card_y + 1.5, '提神',
        fontsize=7.5, color=SLATE, fontproperties=SANS, ha='center')

# Block 3: 13:30-15:00 Listening+Reading (emerald)
ax.add_patch(FancyBboxPatch((38, card_y), 12, card_h,
                              boxstyle="round,pad=0,rounding_size=0.4",
                              facecolor=EMERALD_LIGHT, edgecolor=EMERALD, lw=1.2))
ax.text(39, card_y + card_h - 1.5, '下午 · 练习',
        fontsize=8, color=EMERALD, fontproperties=SANS_BLD)
ax.text(39, card_y + card_h - 4, '听力',
        fontsize=11, color=INK, fontproperties=SERIF_BLD)
ax.text(39, card_y + card_h - 6, '+ 阅读',
        fontsize=11, color=INK, fontproperties=SERIF_BLD)
ax.text(39, card_y + 2.5, '完整一套',
        fontsize=8, color=INK, fontproperties=SANS)
ax.text(39, card_y + 1, '机考练习',
        fontsize=8, color=INK, fontproperties=SANS)

# Block 4: 15:00-17:30 Review (emerald)
ax.add_patch(FancyBboxPatch((50, card_y), 20, card_h,
                              boxstyle="round,pad=0,rounding_size=0.4",
                              facecolor=EMERALD_LIGHT, edgecolor=EMERALD, lw=1.2))
ax.text(51, card_y + card_h - 1.5, '下午 · 复盘',
        fontsize=8, color=EMERALD, fontproperties=SANS_BLD)
ax.text(51, card_y + card_h - 4, '复盘 + 精听',
        fontsize=11, color=INK, fontproperties=SERIF_BLD)
ax.text(51, card_y + card_h - 6, '+ 整理错题',
        fontsize=10, color=INK, fontproperties=SERIF_BLD)
ax.text(51, card_y + 2.5, '单句精听',
        fontsize=8, color=INK, fontproperties=SANS)
ax.text(51, card_y + 1, '· 错题归档',
        fontsize=8, color=INK, fontproperties=SANS)

# Block 5: 17:30-19:00 Dinner
ax.add_patch(FancyBboxPatch((70, card_y), 12, card_h,
                              boxstyle="round,pad=0,rounding_size=0.4",
                              facecolor='#F8FAFC', edgecolor=BORDER, lw=0.8))
ax.text(76, card_y + card_h - 2, '休息',
        fontsize=8, color=SLATE, fontproperties=SANS_BLD, ha='center')
ax.text(76, card_y + card_h - 5.5, '晚饭',
        fontsize=10, color=INK, fontproperties=SERIF_BLD, ha='center')
ax.text(76, card_y + card_h - 7.5, '+ 休息',
        fontsize=10, color=INK, fontproperties=SERIF_BLD, ha='center')
ax.text(76, card_y + 1.5, '切换状态',
        fontsize=7.5, color=SLATE, fontproperties=SANS, ha='center')

# Block 6: 19:00-22:00 Writing (amber) — full width, second row
write_y = card_y - card_h - 2  # Below first row
write_h = 12
ax.add_patch(FancyBboxPatch((8, write_y), 74, write_h,
                              boxstyle="round,pad=0,rounding_size=0.4",
                              facecolor=AMBER_LIGHT, edgecolor=AMBER, lw=1.2))
ax.text(9, write_y + write_h - 1.5, '晚上 · 输出',
        fontsize=8, color=AMBER, fontproperties=SANS_BLD)
ax.text(9, write_y + write_h - 4, '写作 + AI 改作文',
        fontsize=12, color=INK, fontproperties=SERIF_BLD)
ax.text(9, write_y + write_h - 6.5, '+ 看课程视频',
        fontsize=10, color=INK, fontproperties=SERIF_BLD)
ax.text(9, write_y + 2.5,
        '保持模板 · 让 AI 升级到下一档',
        fontsize=8, color=INK, fontproperties=SANS)
ax.text(9, write_y + 1, '· 不要直接让 AI 写 9 分给你',
        fontsize=8, color=INK, fontproperties=SANS)

# ====== KEY INSIGHT BOX ======
insight_y = 4
insight_h = 5
ax.add_patch(FancyBboxPatch((8, insight_y), 74, insight_h,
                              boxstyle="round,pad=0,rounding_size=0.4",
                              facecolor=SOFT, edgecolor='none'))
ax.add_patch(Rectangle((8, insight_y), 0.25, insight_h,
                         facecolor=GOLD, edgecolor='none'))

ax.text(10, insight_y + insight_h - 1.5, '关键洞察',
        fontsize=9, color=GOLD, fontproperties=SANS_BLD)
ax.text(10, insight_y + insight_h - 3.2,
        '报考时段跟着练习时段走，让大脑在固定时段自动进入「考试模式」。',
        fontsize=9.5, color=INK, fontproperties=SERIF, style='italic')

# ====== FOOTER ======
ax.add_patch(Rectangle((0, 0), 100, 2.5, facecolor=INK, edgecolor='none'))
ax.text(3, 1.25, '— 雅思自学流程 · Kasa_ZYY 整理稿',
        fontsize=7.5, color=PAPER, fontproperties=SANS, va='center')
ax.text(97, 1.25, 'BV1cyDKBLEXY',
        fontsize=7.5, color=GOLD, fontproperties=SANS_BLD,
        ha='right', va='center')

out = r'C:\Users\Administrator\Desktop\diagrams\daily-schedule.png'
plt.savefig(out, dpi=200, bbox_inches='tight', facecolor=PAPER, pad_inches=0.15)
plt.close()
print('Saved:', out, '·', os.path.getsize(out), 'bytes')