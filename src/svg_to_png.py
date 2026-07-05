"""
Convert SVG diagrams to high-resolution PNGs using cairosvg or fallback.
"""
import subprocess, os

cairo = None
try:
    import cairosvg
    cairo = 'cairosvg'
except ImportError:
    pass

# Try cairosvg first
for svg_name, png_name in [
    ('daily-schedule.svg', 'daily-schedule.png'),
    ('intensive-listening-flow.svg', 'intensive-listening-flow.png'),
]:
    svg = os.path.join(r'C:\Users\Administrator\Desktop\diagrams', svg_name)
    png = os.path.join(r'C:\Users\Administrator\Desktop\diagrams', png_name)
    if cairo:
        cairosvg.svg2png(url=svg, write_to=png, output_width=1800)
        print(f'cairosvg: {svg_name} -> {png_name}')
    else:
        # Fallback: use a Python svg renderer (svglib + reportlab)
        try:
            from svglib.svglib import svg2rlg
            from reportlab.graphics import renderPM
            drawing = svg2rlg(svg)
            renderPM.drawToFile(drawing, png, fmt='PNG')
            print(f'svglib: {svg_name} -> {png_name}')
        except Exception as e:
            print(f'fallback failed: {e}')

if not cairo:
    # Install cairosvg if not available
    subprocess.run(['pip', 'install', '--quiet', 'cairosvg'], check=False)