"""Sculpt, rig, animate and export a Saber collectible using Blender bpy.
Artist coordinates in this file are (x, height, forward); Blender uses Z up.
"""
from pathlib import Path
import argparse, math, sys
import bpy
from mathutils import Vector, Matrix

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import saber_sculpt
TAU=math.tau
FPS=24
DURATION=16
PARTS=[]
BLINK=[]

def P(p): return Vector((p[0],-p[2],p[1]))
def select_only(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True);bpy.context.view_layer.objects.active=obj
def srgb(x): return x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4
def mat(name, color, metal=0, rough=.45):
    color=color.lstrip('#'); rgb=tuple(srgb(int(color[i:i+2],16)/255) for i in (0,2,4))
    m=bpy.data.materials.new(name);m.diffuse_color=(*rgb,1);m.use_nodes=True
    s=m.node_tree.nodes.get('Principled BSDF');s.inputs['Base Color'].default_value=(*rgb,1)
    s.inputs['Metallic'].default_value=metal;s.inputs['Roughness'].default_value=rough
    return m

def finish(obj,name,m,bone=None,smooth=True):
    obj.name=name
    if m: obj.data.materials.append(m)
    if obj.type=='MESH':
        for f in obj.data.polygons:f.use_smooth=smooth
        if bone: PARTS.append((obj,bone))
    return obj

def mesh(name,verts,faces,m,bone=None,smooth=True):
    data=bpy.data.meshes.new(name);data.from_pydata([P(v) for v in verts],[],faces);data.update()
    obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj)
    return finish(obj,name,m,bone,smooth)

def sphere(name,at,size,m,bone=None):
    small=max(size)<.10
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20 if small else 32,ring_count=12 if small else 20,location=P(at))
    o=bpy.context.object;o.scale=(size[0],size[2],size[1]);return finish(o,name,m,bone)

def cylinder(name,a,b,r1,r2,m,bone=None,vertices=48):
    a,b=P(a),P(b);v=b-a
    bpy.ops.mesh.primitive_cone_add(vertices=vertices,radius1=r1,radius2=r2,depth=v.length,location=(a+b)/2)
    o=bpy.context.object;o.rotation_euler=v.to_track_quat('Z','Y').to_euler();return finish(o,name,m,bone)

def curve(name,points,r,m,bone=None):
    data=bpy.data.curves.new(name,'CURVE');data.dimensions='3D';data.resolution_u=2 if len(points)>10 else 8
    s=data.splines.new('BEZIER');s.bezier_points.add(len(points)-1)
    for p,co in zip(s.bezier_points,points):p.co=P(co);p.handle_left_type='AUTO';p.handle_right_type='AUTO'
    data.bevel_depth=r;data.bevel_resolution=1
    obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj)
    select_only(obj);bpy.ops.object.convert(target='MESH');obj.select_set(False)
    return finish(obj,name,m,bone)

def bezier(c,n=22):
    c=list(map(Vector,c));return [tuple((1-t)**3*c[0]+3*(1-t)**2*t*c[1]+3*(1-t)*t*t*c[2]+t**3*c[3]) for t in [i/(n-1) for i in range(n)]]

def lock(name,control,width,depth,m,bone='head',root_taper=False):
    points=bezier(control,24);verts=[];faces=[]
    for i,p in enumerate(points):
        p=Vector(p);t=i/(len(points)-1)
        tangent=(Vector(points[min(i+1,len(points)-1)])-Vector(points[max(i-1,0)])).normalized()
        right=Vector((1,0,0));right=(right-tangent*right.dot(tangent)).normalized()
        if right.length<.1:right=Vector((0,0,1))
        normal=right.cross(tangent).normalized()
        f=max(.015,math.sin(math.pi*(.18+.82*t))**.70)*(1-.4*t)
        if root_taper:f=max(.006,math.sin(math.pi*t)**.65)*(1-.2*t)
        for j in range(10):
            a=TAU*j/10;v=p+right*math.cos(a)*width*f+normal*math.sin(a)*depth*f;verts.append(v)
    for i in range(len(points)-1):
        for j in range(10):a=i*10+j;b=i*10+(j+1)%10;faces.append((a,a+10,b+10,b))
    faces.extend([tuple(range(10)),tuple((len(points)-1)*10+j for j in reversed(range(10)))])
    return mesh(name,verts,faces,m,bone)

def ring(name,at,r,thickness,m,bone=None):
    steps=96 if r>.5 else 32 if r>.15 else 20
    return curve(name,[(at[0]+r*math.sin(a),at[1],at[2]+r*math.cos(a)) for a in [TAU*i/steps for i in range(steps+1)]],thickness,m,bone)

