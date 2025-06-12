import unittest
import subprocess
import tempfile
import sys
import os
from type_checker import TypeError
from lexer import Lexer
from parser import Parser
from codegen import CodeGen
from type_checker import TypeChecker

from tests import build_dir


class TestPipelineRuntime(unittest.TestCase):
    def compile_and_run(self, code: str) -> str:
        # Compile full pipeline
        tokens = Lexer(code).tokenize()
        ast = Parser(tokens).parse()
        checker = TypeChecker()
        checker.check(ast)
        c_code = CodeGen().generate(ast)
        # print("=== Generated C ===")
        # print(c_code)

        # Save C code
        with tempfile.NamedTemporaryFile(suffix=".c", delete=False) as c_file:
            c_file.write(c_code.encode("utf-8"))
            c_file_path = c_file.name

        # Compile using GCC
        exe_path = c_file_path[:-2]
        if sys.platform == "win32":
            exe_path += ".exe"

        # Runtime build once
        # need to make sure pb_runtime.a is up to date
        runtime_lib = os.path.join(build_dir, "pb_runtime.a")
        if not os.path.isfile(runtime_lib):
            print("Runtime library not found; building it now...")
            result = subprocess.run("python run.py buildlib")

        compile_cmd = [
            "gcc", "-std=c99", "-W", c_file_path,
            "-o", exe_path,
            "-I", build_dir,
            os.path.join(build_dir, "pb_runtime.a")
        ]

        result = subprocess.run(compile_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"GCC build failed:\n{result.stderr}")

        # Run & capture output
        run_result = subprocess.run([exe_path], capture_output=True, text=True)
        # print(f"[INFO] Program exited with {run_result.returncode}")

        return run_result.stdout.strip()

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
        output = self.compile_and_run(code)
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
        output = self.compile_and_run(code)
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
        output = self.compile_and_run(code)
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
        output = self.compile_and_run(code)
        lines = output.strip().splitlines()
        self.assertEqual(lines[0], "1.500000")
        self.assertEqual(lines[1], "3.500000")

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
        output = self.compile_and_run(code)
        lines = output.strip().splitlines()

        # Assertions for arr_int
        self.assertEqual(lines[0], "100")              # arr_int[0] before assignment
        self.assertEqual(lines[1], "1")                # arr_int[0] after assignment
        self.assertEqual(lines[2], "1")                # arr_int[0] after assignment
        self.assertEqual(lines[3], "[1]")              # arr_int list contents

        # Assertions for arr_str
        self.assertEqual(lines[4], "a")                # arr_str[0] before assignment
        self.assertEqual(lines[5], "C")                # arr_str[0] after assignment
        self.assertEqual(lines[6], '["C", "C"]')           # arr_str list contents

        # Assertions for arr_bool
        self.assertEqual(lines[7], "[false]")          # arr_bool after assignment

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
        output = self.compile_and_run(code)
        lines = output.strip().splitlines()

        # Assertions for type conversions
        self.assertEqual(lines[0], "x: 10, x_float: 10.000000")  # x to float
        self.assertEqual(lines[1], "b: 1.0, b_float: 1.000000")  # b to float
        self.assertEqual(lines[2], "y: 1.000000, y_int: 1")        # y to int
        self.assertEqual(lines[3], "a: 1, a_int: 1")        # a to int
        self.assertEqual(lines[4], "x: 10, x_bool: True")     # x to bool
        self.assertEqual(lines[5], "y: 1.000000, y_bool: True")    # y to bool
        self.assertEqual(lines[6], "z: 0.000000, z_bool: False")    # z to bool


if __name__ == "__main__":
    unittest.main()
