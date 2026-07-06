"""
PDF renderer — driven by `data['layout']` built by llm_client._build_layout().

Each layout item is dispatched by its `type` field to the matching section
builder.  Sections with no meaningful content are absent from the layout
array and thus never rendered — no empty headers or placeholders.
"""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer,
    Table, TableStyle, PageBreak, HRFlowable, KeepTogether,
    Image as RLImage,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

from design_tokens import (
    INK_HEX as INK,
    GOLD_HEX as GOLD,
    PAPER_HEX as PAPER,
    SLATE_HEX as SLATE,
    BORDER_HEX as BORDER,
    PURPLE_HEX as PURPLE,
    EMERALD_HEX as EMERALD,
    AMBER_HEX as AMBER,
    RED_HEX as RED,
    MUTED_BG_HEX as MUTED_BG,
)


def _register_font():
    """Register STSong-Light for CJK. No-op if already registered."""
    try:
        pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
    except Exception:
        pass


def _styles():
    s = getSampleStyleSheet()
    return {
        'eyebrow': ParagraphStyle('Eyebrow', parent=s['Normal'], fontName='STSong-Light',
            fontSize=9, leading=12, textColor=GOLD, spaceAfter=4),
        'display': ParagraphStyle('Display', parent=s['Title'], fontName='STSong-Light',
            fontSize=28, leading=36, textColor=INK, spaceAfter=4),
        'subhead': ParagraphStyle('Subhead', parent=s['Normal'], fontName='STSong-Light',
            fontSize=14, leading=20, textColor=SLATE, spaceAfter=10, fontStyle='italic'),
        'h1': ParagraphStyle('H1', parent=s['Heading1'], fontName='STSong-Light',
            fontSize=22, leading=30, spaceAfter=4, spaceBefore=4, textColor=INK),
        'num': ParagraphStyle('Num', parent=s['Normal'], fontName='STSong-Light',
            fontSize=11, leading=14, textColor=GOLD, spaceAfter=0),
        'h2': ParagraphStyle('H2', parent=s['Heading2'], fontName='STSong-Light',
            fontSize=15, leading=22, spaceAfter=6, spaceBefore=10, textColor=INK),
        'h3': ParagraphStyle('H3', parent=s['Heading3'], fontName='STSong-Light',
            fontSize=12, leading=18, spaceAfter=4, spaceBefore=8, textColor=SLATE,
            fontStyle='italic'),
        'body': ParagraphStyle('Body', parent=s['BodyText'], fontName='STSong-Light',
            fontSize=10, leading=16, spaceAfter=4, alignment=TA_JUSTIFY, textColor=INK),
        'bullet': ParagraphStyle('Bullet', parent=s['BodyText'], fontName='STSong-Light',
            fontSize=10, leading=16, leftIndent=14, spaceAfter=2, textColor=INK),
        'quote': ParagraphStyle('Quote', parent=s['BodyText'], fontName='STSong-Light',
            fontSize=10.5, leading=17, leftIndent=20, rightIndent=20,
            textColor=INK, spaceAfter=8, spaceBefore=6, fontStyle='italic'),
        'foot': ParagraphStyle('Foot', parent=s['Normal'], fontName='STSong-Light',
            fontSize=8, leading=11, textColor=SLATE),
        'caption': ParagraphStyle('Caption', parent=s['Normal'], fontName='STSong-Light',
            fontSize=9, leading=12, textColor=SLATE, fontStyle='italic',
            alignment=TA_CENTER, spaceAfter=6),
        'small': ParagraphStyle('Small', parent=s['Normal'], fontName='STSong-Light',
            fontSize=9, leading=13, textColor=SLATE),
    }


# ===== Helpers =====
def hr(color=BORDER, thickness=0.4):
    return HRFlowable(width="100%", thickness=thickness,
                      color=colors.HexColor(color), spaceBefore=2, spaceAfter=8)


def gold_rule(width='25%'):
    return HRFlowable(width=width, thickness=1.2, color=colors.HexColor(GOLD),
                      spaceBefore=2, spaceAfter=6, hAlign='LEFT')


def p(text, st):
    return Paragraph(text or '', st)


def bullet(text, st):
    return Paragraph(f'· {text}', st)


def quote(text, st):
    return Paragraph(f'<font color="{GOLD}">▍ </font>{text}', st)


def section_header(num, title, eyebrow=None, st=None):
    flow = []
    if eyebrow:
        flow.append(p(eyebrow.upper(), st['eyebrow']))
    flow.append(p(f'<font color="{GOLD}">{num}</font>  {title}', st['h1']))
    flow.append(gold_rule('15%'))
    return flow


def optional(flowables):
    """Wrap a list of flowables so missing/empty sections don't leave half-pages."""
    return KeepTogether(flowables) if flowables else None


# ===== Section builders =====
def _section_cover(assets, st):
    flow = []
    cover_path = assets.get('cover')
    if cover_path and Path(cover_path).exists():
        flow.append(RLImage(str(cover_path), width=17.7 * cm, height=10 * cm))
    return flow


