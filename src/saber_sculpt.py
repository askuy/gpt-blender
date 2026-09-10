"""Reference-led Saber sculpt. Dimensions use (x, height, forward).

Study: Good Smile Company, Saber ~Triumphant Excalibur~, product 2780.
The product photographs guide proportions and costume construction; no image
or mesh from the product is embedded in the exported model.
"""
import math
from mathutils import Vector


def install(api):
    """Share the builder's materials/helpers without introducing another scene."""
    for name in ['bpy','P','mesh','sphere','cylinder','curve','ring','lock','rounded',
                 'select_only','PARTS','BLINK','EXPRESSIONS','SKIN','BLUSH','IVORY','IVORY_SHADOW',
                 'WHITE','LIP','INK','IRIS','IRIS_DARK','IRIS_LIGHT','HAIR','HAIR_LIGHT',
                 'HAIR_DARK','BLUE','BLUE_DARK','BLUE_LIGHT','SILVER','STEEL_DARK',
                 'GOLD','BASE','BLADE','mat','srgb']:
        globals()[name]=api[name]


def profile(points,y):
    # Catmull–Rom interpolation keeps the cheek and jaw continuous in profile.
    for i in range(len(points)-1):
        if points[i][0]<=y<=points[i+1][0]:
            t=(y-points[i][0])/(points[i+1][0]-points[i][0])
            p0,p1,p2,p3=points[max(0,i-1)],points[i],points[i+1],points[min(len(points)-1,i+2)]
            return tuple(.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t) for a,b,c,d in zip(p0[1:],p1[1:],p2[1:],p3[1:]))
    return points[0][1:] if y<points[0][0] else points[-1][1:]


def head():
    import saber_portrait
    saber_portrait.install(globals())
    saber_portrait.head()


BODY=[(3.39,.266,.187),(3.54,.273,.193),(3.70,.317,.233),(3.91,.395,.252),(4.10,.377,.197),(4.22,.327,.158),(4.34,.205,.125),(4.42,.122,.110)]


def armor_depth(x,y):
    rx,rz=profile(BODY,y)
    z=rz*max(0,1-(x/rx)**2)**.5+.018
    z+=.042*math.exp(-((abs(x)-.16)/.115)**2-((y-3.98)/.14)**2)
    return z


def surface_path(points,depth):
    result=[]
    for a,b in zip(points,points[1:]):
        for i in range(12):
            t=i/12;x=a[0]+(b[0]-a[0])*t;y=a[1]+(b[1]-a[1])*t
            result.append((x,y,depth(x,y)))
    x,y=points[-1];result.append((x,y,depth(x,y)))
    return result


