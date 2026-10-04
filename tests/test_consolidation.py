"""Executable regressions for features recovered from the branch backlog."""
from pathlib import Path
import os
import shlex
import subprocess
import sys
import tempfile
import textwrap
import unittest

from pb_pipeline import compile_code_to_c_and_h
from type_checker import TypeError
from tests.test_runtime import compile_and_run, compile_modules_and_run_main


class TestConsolidatedRuntime(unittest.TestCase):
    def run_pb(self, source):
        return compile_and_run(textwrap.dedent(source))

    def test_typed_enums_and_aliases(self):
        modules = {
            "colors": "class Color(Enum):\n    RED = 1\n    BLUE = 2\n",
            "main": "from colors import Color as Shade\ndef main() -> int:\n    value: Shade = Shade.BLUE\n    print(value)\n    return 0\n",
        }
        self.assertEqual(compile_modules_and_run_main(modules), "Color.BLUE")

    def test_enum_qualified_import(self):
        modules = {
            "colors": "class Color(Enum):\n    RED = 1\n",
            "main": "import colors as c\ndef main() -> int:\n    print(c.Color.RED)\n    return 0\n",
        }
        self.assertEqual(compile_modules_and_run_main(modules), "Color.RED")

    def test_enum_rejects_cross_type_assignment(self):
        with self.assertRaises(TypeError):
            compile_code_to_c_and_h("class A(Enum):\n    X = 1\nclass B(Enum):\n    X = 1\ndef main() -> int:\n    a: A = B.X\n    return 0\n")

    def test_enum_rejects_duplicate_members(self):
        with self.assertRaises(TypeError):
            compile_code_to_c_and_h("class A(Enum):\n    X = 1\n    X = 2\n")

    def test_iterables_and_unicode(self):
        self.assertEqual(self.run_pb('''
            def main() -> int:
                values: list[int] = [1, 2]
                unique: set[int] = {3, 4}
                mapping: dict[str, int] = {"a": 1, "b": 2}
                for value in values:
                    print(value)
                for value in unique:
                    print(value)
                for key in mapping:
                    print(key)
                for ch in "ą🙂":
                    print(ch)
                return 0
        '''), "1\n2\n3\n4\na\nb\ną\n🙂")

    def test_iterable_function_called_once_and_return_storage_survives(self):
        self.assertEqual(self.run_pb('''
            calls: int = 0
            def values() -> list[int]:
                global calls
                calls += 1
                result: list[int] = [1, 2]
                return result
            def main() -> int:
                for value in values():
                    print(value)
                print(calls)
                return 0
        '''), "1\n2\n1")

    def test_nested_iterators_have_independent_indices(self):
        self.assertEqual(self.run_pb('''
            def main() -> int:
                a: list[int] = [1, 2]
                b: list[int] = [3, 4]
                for x in a:
                    for y in b:
                        print(x, y)
                return 0
        '''), "1 3\n1 4\n2 3\n2 4")

    def test_growth_preserves_alias_storage(self):
        self.assertEqual(self.run_pb('''
            def main() -> int:
                values: list[int] = [1, 2, 3, 4, 5]
                alias: list[int] = values
                values.append(6)
                print(alias)
                print(values)
                return 0
        '''), "[1, 2, 3, 4, 5]\n[1, 2, 3, 4, 5, 6]")

    def test_owned_strings_and_multi_argument_containers(self):
        self.assertEqual(self.run_pb('''
            def main() -> int:
                saved: str = str(1)
                for i in range(10):
                    other: str = str(i)
                text: str = "hello" + " " + "world"
                text += "!"
                values: list[int] = [1, 2]
                print(saved, text, values, True, str(False))
                return 0
        '''), "1 hello world! [1, 2] True False")

    def test_print_arguments_evaluated_before_printing(self):
        self.assertEqual(self.run_pb('''
            def argument(value: int) -> int:
                print(value)
                return value
            def main() -> int:
                print(argument(1), argument(2))
                return 0
        '''), "1\n2\n1 2")

    def test_print_fstrings_keep_distinct_values(self):
        self.assertEqual(self.run_pb('''
            def main() -> int:
                print(f"{1}", f"{2}")
                return 0
        '''), "1 2")

    def test_typed_dictionary_updates_and_missing_keys(self):
        self.assertEqual(self.run_pb('''
            def main() -> int:
                values: dict[str, int] = {"a": 1}
                values["a"] = 2
                result: int = values["a"]
                print(values, result)
                try:
                    values["b"] = 3
                except Exception:
                    print("missing")
                return 0
        '''), "{'a': 2} 2\nmissing")

    def test_return_expression_evaluated_before_finally(self):
        self.assertEqual(self.run_pb('''
            def first() -> int:
                values: list[int] = []
                values.append(7)
                try:
                    return values[0]
                finally:
                    values[0] = 9
                    print("finally")
            def main() -> int:
                print(first())
                return 0
        '''), "finally\n7")

    def test_finally_on_unhandled_exception_and_base_catch(self):
        self.assertEqual(self.run_pb('''
            class Problem(BaseException):
                pass
            def fail() -> None:
                try:
                    raise Problem("oops")
                finally:
                    print("finally")
            def main() -> int:
                try:
                    fail()
                except BaseException as error:
                    print(error.msg)
                return 0
        '''), "finally\noops")

    def test_builtin_message_payload_reraise(self):
        self.assertEqual(self.run_pb('''
            def main() -> int:
                values: list[int] = []
                try:
                    try:
                        print(values[0])
                    except IndexError:
                        raise
                except Exception as error:
                    print("caught")
                return 0
        '''), "caught")

    def test_builtin_exceptions_across_modules(self):
        modules = {
            "one": "def fail() -> None:\n    raise ValueError('one')\n",
            "two": "def fail() -> None:\n    raise RuntimeError('two')\n",
            "main": "import one\nimport two\ndef main() -> int:\n    try:\n        one.fail()\n    except Exception as error:\n        print(error.msg)\n    try:\n        two.fail()\n    except BaseException as error:\n        print(error.msg)\n    return 0\n",
        }
        self.assertEqual(compile_modules_and_run_main(modules), "one\ntwo")

    def test_try_stack_balances_repeated_raises(self):
        self.assertEqual(self.run_pb('''
            def main() -> int:
                count: int = 0
                for i in range(300):
                    try:
                        raise ValueError("x")
                    except Exception:
                        count += 1
                print(count)
                return 0
        '''), "300")

    def test_local_assignment_survives_exception(self):
        self.assertEqual(self.run_pb('''
            def main() -> int:
                value: int = 0
                try:
                    value = 7
                    raise ValueError("x")
                except Exception:
                    print(value)
                return 0
        '''), "7")

    def test_finally_on_break_and_continue(self):
        self.assertEqual(self.run_pb('''
            def main() -> int:
                for i in range(3):
                    try:
                        if i == 0:
                            continue
                        break
                    finally:
                        print(i)
                print("done")
                return 0
        '''), "0\n1\ndone")

    def test_allocated_class_return_and_nested_attributes(self):
        self.assertEqual(self.run_pb('''
            class Point:
                def __init__(self, x: int):
                    self.x = x
            class Box:
                def __init__(self):
                    self.point = Point(1)
            def make() -> Box:
                value: Box = Box()
                return value
            def main() -> int:
                value: Box = make()
                value.point.x = 9
                print(value.point.x)
                return 0
        '''), "9")

    def test_pong_generates_without_nul_bytes(self):
        root = Path(__file__).resolve().parents[1]
        path = root / "examples" / "ray_pong.pb"
        _, generated, *_ = compile_code_to_c_and_h(path.read_text(), pb_path=str(path))
        self.assertNotIn("\0", generated)
        self.assertIn("DrawRectangle", generated)

    def test_pong_runs_against_headless_native_binding(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "examples" / "ray_pong.pb").read_text()
        header, generated, *_ = compile_code_to_c_and_h(source, module_name="pong", pb_path=str(root / "examples" / "ray_pong.pb"))
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            (directory / "pong.h").write_text(header)
            (directory / "pong.c").write_text(generated)
            (directory / "raylib.h").write_text('''
#pragma once
#include <stdbool.h>
typedef struct { unsigned char r,g,b,a; } Color;
static const Color RAYWHITE={255,255,255,255}, DARKGRAY={80,80,80,255};
enum {KEY_W, KEY_S, KEY_UP, KEY_DOWN, KEY_SPACE};
void InitWindow(int,int,const char*); void CloseWindow(void); void SetTargetFPS(int);
bool WindowShouldClose(void); float GetFrameTime(void);
bool IsKeyDown(int); bool IsKeyPressed(int);
void BeginDrawing(void); void EndDrawing(void); void ClearBackground(Color);
void DrawRectangle(int,int,int,int,Color); void DrawCircle(int,int,float,Color);
void DrawLine(int,int,int,int,Color); void DrawText(const char*,int,int,int,Color);
''')
            (directory / "fake_raylib.c").write_text('''
#include "raylib.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static int frames, draws, pauses;
static char score[80];
void InitWindow(int w,int h,const char*t){assert(w==800 && h==600 && t);}
void CloseWindow(void){assert(draws==600);assert(pauses==20);assert(strcmp(score,"0 : 0")!=0);puts("PB_PONG_OK");}
void SetTargetFPS(int fps){assert(fps==60);}
bool WindowShouldClose(void){return ++frames>600;}
float GetFrameTime(void){return 0.5f;}
bool IsKeyDown(int k){return (frames<100 && (k==KEY_W || k==KEY_UP)) || (frames>=100 && frames<300 && (k==KEY_S || k==KEY_DOWN));}
bool IsKeyPressed(int k){return k==KEY_SPACE && (frames==20 || frames==40);}
void BeginDrawing(void){draws++;} void EndDrawing(void){}
void ClearBackground(Color c){(void)c;}
void DrawRectangle(int x,int y,int w,int h,Color c){(void)c;assert((x==20 || x==765) && y>=0 && y<=500 && w==15 && h==100);}
void DrawCircle(int x,int y,float r,Color c){(void)c;assert(x>=0 && x<=800 && y>=10 && y<=590 && r==10.0f);}
void DrawLine(int a,int b,int c,int d,Color color){(void)a;(void)b;(void)c;(void)d;(void)color;}
void DrawText(const char*t,int x,int y,int size,Color c){(void)x;(void)y;(void)size;(void)c;if(strchr(t,':'))snprintf(score,sizeof(score),"%s",t);if(strstr(t,"PAUSED"))pauses++;}
''')
            exe = directory / ("pong.exe" if sys.platform == "win32" else "pong")
            subprocess.run(["gcc", "-std=c99", *shlex.split(os.environ.get("PB_CFLAGS", "")), str(directory / "pong.c"), str(directory / "fake_raylib.c"), str(root / "src" / "pb_runtime.c"), "-I", str(directory), "-I", str(root / "src"), "-o", str(exe)], check=True, capture_output=True)
            result = subprocess.run([str(exe)], check=True, capture_output=True, text=True)
            self.assertEqual(result.stdout.strip(), "PB_PONG_OK")


if __name__ == "__main__":
    unittest.main()
