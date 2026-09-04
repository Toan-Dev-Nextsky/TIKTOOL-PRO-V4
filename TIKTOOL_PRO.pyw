import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(current_dir)
sys.path.insert(0, current_dir)

if __name__ == "__main__":
    with open(os.path.join(current_dir, "BB_RB.py"), "rb") as f:
        code = compile(f.read(), "BB_RB.py", "exec")
        exec(code, {"__name__": "__main__"})