def torso():
    verts=[];faces=[]
    for i in range(41):
        y=3.34+1.08*i/40;rx,rz=profile(BODY,y)
        for j in range(80):
            a=math.tau*j/80;verts.append((rx*math.sin(a),y,rz*math.cos(a)))
    for i in range(40):
        for j in range(80):a=i*80+j;b=i*80+(j+1)%80;faces.append((a,b,b+80,a+80))
    mesh('Fitted royal-blue tunic',verts,faces,BLUE,'chest')
    # Continuous wrap-around cuirass, with a shaped chest and a narrow waist.
    verts=[];faces=[]
    for i in range(33):
        t=i/32
        for j in range(96):
            a=math.tau*j/96;y=3.51+(4.225-.065*abs(math.sin(a))-3.51)*t
            rx,rz=profile(BODY,y);x=(rx+.013)*math.sin(a)
            z=(armor_depth(min(rx-.0001,max(-rx+.0001,x)),y) if math.cos(a)>=0 else (rz+.018)*math.cos(a))
            verts.append((x,y,z))
    for i in range(32):
        for j in range(96):a=i*96+j;b=i*96+(j+1)%96;faces.append((a,b,b+96,a+96))
    plate=mesh('Sculpted silver cuirass',verts,faces,SILVER,'chest')
    mod=plate.modifiers.new('Plate thickness','SOLIDIFY');mod.thickness=.012;select_only(plate);bpy.ops.object.modifier_apply(modifier=mod.name)
    for row in [0,32]:curve('Cuirass rolled edge',verts[row*96:(row+1)*96]+[verts[row*96]],.006,STEEL_DARK,'chest')
    for sign in [-1,1]:
        for points in [
            [(0,4.220),(.09,3.995),(.265,3.930),(.338,4.140)],
            [(.265,3.905),(.214,3.706),(.275,3.553)],
            [(0,3.89),(.076,3.816),(.214,3.706)],
        ]:
            curve('Cuirass inset panel seam',surface_path([(sign*x,y) for x,y in points],lambda x,y:armor_depth(x,y)+.003),.005,STEEL_DARK,'chest')
        # The small angular blue insignia is painted onto the breastplate.
        for points in [[(.025,3.866),(.090,3.916),(.070,3.845)],[(.025,3.815),(.122,3.807),(.055,3.782)],[(.020,3.774),(.076,3.701),(.032,3.730)]]:
            mesh('Blue breastplate insignia',[(sign*x,y,armor_depth(sign*x,y)+.003) for x,y in points],[(0,1,2)],BLUE_DARK,'chest')
        def tunic_depth(x,y):
            rx,rz=profile(BODY,y)
            return rz*math.sqrt(max(0,1-(x/rx)**2))+.004
        trim=[(sign*x,y) for x,y in [(.105,4.395),(.155,4.347),(.29,4.236)]]
        curve('Tunic collar golden seam',surface_path(trim,tunic_depth),.004,GOLD,'chest')
        curve('Back tunic gold seam',surface_path(trim,lambda x,y:-tunic_depth(x,y)),.004,GOLD,'chest')
        def back_depth(x,y):
            rx,rz=profile(BODY,y)
            return -(rz+.018)*math.sqrt(max(0,1-(x/(rx+.013))**2))-.005
        back=surface_path([(sign*x,y) for x,y in [(0,4.123),(.20,3.998),(.25,3.805),(0,3.69)]],back_depth)
        curve('Back armor panel seam',back,.005,STEEL_DARK,'chest')
    cylinder('Standing blue collar',(0,4.39,0),(0,4.475,0),.126,.105,BLUE,'chest')
    ring('Collar gold binding',(0,4.473,0),.107,.005,GOLD,'chest')
    # Laced waist visible below the silver plate.
    for i in range(4):
        y=3.49-i*.053
        for sign in [-1,1]:
            sphere('Waist eyelet',(sign*.088,y,.205),(.012,.012,.007),SILVER,'hips')
        if i<3:
            curve('Crossed waist lace',[(-.088,y,.214),(.088,y-.053,.218)],.005,STEEL_DARK,'hips')
            curve('Crossed waist lace',[(.088,y,.214),(-.088,y-.053,.218)],.005,STEEL_DARK,'hips')


def skirt_position(t,a,outer=False):
    # Fitted waist, flared lower skirt, and uneven lifted hem replace the cone.
    rx=.30+1.17*t**.92;rz=.20+.87*t**.94
    wave=(.005+.055*t**1.6)*math.cos(14*a+.9*t)+.055*t**3*math.sin(3*a+.6)
    if outer:rx+=.030;rz+=.030
    y=3.39-2.27*t+(.18*math.cos(a-.40)+.25*abs(math.sin(a))**1.5+.13*math.sin(a))*t**2
    if outer:y+=.13*t
    return ((rx+wave)*math.sin(a)+.10*t*t,y,(rz+wave)*math.cos(a)-.08*t*t)


