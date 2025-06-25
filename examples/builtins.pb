def main():
    x: int = 10
    y: float = 1.0
    z: float = 0.0
    a: str = "1"
    b: str = "1.0"

    x_float: float = float(x)
    print(f"x: {x}, x_float: {x_float}")

    b_float: float = float(b)
    print(f"b: '{b}', b_float: {b_float}")

    y_int: int = int(y)
    print(f"y: {y}, y_int: {y_int}")

    a_int: int = int(a)
    print(f"a: '{a}', a_int: {a_int}")

    x_bool: bool = bool(x)
    print(f"x: {x}, x_bool: {x_bool}")

    y_bool: bool = bool(y)
    print(f"y: {y}, y_bool: {y_bool}")

    z_bool: bool = bool(z)
    print(f"z: {z}, z_bool: {z_bool}")

    # List int conversions
    arr: list[int] = [1, 2, 3]
    arr[0] = int(4.5)
    print(arr)

    arr2: list[str] = ["1", "2", "3"]
    arr2[0] = str(4)
    print(arr2)
    
    arr3: list[float] = [1.1, 2.2, 3.3]
    arr3[0] = float(4)
    print(arr3)
    
    arr4: list[bool] = [True, False]
    arr4[0] = bool(1)
    print(arr4)

if __name__ == "__main__":
    main()
