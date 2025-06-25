def main():
    a: list[int] = [0] 
    a[0] = 10 
    x: int = a[0] 
    print(a)
    print(x)

    b: list[int] = []
    try:
        b[0] = 1
    except IndexError as exc:
         print(exc)
         b = [1]
    y: int = b[0] 
    print(b)
    print(y)

    print("LEN(a):", len(a)) 

if __name__ == "__main__":
    main()
