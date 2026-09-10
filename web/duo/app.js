import * as THREE from 'three';
import { GLTFLoader } from '../vendor/GLTFLoader.js';
import { OrbitControls } from '../vendor/OrbitControls.js';

const $ = id => document.getElementById(id);
const canvas = $('scene');
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
let renderer;
try {
  renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, preserveDrawingBuffer: true });
} catch {
  $('loadingText').textContent = '3D is unavailable. Enable hardware acceleration and refresh.';
  throw new Error('WebGL unavailable');
}
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.AgXToneMapping;
renderer.toneMappingExposure = 1.08;
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(32, 1, .05, 100);
const controls = new OrbitControls(camera, canvas);
controls.enableDamping = true;
controls.dampingFactor = .09;
controls.enablePan = false;
controls.minDistance = 6;
controls.maxDistance = 23;
controls.minPolarAngle = .3;
controls.maxPolarAngle = Math.PI-.3;

// Large reflected softboxes reveal the actual bevels in the Blender geometry.
const studio = new THREE.Scene();
studio.background = new THREE.Color('#c1bfca');
for (const [at, size, color, power] of [
  [[-6, 6, 4], [4, 9, .1], '#ffffff', 3],
  [[6, 3, 0], [2, 10, .1], '#d9dafa', 2.8],
  [[0, 8, -4], [8, 3, .1], '#ffffff', 3.5],
  [[0, -5, 4], [7, 2, .1], '#c9bed9', .6],
]) {
  const mat = new THREE.MeshBasicMaterial({ color });
  mat.color.multiplyScalar(power);
  const panel = new THREE.Mesh(new THREE.BoxGeometry(...size), mat);
  panel.position.fromArray(at);
  panel.lookAt(0, 0, 0);
  studio.add(panel);
}
const pmrem = new THREE.PMREMGenerator(renderer);
const environment = pmrem.fromScene(studio, .05);
scene.environment = environment.texture;
scene.environmentIntensity = .8;
studio.traverse(o => { o.geometry?.dispose(); o.material?.dispose(); });
pmrem.dispose();
scene.add(new THREE.HemisphereLight('#f7f5ff', '#b0a6bd', 1.1));
for (const [at, color, power] of [[[-3, 6, 7], '#fff8f2', 3.5], [[5, 4, -4], '#cecfff', 4], [[0, -2, 6], '#ffffff', .8]]) {
  const light = new THREE.DirectionalLight(color, power);
  light.position.fromArray(at);
  scene.add(light);
}

// A soft studio contact shadow follows the width of the folding object.
const shadowCanvas = document.createElement('canvas');
shadowCanvas.width = shadowCanvas.height = 256;
const ctx = shadowCanvas.getContext('2d');
const gradient = ctx.createRadialGradient(128, 128, 8, 128, 128, 126);
gradient.addColorStop(0, '#4b39503b'); gradient.addColorStop(.45, '#6f587526'); gradient.addColorStop(1, '#6f587500');
ctx.fillStyle = gradient; ctx.fillRect(0, 0, 256, 256);
const shadow = new THREE.Mesh(new THREE.PlaneGeometry(8, 5), new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(shadowCanvas), transparent: true, depthWrite: false }));
shadow.rotation.x = -Math.PI/2;
shadow.position.y = -2.6;
scene.add(shadow);

function coverTexture() {
  const c = document.createElement('canvas'); c.width = 800; c.height = 1200;
  const g = c.getContext('2d');
  const bg = g.createLinearGradient(0, 0, 800, 1200);
  bg.addColorStop(0, '#242337'); bg.addColorStop(.5, '#635a83'); bg.addColorStop(1, '#bab5cf');
  g.fillStyle = bg; g.fillRect(0, 0, 800, 1200);
  for (let i=0; i<5; i++) {
    g.beginPath(); g.ellipse(650-i*105, 940+i*30, 280+i*25, 650, -.48, 0, Math.PI*2);
    g.strokeStyle = `rgba(232,222,255,${.08+i*.04})`; g.lineWidth = 28; g.stroke();
  }
  g.textAlign = 'center'; g.fillStyle = '#f8f5ff';
  g.font = '300 155px -apple-system, sans-serif'; g.fillText('9:41', 400, 325);
  g.font = '25px -apple-system, sans-serif'; g.fillText('Thursday, find the good', 400, 390);
  g.font = '22px -apple-system, sans-serif'; g.fillStyle = '#ffffffbb'; g.fillText('Unfold gently', 400, 1060);
  g.beginPath(); g.roundRect(280, 1150, 240, 9, 5); g.fillStyle = '#ffffffdd'; g.fill();
  const texture = new THREE.CanvasTexture(c); texture.colorSpace = THREE.SRGBColorSpace; texture.flipY = false;
  return texture;
}

