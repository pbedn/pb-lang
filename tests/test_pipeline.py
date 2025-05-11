import unittest
from lexer import Lexer
from parser import Parser
from type_checker import TypeChecker, TypeError
from codegen import CodeGen


class TestCodeGenFromSource(unittest.TestCase):
    def compile_pipeline(self, code: str) -> str:
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        print(tokens)

        parser = Parser(tokens)
        ast = parser.parse()

        checker = TypeChecker()
        checker.check(ast)

        codegen = CodeGen()
        return codegen.generate(ast)

    def test_var_decl_from_source(self):
        code = (
            "x: int = 42\n"
        )
        c_code = self.compile_pipeline(code)
        self.assertIn("int64_t x = 42;", c_code)

    def test_assign_stmt_from_source(self):
        code = (
            "x: int = 0\n"
            "x = 42\n"
        )
        c_code = self.compile_pipeline(code)
        self.assertIn("int64_t x = 0;", c_code)
        self.assertIn("x = 42;", c_code)

    def test_aug_assign_stmt_from_source(self):
        code = (
            "x: int = 0\n"
            "x += 1\n"
        )
        c_code = self.compile_pipeline(code)
        self.assertIn("int64_t x = 0;", c_code)
        self.assertIn("x += 1;", c_code)

    def test_return_stmt_from_source(self):
        code = (
            "def main() -> int:\n"
            "    return 0\n"
        )
        c_code = self.compile_pipeline(code)
        self.assertIn("return 0;", c_code)

    def test_pass_stmt_from_source(self):
        code = (
            "def noop() -> None:\n"
            "    pass\n"
        )
        c_code = self.compile_pipeline(code)
        self.assertIn(";  // pass", c_code)

    def test_break_continue_from_source(self):
        code = (
            "while True:\n"
            "    break\n"
            "    continue\n"
        )
        c_code = self.compile_pipeline(code)
        self.assertIn("break;", c_code)
        self.assertIn("continue;", c_code)

    def test_expr_stmt_call_from_source(self):
        code = (
            "def f(x: int) -> None:\n"
            "    pass\n"
            "\n"
            "def main() -> int:\n"
            "    f(1)\n"
            "    return 0\n"
        )
        c_code = self.compile_pipeline(code)
        self.assertIn("f(1);", c_code)
        self.assertIn("return 0;", c_code)

    def test_return_and_pass_statements(self):
        code = (
            "def main() -> int:\n"
            "    pass\n"
            "    return 0\n"
        )
        with self.assertRaises(TypeError):
            self.compile_pipeline(code)

    def test_if_stmt_from_source(self):
        code = (
            "if True:\n"
            "    pass\n"
            "else:\n"
            "    pass\n"
        )
        c = self.compile_pipeline(code)
        self.assertIn("if (True) {", c)
        self.assertIn("else {", c)

    def test_while_stmt_from_source(self):
        code = (
            "while True:\n"
            "    pass\n"
        )
        c = self.compile_pipeline(code)
        self.assertIn("while (True) {", c)

    # def test_for_stmt_from_source(self):
    #     code = (
    #         "arr: list[int] = [1, 2, 3]\n"
    #         "for x in arr:\n"
    #         "    pass\n"
    #     )
    #     c = self.compile_pipeline(code)
    #     self.assertIn("for (int __i_x = 0;", c)
    #     self.assertIn("x = arr.data[__i_x];", c)

    def test_function_def_from_source(self):
        code = (
            "def main(a: int) -> int:\n"
            "    return a\n"
        )
        c = self.compile_pipeline(code)
        self.assertIn("int64_t main(int64_t a)", c)
        self.assertIn("return a;", c)




