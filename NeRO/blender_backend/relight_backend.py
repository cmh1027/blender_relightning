import argparse
import os
import sys
from pathlib import Path
import numpy as np
from collections import defaultdict
import json
print(os.path.abspath('.'))
sys.path.append(os.path.abspath('.'))
from blender_backend.blender_utils import setup, set_camera_by_pose, generate_relghting_poses, add_env_light
from mathutils import Matrix; 
import bpy
from glob import glob

def render():
    args.mesh = f'meshes/{args.root}/{args.dataset}/{args.scene}/nero-300000.ply'
    args.material = f'materials/{args.root}/{args.dataset}/{args.scene}/nero-100000'
    if args.dataset != 'glossy':
        cam_path = f'data/{args.dataset}/{args.scene}/transforms_val.json'
        if not os.path.exists(cam_path):
            cam_path = f'data/{args.dataset}/{args.scene}/transforms_test.json'
    else:
        cam_path = f'data/{args.dataset}/{args.scene}/transforms_relight.json'

    
    setup(args.height, args.width, tile_size=256**2, samples=args.samples)
    bpy.context.scene.render.film_transparent = True

    bpy.ops.import_mesh.ply(filepath=args.mesh)
    obj = bpy.data.objects[Path(args.mesh).stem]

    metallic = np.load(f'{args.material}/metallic.npy')
    roughness = np.load(f'{args.material}/roughness.npy')
    albedo = np.load(f'{args.material}/albedo.npy')

    mat_vert_color = obj.data.vertex_colors.new()
    rgb_vert_color = obj.data.vertex_colors.new()

    # a map from the unique index to the loop index
    vertex_map = defaultdict(list)
    for poly in obj.data.polygons:
        for v_ix, l_ix in zip(poly.vertices, poly.loop_indices):
            vertex_map[v_ix].append(l_ix)

    # set all loop index
    for v_ix, l_ixs in vertex_map.items():
        for l_ix in l_ixs:
            rgb_vert_color.data[l_ix].color.data.color[:3] = albedo[v_ix]
            mat_vert_color.data[l_ix].color.data.color[0] = metallic[v_ix,0]
            mat_vert_color.data[l_ix].color.data.color[1] = roughness[v_ix,0]

    if args.trans:
        # trans = np.asarray([[1,0,0],[0,0,-1],[0,1,0]],np.float32)
        obj.rotation_euler[0]=np.pi/2

    # create a material
    material = bpy.data.materials.new(name='mat')
    material.use_nodes = True
    obj.data.materials.append(material)
    bsdf_node = material.node_tree.nodes['Principled BSDF']
    bsdf_node.inputs['Specular'].default_value = 0.5
    bsdf_node.inputs['Specular Tint'].default_value = 0.0
    bsdf_node.inputs['Sheen Tint'].default_value = 0.0
    bsdf_node.inputs['Clearcoat Roughness'].default_value = 0.0

    # link base color
    color_node = material.node_tree.nodes.new("ShaderNodeVertexColor")
    color_node.layer_name = rgb_vert_color.name
    material.node_tree.links.new(color_node.outputs['Color'], bsdf_node.inputs['Base Color'])

    # link metallic and roughness
    mr_node = material.node_tree.nodes.new("ShaderNodeVertexColor")
    mr_node.layer_name = mat_vert_color.name
    sep_node = material.node_tree.nodes.new("ShaderNodeSeparateRGB")
    material.node_tree.links.new(mr_node.outputs['Color'], sep_node.inputs['Image'])
    material.node_tree.links.new(sep_node.outputs['R'], bsdf_node.inputs['Metallic'])
    material.node_tree.links.new(sep_node.outputs['G'], bsdf_node.inputs['Roughness'])
    for hdr in glob("irrmaps/*/*.hdr"):
        if 'nero' in hdr and args.dataset != 'glossy': continue 
        if 'nero' not in hdr and args.dataset == 'glossy': continue
        hdr_dataset = os.path.basename(os.path.dirname(hdr))
        args.output = f'relight/{args.root}/{hdr_dataset}/{args.dataset}/{args.scene}'
        os.makedirs(args.output, exist_ok=True)
        
        # add background light
        print('load env map ...')
        add_env_light(fn=hdr)
        with open(cam_path, 'r') as f:
            cam_cfg = json.load(f)
        camera_data   = bpy.data.cameras.new(name='Camera')
        camera_object = bpy.data.objects.new('Camera', camera_data)
        bpy.context.scene.collection.objects.link(camera_object)
        bpy.context.scene.camera  = camera_object
        camera_data.angle = cam_cfg['camera_angle_x']
        for i in range(8):
            mtx = np.array(cam_cfg['frames'][i]['transform_matrix'], dtype=np.float32)
            mtx[:3, 3] = mtx[:3, 3] / 2
            bpy.context.scene.camera.matrix_world = Matrix(mtx)
            bpy.context.scene.render.filepath = f'{args.output}/{os.path.basename(hdr)[:-4]}_r_{"%03d" % i}.png'
            bpy.ops.render.render(write_still=True)  # render still
            # img = np.array(Image.open(f'{args.output}/{os.path.basename(hdr)[:-4]}_r_{"%03d" % i}.png'))
            # crop_img = img[400:-400, 400:-400]
            # Image.fromarray(crop_img).save(Image.open(f'{args.output}/{os.path.basename(hdr)[:-4]}_r_{"%03d" % i}_resize.png'))
            # print(f'{args.output}/{os.path.basename(hdr)[:-4]}_r_{"%03d" % i}.png')
            # exit()
            

if __name__=="__main__":
    parser = argparse.ArgumentParser(description='Renders given obj file by rotation a camera around it.')
    parser.add_argument('--output', type=str, default='data/relight')
    parser.add_argument('--dataset', type=str)
    parser.add_argument('--scene', type=str)
    parser.add_argument('--root', type=str)

    parser.add_argument('--width', type=int, default=1600)
    parser.add_argument('--height', type=int, default=1600)
    parser.add_argument('--samples', type=int, default=1024)
    parser.add_argument('--cam_dist', type=float, default=3.0)
    parser.add_argument('--num', type=int, default=360)

    parser.add_argument('--trans', action='store_true', dest='trans', default=False)

    parser.add_argument('--pose_type', type=str, default='video')
    parser.add_argument('--azimuth', type=float, default=0.0)
    parser.add_argument('--elevation', type=float, default=45.0)
    parser.add_argument('--cam_path', type=str)
    parser.add_argument('--only_pose', action='store_true')
    argv = sys.argv[sys.argv.index("--") + 1:]
    args = parser.parse_args(argv)
    render()
