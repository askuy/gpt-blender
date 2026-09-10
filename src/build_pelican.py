"""An original pelican on a bicycle: editable geometry and a seamless ride.

Blender coordinates: X forward, Y across the bike, Z up. Object-space rigs
use analytic two-link legs; level pedals and webbed feet follow the crank.
Run npm run pelican:scene -- --preview to rebuild the GLB and inspection views.
"""
import argparse
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
FPS, DURATION = 24, 4
TAU = math.tau


def select(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def mat(name, color, rough=.48, metal=0):
    def linear(v):
        v = int(v, 16) / 255
        return v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4
    rgb = tuple(linear(color[i:i+2]) for i in (1, 3, 5))
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, 1)
    m.use_nodes = True
    shader = m.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*rgb, 1)
    shader.inputs['Roughness'].default_value = rough
    shader.inputs['Metallic'].default_value = metal
    return m


def finish(obj, name, material, parent=None):
    obj.name = name
    if material:
        obj.data.materials.append(material)
    if obj.type == 'MESH':
        for face in obj.data.polygons:
            face.use_smooth = True
    if parent:
        # Geometry is authored in scene coordinates, then attached without moving.
        bpy.context.view_layer.update()
        transform = obj.matrix_world.copy()
        obj.parent = parent
        obj.matrix_world = transform
    return obj


def group(name, at=(0, 0, 0)):
    obj = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(obj)
    obj.location = at
    return obj


def mesh(name, vertices, faces, material, parent=None):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    return finish(obj, name, material, parent)


def sphere(name, at, size, material, parent=None):
    small = max(size) < .12
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20 if small else 36, ring_count=12 if small else 24, location=at)
    obj = bpy.context.object
    obj.scale = size
    return finish(obj, name, material, parent)


def rod(name, a, b, radius, material, parent=None, radius2=None, sides=16):
    a, b = Vector(a), Vector(b)
    bpy.ops.mesh.primitive_cone_add(vertices=sides, radius1=radius, radius2=radius if radius2 is None else radius2, depth=(b-a).length, location=(a+b)/2)
    obj = bpy.context.object
    obj.rotation_euler = (b-a).to_track_quat('Z', 'Y').to_euler()
    return finish(obj, name, material, parent)


def box(name, at, size, material, bevel=.04, parent=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=at)
    obj = bpy.context.object
    obj.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    mod = obj.modifiers.new('Rounded crafted edges', 'BEVEL')
    mod.width, mod.segments = bevel, 4
    bpy.ops.object.modifier_apply(modifier=mod.name)
    return finish(obj, name, material, parent)


def curve(name, points, radius, material, parent=None, cyclic=False):
    data = bpy.data.curves.new(name, 'CURVE')
    data.dimensions = '3D'
    data.resolution_u = 10
    spline = data.splines.new('BEZIER')
    spline.bezier_points.add(len(points)-1)
    for p, co in zip(spline.bezier_points, points):
        p.co = co
        p.handle_left_type = p.handle_right_type = 'AUTO'
    spline.use_cyclic_u = cyclic
    data.bevel_depth, data.bevel_resolution = radius, 2
    data.use_fill_caps = True
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    select(obj)
    bpy.ops.object.convert(target='MESH')
    return finish(obj, name, material, parent)


def torus(name, at, radius, tube, material, parent=None, axis='Y'):
    bpy.ops.mesh.primitive_torus_add(major_segments=80, minor_segments=12, location=at, major_radius=radius, minor_radius=tube)
    obj = bpy.context.object
    if axis == 'Y':
        obj.rotation_euler.x = math.pi / 2
    return finish(obj, name, material, parent)


def feather(name, a, b, width, depth, material, parent=None):
    a, b = Vector(a), Vector(b)
    obj = sphere(name, (a+b)/2, (width, depth, (b-a).length/2), material)
    obj.rotation_euler = (b-a).to_track_quat('Z', 'Y').to_euler()
    return finish(obj, name, None, parent)


