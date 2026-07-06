"""
Single source of truth for design tokens used across all renderers
(make_cover, make_infographic, render_pdf, render_docx).

Centralizing these here means changing the brand is one edit, not four.
Tokens are exposed in three flavours:
    - PIL:        RGB tuples (e.g. INK)
    - reportlab:  '#RRGGBB' strings (e.g. INK_HEX)
    - python-docx: RGBColor instances (e.g. INK_DOCX)
so each renderer can import without per-call conversion.
"""
from pathlib import Path

from docx.shared import RGBColor

# ============ Palette (single source) ============
# 0xRR, 0xGG, 0xBB
PALETTE = {
    'INK':       (0x0F, 0x17, 0x2A),
    'GOLD':      (0xB8, 0x86, 0x0B),
    'PAPER':     (0xFA, 0xF8, 0xF5),
    'SLATE':     (0x64, 0x74, 0x8B),
    'BORDER':    (0xE8, 0xE2, 0xD5),
    'PURPLE':    (0x7C, 0x3A, 0xED),
    'EMERALD':   (0x05, 0x96, 0x69),
    'AMBER':     (0xD9, 0x77, 0x06),
    'RED':       (0xDC, 0x26, 0x26),
    'MUTED_BG':  (0xF4, 0xF0, 0xE8),
    'SOFT':      (0xF4, 0xF0, 0xE8),  # alias used by PIL renderers
    'LAVENDER':  (0xEF, 0xE7, 0xFC),
    'WHITE':     (0xFF, 0xFF, 0xFF),
}


# ============ Name-based accessors ============
def _rgb(name: str) -> tuple:
    return PALETTE[name]


def _hex(name: str) -> str:
    r, g, b = PALETTE[name]
    return f'#{r:02X}{g:02X}{b:02X}'


def _docx(name: str) -> RGBColor:
    r, g, b = PALETTE[name]
    return RGBColor(r, g, b)


# ---- PIL tuples (used by make_cover.py / make_infographic.py) ----
INK       = _rgb('INK')
GOLD      = _rgb('GOLD')
PAPER     = _rgb('PAPER')
SLATE     = _rgb('SLATE')
BORDER    = _rgb('BORDER')
PURPLE    = _rgb('PURPLE')
EMERALD   = _rgb('EMERALD')
AMBER     = _rgb('AMBER')
RED       = _rgb('RED')
MUTED_BG  = _rgb('MUTED_BG')
SOFT      = _rgb('SOFT')
LAVENDER  = _rgb('LAVENDER')
WHITE     = _rgb('WHITE')

# ---- reportlab #RRGGBB strings (used by render_pdf.py) ----
INK_HEX      = _hex('INK')
GOLD_HEX     = _hex('GOLD')
PAPER_HEX    = _hex('PAPER')
SLATE_HEX    = _hex('SLATE')
BORDER_HEX   = _hex('BORDER')
PURPLE_HEX   = _hex('PURPLE')
EMERALD_HEX  = _hex('EMERALD')
AMBER_HEX    = _hex('AMBER')
RED_HEX      = _hex('RED')
MUTED_BG_HEX = _hex('MUTED_BG')

# ---- python-docx RGBColor (used by render_docx.py) ----
INK_DOCX       = _docx('INK')
GOLD_DOCX      = _docx('GOLD')
PAPER_DOCX     = _docx('PAPER')
SLATE_DOCX     = _docx('SLATE')
BORDER_DOCX    = _docx('BORDER')
EMERALD_DOCX   = _docx('EMERALD')
AMBER_DOCX     = _docx('AMBER')
RED_DOCX       = _docx('RED')
MUTED_BG_DOCX  = _docx('MUTED_BG')

# Backwards-compatible aliases for render_docx.py (used as '0F172A' style strings)
BG_DARK  = '0F172A'
BG_LIGHT = 'FCFBF8'
BG_BAND  = 'F4F0E8'

