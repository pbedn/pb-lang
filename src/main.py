import os
import subprocess
import argparse
import shutil
from pprint import pprint

from lexer import Lexer, LexerError
from lang_ast import ImportStmt, ImportFromStmt
from parser import Parser, ParserError
from codegen import CodeGen
from module_loader import load_module
from type_checker import TypeChecker, TypeError
from pb_pipeline import compile_code_to_c_and_h 

RICH_PRINT = False

def pretty_print_code(code: str, lexer="c"):
    """
    Pretty print code using the rich library.
    """
    if RICH_PRINT:
        from rich.syntax import Syntax
        from rich.console import Console
        syntax = Syntax(code, lexer, theme="lightbulb", line_numbers=True, background_color="#0C0C0C")
        Console().print(syntax)
    else:
        print(code)


def enable_rich():
    global RICH_PRINT
    from rich.pretty import pprint as rich_pprint
    globals()['pprint'] = rich_pprint
    RICH_PRINT = True


def compile_to_c(
    source_code: str, pb_path: str, output_file: str = "out.c", 
    verbose: bool = False, debug: bool = False
):
    basename = os.path.splitext(os.path.basename(pb_path))[0]
    h_code, c_code, ast, loaded_modules = compile_code_to_c_and_h(
        source_code,
        module_name=basename,
        debug=debug,
        verbose=verbose,
        pretty_print_code=pretty_print_code,
        pprint=pprint,
        import_support=True,
        pb_path=pb_path
    )
    if ast is None:
        return (False, None, {})
    output_h_path = get_build_output_path(output_file.replace(".c", ".h"))
    with open(output_h_path, "w") as f:
        f.write(h_code)
    output_c_path = get_build_output_path(output_file)
    with open(output_c_path, "w") as f:
        f.write(c_code)
    if verbose: print(f"C code written to {output_c_path}")
    return (True, ast, loaded_modules)


def build(source_code: str, pb_path: str, output_file: str, verbose: bool = False, debug: bool = False) -> bool:
    if not debug: check_gcc_installed(verbose)

    # Compile entry point to C
    success, ast, loaded_modules = compile_to_c(source_code, pb_path, f"{output_file}.c", verbose=verbose, debug=debug)
    if not success:
        print("Skipping GCC build because type checking failed.")
        return False

    # For each module, generate .c and .h
    build_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "build"))
    module_c_files = []
    for mod in loaded_modules.values():
        if not hasattr(mod, "program"):
            continue  # Defensive: only process modules with AST
        c_file = write_module_code_files(mod, build_dir, verbose, debug)
        module_c_files.append(c_file)

    c_path = get_build_output_path(f"{output_file}.c")
    module_c_files.append(c_path)

    exe_file = get_build_output_path(output_file) + (".exe" if os.name == "nt" else "")

    runtime_header = get_build_output_path("pb_runtime.h")
    runtime_lib = get_build_output_path("pb_runtime.a")

    # -- Disabled while still prototyping
    # Check if runtime library exists
    # if not os.path.isfile(runtime_lib):
        # if verbose: print("Runtime library not found; building it now...")
        # build_runtime_library(verbose=verbose, debug=debug)    
    build_runtime_library(verbose=verbose, debug=debug)    

    compile_cmd = [
        "gcc", "-std=c99",
        "-Wall",        # common warnings
        "-Wextra",      # extra warnings
        "-Wconversion", # warns about implicit type conversions
        "-Wpedantic",   # enforces ISO C standard
        *module_c_files,
        "-o", exe_file,
        "-I", build_dir,
        runtime_lib
    ]
    if verbose: print("Compile command:", " ".join(compile_cmd))

    result = subprocess.run(compile_cmd, capture_output=True, text=True)
    if result.returncode == 0:
        if verbose: print(f"Built: {exe_file}")
        return True
    else:
        print(f"GCC build failed (exit code {result.returncode})")
        print(f"Error output: {result.stderr}")
        return False


def run(source_code: str, pb_path: str, output_file: str, verbose: bool = False, debug: bool = False):
    success = build(source_code, pb_path, output_file, verbose=verbose, debug=debug)
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


