"""
Redesigned PDF for the IELTS self-study summary.

Design system (from ui-ux-pro-max):
- Style: Exaggerated Minimalism
- Pattern: Minimal Single Column
- Palette: warm off-white paper + ink black + goldenrod accent
- Typography: bold headlines (Chinese via STSong), refined spacing
- Embedded visual assets: cover, infographic, two diagrams

Layout strategy:
1. Cover page (full-bleed cover image)
2. Video metadata (compact table)
3. TL;DR infographic (full-page image)
4. Schedule diagram + 4 quadrant commentary
5. Listening flow diagram + commentary
6. Sectioned deep-dive content (vocab/listening/reading/writing/speaking)
7. Pro tips
8. Money map
9. Key quotes
10. Timestamp index
"""
import json
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, KeepTogether, HRFlowable, Image
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

OUTPUT = r'C:\Users\Administrator\Desktop\雅思自学流程-Kasa_ZYY-总结.pdf'

pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))

# ===== Design tokens =====
INK = '#0F172A'
GOLD = '#B8860B'
PAPER = '#FAF8F5'
SLATE = '#64748B'
BORDER = '#E8E2D5'
PURPLE = '#7C3AED'
PURPLE_LIGHT = '#F3E8FF'
EMERALD = '#059669'
EMERALD_LIGHT = '#D1FAE5'
AMBER = '#D97706'
AMBER_LIGHT = '#FEF3C7'
MUTED_BG = '#F4F0E8'

styles = getSampleStyleSheet()

# Editorial-style typography
T_EYEBROW = ParagraphStyle('Eyebrow', parent=styles['Normal'], fontName='STSong-Light',
    fontSize=9, leading=12, textColor=GOLD, spaceAfter=4)
T_DISPLAY = ParagraphStyle('Display', parent=styles['Title'], fontName='STSong-Light',
    fontSize=28, leading=36, textColor=INK, spaceAfter=4, fontWeight='bold')
T_SUBHEAD = ParagraphStyle('Subhead', parent=styles['Normal'], fontName='STSong-Light',
    fontSize=14, leading=20, textColor=SLATE, spaceAfter=10, fontStyle='italic')
T_H1 = ParagraphStyle('H1', parent=styles['Heading1'], fontName='STSong-Light',
    fontSize=22, leading=30, spaceAfter=4, spaceBefore=4, textColor=INK)
T_NUM = ParagraphStyle('Num', parent=styles['Normal'], fontName='STSong-Light',
    fontSize=11, leading=14, textColor=GOLD, spaceAfter=0, fontWeight='bold')
T_H2 = ParagraphStyle('H2', parent=styles['Heading2'], fontName='STSong-Light',
    fontSize=15, leading=22, spaceAfter=6, spaceBefore=10, textColor=INK)
T_H3 = ParagraphStyle('H3', parent=styles['Heading3'], fontName='STSong-Light',
    fontSize=12, leading=18, spaceAfter=4, spaceBefore=8, textColor=SLATE, fontStyle='italic')
T_BODY = ParagraphStyle('Body', parent=styles['BodyText'], fontName='STSong-Light',
    fontSize=10, leading=16, spaceAfter=4, alignment=TA_JUSTIFY, textColor=INK)
T_BULLET = ParagraphStyle('Bullet', parent=T_BODY, leftIndent=14, spaceAfter=2)
T_QUOTE = ParagraphStyle('Quote', parent=T_BODY, leftIndent=20, rightIndent=20,
    fontSize=10.5, leading=17, textColor=INK,
    borderColor=GOLD, borderWidth=0,
    borderPadding=10, spaceAfter=8, spaceBefore=6, fontStyle='italic')
T_FOOT = ParagraphStyle('Foot', parent=styles['Normal'], fontName='STSong-Light',
    fontSize=8, leading=11, textColor=SLATE)
T_CAPTION = ParagraphStyle('Caption', parent=styles['Normal'], fontName='STSong-Light',
    fontSize=9, leading=12, textColor=SLATE, fontStyle='italic', alignment=TA_CENTER, spaceAfter=6)

def hr(color=BORDER, thickness=0.4):
    return HRFlowable(width="100%", thickness=thickness, color=colors.HexColor(color),
                      spaceBefore=2, spaceAfter=8)

