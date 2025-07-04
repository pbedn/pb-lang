from sys import exception
import unittest

from type_checker import TypeChecker, TypeError, ModuleSymbol
from lang_ast import (
    Program,
    VarDecl,
    Literal,
    StringLiteral,
    FStringLiteral,
    FStringText,
    FStringExpr,
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
    SetExpr,
    DictExpr,
    AssertStmt,
    RaiseStmt,
    GlobalStmt,
    TryExceptStmt,
    ExceptBlock,
    ExprStmt,
    ImportStmt,
    ImportFromStmt,
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
            self.tc.check_expr(Identifier(name="z", inferred_type="str"))

    def test_binop_add_ints(self):
        expr = BinOp(Literal("1"), "+", Literal("2"))
        self.assertEqual(self.tc.check_expr(expr), "int")

    def test_binop_add_floats(self):
        expr = BinOp(Literal("1.0"), "+", Literal("2.0"))
        self.assertEqual(self.tc.check_expr(expr), "float")

    def test_binop_add_int_and_float(self):
        expr = BinOp(Literal("1"), "+", Literal("2.0"))
        self.assertEqual(self.tc.check_expr(expr), "float")

    def test_binop_add_bool_and_int(self):
        expr = BinOp(Literal("True"), "+", Literal("7"))
        self.assertEqual(self.tc.check_expr(expr), "int")

    def test_binop_add_bool_and_float(self):
        expr = BinOp(Literal("False"), "+", Literal("1.0"))
        self.assertEqual(self.tc.check_expr(expr), "float")

    def test_binop_mul_int_and_float(self):
        expr = BinOp(Literal("1"), "*", Literal("2.0"))
        self.assertEqual(self.tc.check_expr(expr), "float")

    def test_binop_mul_int_and_bool(self):
        expr = BinOp(Literal("1"), "*", Literal("False"))
        self.assertEqual(self.tc.check_expr(expr), "int")

    def test_binop_add_incompatible_types_raises(self):
        expr = BinOp(Literal('"hello"'), "+", Literal("3"))
        with self.assertRaises(TypeError):
            self.tc.check_expr(expr)

    def test_binop_eq(self):
        expr = BinOp(Literal("42"), "==", Literal("42"))
        self.assertEqual(self.tc.check_expr(expr), "bool")

    def test_binop_lt(self):
        expr = BinOp(Literal("1"), "<", Literal("2"))
        self.assertEqual(self.tc.check_expr(expr), "bool")

    def test_binop_lte(self):
        expr = BinOp(Literal("1"), "<=", Literal("2"))
        self.assertEqual(self.tc.check_expr(expr), "bool")

    def test_binop_gt(self):
        expr = BinOp(Literal("2"), ">", Literal("1"))
        self.assertEqual(self.tc.check_expr(expr), "bool")

    def test_binop_gte(self):
        expr = BinOp(Literal("2"), ">=", Literal("1"))
        self.assertEqual(self.tc.check_expr(expr), "bool")

    def test_chained_comparison_type(self):
        expr = BinOp(BinOp(Literal("1"), "<", Literal("2")), "and", BinOp(Literal("2"), "<", Literal("3")))
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
        self.tc.functions["inc"] = (["int"], "int", 1)
        call = CallExpr(func=Identifier("inc"), args=[Literal("1")])
        self.assertEqual(self.tc.check_expr(call), "int")

    def test_call_expr_wrong_arg_count(self):
        self.tc.functions["f"] = (["int", "int"], "int", 2)
        call = CallExpr(func=Identifier("f"), args=[Literal("1")])
        with self.assertRaises(TypeError):
            self.tc.check_expr(call)

    def test_call_expr_wrong_arg_type(self):
        self.tc.functions["f"] = (["int"], "int", 1)
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
        fn = FunctionDef(name='main', params=[], body=[], return_type="")
        self.tc.check_return_stmt(stmt, fn)  # should not raise

    def test_return_stmt_mismatch(self):
        self.tc.current_return_type = "int"
        stmt = ReturnStmt(value=Literal("3.14"))
        fn = FunctionDef(name='main', params=[], body=[], return_type="")
        with self.assertRaises(TypeError):
            self.tc.check_return_stmt(stmt, fn)

    def test_return_stmt_void_expected(self):
        self.tc.current_return_type = "None"
        stmt = ReturnStmt(value=None)
        fn = FunctionDef(name='main', params=[], body=[], return_type="")
        self.tc.check_return_stmt(stmt, fn)  # OK

    def test_return_stmt_nonvoid_in_void_function(self):
        self.tc.current_return_type = "None"
        stmt = ReturnStmt(value=Literal("1"))
        fn = FunctionDef(name='main', params=[], body=[], return_type="")
        with self.assertRaises(TypeError):
            self.tc.check_return_stmt(stmt, fn)

    def test_return_stmt_outside_function(self):
        self.tc.current_return_type = None
        stmt = ReturnStmt(value=Literal("42"))
        fn = FunctionDef(name='main', params=[], body=[], return_type="")
        with self.assertRaises(TypeError):
            self.tc.check_return_stmt(stmt, fn)

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
        self.tc.check_assign_stmt(stmt)

    def test_assign_stmt_mismatch(self):
        self.tc.env["x"] = "int"
        stmt = AssignStmt(target=Identifier("x"), value=Literal("3.14"))
        with self.assertRaises(TypeError):
            self.tc.check_assign_stmt(stmt)

    def test_assign_stmt_undefined(self):
        stmt = AssignStmt(target=Identifier("x"), value=Literal("42"))
        with self.assertRaises(TypeError):
            self.tc.check_assign_stmt(stmt)

    def test_assign_stmt_list_int_set(self):
        self.tc.env["arr_int"] = "list[int]"
        # Simulate: arr_int[0] = 1
        stmt = AssignStmt(target=IndexExpr(Identifier("arr_int", inferred_type='list[int]'), Literal("0")), value=Literal("1"))
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
        """
        class C:
            def __init__(self) -> None:
                self.x = 42
        """
        cls = ClassDef(
            name="C",
            base=None,
            fields=[],  # no class attributes
            methods=[
                FunctionDef(
                    name="__init__",
                    params=[Parameter("self", None)],
                    return_type="None",
                    body=[
                        AssignStmt(AttributeExpr(Identifier("self"), "x"), Literal("42"))
                    ]
                )
            ]
        )
        self.tc.check_class_def(cls)
        self.assertEqual(self.tc.instance_fields["C"]["x"], "int")

    def test_class_def_with_base(self):
        self.tc.known_classes.add("Base")
        self.tc.instance_fields["Base"] = {}
        self.tc.class_attrs["Base"] = {}
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
        self.tc.known_classes.add("Point")
        self.tc.instance_fields["Point"] = {"x": "int", "y": "int"}

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
        self.tc.instance_fields["Point"] = {"x": "int"}
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

    def test_list_expr_empty_with_type_hint(self):
        expr = ListExpr(elements=[])
        self.assertEqual(self.tc.check_expr(expr, expected_type="list[int]"), "list[int]")

    def test_set_expr_valid(self):
        expr = SetExpr(elements=[Literal("1"), Literal("2")])
        self.assertEqual(self.tc.check_expr(expr), "set[int]")

    def test_set_expr_empty_with_hint(self):
        expr = SetExpr(elements=[])
        self.assertEqual(self.tc.check_expr(expr, expected_type="set[int]"), "set[int]")

    def test_var_decl_empty_list_with_annotation(self):
        decl = VarDecl(name="a", declared_type="list[int]", value=ListExpr(elements=[]))
        self.tc.check_var_decl(decl)  # should not raise
        self.assertEqual(self.tc.env["a"], "list[int]")

    def test_var_decl_empty_list_without_annotation(self):
        decl = VarDecl(name="a", declared_type=None, value=ListExpr(elements=[]))
        with self.assertRaises(TypeError):
            self.tc.check_var_decl(decl)

    def test_var_decl_optional_accepts_none(self):
        decl = VarDecl(name="x", declared_type="int | None", value=Literal("None"))
        self.tc.check_var_decl(decl)
        self.assertEqual(self.tc.env["x"], "int | None")

    def test_var_decl_optional_accepts_value(self):
        decl = VarDecl(name="y", declared_type="int | None", value=Literal("1"))
        self.tc.check_var_decl(decl)
        self.assertEqual(self.tc.env["y"], "int | None")

    def test_var_decl_optional_rejects_wrong(self):
        decl = VarDecl(name="z", declared_type="int | None", value=StringLiteral("bad"))
        with self.assertRaises(TypeError):
            self.tc.check_var_decl(decl)

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
        self.tc.global_env["x"] = "int"
        self.tc.global_env["y"] = "int"
        stmt = GlobalStmt(names=["x", "y"])
        self.tc.check_global_stmt(stmt)

    def test_global_stmt_outside_function(self):
        self.tc.current_return_type = None
        stmt = GlobalStmt(names=["x"])
        with self.assertRaises(TypeError):
            self.tc.check_global_stmt(stmt)

    def test_try_except_valid(self):
        self.tc.known_classes.add("Error")
        self.tc.instance_fields["Error"] = {}
        self.tc.class_attrs["Error"] = {}
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

    def test_call_expr_with_default_arg(self):
        self.tc.functions["increment"] = (["int", "int"], "int", 1)
        call1 = CallExpr(Identifier("increment"), [Literal("5")])
        call2 = CallExpr(Identifier("increment"), [Literal("5"), Literal("2")])
        self.assertEqual(self.tc.check_expr(call1), "int")
        self.assertEqual(self.tc.check_expr(call2), "int")

    def test_call_expr_missing_required_arg(self):
        self.tc.functions["increment"] = (["int", "int"], "int", 1)
        call = CallExpr(Identifier("increment"), [])
        with self.assertRaises(TypeError):
            self.tc.check_expr(call)

    def test_call_expr_too_many_args(self):
        self.tc.functions["increment"] = (["int", "int"], "int", 1)
        call = CallExpr(Identifier("increment"), [Literal("1"), Literal("2"), Literal("3")])
        with self.assertRaises(TypeError):
            self.tc.check_expr(call)

    def test_call_range_1_arg(self):
        self.tc.functions["range"] = (["int", "int"], "list[int]", 1)
        call = CallExpr(Identifier("range"), [Literal("5")])
        self.assertEqual(self.tc.check_expr(call), "list[int]")

    def test_call_range_2_args(self):
        self.tc.functions["range"] = (["int", "int"], "list[int]", 1)
        call = CallExpr(Identifier("range"), [Literal("1"), Literal("5")])
        self.assertEqual(self.tc.check_expr(call), "list[int]")

    def test_call_range_too_few_args(self):
        self.tc.functions["range"] = (["int", "int"], "list[int]", 1)
        call = CallExpr(Identifier("range"), [])
        with self.assertRaises(TypeError):
            self.tc.check_expr(call)

    def test_call_range_too_many_args(self):
        self.tc.functions["range"] = (["int", "int"], "list[int]", 1)
        call = CallExpr(Identifier("range"), [Literal("1"), Literal("2"), Literal("3")])
        with self.assertRaises(TypeError):
            self.tc.check_expr(call)

    def test_attribute_expr_class_attr_static_access(self):
        # class Player:
        #     species: str = "Human"
        #
        # Player.species  # static access

        self.tc.class_attrs["Player"] = {"species": "str"}
        expr = AttributeExpr(Identifier("Player"), "species")
        typ = self.tc.check_expr(expr)
        self.assertEqual(typ, "str")

    def test_attribute_expr_class_attr_not_found(self):
        # class Player:
        #     species: str = "Human"
        #
        # Player.hp  # invalid: hp not defined as class attribute

        self.tc.class_attrs["Player"] = {"species": "str"}
        expr = AttributeExpr(Identifier("Player"), "hp")
        with self.assertRaises(TypeError):
            self.tc.check_expr(expr)

    def test_attribute_expr_class_not_found(self):
        # UnknownClass.foo  # invalid: UnknownClass is not defined

        expr = AttributeExpr(Identifier("UnknownClass"), "foo")
        with self.assertRaises(TypeError):
            self.tc.check_expr(expr)

    def test_instance_accesses_class_attr(self):
        self.tc.env["p"] = "Player"
        self.tc.known_classes.add("Player")
        self.tc.instance_fields["Player"] = {}
        self.tc.class_attrs["Player"] = {"name": "str"}
        expr = AttributeExpr(Identifier("p"), "name")
        typ = self.tc.check_expr(expr)
        self.assertEqual(typ, "str")

    def test_subclass_inherits_class_attr(self):
        self.tc.env["m"] = "Mage"
        self.tc.known_classes.update({"Player", "Mage"})
        self.tc.class_bases["Mage"] = "Player"
        self.tc.instance_fields["Player"] = {}
        self.tc.instance_fields["Mage"] = {}
        self.tc.class_attrs["Player"] = {"name": "str"}
        self.tc.class_attrs["Mage"] = {"name": "str"}

        expr1 = AttributeExpr(Identifier("Mage"), "name")
        expr2 = AttributeExpr(Identifier("m"), "name")
        self.assertEqual(self.tc.check_expr(expr1), "str")
        self.assertEqual(self.tc.check_expr(expr2), "str")

    def test_is_subclass(self):
        self.tc.known_classes.update({"Player", "Mage", "Wizard", "object"})
        self.tc.class_bases["Mage"] = "Player"
        self.tc.class_bases["Wizard"] = "Mage"

        # Exact matches
        self.assertTrue(self.tc.is_subclass("Player", "Player"))
        self.assertTrue(self.tc.is_subclass("Mage", "Mage"))

        # Direct inheritance
        self.assertTrue(self.tc.is_subclass("Mage", "Player"))

        # Transitive inheritance
        self.assertTrue(self.tc.is_subclass("Wizard", "Player"))
        self.assertTrue(self.tc.is_subclass("Wizard", "Mage"))

        # Negative cases
        self.assertFalse(self.tc.is_subclass("Player", "Mage"))
        self.assertFalse(self.tc.is_subclass("object", "Player"))
        self.assertFalse(self.tc.is_subclass("Mage", "Wizard"))

    def test_attribute_expr_static_method_call_superclass_invalid(self):
        self.tc.known_classes.update({"A", "B", "C"})
        self.tc.class_bases["B"] = "A"
        self.tc.methods["C"] = {
            "do": (["B"], "None", 1)
        }
        self.tc.env["A"] = ClassDef("A", "", fields={}, methods={})
        expr = CallExpr(
            func=AttributeExpr(obj=Identifier("C"), attr="do"),
            args=[CallExpr(func=Identifier("A"), args=[])]
        )
        with self.assertRaises(TypeError):
            self.tc.check_expr(expr)

    def test_attribute_expr_static_method_call_with_incompatible_type(self):
        self.tc.env["Player"] = "Player"
        self.tc.methods["Player"] = {
            "heal": (["int"], "None", 1)
        }
        expr = CallExpr(
            func=AttributeExpr(obj=Identifier("Player"), attr="heal"),
            args=[Literal('"abc"')]
        )
        with self.assertRaises(TypeError):
            self.tc.check_expr(expr)

    def test_check_expr_fstring_literal(self):
        lit = FStringLiteral(parts=[
            FStringText("Value is "),
            FStringExpr(expr=Literal("42"))
        ])
        typ = self.tc.check_expr(lit)

        # Expected: inferred type is always "str"
        self.assertEqual(typ, "str")

        # Additionally: ensure sub-expression is type-checked
        self.assertEqual(lit.parts[1].expr.inferred_type, "int")
        # And the FStringExpr itself gets the propagated type
        self.assertEqual(lit.parts[1].inferred_type, "int")

    def test_print_int(self):
        call = CallExpr(func=Identifier("print"), args=[Literal("42")])
        self.assertEqual(self.tc.check_expr(call), "None")

    def test_print_list(self):
        call = CallExpr(
            func=Identifier("print"),
            args=[ListExpr(elements=[Literal("1"), Literal("2")])]
        )
        self.tc.check_expr(call)

    def test_binop_or_bool(self):
        expr = BinOp(Literal("True"), "or", Literal("False"))
        self.assertEqual(self.tc.check_expr(expr), "bool")

    def test_binop_or_nonbool(self):
        expr = BinOp(Literal("1"), "or", Literal("0"))
        with self.assertRaises(TypeError):
            self.tc.check_expr(expr)

    def test_binop_unknown_op(self):
        expr = BinOp(Literal("1"), "^", Literal("2"))
        with self.assertRaises(TypeError):
            self.tc.check_expr(expr)

    def test_unary_unknown_op(self):
        expr = UnaryOp("~", Literal("1"))
        with self.assertRaises(TypeError):
            self.tc.check_expr(expr)

    def test_call_expr_subclass_arg(self):
        # f(Player) registered, but we pass a Mage
        self.tc.known_classes.update({"Player", "Mage"})
        self.tc.class_bases["Mage"] = "Player"

        self.tc.env["m"] = "Mage"
        self.tc.functions["f"] = (["Player"], "None", 1)
        call = CallExpr(func=Identifier("f"), args=[Identifier("m")])
        self.assertEqual(self.tc.check_expr(call), "None")

    def test_call_static_method(self):
        # class A { def m(self) -> int: ... }
        self.tc.class_attrs["A"] = {}
        self.tc.methods["A"] = {"m": (["A"], "int", 1)}
        self.tc.env["self"] = "A"
        call = CallExpr(func=AttributeExpr(Identifier("A"), "m"), args=[Identifier("self")])
        self.assertEqual(self.tc.check_expr(call), "int")

    def test_check_function_def_default_param_order(self):
        fn = FunctionDef(
            name="bad",
            params=[
              Parameter("x", "int", default=Literal("1")),
              Parameter("y", "int")
            ],
            return_type="None",
            body=[]
        )
        with self.assertRaises(TypeError):
            self.tc.check_function_def(fn)

    def test_global_stmt_allows_assignment(self):
        self.tc.global_env["x"] = "int"
        self.tc.current_return_type = "None"
        self.tc.check_global_stmt(GlobalStmt(names=["x"]))
        stmt = AssignStmt(Identifier("x"), Literal("5"))
        self.tc.check_assign_stmt(stmt)

    def test_function_no_return(self):
        fn = FunctionDef(name="f", params=[], return_type="int", body=[])
        with self.assertRaises(TypeError):
            self.tc.check_function_def(fn)

    def test_class_instantiation_no_args(self):
        # class C: def __init__(self) -> None: ...
        self.tc.known_classes.add("C")
        self.tc.methods["C"] = {
            "__init__": (["C"], "None", 1)
        }
        expr = CallExpr(Identifier("C"), [])
        self.assertEqual(self.tc.check_expr(expr), "C")

    def test_class_instantiation_missing_required(self):
        # class D: def __init__(self, x: int) -> None: ...
        self.tc.known_classes.add("D")
        self.tc.methods["D"] = {
            "__init__": (["D", "int"], "None", 2)
        }
        expr = CallExpr(Identifier("D"), [])
        with self.assertRaises(TypeError):
            self.tc.check_expr(expr)

    def test_class_instantiation_too_many_args(self):
        # class E: def __init__(self, x: int) -> None: ...
        self.tc.known_classes.add("E")
        self.tc.methods["E"] = {
            "__init__": (["E", "int"], "None", 2)
        }
        expr = CallExpr(Identifier("E"), [Literal("1"), Literal("2")])
        with self.assertRaises(TypeError):
            self.tc.check_expr(expr)

    def test_class_instantiation_wrong_arg_type(self):
        # class F: def __init__(self, x: int) -> None: ...
        self.tc.known_classes.add("F")
        self.tc.methods["F"] = {
            "__init__": (["F", "int"], "None", 2)
        }
        expr = CallExpr(Identifier("F"), [Literal("'hello'")])
        with self.assertRaises(TypeError):
            self.tc.check_expr(expr)

    def test_class_instantiation_subclass_arg(self):
        # class G: def __init__(self, p: Parent) -> None: ...
        self.tc.known_classes.update({"Parent", "Child"})
        self.tc.class_bases["Child"] = "Parent"
        self.tc.methods["G"] = {
            "__init__": (["G", "Parent"], "None", 2)
        }
        # simulate variable c: Child
        self.tc.env["c"] = "Child"
        expr = CallExpr(Identifier("G"), [Identifier("c")])
        self.assertEqual(self.tc.check_expr(expr), "G")

    def test_top_level_var_decl_goes_to_global_env(self):
        # Simulate top-level declaration
        self.tc.current_return_type = None
        decl = VarDecl(name="g", declared_type="int", value=Literal("42"))
        self.tc.check_var_decl(decl)
        self.assertIn("g", self.tc.global_env)
        self.assertEqual(self.tc.global_env["g"], "int")

    def test_global_stmt_imports_variable_to_local_env(self):
        self.tc.global_env["counter"] = "int"
        self.tc.current_return_type = "int"
        stmt = GlobalStmt(names=["counter"])
        self.tc.check_global_stmt(stmt)
        self.assertIn("counter", self.tc.env)
        self.assertEqual(self.tc.env["counter"], "int")

    def test_global_stmt_rejects_undeclared_variable(self):
        self.tc.current_return_type = "int"
        stmt = GlobalStmt(names=["missing"])
        with self.assertRaises(TypeError):
            self.tc.check_global_stmt(stmt)

    def test_assignment_with_numeric_promotion(self):
        stmt1 = VarDecl(name="x", declared_type="float", value=Literal(raw="1.0"))
        stmt2 = VarDecl(name="y", declared_type="int", value=Literal(raw="1"))
        self.tc.check_var_decl(stmt1)
        self.tc.check_var_decl(stmt2)

    def test_assignment_with_invalid_numeric_narrowing(self):
        stmt = VarDecl(name="x", declared_type="int", value=Literal(raw="3.14"))
        with self.assertRaises(TypeError):
            self.tc.check_var_decl(stmt)

    def test_attribute_access_on_module(self):
        # Simulate: import foo as bar
        import_stmt = ImportStmt(module=["foo"], alias="bar")
        self.tc.check_stmt(import_stmt)

        # Simulate: bar.some_func
        self.tc.modules["bar"] = ModuleSymbol("bar", None, exports={"some_func": "function"})
        expr = AttributeExpr(obj=Identifier("bar"), attr="some_func")
        result_type = self.tc.check_expr(expr)

        # fixme: remove placeholder
        # Expected: 'function' as a placeholder
        self.assertEqual(result_type, "function")

    def test_attribute_access_on_unknown_module(self):
        # Case 1: No import of "baz" — should raise TypeError for unknown identifier
        expr = AttributeExpr(obj=Identifier("baz"), attr="missing_func")
        with self.assertRaises(TypeError):
            self.tc.check_expr(expr)

        # Case 2: "baz" imported as a module, but export does not exist — should raise TypeError for missing export
        self.tc.modules["baz"] = ModuleSymbol("baz", None, exports={"exists": "function"})
        expr_missing = AttributeExpr(obj=Identifier("baz"), attr="not_exported")
        with self.assertRaises(TypeError):
            self.tc.check_expr(expr_missing)

    def test_assign_to_module_attribute_raises(self):
        # Simulate imported module 'mathlib'
        self.tc.modules["mathlib"] = ModuleSymbol("mathlib", None, exports={"add": "function"})
        stmt = AssignStmt(AttributeExpr(Identifier("mathlib"), "x"), Literal("42"))
        # Expected: assigning to mathlib.x should raise TypeError
        with self.assertRaises(TypeError):
            self.tc.check_assign_stmt(stmt)

    def test_aug_assign_to_module_attribute_raises(self):
        # Simulate imported module 'mathlib'
        self.tc.modules["mathlib"] = ModuleSymbol("mathlib", None, exports={"add": "function"})
        stmt = AugAssignStmt(AttributeExpr(Identifier("mathlib"), "x"), "+=", Literal("1"))
        # Expected: augmented assignment to mathlib.x should raise TypeError
        with self.assertRaises(TypeError):
            self.tc.check_aug_assign_stmt(stmt)

    def test_nested_module_attribute_access(self):
        self.tc.modules["test_import.mathlib2"] = ModuleSymbol(
            "test_import.mathlib2", None, exports={"PI": "float"}
        )
        expr = AttributeExpr(
            obj=AttributeExpr(Identifier("test_import"), "mathlib2"),
            attr="PI",
        )
        result = self.tc.check_expr(expr)
        self.assertEqual(result, "float")


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
        checker.functions["inc"] = (["int"], "int", 1)
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
        checker.functions["inc"] = (["int"], "int", 1)
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
        class Counter:
            def __init__(self) -> None:
                self.count = 0

            def inc(self) -> None:
                self.count += 1
        """
        prog = Program(body=[
            ClassDef(
                name="Counter",
                base=None,
                fields=[],  # no class attributes
                methods=[
                    FunctionDef(
                        name="__init__",
                        params=[Parameter("self", None)],
                        return_type="None",
                        body=[
                            AssignStmt(AttributeExpr(Identifier("self"), "count"), Literal("0"))
                        ]
                    ),
                    FunctionDef(
                        name="inc",
                        params=[Parameter("self", None)],
                        return_type="None",
                        body=[
                            AugAssignStmt(AttributeExpr(Identifier("self"), "count"), "+=", Literal("1"))
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
            VarDecl("x", "int", Literal("0")),  # added global var x
            VarDecl("y", "int", Literal("0")),  # added global var y
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

    def test_function_assigns_to_global_variable(self):
        """
        Program being tested:
            counter: int = 100

            def update() -> None:
                global counter
                counter = 200

        Expected:
            - Global variable 'counter' recognized
            - Assignment inside function allowed after 'global' declaration
        """
        prog = Program(body=[
            VarDecl(name="counter", declared_type="int", value=Literal("100")),
            FunctionDef(
                name="update",
                params=[],
                return_type="None",
                body=[
                    GlobalStmt(names=["counter"]),
                    AssignStmt(Identifier("counter"), Literal("200"))
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

    def test_function_with_default_argument(self):
        """
        def increment(x: int, step: int = 1) -> int:
            return x + step

        a: int = increment(5)
        b: int = increment(5, 3)
        """
        prog = Program(body=[
            FunctionDef(
                name="increment",
                params=[Parameter("x", "int"), Parameter("step", "int", default=Literal("1"))],
                return_type="int",
                body=[
                    ReturnStmt(BinOp(Identifier("x"), "+", Identifier("step")))
                ]
            ),
            VarDecl("a", "int", CallExpr(Identifier("increment"), [Literal("5")])),
            VarDecl("b", "int", CallExpr(Identifier("increment"), [Literal("5"), Literal("3")])),
        ])
        TypeChecker().check(prog)

    def test_function_with_None_return_type(self):
        """
        def add_in_place(x: int, y: int) -> None:
            x += y
        """
        prog = Program(body=[
            FunctionDef(
                name="add_in_place",
                params=[Parameter("x", "int"), Parameter("y", "int")],
                return_type="None",
                body=[
                    AugAssignStmt(Identifier("x"), "+=", Identifier("y"))
                ]
            ),
        ])
        TypeChecker().check(prog)

    def test_function_returns_int_but_expected_None_type(self):
        """
        def add_in_place(x: int, y: int) -> None:
            x += y
        """
        prog = Program(body=[
            FunctionDef(
                name="add_in_place",
                params=[Parameter("x", "int"), Parameter("y", "int")],
                return_type="None",
                body=[
                    AugAssignStmt(Identifier("x"), "+=", Identifier("y")),
                    ReturnStmt(value=Identifier(name='x', inferred_type=None), inferred_type=None)
                ]
            ),
        ])
        with self.assertRaises(TypeError) as ctx:
            TypeChecker().check(prog)
        self.assertIn("Return type mismatch: expected `None`, got `int` in function `add_in_place`", str(ctx.exception))

    def test_for_loop_with_range(self):
        """
        Program:
            def count_up() -> int:
                total: int = 0
                for i in range(5):
                    total += i
                return total

        Assumptions:
            - range(n) returns list[int]
            - 'i' is int
            - 'total += i' is valid
        """
        prog = Program(body=[
            FunctionDef(
                name="count_up",
                params=[],
                return_type="int",
                body=[
                    VarDecl("total", "int", Literal("0")),
                    ForStmt(
                        var_name="i",
                        iterable=CallExpr(Identifier("range"), [Literal("5")]),
                        body=[
                            AugAssignStmt(Identifier("total"), "+=", Identifier("i"))
                        ]
                    ),
                    ReturnStmt(Identifier("total"))
                ]
            )
        ])
        checker = TypeChecker()
        checker.functions["range"] = (["int", "int"], "list[int]", 1)
        checker.check(prog)

    def test_for_loop_with_range_two_args(self):
        """
        Program:
            def count_range() -> int:
                sum: int = 0
                for i in range(1, 4):
                    sum += i
                return sum

        Assumptions:
            - range(start, stop) is supported
        """
        prog = Program(body=[
            FunctionDef(
                name="count_range",
                params=[],
                return_type="int",
                body=[
                    VarDecl("sum", "int", Literal("0")),
                    ForStmt(
                        var_name="i",
                        iterable=CallExpr(Identifier("range"), [Literal("1"), Literal("4")]),
                        body=[
                            AugAssignStmt(Identifier("sum"), "+=", Identifier("i"))
                        ]
                    ),
                    ReturnStmt(Identifier("sum"))
                ]
            )
        ])
        checker = TypeChecker()
        checker.functions["range"] = (["int", "int"], "list[int]", 1)
        checker.check(prog)

    def test_raise_runtime_error(self):
        """
        Program:
            class Exception:
                def __init__(self, msg: str) -> None:
                    pass

            class RuntimeError(Exception):
                pass

            def crash() -> None:
                raise RuntimeError("division by zero")

        Assumptions:
            - Exception is the base for all user exceptions.
            - __init__ is inherited by RuntimeError.
        """
        prog = Program(body=[
            # Base exception
            ClassDef(
                name="Exception",
                base=None,
                fields=[],
                methods=[
                    FunctionDef(
                        name="__init__",
                        params=[
                            Parameter("self", "Exception"),
                            Parameter("msg", "str")
                        ],
                        return_type="None",
                        body=[PassStmt()]
                    )
                ]
            ),
            # RuntimeError inherits from Exception, does not declare __init__
            ClassDef(
                name="RuntimeError",
                base="Exception",
                fields=[],
                methods=[]
            ),
            # Function using raise
            FunctionDef(
                name="crash",
                params=[],
                return_type="None",
                body=[
                    RaiseStmt(
                        CallExpr(
                            Identifier("RuntimeError"),
                            [Literal('"division by zero"')]
                        )
                    )
                ]
            )
        ])
        checker = TypeChecker()
        checker.known_classes.add("RuntimeError")
        checker.instance_fields["RuntimeError"] = {}
        checker.class_attrs["RuntimeError"] = {}
        checker.functions["RuntimeError"] = (["str"], "RuntimeError", 1)
        checker.check(prog)

    def test_class_method_no_init(self):
        """
        class Counter:
            def __init__(self) -> None:
                self.count = 0

            def tick(self) -> None:
                self.count += 1
        """
        prog = Program(body=[
            ClassDef(
                name="Counter",
                base=None,
                fields=[VarDecl("name", "str", StringLiteral("Name"))],
                methods=[]
            )
        ])
        TypeChecker().check(prog)

    def test_class_method_self_inferred(self):
        """
        class Counter:
            def __init__(self) -> None:
                self.count = 0

            def tick(self) -> None:
                self.count += 1
        """
        prog = Program(body=[
            ClassDef(
                name="Counter",
                base=None,
                fields=[],  # all instance fields are set in __init__
                methods=[
                    FunctionDef(
                        name="__init__",
                        params=[Parameter("self", None)],
                        return_type="None",
                        body=[
                            AssignStmt(AttributeExpr(Identifier("self"), "count"), Literal("0"))
                        ]
                    ),
                    FunctionDef(
                        name="tick",
                        params=[Parameter("self", None)],
                        return_type="None",
                        body=[
                            AugAssignStmt(AttributeExpr(Identifier("self"), "count"), "+=", Literal("1"))
                        ]
                    )
                ]
            )
        ])
        TypeChecker().check(prog)

    def test_instance_attrs_in_init(self):
        """
        class Player:
            hp: int = 100

            def __init__(self, mp: int) -> None:
                self.hp = 100
                self.mp = mp
                self.name = "Hero"
        """
        prog = Program(body=[
            ClassDef(
                name="Player",
                base=None,
                fields=[VarDecl("hp", "int", Literal("100"))],
                methods=[
                    FunctionDef(
                        name="__init__",
                        params=[Parameter("self", None), Parameter("mp", "int")],
                        return_type="None",
                        body=[
                            AssignStmt(AttributeExpr(Identifier("self"), "hp"), Literal("100")),
                            AssignStmt(AttributeExpr(Identifier("self"), "mp"), Identifier("mp")),
                            AssignStmt(AttributeExpr(Identifier("self"), "name"), StringLiteral("Hero"))
                        ]
                    )
                ]
            )
        ])
        TypeChecker().check(prog)

    def test_redefine_instance_attr_in_method(self):
        """
        class Player:
            hp: int = 100

            def __init__(self) -> None:
                self.hp = 100

            def reset(self) -> None:
                self.hp = 0
        """
        prog = Program(body=[
            ClassDef(
                name="Player",
                base=None,
                fields=[VarDecl("hp", "int", Literal("100"))],
                methods=[
                    FunctionDef(
                        name="__init__",
                        params=[Parameter("self", None)],
                        return_type="None",
                        body=[
                            AssignStmt(AttributeExpr(Identifier("self"), "hp"), Literal("100")),
                        ]
                    ),
                    FunctionDef(
                        name="reset",
                        params=[Parameter("self", None)],
                        return_type="None",
                        body=[
                            AssignStmt(AttributeExpr(Identifier("self"), "hp"), Literal("0")),
                        ]
                    )
                ]
            )
        ])
        TypeChecker().check(prog)

    def test_assign_new_attr_outside_init_should_error(self):
        """
        class Player:
            def __init__(self) -> None:
                self.hp = 100

            def add_score(self) -> None:
                self.score = 10  # Error: not allowed outside __init__
        """
        prog = Program(body=[
            ClassDef(
                name="Player",
                base=None,
                fields=[],
                methods=[
                    FunctionDef(
                        name="__init__",
                        params=[Parameter("self", None)],
                        return_type="None",
                        body=[
                            AssignStmt(AttributeExpr(Identifier("self"), "hp"), Literal("100")),
                        ]
                    ),
                    FunctionDef(
                        name="add_score",
                        params=[Parameter("self", None)],
                        return_type="None",
                        body=[
                            AssignStmt(AttributeExpr(Identifier("self"), "score"), Literal("10")),
                        ]
                    )
                ]
            )
        ])
        with self.assertRaises(TypeError):
            TypeChecker().check(prog)

    def test_mismatched_attr_type_should_error(self):
        """
        class Player:
            def __init__(self) -> None:
                self.hp = 100

            def corrupt(self) -> None:
                self.hp = "full"  # Error: expected int
        """
        prog = Program(body=[
            ClassDef(
                name="Player",
                base=None,
                fields=[],
                methods=[
                    FunctionDef(
                        name="__init__",
                        params=[Parameter("self", None)],
                        return_type="None",
                        body=[
                            AssignStmt(AttributeExpr(Identifier("self"), "hp"), Literal("100")),
                        ]
                    ),
                    FunctionDef(
                        name="corrupt",
                        params=[Parameter("self", None)],
                        return_type="None",
                        body=[
                            AssignStmt(AttributeExpr(Identifier("self"), "hp"), StringLiteral("full")),
                        ]
                    )
                ]
            )
        ])
        with self.assertRaises(TypeError):
            TypeChecker().check(prog)

    def test_class_attrs_and_instance_attrs(self):
        """
        class Player:
            species: str = "Human"

            def __init__(self) -> None:
                self.name = "Hero"
                self.hp = 100
        """
        prog = Program(body=[
            ClassDef(
                name="Player",
                base=None,
                fields=[VarDecl("species", "str", StringLiteral("Human"))],
                methods=[
                    FunctionDef(
                        name="__init__",
                        params=[Parameter("self", None)],
                        return_type="None",
                        body=[
                            AssignStmt(AttributeExpr(Identifier("self"), "name"), StringLiteral("Hero")),
                            AssignStmt(AttributeExpr(Identifier("self"), "hp"), Literal("100")),
                        ]
                    )
                ]
            )
        ])
        TypeChecker().check(prog)

    def test_class_method_static_access(self):
        """
        class Player:
            species: str = "Human"

            def get_species_one(self) -> str:
                return Player.species
        """
        prog = Program(body=[
            ClassDef(
                name="Player",
                base=None,
                fields=[
                    VarDecl("species", "str", StringLiteral("Human"))
                ],
                methods=[
                    FunctionDef(
                        name="get_species_one",
                        params=[Parameter("self", None)],
                        return_type="str",
                        body=[
                            ReturnStmt(
                                AttributeExpr(Identifier("Player"), "species")
                            )
                        ]
                    )
                ]
            )
        ])
        TypeChecker().check(prog)

    def test_class_inheritance_explicit_init_call(self):
        """
        class Player:
            def __init__(self, hp: int, mp: int = 150) -> None:
                self.hp = hp
                self.mp = mp

        class Mage(Player):
            power: str = "fire"

            def __init__(self, hp: int) -> None:
                Player.__init__(self, hp)
                self.mp = 200
        """
        prog = Program(body=[
            ClassDef(
                name="Player",
                base=None,
                fields=[],
                methods=[
                    FunctionDef(
                        name="__init__",
                        params=[
                            Parameter("self", "Player"),
                            Parameter("hp", "int"),
                            Parameter("mp", "int", default=Literal("150"))
                        ],
                        return_type="None",
                        body=[
                            AssignStmt(AttributeExpr(Identifier("self"), "hp"), Identifier("hp")),
                            AssignStmt(AttributeExpr(Identifier("self"), "mp"), Identifier("mp")),
                        ]
                    )
                ]
            ),
            ClassDef(
                name="Mage",
                base="Player",
                fields=[
                    VarDecl("power", "str", StringLiteral("fire"))
                ],
                methods=[
                    FunctionDef(
                        name="__init__",
                        params=[
                            Parameter("self", "Mage"),
                            Parameter("hp", "int")
                        ],
                        return_type="None",
                        body=[
                            ExprStmt(CallExpr(
                                func=AttributeExpr(Identifier("Mage"), "__init__"),
                                args=[Identifier("self"), Identifier("hp")]
                            )),
                            AssignStmt(
                                AttributeExpr(Identifier("self"), "mp"),
                                Literal("200")
                            )
                        ]
                    )
                ]
            )
        ])
        TypeChecker().check(prog)

    def test_inherited_class_explicit_init_missing_args(self):
        """
        class Player:
            def __init__(self, hp: int, mp: int = 150) -> None:
                self.hp = hp
                self.mp = mp

        class Mage(Player):
            def __init__(self, hp: int) -> None:
                Player.__init__(self, hp)  # OK: mp is defaulted
                Player.__init__(self)      # Error: missing required arg 'hp'
        """
        player = ClassDef(
            name="Player",
            base=None,
            fields=[],
            methods=[
                FunctionDef(
                    name="__init__",
                    params=[
                        Parameter("self", "Player"),
                        Parameter("hp", "int"),
                        Parameter("mp", "int", default=Literal("150"))
                    ],
                    return_type="None",
                    body=[]
                )
            ]
        )

        mage = ClassDef(
            name="Mage",
            base="Player",
            fields=[],
            methods=[
                FunctionDef(
                    name="__init__",
                    params=[
                        Parameter("self", "Mage"),
                        Parameter("hp", "int")
                    ],
                    return_type="None",
                    body=[
                        # Valid call
                        ExprStmt(CallExpr(
                            func=AttributeExpr(Identifier("Player"), "__init__"),
                            args=[Identifier("self"), Identifier("hp")]
                        )),
                        # Invalid call — missing required 'hp'
                        ExprStmt(CallExpr(
                            func=AttributeExpr(Identifier("Player"), "__init__"),
                            args=[Identifier("self")]
                        ))
                    ]
                )
            ]
        )

        with self.assertRaises(TypeError):
            TypeChecker().check(Program(body=[player, mage]))

    def test_class_method_call_via_explicit_base(self):
        """
        class Player:
            def __init__(self, hp: int, mp: int = 150) -> None:
                self.hp = hp
                self.mp = mp

        class Mage(Player):
            def __init__(self, hp: int) -> None:
                Mage.__init__(self, hp)
                self.mp = 200
        """
        prog = Program(body=[
            ClassDef(
                name="Player",
                base=None,
                fields=[],
                methods=[
                    FunctionDef(
                        name="__init__",
                        params=[
                            Parameter("self", "Player"),
                            Parameter("hp", "int"),
                            Parameter("mp", "int", default=Literal("150"))
                        ],
                        return_type="None",
                        body=[
                            AssignStmt(AttributeExpr(Identifier("self"), "hp"), Identifier("hp")),
                            AssignStmt(AttributeExpr(Identifier("self"), "mp"), Identifier("mp")),
                        ]
                    )
                ]
            ),
            ClassDef(
                name="Mage",
                base="Player",
                fields=[],
                methods=[
                    FunctionDef(
                        name="__init__",
                        params=[
                            Parameter("self", "Mage"),
                            Parameter("hp", "int")
                        ],
                        return_type="None",
                        body=[
                            ExprStmt(CallExpr(
                                func=AttributeExpr(Identifier("Player"), "__init__"),
                                args=[Identifier("self"), Identifier("hp")]
                            )),
                            AssignStmt(AttributeExpr(Identifier("self"), "mp"), Literal("200"))
                        ]
                    )
                ]
            )
        ])
        TypeChecker().check(prog)

    def test_invalid_method_call_on_class(self):
        """
        class Player:
            def start(self) -> None:
                pass

        class Mage:
            def cast(self) -> None:
                Player.nonexistent(self)  # Error: no such method
        """
        prog = Program(body=[
            ClassDef(
                name="Player",
                base=None,
                fields=[],
                methods=[
                    FunctionDef(
                        name="start",
                        params=[Parameter("self", "Player")],
                        return_type="None",
                        body=[]
                    )
                ]
            ),
            ClassDef(
                name="Mage",
                base=None,
                fields=[],
                methods=[
                    FunctionDef(
                        name="cast",
                        params=[Parameter("self", "Mage")],
                        return_type="None",
                        body=[
                            ExprStmt(CallExpr(
                                func=AttributeExpr(Identifier("Player"), "nonexistent"),
                                args=[Identifier("self")]
                            ))
                        ]
                    )
                ]
            )
        ])
        with self.assertRaises(TypeError) as ctx:
            TypeChecker().check(prog)
        self.assertIn("Class 'Player' has no method 'nonexistent'", str(ctx.exception))

    def test_method_shadowing_in_subclass(self):
        """
        class Base:
            def speak(self, msg: str) -> None:
                pass

        class Child(Base):
            def speak(self, times: int) -> None:
                pass
        """
        prog = Program(body=[
            ClassDef(
                name="Base",
                base=None,
                fields=[],
                methods=[
                    FunctionDef(
                        name="speak",
                        params=[
                            Parameter("self", "Base"),
                            Parameter("msg", "str")
                        ],
                        return_type="None",
                        body=[]
                    )
                ]
            ),
            ClassDef(
                name="Child",
                base="Base",
                fields=[],
                methods=[
                    FunctionDef(
                        name="speak",
                        params=[
                            Parameter("self", "Child"),
                            Parameter("times", "int")
                        ],
                        return_type="None",
                        body=[]
                    )
                ]
            )
        ])
        TypeChecker().check(prog)

    def test_method_call_with_wrong_argument_count(self):
        """
        class A:
            def greet(self, name: str, punctuation: str = "!") -> None:
                pass

        A.greet("only_one")  # Error: missing 'self'
        """
        prog = Program(body=[
            ClassDef(
                name="A",
                base=None,
                fields=[],
                methods=[
                    FunctionDef(
                        name="greet",
                        params=[
                            Parameter("self", "A"),
                            Parameter("name", "str"),
                            Parameter("punctuation", "str", default=StringLiteral("!"))
                        ],
                        return_type="None",
                        body=[]
                    )
                ]
            ),
            # Invalid call: missing 'self'
            ExprStmt(CallExpr(
                func=AttributeExpr(Identifier("A"), "greet"),
                args=[StringLiteral("only_one")]
            ))
        ])
        with self.assertRaises(TypeError) as ctx:
            TypeChecker().check(prog)
        self.assertIn("expects between 2 and 3 arguments", str(ctx.exception))

    def test_call_on_undeclared_class(self):
        """
        Bork.__init__(self)  # Error: class 'Bork' not declared
        """
        prog = Program(body=[
            ExprStmt(CallExpr(
                func=AttributeExpr(Identifier("Bork"), "__init__"),
                args=[Identifier("self")]
            ))
        ])
        with self.assertRaises(TypeError) as ctx:
            TypeChecker().check(prog)
        self.assertIn("Class 'Bork' is not defined", str(ctx.exception))

    def test_inherited_field_access_in_subclass_method(self):
        """
        class Base:
            def __init__(self, x: int) -> None:
                self.x = x

        class Sub(Base):
            def double(self) -> int:
                return self.x * 2
        """
        prog = Program(body=[
            ClassDef(
                name="Base",
                base=None,
                fields=[],
                methods=[
                    FunctionDef(
                        name="__init__",
                        params=[
                            Parameter("self", "Base"),
                            Parameter("x", "int")
                        ],
                        return_type="None",
                        body=[
                            AssignStmt(AttributeExpr(Identifier("self"), "x"), Identifier("x"))
                        ]
                    )
                ]
            ),
            ClassDef(
                name="Sub",
                base="Base",
                fields=[],
                methods=[
                    FunctionDef(
                        name="double",
                        params=[Parameter("self", "Sub")],
                        return_type="int",
                        body=[
                            ReturnStmt(BinOp(
                                left=AttributeExpr(Identifier("self"), "x"),
                                op="*",
                                right=Literal("2")
                            ))
                        ]
                    )
                ]
            )
        ])
        TypeChecker().check(prog)

    def test_field_access_without_inheritance(self):
        """
        class A:
            def method(self) -> int:
                return self.y  # Error: 'y' not defined
        """
        prog = Program(body=[
            ClassDef(
                name="A",
                base=None,
                fields=[],
                methods=[
                    FunctionDef(
                        name="method",
                        params=[Parameter("self", "A")],
                        return_type="int",
                        body=[
                            ReturnStmt(AttributeExpr(Identifier("self"), "y"))
                        ]
                    )
                ]
            )
        ])
        with self.assertRaises(TypeError) as ctx:
            TypeChecker().check(prog)
        self.assertIn("Instance `self` for class 'A' has no attribute 'y'", str(ctx.exception))

    def test_aug_assign_on_instance_field_outside_method(self):
        """
        Program:
            def main() -> int:
                mage: Mage = Mage(100)
                mage.hp -= 10
                return 0

        Expected:
            - Valid: mage.hp -= 10 is allowed outside of a method
        """

        prog = Program(body=[
            ClassDef(
                name="Mage",
                base=None,
                fields=[],
                methods=[
                    FunctionDef(
                        name="__init__",
                        params=[Parameter("self", "Mage"), Parameter("hp", "int")],
                        return_type="None",
                        body=[
                            AssignStmt(AttributeExpr(Identifier("self"), "hp"), Identifier("hp"))
                        ]
                    )
                ]
            ),
            FunctionDef(
                name="main",
                params=[],
                return_type="int",
                body=[
                    VarDecl("mage", "Mage", CallExpr(Identifier("Mage"), [Literal("100")])),
                    AugAssignStmt(AttributeExpr(Identifier("mage"), "hp"), "-=", Literal("10")),
                    ReturnStmt(Literal("0"))
                ]
            )
        ])

        checker = TypeChecker()
        checker.check(prog)

        # Now these are valid assertions
        assert "Mage" in checker.known_classes
        assert "Mage" in checker.methods
        assert "hp" in checker.instance_fields["Mage"]

    def test_list_assignment_and_print_int_list(self):
        """
        arr: list[int] = [0, 0]
        arr[0] = 42
        print(arr)
        """
        prog = Program(body=[
            VarDecl("arr", "list[int]", ListExpr(
                elements=[Literal("0"), Literal("0")]
            )),
            AssignStmt(
                target=IndexExpr(Identifier("arr"), Literal("0")),
                value=Literal("42")
            ),
            ExprStmt(CallExpr(Identifier("print"), [Identifier("arr")]))
        ])
        TypeChecker().check(prog)

    def test_int_to_float_conversion(self):
        """
        x: int = 10
        x_float: float = float(x)
        print(x_float)
        """
        prog = Program(body=[
            VarDecl("x", "int", Literal("10")),
            VarDecl("x_float", "float", CallExpr(Identifier("float"), [Identifier("x")])),
            ExprStmt(CallExpr(Identifier("print"), [Identifier("x_float")]))
        ])
        checker = TypeChecker().check(prog)
        self.assertEqual(checker.body[0].inferred_type, "int")
        self.assertEqual(checker.body[1].inferred_type, "float")
        self.assertEqual(checker.body[1].value.inferred_type, "float")

    def test_float_to_int_conversion(self):
        """
        y: float = 1.5
        y_int: int = int(y)
        print(y_int)
        """
        prog = Program(body=[
            VarDecl("y", "float", Literal("1.5")),
            VarDecl("y_int", "int", CallExpr(Identifier("int"), [Identifier("y")])),
            ExprStmt(CallExpr(Identifier("print"), [Identifier("y_int")]))
        ])
        checker = TypeChecker().check(prog)
        self.assertEqual(checker.body[0].inferred_type, "float")
        self.assertEqual(checker.body[1].inferred_type, "int")
        self.assertEqual(checker.body[1].value.inferred_type, "int")

    def test_string_to_int_conversion(self):
        """
        a: str = "123"
        a_int: int = int(a)
        print(a_int)
        """
        prog = Program(body=[
            VarDecl("a", "str", StringLiteral("123")),
            VarDecl("a_int", "int", CallExpr(Identifier("int"), [Identifier("a")])),
            ExprStmt(CallExpr(Identifier("print"), [Identifier("a_int")]))
        ])
        checker = TypeChecker().check(prog)
        self.assertEqual(checker.body[0].inferred_type, "str")
        self.assertEqual(checker.body[1].inferred_type, "int")
        self.assertEqual(checker.body[1].value.inferred_type, "int")

    def test_string_to_float_conversion(self):
        """
        b: str = "1.23"
        b_float: float = float(b)
        print(b_float)
        """
        prog = Program(body=[
            VarDecl("b", "str", StringLiteral("1.23")),
            VarDecl("b_float", "float", CallExpr(Identifier("float"), [Identifier("b")])),
            ExprStmt(CallExpr(Identifier("print"), [Identifier("b_float")]))
        ])
        checker = TypeChecker().check(prog)
        self.assertEqual(checker.body[0].inferred_type, "str")
        self.assertEqual(checker.body[1].inferred_type, "float")
        self.assertEqual(checker.body[1].value.inferred_type, "float")

    def test_int_to_bool_conversion(self):
        """
        x: int = 0
        x_bool: bool = bool(x)
        print(x_bool)
        """
        prog = Program(body=[
            VarDecl("x", "int", Literal("0")),
            VarDecl("x_bool", "bool", CallExpr(Identifier("bool"), [Identifier("x")])),
            ExprStmt(CallExpr(Identifier("print"), [Identifier("x_bool")]))
        ])
        checker = TypeChecker().check(prog)
        self.assertEqual(checker.body[0].inferred_type, "int")
        self.assertEqual(checker.body[1].inferred_type, "bool")
        self.assertEqual(checker.body[1].value.inferred_type, "bool")

    def test_float_to_bool_conversion(self):
        """
        y: float = 0.0
        y_bool: bool = bool(y)
        print(y_bool)
        """
        prog = Program(body=[
            VarDecl("y", "float", Literal("0.0")),
            VarDecl("y_bool", "bool", CallExpr(Identifier("bool"), [Identifier("y")])),
            ExprStmt(CallExpr(Identifier("print"), [Identifier("y_bool")]))
        ])
        checker = TypeChecker().check(prog)
        self.assertEqual(checker.body[0].inferred_type, "float")
        self.assertEqual(checker.body[1].inferred_type, "bool")
        self.assertEqual(checker.body[1].value.inferred_type, "bool")

    def test_list_int_conversion(self):
        """
        arr: list[int] = [1, 2, 3]
        arr[0] = int(4.5)
        print(arr)
        """
        prog = Program(body=[
            VarDecl("arr", "list[int]", ListExpr(elements=[Literal("1"), Literal("2"), Literal("3")])),
            AssignStmt(target=IndexExpr(Identifier("arr"), Literal("0")), value=CallExpr(Identifier("int"), [Literal("4.5")])),
            ExprStmt(CallExpr(Identifier("print"), [Identifier("arr")]))
        ])
        checker = TypeChecker().check(prog)
        self.assertEqual(checker.body[0].inferred_type, "list[int]")
        self.assertEqual(checker.body[1].inferred_type, "list[int]")

    def test_list_str_conversion(self):
        """
        arr: list[str] = ["1", "2", "3"]
        arr[0] = str(4)
        print(arr)
        """
        prog = Program(body=[
            VarDecl("arr", "list[str]", ListExpr(elements=[StringLiteral("1"), StringLiteral("2"), StringLiteral("3")])),
            AssignStmt(target=IndexExpr(Identifier("arr"), Literal("0")), value=CallExpr(Identifier("str"), [Literal("4")])),
            ExprStmt(CallExpr(Identifier("print"), [Identifier("arr")]))
        ])
        checker = TypeChecker().check(prog)
        self.assertEqual(checker.body[0].inferred_type, "list[str]")
        self.assertEqual(checker.body[1].inferred_type, "list[str]")

    def test_list_float_conversion(self):
        """
        arr: list[float] = [1.1, 2.2, 3.3]
        arr[0] = float(4)
        print(arr)
        """
        prog = Program(body=[
            VarDecl("arr", "list[float]", ListExpr(elements=[Literal("1.1"), Literal("2.2"), Literal("3.3")])),
            AssignStmt(target=IndexExpr(Identifier("arr"), Literal("0")), value=CallExpr(Identifier("float"), [Literal("4")])),
            ExprStmt(CallExpr(Identifier("print"), [Identifier("arr")]))
        ])
        checker = TypeChecker().check(prog)
        self.assertEqual(checker.body[0].inferred_type, "list[float]")
        self.assertEqual(checker.body[1].inferred_type, "list[float]")

    def test_list_bool_conversion(self):
        """
        arr: list[bool] = [True, False]
        arr[0] = bool(1)
        print(arr)
        """
        prog = Program(body=[
            VarDecl("arr", "list[bool]", ListExpr(elements=[Literal("True"), Literal("False")])),
            AssignStmt(target=IndexExpr(Identifier("arr"), Literal("0")), value=CallExpr(Identifier("bool"), [Literal("1")])),
            ExprStmt(CallExpr(Identifier("print"), [Identifier("arr")]))
        ])
        checker = TypeChecker().check(prog)
        self.assertEqual(checker.body[0].inferred_type, "list[bool]")
        self.assertEqual(checker.body[1].inferred_type, "list[bool]")

    def test_open_and_file_methods(self):
        prog = Program(body=[
            VarDecl("f", "file", CallExpr(Identifier("open"), [StringLiteral("t.txt"), StringLiteral("w")])),
            ExprStmt(CallExpr(AttributeExpr(Identifier("f"), "write"), [StringLiteral("hi")])),
            ExprStmt(CallExpr(AttributeExpr(Identifier("f"), "close"), []))
        ])
        TypeChecker().check(prog)

    def test_len_builtin(self):
        prog = Program(body=[
            VarDecl("arr", "list[int]", ListExpr(elements=[Literal("1"), Literal("2"), Literal("3")])),
            VarDecl("n", "int", CallExpr(Identifier("len"), [Identifier("arr")]))
        ])
        checker = TypeChecker().check(prog)
        self.assertEqual(checker.body[1].inferred_type, "int")

    def test_list_methods(self):
        prog = Program(body=[
            VarDecl("arr", "list[int]", ListExpr(elements=[Literal("1"), Literal("2")])),
            ExprStmt(CallExpr(AttributeExpr(Identifier("arr"), "append"), [Literal("3")])),
            VarDecl("x", "int", CallExpr(AttributeExpr(Identifier("arr"), "pop"), [])),
            VarDecl("r", "bool", CallExpr(AttributeExpr(Identifier("arr"), "remove"), [Literal("1")])),
        ])
        checker = TypeChecker().check(prog)
        self.assertEqual(checker.body[1].expr.inferred_type, "None")
        self.assertEqual(checker.body[2].inferred_type, "int")
        self.assertEqual(checker.body[3].inferred_type, "bool")
