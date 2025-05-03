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


if __name__ == "__main__":
    unittest.main()
