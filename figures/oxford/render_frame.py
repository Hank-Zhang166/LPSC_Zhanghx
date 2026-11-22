"""Run with blender --background --factory-startup --python render_frame.py."""
from itertools import product
import json
from math import cos, radians, sin
from pathlib import Path

import bpy
from mathutils import Vector


dest = Path(__file__).resolve().parent
data = json.loads((dest / "first_frame.json").read_text(encoding="utf-8"))
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.samples = 20
scene.cycles.use_denoising = True
scene.render.resolution_x = 1280
scene.render.resolution_y = 1280
scene.render.resolution_percentage = 100
scene.render.film_transparent = True
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.filepath = str(dest / "lpsc_52.png")
scene.view_settings.view_transform = "Standard"
scene["source_and_license"] = data["source"]
bpy.context.preferences.filepaths.save_version = 0

palette = {"Li": ("6CADD7", 0.43), "P": ("9659AF", 0.57),
           "S": ("DEA43D", 0.60), "Cl": ("169780", 0.69)}


def material(label, hex_rgb):
    srgb = [int(hex_rgb[i:i+2], 16) / 255 for i in (0, 2, 4)]
    color = tuple(c / 12.92 if c <= 0.04045 else ((c+0.055)/1.055)**2.4 for c in srgb)
    mat = bpy.data.materials.new(label)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes["Principled BSDF"]
    shader.inputs["Base Color"].default_value = (*color, 1)
    shader.inputs["Roughness"].default_value = 0.53
    return mat


basis = [Vector(row) for row in data["cell_rows"]]
center = (basis[0] + basis[1] + basis[2]) / 2
atoms = [(a["element"], Vector(a["xyz"]) - center) for a in data["atoms"]]
assert len(atoms) == 52
mats = {el: material(el, meta[0]) for el, meta in palette.items()}
meshes = {}
for i, (el, location) in enumerate(atoms, start=1):
    if el not in meshes:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=40, ring_count=20,
                                             radius=palette[el][1], location=location)
        obj = bpy.context.object
        obj.data.materials.append(mats[el])
        for face in obj.data.polygons:
            face.use_smooth = True
        meshes[el] = obj.data
    else:
        obj = bpy.data.objects.new(el, meshes[el])
        scene.collection.objects.link(obj)
        obj.location = location
    obj.name = f"{i:02d}_{el}"
    obj["atom_index_zero_based"] = i - 1


def vertex(ijk):
    return sum((v * q for v, q in zip(basis, ijk)), -center)


stroke = material("Periodic cell / blue-gray", "58717B")
for corners in product((0, 1), repeat=3):
    for axis in range(3):
        if corners[axis]:
            continue
        opposite = list(corners)
        opposite[axis] = 1
        curve = bpy.data.curves.new("Lattice edge", "CURVE")
        curve.dimensions = "3D"
        curve.bevel_depth = 0.027
        curve.bevel_resolution = 3
        segment = curve.splines.new("POLY")
        segment.points.add(1)
        for point, p in zip(segment.points, (vertex(corners), vertex(opposite))):
            point.co = (*p, 1)
        border = bpy.data.objects.new("Cell edge", curve)
        scene.collection.objects.link(border)
        border.data.materials.append(stroke)


def direction(azimuth, elevation):
    a, e = radians(azimuth), radians(elevation)
    return Vector((cos(a)*cos(e), sin(a)*cos(e), sin(e)))


def overlap_score(u):
    # Choose a readable angle; only the orthographic camera changes.
    cost = 0.0
    for i, (el, pos) in enumerate(atoms):
        for other, otherpos in atoms[i+1:]:
            delta = pos - otherpos
            separation = (delta - delta.dot(u) * u).length
            touching = palette[el][1] + palette[other][1]
            cost += max(0, touching - separation) ** 2
    return cost


u = min((direction(a, e) for a in range(-64, -19, 4) for e in range(18, 43, 3)),
        key=overlap_score)
bpy.ops.object.camera_add(location=u*32)
camera = bpy.context.object
camera.rotation_euler = (-u).to_track_quat("-Z", "Y").to_euler()
camera.data.type = "ORTHO"
right = camera.rotation_euler.to_quaternion() @ Vector((1, 0, 0))
up = camera.rotation_euler.to_quaternion() @ Vector((0, 1, 0))
points = [(vertex(v), 0.04) for v in product((0, 1), repeat=3)]
points.extend((pos, palette[el][1]) for el, pos in atoms)
camera.data.ortho_scale = 2.12 * max(abs(pos.dot(axis))+r for pos, r in points for axis in (right, up))
scene.camera = camera

world = bpy.data.worlds.new("Neutral ambient studio")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.46
scene.world = world
for name, pos, power, diameter in [
        ("Key", (-5, -14, 18), 2450, 12), ("Fill", (13, -4, 7), 1150, 10),
        ("Edge", (4, 13, 12), 1550, 9)]:
    bpy.ops.object.light_add(type="AREA", location=pos)
    light = bpy.context.object
    light.name = name
    light.data.energy = power
    light.data.shape = "DISK"
    light.data.size = diameter
    light.rotation_euler = (-light.location).to_track_quat("-Z", "Y").to_euler()

bpy.ops.wm.save_as_mainfile(filepath=str(dest / "lpsc_52.blend"), compress=True)
bpy.ops.render.render(write_still=True)
