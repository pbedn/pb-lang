"""Boundary and failure-path coverage for the consolidated implementations."""
import importlib.util
import os
from pathlib import Path
import shlex
import subprocess
import sys
import textwrap
from unittest.mock import patch

import pytest

from pb_pipeline import compile_code_to_c_and_h
from type_checker import TypeError as PBTypeError
from tests.test_runtime import compile_and_run, compile_modules_and_run_main

ROOT = Path(__file__).resolve().parents[1]


def execute(source):
    return compile_and_run(textwrap.dedent(source))


@pytest.mark.parametrize("value", ['True', '1.5', '"text"', '1 + 2', '2147483648', '-2147483649'])
def test_invalid_enum_values_are_rejected(value):
    with pytest.raises(PBTypeError):
        compile_code_to_c_and_h(f"class Number(Enum):\n    VALUE = {value}\n")


@pytest.mark.parametrize("value", ['-2147483648', '2147483647', '0x2a', '1_000'])
def test_enum_integer_boundaries(value):
    assert execute(f'''
        class Number(Enum):
            VALUE = {value}
        def main() -> int:
            print(Number.VALUE)
            return 0
    ''') == "Number.VALUE"


def test_enum_value_alias_uses_first_member_name():
    assert execute('''
        class Number(Enum):
            FIRST = 1
            ALIAS = 1
        def main() -> int:
            print(Number.ALIAS, Number.FIRST == Number.ALIAS)
            return 0
    ''') == "Number.FIRST True"


def test_same_enum_names_in_different_modules_do_not_collide():
    assert compile_modules_and_run_main({
        "one": "class Color(Enum):\n    RED = 1\n",
        "two": "class Color(Enum):\n    BLUE = 2\n",
        "main": "import one\nimport two\ndef main() -> int:\n    print(one.Color.RED, two.Color.BLUE)\n    return 0\n",
    }) == "Color.RED Color.BLUE"


@pytest.mark.parametrize("typ,literal,expected", [
    ("list[int]", "[1, 2]", "[1, 2]"),
    ("list[str]", '["a", "b"]', "['a', 'b']"),
    ("set[int]", "{1, 2}", "{1, 2}"),
    ("dict[str, int]", '{"a": 3}', "{'a': 3}"),
])
def test_returned_container_survives_another_function_call(typ, literal, expected):
    assert execute(f'''
        def create() -> {typ}:
            result: {typ} = {literal}
            return result
        def overwrite() -> int:
            scratch: list[int] = [90, 91, 92, 93]
            return scratch[0]
        def main() -> int:
            saved: {typ} = create()
            ignored: int = overwrite()
            print(saved)
            return 0
    ''') == expected


@pytest.mark.parametrize("typ,literal", [("list[int]", "[]"), ("dict[str, int]", "{}"), ("str", '""')])
def test_empty_iterables_do_not_execute_loop(typ, literal):
    assert execute(f'''
        def main() -> int:
            values: {typ} = {literal}
            for item in values:
                print("unexpected")
            print("done")
            return 0
    ''') == "done"


def test_range_bound_function_evaluated_once():
    assert execute('''
        calls: int = 0
        def stop() -> int:
            global calls
            calls += 1
            return 3
        def main() -> int:
            for item in range(stop()):
                print(item)
            print(calls)
            return 0
    ''') == "0\n1\n2\n1"


def test_long_concatenated_string_is_not_truncated():
    word = "x" * 400
    assert execute(f'''
        def main() -> int:
            text: str = "{word}" + "{word}"
            print(len(text))
            return 0
    ''') == "800"


def test_returned_fstring_is_copied_before_next_formatting_call():
    assert execute('''
        def label(value: int) -> str:
            return f"item {value}"
        def main() -> int:
            saved: str = label(1)
            other: str = label(2)
            print(saved, other)
            return 0
    ''') == "item 1 item 2"


def test_empty_print_and_mixed_container_arguments():
    assert execute('''
        def main() -> int:
            print("before")
            print()
            values: set[int] = {1, 2}
            mapping: dict[str, bool] = {"a": True}
            print(values, mapping, 2.5)
            return 0
    ''') == "before\n\n{1, 2} {'a': True} 2.5"


def test_dictionary_missing_read_catches_keyerror():
    assert execute('''
        def main() -> int:
            values: dict[str, int] = {"a": 1}
            try:
                print(values["missing"])
            except KeyError as error:
                print(error.msg)
            return 0
    ''') == "missing"


