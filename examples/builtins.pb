# python .\examples\builtins.pb
# x: 10, x_float: 10.0
# b: '1.0', b_float: 1.0
# y: 1.0, y_int: 1
# a: '1', a_int: 1
# x: 10, x_bool: True
# y: 1.0, y_bool: True
# z: 0.0, z_bool: False
# [4, 2, 3]
# ['4', '2', '3']
# [4.0, 2.2, 3.3]
# [True, False]

# PB
# python run.py run .\examples\builtins.pb
# x: 10, x_float: 10.0
# b: '1.0', b_float: 1.0
# y: 1.0, y_int: 1
# a: '1', a_int: 1
# x: 10, x_bool: True
# y: 1.0, y_bool: True
# z: 0.0, z_bool: False
# [4, 2, 3]
# ['4', '2', '3']
# [4, 2.2, 3.3]
# [True, False]

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
