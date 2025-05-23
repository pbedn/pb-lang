## 📄 Files

### `ref/lang.pb`

**The source program written in the custom language.**

This file demonstrates all currently implemented features such as:

- Functions and return types
- Loops (`while`, `for`)
- Conditionals (`if`, `elif`, `else`)
- Lists and indexing
- Boolean literals and logical operators
- Augmented assignment
- Special operators (`is`, `is not`)
- The `pass` statement

It serves as the **input to the compiler pipeline.**

---

### `ref/lang.c`

**The C code generated by compiling `lang.pb`.**

This is a **direct C translation** of the `lang.pb` source,
fully statically typed and compilable with standard C tools (e.g., GCC).
It serves as the **expected ("golden") output** in tests to ensure the compiler
(lexer → parser → type checker → code generator) produces correct and stable results.

---

## 🚀 Example

To compile the language:

```bash
python run.py toc ref/lang.pb
```
