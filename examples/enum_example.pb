from enum import Enum

class Scene(Enum):
    MENU = 1
    GAME = 2

def main():
    print(Scene.MENU)

if __name__ == "__main__":
    main()
