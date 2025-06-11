import unittest

from lexer import Lexer, TokenType
from parser import Parser, ParserError

from lang_ast import (
    Program,

    Stmt,
    FunctionDef,
    ClassDef,
    GlobalStmt,
    VarDecl,
    AssignStmt,
    AugAssignStmt,
    IfBranch,
    IfStmt,
    WhileStmt,
    ForStmt,
    TryExceptStmt,
    ExceptBlock,
    RaiseStmt,
    ReturnStmt,
    AssertStmt,
    BreakStmt,
    ContinueStmt,
    PassStmt,
    ExprStmt,
    ImportStmt,

    Expr,
    Identifier,
    Literal,
    StringLiteral,
    FStringLiteral,
    BinOp,
    UnaryOp,
    CallExpr,
    AttributeExpr,
    IndexExpr,
    ListExpr,
    DictExpr,
)

class ParserTestCase(unittest.TestCase):
    def parse_tokens(self, code: str):
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        return Parser(tokens)

class TestParserHelpers(ParserTestCase):

    def test_current_and_peek(self):
        parser = self.parse_tokens("x + 1")
        self.assertEqual(parser.current().type, TokenType.IDENTIFIER)
        self.assertEqual(parser.peek().type, TokenType.PLUS)
        self.assertEqual(parser.peek(2).type, TokenType.INT_LIT)

    def test_advance(self):
        parser = self.parse_tokens("x + 1")
        parser.advance()
        self.assertEqual(parser.current().type, TokenType.PLUS)
        parser.advance()
        self.assertEqual(parser.current().type, TokenType.INT_LIT)

    def test_check(self):
        parser = self.parse_tokens("x")
        self.assertTrue(parser.check(TokenType.IDENTIFIER))
        parser.advance()
        self.assertFalse(parser.check(TokenType.IDENTIFIER))

    def test_match(self):
        parser = self.parse_tokens("x + 1")
        self.assertTrue(parser.match(TokenType.IDENTIFIER))
        self.assertTrue(parser.match(TokenType.PLUS))
        self.assertFalse(parser.match(TokenType.PLUS))

    def test_expect_success(self):
        parser = self.parse_tokens("x")
        tok = parser.expect(TokenType.IDENTIFIER)
        self.assertEqual(tok.value, "x")

    def test_expect_failure(self):
        parser = self.parse_tokens("x")
        parser.expect(TokenType.IDENTIFIER)
        with self.assertRaises(ParserError):
            parser.expect(TokenType.IDENTIFIER)

    def test_at_end(self):
        parser = self.parse_tokens("x")
        self.assertFalse(parser.at_end())
        parser.advance()  # x
        parser.advance()  # NEWLINE
        parser.advance()  # EOF
        self.assertTrue(parser.at_end())