def rounded(name,at,size,m,bone=None):
    bpy.ops.mesh.primitive_cube_add(size=1,location=P(at));o=bpy.context.object;o.scale=(size[0],size[2],size[1])
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    mod=o.modifiers.new('Cast resin edge','BEVEL');mod.width=.025;mod.segments=3
    bpy.ops.object.modifier_apply(modifier=mod.name);return finish(o,name,m,bone)

def plinth():
    cylinder('Obsidian display plinth',(0,.035,0),(0,.245,0),1.53,1.53,BASE,None,128)
    ring('Brass lower rim',(0,.050,0),1.53,.021,GOLD)
    ring('Brass upper rim',(0,.236,0),1.53,.013,GOLD)
    ring('Engraved inner circle',(0,.249,0),1.35,.004,GOLD)
    for i in range(48):
        a=TAU*i/48;r=1.40;length=.065 if i%4==0 else .025
        curve('Dial engraving',[(r*math.sin(a),.249,r*math.cos(a)),((r+length)*math.sin(a),.249,(r+length)*math.cos(a))],.003,GOLD)
    rounded('Nameplate',(0,.15,1.55),(.76,.15,.045),GOLD)
    data=bpy.data.curves.new('SABER nameplate lettering','FONT');data.body='S A B E R';data.align_x='CENTER';data.size=.092;data.extrude=.0005
    o=bpy.data.objects.new('SABER nameplate lettering',data);bpy.context.collection.objects.link(o)
    o.location=P((0,.117,1.579));o.rotation_euler=(math.pi/2,0,0)
    select_only(o);bpy.ops.object.convert(target='MESH');o.select_set(False);finish(o,o.name,BASE)


