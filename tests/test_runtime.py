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
from pb_pipeline import compile_code_to_c_and_h

from tests import build_dir


class TestPipelineRuntime(unittest.TestCase):
    def compile_and_run(self, code: str) -> str:
        h_code, c_code, *_ = compile_code_to_c_and_h(code, module_name="main")

        with tempfile.TemporaryDirectory() as tmpdir:
            h_file_path = os.path.join(tmpdir, "main.h")
            c_file_path = os.path.join(tmpdir, "main.c")
            exe_path = os.path.join(tmpdir, "main")
            if sys.platform == "win32":
                exe_path += ".exe"

            # Write header and C files
            with open(h_file_path, "w", encoding="utf-8") as h_file:
                h_file.write(h_code)
            with open(c_file_path, "w", encoding="utf-8") as c_file:
                c_file.write(c_code)

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
                runtime_lib
            ]

            result = subprocess.run(compile_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(f"GCC build failed:\n{result.stderr}")

            # Run & capture output
            run_result = subprocess.run([exe_path], capture_output=True, text=True)
            output = run_result.stdout + run_result.stderr

            return output.strip()

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
        output = self.compile_and_run(code)
        lines = output.strip().splitlines()

        # Assertions for correctness of f-string interpolation
        self.assertEqual(lines[0], "Simple fstring: x=5")
        self.assertEqual(lines[1], "x + 1: 6")
        self.assertEqual(lines[2], "Float conversion: 2.000000")
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
            "    pass\n"
            "\n"
            "def crash():\n"
            "    raise RuntimeError(\"division by zero\")\n"
            "\n"
            "def main():\n"
            "    crash()\n"
        )
        output = self.compile_and_run(code)
        self.assertIn("Exception raised", output)

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
        output = self.compile_and_run(code)
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
        output = self.compile_and_run(code)
        lines = output.strip().splitlines()
        self.assertEqual(lines[0], "150")
        self.assertEqual(lines[1], "150")
        self.assertEqual(lines[2], "P")
        self.assertEqual(lines[3], "150")
        self.assertEqual(lines[4], "200")
        self.assertEqual(lines[5], "150")


if __name__ == "__main__":
    unittest.main()