def loft(name, sections, material, parent=None):
    """Smooth closed cross sections along X: (x, half-width, top, bottom)."""
    vertices, faces, sides = [], [], 40
    for x, width, top, bottom in sections:
        for j in range(sides):
            angle = TAU*j/sides
            vertices.append((x, width*math.cos(angle), (top+bottom)/2+(top-bottom)/2*math.sin(angle)))
    for i in range(len(sections)-1):
        for j in range(sides):
            a, b = i*sides+j, i*sides+(j+1)%sides
            faces.append((a, b, b+sides, a+sides))
    faces += [tuple(reversed(range(sides))), tuple((len(sections)-1)*sides+j for j in range(sides))]
    obj = mesh(name, vertices, faces, material, parent)
    mod = obj.modifiers.new('Soft sculpted surface', 'SUBSURF')
    mod.levels = 2
    select(obj)
    bpy.ops.object.modifier_apply(modifier=mod.name)
    return obj


def build_bike(m):
    wheels = []
    for x, label in [(-1.18, 'rear'), (1.18, 'front')]:
        root = group('Wheel_'+label, (x, 0, .80))
        wheels.append(root)
        torus('Charcoal rubber tire', (x, 0, .80), .635, .085, m['rubber'], root)
        for side in [-1, 1]:
            torus('Cream tire sidewall', (x, side*.065, .80), .63, .035, m['cream'], root)
            torus('Polished wheel rim', (x, side*.052, .80), .566, .021, m['chrome'], root)
        rod('Wheel hub', (x, -.12, .8), (x, .12, .8), .07, m['chrome'], root)
        for i in range(28):
            a = TAU*i/28
            rod('Laced spoke', (x+.055*math.cos(a+.5), -.045 if i%2 else .045, .80+.055*math.sin(a+.5)), (x+.557*math.cos(a), 0, .80+.557*math.sin(a)), .009, m['chrome'], root, sides=8)
        box('Amber spoke reflector', (x+.34, -.018, .80), (.09, .045, .035), m['amber'], .012, root)
    rear, front = (-1.18, 0, .80), (1.18, 0, .80)
    crank_at, seat, head, low_head = (-.20, 0, .79), (-.57, 0, 1.70), (.78, 0, 1.65), (.95, 0, 1.24)
    for a, b in [(crank_at, seat), (seat, head), (crank_at, low_head), (head, low_head)]:
        rod('Mint enamel frame', a, b, .057, m['mint'], sides=24)
    for side in [-1, 1]:
        offset_rear = (rear[0], side*.13, rear[2])
        rod('Rear chain stay', (-.20, side*.11, .79), offset_rear, .035, m['mint'])
        rod('Rear seat stay', seat, offset_rear, .035, m['mint'])
        curve('Curved front fork', [low_head, (1.05, side*.13, 1.02), (1.18, side*.13, .8)], .037, m['mint'])
        rod('Wheel axle nut', (1.18, side*.12, .80), (1.18, side*.165, .80), .045, m['chrome'])
    for x in [-1.18, 1.18]:
        curve('Mint mudguard', [(x+.753*math.cos(a), 0, .80+.753*math.sin(a)) for a in [math.pi*.12+i*math.pi*.78/28 for i in range(29)]], .038, m['mint'])
    rod('Seat post', seat, (-.61, 0, 1.90), .034, m['chrome'])
    sphere('Cognac leather saddle', (-.65, 0, 1.91), (.28, .22, .078), m['leather'])
    for side in [-1, 1]:
        sphere('Saddle brass rivet', (-.79, side*.176, 1.927), (.017, .012, .013), m['brass'])
    rod('Handlebar stem', head, (.73, 0, 1.94), .037, m['chrome'])
    curve('Swept chrome handlebar', [(.82, -.43, 1.99), (.94, -.27, 1.98), (.74, 0, 1.96), (.94, .27, 1.98), (.82, .43, 1.99)], .032, m['chrome'])
    for side in [-1, 1]:
        rod('Leather handlebar grip', (.82, side*.32, 1.99), (.82, side*.48, 1.99), .05, m['leather'])
    sphere('Brass bicycle bell', (.84, -.23, 2.01), (.085, .085, .05), m['brass'])
    curve('Front brake cable', [(.86, -.30, 1.98), (1.12, -.17, 1.80), (1.05, -.04, 1.45)], .012, m['rubber'])
    sphere('Headlamp chrome shell', (1.03, 0, 1.55), (.105, .10, .10), m['chrome'])
    sphere('Warm headlamp glass', (1.111, 0, 1.55), (.025, .080, .080), m['cream'])
    torus('Bottom bracket', crank_at, .12, .023, m['chrome'])
    torus('Chain ring', (-.20, -.14, .79), .207, .018, m['chrome'])
    torus('Rear sprocket', (-1.18, -.14, .80), .093, .012, m['chrome'])
    curve('Continuous bicycle chain', [(-1.18, -.165, .893), (-.20, -.165, .997), (.007, -.165, .79), (-.20, -.165, .583), (-1.18, -.165, .707), (-1.273, -.165, .80)], .013, m['steel'], cyclic=True)
    crank = group('Crank', crank_at)
    for side in [-1, 1]:
        rod('Chrome crank arm', (-.20, side*.20, .79), (-.20+side*.28, side*.20, .79), .026, m['chrome'], crank)
        rod('Pedal axle', (-.20+side*.28, side*.18, .79), (-.20+side*.28, side*.39, .79), .021, m['chrome'], crank)
    return wheels, crank


