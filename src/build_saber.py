"""Sculpt, rig, animate and export a Saber collectible using Blender bpy.
Artist coordinates in this file are (x, height, forward); Blender uses Z up.
"""
from pathlib import Path
import argparse, json, math, sys
import bpy
from mathutils import Vector, Matrix

ROOT=Path(__file__).resolve().parents[1]
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
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=20,location=P(at))
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

def lock(name,control,width,depth,m,bone='head'):
    points=bezier(control,24);verts=[];faces=[]
    for i,p in enumerate(points):
        p=Vector(p);t=i/(len(points)-1)
        tangent=(Vector(points[min(i+1,len(points)-1)])-Vector(points[max(i-1,0)])).normalized()
        right=Vector((1,0,0));right=(right-tangent*right.dot(tangent)).normalized()
        if right.length<.1:right=Vector((0,0,1))
        normal=right.cross(tangent).normalized()
        f=max(.015,math.sin(math.pi*(.18+.82*t))**.70)*(1-.4*t)
        for j in range(10):
            a=TAU*j/10;v=p+right*math.cos(a)*width*f+normal*math.sin(a)*depth*f;verts.append(v)
    for i in range(len(points)-1):
        for j in range(10):a=i*10+j;b=i*10+(j+1)%10;faces.append((a,b,b+10,a+10))
    faces.extend([tuple(reversed(range(10))),tuple((len(points)-1)*10+j for j in range(10))])
    return mesh(name,verts,faces,m,bone)

def ring(name,at,r,thickness,m,bone=None):
    return curve(name,[(at[0]+r*math.sin(a),at[1],at[2]+r*math.cos(a)) for a in [TAU*i/96 for i in range(97)]],thickness,m,bone)

def rounded(name,at,size,m,bone=None):
    bpy.ops.mesh.primitive_cube_add(size=1,location=P(at));o=bpy.context.object;o.scale=(size[0],size[2],size[1])
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    mod=o.modifiers.new('Cast resin edge','BEVEL');mod.width=.025;mod.segments=3
    bpy.ops.object.modifier_apply(modifier=mod.name);return finish(o,name,m,bone)

SKIN=None

