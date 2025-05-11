from sys import exception
import unittest

from type_checker import TypeChecker, TypeError
from lang_ast import (
    Program,
    VarDecl,
    Literal,
    Identifier,
    BinOp,
    UnaryOp,
    CallExpr,
    ReturnStmt,
    Parameter,
    FunctionDef,
    AssignStmt,
    IndexExpr,
    AugAssignStmt,
    IfStmt,
    IfBranch,
    WhileStmt,
    ForStmt,
    BreakStmt,
    ContinueStmt,
    PassStmt,
    ClassDef,
    AttributeExpr,
    IndexExpr,
    ListExpr,
    DictExpr,
    AssertStmt,
    RaiseStmt,
    GlobalStmt,
    TryExceptStmt,
    ExceptBlock,
)



# ────────────────────────────────────────────────────────────────
# Unit-level tests (method-level granularity)
# ────────────────────────────────────────────────────────────────
class TestTypeCheckerInternals(unittest.TestCase):
    def setUp(self):
        self.tc = TypeChecker()

    def test_check_var_decl_matches_type(self):
        decl = VarDecl(name="x", declared_type="int", value=Literal(raw="42"))
        self.tc.check_var_decl(decl)  # should not raise
        self.assertEqual(self.tc.env["x"], "int")

    def test_check_var_decl_mismatch(self):
        decl = VarDecl(name="x", declared_type="float", value=Literal(raw="42"))
        with self.assertRaises(TypeError):
            self.tc.check_var_decl(decl)

    def test_check_expr_literal_int(self):
        typ = self.tc.check_expr(Literal(raw="123"))
        self.assertEqual(typ, "int")

    def test_check_expr_literal_float(self):
        typ = self.tc.check_expr(Literal(raw="3.14"))
        self.assertEqual(typ, "float")

    def test_check_expr_literal_scientific(self):
        typ = self.tc.check_expr(Literal(raw="6.02e23"))
        self.assertEqual(typ, "float")

    def test_check_expr_literal_bool_true(self):
        typ = self.tc.check_expr(Literal(raw="True"))
        self.assertEqual(typ, "bool")

    def test_check_expr_literal_bool_false(self):
        typ = self.tc.check_expr(Literal(raw="False"))
        self.assertEqual(typ, "bool")

    def test_check_expr_literal_none(self):
        typ = self.tc.check_expr(Literal(raw="None"))
        self.assertEqual(typ, "None")

    def test_check_expr_identifier_found(self):
        self.tc.env["y"] = "int"
        typ = self.tc.check_expr(Identifier(name="y"))
        self.assertEqual(typ, "int")

    def test_check_expr_identifier_undefined(self):
        with self.assertRaises(TypeError):
            self.tc.check_expr(Identifier(name="z"))

    def test_binop_add_ints(self):
        expr = BinOp(Literal("1"), "+", Literal("2"))
        self.assertEqual(self.tc.check_expr(expr), "int")

    def test_binop_add_floats(self):
        expr = BinOp(Literal("1.0"), "+", Literal("2.0"))
        self.assertEqual(self.tc.check_expr(expr), "float")

    def test_binop_add_mismatch(self):
        expr = BinOp(Literal("1"), "+", Literal("2.0"))
        with self.assertRaises(TypeError):
            self.tc.check_expr(expr)

    def test_binop_eq(self):
        expr = BinOp(Literal("42"), "==", Literal("42"))
        self.assertEqual(self.tc.check_expr(expr), "bool")

    def test_binop_lt(self):
        expr = BinOp(Literal("1"), "<", Literal("2"))
        self.assertEqual(self.tc.check_expr(expr), "bool")

    def test_binop_is(self):
        expr = BinOp(Literal("None"), "is", Literal("None"))
        self.assertEqual(self.tc.check_expr(expr), "bool")

    def test_binop_and_bool(self):
        expr = BinOp(Literal("True"), "and", Literal("False"))
        self.assertEqual(self.tc.check_expr(expr), "bool")

    def test_binop_and_nonbool(self):
        expr = BinOp(Literal("1"), "and", Literal("2"))
        with self.assertRaises(TypeError):
            self.tc.check_expr(expr)

    def test_unary_minus_int(self):
        expr = UnaryOp("-", Literal("42"))
        self.assertEqual(self.tc.check_expr(expr), "int")

    def test_unary_minus_float(self):
        expr = UnaryOp("-", Literal("3.14"))
        self.assertEqual(self.tc.check_expr(expr), "float")

    def test_unary_minus_invalid(self):
        expr = UnaryOp("-", Literal("True"))
        with self.assertRaises(TypeError):
            self.tc.check_expr(expr)

    def test_unary_not_bool(self):
        expr = UnaryOp("not", Literal("False"))
        self.assertEqual(self.tc.check_expr(expr), "bool")

    def test_unary_not_invalid(self):
        expr = UnaryOp("not", Literal("1"))
        with self.assertRaises(TypeError):
            self.tc.check_expr(expr)

    def test_call_expr_valid(self):
        self.tc.functions["inc"] = (["int"], "int")
        call = CallExpr(func=Identifier("inc"), args=[Literal("1")])
        self.assertEqual(self.tc.check_expr(call), "int")

    def test_call_expr_wrong_arg_count(self):
        self.tc.functions["f"] = (["int", "int"], "int")
        call = CallExpr(func=Identifier("f"), args=[Literal("1")])
        with self.assertRaises(TypeError):
            self.tc.check_expr(call)

    def test_call_expr_wrong_arg_type(self):
        self.tc.functions["f"] = (["int"], "int")
        call = CallExpr(func=Identifier("f"), args=[Literal("True")])
        with self.assertRaises(TypeError):
            self.tc.check_expr(call)

    def test_call_expr_unknown_function(self):
        call = CallExpr(func=Identifier("ghost"), args=[])
        with self.assertRaises(TypeError):
            self.tc.check_expr(call)

    def test_return_stmt_matching_type(self):
        self.tc.current_return_type = "int"
        stmt = ReturnStmt(value=Literal("1"))
        self.tc.check_return_stmt(stmt)  # should not raise

    def test_return_stmt_mismatch(self):
        self.tc.current_return_type = "int"
        stmt = ReturnStmt(value=Literal("3.14"))
        with self.assertRaises(TypeError):
            self.tc.check_return_stmt(stmt)

    def test_return_stmt_void_expected(self):
        self.tc.current_return_type = "None"
        stmt = ReturnStmt(value=None)
        self.tc.check_return_stmt(stmt)  # OK

    def test_return_stmt_nonvoid_in_void_function(self):
        self.tc.current_return_type = "None"
        stmt = ReturnStmt(value=Literal("1"))
        with self.assertRaises(TypeError):
            self.tc.check_return_stmt(stmt)

    def test_return_stmt_outside_function(self):
        self.tc.current_return_type = None
        stmt = ReturnStmt(value=Literal("42"))
        with self.assertRaises(TypeError):
            self.tc.check_return_stmt(stmt)

    def test_check_function_def_valid(self):
        fn = FunctionDef(
            name="square",
            params=[Parameter("x", "int")],
            return_type="int",
            body=[ReturnStmt(BinOp(Identifier("x"), "*", Identifier("x")))]
        )
        self.tc.check_function_def(fn)
        self.assertIn("square", self.tc.functions)

    def test_check_function_def_duplicate_param(self):
        fn = FunctionDef(
            name="bad",
            params=[Parameter("x", "int"), Parameter("x", "float")],
            return_type="int",
            body=[ReturnStmt(Identifier("x"))]
        )
        with self.assertRaises(TypeError):
            self.tc.check_function_def(fn)

    def test_check_function_def_missing_type(self):
        fn = FunctionDef(
            name="oops",
            params=[Parameter("x", None)],
            return_type="int",
            body=[ReturnStmt(Identifier("x"))]
        )
        with self.assertRaises(TypeError):
            self.tc.check_function_def(fn)

    def test_assign_stmt_matching_type(self):
        self.tc.env["x"] = "int"
        stmt = AssignStmt(target=Identifier("x"), value=Literal("42"))
        self.tc.check_assign_stmt(stmt)  # OK

    def test_assign_stmt_mismatch(self):
        self.tc.env["x"] = "int"
        stmt = AssignStmt(target=Identifier("x"), value=Literal("3.14"))
        with self.assertRaises(TypeError):
            self.tc.check_assign_stmt(stmt)

    def test_assign_stmt_undefined(self):
        stmt = AssignStmt(target=Identifier("x"), value=Literal("42"))
        with self.assertRaises(TypeError):
            self.tc.check_assign_stmt(stmt)

    def test_assign_stmt_non_identifier_target(self):
        self.tc.env["x"] = "int"
        # Simulate invalid target like x[0] = ...
        stmt = AssignStmt(target=IndexExpr(Identifier("x"), Literal("0")), value=Literal("1"))
        with self.assertRaises(TypeError):
            self.tc.check_assign_stmt(stmt)

    def test_aug_assign_valid(self):
        self.tc.env["x"] = "int"
        stmt = AugAssignStmt(Identifier("x"), "+=", Literal("1"))
        self.tc.check_aug_assign_stmt(stmt)

    def test_aug_assign_type_mismatch(self):
        self.tc.env["x"] = "int"
        stmt = AugAssignStmt(Identifier("x"), "+=", Literal("3.14"))
        with self.assertRaises(TypeError):
            self.tc.check_aug_assign_stmt(stmt)

    def test_aug_assign_unsupported_operator(self):
        self.tc.env["x"] = "int"
        stmt = AugAssignStmt(Identifier("x"), "**=", Literal("2"))  # Invalid op
        with self.assertRaises(TypeError):
            self.tc.check_aug_assign_stmt(stmt)

    def test_aug_assign_on_undefined_variable(self):
        stmt = AugAssignStmt(Identifier("x"), "+=", Literal("1"))
        with self.assertRaises(TypeError):
            self.tc.check_aug_assign_stmt(stmt)

    def test_if_stmt_with_bool_condition(self):
        stmt = IfStmt(branches=[
            IfBranch(condition=Literal("True"), body=[
                VarDecl("x", "int", Literal("1")),
                AssignStmt(Identifier("x"), Literal("2"))
            ]),
            IfBranch(condition=None, body=[
                AssignStmt(Identifier("x"), Literal("3"))
            ])
        ])
        self.tc.env["x"] = "int"
        self.tc.check_if_stmt(stmt)

    def test_if_stmt_with_invalid_condition(self):
        stmt = IfStmt(branches=[
            IfBranch(condition=Literal("42"), body=[])
        ])
        with self.assertRaises(TypeError):
            self.tc.check_if_stmt(stmt)

    def test_while_stmt_valid(self):
        stmt = WhileStmt(
            condition=Literal("True"),
            body=[
                VarDecl("x", "int", Literal("1")),
                AssignStmt(Identifier("x"), Literal("2")),
                BreakStmt(),
                ContinueStmt()
            ]
        )
        self.tc.env["x"] = "int"
        self.tc.check_while_stmt(stmt)

    def test_while_stmt_condition_not_bool(self):
        stmt = WhileStmt(condition=Literal("42"), body=[])
        with self.assertRaises(TypeError):
            self.tc.check_while_stmt(stmt)

    def test_break_outside_loop(self):
        with self.assertRaises(TypeError):
            self.tc.check_stmt(BreakStmt())

    def test_continue_outside_loop(self):
        with self.assertRaises(TypeError):
            self.tc.check_stmt(ContinueStmt())

    def test_for_loop_valid(self):
        stmt = ForStmt(
            var_name="item",
            iterable=Literal("[]"),
            body=[
                PassStmt()
            ]
        )
        self.tc.env["values"] = "list[int]"
        stmt.iterable = Identifier("values")
        self.tc.check_for_stmt(stmt)

    def test_for_loop_iterable_not_list(self):
        stmt = ForStmt(
            var_name="x",
            iterable=Literal("42"),
            body=[]
        )
        with self.assertRaises(TypeError):
            self.tc.check_for_stmt(stmt)

    def test_class_def_simple(self):
        cls = ClassDef(
            name="Point",
            base=None,
            fields=[
                VarDecl("x", "int", Literal("0")),
                VarDecl("y", "int", Literal("0"))
            ],
            methods=[]
        )
        self.tc.check_class_def(cls)
        self.assertIn("Point", self.tc.classes)
        self.assertEqual(self.tc.classes["Point"]["x"], "int")

    def test_class_def_with_base(self):
        self.tc.classes["Base"] = {}
        cls = ClassDef(
            name="Child",
            base="Base",
            fields=[],
            methods=[]
        )
        self.tc.check_class_def(cls)

    def test_class_def_invalid_base(self):
        cls = ClassDef(
            name="Child",
            base="Ghost",
            fields=[],
            methods=[]
        )
        with self.assertRaises(TypeError):
            self.tc.check_class_def(cls)

    def test_class_def_with_method(self):
        cls = ClassDef(
            name="Greeter",
            base=None,
            fields=[],
            methods=[
                FunctionDef(
                    name="say_hi",
                    params=[Parameter("self", "Greeter")],
                    return_type="None",
                    body=[ReturnStmt(None)]
                )
            ]
        )
        self.tc.check_class_def(cls)

    def test_attribute_expr_valid(self):
        self.tc.env["self"] = "Point"
        self.tc.classes["Point"] = {"x": "int", "y": "int"}

        expr = AttributeExpr(Identifier("self"), "x")
        typ = self.tc.check_expr(expr)
        self.assertEqual(typ, "int")

    def test_attribute_expr_unknown_class(self):
        self.tc.env["obj"] = "Ghost"
        expr = AttributeExpr(Identifier("obj"), "foo")
        with self.assertRaises(TypeError):
            self.tc.check_expr(expr)

    def test_attribute_expr_field_not_found(self):
        self.tc.env["self"] = "Point"
        self.tc.classes["Point"] = {"x": "int"}
        expr = AttributeExpr(Identifier("self"), "y")
        with self.assertRaises(TypeError):
            self.tc.check_expr(expr)

    def test_attribute_expr_obj_not_identifier(self):
        expr = AttributeExpr(BinOp(Literal("1"), "+", Literal("2")), "x")
        with self.assertRaises(TypeError):
            self.tc.check_expr(expr)

    def test_index_expr_list_int(self):
        self.tc.env["nums"] = "list[int]"
        expr = IndexExpr(Identifier("nums"), Literal("0"))
        self.assertEqual(self.tc.check_expr(expr), "int")

    def test_index_expr_list_wrong_index(self):
        self.tc.env["nums"] = "list[int]"
        expr = IndexExpr(Identifier("nums"), Literal('"zero"'))
        with self.assertRaises(TypeError):
            self.tc.check_expr(expr)

    def test_index_expr_dict_str(self):
        self.tc.env["scores"] = "dict[str, int]"
        expr = IndexExpr(Identifier("scores"), Literal('"math"'))
        self.assertEqual(self.tc.check_expr(expr), "int")

    def test_index_expr_dict_wrong_key(self):
        self.tc.env["scores"] = "dict[str, int]"
        expr = IndexExpr(Identifier("scores"), Literal("0"))
        with self.assertRaises(TypeError):
            self.tc.check_expr(expr)

    def test_index_expr_invalid_base(self):
        self.tc.env["x"] = "int"
        expr = IndexExpr(Identifier("x"), Literal("0"))
        with self.assertRaises(TypeError):
            self.tc.check_expr(expr)

    def test_list_expr_valid(self):
        expr = ListExpr(elements=[
            Literal("1"), Literal("2"), Literal("3")
        ])
        self.assertEqual(self.tc.check_expr(expr), "list[int]")

    def test_list_expr_mixed_types(self):
        expr = ListExpr(elements=[
            Literal("1"), Literal("2.0")
        ])
        with self.assertRaises(TypeError):
            self.tc.check_expr(expr)

    def test_list_expr_empty(self):
        expr = ListExpr(elements=[])
        with self.assertRaises(TypeError):
            self.tc.check_expr(expr)

    def test_dict_expr_valid(self):
        expr = DictExpr(
            keys=[Literal('"a"'), Literal('"b"')],
            values=[Literal("1"), Literal("2")]
        )
        self.assertEqual(self.tc.check_expr(expr), "dict[str, int]")

    def test_dict_expr_non_str_keys(self):
        expr = DictExpr(
            keys=[Literal("1")],
            values=[Literal("2")]
        )
        with self.assertRaises(TypeError):
            self.tc.check_expr(expr)

    def test_dict_expr_mixed_value_types(self):
        expr = DictExpr(
            keys=[Literal('"a"'), Literal('"b"')],
            values=[Literal("1"), Literal("3.14")]
        )
        with self.assertRaises(TypeError):
            self.tc.check_expr(expr)

    def test_dict_expr_empty(self):
        expr = DictExpr(keys=[], values=[])
        with self.assertRaises(TypeError):
            self.tc.check_expr(expr)

    def test_assert_stmt_valid(self):
        stmt = AssertStmt(condition=Literal("True"))
        self.tc.check_assert_stmt(stmt)  # should pass

    def test_assert_stmt_invalid_type(self):
        stmt = AssertStmt(condition=Literal("42"))
        with self.assertRaises(TypeError):
            self.tc.check_assert_stmt(stmt)

    def test_raise_stmt_valid(self):
        stmt = RaiseStmt(exception=Literal('"Error!"'))
        self.tc.check_raise_stmt(stmt)

    def test_raise_stmt_none(self):
        stmt = RaiseStmt(exception=Literal("None"))
        with self.assertRaises(TypeError):
            self.tc.check_raise_stmt(stmt)

    def test_global_stmt_in_function(self):
        self.tc.current_return_type = "int"
        stmt = GlobalStmt(names=["x", "y"])
        self.tc.check_global_stmt(stmt)

    def test_global_stmt_outside_function(self):
        self.tc.current_return_type = None
        stmt = GlobalStmt(names=["x"])
        with self.assertRaises(TypeError):
            self.tc.check_global_stmt(stmt)

    def test_try_except_valid(self):
        self.tc.classes["Error"] = {}
        stmt = TryExceptStmt(
            try_body=[
                AssertStmt(condition=Literal("True"))
            ],
            except_blocks=[
                ExceptBlock(
                    exc_type="Error",
                    alias="e",
                    body=[PassStmt()]
                )
            ]
        )
        self.tc.current_return_type = "None"
        self.tc.check_try_except_stmt(stmt)

    def test_try_except_unknown_exc_type(self):
        stmt = TryExceptStmt(
            try_body=[PassStmt()],
            except_blocks=[
                ExceptBlock(exc_type="Ghost", alias=None, body=[PassStmt()])
            ]
        )
        with self.assertRaises(TypeError):
            self.tc.check_try_except_stmt(stmt)

    def test_function_with_pass_and_return(self):
        fn = FunctionDef(
            name="bad_func",
            params=[],
            return_type="int",
            body=[PassStmt(), ReturnStmt(Literal("0"))]
        )
        with self.assertRaises(TypeError):
            self.tc.check_function_def(fn)

    def test_multiple_main_functions(self):
        prog = Program(body=[
            FunctionDef(name="main", params=[], return_type="int", body=[ReturnStmt(Literal("0"))]),
            FunctionDef(name="main", params=[], return_type="int", body=[ReturnStmt(Literal("0"))])
        ])
        with self.assertRaises(TypeError):
            TypeChecker().check(prog)