def _section_meta(d, st, eyebrow, en_eyebrow):
    flow = []
    flow += section_header(eyebrow, '视频基本信息', en_eyebrow, st)

    rows = [
        ['标题', d.get('title') or '—'],
        ['UP 主', d.get('uploader') or '—'],
        ['BV 号', d.get('bvid') or '—'],
        ['时长', d.get('duration_label') or '—'],
        ['发布日期', str(d.get('pubdate') or '—')],
        ['数据', ' · '.join(filter(None, [
            f"{d.get('view')} 播放" if d.get('view') else '',
            f"{d.get('like')} 赞" if d.get('like') else '',
            f"{d.get('favorite')} 收藏" if d.get('favorite') else '',
            f"{d.get('danmaku')} 弹幕" if d.get('danmaku') else '',
        ])) or '—'],
        ['分区', d.get('tname') or '—'],
        ['标签', ' / '.join(d.get('tags') or []) or '—'],
    ]
    rows = [r for r in rows if r[1] and r[1] != '—']

    t = Table(rows, colWidths=[3 * cm, 14 * cm])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'STSong-Light'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor(MUTED_BG)),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor(GOLD)),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor(BORDER)),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    flow.append(t)

    # Intro paragraph inlined on the same page (ponytail: merged into meta)
    intro_para = d.get('_intro') or ''
    if intro_para:
        flow.append(Spacer(1, 0.3 * cm))
        flow.append(p(intro_para, st['body']))
    return flow


def _section_infographic(assets, info, st):
    flow = []
    info = info if isinstance(info, dict) else {}
    flow.append(p((info.get('eyebrow') or 'CORE TAKEAWAYS').upper(), st['eyebrow']))
    flow.append(p(info.get('hero_title') or '核心结论', st['display']))
    flow.append(p('TL;DR · 60 秒读完', st['subhead']))
    flow.append(gold_rule('20%'))

    info_path = assets.get('infographic')
    if info_path and Path(info_path).exists():
        flow.append(RLImage(str(info_path), width=17.7 * cm, height=13.3 * cm))
        flow.append(Spacer(1, 0.2 * cm))
        flow.append(p('▲ 一图速览 · 详见后续章节展开', st['caption']))
    return flow


def _section_chapter(d, st, eyebrow, en_eyebrow):
    flow = []
    title = d.get('title') or '章节'
    flow += section_header(eyebrow, title, en_eyebrow, st)

    if d.get('subtitle'):
        flow.append(p(d['subtitle'], st['subhead']))

    if d.get('body'):
        flow.append(p(d['body'], st['body']))

    for b in (d.get('bullets') or []):
        flow.append(bullet(str(b), st['bullet']))

    for sub in (d.get('subsections') or []):
        flow.append(p(sub.get('heading', ''), st['h3']))
        for b in (sub.get('bullets') or []):
            flow.append(bullet(str(b), st['bullet']))

    if d.get('pull_quote'):
        flow.append(Spacer(1, 0.2 * cm))
        flow.append(quote(d['pull_quote'], st['quote']))
    return flow


def _section_pro_tips(d, st, eyebrow, en_eyebrow):
    flow = [PageBreak()]
    items = d.get('items') or []
    title = d.get('intro') or '临场技巧'
    flow += section_header(eyebrow, title, en_eyebrow, st)
    for it in items:
        if it.get('heading'):
            flow.append(p(it['heading'], st['h2']))
        for b in (it.get('bullets') or []):
            flow.append(bullet(str(b), st['bullet']))
    return flow


def _section_money_map(d, st, eyebrow, en_eyebrow):
    rows = d.get('rows') or []
    if len(rows) < 3:
        return []
    flow = [PageBreak()]
    flow += section_header(eyebrow, d.get('intro') or '钱花在哪里 · 不花在哪里',
                           en_eyebrow, st)

    status_color = {'推荐': EMERALD, '不建议': RED, '看情况': AMBER}
    data = [['建议', '项目', '理由']]
    for r in rows:
        data.append([
            r.get('status', ''),
            r.get('item', ''),
            r.get('reason', ''),
        ])
    t = Table(data, colWidths=[2.4 * cm, 5 * cm, 10 * cm])
    style = [
        ('FONTNAME', (0, 0), (-1, -1), 'STSong-Light'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(MUTED_BG)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor(GOLD)),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor(BORDER)),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]
    for i, r in enumerate(rows, start=1):
        c = status_color.get(r.get('status', ''))
        if c:
            style.append(('TEXTCOLOR', (0, i), (0, i), colors.HexColor(c)))
    t.setStyle(TableStyle(style))
    flow.append(t)
    return flow


def _section_quotes(d, st, eyebrow, en_eyebrow):
    items = d.get('items') or []
    items = [q for q in items if q]
    if not items:
        return []
    flow = [PageBreak()]
    flow += section_header(eyebrow, '关键金句', en_eyebrow, st)
    for q in items[:12]:
        flow.append(quote(q, st['quote']))
    return flow


