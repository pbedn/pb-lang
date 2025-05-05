import unittest
from lexer import Lexer
from parser import Parser
from codegen import CCodeGenerator
from lang_ast import *

class TestLexer(unittest.TestCase):
    def test_keywords_and_literals(self):
        code = 'def main() -> int:\n    return 42\n    print("hello")\n    if x == 1:\n        pass\n    else:\n        pass'
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        types = [t.type.name for t in tokens]
        for expected in ["DEF", "RETURN", "INT_LIT", "STRING_LIT", "IF", "ELSE", "EQEQ"]:
            self.assertIn(expected, types)

    def test_operators(self):
        code = 'a + b - c * d / e % f and g or not h'
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        ops = [t.value for t in tokens if t.type.name in ["PLUS", "MINUS", "STAR", "SLASH", "PERCENT", "AND", "OR", "NOT"]]
        for op in ['+', '-', '*', '/', '%', 'and', 'or', 'not']:
            self.assertIn(op, ops)

    def test_augmented_assignment_tokens(self):
        code = (
            "x += 1\n"
            "y -= 2\n"
            "z *= 3\n"
            "w /= 4\n"
            "v %= 5\n"
        )
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        types = [t.type.name for t in tokens]
        self.assertIn("PLUSEQ", types)
        self.assertIn("MINUSEQ", types)
        self.assertIn("STAREQ", types)
        self.assertIn("SLASHEQ", types)
        self.assertIn("PERCENTEQ", types)

    def test_global_keyword(self):
        code = 'global x, y'
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        types = [t.type.name for t in tokens]
        self.assertIn("GLOBAL", types)
