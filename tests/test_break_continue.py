import unittest
from lexer import Lexer
from parser import Parser
from codegen import CCodeGenerator
from type_checker import TypeChecker

class TestBreakContinue(unittest.TestCase):
    def compile(self, code: str) -> str:
        tokens = Lexer(code).tokenize()
        ast = Parser(tokens).parse()
        TypeChecker().check(ast)
        return CCodeGenerator().generate(ast)

    def test_break_in_loop(self):
        code = '''
def main() -> int:
    i = 0
    while i < 10:
        if i == 5:
            break
        i = i + 1
    return i
'''
        c = self.compile(code)
        self.assertIn("break;", c)

    def test_continue_in_loop(self):
        code = '''
def main() -> int:
    for i in range(0, 5):
        if i == 2:
            continue
        print(i)
    return 0
'''
        c = self.compile(code)
        self.assertIn("continue;", c)

    def test_break_outside_loop_should_fail(self):
        code = '''
def main() -> int:
    break
    return 0
'''
        with self.assertRaises(Exception) as ctx:
            self.compile(code)
        self.assertIn("used outside of loop", str(ctx.exception))

if __name__ == "__main__":
    unittest.main()
