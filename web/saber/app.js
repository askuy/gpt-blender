import * as THREE from 'three';
import { OrbitControls } from '../vendor/OrbitControls.js';
import { GLTFLoader } from '../vendor/GLTFLoader.js';

const $=id=>document.getElementById(id);
const canvas=$('scene');
const renderer=new THREE.WebGLRenderer({canvas,antialias:true,alpha:true,preserveDrawingBuffer:true});
renderer.setPixelRatio(Math.min(devicePixelRatio,1.75));
renderer.outputColorSpace=THREE.SRGBColorSpace;
renderer.toneMapping=THREE.AgXToneMapping;
renderer.toneMappingExposure=1.2;
renderer.shadowMap.enabled=true;
renderer.shadowMap.type=THREE.PCFSoftShadowMap;
const scene=new THREE.Scene();
const camera=new THREE.PerspectiveCamera(31,1,.05,100);
const controls=new OrbitControls(camera,canvas);
controls.enableDamping=true;
controls.dampingFactor=.075;
controls.enablePan=false;
controls.minDistance=1.25;
controls.maxDistance=18;
controls.minPolarAngle=.35;
controls.maxPolarAngle=Math.PI*.51;
controls.autoRotateSpeed=.7;
controls.target.set(0,2.85,0);
camera.position.set(6.3,4.5,11);

// Procedural studio reflections give the silver armor actual view-dependent highlights.
const studio=new THREE.Scene();
studio.background=new THREE.Color('#b6bfcb');
for(const [p,size,intensity,color] of [
  [[-4,5,3],[3,8,.1],3.5,'#fff4df'],
  [[4,4,-3],[3,7,.1],4,'#dbeaff'],
  [[0,8,0],[7,.1,6],2.5,'#ffffff'],
  [[0,2,6],[2,6,.1],1.6,'#ffffff'],
]){
  const m=new THREE.MeshBasicMaterial({color});m.color.multiplyScalar(intensity);
  const box=new THREE.Mesh(new THREE.BoxGeometry(...size),m);box.position.set(...p);box.lookAt(0,3,0);studio.add(box);
}
const pmrem=new THREE.PMREMGenerator(renderer);
const environment=pmrem.fromScene(studio,.06,.1,100);
scene.environment=environment.texture;
scene.environmentIntensity=.6;
studio.traverse(o=>{o.geometry?.dispose();o.material?.dispose();});pmrem.dispose();
const hemi=new THREE.HemisphereLight('#f8f6ec','#7b7985',2.1);scene.add(hemi);
const key=new THREE.DirectionalLight('#fff2dc',3.8);key.position.set(-3,12,5);key.castShadow=true;key.shadow.mapSize.set(2048,2048);
Object.assign(key.shadow.camera,{left:-4,right:4,top:7,bottom:-3,near:.1,far:25});key.shadow.bias=-.00015;key.shadow.normalBias=.015;key.target.position.set(0,2.6,0);scene.add(key,key.target);
const rim=new THREE.DirectionalLight('#c4d7ff',3);rim.position.set(4,5,-4);scene.add(rim);
const fill=new THREE.DirectionalLight('#ffffff',1.1);fill.position.set(0,4,8);scene.add(fill);
const floor=new THREE.Mesh(new THREE.PlaneGeometry(200,200),new THREE.ShadowMaterial({opacity:.065}));floor.rotation.x=-Math.PI/2;floor.position.y=.027;floor.receiveShadow=true;scene.add(floor);
const shadowCanvas=document.createElement('canvas');shadowCanvas.width=256;shadowCanvas.height=256;
const ctx=shadowCanvas.getContext('2d');const gradient=ctx.createRadialGradient(128,128,30,128,128,126);gradient.addColorStop(0,'rgba(12,20,28,.34)');gradient.addColorStop(.6,'rgba(12,20,28,.16)');gradient.addColorStop(1,'rgba(12,20,28,0)');ctx.fillStyle=gradient;ctx.fillRect(0,0,256,256);
const contact=new THREE.Mesh(new THREE.PlaneGeometry(4.6,4.6),new THREE.MeshBasicMaterial({map:new THREE.CanvasTexture(shadowCanvas),transparent:true,depthWrite:false}));contact.rotation.x=-Math.PI/2;contact.position.y=.029;scene.add(contact);

