# Function definitions with typed parameters and return types
# Arithmetic, conditionals, while loops
# Variable assignment
# Function calls (including nested calls)
# Printing of literals and variables
# Print of different types (str, int, bool)
# Explicit return values

def add(x: int, y: int) -> int:
    return x + y

def is_even(n: int) -> bool:
    return (n % 2) == 0

def print_loop(max_val: int) -> int:
    i = 0
    while i < max_val:
        if is_even(i):
            print("Even:")
            print(i)
        else:
            print("Odd:")
            print(i)
        i = i + 1
    return 0

def main() -> int:
    print("Starting test...")
    result = add(10, 5)
    print("Sum is:")
    print(result)

    print("Testing loop:")
    print_loop(5)

    return 0
