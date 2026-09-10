import * as THREE from 'three';
import { OrbitControls } from '../vendor/OrbitControls.js';
import { GLTFLoader } from '../vendor/GLTFLoader.js';

const $ = id => document.getElementById(id);
const motionPreference = matchMedia('(prefers-reduced-motion: reduce)');
let toastTimer;
function toast(message) {
  clearTimeout(toastTimer);
  $('toast').textContent = message;
  $('toast').hidden = false;
  toastTimer = setTimeout(() => { $('toast').hidden = true; }, 2500);
}
$('retry').onclick = () => location.reload();

async function start() {
  const canvas = $('scene');
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.75));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.AgXToneMapping;
  renderer.toneMappingExposure = 1.1;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFShadowMap;
  const scene = new THREE.Scene();
  scene.background = new THREE.Color('#f5f2e9');
  const camera = new THREE.OrthographicCamera(-5, 5, 3, -3, .1, 80);
  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true;
  controls.dampingFactor = .09;
  controls.enablePan = false;
  controls.minZoom = .65;
  controls.maxZoom = 3;
  controls.minPolarAngle = .32;
  controls.maxPolarAngle = Math.PI * .49;
  controls.autoRotateSpeed = .65;

  const studio = new THREE.Scene();
  studio.background = new THREE.Color('#b8c5bb');
  for (const [at, size, power, color] of [
    [[-4, 6, 3], [4, 7, .1], 3, '#fff6df'],
    [[4, 5, -3], [3, 7, .1], 3.5, '#e4f4f0'],
    [[0, 8, 0], [7, .1, 5], 2, '#ffffff'],
  ]) {
    const material = new THREE.MeshBasicMaterial({ color });
    material.color.multiplyScalar(power);
    const light = new THREE.Mesh(new THREE.BoxGeometry(...size), material);
    light.position.set(...at);
    light.lookAt(0, 2, 0);
    studio.add(light);
  }
  const pmrem = new THREE.PMREMGenerator(renderer);
  const environment = pmrem.fromScene(studio, .05, .1, 50);
  scene.environment = environment.texture;
  scene.environmentIntensity = .42;
  studio.traverse(object => { object.geometry?.dispose(); object.material?.dispose(); });
  pmrem.dispose();
  scene.add(new THREE.HemisphereLight('#fff7e6', '#a9b39c', 1.2));
  const key = new THREE.DirectionalLight('#fff1d7', 3.2);
  key.position.set(-3, 8, 5);
  key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048);
  Object.assign(key.shadow.camera, { left: -5, right: 5, top: 6, bottom: -4, near: .1, far: 25 });
  key.shadow.normalBias = .014;
  key.shadow.bias = -.00015;
  key.shadow.radius = 3;
  key.target.position.set(0, 1.6, 0);
  scene.add(key, key.target);
  const rim = new THREE.DirectionalLight('#e1f5f4', 2.1);
  rim.position.set(3, 6, -5);
  scene.add(rim);
  const fill = new THREE.DirectionalLight('#fff9ec', .7);
  fill.position.set(5, 3, 8);
  scene.add(fill);
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(100, 100), new THREE.ShadowMaterial({ opacity: .10 }));
  ground.rotation.x = -Math.PI / 2;
  ground.position.y = -.365;
  ground.receiveShadow = true;
  scene.add(ground);

  // A soft local contact shadow avoids a floating diorama at grazing angles.
  const shadowCanvas = document.createElement('canvas');
  shadowCanvas.width = shadowCanvas.height = 128;
  const ctx = shadowCanvas.getContext('2d');
  const gradient = ctx.createRadialGradient(64, 64, 5, 64, 64, 63);
  gradient.addColorStop(0, '#31473532');
  gradient.addColorStop(.60, '#3147351c');
  gradient.addColorStop(1, '#31473500');
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, 128, 128);
  const contact = new THREE.Mesh(new THREE.PlaneGeometry(8.8, 5.2), new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(shadowCanvas), transparent: true, depthWrite: false }));
  contact.rotation.x = -Math.PI / 2;
  contact.position.y = -.358;
  scene.add(contact);

  // Lane dashes pass under the bicycle at the tire's rolling speed (r = .72).
  const road = new THREE.InstancedMesh(new THREE.BoxGeometry(.30, .005, .033), new THREE.MeshStandardMaterial({ color: '#f5efdb', roughness: .8 }), 9);
  road.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  road.frustumCulled = false;
  scene.add(road);
  const dummy = new THREE.Object3D();
  let ready = false, playing = !motionPreference.matches, elapsed = 0, speed = 1;
  let view = 'ride', transition = null, viewHeight = 6.3, last = performance.now();
  let model, mixer, duration, contextLost = false;
  const small = () => window.innerWidth <= 640;
  const aspect = () => canvas.clientWidth / canvas.clientHeight;
  const presets = {
    ride: () => ({ position: [5.4, 5.1, 10], target: [0, 1.73, 0], height: small() ? 7.3 / aspect() : 6.3 }),
    side: () => ({ position: [0, 3.5, 12], target: [0, 1.82, 0], height: small() ? 7.3 / aspect() : 5.85 }),
    face: () => ({ position: [3.7, 4.6, 8], target: [.63, 3.36, 0], height: small() ? 3.1 / aspect() : 2.85 }),
  };
  function project(height = viewHeight) {
    viewHeight = height;
    camera.left = -height * aspect() / 2;
    camera.right = height * aspect() / 2;
    camera.top = height / 2;
    camera.bottom = -height / 2;
    camera.updateProjectionMatrix();
  }
  function stopOrbit() {
    controls.autoRotate = false;
    $('orbit').setAttribute('aria-pressed', 'false');
  }
  function setView(name, instant = false) {
    if (!presets[name]) return;
    const p = presets[name]();
    view = name;
    stopOrbit();
    camera.zoom = 1;
    if (instant || motionPreference.matches) {
      camera.position.fromArray(p.position);
      controls.target.fromArray(p.target);
      project(p.height);
      transition = null;
      controls.update();
    } else {
      transition = { from: camera.position.clone(), targetFrom: controls.target.clone(), to: new THREE.Vector3(...p.position), targetTo: new THREE.Vector3(...p.target), fromHeight: viewHeight, height: p.height, time: 0 };
    }
    document.querySelectorAll('[data-view]').forEach(button => {
      button.classList.toggle('selected', button.dataset.view === name);
      button.setAttribute('aria-pressed', String(button.dataset.view === name));
    });
  }
  let wasSmall = small();
  new ResizeObserver(() => {
    const { width, height } = $('sceneWrap').getBoundingClientRect();
    renderer.setSize(width, height, false);
    if (wasSmall !== small()) { wasSmall = small(); setView(view, true); }
    else project(small() ? presets[view]().height : viewHeight);
  }).observe($('sceneWrap'));
  renderer.setSize($('sceneWrap').clientWidth, $('sceneWrap').clientHeight, false);
  setView('ride', true);

  function updateState() {
    $('pause').setAttribute('aria-label', playing ? 'Pause ride' : 'Resume ride');
    $('pause').title = (playing ? 'Pause ride' : 'Resume ride') + ' (Space)';
    $('pause').querySelector('use').setAttribute('href', playing ? '#i-pause' : '#i-play');
    document.body.classList.toggle('paused', !playing);
  }
  function applyTime() {
    if (!ready) return;
    mixer.setTime(((elapsed % duration) + duration) % duration);
    model.updateMatrixWorld(true);
    const distance = elapsed * Math.PI * 2 * .72;
    for (let i = 0; i < road.count; i++) {
      const x = ((i * .75 - distance) % 6.75 + 6.75) % 6.75 - 3.375;
      const edge = THREE.MathUtils.smoothstep(3.2 - Math.abs(x), 0, .4);
      dummy.position.set(x, .088, .49);
      dummy.scale.set(edge, 1, edge);
      dummy.updateMatrix();
      road.setMatrixAt(i, dummy.matrix);
    }
    road.instanceMatrix.needsUpdate = true;
  }
  function pause() { playing = false; updateState(); }
  $('pause').onclick = () => { playing = !playing; updateState(); };
  $('speed').oninput = event => {
    speed = Number(event.target.value);
    $('speedValue').value = speed.toFixed(1) + '×';
    $('speed').setAttribute('aria-valuetext', speed.toFixed(1) + ' times speed');
    updateState();
  };
  $('orbit').onclick = () => {
    transition = null;
    controls.autoRotate = !controls.autoRotate;
    $('orbit').setAttribute('aria-pressed', String(controls.autoRotate));
  };
  controls.addEventListener('start', () => { transition = null; stopOrbit(); });
  document.querySelectorAll('[data-view]').forEach(button => { button.onclick = () => setView(button.dataset.view); });
  $('reset').onclick = () => {
    elapsed = 0;
    speed = 1;
    playing = !motionPreference.matches;
    $('speed').value = '1';
    $('speed').dispatchEvent(new Event('input'));
    setView('ride');
    applyTime();
  };

  let audioContext, bellCount = 0;
  $('bell').onclick = async () => {
    bellCount++;
    toast('Ring ring!');
    try {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (!AudioContext) return;
      audioContext ??= new AudioContext();
      await audioContext.resume();
      // Two short strikes, with inharmonic partials, make a quiet bicycle bell.
      for (const delay of [0, .16]) {
        for (const [frequency, gain] of [[1450, .11], [2180, .035], [3610, .012]]) {
          const oscillator = audioContext.createOscillator();
          const envelope = audioContext.createGain();
          const t = audioContext.currentTime + delay;
          oscillator.frequency.value = frequency;
          envelope.gain.setValueAtTime(0, t);
          envelope.gain.linearRampToValueAtTime(gain, t + .006);
          envelope.gain.exponentialRampToValueAtTime(.0001, t + .8);
          oscillator.connect(envelope).connect(audioContext.destination);
          oscillator.start(t);
          oscillator.stop(t + .85);
          oscillator.onended = () => { oscillator.disconnect(); envelope.disconnect(); };
        }
      }
    } catch { toast('Audio unavailable.'); }
  };
  $('capture').onclick = () => {
    renderer.render(scene, camera);
    canvas.toBlob(blob => {
      if (!blob) { toast('Could not save. Try again.'); return; }
      const link = document.createElement('a');
      const url = URL.createObjectURL(blob);
      link.href = url;
      link.download = 'pelican-ride.png';
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 3000);
      toast('Photo saved.');
    }, 'image/png');
  };
  document.addEventListener('keydown', event => {
    if (!ready || event.repeat || event.altKey || event.ctrlKey || event.metaKey || ['INPUT', 'BUTTON', 'A', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) return;
    if (event.code === 'Space') { event.preventDefault(); $('pause').click(); }
    if (event.code === 'KeyB') $('bell').click();
  });
  document.addEventListener('visibilitychange', () => { last = performance.now(); });
  motionPreference.addEventListener('change', event => { if (event.matches) { pause(); stopOrbit(); transition = null; } });
  canvas.addEventListener('webglcontextlost', event => {
    event.preventDefault();
    contextLost = true;
    pause();
    $('loading').hidden = false;
    $('loadingText').textContent = 'Display interrupted. Please reload.';
    $('retry').hidden = false;
    document.querySelectorAll('.ride-controls button, .ride-controls input, [data-view]').forEach(el => { el.disabled = true; });
  });

  const gltf = await new GLTFLoader().loadAsync('./assets/pelican.glb', event => {
    if (event.total) $('loadProgress').style.width = `${Math.min(98, event.loaded / event.total * 100)}%`;
  });
  model = gltf.scene;
  const geometry = { meshes: 0, triangles: 0 };
  model.traverse(object => {
    if (!object.isMesh) return;
    geometry.meshes++;
    geometry.triangles += (object.geometry.index?.count || object.geometry.attributes.position.count) / 3;
    object.castShadow = true;
    object.receiveShadow = true;
    if (object.material) object.material.envMapIntensity = .7;
    // Tiny eye details retain their painted finish instead of self-shadow speckling.
    if (['ink', 'white', 'eye_patch', 'blush', 'bill_seam'].includes(object.material?.name)) object.receiveShadow = false;
  });
  if (!gltf.animations.length) throw new Error('The pelican GLB has no authored animation.');
  scene.add(model);
  mixer = new THREE.AnimationMixer(model);
  const origin = Math.min(...gltf.animations.flatMap(clip => clip.tracks.map(track => track.times[0])));
  for (const clip of gltf.animations) {
    for (const track of clip.tracks) track.times = track.times.map(time => time - origin);
    clip.resetDuration();
    mixer.clipAction(clip).play();
  }
  duration = Math.max(...gltf.animations.map(clip => clip.duration));
  ready = true;
  $('loading').hidden = true;
  document.querySelectorAll('button[disabled], input[disabled]').forEach(el => { el.disabled = false; });
  updateState();
  applyTime();

  const node = name => model.getObjectByName(name);
  const position = name => node(name)?.getWorldPosition(new THREE.Vector3()).toArray();
  const rotation = name => node(name)?.getWorldQuaternion(new THREE.Quaternion()).toArray();
  // Read actual GLB transforms so automated checks exercise the exported animation.
  window.pelican = {
    ready: true, pause, setView,
    seek(time) { if (Number.isFinite(time) && time >= 0) { elapsed = time; applyTime(); } },
    state: () => ({
      playing, elapsed, speed, view, duration, autoRotate: controls.autoRotate,
      camera: camera.position.toArray(), target: controls.target.toArray(), zoom: camera.zoom,
      light: 'coastal-day', bellCount, audioState: audioContext?.state ?? 'uninitialized',
      wheel: rotation('Wheel_front'), rearWheel: rotation('Wheel_rear'), crank: rotation('Crank'),
      head: rotation('Pelican_head'), scarf: rotation('Scarf_flutter'),
      leftFoot: position('Foot_L'), rightFoot: position('Foot_R'), leftPedal: position('Pedal_L'), rightPedal: position('Pedal_R'),
      knee: position('Knee_L'), clips: gltf.animations.length, ...geometry,
    }),
  };
  function frame(now) {
    const dt = Math.min((now - last) / 1000, .05);
    last = now;
    if (contextLost || document.hidden) return;
    if (playing) { elapsed += dt * speed; applyTime(); }
    if (transition) {
      transition.time += dt;
      const p = Math.min(transition.time / .85, 1);
      const eased = p * p * (3 - 2 * p);
      camera.position.lerpVectors(transition.from, transition.to, eased);
      controls.target.lerpVectors(transition.targetFrom, transition.targetTo, eased);
      project(THREE.MathUtils.lerp(transition.fromHeight, transition.height, eased));
      if (p === 1) transition = null;
    }
    controls.update(dt);
    renderer.render(scene, camera);
  }
  last = performance.now();
  renderer.setAnimationLoop(frame);
}

start().catch(error => {
  console.error('Pelican viewer:', error);
  $('loading').hidden = false;
  $('loadingText').textContent = 'Unable to load. Check your connection and WebGL support.';
  $('retry').hidden = false;
});
