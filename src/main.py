import os
import subprocess
import argparse
from lexer import Lexer, LexerError
from parser import Parser, ParserError
from codegen import CCodeGenerator
from type_checker import TypeChecker, LangTypeError
from pprint import pprint

def compile_to_c(source_code: str, output_file: str = "out.c", verbose: bool = False, debug: bool = False):
    lexer = Lexer(source_code)
    try:
        tokens = lexer.tokenize()
    except LexerError as e:
        print(f"Lexer error: {e}")
        return False

    parser = Parser(tokens)
    if debug: pprint(tokens)
    try:
        ast = parser.parse()
        if debug: pprint(ast)
    except ParserError as e:
        print(f"Parser error: {e}")
        return False

    # Run type checker
    try:
        checker = TypeChecker()
        checker.check(ast)
        if verbose:
            print(f"-- Registered globals:")
            for k,v in checker.global_env.items():
                print(f"{k} -> {v}")
            print("-- Registered functions:")
            for k, v in checker.functions.items():
                print(f"{k}: {v}")
            print("\n")
        functions = checker.functions
    except LangTypeError as e:
        print(f"❌ Type Error: {e}")
        return False

    global_vars = checker.global_env  # Dict: name -> type
    codegen = CCodeGenerator(functions=functions, global_vars=global_vars)
    c_code = codegen.generate(ast)

    output_path = get_build_output_path(output_file)
    with open(output_path, "w") as f:
        f.write(c_code)
    print(f"C code written to {output_path}")
    return True


def build(source_code: str, output_file: str, verbose: bool = False, debug: bool = False) -> bool:
    success = compile_to_c(source_code, f"{output_file}.c", verbose=verbose, debug=debug)
    if not success:
        print("Skipping GCC build because type checking failed.")
        return False

    c_path = get_build_output_path(f"{output_file}.c")
    exe_file = get_build_output_path(output_file) + (".exe" if os.name == "nt" else "")
    compile_cmd = ["gcc", "-std=c99", "-W", c_path, "-o", exe_file]

    result = subprocess.run(compile_cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"Built: {exe_file}")
        return True
    else:
        print(f"❌ GCC build failed (exit code {result.returncode})")
        print(f"Error output: {result.stderr}")
        return False



def run(source_code: str, output_file: str, verbose: bool = False, debug: bool = False):
    success = build(source_code, output_file, verbose=verbose, debug=debug)
    if not success:
        print("Skipping run because compilation failed.")
        return
    # exe_file = output_file + (".exe" if os.name == "nt" else "")
    exe_file = get_build_output_path(output_file) + (".exe" if os.name == "nt" else "")
    print("Running:", exe_file)
    print("\n")
    subprocess.run([exe_file])
    print("\n")


def get_build_output_path(output_file: str) -> str:
    build_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "build"))
    os.makedirs(build_dir, exist_ok=True)
    return os.path.join(build_dir, output_file)


def main():
    parser = argparse.ArgumentParser(description="Fast Python Language Toolchain")
    parser.add_argument("command", choices=["toc", "build", "run"], help="Action to perform")
    parser.add_argument("file", help="Path to .pb source file")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    args = parser.parse_args()

    if not args.file.endswith(".pb"):
        print("Input file must be .pb")
        return

    pb_path = args.file
    if not os.path.isabs(pb_path):
        pb_path = os.path.join(os.path.dirname(__file__), "..", pb_path)

    with open(pb_path) as f:
        code = f.read()


    output_path = os.path.splitext(args.file)[0]
    output_filename = os.path.basename(output_path)

    if args.command == "toc":
        compile_to_c(code, f"{output_filename}.c", verbose=args.verbose, debug=args.debug)
    elif args.command == "build":
        build(code, output_filename, verbose=args.verbose, debug=args.debug)
    elif args.command == "run":
        run(code, output_filename, verbose=args.verbose, debug=args.debug)

if __name__ == "__main__":
    main()
