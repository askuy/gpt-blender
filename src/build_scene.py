"""Build the Niu Lai meme as editable Blender geometry and animation.

Run: Blender --background --python src/build_scene.py -- --preview
All characters, mouth geometry, terrain and animation are generated here.
"""
import argparse
import json
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
FPS = 24
DURATION = 14
random.seed(19)


def args():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument('--preview', action='store_true')
    p.add_argument('--render', action='store_true')
    p.add_argument('--no-export', action='store_true')
    return p.parse_args(argv)


def material(name, color, roughness=.6, noise=0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    n = mat.node_tree.nodes
    shader = n.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*color, 1)
    shader.inputs['Roughness'].default_value = roughness
    if noise:
        tex = n.new('ShaderNodeTexNoise')
        tex.inputs['Scale'].default_value = 90
        tex.inputs['Detail'].default_value = 2
        bump = n.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value = noise
        bump.inputs['Distance'].default_value = .025
        mat.node_tree.links.new(tex.outputs['Fac'], bump.inputs['Height'])
        mat.node_tree.links.new(bump.outputs['Normal'], shader.inputs['Normal'])
    return mat


def parent(obj, target):
    if target:
        obj.parent = target
    return obj


def empty(name, at=(0, 0, 0), target=None):
    obj = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(obj)
    obj.location = at
    return parent(obj, target)


def finish(obj, name, mat, target=None):
    obj.name = name
    if mat:
        obj.data.materials.append(mat)
    if obj.type == 'MESH':
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
    return parent(obj, target)


def ellipsoid(name, at, size, mat, target=None, segments=40, rings=24):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, location=at)
    obj = finish(bpy.context.object, name, mat, target)
    obj.scale = size
    return obj


def rounded_box(name, at, size, mat, target=None, bevel=.06):
    bpy.ops.mesh.primitive_cube_add(size=1, location=at)
    obj = bpy.context.object
    obj.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    mod = obj.modifiers.new('Soft sculpted edges', 'BEVEL')
    mod.width = bevel
    mod.segments = 3
    bpy.ops.object.modifier_apply(modifier=mod.name)
    return finish(obj, name, mat, target)


def tube(name, coords, radii, mat, target=None, sides=12):
    verts, faces = [], []
    points = [Vector(x) for x in coords]
    previous_u = None
    for i, p in enumerate(points):
        tangent = (points[min(i + 1, len(points) - 1)] - points[max(i - 1, 0)]).normalized()
        axis = Vector((0, 0, 1)) if abs(tangent.z) < .92 else Vector((0, 1, 0))
        u = tangent.cross(axis).normalized() if previous_u is None else (previous_u-tangent*previous_u.dot(tangent)).normalized()
        previous_u = u
        v = tangent.cross(u).normalized()
        for j in range(sides):
            a = j * math.tau / sides
            verts.append(p + radii[i] * (u * math.cos(a) + v * math.sin(a)))
    for i in range(len(points) - 1):
        for j in range(sides):
            a, b = i*sides+j, i*sides+(j+1)%sides
            faces.append((a, b, b+sides, a+sides))
    faces.extend([tuple(reversed(range(sides))), tuple((len(points)-1)*sides+j for j in range(sides))])
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return finish(obj, name, mat, target)


def curve_points(control, count=30):
    # Cubic Bezier, used for soft horns, brows, tails and flower stems.
    a, b, c, d = map(Vector, control)
    return [(1-t)**3*a + 3*(1-t)**2*t*b + 3*(1-t)*t*t*c + t**3*d for t in [i/(count-1) for i in range(count)]]


