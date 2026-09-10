"""Editable Apple Duo foldable concept; geometry, shared screen UVs and hinge animation.

No official product dimensions are asserted. X is width, -Y is screen front,
Z is up. Frame 1 is closed; frame 121 is open, at 30 fps.
"""
import argparse
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
W, H, T, GAP = 2.86, 4.26, .155, .018
FPS, END = 30, 121


def material(name, color, metal=0, rough=.3):
    rgb = tuple(((int(color[i:i+2], 16)/255+.055)/1.055)**2.4 for i in (1, 3, 5))
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, 1)
    m.use_nodes = True
    s = m.node_tree.nodes.get('Principled BSDF')
    s.inputs['Base Color'].default_value = (*rgb, 1)
    s.inputs['Metallic'].default_value = metal
    s.inputs['Roughness'].default_value = rough
    return m


def attach(obj, name, mat=None, parent=None):
    obj.name = name
    if mat:
        obj.data.materials.append(mat)
    if parent:
        bpy.context.view_layer.update()
        matrix = obj.matrix_world.copy()
        obj.parent = parent
        obj.matrix_world = matrix
    return obj


def group(name, at=(0, 0, 0), parent=None):
    obj = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(obj)
    obj.location = at
    return attach(obj, name, parent=parent)


def outline(cx, cz, width, height, radius, steps=12):
    points = []
    radii = radius if isinstance(radius,tuple) else (radius,)*4
    for (x, z, start), radius in zip([(1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)],radii):
        for i in range(steps+1):
            a = math.radians(start+i*90/steps)
            points.append((cx+x*(width/2-radius)+radius*math.cos(a),
                           cz+z*(height/2-radius)+radius*math.sin(a)))
    return points


def slab(name, cx, cz, width, height, y, depth, radius, mat, parent, bevel=.008):
    points = outline(cx, cz, width, height, radius)
    n = len(points)
    verts = [(x, y-depth/2, z) for x, z in points]+[(x, y+depth/2, z) for x, z in points]
    faces = [tuple(range(n)), tuple(reversed(range(n, n*2)))]
    faces += [(i, n+i, n+(i+1)%n, (i+1)%n) for i in range(n)]
    data = bpy.data.meshes.new(name)
    data.from_pydata(verts, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    if bevel:
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        mod = obj.modifiers.new('Machined edge', 'BEVEL')
        mod.width, mod.segments = bevel, 3
        bpy.ops.object.modifier_apply(modifier=mod.name)
        obj.select_set(False)
    return attach(obj, name, mat, parent)


def screen(name, cx, width, height, y, mat, parent, shared=False, back=False):
    radius = ((.012,.19,.19,.012) if cx<0 else (.19,.012,.012,.19)) if shared else .19
    points = outline(cx, 0, width, height, radius)
    data = bpy.data.meshes.new(name)
    face = tuple(reversed(range(len(points)))) if back else tuple(range(len(points)))
    data.from_pydata([(x, y, z) for x, z in points], [], [face])
    data.update()
    uv = data.uv_layers.new(name='Continuous display UV')
    for loop in data.loops:
        x, z = points[loop.vertex_index]
        u = (x+(W+GAP/2-.055))/(2*W+GAP-.11) if shared else (x-cx)/width+.5
        uv.data[loop.index].uv = (1-u if back else u, z/height+.5)
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    return attach(obj, name, mat, parent)


def cylinder(name, at, radius, depth, mat, parent, axis='Y'):
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=radius, depth=depth, location=at)
    obj = bpy.context.object
    if axis == 'Y':
        obj.rotation_euler.x = math.pi/2
    elif axis == 'X':
        obj.rotation_euler.y = math.pi/2
    for p in obj.data.polygons:
        p.use_smooth = len(p.vertices) == 4
    return attach(obj, name, mat, parent)


