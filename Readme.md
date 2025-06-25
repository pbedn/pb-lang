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

List conversions:

```python
arr: list[int] = [1, 2, 3]
arr[0] = int(4.5)
print(arr)  # [4, 2, 3]

arr2: list[str] = ["1", "2", "3"]
arr2[0] = str(4)
print(arr2)  # ['4', '2', '3']
```
