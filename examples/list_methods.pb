def main():
    nums: list[int] = [1, 2]
    nums.append(3)
    print(nums)
    last: int = nums.pop()
    print(last)
    print(nums)
    nums.append(4)
    nums.remove(1)
    print(nums)

    words: list[str] = []
    words.append("a")
    print(words.pop())
    words.append("b")
    words.remove("b")
    print(words)

if __name__ == "__main__":
    main()
