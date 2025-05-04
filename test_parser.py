import unittest
from lexer import Lexer
from parser import Parser
from codegen import CCodeGenerator
from lang_ast import (
    FunctionDef, IfStmt, ReturnStmt, AssignStmt, WhileStmt, ForStmt, PassStmt, AugAssignStmt, Literal
)

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

    def test_if_elif_else(self):
        code = (
            "def main() -> int:\n"
            "    if x == 1:\n"
            "        print(\"one\")\n"
            "    elif x == 2:\n"
            "        print(\"two\")\n"
            "    else:\n"
            "        print(\"other\")\n"
            "    return 0\n"
        )
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()

        if_stmt = ast.body[0].body[0]
        self.assertIsInstance(if_stmt, IfStmt)
        # Check elif is desugared into nested if inside else_body
        nested_if = if_stmt.else_body[0]
        self.assertIsInstance(nested_if, IfStmt)
        self.assertEqual(len(nested_if.then_body), 1)

    def test_parser_pass_statement(self):
        code = (
            "def main() -> int:\n"
            "    if True:\n"
            "        pass\n"
        )
        tokens = Lexer(code).tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        # Look for PassStmt in AST
        self.assertTrue(any(isinstance(stmt, PassStmt) for func in ast.body for stmt in func.body[0].then_body))

    def test_augmented_assignment_stmt(self):
        code = (
            "def main() -> int:\n"
            "    x = 10\n"
            "    x += 5\n"
            "    return x\n"
        )
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        func = ast.body[0]
        aug_stmt = func.body[1]
        self.assertIsInstance(aug_stmt, AugAssignStmt)
        self.assertEqual(aug_stmt.target, "x")
        self.assertEqual(aug_stmt.op, "+")
        self.assertIsInstance(aug_stmt.value, Literal)



if __name__ == "__main__":
    unittest.main()
