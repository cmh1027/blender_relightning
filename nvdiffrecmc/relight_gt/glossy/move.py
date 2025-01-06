from glob import glob
import os
import shutil
for path in glob("*"):
    if not os.path.isdir(path): continue
    idx = path.find("_")
    scene = path[:idx]
    env = path[idx+1:]
    for i in range(16):
        os.makedirs(scene, exist_ok=True)
        fname = f"{scene}/{env}_r_{'%03d' % i}.png"
        shutil.copy(os.path.join(path, f"{i}.png"), fname)