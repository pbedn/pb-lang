import os
import unittest
from lexer import Lexer
from parser import Parser
from codegen import CCodeGenerator
from type_checker import TypeChecker, LangTypeError
from lang_ast import Program

BASE_DIR = os.path.dirname(__file__)

class TestPipeline(unittest.TestCase):
    def compile_pipeline(self, code: str) -> str:
        lexer = Lexer(code)
        tokens = lexer.tokenize()

        parser = Parser(tokens)
        ast = parser.parse()

        checker = TypeChecker()
        checker.check(ast)

        global_vars = set(checker.global_env.keys())
        codegen = CCodeGenerator(global_vars=global_vars)
        return codegen.generate(ast)

    def test_lang_pb_codegen_matches_expected(self):
        self.maxDiff = None
        pb_path = os.path.join(BASE_DIR, "../ref/lang.pb")
        expected_c_path = os.path.join(BASE_DIR, "../ref/ref_lang.c")
        with open(pb_path) as f:
            source = f.read()

        with open(expected_c_path) as f:
            expected_c = f.read()

        generated_c = self.compile_pipeline(source)

        # Optional: normalize line endings to be OS-independent
        expected_c_normalized = expected_c.replace("\r\n", "\n").strip()
        generated_c_normalized = generated_c.replace("\r\n", "\n").strip()

        # Assert full match
        self.assertEqual(
            generated_c_normalized, expected_c_normalized,
            msg="Generated C code does not match the expected output."
        )


    def test_hello_world(self):
        code = (
            "def main() -> int:\n"
            "    print(\"Hello, world!\")\n"
            "    return 0\n"
        )
        c_code = self.compile_pipeline(code)
        self.assertIn('printf("%s\\n", "Hello, world!");', c_code)
        self.assertIn('return 0;', c_code)

    def test_addition_function(self):
        code = (
            "def add(x: int, y: int) -> int:\n"
            "    return x + y\n"
            "\n"
            "def main() -> int:\n"
            "    result = add(3, 4)\n"
            "    print(\"Result:\")\n"
            "    print(result)\n"
            "    return result\n"
        )
        c_code = self.compile_pipeline(code)
        self.assertIn("int add(int x, int y)", c_code)
        self.assertIn("int result = add(3, 4);", c_code)
        self.assertIn('printf("%d\\n", result);', c_code)

    def test_conditionals(self):
        code = (
            "def main() -> int:\n"
            "    if 3 == 3:\n"
            "        print(\"Equal\")\n"
            "    else:\n"
            "        print(\"Not equal\")\n"
            "    return 0\n"
        )

        c_code = self.compile_pipeline(code)
        self.assertIn('if ((3 == 3)) {', c_code)
        self.assertIn('printf("%s\\n", "Equal");', c_code)
        self.assertIn('else {', c_code)

    def test_builtin_constants(self):
        code = (
            "def main() -> int:\n"
            "    x = True\n"
            "    y = False\n"
            "    if x:\n"
            "        print(\"yes\")\n"
            "    if not y:\n"
            "        print(\"still yes\")\n"
            "    return 0\n"
        )
        c_code = self.compile_pipeline(code)
        self.assertIn('bool x = true;', c_code)
        self.assertIn('bool y = false;', c_code)
        self.assertIn('if (x) {', c_code)
        self.assertIn('if ((!y)) {', c_code)

    def test_list_indexing(self):
        code = (
            "def main() -> int:\n"
            "    numbers = [10, 20, 30]\n"
            "    x = numbers[1]\n"
            "    print(x)\n"
            "    return 0\n"
        )
        c_code = self.compile_pipeline(code)
        self.assertIn('int numbers[] = { 10, 20, 30 };', c_code)
        self.assertIn('int x = numbers[1];', c_code)
        self.assertIn('printf("%d\\n", x);', c_code)

    def test_void_function(self):
        code = (
            "def debug():\n"
            "    print(\"Debugging...\")\n"
        )
        c_code = self.compile_pipeline(code)
        self.assertIn('void debug()', c_code)
        self.assertIn('printf("%s\\n", "Debugging...");', c_code)

    def test_list_of_bools(self):
        code = (
            "def main() -> int:\n"
            "    flags = [True, False, True]\n"
            "    x = flags[0]\n"
            "    print(x)\n"
            "    return 0\n"
        )
        c_code = self.compile_pipeline(code)
        self.assertIn('bool flags[] = { true, false, true };', c_code)
        self.assertIn('bool x = flags[0];', c_code)
        self.assertIn('printf("%s\\n", x ? "true" : "false");', c_code)

    def test_list_mixed_types_error(self):
        code = (
            "def main() -> int:\n"
            "    stuff = [1, True, \"oops\"]\n"
            "    return 0\n"
        )
        with self.assertRaises(Exception) as ctx:
            self.compile_pipeline(code)
        self.assertIn("All elements of a list must have the same type", str(ctx.exception))

    def test_pass_statement(self):
        code = (
            "def main() -> int:\n"
            "    if True:\n"
            "        pass\n"
            "    print(\"Done\")\n"
            "    return 0\n"
        )
        c_code = self.compile_pipeline(code)
        self.assertIn('// pass', c_code)
        self.assertIn('printf("%s\\n", "Done");', c_code)

    def test_is_and_is_not(self):
        code = (
            "def main() -> int:\n"
            "    a = 10\n"
            "    b = 10\n"
            "    if a is b:\n"
            "        print(\"Equal\")\n"
            "    if a is not 20:\n"
            "        print(\"Not 20\")\n"
            "    return 0\n"
        )
        c_code = self.compile_pipeline(code)
        # Check that 'is' became '=='
        self.assertIn('if ((a == b)) {', c_code)
        # Check that 'is not' became '!='
        self.assertIn('if ((a != 20)) {', c_code)
        # Check the print statements exist
        self.assertIn('printf("%s\\n", "Equal");', c_code)
        self.assertIn('printf("%s\\n", "Not 20");', c_code)

    def test_augmented_assignment_pipeline(self):
        code = (
            "def main() -> int:\n"
            "    x = 10\n"
            "    x += 5\n"
            "    print(x)\n"
            "    return 0\n"
        )
        c_code = self.compile_pipeline(code)
        self.assertIn('int x = 10;', c_code)
        self.assertIn('x += 5;', c_code)
        self.assertIn('printf("%d\\n", x);', c_code)

    def test_global_read_without_global(self):
        code = (
            "x: int = 100\n"
            "\n"
            "def main() -> int:\n"
            "    print(x)\n"
            "    return x\n"
        )
        c_code = self.compile_pipeline(code)
        self.assertIn('int x = 100;', c_code)
        self.assertIn('printf("%d\\n", x);', c_code)

    def test_global_write_with_global(self):
        code = (
            "x:int = 10\n"
            "\n"
            "def main() -> int:\n"
            "    global x\n"
            "    x = 20\n"
            "    print(x)\n"
            "    return x\n"
        )
        c_code = self.compile_pipeline(code)
        self.assertIn('int x = 10;', c_code)
        self.assertIn('x = 20;', c_code)

    def test_global_write_without_global_is_local(self):
        code = (
            "x: int = 10\n"
            "\n"
            "def main() -> int:\n"
            "    x = 5\n"
            "    print(x)\n"
            "    return x\n"
        )
        c_code = self.compile_pipeline(code)
        self.assertIn('int x = 10;', c_code)  # global var
        self.assertIn('int x = 5;', c_code)   # local shadowing var

    def test_global_stmt_without_existing_global_should_fail(self):
        code = (
            "def main() -> int:\n"
            "    global y\n"
            "    y = 5\n"
            "    return y\n"
        )
        with self.assertRaises(LangTypeError) as ctx:
            self.compile_pipeline(code)
        self.assertIn("Global variable 'y' not defined", str(ctx.exception))

    def test_vardecl_pipeline(self):
        code = (
            "def main() -> int:\n"
            "    x: int = 10\n"
            "    print(x)\n"
            "    return 0\n"
        )
        c_code = self.compile_pipeline(code)
        self.assertIn('int x = 10;', c_code)
        self.assertIn('printf("%d\\n", x);', c_code)


if __name__ == "__main__":
    unittest.main()
