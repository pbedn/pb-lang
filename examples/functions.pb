def print_int(x: int):
    print(x)

def add(x: int, y: int) -> int:
    return x + y

def add_in_place(x: int, y: int) -> None:
    x += y
    print_int(x)

def main():
    x: int = 10
    y: int = 20
    z: int = add(x, y)
    print_int(z)
    add_in_place(x, y)
