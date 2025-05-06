import unittest
from lexer import Lexer
from parser import Parser, ParserError
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
        self.assertIsInstance(aug_stmt.target, Identifier)
        self.assertEqual(aug_stmt.target.name, "x")
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
            "counter: int = 100\n"
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
        top_level_vardecl = ast.body[0]
        self.assertIsInstance(top_level_vardecl, VarDecl)
        self.assertEqual(top_level_vardecl.name, "counter")
        self.assertEqual(top_level_vardecl.declared_type, "int")
        self.assertEqual(top_level_vardecl.value, Literal(100))

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
        self.assertIsInstance(assign1.target, Identifier)
        self.assertEqual(assign1.target.name, "counter")

        assign2 = body[2]
        self.assertIsInstance(assign2.target, Identifier)
        self.assertEqual(assign2.target.name, "value")

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

    def test_parser_should_fail_on_uninitialized_global_var(self):
        code = (
            "counter: int\n"  # ❌ invalid: no initializer
            "\n"
            "def main() -> int:\n"
            "    return 0\n"
        )
        lexer = Lexer(code)
        tokens = lexer.tokenize()

        parser = Parser(tokens)
        with self.assertRaises(ParserError) as ctx:
            parser.parse()
        self.assertIn("Global variable declaration must include an initializer", str(ctx.exception))

    def test_attribute_expr_parsing(self):
        code = (
            "def main() -> int:\n"
            "    x = player.hp\n"
            "    y = game.world.level\n"
            "    return 0\n"
        )
        tokens = Lexer(code).tokenize()
        parser = Parser(tokens)
        ast = parser.parse()

        func = ast.body[0]
        assign1 = func.body[0]
        assign2 = func.body[1]

        # First: x = player.hp
        self.assertIsInstance(assign1.value, AttributeExpr)
        self.assertEqual(assign1.value.attr, "hp")
        self.assertIsInstance(assign1.value.obj, Identifier)
        self.assertEqual(assign1.value.obj.name, "player")

        # Second: y = game.world.level
        attr_expr = assign2.value
        self.assertIsInstance(attr_expr, AttributeExpr)
        self.assertEqual(attr_expr.attr, "level")

        # game.world
        inner_attr = attr_expr.obj
        self.assertIsInstance(inner_attr, AttributeExpr)
        self.assertEqual(inner_attr.attr, "world")
        self.assertIsInstance(inner_attr.obj, Identifier)
        self.assertEqual(inner_attr.obj.name, "game")

    def test_classdef_parsing(self):
        code = (
            "class Player:\n"
            "    hp: int = 100\n"
            "\n"
            "    def heal(self, amount: int):\n"
            "        self.hp += amount\n"
        )
        tokens = Lexer(code).tokenize()
        parser = Parser(tokens)
        ast = parser.parse()

        class_def = ast.body[0]
        self.assertIsInstance(class_def, ClassDef)
        self.assertEqual(class_def.name, "Player")
        self.assertIsNone(class_def.base)

        # Check field
        self.assertEqual(len(class_def.fields), 1)
        field = class_def.fields[0]
        self.assertIsInstance(field, VarDecl)
        self.assertEqual(field.name, "hp")
        self.assertEqual(field.declared_type, "int")

        # Check method
        self.assertEqual(len(class_def.methods), 1)
        method = class_def.methods[0]
        self.assertIsInstance(method, FunctionDef)
        self.assertEqual(method.name, "heal")

    def test_assert_stmt_parsing(self):
        code = (
            "def main() -> int:\n"
            "    assert x > 0\n"
            "    return 0\n"
        )
        tokens = Lexer(code).tokenize()
        parser = Parser(tokens)
        ast = parser.parse()

        func = ast.body[0]
        assert_stmt = func.body[0]
        self.assertIsInstance(assert_stmt, AssertStmt)
        self.assertIsInstance(assert_stmt.condition, BinOp)
        self.assertEqual(assert_stmt.condition.op, ">")