def gold_rule(width='25%'):
    return HRFlowable(width=width, thickness=1.2, color=colors.HexColor(GOLD),
                      spaceBefore=2, spaceAfter=6, hAlign='LEFT')

def p(text, style=T_BODY):
    return Paragraph(text, style)

def bullet(text):
    return Paragraph(f'· {text}', T_BULLET)

def quote(text):
    # left vertical gold bar + indented italic
    return Paragraph(f'<font color="{GOLD}">▍ </font>{text}', T_QUOTE)

def section_header(num, title, eyebrow=None):
    """Editorial section header: gold number + title + hairline rule."""
    flow = []
    if eyebrow:
        flow.append(p(eyebrow.upper(), T_EYEBROW))
    flow.append(p(f'<font color="{GOLD}">{num}</font>  {title}', T_H1))
    flow.append(gold_rule('15%'))
    return flow

# ===== Document =====
doc = SimpleDocTemplate(OUTPUT, pagesize=A4,
    leftMargin=2.0*cm, rightMargin=2.0*cm,
    topMargin=1.8*cm, bottomMargin=1.8*cm,
    title='雅思自学流程总结 · Kasa_ZYY',
    author='MiniMax-M3',
    subject='IELTS Self-Study Playbook')

story = []

# ============ 1. COVER (full bleed) ============
cover = Image(r'C:\Users\Administrator\Desktop\雅思自学-封面.png',
              width=17.7*cm, height=10*cm)
story.append(cover)
story.append(PageBreak())

# ============ 2. AT-A-GLANCE ============
for f in section_header('01', '视频基本信息', 'At a Glance'):
    story.append(f)

meta = [
    ['标题', '雅思自学流程介绍，以及一些奇技淫巧'],
    ['UP 主', 'Kasa_ZYY'],
    ['BV 号', 'BV1cyDKBLEXY'],
    ['时长', '66 分 15 秒（3975 秒）'],
    ['发布日期', '2026-04-04'],
    ['数据', '318,541 播放 · 22,719 赞 · 48,955 收藏 · 726 弹幕'],
    ['分区', '学习 · 英语 · 雅思'],
    ['标签', '自学 / 英语 / 雅思 / 学习 / 教程 / IELTS'],
]
t = Table(meta, colWidths=[3*cm, 14*cm])
t.setStyle(TableStyle([
    ('FONTNAME', (0,0), (-1,-1), 'STSong-Light'),
    ('FONTSIZE', (0,0), (-1,-1), 10),
    ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#F4F0E8')),
    ('TEXTCOLOR', (0,0), (0,-1), colors.HexColor(GOLD)),
    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor(BORDER)),
    ('LEFTPADDING', (0,0), (-1,-1), 8),
    ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ('TOPPADDING', (0,0), (-1,-1), 6),
    ('BOTTOMPADDING', (0,0), (-1,-1), 6),
]))
story.append(t)
story.append(Spacer(1, 0.4*cm))
story.append(p('内容主线：一份完整的雅思自学日常时间表，加上听力/阅读/写作/词汇的具体方法，以及作者亲身验证过的若干「奇技淫巧」。', T_BODY))

story.append(PageBreak())

# ============ 3. TL;DR INFOGRAPHIC (full-page) ============
story.append(p('CORE TAKEAWAYS', T_EYEBROW))
story.append(p('七条核心结论', T_DISPLAY))
story.append(p('TL;DR · 60 秒读完', T_SUBHEAD))
story.append(gold_rule('20%'))

info = Image(r'C:\Users\Administrator\Desktop\雅思自学-TL;DR-信息图.png',
             width=17.7*cm, height=13.3*cm)
story.append(info)
story.append(Spacer(1, 0.2*cm))
story.append(p('▲ 七条结论一览 · 详见后续章节展开', T_CAPTION))

story.append(PageBreak())

# ============ 4. SCHEDULE DIAGRAM ============
for f in section_header('02', '每日作息', 'Daily Schedule'):
    story.append(f)
story.append(p('作者本人 13 小时备考节奏 · 三个时段、三种能量', T_SUBHEAD))

sch = Image(r'C:\Users\Administrator\Desktop\diagrams\daily-schedule.png',
            width=17.7*cm, height=9.5*cm)
story.append(sch)
story.append(Spacer(1, 0.3*cm))

