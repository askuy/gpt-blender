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
                 'select_only','PARTS','BLINK','SKIN','BLUSH','IVORY','IVORY_SHADOW',
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


FACE=[(4.535,.026,.110,.040),(4.57,.078,.169,.068),(4.63,.168,.212,.135),
      (4.72,.249,.247,.209),(4.82,.296,.257,.246),(4.94,.311,.251,.267),
      (5.07,.306,.236,.263),(5.19,.258,.196,.231),(5.28,.132,.096,.127),(5.317,.006,.009,.009)]


def face_depth(x,y):
    rx,front,_=profile(FACE,y)
    z=front*max(0,1-(x/max(rx,.001))**2)**.28
    z+=.019*math.exp(-(x/.023)**2-((y-4.765)/.032)**2)
    z+=.008*math.exp(-(x/.034)**2-((y-4.81)/.060)**2)
    z+=.007*math.exp(-(x/.072)**2-((y-4.665)/.043)**2)
    return z


def paint(name,vertices,faces,color,bone='head',blink_y=None):
    obj=mesh(name,vertices,faces,color,bone)
    if blink_y is not None:BLINK.append((obj,blink_y))
    return obj


def disk(name,cx,cy,rx,ry,depth,material,blink_y=None):
    vertices=[(cx,cy,face_depth(cx,cy)+depth)]
    for i in range(49):
        a=math.tau*i/48;x=cx+rx*math.cos(a);y=cy+ry*math.sin(a)
        vertices.append((x,y,face_depth(x,y)+depth))
    return paint(name,vertices,[(0,i+1,i+2) for i in range(48)],material,blink_y=blink_y)


def hair_piece(name,control,width,depth=.024,grooves=2):
    obj=lock(name,control,width,depth,HAIR,'head',root_taper=True)
    # Fine grooves follow the same sculpted clump rather than painting stripes.
    c=list(map(Vector,control))
    for j in range(grooves):
        points=[];offset=(j-(grooves-1)/2)*width*.38
        for i in range(18):
            t=.10+.78*i/17;v=(1-t)**3*c[0]+3*(1-t)**2*t*c[1]+3*(1-t)*t*t*c[2]+t**3*c[3]
            v.x+=offset*math.sin(math.pi*(.18+.82*t))**.7
            v.z+=depth*.78
            points.append(tuple(v))
        curve(name+' strand groove',points,.0016,HAIR_DARK,'head')
    return obj


