x: int  = 1
def main():
    print(f"{x * 2.0}")
    print(f"{x * False}")

def init():
    print("init runs")

if __name__ == "__main__":
    init()