def skirt():
    for outer,material,name in [(False,IVORY,'White pleated petticoat'),(True,BLUE,'Flowing split blue overskirt')]:
        verts=[];faces=[]
        for i in range(37):
            t=i/36;gap=.31+.51*t if outer else 0
            for j in range(129):
                a=gap+(math.tau-2*gap)*j/128
                verts.append(skirt_position(t,a,outer))
        for i in range(36):
            for j in range(128):a=i*129+j;faces.append((a,a+129,a+130,a+1))
        obj=mesh(name,verts,faces,material,'skirt')
        mod=obj.modifiers.new('Thin fabric shell','SOLIDIFY');mod.thickness=.009;select_only(obj);bpy.ops.object.modifier_apply(modifier=mod.name)
        if outer:
            gap=.82
            curve('Overskirt golden hem',[skirt_position(1,gap+(math.tau-2*gap)*j/192,True) for j in range(193)],.008,GOLD,'skirt')
            for sign in [-1,1]:
                curve('Golden open skirt edge',[skirt_position(t,sign*(.31+.51*t),True) for t in [i/40 for i in range(41)]],.007,GOLD,'skirt')
    # Two fine scalloped ruffle layers give the white skirt actual depth.
    for layer in range(2):
        verts=[];faces=[]
        for i in range(6):
            u=i/5
            for j in range(385):
                a=math.tau*j/384;p=Vector(skirt_position(.95+.05*u,a,False))
                scallop=(.5+.5*math.cos(a*48))**2
                p.y-=.025+layer*.065+u*(.035+.045*scallop)
                p.x+=(.026+.042*u)*math.sin(a);p.z+=(.026+.042*u)*math.cos(a)
                verts.append(tuple(p))
        for i in range(5):
            for j in range(384):a=i*385+j;faces.append((a,a+385,a+386,a+1))
        mesh('Scalloped ivory ruffle',verts,faces,IVORY if layer==0 else IVORY_SHADOW,'skirt')
    # Saber wears a long pointed blue front panel over the white underskirt.
    verts=[];faces=[]
    for i in range(41):
        t=i/40;width=.145+.19*math.sin(math.pi*t*.77)
        for j in range(17):
            u=-1+j/8;x=u*width+.10*t*t
            _,y,z=skirt_position(t,0,True)
            y+=.25*abs(u)**1.6*t**5
            z+=.048-.044*u*u+.009*math.cos(u*math.pi*3)*t
            verts.append((x,y,z))
    for i in range(40):
        for j in range(16):a=i*17+j;faces.append((a,a+17,a+18,a+1))
    mesh('Pointed royal-blue front panel',verts,faces,BLUE,'skirt')
    for j in [0,16]:curve('Front panel gold border',[verts[i*17+j] for i in range(41)],.007,GOLD,'skirt')
    curve('Front panel pointed trim',verts[-17:],.007,GOLD,'skirt')
    for sign in [-1,1]:
        for k,(top,bottom) in enumerate([(3.36,2.91),(2.99,2.49),(2.59,2.04)]):
            verts=[];faces=[]
            for i in range(13):
                u=i/12;y=top+(bottom-top)*u
                for j in range(29):
                    v=j/28;a=sign*(.64+1.07*v)
                    lo,hi=0,1
                    for _ in range(14):
                        mid=(lo+hi)/2
                        if skirt_position(mid,a,True)[1]>y:lo=mid
                        else:hi=mid
                    t=(lo+hi)/2
                    x,_,z=skirt_position(t,a,True)
                    verts.append((x+sign*.036*math.sin(abs(a)),y+.08*abs(2*v-1)*u,z+.038*math.cos(a)))
            for i in range(12):
                for j in range(28):a=i*29+j;faces.append((a,a+29,a+30,a+1))
            obj=mesh('Overlapping side tasset %d'%k,verts,faces,SILVER,'skirt')
            mod=obj.modifiers.new('Forged tasset thickness','SOLIDIFY');mod.thickness=.017;select_only(obj);bpy.ops.object.modifier_apply(modifier=mod.name)
            curve('Tasset dark rolled rim',verts[-29:],.009,STEEL_DARK,'skirt')
            for j in [2,26]:sphere('Tasset silver rivet',verts[-29+j],(.015,.015,.014),SILVER,'skirt')
    for sign in [-1,1]:
        start=len(PARTS)
        x=sign*.34
        cylinder('Clothed leg',(x,.38,-.035),(x,2.2,-.035),.105,.15,BLUE_DARK,'hips')
        verts=[];faces=[]
        for i,(y,rx,rz) in enumerate([(.39,.099,.094),(.55,.102,.102),(.88,.132,.116),(1.3,.152,.133),(1.63,.145,.143)]):
            for j in range(48):
                a=math.tau*j/48;verts.append((x+rx*math.sin(a),y,-.020+rz*math.cos(a)))
        for i in range(4):
            for j in range(48):a=i*48+j;b=i*48+(j+1)%48;faces.append((a,b,b+48,a+48))
        mesh('Shaped silver greave',verts,faces,SILVER,'hips')
        sphere('Sculpted knee plate',(x,1.67,.034),(.158,.153,.140),SILVER,'hips')
        curve('Greave front ridge',[(x,.45,.085),(x,.90,.102),(x,1.55,.128)],.005,STEEL_DARK,'hips')
        verts=[];faces=[]
        for z,rx,y,ry in [(-.15,.059,.345,.084),(-.075,.103,.385,.135),(.08,.123,.370,.117),(.25,.109,.323,.070),(.42,.013,.295,.021)]:
            for j in range(48):
                a=math.tau*j/48;verts.append((x+rx*math.cos(a),y+ry*math.sin(a),z))
        for i in range(4):
            for j in range(48):a=i*48+j;b=i*48+(j+1)%48;faces.append((a,b,b+48,a+48))
        faces.extend([tuple(reversed(range(48))),tuple(4*48+j for j in range(48))])
        mesh('Pointed articulated sabaton',verts,faces,SILVER,'hips')
        rounded('Sabatons heel',(x,.295,-.09),(.13,.10,.16),STEEL_DARK,'hips')
        for i in range(3):
            z=.10+.085*i;y=.46-.026*i
            curve('Toe plate seam',[(x-.10,y-.045,z),(x,y,z+.005),(x+.10,y-.045,z)],.005,STEEL_DARK,'hips')
        # Widen the stance with one foot leading. Baking this into the actual
        # geometry preserves the original grip IK and keeps both feet planted.
        bpy.context.view_layer.update()
        for obj,_ in PARTS[start:]:
            transform=obj.matrix_world.copy()
            for vertex in obj.data.vertices:
                p=transform @ vertex.co;y=p.z
                p.x+=sign*max(0,2.20-y)*.090
                p.y-=sign*.15*max(0,2.20-y)/1.9
                vertex.co=p
            obj.matrix_world.identity()


