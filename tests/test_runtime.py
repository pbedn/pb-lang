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


if __name__ == "__main__":
    unittest.main()
