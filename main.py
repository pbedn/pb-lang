import os
import subprocess
import argparse
from lexer import Lexer
from parser import Parser
from codegen import CCodeGenerator
from type_checker import TypeChecker, TypeError
from pprint import pprint

def compile_to_c(source_code: str, output_file: str = "out.c"):
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()

    parser = Parser(tokens)
    # pprint(tokens)
    ast = parser.parse()
    # pprint(ast)

    # ✅ Run type checker
    try:
        checker = TypeChecker()
        checker.check(ast)
        # todo: add debug option to print stuff
        print("Registered functions:", checker.functions)
        functions = checker.functions
    except TypeError as e:
        print(f"❌ Type Error: {e}")
        return False  # signal failure

    # ✅ Generate C code if type check passes
    codegen = CCodeGenerator(functions=functions)
    c_code = codegen.generate(ast)

    with open(output_file, "w") as f:
        f.write(c_code)
    print(f"✅ C code written to {output_file}")
    return True  # signal success

def build(source_code: str, output_file: str) -> bool:
    success = compile_to_c(source_code, f"{output_file}.c")
    if not success:
        print("⚠️ Skipping GCC build because type checking failed.")
        return False

    exe_file = output_file + (".exe" if os.name == "nt" else "")
    compile_cmd = ["gcc", f"{output_file}.c", "-o", exe_file]
    result = subprocess.run(compile_cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"✅ Built: {exe_file}")
        return True
    else:
        print(f"❌ GCC build failed (exit code {result.returncode})")
        print(result.stderr)
        return False


def run(source_code: str, output_file: str):
    success = build(source_code, output_file)
    if not success:
        print("⚠️ Skipping run because compilation failed.")
        return

    exe_file = output_file + (".exe" if os.name == "nt" else "")
    print("Running:", exe_file)
    print("\n")
    subprocess.run([exe_file])
    print("\n")

def main():
    parser = argparse.ArgumentParser(description="Fast Python Language Toolchain")
    parser.add_argument("command", choices=["toc", "build", "run"], help="Action to perform")
    parser.add_argument("file", help="Path to .pb source file")
    args = parser.parse_args()

    if not args.file.endswith(".pb"):
        print("Input file must be .pb")
        return

    with open(args.file) as f:
        code = f.read()

    output_path = os.path.splitext(args.file)[0]

    if args.command == "toc":
        compile_to_c(code, f"{output_path}.c")
    elif args.command == "build":
        build(code, output_path)
    elif args.command == "run":
        run(code, output_path)

if __name__ == "__main__":
    main()
