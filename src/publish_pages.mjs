import { execFile } from 'node:child_process';
import { cp, mkdtemp, readdir, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { promisify } from 'node:util';

const execute = promisify(execFile);
const root = fileURLToPath(new URL('../', import.meta.url));
const repository = 'askuy/niulai-site';
const siteURL = 'https://askuy.github.io/niulai-site/';
const dryRun = process.argv.includes('--dry-run');

async function validate(directory) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const file = join(directory, entry.name);
    if (entry.isSymbolicLink()) throw new Error(`Cannot publish a symlink: ${file}`);
    if (entry.name === '.git' || /\.(mp4|blend|py|go)$/i.test(entry.name)) {
      throw new Error(`Only static viewer assets may be published: ${file}`);
    }
    if (entry.isDirectory()) await validate(file);
  }
}

await validate(join(root, 'web'));
const directory = await mkdtemp(join(tmpdir(), 'niulai-publish-'));
const checkout = join(directory, 'site');
const git = async (...args) => {
  const result = await execute('git', args, { cwd: checkout, timeout: 120000 });
  if (result.stdout.trim()) console.log(result.stdout.trim());
  return result.stdout.trim();
};

try {
  // A separate clone keeps all private source files and history out of the site.
  await execute('git', ['clone', '--depth', '1', `git@github.com:${repository}.git`, checkout], { timeout: 120000 });
  await git('switch', '-C', 'main');
  for (const entry of await readdir(checkout)) {
    if (entry !== '.git') await rm(join(checkout, entry), { recursive: true, force: true });
  }
  await cp(join(root, 'web'), checkout, { recursive: true });
  await git('add', '--all');
  const changes = await git('diff', '--cached', '--name-only');
  if (!changes) {
    console.log(`No asset changes. Site: ${siteURL}`);
  } else {
    // Preserve upstream Three.js formatting, matching the source repository policy.
    await git('diff', '--cached', '--check', '--', '.', ':(exclude)vendor/**');
    await git('diff', '--cached', '--stat');
    if (dryRun) {
      console.log('Dry run complete; no changes were pushed.');
    } else {
      await git('-c', 'user.name=askuy', '-c', 'user.email=14119383+askuy@users.noreply.github.com', 'commit', '-m', 'Publish static viewer');
      await git('push', 'origin', 'main');
      console.log(`Published assets to ${repository}. Check the Pages deployment at ${siteURL}`);
    }
  }
} finally {
  await rm(directory, { recursive: true, force: true });
}
