import unittest
from codegen import CodeGen
from type_checker import TypeChecker
from lang_ast import *

def assert_all_inferred_types_filled(program: Program):
    def visit_expr(e: Expr):
        if hasattr(e, "inferred_type") and getattr(e, "inferred_type") is None:
            raise RuntimeError(f"Missing inferred_type in {e!r}")
        if isinstance(e, (BinOp, UnaryOp)):
            visit_expr(e.left) if hasattr(e, "left") else None
            visit_expr(e.right) if hasattr(e, "right") else None
            visit_expr(e.operand) if hasattr(e, "operand") else None
        elif isinstance(e, CallExpr):
            visit_expr(e.func)
            for arg in e.args:
                visit_expr(arg)
        elif isinstance(e, (AttributeExpr, IndexExpr)):
            visit_expr(e.obj if hasattr(e, "obj") else e.base)
            if hasattr(e, "index"):
                visit_expr(e.index)
        elif isinstance(e, ListExpr):
            for el in e.elements:
                visit_expr(el)
        elif isinstance(e, DictExpr):
            for k in e.keys + e.values:
                visit_expr(k)
        elif isinstance(e, (Identifier, Literal, StringLiteral, FStringLiteral)):
            pass
        else:
            raise TypeError(f"Unhandled Expr type: {type(e).__name__}")

    def visit_stmt(s: Stmt):
        if isinstance(s, FunctionDef):
            for param in s.params:
                if param.inferred_type is None:
                    raise RuntimeError(f"Missing inferred_type in param {param.name}")
            for stmt in s.body:
                visit_stmt(stmt)
        elif isinstance(s, VarDecl):
            visit_expr(s.value)
            if s.inferred_type is None:
                raise RuntimeError(f"Missing inferred_type in VarDecl {s.name}")
        elif isinstance(s, AssignStmt):
            visit_expr(s.target)
            visit_expr(s.value)
            if s.inferred_type is None:
                raise RuntimeError(f"Missing inferred_type in AssignStmt")
        elif isinstance(s, ExprStmt):
            visit_expr(s.expr)
        elif isinstance(s, WhileStmt):
            visit_expr(s.condition)
            for stmt in s.body:
                visit_stmt(stmt)
        elif isinstance(s, ReturnStmt):
            if s.value: visit_expr(s.value)
            if s.inferred_type is None:
                raise RuntimeError("Missing inferred_type in ReturnStmt")
        elif isinstance(s, IfStmt):
            for branch in s.branches:
                if branch.condition:
                    visit_expr(branch.condition)
                for stmt in branch.body:
                    visit_stmt(stmt)
        elif isinstance(s, (BreakStmt, ContinueStmt, PassStmt)):
            pass
        else:
            # other stmt types as needed
            pass

    for stmt in program.body:
        visit_stmt(stmt)