def rig_and_animate():
    data=bpy.data.armatures.new('Saber collectible armature');rig=bpy.data.objects.new('SABER_RIG',data);bpy.context.collection.objects.link(rig)
    select_only(rig);bpy.ops.object.mode_set(mode='EDIT')
    specs={'hips':((0,3.35,0),(0,3.65,0),None),'chest':((0,3.50,0),(0,4.34,0),'hips'),'head':((0,4.34,0),(0,5.30,0),'chest'),'skirt':((0,3.38,0),(0,1.1,0),'hips'),'sword':((0,3.44,.62),(0,2.99,.62),None)}
    for s,label in [(-1,'L'),(1,'R')]:
        specs['upper.'+label]=((s*.46,4.14,0),(s*.61,3.72,.13),'chest')
        specs['fore.'+label]=((s*.61,3.72,.13),(s*.105,3.48,.53),'upper.'+label)
        specs['hand.'+label]=((s*.105,3.48,.53),(s*.065,3.36,.61),'fore.'+label)
    for name,(a,b,parent) in specs.items():
        bone=data.edit_bones.new(name);bone.head=P(a);bone.tail=P(b)
        if parent:bone.parent=data.edit_bones[parent]
    bpy.ops.object.mode_set(mode='OBJECT');rig.select_set(False)
    for obj,bone in PARTS:
        g=obj.vertex_groups.new(name=bone);g.add(list(range(len(obj.data.vertices))),1,'REPLACE')
        mod=obj.modifiers.new('Saber pose rig','ARMATURE');mod.object=rig;obj.parent=rig
    blink_keys=[]
    for obj,cy in BLINK:
        select_only(obj);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True);obj.select_set(False)
        obj.shape_key_add(name='Basis');key=obj.shape_key_add(name='Blink')
        for v in key.data:v.co.z=cy+(v.co.z-cy)*.035
        blink_keys.append(key)
    bones=rig.pose.bones
    for b in bones:b.rotation_mode='QUATERNION' if b.name.startswith(('upper.','fore.','hand.','sword')) else 'XYZ'
    rest={name:rig.data.bones[name].matrix_local.copy() for name in specs}
    def pose_curve(t,points):
        for (a,va),(b,vb) in zip(points,points[1:]):
            if a<=t<=b:
                f=(t-a)/(b-a);f=f*f*(3-2*f)
                return tuple(x+(y-x)*f for x,y in zip(va,vb))
        return points[-1][1]
    def aim_bone(name,start,end):
        direction=(rest[name].to_quaternion() @ Vector((0,1,0)))
        rotation=direction.rotation_difference((end-start).normalized()).to_matrix().to_4x4() @ rest[name].to_quaternion().to_matrix().to_4x4()
        rotation.translation=start;bones[name].matrix=rotation
        bpy.context.view_layer.update()
    def grip_with_both_hands(transform):
        # Analytic two-bone IK, baked to ordinary keyframes for glTF. Both hands
        # follow the same sword transform so they stay on the grip during a swing.
        for label in ['L','R']:
            upper,fore,hand=['%s.%s'%(part,label) for part in ['upper','fore','hand']]
            shoulder0,elbow0,wrist0=[rest[n].translation for n in [upper,fore,hand]]
            shoulder=bones['chest'].matrix @ rest['chest'].inverted() @ shoulder0
            wrist=transform @ wrist0
            a=(elbow0-shoulder0).length;b=(wrist0-elbow0).length
            delta=wrist-shoulder;distance=delta.length
            if not abs(a-b)+.001<distance<a+b-.001:raise ValueError(f'Sword pose exceeds arm reach: frame {f}, {label}, {distance:.3f}, reach {a+b:.3f}')
            axis=delta.normalized();along=(a*a-b*b+distance*distance)/(2*distance)
            rest_axis=(wrist0-shoulder0).normalized()
            pole=elbow0-shoulder0;pole-=rest_axis*pole.dot(rest_axis)
            pole=(pole-axis*pole.dot(axis)).normalized()
            elbow=shoulder+axis*along+pole*math.sqrt(max(0,a*a-along*along))
            aim_bone(upper,shoulder,elbow);aim_bone(fore,elbow,wrist)
            bones[hand].matrix=transform @ rest[hand]
            bpy.context.view_layer.update()
    for f in range(1,FPS*DURATION+1):
        t=(f-1)/FPS
        for b in bones:b.matrix_basis=Matrix.Identity(4)
        bones['chest'].rotation_euler[0]=.012*math.sin(t*TAU/4)
        bones['head'].rotation_euler[1]=.035*math.sin(t*TAU/8)
        bones['skirt'].rotation_euler[0]=.009*math.sin(t*1.5)
        angle=dx=dy=dz=0
        if 4<=t<10:
            u=(t-4)/6;p=math.sin(math.pi*u)**2
            angle,dx,dy,dz=pose_curve(t-4,[(0,(0,0,0,0)),(1.8,(-1.95,.14,.44,.05)),(3.5,(-1.95,.14,.44,.05)),(6,(0,0,0,0))])
            bones['head'].rotation_euler[0]=.11*p
            bones['chest'].rotation_euler[1]=-.06*p
        elif t>=10:
            u=(t-10)/6;p=math.sin(math.pi*u)**2
            sweep=math.sin(TAU*u)*p
            angle,dx,dy,dz=pose_curve(t-10,[(0,(0,0,0,0)),(1.8,(-2.9,.05,.72,.16)),(2.6,(-2.9,.05,.72,.16)),(3.05,(-.75,-.10,.30,.12)),(3.7,(-.62,-.10,.18,.10)),(6,(0,0,0,0))])
            bones['chest'].rotation_euler[1]=.17*sweep
            bones['head'].rotation_euler[1]=-.15*sweep
            bones['skirt'].rotation_euler[0]=.025*p
            bones['skirt'].rotation_euler[2]=.025*sweep
        bpy.context.view_layer.update()
        grip=P((0,3.44,.62))
        transform=Matrix.Translation(grip+P((dx,dy,dz))) @ Matrix.Rotation(angle,4,'Y') @ Matrix.Translation(-grip)
        bones['sword'].matrix=transform @ rest['sword']
        grip_with_both_hands(transform)
        for b in bones:
            b.keyframe_insert('rotation_quaternion' if b.rotation_mode=='QUATERNION' else 'rotation_euler',frame=f)
            b.keyframe_insert('location',frame=f)
        blink=max(0,1-abs((t%4)-2.45)/.105)
        for key in blink_keys:key.value=blink;key.keyframe_insert('value',frame=f)
    rig['demo']='Saber • a Blender-built animated collectible'
    rig['clips']='idle:0-4,salute:4-10,excalibur:10-16'
    return rig


