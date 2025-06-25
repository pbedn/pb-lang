class RuntimeError(BaseException):
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
