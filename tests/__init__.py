import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

this_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(this_dir, ".."))
build_dir = os.path.join(root_dir, "build")
