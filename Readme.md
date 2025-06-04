### PB lang

Toy programming language that features Python-like syntax and compiles to C99.

```python
# hello.pb
hello: str = "Hello World"

def main() -> int:
    print(hello)
    return 0
```

```bash
$ python run.py run hello.pb
```