class TestParseExpressions(ParserTestCase):

    def test_parse_identifier(self):
        parser = self.parse_tokens("foo")
        ident = parser.parse_identifier()

        # Expected: Identifier("foo")
        self.assertIsInstance(ident, Identifier)
        self.assertEqual(ident.name, "foo")

    def test_parse_literal_int(self):
        parser = self.parse_tokens("42")
        lit = parser.parse_literal()

        # Expected: Literal("42")
        self.assertIsInstance(lit, Literal)
        self.assertEqual(lit.raw, "42")

    def test_parse_literal_float(self):
        parser = self.parse_tokens("3.14")
        lit = parser.parse_literal()

        # Expected: Literal("3.14")
        self.assertIsInstance(lit, Literal)
        self.assertEqual(lit.raw, "3.14")

    def test_parse_literal_string(self):
        parser = self.parse_tokens("'hello'")
        lit = parser.parse_literal()

        # Expected: StringLiteral("hello")
        self.assertIsInstance(lit, StringLiteral)
        self.assertEqual(lit.value, "hello")

    def test_parse_literal_fstring(self):
        parser = self.parse_tokens("f'hello {x}'")
        lit = parser.parse_literal()

        # Expected: FStringLiteral(raw='hello {x}', vars=['x'])
        self.assertIsInstance(lit, FStringLiteral)
        self.assertEqual(lit.raw, "hello {x}")
        self.assertEqual(lit.vars, ["x"])

    def test_parse_literal_constants(self):
        parser = self.parse_tokens("None\nTrue\nFalse")
        lit = parser.parse_literal()
        parser.advance()
        lit2 = parser.parse_literal()
        parser.advance()
        lit3 = parser.parse_literal()

        # Expected: Literal("None")
        self.assertIsInstance(lit, Literal)
        self.assertEqual(lit.raw, "None")
        # Expected: Literal("True")
        self.assertIsInstance(lit2, Literal)
        self.assertEqual(lit2.raw, "True")
        # Expected: Literal("False")
        self.assertIsInstance(lit3, Literal)
        self.assertEqual(lit3.raw, "False")

    def test_parse_unary_minus(self):
        parser = self.parse_tokens("-42")
        expr = parser.parse_unary()

        # Expected: UnaryOp("-", Literal("42"))
        self.assertIsInstance(expr, UnaryOp)
        self.assertEqual(expr.op, "-")
        self.assertIsInstance(expr.operand, Literal)
        self.assertEqual(expr.operand.raw, "42")

    def test_parse_unary_not(self):
        parser = self.parse_tokens("not x")
        expr = parser.parse_unary()

        # Expected: UnaryOp("not", Identifier("x"))
        self.assertIsInstance(expr, UnaryOp)
        self.assertEqual(expr.op, "not")
        self.assertIsInstance(expr.operand, Identifier)
        self.assertEqual(expr.operand.name, "x")

    def test_parse_call_expr(self):
        parser = self.parse_tokens("foo(1, 2 + 3)")
        expr = parser.parse_expr()
        
        self.assertIsInstance(expr, CallExpr)
        self.assertEqual(expr.func.name, "foo")
        self.assertEqual(len(expr.args), 2)
        self.assertIsInstance(expr.args[1], BinOp)
        self.assertEqual(expr.args[1].op, "+")

    def test_parse_postfix_expr(self):
        parser = self.parse_tokens("f(1, 2 + 3)")
        expr = parser.parse_postfix_expr()

        self.assertIsInstance(expr, CallExpr)
        self.assertIsInstance(expr.func, Identifier)
        self.assertEqual(expr.func.name, "f")
        self.assertEqual(len(expr.args), 2)
        self.assertIsInstance(expr.args[0], Literal)
        self.assertEqual(expr.args[0].raw, "1")
        self.assertIsInstance(expr.args[1], BinOp)
        self.assertEqual(expr.args[1].op, "+")

    def test_parse_attribute_expr(self):
        parser = self.parse_tokens("self.value")
        expr = parser.parse_expr()

        self.assertIsInstance(expr, AttributeExpr)
        self.assertIsInstance(expr.obj, Identifier)
        self.assertEqual(expr.obj.name, "self")
        self.assertEqual(expr.attr, "value")

    def test_parse_index_expr(self):
        parser = self.parse_tokens("a[0]")
        expr = parser.parse_expr()

        self.assertIsInstance(expr, IndexExpr)
        self.assertIsInstance(expr.base, Identifier)
        self.assertEqual(expr.base.name, "a")
        self.assertIsInstance(expr.index, Literal)
        self.assertEqual(expr.index.raw, "0")

    def test_parse_chained_index_expr(self):
        parser = self.parse_tokens("matrix[i][j]")
        expr = parser.parse_expr()

        self.assertIsInstance(expr, IndexExpr)
        self.assertIsInstance(expr.base, IndexExpr)

        base = expr.base
        self.assertEqual(base.base.name, "matrix")
        self.assertEqual(base.index.name, "i")
        self.assertEqual(expr.index.name, "j")

    def test_parse_primary_identifier(self):
        parser = self.parse_tokens("foo")
        expr = parser.parse_primary()

        # Expected: Identifier("foo")
        self.assertIsInstance(expr, Identifier)
        self.assertEqual(expr.name, "foo")

    def test_parse_primary_literal(self):
        parser = self.parse_tokens("42")
        expr = parser.parse_primary()

        # Expected: Literal("42")
        self.assertIsInstance(expr, Literal)
        self.assertEqual(expr.raw, "42")

    def test_parse_term_multiplication(self):
        parser = self.parse_tokens("a * b")
        expr = parser.parse_term()

        # Expected: BinOp(Identifier("a"), "*", Identifier("b"))
        self.assertIsInstance(expr, BinOp)
        self.assertEqual(expr.op, "*")
        self.assertIsInstance(expr.left, Identifier)
        self.assertIsInstance(expr.right, Identifier)

    def test_parse_arith_expr_add_sub(self):
        parser = self.parse_tokens("a + b - c")
        expr = parser.parse_arith_expr()

        # Expected AST:
        # BinOp(
        #   left=BinOp(
        #       left=Identifier("a"),
        #       op="+",
        #       right=Identifier("b")
        #   ),
        #   op="-",
        #   right=Identifier("c")
        # )
        self.assertIsInstance(expr, BinOp)
        self.assertEqual(expr.op, "-")
        self.assertIsInstance(expr.left, BinOp)
        self.assertEqual(expr.left.op, "+")
        self.assertEqual(expr.left.left.name, "a")
        self.assertEqual(expr.left.right.name, "b")
        self.assertEqual(expr.right.name, "c")

    def test_parse_comparison_eq(self):
        parser = self.parse_tokens("x == 42")
        expr = parser.parse_comparison()

        # Expected: BinOp(Identifier(\"x\"), \"==\", Literal(\"42\"))
        self.assertIsInstance(expr, BinOp)
        self.assertEqual(expr.op, "==")
        self.assertIsInstance(expr.left, Identifier)
        self.assertEqual(expr.left.name, "x")
        self.assertIsInstance(expr.right, Literal)
        self.assertEqual(expr.right.raw, "42")

    def test_parse_not_expr(self):
        parser = self.parse_tokens("not x == y")
        expr = parser.parse_not_expr()

        # Expected:
        # UnaryOp("not", BinOp(Identifier("x"), "==", Identifier("y")))
        self.assertIsInstance(expr, UnaryOp)
        self.assertEqual(expr.op, "not")
        self.assertIsInstance(expr.operand, BinOp)
        self.assertEqual(expr.operand.op, "==")

    def test_parse_and_expr(self):
        parser = self.parse_tokens("a and b and c")
        expr = parser.parse_and_expr()

        # Expected:
        # BinOp(
        #   left=BinOp(Identifier("a"), "and", Identifier("b")),
        #   op="and",
        #   right=Identifier("c")
        # )
        self.assertIsInstance(expr, BinOp)
        self.assertEqual(expr.op, "and")
        self.assertIsInstance(expr.left, BinOp)
        self.assertEqual(expr.left.op, "and")
        self.assertEqual(expr.left.left.name, "a")
        self.assertEqual(expr.left.right.name, "b")
        self.assertEqual(expr.right.name, "c")

    def test_parse_or_expr(self):
        parser = self.parse_tokens("a or b or c")
        expr = parser.parse_or_expr()

        # Expected:
        # BinOp(
        #   left=BinOp(Identifier("a"), "or", Identifier("b")),
        #   op="or",
        #   right=Identifier("c")
        # )
        self.assertIsInstance(expr, BinOp)
        self.assertEqual(expr.op, "or")
        self.assertIsInstance(expr.left, BinOp)
        self.assertEqual(expr.left.op, "or")
        self.assertEqual(expr.left.left.name, "a")
        self.assertEqual(expr.left.right.name, "b")
        self.assertEqual(expr.right.name, "c")

    def test_parse_expr(self):
        parser = self.parse_tokens("a + b * c or d and not e")
        expr = parser.parse_expr()

        # Expected structure:
        # BinOp(
        #   left=BinOp(
        #     left=Identifier("a"),
        #     op="+",
        #     right=BinOp(
        #       left=Identifier("b"),
        #       op="*",
        #       right=Identifier("c")
        #     )
        #   ),
        #   op="or",
        #   right=BinOp(
        #     left=Identifier("d"),
        #     op="and",
        #     right=UnaryOp("not", Identifier("e"))
        #   )
        # )
        self.assertIsInstance(expr, BinOp)
        self.assertEqual(expr.op, "or")

    def test_parse_is_not_comparison(self):
        """
        Parser should turn `a is not b` into a single BinOp with op 'is not'.
        """
        parser = self.parse_tokens("a is not b\n")
        expr   = parser.parse_expr()

        self.assertIsInstance(expr, BinOp)
        self.assertEqual(expr.op, "is not")
        self.assertIsInstance(expr.left,  Identifier)
        self.assertIsInstance(expr.right, Identifier)
        self.assertEqual(expr.left.name,  "a")
        self.assertEqual(expr.right.name, "b")

    def test_parse_list_expr(self):
        parser = self.parse_tokens("[1, 2, x + y]")
        expr = parser.parse_expr()

        self.assertIsInstance(expr, ListExpr)
        self.assertEqual(len(expr.elements), 3)
        self.assertIsInstance(expr.elements[0], Literal)
        self.assertEqual(expr.elements[0].raw, "1")
        self.assertIsInstance(expr.elements[2], BinOp)
        self.assertEqual(expr.elements[2].op, "+")

    def test_parse_dict_expr(self):
        parser = self.parse_tokens("{'a': 1, 'b': x + 2}")
        expr = parser.parse_expr()

        self.assertIsInstance(expr, DictExpr)
        self.assertEqual(len(expr.keys), 2)
        self.assertEqual(len(expr.values), 2)
        self.assertIsInstance(expr.keys[0], StringLiteral)
        self.assertEqual(expr.keys[0].value, "a")
        self.assertIsInstance(expr.values[1], BinOp)
        self.assertEqual(expr.values[1].op, "+")