def test_modified_parameter_survives_longjmp():
    assert execute('''
        def change(value: int) -> int:
            try:
                value += 5
                raise ValueError("x")
            except Exception:
                return value
        def main() -> int:
            print(change(2))
            return 0
    ''') == "7"


def test_new_exception_in_handler_runs_finally_before_propagating():
    assert execute('''
        def fail() -> None:
            try:
                raise ValueError("first")
            except ValueError:
                raise RuntimeError("second")
            finally:
                print("finally")
        def main() -> int:
            try:
                fail()
            except RuntimeError as error:
                print(error.msg)
            return 0
    ''') == "finally\nsecond"


def test_nested_handler_restores_outer_exception_for_bare_raise():
    assert execute('''
        def main() -> int:
            try:
                try:
                    raise ValueError("outer")
                except ValueError:
                    try:
                        raise RuntimeError("inner")
                    except RuntimeError:
                        print("inner handled")
                    raise
            except ValueError as error:
                print(error.msg)
            return 0
    ''') == "inner handled\nouter"


def test_return_from_handler_restores_callers_active_exception():
    assert execute('''
        def handle() -> int:
            try:
                raise RuntimeError("inner")
            except RuntimeError:
                return 1
        def main() -> int:
            try:
                try:
                    raise ValueError("outer")
                except ValueError:
                    result: int = handle()
                    raise
            except ValueError as error:
                print(error.msg)
            return 0
    ''') == "outer"


def test_finally_return_overrides_pending_exception():
    assert execute('''
        def result() -> int:
            try:
                raise ValueError("ignored")
            finally:
                return 9
        def main() -> int:
            print(result())
            return 0
    ''') == "9"


def test_break_from_inner_loop_keeps_outer_try_active():
    assert execute('''
        def main() -> int:
            try:
                for i in range(3):
                    break
                raise ValueError("still active")
            except ValueError as error:
                print(error.msg)
            return 0
    ''') == "still active"


def test_repeated_returns_leave_no_stale_try_contexts():
    assert execute('''
        def work() -> int:
            try:
                return 1
            finally:
                pass
        def main() -> int:
            total: int = 0
            for i in range(300):
                total += work()
            try:
                raise ValueError("done")
            except Exception:
                print(total)
            return 0
    ''') == "300"


def test_managed_runtime_cleanup_ignores_borrowed_storage_and_can_reinitialize(tmp_path):
    source = tmp_path / "ownership.c"
    source.write_text('''
#include "pb_runtime.h"
int main(void) {
    int64_t borrowed[] = {1,2,3};
    pb_release(borrowed);
    void *owned = pb_alloc(17);
    pb_release(owned);
    pb_release(owned);
    pb_register_exception("Custom", "Exception");
    pb_memory_cleanup();
    pb_memory_cleanup();
    pb_register_exception("Custom", "Exception");
    pb_current_exc.type = "Custom";
    assert(pb_exception_matches("BaseException"));
    assert(strcmp(pb_string_copy("again"), "again") == 0);
    pb_memory_cleanup();
    puts("ok");
    return 0;
}
''', encoding="utf-8")
    executable = tmp_path / ("ownership.exe" if sys.platform == "win32" else "ownership")
    subprocess.run(["gcc", "-std=c99", *shlex.split(os.environ.get("PB_CFLAGS", "")), str(source), str(ROOT / "src/pb_runtime.c"), "-I", str(ROOT / "src"), "-o", str(executable)], check=True, capture_output=True)
    result = subprocess.run([str(executable)], capture_output=True, text=True, check=True)
    assert result.stdout.strip() == "ok"


@pytest.mark.parametrize("failure_stage", ["compile", "archive"])
def test_runtime_build_failures_are_reported(failure_stage):
    from main import build_runtime_library
    success = subprocess.CompletedProcess([], 0, "", "")
    failure = subprocess.CompletedProcess([], 1, "", "intentional failure")
    results = [failure] if failure_stage == "compile" else [success, failure]
    with patch("main.subprocess.run", side_effect=results), pytest.raises(RuntimeError, match="intentional failure"):
        build_runtime_library()


