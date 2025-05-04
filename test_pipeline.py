import unittest
from lexer import Lexer
from parser import Parser
from codegen import CCodeGenerator
from type_checker import TypeChecker
from lang_ast import Program

class TestPipeline(unittest.TestCase):
    def compile_pipeline(self, code: str) -> str:
        lexer = Lexer(code)
        tokens = lexer.tokenize()

        parser = Parser(tokens)
        ast = parser.parse()

        checker = TypeChecker()
        checker.check(ast)

        codegen = CCodeGenerator()
        return codegen.generate(ast)

    def test_lang_pb_codegen_matches_expected(self):
        with open("lang.pb") as f:
            source = f.read()

        with open("expected_lang.c") as f:
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
        source = '''
def main() -> int:
    print("Hello, world!")
    return 0
'''
        c_code = self.compile_pipeline(source)
        self.assertIn('printf("%s\\n", "Hello, world!");', c_code)
        self.assertIn('return 0;', c_code)

    def test_addition_function(self):
        source = '''
def add(x: int, y: int) -> int:
    return x + y

def main() -> int:
    result = add(3, 4)
    print("Result:")
    print(result)
    return result
'''
        c_code = self.compile_pipeline(source)
        self.assertIn("int add(int x, int y)", c_code)
        self.assertIn("int result = add(3, 4);", c_code)
        self.assertIn('printf("%d\\n", result);', c_code)

    def test_conditionals(self):
        source = (
            "def main() -> int:\n"
            "    if 3 == 3:\n"
            "        print(\"Equal\")\n"
            "    else:\n"
            "        print(\"Not equal\")\n"
            "    return 0\n"
        )

        c_code = self.compile_pipeline(source)
        self.assertIn('if ((3 == 3)) {', c_code)
        self.assertIn('printf("%s\\n", "Equal");', c_code)
        self.assertIn('else {', c_code)

    def test_builtin_constants(self):
        source = (
            "def main() -> int:\n"
            "    x = True\n"
            "    y = False\n"
            "    if x:\n"
            "        print(\"yes\")\n"
            "    if not y:\n"
            "        print(\"still yes\")\n"
            "    return 0\n"
        )
        c_code = self.compile_pipeline(source)
        self.assertIn('bool x = true;', c_code)
        self.assertIn('bool y = false;', c_code)
        self.assertIn('if (x) {', c_code)
        self.assertIn('if ((!y)) {', c_code)

    def test_list_indexing(self):
        source = (
            "def main() -> int:\n"
            "    numbers = [10, 20, 30]\n"
            "    x = numbers[1]\n"
            "    print(x)\n"
            "    return 0\n"
        )
        c_code = self.compile_pipeline(source)
        self.assertIn('int numbers[] = { 10, 20, 30 };', c_code)
        self.assertIn('int x = numbers[1];', c_code)
        self.assertIn('printf("%d\\n", x);', c_code)

    def test_void_function(self):
        source = (
            "def debug():\n"
            "    print(\"Debugging...\")\n"
        )
        c_code = self.compile_pipeline(source)
        self.assertIn('void debug()', c_code)
        self.assertIn('printf("%s\\n", "Debugging...");', c_code)

    def test_list_of_bools(self):
        code = source = (
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


if __name__ == "__main__":
    unittest.main()
