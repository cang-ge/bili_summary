import json
with open(r'C:\Users\Administrator\AppData\Local\Temp\bili_transcript.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Save plain transcript as text for reference
with open(r'C:\Users\Administrator\AppData\Local\Temp\bili_transcript.txt', 'w', encoding='utf-8') as f:
    for s in data['segments']:
        m = int(s['start'] // 60); sec = int(s['start'] % 60)
        f.write(f'[{m:02d}:{sec:02d}] {s["text"].strip()}\n')
print('Transcript text saved. Total segments:', len(data['segments']))