@pytest.mark.parametrize("flags,expected", [(None, "-O1"), (["-O2"], "-O2")])
def test_runtime_optimization_uses_explicit_flags_before_environment(flags, expected, monkeypatch):
    from main import build_runtime_library
    success = subprocess.CompletedProcess([], 0, "", "")
    monkeypatch.setenv("PB_CFLAGS", "-O1")
    with patch("main.subprocess.run", return_value=success) as compiler:
        build_runtime_library(compile_flags=flags)
    command = compiler.call_args_list[0].args[0]
    assert expected in command
    assert ("-O1" in command) == (flags is None)


def test_uncaught_exception_preserves_its_message():
    assert execute('''
        def main() -> int:
            raise ValueError("failure")
            return 0
    ''') == "ValueError: failure"


def test_reference_program_is_stable_across_repeated_process_runs(tmp_path):
    source = (ROOT / "ref/lang.pb").read_text(encoding="utf-8")
    header, generated, *_ = compile_code_to_c_and_h(source, module_name="stress", pb_path=str(ROOT / "ref/lang.pb"))
    (tmp_path / "stress.h").write_text(header, encoding="utf-8")
    (tmp_path / "stress.c").write_text(generated, encoding="utf-8")
    executable = tmp_path / ("stress.exe" if sys.platform == "win32" else "stress")
    subprocess.run(["gcc", "-std=c99", *shlex.split(os.environ.get("PB_CFLAGS", "")), str(tmp_path / "stress.c"), str(ROOT / "src/pb_runtime.c"), "-I", str(ROOT / "src"), "-o", str(executable)], check=True, capture_output=True)
    expected = subprocess.run([sys.executable, str(ROOT / "ref/lang.pb")], capture_output=True, text=True, check=True).stdout.splitlines()
    for attempt in range(30):
        result = subprocess.run([str(executable)], capture_output=True, text=True)
        assert result.returncode == 0, (attempt, result.stderr)
        assert result.stdout.splitlines() == expected


def test_custom_build_output_name_compiles_imports_and_runs(tmp_path):
    from main import build
    (tmp_path / "helper.pb").write_text("def answer() -> int:\n    return 42\n", encoding="utf-8")
    source = "import helper\ndef main() -> int:\n    print(helper.answer())\n    return 0\n"
    source_path = tmp_path / "source.pb"
    source_path.write_text(source, encoding="utf-8")
    output = str(tmp_path / "custom")
    success, _ = build(source, str(source_path), output)
    assert success
    executable = output + (".exe" if sys.platform == "win32" else "")
    assert subprocess.run([executable], check=True, capture_output=True, text=True).stdout.strip() == "42"


@pytest.mark.parametrize("operation", ["get", "set"])
def test_keyerror_payload_and_base_catch(operation):
    action = 'print(values["absent"])' if operation == "get" else 'values["absent"] = 2'
    assert execute(f'''
        def main() -> int:
            values: dict[str, int] = {{"present": 1}}
            try:
                {action}
            except KeyError as error:
                print(error.msg)
            try:
                raise KeyError("explicit")
            except BaseException as error:
                print(error.msg)
            return 0
    ''') == "absent\nexplicit"


def test_break_in_handler_restores_outer_exception():
    assert execute('''
        def main() -> int:
            try:
                try:
                    raise ValueError("outer")
                except ValueError:
                    for i in range(1):
                        try:
                            raise RuntimeError("inner")
                        except RuntimeError:
                            break
                    raise
            except ValueError as error:
                print(error.msg)
            return 0
    ''') == "outer"


def binding_generator():
    spec = importlib.util.spec_from_file_location("pb_binding_test", ROOT / "vendor/raylib/script/binding_generator.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("ctype", ["char*", "const char *", "char *"])
def test_binding_generator_preserves_string_pointer_types(ctype):
    assert binding_generator().map_c_type(ctype) == "str"


def test_binding_generator_excludes_unsupported_callbacks_and_variadics():
    module = binding_generator()
    header = """
RLAPI void SetAudioStreamCallback(AudioStream stream, AudioCallback callback);
RLAPI void TraceLog(int level, const char *text, ...);
RLAPI void DrawText(const char *text, int x, int y, int size, Color color);
typedef void (*AudioCallback)(void *buffer, unsigned int frames);
"""
    assert module.parse_function_pointer_aliases(header) == []
    assert module.parse_functions(header) == ["def DrawText(text: str, x: int, y: int, size: int, color: Color) -> None: ..."]
    assert Path(module.PB_OUTPUT_PATH).name == "raylib_stub.pb"
