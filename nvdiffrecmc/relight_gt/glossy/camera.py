from glob import glob
import os
import numpy as np
import json
import pickle

def compute_fovx(K):
    fx = K[0, 0]  # Focal length in x-direction
    width = 2 * fx  # Sensor width in pixels (assuming square pixels)
    fovx = 2 * np.arctan(width / (2 * fx))  # Horizontal field of view
    return fovx

def convert_pose_to_extrinsic(w2c):
    c2w = np.linalg.inv(np.array(w2c))
    transform = np.array([
        [1, 0, 0, 0],
        [0, -1, 0, 0],
        [0, 0, -1, 0],
        [0, 0, 0, 1]
    ]).astype(np.float32)
    c2w = c2w @ transform # OpenCV -> OpenGL
    return c2w

scenes = ['angel', 'bell', 'cat', 'horse', 'luyu', 'potion', 'table_bell', 'teapot']
for scene in scenes:

    meta = {"camera_angle_x": None, "frames": []}
    for idx, camera_path in enumerate(sorted(glob(os.path.join(scene+"_corridor", "*-camera.pkl")))):
        camera = pickle.load(open(camera_path, "rb")) # Extrinsic (w2c) OpenCV
        w2c, K = camera
        if idx == 0:
            fovx = compute_fovx(K)
            meta["camera_angle_x"] = fovx
        
        image_path = "./" + os.path.basename(camera_path).replace("-camera.pkl", "")
        w2c = w2c.tolist() + [[0., 0., 0., 1.]]
        meta['frames'].append(
            {
                "file_path": image_path,
                "transform_matrix": convert_pose_to_extrinsic(w2c).tolist() # Camera pose (c2w)
            },
        )
    os.makedirs(os.path.dirname(os.path.join("poses", scene, "transforms_val.json")), exist_ok=True)
    json.dump(meta, open(os.path.join("poses", scene, "transforms_relight.json"), "w"))