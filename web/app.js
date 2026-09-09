import * as THREE from 'three';
import { OrbitControls } from './vendor/OrbitControls.js';
import { GLTFLoader } from './vendor/GLTFLoader.js';

const $ = (id) => document.getElementById(id);
const canvas = $('scene');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.AgXToneMapping;
renderer.toneMappingExposure = 1.35;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
const scene = new THREE.Scene();
scene.background = new THREE.Color('#b7cbd2');
scene.fog = new THREE.Fog('#b7cbd2', 22, 65);
const camera = new THREE.PerspectiveCamera(40, 1, .08, 120);
const controls = new OrbitControls(camera, canvas);
controls.enableDamping = true;
controls.dampingFactor = .08;
controls.minDistance = 2.5;
controls.maxDistance = 22;
controls.maxPolarAngle = Math.PI * .49;
controls.target.set(0, 2, 0);
const hemi = new THREE.HemisphereLight('#e7f0f1', '#666342', 2.3);
scene.add(hemi);
const sun = new THREE.DirectionalLight('#fff0d7', 3.4);
sun.position.set(-3, 8, 5);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
Object.assign(sun.shadow.camera, { left: -8, right: 8, top: 8, bottom: -8, near: .5, far: 30 });
sun.shadow.bias = -.0003;
sun.shadow.normalBias = .025;
scene.add(sun);
const rim = new THREE.DirectionalLight('#ffd18d', 1.4);
rim.position.set(4, 6, -3);
scene.add(rim);

let mixer, cameras, duration = 14, time = 0, playing = false, free = false, sound = false, ready = false;
let last = performance.now();
const audio = $('dialogue');

function resize() {
  const { width, height } = canvas.parentElement.getBoundingClientRect();
  renderer.setSize(width, height, false);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
}
new ResizeObserver(resize).observe(canvas.parentElement);

function setCamera(t) {
  if (!cameras || free) return;
  const f = cameras.frames[Math.min(cameras.frames.length - 1, Math.floor(t * cameras.fps))];
  camera.position.fromArray(f.position);
  controls.target.fromArray(f.target);
  // Blender's square camera is matched vertically; wide viewers retain headroom.
  camera.fov = camera.aspect < 1 ? f.fov / camera.aspect : f.fov;
  camera.updateProjectionMatrix();
  camera.lookAt(controls.target);
}

function syncAudio(force = false) {
  if (!sound || !playing) { audio.pause(); return; }
  let target = time;
  if (time > 12.25) target = .4 + time - 12.25;
  if ((time >= 5.9 && time <= 12.25) || target >= 5.9) { audio.pause(); return; }
  if (force || Math.abs(audio.currentTime - target) > .16) audio.currentTime = target;
  if (audio.paused) audio.play().catch(() => {
    sound = false;
    $('sound').classList.remove('active');
    $('sound').setAttribute('aria-label', '开启原片声音');
  });
}

function updateUI() {
  $('timeline').value = time;
  $('time').textContent = `00:${String(Math.floor(time)).padStart(2, '0')} / 00:14`;
  $('play').textContent = playing ? 'Ⅱ' : '▶';
  $('play').setAttribute('aria-label', playing ? '暂停动画' : '播放动画');
  const mama = (time > .32 && time < 3.26) || time > 12.35;
  const reply = time > 4.6 && time < 5.55;
  $('subtitle').hidden = !(mama || reply);
  $('subtitle').querySelector('strong').textContent = mama ? '妈妈——！' : '牛来！';
  $('subtitle').querySelector('span').textContent = mama ? 'MAMA!' : 'NIU LAI!';
  $('hint').textContent = free ? '拖动旋转 · 滚轮缩放' : time > 5.65 && time < 11.2 ? '是真的 3D。现在，你也可以转动镜头。' : '拖动画面，看看牛的背后。';
  document.body.classList.toggle('playing', playing || time > .1);
  document.body.classList.toggle('free', free);
}

function setTime(t) {
  time = Math.max(0, Math.min(duration - .001, t));
  mixer?.setTime(time);
  setCamera(time);
  updateUI();
}

function togglePlaying(next = !playing) {
  if (!ready) return;
  playing = next;
  if (playing && time >= duration - .05) setTime(0);
  $('startOverlay').hidden = true;
  syncAudio(true);
  updateUI();
}

function freeCamera(next) {
  free = next;
  if (free) $('startOverlay').hidden = true;
  $('modeLabel').textContent = free ? '自由视角' : '导演视角';
  $('camera').textContent = free ? '回到导演视角' : '自由视角';
  if (!free) setCamera(time);
  updateUI();
}

$('play').onclick = () => togglePlaying();
$('start').onclick = () => { sound = true; $('sound').classList.add('active'); $('sound').setAttribute('aria-label','关闭原片声音'); togglePlaying(true); };
$('sound').onclick = () => {
  sound = !sound;
  $('sound').classList.toggle('active', sound);
  $('sound').setAttribute('aria-label', sound ? '关闭原片声音' : '开启原片声音');
  syncAudio(true);
};
$('timeline').oninput = (event) => { setTime(Number(event.target.value)); syncAudio(true); };
$('reset').onclick = () => { freeCamera(false); setTime(0); togglePlaying(true); };
$('mama').onclick = () => { setTime(.28); togglePlaying(true); };
$('camera').onclick = () => freeCamera(!free);
controls.addEventListener('start', () => { if (ready) freeCamera(true); });
document.addEventListener('keydown', (event) => {
  if (event.code === 'Space' && !['BUTTON', 'INPUT', 'A'].includes(document.activeElement.tagName)) {
    event.preventDefault(); togglePlaying();
  }
});
document.addEventListener('visibilitychange', () => { if (document.hidden) togglePlaying(false); });

try {
  const [gltf, data] = await Promise.all([
    new GLTFLoader().loadAsync('./assets/niulai.glb'),
    fetch('./assets/cameras.json').then((r) => { if (!r.ok) throw new Error('镜头文件加载失败'); return r.json(); }),
  ]);
  cameras = data;
  duration = data.duration;
  gltf.scene.traverse((obj) => {
    if (!obj.isMesh) return;
    obj.castShadow = true;
    obj.receiveShadow = true;
    if (obj.name.includes('blades')) obj.material.side = THREE.DoubleSide;
  });
  scene.add(gltf.scene);
  mixer = new THREE.AnimationMixer(gltf.scene);
  for (const clip of gltf.animations) mixer.clipAction(clip).play();
  ready = true;
  for (const id of ['play', 'mama', 'camera', 'reset']) $(id).disabled = false;
  $('loading').hidden = true;
  $('startOverlay').hidden = false;
  resize();
  setTime(0);
  window.niulai = {
    ready: true,
    seek: setTime,
    play: () => togglePlaying(true),
    pause: () => togglePlaying(false),
    free: freeCamera,
    state: () => ({ time, playing, free, sound, duration, clips: gltf.animations.length, triangles: renderer.info.render.triangles, camera: camera.position.toArray() }),
  };
} catch (error) {
  $('loading').querySelector('p').textContent = `场景暂时没有加载成功：${error.message}`;
  $('loading').querySelector('.loader').hidden = true;
  console.error(error);
}

function frame(now) {
  const delta = Math.min((now - last) / 1000, .08);
  last = now;
  if (ready && playing) {
    setTime(time + delta);
    if (time >= duration - .002) togglePlaying(false);
    else syncAudio();
  }
  if (free) controls.update();
  renderer.render(scene, camera);
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);
