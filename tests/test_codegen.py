import unittest
from codegen import CodeGen
from lang_ast import *

def codegen_output(program: Program) -> str:
    return CodeGen().generate(program)

def assert_contains_all(testcase, output: str, snippets: list[str]):
    for snippet in snippets:
        testcase.assertIn(snippet, output, f"Missing: {snippet}")

class TestCodeGen(unittest.TestCase):

    def test_global_variable(self):
        prog = Program(body=[
            VarDecl(name="counter", declared_type="int", value=Literal(raw="100"))
        ])
        output = codegen_output(prog)
        assert_contains_all(self, output, [
            "int64_t counter = 100;"
        ])

    def test_simple_function(self):
        prog = Program(body=[
            FunctionDef(
                name="add",
                params=[Parameter("x", "int", None), Parameter("y", "int", None)],
                return_type="int",
                body=[
                    VarDecl("result", "int", BinOp(Identifier("x"), "+", Identifier("y"))),
                    ExprStmt(CallExpr(Identifier("print"), [StringLiteral("Adding numbers:")])),
                    ExprStmt(CallExpr(Identifier("print"), [Identifier("result")])),
                    ReturnStmt(Identifier("result"))
                ],
                globals_declared=None
            )
        ])
        output = codegen_output(prog)
        assert_contains_all(self, output, [
            "int64_t add(int64_t x, int64_t y)",
            "int64_t result = (x + y);",
            'pb_print_str("Adding numbers:");',
            "pb_print_int(result);",
            "return result;"
        ])

    def test_class_with_method(self):
        prog = Program(body=[
            ClassDef(
                name="Player",
                base=None,
                fields=[VarDecl("hp", "int", Literal("100"))],
                methods=[
                    FunctionDef(
                        name="heal",
                        params=[Parameter("self", None, None), Parameter("amount", "int", None)],
                        return_type="None",
                        body=[
                            AugAssignStmt(
                                target=AttributeExpr(Identifier("self"), "hp"),
                                op="+=",
                                value=Identifier("amount")
                            )
                        ],
                        globals_declared=None
                    )
                ]
            )
        ])
        output = codegen_output(prog)
        assert_contains_all(self, output, [
            "typedef struct Player {",
            "int64_t hp;",
            "} Player;",
            "void Player__heal(struct Player * self, int64_t amount)",
            "self->hp += amount;"
        ])

    def test_fstring_interpolation(self):
        prog = Program(body=[
            FunctionDef(
                name="main",
                params=[],
                return_type="int",
                body=[
                    VarDecl("value", "int", Literal("42")),
                    VarDecl("name", "str", StringLiteral("Alice")),
                    ExprStmt(CallExpr(Identifier("print"), [
                        FStringLiteral(raw="Value is {value}", vars=["value"])
                    ])),
                    ExprStmt(CallExpr(Identifier("print"), [
                        FStringLiteral(raw="Hello, {name}!", vars=["name"])
                    ])),
                    ReturnStmt(Literal("0"))
                ],
                globals_declared=None
            )
        ])
        output = codegen_output(prog)
        assert_contains_all(self, output, [
            'int main(void)',
            'int64_t value = 42;',
            'const char * name = "Alice";',
            'pb_print_str((snprintf(__fbuf, 256, "Value is %lld", value), __fbuf));',
            'pb_print_str((snprintf(__fbuf, 256, "Hello, %s!", name), __fbuf));',
            "return 0;"
        ])

    def test_if_else_chain(self):
        prog = Program(body=[
            FunctionDef(
                name="main",
                params=[],
                return_type="int",
                body=[
                    VarDecl("n", "int", Literal("5")),
                    IfStmt(branches=[
                        IfBranch(BinOp(Identifier("n"), "==", Literal("0")), [
                            ExprStmt(CallExpr(Identifier("print"), [StringLiteral("zero")]))
                        ]),
                        IfBranch(BinOp(Identifier("n"), "==", Literal("5")), [
                            ExprStmt(CallExpr(Identifier("print"), [StringLiteral("five")]))
                        ]),
                        IfBranch(None, [
                            ExprStmt(CallExpr(Identifier("print"), [StringLiteral("other")]))
                        ])
                    ]),
                    ReturnStmt(Literal("0"))
                ],
                globals_declared=None
            )
        ])
        output = codegen_output(prog)
        assert_contains_all(self, output, [
        "if ((n == 0)) {",
        'pb_print_str("zero");',
        "}",
        "else if ((n == 5)) {",
        'pb_print_str("five");',
        "}",
        "else  {",
        'pb_print_str("other");',
        "}",
        "return 0;"
        ])

    def test_while_loop_with_update(self):
        program = Program(body=[
            FunctionDef(
                name="main",
                params=[],
                return_type="int",
                body=[
                    VarDecl("i", "int", Literal("0")),
                    WhileStmt(
                        condition=BinOp(Identifier("i"), "<", Literal("3")),
                        body=[
                            ExprStmt(CallExpr(Identifier("print"), [Identifier("i")])),
                            AssignStmt(
                                target=Identifier("i"),
                                value=BinOp(Identifier("i"), "+", Literal("1"))
                            )
                        ]
                    ),
                    ReturnStmt(Literal("0"))
                ],
                globals_declared=None
            )
        ])
        output = codegen_output(program)
        assert_contains_all(self, output, [
            "int64_t i = 0;",
            "while ((i < 3)) {",
            "pb_print_int(i);",
            "i = (i + 1);",
            "}",
            "return 0;"
        ])

    def test_for_loop_range(self):
        program = Program(body=[
            FunctionDef(
                name="main",
                params=[],
                return_type="int",
                body=[
                    ForStmt(
                        var_name="k",
                        iterable=CallExpr(Identifier("range"), [Literal("0"), Literal("3")]),
                        body=[
                            ExprStmt(CallExpr(Identifier("print"), [Identifier("k")]))
                        ]
                    ),
                    ReturnStmt(Literal("0"))
                ],
                globals_declared=None
            )
        ])
        output = codegen_output(program)
        assert_contains_all(self, output, [
            "for (int64_t k = 0; k < 3; ++k) {",
            "pb_print_int(k);",
            "}",
            "return 0;"
        ])

    def test_for_loop_with_break_continue(self):
        program = Program(body=[
            FunctionDef(
                name="main",
                params=[],
                return_type="int",
                body=[
                    ForStmt(
                        var_name="i",
                        iterable=CallExpr(Identifier("range"), [Literal("0"), Literal("5")]),
                        body=[
                            IfStmt(branches=[
                                IfBranch(BinOp(Identifier("i"), "==", Literal("2")), [
                                    ContinueStmt()
                                ])
                            ]),
                            IfStmt(branches=[
                                IfBranch(BinOp(Identifier("i"), "==", Literal("4")), [
                                    BreakStmt()
                                ])
                            ]),
                            ExprStmt(CallExpr(Identifier("print"), [Identifier("i")]))
                        ]
                    ),
                    ReturnStmt(Literal("0"))
                ],
                globals_declared=None
            )
        ])
        output = codegen_output(program)
        assert_contains_all(self, output, [
            "for (int64_t i = 0; i < 5; ++i) {",
            "if ((i == 2)) {",
            "continue;",
            "}",
            "if ((i == 4)) {",
            "break;",
            "}",
            "pb_print_int(i);",
            "}",
            "return 0;"
        ])

    def test_augmented_assignments(self):
        program = Program(body=[
            FunctionDef(
                name="main",
                params=[],
                return_type="int",
                body=[
                    VarDecl("x", "int", Literal("5")),
                    AugAssignStmt(Identifier("x"), "+=", Literal("3")),
                    AugAssignStmt(Identifier("x"), "-=", Literal("2")),
                    AugAssignStmt(Identifier("x"), "*=", Literal("4")),
                    AugAssignStmt(Identifier("x"), "//=", Literal("2")),
                    AugAssignStmt(Identifier("x"), "%=", Literal("3")),
                    ExprStmt(CallExpr(Identifier("print"), [Identifier("x")])),
                    ReturnStmt(Literal("0"))
                ],
                globals_declared=None
            )
        ])
        output = codegen_output(program)
        assert_contains_all(self, output, [
            "int64_t x = 5;",
            "x += 3;",
            "x -= 2;",
            "x *= 4;",
            "x /= 2;",
            "x %= 3;",
            "pb_print_int(x);",
            "return 0;"
        ])

    def test_list_and_indexing(self):
        program = Program(body=[
            FunctionDef(
                name="main",
                params=[],
                return_type="int",
                body=[
                    VarDecl("nums", "list[int]", ListExpr(
                        elements=[Literal("10"), Literal("20"), Literal("30")]
                    )),
                    VarDecl("first", "int", IndexExpr(Identifier("nums"), Literal("0"))),
                    ExprStmt(CallExpr(Identifier("print"), [Identifier("first")])),
                    ReturnStmt(Literal("0"))
                ],
                globals_declared=None
            )
        ])
        output = codegen_output(program)
        assert_contains_all(self, output, [
            "int64_t __tmp_list_",
            "List_int nums =",
            "int64_t first = nums.data[0];",
            "pb_print_int(first);",
            "return 0;"
        ])

    def test_dict_literal_and_access(self):
        program = Program(body=[
            FunctionDef(
                name="main",
                params=[],
                return_type="int",
                body=[
                    VarDecl(
                        "d", "dict[str, int]",
                        DictExpr(
                            keys=[StringLiteral("a"), StringLiteral("b")],
                            values=[Literal("1"), Literal("2")]
                        )
                    ),
                    ExprStmt(CallExpr(Identifier("print"), [
                        IndexExpr(Identifier("d"), StringLiteral("a"))
                    ])),
                    ReturnStmt(Literal("0"))
                ],
                globals_declared=None
            )
        ])
        output = codegen_output(program)
        assert_contains_all(self, output, [
            "Pair_str_int __tmp_dict_",
            "Dict_str_int d =",
            'pb_print_int(pb_dict_get(d, "a"));',
            "return 0;"
        ])

    def test_try_except_raise(self):
        program = Program(body=[
            FunctionDef(
                name="main",
                params=[],
                return_type="int",
                body=[
                    TryExceptStmt(
                        try_body=[
                            RaiseStmt(
                                exception=CallExpr(func=Identifier("RuntimeError"), args=[StringLiteral("fail")])
                            )
                        ],
                        except_blocks=[
                            ExceptBlock(
                                exc_type="RuntimeError",
                                alias=None,
                                body=[ExprStmt(CallExpr(Identifier("print"), [StringLiteral("caught")]))]
                            )
                        ]
                    ),
                    ReturnStmt(Literal("0"))
                ],
                globals_declared=None
            )
        ])
        output = codegen_output(program)
        assert_contains_all(self, output, [
            "/* try/except not supported at runtime */",
            "return 0;"
        ])

    def test_class_inheritance_dispatch(self):
        program = Program(body=[
            ClassDef(
                name="Player",
                base=None,
                fields=[VarDecl("hp", "int", Literal("100"))],
                methods=[
                    FunctionDef(
                        name="get_hp",
                        params=[Parameter("self", None, None)],
                        return_type="int",
                        body=[ReturnStmt(AttributeExpr(Identifier("self"), "hp"))],
                        globals_declared=None
                    )
                ]
            ),
            ClassDef(
                name="Mage",
                base="Player",
                fields=[],
                methods=[]
            ),
            FunctionDef(
                name="main",
                params=[],
                return_type="int",
                body=[
                    VarDecl("m", "Mage", CallExpr(Identifier("Mage"), [])),
                    ExprStmt(CallExpr(Identifier("print"), [
                        CallExpr(func=AttributeExpr(Identifier("m"), "get_hp"), args=[])
                    ])),
                    ReturnStmt(Literal("0"))
                ],
                globals_declared=None
            )
        ])
        output = codegen_output(program)
        assert_contains_all(self, output, [
            "static inline int64_t Mage__get_hp(",
            "struct Mage * self)",
            "return Player__get_hp((struct Player *)self);"
        ])

    def test_global_variable_in_method(self):
        program = Program(body=[
            VarDecl("counter", "int", Literal("0")),
            ClassDef(
                name="A",
                base=None,
                fields=[],
                methods=[
                    FunctionDef(
                        name="inc",
                        params=[Parameter("self", None, None)],
                        return_type="None",
                        body=[
                            GlobalStmt(names=["counter"]),
                            AugAssignStmt(Identifier("counter"), "+=", Literal("1"))
                        ],
                        globals_declared=None
                    )
                ]
            )
        ])
        output = codegen_output(program)
        assert_contains_all(self, output, [
            "int64_t counter = 0;",
            "void A__inc(struct A * self)",
            "/* global counter */",
            "counter += 1;"
        ])

    def test_function_with_default_arg(self):
        program = Program(body=[
            FunctionDef(
                name="incr",
                params=[
                    Parameter("x", "int", None),
                    Parameter("step", "int", Literal("2"))
                ],
                return_type="int",
                body=[
                    ReturnStmt(BinOp(Identifier("x"), "+", Identifier("step")))
                ],
                globals_declared=None
            )
        ])
        output = codegen_output(program)
        assert_contains_all(self, output, [
            "int64_t incr(int64_t x, int64_t step)",
            "return (x + step);"
        ])

    def test_is_and_is_not(self):
        program = Program(body=[
            FunctionDef(
                name="main",
                params=[],
                return_type="int",
                body=[
                    VarDecl("a", "int", Literal("10")),
                    VarDecl("b", "int", Literal("10")),
                    IfStmt(branches=[
                        IfBranch(BinOp(Identifier("a"), "is", Identifier("b")), [
                            ExprStmt(CallExpr(Identifier("print"), [StringLiteral("a is b")]))
                        ])
                    ]),
                    IfStmt(branches=[
                        IfBranch(BinOp(Identifier("a"), "is not", Literal("20")), [
                            ExprStmt(CallExpr(Identifier("print"), [StringLiteral("a is not 20")]))
                        ])
                    ]),
                    ReturnStmt(Literal("0"))
                ],
                globals_declared=None
            )
        ])
        output = codegen_output(program)
        assert_contains_all(self, output, [
            "if ((a == b)) {",
            'pb_print_str("a is b");',
            "}",
            "if ((a != 20)) {",
            'pb_print_str("a is not 20");',
            "}",
            "return 0;"
        ])

    def test_boolean_and_not(self):
        program = Program(body=[
            FunctionDef(
                name="main",
                params=[],
                return_type="int",
                body=[
                    VarDecl("x", "bool", Literal("True")),
                    VarDecl("y", "bool", Literal("False")),
                    IfStmt(branches=[
                        IfBranch(
                            BinOp(Identifier("x"), "and", UnaryOp("not", Identifier("y"))),
                            [ExprStmt(CallExpr(Identifier("print"), [StringLiteral("x is True and y is False")]))]
                        )
                    ]),
                    ReturnStmt(Literal("0"))
                ],
                globals_declared=None
            )
        ])
        output = codegen_output(program)
        assert_contains_all(self, output, [
            "bool x = true;",
            "bool y = false;",
            "if ((x && !(y))) {",
            'pb_print_str("x is True and y is False");',
            "}",
            "return 0;"
        ])

    def test_class_vs_instance_attr(self):
        program = Program(body=[
            ClassDef(
                name="Thing",
                base=None,
                fields=[VarDecl("kind", "str", StringLiteral("generic"))],
                methods=[
                    FunctionDef(
                        name="get_class_kind",
                        params=[Parameter("self", None, None)],
                        return_type="str",
                        body=[ReturnStmt(AttributeExpr(Identifier("Thing"), "kind"))],
                        globals_declared=None
                    )
                ]
            ),
            FunctionDef(
                name="main",
                params=[],
                return_type="int",
                body=[
                    VarDecl("t", "Thing", CallExpr(Identifier("Thing"), [])),
                    ExprStmt(CallExpr(Identifier("print"), [
                        CallExpr(func=AttributeExpr(Identifier("t"), "get_class_kind"), args=[])
                    ])),
                    ReturnStmt(Literal("0"))
                ],
                globals_declared=None
            )
        ])
        output = codegen_output(program)
        assert_contains_all(self, output, [
            'const char * Thing_kind = "generic";',
            "const char * Thing__get_class_kind(struct Thing * self)",
            "return Thing_kind;",
            "pb_print_str(Thing__get_class_kind(t));",
            "return 0;"
        ])

    def test_pass_statement(self):
        program = Program(body=[
            FunctionDef(
                name="main",
                params=[],
                return_type="int",
                body=[
                    IfStmt(branches=[
                        IfBranch(Literal("True"), [PassStmt()])
                    ]),
                    ExprStmt(CallExpr(Identifier("print"), [StringLiteral("done")])),
                    ReturnStmt(Literal("0"))
                ],
                globals_declared=None
            )
        ])
        output = codegen_output(program)
        assert_contains_all(self, output, [
            "if (true) {",
            ";  // pass",
            "}",
            'pb_print_str("done");',
            "return 0;"
        ])

    def test_main_entry_point(self):
        program = Program(body=[
            FunctionDef(
                name="main",
                params=[],
                return_type="int",
                body=[
                    ExprStmt(CallExpr(Identifier("print"), [StringLiteral("hello")])),
                    ReturnStmt(Literal("0"))
                ],
                globals_declared=None
            )
        ])
        output = codegen_output(program)
        assert_contains_all(self, output, [
            "int main(void)",
            'pb_print_str("hello");',
            "return 0;"
        ])


if __name__ == "__main__":
    unittest.main()