# Quadrant commentary — proper 2x2 grid, 1 cell per quadrant
quad_data = [
    [
        p('<font color="' + PURPLE + '"><b>上午 · 输入</b></font>', T_BODY),
        p('<font color="' + EMERALD + '"><b>下午 · 练习</b></font>', T_BODY),
    ],
    [
        bullet('词汇是 4 项技能的底座'),
        bullet('完整一套机考（听力 + 阅读）'),
    ],
    [
        bullet('100-150 新词 + 复习 150-200'),
        bullet('报考时段 = 练习时段'),
    ],
    [
        p('<font color="' + AMBER + '"><b>晚上 · 输出</b></font>', T_BODY),
        p('<font color="' + SLATE + '"><b>休息 · 切换</b></font>', T_BODY),
    ],
    [
        bullet('写作早开始，写完 AI 改'),
        bullet('午睡 5 分钟提神'),
    ],
    [
        bullet('模板不动，只升一档'),
        bullet('晚饭彻底离开学习环境'),
    ],
]
t = Table(quad_data, colWidths=[8.85*cm, 8.85*cm])
t.setStyle(TableStyle([
    ('FONTNAME', (0,0), (-1,-1), 'STSong-Light'),
    ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FCFBF8')),
    ('GRID', (0,0), (-1,-1), 0.4, colors.HexColor(BORDER)),
    ('LEFTPADDING', (0,0), (-1,-1), 12),
    ('RIGHTPADDING', (0,0), (-1,-1), 12),
    ('TOPPADDING', (0,0), (-1,-1), 8),
    ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    # Header rows: shaded
    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F4F0E8')),
    ('BACKGROUND', (0,3), (-1,3), colors.HexColor('#F4F0E8')),
    # Color-coded left accent (full quadrant)
    ('LINEBEFORE', (0, 0), (0, 2), 4, colors.HexColor(PURPLE)),
    ('LINEBEFORE', (1, 0), (1, 2), 4, colors.HexColor(EMERALD)),
    ('LINEBEFORE', (0, 3), (0, 5), 4, colors.HexColor(AMBER)),
    ('LINEBEFORE', (1, 3), (1, 5), 4, colors.HexColor(SLATE)),
]))
story.append(t)

story.append(PageBreak())

# ============ 5. VOCAB ============
for f in section_header('03', '词汇 · 一切的地基', 'Vocabulary'):
    story.append(f)
story.append(p('原则、拼写、流程、不要做的事', T_SUBHEAD))

story.append(p('5.1  核心原则', T_H2))
for t_ in [
    '背单词本质是「重复，重复，还是重复」。',
    '每天 100-150 新词，复习 150-200，绝对不能含糊。',
    '三秒规则：3 秒内想不出中文意思 = 不认识，立刻标「不认识」。不要骗自己。',
    '「四会非会就是不会，四懂非懂就是不懂，不懂装懂那更是不懂。」',
    '发音 + 拼写都要记：听力考发音，写作/填空题考拼写。',
]:
    story.append(bullet(t_))

story.append(p('5.2  拼写就是分数', T_H2))
story.append(quote('一个拼写错误 = 1 分没拿到。雅思听力 40 题 / 40 分，错 1 个就是 29 → 6.5 分，跟 7 分天差地别。'))

story.append(p('5.3  流程演示（基于 App）', T_H2))
for t_ in [
    '背 100 个新词 → 完成 ✓',
    '次日：再学新 100 词 + 复习昨天',
    '背到 500 词以后：每天整体过 500 词（只看中文想英文，看英文想中文）',
    '背到 1000 词以后：每天整体过 1000 词',
    '每次过单词时，三秒想不出 → 立刻标错 → 加入「不认识」清单 → 之后再重点背',
]:
    story.append(bullet(t_))

story.append(p('5.4  不要做的事', T_H2))
for t_ in [
    '不要花大量时间抠「单词意识」/ 字眼，只记最常用的中文对应即可。',
    '真的完全查不到的中文意思（如 turbulence 生僻义），再去查 AI，不要逐字查。',
    '不要在阅读时把每个生词都记下来——只记影响你理解句子主干的单词。',
]:
    story.append(bullet(t_))

story.append(PageBreak())

# ============ 6. LISTENING + DIAGRAM ============
for f in section_header('04', '听力 · 奇技淫巧集中地', 'Listening'):
    story.append(f)
