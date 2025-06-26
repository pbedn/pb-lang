def main():
    s: int = 0
    for i in range(50_000_000):
        s += (i % 10) * (i // 3)
    print(s)


if __name__ == "__main__":
    main()
