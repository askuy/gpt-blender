// Render a few unique transparent caption plates, then hard-link repeated frames.
// This works with ffmpeg builds that do not include libass or drawtext.
import sharp from 'sharp';
import { readFile, mkdir, writeFile, link, unlink } from 'node:fs/promises';
import { resolve } from 'node:path';

const [assFile, outputDir, secondsText = '17'] = process.argv.slice(2);
const folder = resolve(outputDir);
await mkdir(folder, { recursive: true });
const stamp = (s) => s.split(':').map(Number).reduce((a, b) => a * 60 + b, 0);
const events = (await readFile(assFile, 'utf8')).split('\n').filter((s) => s.startsWith('Dialogue: ')).map((line) => {
  const fields = line.slice(10).split(',');
  return { start: stamp(fields[1]), end: stamp(fields[2]), style: fields[3], text: fields.slice(9).join(',') };
});
const escape = (s) => s.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
function label(event) {
  const style = {
    Label: { x: 42, y: 57, size: 23, color: '#f5f2e8', align: 'start', weight: 500, spacing: 2 },
    Hook: { x: 540, y: 120, size: 40, color: '#fff2e5', align: 'middle', weight: 700, spacing: 0 },
    Speech: { x: 540, y: 994, size: 51, color: '#fff7f0', align: 'middle', weight: 800, spacing: 0 },
    Small: { x: 540, y: 1035, size: 22, color: '#f1e7d7', align: 'middle', weight: 600, spacing: 2 },
  }[event.style];
  return `<text x="${style.x}" y="${style.y}" font-family="Arial, PingFang SC, Noto Sans CJK SC, Noto Sans SC, sans-serif" font-size="${style.size}" font-weight="${style.weight}" letter-spacing="${style.spacing}" text-anchor="${style.align}" fill="${style.color}" stroke="#20291e" stroke-width="${event.style === 'Speech' ? 5 : 2}" stroke-opacity=".8" stroke-linejoin="round" paint-order="stroke">${escape(event.text)}</text>`;
}
const unique = new Map();
for (let frame = 0; frame < Number(secondsText) * 24; frame++) {
  const t = frame / 24;
  const active = events.filter((e) => t >= e.start && t < e.end);
  const key = active.map((e) => e.style + e.text).join('|');
  const path = resolve(folder, `caption_${String(frame + 1).padStart(4, '0')}.png`);
  await unlink(path).catch((error) => { if (error.code !== 'ENOENT') throw error; });
  if (unique.has(key)) { await link(unique.get(key), path); continue; }
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1080"><defs><linearGradient id="shade" x2="0" y2="1"><stop stop-color="#101a12" stop-opacity=".35"/><stop offset="1" stop-color="#101a12" stop-opacity="0"/></linearGradient></defs><rect width="1080" height="150" fill="url(#shade)"/>${active.map(label).join('')}</svg>`;
  await writeFile(path, await sharp(Buffer.from(svg)).png().toBuffer());
  unique.set(key, path);
}
console.log(`Caption plates: ${unique.size}; frames: ${Number(secondsText) * 24}`);