class TestParseStatements(ParserTestCase):

    def test_parse_expr_stmt(self):
        parser = self.parse_tokens("foo + 1\n")
        stmt = parser.parse_expr_stmt()

        # Expected: ExprStmt(BinOp(Identifier("foo"), "+", Literal("1")))
        self.assertIsInstance(stmt, ExprStmt)
        self.assertIsInstance(stmt.expr, BinOp)
        self.assertEqual(stmt.expr.op, "+")
        self.assertEqual(stmt.expr.left.name, "foo")
        self.assertEqual(stmt.expr.right.raw, "1")

    def test_parse_return_stmt_empty(self):
        code = (
            "def f() -> None:\n"
            "    return\n"
        )
        parser = self.parse_tokens(code)
        func   = parser.parse_function_def()          # parse whole function

        # Body should contain exactly one ReturnStmt(None)
        self.assertEqual(len(func.body), 1)
        stmt = func.body[0]
        self.assertIsInstance(stmt, ReturnStmt)
        self.assertIsNone(stmt.value)

    def test_parse_return_stmt_value(self):
        with self.assertRaises(ParserError):
            self.parse_tokens("return x + 1\n").parse_return_stmt()

    def test_parse_var_decl(self):
        parser = self.parse_tokens("x: int = 42\n")
        stmt = parser.parse_var_decl()

        # Expected: VarDecl("x", "int", Literal("42"))
        self.assertIsInstance(stmt, VarDecl)
        self.assertEqual(stmt.name, "x")
        self.assertEqual(stmt.declared_type, "int")
        self.assertIsInstance(stmt.value, Literal)
        self.assertEqual(stmt.value.raw, "42")

    def test_parse_assign_stmt(self):
        parser = self.parse_tokens("x = y + 1\n")
        stmt = parser.parse_assign_stmt()

        # Expected: AssignStmt(
        #   target=Identifier("x"),
        #   value=BinOp(Identifier("y"), "+", Literal("1"))
        # )
        self.assertIsInstance(stmt, AssignStmt)
        self.assertIsInstance(stmt.target, Identifier)
        self.assertEqual(stmt.target.name, "x")
        self.assertIsInstance(stmt.value, BinOp)
        self.assertEqual(stmt.value.op, "+")

    def test_parse_aug_assign_stmt(self):
        parser = self.parse_tokens("x += 2\n")
        stmt = parser.parse_aug_assign_stmt()

        # Expected: AugAssignStmt(
        #   target=Identifier("x"),
        #   op="+=",
        #   value=Literal("2")
        # )
        self.assertIsInstance(stmt, AugAssignStmt)
        self.assertEqual(stmt.op, "+=")
        self.assertIsInstance(stmt.target, Identifier)
        self.assertEqual(stmt.target.name, "x")
        self.assertIsInstance(stmt.value, Literal)
        self.assertEqual(stmt.value.raw, "2")

    def test_parse_if_stmt(self):
        code = (
            "if x:\n"
            "    print(1)\n"
            "elif y:\n"
            "    print(2)\n"
            "else:\n"
            "    print(3)\n"
        )
        parser = self.parse_tokens(code)
        stmt = parser.parse_if_stmt()

        # Expected: IfStmt with 3 branches (if, elif, else)
        self.assertIsInstance(stmt, IfStmt)
        self.assertEqual(len(stmt.branches), 3)
        self.assertIsInstance(stmt.branches[0].condition, Identifier)

    def test_parse_statement_combined(self):
        code = (
            "def g() -> int:\n"
            "    x: int = 1\n"
            "    y = x + 2\n"
            "    y += 3\n"
            "    if y > 2:\n"
            "        return y\n"
            "    else:\n"
            "        return 0\n"
        )
        parser = self.parse_tokens(code)
        func   = parser.parse_function_def()

        stmt1, stmt2, stmt3, stmt4 = func.body
        self.assertIsInstance(stmt1, VarDecl)
        self.assertIsInstance(stmt2, AssignStmt)
        self.assertIsInstance(stmt3, AugAssignStmt)
        self.assertIsInstance(stmt4, IfStmt)
        self.assertEqual(len(stmt4.branches), 2)
        # first branch has return
        self.assertIsInstance(stmt4.branches[0].body[0], ReturnStmt)
        # else-branch return
        self.assertIsNone(stmt4.branches[1].condition)
        self.assertIsInstance(stmt4.branches[1].body[0], ReturnStmt)

    def test_parse_program(self):
        code = (
            "x: int = 10\n"
            "x += 1\n"
        )
        parser = self.parse_tokens(code)
        prog = parser.parse()

        # Expected: Program with 3 statements
        self.assertIsInstance(prog, Program)
        self.assertEqual(len(prog.body), 2)
        self.assertIsInstance(prog.body[0], VarDecl)
        self.assertIsInstance(prog.body[1], AugAssignStmt)

    def test_parse_while_stmt(self):
        code = (
            "while x < 5:\n"
            "    x += 1\n"
        )
        parser = self.parse_tokens(code)
        stmt = parser.parse_while_stmt()

        # Expected: WhileStmt(condition=BinOp(...), body=[AugAssignStmt(...)])
        self.assertIsInstance(stmt, WhileStmt)
        self.assertIsInstance(stmt.condition, BinOp)
        self.assertEqual(stmt.condition.op, "<")
        self.assertIsInstance(stmt.body[0], AugAssignStmt)

    def test_parse_for_stmt(self):
        code = (
            "for i in data:\n"
            "    print(i)\n"
        )
        parser = self.parse_tokens(code)
        stmt = parser.parse_for_stmt()

        # Expected: ForStmt(var="i", iterable=Identifier("data"), body=[ExprStmt])
        self.assertIsInstance(stmt, ForStmt)
        self.assertEqual(stmt.var_name, "i")
        self.assertIsInstance(stmt.iterable, Identifier)
        self.assertIsInstance(stmt.body[0], ExprStmt)

    def test_parse_simple_statements(self):
        code = (
            "while True:\n"
            "    break\n"
            "    continue\n"
        )
        parser = self.parse_tokens(code)
        loop   = parser.parse_statement()     # parse the while-loop

        self.assertIsInstance(loop, WhileStmt)

        body = loop.body
        self.assertIsInstance(body[0], BreakStmt)
        self.assertIsInstance(body[1], ContinueStmt)

    def test_parse_function_None_return_type(self):
        code = (
            "def add_in_place(x: int, y: int) -> None:\n"
            "    x += y\n"
        )
        parser = self.parse_tokens(code)
        stmt = parser.parse_function_def()

        # Expected: FunctionDef("add_in_place", [x:int, y:int], "None", [...])
        self.assertIsInstance(stmt, FunctionDef)
        self.assertEqual(stmt.name, "add_in_place")
        self.assertEqual(len(stmt.params), 2)
        self.assertEqual(stmt.params[0].name, "x")
        self.assertEqual(stmt.params[0].type, "int")
        self.assertEqual(stmt.return_type, "None")
        self.assertIsInstance(stmt.body[0], AugAssignStmt)

    def test_parse_function_no_return_type(self):
        code = (
            "def add_in_place(x: int, y: int):\n"
            "    x += y\n"
        )
        parser = self.parse_tokens(code)
        stmt = parser.parse_function_def()

        # Expected: FunctionDef("add_in_place", [x:int, y:int], "None", [...])
        self.assertIsInstance(stmt, FunctionDef)
        self.assertEqual(stmt.name, "add_in_place")
        self.assertEqual(len(stmt.params), 2)
        self.assertEqual(stmt.params[0].name, "x")
        self.assertEqual(stmt.params[0].type, "int")
        self.assertEqual(stmt.return_type, "None")
        self.assertIsInstance(stmt.body[0], AugAssignStmt)

    def test_parse_function_def(self):
        code = (
            "def add(x: int, y: int) -> int:\n"
            "    return x + y\n"
        )
        parser = self.parse_tokens(code)
        stmt = parser.parse_function_def()

        # Expected: FunctionDef("add", [x:int, y:int], "int", [...])
        self.assertIsInstance(stmt, FunctionDef)
        self.assertEqual(stmt.name, "add")
        self.assertEqual(len(stmt.params), 2)
        self.assertEqual(stmt.params[0].name, "x")
        self.assertEqual(stmt.params[0].type, "int")
        self.assertEqual(stmt.return_type, "int")
        self.assertIsInstance(stmt.body[0], ReturnStmt)

    def test_parse_function_def_with_default(self):
        code = (
            "def inc(x: int = 1) -> int:\n"
            "    return x + y\n"
        )
        parser = self.parse_tokens(code)
        stmt = parser.parse_function_def()

        # Expected: FunctionDef("add", [x:int, y:int], "int", [...])
        self.assertIsInstance(stmt, FunctionDef)
        self.assertEqual(stmt.name, "inc")
        self.assertEqual(len(stmt.params), 1)
        self.assertEqual(stmt.params[0].name, "x")
        self.assertEqual(stmt.params[0].type, "int")
        self.assertIsNotNone(stmt.params[0].default)
        self.assertEqual(stmt.return_type, "int")
        self.assertIsInstance(stmt.body[0], ReturnStmt)

    def test_parse_class_def(self):
        code = (
            "class Point:\n"
            "    x: int = 0\n"
            "    y: int = 0\n"
            "    def reset(self) -> None:\n"
            "        pass\n"
        )
        parser = self.parse_tokens(code)
        stmt = parser.parse_class_def()

        # Expected: ClassDef(name="Point", base=None, fields=[x, y], methods=[reset])
        self.assertIsInstance(stmt, ClassDef)
        self.assertEqual(stmt.name, "Point")
        self.assertIsNone(stmt.base)

        # Fields
        self.assertEqual(len(stmt.fields), 2)
        self.assertIsInstance(stmt.fields[0], VarDecl)
        self.assertEqual(stmt.fields[0].name, "x")
        self.assertEqual(stmt.fields[0].declared_type, "int")
        self.assertEqual(stmt.fields[0].value.raw, "0")

        self.assertEqual(stmt.fields[1].name, "y")
        self.assertEqual(stmt.fields[1].declared_type, "int")

        # Methods
        self.assertEqual(len(stmt.methods), 1)
        method = stmt.methods[0]
        self.assertIsInstance(method, FunctionDef)
        self.assertEqual(method.name, "reset")
        self.assertEqual(method.return_type, "None")
        self.assertEqual(len(method.params), 1)
        self.assertEqual(method.params[0].name, "self")

    def test_parse_class_def_with_base(self):
        code = (
            "class Point(Base):\n"
            "    x: int = 0\n"
            "    def move(self) -> None:\n"
            "        pass\n"
        )
        parser = self.parse_tokens(code)
        stmt = parser.parse_class_def()

        # Expected: ClassDef(name="Point", base="Base", fields=[x], methods=[move])
        self.assertIsInstance(stmt, ClassDef)
        self.assertEqual(stmt.name, "Point")
        self.assertEqual(stmt.base, "Base")

        # Fields
        self.assertEqual(len(stmt.fields), 1)
        self.assertEqual(stmt.fields[0].name, "x")
        self.assertEqual(stmt.fields[0].declared_type, "int")
        self.assertEqual(stmt.fields[0].value.raw, "0")

        # Methods
        self.assertEqual(len(stmt.methods), 1)
        self.assertEqual(stmt.methods[0].name, "move")
        self.assertEqual(stmt.methods[0].return_type, "None")

    def test_parse_global_inside_function(self):
        code = (
            "def use_globals() -> None:\n"
            "    global a, b\n"
            "    a = 1\n"
            "    b = 2\n"
        )
        parser = self.parse_tokens(code)
        func = parser.parse_function_def()

        self.assertEqual(func.name, "use_globals")
        self.assertEqual(len(func.body), 3)
        self.assertIsInstance(func.body[0], GlobalStmt)
        self.assertEqual(func.body[0].names, ["a", "b"])

    def test_parse_assert_stmt(self):
        parser = self.parse_tokens("assert x > 0\n")
        stmt = parser.parse_assert_stmt()

        # Expected: AssertStmt(condition=BinOp(Identifier("x"), ">", Literal("0")))
        self.assertIsInstance(stmt, AssertStmt)
        self.assertIsInstance(stmt.condition, BinOp)
        self.assertEqual(stmt.condition.op, ">")

    def test_parse_raise_stmt(self):
        parser = self.parse_tokens("raise ValueError()\n")
        stmt = parser.parse_raise_stmt()

        self.assertIsInstance(stmt, RaiseStmt)
        self.assertIsInstance(stmt.exception, CallExpr)
        self.assertIsInstance(stmt.exception.func, Identifier)
        self.assertEqual(stmt.exception.func.name, "ValueError")

    def test_parse_try_except_stmt(self):
        code = (
            "try:\n"
            "    risky()\n"
            "except ValueError as err:\n"
            "    handle(err)\n"
            "except:\n"
            "    pass\n"
        )
        parser = self.parse_tokens(code)
        stmt = parser.parse_try_except_stmt()

        self.assertIsInstance(stmt, TryExceptStmt)
        self.assertEqual(len(stmt.except_blocks), 2)

        block1 = stmt.except_blocks[0]
        self.assertEqual(block1.exc_type, "ValueError")
        self.assertEqual(block1.alias, "err")
        self.assertIsInstance(block1.body[0], ExprStmt)

        block2 = stmt.except_blocks[1]
        self.assertIsNone(block2.exc_type)
        self.assertIsNone(block2.alias)
        self.assertIsInstance(block2.body[0], PassStmt)

    def test_parse_import_stmt(self):
        parser = self.parse_tokens("import math.utils.io\n")
        stmt = parser.parse_import_stmt()

        self.assertIsInstance(stmt, ImportStmt)
        self.assertEqual(stmt.module, ["math", "utils", "io"])


