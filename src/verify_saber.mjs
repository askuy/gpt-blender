import { chromium } from '@playwright/test';
import assert from 'node:assert/strict';
import { cp, mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import httpServer from 'http-server';

const root = fileURLToPath(new URL('../', import.meta.url));
const renders = join(root, 'renders/saber');
await mkdir(renders, { recursive: true });
await mkdir(join(root, 'output/saber'), { recursive: true });
const differs = (a, b, tolerance = .01) => a.some((n, i) => Math.abs(n - b[i]) > tolerance);
let browser, server, directory;

try {
  let base = process.env.PREVIEW_URL;
  if (!base) {
    directory = await mkdtemp(join(tmpdir(), 'saber-pages-'));
    await cp(join(root, 'web'), join(directory, 'gpt-blender-site'), { recursive: true });
    server = httpServer.createServer({ root: directory, cache: -1, showDir: false });
    await new Promise((resolve, reject) => {
      server.server.once('error', reject);
      server.listen(0, '127.0.0.1', resolve);
    });
    base = `http://127.0.0.1:${server.server.address().port}/gpt-blender-site/`;
  }
  const url = new URL('saber/', base).href;
  browser = await chromium.launch({
    headless: true,
    ...(process.env.CHROME_BIN ? { executablePath: process.env.CHROME_BIN } : {}),
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 });
  const errors = [], requests = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('response', r => { if (r.status() >= 400) errors.push(`${r.status()} ${r.url()}`); });
  page.on('request', r => { if (r.url().startsWith('http')) requests.push(r.url()); });
  await page.goto(url);
  await page.waitForFunction(() => window.saber?.ready, null, { timeout: 90000 });
  const state = () => page.evaluate(() => window.saber.state());
  const snapshot = async name => {
    await page.waitForTimeout(300);
    await page.screenshot({ path: join(renders, `${name}.png`), fullPage: true });
  };
  assert.equal(await page.locator('video, a[href$=".mp4"]').count(), 0);
  await page.waitForFunction(() => window.saber.state().elapsed > .2);
  await page.getByRole('button', { name: '暂停动作', exact: true }).click();
  await page.evaluate(() => window.saber.seek(0));
  const idle = await state();
  assert.equal(idle.expression, 0, 'Idle must use the closed-mouth portrait');
  assert.ok(idle.skinned > 0 && idle.clips > 0, 'Blender skin and animation data must load');
  assert.ok(idle.triangles > 50000 && idle.triangles < 250000, 'Figure geometry must remain within the render budget');
  assert.equal(idle.gemSize.length, 3, 'Inspect the actual exported guard jewel');
  assert.ok(Math.max(...idle.gemSize) < .2, 'The guard jewel must keep its small sculpted size');
  await snapshot('browser-desktop');
  const loadedRequests = requests.length;

  await page.evaluate(() => window.saber.seek(2.458333));
  assert.ok((await state()).blink > .8, 'Baked eye shape keys must blink');
  await page.evaluate(() => window.saber.seek(0));
  assert.equal((await state()).blink, 0);

  await page.getByRole('button', { name: '抬剑致意' }).click();
  await page.waitForFunction(() => window.saber.state().elapsed > 1);
  assert.equal((await state()).mode, 'salute');
  assert.ok(differs(idle.hand, (await state()).hand, .1), 'Playing the clip must move the actual hand bone');
  await page.getByRole('button', { name: '暂停动作', exact: true }).click();
  await page.evaluate(() => { window.saber.seek(2.5); window.saber.setView('full', true); });
  const salute = await state();
  assert.ok(differs(idle.swordRotation, salute.swordRotation, .2), 'Salute must rotate the real sword');
  await snapshot('browser-salute');
  await page.waitForTimeout(250);
  assert.deepEqual((await state()).hand, salute.hand, 'Paused bones must hold their pose');
  assert.equal((await state()).elapsed, salute.elapsed);

  await page.getByRole('button', { name: '唤醒圣剑' }).click();
  await page.evaluate(() => { window.saber.pause(); window.saber.seek(2.2); window.saber.setView('full', true); });
  await snapshot('browser-raised');
  const raised = await state();
  assert.equal(raised.mode, 'excalibur');
  assert.ok(raised.expression > .95, 'The battle expression must follow the exported sword animation');
  assert.ok(raised.energy > .8, 'Awakening must light the sword');
  const frozen = await page.locator('canvas').evaluate(canvas => canvas.toDataURL());
  await page.waitForTimeout(200);
  assert.ok(await page.locator('canvas').evaluate(canvas => canvas.toDataURL()) === frozen, 'Pause must also freeze the particles and glow');
  await page.evaluate(() => window.saber.seek(3.1));
  assert.ok(differs(raised.swordRotation, (await state()).swordRotation, .5), 'The sword must sweep down after the raised pose');
  await snapshot('browser-action');
  await page.evaluate(() => window.saber.setView('face', true));
  await snapshot('browser-expression');
  await page.evaluate(() => window.saber.setView('full', true));
  await page.evaluate(() => window.saber.seek(5.85));
  await page.getByRole('button', { name: '继续动作', exact: true }).click();
  await page.waitForFunction(() => window.saber.state().mode === 'idle');
  assert.equal((await state()).expression, 0, 'Returning to idle must restore the calm portrait');

  await page.getByRole('button', { name: '重置展柜', exact: true }).click();
  await page.evaluate(() => { window.saber.pause(); window.saber.seek(0); window.saber.setView('full', true); });
  const before = (await state()).camera;
  const box = await page.locator('canvas').boundingBox();
  await page.mouse.move(box.x + box.width * .5, box.y + box.height * .5);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * .64, box.y + box.height * .55, { steps: 15 });
  await page.mouse.up();
  await page.waitForTimeout(300);
  assert.ok(differs(before, (await state()).camera, .5), 'Dragging must orbit the camera');
  await page.getByRole('button', { name: '自动旋转' }).click();
  const rotating = (await state()).camera;
  await page.waitForTimeout(400);
  assert.equal((await state()).autoRotate, true);
  assert.ok(differs(rotating, (await state()).camera, .05));
  await page.locator('[data-view="face"]').click();
  await page.waitForTimeout(1100);
  assert.equal((await state()).autoRotate, false);
  assert.equal((await state()).view, 'face');
  await snapshot('browser-face');
  await page.locator('[data-view="back"]').click();
  await page.waitForTimeout(1100);
  assert.ok((await state()).camera[2] < -10);
  await snapshot('browser-back');
  await page.locator('[data-view="sword"]').click();
  await page.waitForTimeout(1100);
  assert.equal((await state()).view, 'sword');
  await page.locator('button[data-light="night"]').click();
  assert.equal((await state()).light, 'night');
  await page.getByRole('button', { name: '白模欣赏' }).click();
  assert.equal((await state()).resin, true);
  await snapshot('browser-resin');
  await page.locator('button[data-light="warm"]').click();
  assert.equal((await state()).light, 'warm');
  await page.getByRole('button', { name: '重置展柜', exact: true }).click();
  const reset = await state();
  assert.equal(reset.resin, false);
  assert.equal(reset.autoRotate, false);
  assert.equal(reset.light, 'day');
  assert.equal(reset.mode, 'idle');

  const downloadEvent = page.waitForEvent('download');
  await page.getByRole('button', { name: '保存手办截图', exact: true }).click();
  const download = await downloadEvent;
  assert.equal(download.suggestedFilename(), 'saber-figure.png');
  const screenshotFile = join(renders, 'download.png');
  await download.saveAs(screenshotFile);
  const png = await readFile(screenshotFile);
  assert.ok(png.length > 10000);
  assert.equal(png.subarray(1, 4).toString(), 'PNG');
  await page.getByRole('button', { name: '关于这件作品' }).click();
  assert.equal(await page.locator('dialog').evaluate(d => d.open), true);
  await page.keyboard.press('Escape');
  assert.equal(await page.locator('dialog').evaluate(d => d.open), false);

  await page.setViewportSize({ width: 390, height: 844 });
  await page.evaluate(() => { window.saber.pause(); window.saber.seek(0); window.saber.setView('full', true); });
  await snapshot('browser-mobile');
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, 'Mobile must not overflow horizontally');
  await page.getByRole('button', { name: '唤醒圣剑' }).click();
  await page.evaluate(() => { window.saber.pause(); window.saber.seek(2.2); window.saber.setView('full', true); });
  await snapshot('browser-mobile-action');
  assert.equal(requests.length, loadedRequests, 'Interactions must not fetch additional models or call a backend');
  assert.ok(requests.every(r => new URL(r).origin === new URL(url).origin), 'Viewer assets must all be hosted locally');
  assert.equal(requests.some(r => /\.mp4|\.m4a|niulai\.glb/.test(r)), false, 'Saber must not load the other demo or media');
  assert.deepEqual(errors, []);

  const calm = await browser.newPage({ reducedMotion: 'reduce' });
  await calm.goto(url);
  await calm.waitForFunction(() => window.saber?.ready, null, { timeout: 90000 });
  assert.equal(await calm.evaluate(() => window.saber.state().playing), false, 'Respect reduced motion on first load');
  await calm.close();
  const result = {
    passed: true, url,
    checks: ['skinned GLB', 'jewel dimensions', 'blink shape keys', 'battle expression and return to calm', 'moving hand and sword bones', 'pause freezes pose and effects', 'swing and return to idle', 'drag and auto orbit', 'camera presets', 'lighting and resin', 'reset', 'PNG download', 'dialog', 'mobile layout', 'no extra interaction traffic', 'reduced motion', 'no page errors'],
    state: idle,
  };
  await writeFile(join(root, 'output/saber/verification.json'), JSON.stringify(result, null, 2));
  console.log(JSON.stringify(result));
} finally {
  await browser?.close();
  if (server) {
    server.server.closeAllConnections();
    await new Promise(resolve => server.server.close(resolve));
  }
  if (directory) await rm(directory, { recursive: true, force: true });
}
