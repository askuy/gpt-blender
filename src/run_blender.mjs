import { spawn, spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));
const script = fileURLToPath(new URL('./build_scene.py', import.meta.url));
const candidates = process.env.BLENDER_BIN
  ? [process.env.BLENDER_BIN]
  : ['blender', ...(process.platform === 'darwin' ? ['/Applications/Blender.app/Contents/MacOS/Blender'] : [])];
const executable = candidates.find((name) =>
  name === 'blender'
    ? spawnSync(name, ['--version'], { stdio: 'ignore' }).status === 0
    : existsSync(name),
);
if (!executable) {
  console.error('Blender was not found. Install Blender 4.5 LTS, add it to PATH, or set BLENDER_BIN to its executable.');
  process.exit(1);
}
const child = spawn(executable, ['--background', '--python', script, '--', ...process.argv.slice(2)], {
  cwd: root,
  stdio: 'inherit',
});
child.on('error', (error) => { console.error(error.message); process.exitCode = 1; });
child.on('exit', (code, signal) => { process.exitCode = code ?? (signal ? 1 : 0); });
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => child.kill(signal));
