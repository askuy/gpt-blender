import { chromium } from '@playwright/test';
import assert from 'node:assert/strict';
import { cp, mkdir, mkdtemp, rm, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import httpServer from 'http-server';
const root = fileURLToPath(new URL('../', import.meta.url));
for (const folder of ['renders','output']) await mkdir(root+folder,{recursive:true});
let browser, server, siteDirectory;
try {
let base=process.env.PREVIEW_URL;
if (!base) {
// Match the /niulai-site/ subdirectory used by GitHub Pages.
siteDirectory=await mkdtemp(join(tmpdir(),'niulai-pages-'));
await cp(root+'web',join(siteDirectory,'niulai-site'),{recursive:true});
server=httpServer.createServer({root:siteDirectory,cache:-1,showDir:false});
await new Promise((resolve,reject)=>{
  server.server.once('error',reject);
  server.listen(0,'127.0.0.1',resolve);
});
base=`http://127.0.0.1:${server.server.address().port}/niulai-site/`;
}
for (const path of ['reference/movie-excerpt.mp4','output/niulai-twitter.mp4','package.json']) {
  const response=await fetch(new URL(path,base));
  await response.arrayBuffer();
  assert.equal(response.status,404,`${path} must not be published`);
}
browser = await chromium.launch({headless:true,...(process.env.CHROME_BIN?{executablePath:process.env.CHROME_BIN}:{})});
const errors=[];
const page=await browser.newPage({viewport:{width:1440,height:1100},deviceScaleFactor:1});
page.on('pageerror',e=>errors.push(e.message));
page.on('response',r=>{if(r.status()>=400)errors.push(`${r.status()} ${r.url()}`)});
await page.goto(base);
await page.waitForFunction(()=>window.niulai?.ready,null,{timeout:60000});
assert.equal(await page.locator('a[href*=".mp4"], video').count(),0,'Viewer must not include MP4 videos or links');
await page.screenshot({path:root+'renders/web-desktop.png',fullPage:true});
await page.getByRole('button',{name:'开始，声音开大一点'}).click();
await page.waitForFunction(()=>window.niulai.state().time>.5);
assert.equal(await page.evaluate(()=>document.getElementById('dialogue').paused),false,'Original audio should play after an explicit click');
await page.getByRole('button',{name:'暂停动画',exact:true}).click();
assert.equal(await page.evaluate(()=>window.niulai.state().playing),false);
assert.equal(await page.evaluate(()=>document.getElementById('dialogue').paused),true);
await page.locator('#timeline').evaluate(el=>{el.value='4.9';el.dispatchEvent(new Event('input',{bubbles:true}))});
assert.equal(await page.evaluate(()=>window.niulai.state().time),4.9);
assert.equal(await page.locator('#subtitle strong').textContent(),'牛来！');
await page.getByRole('button',{name:'自由视角',exact:true}).click();
assert.equal(await page.evaluate(()=>window.niulai.state().free),true);
const before=await page.evaluate(()=>window.niulai.state().camera);
const box=await page.locator('canvas').boundingBox();
await page.mouse.move(box.x+box.width*.5,box.y+box.height*.5);
await page.mouse.down();await page.mouse.move(box.x+box.width*.7,box.y+box.height*.56,{steps:15});await page.mouse.up();
await page.waitForTimeout(300);
const after=await page.evaluate(()=>window.niulai.state().camera);
assert.ok(before.some((n,i)=>Math.abs(n-after[i])>.2),'Dragging must rotate the actual camera');
await page.getByRole('button',{name:'再喊一声「妈妈」'}).click();
assert.equal(await page.evaluate(()=>window.niulai.state().playing),true);
assert.equal(await page.evaluate(()=>window.niulai.state().free),true,'Replay preserves the user’s free view');
await page.getByRole('button',{name:'重播',exact:true}).click();
assert.equal(await page.evaluate(()=>window.niulai.state().free),false);
await page.evaluate(()=>{window.niulai.pause();window.niulai.seek(8.5)});
await page.waitForTimeout(500);
await page.screenshot({path:root+'renders/web-orbit.png',fullPage:true});
await page.setViewportSize({width:390,height:844});
await page.evaluate(()=>window.niulai.seek(1.3));
await page.waitForTimeout(500);
assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'Mobile page must not overflow horizontally');
await page.screenshot({path:root+'renders/web-mobile.png',fullPage:true});
const state=await page.evaluate(()=>window.niulai.state());
assert.ok(state.triangles>50000,'Scene contains real mesh geometry');
assert.ok(state.clips>0,'Animation clips are present');
assert.deepEqual(errors,[]);
const result={passed:true,checks:['only viewer files are published','model loads','no MP4 videos or links','original audio plays after click','pause stops audio','timeline seeks','dialogue captions','actual camera orbit','replay from free camera','director reset','mobile layout','no page errors'],state};
await writeFile(root+'output/verification.json',JSON.stringify(result,null,2));
console.log(JSON.stringify(result));
} finally {
  await browser?.close();
  if (server) {
    server.server.closeAllConnections();
    await new Promise(resolve=>server.server.close(resolve));
  }
  if (siteDirectory) await rm(siteDirectory,{recursive:true,force:true});
}
