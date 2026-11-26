"""Blender 5.3: exploded pellet/electrodes; synthetic geometry, no crystallographic data."""
from pathlib import Path
import math
import random
import bpy
from mathutils import Vector

out = Path(__file__).resolve().parent
rng = random.Random(709)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 24
scene.cycles.use_denoising = True
scene.render.resolution_x, scene.render.resolution_y = 1100, 1000
scene.render.resolution_percentage = 100
scene.render.film_transparent = True
scene.view_settings.view_transform = 'AgX'
world = bpy.data.worlds.new('Soft studio')
scene.world = world
world.use_nodes = True
world.node_tree.nodes.get('Background').inputs[0].default_value = (.7,.8,.85,1)
world.node_tree.nodes.get('Background').inputs[1].default_value = .55

def material(name, rgb, metallic=0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*rgb,1)
    m.use_nodes=True
    p=m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value=(*rgb,1)
    p.inputs['Metallic'].default_value=metallic
    p.inputs['Roughness'].default_value=.35
    return m

shades=[material('Grain %02d'%i,(.05+.035*i,.26+.048*i,.23+.042*i)) for i in range(6)]
contact=material('Brushed contact',(.51,.37,.19),.72)
edge=material('Contact rim',(.28,.28,.29),.8)
def disk(name,r,z,depth,mat):
    bpy.ops.mesh.primitive_cylinder_add(vertices=120,radius=r,depth=depth,location=(0,0,z))
    obj=bpy.context.object
    obj.name=name
    obj.data.materials.append(mat)
    mod=obj.modifiers.new('Machined edge','BEVEL')
    mod.width=.055
    mod.segments=3
    obj.modifiers.new('Surface normals','WEIGHTED_NORMAL')

def bisect(poly,nx,ny,c):
    result=[]
    for p,q in zip(poly,poly[1:]+poly[:1]):
        a=nx*p[0]+ny*p[1]-c
        b=nx*q[0]+ny*q[1]-c
        if a<=0: result.append(p)
        if (a<0)!=(b<0):
            t=a/(a-b)
            result.append((p[0]+t*(q[0]-p[0]),p[1]+t*(q[1]-p[1])))
    return result

R=2.35
seeds=[]
while len(seeds)<77:
    x,y=rng.uniform(-R,R),rng.uniform(-R,R)
    if x*x+y*y<R*R and all((x-a)**2+(y-b)**2>.035 for a,b in seeds):
        seeds.append((x,y))
circle=[(R*math.cos(i*math.tau/120),R*math.sin(i*math.tau/120)) for i in range(120)]
for idx,(x,y) in enumerate(seeds):
    p=circle[:]
    for a,b in seeds:
        if (a,b)!=(x,y): p=bisect(p,a-x,b-y,(a*a+b*b-x*x-y*y)/2)
    p=[(x+.967*(a-x),y+.967*(b-y)) for a,b in p]
    n=len(p)
    top=.38+rng.uniform(-.04,.055)
    vs=[(a,b,z) for z in [-.42,top] for a,b in p]
    fs=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,n+(i+1)%n,n+i) for i in range(n)]
    mesh=bpy.data.meshes.new('Cell')
    mesh.from_pydata(vs,[],fs)
    ob=bpy.data.objects.new('Schematic grain %02d'%idx,mesh)
    scene.collection.objects.link(ob)
    ob.data.materials.append(rng.choice(shades))
    mod=ob.modifiers.new('Grain edge','BEVEL')
    mod.width=.025
    mod.segments=2
    ob.modifiers.new('Normals','WEIGHTED_NORMAL')
disk('Upper blocking electrode',R,1.85,.22,contact)
disk('Lower blocking electrode',R,-1.25,.23,contact)
disk('Lower electrode backing',R*.94,-1.42,.12,edge)
def point(ob): ob.rotation_euler=(Vector((0,0,.1))-ob.location).to_track_quat('-Z','Y').to_euler()
for pos,energy,size in [((2,-6,8),850,5),((-5,-2,4),550,4),((1,5,6),1150,4)]:
    bpy.ops.object.light_add(type='AREA',location=pos)
    ob=bpy.context.object
    ob.data.energy,ob.data.shape,ob.data.size=energy,'DISK',size
    point(ob)
bpy.ops.object.camera_add(location=(6,-9,5))
cam=bpy.context.object
point(cam)
cam.data.type='ORTHO'
cam.data.ortho_scale=7.0
scene.camera=cam
bpy.ops.wm.save_as_mainfile(filepath=str(out/'pellet.blend'))