const energyGroup=new THREE.Group();scene.add(energyGroup);
const energyMaterial=new THREE.MeshBasicMaterial({color:'#ebca81',transparent:true,opacity:0,depthWrite:false,blending:THREE.AdditiveBlending});
for(const radius of [1.67,1.85]){const ring=new THREE.Mesh(new THREE.TorusGeometry(radius,.009,8,160),energyMaterial);ring.rotation.x=Math.PI/2;ring.position.y=.038;energyGroup.add(ring);}
const particleCount=150;const positions=new Float32Array(particleCount*3);const seeds=Array.from({length:particleCount},(_,i)=>({a:i*2.39996,r:.35+(Math.sin(i*19.4)*.5+.5)*1.8,h:(i*.618034)%1}));
const particleGeometry=new THREE.BufferGeometry();particleGeometry.setAttribute('position',new THREE.BufferAttribute(positions,3));
const particleCanvas=document.createElement('canvas');particleCanvas.width=32;particleCanvas.height=32;const pc=particleCanvas.getContext('2d');const pg=pc.createRadialGradient(16,16,0,16,16,16);pg.addColorStop(0,'#fff6d3');pg.addColorStop(.18,'#ffe7a7');pg.addColorStop(1,'#dca35b00');pc.fillStyle=pg;pc.fillRect(0,0,32,32);
const particleMaterial=new THREE.PointsMaterial({color:'#ffdc96',size:.075,map:new THREE.CanvasTexture(particleCanvas),transparent:true,opacity:0,depthWrite:false,blending:THREE.AdditiveBlending});
const particles=new THREE.Points(particleGeometry,particleMaterial);particles.frustumCulled=false;scene.add(particles);
const swordLight=new THREE.PointLight('#ffc870',0,8,2);scene.add(swordLight);