def apple_logo(cx, y, parent, mat):
    # A small editable bitten-apple silhouette, built with a Bézier outline.
    coords = [(0,.23),(-.19,.28),(-.34,.18),(-.37,-.04),(-.28,-.28),(-.14,-.38),
              (0,-.34),(.14,-.38),(.28,-.26),(.34,-.12),(.23,-.04),(.22,.08),(.32,.18),(.18,.27)]
    for name, pts in [('Apple emblem', coords), ('Apple leaf', [(.015,.29),(.045,.45),(.19,.52),(.16,.37)])]:
        curve = bpy.data.curves.new(name, 'CURVE')
        curve.dimensions, curve.resolution_u = '2D', 16
        curve.fill_mode = 'BOTH'
        spline = curve.splines.new('BEZIER')
        spline.bezier_points.add(len(pts)-1)
        for p, (x,z) in zip(spline.bezier_points, pts):
            p.co = (-x*.78,z*.78,0)
            p.handle_left_type = p.handle_right_type = 'AUTO'
        spline.use_cyclic_u = True
        obj = bpy.data.objects.new(name, curve)
        bpy.context.collection.objects.link(obj)
        obj.location = (cx,y,-.17)
        obj.rotation_euler.x = math.pi/2
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.convert(target='MESH')
        attach(obj, name, mat, parent)