def head():
    # A continuous custom head surface: jaw, cheeks, forehead and skull.
    rings=[(-.43,.025,.05),(-.37,.17,.16),(-.26,.29,.25),(-.10,.365,.295),(.09,.38,.31),(.29,.34,.28),(.43,.22,.20),(.48,.015,.015)]
    verts=[];faces=[]
    for y,rx,rz in rings:
        for j in range(64):
            a=TAU*j/64;x=rx*math.sin(a);z=rz*math.cos(a)
            if math.cos(a)>0:z+=.016*math.exp(-((y+.1)/.18)**2)*math.cos(a)**8
            verts.append((x,4.90+y,z))
    for i in range(len(rings)-1):
        for j in range(64):a=i*64+j;b=i*64+(j+1)%64;faces.append((a,b,b+64,a+64))
    face=mesh('Saber • sculpted face',verts,faces,SKIN,'head')
    sub=face.modifiers.new('Soft facial planes','SUBSURF');sub.levels=2;bpy.context.view_layer.objects.active=face;bpy.ops.object.modifier_apply(modifier=sub.name)
    for v in face.data.vertices:
        if v.co.y<0:v.co.y-=.034*math.exp(-(v.co.x/.040)**2-((v.co.z-4.75)/.072)**2)
    cylinder('Neck',(0,4.32,0),(0,4.54,0),.13,.12,SKIN,'head')
    for sign in [-1,1]:
        sphere('Ear',(sign*.36,4.80,-.01),(.08,.12,.055),SKIN,'head')
        sphere('Ear inner',(sign*.398,4.81,.027),(.019,.066,.012),BLUSH,'head')
        # Almond-shaped painted eyes lie on the sculpted facial surface.
        cx=sign*.164;cy=4.865
        verts=[(cx,cy,.317-.32*abs(cx)**1.6)];faces=[]
        for i in range(49):
            a=TAU*i/48;dx=.132*math.cos(a);dy=.080*math.sin(a)*(1-.22*abs(math.cos(a)))
            z=.317-.32*abs(cx+dx)**1.6
            verts.append((cx+dx,cy+dy,z))
        for i in range(48):faces.append((0,i+1,i+2))
        eye=mesh('Eye white',verts,faces,IVORY,'head');BLINK.append((eye,cy))
        z=.326-.32*abs(cx)**1.6
        for name,at,size,m in [
            ('Iris dark rim',(cx,cy,z+.004),(.060,.073,.010),IRIS_DARK),
            ('Jade iris',(cx,cy-.004,z+.011),(.047,.064,.008),IRIS),
            ('Iris lower light',(cx,cy-.030,z+.018),(.030,.023,.003),IRIS_LIGHT),
            ('Pupil',(cx,cy+.006,z+.020),(.022,.047,.004),INK),
            ('Eye catchlight',(cx-.017,cy+.030,z+.026),(.016,.019,.003),WHITE),
            ('Eye tiny glint',(cx+.019,cy-.027,z+.025),(.007,.008,.003),WHITE)]:
            o=sphere(name,at,size,m,'head');BLINK.append((o,cy))
        top=[(cx-.130,cy+.005,.317-.32*abs(cx-.13)**1.6),(cx-.070,cy+.073,.325-.32*abs(cx-.07)**1.6),(cx+.042,cy+.081,.325-.32*abs(cx+.042)**1.6),(cx+.131,cy+.015,.319-.32*abs(cx+.131)**1.6)]
        o=curve('Upper painted eyelashes',top,.007,INK,'head');BLINK.append((o,cy))
        curve('Lower eyelid',[(cx-.117,cy-.012,z-.011),(cx,cy-.079,z+.002),(cx+.113,cy-.018,z-.020)],.0025,LIP,'head')
        curve('Golden eyebrow',[(cx-.104,5.010,.288),(cx,5.037,.306),(cx+.105,5.015,.27)],.008,HAIR_DARK,'head')
    curve('Quiet smile',[(-.050,4.625,.263),(0,4.618,.277),(.050,4.627,.263)],.0055,LIP,'head')
    # Hair cap excludes the face; individual shaped locks define the silhouette.
    verts=[];faces=[]
    for i in range(25):
        u=i/24
        for j in range(64):
            a=TAU*j/64;limit=1.25+.95*(1-math.cos(a))/2;theta=.012+u*limit
            verts.append((.409*math.sin(theta)*math.sin(a),4.96+.466*math.cos(theta),.345*math.sin(theta)*math.cos(a)-.018))
    for i in range(24):
        for j in range(64):a=i*64+j;b=i*64+(j+1)%64;faces.append((a,b,b+64,a+64))
    mesh('Golden hair cap',verts,faces,HAIR,'head')
    for i in range(11):
        u=(i-5)/5;x=u*.32;tip=x*1.06+(.025 if i%2 else -.018)
        lock('Sculpted fringe %02d'%i,[(x*.44,5.365,.02),(x*.70,5.34,.31),(x,5.17,.39),(tip,4.996+.045*abs(u)-(.055 if i==6 else 0),.329)],.074,.030,HAIR_LIGHT if i%3==0 else HAIR)
    for s in [-1,1]:
        for i in range(3):
            lock('Cheek framing hair',[(s*(.30+i*.025),5.20,.12),(s*.42,5.02,.19),(s*(.39+i*.015),4.72,.14),(s*(.29+i*.035),4.48+i*.025,.095)],.058,.033,HAIR if i%2 else HAIR_LIGHT)
        for i in range(4):
            lock('Combed back hair',[(s*.06,5.37,-.08),(s*(.26+i*.028),5.27,-.12),(s*.39,4.92,-.23),(s*.19,4.76,-.32)],.047,.017,HAIR_LIGHT if i%2 else HAIR)
    sphere('Braided bun core',(0,4.96,-.376),(.255,.245,.20),HAIR,'head')
    for strand in range(3):
        points=[]
        for i in range(101):
            a=TAU*i/100;phase=a*10+strand*TAU/3;r=.219+.026*math.cos(phase)
            points.append((r*math.cos(a),4.96+r*math.sin(a),-.503+.021*math.sin(phase)))
        curve('Woven crown braid',points,.027,[HAIR,HAIR_LIGHT,HAIR_DARK][strand],'head')
    for s in [-1,1]:
        lock('Blue ribbon loop',[(0,4.82,-.53),(s*.50,5.00,-.57),(s*.44,4.62,-.62),(0,4.81,-.56)],.098,.025,BLUE,'head')
        lock('Trailing blue ribbon',[(s*.035,4.83,-.53),(s*.18,4.52,-.60),(s*.33,4.41,-.46),(s*.35,4.22,-.51)],.075,.016,BLUE,'head')
    sphere('Ribbon knot',(0,4.81,-.57),(.09,.068,.05),BLUE,'head')
    lock('Signature ahoge',[(-.055,5.39,-.035),(-.23,5.76,.01),(.12,5.82,.08),(.16,5.53,.12)],.031,.018,HAIR_LIGHT)