class TestParseComplexStmtAndExpr(ParserTestCase):

    def test_parse_full_program(self):
        code = (
            "import sys.io\n"
            "counter: int = 100\n"
            "\n"
            "class Counter:\n"
            "    value: int = 0\n"
            "    def increment(self) -> None:\n"
            "        self.value += 1\n"
            "\n"
            "def main() -> int:\n"
            "    global counter\n"
            "    counter = 1\n"
            "    x: int = 10\n"
            "    while x > 0:\n"
            "        x -= 1\n"
            "    if x == 0:\n"
            "        return x\n"
            "    else:\n"
            "        raise ValueError()\n"
        )

        parser = self.parse_tokens(code)
        prog = parser.parse()

        self.assertIsInstance(prog, Program)
        # Expect four top-level statements:
        #   1) import sys.io
        #   2) counter: int = 100
        #   3) class Counter …
        #   4) def main() …
        self.assertEqual(len(prog.body), 4)

        # --- Check Import ---
        self.assertIsInstance(prog.body[0], ImportStmt)
        self.assertEqual(prog.body[0].module, ["sys", "io"])

        # --- Check top-level VarDecl ---
        self.assertIsInstance(prog.body[1], VarDecl)
        self.assertEqual(prog.body[1].name, "counter")
        self.assertEqual(prog.body[1].declared_type, "int")

        # --- Check ClassDef ---
        cls = prog.body[2]
        self.assertIsInstance(cls, ClassDef)
        self.assertEqual(cls.name, "Counter")
        self.assertEqual(len(cls.fields), 1)
        self.assertEqual(cls.fields[0].name, "value")
        self.assertEqual(cls.fields[0].declared_type, "int")

        self.assertEqual(len(cls.methods), 1)
        self.assertEqual(cls.methods[0].name, "increment")
        self.assertEqual(cls.methods[0].params[0].name, "self")

        # --- Check FunctionDef ---
        fn = prog.body[3]
        self.assertIsInstance(fn, FunctionDef)
        self.assertEqual(fn.name, "main")
        self.assertEqual(fn.return_type, "int")

        # Inside function: global, assignment, while, if-else
        stmt_types = [type(s) for s in fn.body]
        self.assertIn(GlobalStmt, stmt_types)
        self.assertIn(AssignStmt, stmt_types)
        self.assertTrue(any(isinstance(s, WhileStmt) for s in fn.body))
        self.assertTrue(any(isinstance(s, IfStmt) for s in fn.body))


    def test_parse_program_with_try_except_and_assert(self):
        code = (
            "def safe_div(x: int, y: int) -> float:\n"
            "    try:\n"
            "        return x / y\n"
            "    except ZeroDivisionError as err:\n"
            "        print(err)\n"
            "        assert y != 0\n"
            "        return 0.0\n"
        )

        parser = self.parse_tokens(code)
        prog = parser.parse()

        self.assertIsInstance(prog, Program)
        self.assertEqual(len(prog.body), 1)
        fn = prog.body[0]
        self.assertIsInstance(fn, FunctionDef)
        self.assertEqual(fn.name, "safe_div")
        self.assertEqual(len(fn.body), 1)

        try_stmt = fn.body[0]
        self.assertIsInstance(try_stmt, TryExceptStmt)
        self.assertEqual(len(try_stmt.except_blocks), 1)

        exc = try_stmt.except_blocks[0]
        self.assertEqual(exc.exc_type, "ZeroDivisionError")
        self.assertEqual(exc.alias, "err")

    def test_parse_program_with_list_methods(self):
        code = (
            "def list_met() -> None:\n"
            "    arr: list[int] = [1, 2, 3]\n"
            "    arr.append(4)\n"
            "    arr.append(5)\n"
            "    arr.remove(4)\n"
            "    arr.pop(4)\n"
        )

        # Expected
        # Program(body=[
        #     FunctionDef(
        #         name="list_met",
        #         params=[],
        #         return_type="None",
        #         body=[
        #             VarDecl(
        #                 name="arr",
        #                 declared_type="list[int]",
        #                 value=ListExpr(elements=[
        #                     Literal(raw="1"),
        #                     Literal(raw="2"),
        #                     Literal(raw="3")
        #                 ])
        #             ),
        #             ExprStmt(
        #                 expr=CallExpr(
        #                     func=AttributeExpr(
        #                         obj=Identifier(name="arr"),
        #                         attr="append"
        #                     ),
        #                     args=[Literal(raw="4")]
        #                 )
        #             ),
        #             ExprStmt(
        #                 expr=CallExpr(
        #                     func=AttributeExpr(
        #                         obj=Identifier(name="arr"),
        #                         attr="remove"
        #                     ),
        #                     args=[Literal(raw="2")]
        #                 )
        #             ),
        #             ExprStmt(
        #                 expr=CallExpr(
        #                     func=AttributeExpr(
        #                         obj=Identifier(name="arr"),
        #                         attr="pop"
        #                     ),
        #                     args=[]
        #                 )
        #             ),
        #         ]
        #     )
        # ])

        parser = self.parse_tokens(code)
        prog = parser.parse()

        self.assertIsInstance(prog, Program)
        self.assertEqual(len(prog.body), 1)
        fn = prog.body[0]
        self.assertIsInstance(fn, FunctionDef)
        self.assertEqual(fn.name, "list_met")
        self.assertEqual(fn.return_type, "None")
        self.assertEqual(len(fn.body), 5)

        # --- VarDecl for arr ---
        decl = fn.body[0]
        self.assertIsInstance(decl, VarDecl)
        self.assertEqual(decl.name, "arr")
        self.assertEqual(decl.declared_type, "list[int]")
        self.assertIsInstance(decl.value, ListExpr)
        self.assertEqual([e.raw for e in decl.value.elements], ["1", "2", "3"])

        # --- Call to arr.append(4) ---
        stmt1 = fn.body[1]
        self.assertIsInstance(stmt1, ExprStmt)
        call1 = stmt1.expr
        self.assertIsInstance(call1, CallExpr)
        self.assertIsInstance(call1.func, AttributeExpr)
        self.assertEqual(call1.func.obj.name, "arr")
        self.assertEqual(call1.func.attr, "append")
        self.assertEqual(len(call1.args), 1)
        self.assertEqual(call1.args[0].raw, "4")

        # --- Call to arr.append(5) ---
        stmt2 = fn.body[2]
        call2 = stmt2.expr
        self.assertIsInstance(call2, CallExpr)
        self.assertEqual(call2.func.attr, "append")
        self.assertEqual(call2.args[0].raw, "5")

        # --- Call to arr.remove(4) ---
        stmt3 = fn.body[3]
        call3 = stmt3.expr
        self.assertIsInstance(call3, CallExpr)
        self.assertEqual(call3.func.attr, "remove")
        self.assertEqual(call3.args[0].raw, "4")

        # --- Call to arr.pop(4) ---
        stmt4 = fn.body[4]
        call4 = stmt4.expr
        self.assertIsInstance(call4, CallExpr)
        self.assertEqual(call4.func.attr, "pop")
        self.assertEqual(call4.args[0].raw, "4")