def build_bird(m):
    body = sphere('Pelican pear shaped body', (-.62, 0, 2.30), (.62, .44, .64), m['ivory'])
    breast = sphere('Soft breast', (-.27, 0, 2.47), (.40, .38, .50), m['ivory'])
    for i in range(5):
        feather('Layered tail feather', (-.91, (i-2)*.075, 2.26), (-1.59-abs(i-2)*.02, (i-2)*.09, 2.54-abs(i-2)*.035), .095, .08, m['feather'] if i%2 else m['ivory'])
    # Overlapping tapered neck sections form the characteristic pelican S curve.
    neck = curve('Curved ivory neck', [(-.28, 0, 2.64), (.04, 0, 2.91), (-.02, 0, 3.19), (.16, 0, 3.50)], .235, m['ivory'])
    select(body)
    breast.select_set(True)
    neck.select_set(True)
    bpy.ops.object.join()
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    remesh = body.modifiers.new('Continuous sculpted breast and neck', 'REMESH')
    remesh.mode, remesh.voxel_size = 'VOXEL', .033
    bpy.ops.object.modifier_apply(modifier=remesh.name)
    smooth = body.modifiers.new('Polished clay', 'SMOOTH')
    smooth.factor, smooth.iterations = 1, 5
    bpy.ops.object.modifier_apply(modifier=smooth.name)
    finish(body, 'Continuous pelican body and neck', None)
    bpy.context.view_layer.update()
    neck_top = max((body.matrix_world @ v.co).z for v in body.data.vertices)
    assert neck_top > 3.45, 'The voxel union must preserve the neck connecting to the head'
    head = group('Pelican_head', (.13, 0, 3.38))
    sphere('Pelican head', (.22, 0, 3.59), (.37, .294, .39), m['ivory'], head)
    loft('Long golden upper bill', [(.43, .20, 3.62, 3.48), (.61, .245, 3.62, 3.47), (1.13, .17, 3.55, 3.43), (1.70, .055, 3.46, 3.38), (1.90, .006, 3.38, 3.34)], m['yellow'], head)
    loft('Deep pelican throat pouch', [(.30, .10, 3.46, 3.22), (.55, .239, 3.48, 3.09), (.87, .219, 3.46, 3.055), (1.18, .17, 3.43, 3.16), (1.62, .065, 3.39, 3.32), (1.89, .003, 3.37, 3.345)], m['pouch'], head)
    for side in [-1, 1]:
        curve('Bill smile seam', [(.46, side*.205, 3.485), (.76, side*.229, 3.467), (1.28, side*.15, 3.413), (1.82, side*.025, 3.366)], .009, m['bill_seam'], head)
        sphere('Ochre eye surround', (.335, side*.258, 3.714), (.118, .048, .127), m['eye_patch'], head)
        sphere('Glazed eye white', (.346, side*.291, 3.721), (.082, .042, .091), m['white'], head)
        sphere('Curious dark pupil', (.373, side*.326, 3.720), (.042, .021, .052), m['ink'], head)
        sphere('Eye catchlight', (.381, side*.344, 3.741), (.013, .008, .016), m['white'], head)
        curve('Gentle expressive brow', [(.253, side*.278, 3.842), (.315, side*.300, 3.858), (.389, side*.278, 3.837)], .013, m['ink'], head)
        sphere('Bill nostril', (.70, side*.221, 3.554), (.04, .007, .011), m['bill_seam'], head)
        sphere('Warm cheek', (.195, side*.285, 3.578), (.092, .015, .049), m['blush'], head)
    for i in range(3):
        feather('Wind swept crown', (.10-i*.06, (i-1)*.052, 3.855), (-.21-i*.055, (i-1)*.069, 3.99-i*.045), .061, .055, m['ivory'], head)
    for side in [-1, 1]:
        feather('Folded wing shoulder', (-.86, side*.30, 2.70), (-.05, side*.465, 2.26), .26, .155, m['feather'])
        feather('Wing reaching handlebars', (-.13, side*.458, 2.32), (.84, side*.41, 2.015), .14, .096, m['ivory'])
        for i in range(5):
            feather('Overlapping flight feather', (-.64+i*.08, side*(.42+.012*i), 2.51-i*.06), (.10+i*.13, side*(.51-.018*i), 2.22-i*.044), .078, .051, m['ivory'] if i%2 else m['feather_light'])
        sphere('Wing tip on handlebar', (.82, side*.419, 2.017), (.105, .079, .065), m['ivory'])
    torus('Coral scarf collar', (-.017, 0, 3.075), .231, .051, m['scarf'], axis='Z')
    sphere('Scarf knot', (-.19, -.15, 3.069), (.11, .10, .09), m['scarf'])
    scarf = group('Scarf_flutter', (-.19, -.10, 3.07))
    for offset in [0, .13]:
        vertices = [(-.16, -.10, 3.105-offset), (-.19, -.105, 2.991-offset), (-.61, -.095, 2.962-offset), (-1.07, -.03, 3.117-offset), (-1.0, -.025, 3.24-offset), (-.59, -.07, 3.117-offset)]
        obj = mesh('Flying coral scarf ribbon', vertices, [tuple(range(6))], m['scarf'], scarf)
        solid = obj.modifiers.new('Cloth thickness', 'SOLIDIFY')
        solid.thickness = .025
        bevel = obj.modifiers.new('Soft ribbon edge', 'BEVEL')
        bevel.width, bevel.segments = .025, 3
        select(obj)
        bpy.ops.object.modifier_apply(modifier=solid.name)
        bpy.ops.object.modifier_apply(modifier=bevel.name)
    return head, scarf