def _section_timestamp_index(d, st, eyebrow, en_eyebrow):
    rows = d.get('rows') or []
    if len(rows) < 3:
        return []
    flow = [PageBreak()]
    flow += section_header(eyebrow, '附录 · 时间戳索引', en_eyebrow, st)

    data = [['时间范围', '主题']]
    for r in rows:
        data.append([r.get('range', ''), r.get('topic', '')])
    t = Table(data, colWidths=[3.5 * cm, 13.5 * cm])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'STSong-Light'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(MUTED_BG)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor(GOLD)),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor(BORDER)),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    flow.append(t)
    return flow


def _section_closing(closing, st):
    flow = []
    closing = closing if isinstance(closing, dict) else {}
    flow.append(Spacer(1, 0.6 * cm))
    if closing.get('disclaimer'):
        flow.append(p(closing['disclaimer'], st['foot']))
    if closing.get('credit'):
        flow.append(Spacer(1, 0.2 * cm))
        flow.append(p(closing['credit'], st['foot']))
    return flow


# ===== Main entry =====
def render_pdf(data: dict, out_path: Path) -> None:
    _register_font()
    st = _styles()

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    meta = data.get('meta') or {}
    doc = BaseDocTemplate(
        str(out_path), pagesize=A4,
        leftMargin=2.0 * cm, rightMargin=2.0 * cm,
        topMargin=1.8 * cm, bottomMargin=1.8 * cm,
        title=meta.get('title') or 'Video Summary',
        author=meta.get('uploader') or '',
        subject='B 站视频总结',
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin,
                  doc.width, doc.height, id='normal')
    doc.addPageTemplates([PageTemplate(id='main', frames=[frame])])

    # ---- Layout-driven rendering loop ----
    assets = data.get('_assets') or {}
    layout = data.get('layout') or []
    story = []

    for item in layout:
        t = item['type']
        d = item['data']
        eb = item.get('eyebrow', '')
        en_eb = item.get('en_eyebrow', '')

        if t == 'cover':
            flow = _section_cover(assets, st)
            if flow:
                story += flow
                story.append(PageBreak())

        elif t == 'meta':
            story += _section_meta(d, st, eb, en_eb)
            story.append(PageBreak())

        elif t == 'chapter':
            flow = _section_chapter(d, st, eb, en_eb)
            if flow:
                story.append(KeepTogether(flow))

        elif t == 'pro_tips':
            story += _section_pro_tips(d, st, eb, en_eb)

        elif t == 'money_map':
            story += _section_money_map(d, st, eb, en_eb)

        elif t == 'quotes':
            story += _section_quotes(d, st, eb, en_eb)

        elif t == 'infographic':
            flow = _section_infographic(assets, d, st)
            if flow:
                flow.append(PageBreak())
                story += flow

        elif t == 'timestamp_index':
            story += _section_timestamp_index(d, st, eb, en_eb)

        elif t == 'closing':
            story += _section_closing(d, st)

    doc.build(story)
    print(f'PDF saved: {out_path} ({out_path.stat().st_size // 1024} KB)')


if __name__ == '__main__':
    sample = {
        'meta': {
            'title': '测试视频', 'uploader': 'TestUser', 'bvid': 'BV1xxxx',
            'pubdate': '2026-07-06', 'duration_label': '10 分',
            'view': '1.0 万', 'like': '500', 'favorite': '200', 'danmaku': '30',
            'tname': '知识', 'tags': ['测试', 'demo'],
        },
        'cover': {'display_title': '测试视频'},
        'intro': {'paragraph': '这是一个测试视频的引言。'},
        'layout': [
            {'type': 'cover', 'data': {}},
            {'type': 'meta', 'data': {
                'title': '测试视频', 'uploader': 'TestUser', 'bvid': 'BV1xxxx',
                'pubdate': '2026-07-06', 'duration_label': '10 分',
                'view': '1.0 万', 'like': '500', 'favorite': '200', 'danmaku': '30',
                'tname': '知识', 'tags': ['测试', 'demo'],
            }, 'eyebrow': '01', 'en_eyebrow': 'At a Glance'},
            {'type': 'intro', 'data': {'paragraph': '这是一个测试视频的引言。'}},
            {'type': 'chapter', 'data': {
                'title': '第一章节', 'eyebrow': 'Chapter 1', 'body': '章节正文。',
                'bullets': ['要点 1', '要点 2'], 'pull_quote': '金句示例。'},
             'eyebrow': '02', 'en_eyebrow': 'Chapter 1'},
            {'type': 'chapter', 'data': {
                'title': '第二章节', 'body': '继续。', 'bullets': ['a', 'b']},
             'eyebrow': '03'},
            {'type': 'quotes', 'data': {'items': ['第一句', '第二句', '第三句']},
             'eyebrow': 'QUOTES', 'en_eyebrow': 'Key Quotes'},
            {'type': 'closing', 'data': {'disclaimer': '※ 自动生成的总结', 'credit': '整理 · TestUser'}},
        ],
    }
    render_pdf(sample, Path('output/summary.pdf'))