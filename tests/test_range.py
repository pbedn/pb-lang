import unittest
from lexer import Lexer
from parser import Parser
from codegen import CCodeGenerator
from type_checker import TypeChecker

class TestRangeBuiltin(unittest.TestCase):
    def compile(self, code: str) -> str:
        tokens = Lexer(code).tokenize()
        ast = Parser(tokens).parse()
        TypeChecker().check(ast)
        return CCodeGenerator().generate(ast)

    def test_range_two_args(self):
        code = '''
def main() -> int:
    for i in range(0, 3):
        print(i)
    return 0
'''
        c_code = self.compile(code)
        self.assertIn("for (int i = 0; i < 3; i++) {", c_code)
        self.assertIn('printf("%d\\n", i);', c_code)

    def test_range_one_arg(self):
        code = '''
def main() -> int:
    for x in range(2):
        print(x)
    return 0
'''
        c_code = self.compile(code)
        self.assertIn("for (int x = 0; x < 2; x++) {", c_code)
        self.assertIn('printf("%d\\n", x);', c_code)

    def test_range_type_error(self):
        code = '''
def main() -> int:
    for x in range("bad"):
        print(x)
    return 0
'''
        with self.assertRaises(Exception) as ctx:
            self.compile(code)
        self.assertIn("range() arguments must be integers", str(ctx.exception))

    def test_range_argument_count_error(self):
        code = '''
def main() -> int:
    for x in range(1, 2, 3):
        print(x)
    return 0
'''
        with self.assertRaises(Exception) as ctx:
            self.compile(code)
        self.assertIn("range() takes 1 or 2 arguments", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
