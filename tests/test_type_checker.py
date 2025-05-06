import unittest
from lang_ast import *
from parser import Parser, ParserError
from lexer import Lexer
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
        with self.assertRaises(ParserError) as ctx:
            # Simulate parsing the invalid top-level assignment
            lexer = Lexer("counter = 100")
            tokens = lexer.tokenize()
            parser = Parser(tokens)
            parser.parse()
        self.assertIn("Only function definitions and typed variable declarations are allowed", str(ctx.exception))

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
                    VarDecl("floats", "list[float]", ListExpr([Literal(1.0), Literal(2.0)])),
                    VarDecl("x", "float", IndexExpr(Identifier("floats"), Literal(0))),
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
                    AugAssignStmt(Identifier("value"), "+", Literal(2.5)),
                    ReturnStmt(Literal(0))
                ],
                return_type="int"
            )
        ])
        self.check_ok(prog)

    def test_augassign_local_ok(self):
        prog = Program([
            FunctionDef(
                name="main",
                params=[],
                body=[
                    VarDecl("x", "int", Literal(10)),
                    AugAssignStmt(Identifier("x"), "+", Literal(5)),
                    ReturnStmt(Identifier("x"))
                ],
                return_type="int"
            )
        ])
        self.check_ok(prog)

    def test_augassign_global_ok(self):
        prog = Program([
            VarDecl("counter", "int", Literal(0)),
            FunctionDef(
                name="main",
                params=[],
                body=[
                    GlobalStmt(["counter"]),
                    AugAssignStmt(Identifier("counter"), "+", Literal(1)),
                    ReturnStmt(Identifier("counter"))
                ],
                return_type="int"
            )
        ])
        self.check_ok(prog)

    def test_augassign_undeclared_should_fail(self):
        prog = Program([
            FunctionDef(
                name="main",
                params=[],
                body=[
                    AugAssignStmt(Identifier("x"), "+", Literal(5)),
                    ReturnStmt(Literal(0))
                ],
                return_type="int"
            )
        ])
        self.check_type_error(prog)

    def test_augassign_global_without_global_shadow_should_fail(self):
        prog = Program([
            VarDecl("counter", "int", Literal(0)),
            FunctionDef(
                name="main",
                params=[],
                body=[
                    VarDecl("counter", "int", Literal(5)),  # local shadow
                    AugAssignStmt(Identifier("counter"), "+", Literal(1)),
                    ReturnStmt(Identifier("counter"))
                ],
                return_type="int"
            )
        ])
        self.check_ok(prog)

    def test_augassign_global_without_global_should_fail(self):
        prog = Program([
            VarDecl("counter", "int", Literal(0)),
            FunctionDef(
                name="main",
                params=[],
                body=[
                    AugAssignStmt(Identifier("counter"), "+", Literal(1)),
                    ReturnStmt(Identifier("counter"))
                ],
                return_type="int"
            )
        ])
        self.check_type_error(prog)

    def test_augassign_type_mismatch_should_fail(self):
        prog = Program([
            FunctionDef(
                name="main",
                params=[],
                body=[
                    VarDecl("value", "int", Literal(10)),
                    AugAssignStmt(Identifier("value"), "+", Literal(2.5)),  # int += float (mismatch)
                    ReturnStmt(Identifier("value"))
                ],
                return_type="int"
            )
        ])
        self.check_type_error(prog)

    def test_augassign_global_correct_type_ok(self):
        prog = Program([
            VarDecl("total", "float", Literal(0.0)),
            FunctionDef(
                name="main",
                params=[],
                body=[
                    GlobalStmt(["total"]),
                    AugAssignStmt(Identifier("total"), "+", Literal(2.5)),
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

    def test_recursive_function_call(self):
        prog = Program([
            FunctionDef(
                name="factorial",
                params=[("n", "int")],
                body=[
                    IfStmt(
                        condition=BinOp(Identifier("n"), "==", Literal(0)),
                        then_body=[ReturnStmt(Literal(1))],
                        else_body=[
                            ReturnStmt(
                                BinOp(
                                    Identifier("n"),
                                    "*",
                                    CallExpr(Identifier("factorial"), [BinOp(Identifier("n"), "-", Literal(1))])
                                )
                            )
                        ]
                    )
                ],
                return_type="int"
            )
        ])
        self.check_ok(prog)

    def test_function_calls_another_function(self):
        prog = Program([
            FunctionDef(
                name="g",
                params=[],
                body=[ReturnStmt(Literal(123))],
                return_type="int"
            ),
            FunctionDef(
                name="f",
                params=[],
                body=[ReturnStmt(CallExpr(Identifier("g"), []))],
                return_type="int"
            )
        ])
        self.check_ok(prog)

    def test_nested_binop_expression(self):
        prog = Program([
            FunctionDef(
                name="main",
                params=[],
                body=[
                    ReturnStmt(
                        BinOp(
                            BinOp(Literal(1), "+", Literal(2)),
                            "*",
                            Literal(3)
                        )
                    )
                ],
                return_type="int"
            )
        ])
        self.check_ok(prog)

    def test_logical_nested_expressions(self):
        prog = Program([
            FunctionDef(
                name="main",
                params=[("x", "int"), ("y", "int")],
                body=[
                    ReturnStmt(
                        BinOp(
                            BinOp(Identifier("x"), ">", Literal(0)),
                            "and",
                            BinOp(Identifier("y"), "<", Literal(10))
                        )
                    )
                ],
                return_type="bool"
            )
        ])
        self.check_ok(prog)

    def test_empty_function_body_with_return_type_int_allowed(self):
        prog = Program([
            FunctionDef(
                name="noop",
                params=[],
                body=[
                    PassStmt()
                ],
                return_type="int"
            )
        ])
        self.check_ok(prog)

    def test_global_without_declaring_global_should_fail(self):
        prog = Program([
            VarDecl("counter", "int", Literal(0)),
            FunctionDef(
                name="main",
                params=[],
                body=[
                    AssignStmt("counter", BinOp(Identifier("counter"), "+", Literal(1))),
                    ReturnStmt(Identifier("counter"))
                ],
                return_type="int"
            )
        ])
        self.check_type_error(prog)

    def test_augassign_undefined_variable_should_fail(self):
        prog = Program([
            FunctionDef(
                name="main",
                params=[],
                body=[
                    AugAssignStmt("x", "+", Literal(1)),
                    ReturnStmt(Literal(0))
                ],
                return_type="int"
            )
        ])
        self.check_type_error(prog)

    def test_class_with_field_and_valid_method(self):
        """
        Check that the class is correctly type-checked.

        class Player:
            hp: int = 100

            def heal(self, amount: int):
                self.hp += amount
        """
        prog = Program([
            ClassDef(
                name="Player",
                base=None,
                fields=[
                    VarDecl("hp", "int", Literal(100))
                ],
                methods=[
                    FunctionDef(
                        name="heal",
                        params=[("self", "Player"), ("amount", "int")],
                        body=[
                            AugAssignStmt(
                                AttributeExpr(Identifier("self"), "hp"),
                                "+",
                                Identifier("amount")
                            )
                        ],
                        return_type=None
                    )
                ]
            )
        ])
        self.check_ok(prog)

    def test_class_field_type_mismatch_should_fail(self):
        """
        Detects a mismatch between declared type and value.

        class Player:
            hp: int = "oops"
        """
        prog = Program([
            ClassDef(
                name="Player",
                base=None,
                fields=[
                    VarDecl("hp", "int", Literal("oops"))
                ],
                methods=[]
            )
        ])
        self.check_type_error(prog)

    def test_class_accessing_nonexistent_field_should_fail(self):
        """
        Ensure accessing a non-existent field raises an error.

        class Player:
            hp: int = 100

            def debug(self):
                print(self.mana)
        """
        prog = Program([
            ClassDef(
                name="Player",
                base=None,
                fields=[
                    VarDecl("hp", "int", Literal(100))
                ],
                methods=[
                    FunctionDef(
                        name="debug",
                        params=[("self", "Player")],
                        body=[
                            CallExpr(
                                Identifier("print"),
                                [AttributeExpr(Identifier("self"), "mana")]
                            )
                        ],
                        return_type=None
                    )
                ]
            )
        ])
        self.check_type_error(prog)

    def test_class_method_param_type_mismatch_should_fail(self):
        """
        amount is a str but used in self.hp += amount (should fail).

        class Player:
            hp: int = 100

            def heal(self, amount: str):
                self.hp += amount
        """
        prog = Program([
            ClassDef(
                name="Player",
                base=None,
                fields=[
                    VarDecl("hp", "int", Literal(100))
                ],
                methods=[
                    FunctionDef(
                        name="heal",
                        params=[("self", "Player"), ("amount", "str")],
                        body=[
                            AugAssignStmt(
                                AttributeExpr(Identifier("self"), "hp"),
                                "+",
                                Identifier("amount")
                            )
                        ],
                        return_type=None
                    )
                ]
            )
        ])
        self.check_type_error(prog)

    def test_class_method_returning_field_valid(self):
        """
        Check that returning a field works and type matches.

        class Player:
            hp: int = 100

            def get_hp(self) -> int:
                return self.hp
        """
        prog = Program([
            ClassDef(
                name="Player",
                base=None,
                fields=[
                    VarDecl("hp", "int", Literal(100))
                ],
                methods=[
                    FunctionDef(
                        name="get_hp",
                        params=[("self", "Player")],
                        body=[
                            ReturnStmt(AttributeExpr(Identifier("self"), "hp"))
                        ],
                        return_type="int"
                    )
                ]
            )
        ])
        self.check_ok(prog)

    def test_class_method_return_type_mismatch_should_fail(self):
        """
        Declared return type is str but returns self.hp (which is int).

        class Player:
            hp: int = 100

            def get_hp(self) -> str:
                return self.hp
        """
        prog = Program([
            ClassDef(
                name="Player",
                base=None,
                fields=[
                    VarDecl("hp", "int", Literal(100))
                ],
                methods=[
                    FunctionDef(
                        name="get_hp",
                        params=[("self", "Player")],
                        body=[
                            ReturnStmt(AttributeExpr(Identifier("self"), "hp"))
                        ],
                        return_type="str"
                    )
                ]
            )
        ])
        self.check_type_error(prog)

    def test_class_method_missing_self_should_fail(self):
        """
        First parameter must be self; should fail if missing.

        class Player:
            hp: int = 100

            def get_hp() -> int:
                return self.hp
        """
        prog = Program([
            ClassDef(
                name="Player",
                base=None,
                fields=[
                    VarDecl("hp", "int", Literal(100))
                ],
                methods=[
                    FunctionDef(
                        name="get_hp",
                        params=[],  # missing self
                        body=[
                            ReturnStmt(AttributeExpr(Identifier("self"), "hp"))
                        ],
                        return_type="int"
                    )
                ]
            )
        ])
        self.check_type_error(prog)

    def test_class_multiple_fields_and_methods_valid(self):
        """
        Confirm a class with multiple fields and methods type checks.

        class Player:
            hp: int = 100
            name: str = "Hero"

            def get_name(self) -> str:
                return self.name

            def damage(self, amount: int):
                self.hp -= amount
        """
        prog = Program([
            ClassDef(
                name="Player",
                base=None,
                fields=[
                    VarDecl("hp", "int", Literal(100)),
                    VarDecl("name", "str", Literal("Hero")),
                ],
                methods=[
                    FunctionDef(
                        name="get_name",
                        params=[("self", "Player")],
                        body=[
                            ReturnStmt(AttributeExpr(Identifier("self"), "name"))
                        ],
                        return_type="str"
                    ),
                    FunctionDef(
                        name="damage",
                        params=[("self", "Player"), ("amount", "int")],
                        body=[
                            AugAssignStmt(
                                AttributeExpr(Identifier("self"), "hp"),
                                "-",
                                Identifier("amount")
                            )
                        ],
                        return_type=None
                    )
                ]
            )
        ])
        self.check_ok(prog)


if __name__ == "__main__":
    unittest.main()
