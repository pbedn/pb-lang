from raylib import *

def main() -> None:
    InitWindow(800, 600, "Hello Raylib")
    SetTargetFPS(60)
    while not WindowShouldClose():
        BeginDrawing()
        ClearBackground(RAYWHITE)
        DrawText("PB + Raylib", 300, 300, 20, DARKGRAY)
        EndDrawing()
    CloseWindow()
