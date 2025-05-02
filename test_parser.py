import unittest
from lexer import Lexer
from parser import Parser
from codegen import CCodeGenerator
from lang_ast import *

class TestParser(unittest.TestCase):
    def test_function_with_params_and_return(self):
        code = 'def add(x: int, y: int) -> int:\n    return x + y'
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        self.assertIsInstance(ast.body[0], FunctionDef)
        self.assertEqual(ast.body[0].params, [("x", "int"), ("y", "int")])

    def test_if_else_structure(self):
        code = 'def main() -> int:\n    if 1 == 1:\n        print("yes")\n    else:\n        print("no")\n    return 0'
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        func = ast.body[0]
        self.assertIsInstance(func.body[0], IfStmt)
        self.assertIsInstance(func.body[-1], ReturnStmt)

    def test_while_and_assignment(self):
        code = 'def loop() -> int:\n    i = 0\n    while i < 10:\n        i = i + 1\n    return i'
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        body = ast.body[0].body
        self.assertIsInstance(body[0], AssignStmt)
        self.assertIsInstance(body[1], WhileStmt)

    def test_for_loop(self):
        code = 'def f() -> int:\n    for i in items:\n        print(i)\n    return 0'
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        self.assertIsInstance(ast.body[0].body[0], ForStmt)

if __name__ == "__main__":
    unittest.main()