def build_legs(m):
    legs = []
    for side, label in [(-1, 'L'), (1, 'R')]:
        # Unit-length limb meshes: placement/rotation/length are baked each frame.
        upper = sphere('Leg_'+label+'_upper', (0, 0, 0), (.115, .105, .5), m['ivory'])
        lower = sphere('Leg_'+label+'_lower', (0, 0, 0), (.054, .060, .5), m['feet'])
        knee = sphere('Knee_'+label, (0, 0, 0), (.085, .082, .085), m['feet'])
        foot = group('Foot_'+label)
        outline = [(-.10, -.055), (.09, -.092), (.21, -.145), (.235, -.104), (.18, -.021), (.275, .006), (.258, .055), (.168, .072), (.192, .132), (.143, .153), (.046, .098), (-.10, .055)]
        vertices = [(x, y, z) for z in [.037, .091] for x, y in outline]
        n = len(outline)
        faces = [tuple(reversed(range(n))), tuple(range(n, n*2))] + [(i, (i+1)%n, (i+1)%n+n, i+n) for i in range(n)]
        obj = mesh('Sculpted webbed foot '+label, vertices, faces, m['feet'], foot)
        bevel = obj.modifiers.new('Rounded webbed toes', 'BEVEL')
        bevel.width, bevel.segments = .025, 3
        select(obj)
        bpy.ops.object.modifier_apply(modifier=bevel.name)
        for y in [-.08, .025, .105]:
            curve('Webbed toe crease', [(-.02, 0, .094), (.075, y*.6, .096), (.164, y, .093)], .006, m['toe'], foot)
        pedal = group('Pedal_'+label)
        box('Level pedal platform', (0, 0, 0), (.26, .23, .065), m['steel'], .016, pedal)
        for x in [-.082, 0, .082]:
            box('Pedal grip', (x, 0, .035), (.013, .20, .012), m['rubber'], .004, pedal)
        legs.append((side, upper, lower, knee, foot, pedal))
    return legs