let model, mixer, clipDuration=4, hinges=[], actions=[], ready=false, playing=!reducedMotion;
let fold = reducedMotion ? 1 : 0, elapsed=0, transition=null, view='hero', cameraTransition=null, last=performance.now(), toastTimer;
const geometry = { meshes: 0, triangles: 0, clips: 0 };
const ease = t => t*t*t*(t*(t*6-15)+10);
function cycle(t) {
  t %= 12;
  if (t<1.2) return 0;
  if (t<4.7) return ease((t-1.2)/3.5);
  if (t<7.5) return 1;
  if (t<11) return 1-ease((t-7.5)/3.5);
  return 0;
}
function updateUI() {
  const angle = Math.round(fold*180);
  $('angle').textContent = `${angle}°`;
  $('fold').value = fold*180;
  $('fold').style.setProperty('--progress',`${fold*100}%`);
  $('fold').setAttribute('aria-valuetext',`Open ${angle} degrees`);
  $('stateLabel').textContent = fold<.01 ? 'Closed · surprise inside' : fold>.99 ? 'Open · portrait revealed' : 'Between forms · every angle';
  $('play').setAttribute('aria-label',playing ? 'Pause demo' : 'Play demo');
  $('playIcon').setAttribute('d',playing ? 'M9 6v12M15 6v12' : 'M8 5l11 7-11 7Z');
  $('playLabel').textContent = playing ? 'Auto demo' : transition ? 'Folding' : 'Paused at your angle';
  $('reveal').querySelector('span').textContent = fold>.97 ? 'Close and reveal again' : 'Unfold surprise';
}
function applyFold(value) {
  fold = THREE.MathUtils.clamp(value, 0, 1);
  for (const action of actions) action.paused=false;
  mixer?.setTime(fold*clipDuration);
  shadow.scale.x = .55+fold*.45;
  updateUI();
}
function pause() { playing=false; transition=null; updateUI(); }
function moveFold(target) {
  if (!ready) return;
  playing=false;
  if (reducedMotion) { transition=null; applyFold(target); }
  else transition = { from:fold, to:target, time:0, duration:1.9*Math.max(.35,Math.abs(target-fold)) };
  updateUI();
}
function preset(name) {
  const narrow = canvas.clientWidth<500;
  const scale = narrow ? 1.08 : 1;
  const positions = { hero: [.8, 2.9, 12.6], front: [0, .05, 13], back: [-.8, 2.2, -12.8] };
  return new THREE.Vector3(...positions[name]).multiplyScalar(scale);
}
function setView(name, instant=false) {
  if (!['hero','front','back'].includes(name)) return;
  view=name;
  if (instant || reducedMotion) { camera.position.copy(preset(name)); cameraTransition=null; controls.target.set(0,-.05,0); controls.update(); }
  else cameraTransition = { from:camera.position.clone(), to:preset(name), time:0 };
  document.querySelectorAll('[data-view]').forEach(b => { b.classList.toggle('selected',b.dataset.view===name); b.setAttribute('aria-pressed',String(b.dataset.view===name)); });
}
function resize() {
  const {width,height} = $('viewer').getBoundingClientRect();
  renderer.setSize(width,height,false);
  camera.aspect=width/height;
  camera.updateProjectionMatrix();
  setView(view,true);
}
new ResizeObserver(resize).observe($('viewer'));
resize();
controls.addEventListener('start',()=>{cameraTransition=null;});
$('fold').addEventListener('input',e=>{const value=Number(e.target.value)/180;pause();applyFold(value);});
$('close').onclick=()=>moveFold(0);
$('open').onclick=()=>moveFold(1);
$('reveal').onclick=()=>{setView('hero');moveFold(fold>.97?0:1);};
$('play').onclick=()=>{
  if (playing) pause();
  else {
    // Resume at the matching point on the opening branch without jumping.
    let lo=0,hi=1;
    for(let i=0;i<24;i++){const mid=(lo+hi)/2;if(ease(mid)<fold)lo=mid;else hi=mid;}
    elapsed=fold>.999?4.7:1.2+(lo+hi)/2*3.5;
    playing=true;transition=null;updateUI();
  }
};
$('reset').onclick=()=>{elapsed=0;transition=null;playing=!reducedMotion;applyFold(reducedMotion?1:0);setView('hero');};
document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>setView(b.dataset.view));
$('capture').onclick=()=>{
  renderer.render(scene,camera);
  // Include the studio background in the saved PNG.
  const saved=document.createElement('canvas');saved.width=canvas.width;saved.height=canvas.height;
  const c=saved.getContext('2d');c.fillStyle='#f5f4f7';c.fillRect(0,0,saved.width,saved.height);c.drawImage(canvas,0,0);
  saved.toBlob(blob=>{if(!blob)return;const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='apple-duo.png';a.click();setTimeout(()=>URL.revokeObjectURL(url),3000);$('toast').textContent='Moment saved.';$('toast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').hidden=true,2300);});
};