def codegen_output(program: Program) -> str:
    TypeChecker().check(program)
    # assert_all_inferred_types_filled(program)
    codegen = CodeGen()
    h = codegen.generate_header(program)
    c = codegen.generate(program)
    return h + "\n" + c

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
            "int64_t main_add(int64_t x, int64_t y)",
            "int64_t result = (x + y);",
            'pb_print_str("Adding numbers:");',
            "pb_print_int(result);",
            "return result;"
        ])
    def test_numeric_literal_with_underscores(self):
        prog = Program(body=[
            VarDecl(name="x", declared_type="int", value=Literal(raw="1_234"))
        ])
        output = codegen_output(prog)
        self.assertIn("int64_t x = 1234;", output)


    def test_class_with_method(self):
        prog = Program(body=[
            ClassDef(
                name="Player",
                base=None,
                fields=[],  # No class-level fields
                methods=[
                    FunctionDef(
                        name="__init__",
                        params=[Parameter("self", None, None)],
                        return_type="None",
                        body=[
                            AssignStmt(
                                target=AttributeExpr(Identifier("self"), "hp"),
                                value=Literal("100")
                            )
                        ],
                        globals_declared=None
                    ),
                    FunctionDef(
                        name="heal",
                        params=[
                            Parameter("self", None, None),
                            Parameter("amount", "int", None)
                        ],
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
            "int64_t hp;",                          # instance field
            "} Player;",
            "void Player__heal(struct Player * self, int64_t amount)",  # method declaration
            "self->hp += amount;"                   # correct method body line
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
                        FStringLiteral(parts=[
                            FStringText("Value is "),
                            FStringExpr(expr=Identifier("value"))
                        ])
                    ])),
                    ExprStmt(CallExpr(Identifier("print"), [
                        FStringLiteral(parts=[
                            FStringText("Hello, "),
                            FStringExpr(expr=Identifier("name")),
                            FStringText("!")
                        ])
                    ])),
                    ReturnStmt(Literal("0"))
                ],
                globals_declared=None
            )
        ])

        output = codegen_output(prog)

        # Expected generated code contains:
        # int64_t value = 42;
        # const char * name = "Alice";
        # pb_print_str((snprintf(__fbuf, 256, "Value is %lld", value), __fbuf));
        # pb_print_str((snprintf(__fbuf, 256, "Hello, %s!", name), __fbuf));
        self.assertIn('int main(void)', output)
        self.assertIn('int64_t value = 42;', output)
        self.assertIn('const char * name = "Alice";', output)
        self.assertIn('pb_print_str((snprintf(__fbuf, 256, "Value is %lld", value), __fbuf));', output)
        self.assertIn('pb_print_str((snprintf(__fbuf, 256, "Hello, %s!", name), __fbuf));', output)
        self.assertIn('return 0;', output)

    def test_string_concatenation(self):
        prog = Program(body=[
            FunctionDef(
                name="main",
                params=[],
                return_type="int",
                body=[
                    VarDecl("a", "str", StringLiteral("foo")),
                    VarDecl("b", "str", StringLiteral("bar")),
                    VarDecl("c", "str", BinOp(Identifier("a"), "+", Identifier("b"))),
                    ExprStmt(CallExpr(Identifier("print"), [Identifier("c")])),
                    ReturnStmt(Literal("0"))
                ],
                globals_declared=None
            )
        ])
        output = codegen_output(prog)
        self.assertIn('const char * c = pb_str_concat(a, b);', output)
        self.assertIn('pb_print_str(c);', output)

    def test_include_dotted_module_header(self):
        prog = Program(body=[
            ImportStmt(module=["pkg", "sub"])
        ])
        output = codegen_output(prog)
        self.assertIn('#include "pkg.sub.h"', output)

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
                        elements=[Literal("10"), Literal("20"), Literal("30")],
                        elem_type="int",
                        inferred_type="list[int]"
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
            "int64_t __tmp_list_1[] = {10, 20, 30}",
            "List_int nums = (List_int){ .len=3, .data=__tmp_list_1 };",
            "int64_t first = list_int_get(&nums, 0);",
            "pb_print_int(first);",
            "return 0;"
        ])

    def test_list_bool_list_str(self):
        program = Program(body=[
            FunctionDef(
                name="main",
                params=[],
                return_type="int",
                body=[
                    VarDecl("arr", "list[bool]", ListExpr(
                        elements=[Literal("True"), Literal("False")],
                        elem_type="bool",
                        inferred_type="list[bool]"
                    )),
                    VarDecl("arr2", "list[str]", ListExpr(
                        elements=[
                            StringLiteral(value="true", inferred_type="str"),
                            StringLiteral(value="true", inferred_type="str")],
                        elem_type="str",
                        inferred_type="list[str]"
                    )),
                    VarDecl("arr3", "list[int]", ListExpr(
                        elements=[],
                        elem_type="int",
                        inferred_type="list[int]"
                    )),
                    VarDecl("arr4", "list[str]", ListExpr(
                        elements=[],
                        elem_type="str",
                        inferred_type="list[str]"
                    )),
                    ExprStmt(CallExpr(Identifier("print"), [IndexExpr(Identifier("arr"), Literal("0"))])),
                    ExprStmt(CallExpr(Identifier("print"), [IndexExpr(Identifier("arr2"), Literal("1"))])),
                    ReturnStmt(Literal("0"))
                ],
                globals_declared=None
            )
        ])
        output = codegen_output(program)
        assert_contains_all(self, output, [
            "bool __tmp_list_1[] = {true, false};",
            "List_bool arr = (List_bool){ .len=2, .data=__tmp_list_1 };",
            "const char * __tmp_list_2[] = {\"true\", \"true\"};",
            "List_str arr2 = (List_str){ .len=2, .data=__tmp_list_2 };",
            "List_int __tmp_list_3;",
            "list_int_init(&__tmp_list_3);",
            "List_int arr3 = __tmp_list_3;",
            "List_str __tmp_list_4;",
            "list_str_init(&__tmp_list_4);",
            "List_str arr4 = __tmp_list_4;",
            "pb_print_bool(list_bool_get(&arr, 0));",
            "pb_print_str(list_str_get(&arr2, 1));",
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
                            values=[Literal("1"), Literal("2")],
                            elem_type="int",
                            inferred_type="dict[str, int]",
                        ),
                        inferred_type='dict[str, int]'
                    ),
                    ExprStmt(CallExpr(Identifier("print"), [
                        IndexExpr(Identifier("d", "dict[str, int]"), StringLiteral("a"))
                    ])),
                    VarDecl(
                        "d2", "dict[str, str]",
                        DictExpr(
                            keys=[StringLiteral("a"), StringLiteral("b")],
                            values=[StringLiteral("sth here"), StringLiteral("and here")],
                            elem_type="str",
                            inferred_type="dict[str, str]",
                        ),
                        inferred_type='dict[str, str]',
                    ),
                    ExprStmt(CallExpr(Identifier("print"), [
                        IndexExpr(Identifier("d2", "dict[str, str]"), StringLiteral("a"))
                    ])),
                    VarDecl(
                        "d3", "dict[str, bool]",
                        DictExpr(
                            keys=[StringLiteral("a"), StringLiteral("b")],
                            values=[Literal("True"), Literal("False")],
                            elem_type="bool",
                            inferred_type="dict[str, bool]",
                        ),
                        inferred_type='dict[str, bool]'
                    ),
                    ExprStmt(CallExpr(Identifier("print"), [
                        IndexExpr(Identifier("d3", inferred_type="dict[str, bool]"), StringLiteral("a"))
                    ])),
                    ReturnStmt(Literal("0"))
                ],
                globals_declared=None
            )
        ])
        output = codegen_output(program)
        assert_contains_all(self, output, [
            'Pair_str_int __tmp_dict_1[] = {{"a", 1}, {"b", 2}};',
            'Dict_str_int d = (Dict_str_int){ .len=2, .data=__tmp_dict_1 };',
            'pb_print_int(pb_dict_get_str_int(d, "a"));',
            'Pair_str_str __tmp_dict_2[] = {{"a", "sth here"}, {"b", "and here"}};',
            'Dict_str_str d2 = (Dict_str_str){ .len=2, .data=__tmp_dict_2 };',
            'pb_print_str(pb_dict_get_str_str(d2, "a"));',
            'Pair_str_bool __tmp_dict_3[] = {{"a", true}, {"b", false}};',
            'Dict_str_bool d3 = (Dict_str_bool){ .len=2, .data=__tmp_dict_3 };',
            'pb_print_bool(pb_dict_get_str_bool(d3, "a"));',
            'return 0;'
        ])     

    def test_try_except_raise(self):
        program = Program(body=[
            ClassDef(
                name="RuntimeError",
                base=None,
                fields=[],
                methods=[
                    FunctionDef(
                        name="__init__",
                        params=[
                            Parameter("self", "RuntimeError"),
                            Parameter("msg", "str"),
                        ],
                        return_type="None",
                        body=[]
                    )
                ]
            ),
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
        self.assertIn('pb_push_try(&', output)
        self.assertIn('pb_raise_obj("RuntimeError"', output)
        self.assertIn('strcmp(pb_current_exc.type, "RuntimeError") == 0', output)
        self.assertIn('pb_clear_exc();', output)
        self.assertIn('pb_reraise();', output)

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
            "int64_t main_incr(int64_t x, int64_t step)",
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

    def test_chained_comparison_codegen(self):
        program = Program(body=[
            FunctionDef(
                name="main",
                params=[],
                return_type="int",
                body=[
                    VarDecl("x", "int", Literal("5")),
                    IfStmt(branches=[
                        IfBranch(
                            BinOp(
                                BinOp(Literal("1"), "<", Identifier("x")),
                                "and",
                                BinOp(Identifier("x"), "<", Literal("10"))
                            ),
                            [ExprStmt(CallExpr(Identifier("print"), [StringLiteral("ok")]))]
                        )
                    ]),
                    ReturnStmt(Literal("0"))
                ],
                globals_declared=None
            )
        ])
        output = codegen_output(program)
        assert_contains_all(self, output, [
            "int64_t x = 5;",
            "if (((1 < x) && (x < 10))) {",
            'pb_print_str("ok");',
            "}",
            "return 0;",
        ])

    def test_class_attrs_and_dynamic_instance_attr(self):
        program = Program(body=[
            ClassDef(
                name="Player",
                base=None,
                fields=[
                    VarDecl("mp", "int", Literal("100"))
                ],
                methods=[
                    FunctionDef(
                        name="__init__",
                        params=[Parameter("self", None, None)],
                        return_type="None",
                        body=[
                            AssignStmt(
                                target=AttributeExpr(Identifier("self"), "hp"),
                                value=Literal("150")
                            )
                        ],
                        globals_declared=None
                    ),
                    FunctionDef(
                        name="get_hp",
                        params=[Parameter("self", None, None)],
                        return_type="int",
                        body=[
                            ReturnStmt(AttributeExpr(Identifier("self"), "hp"))
                        ],
                        globals_declared=None
                    )
                ]
            ),
            FunctionDef(
                name="main",
                params=[],
                return_type="int",
                body=[
                    VarDecl("p", "Player", CallExpr(Identifier("Player"), [])),
                    ExprStmt(CallExpr(Identifier("print"), [
                        AttributeExpr(Identifier("p"), "hp")
                    ])),
                    ExprStmt(CallExpr(Identifier("print"), [
                        CallExpr(AttributeExpr(Identifier("p"), "get_hp"), [])
                    ])),
                    ExprStmt(CallExpr(Identifier("print"), [
                        AttributeExpr(Identifier("Player"), "mp")
                    ])),
                    ReturnStmt(Literal("0"))
                ],
                globals_declared=None
            )
        ])
        output = codegen_output(program)

        # Ensure generated struct contains both class and instance fields
        assert_contains_all(self, output, [
            "typedef struct Player {",
            "int64_t mp;",
            "int64_t hp;",
            "} Player;",

            # Global class-level field
            "int64_t Player_mp = 100;",

            # Proper __init__ method setting instance hp
            "void Player____init__(struct Player * self)",
            "self->hp = 150;",

            # Method get_hp accessing instance field
            "int64_t Player__get_hp(struct Player * self)",
            "return self->hp;",

            # main function uses all three accesses
            "pb_print_int(p->hp);",
            "pb_print_int(Player__get_hp(p));",
            "pb_print_int(Player_mp);"
        ])

    def test_class_field_without_initializer(self):
        program = Program(body=[
            ClassDef(
                name="Foo",
                base=None,
                fields=[VarDecl("attr1", "int", None)],
                methods=[]
            )
        ])
        output = codegen_output(program)

        assert_contains_all(self, output, [
            "typedef struct Foo {",
            "int64_t attr1;",
            "} Foo;",
        ])
        self.assertNotIn("Foo_attr1 =", output)

    def test_class_inheritance_with_fields(self):
        program = Program(body=[
            ClassDef(
                name="Player",
                base=None,
                fields=[VarDecl("name", "str", StringLiteral("P"))],
                methods=[
                    FunctionDef(
                        name="__init__",
                        params=[Parameter("self", "Player", None)],
                        return_type="None",
                        body=[
                            AssignStmt(
                                target=AttributeExpr(Identifier("self"), "hp"),
                                value=Literal("150")
                            )
                        ]
                    ),
                    FunctionDef(
                        name="get_hp",
                        params=[Parameter("self", "Player", None)],
                        return_type="int",
                        body=[
                            ReturnStmt(
                                AttributeExpr(Identifier("self"), "hp")
                            )
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
                        params=[Parameter("self", "Mage", None)],
                        return_type="None",
                        body=[
                            ExprStmt(
                                CallExpr(
                                    func=AttributeExpr(Identifier("Player"), "__init__"),
                                    args=[Identifier("self")]
                                )
                            ),
                            AssignStmt(
                                target=AttributeExpr(Identifier("self"), "mana"),
                                value=Literal("200")
                            )
                        ]
                    )
                ]
            ),
            FunctionDef(
                name="main",
                params=[],
                return_type="int",
                body=[
                    VarDecl("p", "Player", CallExpr(Identifier("Player"), [])),
                    ExprStmt(CallExpr(Identifier("print"), [
                        AttributeExpr(Identifier("p"), "hp")
                    ])),
                    ExprStmt(CallExpr(Identifier("print"), [
                        CallExpr(AttributeExpr(Identifier("p"), "get_hp"), [])
                    ])),
                    ExprStmt(CallExpr(Identifier("print"), [
                        AttributeExpr(Identifier("Player"), "name")
                    ])),
                    VarDecl("m", "Mage", CallExpr(Identifier("Mage"), [])),
                    ExprStmt(CallExpr(Identifier("print"), [
                        AttributeExpr(Identifier("m"), "hp")
                    ])),
                    ExprStmt(CallExpr(Identifier("print"), [
                        AttributeExpr(Identifier("m"), "mana")
                    ])),
                    ExprStmt(CallExpr(Identifier("print"), [
                        CallExpr(AttributeExpr(Identifier("m"), "get_hp"), [])
                    ])),
                    ReturnStmt(Literal("0"))
                ]
            )
        ])
        c = codegen_output(program)
        assert_contains_all(self, c, [
            "typedef struct Player {",
            "const char * name;",
            "int64_t hp;",
            "typedef struct Mage {",
            "Player base;",
            "int64_t mana;",
            "const char * Player_name = \"P\";",
            "void Player____init__(struct Player * self);",
            "int64_t Player__get_hp(struct Player * self);",
            "void Mage____init__(struct Mage * self);",
            "Player____init__((struct Player *)self);",
            "pb_print_int(p->hp);",
            "pb_print_int(Player__get_hp(p));",
            "pb_print_str(Player_name);",
            "pb_print_int(m->base.hp);",
            "pb_print_int(m->mana);",
            "pb_print_int(Mage__get_hp(m));"
        ])

    def test_codegen_class_attr_inheritance(self):
        # Equivalent PB code:
        #   class Player:
        #       name: str = 'P'
        #       BASE_HP: int = 150
        #       def __init__(self):
        #           self.hp = 150
        #
        #   class Mage(Player):
        #       DEFAULT_MANA: int = 200
        #       def __init__(self):
        #           Player.__init__(self)
        #           self.mana = 200
        #       def total_power(self, bonus: int = 10) -> int:
        #           return self.hp + self.mana + bonus
        #
        #   class ArchMage(Mage):
        #       pass
        #
        #   def main() -> int:
        #       p: Player = Player()
        #       print(p.name)
        #       m: Mage = Mage()
        #       print(m.name)
        #       print(Mage.name)
        #       a: ArchMage = ArchMage()
        #       print(a.mana)
        #       print(a.hp)
        #       print(a.total_power())
        #       return 0

        program = Program(body=[
            ClassDef(
                name="Player",
                base=None,
                fields=[
                    VarDecl("name", "str", StringLiteral("P")),
                    VarDecl("BASE_HP", "int", Literal("150")),
                ],
                methods=[
                    FunctionDef(
                        name="__init__",
                        params=[Parameter("self", "Player")],
                        return_type="None",
                        body=[
                            AssignStmt(
                                target=AttributeExpr(Identifier("self"), "hp"),
                                value=Literal("150"),
                            )
                        ],
                    )
                ],
            ),
            ClassDef(
                name="Mage",
                base="Player",
                fields=[VarDecl("DEFAULT_MANA", "int", Literal("200"))],
                methods=[
                    FunctionDef(
                        name="__init__",
                        params=[Parameter("self", "Mage")],
                        return_type="None",
                        body=[
                            ExprStmt(
                                CallExpr(
                                    func=AttributeExpr(Identifier("Player"), "__init__"),
                                    args=[Identifier("self")],
                                )
                            ),
                            AssignStmt(
                                target=AttributeExpr(Identifier("self"), "mana"),
                                value=Literal("200"),
                            ),
                        ],
                    ),
                    FunctionDef(
                        name="total_power",
                        params=[
                            Parameter("self", "Mage"),
                            Parameter("bonus", "int", Literal("10")),
                        ],
                        return_type="int",
                        body=[
                            ReturnStmt(
                                BinOp(
                                    BinOp(
                                        AttributeExpr(Identifier("self"), "hp"),
                                        "+",
                                        AttributeExpr(Identifier("self"), "mana"),
                                    ),
                                    "+",
                                    Identifier("bonus"),
                                )
                            )
                        ],
                    ),
                ],
            ),
            ClassDef(name="ArchMage", base="Mage", fields=[], methods=[]),
            FunctionDef(
                name="main",
                params=[],
                return_type="int",
                body=[
                    VarDecl("p", "Player", CallExpr(Identifier("Player"), [])),
                    ExprStmt(CallExpr(Identifier("print"), [AttributeExpr(Identifier("p"), "name")])),
                    VarDecl("m", "Mage", CallExpr(Identifier("Mage"), [])),
                    ExprStmt(CallExpr(Identifier("print"), [AttributeExpr(Identifier("m"), "name")])),
                    ExprStmt(CallExpr(Identifier("print"), [AttributeExpr(Identifier("Mage"), "name")])),
                    VarDecl("a", "ArchMage", CallExpr(Identifier("ArchMage"), [])),
                    ExprStmt(CallExpr(Identifier("print"), [AttributeExpr(Identifier("a"), "mana")])),
                    ExprStmt(CallExpr(Identifier("print"), [AttributeExpr(Identifier("a"), "hp")])),
                    ExprStmt(
                        CallExpr(
                            Identifier("print"),
                            [CallExpr(AttributeExpr(Identifier("a"), "total_power"), [])],
                        )
                    ),
                    ReturnStmt(Literal("0")),
                ],
            ),
        ])

        c = codegen_output(program)
        self.assertIn("pb_print_str(Player_name);", c)
        self.assertIn("pb_print_int(a->base.base.hp);", c)

    def test_exception_inheritance_codegen(self):
        prog = Program(body=[
            ClassDef(
                name="Exception",
                base=None,
                fields=[
                    VarDecl(name="msg", declared_type="str", value=None)
                ],
                methods=[
                    FunctionDef(
                        name="__init__",
                        params=[
                            Parameter("self", "Exception"),
                            Parameter("msg", "str")
                        ],
                        return_type="None",
                        body=[
                            AssignStmt(
                                target=AttributeExpr(Identifier("self"), "msg"),
                                value=Identifier("msg")
                            )
                        ]
                    )
                ]
            ),
            ClassDef(
                name="RuntimeError",
                base="Exception",
                fields=[],
                methods=[]
            ),
            FunctionDef(
                name="crash",
                params=[],
                return_type="None",
                body=[
                    RaiseStmt(CallExpr(Identifier("RuntimeError"), [StringLiteral("division by zero")]))
                ]
            ),
            FunctionDef(
                name="main",
                params=[],
                return_type="None",
                body=[
                    ExprStmt(CallExpr(Identifier("crash"), []))
                ]
            )
        ])
        output = codegen_output(prog)
        assert_contains_all(self, output, [
            "typedef struct Exception {",
            "const char * msg;",
            "} Exception;",
            "typedef struct RuntimeError {",
            "Exception base;",
            "} RuntimeError;",
            "void Exception____init__(struct Exception * self, const char * msg);",
            "void RuntimeError____init__(struct RuntimeError * self, const char * msg);",
            "Exception____init__((struct Exception *)self, msg);"
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

    def test_print_identifier_with_inferred_type(self):
        prog = Program(body=[
            FunctionDef(
                name="main",
                params=[],
                return_type="int",
                body=[
                    VarDecl("name", "str", StringLiteral("Alice")),
                    ExprStmt(CallExpr(Identifier("print"), [
                        Identifier(name="name", inferred_type="str")
                    ])),
                    ReturnStmt(Literal("0", inferred_type="int"))
                ],
                globals_declared=None
            )
        ])
        output = codegen_output(prog)
        assert_contains_all(self, output, [
            'pb_print_str(name);',
            'return 0;'
        ])

    def test_print_call_with_inferred_type(self):
        # CallExpr with inferred_type
        prog = Program(body=[
            FunctionDef(
                name="get_name",
                params=[],
                return_type="str",
                body=[
                    ReturnStmt(StringLiteral("Alice", inferred_type="str"))
                ],
                globals_declared=None
            ),
            FunctionDef(
                name="main",
                params=[],
                return_type="int",
                body=[
                    ExprStmt(CallExpr(Identifier("print"), [
                        CallExpr(Identifier("get_name"), [], inferred_type="str")
                    ])),
                    ReturnStmt(Literal("0", inferred_type="int"))
                ],
                globals_declared=None
            )
        ])
        output = codegen_output(prog)
        assert_contains_all(self, output, [
            'pb_print_str(main_get_name());',
            'return 0;'
        ])

    def test_vardecl_with_inferred_types(self):
        prog = Program(body=[
            FunctionDef(
                name="main",
                params=[],
                return_type="int",
                body=[
                    VarDecl("flag", "bool", Literal("True", inferred_type="bool")),
                    VarDecl("pi", "float", Literal("3.14", inferred_type="float")),
                    VarDecl("msg", "str", StringLiteral("hello", inferred_type="str")),
                    ReturnStmt(Literal("0", inferred_type="int")),
                ],
                globals_declared=None
            )
        ])
        output = codegen_output(prog)
        assert_contains_all(self, output, [
            "bool flag = true;",
            "double pi = 3.14;",
            'const char * msg = "hello";',
            "return 0;",
        ])

    def test_list_int_operations(self):
        """
        * List element access by index.
        * Reassignment to indexed elements.
        * Printing values at an index.
        * Assigning indexed value to a local variable.
        * Printing both the variable and the list.
        """
        prog = Program(body=[
            FunctionDef(
                name="main",
                params=[],
                return_type="int",
                body=[
                    VarDecl("arr", "list[int]", ListExpr(
                        elements=[Literal("100")],
                        elem_type="int",
                        inferred_type="list[int]"
                    )),
                    ExprStmt(CallExpr(Identifier("print"), [
                        IndexExpr(Identifier("arr", inferred_type="list[int]"), Literal("0"), elem_type="int")
                    ])),
                    AssignStmt(
                        target=IndexExpr(Identifier("arr", inferred_type="list[int]"), Literal("0")),
                        value=Literal("1"),
                        inferred_type="int"
                    ),
                    VarDecl("x", "int",
                        value=IndexExpr(Identifier("arr", inferred_type="list[int]"), Literal("0"), elem_type="int"),
                        inferred_type="int"
                    ),
                    ExprStmt(CallExpr(Identifier("print"), [Identifier("x", inferred_type="int")])),
                    ExprStmt(CallExpr(Identifier("print"), [
                        IndexExpr(Identifier("arr", inferred_type="list[int]"), Literal("0"), elem_type="int")
                    ])),
                    ExprStmt(CallExpr(Identifier("print"), [Identifier("arr", inferred_type="list[int]")])),
                    ReturnStmt(Literal("0"))
                ]
            )
        ])
        output = codegen_output(prog)
        assert_contains_all(self, output, [
            "int64_t __tmp_list_1[] = {100};",
            "List_int arr = (List_int){ .len=1, .data=__tmp_list_1 };",
            "pb_print_int(list_int_get(&arr, 0));",
            "list_int_set(&arr, 0, 1);",
            "int64_t x = list_int_get(&arr, 0);",
            "pb_print_int(x);",
            "pb_print_int(list_int_get(&arr, 0));",
            "list_int_print(&arr);"
        ])

    def test_list_float_operations(self):
        prog = Program(body=[
            FunctionDef(
                name="main",
                params=[],
                return_type="int",
                body=[
                    VarDecl("arr", "list[float]", ListExpr(
                        elements=[Literal("0.1"), Literal("0.2")],
                        elem_type="float",
                        inferred_type="list[float]"
                    )),
                    AssignStmt(
                        target=IndexExpr(Identifier("arr", inferred_type="list[float]"), Literal("0")),
                        value=Literal("0.125"),
                        inferred_type="float"
                    ),
                    ExprStmt(CallExpr(Identifier("print"), [Identifier("arr", inferred_type="list[float]")])),
                    ReturnStmt(Literal("0"))
                ]
            )
        ])
        output = codegen_output(prog)
        assert_contains_all(self, output, [
            "double __tmp_list_1[] = {0.1, 0.2};",
            "List_float arr = (List_float){ .len=2, .data=__tmp_list_1 };",
            "list_float_set(&arr, 0, 0.125);",
            "list_float_print(&arr);"
        ])

    def test_list_bool_operations(self):
        prog = Program(body=[
            FunctionDef(
                name="main",
                params=[],
                return_type="int",
                body=[
                    VarDecl("arr", "list[bool]", ListExpr(
                        elements=[Literal("True"), Literal("True")],
                        elem_type="bool",
                        inferred_type="list[bool]"
                    )),
                    AssignStmt(
                        target=IndexExpr(Identifier("arr", inferred_type="list[bool]"), Literal("0")),
                        value=Literal("False"),
                        inferred_type="bool"
                    ),
                    ExprStmt(CallExpr(Identifier("print"), [Identifier("arr", inferred_type="list[bool]")])),
                    ReturnStmt(Literal("0"))
                ]
            )
        ])
        output = codegen_output(prog)
        assert_contains_all(self, output, [
            "bool __tmp_list_1[] = {true, true};",
            "List_bool arr = (List_bool){ .len=2, .data=__tmp_list_1 };",
            "list_bool_set(&arr, 0, false);",
            "list_bool_print(&arr);"
        ])

    def test_list_str_operations(self):
        prog = Program(body=[
            FunctionDef(
                name="main",
                params=[],
                return_type="int",
                body=[
                    VarDecl("arr", "list[str]", ListExpr(
                        elements=[StringLiteral("a"), StringLiteral("b")],
                        elem_type="str",
                        inferred_type="list[str]"
                    )),
                    AssignStmt(
                        target=IndexExpr(Identifier("arr", inferred_type="list[str]"), Literal("0")),
                        value=StringLiteral("c"),
                        inferred_type="str"
                    ),
                    ExprStmt(CallExpr(Identifier("print"), [Identifier("arr", inferred_type="list[str]")])),
                    ReturnStmt(Literal("0"))
                ]
            )
        ])
        output = codegen_output(prog)

        assert_contains_all(self, output, [
            'const char * __tmp_list_1[] = {"a", "b"};',
            "List_str arr = (List_str){ .len=2, .data=__tmp_list_1 };",
            "list_str_set(&arr, 0, \"c\");",
            "list_str_print(&arr);"
        ])

    def test_empty_list_assignment(self):
        prog = Program(body=[
            FunctionDef(
                name="main",
                params=[],
                return_type="int",
                body=[
                    VarDecl("a", "list[int]", ListExpr(elements=[Literal("0")], elem_type="int", inferred_type="list[int]")),
                    AssignStmt(target=IndexExpr(Identifier("a", inferred_type="list[int]"), Literal("0")), value=Literal("10"), inferred_type="int"),
                    VarDecl("x", "int", IndexExpr(Identifier("a", inferred_type="list[int]"), Literal("0", inferred_type="int"))),
                    ExprStmt(CallExpr(Identifier("print"), [Identifier("a", inferred_type="list[int]")])),
                    ExprStmt(CallExpr(Identifier("print"), [Identifier("x", inferred_type="int")])),
                    VarDecl("b", "list[int]", ListExpr(elements=[], elem_type="int", inferred_type="list[int]")),
                    AssignStmt(target=IndexExpr(Identifier("b", inferred_type="list[int]"), Literal("0")), value=Literal("1"), inferred_type="int"),
                    VarDecl("y", "int", IndexExpr(Identifier("b", inferred_type="list[int]"), Literal("0", inferred_type="int"))),
                    ExprStmt(CallExpr(Identifier("print"), [Identifier("b", inferred_type="list[int]")])),
                    ExprStmt(CallExpr(Identifier("print"), [Identifier("y", inferred_type="int")])),
                    ReturnStmt(Literal("0"))
                ],
                globals_declared=None
            )
        ])
        output = codegen_output(prog)
        assert_contains_all(self, output, [
            "int64_t __tmp_list_1[] = {0};",
            "List_int a = (List_int){ .len=1, .data=__tmp_list_1 };",
            "list_int_set(&a, 0, 10);",
            "int64_t x = list_int_get(&a, 0);",
            "list_int_print(&a);",
            "pb_print_int(x);",
            "List_int __tmp_list_2;",
            "list_int_init(&__tmp_list_2);",
            "List_int b = __tmp_list_2;",
            "list_int_set(&b, 0, 1);",
            "int64_t y = list_int_get(&b, 0);",
            "list_int_print(&b);",
            "pb_print_int(y);",
        ])

    def test_int_to_float_conversion(self):
        prog = Program(body=[
            FunctionDef(
                name="main",
                params=[],
                return_type="int",
                body=[
                    VarDecl("x", "int", Literal("10")),
                    VarDecl("x_float", "float", CallExpr(Identifier("float"), [Identifier("x")])),
                    ExprStmt(CallExpr(Identifier("print"), [Identifier("x_float")])),
                    ReturnStmt(Literal("0"))
                ]
            )
        ])
        output = codegen_output(prog)
        assert_contains_all(self, output, [
            "int64_t x = 10;",
            "double x_float = (double)(x);",
            "pb_print_double(x_float);"
        ])

    def test_float_to_int_conversion(self):
        prog = Program(body=[
            FunctionDef(
                name="main",
                params=[],
                return_type="int",
                body=[
                    VarDecl("y", "float", Literal("1.5")),
                    VarDecl("y_int", "int", CallExpr(Identifier("int"), [Identifier("y")])),
                    ExprStmt(CallExpr(Identifier("print"), [Identifier("y_int")])),
                    ReturnStmt(Literal("0"))
                ]
            )
        ])
        output = codegen_output(prog)
        assert_contains_all(self, output, [
            "double y = 1.5;",
            "int64_t y_int = (int64_t)(y);",
            "pb_print_int(y_int);"
        ])

    def test_string_to_int_conversion(self):
        prog = Program(body=[
            FunctionDef(
                name="main",
                params=[],
                return_type="int",
                body=[
                    VarDecl("a", "str", StringLiteral("123")),
                    VarDecl("a_int", "int", CallExpr(Identifier("int"), [Identifier("a")])),
                    ExprStmt(CallExpr(Identifier("print"), [Identifier("a_int")])),
                    ReturnStmt(Literal("0"))
                ]
            )
        ])
        output = codegen_output(prog)
        assert_contains_all(self, output, [
            "const char * a = \"123\";",
            "int64_t a_int = (strtoll)(a, NULL, 10);",
            "pb_print_int(a_int);"
        ])

    def test_string_to_float_conversion(self):
        prog = Program(body=[
            FunctionDef(
                name="main",
                params=[],
                return_type="int",
                body=[
                    VarDecl("b", "str", StringLiteral("1.23")),
                    VarDecl("b_float", "float", CallExpr(Identifier("float"), [Identifier("b")])),
                    ExprStmt(CallExpr(Identifier("print"), [Identifier("b_float")])),
                    ReturnStmt(Literal("0"))
                ]
            )
        ])
        output = codegen_output(prog)
        assert_contains_all(self, output, [
            "const char * b = \"1.23\";",
            "double b_float = (strtod)(b, NULL);",
            "pb_print_double(b_float);"
        ])

    def test_int_to_bool_conversion(self):
        prog = Program(body=[
            FunctionDef(
                name="main",
                params=[],
                return_type="int",
                body=[
                    VarDecl("x", "int", Literal("0")),
                    VarDecl("x_bool", "bool", CallExpr(Identifier("bool"), [Identifier("x")])),
                    ExprStmt(CallExpr(Identifier("print"), [Identifier("x_bool")])),
                    ReturnStmt(Literal("0"))
                ]
            )
        ])
        output = codegen_output(prog)
        assert_contains_all(self, output, [
            "int64_t x = 0;",
            "bool x_bool = (x != 0);",
            "pb_print_bool(x_bool);"
        ])

    def test_float_to_bool_conversion(self):
        prog = Program(body=[
            FunctionDef(
                name="main",
                params=[],
                return_type="int",
                body=[
                    VarDecl("y", "float", Literal("0.0")),
                    VarDecl("y_bool", "bool", CallExpr(Identifier("bool"), [Identifier("y")])),
                    ExprStmt(CallExpr(Identifier("print"), [Identifier("y_bool")])),
                    ReturnStmt(Literal("0"))
                ]
            )
        ])
        output = codegen_output(prog)
        assert_contains_all(self, output, [
            "double y = 0.0;",
            "bool y_bool = (y != 0.0);",
            "pb_print_bool(y_bool);"
        ])

    # def test_list_float_conversion(self):
    #     prog = Program(body=[
    #         FunctionDef(
    #             name="main",
    #             params=[],
    #             return_type="int",
    #             body=[
    #                 VarDecl("arr", "list[float]", ListExpr(
    #                     elements=[Literal("1.1"), Literal("2.2"), Literal("3.3")],
    #                     elem_type="float",
    #                     inferred_type="list[float]"
    #                 )),
    #                 AssignStmt(
    #                     target=IndexExpr(Identifier("arr", inferred_type="list[float]"), Literal("0")),
    #                     value=CallExpr(Identifier("float"), [Literal("4")]),
    #                     inferred_type="float"
    #                 ),
    #                 ExprStmt(CallExpr(Identifier("print"), [Identifier("arr", inferred_type="list[float]")])),
    #                 ReturnStmt(Literal("0"))
    #             ]
    #         )
    #     ])
    #     output = codegen_output(prog)
    #     assert_contains_all(self, output, [
    #         "double __tmp_list_1[] = {1.1, 2.2, 3.3};",
    #         "List_float arr = (List_float){ .len=3, .data=__tmp_list_1 };",
    #         "list_float_set(&arr, 0, (float)(4));",
    #         "list_float_print(&arr);"
    #     ])

    def test_set_literal(self):
        prog = Program(body=[
            FunctionDef(
                name="main",
                params=[],
                return_type="int",
                body=[
                    VarDecl("s", "set[int]", SetExpr(
                        elements=[Literal("1"), Literal("2")],
                        elem_type="int",
                        inferred_type="set[int]"
                    )),
                    ExprStmt(CallExpr(Identifier("print"), [Identifier("s")])),
                    ReturnStmt(Literal("0"))
                ],
                globals_declared=None
            )
        ])
        output = codegen_output(prog)
        assert_contains_all(self, output, [
            "int64_t __tmp_set_1[] = {1, 2}",
            "Set_int s = (Set_int){ .len=2, .data=__tmp_set_1 };",
            "set_int_print(&s);",
            "return 0;",
        ])

    def test_set_custom_type_macro(self):
        prog = Program(body=[
            ClassDef(name="Player", base=None, fields=[], methods=[]),
            FunctionDef(
                name="main",
                params=[],
                return_type="int",
                body=[
                    VarDecl(
                        "s",
                        "set[Player]",
                        SetExpr(elements=[], elem_type="Player", inferred_type="set[Player]")
                    ),
                    ReturnStmt(Literal("0"))
                ],
                globals_declared=None
            )
        ])

        TypeChecker().check(prog)
        cg = CodeGen()
        cg.generate_header(prog)
        cg.generate(prog)
        macros = cg.generate_types_header()
        self.assertIn("PB_DECLARE_SET(Player, struct Player *)", macros)

    def test_list_custom_type_macro(self):
        prog = Program(body=[
            ClassDef(name="Enemy", base=None, fields=[], methods=[]),
            FunctionDef(
                name="main",
                params=[],
                return_type="int",
                body=[
                    VarDecl(
                        "lst",
                        "list[Enemy]",
                        ListExpr(elements=[], elem_type="Enemy", inferred_type="list[Enemy]")
                    ),
                    ReturnStmt(Literal("0"))
                ],
                globals_declared=None
            )
        ])

        TypeChecker().check(prog)
        cg = CodeGen()
        cg.generate_header(prog)
        cg.generate(prog)
        macros = cg.generate_types_header()
        self.assertIn("PB_DECLARE_LIST(Enemy, struct Enemy *)", macros)

    def test_dict_custom_type_macro(self):
        prog = Program(body=[
            ClassDef(name="Item", base=None, fields=[], methods=[]),
            FunctionDef(
                name="main",
                params=[],
                return_type="int",
                body=[
                    VarDecl(
                        "d",
                        "dict[str, Item]",
                        DictExpr(keys=[], values=[], elem_type="Item", inferred_type="dict[str, Item]")
                    ),
                    ReturnStmt(Literal("0"))
                ],
                globals_declared=None
            )
        ])

        TypeChecker().check(prog)
        cg = CodeGen()
        cg.generate_header(prog)
        cg.generate(prog)
        macros = cg.generate_types_header()
        self.assertIn("PB_DECLARE_DICT(Item, struct Item *)", macros)

    def test_list_conversion_functions(self):
        prog = Program(body=[
            FunctionDef(
                name="main",
                params=[],
                return_type="int",
                body=[
                    VarDecl("arr", "list[int]", ListExpr(
                        elements=[Literal("1"), Literal("2"), Literal("3")],
                        elem_type="int",
                        inferred_type="list[int]"
                    )),
                    AssignStmt(
                        target=IndexExpr(Identifier("arr", inferred_type="list[int]"), Literal("0")),
                        value=CallExpr(Identifier("int"), [Literal("4.5")]),
                        inferred_type="int"
                    ),
                    ExprStmt(CallExpr(Identifier("print"), [Identifier("arr", inferred_type="list[int]")])),

                    VarDecl("arr2", "list[str]", ListExpr(
                        elements=[StringLiteral("1"), StringLiteral("2"), StringLiteral("3")],
                        elem_type="str",
                        inferred_type="list[str]"
                    )),
                    AssignStmt(
                        target=IndexExpr(Identifier("arr2", inferred_type="list[str]"), Literal("0")),
                        value=CallExpr(Identifier("str"), [Literal("4")]),
                        inferred_type="str"
                    ),
                    ExprStmt(CallExpr(Identifier("print"), [Identifier("arr2", inferred_type="list[str]")])),

                    VarDecl("arr3", "list[float]", ListExpr(
                        elements=[Literal("1.1"), Literal("2.2"), Literal("3.3")],
                        elem_type="float",
                        inferred_type="list[float]"
                    )),
                    AssignStmt(
                        target=IndexExpr(Identifier("arr3", inferred_type="list[float]"), Literal("0")),
                        value=CallExpr(Identifier("float"), [Literal("4")]),
                        inferred_type="float"
                    ),
                    ExprStmt(CallExpr(Identifier("print"), [Identifier("arr3", inferred_type="list[float]")])),

                    VarDecl("arr4", "list[bool]", ListExpr(
                        elements=[Literal("True"), Literal("False")],
                        elem_type="bool",
                        inferred_type="list[bool]"
                    )),
                    AssignStmt(
                        target=IndexExpr(Identifier("arr4", inferred_type="list[bool]"), Literal("0")),
                        value=CallExpr(Identifier("bool"), [Literal("1")]),
                        inferred_type="bool"
                    ),
                    ExprStmt(CallExpr(Identifier("print"), [Identifier("arr4", inferred_type="list[bool]")])),
                    ReturnStmt(Literal("0"))
                ]
            )
        ])
        output = codegen_output(prog)
        assert_contains_all(self, output, [
            "list_int_set(&arr, 0, (int64_t)(4.5));",
            "list_str_set(&arr2, 0, pb_format_int(4));",
            "list_float_set(&arr3, 0, (double)(4));",
            "list_bool_set(&arr4, 0, (1 != 0));",
        ])

    def test_if_name_main_guard_codegen(self):
        prog = Program(body=[
            VarDecl("x", "int", Literal("1")),
            FunctionDef(
                name="main",
                params=[],
                return_type="None",
                body=[
                    ExprStmt(
                        CallExpr(
                            Identifier("print"),
                            [FStringLiteral(parts=[FStringExpr(BinOp(Identifier("x"), "*", Literal("2.0")))])],
                        )
                    ),
                    ExprStmt(
                        CallExpr(
                            Identifier("print"),
                            [FStringLiteral(parts=[FStringExpr(BinOp(Identifier("x"), "*", Literal("False")))])],
                        )
                    ),
                ],
                globals_declared=None,
            ),
            FunctionDef(
                name="init",
                params=[],
                return_type="None",
                body=[ExprStmt(CallExpr(Identifier("print"), [StringLiteral("init runs")]))],
                globals_declared=None,
            ),
        ])

        output = codegen_output(prog)
        self.assertIn('int64_t x = 1;', output)
        self.assertIn('pb_print_str((snprintf(__fbuf, 256, "%s", pb_format_double((x * 2.0))), __fbuf));', output)
        self.assertIn('pb_print_str((snprintf(__fbuf, 256, "%lld", (x * false)), __fbuf));', output)

    def test_global_class_instances_codegen(self):
        prog = Program(body=[
            ClassDef(name="Empty", base=None, fields=[], methods=[]),
            ClassDef(
                name="ClassWithUserDefinedAttr",
                base=None,
                fields=[VarDecl("uda", "Empty", CallExpr(Identifier("Empty"), []))],
                methods=[]
            ),
            VarDecl("e", "Empty", CallExpr(Identifier("Empty"), [])),
            VarDecl("uda", "ClassWithUserDefinedAttr", CallExpr(Identifier("ClassWithUserDefinedAttr"), [])),
            FunctionDef(name="main", params=[], body=[ReturnStmt(Literal("0"))], return_type="int", globals_declared=None)
        ])

        output = codegen_output(prog)
        assert_contains_all(self, output, [
            "__attribute__((constructor)) static void main__init_globals",
            "struct Empty __tmp_empty_",
            "struct ClassWithUserDefinedAttr __tmp_classwithuserdefinedattr_",
        ])

    def test_len_builtin(self):
        prog = Program(body=[
            FunctionDef(
                name="main",
                params=[],
                return_type="int",
                body=[
                    VarDecl("arr", "list[int]", ListExpr(elements=[Literal("1"), Literal("2"), Literal("3")], elem_type="int", inferred_type="list[int]")),
                    VarDecl("l", "int", CallExpr(Identifier("len"), [Identifier("arr", inferred_type="list[int]")])),
                    ExprStmt(CallExpr(Identifier("print"), [Identifier("l", inferred_type="int")])),
                    ReturnStmt(Literal("0"))
                ],
                globals_declared=None
            )
        ])
        output = codegen_output(prog)
        assert_contains_all(self, output, [
            "int64_t __tmp_list_1[] = {1, 2, 3};",
            "List_int arr = (List_int){ .len=3, .data=__tmp_list_1 };",
            "int64_t l = arr.len;",
            "pb_print_int(l);",
        ])

    def test_list_methods_codegen(self):
        prog = Program(body=[
            FunctionDef(
                name="main",
                params=[],
                return_type="int",
                body=[
                    VarDecl("arr", "list[int]", ListExpr(elements=[Literal("1"), Literal("2")], elem_type="int", inferred_type="list[int]")),
                    ExprStmt(CallExpr(AttributeExpr(Identifier("arr"), "append"), [Literal("3")])),
                    VarDecl("x", "int", CallExpr(AttributeExpr(Identifier("arr"), "pop"), [])),
                    VarDecl("r", "bool", CallExpr(AttributeExpr(Identifier("arr"), "remove"), [Literal("1")])),
                    ReturnStmt(Literal("0"))
                ],
                globals_declared=None
            )
        ])
        output = codegen_output(prog)
        assert_contains_all(self, output, [
            "int64_t __tmp_list_1[] = {1, 2};",
            "List_int arr = (List_int){ .len=2, .data=__tmp_list_1 };",
            "list_int_append(&arr, 3);",
            "int64_t x = list_int_pop(&arr);",
            "bool r = list_int_remove(&arr, 1);",
            "return 0;",
        ])


if __name__ == "__main__":
    unittest.main()
