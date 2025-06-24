import unittest
import subprocess
import tempfile
import sys
import os
import shutil
import ast

from type_checker import TypeError
from lexer import Lexer
from parser import Parser
from codegen import CodeGen
from type_checker import TypeChecker
from pb_pipeline import compile_code_to_c_and_h
from main import build_runtime_library
from main import get_build_output_path
from tests import build_dir


def _compile_and_run_modules(modules: dict[str, str]) -> str:
    """
    Compiles and runs PB code from multiple in-memory modules.
    Writes each to disk to support real module imports.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        c_files = []

        # Step 1: Write all .pb files
        for name, code in modules.items():
            pb_rel = f"{name.replace('.', os.sep)}.pb"
            pb_file = os.path.join(tmpdir, pb_rel)
            os.makedirs(os.path.dirname(pb_file), exist_ok=True)
            with open(pb_file, "w", encoding="utf-8") as f:
                f.write(code)

        # Step 2: Compile each module using real pb_path
        for name in modules:
            pb_file = os.path.join(tmpdir, f"{name.replace('.', os.sep)}.pb")
            h_code, c_code, ast, _ = compile_code_to_c_and_h(
                source_code=modules[name],
                module_name=name,
                debug=False,
                verbose=False,
                import_support=True,
                pb_path=pb_file  # Now real path
            )
            if ast is None:
                raise RuntimeError(f"Type-checking failed for module '{name}'")

            h_path = os.path.join(tmpdir, f"{name}.h")
            c_path = os.path.join(tmpdir, f"{name}.c")
            with open(h_path, "w", encoding="utf-8") as f:
                f.write(h_code)
            with open(c_path, "w", encoding="utf-8") as f:
                f.write(c_code)

            c_files.append(c_path)

        exe_path = os.path.join(tmpdir, "main")
        if sys.platform == "win32":
            exe_path += ".exe"

        runtime_lib = get_build_output_path("pb_runtime.a")
        runtime_header = get_build_output_path("pb_runtime.h")
        if not os.path.isfile(runtime_lib) or not os.path.isfile(runtime_header):
            build_runtime_library(verbose=False, debug=False)
        # Copy the runtime header next to generated sources to avoid picking up
        # unrelated headers that may exist in the system include paths on some
        # platforms (e.g. Windows)
        shutil.copy2(runtime_header, os.path.join(tmpdir, "pb_runtime.h"))

        compile_cmd = [
            "gcc", "-std=c99", "-W",
            *c_files,
            "-o", exe_path,
            "-I", tmpdir,
            "-I", get_build_output_path(""),
            runtime_lib
        ]

        result = subprocess.run(compile_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"GCC build failed:\n{result.stderr}")

        run_result = subprocess.run([exe_path], capture_output=True, text=True)
        return (run_result.stdout + run_result.stderr).strip()



def compile_and_run(code: str) -> str:
    """
    Compiles and runs a single-module PB program (as 'main').
    """
    return _compile_and_run_modules({"main": code})


def compile_modules_and_run_main(modules: dict[str, str]) -> str:
    """
    Compiles and runs a PB program consisting of multiple modules.
    The 'main' module must be included in `modules`.
    """
    if "main" not in modules:
        raise ValueError("Expected a 'main' module in provided modules.")
    return _compile_and_run_modules(modules)


class TestPipelineRuntime(unittest.TestCase):

    def test_global_runtime_update(self):
        code = (
            "x: int = 10\n"
            "\n"
            "def main() -> int:\n"
            "    global x\n"
            "    x = 20\n"
            "    print(x)\n"
            "    return 0\n"
        )
        output = compile_and_run(code)
        self.assertIn("20", output)

    def test_global_shadowing_runtime(self):
        code = (
            "x: int = 10\n"
            "\n"
            "def main() -> int:\n"
            "    x = 5\n"
            "    print(x)\n"
            "    return x\n"
        )
        output = compile_and_run(code)
        self.assertIn("5", output)

    def test_global_read_then_update(self):
        code = (
            "x: int = 1\n"
            "\n"
            "def main() -> int:\n"
            "    print(x)\n"
            "    global x\n"
            "    x = 42\n"
            "    print(x)\n"
            "    return 0\n"
        )
        output = compile_and_run(code)
        lines = output.splitlines()
        self.assertEqual(lines[0], "1")
        self.assertEqual(lines[1], "42")

    def test_global_float_update_runtime(self):
        code = (
            "x: float = 1.5\n"
            "\n"
            "def main() -> int:\n"
            "    print(x)\n"
            "    global x\n"
            "    x = 3.5\n"
            "    print(x)\n"
            "    return 0\n"
        )
        output = compile_and_run(code)
        lines = output.strip().splitlines()
        self.assertEqual(lines[0], "1.5")
        self.assertEqual(lines[1], "3.5")

    def test_list_indexing_and_printing(self):
        code = (
            "def main() -> int:\n"
            "    arr_int: list[int] = [100]\n"
            "    print(arr_int[0])\n"
            "    arr_int[0] = 1\n"
            "    x: int = arr_int[0]\n"
            "    print(x)\n"
            "    print(arr_int[0])\n"
            "    print(arr_int)\n"
            "\n"
            "    arr_str: list[str] = [\"a\", 'b']\n"
            "    print(arr_str[0])\n"
            "    arr_str[0] = \"C\"\n"
            "    arr_str[1] = \"C\"\n"
            "    print(arr_str[0])\n"
            "    print(arr_str)\n"
            "\n"
            "    arr_bool: list[bool] = [True]\n"
            "    arr_bool[0] = False\n"
            "    print(arr_bool)\n"
            "    return 0\n"
        )
        output = compile_and_run(code)
        lines = output.strip().splitlines()

        # Assertions for arr_int
        self.assertEqual(lines[0], "100")              # arr_int[0] before assignment
        self.assertEqual(lines[1], "1")                # arr_int[0] after assignment
        self.assertEqual(lines[2], "1")                # arr_int[0] after assignment
        self.assertEqual(lines[3], "[1]")              # arr_int list contents

        # Assertions for arr_str
        self.assertEqual(lines[4], "a")                # arr_str[0] before assignment
        self.assertEqual(lines[5], "C")                # arr_str[0] after assignment
        self.assertEqual(lines[6], "['C', 'C']")           # arr_str list contents

        # Assertions for arr_bool
        self.assertEqual(lines[7], "[False]")          # arr_bool after assignment

    def test_type_conversions_and_printing(self):
        code = (
            "def main() -> int:\n"
            "    x: int = 10\n"
            "    y: float = 1.0\n"
            "    z: float = 0.0\n"
            "    a: str = '1'\n"
            "    b: str = '1.0'\n"
            "\n"
            "    x_float: float = float(x)\n"
            "    print(f'x: {x}, x_float: {x_float}')\n"
            "\n"
            "    b_float: float = float(b)\n"
            "    print(f'b: {b}, b_float: {b_float}')\n"
            "\n"
            "    y_int: int = int(y)\n"
            "    print(f'y: {y}, y_int: {y_int}')\n"
            "\n"
            "    a_int: int = int(a)\n"
            "    print(f'a: {a}, a_int: {a_int}')\n"
            "\n"
            "    x_bool: bool = bool(x)\n"
            "    print(f'x: {x}, x_bool: {x_bool}')\n"
            "\n"
            "    y_bool: bool = bool(y)\n"
            "    print(f'y: {y}, y_bool: {y_bool}')\n"
            "\n"
            "    z_bool: bool = bool(z)\n"
            "    print(f'z: {z}, z_bool: {z_bool}')\n"
            "\n"
            "    return 0\n"
        )
        output = compile_and_run(code)
        lines = output.strip().splitlines()

        # Assertions for type conversions
        self.assertEqual(lines[0], "x: 10, x_float: 10.0")  # x to float
        self.assertEqual(lines[1], "b: 1.0, b_float: 1.0")  # b to float
        self.assertEqual(lines[2], "y: 1.0, y_int: 1")        # y to int
        self.assertEqual(lines[3], "a: 1, a_int: 1")        # a to int
        self.assertEqual(lines[4], "x: 10, x_bool: True")     # x to bool
        self.assertEqual(lines[5], "y: 1.0, y_bool: True")    # y to bool
        self.assertEqual(lines[6], "z: 0.0, z_bool: False")    # z to bool

    def test_fstring_expression_variants(self):
        code = (
            "class Player:\n"
            "    species: str = \"Human\"\n"
            "\n"
            "    def __init__(self, hp: int):\n"
            "        self.hp = hp\n"
            "        self.name = \"Hero\"\n"
            "\n"
            "    def get_name(self) -> str:\n"
            "        return self.name\n"
            "\n"
            "def main() -> int:\n"
            "    x: int = 5\n"
            "    print(f\"Simple fstring: x={x}\")\n"
            "    print(f\"x + 1: {x + 1}\")\n"
            "    print(f\"Float conversion: {float(2)}\")\n"
            "    print(\"--------------------------------\")\n"
            "\n"
            "    p: Player = Player(100)\n"
            "    print(f\"player.hp: {p.hp}\")\n"
            "    print(f\"player get_name: {p.get_name()}\")\n"
            "    print(f\"Player.species: {Player.species}\")\n"
            "    return 0\n"
        )
        output = compile_and_run(code)
        lines = output.strip().splitlines()

        # Assertions for correctness of f-string interpolation
        self.assertEqual(lines[0], "Simple fstring: x=5")
        self.assertEqual(lines[1], "x + 1: 6")
        self.assertEqual(lines[2], "Float conversion: 2.0")
        self.assertEqual(lines[3], "--------------------------------")
        self.assertEqual(lines[4], "player.hp: 100")
        self.assertEqual(lines[5], "player get_name: Hero")
        self.assertEqual(lines[6], "Player.species: Human")

    def test_runtime_exception_is_raised(self):
        code = (
            "class Exception:\n"
            "    def __init__(self, msg: str):\n"
            "        self.msg = msg\n"
            "\n"
            "class RuntimeError(Exception):\n"
            "    def __init__(self, msg: str):\n"
            "        Exception.__init__(self, msg)\n"
            "\n"
            "def crash():\n"
            "    raise RuntimeError(\"division by zero\")\n"
            "\n"
            "def main():\n"
            "    crash()\n"
        )
        output = compile_and_run(code)
        self.assertIn("RuntimeError: division by zero", output)

    def test_reraise(self):
        code = (
            "class Exception:\n"
            "    def __init__(self, msg: str):\n"
            "        self.msg = msg\n"
            "\n"
            "class MyError(Exception):\n"
            "    pass\n"
            "\n"
            "def foo():\n"
            "    try:\n"
            "        raise MyError('oops')\n"
            "    except:\n"
            "        raise\n"
            "\n"
            "def main():\n"
            "    try:\n"
            "        foo()\n"
            "    except MyError as e:\n"
            "        print(e.msg)\n"
        )
        output = compile_and_run(code)
        self.assertEqual(output.strip(), "oops")

    def test_finally_runs(self):
        code = (
            "def main():\n"
            "    try:\n"
            "        print('A')\n"
            "    finally:\n"
            "        print('B')\n"
        )
        output = compile_and_run(code)
        self.assertEqual(output.strip().splitlines(), ['A', 'B'])

    def test_default_arguments(self):
        code = (
            "def increment(x: int, step: int = 1) -> int:\n"
            "    return x + step\n"
            "\n"
            "def main():\n"
            "    a: int = increment(5)\n"
            "    b: int = increment(5, 3)\n"
            "    print(a)\n"
            "    print(b)\n"
        )
        output = compile_and_run(code)
        lines = output.strip().splitlines()
        self.assertEqual(lines[0], "6")
        self.assertEqual(lines[1], "8")

    def test_classes(self):
        code = (
            "# Class can be empty\n"
            "class Empty:\n"
            "    pass\n"
            "\n"
            "# Can have class attributes\n"
            "class ClassWithAttr:\n"
            "    attr1: str = 'some attr'\n"
            "    ATR2: str = 'other attr'\n"
            "\n"
            "class ClassWithUserDefinedAttr:\n"
            "    uda: Empty = Empty()\n"
            "\n"
            "class Player:\n"
            "    name: str = 'P'\n"
            "\n"
            "    def __init__(self) -> None:\n"
            "        self.hp = 150\n"
            "\n"
            "    def get_hp(self) -> int:\n"
            "        return self.hp\n"
            "\n"
            "class Mage(Player):\n"
            "\n"
            "    def __init__(self) -> None:\n"
            "        Player.__init__(self)\n"
            "        self.mana = 200\n"
            "\n"
            "def main() -> int:\n"
            "    p: Player = Player()\n"
            "    print(p.hp)\n"
            "    print(p.get_hp())\n"
            "    print(Player.name)\n"
            "    m: Mage = Mage()\n"
            "    print(m.hp)\n"
            "    print(m.mana)\n"
            "    print(m.get_hp())\n"
            "    return 0\n"
        )
        output = compile_and_run(code)
        lines = output.strip().splitlines()
        self.assertEqual(lines[0], "150")
        self.assertEqual(lines[1], "150")
        self.assertEqual(lines[2], "P")
        self.assertEqual(lines[3], "150")
        self.assertEqual(lines[4], "200")
        self.assertEqual(lines[5], "150")

    def test_class_field_without_initializer_runtime(self):
        code = (
            "class Foo:\n"
            "    val: int\n"
            "\n"
            "    def __init__(self) -> None:\n"
            "        self.val = 5\n"
            "\n"
            "def main() -> int:\n"
            "    f: Foo = Foo()\n"
            "    print(f.val)\n"
            "    return 0\n"
        )
        output = compile_and_run(code)
        self.assertEqual(output.strip(), "5")

    def test_import_mathlib_add(self):
        modules = {
            "mathlib": (
                "PI: float = 3.1415\n"
                "\n"
                "def add(a: int, b: int) -> int:\n"
                "    return a + b\n"
            ),
            "main": (
                "import mathlib\n"
                "\n"
                "def main() -> int:\n"
                "    mathlib.add(5, 4)\n"
                "    print(mathlib.add(5, 4))\n"
                "    x: int = mathlib.add(5, 4)\n"
                "    print(x)\n"
                "    print(mathlib.PI)\n"
                "    return 0\n"
            )
        }

        output = compile_modules_and_run_main(modules)
        lines = output.strip().splitlines()
        self.assertEqual(lines[0], "9")
        self.assertEqual(lines[1], "9")
        self.assertEqual(lines[2], "3.1415")

    def test_from_import_function(self):
        modules = {
            "mathlib": (
                "def add(a: int, b: int) -> int:\n"
                "    return a + b\n"
            ),
            "main": (
                "from mathlib import add\n"
                "\n"
                "def main() -> int:\n"
                "    print(add(2, 3))\n"
                "    return 0\n"
            )
        }

        output = compile_modules_and_run_main(modules)
        self.assertEqual(output.strip(), "5")
    
    def test_file_read_write(self):
        code = (
            "def main() -> int:\n"
            "    f: file = open('tmp.txt', 'w')\n"
            "    f.write('Hello!')\n"
            "    f.close()\n"
            "    f = open('tmp.txt', 'r')\n"
            "    data: str = f.read()\n"
            "    f.close()\n"
            "    print(data)\n"
            "    return 0\n"
        )
        output = compile_and_run(code)
        self.assertEqual(output.strip(), "Hello!")


class TestRefLangOutput(unittest.TestCase):
    """Runtime test for the reference program."""

    def test_ref_lang_runtime_output(self):
        base = os.path.join(os.path.dirname(__file__), "..", "ref")
        with open(os.path.join(base, "lang.pb")) as f:
            lang_src = f.read()
        with open(os.path.join(base, "lang_expected_output.out")) as f:
            expected_lines = f.read().splitlines()

        output = _compile_and_run_modules({"lang": lang_src})

        def safe_eval(line):
            try:
                return ast.literal_eval(line)
            except Exception:
                return line

        actual_lines = [safe_eval(line) for line in output.splitlines()]
        expected_lines = [safe_eval(line) for line in expected_lines]

        self.assertEqual(actual_lines, expected_lines)


class TestImportUtilsHelper(unittest.TestCase):
    """Runtime test for the imports."""

    def test_import_utils_runtime_output(self):
        base = os.path.join(os.path.dirname(__file__), "samples")
        with open(os.path.join(base, "imports.pb")) as f:
            imports_src = f.read()
        with open(os.path.join(base, "mathlib.pb")) as f:
            mathlib_src = f.read()
        with open(os.path.join(base, "utils.pb")) as f:
            utils_src = f.read()
        expected_lines = [
            "9", "9", "3.1415",
            "Runinng helper from imported utils.pb file"
        ]
        output = _compile_and_run_modules({"imports": imports_src, "mathlib": mathlib_src, "utils": utils_src})
        self.assertEqual(output.splitlines(), expected_lines)

    def test_extended_imports_runtime_output(self):
        base = os.path.join(os.path.dirname(__file__), "samples")
        with open(os.path.join(base, "imports_extended.pb")) as f:
            imports_src = f.read()
        with open(os.path.join(base, "mathlib.pb")) as f:
            mathlib_src = f.read()
        with open(os.path.join(base, "utils.pb")) as f:
            utils_src = f.read()
        with open(os.path.join(base, "test_import", "mathlib2.pb")) as f:
            mathlib2_src = f.read()
        expected = [
            "9",
            "9",
            "import mathlib: 3.1415",
            "import mathlib as m1: 3.1415",
            "import test_import.mathlib2: 3.1415",
            "from test_import import mathlib2: 3.1415",
            "from test_import import mathlib2: 3.1415",
            "from test_import.mathlib2 import PI: 3.1415",
            "from test_import.mathlib2 import PI as pi: 3.1415",
            "Runinng helper from imported utils.pb file",
        ]
        modules = {
            "imports_extended": imports_src,
            "mathlib": mathlib_src,
            "utils": utils_src,
            "test_import.mathlib2": mathlib2_src,
        }
        output = _compile_and_run_modules(modules)
        self.assertEqual(output.splitlines(), expected)


if __name__ == "__main__":
    unittest.main()
