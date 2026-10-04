# PB language specification

Updated October 4, 2026. This document describes the implementation on `master`.
PB is an experimental, statically typed language with Python-like syntax and C99
output. It implements a subset of Python, not a drop-in interpreter or a
production memory-safe language.

## Toolchain

Python 3.13 or later, GCC, and GNU `ar` are required for builds. Install the Python
dependencies with `python -m pip install -r requirements.txt`.

```text
python run.py toc examples/hello.pb
python run.py build examples/hello.pb
python run.py run examples/hello.pb
python run.py buildlib
python -m pytest -q
```

Generated headers, C sources, runtime archives, and executables go into `build/`.
`toc` performs lexing, parsing, type checking, and generation; `build` also compiles
and links; `run` builds and executes. Native/vendor programs must be launched
manually. Build and executable failures produce a nonzero command exit status.

## Lexical rules

Source uses UTF-8, significant indentation with spaces, and `#` comments. Tabs in
indentation are rejected. Integer/float literals support digit separators;
hexadecimal integers are supported. Strings support quotes, escapes, raw prefixes,
and triple-quoted multiline forms. F-strings support expressions in `{...}` but
not conversions or format specifications such as `!r` and `:.2f`.

`True`, `False`, and `None` are literals. `True` and `False` cannot be rebound.
Lowercase `true` and `false` are ordinary identifiers.

## Types and bindings

| PB type | C representation | Implementation |
| --- | --- | --- |
| `int` | `int64_t` | Signed 64-bit arithmetic |
| `float` | `double` | Floating-point arithmetic |
| `bool` | `bool` | Boolean values |
| `str` | `const char *` | UTF-8 text, `+` and `+=` concatenation |
| `list[T]` | `List_T` | Indexed access, append, pop, remove |
| `set[T]` | `Set_T` | Literal construction, printing, iteration |
| `dict[str, T]` | `Dict_str_T` | Lookup and updates of existing keys |
| `file` | `PbFile` | Open, read, write, close |
| User class | `struct Class *` | Fields, methods, single inheritance |
| Enum | C enum | Distinct static type and named integer members |

The built-in runtime container element/value types are `int`, `float`, `bool`,
and `str`. Declarations can be generated for other generic types, but their full
runtime methods are not implemented. Variables require explicit types. Class
fields may omit initializers and be set in constructors. Reassignment preserves
the static type. Function parameters are typed; default arguments and return
annotations are supported. Omitted return annotations mean `None`/void.

Numeric argument widening and subclass compatibility are accepted where
implemented. Explicit conversion uses `int`, `float`, `bool`, `str`, and `hex`.
`str` accepts numbers, booleans, and strings; numeric results have stable storage.
Optional types (`T | None`) are parsed and checked, but complete optional-value
runtime lowering remains experimental.

```python
def add(x: int, y: int = 1) -> int:
    return x + y

def main() -> int:
    values: list[int] = [1, 2]
    values.append(add(2))
    print("values:", values)
    return 0
```

`print` evaluates multiple arguments from left to right, separates values with
spaces, and adds one newline. Scalars, built-in containers, and enums can be
mixed. `len` accepts strings and built-in containers. String length/iteration
count UTF-8 code points, not grapheme clusters.

## Containers and loops

`for` supports one- or two-argument `range`, lists, sets, dictionary keys, and
strings. Iterable expressions and range bounds are evaluated once; nested loops
have independent state. Three-argument ranges are not supported.

List assignment must address an existing element: assigning at `len(values)`
raises `IndexError`; use `append` to grow. Negative indices are currently rejected.
Dictionary lookup and updates of missing keys raise `KeyError`. New-key insertion
and deletion need a future mutable dictionary representation.

Set literals remove repeated expressions during generation. General runtime
uniqueness and a complete Python-style set API remain unimplemented. Containers
are C value records: assignment copies length/capacity and shares backing storage.
Element updates can be shared. Resizing a list gives that value new storage and
keeps older copies valid. This differs from Python container identity.

## Classes and enums

