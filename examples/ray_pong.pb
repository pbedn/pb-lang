# Two-player Pong. W/S move the left paddle; arrows move the right.
# Space pauses or resumes. Escape closes the window. No external assets needed.
from raylib import (
    InitWindow, CloseWindow, SetTargetFPS, WindowShouldClose, GetFrameTime,
    IsKeyDown, IsKeyPressed, KEY_W, KEY_S, KEY_UP, KEY_DOWN, KEY_SPACE,
    BeginDrawing, EndDrawing, ClearBackground, DrawRectangle, DrawCircle,
    DrawLine, DrawText, RAYWHITE, DARKGRAY
)

def main() -> int:
    InitWindow(800, 600, "PB Pong - W/S and arrows")
    SetTargetFPS(60)
    left_y: float = 250.0
    right_y: float = 250.0
    ball_x: float = 400.0
    ball_y: float = 300.0
    velocity_x: float = 320.0
    velocity_y: float = 180.0
    left_score: int = 0
    right_score: int = 0
    paused: bool = False

    while not WindowShouldClose():
        dt: float = GetFrameTime()
        if dt > 0.05:
            dt = 0.05
        if IsKeyPressed(KEY_SPACE):
            paused = not paused
        if not paused:
            if IsKeyDown(KEY_W):
                left_y -= 400.0 * dt
            if IsKeyDown(KEY_S):
                left_y += 400.0 * dt
            if IsKeyDown(KEY_UP):
                right_y -= 400.0 * dt
            if IsKeyDown(KEY_DOWN):
                right_y += 400.0 * dt
            if left_y < 0.0:
                left_y = 0.0
            if left_y > 500.0:
                left_y = 500.0
            if right_y < 0.0:
                right_y = 0.0
            if right_y > 500.0:
                right_y = 500.0

            ball_x += velocity_x * dt
            ball_y += velocity_y * dt
            if ball_y < 10.0:
                ball_y = 10.0
                velocity_y = -velocity_y
            if ball_y > 590.0:
                ball_y = 590.0
                velocity_y = -velocity_y
            if velocity_x < 0.0 and ball_x < 45.0 and ball_x > 15.0:
                if ball_y >= left_y and ball_y <= left_y + 100.0:
                    ball_x = 45.0
                    velocity_x = -velocity_x
            if velocity_x > 0.0 and ball_x > 755.0 and ball_x < 785.0:
                if ball_y >= right_y and ball_y <= right_y + 100.0:
                    ball_x = 755.0
                    velocity_x = -velocity_x
            if ball_x < 0.0:
                right_score += 1
                ball_x = 400.0
                ball_y = 300.0
                velocity_x = 320.0
            if ball_x > 800.0:
                left_score += 1
                ball_x = 400.0
                ball_y = 300.0
                velocity_x = -320.0

        BeginDrawing()
        ClearBackground(DARKGRAY)
        DrawLine(400, 0, 400, 600, RAYWHITE)
        DrawRectangle(20, int(left_y), 15, 100, RAYWHITE)
        DrawRectangle(765, int(right_y), 15, 100, RAYWHITE)
        DrawCircle(int(ball_x), int(ball_y), 10.0, RAYWHITE)
        DrawText(f"{left_score} : {right_score}", 345, 20, 30, RAYWHITE)
        if paused:
            DrawText("PAUSED - Space to resume", 240, 280, 24, RAYWHITE)
        EndDrawing()

    CloseWindow()
    return 0
