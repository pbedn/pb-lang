import unittest
from lang_ast import *
from codegen import CodeGen

class TestCodeGenFromAST(unittest.TestCase):

    def test_var_decl_int(self):
        prog = Program(body=[
            VarDecl(name="x", declared_type="int", value=Literal("42"))
        ])
        c = CodeGen().generate(prog)
        self.assertIn("int64_t x = 42;", c)

    def test_assign_stmt(self):
        prog = Program(body=[
            VarDecl("x", "int", Literal("0")),
            AssignStmt(target=Identifier("x"), value=Literal("42"))
        ])
        c_code = CodeGen().generate(prog)
        self.assertIn("int64_t x = 0;", c_code)
        self.assertIn("x = 42;", c_code)

    def test_aug_assign_stmt(self):
        prog = Program(body=[
            VarDecl("x", "int", Literal("0")),
            AugAssignStmt(Identifier("x"), "+=", Literal("1"))
        ])
        c_code = CodeGen().generate(prog)
        self.assertIn("x += 1;", c_code)

    def test_return_stmt(self):
        prog = Program(body=[
            FunctionDef(
                name="main",
                params=[],
                return_type="int",
                body=[ReturnStmt(Literal("0"))]
            )
        ])
        c_code = CodeGen().generate(prog)
        self.assertIn("return 0;", c_code)

    def test_pass_stmt(self):
        prog = Program(body=[PassStmt()])
        c_code = CodeGen().generate(prog)
        self.assertIn(";  // pass", c_code)

    def test_break_continue(self):
        prog = Program(body=[BreakStmt(), ContinueStmt()])
        c_code = CodeGen().generate(prog)
        self.assertIn("break;", c_code)
        self.assertIn("continue;", c_code)


    def test_expr_stmt_call(self):
        prog = Program(body=[
            ExprStmt(CallExpr(func=Identifier("f"), args=[Literal("1")]))
        ])
        c_code = CodeGen().generate(prog)
        self.assertIn("f(1);", c_code)

    def test_if_stmt(self):
        prog = Program(body=[
            IfStmt(branches=[
                IfBranch(Literal("True"), [PassStmt()]),
                IfBranch(None, [PassStmt()])
            ])
        ])
        c = CodeGen().generate(prog)
        self.assertIn("if (True) {", c)
        self.assertIn("else {", c)

    def test_while_stmt(self):
        prog = Program(body=[
            WhileStmt(condition=Literal("True"), body=[PassStmt()])
        ])
        c = CodeGen().generate(prog)
        self.assertIn("while (True) {", c)

    def test_for_stmt(self):
        prog = Program(body=[
            ForStmt("x", Identifier("arr"), [PassStmt()])
        ])
        c = CodeGen().generate(prog)
        self.assertIn("for (int __i_x = 0;", c)
        self.assertIn("x = arr.data[__i_x];", c)

    def test_function_def(self):
        fn = FunctionDef(
            name="main",
            params=[Parameter("a", "int")],
            return_type="int",
            body=[ReturnStmt(Identifier("a"))]
        )
        prog = Program(body=[fn])
        c = CodeGen().generate(prog)
        self.assertIn("int64_t main(int64_t a)", c)
        self.assertIn("return a;", c)




    

