# PB 0.1 - Language Specification - (May 2025)

## 1. Goals & Philosophy

* **Static, strong, explicit** – every binding carries a compile-time type.  
* **Pythonic surface, C-level confidence** – familiar syntax, predictable performance.  
* **Safety first** – many errors rejected at lex, parse or type‑check time.  
* **Simplicity** – a deliberately small subset of Python; no GC, no runtime dynamic typing.

PB is a **statically and strongly typed programming language** that features Python-like syntax and compiles to C (targeting C99). It is designed to be minimal, fast, and safe, intentionally avoiding dynamic typing. PB prioritizes readability and simplicity, enabling developers to write high-performance code with clear C semantics under the hood.

---

## 2. Lexical Structure

### Character set

UTF‑8 source; keywords stay ASCII.

### Identifiers

Identifiers consist of letters, digits, and underscores and must begin with a letter or underscore:

### Keywords

Reserved words include:

```
and, as, assert, break, class, continue, def, elif, else, except,
False, for, global, if, import, in, is, None, not, or, pass,
raise, return, True, try, while
```
> **Note:** `True` and `False` are keywords (not re-bindable). Any attempt to assign, delete, or bind them is a compile-time `SyntaxError`. Lowercase `true`/`false` are ordinary identifiers.

### Literals

* Integer literals: `42`, `1_000`
* Float literals: `3.14`, `1_000.0`, `6.022_140e23`
    - Underscores may separate digits anywhere; they are stripped at lexing.
    - At least one digit before and after the dot; no leading-dot (`.5`) or trailing-dot (`5.`) forms are allowed.
* String literals: single- or double-quoted, single-line only (e.g., `"Hello"`, `'world'`). Escape sequences (`\n`, `\\`, etc.) are decoded; invalid escapes raise a `LexerError` with the raw lexeme.
* F-string literals: `f"..."` or `f'...'`, single-line only.
    - Placeholders use `{expr}` syntax where `expr` is a full expression (e.g., `x`, `a + b`, `obj.attr`, `call()`).
    - Internally, an f-string is parsed into a sequence of static text and embedded expressions:
      ```pb
      f"Hello {name}, your score is {player.get_score()}"
      ```
      is compiled as:
      ```c
      snprintf(__fbuf, 256, "Hello %s, your score is %lld", name, Player__get_score(player));
      ```
    - No support for `!conversion` (`!r`, `!s`) or `:format_spec` yet.

* Boolean literals: `True`, `False` (keywords)

### Comments

* Single-line comments begin with `#`
* The lexer removes comments entirely from generated C

### Indentation & Whitespace

* Indentation is significant.
* Spaces-only for indentation; tabs in indentation cause a `LexerError`.
* Mixed spaces+tabs in leading whitespace is a `LexerError`.

---

## 3. Static Types

| PB type | Meaning | Lowered C |
|---------|---------|-----------|
| `int`   | signed 64‑bit integer | `int64_t` |
| `float` | IEEE‑754 double | `double` |
| `bool`  | `True`/`False` | `_Bool` |
| `str`   | UTF‑8, immutable | `const char *` |
| `list[T]` | homogeneous, mutable (`list[int]`, `list[str]`, `list[float]`, `list[bool]`) | `List_int`|
| `dict[str,T]` | string keys (runtime ships only `dict[str,int]`) | `Dict_str_int` |
| *User class* | single inheritance | `struct <Class>` |

### Lists

```python
numbers: list[int] = [1, 2, 3]
```

### Dicts

```python
settings: dict[str, int] = {"volume": 10}
```
### Type Conversion

* **Implicit coercion is allowed** in the following cases:
  - **Numeric widening**: `bool → int → float` (e.g., a `bool` can be passed to a function expecting an `int`).
  - **Subclass compatibility**: Instances of a subclass can be used where a superclass is expected.

* **No implicit coercion** is performed between unrelated types (e.g., `str → int`, or unrelated classes).

* **Explicit conversion** is still available using built-in constructors: `int(x)`, `float(x)`, `str(x)`, `bool(x)`.

---

## 4. Declarations

### Variables

```python
x: int = 5      # type + initializer are both required
```
Re‑assignment must keep the same static type.

### Functions

Explicit parameter and return annotations:

```python
def add(x: int, y: int) -> int:
    return x + y
```

Default parameters allowed:

```python
def inc(x: int, step: int = 1) -> int:
    return x + step
```

* All parameters typed; defaults allowed.  
* Nested functions **not supported**.  
* `return` outside a function is a parser error.

### Classes

Support for single inheritance.

```python
class Enemy:
    hp: int = 100
    def heal(self, amt: int) -> None:
        self.hp += amt

class Boss(Enemy):
    rage: int = 0
```

* Single inheritance; empty body is a parser error.  
* Fields may be explicit (`hp`) or inferred from `self.x = …` in `__init__`.  
* No `super()` helper yet – call base methods directly (`Enemy__heal(self, 5)`).

---

## 5. Statements

| Statement | Notes |
|-----------|-------|
| `if / elif / else` | standard, no `elif` fall‑through quirks |
| `while cond:` | no `else` clause (not implemented) |
| `for v in range(...)` | *only* `range` is iterable; compiles to a `for` loop in C |
| `break / continue / pass` | only inside loops |
| `assert expr` | runtime check → `pb_fail` on failure |
| `try / except` | parses & type‑checks, but code‑gen emits a comment (no runtime) |
| `raise expr` | aborts (`pb_fail("Exception raised")`) |

### Exception Handling

