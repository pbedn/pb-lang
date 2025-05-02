def main() -> int:
    print("Counting up:")
    for i in range(0, 5):
        print(i)

    print("Single-arg range:")
    for j in range(3):
        print(j)

    print("For loop with break:")
    for i in range(10):
        print(i)
        if i == 5:
            break

    print("While loop with break")
    i = 0
    while True:
        print(i)
        if i == 5:
            break
        i = i + 1
    return 0