new GLTFLoader().load('./assets/duo.glb',gltf=>{
  model=gltf.scene;scene.add(model);geometry.clips=gltf.animations.length;
  model.traverse(obj=>{
    if (obj.name==='Hinge_Left'||obj.name==='Hinge_Right') hinges.push(obj);
    if (!obj.isMesh) return;
    geometry.meshes++;
    geometry.triangles+=(obj.geometry.index?.count||obj.geometry.attributes.position.count)/3;
    if (obj.material.name==='Inner portrait OLED') {
      const map=obj.material.emissiveMap;
      map.anisotropy=renderer.capabilities.getMaxAnisotropy();
      obj.material=new THREE.MeshBasicMaterial({map,side:THREE.FrontSide,toneMapped:false});
    } else if(obj.name==='Cover_Display') {
      obj.material=new THREE.MeshBasicMaterial({map:coverTexture(),side:THREE.FrontSide,toneMapped:false});
    } else obj.material.envMapIntensity=/Sapphire|Obsidian|Lens/.test(obj.material.name)?.18:.9;
  });
  if(hinges.length!==2||!gltf.animations.length)throw new Error('Missing Blender hinge animation');
  mixer=new THREE.AnimationMixer(model);
  const origin=Math.min(...gltf.animations.flatMap(c=>c.tracks.map(t=>t.times[0])));
  for(const clip of gltf.animations){
    for(const track of clip.tracks)track.times=track.times.map(t=>t-origin);
    clip.resetDuration();clipDuration=clip.duration;
    const action=mixer.clipAction(clip);action.setLoop(THREE.LoopOnce,1);action.clampWhenFinished=true;action.play();actions.push(action);
  }
  ready=true;applyFold(fold);$('loading').hidden=true;
  document.querySelectorAll('button[disabled],input[disabled]').forEach(b=>b.disabled=false);
},undefined,error=>{
  console.error(error);$('loadingText').textContent='Model failed to load. Refresh to try again.';
});

window.duo={
  get ready(){return ready;},
  pause,
  seek(value){pause();applyFold(value);},
  setView,
  state(){return{ready,playing,fold,elapsed,view,camera:camera.position.toArray(),hinges:hinges.map(h=>h.quaternion.toArray()),...geometry};},
};
function animate(now){
  requestAnimationFrame(animate);
  const dt=Math.min((now-last)/1000,.05);last=now;
  if(document.hidden)return;
  if(ready&&playing){elapsed+=dt;applyFold(cycle(elapsed));}
  if(ready&&transition){transition.time+=dt;const t=Math.min(transition.time/transition.duration,1);applyFold(THREE.MathUtils.lerp(transition.from,transition.to,ease(t)));if(t===1){transition=null;updateUI();}}
  if(cameraTransition){
    cameraTransition.time+=dt;const t=Math.min(cameraTransition.time/1.1,1);
    // Orbit along a spherical arc so front-to-back never passes through the device.
    const a=new THREE.Spherical().setFromVector3(cameraTransition.from);
    const b=new THREE.Spherical().setFromVector3(cameraTransition.to);
    let delta=b.theta-a.theta;delta=Math.atan2(Math.sin(delta),Math.cos(delta));
    const s=ease(t);camera.position.setFromSpherical(new THREE.Spherical(THREE.MathUtils.lerp(a.radius,b.radius,s),THREE.MathUtils.lerp(a.phi,b.phi,s),a.theta+delta*s));
    if(t===1)cameraTransition=null;
  }
  controls.update();renderer.render(scene,camera);
}
requestAnimationFrame(animate);
