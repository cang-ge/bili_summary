import os, json, shutil
# === Plan C: monkey-patch whisper to use the imageio-bundled ffmpeg ===
import imageio_ffmpeg
FFMPEG_REAL = imageio_ffmpeg.get_ffmpeg_exe()
FFMPEG_DIR = os.path.dirname(FFMPEG_REAL)

# Put ffmpeg dir at front of PATH so subprocess finds it as "ffmpeg"
os.environ['PATH'] = FFMPEG_DIR + os.pathsep + os.environ['PATH']

# Also pre-import whisper and patch its audio loader's expected binary name
import whisper.audio as _wa
import shutil as _sh
_target = _sh.which('ffmpeg')
print(f'ffmpeg resolved to: {_target}')

import whisper
print('Loading model (small, GPU)...')
model = whisper.load_model('small', device='cuda')
print('Transcribing...')
result = model.transcribe(
    r'C:\Users\Administrator\AppData\Local\Temp\bili_audio.wav',
    language='zh',
    task='transcribe',
    verbose=False,
    fp16=True
)
print(f'Segments: {len(result["segments"])}')
with open(r'C:\Users\Administrator\AppData\Local\Temp\bili_transcript.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
total = sum(len(s['text']) for s in result['segments'])
print('Done. Total chars:', total)
# Quick preview
for s in result['segments'][:10]:
    m = int(s['start'] // 60); sec = int(s['start'] % 60)
    print(f'[{m:02d}:{sec:02d}] {s["text"].strip()}')