story.append(p('考场节奏 · 精听流程 · 错题归档 · 基础信息', T_SUBHEAD))

flow = Image(r'C:\Users\Administrator\Desktop\diagrams\intensive-listening-flow.png',
             width=15.5*cm, height=10*cm, kind='proportional')
# Center it
flow.hAlign = 'CENTER'
story.append(flow)
story.append(p('▲ 精听 5 步流程 · 听力提分唯一方法', T_CAPTION))

story.append(Spacer(1, 0.3*cm))
story.append(p('6.1  考场节奏 · 平时练习的核心技巧', T_H2))
for t_ in [
    '选项要「一眼翻译」：训练自己一秒钟内把匹配题选项的中文意思直接翻译出来。',
    '录音开始放寒暄时（"This is the British Council..."），立刻翻到 P3 先读题。',
    'P2/P3 比 P1/P4 难，重点突破匹配题。',
    'P1 是填词题多，但要警惕偶发的选择题（剑 7/8 出现过，作者亲历）。',
    '做完 P1 之后，你比其他人多看了 P2 一遍题。',
    '填词题：单词、冠词、单复数、时态、大小写一个都不能错。',
]:
    story.append(bullet(t_))

story.append(p('6.2  复盘 · 精听（最最关键）', T_H2))
story.append(quote('精听是提高听力的唯一方法。不要全文精听，要单句精听。'))
for step in [
    '听 1 遍 → 2 遍 → 3 遍',
    '仍不懂 → 打开译文，对照听',
    '还不懂 → 把句子丢给 AI 做语法分析：主谓宾 / 状语 / 定语 / 从句',
    '真正读懂结构 → 下次听到同结构立即反应',
]:
    story.append(bullet(step))

story.append(PageBreak())

story.append(p('6.3  错题归档（用飞书 / Excel）', T_H2))
for t_ in [
    '精听完开始改错，把错误分类：拼写 / 大小写 / 单复数 / 单词不会',
    '所有错词加入每日早上的单词背诵流程',
    '不要追求「精听会不会太简单所以不听」——只要一遍就懂，就过',
]:
    story.append(bullet(t_))

story.append(p('6.4  地图题', T_H2))
for t_ in [
    '本质只是方位词：东南西北 / 红绿灯 / 十字路口',
    '把这些方位词读懂，地图题就很简单',
    '听的时候跟着图形一格一格走，不要提前猜',
]:
    story.append(bullet(t_))

story.append(p('6.5  必须敏感的基础信息', T_H2))
for t_ in [
    '数字：电话号码、护照号、信用卡号等长串要瞬间反应',
    '月份拼写：January 不是 Jan first，是 January first',
    '星期、颜色、国家（Portuguese 等）必须反映迅速',
    'm vs n：人名地名发音（Wombat ≠ Wonbat）第一遍就要听完整名字',
]:
    story.append(bullet(t_))

story.append(PageBreak())

# ============ 7. READING ============
for f in section_header('05', '阅读', 'Reading'):
    story.append(f)
story.append(p('题型策略 · 复盘动作', T_SUBHEAD))

story.append(p('7.1  题型策略', T_H2))
typo_data = [
    [p('<b>题型</b>', T_BODY), p('<b>策略</b>', T_BODY)],
    [p('填空题', T_BODY), p('优先圈出关键定位词（人名 / 时间 / 数字），便于中途插入的填空题', T_BODY)],
    [p('判断题 T/F/NG', T_BODY), p('读 2 道题 → 读 1 段 → 对应判断；拿不准果断跳过，不要纠结 20 分钟', T_BODY)],
    [p('匹配题', T_BODY), p('不要靠一句话定位，理解整段逻辑主干；像阅读理解那样做', T_BODY)],
    [p('单选题', T_BODY), p('问题一定要读懂，选项逐个搞懂；错了就做语法分析', T_BODY)],
]
t = Table(typo_data, colWidths=[3.5*cm, 13.5*cm])
t.setStyle(TableStyle([
    ('FONTNAME', (0,0), (-1,-1), 'STSong-Light'),
    ('BACKGROUND', (0,0), (-1,0), colors.HexColor(INK)),
    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
    ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#FCFBF8')),
    ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor(BORDER)),
    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ('LEFTPADDING', (0,0), (-1,-1), 8),
    ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ('TOPPADDING', (0,0), (-1,-1), 6),
    ('BOTTOMPADDING', (0,0), (-1,-1), 6),
]))
story.append(t)

