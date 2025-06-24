import sys
import os
import types
import ast

def has_main_function(source):
    """Check if the source defines a top-level def main()."""
    try:
        tree = ast.parse(source)
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name == "main":
                return True
        return False
    except SyntaxError as e:
        print(f"Syntax error while parsing: {e}")
        return False

def run_pb(filepath):
    filepath = os.path.abspath(filepath)
    with open(filepath, "r", encoding="utf-8") as f:
        source = f.read()

    if has_main_function(source):
        source += "\n\nmain()\n"

    code = compile(source, filepath, mode="exec")
    modname = os.path.splitext(os.path.basename(filepath))[0]
    mod = types.ModuleType(modname)
    mod.__file__ = filepath
    exec(code, mod.__dict__)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python run_pb_file.py <path/to/file.pb>")
        sys.exit(1)

    run_pb(sys.argv[1])