const reducedMotion=matchMedia('(prefers-reduced-motion: reduce)').matches;
let model,mixer,bone,swordBone,ready=false,playing=!reducedMotion,mode='idle',elapsed=0,energy=0,resin=false,last=performance.now(),view='full',transition=null,toastTimer;
const originalMaterials=new Map();const whiteResin=new THREE.MeshPhysicalMaterial({color:'#eee7d7',roughness:.44,metalness:0,clearcoat:.12});
const clips={idle:[0,3.96],salute:[4,9.96],excalibur:[10,15.92]};
const mobile=()=>canvas.clientWidth<700;
const presets={
  full:()=>{const active=mode==='excalibur';const position=mobile()?[7.0,4.45,13.6]:[6.3,4.5,11];return{position:position.map(n=>n*(active?1.23:1)),target:[active?.15:0,active?3.5:2.85,0]};},
  face:()=>({position:[1.55,5.03,3.1],target:[0,4.89,0]}),
  back:()=>({position:mobile()?[-6,4.5,-13.8]:[-5.6,4.25,-11],target:[0,2.90,0]}),
  sword:()=>({position:[2.8,3.4,5.6],target:[0,2.52,.45]}),
};
const notes={full:'盔甲的反光，也会跟着视角变化。',face:'金色发束、绿色眼睛，还有那一缕熟悉的呆毛。',back:'绕到背后，看看编织的发辫与层叠裙摆。',sword:'Excalibur。试着唤醒她手中的圣剑。'};
function setView(name,instant=false){
  view=name;const p=presets[name]();
  if(instant||reducedMotion){camera.position.fromArray(p.position);controls.target.fromArray(p.target);transition=null;}
  else transition={from:camera.position.clone(),targetFrom:controls.target.clone(),to:new THREE.Vector3(...p.position),targetTo:new THREE.Vector3(...p.target),time:0};
  controls.autoRotate=false;$('rotate').setAttribute('aria-pressed','false');
  document.querySelectorAll('[data-view]').forEach(b=>{b.classList.toggle('selected',b.dataset.view===name);b.setAttribute('aria-pressed',String(b.dataset.view===name));});
  $('detailNote').textContent=notes[name];
}
function resize(){const {width,height}=canvas.parentElement.getBoundingClientRect();renderer.setSize(width,height,false);camera.aspect=width/height;camera.updateProjectionMatrix();if(view==='full'&&!transition)setView('full',true);}
new ResizeObserver(resize).observe(canvas.parentElement);resize();setView('full',true);
function toast(text){clearTimeout(toastTimer);$('toast').textContent=text;$('toast').hidden=false;toastTimer=setTimeout(()=>$('toast').hidden=true,2400);}
function updateState(){
  $('pause').textContent=playing?'Ⅱ':'▶';$('pause').setAttribute('aria-label',playing?'暂停动作':'继续动作');
  $('stateLabel').textContent=!playing?'定格 · 这一瞬间':mode==='salute'?'骑士 · 抬剑致意':mode==='excalibur'?'圣剑 · 解放':'静候 · 待机';
  $('awaken').classList.toggle('active',mode==='excalibur');document.body.classList.toggle('awakened',mode==='excalibur');document.body.classList.toggle('paused',!playing);
}
function playMotion(next){if(!ready||!clips[next])return;mode=next;elapsed=0;playing=true;mixer.setTime(clips[mode][0]);if(mode!=='idle'||view==='full')setView('full');updateState();}
function reset(){playMotion('idle');setView('full');setLight('day');if(resin)toggleResin();}
function toggleResin(){
  if(!ready)return;resin=!resin;
  model.traverse(o=>{if(o.isMesh&&originalMaterials.has(o))o.material=resin?whiteResin:originalMaterials.get(o);});
  $('resin').setAttribute('aria-pressed',String(resin));
  toast(resin?'素色树脂，欣赏雕塑的形状。':'恢复原色涂装。');
}
function setLight(name){
  document.body.dataset.light=name;
  const options={day:{key:'#fff2dc',rim:'#c4d7ff',keyPower:3.8,rimPower:3,ambient:2.1,exposure:1.2},night:{key:'#c5dbff',rim:'#b4c7ff',keyPower:2.2,rimPower:4,ambient:.55,exposure:1.15},warm:{key:'#ffe0ac',rim:'#efc490',keyPower:3.5,rimPower:2.8,ambient:1.6,exposure:1.18}};
  const p=options[name];key.color.set(p.key);rim.color.set(p.rim);key.intensity=p.keyPower;rim.intensity=p.rimPower;hemi.intensity=p.ambient;renderer.toneMappingExposure=p.exposure;
  document.querySelectorAll('button[data-light]').forEach(b=>{b.classList.toggle('selected',b.dataset.light===name);b.setAttribute('aria-pressed',String(b.dataset.light===name));});
}
$('pause').onclick=()=>{playing=!playing;updateState();};
$('salute').onclick=()=>playMotion('salute');$('awaken').onclick=()=>playMotion('excalibur');
$('rotate').onclick=()=>{transition=null;controls.autoRotate=!controls.autoRotate;$('rotate').setAttribute('aria-pressed',String(controls.autoRotate));};
$('resin').onclick=toggleResin;$('reset').onclick=reset;
document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>setView(b.dataset.view));
document.querySelectorAll('button[data-light]').forEach(b=>b.onclick=()=>setLight(b.dataset.light));
controls.addEventListener('start',()=>{transition=null;controls.autoRotate=false;$('rotate').setAttribute('aria-pressed','false');});
$('capture').onclick=()=>{renderer.render(scene,camera);canvas.toBlob(blob=>{if(!blob)return;const link=document.createElement('a');link.href=URL.createObjectURL(blob);link.download='saber-figure.png';link.click();setTimeout(()=>URL.revokeObjectURL(link.href),3000);toast('已保存这一刻。');},'image/png');};
$('aboutOpen').onclick=()=>$('about').showModal();$('aboutClose').onclick=()=>$('about').close();$('about').addEventListener('click',e=>{if(e.target===$('about')){const r=$('about').getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)$('about').close();}});
document.addEventListener('keydown',e=>{if($('about').open||['BUTTON','INPUT','A'].includes(document.activeElement.tagName))return;if(e.code==='Space'&&ready){e.preventDefault();$('pause').click();}if(e.code==='KeyE'&&ready)$('awaken').click();});
document.addEventListener('visibilitychange',()=>{last=performance.now();});

