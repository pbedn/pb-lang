import os
import subprocess
import argparse
import shutil
from pprint import pprint

from lexer import Lexer, LexerError
from parser import Parser, ParserError
from codegen import CodeGen
from type_checker import TypeChecker, TypeError

from utils import elapsed


def compile_to_c(source_code: str, output_file: str = "out.c", verbose: bool = False, debug: bool = False):
    lexer = Lexer(source_code)
    try:
        tokens = lexer.tokenize()
        if debug: print("TOKENS:\n"); pprint(tokens); print(f"{'-'*80}\n")
    except LexerError as e:
        print(f"Lexer error: {e}")
        return False

    parser = Parser(tokens)
    try:
        ast = parser.parse()
        if debug: print("AST:\n"); pprint(ast); print(f"{'-'*80}\n")
    except ParserError as e:
        print(f"Parser error: {e}")
        return False

    # Run type checker
    try:
        checker = TypeChecker()
        checker.check(ast)
        if debug: print("ENRICHED AST:\n"); pprint(ast); print(f"{'-'*80}\n")
    except TypeError as e:
        print(f"Type Error: {e}")
        return False

    codegen = CodeGen()
    c_code = codegen.generate(ast)
    if debug: print("C CODE:\n"); print(c_code); print(f"{'-'*80}\n")

    output_path = get_build_output_path(output_file)
    with open(output_path, "w") as f:
        f.write(c_code)

    copy_runtime_header(output_path, verbose)
    if verbose: print(f"C code written to {output_path}")
    return True


def build(source_code: str, output_file: str, verbose: bool = False, debug: bool = False) -> bool:
    try:
        subprocess.run(['gcc', '--version'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if verbose: print("GCC is available")
    except FileNotFoundError:
        print("GCC is not installed or not in the system PATH.")
        print("If not installed then run `sudo apt install gcc`")
        return False
    except subprocess.CalledProcessError:
        if verbose: print("GCC is available, but an error occurred while running it.")
        return False

    success = compile_to_c(source_code, f"{output_file}.c", verbose=verbose, debug=debug)
    if not success:
        print("Skipping GCC build because type checking failed.")
        return False

    c_path = get_build_output_path(f"{output_file}.c")
    exe_file = get_build_output_path(output_file) + (".exe" if os.name == "nt" else "")
    compile_cmd = ["gcc", "-std=c99", "-W", c_path, "-o", exe_file]

    result = subprocess.run(compile_cmd, capture_output=True, text=True)
    if result.returncode == 0:
        if verbose: print(f"Built: {exe_file}")
        return True
    else:
        print(f"GCC build failed (exit code {result.returncode})")
        print(f"Error output: {result.stderr}")
        return False


def run(source_code: str, output_file: str, verbose: bool = False, debug: bool = False):
    success = build(source_code, output_file, verbose=verbose, debug=debug)
    if not success:
        print("Skipping run because compilation failed.")
        return
    # exe_file = output_file + (".exe" if os.name == "nt" else "")
    exe_file = get_build_output_path(output_file) + (".exe" if os.name == "nt" else "")
    if verbose: print("Running:", exe_file)
    if verbose: print("\n")
    subprocess.run([exe_file])
    if verbose: print("\n")


def get_build_output_path(output_file: str) -> str:
    build_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "build"))
    os.makedirs(build_dir, exist_ok=True)
    return os.path.join(build_dir, output_file)

@elapsed
def copy_runtime_header(c_output_path: str, verbose: bool = False):
    """
    Copies 'runtime.h' from the same directory as this script
    to the directory containing the C file (overwriting if exists).
    """
    dest_dir = os.path.dirname(c_output_path)
    this_dir = os.path.dirname(os.path.abspath(__file__))
    runtime_src = os.path.join(this_dir, "runtime.h")

    if not os.path.isfile(runtime_src):
        raise FileNotFoundError(f"runtime.h not found at: {runtime_src}")

    dest_path = os.path.join(dest_dir, "runtime.h")

    # Only copy if destination does not exist or is older than source
    need_copy = (
        not os.path.exists(dest_path)
        or os.path.getmtime(runtime_src) > os.path.getmtime(dest_path)
    )
    if need_copy:
        shutil.copy2(runtime_src, dest_path)
        if verbose: print(f"[info] Copied runtime.h to {dest_path}")
    else:
        if verbose: print(f"[info] runtime.h in {dest_dir} is up to date")


def main():
    parser = argparse.ArgumentParser(description="PB Language Toolchain")
    parser.add_argument("command", choices=["toc", "build", "run"], help="Action to perform")
    parser.add_argument("file", help="Path to .pb source file")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug output")
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