def head():
    verts=[];faces=[]
    for i in range(81):
        y=4.535+(5.317-4.535)*i/80;rx,front,back=profile(FACE,y)
        for j in range(96):
            a=math.tau*j/96;x=rx*math.sin(a)
            z=face_depth(x,y) if math.cos(a)>=0 else back*math.cos(a)
            verts.append((x,y,z))
    for i in range(80):
        for j in range(96):a=i*96+j;b=i*96+(j+1)%96;faces.append((a,b,b+96,a+96))
    mesh('Saber sculpt — tapered jaw and facial planes',verts,faces,SKIN,'head')
    cylinder('Slender neck',(0,4.31,0),(0,4.65,-.012),.106,.092,SKIN,'head')
    for sign in [-1,1]:
        sphere('Ear',(sign*.301,4.795,-.015),(.047,.079,.036),SKIN,'head')
        sphere('Ear concha',(sign*.325,4.797,.011),(.020,.048,.010),BLUSH,'head')
        inner=.062;outer=.247;cy=4.887
        def eye_y(x,top):
            u=max(0,min(1,(abs(x)-inner)/(outer-inner)))
            return cy+.025*u+(.053 if top else -.033)*math.sin(math.pi*u)**.85
        # Painted almond opening conforms to the cheek. No protruding eyeballs.
        verts=[];faces=[]
        for i in range(49):
            x=sign*(inner+(outer-inner)*i/48)
            for k in range(9):
                y=eye_y(x,False)+(eye_y(x,True)-eye_y(x,False))*k/8
                verts.append((x,y,face_depth(x,y)+.0025))
        for i in range(48):
            for k in range(8):a=i*9+k;faces.append((a,a+9,a+10,a+1))
        paint('Painted almond eye',verts,faces,WHITE,blink_y=cy)
        # Thin, clipped iris with a radial painted gradient and a shaded upper lid.
        cx=sign*.156;iy=cy+.016;verts=[];faces=[];colors=[]
        for r in range(13):
            radius=max(.0001,r/12)
            for j in range(64):
                a=math.tau*j/64;x=cx+.043*radius*math.cos(a)
                y=iy+.056*radius*math.sin(a)
                y=max(eye_y(x,False)+.001,min(eye_y(x,True)-.001,y))
                verts.append((x,y,face_depth(x,y)+.0038))
                if radius>.87:color=(.012,.075,.065)
                elif radius<.34:color=(.018,.10,.09)
                else:
                    light=max(0,min(1,(iy+.02-y)/.065))
                    fiber=.025*math.sin(a*23+radius*17)
                    color=(.014+.14*light+fiber,.12+.45*light+fiber,.11+.30*light+fiber)
                colors.append(tuple(srgb(max(0,c)) for c in color))
        for r in range(12):
            for j in range(64):a=r*64+j;b=r*64+(j+1)%64;faces.append((a,b,b+64,a+64))
        iris_mat=bpy.data.materials.get('Painted emerald iris')
        if iris_mat is None:
            iris_mat=mat('Painted emerald iris','#ffffff',0,.57)
            vertex=iris_mat.node_tree.nodes.new('ShaderNodeVertexColor');vertex.layer_name='Iris pigment'
            iris_mat.node_tree.links.new(vertex.outputs['Color'],iris_mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
        iris=paint('Emerald iris painting',verts,faces,iris_mat,blink_y=cy)
        layer=iris.data.color_attributes.new(name='Iris pigment',type='FLOAT_COLOR',domain='POINT')
        for item,color in zip(layer.data,colors):item.color=(*color,1)
        disk('Painted pupil',cx,iy+.003,.011,.028,.0049,IRIS_DARK,cy)
        disk('Iris painted highlight',cx-.013,iy+.019,.010,.013,.0058,WHITE,cy)
        disk('Iris secondary glint',cx+.015,iy-.025,.004,.0045,.0058,WHITE,cy)
        # A tapered ink ribbon supplies the characteristic sharp upper lash line.
        verts=[];faces=[]
        for i in range(41):
            u=i/40;x=sign*(inner+(outer-inner)*u);y=eye_y(x,True)
            width=.002+.009*math.sin(math.pi*u)**.65+.003*u
            for dy in [0,width]:verts.append((x,y+dy,face_depth(x,y+dy)+.0048))
        for i in range(40):a=i*2;faces.append((a,a+2,a+3,a+1))
        paint('Sharp upper eyelash',verts,faces,INK,blink_y=cy)
        points=[(sign*.230,cy+.045),(sign*.260,cy+.041),(sign*.247,cy+.023)]
        paint('Outer eyelash wing',[(x,y,face_depth(x,y)+.0049) for x,y in points],[(0,1,2)],INK,blink_y=cy)
        lower=[]
        for i in range(18):
            x=sign*(.14+.107*i/17);y=eye_y(x,False);lower.append((x,y,face_depth(x,y)+.003))
        curve('Fine lower lid',lower,.0014,LIP,'head')
        points=[(sign*.07,4.980),(sign*.145,5.010),(sign*.227,5.026)]
        curve('Resolute brow',[(x,y,face_depth(x,y)+.002) for x,y in points],.0045,HAIR_DARK,'head')
    curve('Quiet closed mouth',[(x,y,face_depth(x,y)+.0015) for x,y in [(-.032,4.653),(0,4.656),(.032,4.654)]],.0022,LIP,'head')
    # Smaller crown and directional, asymmetrical fringe with individual tips.
    verts=[];faces=[]
    for i in range(29):
        for j in range(80):
            a=math.tau*j/80;limit=1.21+1.25*(1-math.cos(a))/2;theta=.008+i/28*limit
            side=math.cos(a);front=side**.50 if side>=0 else side
            verts.append((.355*math.sin(theta)*math.sin(a),4.982+.383*math.cos(theta),.309*math.sin(theta)*front-.016))
    for i in range(28):
        for j in range(80):a=i*80+j;b=i*80+(j+1)%80;faces.append((a,a+80,b+80,b))
    mesh('Hair crown',verts,faces,HAIR,'head')
    for i,(root,tip,tip_y,width) in enumerate([
        (-.095,-.288,4.901,.051),(-.052,-.232,4.918,.060),(-.01,-.168,4.949,.057),
        (.025,-.103,4.963,.055),(.055,-.025,4.928,.063),(.075,.050,4.937,.059),
        (.095,.128,4.969,.064),(.12,.208,4.949,.064),(.14,.280,4.908,.054)]):
        hair_piece('Saber swept fringe %02d'%i,[(root,5.315,-.010),(root-.035,5.33,.248),(tip-.025,5.15,.319),(tip,tip_y,.249 if abs(tip)>.22 else .275)],width,.027)
    for sign in [-1,1]:
        for i in range(4):
            hair_piece('Tapered temple lock',[(sign*(.285+.014*i),5.186,.123),(sign*(.340+.012*i),4.96,.180),(sign*(.29+.044*i),4.67,.164),(sign*(.28+.065*i),4.585+.037*i,.16-.063*i)],.031-i*.003,.018,1)
        for i in range(20):
            a=.75+i*.125
            points=[]
            for k in range(32):
                t=k/31;theta=.11+(1.13+1.19*(1-math.cos(a))/2)*t
                side=math.cos(a);front=side**.50 if side>=0 else side
                points.append((sign*.358*math.sin(theta)*math.sin(a),4.982+.386*math.cos(theta),.312*math.sin(theta)*front-.016))
            curve('Combed crown hair groove',points,.0019,HAIR_DARK if i%3 else HAIR_LIGHT,'head')
    sphere('Coiled hair bun',(0,4.947,-.318),(.200,.180,.141),HAIR,'head')
    for strand in range(3):
        points=[]
        for k in range(97):
            a=math.tau*k/96;phase=a*12+strand*math.tau/3;r=.172+.010*math.cos(phase)
            points.append((r*math.cos(a),4.947+(r-.020)*math.sin(a),-.455+.010*math.sin(phase)))
        curve('Woven bun braid',points,.012,HAIR_LIGHT if strand==0 else HAIR,'head')
    for i in range(7):
        r=.025+i*.020
        curve('Coiled bun hair',[(r*math.cos(a),4.947+r*.88*math.sin(a),-.459+.045*(r/.17)**2) for a in [math.tau*k/48 for k in range(49)]],.0016,HAIR_DARK,'head')
    for sign in [-1,1]:
        lock('Folded royal-blue bow',[(0,4.82,-.455),(sign*.36,4.98,-.48),(sign*.30,4.69,-.54),(0,4.81,-.46)],.079,.013,BLUE,'head')
        lock('Bow trailing fabric',[(sign*.027,4.82,-.46),(sign*.10,4.65,-.50),(sign*.26,4.48,-.42),(sign*.33,4.52,-.45)],.047,.007,BLUE,'head')
    sphere('Bow knot',(0,4.815,-.486),(.057,.041,.026),BLUE,'head')
    hair_piece('Saber ahoge',[(.055,5.337,-.02),(-.045,5.620,.02),(-.242,5.596,.05),(-.259,5.423,.099)],.017,.009,0)


BODY=[(3.39,.266,.187),(3.54,.273,.193),(3.70,.317,.233),(3.91,.395,.252),(4.10,.377,.197),(4.22,.327,.158),(4.34,.205,.125),(4.42,.122,.110)]


def armor_depth(x,y):
    rx,rz=profile(BODY,y)
    z=rz*max(0,1-(x/rx)**2)**.5+.018
    z+=.026*math.exp(-((abs(x)-.16)/.115)**2-((y-3.94)/.14)**2)
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
            a=math.tau*j/96;y=3.51+(4.125+.045*abs(math.sin(a))-3.51)*t
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
            [(0,4.122),(.09,3.979),(.265,3.905),(.338,4.068)],
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
    rx=.30+1.04*t**1.20;rz=.20+.85*t**1.13
    wave=(.006+.035*t*t)*math.cos(14*a+.9*t)+.055*t**3*math.sin(3*a+.6)
    if outer:rx+=.030;rz+=.030
    y=3.39-2.37*t+(.19*math.cos(a-.40)+.065*math.sin(3*a))*t**3
    if outer:y+=.13*t
    return ((rx+wave)*math.sin(a)-.095*t*t,y,(rz+wave)*math.cos(a))


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
            u=-1+j/8;x=u*width-.095*t*t
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
        x=sign*.34
        cylinder('Clothed leg',(x,.38,-.035),(x,2.2,-.035),.105,.15,BLUE_DARK,'hips')
        verts=[];faces=[]
        for i,(y,rx,rz) in enumerate([(.39,.099,.094),(.55,.102,.102),(.88,.132,.116),(1.3,.152,.133),(1.63,.145,.143)]):
            for j in range(48):
                a=math.tau*j/48;verts.append((x+rx*math.sin(a),y,-.020+rz*math.cos(a)))
        for i in range(4):
            for j in range(48):a=i*48+j;b=i*48+(j+1)%48;faces.append((a,b,b+48,a+48))
        mesh('Shaped silver greave',verts,faces,SILVER,'hips')
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