def torso():
    rings=[(3.38,.305,.20),(3.53,.32,.20),(3.83,.445,.263),(4.13,.43,.22),(4.28,.33,.18)]
    verts=[];faces=[]
    for y,rx,rz in rings:
        for j in range(64):a=TAU*j/64;verts.append((rx*math.sin(a),y,rz*math.cos(a)))
    for i in range(4):
        for j in range(64):a=i*64+j;b=i*64+(j+1)%64;faces.append((a,b,b+64,a+64))
    o=mesh('Tailored blue bodice',verts,faces,BLUE,'chest');s=o.modifiers.new('Tailored surface','SUBSURF');s.levels=2;bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=s.name)
    # Smooth silver front shell, gently articulated at the waist.
    verts=[];faces=[]
    for i in range(21):
        t=i/20;y=3.46+.795*t;rx=.32+.13*math.sin(math.pi*t*.85);rz=.216+.075*math.sin(math.pi*t)
        for j in range(49):
            a=-1.44+2.88*j/48
            yy=y+.047*math.cos(a)**2*(1-t)**4-.052*math.cos(a)**2*t**5
            verts.append((rx*math.sin(a),yy,rz*math.cos(a)+.014))
    for i in range(20):
        for j in range(48):a=i*49+j;faces.append((a,a+1,a+50,a+49))
    armor=mesh('Silver cuirass',verts,faces,SILVER,'chest')
    solid=armor.modifiers.new('Cast armor thickness','SOLIDIFY');solid.thickness=.022;bpy.context.view_layer.objects.active=armor;bpy.ops.object.modifier_apply(modifier=solid.name)
    for y,rx,rz in [(3.485,.322,.230),(4.25,.383,.243)]:
        curve('Cuirass edging',[(rx*math.sin(a),y-.040*math.cos(a)**2,rz*math.cos(a)+.020) for a in [-1.43+2.86*j/48 for j in range(49)]],.013,STEEL_DARK,'chest')
    for s in [-1,1]:
        curve('Cuirass fleur engraving',[(0,3.66,.302),(s*.095,3.84,.306),(s*.27,3.98,.236),(s*.27,4.10,.216)],.011,BLUE_DARK,'chest')
        curve('Silver engraved flourish',[(s*.09,3.87,.306),(s*.12,4.045,.279),(s*.045,4.13,.263)],.009,BLUE_DARK,'chest')
        sphere('Shoulder blue puff',(s*.455,4.13,0),(.218,.25,.235),BLUE,'upper.'+('L' if s<0 else 'R'))
        for k in range(3):
            z=(k-1)*.11
            curve('Puff sleeve fold',[(s*.34,4.30,z),(s*.55,4.24,z*1.7),(s*.61,4.02,z)],.010,BLUE_LIGHT,'upper.'+('L' if s<0 else 'R'))
    cylinder('High blue collar',(0,4.22,0),(0,4.36,0),.19,.145,BLUE,'chest')
    ring('Collar silver piping',(0,4.347,0),.15,.011,SILVER,'chest')
    ring('Waist belt',(0,3.44,0),.31,.025,STEEL_DARK,'hips')
    sphere('Belt central clasp',(0,3.43,.230),(.086,.050,.021),GOLD,'hips')


def skirt_position(t,a,outer=False):
    rx=.34+.94*t**.70;rz=.21+.78*t**.77
    fold=(.008+.040*t)*math.cos(16*a+.17*math.sin(t*5))
    if outer:rx+=.034;rz+=.034
    y=3.43-(2.37 if outer else 2.49)*t+.025*t*t*math.cos(16*a)
    return ((rx+fold)*math.sin(a),y,(rz+fold)*math.cos(a))

