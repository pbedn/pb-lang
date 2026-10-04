# PB language

An experimental language with Python-like syntax, explicit static types, and C99
output. It implements functions, classes, built-in containers, enums, imports,
file I/O, runtime exceptions, and an initial native binding API.

```python
def main() -> int:
    message: str = "Hello " + "World"
    print(message)
    return 0
```

Install Python 3.13 or later, GCC, and GNU `ar`, then:

```text
python -m pip install -r requirements.txt
python run.py run examples/hello.pb
python run.py buildlib
python -m pytest -q
```

`toc`, `build`, and `run` generate C, build an executable, or build and run.
Outputs go into `build/`. Windows users can use a portable MinGW/GCC toolchain.

The bundled Raylib library targets Windows. Build `examples/ray_pong.pb`, then
launch `build/ray_pong.exe`. W/S and the arrows move paddles, Space pauses, and
Escape closes. No sound files or other assets are required.

```text
python run.py build examples/ray_pong.pb
python benchmark/pb_bench.py --quick --repeats 1
```

PB is a prototype, not a drop-in Python replacement. See the
[specification](ref/spec.md), [roadmap](ref/roadmap.md), and
[branch consolidation record](ref/branch-consolidation.md) for current behavior,
limitations, and the source work preserved from retired branches.
