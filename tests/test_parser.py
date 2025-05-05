import unittest
from lexer import Lexer
from parser import Parser
from codegen import CCodeGenerator
from lang_ast import (
    FunctionDef, IfStmt, ReturnStmt, AssignStmt, WhileStmt, ForStmt, PassStmt, AugAssignStmt, Literal,
    GlobalStmt, VarDecl
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

    def test_global_stmt_parser(self):
        code = (
            "def main() -> int:\n"
            "    global x, y\n"
            "    x = 10\n"
            "    return x\n"
        )
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        func_body = ast.body[0].body
        self.assertTrue(any(isinstance(stmt, GlobalStmt) for stmt in func_body))

    def test_parser_with_top_level_and_function_global(self):
        code = (
            "counter = 100\n"
            "\n"
            "def main() -> int:\n"
            "    global counter, value\n"
            "    counter = 1\n"
            "    value = 2\n"
            "    return counter\n"
        )
        lexer = Lexer(code)
        tokens = lexer.tokenize()

        parser = Parser(tokens)
        ast = parser.parse()

        # Top-level: should have 2 statements: AssignStmt + FunctionDef
        self.assertEqual(len(ast.body), 2)

        # --- Top-level global var ---
        top_level_assign = ast.body[0]
        self.assertIsInstance(top_level_assign, AssignStmt)
        self.assertEqual(top_level_assign.target, "counter")
        self.assertIsInstance(top_level_assign.value, Literal)
        self.assertEqual(top_level_assign.value.value, 100)

        # --- Function def ---
        func_def = ast.body[1]
        self.assertIsInstance(func_def, FunctionDef)
        self.assertEqual(func_def.name, "main")

        # Check globals_declared
        self.assertIsNotNone(func_def.globals_declared)
        self.assertSetEqual(func_def.globals_declared, {"counter", "value"})

        # Check function body: [GlobalStmt, AssignStmt, AssignStmt, ReturnStmt]
        body = func_def.body
        self.assertEqual(len(body), 4)

        global_stmt = body[0]
        self.assertIsInstance(global_stmt, GlobalStmt)
        self.assertListEqual(global_stmt.names, ["counter", "value"])

        assign1 = body[1]
        self.assertIsInstance(assign1, AssignStmt)
        self.assertEqual(assign1.target, "counter")

        assign2 = body[2]
        self.assertIsInstance(assign2, AssignStmt)
        self.assertEqual(assign2.target, "value")

        return_stmt = body[3]
        self.assertIsInstance(return_stmt, ReturnStmt)

    def test_vardecl_parser(self):
        code = (
            "def main() -> int:\n"
            "    x: int = 5\n"
            "    return x\n"
        )
        tokens = Lexer(code).tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        func_body = ast.body[0].body
        vardecl = func_body[0]
        self.assertIsInstance(vardecl, VarDecl)
        self.assertEqual(vardecl.name, "x")
        self.assertEqual(vardecl.declared_type, "int")

if __name__ == "__main__":
    unittest.main()
