"""
python examples\arr_rw.pb
[10]
10
list assignment index out of range
[1]
1
LEN(a): 1
"""


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

    print("LEN(a):", len(a)) # PB returns -> TypeError: Call to undefined function 'len'

if __name__ == "__main__":
    main()