def aim(obj, at, target=(0,0,0)):
    obj.location = at
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--preview', action='store_true')
    opt = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    for folder in ['web/duo/assets','output/duo','renders/duo']:
        (ROOT/folder).mkdir(parents=True,exist_ok=True)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    silver = material('Brushed silver titanium','#cbd0d8',.92,.24)
    chrome = material('Polished chamfer','#e6eaf0',1,.15)
    back = material('Porcelain silver back','#e5e7ec',.35,.3)
    black = material('Obsidian bezel','#07080d',.1,.23)
    antenna = material('Antenna inlay','#a1a5ae',.15,.4)
    lens = material('Sapphire lens','#12243a',.65,.12)
    iris = material('Lens blue reflection','#395e99',.7,.12)
    pearl = material('Flash diffuser','#fcf5d9',.1,.2)
    portrait = material('Inner portrait OLED','#ffffff',0,.62)
    image = bpy.data.images.load(str(ROOT/'web/duo/assets/portrait.jpg'))
    image.pack()
    tex = portrait.node_tree.nodes.new('ShaderNodeTexImage')
    tex.image = image
    shader = portrait.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (.002,.002,.002,1)
    portrait.node_tree.links.new(tex.outputs['Color'],shader.inputs['Emission Color'])
    shader.inputs['Emission Strength'].default_value = .9
    portrait.use_backface_culling = True
    cover = material('Cover OLED','#191827',0,.6)
    s = cover.node_tree.nodes.get('Principled BSDF')
    s.inputs['Emission Color'].default_value = (.032,.025,.07,1)
    s.inputs['Emission Strength'].default_value = .7

    root = group('Duo_Root')
    hinges = []
    for sign, label in [(-1,'Left'),(1,'Right')]:
        cx = sign*(W/2+GAP/2)
        hinge = group('Hinge_'+label,(sign*GAP/2,-T/2-.031,0),root)
        hinges.append(hinge)
        def corners(r):
            return (.045,r,r,.045) if sign<0 else (r,.045,.045,r)
        slab(label+' titanium frame',cx,0,W,H,0,T,corners(.245),silver,hinge,.012)
        slab(label+' front polished rim',cx,0,W-.026,H-.026,-T/2,.018,corners(.232),chrome,hinge,.004)
        slab(label+' black glass surround',cx,0,W-.065,H-.065,-T/2-.012,.014,corners(.213),black,hinge,.003)
        slab(label+' ceramic rear',cx,0,W-.055,H-.055,T/2+.006,.018,corners(.219),back,hinge,.004)
        # Near the center fold, the live picture reaches the hinge; only outer edges have a bezel.
        screen('Display_'+label,cx-sign*.024,W-.067,H-.115,-T/2-.023,portrait,hinge,shared=True)
        cylinder(label+' hinge barrel',(sign*.025,.007,0),.054,H-.48,chrome,hinge,axis='Z')
        for z in [-1.67,1.67]:
            slab(label+' antenna band',cx, z, W+.008,.026,0,T+.002,.01,antenna,hinge,0)
        # Speaker holes and a port along the lower edge.
        for i in range(7):
            cylinder(label+' speaker '+str(i),(cx-.78+i*.105,0,-H/2-.001),.025,.006,black,hinge,axis='Z')
        port = cylinder(label+' USB C',(cx+.35,0,-H/2-.002),.105,.006,black,hinge,axis='Z')
        port.scale = (1.65,.31,1)
        if sign < 0:
            slab('Camera island',cx,1.47,2.31,.82,.145,.12,.24,silver,hinge,.014)
            for i,x in enumerate([cx-.69,cx+.04]):
                cylinder('Camera machined ring '+str(i),(x,.234,1.47),.30,.12,chrome,hinge)
                cylinder('Camera dark surround '+str(i),(x,.30,1.47),.262,.025,black,hinge)
                cylinder('Camera glass '+str(i),(x,.316,1.47),.215,.012,lens,hinge)
                cylinder('Camera optical element '+str(i),(x,.324,1.47),.129,.008,black,hinge)
                cylinder('Camera glint '+str(i),(x-.045,.33,1.535),.042,.008,iris,hinge)
            cylinder('True tone flash',(cx+.73,.221,1.59),.102,.04,pearl,hinge)
            cylinder('Rear microphone',(cx+.73,.22,1.3),.032,.04,black,hinge)
            apple_logo(cx,T/2+.018,hinge,chrome)
        else:
            slab('Cover black surround',cx,0,W-.10,H-.10,T/2+.021,.01,.20,black,hinge,.002)
            screen('Cover_Display',cx,W-.17,H-.17,T/2+.03,cover,hinge,back=True)
            slab('Cover dynamic island',cx,1.80,.65,.17,T/2+.04,.015,.08,black,hinge,.002)
        for z,height in ([(.72,.46),(-.03,.25)] if sign>0 else [(.65,.34),(.10,.34)]):
            slab(label+' side button',sign*(W+GAP/2+.012),z,.035,height,0,.084,.015,chrome,hinge,.005)

    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.frame_start, scene.frame_end = 1, END
    for frame in range(1,END+1):
        f = (frame-1)/(END-1)
        for sign, hinge in zip([-1,1],hinges):
            hinge.rotation_euler.z = -sign*(1-f)*math.pi/2
            hinge.keyframe_insert('rotation_euler',frame=frame)
        root.rotation_euler = (.055,-.065,math.radians(82*(1-f)+5))
        root.location = -(root.rotation_euler.to_matrix() @ Vector((0,-W/2*(1-f),0)))
        root.keyframe_insert('rotation_euler',frame=frame)
        root.keyframe_insert('location',frame=frame)
    for obj in [root,*hinges]:
        for fc in obj.animation_data.action.fcurves:
            for key in fc.keyframe_points:
                key.interpolation = 'LINEAR'
    model_objects = list(scene.objects)
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
    scene.eevee.taa_render_samples = 48
    scene.render.resolution_x, scene.render.resolution_y = 1440,1080
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'AgX'
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.5,.52,.6,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value = .4
    for name,at,power,size,color in [('Key softbox',(-3,-5,7),1000,5,(1,.95,.9)),('Cool edge',(5,2,4),1250,4,(.75,.83,1)),('Front fill',(0,-6,1),400,3,(1,1,1))]:
        bpy.ops.object.light_add(type='AREA')
        obj = bpy.context.object
        obj.name,obj.data.energy,obj.data.size,obj.data.color = name,power,size,color
        aim(obj,at)
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-2.52))
    attach(bpy.context.object,'Studio floor',material('Studio ivory','#eeedf2',0,.7))
    bpy.ops.object.camera_add()
    camera = bpy.context.object
    camera.data.type,camera.data.ortho_scale = 'ORTHO',8.8
    scene.camera = camera
    aim(camera,(.8,-12,4.3))
    scene.frame_set(103)
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'output/duo/duo.blend'))
    if opt.preview:
        for frame,name in [(1,'closed'),(61,'folding'),(121,'open')]:
            scene.frame_set(frame)
            scene.render.filepath = str(ROOT/f'renders/duo/{name}.png')
            bpy.ops.render.render(write_still=True)
    scene.frame_set(1)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in model_objects:
        obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(ROOT/'web/duo/assets/duo.glb'),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='SCENE',export_frame_range=True,export_force_sampling=True,export_cameras=False,export_lights=False,export_extras=True)
    print('DUO_BUILD_COMPLETE',len(model_objects),'objects')


if __name__ == '__main__':
    main()
