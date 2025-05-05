# lang.pb
# This file demonstrates all currently implemented features of the language.
# Each section includes comments describing what is tested.

# === Global variable declaration ===
counter: int = 100

# === Function definition with parameters and return value ===
def add(x: int, y: int) -> int:
    # Local variable assignment and arithmetic expression
    result: int = x + y
    
    # Print statements (strings and integers)
    print("Adding numbers:")
    print(result)
    
    # Return statement
    return result

# === Function returning a boolean (demonstrates bool literals and if/else) ===
def is_even(n: int) -> bool:
    if n % 2 == 0:
        return True  # Built-in bool literal
    else:
        return False

# === Main function showcasing all features ===
def main() -> int:
    print("=== Global Variable Before Update ===")
    print(counter)

    global counter
    counter = 200

    print("=== Global Variable After Update ===")
    print(counter)

    # Function call and assignment
    print("=== Function Call ===")
    total: int = add(10, 5)

    # Explicit var declaration (VarDecl)
    print("=== Handle Float/Double ===")
    threshold: float = 50.0
    print(threshold)
    
    # If/Else statement using a function returning bool
    print("=== If/Else ===")
    if is_even(total):
        print("Total is even")
    else:
        print("Total is odd")
    
    # While loop with condition and local variable update
    print("=== While Loop ===")
    loop_counter: int = 0
    while loop_counter < 3:
        print(loop_counter)
        loop_counter = loop_counter + 1  # Reassignment
    
    # For loop using range(start, end)
    print("=== For Loop with range(0, 3) ===")
    for i in range(0, 3):
        print(i)
    
    # For loop using range(end)
    print("=== For Loop with range(2) ===")
    for j in range(2):
        print(j)
    
    # For loop with break and continue control flow
    print("=== Break and Continue ===")
    for k in range(0, 5):
        if k == 2:
            continue  # Skip current iteration
        if k == 4:
            break  # Exit loop
        print(k)
    
    # List literal and indexing
    print("=== List and Indexing ===")
    numbers = [100, 200, 300]  # ListExpr
    first_number: int = numbers[0]  # IndexExpr
    second_number: int = numbers[1]
    print(first_number)
    print(second_number)
    
    # Boolean literals and logical operators
    print("=== Boolean Literals ===")
    x: bool = True
    y: bool = False
    if x and not y:  # Logical AND and NOT
        print("x is True and y is False")

    # Boolean list and indexing
    print("=== Boolean List and Indexing ===")
    flags = [True, False, True]
    first_flag: bool = flags[0]
    second_flag: bool = flags[1]
    print(first_flag)
    print(second_flag)

    # If/Elif/Else chain
    print("=== If/Elif/Else ===")
    n: int = 5
    if n == 0:
        print("zero")
    elif n == 5:
        print("five")
    else:
        print("other")

    # Pass statement demonstration
    print("=== Pass Statement ===")
    if True:
        pass
    print("Pass block completed")

    # 'is' and 'is not' operators
    print("=== Is / Is Not Operators ===")
    a: int = 10
    b: int = 10
    if a is b:
        print("a is b")
    if a is not 20:
        print("a is not 20")

    # Augmented assignment demonstration
    print("=== Augmented Assignment ===")
    m: int = 5
    print(m)
    m += 3
    print(m)
    m -= 2
    print(m)
    m *= 4
    print(m)
    m /= 2
    print(m)
    m %= 3
    print(m)

    
    # Return statement to indicate success
    return 0