story.append(p('7.2  复盘 · 关键动作', T_H2))
for t_ in [
    '不要全文标注生词（感动自己），只标影响理解主干的词',
    '不懂的句子 → 复制粘贴给 AI 做语法分析，搞清结构',
    '语法分析不是每句都做：明显简单的不用；不简单的才做（每题约 30 秒，可训练加速）',
    '不要迷信「定位」：IELTS 越来越难，本质上还是考对文章逻辑的理解',
    '做完所有题后回头看：定位 + 句子理解双线并行',
]:
    story.append(bullet(t_))

story.append(PageBreak())

# ============ 8. WRITING ============
for f in section_header('06', '写作', 'Writing'):
    story.append(f)
story.append(p('越早开始 · AI 模板升级 · 错误自查', T_SUBHEAD))

story.append(p('8.1  总体策略', T_H2))
for t_ in [
    '越早开始写越好：水平差也要硬写，错误是改出来的',
    '大作文建议写 400 词左右（要求 250，多写 ≈ 高分；作者总分 6.5 时写作单科拿过 7）',
    '小作文 150-200 词，按题型准备模板',
    '写作 6.5 = 语法好 + 模板稳，并不需要多华丽的单词',
]:
    story.append(bullet(t_))

story.append(p('8.2  AI 改作文的正确打开方式', T_H2))
story.append(quote('让 AI 在你的模板基础上改，只升级到下一档分数（如 6 → 7），不要直接让 AI 给你写一篇 9 分。'))
workflow = [
    '写完一篇',
    '丢给 AI：「请基于我的水平、保持我的模板结构，把用词 / 句式升级到 X.X 分」',
    '拿 AI 改后的版本与自己的版本做对比',
    '逐句问 AI：「为什么改成这样就能到 7 分？」',
    '如此循环，写作能力会真正提升',
]
for s in workflow:
    story.append(bullet(s))

story.append(p('8.3  必须自查的错误类型', T_H2))
for t_ in ['主谓一致 (subject-verb agreement)', '单复数', '拼写 / 大小写', '时态', '指代不明']:
    story.append(bullet(t_))

story.append(PageBreak())

# ============ 9. SPEAKING ============
for f in section_header('07', '口语', 'Speaking'):
    story.append(f)
story.append(p('写作好 → 口语不会差 · 研究题库 ≠ 背答案', T_SUBHEAD))

for t_ in [
    '作者本人口语一直 6 分，但他认为「写作好 → 口语不会差」，二者底层能力相通',
    '如果学校卡小分（6.5 / 7），需要专门研究口语题库',
    '研究题库 ≠ 背答案：研究的是「评分标准在意的格式、剧情、表达方式」',
    '找专业老师做 1-2 次模拟：让老师评价当前分段 + 给提升路径',
    '不要每周都练，1-2 次专项即可',
]:
    story.append(bullet(t_))

story.append(PageBreak())

# ============ 10. PRO TIPS ============
for f in section_header('08', '临场技巧 · 奇技淫巧', 'Pro Tips'):
    story.append(f)

story.append(p('9.1  听力耳机音量（独家技巧）', T_H2))
for t_ in [
    '练习时音量保持 70% 左右',
    '考试那天调到 100% — 平时 70 已经 OK 的，到考场 100 会让你觉得「哇，好清晰」',
    '如果你平时就用 100%，考试就没法再升一级了',
]:
    story.append(bullet(t_))

story.append(p('9.2  考试开始前的「环境观察」', T_H2))
for t_ in [
    '进入机考页面后会先播放考试须知',
    '放完后会给你一个「播放按钮」——不要立即点！',
    '先观察周围同学：是否有老师正在帮同学处理登录问题？',
    '等全场同学都开始放听力了，老师也走了，再点开始',
    '只要不点，时间就不算你的听力时间',
]:
    story.append(bullet(t_))

story.append(p('9.3  考试中的小动作', T_H2))
for t_ in [
    '可以带水进考场（作者经验允许），紧张时含一口',
    '不要喝多，喝多要去厕所 → 浪费时间，且时间不暂停',
]:
    story.append(bullet(t_))