class TestParserEdgeCases(unittest.TestCase):
    def lex(self, src: str):
        return Lexer(src).tokenize()

    def parse_program(self, src: str):
        return Parser(self.lex(src)).parse()

    def parse_expr(self, src: str):
        return Parser(self.lex(src)).parse_expr()

    # precedence -------------------------------------------------------
    def test_unary_and_mul_precedence(self):
        expr = self.parse_expr("-x * y\n")
        self.assertIsInstance(expr, BinOp)
        self.assertEqual(expr.op, "*")
        self.assertIsInstance(expr.left, UnaryOp)

    def test_chained_comparison_illegal(self):
        """
        We expect a ParserError only when the whole line is parsed
        as a statement (because the trailing '< c' is left over).
        """
        with self.assertRaises(ParserError):
            # parse **program**, not just expression
            self.parse_program("a < b < c\n")

    # `is` and `is not` -----------------------------------------------
    def test_parse_is_operator(self):
        expr = self.parse_expr("a is b\n")
        self.assertIsInstance(expr, BinOp)
        self.assertEqual(expr.op, "is")

    def test_parse_is_not_operator(self):
        expr = self.parse_expr("a is not b\n")
        self.assertIsInstance(expr, BinOp)
        self.assertEqual(expr.op, "is not")

    # parameters -------------------------------------------------------
    def test_param_with_type_only(self):
        stmt = self.parse_program("def f(x: int) -> None:\n    pass\n").body[0]
        param = stmt.params[0]
        self.assertEqual((param.name, param.type, param.default), ("x", "int", None))

    def test_param_with_default_only(self):
        stmt = self.parse_program("def f(x = 5) -> None:\n    pass\n").body[0]
        param = stmt.params[0]
        self.assertIsNone(param.type)
        self.assertIsNotNone(param.default)

    def test_param_type_and_default(self):
        stmt = self.parse_program("def f(x: int = 0) -> None:\n    pass\n").body[0]
        param = stmt.params[0]
        self.assertEqual(param.type, "int")
        self.assertIsNotNone(param.default)

    # literals ---------------------------------------------------------
    def test_nested_list_and_dict(self):
        expr = self.parse_expr("[{'a': [1, 2]}]\n")
        self.assertIsInstance(expr, ListExpr)
        self.assertIsInstance(expr.elements[0], DictExpr)

    # global stmt ------------------------------------------------------
    def test_global_multiple_names(self):
        with self.assertRaises(ParserError):
            self.parse_program("global a, b, c\n")

    # VarDecl missing initializer -------------------------------------
    def test_vardecl_without_initializer(self):
        with self.assertRaises(ParserError):
            self.parse_program("x: int\n")

    # illegal break ----------------------------------------------------
    def test_break_outside_loop(self):
        bad_fun = (
            "def f() -> None:\n"
            "    break\n"
        )
        with self.assertRaises(ParserError):
            self.parse_program(bad_fun)

    def test_fstring_vars_list(self):
        lit = Parser(self.lex('f"{a}{b}{c}"\n')).parse_literal()
        self.assertIsInstance(lit, FStringLiteral)
        self.assertEqual(lit.vars, ["a", "b", "c"])

    def test_break_error(self):
        with self.assertRaises(ParserError):
            self.parse_program("break\n")

    def test_return_error(self):
        with self.assertRaises(ParserError):
            self.parse_program("return 1\n")

    def test_global_top_level_error(self):
        with self.assertRaises(ParserError):
            self.parse_program("global x\n")

    def test_duplicate_param_error(self):
        bad = "def f(x: int, x: int) -> None:\n    pass\n"
        with self.assertRaises(ParserError):
            self.parse_program(bad)

    def test_empty_function_body_error(self):
        bad = "def f() -> None:\n    \n"
        with self.assertRaises(ParserError):
            self.parse_program(bad)

    def test_empty_class_body_error(self):
        bad = "class C:\n    \n"
        with self.assertRaises(ParserError):
            self.parse_program(bad)

    def test_chained_comparison_error(self):
        with self.assertRaises(ParserError):
            self.parse_program("a < b < c\n")

    def test_function_call_not_allowed_in_global_scope(self):
        self.assertRaisesRegex(ParserError, "Function call", self.parse_program, "print(5)\n")

    def test_if_statement_not_allowed_in_global_scope(self):
        with self.assertRaisesRegex(ParserError, "Statement `If` not allowed in global scope."):
            self.parse_program("if True:\n    pass\n")

    def test_while_statement_not_allowed_in_global_scope(self):
        with self.assertRaisesRegex(ParserError, "Statement `While` not allowed in global scope."):
            self.parse_program("while True:\n    pass\n")

    def test_for_statement_not_allowed_in_global_scope(self):
        with self.assertRaisesRegex(ParserError, "Statement `For` not allowed in global scope."):
            self.parse_program("for i in range(5):\n    pass\n")

    def test_try_except_statement_not_allowed_in_global_scope(self):
        with self.assertRaisesRegex(ParserError, "Statement `TryExcept` not allowed in global scope."):
            self.parse_program("try:\n    pass\nexcept:\n    pass\n")

    def test_raise_statement_not_allowed_in_global_scope(self):
        with self.assertRaisesRegex(ParserError, "Statement `Raise` not allowed in global scope."):
            self.parse_program("raise Exception()\n")

    def test_assert_statement_not_allowed_in_global_scope(self):
        with self.assertRaisesRegex(ParserError, "Statement `Assert` not allowed in global scope."):
            self.parse_program("assert False\n")

    def test_pass_statement_not_allowed_in_global_scope(self):
        with self.assertRaisesRegex(ParserError, "Statement `Pass` not allowed in global scope."):
            self.parse_program("pass\n")