def mouth_mesh(name, head, lip, cavity):
    # Sculpted elliptical lip, with a matching inset bowl. The top stays fixed
    # while the jaw drops. This is geometry with a real opening shape key.
    def ring(height):
        out = []
        for i in range(64):
            a = math.tau*i/64
            for j in range(12):
                b = math.tau*j/12
                thickness = .076 + .026*max(0, -math.sin(a))
                out.append(((.485 + thickness*math.cos(b))*math.cos(a),
                            -1.004 - .065*math.sin(b),
                            -.54-height+(height+thickness*math.cos(b))*math.sin(a)))
        return out

    verts = ring(.06)
    faces = []
    for i in range(64):
        for j in range(12):
            faces.append((i*12+j, ((i+1)%64)*12+j, ((i+1)%64)*12+(j+1)%12, i*12+(j+1)%12))
    mesh = bpy.data.meshes.new(name+' lips')
    mesh.from_pydata(verts, [], faces)
    obj = bpy.data.objects.new(name+' lips', mesh)
    bpy.context.collection.objects.link(obj)
    finish(obj, name+' lips', lip, head)
    obj.shape_key_add(name='Basis')
    key = obj.shape_key_add(name='MAMA')
    for v, co in zip(key.data, ring(.43)):
        v.co = co

    def bowl(height):
        out = [(0, -.93, -.54-height)]
        for k in range(1, 9):
            r = k/8
            for i in range(64):
                a = math.tau*i/64
                out.append((.49*r*math.cos(a), -.93-.075*r*r, -.54-height+height*r*math.sin(a)))
        return out

    faces = [(0, 1+i, 1+(i+1)%64) for i in range(64)]
    for k in range(7):
        for i in range(64):
            a, b = 1+k*64+i, 1+k*64+(i+1)%64
            faces.append((a, a+64, b+64, b))
    mesh = bpy.data.meshes.new(name+' mouth cavity')
    mesh.from_pydata(bowl(.06), [], faces)
    dark = bpy.data.objects.new(name+' mouth cavity', mesh)
    bpy.context.collection.objects.link(dark)
    finish(dark, dark.name, cavity, head)
    dark.shape_key_add(name='Basis')
    dark_key = dark.shape_key_add(name='MAMA')
    for v, co in zip(dark_key.data, bowl(.43)):
        v.co = co
    # Outer jaw volume attaches the lip to the head in every camera angle.
    def jaw_shell(height):
        result=[]
        for layer in range(9):
            t=layer/8
            for i in range(64):
                a=math.tau*i/64
                radius=.53*(1-t)+.45*t
                h=(height+.085)*(1-t)+(.22+height*.45)*t
                result.append((radius*math.cos(a),-.975+.67*t,-.54-height+.20*t+h*math.sin(a)))
        return result
    faces=[]
    for layer in range(8):
        for i in range(64):
            a=layer*64+i;b=layer*64+(i+1)%64
            faces.append((a,b,b+64,a+64))
    mesh=bpy.data.meshes.new(name+' jaw volume');mesh.from_pydata(jaw_shell(.06),[],faces)
    jaw=bpy.data.objects.new(name+' jaw volume',mesh);bpy.context.collection.objects.link(jaw)
    finish(jaw,jaw.name,lip,head)
    jaw.shape_key_add(name='Basis');jaw_key=jaw.shape_key_add(name='MAMA')
    for v,co in zip(jaw_key.data,jaw_shell(.43)):v.co=co
    return [key, dark_key, jaw_key]


