import bpy 
import json
import numpy as np
import os
from mathutils import Matrix; 
from math import *
from glob import glob
RESOLUTION = 800
SAMPLES = 64
BOUNCES = 1

scene = bpy.context.scene
scene.world.use_nodes = True
scene.render.engine = 'CYCLES'
scene.render.film_transparent = True
scene.cycles.device = 'GPU'
scene.cycles.samples = SAMPLES
scene.cycles.max_bounces = BOUNCES
scene.cycles.diffuse_bounces = BOUNCES
scene.cycles.glossy_bounces = BOUNCES
scene.cycles.transmission_bounces = 0
scene.cycles.volume_bounces = 0
scene.cycles.transparent_max_bounces = 8
scene.cycles.use_denoising = True

scene.render.resolution_x = RESOLUTION
scene.render.resolution_y = RESOLUTION
scene.render.resolution_percentage = 100

# OpenEXR output, should not be tonemapped
scene.display_settings.display_device = 'None'
scene.view_settings.view_transform = 'Standard'
scene.view_settings.exposure = 0.0
scene.view_settings.gamma = 1.0
scene.render.image_settings.file_format = 'OPEN_EXR' 

scene.view_layers['ViewLayer'].use_pass_combined=True
scene.view_layers['ViewLayer'].use_pass_diffuse_direct=True
scene.view_layers['ViewLayer'].use_pass_diffuse_color=True
scene.view_layers['ViewLayer'].use_pass_glossy_direct=True
scene.view_layers['ViewLayer'].use_pass_glossy_color=True

ROOT_DIR = "/Users/minhyukchoi/Desktop/blender/nvdiffrecmc"
def relight_scene(MODEL, DATASET, SCENE, alpha_transparency=False):
    if DATASET != "glossy":
        HDR_LIST = ["nerf", "nerfactor"]
    else:
        HDR_LIST = ["nero"]
    for HDR in HDR_LIST:
        PROBE = "data/irrmaps"
        MESH_PATH = os.path.join(ROOT_DIR, f"out/{MODEL}/{DATASET}/{SCENE}/mesh")
        RESULTS_PATH = os.path.join(ROOT_DIR, f"relight/{MODEL}/{HDR}/{DATASET}/{SCENE}")
        os.makedirs(RESULTS_PATH, exist_ok=True)

        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete()

        ################### Import obj mesh ###################

        bpy.ops.import_scene.obj(filepath=os.path.join(MESH_PATH, "mesh.obj"))
        obj_object = bpy.context.selected_objects[0]
        obj_object.rotation_euler = [np.pi*0.5, 0, 0]

        ################### Fix material graph ###################

        # Get material node tree, find BSDF and specular texture
        material = obj_object.active_material
        bsdf = material.node_tree.nodes["Principled BSDF"]
        image_node_ks = bsdf.inputs["Specular"].links[0].from_node

        # Split the specular texture into metalness and roughness
        separate_node = material.node_tree.nodes.new(type="ShaderNodeSeparateRGB")
        separate_node.name="SeparateKs"
        material.node_tree.links.new(image_node_ks.outputs[0], separate_node.inputs[0])
        material.node_tree.links.new(separate_node.outputs[2], bsdf.inputs["Metallic"])
        material.node_tree.links.new(separate_node.outputs[1], bsdf.inputs["Roughness"])

        material.node_tree.links.remove(bsdf.inputs["Specular"].links[0])

        # Add alpha channel if applicable
        if alpha_transparency:
            image_node_kd = bsdf.inputs["Base Color"].links[0].from_node
            material.node_tree.links.new(image_node_kd.outputs[1], bsdf.inputs["Alpha"])

        normal_map_node = bsdf.inputs["Normal"].links[0].from_node
        texture_n_node = normal_map_node.inputs["Color"].links[0].from_node
        material.node_tree.links.remove(normal_map_node.inputs["Color"].links[0])

        normal_separate_node = material.node_tree.nodes.new(type="ShaderNodeSeparateRGB")
        normal_separate_node.name="SeparateNormal"

        normal_combine_node = material.node_tree.nodes.new(type="ShaderNodeCombineRGB")
        normal_combine_node.name="CombineNormal"

        normal_invert_node = material.node_tree.nodes.new(type="ShaderNodeMath")
        normal_invert_node.name="InvertNormal"
        normal_invert_node.operation='SUBTRACT'
        normal_invert_node.inputs[0].default_value = 1.0

        material.node_tree.links.new(texture_n_node.outputs[0], normal_separate_node.inputs['Image'])
        material.node_tree.links.new(normal_separate_node.outputs['R'], normal_combine_node.inputs['R'])

        material.node_tree.links.new(normal_separate_node.outputs['G'], normal_invert_node.inputs[1])
        material.node_tree.links.new(normal_invert_node.outputs[0], normal_combine_node.inputs['G'])

        material.node_tree.links.new(normal_separate_node.outputs['B'], normal_combine_node.inputs['B'])
        material.node_tree.links.new(normal_combine_node.outputs[0], normal_map_node.inputs["Color"])

        # Set default values
        bsdf.inputs["Specular"].default_value = 0.5
        bsdf.inputs["Specular Tint"].default_value = 0.0
        bsdf.inputs["Sheen Tint"].default_value = 0.0
        bsdf.inputs["Clearcoat Roughness"].default_value = 0.0

        ################### Load HDR probe ###################

        # Common setup
        poses = os.path.join(ROOT_DIR, f"data/{DATASET}/{SCENE}/transforms_val.json")
        if not os.path.exists(poses):
            poses = os.path.join(ROOT_DIR, f"data/{DATASET}/{SCENE}/transforms_test.json")
        with open(poses, 'r') as f:
            val_cfg = json.load(f)

        camera_data   = bpy.data.cameras.new(name='Camera')
        camera_object = bpy.data.objects.new('Camera', camera_data)
        scene.collection.objects.link(camera_object)
        scene.camera  = camera_object
        camera_data.angle = val_cfg['camera_angle_x']

        for file in glob(os.path.join(ROOT_DIR, PROBE, HDR, "*.hdr")):
            envmap = scene.world.node_tree.nodes.new(type="ShaderNodeTexEnvironment")
            envmap.image = bpy.data.images.load(file)
            scene.world.node_tree.links.new(envmap.outputs[0], scene.world.node_tree.nodes['Background'].inputs['Color'])

            for i in range(8):
                mtx = np.array(val_cfg['frames'][i]['transform_matrix'], dtype=np.float32)
                scene.camera.matrix_world = Matrix(mtx)
                scene.render.filepath = os.path.join(RESULTS_PATH, os.path.basename(file)[:-4] + '_r_{0:03d}'.format(int(i)))
                if os.path.exists(os.path.join(RESULTS_PATH, os.path.basename(file)[:-4] + '_r_{0:03d}'.format(int(i))) + ".exr"): continue
                bpy.ops.render.render(write_still=True)  # render still 

for s in ["drums"]:
    relight_scene("nvdiffrecmc", "synthetic", SCENE=s)