def build_landscape(m):
    box('Sand island', (0, .15, -.15), (6.8, 3.55, .42), m['sand'], .30)
    box('Raised coastal cycle path', (0, -.05, .035), (6.67, 1.78, .09), m['road'], .075)
    for y in [-.85, .75]:
        box('Ivory path edge', (0, y, .086), (6.30, .033, .008), m['white'], .007)
    # Local geometric scenery; these are deliberately sparse to keep the rider clear.
    for i, (x, y, scale) in enumerate([(-2.65, .91, .7), (2.62, 1.04, 1), (-2.8, -1.24, .55), (1.70, 1.20, .58), (-1.74, 1.40, .55)]):
        for j in range(5):
            a = j*2.39996
            curve('Dune grass', [(x, y, .09), (x+.09*math.cos(a), y+.08*math.sin(a), .20+scale*.14), (x+.21*math.cos(a), y+.16*math.sin(a), .12+scale*(.18+.05*(j%3)))], .018, m['grass'])
        sphere('Smooth dune pebble', (x+.20, y-.07, .12), (.13*scale, .10*scale, .07*scale), m['pebble'])
    for x, y, s in [(-2.42, -1.24, .12), (2.14, -1.18, .10), (.81, 1.43, .13)]:
        shell = sphere('Little beach shell', (x, y, .086), (s, s*.78, s*.34), m['cream'])
        for i in range(5):
            a = math.pi*(.12+i*.18)
            curve('Shell ridge', [(x-s*.7, y, .105), (x+s*.23*math.cos(a), y+s*.66*math.sin(a), .125), (x+s*.86*math.cos(a), y+s*.76*math.sin(a), .095)], .006, m['pebble'])
    # Small sea-glass inset on the far edge of the diorama.
    box('Sea glass inlet', (.50, 1.38, .025), (3.4, .60, .065), m['sea'], .18)
    for x, y, length in [(-.65, 1.38, .36), (.32, 1.47, .48), (1.07, 1.31, .32), (1.65, 1.47, .24)]:
        curve('Sea foam', [(x, y, .065), (x+length*.5, y-.045, .065), (x+length, y, .065)], .013, m['white'])


def animate(wheels, crank, head, scarf, legs):
    animated = wheels + [crank, head, scarf]
    for _, upper, lower, knee, foot, pedal in legs:
        animated += [upper, lower, knee, foot, pedal]
    max_error = 0
    for frame in range(1, FPS*DURATION+2):
        t = (frame-1)/FPS
        phase = TAU*t*.5
        for wheel in wheels:
            wheel.rotation_euler.y = 2*phase
        crank.rotation_euler.y = phase
        head.rotation_euler.y = .021*math.sin(phase)
        head.rotation_euler.z = .018*math.sin(phase*.5)
        scarf.rotation_euler.x = .11*math.sin(phase*2)
        scarf.rotation_euler.y = .06*math.sin(phase*2+.3)
        for side, upper, lower, knee_obj, foot, pedal in legs:
            angle = phase + (math.pi if side == -1 else 0)
            at = Vector((-.20+.28*math.cos(angle), side*.34, .79-.28*math.sin(angle)))
            hip = Vector((-.59, side*.265, 1.997))
            ankle = at + Vector((-.025, 0, .10))
            delta = ankle-hip
            d = delta.length
            l1, l2 = .72, .78
            if d >= l1+l2:
                raise ValueError('Unreachable pedal: adjust leg proportions')
            direction = delta.normalized()
            bend = Vector((1, 0, 0))
            bend = (bend-direction*bend.dot(direction)).normalized()
            along = (l1*l1-l2*l2+d*d)/(2*d)
            knee = hip + direction*along + bend*math.sqrt(max(0, l1*l1-along*along))
            for obj, a, b, radius in [(upper, hip, knee, .115), (lower, knee, ankle, .054)]:
                obj.location = (a+b)/2
                obj.rotation_euler = (b-a).to_track_quat('Z', 'Y').to_euler()
                obj.scale = (radius, radius*.97, (b-a).length/2)
            knee_obj.location = knee
            pedal.location = at
            foot.location = at
            max_error = max(max_error, abs((knee-hip).length-l1), abs((ankle-knee).length-l2))
        for obj in animated:
            for prop in ['location', 'rotation_euler', 'scale']:
                obj.keyframe_insert(prop, frame=frame, group=obj.name)
    for obj in animated:
        # Linear samples prevent Bézier overshoot; full rotations preserve direction.
        action = obj.animation_data.action
        for fc in action.fcurves:
            for key in fc.keyframe_points:
                key.interpolation = 'LINEAR'
    print('PELICAN_IK_MAX_ERROR', max_error)


