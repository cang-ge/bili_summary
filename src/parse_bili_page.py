import gzip, re, json

with open(r'C:\Users\Administrator\AppData\Local\Temp\bili_page.html', 'rb') as f:
    data = f.read()
if data[:2] == b'\x1f\x8b':
    data = gzip.decompress(data)

# All extracted text
out = {}

# Title
idx = data.find(b'"title":"')
if idx > 0:
    start = idx + len(b'"title":"')
    end = data.find(b'"', start)
    out['title'] = data[start:end].decode('utf-8', errors='replace')

# desc
idx = data.find(b'"desc":"')
if idx > 0:
    start = idx + len(b'"desc":"')
    end = data.find(b'"', start)
    out['desc'] = data[start:end].decode('utf-8', errors='replace')

# tname (partition name) - usually further in
ms = list(re.finditer(rb'"tname":"([^"]+)"', data))
if ms:
    out['tname'] = ms[0].group(1).decode('utf-8', errors='replace')

# Find owner name - look in a specific area
m = re.search(rb'"owner":\{[^}]*"name":"([^"]+)"', data)
if m:
    out['owner'] = m.group(1).decode('utf-8', errors='replace')

# Tags
tags = re.findall(rb'"tag_name":"([^"]+)"', data)
out['tags'] = [t.decode('utf-8', errors='replace') for t in tags[:20]]

# Long descriptions (subtitle text)
long_descs = re.findall(rb'"description":"([^"]{50,2000})"', data)
out['long_descriptions'] = [d.decode('utf-8', errors='replace')[:500] for d in long_descs[:5]]

# Publish date and duration
m = re.search(rb'"pubdate":(\d+)', data)
if m: out['pubdate'] = int(m.group(1))
m = re.search(rb'"duration":(\d+)', data)
if m: out['duration_sec'] = int(m.group(1))

# Stats
for k in ['view','like','danmaku','reply','favorite','coin','share']:
    m = re.search(rf'"{k}":(\d+)'.encode(), data)
    if m: out[k] = int(m.group(1))

with open(r'C:\Users\Administrator\AppData\Local\Temp\bili_meta.json', 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

# Print to stdout with UTF-8 safe
for k, v in out.items():
    if isinstance(v, list):
        print(f'{k}:')
        for x in v: print(f'  - {x}')
    else:
        print(f'{k}: {v}')

print('---written to bili_meta.json---')