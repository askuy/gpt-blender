"""Saber portrait study: short lower face, teal eyes and swept layered hair.

Coordinates are (x, height, forward). Geometry and paint are authored here;
the Good Smile product 2780 photographs are visual references only.
"""
import math
from mathutils import Vector


def install(api):
    names=['bpy','mesh','sphere','cylinder','curve','lock','select_only','BLINK',
           'SKIN','BLUSH','WHITE','LIP','INK','IRIS_DARK','HAIR','HAIR_LIGHT',
           'HAIR_DARK','BLUE','mat','srgb','profile','EXPRESSIONS']
    globals().update({k:api[k] for k in names})


FACE = [(4.565,.019,.122,.034),(4.592,.070,.170,.070),
        (4.635,.151,.222,.136),(4.700,.230,.255,.207),
        (4.785,.281,.259,.248),(4.900,.297,.250,.262),
        (5.035,.295,.230,.258),(5.180,.249,.183,.220),
        (5.285,.122,.091,.121),(5.318,.005,.008,.008)]


def facial_depth(x,y):
    rx,front,_=profile(FACE,y)
    z=front*max(0,1-(x/max(rx,.001))**2)**.31
    # Small nose, defined profile, and a soft muzzle. No separate nose ball.
    z+=.032*math.exp(-(x/.021)**2-((y-4.713)/.024)**2)
    z+=.010*math.exp(-(x/.027)**2-((y-4.762)/.053)**2)
    z+=.007*math.exp(-(x/.063)**2-((y-4.667)/.032)**2)
    return z


def paint(name,vertices,faces,color,blink=None):
    obj=mesh(name,vertices,faces,color,'head')
    if blink is not None:BLINK.append((obj,blink))
    return obj


def paint_disk(name,cx,cy,rx,ry,offset,material,blink=None):
    vertices=[(cx,cy,facial_depth(cx,cy)+offset)]
    for i in range(33):
        a=math.tau*i/32;x=cx+rx*math.cos(a);y=cy+ry*math.sin(a)
        vertices.append((x,y,facial_depth(x,y)+offset))
    return paint(name,vertices,[(0,i+1,i+2) for i in range(32)],material,blink)


def swept_lock(name,control,width,depth=.025,material=None,ridges=0):
    """A curved, flattened sculpted blade, with roots buried in the crown.

    The local cross section follows the curve's tangent. This avoids the
    pinched sausage cross sections and floating strand lines of v2.
    """
    c=list(map(Vector,control));vertices=[];faces=[]
    def section(t,q):
        p=(1-t)**3*c[0]+3*(1-t)**2*t*c[1]+3*(1-t)*t*t*c[2]+t**3*c[3]
        tangent=(3*(1-t)**2*(c[1]-c[0])+6*(1-t)*t*(c[2]-c[1])+3*t*t*(c[3]-c[2])).normalized()
        side=Vector((1,0,0));side=(side-tangent*side.dot(tangent)).normalized()
        normal=tangent.cross(side).normalized()
        if normal.dot(p-Vector((0,4.98,-.020)))<0:normal=-normal
        taper=max(.004,(1-t)**.60)*(.62+.65*math.sin(math.pi*t))
        # Broad root and convex centre ridge, tapering into a fine swept tip.
        flute=1-.14*math.sin(q*math.pi*2+.25*math.sin(math.pi*t))**2
        v=p+side*(q*width*taper)+normal*(depth*taper*(1-q*q)*flute)
        return v,normal,taper
    underside=[]
    for i in range(25):
        t=i/24
        for j in range(11):
            q=-1+j/5;v,normal,taper=section(t,q);vertices.append(tuple(v))
            underside.append(tuple(v-normal*(.009*taper)))
    for i in range(24):
        for j in range(10):a=i*11+j;faces.append((a,a+11,a+12,a+1))
    # Close the shell with tapered thickness, including the tip. A constant
    # Solidify offset leaves conspicuous rectangular hooks at fine hair tips.
    count=len(vertices);vertices.extend(underside)
    faces.extend(tuple(v+count for v in reversed(face)) for face in list(faces))
    boundary=list(range(11))+[i*11+10 for i in range(1,25)]+list(range(24*11+9,24*11-1,-1))+[i*11 for i in range(23,0,-1)]
    for a,b in zip(boundary,boundary[1:]+boundary[:1]):faces.append((a,b,b+count,a+count))
    obj=mesh(name,vertices,faces,material or HAIR,'head')
    for k in range(ridges):
        points=[]
        for i in range(22):
            t=.12+.76*i/21;v,n,taper=section(t,(k-(ridges-1)/2)*.6)
            points.append(tuple(v+n*.0008))
        curve(name+' fine sculpt ridge',points,.0012,HAIR_LIGHT,'head')
    return obj