def skirt():
    for outer,m,name in [(False,IVORY,'Ivory folded underskirt'),(True,BLUE,'Royal blue overskirt')]:
        verts=[];faces=[]
        for i in range(29):
            t=i/28;gap=(.22+.34*t) if outer else 0
            for j in range(97):a=gap+(TAU-2*gap)*j/96;verts.append(skirt_position(t,a,outer))
        for i in range(28):
            for j in range(96):a=i*97+j;faces.append((a,a+1,a+98,a+97))
        o=mesh(name,verts,faces,m,'skirt')
        mod=o.modifiers.new('Fabric thickness','SOLIDIFY');mod.thickness=.012;bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=mod.name)
        gap=.56 if outer else 0
        curve(name+' hem', [skirt_position(1,gap+(TAU-2*gap)*j/128,outer) for j in range(129)],.013,GOLD if outer else IVORY_SHADOW,'skirt')
    for s in [-1,1]:
        curve('Blue dress gold opening', [skirt_position(t,s*(.22+.34*t),True) for t in [j/32 for j in range(33)]],.011,GOLD,'skirt')
        # Three overlapping, shaped silver hip plates.
        for k,(top,bottom) in enumerate([(3.34,2.91),(2.98,2.40),(2.47,1.81)]):
            verts=[];faces=[]
            for i in range(9):
                t=i/8;y=top+(bottom-top)*t
                for j in range(17):
                    u=j/16;a=s*(.63+.61*u);f=(3.43-y)/2.37
                    x,yy,z=skirt_position(f,a,True)
                    verts.append((x+s*.027,y+.10*abs(u-.5)*2*t,z+.020))
            for i in range(8):
                for j in range(16):a=i*17+j;faces.append((a,a+1,a+18,a+17))
            o=mesh('Articulated silver tasset %d'%k,verts,faces,SILVER,'skirt')
            sol=o.modifiers.new('Plate thickness','SOLIDIFY');sol.thickness=.025;bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=sol.name)
            curve('Tasset polished border',verts[-17:],.014,STEEL_DARK,'skirt')
            for j in [2,14]:sphere('Gold armor rivet',verts[17+j],(.022,.022,.018),GOLD,'skirt')
    # The legs are complete geometry below the fabric.
    for s in [-1,1]:
        x=s*.40
        cylinder('Covered leg',(x,.38,0),(x,2.25,0),.145,.18,BLUE_DARK,'hips')
        cylinder('Silver greave',(x,.40,.035),(x,1.05,.02),.13,.16,SILVER,'hips')
        curve('Greave ridge',[(x,.42,.178),(x,.70,.180),(x,1.02,.170)],.012,STEEL_DARK,'hips')
        sphere('Armored foot',(x,.365,.135),(.174,.135,.34),SILVER,'hips')
        for i in range(3):
            z=.19+i*.072
            curve('Sabatons articulated seam',[(x-.14,.38,z),(x,.481-.014*i,z+.020),(x+.14,.38,z)],.008,STEEL_DARK,'hips')


def arms():
    for s,label in [(-1,'L'),(1,'R')]:
        sh=(s*.46,4.14,0);el=(s*.61,3.72,.13);wr=(s*.105,3.48,.53)
        cylinder('Upper sleeve',sh,el,.15,.13,BLUE,'upper.'+label)
        sphere('Elbow joint',el,(.146,.15,.145),STEEL_DARK,'fore.'+label)
        cylinder('Forged vambrace',el,wr,.18,.106,SILVER,'fore.'+label)
        line=[tuple(Vector(el).lerp(Vector(wr),t)) for t in [.16,.5,.87]]
        for c in line:
            v=(Vector(wr)-Vector(el)).normalized();a=Vector(c)-v*.012;b=Vector(c)+v*.012
            cylinder('Vambrace blue seam',a,b,.150-(3.72-c[1])*.22,.150-(3.72-c[1])*.22,BLUE_DARK,'fore.'+label)
        hand=(s*.07,3.445,.585)
        sphere('Gauntlet palm',hand,(.117,.096,.085),SILVER,'hand.'+label)
        for i in range(4):
            x=s*(.027+i*.038)
            sphere('Gauntlet finger upper',(x,3.405,.654),(.023,.046,.029),SILVER,'hand.'+label)
            sphere('Gauntlet finger lower',(x,3.359,.637),(.023,.035,.026),SILVER,'hand.'+label)
            curve('Gauntlet finger crease',[(x-.017,3.392,.677),(x+.017,3.392,.677)],.003,STEEL_DARK,'hand.'+label)
        sphere('Gauntlet thumb',(s*.125,3.472,.629),(.041,.062,.040),SILVER,'hand.'+label)


