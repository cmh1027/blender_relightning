import argparse
import subprocess
import os
from glob import glob

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', type=str)
    parser.add_argument('--scene', type=str)
    parser.add_argument('--trans', dest='trans', action='store_true', default=False)
    parser.add_argument('--root', type=str, default="nero")
    args = parser.parse_args()

    cmds = [
        'Blender', '--background', '--python', 'blender_backend/relight_backend.py', '--',
        '--dataset', args.dataset,
        '--scene', args.scene,
        '--root', args.root
    ]
    subprocess.run(cmds)


if __name__ == "__main__":
    main()