Classes support fields, constructors, methods, and single inheritance. Dispatch
is static. Nested attribute reads and assignments work. Local class instances use
managed heap storage and can be returned. Multiple inheritance, `super()`, and
dynamic dispatch are not implemented.

```python
from enum import Enum

class Scene(Enum):
    MENU = 1
    GAME = 2

def main() -> int:
    scene: Scene = Scene.GAME
    print(scene)  # Scene.GAME
    return 0
```

Enum members require explicit integer constants in the signed 32-bit C99 range.
Duplicate names and cross-enum assignments are rejected. Equal-valued aliases
print the first member's name. Enums can be exported, imported under an alias,
or addressed through a module alias. Their C symbols are module-qualified.
`auto()`, string values, and reflective `.name`/`.value` APIs are future work.

## Imports and native bindings

Each `.pb` file is a module. Imports support dotted absolute names, aliases,
`from`, star imports, and parenthesized lists. Search order is stdlib, vendor,
then the entry module directory. `__name__` guards are recognized. Use `global`
to reassign module globals inside functions. Relative imports are unimplemented.
The initial PB stdlib contains `random` and the enum marker.

Vendor `metadata.json` declares include/library paths, link flags, and native
status. Native declarations describe an existing C API and are not generated as
C implementations. Raylib's verified subset is `vendor/raylib/raylib.pb`.
`examples/ray_core.pb` and `examples/ray_pong.pb` use it. Pong supports two-player
movement, wall/paddle bounces, scoring, pause, and close without external assets.
The bundled Raylib library and metadata currently target Windows.

```text
python run.py build examples/ray_pong.pb
build/ray_pong.exe
```

The generator writes experimental `raylib_stub.pb` reference output without
replacing the curated API. General pointer/callback/variadic ABI support and
native struct-by-value lowering are not a supported interface yet. The original
larger C Pong design remains in `ref/pong/`.

## Exceptions and control flow

Conditionals, while/for loops, break, continue, pass, and assert are implemented.
Runtime exceptions use `setjmp`/`longjmp`. `BaseException` is the root; `Exception`,
`RuntimeError`, `ValueError`, `IndexError`, `KeyError`, and `TypeError` are built-in types.
User subclasses inherit a message constructor. Handlers match ancestors and
exact types. Runtime exceptions can carry message payloads; explicit exception
objects must have their message in the first storage slot.

Try/except/finally handles normal completion, unhandled errors, errors raised by
handlers, returns, breaks, and continues. Return expressions are evaluated before
finally. Bare raise inside a handler preserves and re-raises the active payload.
Uncaught errors terminate with a readable message. Internal allocation failures
use `pb_fail` and are not recoverable language exceptions.

## Ownership and lifetime policy

PB has no tracing garbage collector. Runtime allocations for list growth,
concatenated/copied strings, file reads, and local class instances are tracked
and released at orderly process shutdown, including `pb_fail`'s exit path.

Generated code does not free a list when a local leaves scope. Returned values,
aliases, and exceptions make that unsafe. Growth copies into managed storage and
retains previous managed buffers until shutdown so aliases stay valid. C release
helpers only free registered allocations, never borrowed stack arrays.

Container literals initially borrow backing arrays in their C scope. Returning a
built-in container or assigning one to an instance field copies its backing array
into managed storage. Returning a string copies it too. Container copies are
shallow for string elements/values, whose strings must have valid lifetimes.
F-strings still use a shared 256-byte buffer per function. Direct formatting works;
retained interpolated strings need a future owned representation. Multi-argument
printing copies formatted strings before printing to preserve distinct arguments.

This conservative policy retains allocations until exit and is unsuitable for
unbounded allocation in long-running processes. Early reclamation, deep ownership,
reference semantics, and allocation accounting are explicit roadmap work.

## Compatibility and remaining work

PB follows C arithmetic where no Python-specific lowering exists. Negative floor
division/modulo and conversion edge cases are not guaranteed to match Python.
Overflow checks, complete memory safety, general string comparison, full optional
lowering, comprehensions, lambdas, decorators, generators, and closures remain
unimplemented. See [roadmap.md](roadmap.md) and the
[branch consolidation record](branch-consolidation.md) for priorities and provenance.