def cow(name, at, color, adult=False):
    fur = material(name+' ochre clay', color, .72, .17)
    pink = material(name+' warm muzzle', (.68, .34, .25), .58, .05)
    inner = material(name+' inner ears', (.57, .26, .19), .7)
    hornmat = material(name+' horn ivory', (.39, .27, .16), .66, .2)
    dark = material(name+' mouth velvet', (.070, .013, .022), .95)
    eye_white = material(name+' eye whites', (.93, .88, .74), .27)
    iris_mat = material(name+' iris', (.12, .078, .044), .26)
    pupil_mat = material(name+' pupils', (.007, .010, .014), .2)
    brow_mat = material(name+' eyebrow', (.105, .043, .018), .8)
    teeth_mat = material(name+' teeth', (.90, .82, .62), .42)
    tongue_mat = material(name+' tongue', (.53, .15, .19), .66)
    hoof_mat = material(name+' hooves', (.12, .09, .065), .66)
    nostril_mat = material(name+' nostril shadow', (.26,.095,.064),.88)
    root = empty(name, at)

    if not adult:
        body = ellipsoid(name+' torso', (0, .10, 1.40), (.65, .48, .96), fur, root)
        for sign in [-1, 1]:
            arm = ellipsoid(name+' arm', (sign*.71, -.01, 1.42), (.22, .24, .7), fur, root)
            arm.rotation_euler[1] = sign*-.19
            hand = ellipsoid(name+' hand', (sign*.82, -.1, .9), (.22, .22, .25), hoof_mat, root)
            ellipsoid(name+' shin', (sign*.28, .12, .45), (.21, .24, .47), fur, root)
            rounded_box(name+' split hoof', (sign*.28, -.035, .13), (.44, .60, .26), hoof_mat, root)
            rounded_box(name+' hoof seam', (sign*.28, -.341, .13), (.02, .014, .15), brow_mat, root, .006)
        head = empty(name+' head', (0, -.02, 2.86), root)
    else:
        ellipsoid(name+' barrel', (0, .62, 1.41), (.78, 1.23, .79), fur, root)
        ellipsoid(name+' shoulder', (0, -.04, 1.69), (.68, .59, .84), fur, root)
        for x in [-.48, .48]:
            for y in [-.2, 1.33]:
                ellipsoid(name+' leg', (x, y, .68), (.22, .24, .72), fur, root)
                rounded_box(name+' hoof', (x, y-.05, .13), (.43, .51, .26), hoof_mat, root)
        tail = tube(name+' tail', curve_points([(0, 1.7, 1.9),(.4,2.1,1.6),(.25,2.0,.8),(.5,2.0,.65)]), [.065]*30, fur, root)
        ellipsoid(name+' tail tuft', (.5, 2.0, .65), (.12,.13,.25), hornmat, root)
        head = empty(name+' head', (0, -.57, 2.52), root)
        head.scale = (1.1, 1.1, 1.1)

    ellipsoid(name+' head sculpt', (0, .0, .0), (.79, .63, 1.00), fur, head, 64, 40)
    ellipsoid(name+' cheek L', (-.5, -.3, -.28), (.30, .33, .53), fur, head)
    ellipsoid(name+' cheek R', (.5, -.3, -.28), (.30, .33, .53), fur, head)
    ellipsoid(name+' muzzle bridge', (0, -.62, -.21), (.49, .35, .44), fur, head)
    ellipsoid(name+' pink nose', (0, -.80, -.29), (.49, .27, .32), pink, head, 48, 32)
    for sign in [-1, 1]:
        nostril = ellipsoid(name+' nostril', (sign*.20, -1.056, -.22), (.072, .012, .038), nostril_mat, head)
        nostril.rotation_euler[1] = sign*-.24
        ear = ellipsoid(name+' ear', (sign*.88, .01, .34), (.35, .145, .22), fur, head)
        ear.rotation_euler[1] = sign*-.47
        ear_inner = ellipsoid(name+' ear inside', (sign*.9, -.12, .35), (.225, .035, .127), inner, head)
        ear_inner.rotation_euler[1] = sign*-.47
        points = curve_points([(sign*.59,.09,.65),(sign*1.0,.14,.92),(sign*1.05,.10,1.32),(sign*.99,.08,1.46)])
        tube(name+' curved horn', points, [.18*(1-i/29)**.65+.008 for i in range(30)], hornmat, head, 20)
        ellipsoid(name+' eye white', (sign*.36, -.552, .22), (.243, .127, .202), eye_white, head)
        ellipsoid(name+' iris', (sign*.335, -.666, .22), (.124, .038, .133), iris_mat, head)
        ellipsoid(name+' pupil', (sign*.326, -.699, .23), (.077, .018, .092), pupil_mat, head)
        ellipsoid(name+' eye glint', (sign*.326-.026, -.716, .277), (.024, .008, .027), eye_white, head, 20, 12)
        if adult:
            ellipsoid(name+' unimpressed eyelid', (sign*.36,-.557,.355),(.257,.142,.109),fur,head)
            controls = [(sign*.12,-.58,.57),(sign*.24,-.64,.61),(sign*.52,-.52,.55),(sign*.66,-.4,.55)]
        else:
            controls = [(sign*.10,-.59,.63),(sign*.24,-.60,.76),(sign*.5,-.52,.43),(sign*.64,-.41,.47)]
        tube(name+' expressive brow', curve_points(controls), [.038]*30, brow_mat, head, 10)

    mouth_keys = mouth_mesh(name, head, pink, dark)
    lower = empty(name+' lower jaw teeth', (0, 0, 0), head)
    upper = empty(name+' upper teeth', (0,0,0),head)
    for i in range(7):
        x=(i-3)*.113
        z=-.635-.045*(abs(x)/.36)**2
        rounded_box(name+' upper tooth', (x, -1.022, z), (.107,.062,.078), teeth_mat, upper, .023)
        rounded_box(name+' lower tooth', (x, -1.027, -.595+.055*(abs(x)/.36)**2), (.107,.065,.092), teeth_mat, lower, .024)
    tongue=ellipsoid(name+' tongue', (0,-.983,-.59), (.21,.06,.055), tongue_mat, lower)
    return {'root':root,'head':head,'mouth_keys':mouth_keys,'lower':lower,'upper':upper,'tongue':tongue, 'adult':adult}


