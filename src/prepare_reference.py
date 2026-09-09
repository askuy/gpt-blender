"""Rebuild the included dialogue excerpt and amplitude envelope from the reference."""
import json
import math
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
reference = ROOT / 'reference/movie-excerpt.mp4'
audio = ROOT / 'web/assets/dialogue.m4a'


def main():
    if not reference.is_file():
        raise SystemExit(f'Missing reference video: {reference}')
    audio.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        'ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-ss', '3.9',
        '-i', str(reference), '-t', '5.9', '-vn', '-c:a', 'aac', '-b:a', '192k', str(audio),
    ], check=True)
    data = subprocess.check_output([
        'ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', str(reference),
        '-ac', '1', '-ar', '12000', '-f', 'f32le', '-',
    ])
    samples = struct.unpack('<' + 'f' * (len(data) // 4), data)
    envelope = []
    for i in range(0, len(samples), 240):
        block = samples[i:i + 240]
        envelope.append(round(math.sqrt(sum(v*v for v in block) / len(block)), 5))
    target = ROOT / 'src/audio-envelope.json'
    target.write_text(json.dumps({'fps': 50, 'reference_start': 3.9, 'samples': envelope}), encoding='utf-8')
    print(f'Prepared {audio.relative_to(ROOT)} and {target.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
