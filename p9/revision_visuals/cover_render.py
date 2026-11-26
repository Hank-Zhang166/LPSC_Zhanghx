"""Run in Blender 5.3: blender -b -P p9/revision_visuals/cover_render.py"""
from pathlib import Path
import bpy
from mathutils import Vector
out = Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(out / "blender/pellet.blend"))
scene = bpy.context.scene
# Offset the upper contact to reveal the grain boundary network in the powder pellet.
bpy.data.objects["Upper blocking electrode"].location += Vector((-.25,.50,.23))
scene.camera.location=Vector((6,-8,6.6))
scene.camera.rotation_euler=(Vector((0,.07,.23))-scene.camera.location).to_track_quat("-Z","Y").to_euler()
scene.camera.data.ortho_scale=7.1
scene.render.resolution_x,scene.render.resolution_y=1050,1000
scene.render.resolution_percentage=100
scene.cycles.samples=20
scene.render.filepath=str(out/"pellet_cutaway.png")
bpy.ops.render.render(write_still=True)