def snake(at):
    root=empty('THE SNAKE',at)
    skin=material('Snake jade',(.105,.205,.117),.52,.13)
    belly=material('Snake peach belly',(.61,.29,.25),.67)
    black=material('Snake eyes',(.008,.012,.008),.25)
    golden=material('Snake amber',(.65,.37,.055),.34)
    coords=[]
    for i in range(65):
        t=i/64
        coords.append((.72*math.cos(t*math.tau*1.7)*(1-t),.67*math.sin(t*math.tau*1.7)*(1-t)+.4,.17+2.00*t**3))
    tube('Snake coiled body',coords,[.06+.15*math.sin(math.pi*i/128) for i in range(65)],skin,root,18)
    head=empty('Snake sway',(0,.4,2.10),root)
    hood=ellipsoid('Cobra hood',(0,.09,-.28),(.48,.15,.64),skin,head)
    ellipsoid('Cobra hood lining',(0,-.046,-.27),(.35,.026,.53),belly,head)
    ellipsoid('Snake head',(0,-.01,.15),(.255,.30,.23),skin,head)
    for s in [-1,1]:
        ellipsoid('Snake eye',(s*.19,-.23,.21),(.073,.045,.067),golden,head,24,16)
        ellipsoid('Snake slit',(s*.19,-.271,.21),(.016,.01,.049),black,head,20,12)
    tube('Snake tongue',[(0,-.26,.04),(0,-.45,.02),(-.06,-.52,.015)],[.018,.014,.003],belly,head)
    tube('Snake tongue fork',[(0,-.43,.02),(.06,-.52,.015)],[.014,.003],belly,head)
    return head


def world():
    soil=material('Meadow moss',(.21,.285,.105),.92,.12)
    grassmats=[material('Grass '+str(i),c,.88) for i,c in enumerate([(.15,.24,.055),(.29,.36,.095),(.41,.43,.16)])]
    rockmat=material('Warm limestone',(.40,.385,.27),.87,.25)
    # Rounded landscape, with a large seamless plane underneath for orbiting.
    ellipsoid('Rolling meadow',(0,0,-.46),(18,18,.5),soil,segments=80,rings=32)
    for x,y,s in [(-11,10,5),(7,13,6),(13,9,5),(-16,5,4)]:
        ellipsoid('Distant velvet hill',(x,y,.15),(s,s*.8,s*.34),soil,segments=40,rings=24)
    for x,y,s in [(-3.4,.4,.55),(4.3,.4,.7),(1.5,3.9,.46),(-1.6,3,.3)]:
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2,radius=1,location=(x,y,s*.35))
        obj=finish(bpy.context.object,'Meadow limestone',rockmat)
        obj.scale=(s,s*.73,s*.58)
        bevel=obj.modifiers.new('Eroded stone','BEVEL');bevel.width=.08;bevel.segments=2
    # Combined blade mesh instead of hundreds of separate objects.
    verts,faces,indices=[],[],[]
    for i in range(1150):
        x=random.uniform(-11,11);y=random.uniform(-7,12)
        if (-2.4<x<.2 and -1.2<y<1.3) or (1<x<3.1 and -.1<y<3):continue
        z=.035-.0015*(x*x+y*y)
        height=random.uniform(.065,.23)
        a=random.uniform(0,math.tau);dx=.03*math.cos(a);dy=.03*math.sin(a)
        start=len(verts)
        verts.extend([(x-dx,y-dy,z),(x+dx,y+dy,z),(x+.045*math.sin(a),y+.025,z+height)])
        faces.append((start,start+1,start+2));indices.append(random.randrange(3))
    mesh=bpy.data.meshes.new('Meadow blades');mesh.from_pydata(verts,[],faces)
    obj=bpy.data.objects.new('Meadow blades',mesh);bpy.context.collection.objects.link(obj)
    for m in grassmats:mesh.materials.append(m)
    for p,i in zip(mesh.polygons,indices):p.material_index=i
    petal=material('Tiny daisies',(.92,.84,.60),.8)
    center=material('Daisy gold',(.8,.41,.06),.8)
    for x,y in [(-2.7,-1.1),(1.5,-1.4),(3.2,2.4),(-3.2,2.1),(.7,3.8),(-.1,-2.4)]:
        tube('Daisy stem',[(x,y,0),(x+.03,y,.23)],[.011,.008],grassmats[0],sides=6)
        ellipsoid('Daisy center',(x+.03,y,.235),(.04,.04,.03),center,segments=16,rings=8)
        for j in range(6):
            a=j*math.tau/6
            pet=ellipsoid('Daisy petal',(x+.03+.062*math.cos(a),y+.062*math.sin(a),.23),(.061,.025,.014),petal,segments=12,rings=8)
            pet.rotation_euler[2]=a


