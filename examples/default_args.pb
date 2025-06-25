def increment(x: int, step: int = 1) -> int:
    return x + step

def main():
    a: int = increment(5)
    b: int = increment(5, 3)
    print(a)
    print(b)

if __name__ == "__main__":
    main()
