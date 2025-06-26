# python examples\exception.pb
# division by zero

class RuntimeError(BaseException): # PB -> TypeError: Base class 'BaseException' not defined before 'RuntimeError'
    pass

def crash():
    raise RuntimeError("division by zero")

def main():
    try:
        crash()
    except RuntimeError as exc:
        print(exc)

if __name__ == "__main__":
    main()
