
def main():
    arr_int: list[int] = [100]
    print(arr_int[0])
    arr_int[0] = 1
    x: int = arr_int[0]
    print(x)
    print(arr_int[0])
    print(arr_int)

    arr_str: list[str] = ["a", 'b']
    print(arr_str[0])
    arr_str[0] = "C"
    arr_str[1] = "C"
    # arr_str[2] = "C"  # this will raise IndexError
    try:
        arr_str[2] = "C"
    except IndexError:
        print(f"Caught Index Error for list element with index 2")
    print(arr_str[0])
    print(arr_str)

    arr_bool: list[bool] = [True]
    arr_bool[0] = False
    print(arr_bool)

    arr_str2: list[str] = ["some string", 'word', 'L']
    print(arr_str2)
