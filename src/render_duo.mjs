// Deterministic 12-second film of the Blender GLB in the web studio.
import { chromium } from '@playwright/test';
import { existsSync } from 'node:fs';
import { mkdir } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { fileURLToPath } from 'node:url';
import { join } from 'node:path';
import httpServer from 'http-server';

const root=fileURLToPath(new URL('../',import.meta.url));
await mkdir(join(root,'output/duo'),{recursive:true});
const server=httpServer.createServer({root:join(root,'web'),cache:-1,showDir:false});
let browser,encoder;
try {
  await new Promise((resolve,reject)=>{server.server.once('error',reject);server.listen(0,'127.0.0.1',resolve);});
  const chrome=process.env.CHROME_BIN||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
  browser=await chromium.launch({headless:true,...(existsSync(chrome)?{executablePath:chrome}:{})});
  const page=await browser.newPage({viewport:{width:1080,height:1080},deviceScaleFactor:1,reducedMotion:'reduce'});
  await page.goto(`http://127.0.0.1:${server.server.address().port}/duo/`);
  await page.waitForFunction(()=>window.duo?.ready,null,{timeout:60000});
  await page.addStyleTag({content:`
    .site-header,.intro,.controls,footer,.view-top,.view-bottom{display:none!important}
    main{max-width:none}.hero{display:block;padding:0;height:100vh;min-height:0}
    .viewer{width:100%;height:100vh;margin:0}.backdrop-word{font-size:650px;left:48%}
    .film-title{position:fixed;top:70px;left:78px;z-index:9;font-size:31px;font-weight:550;letter-spacing:-.04em}
    .film-title small{display:block;margin-top:12px;font-size:13px;color:#9587a4;letter-spacing:.18em;font-weight:400}
    .film-caption{position:fixed;bottom:65px;width:100%;text-align:center;color:#8d7c9e;font-size:14px;letter-spacing:.12em;z-index:9}
  `});
  await page.evaluate(()=>{
    const title=document.createElement('div');title.className='film-title';title.innerHTML='Apple Duo<small>Closed, imagine. Open, feel it.</small>';document.body.append(title);
    const caption=document.createElement('div');caption.className='film-caption';caption.textContent='Every angle reveals something new.';document.body.append(caption);
    window.duo.setView('hero',true);
  });
  await page.waitForTimeout(150);
  const output=join(root,'output/duo/duo-reveal.mp4');
  encoder=spawn('ffmpeg',['-y','-loglevel','error','-f','image2pipe','-vcodec','mjpeg','-r','24','-i','pipe:0','-an','-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',output],{stdio:['pipe','ignore','inherit']});
  const completion=once(encoder,'close');
  const ease=t=>t*t*t*(t*(t*6-15)+10);
  for(let i=0;i<288;i++){
    const t=i/24;
    const fold=t<1.2?0:t<4.7?ease((t-1.2)/3.5):t<7.5?1:t<11?1-ease((t-7.5)/3.5):0;
    await page.evaluate(f=>{window.duo.seek(f);return new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));},fold);
    const frame=await page.screenshot({type:'jpeg',quality:95});
    if(!encoder.stdin.write(frame))await once(encoder.stdin,'drain');
    if(i%48===0)console.log(`Duo film: ${i}/288 frames`);
  }
  encoder.stdin.end();
  const [code]=await completion;
  if(code!==0)throw new Error(`FFmpeg exited with ${code}`);
  console.log(`Duo film complete: ${output}`);
} finally {
  if(encoder&&encoder.exitCode===null)encoder.kill('SIGTERM');
  await browser?.close();
  server.server.closeAllConnections();await new Promise(resolve=>server.server.close(resolve));
}
