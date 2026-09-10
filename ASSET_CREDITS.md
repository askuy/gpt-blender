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

## Pelican cycling club

- Original stylized character and coastal diorama, constructed procedurally by `src/build_pelican.py` using Blender. No external meshes, photographs, image textures, animation clips or audio recordings are used.
- `output/pelican/pelican.blend` retains the editable model and four-second animation. `web/pelican/assets/pelican.glb` contains baked object-transform tracks and static meshes batched by material and parent. Both legs use analytic two-link positioning; level webbed feet follow opposite pedals and the wheels retain a 2:1 gear ratio.
- The inspection views and `output/pelican/contact-sheet.jpg` are renders of this scene. The browser contact shadow and moving lane markings are generated locally in code. The bicycle bell uses Web Audio oscillators, triggered by user interaction.
- The viewer reuses the repository's vendored Three.js, OrbitControls and GLTFLoader. There are no AI API calls or backend services.

## Apple Duo foldable concept

- `src/build_duo.py` constructs the silver enclosure, beveled edges, cameras, Apple-shaped emblem, cover display, ports and two animated hinges in Blender 4.5 LTS. This is a visual concept with invented dimensions, not a verified reconstruction of an announced Apple product. Apple names and marks belong to their owner.
- `web/duo/assets/portrait.jpg` is a locally stored Unsplash photograph, downloaded from https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=1600&h=1200&q=90&fit=crop&crop=faces . Source service license: https://unsplash.com/license . The photograph is mapped continuously across the two inner display meshes and packed into the Blender file and GLB. It is not AI-generated; the attempted built-in image generation returned no usable file.
- `output/duo/duo.blend` keeps editable parts and 121 frames at 30 fps, from closed to open. `web/duo/assets/duo.glb` contains the geometry, packed photo and sampled object animations. The browser scrubs those Blender tracks, adds studio reflections and generates its outer lock-screen interface locally with canvas.
- `output/duo/duo-reveal.mp4` is a deterministic 12-second browser render of the Blender GLB, encoded with FFmpeg by `src/render_duo.mjs`. `output/duo/contact-sheet.jpg` shows the closed, half-open and open Blender renders. Browser interactions make no external API calls.

## Third-party software

- **Three.js 0.180.0**: local browser rendering library and its GLTF loader, OrbitControls and BufferGeometryUtils. MIT license: [`web/vendor/THREE-LICENSE.txt`](web/vendor/THREE-LICENSE.txt). Upstream: https://github.com/mrdoob/three.js/tree/r180
- **Blender**: external modeling/rendering tool, tested with 4.5.13 LTS. Blender binaries are not included. https://www.blender.org/
- **FFmpeg**: external media processing tool. Binaries are not included. https://ffmpeg.org/
- **Sharp** and **Playwright**: development dependencies pinned in `package-lock.json`; their respective package licenses apply. https://sharp.pixelplumbing.com/ and https://playwright.dev/