def aim(obj,at,target):obj.location=P(at);obj.rotation_euler=(P(target)-obj.location).to_track_quat('-Z','Y').to_euler()
def main():
    global SKIN,BLUSH,IVORY,IVORY_SHADOW,WHITE,LIP,INK,IRIS,IRIS_DARK,IRIS_LIGHT,HAIR,HAIR_LIGHT,HAIR_DARK,BLUE,BLUE_DARK,BLUE_LIGHT,SILVER,STEEL_DARK,GOLD,BASE,BLADE
    p=argparse.ArgumentParser();p.add_argument('--preview',action='store_true');opt=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    for folder in ['output/saber','renders/saber','web/saber/assets']:(ROOT/folder).mkdir(parents=True,exist_ok=True)
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    SKIN=mat('Porcelain skin','#f8dfc8',0,.48);BLUSH=mat('Soft ear blush','#d99e8d');LIP=mat('Painted lips','#ac6a5f');INK=mat('Painted lash ink','#453b32',0,.58)
    IVORY=mat('Ivory silk','#f0ebdd',0,.48);IVORY_SHADOW=mat('Ivory edging','#cfc5a8');WHITE=mat('Eye glaze','#fff9ee',0,.19)
    IRIS=mat('Jade green eyes','#558c63',.10,.25);IRIS_DARK=mat('Deep jade','#183f39',.15,.25);IRIS_LIGHT=mat('Eye jade highlight','#a3bc72',0,.3)
    HAIR=mat('Sculpted blonde hair','#d3a340',0,.48);HAIR_LIGHT=mat('Golden hair highlights','#e0b85e',0,.47);HAIR_DARK=mat('Hair strand shadows','#b38433',0,.52)
    BLUE=mat('Royal blue enamel cloth','#152568',0,.56);BLUE_DARK=mat('Midnight blue details','#111e47',.08,.45);BLUE_LIGHT=mat('Blue silk highlights','#28488a',0,.58)
    SILVER=mat('Polished silver armor','#c5cbd0',.77,.27);STEEL_DARK=mat('Steel engraved edges','#57677b',.72,.33);GOLD=mat('Pale antique gold','#c8ac69',.70,.29);BASE=mat('Midnight lacquer plinth','#202a32',.36,.29);BLADE=mat('EXCALIBUR luminous steel','#e0e6ed',.80,.22)
    saber_sculpt.install(globals())
    plinth();saber_sculpt.skirt();saber_sculpt.torso();saber_sculpt.head();saber_sculpt.arms();saber_sculpt.sword();rig=rig_and_animate()
    model_objects=list(bpy.context.scene.objects)
    scene=bpy.context.scene;scene.render.engine='BLENDER_EEVEE_NEXT';scene.eevee.taa_render_samples=64
    scene.render.resolution_x=1000;scene.render.resolution_y=1200;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
    scene.render.fps=FPS;scene.frame_start=1;scene.frame_end=FPS*DURATION;scene.view_settings.view_transform='AgX'
    scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.6,.57,.50,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.40
    scene.frame_set(1)
    for name,at,power,size,color in [('Key softbox',(-4,8,6),700,5,(1,.88,.72)),('Cool rim',(4,6,-4),950,4,(.68,.78,1)),('Front fill',(1,4,7),240,3,(1,1,1))]:
        bpy.ops.object.light_add(type='AREA');o=bpy.context.object;o.name=name;o.data.energy=power;o.data.shape='DISK';o.data.size=size;o.data.color=color;aim(o,at,(0,3,0))
    bpy.ops.mesh.primitive_plane_add(size=200);ground=bpy.context.object;ground.name='Studio cyclorama';ground.data.materials.append(mat('Warm studio backdrop','#e7e1d4',0,.8))
    bpy.ops.object.camera_add();camera=bpy.context.object;camera.data.type='ORTHO';camera.data.ortho_scale=6.65;scene.camera=camera;aim(camera,(6.3,4.4,11),(0,2.84,0))
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'output/saber/saber.blend'))
    if opt.preview:
        for frame,name,at,target,scale in [(1,'front',(4.6,4.1,11),(0,2.85,0),6.6),(1,'face',(1.8,5.0,8),(0,4.95,0),1.75),(1,'back',(-5,4.4,-10),(0,2.85,0),6.6),(169,'salute',(5,4.6,11),(.5,2.9,0),6.7),(289,'raised',(5,4.6,11),(0,3.6,0),8.7),(313,'action',(5,4.6,11),(0,2.9,0),7.5)]:
            scene.frame_set(frame);aim(camera,at,target);camera.data.ortho_scale=scale;scene.render.filepath=str(ROOT/f'renders/saber/{name}.png');bpy.ops.render.render(write_still=True)
    # Keep the editable .blend intact; merge only the unsaved export representation.
    scene.frame_set(1)
    groups={}
    export_objects=[rig]
    for obj in model_objects:
        if obj.type!='MESH':continue
        if obj.data.shape_keys:export_objects.append(obj);continue
        key=(tuple(m.name for m in obj.data.materials),bool(obj.find_armature()))
        groups.setdefault(key,[]).append(obj)
    for objects in groups.values():
        bpy.ops.object.select_all(action='DESELECT')
        for obj in objects:obj.select_set(True)
        bpy.context.view_layer.objects.active=objects[0]
        if len(objects)>1:bpy.ops.object.join()
        export_objects.append(bpy.context.object)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in export_objects:obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(ROOT/'web/saber/assets/saber.glb'),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='SCENE',export_frame_range=True,export_force_sampling=True,export_cameras=False,export_lights=False,export_morph=True,export_materials='EXPORT',export_extras=True)
    print('SABER_BUILD_COMPLETE',len(export_objects),'export objects')

if __name__=='__main__': main()
