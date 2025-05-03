# lang.pb
# This file demonstrates all currently implemented features of the language.
# Each section includes comments describing what is tested.

# === Function definition with parameters and return value ===
def add(x: int, y: int) -> int:
    # Local variable assignment and arithmetic expression
    result = x + y
    
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
    # Function call and assignment
    print("=== Function Call ===")
    total = add(10, 5)
    
    # If/Else statement using a function returning bool
    print("=== If/Else ===")
    if is_even(total):
        print("Total is even")
    else:
        print("Total is odd")
    
    # While loop with condition and local variable update
    print("=== While Loop ===")
    counter = 0
    while counter < 3:
        print(counter)
        counter = counter + 1  # Reassignment
    
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
    first_number = numbers[0]  # IndexExpr
    second_number = numbers[1]
    print(first_number)
    print(second_number)
    
    # Boolean literals and logical operators
    print("=== Boolean Literals ===")
    x = True
    y = False
    if x and not y:  # Logical AND and NOT
        print("x is True and y is False")
    
    # Return statement to indicate success
    return 0
