import os
import sys
import runpy

current_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(current_dir)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

if __name__ == "__main__":
    target = os.path.join(current_dir, "BB_RB.py")
    runpy.run_path(target, run_name="__main__")
