import unittest
from lexer import Lexer
from parser import Parser
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

if __name__ == "__main__":
    unittest.main()