story.append(p('9.4  报考时段选择', T_H2))
story.append(quote('练习在哪个时段，就报哪个时段的考试。大脑会在固定时段自动进入「考试模式」。'))

story.append(p('9.5  剑雅真题使用顺序', T_H2))
for t_ in [
    '建议先做 剑 20 → 剑 18：这些版本前面会放 "this is the British Council..." 的寒暄，给你足够时间练「先读 P3」',
    '剑 17/18 之后开始没有寒暄了，直接进 P1，时间紧',
    '所以先用老版本练节奏，再做新版本',
    '老版本（剑 7/8/9）也要做：题型有时会复古（建桥 7/8 的 P1 选择题作者亲历过）',
    '做过老题 → 考场上不慌',
]:
    story.append(bullet(t_))

story.append(PageBreak())

# ============ 11. MONEY MAP ============
for f in section_header('09', '钱花在哪里 · 不花在哪里', 'Money Map'):
    story.append(f)

money = [
    [p('<b>建议</b>', T_BODY), p('<b>项目</b>', T_BODY), p('<b>理由</b>', T_BODY)],
    [p('<font color="' + EMERALD + '"><b>推荐</b></font>', T_BODY),
     p('AI 会员（ChatGPT 等）', T_BODY),
     p('反馈、情绪价值、持续激励、未来通用技能', T_BODY)],
    [p('<font color="' + EMERALD + '"><b>推荐</b></font>', T_BODY),
     p('专业老师 1 对 1 专项方法课', T_BODY),
     p('当你卡在某一分段很久（如 P1/P4 填空总错），需要人打破思维僵局', T_BODY)],
    [p('<font color="' + EMERALD + '"><b>推荐</b></font>', T_BODY),
     p('写作老师人工批改', T_BODY),
     p('与 AI 互补，更精准、更便宜', T_BODY)],
    [p('<font color="' + EMERALD + '"><b>推荐</b></font>', T_BODY),
     p('口语模拟 1-2 次', T_BODY),
     p('让老师给出明确的提升路径与目标分要求', T_BODY)],
    [p('<font color="#DC2626"><b>不建议</b></font>', T_BODY),
     p('雅思全程班 / 冲刺班', T_BODY),
     p('信息透明、AI 已能覆盖；动辄上万，本质靠自己', T_BODY)],
    [p('<font color="#DC2626"><b>不建议</b></font>', T_BODY),
     p('「3 天 7 天速成」课程', T_BODY),
     p('焦虑营销、装逼话术、毫无玄学', T_BODY)],
    [p('<font color="#DC2626"><b>不建议</b></font>', T_BODY),
     p('真题库（不是剑雅）会员', T_BODY),
     p('碎片化、缺连贯节奏；不如把剑雅做三遍', T_BODY)],
    [p('<font color="' + AMBER + '"><b>看情况</b></font>', T_BODY),
     p('心理咨询', T_BODY),
     p('当你焦虑、心态崩时比报班有用得多', T_BODY)],
]
t = Table(money, colWidths=[2.4*cm, 5*cm, 10*cm])
t.setStyle(TableStyle([
    ('FONTNAME', (0,0), (-1,-1), 'STSong-Light'),
    ('BACKGROUND', (0,0), (-1,0), colors.HexColor(INK)),
    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
    ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#FCFBF8')),
    ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor(BORDER)),
    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ('LEFTPADDING', (0,0), (-1,-1), 6),
    ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ('TOPPADDING', (0,0), (-1,-1), 6),
    ('BOTTOMPADDING', (0,0), (-1,-1), 6),
]))
story.append(t)

story.append(PageBreak())

# ============ 12. KEY QUOTES ============
for f in section_header('10', '关键金句', 'Key Quotes'):
    story.append(f)
story.append(p('— 直接摘自原视频，建议贴在书桌前', T_SUBHEAD))

quotes = [
    '如果你语法都不懂，赶紧停下来，先去学语法。',
    '四会非会就是不会，四懂非懂就是不懂，不懂装懂那更是不懂。',
    '环境是真的非常重要。环境会倒逼自己自学。',
    '雅思这么多年了，技巧性的东西在网上都能找到属于自己的方法。',
    '花 2000 块去考一次，不是为了过，是为了熟悉流程 + 让自己心痛。',
    'AI 不仅是工具，还是情绪价值提供者。',
    '语法真的是一切的基础。',
    '报名时段跟着练习时段走，让大脑自动进入考试状态。',
    '报考下午场就下午练，报考上午就上午练。',
    '听力复习唯一的方法：精听，单句精听。',
    'AI 改作文要在你模板上改到下一档，不要直接写 9 分给你。',
    '小红书 / 抖音删掉，那上面的「8 分有手就行」会影响你心态。',
]
for q in quotes:
    story.append(quote(q))

