# Asset credits and provenance

## Movie reference and original dialogue

- Work: **《牛来》 / Niu Lai**.
- Reference publisher: **猫眼侃世界**.
- Source: https://newsa.html5.qq.com/v1/share-video?vid=93819400611114414
- Local reference: `reference/movie-excerpt.mp4`, 12.055 seconds, a third-party recording of a screen.
- Reference stills: extracted from this recording, including `snake.jpg`, `niulai-mama.jpg`, `mother-niulai.jpg` and `storyboard.jpg`.
- `web/assets/dialogue.m4a`: source time 3.9–9.8 seconds.
- Social-video introduction: source time 4.8–6.6 seconds followed by 8.35–9.55 seconds.
- The final “Mama!” is a replay of the excerpt. No voice synthesis or voice cloning is used.

Original film footage, dialogue and original character rights remain with their respective owners. These source media are separate from the code-generated recreation.

## Generated assets

`src/build_scene.py` constructs the clay-style characters and environment using Blender's `bpy` API. The `.blend`, `.glb`, rendered recreation, cover and final storyboard are generated from this workflow. No original movie model files or external 3D-generation service were used.

GPT‑6 / Codex authored and revised the scripts through multiple iterations and rendered checks. An exact API model snapshot and a complete timestamped prompt log were not recorded.

## Third-party software

- **Three.js 0.180.0**: local browser rendering library and its GLTF loader, OrbitControls and BufferGeometryUtils. MIT license: [`web/vendor/THREE-LICENSE.txt`](web/vendor/THREE-LICENSE.txt). Upstream: https://github.com/mrdoob/three.js/tree/r180
- **Blender**: external modeling/rendering tool, tested with 4.5.13 LTS. Blender binaries are not included. https://www.blender.org/
- **FFmpeg**: external media processing tool. Binaries are not included. https://ffmpeg.org/
- **Sharp** and **Playwright**: development dependencies pinned in `package-lock.json`; their respective package licenses apply. https://sharp.pixelplumbing.com/ and https://playwright.dev/