def aim(obj, at, target):
    obj.location = at
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z', 'Y').to_euler()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--preview', action='store_true')
    opt = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    for folder in ['output/pelican', 'web/pelican/assets', 'renders/pelican']:
        (ROOT/folder).mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    colors = {
        'ivory': '#f8f4e8', 'feather': '#e1e3d8', 'feather_light': '#f0ede1',
        'white': '#fff9ed', 'cream': '#eaddb8', 'yellow': '#efb940', 'pouch': '#e4a347',
        'bill_seam': '#ad752e', 'eye_patch': '#edc668', 'ink': '#283f3c', 'blush': '#ecd0b2',
        'feet': '#e4a148', 'toe': '#bc803c', 'scarf': '#d96c4a', 'mint': '#478b79',
        'leather': '#77533e', 'rubber': '#2d3e3c', 'chrome': '#b7c8c3', 'steel': '#52625c',
        'brass': '#d6b264', 'amber': '#e9a14a', 'sand': '#e2d3af', 'road': '#bac8b5',
        'grass': '#6e8862', 'pebble': '#c1b598', 'sea': '#8fbfb7',
    }
    m = {key: mat(key, color, .28 if key in ['mint', 'chrome', 'brass', 'ink'] else .53, .7 if key in ['chrome', 'brass'] else .12 if key == 'mint' else 0) for key, color in colors.items()}
    wheels, crank = build_bike(m)
    head, scarf = build_bird(m)
    legs = build_legs(m)
    build_landscape(m)
    animate(wheels, crank, head, scarf, legs)
    model_objects = list(bpy.context.scene.objects)
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
    scene.eevee.taa_render_samples = 48
    scene.render.resolution_x, scene.render.resolution_y = 1400, 1100
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.fps = FPS
    scene.frame_start, scene.frame_end = 1, FPS*DURATION+1
    scene.view_settings.view_transform = 'AgX'
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.77, .81, .77, 1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value = .5
    for name, at, power, size, color in [('Large warm softbox', (-3, -4, 8), 850, 5, (1, .91, .76)), ('Sea rim light', (2, 4, 6), 1000, 4, (.78, .91, 1)), ('Soft front fill', (5, -6, 4), 400, 4, (1, 1, 1))]:
        bpy.ops.object.light_add(type='AREA')
        obj = bpy.context.object
        obj.name, obj.data.energy, obj.data.size, obj.data.color = name, power, size, color
        aim(obj, at, (0, 0, 2))
    bpy.ops.mesh.primitive_plane_add(size=200)
    finish(bpy.context.object, 'Studio backdrop', mat('Studio backdrop', '#f2eee3', .8))
    bpy.context.object.location.z = -.37
    bpy.ops.object.camera_add()
    camera = bpy.context.object
    camera.data.type, camera.data.ortho_scale = 'ORTHO', 7.8
    scene.camera = camera
    aim(camera, (5.4, -10, 5.1), (0, 0, 1.70))
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'output/pelican/pelican.blend'))
    if opt.preview:
        for frame, name, at, target, scale in [
            (9, 'hero', (5.4, -10, 5.1), (0, 0, 1.72), 7.8),
            (21, 'side', (0, -12, 3.8), (0, 0, 1.8), 7.6),
            (1, 'face', (3.7, -8, 4.6), (.55, 0, 3.38), 3.0),
            (33, 'back', (-5.4, 10, 4.8), (0, 0, 1.7), 7.8),
        ]:
            scene.frame_set(frame)
            aim(camera, at, target)
            camera.data.ortho_scale = scale
            scene.render.filepath = str(ROOT/f'renders/pelican/{name}.png')
            bpy.ops.render.render(write_still=True)
    scene.frame_set(1)
    # Keep every modeled part editable in .blend; batch static meshes for the web.
    groups, exports = {}, []
    for obj in model_objects:
        if obj.type != 'MESH' or obj.animation_data:
            exports.append(obj)
            continue
        key = (obj.parent, tuple(obj.data.materials))
        groups.setdefault(key, []).append(obj)
    for objects in groups.values():
        select(objects[0])
        for obj in objects:
            obj.select_set(True)
        if len(objects) > 1:
            bpy.ops.object.join()
        exports.append(bpy.context.object)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in exports:
        obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(ROOT/'web/pelican/assets/pelican.glb'), export_format='GLB', use_selection=True, export_animations=True, export_animation_mode='SCENE', export_frame_range=True, export_force_sampling=True, export_cameras=False, export_lights=False, export_extras=True)
    print('PELICAN_BUILD_COMPLETE', len(exports), 'export objects')


if __name__ == '__main__':
    main()
