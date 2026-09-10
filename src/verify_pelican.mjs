import { chromium } from '@playwright/test';
import assert from 'node:assert/strict';
import { cp, mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import httpServer from 'http-server';

const root = fileURLToPath(new URL('../', import.meta.url));
const renders = join(root, 'renders/pelican');
await mkdir(renders, { recursive: true });
await mkdir(join(root, 'output/pelican'), { recursive: true });
const differs = (a, b, tolerance = .01) => a.some((n, i) => Math.abs(n - b[i]) > tolerance);
const distance = (a, b) => Math.hypot(...a.map((n, i) => n - b[i]));
let browser, server, directory;

try {
  let base = process.env.PREVIEW_URL;
  if (!base) {
    directory = await mkdtemp(join(tmpdir(), 'pelican-pages-'));
    await cp(join(root, 'web'), join(directory, 'gpt-blender-site'), { recursive: true });
    server = httpServer.createServer({ root: directory, cache: -1, showDir: false });
    await new Promise((resolve, reject) => {
      server.server.once('error', reject);
      server.listen(0, '127.0.0.1', resolve);
    });
    base = `http://127.0.0.1:${server.server.address().port}/gpt-blender-site/`;
  }
  const url = new URL('pelican/', base).href;
  browser = await chromium.launch({ headless: true, ...(process.env.CHROME_BIN ? { executablePath: process.env.CHROME_BIN } : {}) });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 });
  const errors = [], requests = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('response', r => { if (r.status() >= 400) errors.push(`${r.status()} ${r.url()}`); });
  page.on('request', r => { if (r.url().startsWith('http')) requests.push(r.url()); });
  await page.goto(url);
  await page.waitForFunction(() => window.pelican?.ready, null, { timeout: 90000 });
  const state = () => page.evaluate(() => window.pelican.state());
  const snapshot = async name => {
    await page.waitForTimeout(350);
    await page.screenshot({ path: join(renders, `${name}.png`), fullPage: true });
  };
  await page.waitForFunction(() => window.pelican.state().elapsed > .2);
  await page.getByRole('button', { name: 'Pause ride', exact: true }).click();
  await page.evaluate(() => window.pelican.seek(0));
  const first = await state();
  assert.ok(first.clips > 0 && first.triangles > 25000 && first.triangles < 200000, 'Load an actual animated Blender model within the geometry budget');
  assert.ok(Math.abs(first.duration - 4) < .01, 'The authored loop lasts four seconds');
  assert.equal(await page.locator('video').count(), 0);
  await snapshot('browser-desktop');
  const loadedRequests = requests.length;

  // Sample the whole cycle, including both extrema, not just the opening pose.
  for (const t of [0, .125, .25, .5, .75, 1, 1.5, 2, 3.5, 3.999]) {
    await page.evaluate(t => window.pelican.seek(t), t);
    const pose = await state();
    assert.ok(distance(pose.leftFoot, pose.leftPedal) < .00001, `Left webbed foot stays on pedal at ${t}s`);
    assert.ok(distance(pose.rightFoot, pose.rightPedal) < .00001, `Right webbed foot stays on pedal at ${t}s`);
    const separation = distance([pose.leftPedal[0], pose.leftPedal[1]], [pose.rightPedal[0], pose.rightPedal[1]]);
    assert.ok(Math.abs(separation - .56) < .002, 'Opposite pedals preserve the crank diameter');
    assert.ok(Math.abs(pose.leftPedal[2] - .34) < .0001, 'The left foot remains outside the frame');
    assert.ok(Math.abs(pose.rightPedal[2] + .34) < .0001, 'The right foot remains outside the frame');
    assert.ok(pose.leftFoot[1] > .50 && pose.rightFoot[1] > .50, 'Pedals never enter the ground');
  }
  await page.evaluate(() => window.pelican.seek(.25));
  const quarter = await state();
  assert.ok(differs(first.wheel, quarter.wheel, .2), 'Both real wheels rotate');
  assert.ok(differs(first.rearWheel, quarter.rearWheel, .2));
  assert.ok(differs(first.crank, quarter.crank, .1), 'The crank is animated');
  const wheelAngle = 2 * Math.acos(Math.abs(quarter.wheel[3]));
  const crankAngle = 2 * Math.acos(Math.abs(quarter.crank[3]));
  assert.ok(Math.abs(wheelAngle - 2 * crankAngle) < .001, 'The bicycle keeps its 2:1 gear ratio');
  assert.ok(differs(first.knee, quarter.knee, .04), 'Leg joints bend with the pedal');
  assert.ok(differs(first.head, quarter.head, .002), 'Authored head movement is present');
  await page.evaluate(() => window.pelican.seek(4));
  assert.ok(distance((await state()).leftFoot, first.leftFoot) < .0001, 'The cycle repeats without a foot jump');
  await page.evaluate(() => window.pelican.seek(.75));
  await page.waitForTimeout(500);
  const paused = await state();
  const frozen = await page.locator('canvas').evaluate(canvas => canvas.toDataURL());
  await page.waitForTimeout(250);
  assert.equal((await state()).elapsed, paused.elapsed);
  assert.deepEqual((await state()).leftFoot, paused.leftFoot);
  assert.equal(await page.locator('canvas').evaluate(canvas => canvas.toDataURL()), frozen, 'Pause freezes model, scarf, and passing road marks');

  const changeSpeed = value => page.locator('#speed').evaluate((el, value) => { el.value = value; el.dispatchEvent(new Event('input', { bubbles: true })); }, value);
  await changeSpeed('0.5');
  await page.getByRole('button', { name: 'Resume ride', exact: true }).click();
  const slowStart = (await state()).elapsed;
  await page.waitForTimeout(700);
  const slowDelta = (await state()).elapsed - slowStart;
  await changeSpeed('2');
  assert.equal((await state()).speed, 2);
  assert.equal(await page.locator('#speedValue').textContent(), '2.0×');
  const fastStart = (await state()).elapsed;
  await page.waitForTimeout(700);
  assert.ok((await state()).elapsed - fastStart > slowDelta * 2, 'Speed changes the actual animation clock');
  await page.getByRole('button', { name: 'Pause ride', exact: true }).click();

  await page.locator('[data-view="side"]').click();
  await page.waitForTimeout(1100);
  assert.equal((await state()).view, 'side');
  assert.ok(Math.abs((await state()).camera[0]) < .001);
  await snapshot('browser-side');
  await page.locator('[data-view="face"]').click();
  await page.waitForTimeout(1100);
  assert.equal((await state()).view, 'face');
  await snapshot('browser-face');
  await page.locator('[data-view="ride"]').click();
  await page.waitForTimeout(1100);
  const beforeDrag = (await state()).camera;
  const box = await page.locator('canvas').boundingBox();
  await page.mouse.move(box.x + box.width * .5, box.y + box.height * .45);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * .67, box.y + box.height * .50, { steps: 15 });
  await page.mouse.up();
  await page.waitForTimeout(400);
  assert.ok(differs(beforeDrag, (await state()).camera, .5), 'Pointer dragging rotates the camera');
  const zoom = (await state()).zoom;
  await page.mouse.wheel(0, -220);
  await page.waitForTimeout(350);
  assert.ok((await state()).zoom > zoom, 'Wheel input zooms the model');
  await page.getByRole('button', { name: 'Auto orbit', exact: true }).click();
  const orbit = (await state()).camera;
  await page.waitForTimeout(500);
  assert.ok(differs(orbit, (await state()).camera, .05), 'Auto orbit moves the real camera even while the ride is paused');
  await page.locator('[data-view="ride"]').click();
  assert.equal((await state()).autoRotate, false);

  await page.getByRole('button', { name: 'Ring bell' }).click();
  await page.waitForFunction(() => window.pelican.state().audioState === 'running');
  assert.equal((await state()).bellCount, 1);
  await page.locator('canvas').focus();
  await page.keyboard.press('b');
  assert.equal((await state()).bellCount, 2);
  await page.keyboard.press('Space');
  assert.equal((await state()).playing, true);
  await page.keyboard.press('Space');
  assert.equal((await state()).playing, false);
  const downloadEvent = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Save photo', exact: true }).click();
  const download = await downloadEvent;
  assert.equal(download.suggestedFilename(), 'pelican-ride.png');
  const downloadPath = join(renders, 'download.png');
  await download.saveAs(downloadPath);
  const png = await readFile(downloadPath);
  assert.equal(png.subarray(1, 4).toString(), 'PNG');
  assert.ok(png.length > 20000);
  await page.getByRole('button', { name: 'Reset ride', exact: true }).click();
  assert.equal((await state()).speed, 1);
  assert.equal((await state()).view, 'ride');
  assert.equal((await state()).zoom, 1);
  assert.equal((await state()).autoRotate, false);
  assert.equal((await state()).playing, true);

  for (const width of [390, 320, 768]) {
    await page.setViewportSize({ width, height: 844 });
    await page.evaluate(() => { window.pelican.pause(); window.pelican.seek(.4); window.pelican.setView('ride', true); });
    await snapshot(`browser-${width}`);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, `No overflow at ${width}px`);
  }
  assert.equal(requests.length, loadedRequests, 'All interactions work without more network requests');
  assert.ok(requests.every(request => new URL(request).origin === new URL(url).origin), 'All model and library assets are local');
  assert.deepEqual(errors, []);

  const calm = await browser.newPage({ reducedMotion: 'reduce' });
  await calm.goto(url);
  await calm.waitForFunction(() => window.pelican?.ready, null, { timeout: 90000 });
  assert.equal(await calm.evaluate(() => window.pelican.state().playing), false);
  await calm.getByRole('button', { name: 'Reset ride', exact: true }).click();
  assert.equal(await calm.evaluate(() => window.pelican.state().playing), false, 'Reset also respects reduced motion');
  await calm.getByRole('button', { name: 'Resume ride', exact: true }).click();
  assert.equal(await calm.evaluate(() => window.pelican.state().playing), true, 'Reduced motion still allows an explicit start');
  await calm.close();

  const failed = await browser.newPage();
  await failed.route('**/pelican.glb', route => route.abort());
  await failed.goto(url);
  await failed.locator('#retry').waitFor({ state: 'visible' });
  assert.equal(await failed.locator('#pause').isDisabled(), true, 'A failed model leaves actions disabled and offers retry');
  await failed.close();
  const result = { passed: true, url, checks: ['animated Blender geometry', 'feet stay on level pedals across full cycle', '2:1 crank/wheel ratio', 'bending leg joints', 'continuous loop', 'pause freezes model and scenery', 'real playback speed', 'camera presets, drag and zoom', 'automatic orbit', 'local bell and keyboard controls', 'PNG download', 'reset', '390/320/768px layouts', 'no additional traffic', 'reduced motion', 'failed-model recovery', 'no browser errors'], state: first };
  await writeFile(join(root, 'output/pelican/verification.json'), JSON.stringify(result, null, 2));
  console.log(JSON.stringify(result));
} finally {
  await browser?.close();
  if (server) {
    server.server.closeAllConnections();
    await new Promise(resolve => server.server.close(resolve));
  }
  if (directory) await rm(directory, { recursive: true, force: true });
}
