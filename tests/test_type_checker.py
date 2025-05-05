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

    def test_list_mixed_type_type_error(self):
        prog = Program([
            FunctionDef(
                name="main",
                params=[],
                body=[
                    AssignStmt("bad_list", ListExpr([Literal(1), Literal(2.0), Literal(3)])),
                ],
                return_type="int"
            )
        ])
        self.check_type_error(prog)

    def test_index_expr_infers_float_type(self):
        prog = Program([
            FunctionDef(
                name="main",
                params=[],
                body=[
                    AssignStmt("floats", ListExpr([Literal(1.0), Literal(2.0)])),
                    AssignStmt("x", IndexExpr(Identifier("floats"), Literal(0))),
                    ReturnStmt(Identifier("x"))
                ],
                return_type="float"
            )
        ])
        self.check_ok(prog)

    def test_augassign_float_type_check(self):
        prog = Program([
            FunctionDef(
                name="main",
                params=[],
                body=[
                    VarDecl("value", "float", Literal(1.5)),
                    AugAssignStmt("value", "+", Literal(2.5)),
                    ReturnStmt(Literal(0))
                ],
                return_type="int"
            )
        ])
        self.check_ok(prog)

    def test_logical_type_mismatch_should_fail(self):
        prog = Program([
            FunctionDef(
                name="main",
                params=[],
                body=[
                    ReturnStmt(
                        BinOp(Literal(1), "and", Literal(2))  # ints, invalid for logical ops
                    )
                ],
                return_type="bool"
            )
        ])
        self.check_type_error(prog)

    def test_print_list_should_fail(self):
        prog = Program([
            FunctionDef(
                name="main",
                params=[],
                body=[
                    CallExpr(Identifier("print"), [ListExpr([Literal(1), Literal(2)])]),
                    ReturnStmt(Literal(0))
                ],
                return_type="int"
            )
        ])
        self.check_type_error(prog)

    def test_empty_list_literal_should_fail(self):
        prog = Program([
            FunctionDef(
                name="main",
                params=[],
                body=[
                    AssignStmt("x", ListExpr([])),
                    ReturnStmt(Literal(0))
                ],
                return_type="int"
            )
        ])
        self.check_type_error(prog)

    def test_void_function_no_return(self):
        prog = Program([
            FunctionDef(
                name="debug",
                params=[],
                body=[
                    CallExpr(Identifier("print"), [Literal("Debugging...")])
                ],
                return_type=None
            )
        ])
        TypeChecker().check(prog)

    def test_void_function_return_none(self):
        prog = Program([
            FunctionDef(
                name="debug",
                params=[],
                body=[
                    ReturnStmt(Literal(None))
                ],
                return_type=None
            )
        ])
        TypeChecker().check(prog)

    def test_return_value_in_void_function_should_fail(self):
        prog = Program([
            FunctionDef(
                name="debug",
                params=[],
                body=[
                    ReturnStmt(Literal(123))
                ],
                return_type=None
            )
        ])
        with self.assertRaises(LangTypeError) as ctx:
            TypeChecker().check(prog)
        self.assertIn("Cannot return a value from a function declared as void", str(ctx.exception))

    def test_return_string_in_void_function_should_fail(self):
        prog = Program([
            FunctionDef(
                name="debug",
                params=[],
                body=[
                    ReturnStmt(Literal("oops"))
                ],
                return_type=None
            )
        ])
        with self.assertRaises(LangTypeError) as ctx:
            TypeChecker().check(prog)
        self.assertIn("Cannot return a value from a function declared as void", str(ctx.exception))

    def test_int_return_function_ok(self):
        prog = Program([
            FunctionDef(
                name="get_number",
                params=[],
                body=[
                    ReturnStmt(Literal(42))
                ],
                return_type="int"
            )
        ])
        TypeChecker().check(prog)

    def test_int_return_function_wrong_type_should_fail(self):
        prog = Program([
            FunctionDef(
                name="get_number",
                params=[],
                body=[
                    ReturnStmt(Literal("not a number"))
                ],
                return_type="int"
            )
        ])
        with self.assertRaises(LangTypeError) as ctx:
            TypeChecker().check(prog)
        self.assertIn("Function declared to return 'int' but got 'str'", str(ctx.exception))

if __name__ == "__main__":
    unittest.main()