def sword():
    start=len(PARTS)
    bone='sword';z=.62
    cylinder('Excalibur blue grip',(0,2.98,z),(0,3.49,z),.055,.052,BLUE_DARK,bone,32)
    for i in range(9):ring('Hilt gold wrap',(0,3.03+i*.048,z),.056,.008,GOLD,bone)
    sphere('Golden pommel',(0,3.51,z),(.077,.09,.06),GOLD,bone)
    # Flattened, diamond-section blade: true volume with a central fuller.
    verts=[];faces=[]
    for y,w in [(.35,.001),(.67,.085),(2.85,.092),(2.99,.11)]:
        for x,depth in [(-w,0),(0,.035),(w,0),(0,-.035)]:verts.append((x,y,z+depth))
    for i in range(3):
        for j in range(4):a=i*4+j;b=i*4+(j+1)%4;faces.append((a,b,b+4,a+4))
    faces.append((12,13,14,15));mesh('EXCALIBUR blade',verts,faces,BLADE,bone,False)
    curve('Blade gold central inlay',[(0,.62,z+.035),(0,1.02,z+.036),(0,2.85,z+.036)],.010,GOLD,bone)
    for s in [-1,1]:
        curve('Winged crossguard',[(0,2.99,z),(s*.17,3.01,z),(s*.36,3.08,z),(s*.47,2.98,z)],.058,GOLD,bone)
        curve('Guard blue inset',[(s*.095,3.035,z+.055),(s*.22,3.065,z+.055),(s*.37,3.10,z+.055)],.019,BLUE_DARK,bone)
    sphere('Guard sapphire',(0,3.01,z+.067),(.069,.076,.023),IRIS_DARK,bone)
    # Flush the last sphere's scale before reading matrix_world. Without this,
    # Blender returns the stale unit-sphere matrix and the gem becomes enormous.
    bpy.context.view_layer.update()
    pivot=P((0,3.44,z));tilt=Matrix.Translation(pivot) @ Matrix.Rotation(-.255,4,'X') @ Matrix.Translation(-pivot)
    for obj,_ in PARTS[start:]:obj.matrix_world=tilt @ obj.matrix_world


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
    HAIR=mat('Sculpted blonde hair','#d9b768',.04,.40);HAIR_LIGHT=mat('Golden hair highlights','#ecd394',.04,.37);HAIR_DARK=mat('Hair strand shadows','#a98345',0,.48)
    BLUE=mat('Royal blue enamel cloth','#233f83',.09,.44);BLUE_DARK=mat('Midnight blue details','#14274c',.13,.43);BLUE_LIGHT=mat('Blue silk highlights','#4a639f',.06,.5)
    SILVER=mat('Polished silver armor','#c5cbd0',.77,.27);STEEL_DARK=mat('Steel engraved edges','#57677b',.72,.33);GOLD=mat('Pale antique gold','#c8ac69',.70,.29);BASE=mat('Midnight lacquer plinth','#202a32',.36,.29);BLADE=mat('EXCALIBUR luminous steel','#e0e6ed',.80,.22)
    plinth();skirt();torso();head();arms();sword();rig=rig_and_animate()
    model_objects=list(bpy.context.scene.objects)
    scene=bpy.context.scene;scene.render.engine='BLENDER_EEVEE_NEXT';scene.eevee.taa_render_samples=64
    scene.render.resolution_x=1000;scene.render.resolution_y=1200;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
    scene.render.fps=FPS;scene.frame_start=1;scene.frame_end=FPS*DURATION;scene.view_settings.view_transform='AgX'
    scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.6,.57,.50,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.7
    scene.frame_set(1)
    for name,at,power,size,color in [('Key softbox',(-4,8,6),1100,5,(1,.88,.72)),('Cool rim',(4,6,-4),1500,4,(.68,.78,1)),('Front fill',(1,4,7),550,3,(1,1,1))]:
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
