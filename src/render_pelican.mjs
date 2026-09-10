// Render the Pelican Ride film directly with Blender.
import { existsSync } from 'node:fs';
import { spawn, spawnSync } from 'node:child_process';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));
const script = fileURLToPath(new URL('./render_pelican_video.py', import.meta.url));
const blend = join(root, 'output/pelican/pelican.blend');
const candidates = process.env.BLENDER_BIN
  ? [process.env.BLENDER_BIN]
  : ['blender', ...(process.platform === 'darwin' ? [
    '/Applications/Blender.app/Contents/MacOS/Blender',
    join(homedir(), '.local/opt/blender-4.5.13/Blender.app/Contents/MacOS/Blender'),
  ] : [])];
const executable = candidates.find(name =>
  name === 'blender'
    ? spawnSync(name, ['--version'], { stdio: 'ignore' }).status === 0
    : existsSync(name),
);
if (!executable) {
  throw new Error('Blender was not found. Install Blender 4.5 LTS, add it to PATH, or set BLENDER_BIN.');
}
if (!existsSync(blend)) {
  throw new Error(`Missing ${blend}. Run npm run pelican:scene first.`);
}

const args = [
  '--background',
  blend,
  '--python-exit-code', '1',
  '--python', script,
  '--',
  ...process.argv.slice(2),
];
const child = spawn(executable, args, { cwd: root, stdio: 'inherit' });
child.on('error', error => {
  console.error(error.message);
  process.exitCode = 1;
});
child.on('exit', (code, signal) => {
  process.exitCode = code ?? (signal ? 1 : 0);
});
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => child.kill(signal));