# ────────────────────────────────────────────────────────────────
# Top-down tests (integration-level)
# ────────────────────────────────────────────────────────────────
class TestTypeCheckerProgramLevel(unittest.TestCase):
    def test_correct_program(self):
        """
        Program being tested:
            x: int = 42

        Expected:
            - Variable 'x' is declared as int and initialized with int literal
            - Should pass type checking
        """
        prog = Program(body=[
            VarDecl(name="x", declared_type="int", value=Literal(raw="42"))
        ])
        TypeChecker().check(prog)

    def test_type_mismatch_in_program(self):
        """
        Program being tested:
            x: str = 42

        Error:
            - Literal '42' is an int
            - Declared type is str → mismatch

        Expected:
            - Should raise TypeError
        """
        prog = Program(body=[
            VarDecl(name="x", declared_type="str", value=Literal(raw="42"))
        ])
        with self.assertRaises(TypeError):
            TypeChecker().check(prog)

    def test_call_expr_in_program_valid(self):
        """
        Program being tested:
            x: int = 1
            y: int = inc(x)

        Assumptions:
            - x is declared as int
            - inc is a function: (int) -> int

        Expected:
            - Should type check successfully.
        """
        prog = Program(body=[
            VarDecl(name="x", declared_type="int", value=Literal("1")),
            VarDecl(name="y", declared_type="int", value=CallExpr(
                func=Identifier("inc"),
                args=[Identifier("x")]
            ))
        ])
        checker = TypeChecker()
        checker.env["x"] = "int"
        checker.functions["inc"] = (["int"], "int")
        checker.check(prog)

    def test_call_expr_in_program_type_mismatch(self):
        """
        Program being tested:
            s: str = inc(3.14)

        Assumptions:
            - inc is a function: (int) -> int

        Error:
            - Argument 3.14 is float, but inc expects int
            - Assigned to a variable of type str, which is also incorrect

        Expected:
            - Should raise TypeError
        """
        prog = Program(body=[
            VarDecl(name="s", declared_type="str", value=CallExpr(
                func=Identifier("inc"),
                args=[Literal("3.14")]
            ))
        ])
        checker = TypeChecker()
        checker.functions["inc"] = (["int"], "int")
        with self.assertRaises(TypeError):
            checker.check(prog)

    def test_function_def_and_call(self):
        """
        Program being tested:
            def double(n: int) -> int:
                return n + n

            result: int = double(5)

        Expected:
            - Function 'double' registered and type-checked
            - Function call type-checked
        """
        prog = Program(body=[
            FunctionDef(
                name="double",
                params=[Parameter("n", "int")],
                return_type="int",
                body=[
                    ReturnStmt(BinOp(Identifier("n"), "+", Identifier("n")))
                ]
            ),
            VarDecl(
                name="result",
                declared_type="int",
                value=CallExpr(Identifier("double"), [Literal("5")])
            )
        ])
        TypeChecker().check(prog)

    def test_assignment_in_function(self):
        """
        Program:
            def main() -> int:
                x: int = 10
                x = 20
                return x

        Expected:
            - VarDecl introduces 'x' as int
            - Assignment must match that type
        """
        prog = Program(body=[
            FunctionDef(
                name="main",
                params=[],
                return_type="int",
                body=[
                    VarDecl("x", "int", Literal("10")),
                    AssignStmt(Identifier("x"), Literal("20")),
                    ReturnStmt(Identifier("x"))
                ]
            )
        ])
        TypeChecker().check(prog)

    def test_augmented_assignment_in_function(self):
        """
        Program:
            def bump() -> int:
                x: int = 0
                x += 1
                return x

        Expected:
            - Variable 'x' is declared as int
            - Augmented assignment matches type
        """
        prog = Program(body=[
            FunctionDef(
                name="bump",
                params=[],
                return_type="int",
                body=[
                    VarDecl("x", "int", Literal("0")),
                    AugAssignStmt(Identifier("x"), "+=", Literal("1")),
                    ReturnStmt(Identifier("x"))
                ]
            )
        ])
        TypeChecker().check(prog)

    def test_if_stmt_in_function(self):
        """
        Program:
            def check(val: int) -> int:
                if val > 0:
                    return 1
                else:
                    return 0

        Expected:
            - Condition is a bool-returning expression
            - Both branches return int
        """
        prog = Program(body=[
            FunctionDef(
                name="check",
                params=[Parameter("val", "int")],
                return_type="int",
                body=[
                    IfStmt(branches=[
                        IfBranch(
                            condition=BinOp(Identifier("val"), ">", Literal("0")),
                            body=[ReturnStmt(Literal("1"))]
                        ),
                        IfBranch(
                            condition=None,
                            body=[ReturnStmt(Literal("0"))]
                        )
                    ])
                ]
            )
        ])
        TypeChecker().check(prog)

    def test_while_loop_in_function(self):
        """
        Program:
            def loop() -> int:
                x: int = 0
                while x < 5:
                    x += 1
                return x

        Expected:
            - 'x < 5' → bool
            - body executes in loop context
        """
        prog = Program(body=[
            FunctionDef(
                name="loop",
                params=[],
                return_type="int",
                body=[
                    VarDecl("x", "int", Literal("0")),
                    WhileStmt(
                        condition=BinOp(Identifier("x"), "<", Literal("5")),
                        body=[
                            AugAssignStmt(Identifier("x"), "+=", Literal("1"))
                        ]
                    ),
                    ReturnStmt(Identifier("x"))
                ]
            )
        ])
        TypeChecker().check(prog)

    def test_for_loop_in_function(self):
        """
        Program:
            def sum(values: list[int]) -> int:
                total: int = 0
                for x in values:
                    total += x
                return total

        Expected:
            - values is list[int]
            - x is int
            - AugAssignStmt is valid
        """
        prog = Program(body=[
            FunctionDef(
                name="sum",
                params=[Parameter("values", "list[int]")],
                return_type="int",
                body=[
                    VarDecl("total", "int", Literal("0")),
                    ForStmt(
                        var_name="x",
                        iterable=Identifier("values"),
                        body=[
                            AugAssignStmt(Identifier("total"), "+=", Identifier("x"))
                        ]
                    ),
                    ReturnStmt(Identifier("total"))
                ]
            )
        ])
        TypeChecker().check(prog)

    def test_class_def_and_usage(self):
        """
        Program:
            class Counter:
                count: int = 0

                def tick(self) -> None:
                    self.count += 1

        Expected:
            - Class with int field
            - Method updates that field via 'self.count'
        """
        prog = Program(body=[
            ClassDef(
                name="Counter",
                base=None,
                fields=[VarDecl("count", "int", Literal("0"))],
                methods=[
                    FunctionDef(
                        name="tick",
                        params=[Parameter("self", "Counter")],
                        return_type="None",
                        body=[
                            AugAssignStmt(
                                target=AttributeExpr(Identifier("self"), "count"),
                                op="+=",
                                value=Literal("1")
                            )
                        ]
                    )
                ]
            )
        ])
        TypeChecker().check(prog)

    def test_list_expr_in_function(self):
        """
        Program:
            def make_list() -> list[int]:
                nums: list[int] = [1, 2, 3]
                return nums

        Expected:
            - All list elements are int
            - Variable declared as list[int]
            - Return matches function return type
        """
        prog = Program(body=[
            FunctionDef(
                name="make_list",
                params=[],
                return_type="list[int]",
                body=[
                    VarDecl(
                        name="nums",
                        declared_type="list[int]",
                        value=ListExpr(elements=[
                            Literal("1"), Literal("2"), Literal("3")
                        ])
                    ),
                    ReturnStmt(Identifier("nums"))
                ]
            )
        ])
        TypeChecker().check(prog)

    def test_dict_expr_in_function(self):
        """
        Program:
            def make_dict() -> dict[str, int]:
                scores: dict[str, int] = {"math": 90, "english": 95}
                return scores

        Expected:
            - All keys are str, values are int
            - Variable declared as dict[str, int]
            - Return matches function return type
        """
        prog = Program(body=[
            FunctionDef(
                name="make_dict",
                params=[],
                return_type="dict[str, int]",
                body=[
                    VarDecl(
                        name="scores",
                        declared_type="dict[str, int]",
                        value=DictExpr(
                            keys=[Literal('"math"'), Literal('"english"')],
                            values=[Literal("90"), Literal("95")]
                        )
                    ),
                    ReturnStmt(Identifier("scores"))
                ]
            )
        ])
        TypeChecker().check(prog)

    def test_assert_stmt_in_function(self):
        """
        Program:
            def check_positive(x: int) -> int:
                assert x > 0
                return x

        Expected:
            - Assert condition is bool
        """
        prog = Program(body=[
            FunctionDef(
                name="check_positive",
                params=[Parameter("x", "int")],
                return_type="int",
                body=[
                    AssertStmt(condition=BinOp(Identifier("x"), ">", Literal("0"))),
                    ReturnStmt(Identifier("x"))
                ]
            )
        ])
        TypeChecker().check(prog)

    def test_raise_stmt_in_function(self):
        """
        Program:
            def crash() -> None:
                raise "Something went wrong"

        Expected:
            - Raises a string (acceptable for now)
            - Should type-check
        """
        prog = Program(body=[
            FunctionDef(
                name="crash",
                params=[],
                return_type="None",
                body=[
                    RaiseStmt(exception=Literal('"Something went wrong"'))
                ]
            )
        ])
        TypeChecker().check(prog)

    def test_global_stmt_in_function_body(self):
        """
        Program:
            def set_globals() -> None:
                global x, y
                x: int = 1
                y: int = 2

        Expected:
            - 'global x, y' is allowed
            - VarDecls are local declarations here
        """
        prog = Program(body=[
            FunctionDef(
                name="set_globals",
                params=[],
                return_type="None",
                body=[
                    GlobalStmt(names=["x", "y"]),
                    VarDecl("x", "int", Literal("1")),
                    VarDecl("y", "int", Literal("2"))
                ]
            )
        ])
        TypeChecker().check(prog)

    def test_try_except_in_function(self):
        """
        Program:
            class CustomError:
                pass

            def risky() -> None:
                try:
                    assert True
                except CustomError as e:
                    pass

        Expected:
            - Class CustomError is known
            - Except block binds alias and body type-checks
        """
        prog = Program(body=[
            ClassDef(
                name="CustomError",
                base=None,
                fields=[],
                methods=[]
            ),
            FunctionDef(
                name="risky",
                params=[],
                return_type="None",
                body=[
                    TryExceptStmt(
                        try_body=[AssertStmt(condition=Literal("True"))],
                        except_blocks=[
                            ExceptBlock(
                                exc_type="CustomError",
                                alias="e",
                                body=[PassStmt()]
                            )
                        ]
                    )
                ]
            )
        ])
        TypeChecker().check(prog)