class TestClassDefParsing(unittest.TestCase):

    def test_class_pass_only(self):
        code = (
            "class A:\n"
            "    pass\n"
        )
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        tree = parser.parse()
        self.assertEqual(len(tree.body), 1)
        cls = tree.body[0]
        self.assertEqual(cls.name, "A")
        self.assertTrue(any(isinstance(stmt, PassStmt) for stmt in cls.methods))

    def test_class_pass_then_method_should_fail(self):
        code = (
            "class A:\n"
            "    pass\n"
            "    def foo():\n"
            "        pass\n"
        )
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        with self.assertRaises(ParserError):
            parser.parse()

    def test_class_pass_then_field_should_fail(self):
        code = (
            "class A:\n"
            "    pass\n"
            "    x: int = 5\n"
        )
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        with self.assertRaises(ParserError):
            parser.parse()

    def test_class_fields_then_methods_ok(self):
        code = (
            "class A:\n"
            "    x: int = 5\n"
            "    def foo() -> int:\n"
            "        return self.x\n"
        )
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        tree = parser.parse()
        cls = tree.body[0]
        self.assertEqual(len(cls.fields), 1)
        self.assertEqual(len(cls.methods), 1)

    def test_class_field_after_method_should_fail(self):
        code = (
            "class A:\n"
            "    def foo():\n"
            "        pass\n"
            "    x: int = 5\n"
        )
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        with self.assertRaises(ParserError):
            parser.parse()

    def test_class_expression_should_fail(self):
        code = (
            "class A:\n"
            "    print(123)\n"
        )
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        with self.assertRaises(ParserError):
            parser.parse()

    def test_multiple_statements_on_one_line_should_fail(self):
        code = (
            "def main() -> int:\n"
            "    print(1); print(2)\n"
        )
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        with self.assertRaises(ParserError):
            parser.parse()

    def test_assignment_inside_expression_should_fail(self):
        code = (
            "def main() -> int:\n"
            "    y = (x = 5)\n"
        )
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        with self.assertRaises(ParserError):
            parser.parse()

    def test_list_assignment_target_should_fail(self):
        code = (
            "def main() -> int:\n"
            "    [a, b] = [1, 2]\n"
        )
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        with self.assertRaises(ParserError):
            parser.parse()

    def test_nested_function_definition_should_fail(self):
        code = (
            "def outer() -> int:\n"
            "    def inner() -> int:\n"
            "        return 0\n"
            "    return 1\n"
        )
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        with self.assertRaises(ParserError):
            parser.parse()

    def test_top_level_expression_should_fail(self):
        code = (
            "print(123)\n"
        )
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        with self.assertRaises(ParserError):
            parser.parse()

    def test_function_with_only_pass(self):
        code = (
            "def noop() -> int:\n"
            "    pass\n"
        )
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        func = ast.body[0]
        self.assertIsInstance(func, FunctionDef)
        self.assertEqual(func.name, "noop")
        self.assertEqual(len(func.body), 1)
        self.assertIsInstance(func.body[0], PassStmt)

    def test_class_with_two_fields_and_two_methods(self):
        code = (
            "class A:\n"
            "    x: int = 1\n"
            "    y: int = 2\n"
            "\n"
            "    def foo() -> int:\n"
            "        return self.x\n"
            "\n"
            "    def bar() -> int:\n"
            "        return self.y\n"
        )
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        tree = parser.parse()
        cls = tree.body[0]
        self.assertIsInstance(cls, ClassDef)
        self.assertEqual(len(cls.fields), 2)
        self.assertEqual(len(cls.methods), 2)
        field_names = [field.name for field in cls.fields]
        self.assertIn("x", field_names)
        self.assertIn("y", field_names)
        method_names = [method.name for method in cls.methods]
        self.assertIn("foo", method_names)
        self.assertIn("bar", method_names)

    def test_assignment_to_nested_attribute(self):
        code = (
            "def main() -> int:\n"
            "    player.stats.hp = 100\n"
            "    return 0\n"
        )
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        assign_stmt = ast.body[0].body[0]
        self.assertIsInstance(assign_stmt, AssignStmt)
        target = assign_stmt.target
        self.assertIsInstance(target, AttributeExpr)
        # Check it's player.stats.hp
        self.assertEqual(target.attr, "hp")
        level2 = target.obj
        self.assertIsInstance(level2, AttributeExpr)
        self.assertEqual(level2.attr, "stats")
        self.assertIsInstance(level2.obj, Identifier)
        self.assertEqual(level2.obj.name, "player")

    def test_class_pass_then_expression_should_fail(self):
        code = (
            "class A:\n"
            "    pass\n"
            "    print(123)\n"
        )
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        with self.assertRaises(ParserError):
            parser.parse()

    def test_complex_assignment_target_attribute_index_chain(self):
        code = (
            "def main() -> int:\n"
            "    game.world[0].player.hp = 100\n"
            "    return 0\n"
        )
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        assign_stmt = ast.body[0].body[0]
        self.assertIsInstance(assign_stmt, AssignStmt)
        target = assign_stmt.target
        self.assertIsInstance(target, AttributeExpr)
        self.assertEqual(target.attr, "hp")
        mid = target.obj
        self.assertIsInstance(mid, AttributeExpr)
        self.assertEqual(mid.attr, "player")
        mid_index = mid.obj
        self.assertIsInstance(mid_index, IndexExpr)
        self.assertIsInstance(mid_index.index, Literal)
        self.assertEqual(mid_index.index.value, 0)
        self.assertIsInstance(mid_index.base, AttributeExpr)
        self.assertEqual(mid_index.base.attr, "world")
        self.assertIsInstance(mid_index.base.obj, Identifier)
        self.assertEqual(mid_index.base.obj.name, "game")

    def test_empty_function_body_should_fail(self):
        code = (
            "def foo() -> int:\n"
        )
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        with self.assertRaises(ParserError):
            parser.parse()

    def test_empty_class_body_should_fail(self):
        code = (
            "class A:\n"
        )
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        with self.assertRaises(ParserError):
            parser.parse()

    def test_assign_to_literal_should_fail(self):
        code = (
            "def f() -> int:\n"
            "    123 = 5\n"
        )
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        with self.assertRaises(ParserError):
            parser.parse()

    def test_top_level_expression_should_fail(self):
        code = (
            "print(123)\n"
        )
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        with self.assertRaises(ParserError):
            parser.parse()

    def test_function_no_parameters(self):
        code = (
            "def foo() -> int:\n"
            "    return 0\n"
        )
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        func = ast.body[0]
        self.assertIsInstance(func, FunctionDef)
        self.assertEqual(func.name, "foo")
        self.assertEqual(func.params, [])

    def test_attribute_and_index_chain_in_expr(self):
        code = (
            "def main() -> int:\n"
            "    x = obj[0].field[1]\n"
            "    return 0\n"
        )
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        assign = ast.body[0].body[0]
        self.assertIsInstance(assign, AssignStmt)
        value = assign.value
        self.assertIsInstance(value, IndexExpr)
        self.assertIsInstance(value.base, AttributeExpr)
        self.assertEqual(value.base.attr, "field")
        self.assertIsInstance(value.base.obj, IndexExpr)
        self.assertIsInstance(value.base.obj.base, Identifier)
        self.assertEqual(value.base.obj.base.name, "obj")

    def test_class_field_without_initializer_should_fail(self):
        code = (
            "class A:\n"
            "    x: int\n"
        )
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        with self.assertRaises(ParserError):
            parser.parse()


if __name__ == "__main__":
    unittest.main()