def write_module_code_files(mod_symbol, build_dir, verbose: bool = False, debug: bool = False):
    # Derive path: e.g. "foo/bar" -> "build/foo/bar.h", "build/foo/bar.c"
    rel_path = mod_symbol.name.replace(".", os.sep)
    mod_dir = os.path.join(build_dir, os.path.dirname(rel_path))
    os.makedirs(mod_dir, exist_ok=True)
    basename = os.path.basename(rel_path)

    h_path = os.path.join(mod_dir, f"{basename}.h")
    c_path = os.path.join(mod_dir, f"{basename}.c")
    codegen = CodeGen()
    h_code = codegen.generate_header(mod_symbol.program)
    if debug: print(f"Module HEADER: {basename}.h\n"); pretty_print_code(h_code, "c"); print(f"{'-'*80}\n")
    c_code = codegen.generate(mod_symbol.program)
    if debug: print(f"Module CODE: {basename}.c\n"); pretty_print_code(c_code, "c"); print(f"{'-'*80}\n")

    with open(h_path, "w") as f:
        f.write(h_code)
    with open(c_path, "w") as f:
        f.write(c_code)
    return c_path  # return path for later GCC command


def build_runtime_library(verbose: bool = False, debug: bool = False):
    """
    Builds the PB runtime into a static library (pb_runtime.a)
    and copies the header to the build directory.
    """
    this_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(this_dir, ".."))
    src_c = os.path.join(this_dir, "pb_runtime.c")
    src_h = os.path.join(this_dir, "pb_runtime.h")
    build_dir = os.path.join(root_dir, "build")
    os.makedirs(build_dir, exist_ok=True)

    lib_path = os.path.join(build_dir, "pb_runtime.a")
    header_dest = os.path.join(build_dir, "pb_runtime.h")

    if not os.path.isfile(src_c):
        print(f"pb_runtime.c not found at: {src_c}")
        return

    # Compile to object file
    obj_path = os.path.join(build_dir, "pb_runtime.o")
    compile_cmd = ["gcc", "-std=c99", "-c", src_c, "-o", obj_path]
    if verbose: print("PB Runtime compile command:", " ".join(compile_cmd))

    result = subprocess.run(compile_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Compilation failed:\n{result.stderr}")
        return

    # Archive into static library
    # lib_path = os.path.join(build_dir, "libpbruntime.a")
    ar_cmd = ["ar", "rcs", lib_path, obj_path]
    if verbose: print("Archive command:", " ".join(ar_cmd))

    result = subprocess.run(ar_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Archiving failed:\n{result.stderr}")
        return

    if verbose:
        print(f"Built static library: {lib_path}")

    # Copy header
    shutil.copy2(src_h, header_dest)
    if verbose:
        print(f"Copied pb_runtime.h to: {header_dest}")


def check_gcc_installed(verbose):
    """
    Check if GCC is installed by running 'gcc --version'.
    If not installed, print an error message and exit.
    """
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


def main():
    parser = argparse.ArgumentParser(description="PB Language Toolchain")
    parser.add_argument("command", choices=["toc", "build", "run", "buildlib"], help="Action to perform")
    parser.add_argument("file", nargs="?", help="Path to .pb source file")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug output")
    parser.add_argument("-r", "--rich", action="store_true", help="Pretty print with rich")
    args = parser.parse_args()

    if args.rich:
        enable_rich()
    
    try:
        if args.command == "buildlib":
            build_runtime_library(verbose=args.verbose, debug=args.debug)
            return

        if not args.file or not args.file.endswith(".pb"):
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
            compile_to_c(code, pb_path, f"{output_filename}.c", verbose=args.verbose, debug=args.debug)
        elif args.command == "build":
            build(code, pb_path, output_filename, verbose=args.verbose, debug=args.debug)
        elif args.command == "run":
            run(code, pb_path, output_filename, verbose=args.verbose, debug=args.debug)

    except Exception as e:
        print(f"{type(e).__name__}: {e}")
        exit(1)

if __name__ == "__main__":
    main()