class TestGenericTypes(ParserTestCase):

    def test_parse_var_decl_with_empty_list(self):
        code = (
            "arr: list[int] = []\n"
        )

        parser = self.parse_tokens(code)
        prog = parser.parse()

        self.assertIsInstance(prog, Program)
        self.assertEqual(len(prog.body), 1)

        decl = prog.body[0]
        self.assertIsInstance(decl, VarDecl)
        self.assertEqual(decl.name, "arr")
        self.assertEqual(decl.declared_type, "list[int]")
        self.assertEqual(decl.value.elements, [])

    def test_parse_var_decl_with_generic_list(self):
        code = (
            "arr: list[int] = [1, 2, 3]\n"
        )

        parser = self.parse_tokens(code)
        prog = parser.parse()

        self.assertIsInstance(prog, Program)
        self.assertEqual(len(prog.body), 1)

        decl = prog.body[0]
        self.assertIsInstance(decl, VarDecl)
        self.assertEqual(decl.name, "arr")
        self.assertEqual(decl.declared_type, "list[int]")
        self.assertEqual(decl.value.elements, [
            Literal(raw='1'), Literal(raw='2'), Literal(raw='3')])

    def test_parse_function_with_generic_annotations(self):
        code = (
            "def foo(xs: list[int]) -> dict[str, int]:\n"
            "    return {}\n"
        )

        parser = self.parse_tokens(code)
        prog = parser.parse()

        self.assertIsInstance(prog, Program)
        self.assertEqual(len(prog.body), 1)

        fn = prog.body[0]
        self.assertIsInstance(fn, FunctionDef)
        self.assertEqual(fn.name, "foo")
        # parameters
        self.assertEqual(len(fn.params), 1)
        param = fn.params[0]
        self.assertEqual(param.type, "list[int]")
        # return type
        self.assertEqual(fn.return_type, "dict[str, int]")

    def test_parse_nested_generic_type(self):
        code = (
            "data: list[dict[str, float]] = []\n"
        )

        parser = self.parse_tokens(code)
        prog = parser.parse()

        self.assertIsInstance(prog, Program)
        self.assertEqual(len(prog.body), 1)

        decl = prog.body[0]
        self.assertIsInstance(decl, VarDecl)
        self.assertEqual(decl.name, "data")
        self.assertEqual(decl.declared_type, "list[dict[str, float]]")


