# A simple script that uses blender to render views of a single object by rotation the camera around it.
# Also produces depth map at the same time.

import argparse, sys, os
import json
import bpy
import mathutils
import numpy as np
RESOLUTION = 800
DEPTH_SCALE = 1.4
COLOR_DEPTH = 8
FORMAT = 'PNG'
CIRCLE_FIXED_START = (.3,0,0)
DATASET = sys.argv[-2]
SCENE = sys.argv[-1]
PROBE = "data/irrmaps"

ROOT_DIR = "/Users/minhyukchoi/Desktop/blender/nvdiffrecmc"

def listify_matrix(matrix):
    matrix_list = []
    for row in matrix:
        matrix_list.append(list(row))
    return matrix_list


# Render Optimizations
bpy.context.scene.render.use_persistent_data = True


# Set up rendering of depth map.
bpy.context.scene.use_nodes = True
tree = bpy.context.scene.node_tree
links = tree.links

# Add passes for additionally dumping albedo and normals.
#bpy.context.scene.view_layers["RenderLayer"].use_pass_normal = True
bpy.context.scene.render.image_settings.file_format = str(FORMAT)
bpy.context.scene.render.image_settings.color_depth = str(COLOR_DEPTH)

# Create input render layer node.
render_layers = tree.nodes.new('CompositorNodeRLayers')

depth_file_output = tree.nodes.new(type="CompositorNodeOutputFile")
depth_file_output.label = 'Depth Output'
if FORMAT == 'OPEN_EXR':
    links.new(render_layers.outputs['Depth'], depth_file_output.inputs[0])
else:
    # Remap as other types can not represent the full range of depth.
    map = tree.nodes.new(type="CompositorNodeMapValue")
    # Size is chosen kind of arbitrarily, try out until you're satisfied with resulting depth map.
    map.offset = [-0.7]
    map.size = [DEPTH_SCALE]
    map.use_min = True
    map.min = [0]
    links.new(render_layers.outputs['Depth'], map.inputs[0])

    links.new(map.outputs[0], depth_file_output.inputs[0])

normal_file_output = tree.nodes.new(type="CompositorNodeOutputFile")
normal_file_output.label = 'Normal Output'
links.new(render_layers.outputs['Normal'], normal_file_output.inputs[0])

# Background
bpy.context.scene.render.dither_intensity = 0.0
bpy.context.scene.render.film_transparent = True

# Create collection for objects not to render with background

objs = [ob for ob in bpy.context.scene.objects if ob.type in ('EMPTY') and 'Empty' in ob.name]
bpy.ops.object.delete({"selected_objects": objs})

def parent_obj_to_camera(b_camera):
    origin = (0, 0, 0)
    b_empty = bpy.data.objects.new("Empty", None)
    b_empty.location = origin
    b_camera.parent = b_empty  # setup parenting

    scn = bpy.context.scene
    scn.collection.objects.link(b_empty)
    bpy.context.view_layer.objects.active = b_empty
    # scn.objects.active = b_empty
    return b_empty


scene = bpy.context.scene
scene.render.resolution_x = RESOLUTION
scene.render.resolution_y = RESOLUTION
scene.render.resolution_percentage = 100

cam = scene.objects['Camera']
cam.location = (0, 4.0, 0.5)
cam_constraint = cam.constraints.new(type='TRACK_TO')
cam_constraint.track_axis = 'TRACK_NEGATIVE_Z'
cam_constraint.up_axis = 'UP_Y'
b_empty = parent_obj_to_camera(cam)
cam_constraint.target = b_empty

scene.render.image_settings.file_format = 'PNG'  # set output format to .png

from glob import glob
from mathutils import Matrix; 
from math import *
pose = os.path.join(ROOT_DIR, f"data/{DATASET}/{SCENE}/transforms_val.json")
if not os.path.exists(pose):
    pose = os.path.join(ROOT_DIR, f"data/{DATASET}/{SCENE}/transforms_test.json")
with open(pose, 'r') as f:
    val_cfg = json.load(f)

camera_data   = bpy.data.cameras.new(name='Camera')
camera_object = bpy.data.objects.new('Camera', camera_data)
scene.collection.objects.link(camera_object)
scene.camera  = camera_object
camera_data.angle = val_cfg['camera_angle_x']

for HDR in ["nerf", "nerfactor"]:
    RESULTS_PATH = os.path.join(ROOT_DIR, f"relight_gt/{DATASET}", HDR, SCENE)
    for file in glob(os.path.join(ROOT_DIR, PROBE, HDR, "*.hdr")):
        envmap = scene.world.node_tree.nodes.new(type="ShaderNodeTexEnvironment")
        envmap.image = bpy.data.images.load(file)
        scene.world.node_tree.links.new(envmap.outputs[0], scene.world.node_tree.nodes['Background'].inputs['Color'])
        for i in range(8):
            mtx = np.array(val_cfg['frames'][i]['transform_matrix'], dtype=np.float32)
            scene.camera.matrix_world = Matrix(mtx)
            scene.render.filepath = os.path.join(RESULTS_PATH, os.path.basename(file)[:-4] + '_r_{0:03d}'.format(int(i)))
            bpy.ops.render.render(write_still=True)  # render still 
