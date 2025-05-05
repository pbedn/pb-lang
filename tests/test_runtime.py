import unittest
import subprocess
import tempfile
import sys
from type_checker import LangTypeError
from lexer import Lexer
from parser import Parser
from codegen import CCodeGenerator
from type_checker import TypeChecker

class TestPipelineRuntime(unittest.TestCase):
    def compile_and_run(self, code: str) -> str:
        # Compile full pipeline
        tokens = Lexer(code).tokenize()
        ast = Parser(tokens).parse()
        TypeChecker().check(ast)
        c_code = CCodeGenerator().generate(ast)

        # Save C code
        with tempfile.NamedTemporaryFile(suffix=".c", delete=False) as c_file:
            c_file.write(c_code.encode("utf-8"))
            c_file_path = c_file.name

        # Compile using GCC
        exe_path = c_file_path[:-2]
        if sys.platform == "win32":
            exe_path += ".exe"

        compile_cmd = ["gcc", c_file_path, "-o", exe_path]
        result = subprocess.run(compile_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"GCC build failed:\n{result.stderr}")

        # Run & capture output
        run_result = subprocess.run([exe_path], capture_output=True, text=True)
        print(f"[INFO] Program exited with {run_result.returncode}")

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

if __name__ == "__main__":
    unittest.main()
