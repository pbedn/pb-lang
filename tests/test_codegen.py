import unittest
from codegen import CCodeGenerator
from lang_ast import *

class TestCodegen(unittest.TestCase):

    def test_generate_print(self):
        ast = Program([
            FunctionDef(
                name="main",
                params=[],
                body=[CallExpr(func=Identifier("print"), args=[Literal("Test")]), ReturnStmt(Literal(0))],
                return_type="int"
            )
        ])
        c_code = CCodeGenerator().generate(ast)
        self.assertIn('printf("%s\\n", "Test");', c_code)

    def test_generate_binop_and_call(self):
        ast = Program([
            FunctionDef(
                name="add",
                params=[("a", "int"), ("b", "int")],
                body=[ReturnStmt(BinOp(Identifier("a"), "+", Identifier("b")))],
                return_type="int"
            ),
            FunctionDef(
                name="main",
                params=[],
                body=[AssignStmt("x", CallExpr(Identifier("add"), [Literal(1), Literal(2)])), ReturnStmt(Identifier("x"))],
                return_type="int"
            )
        ])
        c_code = CCodeGenerator().generate(ast)
        self.assertIn("int add(int a, int b)", c_code)
        self.assertIn("int x = add(1, 2);", c_code)
        self.assertIn("return x;", c_code)

    def test_codegen_global_assignment_with_global_ast(self):
        ast = Program([
            AssignStmt("x", Literal(10)),
            FunctionDef(
                name="main",
                params=[],
                body=[
                    GlobalStmt(["x"]),
                    AssignStmt("x", Literal(20)),
                    ReturnStmt(Identifier("x"))
                ],
                return_type="int",
                globals_declared={"x"}
            )
        ])
        c_code = CCodeGenerator(global_vars={"x"}).generate(ast)

        # Check top-level declaration
        self.assertIn("int x = 10;", c_code)
        # Check inside function: assignment only (no redeclare)
        self.assertIn("x = 20;", c_code)
        self.assertNotIn("int x = 20;", c_code)

    def test_codegen_local_shadowing_without_global_ast(self):
        ast = Program([
            AssignStmt("x", Literal(10)),
            FunctionDef(
                name="main",
                params=[],
                body=[
                    AssignStmt("x", Literal(5)),
                    ReturnStmt(Identifier("x"))
                ],
                return_type="int",
                globals_declared=set()
            )
        ])
        c_code = CCodeGenerator(global_vars={"x"}).generate(ast)

        # Check top-level declaration
        self.assertIn("int x = 10;", c_code)
        # Check inside function: local shadowing (must declare)
        self.assertIn("int x = 5;", c_code)

    def test_global_float_vardecl_generates_double(self):
        ast = Program([
            VarDecl("threshold", "float", Literal(50.0)),
            FunctionDef(
                name="main",
                params=[],
                body=[
                    ReturnStmt(Literal(0))
                ],
                return_type="int"
            )
        ])
        c_code = CCodeGenerator().generate(ast)
        self.assertIn("double threshold = 50.0;", c_code)

    def test_local_float_vardecl_generates_double(self):
        ast = Program([
            FunctionDef(
                name="main",
                params=[],
                body=[
                    VarDecl("threshold", "float", Literal(50.0)),
                    ReturnStmt(Literal(0))
                ],
                return_type="int"
            )
        ])
        c_code = CCodeGenerator().generate(ast)
        self.assertIn("double threshold = 50.0;", c_code)

    def test_function_param_float_is_double(self):
        ast = Program([
            FunctionDef(
                name="show",
                params=[("value", "float")],
                body=[
                    ReturnStmt(Literal(0))
                ],
                return_type="int"
            )
        ])
        c_code = CCodeGenerator().generate(ast)
        self.assertIn("int show(double value)", c_code)

    def test_print_float_uses_printf_f_format(self):
        ast = Program([
            FunctionDef(
                name="main",
                params=[],
                body=[
                    CallExpr(Identifier("print"), [Literal(50.0)]),
                    ReturnStmt(Literal(0))
                ],
                return_type="int"
            )
        ])
        c_code = CCodeGenerator().generate(ast)
        self.assertIn('printf("%f\\n", 50.0);', c_code)

    def test_list_of_floats_codegen(self):
        prog = Program([
            FunctionDef(
                name="main",
                params=[],
                body=[
                    AssignStmt("floats", ListExpr([Literal(1.0), Literal(2.0), Literal(3.0)])),
                    ReturnStmt(Literal(0))
                ],
                return_type="int"
            )
        ])
        c_code = CCodeGenerator().generate(prog)
        self.assertIn("double floats[] = { 1.0, 2.0, 3.0 };", c_code)

    def test_augassign_float_codegen(self):
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
        c_code = CCodeGenerator().generate(prog)
        self.assertIn("double value = 1.5;", c_code)
        self.assertIn("value += 2.5;", c_code)

    def test_complex_logical_expr_codegen(self):
        prog = Program([
            FunctionDef(
                name="main",
                params=[("x", "bool"), ("y", "bool"), ("z", "bool")],
                body=[
                    IfStmt(
                        condition=BinOp(
                            BinOp(Identifier("x"), "and", UnaryOp("not", Identifier("y"))),
                            "or",
                            Identifier("z")
                        ),
                        then_body=[ReturnStmt(Literal(1))],
                        else_body=[ReturnStmt(Literal(0))]
                    )
                ],
                return_type="int"
            )
        ])
        c_code = CCodeGenerator().generate(prog)
        self.assertIn("if (((x && (!y)) || z))", c_code)

    def test_function_call_with_float_param_codegen(self):
        prog = Program([
            FunctionDef(
                name="square",
                params=[("x", "float")],
                body=[
                    ReturnStmt(BinOp(Identifier("x"), "*", Identifier("x")))
                ],
                return_type="float"
            ),
            FunctionDef(
                name="main",
                params=[],
                body=[
                    CallExpr(Identifier("print"), [CallExpr(Identifier("square"), [Literal(2.5)])]),
                    ReturnStmt(Literal(0))
                ],
                return_type="int"
            )
        ])
        c_code = CCodeGenerator().generate(prog)
        self.assertIn("double square(double x)", c_code)
        self.assertIn('printf("%f\\n", square(2.5));', c_code)



if __name__ == "__main__":
    unittest.main()