class TestParseLists(ParserTestCase):

    def parse_expr(self, code: str):
        return self.parse_tokens(code).parse_expr()

    def parse_expr_stmt(self, code: str):
        return self.parse_tokens(code).parse_expr_stmt()

    def test_list_with_ints(self):
        expr = self.parse_expr("[1, 2, 3]\n")
        self.assertIsInstance(expr, ListExpr)
        self.assertEqual(len(expr.elements), 3)
        for i, val in enumerate(["1", "2", "3"]):
            self.assertIsInstance(expr.elements[i], Literal)
            self.assertEqual(expr.elements[i].raw, val)

    def test_list_with_floats(self):
        expr = self.parse_expr("[1.0, 2.5, 3.14]\n")
        self.assertIsInstance(expr, ListExpr)
        self.assertEqual(len(expr.elements), 3)
        self.assertEqual([e.raw for e in expr.elements], ["1.0", "2.5", "3.14"])

    def test_list_with_bools(self):
        expr = self.parse_expr("[True, False, True]\n")
        self.assertIsInstance(expr, ListExpr)
        self.assertEqual([e.raw for e in expr.elements], ["True", "False", "True"])

    def test_list_with_strings(self):
        expr = self.parse_expr("['a', 'b', 'c']\n")
        self.assertIsInstance(expr, ListExpr)
        self.assertEqual(len(expr.elements), 3)
        for el in expr.elements:
            self.assertIsInstance(el, StringLiteral)
        self.assertEqual([el.value for el in expr.elements], ["a", "b", "c"])

    def test_empty_list(self):
        expr = self.parse_expr("[]\n")
        self.assertIsInstance(expr, ListExpr)
        self.assertEqual(expr.elements, [])

    def test_list_append_method(self):
        stmt = self.parse_expr_stmt("items.append(42)\n")
        self.assertIsInstance(stmt, ExprStmt)

        expr = stmt.expr
        self.assertIsInstance(expr, CallExpr)

        self.assertIsInstance(expr.func, AttributeExpr)
        self.assertEqual(expr.func.attr, "append")
        self.assertEqual(expr.func.obj.name, "items")

        self.assertEqual(len(expr.args), 1)
        self.assertIsInstance(expr.args[0], Literal)
        self.assertEqual(expr.args[0].raw, "42")

    def test_list_pop_method(self):
        stmt = self.parse_expr_stmt("items.pop()\n")
        self.assertIsInstance(stmt, ExprStmt)

        expr = stmt.expr
        self.assertIsInstance(expr, CallExpr)

        self.assertIsInstance(expr.func, AttributeExpr)
        self.assertEqual(expr.func.attr, "pop")
        self.assertEqual(expr.func.obj.name, "items")
        self.assertEqual(expr.args, [])

    def test_list_remove_method(self):
        stmt = self.parse_expr_stmt("items.remove('a')\n")
        self.assertIsInstance(stmt, ExprStmt)

        expr = stmt.expr
        self.assertIsInstance(expr, CallExpr)

        self.assertIsInstance(expr.func, AttributeExpr)
        self.assertEqual(expr.func.attr, "remove")
        self.assertEqual(expr.func.obj.name, "items")

        self.assertEqual(len(expr.args), 1)
        self.assertIsInstance(expr.args[0], StringLiteral)
        self.assertEqual(expr.args[0].value, "a")


if __name__ == "__main__":
    unittest.main()