def point_camera(camera, at, target):
    camera.location=at
    camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()


def lerp(a,b,t):return tuple(x+(y-x)*t for x,y in zip(a,b))
def smooth(t):return max(0,min(1,t))**2*(3-2*max(0,min(1,t)))


def camera_pose(t):
    calf_pos=(-1.2,-5.85,3.3);calf_target=(-1.2,-.08,2.68)
    mom_pos=(5.5,-4.07,3.1);mom_target=(2.4,.28,2.55)
    if t<3.7:
        return lerp(calf_pos,(-1.2,-5.45,3.28),smooth(t/3.7)),calf_target,52
    if t<5.65:return mom_pos,mom_target,49
    if t<7.4:
        f=smooth((t-5.65)/1.75)
        return lerp(mom_pos,(7.5,-9.0,5.5),f),lerp(mom_target,(.1,.55,1.7),f),49-7*f
    if t<11.1:
        a=-.88+smooth((t-7.4)/3.7)*1.43
        return (11.2*math.cos(a),11.2*math.sin(a)+.6,5.1),(.1,.55,1.7),42
    f=smooth((t-11.1)/1.2)
    a=.55+(-math.pi/2-.55)*f
    radius=11.2+(5.77-11.2)*f
    center=lerp((0,.6),(-1.2,-.08),f)
    return (center[0]+radius*math.cos(a),center[1]+radius*math.sin(a),5.1+(3.3-5.1)*f),lerp((.1,.55,1.7),calf_target,f),42+10*f


def animate(calf,mom,snake_head,camera):
    data=json.loads((ROOT/'src/audio-envelope.json').read_text())
    envelope=data['samples']
    def amplitude(source_t):
        idx=int(source_t*50)
        values=envelope[max(0,idx-2):idx+3]
        return min(1,max(values,default=0)*10)**.6
    cameras=[]
    for f in range(1,FPS*DURATION+1):
        t=(f-1)/FPS
        source_t=t+3.9
        if 12.25<t<14:source_t=4.3+(t-12.25)
        a=amplitude(source_t) if (t<3.4 or t>12.25) else 0
        b=amplitude(t+3.9) if 4.35<t<5.65 else 0
        for rig,value in [(calf,a),(mom,b)]:
            if rig['adult']:value*=.36
            jaw=.04+.94*value
            for key in rig['mouth_keys']:
                key.value=jaw;key.keyframe_insert('value',frame=f)
            rig['lower'].location.z=-.74*jaw
            rig['lower'].keyframe_insert('location',frame=f)
            rig['upper'].location.y=.15*(1-smooth(value*6))
            rig['upper'].keyframe_insert('location',frame=f)
            rig['tongue'].scale.z=.055+.09*value
            rig['tongue'].keyframe_insert('scale',frame=f)
        calf['head'].rotation_euler=(.035*math.sin(t*3)+.045*a,.027*math.sin(t*4),.027*math.sin(t*2))
        calf['head'].keyframe_insert('rotation_euler',frame=f)
        calf['root'].location.z=.015*math.sin(t*3)+.023*a
        calf['root'].keyframe_insert('location',frame=f)
        mom['head'].rotation_euler[2]=-.55+.58*smooth((t-3.7)/.75)
        mom['head'].rotation_euler[0]=-.015+.025*b
        mom['head'].keyframe_insert('rotation_euler',frame=f)
        snake_head.rotation_euler[1]=.09*math.sin(t*2)
        snake_head.keyframe_insert('rotation_euler',frame=f)
        at,target,lens=camera_pose(t)
        point_camera(camera,at,target)
        camera.keyframe_insert('location',frame=f)
        camera.keyframe_insert('rotation_euler',frame=f)
        camera.data.lens=lens;camera.data.keyframe_insert('lens',frame=f)
        cameras.append({'time':t,'position':[at[0],at[2],-at[1]],'target':[target[0],target[2],-target[1]],'fov':math.degrees(2*math.atan(36/(2*lens)))})
    (ROOT/'web/assets/cameras.json').write_text(json.dumps({'fps':FPS,'duration':DURATION,'frames':cameras}))
    # Linear interpolation keeps exported morph tracks identical to the source.
    for action in bpy.data.actions:
        try:
            for fc in action.fcurves:
                for key in fc.keyframe_points:key.interpolation='LINEAR'
        except AttributeError:pass