def tube(name,a,b,sections,material,bone,folds=0):
    a,b=Vector(a),Vector(b);axis=(b-a).normalized();right=axis.cross(Vector((0,0,1))).normalized();up=right.cross(axis).normalized()
    vertices=[];faces=[]
    for t,radius in sections:
        center=a.lerp(b,t)
        for j in range(48):
            angle=math.tau*j/48;r=radius*(1+folds*math.cos(7*angle+2*t))
            vertices.append(tuple(center+right*r*math.cos(angle)+up*r*math.sin(angle)))
    for i in range(len(sections)-1):
        for j in range(48):a0=i*48+j;b0=i*48+(j+1)%48;faces.append((a0,a0+48,b0+48,b0))
    faces.extend([tuple(range(48)),tuple((len(sections)-1)*48+j for j in reversed(range(48)))])
    return mesh(name,vertices,faces,material,bone)


def arms():
    for sign,label in [(-1,'L'),(1,'R')]:
        sh=(sign*.46,4.14,0);el=(sign*.61,3.72,.13);wr=(sign*.105,3.48,.53)
        tube('Sewn puff sleeve',sh,el,[(-.17,.09),(0,.16),(.28,.191),(.52,.168),(.79,.116),(1,.102)],BLUE,'upper.'+label,.07)
        tube('Sleeve golden binding',sh,el,[(.71,.128),(.74,.129)],GOLD,'upper.'+label)
        sphere('Armored elbow articulation',el,(.120,.123,.119),STEEL_DARK,'fore.'+label)
        tube('Forearm dark lining',el,wr,[(0,.124),(1,.084)],BLUE_DARK,'fore.'+label)
        for i in range(4):
            t=i*.235
            radius=.140-.043*t
            tube('Layered forged vambrace',el,wr,[(t-.04,radius),(t+.12,radius-.006),(t+.245,radius-.019)],SILVER,'fore.'+label)
            tube('Vambrace rolled edge',el,wr,[(t-.045,radius+.001),(t-.023,radius+.001)],STEEL_DARK,'fore.'+label)
        hand=(sign*.07,3.445,.585)
        sphere('Gauntlet palm',hand,(.095,.081,.069),SILVER,'hand.'+label)
        for i in range(4):
            x=sign*(.020+i*.033)
            sphere('Gauntlet finger upper',(x,3.409,.647),(.019,.038,.024),SILVER,'hand.'+label)
            sphere('Gauntlet finger lower',(x,3.373,.638),(.019,.027,.022),SILVER,'hand.'+label)
            curve('Gauntlet finger joint',[(x-.014,3.396,.669),(x+.014,3.396,.669)],.002,STEEL_DARK,'hand.'+label)
        sphere('Gauntlet thumb',(sign*.105,3.470,.624),(.034,.048,.031),SILVER,'hand.'+label)