```python
try:
    risky()
except RuntimeError:
    print("Caught an error")
```
### Function Calls

Supports positional and keyword arguments:

```python
add(5, 3)
increment(10)
increment(10, 2)
```

### Attribute & Index Access

```python
player.hp
numbers[0]
settings["volume"]
```

### String Interpolation

F-string syntax supports full expressions inside `{}`:
- Literals: `f"pi ≈ {3.14}"`
- Arithmetic: `f"Total: {price * qty}"`
- Function calls: `f"Score: {get_score()}"`
- Method calls: `f"HP: {self.hp}"`
- Attribute access: `f"User: {player.name}"`

Resulting C code uses `snprintf` for efficient formatting at compile-time.


### Expression Postfixes

All of these can be chained in any order:

* **Indexing**: `expr[expr]`
* **Attribute**: `expr.attr`
* **Call**: `expr(arg, …)`

Example:

```python
obj.method()[i](x)
```

---

## 6. Expressions & Operators

| Category   | Operators                        | Notes                                          |
| ---------- | -------------------------------- | ---------------------------------------------- |
| Arithmetic | `+`, `-`, `*`, `/`, `//`, `%`    | boolean arithmetic (`True + 1`) is a type error.       |
| Comparison | `==`, `!=`, `<`, `<=`, `>`, `>=` |                                                |
| Identity   | `is`, `is not`                   | Only valid on bools → compiles to `==` / `!=`. |
| Logical    | `and`, `or`, `not`               |                                                |

Precedence: `not` > `*`/`/`/`//`/`%` > `+`/`-` > `<`/`>`/… > `==`/`!=`/`is` > `and` > `or`.

Logical ops compile to `&&` / `||`; `is`→`==`, `is not`→`!=`.

Arithmetic allowed only on `int`/`float`.

---

## 7. Modules & Imports

* One `.pb` file = one module.  
* Absolute imports only (`import math.stats`); no relative imports yet.

Global variables are module‑scoped; use `global name` inside a function to assign to them.

---

## 8. Built-in Functions

`print`, `range`.  
`print` chooses helper (`pb_print_int`, `pb_print_bool`, …) based on static type.

---

## 9. Compile‑time & Error Model

| Phase | Errors raised |  When |
|-------|---------------| ---------------|
| Lexing | LexerError | mixed tabs/spaces, bad token, invalid f‑string placeholder |
| Parsing | ParserError | `break` outside loop, empty class, chained comparison, duplicate param, etc. |
| Type check | TypeError | mismatched types, heterogeneous list, arithmetic on non‑numeric, etc. |
| Runtime | ConversionError, RuntimeError | failed `assert`, explicit `raise` → abort |

Compilation stops at the first error per phase.

---

## 10. From PB to C99 — Mapping Highlights

| PB construct | Emitted C |
|--------------|-----------|
| Module | single `.c` file with standard headers (`stdio.h`, `stdint.h`, …) |
| `int / float / bool / str` | `int64_t / double / bool / const char *` |
| `list[int]` | `typedef struct { int64_t len; int64_t *data; } List_int;` |
| `dict[str,int]` | `Dict_str_int` plus `pb_dict_get` |
| Function | `ret_type name(params…) { … }` |
| Method `Class.m` | free function `Class__m(Class * self, …)` |
| Constructor `Class(...)` | stack struct `__tmp_<id>` + call to `Class____init__` |
| `for i in range(a,b):` | `for(int64_t i=a; i<b; ++i){ … }` |
| `assert e` | `if(!(e)) pb_fail("Assertion failed");` |
| `print(x)` | dispatches to helper chosen at code‑gen time |

Dynamic features (exceptions, dynamic dispatch) generate stub comments until implemented.

---

## 11. Differences vs. Python 3

| Area | Python 3 | PB 1.0 |
|------|----------|--------|
| Typing | dynamic; optional hints | **mandatory static types** |
| Lists / dicts | heterogeneous | homogeneous; `list[int | float | bool | str]`, `dict[str,int]` |
| Dispatch | dynamic (`obj.m()`) | static (`Class__m(obj, …)`) |
| Inheritance | multiple, `super()` | single, no `super()` helper |
| Loops | any iterable | only `range` |
| Exceptions | full runtime | parsed but aborts at runtime |
| Extras | comprehensions, lambdas, decorators, etc. | **not implemented** |

---

## 12. Quick Cheat‑sheet

```pb
# hello.pb
hello: str = "Hello World"

def main() -> int:
    print(hello)
    return 0
```

```
$ python run.py run .\examples\hello.pb
```

The reference script **`lang.pb`** exercises every feature and is guaranteed to compile.

### Toolchain

```
$python run.py -h
usage: run.py [-h] [-v] [-d] {toc,build,run} file

PB Language Toolchain

positional arguments:
  {toc,build,run}  Action to perform
  file             Path to .pb source file

options:
  -h, --help       show this help message and exit
  -v, --verbose    Enable verbose output
  -d, --debug      Enable debug output
```

---

## 13. Not Yet Implemented / Road‑map

* Multi-line and raw strings
* Enums
* Variadic arguments
* Relative imports
* Standard library in PB

---

### Design Notes

* Tabs forbidden in indentation – portability & tooling.  
* No bool arithmetic – avoids subtle bugs.  
* Simple F‑strings keep lexer and code‑gen trivial yet useful.  
* Static dispatch & structs map 1‑to‑1 onto C, yielding fast, predictable binaries.

*Happy coding in PB!*

-- 

_Last updated : 2025‑05‑14_
