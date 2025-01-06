import numpy as np
import json
import os
# Update transformation matrices to include translation for camera distance of 1 unit from the origin
transforms = []
azimuth_angles_rad = [0, 45, 90, 135, 180, 225, 270, 315]
elevation_angles_rad = [-30, 0, 30, 60]
for azimuth_rad, elevation_rad in [(azimuth, elevation) for azimuth in azimuth_angles_rad for elevation in elevation_angles_rad]:
    # Calculate the translation vector
    x = np.cos(elevation_rad) * np.cos(azimuth_rad)
    y = np.cos(elevation_rad) * np.sin(azimuth_rad)
    z = np.sin(elevation_rad)
    translation_vector = np.array([x, y, z])
    
    # Rotation matrix for azimuth (around Y-axis)
    R_y = np.array([
        [np.cos(azimuth_rad), np.sin(azimuth_rad), 0],
        [0, 1, 0],
        [-np.sin(azimuth_rad), 0, np.cos(azimuth_rad)]
    ])

    # Rotation matrix for elevation (around X-axis)
    R_x = np.array([
        [1, 0, 0],
        [0, np.cos(elevation_rad), -np.sin(elevation_rad)],
        [0, np.sin(elevation_rad), np.cos(elevation_rad)]
    ])

    # Overall rotation matrix R = R_x * R_y
    R = np.dot(R_x, R_y)
    
    # Create the 4x4 transformation matrix including translation
    transformation_matrix = np.eye(4)
    transformation_matrix[:3, :3] = R
    transformation_matrix[:3, 3] = translation_vector
    transforms.append(transformation_matrix)

for scene in ["ficus"]:
    with open(f"data/synthetic/{scene}/transforms_train.json", "r") as f:
        meta = json.load(f)
    new_meta = {'camera_angle_x':meta['camera_angle_x'], 'frames':[]}
    for mat in transforms:
        new_meta['frames'].append({"transform_matrix":mat.tolist()})
    os.makedirs(f"sparse/{scene}", exist_ok=True)
    with open(f"sparse/{scene}/transform_train.json", "w") as f:
        json.dump(new_meta, f)