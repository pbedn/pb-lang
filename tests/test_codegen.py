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

if __name__ == "__main__":
    unittest.main()
