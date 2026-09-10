"""Render an eight-second Pelican Ride film from the editable Blender scene.

The browser viewer remains a four-second interactive loop. This export uses the
same authored Blender animation twice, with a moving perspective camera and
camera-attached title cards so the result reads as a dimensional 3D film.

Run through:
    npm run pelican:video
    npm run pelican:video -- --preview
"""
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


ROOT = Path(__file__).resolve().parents[1]
FPS = 24
SECONDS = 8
FRAME_END = FPS * SECONDS
OUTPUT = ROOT / "output/pelican/pelican-ride.mp4"
PREVIEW = ROOT / "renders/pelican/blender-video-preview.png"


def parse_options():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    frame = 1
    if "--frame" in args:
        index = args.index("--frame")
        if index + 1 >= len(args):
            raise ValueError("--frame requires a frame number")
        frame = max(1, min(FRAME_END, int(args[index + 1])))
    return {"preview": "--preview" in args, "frame": frame}


def emission_material(name, color, strength=1.0):
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeEmission")
    shader.inputs["Color"].default_value = (*color, 1)
    shader.inputs["Strength"].default_value = strength
    links.new(shader.outputs["Emission"], output.inputs["Surface"])
    return material


def text_overlay(name, body, location, size, material, align="LEFT"):
    curve = bpy.data.curves.new(name, "FONT")
    curve.body = body
    curve.align_x = align
    curve.align_y = "CENTER"
    curve.size = size
    curve.space_character = 1.05
    curve.extrude = 0.004
    curve.bevel_depth = 0.002
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    # Text curves face local +Z, which is the camera-facing side at a
    # camera-local negative Z position. Keeping the default orientation avoids
    # the mirrored/upside-down result produced by flipping the curve.
    obj.rotation_euler = (0, 0, 0)
    obj.location = location
    return obj


def attach_overlay(obj, camera):
    obj.parent = camera
    obj.matrix_parent_inverse = Matrix.Identity(4)


def point_camera(camera, at, target):
    camera.location = at
    camera.rotation_mode = "QUATERNION"
    camera.rotation_quaternion = (Vector(target) - Vector(at)).to_track_quat("-Z", "Y")


def keyframe_camera(camera, frame, at, target, lens):
    point_camera(camera, at, target)
    camera.data.lens = lens
    camera.keyframe_insert("location", frame=frame)
    camera.keyframe_insert("rotation_quaternion", frame=frame)
    camera.data.keyframe_insert("lens", frame=frame)


def smooth_camera_curves(camera):
    if not camera.animation_data or not camera.animation_data.action:
        return
    for curve in camera.animation_data.action.fcurves:
        for key in curve.keyframe_points:
            key.interpolation = "BEZIER"
            key.handle_left_type = "AUTO"
            key.handle_right_type = "AUTO"


def loop_model_actions():
    actions = []
    for obj in bpy.context.scene.objects:
        action = obj.animation_data.action if obj.animation_data else None
        if not action or action in actions:
            continue
        actions.append(action)
        for curve in action.fcurves:
            if not any(mod.type == "CYCLES" for mod in curve.modifiers):
                curve.modifiers.new("CYCLES")
    if not actions:
        raise RuntimeError("The Pelican scene has no authored animation actions.")
    return actions


def configure_camera(scene):
    camera = scene.camera
    if camera is None:
        bpy.ops.object.camera_add()
        camera = bpy.context.object
        scene.camera = camera
    camera.data.type = "PERSP"
    camera.data.lens = 52
    camera.data.sensor_width = 36
    camera.data.clip_start = 0.05
    camera.data.clip_end = 100
    camera.data.dof.use_dof = True
    camera.data.dof.aperture_fstop = 5.6
    camera.data.dof.aperture_blades = 6

    focus = bpy.data.objects.get("Pelican video focus")
    if focus is None:
        focus = bpy.data.objects.new("Pelican video focus", None)
        bpy.context.collection.objects.link(focus)
    focus.location = (0, 0, 2.05)
    camera.data.dof.focus_object = focus

    # The orbit, close-up and reverse angle expose the model's depth, wheels,
    # layered feathers, throat pouch and bicycle frame.
    shots = [
        (1, (6.9, -11.5, 5.8), (0.0, 0.0, 1.78), 52),
        (49, (9.2, -2.9, 4.55), (0.0, 0.0, 1.92), 52),
        (97, (3.45, -5.35, 4.25), (0.40, 0.0, 3.28), 52),
        (145, (-7.6, 6.2, 4.85), (0.0, 0.0, 1.78), 52),
        (192, (5.8, -10.0, 5.25), (0.0, 0.0, 1.78), 52),
    ]
    if camera.animation_data:
        camera.animation_data_clear()
    for frame, at, target, lens in shots:
        keyframe_camera(camera, frame, at, target, lens)
    smooth_camera_curves(camera)
    return camera


def configure_overlays(camera):
    title_material = emission_material("Video title green", (0.075, 0.19, 0.14), 1.2)
    accent_material = emission_material("Video accent coral", (0.72, 0.25, 0.15), 1.1)
    for name in ("GPT-6 3D Blender Astra", "Pelican Ride subtitle"):
        old = bpy.data.objects.get(name)
        if old:
            bpy.data.objects.remove(old, do_unlink=True)

    title = text_overlay(
        "GPT-6 3D Blender Astra",
        "GPT-6  ·  3D  ·  BLENDER  ·  ASTRA",
        (-2.20, 2.02, -7.0),
        0.19,
        title_material,
    )
    subtitle = text_overlay(
        "Pelican Ride subtitle",
        "PROCEDURAL PELICAN RIDE  /  鹈鹕骑行",
        (-2.20, 1.70, -7.0),
        0.105,
        accent_material,
    )
    for obj in (title, subtitle):
        attach_overlay(obj, camera)


def configure_render(scene, preview, frame):
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 540 if preview else 1080
    scene.render.resolution_y = 540 if preview else 1080
    scene.render.resolution_percentage = 100
    scene.render.fps = FPS
    scene.frame_start = 1
    scene.frame_end = frame if preview else FRAME_END
    scene.render.image_settings.file_format = "PNG" if preview else "FFMPEG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.film_transparent = False
    scene.render.filepath = str(PREVIEW if preview else OUTPUT)
    if not preview:
        scene.render.ffmpeg.format = "MPEG4"
        scene.render.ffmpeg.codec = "H264"
        scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
        scene.render.ffmpeg.ffmpeg_preset = "GOOD"
        scene.render.ffmpeg.gopsize = 12
        scene.render.ffmpeg.use_max_b_frames = True
        scene.render.ffmpeg.audio_codec = "NONE"
        scene.render.ffmpeg.audio_bitrate = 0
        scene.render.ffmpeg.use_autosplit = False
    scene.render.image_settings.color_depth = "8"
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = 0.15
    scene.view_settings.gamma = 1.0
    if hasattr(scene, "eevee"):
        scene.eevee.taa_render_samples = 64


def main():
    options = parse_options()
    scene = bpy.context.scene
    loop_model_actions()
    camera = configure_camera(scene)
    configure_overlays(camera)
    configure_render(scene, options["preview"], options["frame"])
    scene.frame_set(options["frame"])
    if options["preview"]:
        PREVIEW.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.render.render(write_still=True)
        print(f"PELICAN_BLENDER_PREVIEW_COMPLETE {PREVIEW}")
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.render.render(animation=True)
        print(f"PELICAN_BLENDER_VIDEO_COMPLETE {OUTPUT}")


if __name__ == "__main__":
    main()
