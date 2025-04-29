#!/usr/bin/env python3

import sys
import os
import subprocess
from lexer import Lexer
from parser import Parser
from codegen import emit_c

def build(file_path, output_path):
    with open(file_path) as f:
        code = f.read()

    tokens = Lexer(code).tokenize()
    tree = Parser(tokens).parse()
    c_code = emit_c(tree)

    c_file = output_path + ".c"
    with open(c_file, "w") as f:
        f.write(c_code)

    exe_file = output_path + (".exe" if os.name == "nt" else "")
    compile_cmd = ["gcc", c_file, "-o", exe_file]
    subprocess.run(compile_cmd, check=True)

    print(f"Built: {exe_file}")

def run(file_path):
    output_path = os.path.splitext(file_path)[0]
    build(file_path, output_path)

    exe_file = output_path + (".exe" if os.name == "nt" else "")
    print("Running:", exe_file)
    subprocess.run([exe_file])

def main():
    if len(sys.argv) < 3:
        print("Usage: pyc build|run file.pyc")
        sys.exit(1)

    cmd, file_path = sys.argv[1], sys.argv[2]
    if not file_path.endswith(".pyc"):
        print("Input file must be .pyc")
        sys.exit(1)

    if cmd == "build":
        output_path = os.path.splitext(file_path)[0]
        build(file_path, output_path)
    elif cmd == "run":
        run(file_path)
    else:
        print("Unknown command:", cmd)

if __name__ == "__main__":
    main()