# ============ Fonts ============
# Windows: Noto Serif/Sans SC Variable.
# macOS / Linux: graceful fallback to whatever the system offers.
WINDOWS_FONT_DIRS = (
    Path(r'C:\Windows\Fonts'),
    Path('/Library/Fonts'),                      # macOS system
    Path('/System/Library/Fonts'),                # macOS alternate
    Path('/usr/share/fonts'),                     # Debian/Ubuntu
    Path('/usr/local/share/fonts'),               # brew
    Path('/opt/homebrew/share/fonts'),            # brew Apple Silicon
)

# Preferred font file names (in priority order) — variable fonts are best.
NOTO_SERIF_CANDIDATES = (
    'NotoSerifSC-VF.ttf',
    'NotoSerifSC-Regular.ttf',
    'NotoSerifTC-VF.ttf',
    'NotoSerifSC-Regular.otf',
    'NotoSerifCJK-Regular.ttc',
    'SourceHanSerifSC-Regular.otf',
)
NOTO_SANS_CANDIDATES = (
    'NotoSansSC-VF.ttf',
    'NotoSansSC-Regular.ttf',
    'NotoSansTC-VF.ttf',
    'NotoSansSC-Regular.otf',
    'NotoSansCJK-Regular.ttc',
    'SourceHanSansSC-Regular.otf',
)


def _find_first(names: tuple[str, ...]) -> Path | None:
    """Find the first existing font file matching any of the candidate names."""
    for d in WINDOWS_FONT_DIRS:
        if not d.exists():
            continue
        for n in names:
            p = d / n
            if p.exists():
                return p
    return None


def font_path(kind: str) -> Path:
    """Return a usable Path for ``kind ∈ {'serif', 'sans'}``.

    Resolution order:
      1. Preferred Noto font files in any known system font directory.
      2. Pillow's bundled default via `None` (caller must handle).
    Raises FileNotFoundError if nothing usable is found.
    """
    names = NOTO_SERIF_CANDIDATES if kind == 'serif' else NOTO_SANS_CANDIDATES
    p = _find_first(names)
    if p is not None:
        return p
    # Last resort: look for any Noto* font in those dirs
    for d in WINDOWS_FONT_DIRS:
        if not d.exists():
            continue
        prefix = 'NotoSerif' if kind == 'serif' else 'NotoSans'
        for f in d.glob(f'{prefix}*.ttf'):
            return f
    raise FileNotFoundError(
        f'Could not find any {kind} font. '
        'Install Noto Serif/Sans SC or set $BILI_FONT_DIR.'
    )


def default_font_path() -> Path | None:
    """Return the OS-default font path Pillow should fall back to (None = PIL default)."""
    try:
        from PIL import ImageFont
        # load_default returns an imagefont but we want the path; use truetype fallback to ''
        # That triggers PIL to use the bundled default. Easiest: just try nothing here.
        return None
    except Exception:
        return None


__all__ = [
    'PALETTE',
    # PIL tuples
    'INK', 'GOLD', 'PAPER', 'SLATE', 'BORDER', 'PURPLE', 'EMERALD',
    'AMBER', 'RED', 'MUTED_BG', 'SOFT', 'LAVENDER', 'WHITE',
    # hex
    'INK_HEX', 'GOLD_HEX', 'PAPER_HEX', 'SLATE_HEX', 'BORDER_HEX',
    'PURPLE_HEX', 'EMERALD_HEX', 'AMBER_HEX', 'RED_HEX', 'MUTED_BG_HEX',
    # docx
    'INK_DOCX', 'GOLD_DOCX', 'PAPER_DOCX', 'SLATE_DOCX', 'BORDER_DOCX',
    'EMERALD_DOCX', 'AMBER_DOCX', 'RED_DOCX', 'MUTED_BG_DOCX',
    'BG_DARK', 'BG_LIGHT', 'BG_BAND',
    # fonts
    'font_path', 'default_font_path',
]
