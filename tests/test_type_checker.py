import unittest
from lang_ast import *
from type_checker import TypeChecker, LangTypeError

class TestTypeChecker(unittest.TestCase):
    def check_ok(self, node):
        checker = TypeChecker()
        checker.check(node)  # Should not raise

    def check_type_error(self, node):
        checker = TypeChecker()
        with self.assertRaises(LangTypeError):
            checker.check(node)

    def test_valid_function(self):
        prog = Program([
            FunctionDef(
                name="add",
                params=[("x", "int"), ("y", "int")],
                body=[ReturnStmt(BinOp(Identifier("x"), "+", Identifier("y")))],
                return_type="int"
            )
        ])
        self.check_ok(prog)

    def test_invalid_return_type(self):
        prog = Program([
            FunctionDef(
                name="wrong",
                params=[],
                body=[ReturnStmt(Literal("hello"))],
                return_type="int"
            )
        ])
        self.check_type_error(prog)

    def test_undeclared_variable(self):
        prog = Program([
            FunctionDef(
                name="f",
                params=[],
                body=[ReturnStmt(Identifier("x"))],
                return_type="int"
            )
        ])
        self.check_type_error(prog)

    def test_type_mismatch_binop(self):
        prog = Program([
            FunctionDef(
                name="f",
                params=[],
                body=[
                    AssignStmt("a", Literal(1)),
                    AssignStmt("b", Literal("str")),
                    ReturnStmt(BinOp(Identifier("a"), "+", Identifier("b")))
                ],
                return_type="int"
            )
        ])
        self.check_type_error(prog)

    def test_logical_expression(self):
        prog = Program([
            FunctionDef(
                name="logic",
                params=[("x", "bool"), ("y", "bool")],
                body=[ReturnStmt(BinOp(Identifier("x"), "and", Identifier("y")))],
                return_type="bool"
            )
        ])
        self.check_ok(prog)

    def test_call_argument_mismatch(self):
        prog = Program([
            FunctionDef(
                name="f",
                params=[("x", "int")],
                body=[ReturnStmt(Identifier("x"))],
                return_type="int"
            ),
            FunctionDef(
                name="main",
                params=[],
                body=[ReturnStmt(CallExpr(Identifier("f"), [Literal("oops")]))],
                return_type="int"
            )
        ])
        self.check_type_error(prog)

    def test_indexing_type_errors(self):
        prog = Program([
            FunctionDef(
                name="main",
                params=[],
                body=[
                    AssignStmt("d", Literal(42)),
                    AssignStmt("x", IndexExpr(Identifier("d"), Literal(0))),
                    ReturnStmt(Identifier("x"))
                ],
                return_type="int"
            )
        ])
        self.check_type_error(prog)

    def test_vardecl_type_check(self):
        prog = Program([
            FunctionDef(
                name="main",
                params=[],
                body=[
                    VarDecl("x", "int", Literal(10)),
                    ReturnStmt(Identifier("x")),
                ],
                return_type="int"
            )
        ])
        self.check_ok(prog)

    def test_vardecl_type_mismatch(self):
        prog = Program([
            FunctionDef(
                name="main",
                params=[],
                body=[
                    VarDecl("x", "int", Literal("oops")),
                ],
                return_type="int"
            )
        ])
        self.check_type_error(prog)

    def test_missing_type_in_global_should_fail(self):
        # This mimics: counter = 100  (without type)
        prog = Program([
            AssignStmt("counter", Literal(100)),  # 🚫 invalid: no type
            FunctionDef(
                name="main",
                params=[],
                body=[
                    ReturnStmt(Literal(0))
                ],
                return_type="int"
            )
        ])
        checker = TypeChecker()
        with self.assertRaises(LangTypeError) as ctx:
            checker.check(prog)
        self.assertIn("Global variable 'counter' must be declared with a type", str(ctx.exception))

    def test_global_vardecl_is_valid(self):
        prog = Program([
            VarDecl("counter", "int", Literal(100)),  # ✅ valid
            FunctionDef(
                name="main",
                params=[],
                body=[
                    ReturnStmt(Identifier("counter"))
                ],
                return_type="int"
            )
        ])
        self.check_ok(prog)

if __name__ == "__main__":
    unittest.main()
