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

## Saber fan figure

- Character: **Saber / Artoria Pendragon**, *Fate/stay night*, © TYPE-MOON and the respective rights holders. This is an unofficial fan-art exercise, unaffiliated with the original publishers.
- `src/build_saber.py`, `src/saber_sculpt.py` and `src/saber_portrait.py` procedurally construct the stylized figure, materials, armature, eye shape keys and sword choreography in Blender 4.5.13 LTS. Both arms use analytic two-bone IK, baked to ordinary skeletal keyframes.
- Revisions 2 and 3 use Good Smile Company's **Saber ~Triumphant Excalibur~** product photographs as visual references for the face, hair, armor, skirt and sword: https://www.goodsmile.info/en/product/2780/ . The photos are not bundled or used as textures; skin and teal iris pigments are authored mesh attributes. `src/compare_saber.mjs` makes a local reference comparison in the ignored cache, without claiming an identity score. Product photography rights remain with their respective owners.
- `output/saber/saber.blend` is the editable scene; `web/saber/assets/saber.glb` is the optimized export. No official mesh, external 3D model, motion-capture data, voice or soundtrack is included.
- `output/saber/contact-sheet.jpg` contains renders of this Blender scene. The viewer's studio environment, shadow texture and gold particles are generated locally in code. No AI-generated raster illustration is included in the delivered assets.
- The demo follows the repository's script, render, inspect and revise workflow. It is a stylized procedural interpretation, not a scan or a production character asset.

## Third-party software

- **Three.js 0.180.0**: local browser rendering library and its GLTF loader, OrbitControls and BufferGeometryUtils. MIT license: [`web/vendor/THREE-LICENSE.txt`](web/vendor/THREE-LICENSE.txt). Upstream: https://github.com/mrdoob/three.js/tree/r180
- **Blender**: external modeling/rendering tool, tested with 4.5.13 LTS. Blender binaries are not included. https://www.blender.org/
- **FFmpeg**: external media processing tool. Binaries are not included. https://ffmpeg.org/
- **Sharp** and **Playwright**: development dependencies pinned in `package-lock.json`; their respective package licenses apply. https://sharp.pixelplumbing.com/ and https://playwright.dev/