try{
  const gltf=await new GLTFLoader().loadAsync('./assets/saber.glb',event=>{if(event.total)$('loadProgress').style.width=`${Math.min(98,event.loaded/event.total*100)}%`;});
  model=gltf.scene;scene.add(model);
  model.traverse(o=>{if(o.isMesh){o.castShadow=true;o.receiveShadow=true;originalMaterials.set(o,o.material);if(o.material){o.material.side=THREE.DoubleSide;o.material.envMapIntensity=.65;}}if(o.isBone&&o.name==='handR')bone=o;if(o.isBone&&o.name==='sword')swordBone=o;});
  if(!bone)model.traverse(o=>{if(o.isBone&&/hand.*R/i.test(o.name))bone=o;});
  mixer=new THREE.AnimationMixer(model);
  // Blender's scene starts at frame 1. Normalize every channel together so
  // second 0 in the controls matches the first authored pose, including blinks.
  const origin=Math.min(...gltf.animations.flatMap(clip=>clip.tracks.map(track=>track.times[0])));
  for(const clip of gltf.animations){for(const track of clip.tracks)track.times=track.times.map(time=>time-origin);clip.resetDuration();mixer.clipAction(clip).play();}
  mixer.setTime(0);ready=true;$('loading').hidden=true;document.querySelectorAll('button[disabled]').forEach(b=>b.disabled=false);updateState();
  const geometry={triangles:0,meshes:0,skinned:0,gemSize:[]};
  model.traverse(o=>{if(o.isMesh){geometry.meshes++;geometry.triangles+=(o.geometry.index?.count||o.geometry.attributes.position.count)/3;if(o.material?.name==='Deep jade'&&!o.morphTargetInfluences){o.geometry.computeBoundingBox();geometry.gemSize=o.geometry.boundingBox.getSize(new THREE.Vector3()).multiply(o.getWorldScale(new THREE.Vector3())).toArray();}}if(o.isSkinnedMesh)geometry.skinned++;});
  window.saber={ready:true,play:playMotion,pause:()=>{playing=false;updateState();},seek:t=>{const [start,end]=clips[mode];elapsed=THREE.MathUtils.clamp(t,0,end-start);mixer.setTime(start+elapsed);},setView,setLight,reset,state:()=>{const point=new THREE.Vector3();bone?.getWorldPosition(point);let blink=0;model.traverse(o=>{if(o.morphTargetDictionary?.Blink!==undefined)blink=Math.max(blink,o.morphTargetInfluences[o.morphTargetDictionary.Blink]);});return{ready,mode,elapsed,playing,resin,view,light:document.body.dataset.light,autoRotate:controls.autoRotate,clips:gltf.animations.length,...geometry,blink,energy,camera:camera.position.toArray(),hand:point.toArray(),swordRotation:swordBone?.getWorldQuaternion(new THREE.Quaternion()).toArray()};}};
}catch(error){console.error(error);$('loadingText').textContent='展柜暂时没有打开，请刷新页面重试。';$('loadProgress').style.width='0';}
function frame(now){
  requestAnimationFrame(frame);const dt=Math.min((now-last)/1000,.04);last=now;if(document.hidden)return;
  if(ready&&playing){elapsed+=dt;const [start,end]=clips[mode];if(elapsed>end-start){if(mode==='idle')elapsed%=end-start;else playMotion('idle');}mixer.setTime(clips[mode][0]+elapsed);}
  const targetEnergy=mode==='excalibur'?Math.pow(Math.sin(Math.PI*Math.min(elapsed/5.92,1)),.7):0;
  energy=targetEnergy;
  energyMaterial.opacity=energy*.75;particleMaterial.opacity=energy*.95;swordLight.intensity=energy*6;
  for(const [o,m] of originalMaterials){if(m.name?.includes('EXCALIBUR')){m.emissive.set('#eac272');m.emissiveIntensity=energy*2.5;}}
  if(bone)bone.getWorldPosition(swordLight.position);else swordLight.position.set(0,3.4,.6);
  const effectTime=(clips[mode][0]+elapsed)*1000;
  for(let i=0;i<particleCount;i++){const s=seeds[i];const a=s.a+effectTime*.00018;const r=s.r*(.8+.2*Math.sin(effectTime*.001+i));positions[i*3]=Math.cos(a)*r;positions[i*3+1]=((s.h+effectTime*.00006)%1)*6;positions[i*3+2]=Math.sin(a)*r;}
  particleGeometry.attributes.position.needsUpdate=true;
  if(transition){transition.time+=dt;const t=Math.min(transition.time/.9,1);const e=1-(1-t)**3;camera.position.lerpVectors(transition.from,transition.to,e);controls.target.lerpVectors(transition.targetFrom,transition.targetTo,e);if(t===1)transition=null;}
  controls.update();renderer.render(scene,camera);
}
requestAnimationFrame(frame);
