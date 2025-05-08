# 📜 Language Specification: PB (Full Version)

## 1. Introduction & Philosophy

PB is a **statically and strongly typed programming language** that features Python-like syntax and compiles to C (targeting C99). It is designed to be minimal, fast, and safe, intentionally avoiding dynamic typing and garbage collection. PB prioritizes readability and simplicity, enabling Python developers to write high-performance code with clear C semantics under the hood.

---

## 2. Lexical Structure

### Identifiers

Identifiers consist of letters, digits, and underscores and must begin with a letter or underscore:

```
[a-zA-Z_][a-zA-Z0-9_]*
```

### Keywords

Reserved words include:

```
and, as, assert, break, class, continue, def, elif, else, except,
False, for, global, if, import, in, is, not, or, pass,
raise, return, True, try, while
```
> **Note:** `True` and `False` are keywords (not re-bindable). Any attempt to assign, delete, or bind them is a compile-time `SyntaxError`. Lowercase `true`/`false` are ordinary identifiers.

### Literals

* **Integer literals**: `42`, `1_000`
* **Float literals**: `3.14`, `1_000.0`, `6.022_140e23`

  * **Underscores** may separate digits anywhere; they are stripped at lexing.
  * At least one digit before **and** after the dot; **no** leading-dot (`.5`) or trailing-dot (`5.`) forms are allowed.
* **String literals**: single- or double-quoted, single-line only (e.g., `"Hello"`, `'world'`). Escape sequences (`\n`, `\\`, etc.) are decoded; invalid escapes raise a `LexerError` with the raw lexeme.
* **F-string literals**: `f"..."` or `f'...'`, single-line only.

  * The lexer emits a single `FSTRING_LIT` token whose value is the decoded content **including** literal `{...}` sequences (no expression splitting yet).
* **Boolean literals**: `True`, `False` (keywords)

| Kind         | Examples                                  | Notes                                                                           |
| ------------ | ----------------------------------------- | ------------------------------------------------------------------------------- |
| **Integer**  | `42`, `1_000`, `6_021_700`                | Underscores are discarded; lexed value is the digit string without underscores. |
| **Float**    | `3.14`, `2_5.0`, `6.022_140e23`, `1.0e-3` | Must have digits both sides of `.`; exponent optional.                          |
| **String**   | `"Hello"`, `'world'`                      | Single-line only; supports `\\` escapes.                                        |
| **F-string** | `f"Value: {x}"`                           | Single-line; braces preserved in value; no nested parsing of `{}` yet.          |
| **Boolean**  | `True`, `False`                           | Cannot be redefined.                                                            |

### Comments

* Single-line comments begin with `#`, but only when **not** inside a string or f-string literal.
* The lexer removes comments entirely; no comment tokens.

### Indentation & Whitespace

* **Indentation is significant**.
* **Spaces-only** for indentation; tabs in indentation cause a `LexerError`.
* **Mixed spaces+tabs** in leading whitespace is a `LexerError`.
* Tabs within code (after indent) are preserved but rare.
* Tabs in the indent are converted to four spaces.
* The lexer emits `NEWLINE` even for blank or comment-only lines.
* `INDENT` / `DEDENT` tokens always use column 1.

---

## 3. Types

### Primitive Types

* `int`: arbitrary-precision at compile time; lowered to `int64_t` (or `int128_t` if needed).
* `float`: IEEE-754 `double`.
* `bool`: C99 `_Bool` via `<stdbool.h>`, values `true`/`false`.
* `str`: UTF-8 encoded, immutable.

### Lists

- Homogeneous, mutable sequences.

```python
numbers: list[int] = [1, 2, 3]
```

### Dicts

- Keys must be strings; values can be any type.

```python
settings: dict[str, int] = {"volume": 10}
```
### Type Conversion

* No implicit coercion.
* Explicit conversion via built-ins: `int(x)`, `float(x)`, `str(x)`.

---

## 4. Declarations

### Variables

Must declare type:

```python
x: int = 5
threshold: float = 3.5
```

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

### Classes

Support for single inheritance.

```python
class Player:
    species: str = "Human"  # class attribute

    def __init__(self, hp: int, mp: int = 100):
        self.hp: int = hp
        self.mp: int = mp
        self.name: str = "Hero"

    def get_name(self) -> str:
        return self.name

class Mage(Player):
    mana: int = 200
    def __init__(self, hp: int):
        super().__init__(hp)
        self.spell_power: int = 300

```

Class and instance attributes are distinct. Instance attributes must be initialized in `__init__`.

---

## 5. Statements & Grammar Highlights

* **One file** = one module.
* **Absolute imports only**: `import utils`.
* **global** keyword for function-local globals.
* **Control flow**: `if`/`elif`/`else`, `while`, `for … in` (supports any iterable).
* **Exception handling**: `try` / `except [Exception [as alias]]`.
* **Assertions**: `assert condition` (can be omitted in release).
* **bind & assign**: `x = …`, augmented `+=`, `-=`, `*=`, `/=`, `//=`, `%=`, plus indexing and attribute write.
* **pass**, **break**, **continue**, **return**, **raise**.

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

F-string syntax supports variables and attributes only:

```python
f"HP: {self.hp}"
f"Hello, {name}!"
```

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
| Arithmetic | `+`, `-`, `*`, `/`, `//`, `%`    | No bool arithmetic (`True + 1` illegal).       |
| Comparison | `==`, `!=`, `<`, `<=`, `>`, `>=` |                                                |
| Identity   | `is`, `is not`                   | Only valid on bools → compiles to `==` / `!=`. |
| Logical    | `and`, `or`, `not`               |                                                |

* **Precedence**: `not` > `*`/`/`/`//`/`%` > `+`/`-` > `<`/`>`/… > `==`/`!=`/`is` > `and` > `or`.

---

## 7. Modules & Imports

* **One file per module**.
* **All names** are module-scoped unless declared `global`.
* **Only absolute imports**: no relative imports.

---

## 8. Built-in Functions

* `print(...)`
* `range(...)` (for `for` loops)
* `int(...)`, `float(...)`, `str(...)`
* `assert(...)`

---

## 9. Error Model

### Built-in Exceptions

* **LexerError**: bad token, mixed indent, unterminated string, etc.
* **ParserError**: grammar violations.
* **TypeError**: static type mismatches.
* **ConversionError**: explicit cast failures.
* **RuntimeError**: user exceptions (raised via `raise`).

---

## 10. Codegen Mapping (C99)

No implemented yet

---

## 11. Planned & Future Features

* Multi-line and raw strings
* Enums, decorators
* Generics / templates
* Variadic arguments
* Relative imports
* Full standard library in PB

---

### Design Notes & Motivation

1. **True/False as keywords**: prevents shadowing and simplifies codegen.
2. **No bool arithmetic**: avoids Python quirks.
3. **Strict indentation**: consistent spaces-only policy.
4. **F-strings**: simple, single-token for now; richer parsing later.
5. **Explicit typing**: no implicit coercion, clearer C semantics.
