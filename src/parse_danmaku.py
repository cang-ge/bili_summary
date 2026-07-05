import zlib, re, json

with open(r'C:\Users\Administrator\AppData\Local\Temp\bili_danmaku.xml', 'rb') as f:
    data = f.read()

decompressed = zlib.decompress(data, -15).decode('utf-8', errors='replace')
print('Total decompressed:', len(decompressed))

# Parse <d p="time,type,size,color,pool,user,id">text</d>
ms = re.finditer(r'<d p="([^"]+)">([^<]+)</d>', decompressed)
danmaku = []
for m in ms:
    p = m.group(1).split(',')
    text = m.group(2)
    if len(p) >= 4:
        try:
            time_sec = float(p[0])
            danmaku.append({'time': time_sec, 'text': text})
        except: pass

danmaku.sort(key=lambda x: x['time'])
print(f'Total danmaku entries: {len(danmaku)}')

# Save as JSON
with open(r'C:\Users\Administrator\AppData\Local\Temp\bili_danmaku.json', 'w', encoding='utf-8') as f:
    json.dump(danmaku, f, ensure_ascii=False, indent=2)

# Print first 30 danmaku entries (with time)
for d in danmaku[:30]:
    m = int(d['time'] // 60)
    s = int(d['time'] % 60)
    print(f'[{m:02d}:{s:02d}] {d["text"]}')