def eyes():
    for sign in [-1,1]:
        inner=.063;outer=.238;cy=4.804
        def contour(x,top):
            u=max(0,min(1,(abs(x)-inner)/(outer-inner)))
            if top:
                return cy+.052*u+.022*math.sin(math.pi*u)**.65
            return cy+.052*u-.066*math.sin(math.pi*u)**.8
        verts=[];faces=[]
        for i in range(41):
            x=sign*(inner+(outer-inner)*i/40)
            for k in range(7):
                y=contour(x,False)+(contour(x,True)-contour(x,False))*k/6
                verts.append((x,y,facial_depth(x,y)+.0025))
        for i in range(40):
            for k in range(6):a=i*7+k;faces.append((a,a+7,a+8,a+1))
        paint('Saber angled eye opening',verts,faces,WHITE,cy)
        cx=sign*.152;iy=cy+.009;verts=[];colors=[];faces=[]
        for r in range(11):
            radius=max(.0001,r/10)
            for j in range(48):
                a=math.tau*j/48;x=cx+.058*radius*math.cos(a)
                y=iy+.072*radius*math.sin(a)
                y=max(contour(x,False)+.001,min(contour(x,True)-.001,y))
                verts.append((x,y,facial_depth(x,y)+.0038))
                light=max(0,min(1,(iy+.028-y)/.079))
                fiber=.024*math.sin(a*21+radius*11)
                if radius>.89:color=(.012,.125,.123)
                elif radius<.32:color=(.009,.085,.085)
                else:color=(.010+.035*light+fiber,.07+.55*light+fiber,.08+.45*light+fiber)
                colors.append(tuple(srgb(max(0,c)) for c in color))
        for r in range(10):
            for j in range(48):a=r*48+j;b=r*48+(j+1)%48;faces.append((a,b,b+48,a+48))
        iris_mat=bpy.data.materials.get('Painted emerald iris')
        if iris_mat is None:
            iris_mat=mat('Painted emerald iris','#ffffff',0,.52)
            vertex=iris_mat.node_tree.nodes.new('ShaderNodeVertexColor');vertex.layer_name='Iris pigment'
            iris_mat.node_tree.links.new(vertex.outputs['Color'],iris_mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
        obj=paint('Saber teal iris',verts,faces,iris_mat,cy)
        layer=obj.data.color_attributes.new(name='Iris pigment',type='FLOAT_COLOR',domain='POINT')
        for item,color in zip(layer.data,colors):item.color=(*color,1)
        paint_disk('Painted pupil',cx,iy+.006,.018,.032,.0048,IRIS_DARK,cy)
        paint_disk('Iris main glint',cx-.026,iy-.020,.011,.009,.0055,WHITE,cy)
        paint_disk('Iris upper glint',cx+.012,iy+.031,.004,.004,.0055,WHITE,cy)
        verts=[];faces=[]
        for i in range(41):
            u=i/40;x=sign*(inner+(outer-inner)*u);y=contour(x,True)
            thickness=.001+.010*math.sin(math.pi*u)**.6+.004*u
            for dy in [0,thickness]:verts.append((x,y+dy,facial_depth(x,y+dy)+.005))
        for i in range(40):a=i*2;faces.append((a,a+2,a+3,a+1))
        paint('Saber decisive upper lash',verts,faces,INK,cy)
        wing=[(sign*.216,4.870),(sign*.259,4.879),(sign*.237,4.850)]
        paint('Saber fine outer lash',[(x,y,facial_depth(x,y)+.005) for x,y in wing],[(0,1,2)],INK,cy)
        points=[]
        for i in range(21):
            x=sign*(.090+.146*i/20);y=contour(x,False)
            points.append((x,y,facial_depth(x,y)+.003))
        obj=curve('Painted lower eyelid',points,.0015,INK,'head');BLINK.append((obj,cy))
        # Inward-downward brows supply the focused expression, even at rest.
        points=[(sign*.060,4.879),(sign*.126,4.906),(sign*.220,4.923)]
        verts=[]
        for x,y in points:
            for dy in [0,.007]:verts.append((x,y+dy,facial_depth(x,y+dy)+.003))
        paint('Saber focused brow',verts,[(0,2,3,1),(2,4,5,3)],HAIR_DARK)
    mouth()


def mouth():
    """Baked expression paint meshes, conforming to the sculpt in both poses."""
    dark=mat('Mouth painted depth','#401b1b',0,.85)
    closed=[];opened=[]
    for action,destination in [(False,closed),(True,opened)]:
        cy=4.657 if action else 4.667;rx=.044 if action else .030;ry=.029 if action else .0009
        destination.append((0,cy,facial_depth(0,cy)+.0035))
        for i in range(49):
            a=math.tau*i/48;x=rx*math.cos(a);y=cy+ry*math.sin(a)
            destination.append((x,y,facial_depth(x,y)+.0035))
    obj=paint('Saber battle mouth cavity',closed,[(0,i+1,i+2) for i in range(48)],dark)
    EXPRESSIONS.append((obj,opened))
    closed=[];opened=[]
    for action,destination in [(False,closed),(True,opened)]:
        cy=4.657 if action else 4.667;rx=.044 if action else .030;ry=.029 if action else .0009
        for i in range(49):
            a=math.tau*i/48
            for offset in [0,.0024 if action else .0013]:
                x=(rx+offset)*math.cos(a);y=cy+(ry+offset)*math.sin(a)
                destination.append((x,y,facial_depth(x,y)+.0037))
    obj=paint('Saber expressive lip outline',closed,[(2*i,2*i+2,2*i+3,2*i+1) for i in range(48)],LIP)
    EXPRESSIONS.append((obj,opened))
    teeth=[]
    for i in range(17):
        u=-1+i/8;x=.030*u
        for y in [4.676+.001*(1-u*u),4.680+.004*(1-u*u)]:teeth.append((x,y))
    closed=[(x*.02,4.667+(y-4.680)*.003,facial_depth(x*.02,4.667)+.002) for x,y in teeth]
    opened=[(x,y,facial_depth(x,y)+.012) for x,y in teeth]
    obj=paint('Battle expression upper teeth',closed,[(2*i,2*i+2,2*i+3,2*i+1) for i in range(16)],WHITE)
    EXPRESSIONS.append((obj,opened))


def hair():
    verts=[];faces=[]
    for i in range(33):
        for j in range(80):
            a=math.tau*j/80;limit=1.43+1.00*(1-math.cos(a))/2;theta=.005+i/32*limit
            front=math.cos(a)
            ridge=.0018*math.cos(26*a+1.6*theta)*math.sin(theta)
            verts.append(((.337+ridge)*math.sin(theta)*math.sin(a),4.980+.376*math.cos(theta),(.296+ridge)*math.sin(theta)*front-.020))
    for i in range(32):
        for j in range(80):a=i*80+j;b=i*80+(j+1)%80;faces.append((a,a+80,b+80,b))
    mesh('Saber close-fitting swept crown',verts,faces,HAIR,'head')
    # Unequal locks fan from an off-centre part; the central lock crosses the
    # forehead and the temple tips continue the same flow around the face.
    fringe=[
        ([(-.025,5.341,.014),(-.255,5.325,.145),(-.337,5.016,.217),(-.283,4.823,.170)],.064),
        ([(-.014,5.350,.019),(-.178,5.309,.248),(-.276,4.970,.298),(-.218,4.831,.243)],.064),
        ([(.003,5.354,.022),(-.104,5.307,.294),(-.201,4.964,.326),(-.143,4.843,.281)],.060),
        ([(.025,5.352,.024),(-.028,5.291,.328),(-.120,4.978,.352),(-.059,4.847,.279)],.066),
        ([(.038,5.351,.027),(.047,5.257,.329),(-.015,4.993,.354),(.051,4.827,.281)],.058),
        ([(.052,5.346,.025),(.112,5.221,.322),(.081,5.006,.341),(.177,4.874,.240)],.066),
        ([(.059,5.342,.024),(.217,5.244,.266),(.207,4.992,.305),(.284,4.802,.166)],.070),
        ([(.071,5.337,.017),(.290,5.229,.181),(.320,4.965,.215),(.319,4.769,.098)],.061),
    ]
    for i,(control,width) in enumerate(fringe):
        swept_lock('Swept layered fringe %02d'%i,control,width,.026 if i%2 else .032,ridges=1 if i in [2,4,6] else 0)
    for i,(control,width) in enumerate([
        ([(-.030,5.338,.020),(-.214,5.268,.227),(-.302,4.978,.259),(-.274,4.880,.213)],.033),
        ([(.012,5.350,.033),(-.083,5.233,.337),(-.167,5.015,.356),(-.113,4.918,.309)],.029),
        ([(.041,5.347,.029),(.067,5.268,.339),(.030,5.072,.372),(.105,4.947,.313)],.030),
        ([(.062,5.335,.031),(.184,5.247,.309),(.166,5.080,.351),(.238,4.930,.255)],.029),
    ]):
        control=[(x,y,z+(.025 if j else 0)) for j,(x,y,z) in enumerate(control)]
        swept_lock('Fine overlapping fringe %02d'%i,control,width*.82,.012,HAIR)
    for sign in [-1,1]:
        for i in range(3):
            swept_lock('Saber feathered side lock',[(sign*.267,5.145,.030),(sign*(.336+.018*i),4.859,.198-i*.018),(sign*(.271+.063*i),4.659,.190-i*.072),(sign*(.330+.087*i),4.631+.043*i,.086-i*.097)],.037-i*.003,.019,ridges=0)
        for i in range(16):
            a=.90+i*.132;points=[]
            for k in range(31):
                theta=.21+(1.43+(1-math.cos(a))/2-.24)*k/30
                points.append((sign*.338*math.sin(theta)*math.sin(a),4.98+.377*math.cos(theta),.297*math.sin(theta)*math.cos(a)-.02))
            curve('Combed rear hair engraving',points,.0009,HAIR_DARK,'head')
    sphere('Saber braided hair bun',(0,4.920,-.311),(.194,.166,.142),HAIR,'head')
    for strand in range(3):
        points=[]
        for k in range(97):
            a=math.tau*k/96;phase=a*11+strand*math.tau/3;r=.165+.014*math.cos(phase)
            points.append((r*math.cos(a),4.920+(r-.018)*math.sin(a),-.446+.011*math.sin(phase)))
        curve('Saber woven bun braid',points,.017,HAIR_LIGHT if strand==0 else HAIR,'head')
    for i in range(6):
        r=.024+i*.022
        curve('Bun coiled sculpt',[(r*math.cos(a),4.920+r*.88*math.sin(a),-.454+.034*(r/.16)**2) for a in [math.tau*k/40 for k in range(41)]],.0017,HAIR_DARK,'head')
    for sign in [-1,1]:
        lock('Royal-blue hair ribbon',[(0,4.818,-.447),(sign*.31,4.94,-.46),(sign*.30,4.69,-.53),(0,4.815,-.45)],.068,.013,BLUE,'head')
        lock('Ribbon trailing silk',[(sign*.027,4.816,-.45),(sign*.14,4.65,-.49),(sign*.33,4.64,-.47),(sign*.40,4.69,-.45)],.041,.007,BLUE,'head')
    sphere('Hair ribbon knot',(0,4.816,-.478),(.050,.036,.025),BLUE,'head')
    lock('Saber signature ahoge',[(.034,5.349,.028),(-.035,5.585,.040),(-.237,5.568,.083),(-.277,5.410,.102)],.015,.012,HAIR,'head')


def head():
    vertices=[];faces=[]
    for i in range(65):
        y=4.565+(5.318-4.565)*i/64;rx,front,back=profile(FACE,y)
        for j in range(80):
            a=math.tau*j/80;x=rx*math.sin(a)
            z=facial_depth(x,y) if math.cos(a)>=0 else back*math.cos(a)
            vertices.append((x,y,z))
    for i in range(64):
        for j in range(80):a=i*80+j;b=i*80+(j+1)%80;faces.append((a,b,b+80,a+80))
    skin=mat('Hand-painted porcelain skin','#ffffff',0,.57)
    pigment=skin.node_tree.nodes.new('ShaderNodeVertexColor');pigment.layer_name='Skin pigment'
    skin.node_tree.links.new(pigment.outputs['Color'],skin.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
    obj=mesh('Saber short jaw portrait sculpt',vertices,faces,skin,'head')
    layer=obj.data.color_attributes.new(name='Skin pigment',type='FLOAT_COLOR',domain='POINT')
    for item,(x,y,z) in zip(layer.data,vertices):
        cheek=.19*math.exp(-((abs(x)-.185)/.068)**2-((y-4.730)/.050)**2) if z>0 else 0
        nose=.10*math.exp(-(x/.028)**2-((y-4.714)/.025)**2) if z>0 else 0
        blush=cheek+nose
        color=tuple(srgb(c*(1-blush)+b*blush) for c,b in zip((1,.894,.80),(1,.59,.53)))
        item.color=(*color,1)
    cylinder('Slender neck',(0,4.34,-.015),(0,4.65,-.025),.100,.088,SKIN,'head')
    for sign in [-1,1]:
        sphere('Ear',(sign*.283,4.766,-.013),(.041,.067,.032),SKIN,'head')
        sphere('Ear concha',(sign*.307,4.768,.012),(.018,.041,.008),BLUSH,'head')
    eyes();hair()
