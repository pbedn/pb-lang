import os
import unittest
from lexer import Lexer
from parser import Parser
from type_checker import TypeChecker, TypeError
from codegen import CodeGen

BASE_DIR = os.path.dirname(__file__)

class TestCodeGenFromSource(unittest.TestCase):
    def compile_pipeline(self, code: str) -> str:
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        # print(tokens)

        parser = Parser(tokens)
        ast = parser.parse()

        checker = TypeChecker()
        checker.check(ast)

        codegen = CodeGen()
        return codegen.generate(ast)

    # ────────────────────────────────────────────────────────────────
    # Reference Test
    # ────────────────────────────────────────────────────────────────
    def test_lang_pb_codegen_matches_expected(self):
        self.maxDiff = None
        pb_path = os.path.join(BASE_DIR, "../ref/lang.pb")
        expected_c_path = os.path.join(BASE_DIR, "../ref/ref_lang.c")
        with open(pb_path) as f:
            source = f.read()

        with open(expected_c_path) as f:
            expected_c = f.read()

        generated_c = self.compile_pipeline(source)

        # Optional: normalize line endings to be OS-independent
        expected_c_normalized = expected_c.replace("\r\n", "\n").strip()
        generated_c_normalized = generated_c.replace("\r\n", "\n").strip()

        # Assert full match
        self.assertEqual(
            generated_c_normalized, expected_c_normalized,
            msg="Generated C code does not match the expected output."
        )

    # ────────────────────────────────────────────────────────────────
    # Small unit tests
    # ────────────────────────────────────────────────────────────────
    def test_hello_world(self):
        code = (
            "def main() -> int:\n"
            "    print(\"Hello, world!\")\n"
            "    return 0\n"
        )
        c_code = self.compile_pipeline(code)
        self.assertIn('pb_print_str("Hello, world!");', c_code)
        self.assertIn('return 0;', c_code)

    def test_var_decl_from_source(self):
        code = (
            "x: int = 42\n"
        )
        c_code = self.compile_pipeline(code)
        self.assertIn("int64_t x = 42;", c_code)

    def test_assign_stmt_from_source(self):
        code = (
            "def main() -> int:\n"
            "    x: int = 0\n"
            "    x = 42\n"
            "    return 0\n"
        )
        c_code = self.compile_pipeline(code)
        self.assertIn("int64_t x = 0;", c_code)
        self.assertIn("x = 42;", c_code)

    def test_f_string_interpolation_from_source(self):
        code = (
            "def main() -> int:\n"
            "    name: str = \"Alice\"\n"
            "    print(f\"Hello, {name}!\")\n"
            "    return 0\n"
        )
        c = self.compile_pipeline(code)
        self.assertIn('pb_print_str((snprintf(__fbuf, 256, "Hello, %s!", name), __fbuf));', c)

    def test_aug_assign_stmt_from_source(self):
        code = (
            "def main() -> int:\n"
            "    x: int = 0\n"
            "    x += 1\n"
            "    return 0\n"
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
            "def main() -> int:\n"
            "    for i in range(3):\n"
            "        if i == 1:\n"
            "            continue\n"
            "        if i == 2:\n"
            "            break\n"
            "        print(i)\n"
            "    return 0\n"
        )
        c_code = self.compile_pipeline(code)
        self.assertIn("break;", c_code)
        self.assertIn("continue;", c_code)

    def test_break_outside_loop_should_fail(self):
        code = (
        "def main() -> int:\n"
        "    break\n"
        "    return 0\n"
        )
        with self.assertRaises(Exception) as ctx:
            self.compile_pipeline(code)
        self.assertIn("'break' outside loop at 2,5", str(ctx.exception))

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
            "def main(a: int) -> int:\n"
            "    if True:\n"
            "        pass\n"
            "    else:\n"
            "        pass\n"
            "    return a\n"
        )
        c = self.compile_pipeline(code)
        self.assertIn("if (true) {", c)
        self.assertIn("else  {", c)
        self.assertIn(";  // pass", c)

    # loops ------------------------------------------------------

    def test_while_stmt_from_source(self):
        code = (
            "def main(a: int) -> int:\n"
            "    while True:\n"
            "        pass\n"
            "    return a\n"
        )
        c = self.compile_pipeline(code)
        self.assertIn("while (true) {", c)
        self.assertIn(";  // pass", c)

    @unittest.skip("Not supported yet")
    def test_for_stmt_from_source(self):
        code = (
            "def main() -> int:\n"
            "    arr: list[int] = [1, 2, 3]\n"
            "    for x in arr:\n"
            "        print(x)\n"
            "    return 0\n"
        )
        c = self.compile_pipeline(code)
        self.assertIn("for (int __i_x = 0;", c)
        self.assertIn("x = arr.data[__i_x];", c)

    # function ------------------------------------------------------

    def test_function_def_from_source(self):
        code = (
            "def main(a: int) -> int:\n"
            "    return a\n"
        )
        c = self.compile_pipeline(code)
        self.assertIn("int main(", c)
        # self.assertIn("int64_t a)", c)
        self.assertIn("return a;", c)

    # list ------------------------------------------------------

    def test_list_index_expr_from_source(self):
        code = (
            "def main() -> int:\n"
            "    nums: list[int] = [10, 20, 30]\n"
            "    first: int = nums[0]\n"
            "    print(first)\n"
            "    return 0\n"
        )
        c = self.compile_pipeline(code)
        self.assertIn("List_int nums =", c)
        self.assertIn("int64_t first = nums.data[0];", c)

    @unittest.skip("Not supported yet")
    def test_list_of_bools(self):
        code = (
            "def main() -> int:\n"
            "    flags: list[bool] = [True, False, True]\n"
            "    x: bool = flags[0]\n"
            "    print(x)\n"
            "    return 0\n"
        )
        c_code = self.compile_pipeline(code)
        self.assertIn('bool flags[] = { true, false, true };', c_code)
        self.assertIn('bool x = flags[0];', c_code)
        self.assertIn('printf("%s\\n", x ? "true" : "false");', c_code)

    @unittest.skip("Not supported yet")
    def test_list_mixed_types_error(self):
        code = (
            "def main() -> int:\n"
            "    stuff = [1, True, \"oops\"]\n"
            "    return 0\n"
        )
        with self.assertRaises(Exception) as ctx:
            self.compile_pipeline(code)
        self.assertIn("All elements of a list must have the same type", str(ctx.exception))

    # dict ------------------------------------------------------

    def test_dict_literal_access_from_source(self):
        code = (
            "def main() -> int:\n"
            "    d: dict[str, int] = {\"a\": 1, \"b\": 2}\n"
            "    print(d[\"a\"])\n"
            "    return 0\n"
        )
        c = self.compile_pipeline(code)
        self.assertIn("Dict_str_int d =", c)
        self.assertIn('pb_print_int(pb_dict_get(d, "a"));', c)

    def test_is_and_is_not_from_source(self):
        code = (
            "def main() -> int:\n"
            "    x: int = 10\n"
            "    y: int = 10\n"
            "    if x is y:\n"
            "        print(\"same\")\n"
            "    if x is not 20:\n"
            "        print(\"not 20\")\n"
            "    return 0\n"
        )
        c = self.compile_pipeline(code)
        self.assertIn("if ((x == y)) {", c)
        self.assertIn("if ((x != 20)) {", c)

    def test_logical_and_not_from_source(self):
        code = (
            "def main() -> int:\n"
            "    x: bool = True\n"
            "    y: bool = False\n"
            "    if x and not y:\n"
            "        print(\"ok\")\n"
            "    return 0\n"
        )
        c = self.compile_pipeline(code)
        self.assertIn("if ((x && !(y))) {", c)

    # class ------------------------------------------------------

    def test_class_instantiation_and_method_call(self):
        code = (
            "class Player:\n"
            "    def __init__(self) -> None:\n"
            "        self.hp = 100\n"
            "    def get_hp(self) -> int:\n"
            "        return self.hp\n"
            "\n"
            "def main() -> int:\n"
            "    p: Player = Player()\n"
            "    print(p.get_hp())\n"
            "    return 0\n"
        )
        c = self.compile_pipeline(code)
        self.assertIn("struct Player __tmp_", c)
        self.assertIn("Player____init__(&__tmp_", c)
        self.assertIn("pb_print_int(Player__get_hp(p));", c)

    def test_class_inheritance_and_override(self):
        """type checker doesn't allow calling constructors for subclasses
        unless __init__ is defined on that class directly."""
        code = (
            "class Base:\n"
            "    def greet(self) -> None:\n"
            "        print(\"base\")\n"
            "class Child(Base):\n"
            "    def __init__(self) -> None:\n"
            "        pass\n"
            "    def greet(self) -> None:\n"
            "        print(\"child\")\n"
            "def main() -> int:\n"
            "    c: Child = Child()\n"
            "    c.greet()\n"
            "    return 0\n"
        )
        c = self.compile_pipeline(code)
        self.assertIn("struct Child __tmp_", c)
        self.assertIn("pb_print_str(\"child\");", c)

    # global ------------------------------------------------------

    def test_global_variable_in_method(self):
        code = (
            "counter: int = 0\n"
            "class A:\n"
            "    def bump(self) -> None:\n"
            "        global counter\n"
            "        counter += 1\n"
        )
        c = self.compile_pipeline(code)
        self.assertIn("int64_t counter = 0;", c)
        self.assertIn("/* global counter */", c)
        self.assertIn("counter += 1;", c)

    def test_global_read_without_global(self):
        code = (
            "x: int = 100\n"
            "\n"
            "def main() -> int:\n"
            "    print(x)\n"
            "    return x\n"
        )
        c_code = self.compile_pipeline(code)
        self.assertIn('int64_t x = 100;', c_code)
        self.assertIn('pb_print_int(x);', c_code)

    def test_global_write_with_global(self):
        code = (
            "x:int = 10\n"
            "\n"
            "def main() -> int:\n"
            "    global x\n"
            "    x = 20\n"
            "    print(x)\n"
            "    return x\n"
        )
        c_code = self.compile_pipeline(code)
        self.assertIn('int64_t x = 10;', c_code)
        self.assertIn('x = 20;', c_code)

    def test_global_write_without_global_is_local(self):
        code = (
            "x: int = 10\n"
            "\n"
            "def main() -> int:\n"
            "    x: int = 5\n"
            "    print(x)\n"
            "    return x\n"
        )
        c_code = self.compile_pipeline(code)
        self.assertIn('int64_t x = 10;', c_code)  # global var
        self.assertIn('int64_t x = 5;', c_code)   # local shadowing var

    def test_global_stmt_without_existing_global_should_fail(self):
        code = (
            "def main() -> int:\n"
            "    global y\n"
            "    y = 5\n"
            "    return y\n"
        )
        with self.assertRaises(TypeError) as ctx:
            self.compile_pipeline(code)
        self.assertIn("Global variable 'y' used before declaration", str(ctx.exception))

    # built-in functions ------------------------------------------------------

    def test_range_two_args(self):
        code = (
            "def main() -> int:\n"
            "    for i in range(0, 3):\n"
            "        print(i)\n"
            "    return 0\n"
        )
        c_code = self.compile_pipeline(code)
        self.assertIn("for (int64_t i = 0; i < 3; ++i)", c_code)
        self.assertIn('pb_print_int(i)', c_code)

    def test_range_one_arg(self):
        code = (
            "def main() -> int:\n"
            "    for x in range(2):\n"
            "        print(x)\n"
            "    return 0\n"
        )
        c_code = self.compile_pipeline(code)
        self.assertIn("for (int64_t x = 0; x < 2; ++x)", c_code)
        self.assertIn('pb_print_int(x)', c_code)

    def test_range_type_error(self):
        code = (
            "def main() -> int:\n"
            "    for x in range(\"bad\"):\n"
            "        print(x)\n"
            "    return 0\n"
        )
        with self.assertRaises(Exception) as ctx:
            self.compile_pipeline(code)
        self.assertIn("Argument 1 expected int, got str", str(ctx.exception))

    def test_range_argument_count_error(self):
        code = (
            "def main() -> int:\n"
            "    for x in range(1, 2, 3):\n"
            "        print(x)\n"
            "    return 0\n"
        )
        with self.assertRaises(Exception) as ctx:
            self.compile_pipeline(code)
        self.assertIn("Function 'range' expects between 1 and 2 arguments, got 3", str(ctx.exception))

    def test_for_range_and_control_flow_from_source(self):
        code = (
            "def main() -> int:\n"
            "    for i in range(0, 5):\n"
            "        if i == 2:\n"
            "            continue\n"
            "        if i == 4:\n"
            "            break\n"
            "        print(i)\n"
            "    return 0\n"
        )
        c = self.compile_pipeline(code)
        self.assertIn("for (int64_t i = 0; i < 5; ++i)", c)
        self.assertIn("continue;", c)
        self.assertIn("break;", c)

if __name__ == "__main__":
    unittest.main()