def main():
    opt=args()
    for folder in ['output', 'renders', 'web/assets']:
        (ROOT / folder).mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    scene=bpy.context.scene
    scene.render.engine='BLENDER_EEVEE_NEXT'
    scene.eevee.taa_render_samples=64
    scene.render.use_persistent_data=True
    scene.render.resolution_x=1080;scene.render.resolution_y=1080;scene.render.resolution_percentage=100
    scene.render.fps=FPS
    scene.render.image_settings.file_format='PNG'
    scene.render.image_settings.color_mode='RGB'
    scene.render.image_settings.compression=25
    scene.frame_start=1;scene.frame_end=FPS*DURATION
    scene.view_settings.view_transform='AgX'
    scene.view_settings.look='AgX - Medium High Contrast'
    scene.world.use_nodes=True
    scene.world.node_tree.nodes.get('Background').inputs[0].default_value=(.52,.66,.72,1)
    scene.world.node_tree.nodes.get('Background').inputs[1].default_value=.65
    scene.render.film_transparent=False
    world()
    calf=cow('NIU LAI',(-1.2,-.05,0),(.48,.12,.012))
    mom=cow('MAMA',(2.3,1.25,0),(.70,.34,.018),adult=True)
    mom['root'].rotation_euler[2]=.23
    s=snake((-3.1,-1.35,0))
    # The snake is just out of the original close-up and revealed in the orbit.
    s.parent.rotation_euler[2]=math.pi*.7
    bpy.ops.object.light_add(type='AREA',location=(-3,-5,8))
    key=bpy.context.object;key.name='Large softbox / late afternoon';key.data.energy=1350;key.data.shape='DISK';key.data.size=5
    key.rotation_euler=(Vector((0,0,1.8))-key.location).to_track_quat('-Z','Y').to_euler()
    bpy.ops.object.light_add(type='AREA',location=(4,3,6))
    rim=bpy.context.object;rim.name='Warm rim';rim.data.energy=950;rim.data.color=(1,.79,.48);rim.data.size=4
    rim.rotation_euler=(Vector((0,0,2))-rim.location).to_track_quat('-Z','Y').to_euler()
    bpy.ops.object.camera_add()
    camera=bpy.context.object;camera.name='Meme camera';camera.data.sensor_width=36;scene.camera=camera
    animate(calf,mom,s,camera)
    scene.frame_set(32)
    # Resolve output relative to output/niulai.blend when the saved file is moved.
    scene.render.filepath='//../renders/frame_'
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'output/niulai.blend'))
    if not opt.no_export:
        bpy.ops.export_scene.gltf(filepath=str(ROOT/'web/assets/niulai.glb'),export_format='GLB',export_animations=True,
            export_animation_mode='SCENE',export_frame_range=True,export_force_sampling=True,
            export_cameras=False,export_lights=False,export_morph=True,export_materials='EXPORT')
    if opt.preview:
        for frame,name in [(32,'calf'),(119,'mother'),(211,'orbit')]:
            scene.frame_set(frame);scene.render.filepath=str(ROOT/'renders'/('preview-'+name+'.png'))
            bpy.ops.render.render(write_still=True)
    if opt.render:
        scene.render.filepath=str(ROOT/'renders/frame_')
        bpy.ops.render.render(animation=True)
    print('NIULAI_BUILD_COMPLETE')


if __name__=='__main__':main()