story.append(PageBreak())

# ============ 13. TIMESTAMP INDEX ============
for f in section_header('11', '附录 · 时间戳索引', 'Appendix'):
    story.append(f)
story.append(p('以下时间戳来自原视频，可对照 B 站跳转到对应段落。', T_FOOT))
story.append(Spacer(1, 0.2*cm))

ts_index = [
    [p('<b>时段</b>', T_BODY), p('<b>内容</b>', T_BODY)],
    [p('00:00 - 05:00', T_BODY), p('开场建议：机考训练 / 第一次裸考 / 报班 vs 自学 / 环境', T_BODY)],
    [p('05:00 - 10:00', T_BODY), p('钱花在哪：AI 会员 / 何时找老师 / 写作口语一对一', T_BODY)],
    [p('10:00 - 15:00', T_BODY), p('真题/速成课避坑 + 每日时间表 + 不碰手机原则', T_BODY)],
    [p('15:00 - 20:00', T_BODY), p('背单词方法：100-150 新词 / 三秒规则 / 整体过', T_BODY)],
    [p('20:00 - 25:00', T_BODY), p('拼写重要性 / 听力选项翻译 / 精听入门', T_BODY)],
    [p('25:00 - 30:00', T_BODY), p('听力考场节奏 / 阅读题型策略 / 平行阅读', T_BODY)],
    [p('30:00 - 35:00', T_BODY), p('判断题节奏 / 精听 3 遍流程 / 语法是基础', T_BODY)],
    [p('35:00 - 40:00', T_BODY), p('错题归档 / 地图题 / 数字月份训练', T_BODY)],
    [p('40:00 - 45:00', T_BODY), p('国家名 / m-n 区分 / 阅读复盘 + AI 语法分析', T_BODY)],
    [p('45:00 - 50:00', T_BODY), p('不做全文标注 / 匹配题逻辑主干 / 语法分析时机', T_BODY)],
    [p('50:00 - 55:00', T_BODY), p('判断题问 AI / 写作要早开始 / 模板升级策略', T_BODY)],
    [p('55:00 - 60:00', T_BODY), p('口语题库研究 / 耳机音量 70 技巧 / 考试环境观察', T_BODY)],
    [p('60:00 - 65:00', T_BODY), p('删小红书抖音 / 早睡早起 / 报下午场', T_BODY)],
    [p('65:00 - 66:15', T_BODY), p('剑雅 7/8/9 老题价值 / 收尾', T_BODY)],
]
t = Table(ts_index, colWidths=[3.5*cm, 13.5*cm])
t.setStyle(TableStyle([
    ('FONTNAME', (0,0), (-1,-1), 'STSong-Light'),
    ('BACKGROUND', (0,0), (-1,0), colors.HexColor(INK)),
    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
    ('BACKGROUND', (0,1), (0,-1), colors.HexColor('#F4F0E8')),
    ('TEXTCOLOR', (0,1), (0,-1), colors.HexColor(GOLD)),
    ('BACKGROUND', (1,1), (-1,-1), colors.HexColor('#FCFBF8')),
    ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor(BORDER)),
    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ('LEFTPADDING', (0,0), (-1,-1), 6),
    ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ('TOPPADDING', (0,0), (-1,-1), 5),
    ('BOTTOMPADDING', (0,0), (-1,-1), 5),
]))
story.append(t)

story.append(Spacer(1, 1*cm))
story.append(hr())
story.append(p('※ 本总结基于 Whisper (small 模型, GPU) 转录后人工精读整理，转录原文保存在 bili_transcript.txt，可对照查询。', T_FOOT))
story.append(p('※ 如需引用本文内容，请注明原视频出处：B 站 BV1cyDKBLEXY · UP 主 Kasa_ZYY', T_FOOT))

# Build
doc.build(story)
print('PDF written to:', OUTPUT)
import os
print('Size:', os.path.getsize(OUTPUT), 'bytes')