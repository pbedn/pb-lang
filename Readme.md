### PB lang

Toy programming language that features Python-like syntax and compiles to C99.


```python
# hello.pb
hello: str = "Hello World"

def main():
    print(hello)
```

```bash
$ python run.py run hello.pb
```

PB tries to behave like small, statically typed subset of Python, and can be run using `python hello.pb`, however that requires adding `if __name__ == "__main__"` guard:

```python
# hello.pb
hello: str = "Hello World"

def main():
    print(hello)

if __name__ == "__main__":
    main()
```
