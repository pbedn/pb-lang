import os
import tempfile
import unittest
from lexer import Lexer
from parser import Parser, ParserError
from type_checker import TypeChecker, TypeError
from codegen import CodeGen
from pb_pipeline import compile_code_to_ast, compile_code_to_c_and_h

BASE_DIR = os.path.dirname(__file__)

class TestCodeGenFromSource(unittest.TestCase):
    def compile_pipeline(self, code: str, pb_path: str | None = None) -> tuple:
        h, c, *_ = compile_code_to_c_and_h(code, pb_path=pb_path)
        return h, c

    # ────────────────────────────────────────────────────────────────
    # Reference Test
    # ────────────────────────────────────────────────────────────────
    def test_lang_pb_codegen_matches_expected(self):
        self.maxDiff = None
        pb_path = os.path.join(BASE_DIR, "../ref/lang.pb")
        expected_h_path = os.path.join(BASE_DIR, "../ref/ref_lang.h")
        expected_c_path = os.path.join(BASE_DIR, "../ref/ref_lang.c")
        with open(pb_path) as f:
            source = f.read()

        with open(expected_h_path) as f:
            expected_h = f.read()
        with open(expected_c_path) as f:
            expected_c = f.read()

        generated_h, generated_c, *_ = compile_code_to_c_and_h(
            source,
            module_name="lang",
            pb_path=pb_path,
        )

        # Optional: normalize line endings to be OS-independent
        expected_h_normalized = expected_h.replace("\r\n", "\n").strip()
        expected_c_normalized = expected_c.replace("\r\n", "\n").strip()
        generated_h_normalized = generated_h.replace("\r\n", "\n").strip()
        generated_c_normalized = generated_c.replace("\r\n", "\n").strip()

        # Assert full match
        self.assertEqual(
            generated_h_normalized, expected_h_normalized,
            msg="Generated C header does not match the expected output."
        )
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
        header, c_code = self.compile_pipeline(code)
        self.assertIn('pb_print_str("Hello, world!");', c_code)
        self.assertIn('return 0;', c_code)

    def test_var_decl_from_source(self):
        code = (
            "x: int = 42\n"
        )
        header, c_code = self.compile_pipeline(code)
        self.assertIn("int64_t x = 42;", c_code)

    def test_assign_stmt_from_source(self):
        code = (
            "def main() -> int:\n"
            "    x: int = 0\n"
            "    x = 42\n"
            "    return 0\n"
        )
        header, c_code = self.compile_pipeline(code)
        self.assertIn("int64_t x = 0;", c_code)
        self.assertIn("x = 42;", c_code)

    def test_f_string_interpolation_from_source(self):
        code = (
            "def main() -> int:\n"
            "    name: str = \"Alice\"\n"
            "    print(f\"Hello, {name}!\")\n"
            "    return 0\n"
        )
        h, c = self.compile_pipeline(code)
        self.assertIn('pb_print_str((snprintf(__fbuf, 256, "Hello, %s!", name), __fbuf));', c)

    def test_aug_assign_stmt_from_source(self):
        code = (
            "def main() -> int:\n"
            "    x: int = 0\n"
            "    x += 1\n"
            "    return 0\n"
        )
        header, c_code = self.compile_pipeline(code)
        self.assertIn("int64_t x = 0;", c_code)
        self.assertIn("x += 1;", c_code)

    def test_global_class_instances(self):
        code = (
            "class Empty:\n"
            "    pass\n"
            "\n"
            "class ClassWithUserDefinedAttr:\n"
            "    uda: Empty = Empty()\n"
            "\n"
            "e: Empty = Empty()\n"
            "uda: ClassWithUserDefinedAttr = ClassWithUserDefinedAttr()\n"
            "\n"
            "def main() -> int:\n"
            "    return 0\n"
        )
        h, c = self.compile_pipeline(code)
        self.assertIn("__attribute__((constructor)) static void main__init_globals", c)
        self.assertIn("struct Empty __tmp_empty_", c)
        self.assertIn("struct ClassWithUserDefinedAttr __tmp_classwithuserdefinedattr_", c)

    def test_return_stmt_from_source(self):
        code = (
            "def main() -> int:\n"
            "    return 0\n"
        )
        header, c_code = self.compile_pipeline(code)
        self.assertIn("return 0;", c_code)

    def test_pass_stmt_from_source(self):
        code = (
            "def noop():\n"
            "    pass\n"
        )
        header, c_code = self.compile_pipeline(code)
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
        header, c_code = self.compile_pipeline(code)
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
            "def f(x: int):\n"
            "    pass\n"
            "\n"
            "def main() -> int:\n"
            "    f(1)\n"
            "    return 0\n"
        )
        header, c_code = self.compile_pipeline(code)
        self.assertIn("f(1);", c_code)
        self.assertIn("return 0;", c_code)

    def test_return_and_pass_statements(self):
        code = (
            "def main() -> int:\n"
            "    pass\n"
            "    return 0\n"
        )
        with self.assertRaises(ParserError):
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
        h, c = self.compile_pipeline(code)
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
        h, c = self.compile_pipeline(code)
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
        h, c = self.compile_pipeline(code)
        self.assertIn("for (int __i_x = 0;", c)
        self.assertIn("x = arr.data[__i_x];", c)

    # function ------------------------------------------------------

    def test_function_def_from_source(self):
        code = (
            "def main(a: int) -> int:\n"
            "    return a\n"
        )
        h, c = self.compile_pipeline(code)
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
        h, c = self.compile_pipeline(code)
        self.assertIn("List_int nums =", c)
        self.assertIn("int64_t first = list_int_get(&nums, 0);", c)

    def test_list_of_bools(self):
        code = (
            "def main() -> int:\n"
            "    flags: list[bool] = [True, False, True]\n"
            "    x: bool = flags[0]\n"
            "    print(x)\n"
            "    return 0\n"
        )
        header, c_code = self.compile_pipeline(code)
        self.assertIn('bool __tmp_list_1[] = {true, false, true};', c_code)
        self.assertIn('List_bool flags = (List_bool){ .len=3, .data=__tmp_list_1 };', c_code)
        self.assertIn('bool x = list_bool_get(&flags, 0);', c_code)
        self.assertIn('pb_print_bool(x);', c_code)

    def test_empty_list_assignment_pipeline(self):
        code = (
            "def main() -> int:\n"
            "    b: list[int] = []\n"
            "    b[0] = 1\n"
            "    print(b)\n"
            "    return 0\n"
        )
        header, c_code = self.compile_pipeline(code)
        self.assertIn('list_int_init(&__tmp_list_', c_code)
        self.assertIn('List_int b = __tmp_list_', c_code)
        self.assertIn('list_int_set(&b, 0, 1);', c_code)
        self.assertIn('list_int_print(&b);', c_code)

    def test_set_literal(self):
        code = (
            "def main() -> int:\n"
            "    s: set[int] = {1, 2}\n"
            "    print(s)\n"
            "    return 0\n"
        )
        h, c_code = self.compile_pipeline(code)
        self.assertIn('int64_t __tmp_set_1[] = {1, 2};', c_code)
        self.assertIn('Set_int s = (Set_int){ .len=2, .data=__tmp_set_1 };', c_code)
        self.assertIn('set_int_print(&s);', c_code)

    def test_set_str_literal(self):
        code = (
            "def main() -> int:\n"
            "    s: set[str] = {'a', \"b\"}\n"
            "    print(s)\n"
            "    return 0\n"
        )
        h, c_code = self.compile_pipeline(code)
        self.assertIn('const char * __tmp_set_1[] = {"a", "b"};', c_code)
        self.assertIn('Set_str s = (Set_str){ .len=2, .data=__tmp_set_1 };', c_code)
        self.assertIn('set_str_print(&s);', c_code)

    def test_set_custom_type_decl(self):
        code = (
            "class Player:\n"
            "    pass\n"
            "\n"
            "def main() -> int:\n"
            "    s: set[Player]\n"
            "    return 0\n"
        )
        h, c_code, ast, _ = compile_code_to_c_and_h(code)
        self.assertIn('Set_Player s;', c_code)
        cg = CodeGen()
        cg.generate_header(ast)
        cg.generate(ast)
        macros = cg.generate_types_header()
        self.assertIn('PB_DECLARE_SET(Player, struct Player *)', macros)

    def test_list_index_get_set(self):
        code = (
            "def main() -> int:\n"
            "    nums: list[int] = [10, 20, 30]\n"
            "    first: int = nums[0]\n"
            "    print(first)\n"
            "    print(nums[0])\n"
            "    print(nums)\n"
            "    nums[0] = 123\n"
            "    return 0\n"
        )
        h, c = self.compile_pipeline(code)
        self.assertIn("List_int nums = (List_int){ .len=3, .data=__tmp_list_1 };", c)
        self.assertIn("int64_t first = list_int_get(&nums, 0);", c)
        self.assertIn("pb_print_int(first);", c)
        self.assertIn("pb_print_int(list_int_get(&nums, 0));", c)
        self.assertIn("list_int_print(&nums);", c)
        self.assertIn("list_int_set(&nums, 0, 123);", c)
        self.assertIn("int64_t first = list_int_get(&nums, 0);", c)

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

    def test_dict_int_literal_access_from_source(self):
        code = (
            "def main() -> int:\n"
            "    d: dict[str, int] = {\"a\": 1, \"b\": 2}\n"
            "    print(d[\"a\"])\n"
            "    return 0\n"
        )
        h, c = self.compile_pipeline(code)
        self.assertIn('Pair_str_int __tmp_dict_1[] = {{"a", 1}, {"b", 2}};', c)
        self.assertIn("Dict_str_int d = (Dict_str_int){ .len=2, .data=__tmp_dict_1 };", c)
        self.assertIn('pb_print_int(pb_dict_get_str_int(d, "a"));', c)

    def test_dict_str_literal_access_from_source(self):
        code = (
            "def main() -> int:\n"
            "    d: dict[str, str] = {\"a\": \"sth\", \"b\": \"here\"}\n"
            "    print(d[\"a\"])\n"
            "    return 0\n"
        )
        h, c = self.compile_pipeline(code)
        self.assertIn('Pair_str_str __tmp_dict_1[] = {{"a", "sth"}, {"b", "here"}};', c)
        self.assertIn("Dict_str_str d = (Dict_str_str){ .len=2, .data=__tmp_dict_1 };", c)
        self.assertIn('pb_print_str(pb_dict_get_str_str(d, "a"));', c)

    def test_dict_bool_literal_access_from_source(self):
        code = (
            "def main() -> int:\n"
            "    d: dict[str, bool] = {\"a\": True, \"b\": False}\n"
            "    print(d[\"a\"])\n"
            "    return 0\n"
        )
        h, c = self.compile_pipeline(code)
        self.assertIn('Pair_str_bool __tmp_dict_1[] = {{"a", true}, {"b", false}};', c)
        self.assertIn("Dict_str_bool d = (Dict_str_bool){ .len=2, .data=__tmp_dict_1 };", c)
        self.assertIn('pb_print_bool(pb_dict_get_str_bool(d, "a"));', c)

    def test_dict_float_literal_access_from_source(self):
        code = (
            "def main() -> int:\n"
            "    d: dict[str, float] = {\"a\": 1.0, \"b\": 2.0}\n"
            "    print(d[\"a\"])\n"
            "    return 0\n"
        )
        h, c = self.compile_pipeline(code)
        self.assertIn('Pair_str_float __tmp_dict_1[] = {{"a", 1.0}, {"b", 2.0}};', c)
        self.assertIn("Dict_str_float d = (Dict_str_float){ .len=2, .data=__tmp_dict_1 };", c)
        self.assertIn('pb_print_double(pb_dict_get_str_float(d, "a"));', c)

    # logical ------------------------------------------------------

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
        h, c = self.compile_pipeline(code)
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
        h, c = self.compile_pipeline(code)
        self.assertIn("if ((x && !(y))) {", c)

    def test_chained_comparison_from_source(self):
        code = (
            "def main() -> int:\n"
            "    x: int = 5\n"
            "    if 1 < x < 10:\n"
            "        print(\"ok\")\n"
            "    return 0\n"
        )
        h, c = self.compile_pipeline(code)
        self.assertIn("if (((1 < x) && (x < 10))) {", c)
        self.assertIn('pb_print_str("ok");', c)

    # class ------------------------------------------------------

    def test_class_instantiation_and_method_call(self):
        code = (
            "class Player:\n"
            "    def __init__(self):\n"
            "        self.hp = 100\n"
            "    def get_hp(self) -> int:\n"
            "        return self.hp\n"
            "\n"
            "def main() -> int:\n"
            "    p: Player = Player()\n"
            "    print(p.get_hp())\n"
            "    return 0\n"
        )
        h, c = self.compile_pipeline(code)
        self.assertIn("struct Player __tmp_", c)
        self.assertIn("Player____init__(&__tmp_", c)
        self.assertIn("pb_print_int(Player__get_hp(p));", c)

    def test_class_attrs_and_dynamic_instance_attr_with_static_and_dynamic_access(self):
        code = (
            "class Player:\n"
            "    mp: int = 100\n"
            "\n"
            "    def __init__(self):\n"
            "        self.hp = 150\n"
            "\n"
            "    def get_hp(self) -> int:\n"
            "        return self.hp\n"
            "\n"
            "def main() -> int:\n"
            "    p: Player = Player()\n"
            "    print(p.hp)\n"
            "    print(p.get_hp())\n"
            "    print(Player.mp)\n"
            "    return 0\n"
        )
        h, c = self.compile_pipeline(code)

        # Check that instance and class fields are both accessed correctly
        self.assertIn("struct Player __tmp_", c)
        self.assertIn("Player____init__(&__tmp_", c)
        self.assertIn("pb_print_int(p->hp);", c)
        self.assertIn("pb_print_int(Player__get_hp(p));", c)
        self.assertIn("pb_print_int(Player_mp);", c)

        # Optional: confirm structure of Player includes both fields
        self.assertIn("typedef struct Player {", h)
        self.assertIn("int64_t hp;", h)
        self.assertIn("int64_t mp;", h)

        # Optional: confirm static field initialization
        self.assertIn("int64_t Player_mp = 100;", c)

    def test_class_field_without_initializer_pipeline(self):
        code = (
            "class Foo:\n"
            "    a: int\n"
        )

        h, c = self.compile_pipeline(code)
        self.assertIn("typedef struct Foo {", h)
        self.assertIn("int64_t a;", h)
        self.assertNotIn("Foo_a =", c)

    def test_codegen_class_inheritance_with_fields(self):
        code = (
            "class Player:\n"
            "    name: str = \"P\"\n"
            "\n"
            "    def __init__(self):\n"
            "        self.hp = 150\n"
            "\n"
            "    def get_hp(self) -> int:\n"
            "        return self.hp\n"
            "\n"
            "class Mage(Player):\n"
            "    def __init__(self):\n"
            "        Player.__init__(self)\n"
            "        self.mana = 200\n"
            "\n"
            "def main() -> int:\n"
            "    p: Player = Player()\n"
            "    print(p.hp)\n"
            "    print(p.get_hp())\n"
            "    print(Player.name)\n"
            "    m: Mage = Mage()\n"
            "    print(m.hp)\n"
            "    print(m.mana)\n"
            "    print(m.get_hp())\n"
            "    return 0\n"
        )
        h, c = self.compile_pipeline(code)
        self.assertIn("typedef struct Player {", h)
        self.assertIn("const char * name;", h)
        self.assertIn("int64_t hp;", h)
        self.assertIn("typedef struct Mage {", h)
        self.assertIn("Player base;", h)
        self.assertIn("int64_t mana;", h)
        self.assertIn("const char * Player_name = \"P\";", c)
        self.assertIn("void Player____init__(struct Player * self);", h)
        self.assertIn("int64_t Player__get_hp(struct Player * self);", h)
        self.assertIn("void Mage____init__(struct Mage * self);", h)
        self.assertIn("Player____init__((struct Player *)self);", c)
        self.assertIn("pb_print_int(p->hp);", c)
        self.assertIn("pb_print_int(Player__get_hp(p));", c)
        self.assertIn("pb_print_str(Player_name);", c)
        self.assertIn("pb_print_int(m->base.hp);", c)
        self.assertIn("pb_print_int(m->mana);", c)
        self.assertIn("pb_print_int(Mage__get_hp(m));", c)

    def test_class_attr_inheritance_pipeline(self):
        code = (
            "class Player:\n"
            "    name: str = \"P\"\n"
            "    BASE_HP: int = 150\n"
            "    def __init__(self):\n"
            "        self.hp = 150\n"
            "\n"
            "class Mage(Player):\n"
            "    DEFAULT_MANA: int = 200\n"
            "    def __init__(self):\n"
            "        Player.__init__(self)\n"
            "        self.mana = 200\n"
            "    def total_power(self, bonus: int = 10) -> int:\n"
            "        return self.hp + self.mana + bonus\n"
            "\n"
            "class ArchMage(Mage):\n"
            "    pass\n"
            "\n"
            "def main() -> int:\n"
            "    p: Player = Player()\n"
            "    print(p.name)\n"
            "    m: Mage = Mage()\n"
            "    print(m.name)\n"
            "    print(Mage.name)\n"
            "    a: ArchMage = ArchMage()\n"
            "    print(a.mana)\n"
            "    print(a.hp)\n"
            "    print(a.total_power())\n"
            "    return 0\n"
        )
        h, c = self.compile_pipeline(code)
        self.assertIn("pb_print_str(Player_name);", c)
        self.assertIn("pb_print_str(Player_name);", c)  # via Mage.name
        self.assertIn("int64_t Player_BASE_HP = 150;", c)
        self.assertIn("int64_t Mage_DEFAULT_MANA = 200;", c)
        self.assertIn("pb_print_int(a->base.mana);", c)
        self.assertIn("pb_print_int(a->base.base.hp);", c)
        self.assertIn("pb_print_int(ArchMage__total_power(a, 10));", c)

    def test_class_inheritance_and_override(self):
        """type checker doesn't allow calling constructors for subclasses
        unless __init__ is defined on that class directly."""
        code = (
            "class Base:\n"
            "    def greet(self):\n"
            "        print(\"base\")\n"
            "class Child(Base):\n"
            "    def __init__(self):\n"
            "        pass\n"
            "    def greet(self):\n"
            "        print(\"child\")\n"
            "def main() -> int:\n"
            "    c: Child = Child()\n"
            "    c.greet()\n"
            "    return 0\n"
        )
        h, c = self.compile_pipeline(code)
        self.assertIn("struct Child __tmp_", c)
        self.assertIn("pb_print_str(\"child\");", c)

    def test_pipeline_exception_raise(self):
        pb_code = (
            "class Exception:\n"
            "    def __init__(self, msg: str):\n"
            "        self.msg = msg\n"
            "\n"
            "class RuntimeError(Exception):\n"
            "    pass\n"
            "\n"
            "def crash():\n"
            "    raise RuntimeError(\"division by zero\")\n"
            "\n"
            "def main():\n"
            "    crash()\n"
        )
        header, c_code = self.compile_pipeline(pb_code)
        # Should emit the constructor forwarding and raise call
        self.assertIn('Exception____init__((struct Exception *)self, msg);', c_code)
        self.assertIn('pb_raise_obj("RuntimeError"', c_code)
        # Should use the forwarded RuntimeError constructor
        self.assertIn('void RuntimeError____init__(struct RuntimeError * self, const char * msg)', c_code)

    def test_if_name_main_guard_ignored(self):
        code = (
            "x: int = 1\n"
            "def main():\n"
            "    print(f\"{x * 2.0}\")\n"
            "    print(f\"{x * False}\")\n"
            "\n"
            "def init():\n"
            "    print(\"init runs\")\n"
            "\n"
            "if __name__ == \"__main__\":\n"
            "    init()\n"
        )
        h, c = self.compile_pipeline(code)
        self.assertIn('int64_t x = 1;', c)
        self.assertIn('pb_print_str((snprintf(__fbuf, 256, "%s", pb_format_double((x * 2.0))), __fbuf));', c)
        self.assertIn('pb_print_str((snprintf(__fbuf, 256, "%lld", (x * false)), __fbuf));', c)

    # global ------------------------------------------------------

    def test_global_variable_in_method(self):
        code = (
            "counter: int = 0\n"
            "class A:\n"
            "    def bump(self):\n"
            "        global counter\n"
            "        counter += 1\n"
        )
        h, c = self.compile_pipeline(code)
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
        header, c_code = self.compile_pipeline(code)
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
        header, c_code = self.compile_pipeline(code)
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
        header, c_code = self.compile_pipeline(code)
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
        header, c_code = self.compile_pipeline(code)
        self.assertIn("for (int64_t i = 0; i < 3; ++i)", c_code)
        self.assertIn('pb_print_int(i)', c_code)

    def test_range_one_arg(self):
        code = (
            "def main() -> int:\n"
            "    for x in range(2):\n"
            "        print(x)\n"
            "    return 0\n"
        )
        header, c_code = self.compile_pipeline(code)
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
        h, c = self.compile_pipeline(code)
        self.assertIn("for (int64_t i = 0; i < 5; ++i)", c)
        self.assertIn("continue;", c)
        self.assertIn("break;", c)

    def test_type_check_pipeline(self):
        code = (
            "def main() -> int:\n"
            "    x: int = 10\n"
            "    y: float = 1.0\n"
            "    z: float = 0.0\n"
            "    a: str = '1'\n"
            "    b: str = '1.0'\n"
            "\n"
            "    x_float: float = float(x)\n"
            "    b_float: float = float(b)\n"
            "    y_int: int = int(y)\n"
            "    a_int: int = int(a)\n"
            "    x_bool: bool = bool(x)\n"
            "    y_bool: bool = bool(y)\n"
            "    z_bool: bool = bool(z)\n"
            "    return 0\n"
        )
        h, c = self.compile_pipeline(code)
        
        # Check for type declarations and conversions in the generated C code
        self.assertIn("int64_t x = 10;", c)                # x as int
        self.assertIn("double y = 1.0;", c)                 # y as float
        self.assertIn("double z = 0.0;", c)                 # z as float
        self.assertIn("const char * a = \"1\";", c)        # a as string
        self.assertIn("const char * b = \"1.0\";", c)      # b as string
        self.assertIn("double x_float = (double)(x);", c)  # x to float conversion
        self.assertIn("double b_float = (strtod)(b, NULL);", c)  # b to float conversion
        self.assertIn("int64_t y_int = (int64_t)(y);", c)  # y to int conversion
        self.assertIn("int64_t a_int = (strtoll)(a, NULL, 10);", c)  # a to int conversion
        self.assertIn("bool x_bool = (x != 0);", c)        # x to bool conversion
        self.assertIn("bool y_bool = (y != 0.0);", c)      # y to bool conversion
        self.assertIn("bool z_bool = (z != 0.0);", c)      # z to bool conversion

    def test_list_conversion_functions(self):
        code = (
            "def main():\n"
            "    arr: list[int] = [1, 2, 3]\n"
            "    arr[0] = int(4.5)\n"
            "    print(arr)\n"
            "    arr2: list[str] = ['1', '2', '3']\n"
            "    arr2[0] = str(4)\n"
            "    print(arr2)\n"
            "    arr3: list[float] = [1.1, 2.2, 3.3]\n"
            "    arr3[0] = float(4)\n"
            "    print(arr3)\n"
            "    arr4: list[bool] = [True, False]\n"
            "    arr4[0] = bool(1)\n"
            "    print(arr4)\n"
        )
        h, c = self.compile_pipeline(code)

        self.assertIn('list_int_set(&arr, 0, (int64_t)(4.5));', c)
        self.assertIn('list_str_set(&arr2, 0, pb_format_int(4));', c)
        self.assertIn('list_float_set(&arr3, 0, (double)(4));', c)
        self.assertIn('list_bool_set(&arr4, 0, (1 != 0));', c)
    def test_fstring_expression_codegen(self):
        code = (
            "class Player:\n"
            "    species: str = \"Human\"\n"
            "\n"
            "    def __init__(self, hp: int):\n"
            "        self.hp = hp\n"
            "        self.name = \"Hero\"\n"
            "\n"
            "    def get_name(self) -> str:\n"
            "        return self.name\n"
            "\n"
            "def main() -> int:\n"
            "    x: int = 5\n"
            "    print(f\"Simple fstring: x={x}\")\n"
            "    print(f\"x + 1: {x + 1}\")\n"
            "    print(f\"Float conversion: {float(2)}\")\n"
            "    print(\"--------------------------------\")\n"
            "\n"
            "    p: Player = Player(100)\n"
            "    print(f\"player.hp: {p.hp}\")\n"
            "    print(f\"player get_name: {p.get_name()}\")\n"
            "    print(f\"Player.species: {Player.species}\")\n"
            "    return 0\n"
        )
        h, c = self.compile_pipeline(code)

        # f-string expansions
        self.assertIn('pb_print_str((snprintf(__fbuf, 256, "Simple fstring: x=%lld", x), __fbuf));', c)
        self.assertIn('pb_print_str((snprintf(__fbuf, 256, "x + 1: %lld", (x + 1)), __fbuf));', c)
        self.assertIn('pb_print_str((snprintf(__fbuf, 256, "Float conversion: %s", pb_format_double((double)(2))), __fbuf));', c)
        self.assertIn('pb_print_str("-----', c)

        # player expressions
        self.assertIn('pb_print_str((snprintf(__fbuf, 256, "player.hp: %lld", p->hp), __fbuf));', c)
        self.assertIn('pb_print_str((snprintf(__fbuf, 256, "player get_name: %s", Player__get_name(p)), __fbuf));', c)
        self.assertIn('pb_print_str((snprintf(__fbuf, 256, "Player.species: %s", Player_species), __fbuf));', c)

    def test_raw_and_multiline_string_codegen(self):
        code = (
            "def main():\n"
            "    print(r\"line\\nnext\")\n"
            "    print(\"\"\"hello\n    world\"\"\")\n"
        )
        h, c = self.compile_pipeline(code)
        self.assertIn('pb_print_str("line\\\\nnext");', c)
        self.assertIn('pb_print_str("hello\\n    world");', c)

    def test_raise_valueerror(self):
        code = (
            "def main():\n"
            "    try:\n"
            "        raise ValueError(\"bad\")\n"
            "    except ValueError:\n"
            "        print(\"caught ValueError\")\n"
        )
        header, c_code = self.compile_pipeline(code)
        self.assertIn('pb_print_str("caught ValueError");', c_code)

    def test_dict_keyerror(self):
        code = (
            "class KeyError:\n"
            "    msg: str = ''\n"
            "def main():\n"
            "    d: dict[str, int] = {\"a\": 1}\n"
            "    try:\n"
            "        print(d[\"b\"])\n"
            "    except KeyError:\n"
            "        print(\"caught KeyError\")\n"
        )
        header, c_code = self.compile_pipeline(code)
        self.assertIn('pb_print_int(pb_dict_get_str_int(d, "b"));', c_code)
        self.assertIn('if (strcmp(pb_current_exc.type, "KeyError") == 0)', c_code)
        self.assertIn('pb_print_str("caught KeyError");', c_code)

    def test_reraise_in_except(self):
        code = (
            "def main():\n"
            "    try:\n"
            "        try:\n"
            "            raise ValueError(\"bad\")\n"
            "        except ValueError:\n"
            "            print(\"re-raising\")\n"
            "            raise\n"
            "    except ValueError:\n"
            "        print(\"caught outer\")\n"
        )
        header, c_code = self.compile_pipeline(code)
        self.assertIn('pb_raise_msg("ValueError", "bad");', c_code)
        self.assertIn('if (strcmp(pb_current_exc.type, "ValueError") == 0)', c_code)
        self.assertIn('pb_print_str("re-raising");', c_code)
        self.assertIn('if (__exc_flag_2 && !__exc_handled_2) pb_reraise();', c_code)
        self.assertIn('pb_print_str("caught outer");', c_code)

    def test_raise_custom_struct(self):
        code = (
            "class MyError:\n"
            "    def __init__(self, msg: str):\n"
            "        self.msg = msg\n"
            "def main():\n"
            "    e: MyError = MyError(\"oops\")\n"
            "    try:\n"
            "        raise e\n"
            "    except MyError as err:\n"
            "        print(err.msg)\n"
        )
        header, c_code = self.compile_pipeline(code)
        self.assertIn('pb_raise_obj("MyError", e);', c_code)
        self.assertIn('if (strcmp(pb_current_exc.type, "MyError") == 0)', c_code)
        self.assertIn('struct MyError * err = (struct MyError *)pb_current_exc.value;', c_code)
        self.assertIn('pb_print_str(err->msg);', c_code)

    def test_raise_string(self):
        code = (
            "def main():\n"
            "    try:\n"
            "        raise \"basic failure\"\n"
            "    except Exception:\n"
            "        print(\"caught generic error\")\n"
        )
        header, c_code = self.compile_pipeline(code)
        self.assertIn('pb_raise_msg("str", "basic failure");', c_code)
        self.assertIn('if (strcmp(pb_current_exc.type, "Exception") == 0)', c_code)
        self.assertIn('pb_print_str("caught generic error");', c_code)

    def test_raise_without_except(self):
        code = (
            "def main():\n"
            "    try:\n"
            "        raise \"basic failure\"\n"
            "    except:\n"
            "        print(\"caught generic error\")\n"
        )
        header, c_code = self.compile_pipeline(code)
        self.assertIn('pb_raise_msg("str", "basic failure");', c_code)
        self.assertIn('if (1)', c_code)
        self.assertIn('pb_print_str("caught generic error");', c_code)

    def test_raise_without_raise_msg(self):
        code = (
            "def main():\n"
            "    try:\n"
            "        raise\n"
            "    except Exception:\n"
            "        print(\"caught generic error\")\n"
        )
        header, c_code = self.compile_pipeline(code)
        self.assertIn('pb_reraise();', c_code)
        self.assertIn('if (strcmp(pb_current_exc.type, "Exception") == 0)', c_code)
        self.assertIn('pb_print_str("caught generic error");', c_code)

    def test_pipeline_import_with_alias(self):
        with tempfile.TemporaryDirectory() as tempdir:
            base = os.path.join(os.path.dirname(__file__), "samples")
            # write modules
            for name in ["mathlib.pb", "utils.pb", "test_import/mathlib2.pb", "imports_extended.pb"]:
                src_path = os.path.join(base, name)
                dst_path = os.path.join(tempdir, name)
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                with open(src_path) as fsrc, open(dst_path, "w") as fdst:
                    fdst.write(fsrc.read())

            imports_path = os.path.join(tempdir, "imports_extended.pb")
            with open(imports_path) as f:
                code = f.read()

            h, c, *_ = compile_code_to_c_and_h(code, module_name="imports_extended", pb_path=imports_path)

            # Includes should only appear once despite multiple import forms
            self.assertEqual(c.count('#include "mathlib.h"'), 1)
            self.assertEqual(c.count('#include "test_import.mathlib2.h"'), 1)

            # Alias macros should be generated for imported modules/symbols
            self.assertIn('#define m1 mathlib', c)
            self.assertIn('#define mathlib2 test_import.mathlib2', c)
            self.assertIn('#define m2 test_import.mathlib2', c)
            self.assertIn('#define pi2 PI', c)

    def test_pipeline_from_import_star(self):
        with tempfile.TemporaryDirectory() as tempdir:
            base = os.path.join(os.path.dirname(__file__), "samples")
            for name in ["mathlib.pb", "utils.pb", "imports_star.pb"]:
                src_path = os.path.join(base, name)
                dst_path = os.path.join(tempdir, name)
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                with open(src_path) as fsrc, open(dst_path, "w") as fdst:
                    fdst.write(fsrc.read())

            star_path = os.path.join(tempdir, "imports_star.pb")
            with open(star_path) as f:
                code = f.read()

            h, c, *_ = compile_code_to_c_and_h(code, module_name="imports_star", pb_path=star_path)

            self.assertIn('#include "mathlib.h"', c)
            self.assertIn('#include "utils.h"', c)

    def test_numeric_literals_with_underscores(self):
        code = (
            "def main() -> int:\n"
            "    n: int = 1_0\n"
            "    total: int = 0\n"
            "    for i in range(n):\n"
            "        total += i\n"
            "    print(total)\n"
            "    return 0\n"
        )
        h, c = self.compile_pipeline(code)
        self.assertIn('int64_t n = 10;', c)
        self.assertIn('for (int64_t i = 0; i < n; ++i)', c)

    def test_len_builtin_pipeline(self):
        code = (
            "def main() -> int:\n"
            "    arr: list[int] = [1, 2, 3]\n"
            "    x: int = len(arr)\n"
            "    print(x)\n"
            "    return 0\n"
        )
        header, c_code = self.compile_pipeline(code)
        self.assertIn('int64_t x = arr.len;', c_code)
        self.assertIn('pb_print_int(x);', c_code)


if __name__ == "__main__":
    unittest.main()