def extruded(name,outline,z,thickness,material,bone):
    vertices=[(x,y,z+d) for d in [-thickness/2,thickness/2] for x,y in outline]
    n=len(outline);faces=[tuple(reversed(range(n))),tuple(range(n,n*2))]
    faces.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n))
    obj=mesh(name,vertices,faces,material,bone,False)
    bevel=obj.modifiers.new('Fine forged bevel','BEVEL');bevel.width=.007;bevel.segments=2
    select_only(obj);bpy.ops.object.modifier_apply(modifier=bevel.name)
    return obj


def sword():
    from mathutils import Matrix
    start=len(PARTS);bone='sword';z=.62
    cylinder('Excalibur royal-blue grip',(0,2.98,z),(0,3.49,z),.047,.046,BLUE_DARK,bone,32)
    for i in range(8):ring('Crossed grip binding',(0,3.035+i*.052,z),.048,.005,GOLD,bone)
    extruded('Excalibur faceted pommel',[(-.056,3.46),(-.078,3.52),(-.041,3.57),(.041,3.57),(.078,3.52),(.056,3.46)],z,.081,GOLD,bone)
    verts=[];faces=[]
    for y,width in [(.37,.001),(.61,.067),(2.64,.092),(2.97,.105)]:
        verts.extend([(x,y,z+depth) for x,depth in [(-width,0),(0,.024),(width,0),(0,-.024)]])
    for i in range(3):
        for j in range(4):a=i*4+j;b=i*4+(j+1)%4;faces.append((a,b,b+4,a+4))
    faces.append((12,13,14,15));mesh('EXCALIBUR diamond steel blade',verts,faces,BLADE,bone,False)
    outline=[(-.43,3.13),(-.37,3.16),(-.16,3.00),(-.055,3.025),(.055,3.025),(.16,3.00),(.37,3.16),(.43,3.13),(.235,2.898),(.065,2.932),(-.065,2.932),(-.235,2.898)]
    extruded('Excalibur angular golden crossguard',outline,z,.078,GOLD,bone)
    plaque=[(-.083,2.985),(.083,2.985),(.086,2.735),(0,2.64),(-.086,2.735)]
    extruded('Excalibur heraldic blade collar',plaque,z,.069,GOLD,bone)
    extruded('Blue enamel blade collar',[(-.062,2.968),(.062,2.968),(.065,2.748),(0,2.674),(-.065,2.748)],z+.036,.006,BLUE_DARK,bone)
    for sign in [-1,1]:
        for y in [2.81,2.895]:
            extruded('Gold inlaid diamond',[(sign*.032,y+.020),(sign*.052,y),(sign*.032,y-.020),(sign*.017,y)],z+.043,.002,GOLD,bone)
    # Retain a small jewel as a scale regression landmark, now set into the hilt.
    sphere('Guard sapphire',(0,2.99,z+.048),(.025,.027,.009),IRIS_DARK,bone)
    for i in range(7):
        y=2.55-i*.048
        curve('Etched blade rune',[(-.025,y+.013,z+.019),(0,y-.011,z+.025),(.022,y+.009,z+.019)],.0018,STEEL_DARK,bone)
    bpy.context.view_layer.update()
    pivot=P((0,3.44,z));tilt=Matrix.Translation(pivot) @ Matrix.Rotation(-.255,4,'X') @ Matrix.Translation(-pivot)
    for obj,_ in PARTS[start:]:obj.matrix_world=tilt @ obj.matrix_world
